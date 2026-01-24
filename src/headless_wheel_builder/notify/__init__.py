"""Notification system for Headless Wheel Builder.

This module provides functionality for sending notifications
about build and release events to various channels:

- Slack
- Discord
- Generic webhooks
- Email (optional)
"""

from __future__ import annotations

from headless_wheel_builder.notify.models import (
    NotificationConfig,
    NotificationEvent,
    NotificationResult,
    NotificationType,
)
from headless_wheel_builder.notify.providers import (
    DiscordProvider,
    SlackProvider,
    WebhookProvider,
)
from headless_wheel_builder.notify.sender import NotificationSender

__all__ = [
    "DiscordProvider",
    "NotificationConfig",
    "NotificationEvent",
    "NotificationResult",
    "NotificationSender",
    "NotificationType",
    "SlackProvider",
    "WebhookProvider",
]
