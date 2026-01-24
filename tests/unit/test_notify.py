"""Tests for notification system."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from headless_wheel_builder.notify.models import (
    NotificationConfig,
    NotificationEvent,
    NotificationResult,
    NotificationType,
    ProviderType,
)
from headless_wheel_builder.notify.providers import (
    DiscordProvider,
    SlackProvider,
    WebhookProvider,
    get_provider,
)
from headless_wheel_builder.notify.sender import NotificationSender


class TestNotificationType:
    """Tests for NotificationType enum."""

    def test_all_types_exist(self) -> None:
        """Test all expected types exist."""
        types = [t.value for t in NotificationType]
        assert "build_success" in types
        assert "build_failure" in types
        assert "release_created" in types
        assert "pipeline_start" in types
        assert "pipeline_success" in types
        assert "pipeline_failure" in types
        assert "custom" in types


class TestProviderType:
    """Tests for ProviderType enum."""

    def test_all_providers_exist(self) -> None:
        """Test all expected providers exist."""
        types = [t.value for t in ProviderType]
        assert "slack" in types
        assert "discord" in types
        assert "webhook" in types
        assert "email" in types


class TestNotificationEvent:
    """Tests for NotificationEvent model."""

    def test_minimal_event(self) -> None:
        """Test creating minimal event."""
        event = NotificationEvent(
            type=NotificationType.BUILD_SUCCESS,
            title="Build Complete",
        )
        assert event.type == NotificationType.BUILD_SUCCESS
        assert event.title == "Build Complete"
        assert event.message == ""
        assert event.status == "info"
        assert event.data == {}

    def test_full_event(self) -> None:
        """Test creating full event."""
        event = NotificationEvent(
            type=NotificationType.RELEASE_CREATED,
            title="Release v1.0.0",
            message="New release is available",
            status="success",
            data={"version": "1.0.0", "package": "myapp"},
            url="https://github.com/owner/repo/releases/v1.0.0",
            timestamp="2024-01-15T12:00:00Z",
        )
        assert event.status == "success"
        assert event.data["version"] == "1.0.0"
        assert event.url is not None

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        event = NotificationEvent(
            type=NotificationType.BUILD_SUCCESS,
            title="Build Complete",
            message="Built successfully",
            status="success",
        )
        data = event.to_dict()
        assert data["type"] == "build_success"
        assert data["title"] == "Build Complete"
        assert data["message"] == "Built successfully"
        assert data["status"] == "success"


class TestNotificationConfig:
    """Tests for NotificationConfig model."""

    def test_minimal_config(self) -> None:
        """Test creating minimal config."""
        config = NotificationConfig(
            name="slack-channel",
            provider=ProviderType.SLACK,
            webhook_url="https://hooks.slack.com/...",
        )
        assert config.name == "slack-channel"
        assert config.provider == ProviderType.SLACK
        assert config.enabled is True
        assert config.events is None

    def test_should_notify_enabled(self) -> None:
        """Test should_notify when enabled."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.WEBHOOK,
            webhook_url="https://example.com",
            enabled=True,
        )
        event = NotificationEvent(
            type=NotificationType.BUILD_SUCCESS,
            title="Test",
        )
        assert config.should_notify(event) is True

    def test_should_notify_disabled(self) -> None:
        """Test should_notify when disabled."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.WEBHOOK,
            webhook_url="https://example.com",
            enabled=False,
        )
        event = NotificationEvent(
            type=NotificationType.BUILD_SUCCESS,
            title="Test",
        )
        assert config.should_notify(event) is False

    def test_should_notify_filtered_events(self) -> None:
        """Test should_notify with event filter."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.WEBHOOK,
            webhook_url="https://example.com",
            events=[NotificationType.BUILD_SUCCESS, NotificationType.BUILD_FAILURE],
        )
        success_event = NotificationEvent(
            type=NotificationType.BUILD_SUCCESS,
            title="Test",
        )
        release_event = NotificationEvent(
            type=NotificationType.RELEASE_CREATED,
            title="Test",
        )
        assert config.should_notify(success_event) is True
        assert config.should_notify(release_event) is False

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.SLACK,
            webhook_url="https://hooks.slack.com/...",
            events=[NotificationType.BUILD_SUCCESS],
        )
        data = config.to_dict()
        assert data["name"] == "test"
        assert data["provider"] == "slack"
        assert data["events"] == ["build_success"]

    def test_from_dict(self) -> None:
        """Test creation from dictionary."""
        data = {
            "name": "test",
            "provider": "discord",
            "webhook_url": "https://discord.com/api/webhooks/...",
            "events": ["build_success", "build_failure"],
        }
        config = NotificationConfig.from_dict(data)
        assert config.name == "test"
        assert config.provider == ProviderType.DISCORD
        assert len(config.events) == 2


class TestNotificationResult:
    """Tests for NotificationResult model."""

    def test_success_result(self) -> None:
        """Test successful result."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.WEBHOOK,
            webhook_url="https://example.com",
        )
        result = NotificationResult(
            config=config,
            success=True,
            response_code=200,
        )
        assert result.success is True
        assert result.error is None

    def test_failure_result(self) -> None:
        """Test failed result."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.WEBHOOK,
            webhook_url="https://example.com",
        )
        result = NotificationResult(
            config=config,
            success=False,
            error="Connection refused",
        )
        assert result.success is False
        assert result.error == "Connection refused"

    def test_to_dict(self) -> None:
        """Test conversion to dictionary."""
        config = NotificationConfig(
            name="slack-main",
            provider=ProviderType.SLACK,
            webhook_url="https://hooks.slack.com/...",
        )
        result = NotificationResult(
            config=config,
            success=True,
            response_code=200,
        )
        data = result.to_dict()
        assert data["channel"] == "slack-main"
        assert data["provider"] == "slack"
        assert data["success"] is True


