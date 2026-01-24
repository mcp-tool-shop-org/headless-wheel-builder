"""CLI for metrics and analytics."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from headless_wheel_builder.metrics.collector import MetricsCollector
from headless_wheel_builder.metrics.models import TimeRange
from headless_wheel_builder.metrics.storage import MetricsStorage

console = Console()
error_console = Console(stderr=True)


@click.group(name="metrics")
def metrics() -> None:
    """Build metrics and analytics.

    View and analyze build performance data.
    """
    pass


@metrics.command("summary")
@click.option(
    "--range",
    "time_range",
    type=click.Choice(["hour", "day", "week", "month", "all"]),
    default="all",
    help="Time range",
)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def show_summary(time_range: str, json_output: bool) -> None:
    """Show build metrics summary."""
    collector = MetricsCollector()
    summary = collector.get_summary(TimeRange(time_range))

    if json_output:
        click.echo(json.dumps(summary.to_dict(), indent=2))
        return

    console.print()
    console.print(
        Panel(
            f"[bold]Time Range:[/] {time_range}\n"
            f"[bold]Total Builds:[/] {summary.total_builds}\n"
            f"[bold]Successful:[/] [green]{summary.successful_builds}[/]\n"
            f"[bold]Failed:[/] [red]{summary.failed_builds}[/]\n"
            f"[bold]Success Rate:[/] {summary.success_rate:.1%}\n"
            f"[bold]Avg Duration:[/] {summary.avg_duration_seconds:.1f}s\n"
            f"[bold]Total Built:[/] {_format_bytes(summary.total_bytes_built)}\n"
            f"[bold]Packages:[/] {summary.packages_built}",
            title="Build Metrics Summary",
            border_style="blue",
        )
    )
    console.print()


@metrics.command("report")
@click.option(
    "--range",
    "time_range",
    type=click.Choice(["hour", "day", "week", "month", "all"]),
    default="week",
    help="Time range",
)
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def show_report(time_range: str, json_output: bool) -> None:
    """Show detailed metrics report."""
    collector = MetricsCollector()
    report = collector.get_report(TimeRange(time_range))

    if json_output:
        click.echo(json.dumps(report.to_dict(), indent=2))
        return

    console.print()

    # Summary
    summary = report.summary
    console.print(
        Panel(
            f"Total: {summary.total_builds} | "
            f"Success: [green]{summary.successful_builds}[/] | "
            f"Failed: [red]{summary.failed_builds}[/] | "
            f"Rate: {summary.success_rate:.1%}",
            title=f"Summary ({time_range})",
            border_style="blue",
        )
    )

    # By package
    if report.by_package:
        table = Table(title="By Package")
        table.add_column("Package", style="cyan")
        table.add_column("Builds", justify="right")
        table.add_column("Success", justify="right")
        table.add_column("Rate", justify="right")
        table.add_column("Avg Duration", justify="right")

        for pkg, stats in sorted(
            report.by_package.items(),
            key=lambda x: x[1].total_builds,
            reverse=True,
        )[:10]:
            rate_style = (
                "green"
                if stats.success_rate >= 0.9
                else "yellow"
                if stats.success_rate >= 0.7
                else "red"
            )
            table.add_row(
                pkg,
                str(stats.total_builds),
                str(stats.successful_builds),
                f"[{rate_style}]{stats.success_rate:.1%}[/]",
                f"{stats.avg_duration_seconds:.1f}s",
            )

        console.print(table)

    # By Python version
    if report.by_python_version:
        table = Table(title="By Python Version")
        table.add_column("Version", style="cyan")
        table.add_column("Builds", justify="right")
        table.add_column("Success Rate", justify="right")
        table.add_column("Avg Duration", justify="right")

        for version, stats in sorted(report.by_python_version.items()):
            table.add_row(
                version,
                str(stats.total_builds),
                f"{stats.success_rate:.1%}",
                f"{stats.avg_duration_seconds:.1f}s",
            )

        console.print(table)

    # Recent failures
    if report.recent_failures:
        console.print("\n[bold red]Recent Failures[/]")
        for failure in report.recent_failures[-5:]:
            console.print(
                f"  • {failure.package} {failure.version}: "
                f"[dim]{failure.error or 'Unknown error'}[/]"
            )

    console.print()


@metrics.command("trends")
@click.option("--package", "-p", help="Filter by package")
@click.option("--days", "-d", default=14, help="Number of days")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def show_trends(package: str | None, days: int, json_output: bool) -> None:
    """Show build trends over time."""
    collector = MetricsCollector()
    trends = collector.get_trends(package=package, days=days)

    if json_output:
        click.echo(json.dumps(trends, indent=2))
        return

    if not trends:
        console.print("[yellow]No trend data available[/]")
        return

    console.print()
    title = f"Build Trends - Last {days} Days"
    if package:
        title += f" ({package})"

    table = Table(title=title)
    table.add_column("Date", style="cyan")
    table.add_column("Total", justify="right")
    table.add_column("Success", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Rate", justify="right")
    table.add_column("Avg Duration", justify="right")

    for day in trends:
        rate = day["success_rate"]
        rate_style = "green" if rate >= 0.9 else "yellow" if rate >= 0.7 else "red"
        table.add_row(
            day["date"],
            str(day["total"]),
            str(day["successful"]),
            str(day["failed"]),
            f"[{rate_style}]{rate:.1%}[/]",
            f"{day['avg_duration']:.1f}s",
        )

    console.print(table)
    console.print()


@metrics.command("list")
@click.option("--count", "-n", default=20, help="Number of entries")
@click.option("--package", "-p", help="Filter by package")
@click.option("--failures", "-f", is_flag=True, help="Show only failures")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def list_metrics(
    count: int,
    package: str | None,
    failures: bool,
    json_output: bool,
) -> None:
    """List recent build metrics."""
    storage = MetricsStorage()

    if failures:
        entries = storage.get_failures(count)
    elif package:
        entries = storage.get_by_package(package)[-count:]
    else:
        entries = storage.get_recent(count)

    if json_output:
        click.echo(json.dumps([e.to_dict() for e in entries], indent=2))
        return

    if not entries:
        console.print("[yellow]No metrics found[/]")
        return

    table = Table(title=f"Build Metrics (showing {len(entries)})")
    table.add_column("Timestamp", style="dim")
    table.add_column("Package", style="cyan")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("Duration", justify="right")
    table.add_column("Size", justify="right")

    for entry in entries:
        status = "[green]OK[/]" if entry.success else "[red]FAIL[/]"
        ts = entry.timestamp[:19] if entry.timestamp else "-"
        size = _format_bytes(entry.wheel_size_bytes) if entry.wheel_size_bytes else "-"

        table.add_row(
            ts,
            entry.package,
            entry.version,
            status,
            f"{entry.duration_seconds:.1f}s",
            size,
        )

    console.print(table)


@metrics.command("export")
@click.argument("output_file", type=click.Path(path_type=Path))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "csv"]),
    default="json",
    help="Export format",
)
def export_metrics(output_file: Path, output_format: str) -> None:
    """Export metrics to file."""
    storage = MetricsStorage()
    storage.export(output_file, format=output_format)
    console.print(f"[green]Exported metrics to:[/] {output_file}")


@metrics.command("clear")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def clear_metrics(yes: bool) -> None:
    """Clear all stored metrics."""
    if not yes and not click.confirm("Clear all stored metrics?"):
        raise SystemExit(0)

    storage = MetricsStorage()
    storage.clear()
    console.print("[green]Metrics cleared[/]")


def _format_bytes(size: int | None) -> str:
    """Format bytes as human-readable string."""
    if size is None:
        return "-"

    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size = int(size / 1024)
    return f"{size:.1f} TB"
