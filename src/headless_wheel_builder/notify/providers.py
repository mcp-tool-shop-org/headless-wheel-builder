"""Notification providers for different platforms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import httpx

from headless_wheel_builder.notify.models import (
    NotificationConfig,
    NotificationEvent,
    NotificationResult,
)


class BaseProvider(ABC):
    """Base class for notification providers."""

    def __init__(self, config: NotificationConfig) -> None:
        """Initialize provider.

        Args:
            config: Notification channel configuration
        """
        self.config = config

    @abstractmethod
    def build_payload(self, event: NotificationEvent) -> dict[str, Any]:
        """Build the notification payload.

        Args:
            event: Notification event

        Returns:
            Payload dictionary for the provider's API
        """
        pass

    async def send(self, event: NotificationEvent) -> NotificationResult:
        """Send a notification.

        Args:
            event: Notification event

        Returns:
            Notification result
        """
        try:
            payload = self.build_payload(event)

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.config.webhook_url,
                    json=payload,
                    timeout=30.0,
                )

                if response.status_code in (200, 201, 204):
                    return NotificationResult(
                        config=self.config,
                        success=True,
                        response_code=response.status_code,
                    )
                else:
                    return NotificationResult(
                        config=self.config,
                        success=False,
                        error=f"HTTP {response.status_code}: {response.text}",
                        response_code=response.status_code,
                    )

        except httpx.TimeoutException:
            return NotificationResult(
                config=self.config,
                success=False,
                error="Request timed out",
            )
        except httpx.RequestError as e:
            return NotificationResult(
                config=self.config,
                success=False,
                error=str(e),
            )
        except Exception as e:
            return NotificationResult(
                config=self.config,
                success=False,
                error=f"Unexpected error: {e}",
            )


class SlackProvider(BaseProvider):
    """Slack notification provider.

    Sends notifications via Slack incoming webhooks.
    """

    STATUS_COLORS = {
        "info": "#2196F3",
        "success": "#4CAF50",
        "warning": "#FF9800",
        "error": "#F44336",
    }

    STATUS_EMOJI = {
        "info": ":information_source:",
        "success": ":white_check_mark:",
        "warning": ":warning:",
        "error": ":x:",
    }

    def build_payload(self, event: NotificationEvent) -> dict[str, Any]:
        """Build Slack webhook payload."""
        color = self.STATUS_COLORS.get(event.status, "#2196F3")
        emoji = self.STATUS_EMOJI.get(event.status, ":information_source:")

        # Build fields from event data
        fields: list[dict[str, Any]] = []
        for key, value in event.data.items():
            fields.append(
                {
                    "title": key.replace("_", " ").title(),
                    "value": str(value),
                    "short": len(str(value)) < 30,
                }
            )

        # Build attachment
        attachment: dict[str, Any] = {
            "color": color,
            "title": event.title,
            "text": event.message,
            "fields": fields,
            "footer": "Headless Wheel Builder",
            "ts": int(datetime.now(timezone.utc).timestamp()),
        }

        if event.url:
            attachment["title_link"] = event.url

        return {
            "text": f"{emoji} {event.title}",
            "attachments": [attachment],
        }


class DiscordProvider(BaseProvider):
    """Discord notification provider.

    Sends notifications via Discord webhooks with embeds.
    """

    STATUS_COLORS = {
        "info": 0x2196F3,
        "success": 0x4CAF50,
        "warning": 0xFF9800,
        "error": 0xF44336,
    }

    STATUS_EMOJI = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
    }

    def build_payload(self, event: NotificationEvent) -> dict[str, Any]:
        """Build Discord webhook payload."""
        color = self.STATUS_COLORS.get(event.status, 0x2196F3)
        emoji = self.STATUS_EMOJI.get(event.status, "ℹ️")

        # Build fields from event data
        fields: list[dict[str, Any]] = []
        for key, value in event.data.items():
            fields.append(
                {
                    "name": key.replace("_", " ").title(),
                    "value": str(value),
                    "inline": len(str(value)) < 30,
                }
            )

        # Build embed
        embed: dict[str, Any] = {
            "title": f"{emoji} {event.title}",
            "description": event.message,
            "color": color,
            "fields": fields,
            "footer": {
                "text": "Headless Wheel Builder",
            },
            "timestamp": event.timestamp or datetime.now(timezone.utc).isoformat(),
        }

        if event.url:
            embed["url"] = event.url

        return {
            "embeds": [embed],
        }


class WebhookProvider(BaseProvider):
    """Generic webhook provider.

    Sends notifications as JSON to any HTTP endpoint.
    """

    def build_payload(self, event: NotificationEvent) -> dict[str, Any]:
        """Build generic webhook payload."""
        return {
            "event": event.to_dict(),
            "source": "headless-wheel-builder",
            "timestamp": event.timestamp or datetime.now(timezone.utc).isoformat(),
        }

    async def send(self, event: NotificationEvent) -> NotificationResult:
        """Send webhook with custom headers support."""
        try:
            payload = self.build_payload(event)

            # Get custom headers from extra config
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "HeadlessWheelBuilder/1.0",
            }
            if "headers" in self.config.extra:
                headers.update(self.config.extra["headers"])

            # Get HTTP method (default POST)
            method = self.config.extra.get("method", "POST").upper()

            async with httpx.AsyncClient() as client:
                if method == "POST":
                    response = await client.post(
                        self.config.webhook_url,
                        json=payload,
                        headers=headers,
                        timeout=30.0,
                    )
                else:
                    response = await client.request(
                        method,
                        self.config.webhook_url,
                        json=payload,
                        headers=headers,
                        timeout=30.0,
                    )

                if response.status_code in (200, 201, 202, 204):
                    return NotificationResult(
                        config=self.config,
                        success=True,
                        response_code=response.status_code,
                    )
                else:
                    return NotificationResult(
                        config=self.config,
                        success=False,
                        error=f"HTTP {response.status_code}",
                        response_code=response.status_code,
                    )

        except httpx.TimeoutException:
            return NotificationResult(
                config=self.config,
                success=False,
                error="Request timed out",
            )
        except httpx.RequestError as e:
            return NotificationResult(
                config=self.config,
                success=False,
                error=str(e),
            )
        except Exception as e:
            return NotificationResult(
                config=self.config,
                success=False,
                error=f"Unexpected error: {e}",
            )


def get_provider(config: NotificationConfig) -> BaseProvider:
    """Get the appropriate provider for a configuration.

    Args:
        config: Notification channel configuration

    Returns:
        Provider instance
    """
    from headless_wheel_builder.notify.models import ProviderType

    providers = {
        ProviderType.SLACK: SlackProvider,
        ProviderType.DISCORD: DiscordProvider,
        ProviderType.WEBHOOK: WebhookProvider,
    }

    provider_class = providers.get(config.provider)
    if provider_class is None:
        raise ValueError(f"Unsupported provider: {config.provider}")

    return provider_class(config)
