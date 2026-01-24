"""CLI for release management."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from headless_wheel_builder.release.manager import ReleaseManager
from headless_wheel_builder.release.models import ReleaseStatus
from headless_wheel_builder.release.workflow import WORKFLOW_TEMPLATES

console = Console()
error_console = Console(stderr=True)


def get_manager() -> ReleaseManager:
    """Get release manager instance."""
    return ReleaseManager()


@click.group(name="release")
def release() -> None:
    """Release management and approval workflows.

    Create, manage, and publish releases with multi-stage approvals.
    """
    pass


@release.command("create")
@click.option("--name", "-n", required=True, help="Release name")
@click.option("--version", "-v", required=True, help="Version")
@click.option("--package", "-p", required=True, help="Package name")
@click.option(
    "--wheel",
    "-w",
    multiple=True,
    type=click.Path(exists=True, path_type=Path),
    help="Wheel file paths",
)
@click.option("--changelog", "-c", help="Changelog text")
@click.option(
    "--changelog-file", type=click.Path(exists=True, path_type=Path), help="Changelog file"
)
@click.option(
    "--template", "-t", type=click.Choice(list(WORKFLOW_TEMPLATES.keys())), help="Workflow template"
)
@click.option("--creator", default="cli", help="Creator identifier")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def create_release(
    name: str,
    version: str,
    package: str,
    wheel: tuple[Path, ...],
    changelog: str | None,
    changelog_file: Path | None,
    template: str | None,
    creator: str,
    json_output: bool,
) -> None:
    """Create a new draft release."""
    manager = get_manager()

    # Read changelog from file if provided
    if changelog_file:
        changelog = changelog_file.read_text(encoding="utf-8")

    draft = manager.create_draft(
        name=name,
        version=version,
        package=package,
        wheel_paths=list(wheel),
        changelog=changelog or "",
        created_by=creator,
        template=template,
    )

    if json_output:
        click.echo(json.dumps(draft.to_dict(), indent=2))
        return

    console.print()
    console.print(
        Panel(
            f"[bold]ID:[/] {draft.id}\n"
            f"[bold]Name:[/] {draft.name}\n"
            f"[bold]Version:[/] {draft.version}\n"
            f"[bold]Package:[/] {draft.package}\n"
            f"[bold]Status:[/] {draft.status.value}\n"
            f"[bold]Approval Steps:[/] {len(draft.approval_steps)}",
            title="[green]Draft Release Created[/]",
            border_style="green",
        )
    )
    console.print()


@release.command("list")
@click.option(
    "--status", "-s", type=click.Choice([s.value for s in ReleaseStatus]), help="Filter by status"
)
@click.option("--package", "-p", help="Filter by package")
@click.option("--limit", "-n", default=20, help="Maximum results")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def list_releases(
    status: str | None,
    package: str | None,
    limit: int,
    json_output: bool,
) -> None:
    """List releases."""
    manager = get_manager()

    status_enum = ReleaseStatus(status) if status else None
    releases = manager.list_releases(status=status_enum, package=package, limit=limit)

    if json_output:
        click.echo(json.dumps([r.to_dict() for r in releases], indent=2))
        return

    if not releases:
        console.print("[yellow]No releases found[/]")
        return

    table = Table(title=f"Releases ({len(releases)})")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Package")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("Created")

    for r in releases:
        status_style = {
            "draft": "dim",
            "pending_approval": "yellow",
            "approved": "green",
            "rejected": "red",
            "published": "bold green",
            "failed": "bold red",
            "rolled_back": "magenta",
        }.get(r.status.value, "")

        created = r.created_at[:10] if r.created_at else "-"

        table.add_row(
            r.id,
            r.name,
            r.package,
            r.version,
            f"[{status_style}]{r.status.value}[/]",
            created,
        )

    console.print(table)


@release.command("show")
@click.argument("release_id")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def show_release(release_id: str, json_output: bool) -> None:
    """Show release details."""
    manager = get_manager()
    draft = manager.get_release(release_id)

    if not draft:
        error_console.print(f"[red]Release not found:[/] {release_id}")
        sys.exit(1)

    if json_output:
        click.echo(json.dumps(draft.to_dict(), indent=2))
        return

    console.print()
    console.print(
        Panel(
            f"[bold]ID:[/] {draft.id}\n"
            f"[bold]Name:[/] {draft.name}\n"
            f"[bold]Version:[/] {draft.version}\n"
            f"[bold]Package:[/] {draft.package}\n"
            f"[bold]Status:[/] {draft.status.value}\n"
            f"[bold]Created:[/] {draft.created_at}\n"
            f"[bold]Created By:[/] {draft.created_by}",
            title="Release Details",
            border_style="blue",
        )
    )

    # Approval steps
    if draft.approval_steps:
        console.print("\n[bold]Approval Workflow:[/]")
        for step in draft.approval_steps:
            state_icon = {
                "pending": "⏳",
                "approved": "✅",
                "rejected": "❌",
                "skipped": "⏭️",
            }.get(step.state.value, "?")

            console.print(f"  {state_icon} {step.name}")
            if step.approved_by:
                console.print(f"      Approved by: {', '.join(step.approved_by)}")
            if step.rejected_by:
                console.print(f"      Rejected by: {step.rejected_by}")

    # Changelog
    if draft.changelog:
        console.print("\n[bold]Changelog:[/]")
        console.print(draft.changelog[:500])
        if len(draft.changelog) > 500:
            console.print("...")

    # Wheels
    if draft.wheel_paths:
        console.print("\n[bold]Wheels:[/]")
        for path in draft.wheel_paths:
            console.print(f"  • {path}")

    console.print()


@release.command("submit")
@click.argument("release_id")
def submit_release(release_id: str) -> None:
    """Submit a draft release for approval."""
    manager = get_manager()

    if not manager.submit_for_approval(release_id):
        error_console.print(f"[red]Could not submit release:[/] {release_id}")
        error_console.print("Release may not exist or is not in draft status.")
        sys.exit(1)

    console.print(f"[green]Release submitted for approval:[/] {release_id}")


@release.command("approve")
@click.argument("release_id")
@click.option("--approver", "-a", required=True, help="Approver identifier")
@click.option("--step", "-s", help="Specific step to approve")
@click.option("--comment", "-c", help="Approval comment")
def approve_release(
    release_id: str,
    approver: str,
    step: str | None,
    comment: str | None,
) -> None:
    """Approve a release step."""
    manager = get_manager()

    if not manager.approve(release_id, approver, step, comment or ""):
        error_console.print(f"[red]Could not approve release:[/] {release_id}")
        sys.exit(1)

    draft = manager.get_release(release_id)
    if draft and draft.is_approved:
        console.print(f"[bold green]Release fully approved:[/] {release_id}")
    else:
        console.print(f"[green]Approval recorded:[/] {release_id}")


@release.command("reject")
@click.argument("release_id")
@click.option("--rejector", "-r", required=True, help="Rejector identifier")
@click.option("--step", "-s", help="Specific step to reject")
@click.option("--comment", "-c", help="Rejection reason")
def reject_release(
    release_id: str,
    rejector: str,
    step: str | None,
    comment: str | None,
) -> None:
    """Reject a release."""
    manager = get_manager()

    if not manager.reject(release_id, rejector, step, comment or ""):
        error_console.print(f"[red]Could not reject release:[/] {release_id}")
        sys.exit(1)

    console.print(f"[yellow]Release rejected:[/] {release_id}")


@release.command("publish")
@click.argument("release_id")
@click.option("--publisher", "-p", default="cli", help="Publisher identifier")
@click.option("--force", "-f", is_flag=True, help="Force publish without approval")
def publish_release(
    release_id: str,
    publisher: str,
    force: bool,
) -> None:
    """Publish an approved release."""
    manager = get_manager()

    if force:
        # Skip approval check by temporarily disabling requirement
        manager.config.require_approval = False

    if not manager.publish(release_id, publisher):
        error_console.print(f"[red]Could not publish release:[/] {release_id}")
        error_console.print("Release may not be approved yet.")
        sys.exit(1)

    console.print(f"[bold green]Release published:[/] {release_id}")


@release.command("rollback")
@click.argument("release_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def rollback_release(release_id: str, yes: bool) -> None:
    """Rollback a published release."""
    manager = get_manager()

    if not yes and not click.confirm(f"Rollback release {release_id}?"):
        return

    if not manager.rollback(release_id):
        error_console.print(f"[red]Could not rollback release:[/] {release_id}")
        sys.exit(1)

    console.print(f"[yellow]Release rolled back:[/] {release_id}")


@release.command("delete")
@click.argument("release_id")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def delete_release(release_id: str, yes: bool) -> None:
    """Delete a draft release."""
    manager = get_manager()

    if not yes and not click.confirm(f"Delete release {release_id}?"):
        return

    if not manager.delete(release_id):
        error_console.print(f"[red]Could not delete release:[/] {release_id}")
        error_console.print("Only draft or rejected releases can be deleted.")
        sys.exit(1)

    console.print(f"[green]Release deleted:[/] {release_id}")


@release.command("pending")
@click.option("--approver", "-a", help="Filter by approver")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def show_pending(approver: str | None, json_output: bool) -> None:
    """Show releases pending approval."""
    manager = get_manager()

    if approver:
        releases = manager.get_pending_approvals(approver)
    else:
        releases = manager.list_releases(status=ReleaseStatus.PENDING_APPROVAL)

    if json_output:
        click.echo(json.dumps([r.to_dict() for r in releases], indent=2))
        return

    if not releases:
        console.print("[green]No pending approvals[/]")
        return

    console.print()
    console.print(f"[bold]Pending Approvals ({len(releases)}):[/]")
    console.print()

    for r in releases:
        current = r.current_step
        step_info = f" - {current.name}" if current else ""
        console.print(f"  • {r.id}: {r.name} v{r.version}{step_info}")

    console.print()


@release.command("stats")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def show_stats(json_output: bool) -> None:
    """Show release statistics."""
    manager = get_manager()
    stats = manager.get_statistics()

    if json_output:
        click.echo(json.dumps(stats, indent=2))
        return

    console.print()
    console.print(
        Panel(
            f"[bold]Total Releases:[/] {stats['total']}\n"
            f"[bold]Pending Approval:[/] {stats['pending_approval']}",
            title="Release Statistics",
            border_style="blue",
        )
    )

    if stats["by_status"]:
        console.print("\n[bold]By Status:[/]")
        for status, count in sorted(stats["by_status"].items()):
            console.print(f"  {status}: {count}")

    if stats["by_package"]:
        console.print("\n[bold]By Package:[/]")
        for pkg, count in sorted(stats["by_package"].items(), key=lambda x: -x[1])[:5]:
            console.print(f"  {pkg}: {count}")

    console.print()


@release.command("templates")
def show_templates() -> None:
    """Show available workflow templates."""
    console.print()
    console.print("[bold]Available Workflow Templates:[/]")
    console.print()

    for name, template in WORKFLOW_TEMPLATES.items():
        console.print(f"[cyan]{name}[/]")
        console.print(f"  {template.description}")
        console.print("  Steps:")
        for step in template.steps:
            step_name = step.get("name", "Unnamed")
            required = step.get("required_approvals", 1)
            console.print(f"    • {step_name} ({required} approval(s) required)")
        console.print()
