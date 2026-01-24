"""CLI commands for pipeline operations."""

from __future__ import annotations

import asyncio
import json
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from headless_wheel_builder.pipeline.models import (
    PipelineConfig,
    PipelineResult,
    PipelineStage,
    StageStatus,
)
from headless_wheel_builder.pipeline.runner import Pipeline

console = Console()
error_console = Console(stderr=True)


def _status_icon(status: StageStatus) -> str:
    """Get icon for stage status."""
    return {
        StageStatus.PENDING: "⏳",
        StageStatus.RUNNING: "🔄",
        StageStatus.SUCCESS: "✅",
        StageStatus.FAILED: "❌",
        StageStatus.SKIPPED: "⏭️",
    }.get(status, "❓")


def _status_style(status: StageStatus) -> str:
    """Get style for stage status."""
    return {
        StageStatus.PENDING: "dim",
        StageStatus.RUNNING: "yellow",
        StageStatus.SUCCESS: "green",
        StageStatus.FAILED: "red",
        StageStatus.SKIPPED: "dim",
    }.get(status, "")


def _format_duration(seconds: float | None) -> str:
    """Format duration in human-readable form."""
    if seconds is None:
        return "-"
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.0f}s"


def _display_result(result: PipelineResult, output_json: bool) -> None:
    """Display pipeline result."""
    if output_json:
        console.print(json.dumps(result.summary(), indent=2))
        return

    # Create stages table
    table = Table(title="Pipeline Results", show_header=True)
    table.add_column("Stage", style="bold")
    table.add_column("Status")
    table.add_column("Duration")
    table.add_column("Message")

    for stage in PipelineStage:
        stage_result = result.get_stage(stage)
        if stage_result:
            icon = _status_icon(stage_result.status)
            style = _status_style(stage_result.status)
            duration = _format_duration(stage_result.duration_seconds)
            message = stage_result.error or stage_result.message or ""
            # Truncate long messages
            if len(message) > 50:
                message = message[:47] + "..."
            table.add_row(
                stage.value.capitalize(),
                f"{icon} [{style}]{stage_result.status.value}[/]",
                duration,
                message,
            )

    console.print(table)
    console.print()

    # Summary panel
    if result.success:
        summary_parts = ["[green]✅ Pipeline completed successfully[/green]"]
        if result.wheel_path:
            summary_parts.append(f"📦 Wheel: {result.wheel_path}")
        if result.release_url:
            summary_parts.append(f"🔗 Release: {result.release_url}")
        if result.duration_seconds:
            summary_parts.append(f"⏱️ Duration: {_format_duration(result.duration_seconds)}")

        console.print(Panel("\n".join(summary_parts), title="Summary", border_style="green"))
    else:
        error_parts = ["[red]❌ Pipeline failed[/red]"]
        for error in result.errors:
            error_parts.append(f"  • {error}")

        console.print(Panel("\n".join(error_parts), title="Errors", border_style="red"))


@click.group("pipeline")
def pipeline() -> None:
    """Pipeline orchestration commands.

    Chain build, test, release, and notification stages together.
    """
    pass


@pipeline.command("release")
@click.argument("tag")
@click.option("--repo", "-r", required=True, help="GitHub repository (owner/repo)")
@click.option("--source", "-s", default=".", help="Source to build (path or git URL)")
@click.option("--name", "-n", help="Release name (defaults to tag)")
@click.option("--body", "-b", help="Release body/description")
@click.option("--draft", is_flag=True, help="Create as draft release")
@click.option("--prerelease", is_flag=True, help="Mark as prerelease")
@click.option("--files", "-f", multiple=True, help="Additional files to upload")
@click.option("--python", "-p", help="Python version to build with")
@click.option("--output", "-o", "output_dir", default="dist", help="Output directory")
@click.option(
    "--changelog", "generate_changelog", is_flag=True, help="Generate changelog from commits"
)
@click.option("--changelog-from", help="Starting ref for changelog")
@click.option("--test", "run_tests", is_flag=True, help="Run tests before release")
@click.option("--test-command", help="Custom test command")
@click.option("--notify", multiple=True, help="Notification target (e.g., slack:#channel)")
@click.option("--dry-run", is_flag=True, help="Simulate without making changes")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def release_cmd(
    tag: str,
    repo: str,
    source: str,
    name: str | None,
    body: str | None,
    draft: bool,
    prerelease: bool,
    files: tuple[str, ...],
    python: str | None,
    output_dir: str,
    generate_changelog: bool,
    changelog_from: str | None,
    run_tests: bool,
    test_command: str | None,
    notify: tuple[str, ...],
    dry_run: bool,
    output_json: bool,
) -> None:
    """Build, release, and publish in one command.

    Example:
        hwb pipeline release v1.0.0 --repo owner/repo --changelog
    """
    config = PipelineConfig(
        source=source,
        repo=repo,
        tag=tag,
        name=name,
        body=body,
        draft=draft,
        prerelease=prerelease,
        files=list(files),
        python=python,
        output_dir=output_dir,
        generate_changelog=generate_changelog,
        changelog_from=changelog_from,
        run_tests=run_tests,
        test_command=test_command,
        notify=list(notify),
        dry_run=dry_run,
    )

    async def _run() -> PipelineResult:
        pipe = Pipeline(config)

        if not output_json:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Running pipeline...", total=None)
                result = await pipe.run()
                progress.remove_task(task)
        else:
            result = await pipe.run()

        return result

    result = asyncio.run(_run())
    _display_result(result, output_json)

    if not result.success:
        sys.exit(1)


@pipeline.command("build-only")
@click.option("--source", "-s", default=".", help="Source to build")
@click.option("--python", "-p", help="Python version")
@click.option("--output", "-o", "output_dir", default="dist", help="Output directory")
@click.option("--test", "run_tests", is_flag=True, help="Run tests after build")
@click.option("--test-command", help="Custom test command")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def build_only_cmd(
    source: str,
    python: str | None,
    output_dir: str,
    run_tests: bool,
    test_command: str | None,
    output_json: bool,
) -> None:
    """Build wheel without releasing.

    Example:
        hwb pipeline build-only --test
    """
    config = PipelineConfig(
        source=source,
        python=python,
        output_dir=output_dir,
        run_tests=run_tests,
        test_command=test_command,
    )

    async def _run() -> PipelineResult:
        pipe = Pipeline(config)
        return await pipe.run()

    result = asyncio.run(_run())
    _display_result(result, output_json)

    if not result.success:
        sys.exit(1)


@pipeline.command("status")
@click.argument("result_file", type=click.Path(exists=True))
def status_cmd(result_file: str) -> None:
    """Show status of a previous pipeline run from JSON file."""
    with open(result_file) as f:
        data = json.load(f)

    console.print(json.dumps(data, indent=2))
