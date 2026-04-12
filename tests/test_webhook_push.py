"""Tests for GitHub webhook push event handling."""

import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_webhook_push_subscribed_repo(plugin_instance, mock_send_message):
    """Test that push event to subscribed repo sends notification."""
    # Setup: subscribe to repo
    plugin_instance.subscriptions = {"owner/repo": ["user123"]}

    # Setup: push payload
    payload = {
        "repository": {"full_name": "owner/repo"},
        "ref": "refs/heads/main",
        "pusher": {"name": "testuser"},
        "commits": [{"message": "test commit"}],
        "compare": "https://github.com/owner/repo/compare/abc...def",
        "forced": False,
    }

    # Execute
    await plugin_instance.handle_webhook_event("push", payload)

    # Verify: send_message is called once
    assert mock_send_message.called
    assert mock_send_message.call_count == 1

    # Verify: message contains key information
    call_args = mock_send_message.call_args
    message = call_args[0][1].chain[0].text
    assert "Push" in message
    assert "main" in message
    assert "testuser" in message


@pytest.mark.asyncio
async def test_webhook_push_unsubscribed_repo(plugin_instance, mock_send_message):
    """Test that push event to unsubscribed repo does not send notification."""
    # Setup: no subscriptions
    plugin_instance.subscriptions = {"other/repo": ["user123"]}

    # Setup: push payload for unsubscribed repo
    payload = {
        "repository": {"full_name": "owner/repo"},
        "ref": "refs/heads/main",
        "pusher": {"name": "testuser"},
        "commits": [{"message": "test commit"}],
        "compare": "https://github.com/owner/repo/compare/abc...def",
        "forced": False,
    }

    # Execute
    await plugin_instance.handle_webhook_event("push", payload)

    # Verify: send_message is not called
    assert not mock_send_message.called
    assert mock_send_message.call_count == 0


@pytest.mark.asyncio
async def test_webhook_push_tag_push(plugin_instance, mock_send_message):
    """Test that tag push does not send notification."""
    # Setup: subscribe to repo
    plugin_instance.subscriptions = {"owner/repo": ["user123"]}

    # Setup: tag push payload
    payload = {
        "repository": {"full_name": "owner/repo"},
        "ref": "refs/tags/v1.0.0",
        "pusher": {"name": "testuser"},
        "commits": [{"message": "tag commit"}],
        "compare": "https://github.com/owner/repo/compare/abc...def",
        "forced": False,
    }

    # Execute
    await plugin_instance.handle_webhook_event("push", payload)

    # Verify: send_message is not called (tag push should be ignored)
    assert not mock_send_message.called
    assert mock_send_message.call_count == 0


@pytest.mark.asyncio
async def test_webhook_push_deleted_branch(plugin_instance, mock_send_message):
    """Test that deleted branch push does not send notification."""
    # Setup: subscribe to repo
    plugin_instance.subscriptions = {"owner/repo": ["user123"]}

    # Setup: branch deletion push payload (no commits means deletion)
    payload = {
        "repository": {"full_name": "owner/repo"},
        "ref": "refs/heads/feature-branch",
        "pusher": {"name": "testuser"},
        "commits": [],  # Empty commits indicates deletion
        "compare": "https://github.com/owner/repo/compare/abc...def",
        "forced": False,
    }

    # Execute
    await plugin_instance.handle_webhook_event("push", payload)

    # Verify: send_message is not called (no commits = branch deletion)
    assert not mock_send_message.called
    assert mock_send_message.call_count == 0


@pytest.mark.asyncio
async def test_webhook_push_force_push(plugin_instance, mock_send_message):
    """Test that force push shows warning."""
    # Setup: subscribe to repo
    plugin_instance.subscriptions = {"owner/repo": ["user123"]}

    # Setup: force push payload
    payload = {
        "repository": {"full_name": "owner/repo"},
        "ref": "refs/heads/main",
        "pusher": {"name": "testuser"},
        "commits": [{"message": "force push commit"}],
        "compare": "https://github.com/owner/repo/compare/abc...def",
        "forced": True,  # Force push indicator
    }

    # Execute
    await plugin_instance.handle_webhook_event("push", payload)

    # Verify: send_message is called once
    assert mock_send_message.called
    assert mock_send_message.call_count == 1

    # Verify: message contains force push warning
    call_args = mock_send_message.call_args
    message = call_args[0][1].chain[0].text
    assert "Force Push" in message or "⚠️" in message
    assert "main" in message
    assert "testuser" in message
