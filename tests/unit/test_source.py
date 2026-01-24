"""Tests for source resolution."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from headless_wheel_builder.core.source import SourceResolver, SourceSpec, SourceType
from headless_wheel_builder.exceptions import SourceError

if TYPE_CHECKING:
    from pathlib import Path


class TestSourceResolver:
    """Tests for SourceResolver."""

    def test_parse_local_path(self, sample_project: Path) -> None:
        """Test parsing a local path."""
        resolver = SourceResolver()
        spec = resolver.parse_source(str(sample_project))

        assert spec.type == SourceType.LOCAL_PATH
        assert spec.location == str(sample_project)
        assert spec.ref is None

    def test_parse_git_https(self) -> None:
        """Test parsing a git HTTPS URL."""
        resolver = SourceResolver()
        spec = resolver.parse_source("https://github.com/user/repo")

        assert spec.type == SourceType.GIT_HTTPS
        assert spec.location == "https://github.com/user/repo"

    def test_parse_git_https_with_ref(self) -> None:
        """Test parsing a git HTTPS URL with ref."""
        resolver = SourceResolver()
        spec = resolver.parse_source("https://github.com/user/repo@v1.0.0")

        assert spec.type == SourceType.GIT_HTTPS
        assert spec.location == "https://github.com/user/repo"
        assert spec.ref == "v1.0.0"

    def test_parse_git_https_with_subdirectory(self) -> None:
        """Test parsing a git URL with subdirectory."""
        resolver = SourceResolver()
        spec = resolver.parse_source("https://github.com/user/repo@main#subdirectory=packages/foo")

        assert spec.type == SourceType.GIT_HTTPS
        assert spec.location == "https://github.com/user/repo"
        assert spec.ref == "main"
        assert spec.subdirectory == "packages/foo"

    def test_parse_git_ssh(self) -> None:
        """Test parsing a git SSH URL."""
        resolver = SourceResolver()
        spec = resolver.parse_source("git@github.com:user/repo.git")

        assert spec.type == SourceType.GIT_SSH

    def test_parse_tarball_url(self) -> None:
        """Test parsing a tarball URL."""
        resolver = SourceResolver()
        spec = resolver.parse_source("https://example.com/package-1.0.0.tar.gz")

        assert spec.type == SourceType.TARBALL

    def test_parse_invalid_source(self, tmp_path: Path) -> None:
        """Test parsing an invalid source."""
        resolver = SourceResolver()
        nonexistent = tmp_path / "nonexistent"

        with pytest.raises(SourceError, match="Cannot determine source type"):
            resolver.parse_source(str(nonexistent))

    @pytest.mark.asyncio
    async def test_resolve_local_path(self, sample_project: Path) -> None:
        """Test resolving a local path."""
        resolver = SourceResolver()
        spec = SourceSpec(type=SourceType.LOCAL_PATH, location=str(sample_project))

        resolved = await resolver.resolve(spec)

        assert resolved.local_path == sample_project
        assert not resolved.is_temporary

    @pytest.mark.asyncio
    async def test_resolve_local_path_not_found(self, tmp_path: Path) -> None:
        """Test resolving a nonexistent path."""
        resolver = SourceResolver()
        spec = SourceSpec(type=SourceType.LOCAL_PATH, location=str(tmp_path / "nonexistent"))

        with pytest.raises(SourceError, match="does not exist"):
            await resolver.resolve(spec)

    @pytest.mark.asyncio
    async def test_resolve_local_path_no_pyproject(self, empty_dir: Path) -> None:
        """Test resolving a directory without pyproject.toml."""
        resolver = SourceResolver()
        spec = SourceSpec(type=SourceType.LOCAL_PATH, location=str(empty_dir))

        with pytest.raises(SourceError, match="No pyproject.toml"):
            await resolver.resolve(spec)

    @pytest.mark.asyncio
    async def test_resolve_local_with_subdirectory(
        self, tmp_path: Path, sample_pyproject_content: str
    ) -> None:
        """Test resolving a local path with subdirectory."""
        # Create nested project
        root = tmp_path / "monorepo"
        root.mkdir()
        pkg_dir = root / "packages" / "mypackage"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "pyproject.toml").write_text(sample_pyproject_content)
        (pkg_dir / "src").mkdir()

        resolver = SourceResolver()
        spec = SourceSpec(
            type=SourceType.LOCAL_PATH,
            location=str(root),
            subdirectory="packages/mypackage",
        )

        resolved = await resolver.resolve(spec)

        assert resolved.local_path == pkg_dir


class TestSourceSpec:
    """Tests for SourceSpec dataclass."""

    def test_create_local_spec(self) -> None:
        """Test creating a local path spec."""
        spec = SourceSpec(type=SourceType.LOCAL_PATH, location="/path/to/project")

        assert spec.type == SourceType.LOCAL_PATH
        assert spec.location == "/path/to/project"
        assert spec.ref is None
        assert spec.subdirectory is None

    def test_create_git_spec_with_ref(self) -> None:
        """Test creating a git spec with ref."""
        spec = SourceSpec(
            type=SourceType.GIT_HTTPS,
            location="https://github.com/user/repo",
            ref="v1.0.0",
        )

        assert spec.ref == "v1.0.0"

    def test_empty_git_url_raises(self) -> None:
        """Test that empty git URL raises error."""
        with pytest.raises(SourceError):
            SourceSpec(type=SourceType.GIT_HTTPS, location="")


class TestResolvedSource:
    """Tests for ResolvedSource."""

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, sample_project: Path) -> None:
        """Test that context manager cleans up temporary sources."""
        resolver = SourceResolver()

        # For local paths, no cleanup should happen
        spec = SourceSpec(type=SourceType.LOCAL_PATH, location=str(sample_project))

        resolved = await resolver.resolve(spec)
        with resolved:
            assert resolved.local_path.exists()

        # Local path should still exist (not temporary)
        assert sample_project.exists()
