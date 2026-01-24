"""Tests for artifact caching module."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from headless_wheel_builder.cache.cli import cache
from headless_wheel_builder.cache.models import (
    CacheEntry,
    CacheStats,
    RegistryConfig,
)
from headless_wheel_builder.cache.registry import RegistryEntry, WheelRegistry
from headless_wheel_builder.cache.storage import ArtifactCache

if TYPE_CHECKING:
    from pathlib import Path


class TestCacheEntry:
    """Tests for CacheEntry model."""

    def test_create_minimal(self) -> None:
        """Test creating with minimal fields."""
        entry = CacheEntry(
            package="test-pkg",
            version="1.0.0",
            wheel_name="test_pkg-1.0.0-py3-none-any.whl",
            sha256="abc123",
            size_bytes=10000,
        )
        assert entry.package == "test-pkg"
        assert entry.version == "1.0.0"
        assert entry.sha256 == "abc123"
        assert entry.created_at is not None
        assert entry.last_accessed is not None

    def test_cache_key(self) -> None:
        """Test cache key generation."""
        entry = CacheEntry(
            package="mypackage",
            version="2.0.0",
            wheel_name="mypackage-2.0.0-py3-none-any.whl",
            sha256="abcdef123456789",
            size_bytes=5000,
        )
        assert entry.cache_key == "mypackage-2.0.0-abcdef123456"

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        entry = CacheEntry(
            package="pkg",
            version="1.0.0",
            wheel_name="pkg-1.0.0.whl",
            sha256="hash123",
            size_bytes=1024,
            source="build",
        )
        d = entry.to_dict()
        assert d["package"] == "pkg"
        assert d["sha256"] == "hash123"
        assert d["source"] == "build"

    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "package": "restored",
            "version": "3.0.0",
            "wheel_name": "restored-3.0.0.whl",
            "sha256": "xyz789",
            "size_bytes": 2048,
            "python_version": "py311",
            "platform": "linux",
            "source": "registry",
        }
        entry = CacheEntry.from_dict(data)
        assert entry.package == "restored"
        assert entry.python_version == "py311"
        assert entry.source == "registry"


class TestCacheStats:
    """Tests for CacheStats model."""

    def test_default_values(self) -> None:
        """Test default values."""
        stats = CacheStats()
        assert stats.total_entries == 0
        assert stats.hit_rate == 0.0
        assert stats.packages == 0

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        stats = CacheStats(
            total_entries=10,
            total_size_bytes=1024000,
            hits=80,
            misses=20,
            hit_rate=0.8,
        )
        d = stats.to_dict()
        assert d["total_entries"] == 10
        assert d["hit_rate"] == 0.8


class TestRegistryConfig:
    """Tests for RegistryConfig model."""

    def test_create(self) -> None:
        """Test creating config."""
        config = RegistryConfig(
            url="https://pypi.example.com/simple/",
            username="user",
            password="secret",
        )
        assert config.url == "https://pypi.example.com/simple/"
        assert config.verify_ssl is True

    def test_from_env(self) -> None:
        """Test creating from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "HWB_REGISTRY_URL": "https://registry.example.com",
                "HWB_REGISTRY_USERNAME": "testuser",
                "HWB_REGISTRY_PASSWORD": "testpass",
            },
        ):
            config = RegistryConfig.from_env()
            assert config is not None
            assert config.url == "https://registry.example.com"
            assert config.username == "testuser"

    def test_from_env_missing(self) -> None:
        """Test creating from env with missing URL."""
        with patch.dict("os.environ", {}, clear=True):
            config = RegistryConfig.from_env()
            assert config is None


