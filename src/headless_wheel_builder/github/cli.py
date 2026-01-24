"""CLI commands for GitHub operations."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from headless_wheel_builder.exceptions import GitHubAuthError, GitHubError, HWBError

if TYPE_CHECKING:
    from collections.abc import Coroutine

    from headless_wheel_builder.github.client import GitHubClient
    from headless_wheel_builder.github.models import (
        Issue,
        PullRequest,
        Release,
        ReleaseResult,
        WorkflowRun,
    )

console = Console()
error_console = Console(stderr=True)

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async function."""
    return asyncio.run(coro)


# =============================================================================
# Result Types for Type Safety
# =============================================================================


@dataclass
class DryRunResult:
    """Result for dry run operations."""

    dry_run: bool
    repo: str
    tag: str
    name: str
    draft: bool
    prerelease: bool
    assets: list[str]


@dataclass
class WorkflowRunResult:
    """Result for workflow run action."""

    workflow: str
    ref: str


@dataclass
class WorkflowListResult:
    """Result for workflow list action."""

    runs: list[WorkflowRun]
    repo: str


@dataclass
class WorkflowStatusResult:
    """Result for workflow status action."""

    run: WorkflowRun


@dataclass
class PRCreateResult:
    """Result for PR create action."""

    pr: PullRequest


@dataclass
class PRListResult:
    """Result for PR list action."""

    prs: list[PullRequest]
    repo: str


@dataclass
class PRViewResult:
    """Result for PR view action."""

    pr: PullRequest


@dataclass
class IssueCreateResult:
    """Result for issue create action."""

    issue: Issue


@dataclass
class IssueListResult:
    """Result for issue list action."""

    issues: list[Issue]
    repo: str


@dataclass
class IssueViewResult:
    """Result for issue view action."""

    issue: Issue


# =============================================================================
# Helper Functions
# =============================================================================


async def _get_client_and_repo(ctx: click.Context) -> tuple[GitHubClient, str]:
    """Get configured client and repository."""
    from headless_wheel_builder.github import GitHubClient, GitHubConfig

    token: str | None = ctx.obj.get("github_token")
    repo_str: str | None = ctx.obj.get("github_repo")

    config = GitHubConfig(token=token)
    client = GitHubClient(config)

    # Auto-detect repo if not specified
    if not repo_str:
        detected = await client.detect_repo()
        if detected:
            repo_str = detected.full_name
        else:
            raise click.UsageError("Could not detect repository. Specify with --repo owner/repo")

    return client, repo_str


def _handle_auth_error(e: GitHubAuthError, json_output: bool) -> None:
    """Handle authentication errors."""
    if json_output:
        click.echo(json.dumps({"success": False, "error": str(e)}))
    else:
        error_console.print(f"\n[bold red]Authentication Error:[/] {e}")
        error_console.print("\nSet GITHUB_TOKEN environment variable or use --token flag.")
        error_console.print("Create a token at: https://github.com/settings/tokens\n")
    sys.exit(1)


def _handle_github_error(e: GitHubError, json_output: bool) -> None:
    """Handle GitHub API errors."""
    if json_output:
        click.echo(json.dumps({"success": False, "error": str(e)}))
    else:
        error_console.print(f"\n[bold red]GitHub Error:[/] {e}")
        if e.status_code:
            error_console.print(f"  Status code: {e.status_code}")
    sys.exit(1)


def _handle_hwb_error(e: HWBError, json_output: bool, verbose: int) -> None:
    """Handle general HWB errors."""
    if json_output:
        click.echo(json.dumps({"success": False, "error": str(e)}))
    else:
        error_console.print(f"\n[bold red]Error:[/] {e}")
        if verbose:
            import traceback

            error_console.print(traceback.format_exc())
    sys.exit(1)


def _print_release_dry_run(result: DryRunResult) -> None:
    """Print dry run release info."""
    console.print()
    console.print(Panel("[yellow]DRY RUN - No release created[/]", border_style="yellow"))
    console.print(f"  Repository: {result.repo}")
    console.print(f"  Tag: {result.tag}")
    console.print(f"  Name: {result.name}")
    if result.draft:
        console.print("  Draft: Yes")
    if result.prerelease:
        console.print("  Prerelease: Yes")
    if result.assets:
        console.print(f"  Assets: {len(result.assets)} files")
        for asset in result.assets:
            console.print(f"    - {asset}")
    console.print()


