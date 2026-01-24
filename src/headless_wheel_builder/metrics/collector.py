"""Metrics collector and analyzer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from headless_wheel_builder.metrics.models import (
    BuildMetrics,
    MetricsReport,
    MetricsSummary,
    TimeRange,
)
from headless_wheel_builder.metrics.storage import MetricsStorage

if TYPE_CHECKING:
    from headless_wheel_builder.core.builder import BuildResult


@dataclass
class MetricsCollector:
    """Collector for build metrics and analytics.

    Collects, stores, and analyzes build metrics.

    Attributes:
        storage: Storage backend for metrics
    """

    storage: MetricsStorage | None = None

    def __post_init__(self) -> None:
        """Initialize storage if not provided."""
        if self.storage is None:
            self.storage = MetricsStorage()

    def record_build(
        self,
        result: BuildResult,
        package: str | None = None,
        python_version: str = "3.12",
        platform: str = "native",
        isolation: str = "auto",
        metadata: dict[str, Any] | None = None,
    ) -> BuildMetrics:
        """Record a build result.

        Args:
            result: Build result to record
            package: Package name (uses result.name if not provided)
            python_version: Python version used
            platform: Build platform
            isolation: Isolation method
            metadata: Additional metadata

        Returns:
            Recorded metrics
        """
        metrics = BuildMetrics(
            package=package or result.name or "unknown",
            version=result.version or "unknown",
            success=result.success,
            duration_seconds=result.duration_seconds,
            wheel_size_bytes=result.size_bytes,
            python_version=python_version,
            platform=platform,
            isolation=isolation,
            error=result.error if not result.success else None,
            metadata=metadata or {},
        )

        if self.storage:
            self.storage.add(metrics)

        return metrics

    def record_metrics(self, metrics: BuildMetrics) -> None:
        """Record pre-built metrics.

        Args:
            metrics: Metrics to record
        """
        if self.storage:
            self.storage.add(metrics)

    def get_summary(self, time_range: TimeRange = TimeRange.ALL) -> MetricsSummary:
        """Get summary statistics.

        Args:
            time_range: Time range to summarize

        Returns:
            Summary statistics
        """
        if not self.storage:
            return MetricsSummary(time_range=time_range)

        metrics = self.storage.get_by_time_range(time_range)

        if not metrics:
            return MetricsSummary(time_range=time_range)

        successful = [m for m in metrics if m.success]
        failed = [m for m in metrics if not m.success]
        durations = [m.duration_seconds for m in metrics]
        packages = {m.package for m in metrics}

        total_bytes = sum(m.wheel_size_bytes or 0 for m in successful)

        return MetricsSummary(
            total_builds=len(metrics),
            successful_builds=len(successful),
            failed_builds=len(failed),
            success_rate=len(successful) / len(metrics) if metrics else 0.0,
            avg_duration_seconds=sum(durations) / len(durations) if durations else 0.0,
            min_duration_seconds=min(durations) if durations else 0.0,
            max_duration_seconds=max(durations) if durations else 0.0,
            total_bytes_built=total_bytes,
            packages_built=len(packages),
            time_range=time_range,
        )

    def get_summary_by_package(
        self, time_range: TimeRange = TimeRange.ALL
    ) -> dict[str, MetricsSummary]:
        """Get summary statistics grouped by package.

        Args:
            time_range: Time range to summarize

        Returns:
            Dictionary of package name to summary
        """
        if not self.storage:
            return {}

        metrics = self.storage.get_by_time_range(time_range)

        # Group by package
        by_package: dict[str, list[BuildMetrics]] = {}
        for m in metrics:
            if m.package not in by_package:
                by_package[m.package] = []
            by_package[m.package].append(m)

        # Calculate summaries
        result: dict[str, MetricsSummary] = {}
        for package, pkg_metrics in by_package.items():
            successful = [m for m in pkg_metrics if m.success]
            failed = [m for m in pkg_metrics if not m.success]
            durations = [m.duration_seconds for m in pkg_metrics]
            total_bytes = sum(m.wheel_size_bytes or 0 for m in successful)

            result[package] = MetricsSummary(
                total_builds=len(pkg_metrics),
                successful_builds=len(successful),
                failed_builds=len(failed),
                success_rate=len(successful) / len(pkg_metrics),
                avg_duration_seconds=sum(durations) / len(durations),
                min_duration_seconds=min(durations),
                max_duration_seconds=max(durations),
                total_bytes_built=total_bytes,
                packages_built=1,
                time_range=time_range,
            )

        return result

    def get_report(self, time_range: TimeRange = TimeRange.ALL) -> MetricsReport:
        """Generate a full metrics report.

        Args:
            time_range: Time range for report

        Returns:
            Full metrics report
        """
        summary = self.get_summary(time_range)
        by_package = self.get_summary_by_package(time_range)

        # Get by Python version
        by_python: dict[str, MetricsSummary] = {}
        if self.storage:
            metrics = self.storage.get_by_time_range(time_range)
            grouped: dict[str, list[BuildMetrics]] = {}
            for m in metrics:
                if m.python_version not in grouped:
                    grouped[m.python_version] = []
                grouped[m.python_version].append(m)

            for version, ver_metrics in grouped.items():
                successful = [m for m in ver_metrics if m.success]
                durations = [m.duration_seconds for m in ver_metrics]
                by_python[version] = MetricsSummary(
                    total_builds=len(ver_metrics),
                    successful_builds=len(successful),
                    failed_builds=len(ver_metrics) - len(successful),
                    success_rate=len(successful) / len(ver_metrics),
                    avg_duration_seconds=sum(durations) / len(durations),
                    min_duration_seconds=min(durations),
                    max_duration_seconds=max(durations),
                    time_range=time_range,
                )

        # Get recent failures
        failures: list[BuildMetrics] = []
        if self.storage:
            failures = self.storage.get_failures(10)

        return MetricsReport(
            summary=summary,
            by_package=by_package,
            by_python_version=by_python,
            recent_failures=failures,
        )

    def get_trends(self, package: str | None = None, days: int = 30) -> list[dict[str, Any]]:
        """Get daily trend data.

        Args:
            package: Filter by package (None = all)
            days: Number of days to include

        Returns:
            List of daily data points
        """
        if not self.storage:
            return []

        metrics = self.storage.get_by_time_range(TimeRange.MONTH)

        if package:
            metrics = [m for m in metrics if m.package == package]

        # Group by day
        by_day: dict[str, list[BuildMetrics]] = {}
        for m in metrics:
            if m.timestamp:
                try:
                    ts = datetime.fromisoformat(m.timestamp.replace("Z", "+00:00"))
                    day = ts.strftime("%Y-%m-%d")
                    if day not in by_day:
                        by_day[day] = []
                    by_day[day].append(m)
                except ValueError:
                    pass

        # Calculate daily stats
        trends: list[dict[str, Any]] = []
        for day in sorted(by_day.keys())[-days:]:
            day_metrics = by_day[day]
            successful = sum(1 for m in day_metrics if m.success)
            durations = [m.duration_seconds for m in day_metrics]

            trends.append(
                {
                    "date": day,
                    "total": len(day_metrics),
                    "successful": successful,
                    "failed": len(day_metrics) - successful,
                    "success_rate": successful / len(day_metrics) if day_metrics else 0,
                    "avg_duration": sum(durations) / len(durations) if durations else 0,
                }
            )

        return trends