class TestArtifactCache:
    """Tests for ArtifactCache storage."""

    def test_add_and_get(self, tmp_path: Path) -> None:
        """Test adding and retrieving wheels."""
        cache_dir = tmp_path / "cache"
        cache = ArtifactCache(cache_dir=cache_dir)

        # Create a test wheel
        wheel_path = tmp_path / "test_pkg-1.0.0-py3-none-any.whl"
        wheel_path.write_bytes(b"test wheel content")

        # Add to cache
        entry = cache.add(
            wheel_path=wheel_path,
            package="test_pkg",
            version="1.0.0",
        )
        assert entry.package == "test_pkg"
        assert entry.size_bytes == len(b"test wheel content")

        # Get from cache
        result = cache.get("test_pkg", "1.0.0")
        assert result is not None
        cached_entry, cached_path = result
        assert cached_entry.package == "test_pkg"
        assert cached_path.exists()

    def test_get_by_hash(self, tmp_path: Path) -> None:
        """Test getting wheel by hash."""
        cache_dir = tmp_path / "cache"
        cache = ArtifactCache(cache_dir=cache_dir)

        wheel_path = tmp_path / "pkg-1.0.0.whl"
        wheel_path.write_bytes(b"content")

        entry = cache.add(wheel_path=wheel_path, package="pkg", version="1.0.0")

        result = cache.get_by_hash(entry.sha256)
        assert result is not None
        assert result[0].package == "pkg"

    def test_contains(self, tmp_path: Path) -> None:
        """Test checking if wheel is cached."""
        cache_dir = tmp_path / "cache"
        cache = ArtifactCache(cache_dir=cache_dir)

        wheel_path = tmp_path / "pkg-1.0.0.whl"
        wheel_path.write_bytes(b"content")
        cache.add(wheel_path=wheel_path, package="pkg", version="1.0.0")

        assert cache.contains("pkg", "1.0.0") is True
        assert cache.contains("pkg", "2.0.0") is False
        assert cache.contains("other", "1.0.0") is False

    def test_list_packages(self, tmp_path: Path) -> None:
        """Test listing packages."""
        cache_dir = tmp_path / "cache"
        cache = ArtifactCache(cache_dir=cache_dir)

        for pkg in ["alpha", "beta", "gamma"]:
            wheel_path = tmp_path / f"{pkg}-1.0.0.whl"
            wheel_path.write_bytes(b"content")
            cache.add(wheel_path=wheel_path, package=pkg, version="1.0.0")

        packages = cache.list_packages()
        assert set(packages) == {"alpha", "beta", "gamma"}

    def test_list_versions(self, tmp_path: Path) -> None:
        """Test listing versions of a package."""
        cache_dir = tmp_path / "cache"
        cache = ArtifactCache(cache_dir=cache_dir)

        for ver in ["1.0.0", "1.1.0", "2.0.0"]:
            wheel_path = tmp_path / f"pkg-{ver}.whl"
            wheel_path.write_bytes(f"content-{ver}".encode())
            cache.add(wheel_path=wheel_path, package="pkg", version=ver)

        versions = cache.list_versions("pkg")
        assert set(versions) == {"1.0.0", "1.1.0", "2.0.0"}

    def test_remove(self, tmp_path: Path) -> None:
        """Test removing a package version."""
        cache_dir = tmp_path / "cache"
        cache = ArtifactCache(cache_dir=cache_dir)

        wheel_path = tmp_path / "pkg-1.0.0.whl"
        wheel_path.write_bytes(b"content")
        cache.add(wheel_path=wheel_path, package="pkg", version="1.0.0")

        assert cache.contains("pkg", "1.0.0") is True
        count = cache.remove("pkg", "1.0.0")
        assert count == 1
        assert cache.contains("pkg", "1.0.0") is False

    def test_clear(self, tmp_path: Path) -> None:
        """Test clearing cache."""
        cache_dir = tmp_path / "cache"
        cache = ArtifactCache(cache_dir=cache_dir)

        for i in range(5):
            wheel_path = tmp_path / f"pkg{i}-1.0.0.whl"
            wheel_path.write_bytes(f"content{i}".encode())
            cache.add(wheel_path=wheel_path, package=f"pkg{i}", version="1.0.0")

        assert len(cache.list_packages()) == 5
        cache.clear()
        assert len(cache.list_packages()) == 0

    def test_stats(self, tmp_path: Path) -> None:
        """Test cache statistics."""
        cache_dir = tmp_path / "cache"
        cache = ArtifactCache(cache_dir=cache_dir)

        # Add some entries
        for i in range(3):
            wheel_path = tmp_path / f"pkg{i}-1.0.0.whl"
            wheel_path.write_bytes(b"a" * (1000 * (i + 1)))
            cache.add(wheel_path=wheel_path, package=f"pkg{i}", version="1.0.0")

        # Generate some hits and misses
        cache.get("pkg0", "1.0.0")  # hit
        cache.get("pkg1", "1.0.0")  # hit
        cache.get("nonexistent", "1.0.0")  # miss

        stats = cache.get_stats()
        assert stats.total_entries == 3
        assert stats.packages == 3
        assert stats.total_size_bytes == 1000 + 2000 + 3000
        assert stats.hits == 2
        assert stats.misses == 1

    def test_lru_eviction(self, tmp_path: Path) -> None:
        """Test LRU eviction when max_entries is exceeded."""
        cache_dir = tmp_path / "cache"
        cache = ArtifactCache(cache_dir=cache_dir, max_entries=3)

        # Add 5 entries (should evict 2)
        for i in range(5):
            wheel_path = tmp_path / f"pkg{i}-1.0.0.whl"
            wheel_path.write_bytes(f"content{i}".encode())
            cache.add(wheel_path=wheel_path, package=f"pkg{i}", version="1.0.0")

        # Should only have 3 entries (the last 3 added)
        entries = cache.list_entries()
        assert len(entries) == 3

    def test_size_eviction(self, tmp_path: Path) -> None:
        """Test size-based eviction."""
        cache_dir = tmp_path / "cache"
        cache = ArtifactCache(cache_dir=cache_dir, max_size_bytes=2000)

        # Add entries that exceed max size
        for i in range(5):
            wheel_path = tmp_path / f"pkg{i}-1.0.0.whl"
            wheel_path.write_bytes(b"a" * 500)
            cache.add(wheel_path=wheel_path, package=f"pkg{i}", version="1.0.0")

        stats = cache.get_stats()
        assert stats.total_size_bytes <= 2000

    def test_copy_to(self, tmp_path: Path) -> None:
        """Test copying wheel to destination."""
        cache_dir = tmp_path / "cache"
        cache = ArtifactCache(cache_dir=cache_dir)

        wheel_path = tmp_path / "pkg-1.0.0-py3-none-any.whl"
        wheel_path.write_bytes(b"wheel content")
        entry = cache.add(wheel_path=wheel_path, package="pkg", version="1.0.0")

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        dest_path = cache.copy_to(entry, dest_dir)

        assert dest_path.exists()
        assert dest_path.name == "pkg-1.0.0-py3-none-any.whl"
        assert dest_path.read_bytes() == b"wheel content"

    def test_persistence(self, tmp_path: Path) -> None:
        """Test that cache persists across instances."""
        cache_dir = tmp_path / "cache"

        # Add with first instance
        cache1 = ArtifactCache(cache_dir=cache_dir)
        wheel_path = tmp_path / "pkg-1.0.0.whl"
        wheel_path.write_bytes(b"content")
        cache1.add(wheel_path=wheel_path, package="pkg", version="1.0.0")

        # Load with second instance
        cache2 = ArtifactCache(cache_dir=cache_dir)
        assert cache2.contains("pkg", "1.0.0") is True

    def test_prune_to_size(self, tmp_path: Path) -> None:
        """Test pruning to target size."""
        cache_dir = tmp_path / "cache"
        cache = ArtifactCache(cache_dir=cache_dir)

        # Add entries
        for i in range(5):
            wheel_path = tmp_path / f"pkg{i}-1.0.0.whl"
            wheel_path.write_bytes(b"a" * 1000)
            cache.add(wheel_path=wheel_path, package=f"pkg{i}", version="1.0.0")

        # Total size is 5000, prune to 2000
        pruned = cache.prune_to_size(2000)
        assert pruned >= 3  # Should evict at least 3 entries

        stats = cache.get_stats()
        assert stats.total_size_bytes <= 2000