class TestSlackProvider:
    """Tests for SlackProvider."""

    def test_build_payload(self) -> None:
        """Test building Slack payload."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.SLACK,
            webhook_url="https://hooks.slack.com/...",
        )
        provider = SlackProvider(config)

        event = NotificationEvent(
            type=NotificationType.BUILD_SUCCESS,
            title="Build Complete",
            message="Built mypackage 1.0.0",
            status="success",
            data={"version": "1.0.0", "package": "mypackage"},
        )

        payload = provider.build_payload(event)

        assert "text" in payload
        assert "attachments" in payload
        assert len(payload["attachments"]) == 1
        assert payload["attachments"][0]["title"] == "Build Complete"
        assert payload["attachments"][0]["color"] == "#4CAF50"  # success color


class TestDiscordProvider:
    """Tests for DiscordProvider."""

    def test_build_payload(self) -> None:
        """Test building Discord payload."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.DISCORD,
            webhook_url="https://discord.com/api/webhooks/...",
        )
        provider = DiscordProvider(config)

        event = NotificationEvent(
            type=NotificationType.BUILD_FAILURE,
            title="Build Failed",
            message="Error in compilation",
            status="error",
            data={"error": "Missing dependency"},
        )

        payload = provider.build_payload(event)

        assert "embeds" in payload
        assert len(payload["embeds"]) == 1
        embed = payload["embeds"][0]
        assert "Build Failed" in embed["title"]
        assert embed["color"] == 0xF44336  # error color


class TestWebhookProvider:
    """Tests for WebhookProvider."""

    def test_build_payload(self) -> None:
        """Test building generic webhook payload."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.WEBHOOK,
            webhook_url="https://example.com/webhook",
        )
        provider = WebhookProvider(config)

        event = NotificationEvent(
            type=NotificationType.CUSTOM,
            title="Custom Event",
            message="Test message",
        )

        payload = provider.build_payload(event)

        assert "event" in payload
        assert payload["event"]["type"] == "custom"
        assert payload["source"] == "headless-wheel-builder"


class TestGetProvider:
    """Tests for get_provider function."""

    def test_get_slack_provider(self) -> None:
        """Test getting Slack provider."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.SLACK,
            webhook_url="https://hooks.slack.com/...",
        )
        provider = get_provider(config)
        assert isinstance(provider, SlackProvider)

    def test_get_discord_provider(self) -> None:
        """Test getting Discord provider."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.DISCORD,
            webhook_url="https://discord.com/api/webhooks/...",
        )
        provider = get_provider(config)
        assert isinstance(provider, DiscordProvider)

    def test_get_webhook_provider(self) -> None:
        """Test getting generic webhook provider."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.WEBHOOK,
            webhook_url="https://example.com",
        )
        provider = get_provider(config)
        assert isinstance(provider, WebhookProvider)

    def test_get_unsupported_provider(self) -> None:
        """Test error for unsupported provider."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.EMAIL,
            webhook_url="email@example.com",
        )
        with pytest.raises(ValueError, match="Unsupported provider"):
            get_provider(config)


class TestNotificationSender:
    """Tests for NotificationSender."""

    def test_init_empty(self) -> None:
        """Test sender with no channels."""
        sender = NotificationSender()
        assert len(sender.channels) == 0

    def test_add_channel(self) -> None:
        """Test adding a channel."""
        sender = NotificationSender()
        config = NotificationConfig(
            name="test",
            provider=ProviderType.WEBHOOK,
            webhook_url="https://example.com",
        )
        sender.add_channel(config)
        assert len(sender.channels) == 1

    def test_add_channel_replaces_existing(self) -> None:
        """Test adding channel with same name replaces."""
        sender = NotificationSender()
        config1 = NotificationConfig(
            name="test",
            provider=ProviderType.WEBHOOK,
            webhook_url="https://example1.com",
        )
        config2 = NotificationConfig(
            name="test",
            provider=ProviderType.WEBHOOK,
            webhook_url="https://example2.com",
        )
        sender.add_channel(config1)
        sender.add_channel(config2)
        assert len(sender.channels) == 1
        assert sender.channels[0].webhook_url == "https://example2.com"

    def test_remove_channel(self) -> None:
        """Test removing a channel."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.WEBHOOK,
            webhook_url="https://example.com",
        )
        sender = NotificationSender(channels=[config])
        removed = sender.remove_channel("test")
        assert removed is True
        assert len(sender.channels) == 0

    def test_remove_channel_not_found(self) -> None:
        """Test removing non-existent channel."""
        sender = NotificationSender()
        removed = sender.remove_channel("nonexistent")
        assert removed is False

    @pytest.mark.asyncio
    async def test_send_no_applicable_channels(self) -> None:
        """Test send with no applicable channels."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.WEBHOOK,
            webhook_url="https://example.com",
            events=[NotificationType.BUILD_FAILURE],  # Only failures
        )
        sender = NotificationSender(channels=[config])

        event = NotificationEvent(
            type=NotificationType.BUILD_SUCCESS,  # Success event
            title="Test",
        )

        results = await sender.send(event)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_send_mocked(self) -> None:
        """Test send with mocked HTTP."""
        config = NotificationConfig(
            name="test",
            provider=ProviderType.WEBHOOK,
            webhook_url="https://example.com",
        )
        sender = NotificationSender(channels=[config])

        event = NotificationEvent(
            type=NotificationType.BUILD_SUCCESS,
            title="Test",
        )

        with patch("headless_wheel_builder.notify.providers.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.text = "OK"

            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None

            mock_client.return_value = mock_instance

            results = await sender.send(event)

            assert len(results) == 1
            assert results[0].success is True