def _print_release_success(result: ReleaseResult) -> None:
    """Print successful release result."""
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()

    if result.release:
        table.add_row("Tag", f"[bold]{result.release.tag_name}[/]")
        table.add_row("Name", result.release.name or result.release.tag_name)
        table.add_row("URL", result.release.html_url)

        if result.release.draft:
            table.add_row("Status", "[yellow]Draft[/]")
        elif result.release.prerelease:
            table.add_row("Status", "[yellow]Prerelease[/]")
        else:
            table.add_row("Status", "[green]Published[/]")

    if result.assets_uploaded:
        table.add_row("Assets", f"{len(result.assets_uploaded)} uploaded")
        for asset in result.assets_uploaded:
            console.print(f"    [dim]↳[/] {asset.name} ({asset.size / 1024:.1f} KB)")

    console.print(Panel(table, title="[green]Release Created[/]", border_style="green"))
    console.print()


def _print_release_failure(result: ReleaseResult) -> None:
    """Print failed release result."""
    console.print()
    console.print(Panel("[red]Release Failed[/]", border_style="red"))

    for error in result.errors:
        console.print(f"  [red]✗[/] {error}")

    for path, error in result.assets_failed:
        console.print(f"  [red]✗[/] Failed to upload {path.name}: {error}")

    console.print()


# =============================================================================
# CLI Group
# =============================================================================


@click.group("github")
@click.option(
    "--token",
    envvar="GITHUB_TOKEN",
    help="GitHub token (or set GITHUB_TOKEN env var)",
)
@click.option(
    "--repo",
    "-r",
    help="Repository in 'owner/repo' format (auto-detected from git remote)",
)
@click.pass_context
def github(ctx: click.Context, token: str | None, repo: str | None) -> None:
    """GitHub operations - releases, issues, PRs, workflows.

    Commands for headless GitHub automation without the web UI.

    Examples:

        hwb github release v1.0.0                    # Create release

        hwb github release v1.0.0 --assets dist/*   # Release with assets

        hwb github pr create --title "Fix bug"      # Create PR

        hwb github workflow run build.yml           # Trigger workflow
    """
    ctx.ensure_object(dict)
    ctx.obj["github_token"] = token
    ctx.obj["github_repo"] = repo


# =============================================================================
# Release Commands
# =============================================================================


