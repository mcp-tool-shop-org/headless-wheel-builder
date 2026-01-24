"""Notification sender for coordinating notifications across channels."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from headless_wheel_builder.notify.models import (
    NotificationConfig,
    NotificationEvent,
    NotificationResult,
    NotificationType,
)
from headless_wheel_builder.notify.providers import get_provider


@dataclass
class NotificationSender:
    """Sender for coordinating notifications across multiple channels.

    Attributes:
        channels: List of notification channel configurations
        fail_silently: Whether to continue on notification failures
    """

    channels: list[NotificationConfig] = field(default_factory=lambda: [])
    fail_silently: bool = True

    async def send(
        self,
        event: NotificationEvent,
        channels: list[NotificationConfig] | None = None,
    ) -> list[NotificationResult]:
        """Send a notification to all applicable channels.

        Args:
            event: Notification event to send
            channels: Specific channels to use (default: all configured)

        Returns:
            List of notification results
        """
        target_channels = channels if channels is not None else self.channels

        # Filter to channels that should receive this event
        applicable = [c for c in target_channels if c.should_notify(event)]

        if not applicable:
            return []

        # Send to all channels in parallel
        tasks: list[asyncio.Task[NotificationResult]] = []
        for channel in applicable:
            provider = get_provider(channel)
            tasks.append(asyncio.create_task(provider.send(event)))

        results: list[NotificationResult | BaseException] = await asyncio.gather(
            *tasks, return_exceptions=True
        )

        # Convert exceptions to results
        notification_results: list[NotificationResult] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                notification_results.append(
                    NotificationResult(
                        config=applicable[i],
                        success=False,
                        error=str(result),
                    )
                )
            else:
                notification_results.append(result)

        return notification_results

    async def notify_build_success(
        self,
        package: str,
        version: str,
        wheel_path: str | None = None,
        duration: float | None = None,
    ) -> list[NotificationResult]:
        """Send build success notification.

        Args:
            package: Package name
            version: Package version
            wheel_path: Path to built wheel
            duration: Build duration in seconds

        Returns:
            Notification results
        """
        data: dict[str, Any] = {
            "package": package,
            "version": version,
        }
        if wheel_path:
            data["wheel"] = wheel_path
        if duration:
            data["duration"] = f"{duration:.1f}s"

        event = NotificationEvent(
            type=NotificationType.BUILD_SUCCESS,
            title=f"Build Successful: {package} {version}",
            message=f"Successfully built {package} version {version}",
            status="success",
            data=data,
        )
        return await self.send(event)

    async def notify_build_failure(
        self,
        package: str,
        error: str,
        version: str | None = None,
    ) -> list[NotificationResult]:
        """Send build failure notification.

        Args:
            package: Package name
            error: Error message
            version: Package version (if known)

        Returns:
            Notification results
        """
        title = f"Build Failed: {package}"
        if version:
            title += f" {version}"

        data: dict[str, Any] = {
            "package": package,
            "error": error[:500],  # Truncate long errors
        }
        if version:
            data["version"] = version

        event = NotificationEvent(
            type=NotificationType.BUILD_FAILURE,
            title=title,
            message=error[:200],
            status="error",
            data=data,
        )
        return await self.send(event)

    async def notify_release_created(
        self,
        package: str,
        version: str,
        url: str | None = None,
        assets: list[str] | None = None,
    ) -> list[NotificationResult]:
        """Send release created notification.

        Args:
            package: Package name
            version: Release version
            url: Release URL
            assets: List of release assets

        Returns:
            Notification results
        """
        data: dict[str, Any] = {
            "package": package,
            "version": version,
        }
        if assets:
            data["assets"] = ", ".join(assets[:5])
            if len(assets) > 5:
                data["assets"] += f" (+{len(assets) - 5} more)"

        event = NotificationEvent(
            type=NotificationType.RELEASE_CREATED,
            title=f"Release Created: {package} {version}",
            message=f"New release {version} is now available",
            status="success",
            data=data,
            url=url,
        )
        return await self.send(event)

    async def notify_pipeline_start(
        self,
        package: str,
        stages: list[str] | None = None,
    ) -> list[NotificationResult]:
        """Send pipeline start notification.

        Args:
            package: Package name
            stages: List of stages to run

        Returns:
            Notification results
        """
        data: dict[str, Any] = {
            "package": package,
        }
        if stages:
            data["stages"] = ", ".join(stages)

        event = NotificationEvent(
            type=NotificationType.PIPELINE_START,
            title=f"Pipeline Started: {package}",
            message=f"Build pipeline started for {package}",
            status="info",
            data=data,
        )
        return await self.send(event)

    async def notify_pipeline_success(
        self,
        package: str,
        version: str,
        duration: float | None = None,
        stages_completed: int | None = None,
    ) -> list[NotificationResult]:
        """Send pipeline success notification.

        Args:
            package: Package name
            version: Package version
            duration: Total duration
            stages_completed: Number of stages completed

        Returns:
            Notification results
        """
        data: dict[str, Any] = {
            "package": package,
            "version": version,
        }
        if duration:
            data["duration"] = f"{duration:.1f}s"
        if stages_completed:
            data["stages"] = f"{stages_completed} completed"

        event = NotificationEvent(
            type=NotificationType.PIPELINE_SUCCESS,
            title=f"Pipeline Complete: {package} {version}",
            message="All pipeline stages completed successfully",
            status="success",
            data=data,
        )
        return await self.send(event)

    async def notify_pipeline_failure(
        self,
        package: str,
        stage: str,
        error: str,
    ) -> list[NotificationResult]:
        """Send pipeline failure notification.

        Args:
            package: Package name
            stage: Failed stage name
            error: Error message

        Returns:
            Notification results
        """
        event = NotificationEvent(
            type=NotificationType.PIPELINE_FAILURE,
            title=f"Pipeline Failed: {package}",
            message=f"Pipeline failed at stage: {stage}",
            status="error",
            data={
                "package": package,
                "stage": stage,
                "error": error[:500],
            },
        )
        return await self.send(event)

    def add_channel(self, config: NotificationConfig) -> None:
        """Add a notification channel.

        Args:
            config: Channel configuration
        """
        # Replace if exists with same name
        self.channels = [c for c in self.channels if c.name != config.name]
        self.channels.append(config)

    def remove_channel(self, name: str) -> bool:
        """Remove a notification channel by name.

        Args:
            name: Channel name

        Returns:
            True if channel was removed
        """
        original_len = len(self.channels)
        self.channels = [c for c in self.channels if c.name != name]
        return len(self.channels) < original_len
