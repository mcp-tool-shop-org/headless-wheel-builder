"""CLI for multi-repository operations."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

import click
from rich.console import Console
from rich.table import Table

from headless_wheel_builder.multirepo.config import (
    MultiRepoConfig,
    RepoConfig,
    load_config,
    save_config,
)
from headless_wheel_builder.multirepo.manager import BatchResult, MultiRepoManager

if TYPE_CHECKING:
    from collections.abc import Coroutine

console = Console()
error_console = Console(stderr=True)

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run async function."""
    return asyncio.run(coro)


@click.group(name="multirepo")
def multirepo() -> None:
    """Multi-repository operations.

    Manage and build multiple repositories with dependency resolution.
    """
    pass


@multirepo.command("init")
@click.option("--name", default="default", help="Configuration name")
@click.option("--output", "-o", default="hwb-repos.json", help="Output file")
@click.option("--parallel", default=4, help="Max parallel operations")
def init_config(name: str, output: str, parallel: int) -> None:
    """Initialize a new multi-repo configuration file.

    Creates a sample configuration with example repositories.
    """
    config = MultiRepoConfig(
        name=name,
        parallel=parallel,
        repos=[
            RepoConfig(
                name="example/repo1",
                path="./repos/repo1",
                url="https://github.com/example/repo1",
                tags=["core"],
            ),
            RepoConfig(
                name="example/repo2",
                path="./repos/repo2",
                url="https://github.com/example/repo2",
                dependencies=["example/repo1"],
                tags=["extension"],
            ),
        ],
    )

    output_path = Path(output)
    if output_path.exists() and not click.confirm(f"{output} already exists. Overwrite?"):
        raise SystemExit(1)

    save_config(config, output_path)
    console.print(f"[green]Created configuration file:[/] {output}")
    console.print("\nEdit this file to add your repositories.")


@multirepo.command("add")
@click.argument("repo_name")
@click.option("--config", "-c", default="hwb-repos.json", help="Configuration file")
@click.option("--path", "-p", help="Local path to repository")
@click.option("--url", "-u", help="Git URL for cloning")
@click.option("--branch", default="main", help="Default branch")
@click.option("--python", "python_version", default="3.12", help="Python version")
@click.option("--depends-on", multiple=True, help="Dependencies (can be used multiple times)")
@click.option("--tag", multiple=True, help="Tags (can be used multiple times)")
def add_repo(
    repo_name: str,
    config: str,
    path: str | None,
    url: str | None,
    branch: str,
    python_version: str,
    depends_on: tuple[str, ...],
    tag: tuple[str, ...],
) -> None:
    """Add a repository to the configuration.

    REPO_NAME should be in the format owner/repo.
    """
    config_path = Path(config)

    multi_config = load_config(config_path) if config_path.exists() else MultiRepoConfig()

    repo = RepoConfig(
        name=repo_name,
        path=path,
        url=url or f"https://github.com/{repo_name}",
        branch=branch,
        python_version=python_version,
        dependencies=list(depends_on),
        tags=list(tag),
    )

    multi_config.add_repo(repo)
    save_config(multi_config, config_path)

    console.print(f"[green]Added repository:[/] {repo_name}")


@multirepo.command("remove")
@click.argument("repo_name")
@click.option("--config", "-c", default="hwb-repos.json", help="Configuration file")
def remove_repo(repo_name: str, config: str) -> None:
    """Remove a repository from the configuration."""
    config_path = Path(config)

    if not config_path.exists():
        error_console.print(f"[red]Configuration file not found:[/] {config}")
        sys.exit(1)

    multi_config = load_config(config_path)

    if multi_config.remove_repo(repo_name):
        save_config(multi_config, config_path)
        console.print(f"[green]Removed repository:[/] {repo_name}")
    else:
        error_console.print(f"[yellow]Repository not found:[/] {repo_name}")
        sys.exit(1)


@multirepo.command("list")
@click.option("--config", "-c", default="hwb-repos.json", help="Configuration file")
@click.option("--tag", help="Filter by tag")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def list_repos(config: str, tag: str | None, json_output: bool) -> None:
    """List repositories in the configuration."""
    config_path = Path(config)

    if not config_path.exists():
        error_console.print(f"[red]Configuration file not found:[/] {config}")
        sys.exit(1)

    multi_config = load_config(config_path)

    repos = multi_config.get_repos_by_tag(tag) if tag else multi_config.repos

    if json_output:
        output = [r.to_dict() for r in repos]
        click.echo(json.dumps(output, indent=2))
        return

    table = Table(title=f"Repositories ({multi_config.name})")
    table.add_column("Name", style="cyan")
    table.add_column("Path")
    table.add_column("Python")
    table.add_column("Dependencies")
    table.add_column("Tags")
    table.add_column("Enabled")

    for repo in repos:
        deps = ", ".join(repo.dependencies) if repo.dependencies else "-"
        tags = ", ".join(repo.tags) if repo.tags else "-"
        enabled = "[green]Yes[/]" if repo.enabled else "[red]No[/]"

        table.add_row(
            repo.name,
            repo.path or repo.url or "-",
            repo.python_version,
            deps,
            tags,
            enabled,
        )

    console.print(table)


