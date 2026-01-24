"""Tests for pipeline orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from headless_wheel_builder.pipeline.models import (
    PipelineConfig,
    PipelineResult,
    PipelineStage,
    StageResult,
    StageStatus,
)
from headless_wheel_builder.pipeline.runner import Pipeline


class TestStageResult:
    """Tests for StageResult model."""

    def test_pending(self) -> None:
        """Test creating pending stage result."""
        result = StageResult.pending(PipelineStage.BUILD)
        assert result.stage == PipelineStage.BUILD
        assert result.status == StageStatus.PENDING
        assert result.error is None

    def test_success(self) -> None:
        """Test creating successful stage result."""
        result = StageResult.success(
            PipelineStage.BUILD,
            message="Built wheel",
            data={"wheel": "test.whl"},
        )
        assert result.stage == PipelineStage.BUILD
        assert result.status == StageStatus.SUCCESS
        assert result.message == "Built wheel"
        assert result.data == {"wheel": "test.whl"}

    def test_failure(self) -> None:
        """Test creating failed stage result."""
        result = StageResult.failure(PipelineStage.TEST, "Tests failed")
        assert result.stage == PipelineStage.TEST
        assert result.status == StageStatus.FAILED
        assert result.error == "Tests failed"

    def test_skipped(self) -> None:
        """Test creating skipped stage result."""
        result = StageResult.skipped(PipelineStage.NOTIFY, "No targets")
        assert result.stage == PipelineStage.NOTIFY
        assert result.status == StageStatus.SKIPPED
        assert result.message == "No targets"

    def test_duration(self) -> None:
        """Test duration calculation."""
        result = StageResult.pending(PipelineStage.BUILD)
        result.started_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result.completed_at = datetime(2024, 1, 1, 12, 0, 5, tzinfo=timezone.utc)
        assert result.duration_seconds == 5.0

    def test_duration_none_if_incomplete(self) -> None:
        """Test duration is None when stage not complete."""
        result = StageResult.pending(PipelineStage.BUILD)
        result.started_at = datetime.now(timezone.utc)
        assert result.duration_seconds is None


class TestPipelineConfig:
    """Tests for PipelineConfig model."""

    def test_defaults(self) -> None:
        """Test default configuration."""
        config = PipelineConfig()
        assert config.source == "."
        assert config.repo == ""
        assert config.output_dir == "dist"
        assert config.dry_run is False
        assert config.parallel_uploads is True

    def test_name_defaults_to_tag(self) -> None:
        """Test that name defaults to tag if not set."""
        config = PipelineConfig(tag="v1.0.0")
        assert config.name == "v1.0.0"

    def test_custom_values(self) -> None:
        """Test custom configuration."""
        config = PipelineConfig(
            source="https://github.com/user/repo",
            repo="user/repo",
            tag="v2.0.0",
            name="Release 2.0",
            draft=True,
            prerelease=True,
            files=["README.md", "LICENSE"],
            generate_changelog=True,
            run_tests=True,
            notify=["slack:#channel"],
        )
        assert config.source == "https://github.com/user/repo"
        assert config.repo == "user/repo"
        assert config.tag == "v2.0.0"
        assert config.name == "Release 2.0"
        assert config.draft is True
        assert config.prerelease is True
        assert config.files == ["README.md", "LICENSE"]
        assert config.generate_changelog is True
        assert config.run_tests is True
        assert config.notify == ["slack:#channel"]


class TestPipelineResult:
    """Tests for PipelineResult model."""

    def test_add_stage(self) -> None:
        """Test adding stage results."""
        config = PipelineConfig()
        result = PipelineResult(success=True, config=config)

        stage = StageResult.success(PipelineStage.BUILD, "Done")
        result.add_stage(stage)

        assert PipelineStage.BUILD in result.stages
        assert result.stages[PipelineStage.BUILD] == stage

    def test_add_failed_stage_adds_error(self) -> None:
        """Test that failed stages add to errors list."""
        config = PipelineConfig()
        result = PipelineResult(success=False, config=config)

        stage = StageResult.failure(PipelineStage.BUILD, "Build failed")
        result.add_stage(stage)

        assert len(result.errors) == 1
        assert "build: Build failed" in result.errors[0]

    def test_get_stage(self) -> None:
        """Test getting stage results."""
        config = PipelineConfig()
        result = PipelineResult(success=True, config=config)
        result.add_stage(StageResult.success(PipelineStage.VALIDATE))

        assert result.get_stage(PipelineStage.VALIDATE) is not None
        assert result.get_stage(PipelineStage.BUILD) is None

    def test_failed_stages(self) -> None:
        """Test getting failed stages."""
        config = PipelineConfig()
        result = PipelineResult(success=False, config=config)
        result.add_stage(StageResult.success(PipelineStage.VALIDATE))
        result.add_stage(StageResult.failure(PipelineStage.BUILD, "Error"))

        failed = result.failed_stages
        assert len(failed) == 1
        assert failed[0].stage == PipelineStage.BUILD

    def test_successful_stages(self) -> None:
        """Test getting successful stages."""
        config = PipelineConfig()
        result = PipelineResult(success=True, config=config)
        result.add_stage(StageResult.success(PipelineStage.VALIDATE))
        result.add_stage(StageResult.success(PipelineStage.BUILD))
        result.add_stage(StageResult.skipped(PipelineStage.TEST))

        successful = result.successful_stages
        assert len(successful) == 2

    def test_summary(self) -> None:
        """Test generating summary."""
        config = PipelineConfig(tag="v1.0.0", repo="user/repo")
        result = PipelineResult(success=True, config=config)
        result.started_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result.completed_at = datetime(2024, 1, 1, 12, 0, 10, tzinfo=timezone.utc)
        result.wheel_path = Path("dist/test.whl")
        result.release_url = "https://github.com/user/repo/releases/v1.0.0"
        result.add_stage(StageResult.success(PipelineStage.BUILD))

        summary = result.summary()
        assert summary["success"] is True
        assert summary["duration_seconds"] == 10.0
        assert "build" in summary["stages"]
        # Path separator is OS-dependent
        assert "test.whl" in summary["wheel_path"]
        assert summary["release_url"] == "https://github.com/user/repo/releases/v1.0.0"


class TestPipeline:
    """Tests for Pipeline runner."""

    @pytest.fixture
    def basic_config(self) -> PipelineConfig:
        """Create basic pipeline config."""
        return PipelineConfig(source=".", output_dir="dist")

    @pytest.fixture
    def release_config(self) -> PipelineConfig:
        """Create release pipeline config."""
        return PipelineConfig(
            source=".",
            repo="user/repo",
            tag="v1.0.0",
            output_dir="dist",
        )

    def test_init(self, basic_config: PipelineConfig) -> None:
        """Test pipeline initialization."""
        pipeline = Pipeline(basic_config)
        assert pipeline.config == basic_config
        assert pipeline.result.success is False

    def test_get_stages_basic(self, basic_config: PipelineConfig) -> None:
        """Test stage selection for basic config."""
        pipeline = Pipeline(basic_config)
        stages = pipeline._get_stages_to_run()

        assert PipelineStage.VALIDATE in stages
        assert PipelineStage.BUILD in stages
        assert PipelineStage.RELEASE not in stages
        assert PipelineStage.UPLOAD not in stages

    def test_get_stages_with_release(self, release_config: PipelineConfig) -> None:
        """Test stage selection for release config."""
        pipeline = Pipeline(release_config)
        stages = pipeline._get_stages_to_run()

        assert PipelineStage.VALIDATE in stages
        assert PipelineStage.BUILD in stages
        assert PipelineStage.RELEASE in stages
        assert PipelineStage.UPLOAD in stages

    def test_get_stages_with_tests(self, basic_config: PipelineConfig) -> None:
        """Test stage selection with tests enabled."""
        basic_config.run_tests = True
        pipeline = Pipeline(basic_config)
        stages = pipeline._get_stages_to_run()

        assert PipelineStage.TEST in stages

    def test_get_stages_with_changelog(self, release_config: PipelineConfig) -> None:
        """Test stage selection with changelog enabled."""
        release_config.generate_changelog = True
        pipeline = Pipeline(release_config)
        stages = pipeline._get_stages_to_run()

        assert PipelineStage.CHANGELOG in stages

    def test_get_stages_with_notify(self, basic_config: PipelineConfig) -> None:
        """Test stage selection with notifications."""
        basic_config.notify = ["slack:#channel"]
        pipeline = Pipeline(basic_config)
        stages = pipeline._get_stages_to_run()

        assert PipelineStage.NOTIFY in stages

    @pytest.mark.asyncio
    async def test_validate_success(self, basic_config: PipelineConfig) -> None:
        """Test validation passes for valid config."""
        pipeline = Pipeline(basic_config)
        result = await pipeline._run_validate()

        assert result.status == StageStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_validate_fails_bad_repo_format(self) -> None:
        """Test validation fails for bad repo format."""
        config = PipelineConfig(repo="badfformat", tag="v1.0.0")
        # Mock token to avoid that error
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            pipeline = Pipeline(config)
            result = await pipeline._run_validate()

        assert result.status == StageStatus.FAILED
        assert "Invalid repo format" in (result.error or "")

    @pytest.mark.asyncio
    async def test_validate_fails_missing_tag(self) -> None:
        """Test validation fails when tag missing for release."""
        config = PipelineConfig(repo="user/repo")
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            pipeline = Pipeline(config)
            result = await pipeline._run_validate()

        assert result.status == StageStatus.FAILED
        assert "Tag required" in (result.error or "")

    @pytest.mark.asyncio
    async def test_build_dry_run(self, basic_config: PipelineConfig) -> None:
        """Test build in dry run mode."""
        basic_config.dry_run = True
        pipeline = Pipeline(basic_config)
        result = await pipeline._run_build()

        assert result.status == StageStatus.SUCCESS
        assert "dry-run" in result.message

    @pytest.mark.asyncio
    async def test_test_dry_run(self, basic_config: PipelineConfig) -> None:
        """Test test stage in dry run mode."""
        basic_config.dry_run = True
        pipeline = Pipeline(basic_config)
        result = await pipeline._run_test()

        assert result.status == StageStatus.SUCCESS
        assert "dry-run" in result.message

    @pytest.mark.asyncio
    async def test_changelog_dry_run(self, basic_config: PipelineConfig) -> None:
        """Test changelog in dry run mode."""
        basic_config.dry_run = True
        basic_config.tag = "v1.0.0"
        pipeline = Pipeline(basic_config)
        result = await pipeline._run_changelog()

        assert result.status == StageStatus.SUCCESS
        assert "dry-run" in result.message

    @pytest.mark.asyncio
    async def test_release_dry_run(self, release_config: PipelineConfig) -> None:
        """Test release in dry run mode."""
        release_config.dry_run = True
        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            pipeline = Pipeline(release_config)
            result = await pipeline._run_release()

        assert result.status == StageStatus.SUCCESS
        assert "dry-run" in result.message
        assert release_config.tag in result.message

    @pytest.mark.asyncio
    async def test_upload_no_files(self, basic_config: PipelineConfig) -> None:
        """Test upload succeeds with no files (nothing to upload)."""
        pipeline = Pipeline(basic_config)
        result = await pipeline._run_upload()

        # No files to upload is a success (not a failure)
        assert result.status == StageStatus.SUCCESS
        assert "No assets" in result.message

    @pytest.mark.asyncio
    async def test_notify_skipped_when_no_targets(self, basic_config: PipelineConfig) -> None:
        """Test notify skipped when no targets configured."""
        pipeline = Pipeline(basic_config)
        result = await pipeline._run_notify()

        assert result.status == StageStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_notify_dry_run(self, basic_config: PipelineConfig) -> None:
        """Test notify in dry run mode."""
        basic_config.dry_run = True
        basic_config.notify = ["slack:#channel"]
        pipeline = Pipeline(basic_config)
        result = await pipeline._run_notify()

        assert result.status == StageStatus.SUCCESS
        assert "dry-run" in result.message

    @pytest.mark.asyncio
    async def test_notify_invalid_format(self, basic_config: PipelineConfig) -> None:
        """Test notify with invalid target format."""
        basic_config.notify = ["invalid_no_colon"]
        pipeline = Pipeline(basic_config)
        result = await pipeline._run_notify()

        assert result.status == StageStatus.FAILED
        assert "invalid format" in (result.error or "")

    @pytest.mark.asyncio
    async def test_notify_unknown_provider(self, basic_config: PipelineConfig) -> None:
        """Test notify with unknown provider."""
        basic_config.notify = ["unknown:target"]
        pipeline = Pipeline(basic_config)
        result = await pipeline._run_notify()

        assert result.status == StageStatus.FAILED
        assert "unknown provider" in (result.error or "")

    @pytest.mark.asyncio
    async def test_notify_valid_providers(self, basic_config: PipelineConfig) -> None:
        """Test notify with valid providers."""
        basic_config.notify = ["slack:#channel", "discord:webhook", "webhook:url"]
        pipeline = Pipeline(basic_config)
        result = await pipeline._run_notify()

        assert result.status == StageStatus.SUCCESS
        assert "3" in result.message

    @pytest.mark.asyncio
    async def test_full_pipeline_dry_run(self, release_config: PipelineConfig) -> None:
        """Test full pipeline in dry run mode."""
        release_config.dry_run = True
        release_config.run_tests = True
        release_config.generate_changelog = True
        release_config.notify = ["slack:#releases"]

        with patch.dict("os.environ", {"GITHUB_TOKEN": "test_token"}):
            pipeline = Pipeline(release_config)
            result = await pipeline.run()

        assert result.success is True
        assert len(result.stages) >= 5  # validate, build, test, changelog, notify
        assert result.started_at is not None
        assert result.completed_at is not None


class TestPipelineStages:
    """Tests for PipelineStage enum."""

    def test_all_stages_exist(self) -> None:
        """Test all expected stages exist."""
        stages = [s.value for s in PipelineStage]
        assert "validate" in stages
        assert "build" in stages
        assert "test" in stages
        assert "changelog" in stages
        assert "release" in stages
        assert "upload" in stages
        assert "notify" in stages


class TestStageStatus:
    """Tests for StageStatus enum."""

    def test_all_statuses_exist(self) -> None:
        """Test all expected statuses exist."""
        statuses = [s.value for s in StageStatus]
        assert "pending" in statuses
        assert "running" in statuses
        assert "success" in statuses
        assert "failed" in statuses
        assert "skipped" in statuses
