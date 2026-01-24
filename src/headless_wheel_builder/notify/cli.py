"""CLI for notification system."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import TYPE_CHECKING, Any, TypeVar

import click
from rich.console import Console
from rich.table import Table

from headless_wheel_builder.notify.models import (
    NotificationConfig,
    NotificationEvent,
    NotificationType,
    ProviderType,
)
from headless_wheel_builder.notify.sender import NotificationSender

if TYPE_CHECKING:
    from collections.abc import Coroutine

console = Console()
error_console = Console(stderr=True)

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run async function."""
    return asyncio.run(coro)


@click.group(name="notify")
def notify() -> None:
    """Notification system.

    Send notifications to Slack, Discord, or generic webhooks.
    """
    pass


@notify.command("test")
@click.option("--url", "-u", required=True, help="Webhook URL")
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["slack", "discord", "webhook"]),
    default="webhook",
    help="Provider type",
)
@click.option("--title", "-t", default="Test Notification", help="Notification title")
@click.option("--message", "-m", default="This is a test notification", help="Message")
@click.option(
    "--status",
    type=click.Choice(["info", "success", "warning", "error"]),
    default="info",
    help="Status",
)
def test_notification(
    url: str,
    provider: str,
    title: str,
    message: str,
    status: str,
) -> None:
    """Send a test notification.

    Use this to verify your webhook configuration.
    """
    config = NotificationConfig(
        name="test",
        provider=ProviderType(provider),
        webhook_url=url,
    )

    event = NotificationEvent(
        type=NotificationType.CUSTOM,
        title=title,
        message=message,
        status=status,
        data={"test": True, "source": "hwb notify test"},
    )

    sender = NotificationSender(channels=[config])

    async def _send():
        return await sender.send(event)

    console.print("\n[bold blue]Sending test notification...[/]")
    console.print(f"  Provider: {provider}")
    console.print(f"  Title: {title}")
    console.print()

    results = run_async(_send())

    if results and results[0].success:
        console.print("[green]Notification sent successfully![/]")
    else:
        error = results[0].error if results else "No response"
        error_console.print(f"[red]Failed to send notification:[/] {error}")
        sys.exit(1)


@notify.command("send")
@click.option("--url", "-u", required=True, help="Webhook URL")
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["slack", "discord", "webhook"]),
    default="webhook",
    help="Provider type",
)
@click.option(
    "--type",
    "event_type",
    type=click.Choice([t.value for t in NotificationType]),
    default="custom",
    help="Event type",
)
@click.option("--title", "-t", required=True, help="Notification title")
@click.option("--message", "-m", default="", help="Message")
@click.option(
    "--status",
    type=click.Choice(["info", "success", "warning", "error"]),
    default="info",
    help="Status",
)
@click.option("--data", "-d", multiple=True, help="Data in key=value format")
@click.option("--url-link", help="URL to include in notification")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
def send_notification(
    url: str,
    provider: str,
    event_type: str,
    title: str,
    message: str,
    status: str,
    data: tuple[str, ...],
    url_link: str | None,
    json_output: bool,
) -> None:
    """Send a notification.

    Examples:

        hwb notify send -u https://hooks.slack.com/... -p slack \\
            -t "Build Complete" -m "Built mypackage 1.0.0"

        hwb notify send -u https://discord.com/api/webhooks/... -p discord \\
            -t "Release" --status success -d version=1.0.0 -d package=myapp
    """
    # Parse data key=value pairs
    event_data: dict[str, Any] = {}
    for item in data:
        if "=" in item:
            key, value = item.split("=", 1)
            event_data[key] = value
        else:
            event_data[item] = True

    config = NotificationConfig(
        name="cli",
        provider=ProviderType(provider),
        webhook_url=url,
    )

    event = NotificationEvent(
        type=NotificationType(event_type),
        title=title,
        message=message,
        status=status,
        data=event_data,
        url=url_link,
    )

    sender = NotificationSender(channels=[config])

    async def _send():
        return await sender.send(event)

    results = run_async(_send())

    if json_output:
        output = {
            "success": results[0].success if results else False,
            "results": [r.to_dict() for r in results],
        }
        click.echo(json.dumps(output, indent=2))
    else:
        if results and results[0].success:
            console.print("[green]Notification sent![/]")
        else:
            error = results[0].error if results else "No response"
            error_console.print(f"[red]Failed:[/] {error}")
            sys.exit(1)


@notify.command("providers")
def list_providers() -> None:
    """List available notification providers."""
    console.print("\n[bold]Available Notification Providers[/]\n")

    table = Table()
    table.add_column("Provider", style="cyan")
    table.add_column("Description")
    table.add_column("Webhook Format")

    table.add_row(
        "slack",
        "Slack Incoming Webhooks",
        "https://hooks.slack.com/services/...",
    )
    table.add_row(
        "discord",
        "Discord Webhooks",
        "https://discord.com/api/webhooks/...",
    )
    table.add_row(
        "webhook",
        "Generic HTTP Webhook",
        "Any HTTP(S) URL",
    )

    console.print(table)

    console.print("\n[bold]Usage Examples:[/]")
    console.print("  hwb notify test -u <webhook-url> -p slack")
    console.print("  hwb notify send -u <webhook-url> -p discord -t 'Build Complete'")
    console.print()


@notify.command("events")
def list_events() -> None:
    """List available notification event types."""
    console.print("\n[bold]Available Event Types[/]\n")

    table = Table()
    table.add_column("Event", style="cyan")
    table.add_column("Description")

    events = [
        ("build_success", "Build completed successfully"),
        ("build_failure", "Build failed"),
        ("release_created", "GitHub release created"),
        ("release_published", "Release published to registry"),
        ("upload_success", "Package uploaded successfully"),
        ("upload_failure", "Package upload failed"),
        ("pipeline_start", "Pipeline execution started"),
        ("pipeline_success", "Pipeline completed successfully"),
        ("pipeline_failure", "Pipeline execution failed"),
        ("custom", "Custom event"),
    ]

    for event, desc in events:
        table.add_row(event, desc)

    console.print(table)
    console.print()