@github.command("release")
@click.argument("tag")
@click.option("--name", "-n", help="Release name (defaults to tag)")
@click.option("--body", "-b", help="Release notes body")
@click.option("--body-file", type=click.Path(exists=True), help="Read body from file")
@click.option("--draft", is_flag=True, help="Create as draft release")
@click.option("--prerelease", is_flag=True, help="Mark as prerelease")
@click.option("--target", help="Target branch or commit SHA")
@click.option("--generate-notes", is_flag=True, help="Auto-generate release notes")
@click.option(
    "--assets",
    "-a",
    multiple=True,
    type=click.Path(exists=True),
    help="Files to upload as release assets",
)
@click.option("--dry-run", is_flag=True, help="Show what would be done without doing it")
@click.pass_context
def release_create(
    ctx: click.Context,
    tag: str,
    name: str | None,
    body: str | None,
    body_file: str | None,
    draft: bool,
    prerelease: bool,
    target: str | None,
    generate_notes: bool,
    assets: tuple[str, ...],
    dry_run: bool,
) -> None:
    """Create a GitHub release.

    Creates a release for TAG and optionally uploads assets.

    Examples:

        hwb github release v1.0.0

        hwb github release v1.0.0 --name "Version 1.0.0"

        hwb github release v1.0.0 --assets dist/*.whl

        hwb github release v1.0.0 --draft --prerelease

        hwb github release v1.0.0 --generate-notes
    """
    verbose: int = ctx.obj.get("verbose", 0)
    json_output: bool = ctx.obj.get("json", False)
    quiet: bool = ctx.obj.get("quiet", False)

    # Read body from file if specified
    body_content = body
    if body_file:
        body_content = Path(body_file).read_text()

    # Expand glob patterns in assets
    asset_paths: list[Path] = []
    for pattern in assets:
        path = Path(pattern)
        if path.exists():
            asset_paths.append(path)

    async def _create_release() -> DryRunResult | ReleaseResult:
        client, repo = await _get_client_and_repo(ctx)

        async with client:
            if dry_run:
                return DryRunResult(
                    dry_run=True,
                    repo=repo,
                    tag=tag,
                    name=name or tag,
                    draft=draft,
                    prerelease=prerelease,
                    assets=[str(p) for p in asset_paths],
                )

            if not quiet and not json_output:
                console.print(f"\n[bold blue]Creating release[/] {tag}")
                console.print(f"  Repository: {repo}")
                if asset_paths:
                    console.print(f"  Assets: {len(asset_paths)} files")
                if draft:
                    console.print("  [yellow]DRAFT[/]")
                if prerelease:
                    console.print("  [yellow]PRERELEASE[/]")
                console.print()

            # Create release with assets
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
                disable=quiet or json_output,
            ) as progress:
                progress.add_task("Creating release...", total=None)

                result = await client.create_release_with_assets(
                    repo=repo,
                    tag=tag,
                    assets=asset_paths,
                    name=name,
                    body=body_content,
                    draft=draft,
                    prerelease=prerelease,
                    target_commitish=target,
                    generate_release_notes=generate_notes,
                )

            return result

    try:
        result = run_async(_create_release())

        if json_output:
            if isinstance(result, DryRunResult):
                output = {
                    "dry_run": result.dry_run,
                    "repo": result.repo,
                    "tag": result.tag,
                    "name": result.name,
                    "draft": result.draft,
                    "prerelease": result.prerelease,
                    "assets": result.assets,
                }
                click.echo(json.dumps(output, indent=2))
            else:
                output = {
                    "success": result.success,
                    "release": {
                        "id": result.release.id if result.release else None,
                        "tag": result.release.tag_name if result.release else tag,
                        "url": result.release.html_url if result.release else None,
                        "draft": result.release.draft if result.release else draft,
                        "prerelease": result.release.prerelease if result.release else prerelease,
                    },
                    "assets_uploaded": [a.name for a in result.assets_uploaded],
                    "assets_failed": [str(p) for p, _ in result.assets_failed],
                    "errors": result.errors,
                }
                click.echo(json.dumps(output, indent=2))
        elif not quiet:
            if isinstance(result, DryRunResult):
                _print_release_dry_run(result)
            elif result.success:
                _print_release_success(result)
            else:
                _print_release_failure(result)

        if isinstance(result, DryRunResult):
            sys.exit(0)
        else:
            sys.exit(0 if result.success else 1)

    except GitHubAuthError as e:
        _handle_auth_error(e, json_output)
    except GitHubError as e:
        _handle_github_error(e, json_output)
    except HWBError as e:
        _handle_hwb_error(e, json_output, verbose)


@github.command("releases")
@click.option("--limit", "-l", default=10, help="Number of releases to show")
@click.pass_context
def release_list(ctx: click.Context, limit: int) -> None:
    """List releases for the repository."""
    json_output: bool = ctx.obj.get("json", False)
    quiet: bool = ctx.obj.get("quiet", False)

    async def _list_releases() -> tuple[list[Release], str]:
        client, repo = await _get_client_and_repo(ctx)

        async with client:
            releases = await client.list_releases(repo, per_page=limit)
            return releases, repo

    try:
        releases, repo = run_async(_list_releases())

        if json_output:
            output = [
                {
                    "tag": r.tag_name,
                    "name": r.name,
                    "draft": r.draft,
                    "prerelease": r.prerelease,
                    "url": r.html_url,
                    "published_at": r.published_at.isoformat() if r.published_at else None,
                    "assets": len(r.assets),
                }
                for r in releases
            ]
            click.echo(json.dumps(output, indent=2))
        elif not quiet:
            console.print(f"\n[bold]Releases for {repo}[/]\n")

            if not releases:
                console.print("[dim]No releases found[/]")
            else:
                table = Table(show_header=True, box=None, padding=(0, 2))
                table.add_column("Tag", style="cyan")
                table.add_column("Name")
                table.add_column("Status")
                table.add_column("Assets")
                table.add_column("Date", style="dim")

                for r in releases:
                    status_parts: list[str] = []
                    if r.draft:
                        status_parts.append("[yellow]draft[/]")
                    if r.prerelease:
                        status_parts.append("[yellow]pre[/]")
                    if not status_parts:
                        status_parts.append("[green]release[/]")

                    date_str = r.published_at.strftime("%Y-%m-%d") if r.published_at else "-"

                    table.add_row(
                        r.tag_name,
                        r.name or "",
                        " ".join(status_parts),
                        str(len(r.assets)),
                        date_str,
                    )

                console.print(table)
            console.print()

    except GitHubAuthError as e:
        _handle_auth_error(e, json_output)
    except GitHubError as e:
        _handle_github_error(e, json_output)


