"""Artifact cache storage backend."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from headless_wheel_builder.cache.models import CacheEntry, CacheStats


@dataclass
class ArtifactCache:
    """Local artifact cache with LRU eviction.

    Stores wheels in a content-addressable manner using SHA256 hashes.

    Attributes:
        cache_dir: Directory for cached wheels
        max_size_bytes: Maximum cache size (0 = unlimited)
        max_entries: Maximum number of entries (0 = unlimited)
    """

    cache_dir: Path = field(default_factory=lambda: Path.home() / ".hwb" / "cache")
    max_size_bytes: int = 0  # 0 = unlimited
    max_entries: int = 0  # 0 = unlimited
    _index: dict[str, CacheEntry] = field(default_factory=lambda: {})
    _stats: dict[str, int] = field(default_factory=lambda: {"hits": 0, "misses": 0})

    def __post_init__(self) -> None:
        """Initialize cache directory and load index."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._wheels_dir.mkdir(exist_ok=True)
        self._load_index()

    @property
    def _wheels_dir(self) -> Path:
        """Directory for wheel files."""
        return self.cache_dir / "wheels"

    @property
    def _index_path(self) -> Path:
        """Path to cache index file."""
        return self.cache_dir / "index.json"

    @property
    def _stats_path(self) -> Path:
        """Path to stats file."""
        return self.cache_dir / "stats.json"

    def _load_index(self) -> None:
        """Load cache index from disk."""
        if self._index_path.exists():
            try:
                content = self._index_path.read_text(encoding="utf-8")
                data = json.loads(content)
                self._index = {
                    k: CacheEntry.from_dict(v) for k, v in data.get("entries", {}).items()
                }
            except (json.JSONDecodeError, OSError):
                self._index = {}

        if self._stats_path.exists():
            try:
                content = self._stats_path.read_text(encoding="utf-8")
                data = json.loads(content)
                self._stats = {
                    "hits": data.get("hits", 0),
                    "misses": data.get("misses", 0),
                }
            except (json.JSONDecodeError, OSError):
                pass

    def _save_index(self) -> None:
        """Save cache index to disk."""
        data = {
            "version": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "entries": {k: v.to_dict() for k, v in self._index.items()},
        }
        content = json.dumps(data, indent=2)
        self._index_path.write_text(content, encoding="utf-8")

        # Save stats
        stats_data = {
            "hits": self._stats.get("hits", 0),
            "misses": self._stats.get("misses", 0),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        stats_content = json.dumps(stats_data, indent=2)
        self._stats_path.write_text(stats_content, encoding="utf-8")

    def _hash_file(self, path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _get_wheel_path(self, sha256: str) -> Path:
        """Get path for a wheel file by its hash."""
        # Use first 2 chars as subdirectory for better filesystem performance
        subdir = self._wheels_dir / sha256[:2]
        subdir.mkdir(exist_ok=True)
        return subdir / sha256

    def add(
        self,
        wheel_path: Path,
        package: str,
        version: str,
        python_version: str = "",
        platform: str = "",
        source: str = "build",
        metadata: dict[str, Any] | None = None,
    ) -> CacheEntry:
        """Add a wheel to the cache.

        Args:
            wheel_path: Path to wheel file
            package: Package name
            version: Package version
            python_version: Python version tag
            platform: Platform tag
            source: Source of wheel (build, download, registry)
            metadata: Additional metadata

        Returns:
            Cache entry for the added wheel
        """
        # Calculate hash
        sha256 = self._hash_file(wheel_path)
        size_bytes = wheel_path.stat().st_size

        # Check if already cached
        cache_key = f"{package}-{version}-{sha256[:12]}"
        if cache_key in self._index:
            entry = self._index[cache_key]
            entry.last_accessed = datetime.now(timezone.utc).isoformat()
            entry.access_count += 1
            self._save_index()
            return entry

        # Copy to cache
        cache_path = self._get_wheel_path(sha256)
        if not cache_path.exists():
            shutil.copy2(wheel_path, cache_path)

        # Create entry
        entry = CacheEntry(
            package=package,
            version=version,
            wheel_name=wheel_path.name,
            sha256=sha256,
            size_bytes=size_bytes,
            python_version=python_version,
            platform=platform,
            source=source,
            metadata=metadata or {},
        )

        self._index[cache_key] = entry

        # Evict if needed
        self._evict_if_needed()

        self._save_index()
        return entry

    def get(
        self,
        package: str,
        version: str,
        python_version: str | None = None,
        platform: str | None = None,
    ) -> tuple[CacheEntry, Path] | None:
        """Get a wheel from the cache.

        Args:
            package: Package name
            version: Package version
            python_version: Optional Python version filter
            platform: Optional platform filter

        Returns:
            Tuple of (cache entry, wheel path) or None if not found
        """
        # Find matching entries
        candidates: list[CacheEntry] = []
        for entry in self._index.values():
            if entry.package == package and entry.version == version:
                if python_version and entry.python_version != python_version:
                    continue
                if platform and entry.platform != platform:
                    continue
                candidates.append(entry)

        if not candidates:
            self._stats["misses"] = self._stats.get("misses", 0) + 1
            self._save_index()
            return None

        # Return most recently accessed
        entry = max(candidates, key=lambda e: e.last_accessed or "")
        wheel_path = self._get_wheel_path(entry.sha256)

        if not wheel_path.exists():
            # Wheel file is missing, remove from index
            cache_key = entry.cache_key
            del self._index[cache_key]
            self._stats["misses"] = self._stats.get("misses", 0) + 1
            self._save_index()
            return None

        # Update access tracking
        entry.last_accessed = datetime.now(timezone.utc).isoformat()
        entry.access_count += 1
        self._stats["hits"] = self._stats.get("hits", 0) + 1
        self._save_index()

        return (entry, wheel_path)

    def get_by_hash(self, sha256: str) -> tuple[CacheEntry, Path] | None:
        """Get a wheel by its SHA256 hash.

        Args:
            sha256: SHA256 hash of wheel

        Returns:
            Tuple of (cache entry, wheel path) or None if not found
        """
        for entry in self._index.values():
            if entry.sha256 == sha256:
                wheel_path = self._get_wheel_path(entry.sha256)
                if wheel_path.exists():
                    entry.last_accessed = datetime.now(timezone.utc).isoformat()
                    entry.access_count += 1
                    self._stats["hits"] = self._stats.get("hits", 0) + 1
                    self._save_index()
                    return (entry, wheel_path)

        self._stats["misses"] = self._stats.get("misses", 0) + 1
        self._save_index()
        return None

    def contains(self, package: str, version: str) -> bool:
        """Check if a package version is in the cache.

        Args:
            package: Package name
            version: Package version

        Returns:
            True if cached
        """
        for entry in self._index.values():
            if entry.package == package and entry.version == version:
                wheel_path = self._get_wheel_path(entry.sha256)
                if wheel_path.exists():
                    return True
        return False

    def list_packages(self) -> list[str]:
        """List all cached packages.

        Returns:
            List of package names
        """
        return list({e.package for e in self._index.values()})

    def list_versions(self, package: str) -> list[str]:
        """List cached versions of a package.

        Args:
            package: Package name

        Returns:
            List of versions
        """
        return list({e.version for e in self._index.values() if e.package == package})

    def list_entries(self, package: str | None = None) -> list[CacheEntry]:
        """List cache entries.

        Args:
            package: Optional package filter

        Returns:
            List of cache entries
        """
        entries = list(self._index.values())
        if package:
            entries = [e for e in entries if e.package == package]
        return sorted(entries, key=lambda e: e.last_accessed or "", reverse=True)

    def remove(self, package: str, version: str) -> int:
        """Remove entries for a package version.

        Args:
            package: Package name
            version: Package version

        Returns:
            Number of entries removed
        """
        to_remove: list[str] = []
        for key, entry in self._index.items():
            if entry.package == package and entry.version == version:
                to_remove.append(key)
                # Remove wheel file
                wheel_path = self._get_wheel_path(entry.sha256)
                if wheel_path.exists():
                    wheel_path.unlink()

        for key in to_remove:
            del self._index[key]

        if to_remove:
            self._save_index()

        return len(to_remove)

    def clear(self) -> None:
        """Clear entire cache."""
        # Remove all wheels
        if self._wheels_dir.exists():
            shutil.rmtree(self._wheels_dir)
            self._wheels_dir.mkdir()

        self._index = {}
        self._stats = {"hits": 0, "misses": 0}
        self._save_index()

    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        total_size = sum(e.size_bytes for e in self._index.values())
        packages = {e.package for e in self._index.values()}

        timestamps = [e.created_at for e in self._index.values() if e.created_at]
        oldest = min(timestamps) if timestamps else None
        newest = max(timestamps) if timestamps else None

        hits = self._stats.get("hits", 0)
        misses = self._stats.get("misses", 0)
        total = hits + misses
        hit_rate = hits / total if total > 0 else 0.0

        return CacheStats(
            total_entries=len(self._index),
            total_size_bytes=total_size,
            hits=hits,
            misses=misses,
            hit_rate=hit_rate,
            oldest_entry=oldest,
            newest_entry=newest,
            packages=len(packages),
        )

    def _evict_if_needed(self) -> None:
        """Evict entries if cache limits are exceeded."""
        # Check entry count
        if self.max_entries > 0 and len(self._index) > self.max_entries:
            self._evict_lru(len(self._index) - self.max_entries)

        # Check size
        if self.max_size_bytes > 0:
            total_size = sum(e.size_bytes for e in self._index.values())
            if total_size > self.max_size_bytes:
                self._evict_to_size(self.max_size_bytes)

    def _evict_lru(self, count: int) -> None:
        """Evict least recently used entries.

        Args:
            count: Number of entries to evict
        """
        # Sort by last accessed (oldest first)
        sorted_entries = sorted(
            self._index.items(),
            key=lambda x: x[1].last_accessed or "",
        )

        for key, entry in sorted_entries[:count]:
            wheel_path = self._get_wheel_path(entry.sha256)
            if wheel_path.exists():
                wheel_path.unlink()
            del self._index[key]

    def _evict_to_size(self, target_size: int) -> None:
        """Evict entries until cache is under target size.

        Args:
            target_size: Target size in bytes
        """
        # Sort by last accessed (oldest first)
        sorted_entries = sorted(
            self._index.items(),
            key=lambda x: x[1].last_accessed or "",
        )

        current_size = sum(e.size_bytes for e in self._index.values())

        for key, entry in sorted_entries:
            if current_size <= target_size:
                break

            wheel_path = self._get_wheel_path(entry.sha256)
            if wheel_path.exists():
                wheel_path.unlink()

            current_size -= entry.size_bytes
            del self._index[key]

    def copy_to(self, entry: CacheEntry, destination: Path) -> Path:
        """Copy a cached wheel to a destination.

        Args:
            entry: Cache entry
            destination: Destination directory

        Returns:
            Path to copied wheel
        """
        wheel_path = self._get_wheel_path(entry.sha256)
        dest_path = destination / entry.wheel_name
        shutil.copy2(wheel_path, dest_path)
        return dest_path

    def prune_to_size(self, target_size: int) -> int:
        """Prune cache to target size.

        Evicts least recently used entries until cache is under target size.

        Args:
            target_size: Target size in bytes

        Returns:
            Number of entries evicted
        """
        entries_before = len(self._index)
        self._evict_to_size(target_size)
        self._save_index()
        return entries_before - len(self._index)