class TestRegistryEntry:
    """Tests for RegistryEntry model."""

    def test_create(self) -> None:
        """Test creating entry."""
        entry = RegistryEntry(
            package="test",
            version="1.0.0",
            wheel_name="test-1.0.0-py3-none-any.whl",
            sha256="abc123",
            url="https://example.com/test-1.0.0.whl",
        )
        assert entry.package == "test"
        assert entry.url == "https://example.com/test-1.0.0.whl"

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        entry = RegistryEntry(
            package="pkg",
            version="2.0.0",
            wheel_name="pkg-2.0.0.whl",
            sha256="xyz",
            url="https://example.com/pkg.whl",
            size_bytes=5000,
        )
        d = entry.to_dict()
        assert d["package"] == "pkg"
        assert d["size_bytes"] == 5000


class TestWheelRegistry:
    """Tests for WheelRegistry client."""

    @pytest.fixture
    def registry(self) -> WheelRegistry:
        """Create test registry."""
        config = RegistryConfig(url="https://pypi.example.com")
        return WheelRegistry(config)

    @pytest.mark.asyncio
    async def test_list_packages_json(self, registry: WheelRegistry) -> None:
        """Test listing packages with JSON response."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "projects": [
                {"name": "alpha"},
                {"name": "beta"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(registry, "_get_client") as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            packages = await registry.list_packages()

        assert packages == ["alpha", "beta"]

    @pytest.mark.asyncio
    async def test_list_versions_json(self, registry: WheelRegistry) -> None:
        """Test listing versions with JSON response."""
        mock_response = MagicMock()
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "files": [
                {
                    "filename": "pkg-1.0.0-py3-none-any.whl",
                    "hashes": {"sha256": "abc123"},
                    "url": "https://example.com/pkg-1.0.0.whl",
                    "size": 10000,
                },
                {
                    "filename": "pkg-2.0.0-py3-none-any.whl",
                    "hashes": {"sha256": "def456"},
                    "url": "https://example.com/pkg-2.0.0.whl",
                    "size": 15000,
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(registry, "_get_client") as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            entries = await registry.list_versions("pkg")

        assert len(entries) == 2
        assert entries[0].version == "1.0.0"
        assert entries[1].version == "2.0.0"

    @pytest.mark.asyncio
    async def test_check_exists(self, registry: WheelRegistry) -> None:
        """Test checking if version exists."""
        mock_entries = [
            RegistryEntry(
                package="pkg",
                version="1.0.0",
                wheel_name="pkg-1.0.0.whl",
                sha256="abc",
                url="https://example.com/pkg.whl",
            )
        ]

        with patch.object(registry, "list_versions", return_value=mock_entries):
            assert await registry.check_exists("pkg", "1.0.0") is True
            assert await registry.check_exists("pkg", "2.0.0") is False

    @pytest.mark.asyncio
    async def test_to_cache_entry(self, registry: WheelRegistry, tmp_path: Path) -> None:
        """Test converting registry entry to cache entry."""
        reg_entry = RegistryEntry(
            package="pkg",
            version="1.0.0",
            wheel_name="pkg-1.0.0.whl",
            sha256="hash123",
            url="https://example.com/pkg.whl",
        )

        wheel_path = tmp_path / "pkg-1.0.0.whl"
        wheel_path.write_bytes(b"content")

        cache_entry = registry.to_cache_entry(reg_entry, wheel_path)
        assert cache_entry.package == "pkg"
        assert cache_entry.source == "registry"
        assert cache_entry.metadata["registry_url"] == "https://pypi.example.com"


class TestCacheCLI:
    """Tests for cache CLI commands."""

    def test_stats(self, tmp_path: Path) -> None:
        """Test stats command."""
        runner = CliRunner()
        with patch.object(ArtifactCache, "get_stats") as mock_stats:
            mock_stats.return_value = CacheStats(
                total_entries=10,
                packages=5,
                total_size_bytes=100000,
                hits=80,
                misses=20,
                hit_rate=0.8,
            )
            result = runner.invoke(cache, ["stats"])
            assert result.exit_code == 0
            assert "10" in result.output

    def test_stats_json(self, tmp_path: Path) -> None:
        """Test stats command with JSON output."""
        runner = CliRunner()
        with patch.object(ArtifactCache, "get_stats") as mock_stats:
            mock_stats.return_value = CacheStats(total_entries=5)
            result = runner.invoke(cache, ["stats", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["total_entries"] == 5

    def test_list_empty(self, tmp_path: Path) -> None:
        """Test list with empty cache."""
        runner = CliRunner()
        with patch.object(ArtifactCache, "list_entries", return_value=[]):
            result = runner.invoke(cache, ["list"])
            assert result.exit_code == 0
            assert "No cached" in result.output

    def test_list_with_entries(self, tmp_path: Path) -> None:
        """Test list with entries."""
        runner = CliRunner()
        entries = [
            CacheEntry(
                package="pkg",
                version="1.0.0",
                wheel_name="pkg-1.0.0.whl",
                sha256="abc",
                size_bytes=5000,
            )
        ]
        with patch.object(ArtifactCache, "list_entries", return_value=entries):
            result = runner.invoke(cache, ["list"])
            assert result.exit_code == 0
            assert "pkg" in result.output

    def test_packages(self, tmp_path: Path) -> None:
        """Test packages command."""
        runner = CliRunner()
        with patch.object(ArtifactCache, "list_packages", return_value=["alpha", "beta"]):
            with patch.object(ArtifactCache, "list_versions", return_value=["1.0.0"]):
                result = runner.invoke(cache, ["packages"])
                assert result.exit_code == 0
                assert "alpha" in result.output
                assert "beta" in result.output

    def test_get_found(self, tmp_path: Path) -> None:
        """Test get command when wheel is found."""
        runner = CliRunner()
        entry = CacheEntry(
            package="pkg",
            version="1.0.0",
            wheel_name="pkg-1.0.0.whl",
            sha256="abc",
            size_bytes=1000,
        )
        mock_path = tmp_path / "wheel.whl"

        with patch.object(ArtifactCache, "get", return_value=(entry, mock_path)):
            with patch.object(ArtifactCache, "copy_to", return_value=mock_path):
                result = runner.invoke(cache, ["get", "pkg", "1.0.0"])
                assert result.exit_code == 0
                assert "Copied" in result.output

    def test_get_not_found(self, tmp_path: Path) -> None:
        """Test get command when wheel not found."""
        runner = CliRunner()
        with patch.object(ArtifactCache, "get", return_value=None):
            result = runner.invoke(cache, ["get", "pkg", "1.0.0"])
            assert result.exit_code == 1
            assert "Not found" in result.output

    def test_remove_confirmed(self, tmp_path: Path) -> None:
        """Test remove with confirmation."""
        runner = CliRunner()
        with patch.object(ArtifactCache, "contains", return_value=True):
            with patch.object(ArtifactCache, "remove", return_value=1) as mock_remove:
                result = runner.invoke(cache, ["remove", "pkg", "1.0.0", "--yes"])
                assert result.exit_code == 0
                mock_remove.assert_called_once()

    def test_clear_confirmed(self, tmp_path: Path) -> None:
        """Test clear with confirmation."""
        runner = CliRunner()
        with patch.object(ArtifactCache, "get_stats") as mock_stats:
            mock_stats.return_value = CacheStats(total_entries=5)
            with patch.object(ArtifactCache, "clear") as mock_clear:
                result = runner.invoke(cache, ["clear", "--yes"])
                assert result.exit_code == 0
                mock_clear.assert_called_once()

    def test_clear_empty(self, tmp_path: Path) -> None:
        """Test clear on empty cache."""
        runner = CliRunner()
        with patch.object(ArtifactCache, "get_stats") as mock_stats:
            mock_stats.return_value = CacheStats(total_entries=0)
            result = runner.invoke(cache, ["clear", "--yes"])
            assert result.exit_code == 0
            assert "already empty" in result.output

    def test_info_found(self, tmp_path: Path) -> None:
        """Test info command when wheel found."""
        runner = CliRunner()
        entry = CacheEntry(
            package="pkg",
            version="1.0.0",
            wheel_name="pkg-1.0.0.whl",
            sha256="abc123def456",
            size_bytes=5000,
            source="build",
        )
        mock_path = tmp_path / "wheel.whl"

        with patch.object(ArtifactCache, "get", return_value=(entry, mock_path)):
            result = runner.invoke(cache, ["info", "pkg", "1.0.0"])
            assert result.exit_code == 0
            assert "pkg" in result.output
            assert "abc123def456" in result.output

    def test_prune_dry_run(self, tmp_path: Path) -> None:
        """Test prune with dry run."""
        runner = CliRunner()
        with patch.object(ArtifactCache, "get_stats") as mock_stats:
            mock_stats.return_value = CacheStats(total_size_bytes=5000)
            with patch.object(ArtifactCache, "list_entries", return_value=[]):
                result = runner.invoke(cache, ["prune", "--max-size", "1G", "--dry-run"])
                assert result.exit_code == 0
