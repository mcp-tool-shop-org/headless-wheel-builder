"""Tests for metrics and analytics module."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from headless_wheel_builder.metrics.cli import metrics
from headless_wheel_builder.metrics.collector import MetricsCollector
from headless_wheel_builder.metrics.models import (
    BuildMetrics,
    MetricsReport,
    MetricsSummary,
    TimeRange,
)
from headless_wheel_builder.metrics.storage import MetricsStorage

if TYPE_CHECKING:
    from pathlib import Path


class TestTimeRange:
    """Tests for TimeRange enum."""

    def test_to_seconds_hour(self) -> None:
        """Test hour to seconds."""
        assert TimeRange.HOUR.to_seconds() == 3600

    def test_to_seconds_day(self) -> None:
        """Test day to seconds."""
        assert TimeRange.DAY.to_seconds() == 86400

    def test_to_seconds_week(self) -> None:
        """Test week to seconds."""
        assert TimeRange.WEEK.to_seconds() == 604800

    def test_to_seconds_month(self) -> None:
        """Test month to seconds."""
        assert TimeRange.MONTH.to_seconds() == 2592000

    def test_to_seconds_all(self) -> None:
        """Test all returns 0."""
        assert TimeRange.ALL.to_seconds() == 0


class TestBuildMetrics:
    """Tests for BuildMetrics model."""

    def test_create_minimal(self) -> None:
        """Test creating with minimal fields."""
        m = BuildMetrics(
            package="test-package",
            version="1.0.0",
            success=True,
            duration_seconds=12.5,
        )
        assert m.package == "test-package"
        assert m.version == "1.0.0"
        assert m.success is True
        assert m.duration_seconds == 12.5
        assert m.timestamp is not None

    def test_create_full(self) -> None:
        """Test creating with all fields."""
        m = BuildMetrics(
            package="mypackage",
            version="2.0.0",
            success=False,
            duration_seconds=45.0,
            wheel_size_bytes=1024000,
            timestamp="2024-01-15T10:30:00+00:00",
            python_version="3.11",
            platform="manylinux",
            isolation="docker",
            error="Build failed",
            metadata={"key": "value"},
        )
        assert m.wheel_size_bytes == 1024000
        assert m.python_version == "3.11"
        assert m.platform == "manylinux"
        assert m.error == "Build failed"

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        m = BuildMetrics(
            package="test",
            version="1.0.0",
            success=True,
            duration_seconds=10.0,
            wheel_size_bytes=5000,
        )
        d = m.to_dict()
        assert d["package"] == "test"
        assert d["version"] == "1.0.0"
        assert d["success"] is True
        assert d["wheel_size_bytes"] == 5000

    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "package": "restored",
            "version": "3.0.0",
            "success": False,
            "duration_seconds": 20.0,
            "wheel_size_bytes": 2048,
            "python_version": "3.10",
            "error": "Failed",
        }
        m = BuildMetrics.from_dict(data)
        assert m.package == "restored"
        assert m.version == "3.0.0"
        assert m.success is False
        assert m.wheel_size_bytes == 2048

    def test_auto_timestamp(self) -> None:
        """Test automatic timestamp generation."""
        m = BuildMetrics(
            package="test",
            version="1.0.0",
            success=True,
            duration_seconds=5.0,
        )
        assert m.timestamp is not None
        # Should be valid ISO format
        datetime.fromisoformat(m.timestamp.replace("Z", "+00:00"))


class TestMetricsSummary:
    """Tests for MetricsSummary model."""

    def test_default_values(self) -> None:
        """Test default values."""
        s = MetricsSummary()
        assert s.total_builds == 0
        assert s.successful_builds == 0
        assert s.success_rate == 0.0
        assert s.time_range == TimeRange.ALL

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        s = MetricsSummary(
            total_builds=100,
            successful_builds=90,
            failed_builds=10,
            success_rate=0.9,
            avg_duration_seconds=15.5,
            packages_built=5,
        )
        d = s.to_dict()
        assert d["total_builds"] == 100
        assert d["success_rate"] == 0.9
        assert d["time_range"] == "all"


class TestMetricsReport:
    """Tests for MetricsReport model."""

    def test_create(self) -> None:
        """Test creating report."""
        summary = MetricsSummary(total_builds=10)
        report = MetricsReport(summary=summary)
        assert report.summary.total_builds == 10
        assert report.generated_at is not None

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        summary = MetricsSummary(total_builds=5)
        report = MetricsReport(
            summary=summary,
            by_package={"pkg": MetricsSummary(total_builds=3)},
        )
        d = report.to_dict()
        assert d["summary"]["total_builds"] == 5
        assert "pkg" in d["by_package"]


class TestMetricsStorage:
    """Tests for MetricsStorage."""

    def test_add_and_get(self, tmp_path: Path) -> None:
        """Test adding and retrieving metrics."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        m = BuildMetrics(
            package="test",
            version="1.0.0",
            success=True,
            duration_seconds=10.0,
        )
        storage.add(m)

        all_metrics = storage.get_all()
        assert len(all_metrics) == 1
        assert all_metrics[0].package == "test"

    def test_add_many(self, tmp_path: Path) -> None:
        """Test adding multiple metrics."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        metrics_list = [
            BuildMetrics(package=f"pkg{i}", version="1.0.0", success=True, duration_seconds=i)
            for i in range(5)
        ]
        storage.add_many(metrics_list)

        all_metrics = storage.get_all()
        assert len(all_metrics) == 5

    def test_get_by_package(self, tmp_path: Path) -> None:
        """Test filtering by package."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        storage.add(
            BuildMetrics(package="alpha", version="1.0.0", success=True, duration_seconds=1)
        )
        storage.add(BuildMetrics(package="beta", version="1.0.0", success=True, duration_seconds=2))
        storage.add(
            BuildMetrics(package="alpha", version="2.0.0", success=True, duration_seconds=3)
        )

        alpha_metrics = storage.get_by_package("alpha")
        assert len(alpha_metrics) == 2
        assert all(m.package == "alpha" for m in alpha_metrics)

    def test_get_by_time_range_all(self, tmp_path: Path) -> None:
        """Test getting all metrics with ALL range."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        storage.add(BuildMetrics(package="test", version="1.0.0", success=True, duration_seconds=1))

        metrics_all = storage.get_by_time_range(TimeRange.ALL)
        assert len(metrics_all) == 1

    def test_get_by_time_range_hour(self, tmp_path: Path) -> None:
        """Test filtering by hour range."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        now = datetime.now(timezone.utc)

        # Recent metric
        recent = BuildMetrics(
            package="recent",
            version="1.0.0",
            success=True,
            duration_seconds=1,
            timestamp=now.isoformat(),
        )
        storage.add(recent)

        # Old metric (2 hours ago)
        old_time = now - timedelta(hours=2)
        old = BuildMetrics(
            package="old",
            version="1.0.0",
            success=True,
            duration_seconds=1,
            timestamp=old_time.isoformat(),
        )
        storage.add(old)

        hour_metrics = storage.get_by_time_range(TimeRange.HOUR)
        assert len(hour_metrics) == 1
        assert hour_metrics[0].package == "recent"

    def test_get_recent(self, tmp_path: Path) -> None:
        """Test getting recent entries."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        for i in range(10):
            storage.add(
                BuildMetrics(package=f"pkg{i}", version="1.0.0", success=True, duration_seconds=i)
            )

        recent = storage.get_recent(3)
        assert len(recent) == 3
        # Should be the last 3
        assert recent[-1].package == "pkg9"

    def test_get_failures(self, tmp_path: Path) -> None:
        """Test getting failures only."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        storage.add(
            BuildMetrics(package="success", version="1.0.0", success=True, duration_seconds=1)
        )
        storage.add(
            BuildMetrics(package="fail1", version="1.0.0", success=False, duration_seconds=2)
        )
        storage.add(
            BuildMetrics(package="fail2", version="1.0.0", success=False, duration_seconds=3)
        )

        failures = storage.get_failures()
        assert len(failures) == 2
        assert all(not f.success for f in failures)

    def test_clear(self, tmp_path: Path) -> None:
        """Test clearing metrics."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        storage.add(BuildMetrics(package="test", version="1.0.0", success=True, duration_seconds=1))
        storage.clear()

        assert len(storage.get_all()) == 0

    def test_rotation(self, tmp_path: Path) -> None:
        """Test max entries rotation."""
        storage = MetricsStorage(path=tmp_path / "metrics.json", max_entries=5)
        for i in range(10):
            storage.add(
                BuildMetrics(package=f"pkg{i}", version="1.0.0", success=True, duration_seconds=i)
            )

        all_metrics = storage.get_all()
        assert len(all_metrics) == 5
        # Should keep the last 5
        assert all_metrics[0].package == "pkg5"

    def test_export_json(self, tmp_path: Path) -> None:
        """Test JSON export."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        storage.add(BuildMetrics(package="test", version="1.0.0", success=True, duration_seconds=1))

        export_path = tmp_path / "export.json"
        storage.export(export_path, format="json")

        assert export_path.exists()
        data = json.loads(export_path.read_text())
        assert len(data) == 1
        assert data[0]["package"] == "test"

    def test_export_csv(self, tmp_path: Path) -> None:
        """Test CSV export."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        storage.add(BuildMetrics(package="test", version="1.0.0", success=True, duration_seconds=1))

        export_path = tmp_path / "export.csv"
        storage.export(export_path, format="csv")

        assert export_path.exists()
        lines = export_path.read_text().strip().split("\n")
        assert len(lines) == 2  # header + data
        assert "package" in lines[0]

    def test_empty_file_load(self, tmp_path: Path) -> None:
        """Test loading from non-existent file."""
        storage = MetricsStorage(path=tmp_path / "nonexistent.json")
        assert storage.get_all() == []

    def test_corrupt_file_load(self, tmp_path: Path) -> None:
        """Test loading from corrupt file."""
        path = tmp_path / "corrupt.json"
        path.write_text("not valid json", encoding="utf-8")
        storage = MetricsStorage(path=path)
        assert storage.get_all() == []


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_record_build_success(self, tmp_path: Path) -> None:
        """Test recording successful build."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        collector = MetricsCollector(storage=storage)

        result = MagicMock()
        result.name = "mypackage"
        result.version = "1.0.0"
        result.success = True
        result.duration_seconds = 25.0
        result.size_bytes = 50000

        metrics = collector.record_build(result)
        assert metrics.package == "mypackage"
        assert metrics.success is True

        # Should be stored
        all_metrics = storage.get_all()
        assert len(all_metrics) == 1

    def test_record_build_failure(self, tmp_path: Path) -> None:
        """Test recording failed build."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        collector = MetricsCollector(storage=storage)

        result = MagicMock()
        result.name = "badpackage"
        result.version = "0.1.0"
        result.success = False
        result.duration_seconds = 5.0
        result.size_bytes = None
        result.error = "Compilation failed"

        metrics = collector.record_build(result)
        assert metrics.success is False
        assert metrics.error == "Compilation failed"

    def test_record_metrics(self, tmp_path: Path) -> None:
        """Test recording pre-built metrics."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        collector = MetricsCollector(storage=storage)

        m = BuildMetrics(package="test", version="1.0.0", success=True, duration_seconds=1)
        collector.record_metrics(m)

        assert len(storage.get_all()) == 1

    def test_get_summary_empty(self, tmp_path: Path) -> None:
        """Test summary with no data."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        collector = MetricsCollector(storage=storage)

        summary = collector.get_summary()
        assert summary.total_builds == 0
        assert summary.success_rate == 0.0

    def test_get_summary_with_data(self, tmp_path: Path) -> None:
        """Test summary with data."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        collector = MetricsCollector(storage=storage)

        # Add some builds
        storage.add(
            BuildMetrics(
                package="pkg1",
                version="1.0.0",
                success=True,
                duration_seconds=10,
                wheel_size_bytes=1000,
            )
        )
        storage.add(
            BuildMetrics(
                package="pkg2",
                version="1.0.0",
                success=True,
                duration_seconds=20,
                wheel_size_bytes=2000,
            )
        )
        storage.add(
            BuildMetrics(package="pkg1", version="2.0.0", success=False, duration_seconds=5)
        )

        summary = collector.get_summary()
        assert summary.total_builds == 3
        assert summary.successful_builds == 2
        assert summary.failed_builds == 1
        assert summary.success_rate == pytest.approx(2 / 3)
        assert summary.total_bytes_built == 3000
        assert summary.packages_built == 2

    def test_get_summary_by_package(self, tmp_path: Path) -> None:
        """Test summary grouped by package."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        collector = MetricsCollector(storage=storage)

        storage.add(
            BuildMetrics(package="alpha", version="1.0.0", success=True, duration_seconds=10)
        )
        storage.add(
            BuildMetrics(package="alpha", version="2.0.0", success=True, duration_seconds=15)
        )
        storage.add(
            BuildMetrics(package="beta", version="1.0.0", success=False, duration_seconds=5)
        )

        by_package = collector.get_summary_by_package()
        assert "alpha" in by_package
        assert "beta" in by_package
        assert by_package["alpha"].total_builds == 2
        assert by_package["alpha"].success_rate == 1.0
        assert by_package["beta"].success_rate == 0.0

    def test_get_report(self, tmp_path: Path) -> None:
        """Test full report generation."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        collector = MetricsCollector(storage=storage)

        storage.add(
            BuildMetrics(
                package="pkg",
                version="1.0.0",
                success=True,
                duration_seconds=10,
                python_version="3.11",
            )
        )
        storage.add(
            BuildMetrics(
                package="pkg",
                version="2.0.0",
                success=False,
                duration_seconds=5,
                python_version="3.12",
            )
        )

        report = collector.get_report()
        assert report.summary.total_builds == 2
        assert "pkg" in report.by_package
        assert "3.11" in report.by_python_version
        assert "3.12" in report.by_python_version
        assert len(report.recent_failures) == 1

    def test_get_trends(self, tmp_path: Path) -> None:
        """Test trend generation."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        collector = MetricsCollector(storage=storage)

        now = datetime.now(timezone.utc)

        # Add metrics for today
        storage.add(
            BuildMetrics(
                package="pkg",
                version="1.0.0",
                success=True,
                duration_seconds=10,
                timestamp=now.isoformat(),
            )
        )
        storage.add(
            BuildMetrics(
                package="pkg",
                version="1.0.1",
                success=False,
                duration_seconds=5,
                timestamp=now.isoformat(),
            )
        )

        # Add metric for yesterday
        yesterday = now - timedelta(days=1)
        storage.add(
            BuildMetrics(
                package="pkg",
                version="1.0.2",
                success=True,
                duration_seconds=15,
                timestamp=yesterday.isoformat(),
            )
        )

        trends = collector.get_trends(days=7)
        assert len(trends) == 2  # Two days with data

    def test_get_trends_filtered(self, tmp_path: Path) -> None:
        """Test trend filtering by package."""
        storage = MetricsStorage(path=tmp_path / "metrics.json")
        collector = MetricsCollector(storage=storage)

        now = datetime.now(timezone.utc)
        storage.add(
            BuildMetrics(
                package="alpha",
                version="1.0.0",
                success=True,
                duration_seconds=10,
                timestamp=now.isoformat(),
            )
        )
        storage.add(
            BuildMetrics(
                package="beta",
                version="1.0.0",
                success=True,
                duration_seconds=5,
                timestamp=now.isoformat(),
            )
        )

        alpha_trends = collector.get_trends(package="alpha")
        assert len(alpha_trends) == 1
        assert alpha_trends[0]["total"] == 1

    def test_no_storage(self) -> None:
        """Test collector auto-creates storage."""
        collector = MetricsCollector()
        assert collector.storage is not None


class TestMetricsCLI:
    """Tests for metrics CLI commands."""

    def test_summary_empty(self, tmp_path: Path) -> None:
        """Test summary with no data."""
        runner = CliRunner()
        with patch.object(
            MetricsStorage,
            "__init__",
            lambda self, **kwargs: setattr(self, "path", tmp_path / "m.json")
            or setattr(self, "max_entries", 10000)
            or None,
        ), patch.object(MetricsStorage, "_load", return_value=[]):
            result = runner.invoke(metrics, ["summary"])
            assert result.exit_code == 0
            assert "0" in result.output  # total builds

    def test_summary_json(self, tmp_path: Path) -> None:
        """Test summary JSON output."""
        runner = CliRunner()
        with patch.object(MetricsCollector, "get_summary") as mock_summary:
            mock_summary.return_value = MetricsSummary(
                total_builds=10,
                successful_builds=8,
                success_rate=0.8,
            )
            result = runner.invoke(metrics, ["summary", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["total_builds"] == 10

    def test_report_json(self, tmp_path: Path) -> None:
        """Test report JSON output."""
        runner = CliRunner()
        with patch.object(MetricsCollector, "get_report") as mock_report:
            mock_report.return_value = MetricsReport(
                summary=MetricsSummary(total_builds=5),
            )
            result = runner.invoke(metrics, ["report", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert data["summary"]["total_builds"] == 5

    def test_trends_empty(self, tmp_path: Path) -> None:
        """Test trends with no data."""
        runner = CliRunner()
        with patch.object(MetricsCollector, "get_trends", return_value=[]):
            result = runner.invoke(metrics, ["trends"])
            assert result.exit_code == 0
            assert "No trend data" in result.output

    def test_trends_json(self, tmp_path: Path) -> None:
        """Test trends JSON output."""
        runner = CliRunner()
        trend_data = [
            {
                "date": "2024-01-15",
                "total": 5,
                "successful": 4,
                "failed": 1,
                "success_rate": 0.8,
                "avg_duration": 10.0,
            }
        ]
        with patch.object(MetricsCollector, "get_trends", return_value=trend_data):
            result = runner.invoke(metrics, ["trends", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert len(data) == 1
            assert data[0]["total"] == 5

    def test_list_empty(self, tmp_path: Path) -> None:
        """Test list with no metrics."""
        runner = CliRunner()
        with patch.object(MetricsStorage, "get_recent", return_value=[]):
            result = runner.invoke(metrics, ["list"])
            assert result.exit_code == 0
            assert "No metrics" in result.output

    def test_list_with_data(self, tmp_path: Path) -> None:
        """Test list with metrics."""
        runner = CliRunner()
        mock_metrics = [
            BuildMetrics(package="test", version="1.0.0", success=True, duration_seconds=10),
        ]
        with patch.object(MetricsStorage, "get_recent", return_value=mock_metrics):
            result = runner.invoke(metrics, ["list"])
            assert result.exit_code == 0
            assert "test" in result.output

    def test_list_failures(self, tmp_path: Path) -> None:
        """Test list failures only."""
        runner = CliRunner()
        mock_failures = [
            BuildMetrics(
                package="bad", version="0.1.0", success=False, duration_seconds=5, error="Failed"
            ),
        ]
        with patch.object(MetricsStorage, "get_failures", return_value=mock_failures):
            result = runner.invoke(metrics, ["list", "--failures"])
            assert result.exit_code == 0
            assert "bad" in result.output

    def test_list_json(self, tmp_path: Path) -> None:
        """Test list JSON output."""
        runner = CliRunner()
        mock_metrics = [
            BuildMetrics(package="pkg", version="1.0.0", success=True, duration_seconds=10),
        ]
        with patch.object(MetricsStorage, "get_recent", return_value=mock_metrics):
            result = runner.invoke(metrics, ["list", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert len(data) == 1

    def test_export(self, tmp_path: Path) -> None:
        """Test export command."""
        runner = CliRunner()
        export_path = tmp_path / "export.json"
        with patch.object(MetricsStorage, "export") as mock_export:
            result = runner.invoke(metrics, ["export", str(export_path)])
            assert result.exit_code == 0
            mock_export.assert_called_once()

    def test_clear_confirmed(self, tmp_path: Path) -> None:
        """Test clear with confirmation."""
        runner = CliRunner()
        with patch.object(MetricsStorage, "clear") as mock_clear:
            result = runner.invoke(metrics, ["clear", "--yes"])
            assert result.exit_code == 0
            mock_clear.assert_called_once()

    def test_clear_cancelled(self, tmp_path: Path) -> None:
        """Test clear cancelled."""
        runner = CliRunner()
        with patch.object(MetricsStorage, "clear") as mock_clear:
            runner.invoke(metrics, ["clear"], input="n\n")
            mock_clear.assert_not_called()