# =============================================================================
# Workflow Commands
# =============================================================================


@github.command("workflow")
@click.argument("action", type=click.Choice(["run", "list", "status"]))
@click.argument("workflow", required=False)
@click.option("--ref", default="main", help="Branch or tag to run on")
@click.option("--input", "-i", "inputs", multiple=True, help="Workflow input (key=value)")
@click.option("--watch", "-w", is_flag=True, help="Watch workflow progress")
@click.pass_context
def workflow_cmd(
    ctx: click.Context,
    action: str,
    workflow: str | None,
    ref: str,
    inputs: tuple[str, ...],
    watch: bool,
) -> None:
    """Manage GitHub Actions workflows.

    Examples:

        hwb github workflow list                     # List recent runs

        hwb github workflow run build.yml           # Trigger workflow

        hwb github workflow run ci.yml --ref dev    # Run on dev branch

        hwb github workflow status 123456           # Get run status
    """
    json_output: bool = ctx.obj.get("json", False)
    quiet: bool = ctx.obj.get("quiet", False)

    # Parse inputs
    workflow_inputs: dict[str, str] = {}
    for inp in inputs:
        if "=" in inp:
            key, value = inp.split("=", 1)
            workflow_inputs[key] = value

    async def _workflow_action() -> WorkflowRunResult | WorkflowListResult | WorkflowStatusResult:
        client, repo = await _get_client_and_repo(ctx)

        async with client:
            if action == "run":
                if not workflow:
                    raise click.UsageError("Workflow filename required for 'run'")

                await client.trigger_workflow(
                    repo,
                    workflow,
                    ref=ref,
                    inputs=workflow_inputs if workflow_inputs else None,
                )
                return WorkflowRunResult(workflow=workflow, ref=ref)

            elif action == "list":
                runs = await client.list_workflow_runs(
                    repo,
                    workflow=workflow,
                    per_page=10,
                )
                return WorkflowListResult(runs=runs, repo=repo)

            else:  # action == "status"
                if not workflow:
                    raise click.UsageError("Run ID required for 'status'")
                run = await client.get_workflow_run(repo, int(workflow))
                return WorkflowStatusResult(run=run)

    try:
        result = run_async(_workflow_action())

        if json_output:
            if isinstance(result, WorkflowRunResult):
                click.echo(
                    json.dumps(
                        {
                            "triggered": True,
                            "workflow": result.workflow,
                            "ref": result.ref,
                        },
                        indent=2,
                    )
                )
            elif isinstance(result, WorkflowListResult):
                output = [
                    {
                        "id": r.id,
                        "name": r.name,
                        "status": r.status,
                        "conclusion": r.conclusion,
                        "branch": r.head_branch,
                        "url": r.html_url,
                    }
                    for r in result.runs
                ]
                click.echo(json.dumps(output, indent=2))
            else:  # WorkflowStatusResult
                r = result.run
                click.echo(
                    json.dumps(
                        {
                            "id": r.id,
                            "name": r.name,
                            "status": r.status,
                            "conclusion": r.conclusion,
                            "url": r.html_url,
                        },
                        indent=2,
                    )
                )
        elif not quiet:
            if isinstance(result, WorkflowRunResult):
                console.print(
                    f"\n[green]✓[/] Triggered workflow [bold]{result.workflow}[/] on {result.ref}\n"
                )
            elif isinstance(result, WorkflowListResult):
                console.print(f"\n[bold]Recent workflow runs for {result.repo}[/]\n")

                if not result.runs:
                    console.print("[dim]No workflow runs found[/]")
                else:
                    table = Table(show_header=True, box=None, padding=(0, 2))
                    table.add_column("ID", style="dim")
                    table.add_column("Workflow")
                    table.add_column("Status")
                    table.add_column("Branch")

                    for r in result.runs:
                        if r.status == "completed":
                            if r.conclusion == "success":
                                status = "[green]✓ success[/]"
                            elif r.conclusion == "failure":
                                status = "[red]✗ failure[/]"
                            else:
                                status = f"[yellow]{r.conclusion}[/]"
                        else:
                            status = f"[blue]{r.status}[/]"

                        table.add_row(str(r.id), r.name, status, r.head_branch)

                    console.print(table)
                console.print()

            else:  # WorkflowStatusResult
                r = result.run
                console.print(f"\n[bold]Workflow Run #{r.id}[/]")
                console.print(f"  Name: {r.name}")
                console.print(f"  Status: {r.status}")
                if r.conclusion:
                    console.print(f"  Conclusion: {r.conclusion}")
                console.print(f"  URL: {r.html_url}\n")

    except GitHubAuthError as e:
        _handle_auth_error(e, json_output)
    except GitHubError as e:
        _handle_github_error(e, json_output)


