"""CLI for dependency graph analysis."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from headless_wheel_builder.depgraph.analyzer import DependencyAnalyzer
from headless_wheel_builder.depgraph.models import LicenseCategory

if TYPE_CHECKING:
    from collections.abc import Coroutine

console = Console()
error_console = Console(stderr=True)

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine."""
    return asyncio.run(coro)


@click.group(name="deps")
def deps() -> None:
    """Dependency graph analysis.

    Analyze package dependencies, detect conflicts, and check licenses.
    """
    pass


@deps.command("tree")
@click.argument("package")
@click.option("--version", "-v", help="Specific version")
@click.option("--depth", "-d", default=3, help="Maximum depth")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def show_tree(
    package: str,
    version: str | None,
    depth: int,
    json_output: bool,
) -> None:
    """Show dependency tree for a package."""

    async def _analyze():
        analyzer = DependencyAnalyzer(max_depth=depth)
        try:
            return await analyzer.build_graph(package, version)
        finally:
            await analyzer.close()

    graph = run_async(_analyze())

    if json_output:
        click.echo(json.dumps(graph.to_dict(), indent=2))
        return

    # Build rich tree
    root_node = graph.nodes.get(package)
    version_str = f"=={root_node.version}" if root_node and root_node.version else ""
    tree = Tree(f"[bold cyan]{package}[/]{version_str}")

    def add_children(tree_node: Tree, pkg_name: str, visited: set[str]) -> None:
        if pkg_name in visited:
            return
        visited.add(pkg_name)

        for dep in graph.edges.get(pkg_name, []):
            dep_node = graph.nodes.get(dep)
            dep_version = f"=={dep_node.version}" if dep_node and dep_node.version else ""

            # Add license indicator
            license_indicator = ""
            if dep_node and dep_node.license_info:
                if dep_node.license_info.category == LicenseCategory.COPYLEFT:
                    license_indicator = " [red](GPL)[/]"
                elif dep_node.license_info.category == LicenseCategory.UNKNOWN:
                    license_indicator = " [yellow](?)[/]"

            child: Tree = tree_node.add(f"{dep}{dep_version}{license_indicator}")
            add_children(child, dep, visited.copy())

    add_children(tree, package, set())

    console.print()
    console.print(tree)
    console.print()

    # Show summary
    console.print(f"[dim]Total packages: {len(graph.nodes)}[/]")
    if graph.cycles:
        console.print(f"[red]Circular dependencies: {len(graph.cycles)}[/]")
    if graph.conflicts:
        console.print(f"[yellow]Version conflicts: {len(graph.conflicts)}[/]")


@deps.command("analyze")
@click.argument("path", type=click.Path(exists=True, path_type=Path), default=".")
@click.option("--depth", "-d", default=3, help="Maximum depth")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def analyze_local(
    path: Path,
    depth: int,
    json_output: bool,
) -> None:
    """Analyze dependencies of a local project."""

    async def _analyze():
        analyzer = DependencyAnalyzer(max_depth=depth)
        try:
            return await analyzer.analyze_local(path)
        finally:
            await analyzer.close()

    try:
        graph = run_async(_analyze())
    except ValueError as e:
        error_console.print(f"[red]Error:[/] {e}")
        sys.exit(1)

    if json_output:
        click.echo(json.dumps(graph.to_dict(), indent=2))
        return

    console.print()
    console.print(
        Panel(
            f"[bold]Project:[/] {graph.root}\n"
            f"[bold]Dependencies:[/] {len(graph.nodes) - 1}\n"
            f"[bold]Direct:[/] {len(graph.edges.get(graph.root, []))}\n"
            f"[bold]Transitive:[/] {len(graph.nodes) - 1 - len(graph.edges.get(graph.root, []))}",
            title="Dependency Analysis",
            border_style="blue",
        )
    )

    # Show build order
    if graph.build_order:
        console.print("\n[bold]Build Order:[/]")
        for i, pkg in enumerate(graph.build_order[:10], 1):
            node = graph.nodes.get(pkg)
            version = f" ({node.version})" if node and node.version else ""
            console.print(f"  {i}. {pkg}{version}")
        if len(graph.build_order) > 10:
            console.print(f"  ... and {len(graph.build_order) - 10} more")

    # Show issues
    if graph.cycles:
        console.print("\n[bold red]Circular Dependencies:[/]")
        for cycle in graph.cycles[:5]:
            console.print(f"  • {' -> '.join(cycle)}")

    if graph.conflicts:
        console.print("\n[bold yellow]Version Conflicts:[/]")
        for conflict in graph.conflicts[:5]:
            console.print(f"  • {conflict.package}: {conflict.message}")

    if graph.license_issues:
        console.print("\n[bold yellow]License Issues:[/]")
        for issue in graph.license_issues[:5]:
            console.print(f"  • {issue}")

    console.print()


