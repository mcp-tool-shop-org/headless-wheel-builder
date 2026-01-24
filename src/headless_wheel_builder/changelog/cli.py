"""CLI commands for changelog generation."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from headless_wheel_builder.changelog.generator import (
    ChangelogConfig,
    ChangelogFormat,
    generate_changelog,
)

console = Console()


@click.group("changelog")
def changelog() -> None:
    """Changelog generation from git commits.

    Generate changelogs following Conventional Commits specification.
    """
    pass


@changelog.command("generate")
@click.option("--from", "from_ref", help="Starting ref (tag or commit). Auto-detects if not set.")
@click.option("--to", "to_ref", default="HEAD", help="Ending ref (default: HEAD)")
@click.option("--tag", "-t", help="Release tag for header")
@click.option("--repo", "-r", "repo_path", default=".", help="Repository path")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["markdown", "plain", "github", "json"]),
    default="markdown",
    help="Output format",
)
@click.option("--all", "include_all", is_flag=True, help="Include all commits (not just notable)")
@click.option("--no-group", is_flag=True, help="Don't group by commit type")
@click.option("--no-sha", is_flag=True, help="Don't show commit SHAs")
@click.option("--no-scope", is_flag=True, help="Don't show scopes")
@click.option("--output", "-o", type=click.Path(), help="Output file (stdout if not set)")
def generate_cmd(
    from_ref: str | None,
    to_ref: str,
    tag: str | None,
    repo_path: str,
    output_format: str,
    include_all: bool,
    no_group: bool,
    no_sha: bool,
    no_scope: bool,
    output: str | None,
) -> None:
    """Generate changelog from git commits.

    Examples:
        hwb changelog generate --tag v1.0.0
        hwb changelog generate --from v0.9.0 --to v1.0.0 --format github
        hwb changelog generate --all --format json -o CHANGELOG.json
    """
    format_map = {
        "markdown": ChangelogFormat.MARKDOWN,
        "plain": ChangelogFormat.PLAIN,
        "github": ChangelogFormat.GITHUB,
        "json": ChangelogFormat.JSON,
    }

    config = ChangelogConfig(
        repo_path=repo_path,
        from_ref=from_ref,
        to_ref=to_ref,
        tag=tag,
        include_all=include_all,
        group_by_type=not no_group,
        show_sha=not no_sha,
        show_scope=not no_scope,
        format=format_map.get(output_format, ChangelogFormat.MARKDOWN),
    )

    try:
        log = generate_changelog(config)
        content = log.render()

        if output:
            Path(output).write_text(content, encoding="utf-8")
            console.print(f"[green]Changelog written to {output}[/green]")
            console.print(
                f"  {len(log.commits)} commits, {len(log.breaking_changes)} breaking changes"
            )
        else:
            console.print(content)

    except Exception as e:
        console.print(f"[red]Error generating changelog:[/red] {e}")
        sys.exit(1)


@changelog.command("preview")
@click.option("--from", "from_ref", help="Starting ref")
@click.option("--to", "to_ref", default="HEAD", help="Ending ref")
@click.option("--repo", "-r", "repo_path", default=".", help="Repository path")
def preview_cmd(
    from_ref: str | None,
    to_ref: str,
    repo_path: str,
) -> None:
    """Preview commits that would be included in changelog."""
    config = ChangelogConfig(
        repo_path=repo_path,
        from_ref=from_ref,
        to_ref=to_ref,
        include_all=True,
    )

    try:
        log = generate_changelog(config)

        if not log.commits:
            console.print("[yellow]No commits found[/yellow]")
            return

        # Summary
        console.print(
            Panel(
                f"[bold]{len(log.commits)}[/bold] commits found\n"
                f"[bold]{len(log.breaking_changes)}[/bold] breaking changes\n"
                f"From: {from_ref or '(auto-detected)'}\n"
                f"To: {to_ref}",
                title="Changelog Preview",
            )
        )

        console.print()

        # Breaking changes
        if log.breaking_changes:
            console.print("[bold red]Breaking Changes:[/bold red]")
            for commit in log.breaking_changes:
                console.print(f"  ⚠️  {commit.summary}")
            console.print()

        # By type
        for commit_type, entries in log.entries_by_type.items():
            header = config.sections.get(commit_type, commit_type.value)
            console.print(f"[bold]{header}[/bold] ({len(entries)})")
            for entry in entries[:5]:  # Show first 5
                console.print(f"  • {entry.formatted}")
            if len(entries) > 5:
                console.print(f"  ... and {len(entries) - 5} more")
            console.print()

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