# =============================================================================
# PR Commands
# =============================================================================


@github.command("pr")
@click.argument("action", type=click.Choice(["create", "list", "view"]))
@click.argument("number", required=False, type=int)
@click.option("--title", "-t", help="PR title")
@click.option("--body", "-b", help="PR description")
@click.option("--head", help="Source branch")
@click.option("--base", default="main", help="Target branch")
@click.option("--draft", is_flag=True, help="Create as draft PR")
@click.pass_context
def pr_cmd(
    ctx: click.Context,
    action: str,
    number: int | None,
    title: str | None,
    body: str | None,
    head: str | None,
    base: str,
    draft: bool,
) -> None:
    """Manage pull requests.

    Examples:

        hwb github pr list                           # List open PRs

        hwb github pr create --title "Fix bug"      # Create PR

        hwb github pr view 123                      # View PR details
    """
    json_output: bool = ctx.obj.get("json", False)
    quiet: bool = ctx.obj.get("quiet", False)

    async def _pr_action() -> PRCreateResult | PRListResult | PRViewResult:
        from headless_wheel_builder.version.git import get_current_branch

        client, repo = await _get_client_and_repo(ctx)

        async with client:
            if action == "create":
                if not title:
                    raise click.UsageError("--title is required for creating PR")

                # Auto-detect head branch if not specified
                branch = head
                if not branch:
                    branch = await get_current_branch()

                pr = await client.create_pull_request(
                    repo,
                    title=title,
                    head=branch,
                    base=base,
                    body=body,
                    draft=draft,
                )
                return PRCreateResult(pr=pr)

            elif action == "list":
                prs = await client.list_pull_requests(repo, per_page=10)
                return PRListResult(prs=prs, repo=repo)

            else:  # action == "view"
                if not number:
                    raise click.UsageError("PR number required for 'view'")
                pr = await client.get_pull_request(repo, number)
                return PRViewResult(pr=pr)

    try:
        result = run_async(_pr_action())

        if json_output:
            if isinstance(result, PRCreateResult):
                pr = result.pr
                click.echo(
                    json.dumps(
                        {
                            "number": pr.number,
                            "title": pr.title,
                            "url": pr.html_url,
                            "draft": pr.draft,
                        },
                        indent=2,
                    )
                )
            elif isinstance(result, PRListResult):
                output = [
                    {
                        "number": pr.number,
                        "title": pr.title,
                        "state": pr.state,
                        "draft": pr.draft,
                        "url": pr.html_url,
                    }
                    for pr in result.prs
                ]
                click.echo(json.dumps(output, indent=2))
            else:  # PRViewResult
                pr = result.pr
                click.echo(
                    json.dumps(
                        {
                            "number": pr.number,
                            "title": pr.title,
                            "state": pr.state,
                            "body": pr.body,
                            "url": pr.html_url,
                        },
                        indent=2,
                    )
                )
        elif not quiet:
            if isinstance(result, PRCreateResult):
                pr = result.pr
                console.print(f"\n[green]✓[/] Created PR #{pr.number}")
                console.print(f"  Title: {pr.title}")
                console.print(f"  URL: {pr.html_url}\n")

            elif isinstance(result, PRListResult):
                console.print(f"\n[bold]Open PRs for {result.repo}[/]\n")

                if not result.prs:
                    console.print("[dim]No open pull requests[/]")
                else:
                    table = Table(show_header=True, box=None, padding=(0, 2))
                    table.add_column("#", style="cyan")
                    table.add_column("Title")
                    table.add_column("Branch")
                    table.add_column("Status")

                    for pr in result.prs:
                        status = "[yellow]draft[/]" if pr.draft else "[green]open[/]"
                        pr_title = pr.title[:50] + "..." if len(pr.title) > 50 else pr.title
                        table.add_row(
                            str(pr.number),
                            pr_title,
                            pr.head_ref,
                            status,
                        )

                    console.print(table)
                console.print()

            else:  # PRViewResult
                pr = result.pr
                console.print(f"\n[bold]PR #{pr.number}: {pr.title}[/]")
                console.print(f"  State: {pr.state}")
                console.print(f"  Branch: {pr.head_ref} → {pr.base_ref}")
                console.print(f"  URL: {pr.html_url}")
                if pr.body:
                    console.print(f"\n{pr.body}\n")
                else:
                    console.print()

    except GitHubAuthError as e:
        _handle_auth_error(e, json_output)
    except GitHubError as e:
        _handle_github_error(e, json_output)