@deps.command("licenses")
@click.argument("package_or_path")
@click.option("--check", "-c", multiple=True, help="Check for specific licenses (fail if found)")
@click.option("--allow", "-a", multiple=True, help="Allow only specific licenses")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def check_licenses(
    package_or_path: str,
    check: tuple[str, ...],
    allow: tuple[str, ...],
    json_output: bool,
) -> None:
    """Check licenses of dependencies."""

    async def _analyze():
        analyzer = DependencyAnalyzer(max_depth=5)
        try:
            path = Path(package_or_path)
            if path.exists():
                return await analyzer.analyze_local(path)
            else:
                return await analyzer.build_graph(package_or_path)
        finally:
            await analyzer.close()

    try:
        graph = run_async(_analyze())
    except ValueError as e:
        error_console.print(f"[red]Error:[/] {e}")
        sys.exit(1)

    # Collect licenses
    licenses: dict[str, list[str]] = {}
    for name, node in graph.nodes.items():
        if node.license_info:
            license_name = node.license_info.name
            if license_name not in licenses:
                licenses[license_name] = []
            licenses[license_name].append(name)
        else:
            if "Unknown" not in licenses:
                licenses["Unknown"] = []
            licenses["Unknown"].append(name)

    if json_output:
        click.echo(
            json.dumps(
                {
                    "licenses": licenses,
                    "issues": graph.license_issues,
                },
                indent=2,
            )
        )
        return

    # Display licenses
    table = Table(title="Dependency Licenses")
    table.add_column("License", style="cyan")
    table.add_column("Category")
    table.add_column("Packages", justify="right")

    for license_name, packages in sorted(licenses.items(), key=lambda x: -len(x[1])):
        # Determine category color
        from headless_wheel_builder.depgraph.models import categorize_license

        category = categorize_license(license_name)

        if category == LicenseCategory.PERMISSIVE:
            cat_style = "green"
        elif category == LicenseCategory.COPYLEFT:
            cat_style = "red"
        elif category == LicenseCategory.WEAK_COPYLEFT:
            cat_style = "yellow"
        else:
            cat_style = "dim"

        table.add_row(
            license_name or "Unknown",
            f"[{cat_style}]{category.value}[/]",
            str(len(packages)),
        )

    console.print(table)

    # Check for violations
    exit_code = 0

    if check:
        for license_to_check in check:
            if license_to_check in licenses:
                error_console.print(f"[red]Found forbidden license:[/] {license_to_check}")
                for pkg in licenses[license_to_check]:
                    error_console.print(f"  • {pkg}")
                exit_code = 1

    if allow:
        allowed_set = set(allow)
        for license_name, packages in licenses.items():
            if license_name not in allowed_set and license_name != "Unknown":
                error_console.print(f"[red]Found non-allowed license:[/] {license_name}")
                for pkg in packages:
                    error_console.print(f"  • {pkg}")
                exit_code = 1

    if exit_code != 0:
        sys.exit(exit_code)


@deps.command("conflicts")
@click.argument("package_or_path")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def show_conflicts(
    package_or_path: str,
    json_output: bool,
) -> None:
    """Show version conflicts in dependencies."""

    async def _analyze():
        analyzer = DependencyAnalyzer(max_depth=5)
        try:
            path = Path(package_or_path)
            if path.exists():
                return await analyzer.analyze_local(path)
            else:
                return await analyzer.build_graph(package_or_path)
        finally:
            await analyzer.close()

    try:
        graph = run_async(_analyze())
    except ValueError as e:
        error_console.print(f"[red]Error:[/] {e}")
        sys.exit(1)

    if json_output:
        click.echo(json.dumps([c.to_dict() for c in graph.conflicts], indent=2))
        return

    if not graph.conflicts:
        console.print("[green]No version conflicts detected[/]")
        return

    console.print()
    console.print(f"[bold red]Found {len(graph.conflicts)} version conflict(s):[/]")
    console.print()

    for conflict in graph.conflicts:
        console.print(f"[bold]{conflict.package}[/]")
        console.print(f"  {conflict.message}")
        for source, version in conflict.required_versions.items():
            console.print(f"    • {source} requires {version}")
        console.print()

    sys.exit(1 if graph.conflicts else 0)


@deps.command("cycles")
@click.argument("package_or_path")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def show_cycles(
    package_or_path: str,
    json_output: bool,
) -> None:
    """Show circular dependencies."""

    async def _analyze():
        analyzer = DependencyAnalyzer(max_depth=10)
        try:
            path = Path(package_or_path)
            if path.exists():
                return await analyzer.analyze_local(path)
            else:
                return await analyzer.build_graph(package_or_path)
        finally:
            await analyzer.close()

    try:
        graph = run_async(_analyze())
    except ValueError as e:
        error_console.print(f"[red]Error:[/] {e}")
        sys.exit(1)

    if json_output:
        click.echo(json.dumps({"cycles": graph.cycles}, indent=2))
        return

    if not graph.cycles:
        console.print("[green]No circular dependencies detected[/]")
        return

    console.print()
    console.print(f"[bold red]Found {len(graph.cycles)} circular dependency chain(s):[/]")
    console.print()

    for cycle in graph.cycles:
        console.print(f"  {' -> '.join(cycle)}")

    console.print()
    sys.exit(1 if graph.cycles else 0)


@deps.command("order")
@click.argument("package_or_path")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def show_build_order(
    package_or_path: str,
    json_output: bool,
) -> None:
    """Show optimal build order for dependencies."""

    async def _analyze():
        analyzer = DependencyAnalyzer(max_depth=5)
        try:
            path = Path(package_or_path)
            if path.exists():
                return await analyzer.analyze_local(path)
            else:
                return await analyzer.build_graph(package_or_path)
        finally:
            await analyzer.close()

    try:
        graph = run_async(_analyze())
    except ValueError as e:
        error_console.print(f"[red]Error:[/] {e}")
        sys.exit(1)

    if json_output:
        click.echo(json.dumps({"build_order": graph.build_order}, indent=2))
        return

    console.print()
    console.print("[bold]Build Order[/] (dependencies first):")
    console.print()

    for i, pkg in enumerate(graph.build_order, 1):
        node = graph.nodes.get(pkg)
        version = f" ({node.version})" if node and node.version else ""
        console.print(f"  {i:3}. {pkg}{version}")

    console.print()
