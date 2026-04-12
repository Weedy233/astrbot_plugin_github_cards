"""Tests for polling push event detection."""

import sys

import pytest

if sys.version_info < (3, 10):
    pytest.skip("Plugin requires Python 3.10+", allow_module_level=True)

import json
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_polling_push_detects_new_events(plugin_instance, mock_send_message):
    plugin_instance.subscriptions = {"owner/repo": ["user123"]}
    plugin_instance.last_push_event_ids = {"owner/repo": []}

    mock_events = [
        {
            "id": "123456",
            "type": "PushEvent",
            "created_at": "2024-01-01T00:00:00Z",
            "actor": {"login": "developer"},
            "payload": {
                "ref": "refs/heads/main",
                "commits": [{"message": "test commit", "sha": "abc123"}],
                "compare": "https://github.com/owner/repo/compare/abc...def",
            },
        }
    ]

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_events)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_get.return_value = mock_response

        await plugin_instance._check_all_repos()

        assert mock_send_message.called
        assert "123456" in plugin_instance.last_push_event_ids["owner/repo"]


@pytest.mark.asyncio
async def test_polling_push_dedup_by_event_id(plugin_instance, mock_send_message):
    plugin_instance.subscriptions = {"owner/repo": ["user123"]}
    plugin_instance.last_push_event_ids = {"owner/repo": ["123456"]}

    mock_events = [
        {
            "id": "123456",
            "type": "PushEvent",
            "created_at": "2024-01-01T00:00:00Z",
            "actor": {"login": "developer"},
            "payload": {
                "ref": "refs/heads/main",
                "commits": [{"message": "test commit", "sha": "abc123"}],
                "compare": "https://github.com/owner/repo/compare/abc...def",
            },
        }
    ]

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_events)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_get.return_value = mock_response

        mock_send_message.reset_mock()

        await plugin_instance._check_all_repos()

        assert not mock_send_message.called


@pytest.mark.asyncio
async def test_polling_push_restart_persistence(
    plugin_instance, mock_send_message, tmp_path
):
    data_dir = tmp_path / "data"
    polling_state_file = data_dir / "github_polling_state.json"

    initial_state = {
        "last_check_time": {"owner/repo": "2024-01-01T00:00:00"},
        "last_push_event_ids": {"owner/repo": ["111111", "222222"]},
    }

    polling_state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(polling_state_file, "w") as f:
        json.dump(initial_state, f)

    from main import MyPlugin

    mock_context = MagicMock()
    mock_context.send_message = AsyncMock(return_value=None)

    new_plugin = MyPlugin(mock_context, {"enable_webhook": False})
    new_plugin.subscriptions = {"owner/repo": ["user123"]}

    assert "owner/repo" in new_plugin.last_push_event_ids
    assert "111111" in new_plugin.last_push_event_ids["owner/repo"]
    assert "222222" in new_plugin.last_push_event_ids["owner/repo"]

    mock_events = [
        {
            "id": "111111",
            "type": "PushEvent",
            "created_at": "2024-01-01T00:00:00Z",
            "actor": {"login": "developer"},
            "payload": {
                "ref": "refs/heads/main",
                "commits": [{"message": "old commit"}],
            },
        },
        {
            "id": "333333",
            "type": "PushEvent",
            "created_at": "2024-01-02T00:00:00Z",
            "actor": {"login": "developer"},
            "payload": {
                "ref": "refs/heads/main",
                "commits": [{"message": "new commit"}],
            },
        },
    ]

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_events)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_get.return_value = mock_response

        mock_context.send_message.reset_mock()

        await new_plugin._check_all_repos()

        assert mock_context.send_message.call_count == 1


@pytest.mark.asyncio
async def test_polling_push_multiple_events(plugin_instance, mock_send_message):
    plugin_instance.subscriptions = {"owner/repo": ["user123"]}
    plugin_instance.last_push_event_ids = {"owner/repo": []}

    mock_events = [
        {
            "id": "333333",
            "type": "PushEvent",
            "created_at": "2024-01-03T00:00:00Z",
            "actor": {"login": "developer"},
            "payload": {
                "ref": "refs/heads/main",
                "commits": [{"message": "third commit"}],
            },
        },
        {
            "id": "111111",
            "type": "PushEvent",
            "created_at": "2024-01-01T00:00:00Z",
            "actor": {"login": "developer"},
            "payload": {
                "ref": "refs/heads/main",
                "commits": [{"message": "first commit"}],
            },
        },
        {
            "id": "222222",
            "type": "PushEvent",
            "created_at": "2024-01-02T00:00:00Z",
            "actor": {"login": "developer"},
            "payload": {
                "ref": "refs/heads/main",
                "commits": [{"message": "second commit"}],
            },
        },
    ]

    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_events)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_get.return_value = mock_response

        push_events = await plugin_instance._fetch_push_events("owner/repo")

        assert len(push_events) == 3
        assert push_events[0]["id"] == "111111"
        assert push_events[1]["id"] == "222222"
        assert push_events[2]["id"] == "333333"


@pytest.mark.asyncio
async def test_polling_push_existing_behavior_preserved(
    plugin_instance, mock_send_message
):
    plugin_instance.subscriptions = {"owner/repo": ["user123"]}
    plugin_instance.last_check_time = {"owner/repo": "2024-01-01T00:00:00"}
    plugin_instance.last_push_event_ids = {"owner/repo": []}

    mock_issues = [
        {
            "id": 999,
            "number": 42,
            "title": "New Issue",
            "user": {"login": "reporter"},
            "created_at": "2024-06-01T00:00:00Z",
            "html_url": "https://github.com/owner/repo/issues/42",
        }
    ]

    mock_events = [
        {
            "id": "123456",
            "type": "PushEvent",
            "created_at": "2024-06-01T00:00:00Z",
            "actor": {"login": "developer"},
            "payload": {
                "ref": "refs/heads/main",
                "commits": [{"message": "test commit"}],
            },
        }
    ]

    call_count = {"issues": 0, "events": 0}

    async def mock_get_side_effect(url, **kwargs):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        if "issues" in url:
            call_count["issues"] += 1
            mock_response.json = AsyncMock(return_value=mock_issues)
        else:
            call_count["events"] += 1
            mock_response.json = AsyncMock(return_value=mock_events)

        return mock_response

    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = AsyncMock()
        mock_session.get = mock_get_side_effect
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        await plugin_instance._check_all_repos()

        assert mock_send_message.call_count >= 2
        assert call_count["issues"] >= 1
        assert call_count["events"] >= 1