# =============================================================================
# Issue Commands
# =============================================================================


@github.command("issue")
@click.argument("action", type=click.Choice(["create", "list", "view"]))
@click.argument("number", required=False, type=int)
@click.option("--title", "-t", help="Issue title")
@click.option("--body", "-b", help="Issue description")
@click.option("--label", "-l", "labels", multiple=True, help="Labels to apply")
@click.pass_context
def issue_cmd(
    ctx: click.Context,
    action: str,
    number: int | None,
    title: str | None,
    body: str | None,
    labels: tuple[str, ...],
) -> None:
    """Manage issues.

    Examples:

        hwb github issue list                        # List open issues

        hwb github issue create --title "Bug"       # Create issue

        hwb github issue view 42                    # View issue
    """
    json_output: bool = ctx.obj.get("json", False)
    quiet: bool = ctx.obj.get("quiet", False)

    async def _issue_action() -> IssueCreateResult | IssueListResult | IssueViewResult:
        client, repo = await _get_client_and_repo(ctx)

        async with client:
            if action == "create":
                if not title:
                    raise click.UsageError("--title is required for creating issue")

                issue = await client.create_issue(
                    repo,
                    title=title,
                    body=body,
                    labels=list(labels) if labels else None,
                )
                return IssueCreateResult(issue=issue)

            elif action == "list":
                issues = await client.list_issues(repo, per_page=10)
                return IssueListResult(issues=issues, repo=repo)

            else:  # action == "view"
                if not number:
                    raise click.UsageError("Issue number required for 'view'")
                issue = await client.get_issue(repo, number)
                return IssueViewResult(issue=issue)

    try:
        result = run_async(_issue_action())

        if json_output:
            if isinstance(result, IssueCreateResult):
                issue = result.issue
                click.echo(
                    json.dumps(
                        {
                            "number": issue.number,
                            "title": issue.title,
                            "url": issue.html_url,
                        },
                        indent=2,
                    )
                )
            elif isinstance(result, IssueListResult):
                output = [
                    {
                        "number": i.number,
                        "title": i.title,
                        "state": i.state,
                        "labels": i.labels,
                        "url": i.html_url,
                    }
                    for i in result.issues
                ]
                click.echo(json.dumps(output, indent=2))
            else:  # IssueViewResult
                issue = result.issue
                click.echo(
                    json.dumps(
                        {
                            "number": issue.number,
                            "title": issue.title,
                            "state": issue.state,
                            "body": issue.body,
                            "labels": issue.labels,
                            "url": issue.html_url,
                        },
                        indent=2,
                    )
                )
        elif not quiet:
            if isinstance(result, IssueCreateResult):
                issue = result.issue
                console.print(f"\n[green]✓[/] Created issue #{issue.number}")
                console.print(f"  Title: {issue.title}")
                console.print(f"  URL: {issue.html_url}\n")

            elif isinstance(result, IssueListResult):
                console.print(f"\n[bold]Open issues for {result.repo}[/]\n")

                if not result.issues:
                    console.print("[dim]No open issues[/]")
                else:
                    table = Table(show_header=True, box=None, padding=(0, 2))
                    table.add_column("#", style="cyan")
                    table.add_column("Title")
                    table.add_column("Labels")

                    for issue in result.issues:
                        labels_str = ", ".join(issue.labels[:3]) if issue.labels else "-"
                        issue_title = (
                            issue.title[:50] + "..." if len(issue.title) > 50 else issue.title
                        )
                        table.add_row(
                            str(issue.number),
                            issue_title,
                            labels_str,
                        )

                    console.print(table)
                console.print()

            else:  # IssueViewResult
                issue = result.issue
                console.print(f"\n[bold]Issue #{issue.number}: {issue.title}[/]")
                console.print(f"  State: {issue.state}")
                if issue.labels:
                    console.print(f"  Labels: {', '.join(issue.labels)}")
                console.print(f"  URL: {issue.html_url}")
                if issue.body:
                    console.print(f"\n{issue.body}\n")
                else:
                    console.print()

    except GitHubAuthError as e:
        _handle_auth_error(e, json_output)
    except GitHubError as e:
        _handle_github_error(e, json_output)