@multirepo.command("order")
@click.option("--config", "-c", default="hwb-repos.json", help="Configuration file")
def show_order(config: str) -> None:
    """Show the build order respecting dependencies."""
    config_path = Path(config)

    if not config_path.exists():
        error_console.print(f"[red]Configuration file not found:[/] {config}")
        sys.exit(1)

    multi_config = load_config(config_path)
    manager = MultiRepoManager(multi_config)

    ordered = manager.get_build_order()

    console.print("[bold]Build Order:[/]\n")
    for i, repo in enumerate(ordered, 1):
        deps_str = ""
        if repo.dependencies:
            deps_str = f" [dim](depends on: {', '.join(repo.dependencies)})[/]"
        console.print(f"  {i}. {repo.name}{deps_str}")


@multirepo.command("build")
@click.option("--config", "-c", default="hwb-repos.json", help="Configuration file")
@click.option("--repo", "-r", multiple=True, help="Specific repos to build")
@click.option("--tag", "-t", help="Build repos with tag")
@click.option("--parallel/--no-parallel", default=True, help="Build in parallel")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def build_all(
    config: str,
    repo: tuple[str, ...],
    tag: str | None,
    parallel: bool,
    json_output: bool,
) -> None:
    """Build all repositories.

    Respects dependency order and supports parallel execution.
    """
    config_path = Path(config)

    if not config_path.exists():
        error_console.print(f"[red]Configuration file not found:[/] {config}")
        sys.exit(1)

    multi_config = load_config(config_path)
    manager = MultiRepoManager(multi_config)

    # Determine which repos to build
    repos_to_build: list[RepoConfig] | None = None
    if repo:
        repos_to_build = [r for r in multi_config.repos if r.name in repo]
    elif tag:
        repos_to_build = multi_config.get_repos_by_tag(tag)

    async def _build():
        return await manager.build_all(repos=repos_to_build, parallel=parallel)

    if not json_output:
        console.print("\n[bold blue]Building repositories...[/]")
        if repos_to_build:
            console.print(f"  Repos: {len(repos_to_build)}")
        console.print(f"  Parallel: {parallel}")
        console.print()

    result = run_async(_build())

    if json_output:
        click.echo(json.dumps(result.to_dict(), indent=2))
    else:
        _print_batch_result(result)

    sys.exit(0 if result.success else 1)


@multirepo.command("sync")
@click.option("--config", "-c", default="hwb-repos.json", help="Configuration file")
@click.option("--repo", "-r", multiple=True, help="Specific repos to sync")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def sync_all(config: str, repo: tuple[str, ...], json_output: bool) -> None:
    """Sync all repositories (clone/pull)."""
    config_path = Path(config)

    if not config_path.exists():
        error_console.print(f"[red]Configuration file not found:[/] {config}")
        sys.exit(1)

    multi_config = load_config(config_path)
    manager = MultiRepoManager(multi_config)

    repos_to_sync: list[RepoConfig] | None = None
    if repo:
        repos_to_sync = [r for r in multi_config.repos if r.name in repo]

    async def _sync():
        return await manager.sync_all(repos=repos_to_sync)

    if not json_output:
        console.print("\n[bold blue]Syncing repositories...[/]")
        console.print()

    result = run_async(_sync())

    if json_output:
        click.echo(json.dumps(result.to_dict(), indent=2))
    else:
        _print_batch_result(result)

    sys.exit(0 if result.success else 1)


def _print_batch_result(result: BatchResult) -> None:
    """Print batch operation result."""
    table = Table(title="Results")
    table.add_column("Repository", style="cyan")
    table.add_column("Status")
    table.add_column("Duration")
    table.add_column("Message")

    for repo_result in result.results:
        status = "[green]Success[/]" if repo_result.success else "[red]Failed[/]"

        duration = f"{repo_result.duration_seconds:.1f}s"
        message = repo_result.message
        if repo_result.error:
            message = f"[red]{repo_result.error}[/]"

        table.add_row(
            repo_result.repo.name,
            status,
            duration,
            message,
        )

    console.print(table)

    console.print()
    if result.success:
        console.print(f"[green]All {len(result.succeeded)} repositories completed successfully[/]")
    else:
        console.print(f"[red]{len(result.failed)} failed[/], {len(result.succeeded)} succeeded")

    console.print(f"Total time: {result.total_duration_seconds:.1f}s")
