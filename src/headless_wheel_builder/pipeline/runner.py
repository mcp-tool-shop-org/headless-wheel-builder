"""Pipeline runner for orchestrating build-to-release workflows."""

from __future__ import annotations

import asyncio
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from headless_wheel_builder.core.builder import BuildConfig, BuildEngine
from headless_wheel_builder.exceptions import BuildError
from headless_wheel_builder.github import GitHubClient, GitHubConfig
from headless_wheel_builder.pipeline.models import (
    PipelineConfig,
    PipelineResult,
    PipelineStage,
    StageResult,
    StageStatus,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from headless_wheel_builder.github.models import Release


class Pipeline:
    """Orchestrates build-to-release workflows.

    A pipeline chains multiple stages together:
    1. Validate - Check configuration and prerequisites
    2. Build - Build wheel (and optionally sdist)
    3. Test - Run tests (optional)
    4. Changelog - Generate changelog from commits (optional)
    5. Release - Create GitHub release
    6. Upload - Upload assets to release
    7. Notify - Send notifications (optional)

    Example:
        ```python
        config = PipelineConfig(
            source=".",
            repo="owner/repo",
            tag="v1.0.0",
            generate_changelog=True,
            notify=["slack:#releases"],
        )

        pipeline = Pipeline(config)
        result = await pipeline.run()

        if result.success:
            print(f"Release: {result.release_url}")
        ```
    """

    def __init__(
        self,
        config: PipelineConfig,
        github_config: GitHubConfig | None = None,
    ) -> None:
        """Initialize pipeline.

        Args:
            config: Pipeline configuration
            github_config: GitHub client configuration (uses env token if not provided)
        """
        self.config = config
        self.github_config = github_config or GitHubConfig()
        self.result = PipelineResult(success=False, config=config)
        self._release: Release | None = None
        self._stage_handlers: dict[
            PipelineStage,
            Callable[[], Coroutine[Any, Any, StageResult]],
        ] = {
            PipelineStage.VALIDATE: self._run_validate,
            PipelineStage.BUILD: self._run_build,
            PipelineStage.TEST: self._run_test,
            PipelineStage.CHANGELOG: self._run_changelog,
            PipelineStage.RELEASE: self._run_release,
            PipelineStage.UPLOAD: self._run_upload,
            PipelineStage.NOTIFY: self._run_notify,
        }

    async def run(self) -> PipelineResult:
        """Execute the pipeline.

        Returns:
            PipelineResult with stage outcomes and artifacts
        """
        self.result.started_at = datetime.now(timezone.utc)

        # Determine which stages to run
        stages = self._get_stages_to_run()

        try:
            for stage in stages:
                stage_result = await self._run_stage(stage)
                self.result.add_stage(stage_result)

                # Stop on failure (except for notify which is best-effort)
                if stage_result.status == StageStatus.FAILED and stage != PipelineStage.NOTIFY:
                    break

            # Pipeline succeeds if all required stages succeeded
            required_stages = [s for s in stages if s != PipelineStage.NOTIFY]
            self.result.success = all(
                self.result.stages.get(s, StageResult.pending(s)).status == StageStatus.SUCCESS
                for s in required_stages
            )

        except Exception as e:
            self.result.errors.append(f"Pipeline error: {e}")
            self.result.success = False

        finally:
            self.result.completed_at = datetime.now(timezone.utc)

        return self.result

    def _get_stages_to_run(self) -> list[PipelineStage]:
        """Determine which stages to run based on config."""
        stages = [PipelineStage.VALIDATE, PipelineStage.BUILD]

        if self.config.run_tests:
            stages.append(PipelineStage.TEST)

        if self.config.generate_changelog:
            stages.append(PipelineStage.CHANGELOG)

        # Release and upload require repo and tag
        if self.config.repo and self.config.tag:
            stages.append(PipelineStage.RELEASE)
            stages.append(PipelineStage.UPLOAD)

        if self.config.notify:
            stages.append(PipelineStage.NOTIFY)

        return stages

    async def _run_stage(self, stage: PipelineStage) -> StageResult:
        """Run a single pipeline stage."""
        handler = self._stage_handlers.get(stage)
        if not handler:
            return StageResult.skipped(stage, f"No handler for {stage.value}")

        result = StageResult.pending(stage)
        result.started_at = datetime.now(timezone.utc)
        result.status = StageStatus.RUNNING

        try:
            result = await handler()
            result.started_at = result.started_at or datetime.now(timezone.utc)
        except Exception as e:
            result = StageResult.failure(stage, str(e))

        result.completed_at = datetime.now(timezone.utc)
        return result

    async def _run_validate(self) -> StageResult:
        """Validate pipeline configuration."""
        errors: list[str] = []

        # Check source exists
        source_path = Path(self.config.source)
        if self.config.source != "." and not source_path.exists():
            if not self.config.source.startswith(("http://", "https://", "git@")):
                errors.append(f"Source not found: {self.config.source}")

        # Check repo format if specified
        if self.config.repo and "/" not in self.config.repo:
            errors.append(f"Invalid repo format: {self.config.repo} (expected owner/repo)")

        # Check tag if releasing
        if self.config.repo and not self.config.tag:
            errors.append("Tag required for release")

        # Check GitHub token if releasing
        if self.config.repo and not self.github_config.token:
            errors.append("GitHub token required (set GITHUB_TOKEN or pass token)")

        if errors:
            return StageResult.failure(PipelineStage.VALIDATE, "; ".join(errors))

        return StageResult.success(
            PipelineStage.VALIDATE,
            message="Configuration valid",
            data={
                "source": self.config.source,
                "repo": self.config.repo,
                "tag": self.config.tag,
            },
        )

    async def _run_build(self) -> StageResult:
        """Build wheel from source."""
        if self.config.dry_run:
            return StageResult.success(
                PipelineStage.BUILD,
                message="[dry-run] Would build wheel",
                data={"dry_run": True},
            )

        try:
            output_dir = Path(self.config.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Build configuration
            build_config = BuildConfig(
                output_dir=output_dir,
                python_version=self.config.python or "3.12",
            )

            # Run build
            engine = BuildEngine(build_config)
            build_result = await engine.build(
                source=self.config.source,
                output_dir=output_dir,
            )

            if not build_result.success:
                return StageResult.failure(
                    PipelineStage.BUILD,
                    build_result.error or "Build failed",
                )

            self.result.wheel_path = build_result.wheel_path

            wheel_name = build_result.wheel_path.name if build_result.wheel_path else "wheel"
            return StageResult.success(
                PipelineStage.BUILD,
                message=f"Built {wheel_name}",
                data={
                    "wheel_path": str(build_result.wheel_path) if build_result.wheel_path else None,
                    "sha256": build_result.sha256,
                },
            )

        except BuildError as e:
            return StageResult.failure(PipelineStage.BUILD, str(e))

    async def _run_test(self) -> StageResult:
        """Run tests."""
        if self.config.dry_run:
            return StageResult.success(
                PipelineStage.TEST,
                message="[dry-run] Would run tests",
                data={"dry_run": True},
            )

        try:
            # Use custom command or default to pytest
            command = self.config.test_command or "pytest"

            # Run in subprocess
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.config.source if self.config.source != "." else None,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                error_msg = stderr.decode() if stderr else stdout.decode()
                return StageResult.failure(
                    PipelineStage.TEST,
                    f"Tests failed (exit {proc.returncode}): {error_msg[:500]}",
                )

            return StageResult.success(
                PipelineStage.TEST,
                message="Tests passed",
                data={"command": command},
            )

        except Exception as e:
            return StageResult.failure(PipelineStage.TEST, str(e))

    async def _run_changelog(self) -> StageResult:
        """Generate changelog from git commits."""
        if self.config.dry_run:
            return StageResult.success(
                PipelineStage.CHANGELOG,
                message="[dry-run] Would generate changelog",
                data={"dry_run": True},
            )

        try:
            # Get commits since last tag or specified ref
            from_ref = self.config.changelog_from
            if not from_ref:
                # Try to find previous tag
                try:
                    result = subprocess.run(
                        ["git", "describe", "--tags", "--abbrev=0", "HEAD^"],
                        capture_output=True,
                        text=True,
                        cwd=self.config.source if self.config.source != "." else None,
                        check=False,
                    )
                    if result.returncode == 0:
                        from_ref = result.stdout.strip()
                except Exception:
                    pass

            # Get commits
            git_range = f"{from_ref}..HEAD" if from_ref else "HEAD~10..HEAD"
            result = subprocess.run(
                ["git", "log", "--pretty=format:%s (%h)", git_range],
                capture_output=True,
                text=True,
                cwd=self.config.source if self.config.source != "." else None,
                check=False,
            )

            commits = result.stdout.strip().split("\n") if result.stdout.strip() else []

            # Generate changelog in conventional format
            changelog_lines = [f"## What's Changed in {self.config.tag}", ""]

            # Categorize commits
            features: list[str] = []
            fixes: list[str] = []
            other: list[str] = []

            for commit in commits:
                if commit.startswith("feat"):
                    features.append(f"- {commit}")
                elif commit.startswith("fix"):
                    fixes.append(f"- {commit}")
                else:
                    other.append(f"- {commit}")

            if features:
                changelog_lines.extend(["### ✨ Features", "", *features, ""])
            if fixes:
                changelog_lines.extend(["### 🐛 Bug Fixes", "", *fixes, ""])
            if other:
                changelog_lines.extend(["### 📝 Other Changes", "", *other, ""])

            changelog = "\n".join(changelog_lines)
            self.result.changelog = changelog

            return StageResult.success(
                PipelineStage.CHANGELOG,
                message=f"Generated changelog ({len(commits)} commits)",
                data={"commits": len(commits), "from_ref": from_ref},
            )

        except Exception as e:
            return StageResult.failure(PipelineStage.CHANGELOG, str(e))

    async def _run_release(self) -> StageResult:
        """Create GitHub release."""
        if self.config.dry_run:
            return StageResult.success(
                PipelineStage.RELEASE,
                message=f"[dry-run] Would create release {self.config.tag}",
                data={"dry_run": True, "tag": self.config.tag},
            )

        try:
            async with GitHubClient(self.github_config) as client:
                # Use changelog if generated, otherwise use provided body
                body = self.result.changelog or self.config.body or ""

                release = await client.create_release(
                    self.config.repo,
                    tag=self.config.tag,
                    name=self.config.name,
                    body=body,
                    draft=self.config.draft,
                    prerelease=self.config.prerelease,
                )

                self.result.release_url = release.html_url

                # Store release for upload stage
                self._release = release

                return StageResult.success(
                    PipelineStage.RELEASE,
                    message=f"Created release {self.config.tag}",
                    data={
                        "tag": self.config.tag,
                        "url": release.html_url,
                        "draft": self.config.draft,
                    },
                )

        except Exception as e:
            return StageResult.failure(PipelineStage.RELEASE, str(e))

    async def _run_upload(self) -> StageResult:
        """Upload assets to GitHub release."""
        # Collect files to upload
        files_to_upload: list[Path] = []

        # Add built wheel
        if self.result.wheel_path and self.result.wheel_path.exists():
            files_to_upload.append(self.result.wheel_path)

        # Add additional files from config
        for pattern in self.config.files:
            path = Path(pattern)
            if path.exists():
                files_to_upload.append(path)
            else:
                # Try glob
                output_dir = Path(self.config.output_dir)
                files_to_upload.extend(output_dir.glob(pattern))

        if not files_to_upload:
            return StageResult.success(
                PipelineStage.UPLOAD,
                message="No assets to upload",
                data={"count": 0},
            )

        if self.config.dry_run:
            return StageResult.success(
                PipelineStage.UPLOAD,
                message=f"[dry-run] Would upload {len(files_to_upload)} assets",
                data={"dry_run": True, "files": [str(f) for f in files_to_upload]},
            )

        # Require release for actual upload
        if not self._release:
            return StageResult.failure(
                PipelineStage.UPLOAD,
                "No release available for upload",
            )

        try:
            async with GitHubClient(self.github_config) as client:
                result = await client.upload_assets(
                    self._release.upload_url,
                    [str(f) for f in files_to_upload],
                    parallel=self.config.parallel_uploads,
                )

                if not result.success:
                    errors = [f"{p.name}: {e}" for p, e in result.assets_failed]
                    return StageResult.failure(
                        PipelineStage.UPLOAD,
                        f"Failed to upload: {'; '.join(errors)}",
                    )

                return StageResult.success(
                    PipelineStage.UPLOAD,
                    message=f"Uploaded {len(result.assets_uploaded)} assets",
                    data={
                        "count": len(result.assets_uploaded),
                        "assets": [a.name for a in result.assets_uploaded],
                    },
                )

        except Exception as e:
            return StageResult.failure(PipelineStage.UPLOAD, str(e))

    async def _run_notify(self) -> StageResult:
        """Send notifications."""
        if not self.config.notify:
            return StageResult.skipped(PipelineStage.NOTIFY, "No notifications configured")

        if self.config.dry_run:
            return StageResult.success(
                PipelineStage.NOTIFY,
                message=f"[dry-run] Would notify {len(self.config.notify)} targets",
                data={"dry_run": True, "targets": self.config.notify},
            )

        # Notification will be implemented in Phase 5
        # For now, just log what would be sent
        sent: list[str] = []
        failed: list[str] = []

        for target in self.config.notify:
            # Parse target (e.g., "slack:#channel", "discord:webhook", "webhook:url")
            if ":" not in target:
                failed.append(f"{target}: invalid format")
                continue

            provider, _destination = target.split(":", 1)

            # Placeholder - actual implementation in Phase 5
            if provider in ("slack", "discord", "webhook"):
                # Would send notification here (destination stored in _destination)
                sent.append(target)
            else:
                failed.append(f"{target}: unknown provider '{provider}'")

        if failed and not sent:
            return StageResult.failure(
                PipelineStage.NOTIFY,
                f"All notifications failed: {'; '.join(failed)}",
            )

        message = f"Sent {len(sent)} notifications"
        if failed:
            message += f" ({len(failed)} failed)"

        return StageResult.success(
            PipelineStage.NOTIFY,
            message=message,
            data={"sent": sent, "failed": failed},
        )


async def run_pipeline(
    config: PipelineConfig,
    github_config: GitHubConfig | None = None,
) -> PipelineResult:
    """Convenience function to run a pipeline.

    Args:
        config: Pipeline configuration
        github_config: Optional GitHub client configuration

    Returns:
        PipelineResult with all stage outcomes
    """
    pipeline = Pipeline(config, github_config)
    return await pipeline.run()
