"""Models for metrics and analytics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TimeRange(Enum):
    """Time ranges for metrics aggregation."""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    ALL = "all"

    def to_seconds(self) -> int:
        """Convert to seconds."""
        mapping = {
            TimeRange.HOUR: 3600,
            TimeRange.DAY: 86400,
            TimeRange.WEEK: 604800,
            TimeRange.MONTH: 2592000,
            TimeRange.ALL: 0,
        }
        return mapping[self]


@dataclass
class BuildMetrics:
    """Metrics for a single build.

    Attributes:
        package: Package name
        version: Package version
        success: Whether build succeeded
        duration_seconds: Build duration
        wheel_size_bytes: Size of built wheel
        timestamp: Build timestamp (ISO format)
        python_version: Python version used
        platform: Build platform
        isolation: Isolation method used
        error: Error message if failed
        metadata: Additional metadata
    """

    package: str
    version: str
    success: bool
    duration_seconds: float
    wheel_size_bytes: int | None = None
    timestamp: str | None = None
    python_version: str = "3.12"
    platform: str = "native"
    isolation: str = "auto"
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=lambda: {})

    def __post_init__(self) -> None:
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "package": self.package,
            "version": self.version,
            "success": self.success,
            "duration_seconds": self.duration_seconds,
            "wheel_size_bytes": self.wheel_size_bytes,
            "timestamp": self.timestamp,
            "python_version": self.python_version,
            "platform": self.platform,
            "isolation": self.isolation,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BuildMetrics:
        """Create from dictionary."""
        return cls(
            package=data["package"],
            version=data["version"],
            success=data["success"],
            duration_seconds=data["duration_seconds"],
            wheel_size_bytes=data.get("wheel_size_bytes"),
            timestamp=data.get("timestamp"),
            python_version=data.get("python_version", "3.12"),
            platform=data.get("platform", "native"),
            isolation=data.get("isolation", "auto"),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MetricsSummary:
    """Summary statistics for a set of builds.

    Attributes:
        total_builds: Total number of builds
        successful_builds: Number of successful builds
        failed_builds: Number of failed builds
        success_rate: Success rate (0-1)
        avg_duration_seconds: Average build duration
        min_duration_seconds: Minimum build duration
        max_duration_seconds: Maximum build duration
        total_bytes_built: Total bytes of wheels built
        packages_built: Unique packages built
        time_range: Time range for summary
    """

    total_builds: int = 0
    successful_builds: int = 0
    failed_builds: int = 0
    success_rate: float = 0.0
    avg_duration_seconds: float = 0.0
    min_duration_seconds: float = 0.0
    max_duration_seconds: float = 0.0
    total_bytes_built: int = 0
    packages_built: int = 0
    time_range: TimeRange = TimeRange.ALL

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_builds": self.total_builds,
            "successful_builds": self.successful_builds,
            "failed_builds": self.failed_builds,
            "success_rate": self.success_rate,
            "avg_duration_seconds": self.avg_duration_seconds,
            "min_duration_seconds": self.min_duration_seconds,
            "max_duration_seconds": self.max_duration_seconds,
            "total_bytes_built": self.total_bytes_built,
            "packages_built": self.packages_built,
            "time_range": self.time_range.value,
        }


@dataclass
class MetricsReport:
    """Full metrics report.

    Attributes:
        summary: Summary statistics
        by_package: Metrics grouped by package
        by_python_version: Metrics grouped by Python version
        by_platform: Metrics grouped by platform
        recent_failures: Recent failed builds
        trends: Trend data over time
        generated_at: Report generation timestamp
    """

    summary: MetricsSummary
    by_package: dict[str, MetricsSummary] = field(default_factory=lambda: {})
    by_python_version: dict[str, MetricsSummary] = field(default_factory=lambda: {})
    by_platform: dict[str, MetricsSummary] = field(default_factory=lambda: {})
    recent_failures: list[BuildMetrics] = field(default_factory=lambda: [])
    trends: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: {})
    generated_at: str | None = None

    def __post_init__(self) -> None:
        """Set generation timestamp if not provided."""
        if self.generated_at is None:
            self.generated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "summary": self.summary.to_dict(),
            "by_package": {k: v.to_dict() for k, v in self.by_package.items()},
            "by_python_version": {k: v.to_dict() for k, v in self.by_python_version.items()},
            "by_platform": {k: v.to_dict() for k, v in self.by_platform.items()},
            "recent_failures": [f.to_dict() for f in self.recent_failures],
            "trends": self.trends,
            "generated_at": self.generated_at,
        }
