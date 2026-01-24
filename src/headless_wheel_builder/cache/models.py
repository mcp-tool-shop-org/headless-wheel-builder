"""Models for artifact caching."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class CacheEntry:
    """Cached artifact entry.

    Attributes:
        package: Package name
        version: Package version
        wheel_name: Wheel filename
        sha256: SHA256 hash of wheel
        size_bytes: Size in bytes
        python_version: Python version tag
        platform: Platform tag
        created_at: When cached (ISO format)
        last_accessed: Last access time (ISO format)
        access_count: Number of times accessed
        source: Where the wheel came from (build, download, registry)
        metadata: Additional metadata
    """

    package: str
    version: str
    wheel_name: str
    sha256: str
    size_bytes: int
    python_version: str = ""
    platform: str = ""
    created_at: str | None = None
    last_accessed: str | None = None
    access_count: int = 0
    source: str = "build"
    metadata: dict[str, Any] = field(default_factory=lambda: {})

    def __post_init__(self) -> None:
        """Set timestamps if not provided."""
        now = datetime.now(timezone.utc).isoformat()
        if self.created_at is None:
            self.created_at = now
        if self.last_accessed is None:
            self.last_accessed = now

    @property
    def cache_key(self) -> str:
        """Get unique cache key for this entry."""
        return f"{self.package}-{self.version}-{self.sha256[:12]}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "package": self.package,
            "version": self.version,
            "wheel_name": self.wheel_name,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "python_version": self.python_version,
            "platform": self.platform,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CacheEntry:
        """Create from dictionary."""
        return cls(
            package=data["package"],
            version=data["version"],
            wheel_name=data["wheel_name"],
            sha256=data["sha256"],
            size_bytes=data["size_bytes"],
            python_version=data.get("python_version", ""),
            platform=data.get("platform", ""),
            created_at=data.get("created_at"),
            last_accessed=data.get("last_accessed"),
            access_count=data.get("access_count", 0),
            source=data.get("source", "build"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CacheStats:
    """Cache statistics.

    Attributes:
        total_entries: Number of cached entries
        total_size_bytes: Total size of cached wheels
        hits: Cache hit count
        misses: Cache miss count
        hit_rate: Cache hit rate (0-1)
        oldest_entry: Oldest entry timestamp
        newest_entry: Newest entry timestamp
        packages: Unique packages in cache
    """

    total_entries: int = 0
    total_size_bytes: int = 0
    hits: int = 0
    misses: int = 0
    hit_rate: float = 0.0
    oldest_entry: str | None = None
    newest_entry: str | None = None
    packages: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_entries": self.total_entries,
            "total_size_bytes": self.total_size_bytes,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
            "oldest_entry": self.oldest_entry,
            "newest_entry": self.newest_entry,
            "packages": self.packages,
        }


@dataclass
class RegistryConfig:
    """Configuration for wheel registry.

    Attributes:
        url: Registry base URL
        username: Authentication username
        password: Authentication password/token
        verify_ssl: Whether to verify SSL certificates
        timeout: Request timeout in seconds
    """

    url: str
    username: str | None = None
    password: str | None = None
    verify_ssl: bool = True
    timeout: int = 30

    @classmethod
    def from_env(cls) -> RegistryConfig | None:
        """Create from environment variables.

        Uses:
            HWB_REGISTRY_URL
            HWB_REGISTRY_USERNAME
            HWB_REGISTRY_PASSWORD
        """
        import os

        url = os.environ.get("HWB_REGISTRY_URL")
        if not url:
            return None

        return cls(
            url=url,
            username=os.environ.get("HWB_REGISTRY_USERNAME"),
            password=os.environ.get("HWB_REGISTRY_PASSWORD"),
        )
