"""CLI for artifact cache management."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from headless_wheel_builder.cache.storage import ArtifactCache

console = Console()
error_console = Console(stderr=True)


@click.group(name="cache")
def cache() -> None:
    """Artifact cache management.

    Manage cached wheels and registry integration.
    """
    pass


@cache.command("stats")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def show_stats(json_output: bool) -> None:
    """Show cache statistics."""
    artifact_cache = ArtifactCache()
    stats = artifact_cache.get_stats()

    if json_output:
        click.echo(json.dumps(stats.to_dict(), indent=2))
        return

    console.print()
    console.print(
        Panel(
            f"[bold]Entries:[/] {stats.total_entries}\n"
            f"[bold]Packages:[/] {stats.packages}\n"
            f"[bold]Total Size:[/] {_format_bytes(stats.total_size_bytes)}\n"
            f"[bold]Hit Rate:[/] {stats.hit_rate:.1%}\n"
            f"[bold]Hits:[/] [green]{stats.hits}[/]\n"
            f"[bold]Misses:[/] [yellow]{stats.misses}[/]",
            title="Cache Statistics",
            border_style="blue",
        )
    )
    console.print()


@cache.command("list")
@click.option("--package", "-p", help="Filter by package")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def list_entries(package: str | None, json_output: bool) -> None:
    """List cached wheels."""
    artifact_cache = ArtifactCache()
    entries = artifact_cache.list_entries(package=package)

    if json_output:
        click.echo(json.dumps([e.to_dict() for e in entries], indent=2))
        return

    if not entries:
        console.print("[yellow]No cached wheels found[/]")
        return

    table = Table(title=f"Cached Wheels ({len(entries)})")
    table.add_column("Package", style="cyan")
    table.add_column("Version")
    table.add_column("Size", justify="right")
    table.add_column("Accessed")
    table.add_column("Source")

    for entry in entries:
        accessed = entry.last_accessed[:10] if entry.last_accessed else "-"
        table.add_row(
            entry.package,
            entry.version,
            _format_bytes(entry.size_bytes),
            accessed,
            entry.source,
        )

    console.print(table)


@cache.command("packages")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def list_packages(json_output: bool) -> None:
    """List cached packages."""
    artifact_cache = ArtifactCache()
    packages = artifact_cache.list_packages()

    if json_output:
        click.echo(json.dumps(packages, indent=2))
        return

    if not packages:
        console.print("[yellow]No packages in cache[/]")
        return

    console.print("\n[bold]Cached Packages:[/]\n")
    for pkg in sorted(packages):
        versions = artifact_cache.list_versions(pkg)
        console.print(f"  {pkg}: {', '.join(sorted(versions))}")
    console.print()


@cache.command("get")
@click.argument("package")
@click.argument("version")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output directory")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def get_wheel(
    package: str,
    version: str,
    output: Path | None,
    json_output: bool,
) -> None:
    """Get a wheel from cache.

    If found, copies to output directory (default: current directory).
    """
    artifact_cache = ArtifactCache()
    result = artifact_cache.get(package, version)

    if result is None:
        if json_output:
            click.echo(json.dumps({"found": False}))
        else:
            error_console.print(f"[red]Not found:[/] {package} {version}")
        sys.exit(1)

    entry, _wheel_path = result
    dest_dir = output or Path.cwd()
    dest_path = artifact_cache.copy_to(entry, dest_dir)

    if json_output:
        click.echo(
            json.dumps(
                {
                    "found": True,
                    "path": str(dest_path),
                    "entry": entry.to_dict(),
                },
                indent=2,
            )
        )
    else:
        console.print(f"[green]Copied to:[/] {dest_path}")


@cache.command("add")
@click.argument("wheel_path", type=click.Path(exists=True, path_type=Path))
@click.option("--package", "-p", help="Package name (auto-detected if not specified)")
@click.option("--version", "-v", help="Package version (auto-detected if not specified)")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def add_wheel(
    wheel_path: Path,
    package: str | None,
    version: str | None,
    json_output: bool,
) -> None:
    """Add a wheel to the cache."""
    artifact_cache = ArtifactCache()

    # Parse package and version from wheel name if not provided
    if not package or not version:
        # Wheel format: {package}-{version}-{python}-{abi}-{platform}.whl
        parts = wheel_path.stem.split("-")
        if len(parts) >= 2:
            if not package:
                package = parts[0]
            if not version:
                version = parts[1]

    if not package or not version:
        error_console.print("[red]Could not determine package/version from wheel name[/]")
        error_console.print("Please specify --package and --version")
        sys.exit(1)

    entry = artifact_cache.add(
        wheel_path=wheel_path,
        package=package,
        version=version,
    )

    if json_output:
        click.echo(json.dumps(entry.to_dict(), indent=2))
    else:
        console.print(f"[green]Added to cache:[/] {entry.wheel_name}")
        console.print(f"  SHA256: {entry.sha256[:16]}...")


@cache.command("remove")
@click.argument("package")
@click.argument("version")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def remove_wheel(package: str, version: str, yes: bool) -> None:
    """Remove a package version from cache."""
    artifact_cache = ArtifactCache()

    if not artifact_cache.contains(package, version):
        error_console.print(f"[yellow]Not in cache:[/] {package} {version}")
        return

    if not yes and not click.confirm(f"Remove {package} {version} from cache?"):
        return

    count = artifact_cache.remove(package, version)
    console.print(f"[green]Removed {count} entries[/]")


@cache.command("clear")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def clear_cache(yes: bool) -> None:
    """Clear entire cache."""
    artifact_cache = ArtifactCache()
    stats = artifact_cache.get_stats()

    if stats.total_entries == 0:
        console.print("[yellow]Cache is already empty[/]")
        return

    if not yes:
        size_str = _format_bytes(stats.total_size_bytes)
        if not click.confirm(f"Clear cache? ({stats.total_entries} entries, {size_str})"):
            return

    artifact_cache.clear()
    console.print("[green]Cache cleared[/]")


@cache.command("prune")
@click.option("--max-size", "-s", help="Maximum cache size (e.g., 1G, 500M)")
@click.option("--max-age", "-a", help="Maximum entry age (e.g., 30d, 1w)")
@click.option("--dry-run", is_flag=True, help="Show what would be pruned")
def prune_cache(
    max_size: str | None,
    max_age: str | None,
    dry_run: bool,
) -> None:
    """Prune old or excess entries from cache."""
    artifact_cache = ArtifactCache()

    if not max_size and not max_age:
        console.print("[yellow]Specify --max-size or --max-age[/]")
        return

    entries_before = len(artifact_cache.list_entries())

    if max_size:
        size_bytes = _parse_size(max_size)
        if size_bytes is None:
            error_console.print(f"[red]Invalid size:[/] {max_size}")
            sys.exit(1)

        if dry_run:
            current_size = artifact_cache.get_stats().total_size_bytes
            if current_size > size_bytes:
                console.print(
                    f"Would prune to reduce size from "
                    f"{_format_bytes(current_size)} to {_format_bytes(size_bytes)}"
                )
        else:
            artifact_cache.prune_to_size(size_bytes)

    if max_age:
        # TODO: Implement age-based pruning
        console.print("[yellow]Age-based pruning not yet implemented[/]")

    if not dry_run:
        entries_after = len(artifact_cache.list_entries())
        pruned = entries_before - entries_after
        console.print(f"[green]Pruned {pruned} entries[/]")


@cache.command("info")
@click.argument("package")
@click.argument("version")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def show_info(package: str, version: str, json_output: bool) -> None:
    """Show detailed info about a cached wheel."""
    artifact_cache = ArtifactCache()
    result = artifact_cache.get(package, version)

    if result is None:
        if json_output:
            click.echo(json.dumps({"found": False}))
        else:
            error_console.print(f"[red]Not found:[/] {package} {version}")
        sys.exit(1)

    entry, cache_path = result

    if json_output:
        data = entry.to_dict()
        data["cache_path"] = str(cache_path)
        click.echo(json.dumps(data, indent=2))
        return

    console.print()
    console.print(
        Panel(
            f"[bold]Package:[/] {entry.package}\n"
            f"[bold]Version:[/] {entry.version}\n"
            f"[bold]Wheel:[/] {entry.wheel_name}\n"
            f"[bold]Size:[/] {_format_bytes(entry.size_bytes)}\n"
            f"[bold]SHA256:[/] {entry.sha256}\n"
            f"[bold]Python:[/] {entry.python_version or 'any'}\n"
            f"[bold]Platform:[/] {entry.platform or 'any'}\n"
            f"[bold]Source:[/] {entry.source}\n"
            f"[bold]Created:[/] {entry.created_at or '-'}\n"
            f"[bold]Accessed:[/] {entry.last_accessed or '-'}\n"
            f"[bold]Access Count:[/] {entry.access_count}",
            title="Cache Entry",
            border_style="blue",
        )
    )
    console.print()


def _format_bytes(size: int) -> str:
    """Format bytes as human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size = int(size / 1024)
    return f"{size:.1f} TB"


def _parse_size(size_str: str) -> int | None:
    """Parse size string to bytes."""
    size_str = size_str.strip().upper()

    units = {
        "B": 1,
        "K": 1024,
        "KB": 1024,
        "M": 1024 * 1024,
        "MB": 1024 * 1024,
        "G": 1024 * 1024 * 1024,
        "GB": 1024 * 1024 * 1024,
    }

    for unit, multiplier in units.items():
        if size_str.endswith(unit):
            try:
                value = float(size_str[: -len(unit)])
                return int(value * multiplier)
            except ValueError:
                return None

    # Try as plain number
    try:
        return int(size_str)
    except ValueError:
        return None
