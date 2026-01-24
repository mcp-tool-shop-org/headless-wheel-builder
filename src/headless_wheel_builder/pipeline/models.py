"""Data models for pipeline operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path


class StageStatus(Enum):
    """Status of a pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStage(Enum):
    """Pipeline stages in execution order."""

    VALIDATE = "validate"
    BUILD = "build"
    TEST = "test"
    CHANGELOG = "changelog"
    RELEASE = "release"
    UPLOAD = "upload"
    NOTIFY = "notify"


@dataclass
class StageResult:
    """Result of a single pipeline stage."""

    stage: PipelineStage
    status: StageStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    message: str = ""
    data: dict[str, Any] = field(default_factory=lambda: {})
    error: str | None = None

    @property
    def duration_seconds(self) -> float | None:
        """Get stage duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @classmethod
    def pending(cls, stage: PipelineStage) -> StageResult:
        """Create a pending stage result."""
        return cls(stage=stage, status=StageStatus.PENDING)

    @classmethod
    def success(
        cls,
        stage: PipelineStage,
        message: str = "",
        data: dict[str, Any] | None = None,
    ) -> StageResult:
        """Create a successful stage result."""
        return cls(
            stage=stage,
            status=StageStatus.SUCCESS,
            message=message,
            data=data or {},
        )

    @classmethod
    def failure(cls, stage: PipelineStage, error: str) -> StageResult:
        """Create a failed stage result."""
        return cls(stage=stage, status=StageStatus.FAILED, error=error)

    @classmethod
    def skipped(cls, stage: PipelineStage, reason: str = "") -> StageResult:
        """Create a skipped stage result."""
        return cls(stage=stage, status=StageStatus.SKIPPED, message=reason)


@dataclass
class PipelineConfig:
    """Configuration for a pipeline run.

    Attributes:
        source: Source to build (path, git URL, etc.)
        repo: GitHub repository in 'owner/repo' format
        tag: Release tag (e.g., 'v1.0.0')
        name: Release name (defaults to tag)
        body: Release body/description
        draft: Create as draft release
        prerelease: Mark as prerelease
        files: Additional files to upload as assets
        python: Python version to build with
        output_dir: Output directory for built wheels
        generate_changelog: Auto-generate changelog from commits
        changelog_from: Starting ref for changelog (tag or commit)
        run_tests: Run tests before release
        test_command: Custom test command
        notify: Notification targets (e.g., ['slack:#channel'])
        dry_run: Simulate without making changes
        parallel_uploads: Upload assets in parallel
    """

    source: str = "."
    repo: str = ""
    tag: str = ""
    name: str | None = None
    body: str | None = None
    draft: bool = False
    prerelease: bool = False
    files: list[str] = field(default_factory=lambda: [])
    python: str | None = None
    output_dir: str = "dist"
    generate_changelog: bool = False
    changelog_from: str | None = None
    run_tests: bool = False
    test_command: str | None = None
    notify: list[str] = field(default_factory=lambda: [])
    dry_run: bool = False
    parallel_uploads: bool = True

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not self.name:
            self.name = self.tag


@dataclass
class PipelineResult:
    """Result of a complete pipeline run."""

    success: bool
    config: PipelineConfig
    stages: dict[PipelineStage, StageResult] = field(default_factory=lambda: {})
    started_at: datetime | None = None
    completed_at: datetime | None = None
    wheel_path: Path | None = None
    release_url: str | None = None
    changelog: str | None = None
    errors: list[str] = field(default_factory=lambda: [])

    @property
    def duration_seconds(self) -> float | None:
        """Get total pipeline duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def add_stage(self, result: StageResult) -> None:
        """Add a stage result."""
        self.stages[result.stage] = result
        if result.status == StageStatus.FAILED and result.error:
            self.errors.append(f"{result.stage.value}: {result.error}")

    def get_stage(self, stage: PipelineStage) -> StageResult | None:
        """Get result for a specific stage."""
        return self.stages.get(stage)

    @property
    def failed_stages(self) -> list[StageResult]:
        """Get list of failed stages."""
        return [s for s in self.stages.values() if s.status == StageStatus.FAILED]

    @property
    def successful_stages(self) -> list[StageResult]:
        """Get list of successful stages."""
        return [s for s in self.stages.values() if s.status == StageStatus.SUCCESS]

    def summary(self) -> dict[str, Any]:
        """Get pipeline summary."""
        return {
            "success": self.success,
            "duration_seconds": self.duration_seconds,
            "stages": {
                stage.value: {
                    "status": result.status.value,
                    "duration": result.duration_seconds,
                    "message": result.message,
                    "error": result.error,
                }
                for stage, result in self.stages.items()
            },
            "wheel_path": str(self.wheel_path) if self.wheel_path else None,
            "release_url": self.release_url,
            "errors": self.errors,
        }
