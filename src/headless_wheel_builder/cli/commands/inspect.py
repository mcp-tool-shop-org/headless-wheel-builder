"""Inspect command implementation for Headless Wheel Builder CLI.

This module handles the 'inspect' command which analyzes Python projects
and displays their metadata and structure.
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from headless_wheel_builder.core.analyzer import ProjectAnalyzer
from headless_wheel_builder.exceptions import HWBError

console = Console()
error_console = Console(stderr=True)


async def execute_inspect(
    source: str,
    output_format: str,
    check: bool,
) -> None:
    """Execute the inspect operation.

    Args:
        source: Source directory to inspect
        output_format: Output format (text, json, table)
        check: Only check for errors, don't print metadata
    """
    source_path = Path(source).resolve()

    if not source_path.exists():
        raise click.BadParameter(f"Source directory not found: {source}")

    if not source_path.is_dir():
        raise click.BadParameter(f"Source is not a directory: {source}")

    # Analyze project
    analyzer = ProjectAnalyzer(source_path)
    metadata = await analyzer.analyze()

    if check:
        # Just verify structure is valid
        if metadata.errors:
            error_console.print(
                Panel(
                    "Project has configuration errors:\n"
                    + "\n".join(f"  • {e}" for e in metadata.errors),
                    style="red",
                    title="✗ Validation Failed",
                )
            )
            raise SystemExit(1)
        else:
            console.print("[green]✓ Project structure valid[/green]")
            return

    # Print results based on format
    if output_format == "json":
        import json

        data = {
            "name": metadata.name,
            "version": metadata.version,
            "python_requires": metadata.python_requires,
            "dependencies": metadata.dependencies,
            "optional_dependencies": metadata.optional_dependencies,
            "has_py_typed": metadata.has_py_typed,
            "has_tests": metadata.has_tests,
            "errors": metadata.errors,
        }
        console.print_json(data=data)
    elif output_format == "table":
        _print_inspect_table(metadata, source_path)
    else:  # text
        _print_inspect_text(metadata, source_path)


def _print_inspect_text(metadata, source_path: Path) -> None:
    """Print inspection results in text format.

    Args:
        metadata: Project metadata
        source_path: Source directory path
    """
    console.print(f"\n[bold cyan]Project: {metadata.name}[/bold cyan]")
    console.print(f"Version: {metadata.version}")
    console.print(f"Location: {source_path}")

    if metadata.python_requires:
        console.print(f"Python: {metadata.python_requires}")

    if metadata.dependencies:
        console.print("\n[bold]Dependencies:[/bold]")
        for dep in metadata.dependencies:
            console.print(f"  • {dep}")

    if metadata.optional_dependencies:
        console.print("\n[bold]Optional Dependencies:[/bold]")
        for extra, deps in metadata.optional_dependencies.items():
            console.print(f"  [{extra}]")
            for dep in deps:
                console.print(f"    • {dep}")

    if metadata.errors:
        error_console.print("\n[bold red]Issues:[/bold red]")
        for error in metadata.errors:
            error_console.print(f"  ✗ {error}")
    else:
        console.print("\n[green]✓ No configuration issues detected[/green]")


def _print_inspect_table(metadata, source_path: Path) -> None:
    """Print inspection results in table format.

    Args:
        metadata: Project metadata
        source_path: Source directory path
    """
    table = Table(title="Project Inspection", show_header=True, header_style="bold cyan")
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Name", metadata.name or "[dim]Unknown[/dim]")
    table.add_row("Version", metadata.version or "[dim]Unknown[/dim]")
    table.add_row("Location", str(source_path))
    table.add_row("Python Version", metadata.python_requires or "[dim]Any[/dim]")
    table.add_row(
        "Dependencies",
        str(len(metadata.dependencies)) if metadata.dependencies else "0",
    )
    table.add_row(
        "Type Hints",
        "[green]Yes[/green]" if metadata.has_py_typed else "[dim]No[/dim]",
    )
    table.add_row(
        "Tests", "[green]Yes[/green]" if metadata.has_tests else "[dim]No[/dim]"
    )

    console.print(table)

    if metadata.errors:
        error_console.print("\n[bold red]Configuration Issues:[/bold red]")
        for error in metadata.errors:
            error_console.print(f"  ✗ {error}")
