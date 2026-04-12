"""Pytest fixtures for GitHub Cards plugin testing."""

import os
import sys
from asyncio import Queue
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from astrbot.core.config.astrbot_config import AstrBotConfig
    from astrbot.core.db.sqlite import SQLiteDatabase
    from astrbot.core.star.context import Context

    HAS_ASTRBOT = True
except ImportError:
    HAS_ASTRBOT = False
    AstrBotConfig = MagicMock
    SQLiteDatabase = MagicMock
    Context = MagicMock

if not HAS_ASTRBOT:
    mock_astrbot = MagicMock()
    mock_astrbot.api = MagicMock()
    mock_astrbot.api.message_components = MagicMock()
    mock_astrbot.api.message_components.Plain = MagicMock
    mock_astrbot.api.event = MagicMock()
    mock_astrbot.api.event.AstrMessageEvent = MagicMock
    mock_astrbot.api.event.MessageChain = MagicMock
    mock_astrbot.api.event.filter = MagicMock()
    mock_astrbot.api.star = MagicMock()
    mock_astrbot.api.star.Context = MagicMock
    mock_astrbot.api.star.register = lambda *args, **kwargs: lambda cls: cls
    mock_astrbot.api.AstrBotConfig = MagicMock
    mock_astrbot.api.logger = MagicMock()

    sys.modules["astrbot"] = mock_astrbot
    sys.modules["astrbot.api"] = mock_astrbot.api
    sys.modules["astrbot.api.message_components"] = mock_astrbot.api.message_components
    sys.modules["astrbot.api.event"] = mock_astrbot.api.event
    sys.modules["astrbot.api.star"] = mock_astrbot.api.star


@pytest.fixture
def mock_config(tmp_path: Path) -> dict:
    return {
        "github_token": "test_github_token",
        "check_interval": 1,
        "use_lowercase_repo": True,
        "auto_resolve_links": True,
        "enable_webhook": False,
        "webhook_host": "0.0.0.0",
        "webhook_port": 6192,
        "webhook_secret": "",
        "webhook_path": "/github/webhook",
        "enable_push_notification": True,
        "data_dir": str(tmp_path / "data"),
    }


@pytest.fixture
def mock_astrbot_config(tmp_path: Path):
    if not HAS_ASTRBOT:
        config = MagicMock()
        config.plugin_store_path = str(tmp_path / "plugins")
        config.data_dir = str(tmp_path / "data")
        return config
    config = AstrBotConfig()
    config.plugin_store_path = str(tmp_path / "plugins")
    config.data_dir = str(tmp_path / "data")
    return config


@pytest.fixture
def mock_db(tmp_path: Path):
    if not HAS_ASTRBOT:
        return MagicMock()
    db_path = tmp_path / "test_db.db"
    return SQLiteDatabase(str(db_path))


@pytest.fixture
def mock_context(
    tmp_path: Path,
    mock_astrbot_config,
    mock_db,
) -> MagicMock:
    event_queue = Queue()

    provider_manager = MagicMock()
    platform_manager = MagicMock()
    conversation_manager = MagicMock()
    message_history_manager = MagicMock()
    persona_manager = MagicMock()
    astrbot_config_mgr = MagicMock()

    if HAS_ASTRBOT:
        context = Context(
            event_queue,
            mock_astrbot_config,
            mock_db,
            provider_manager,
            platform_manager,
            conversation_manager,
            message_history_manager,
            persona_manager,
            astrbot_config_mgr,
        )
    else:
        context = MagicMock()
        context.send_message = AsyncMock(return_value=None)

    context.send_message = AsyncMock(return_value=None)

    return context


@pytest.fixture
def mock_send_message(mock_context: MagicMock) -> AsyncMock:
    return mock_context.send_message


@pytest.fixture
def plugin_instance(
    mock_context: MagicMock,
    mock_config: dict,
    tmp_path: Path,
):
    import importlib

    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)

    sys.path.insert(0, str(Path(__file__).parent.parent))

    if "astrbot_plugin_github_cards" in sys.modules:
        del sys.modules["astrbot_plugin_github_cards"]
    if "astrbot_plugin_github_cards.main" in sys.modules:
        del sys.modules["astrbot_plugin_github_cards.main"]
    if "astrbot_plugin_github_cards.formatters" in sys.modules:
        del sys.modules["astrbot_plugin_github_cards.formatters"]

    main_module = importlib.import_module("astrbot_plugin_github_cards.main")
    MyPlugin = main_module.MyPlugin
    plugin = MyPlugin(mock_context, mock_config)

    plugin.SUBSCRIPTION_FILE = str(data_dir / "github_subscriptions.json")
    plugin.DEFAULT_REPO_FILE = str(data_dir / "github_default_repos.json")
    plugin.LINK_SETTINGS_FILE = str(data_dir / "github_link_settings.json")
    plugin.POLLING_STATE_FILE = str(data_dir / "github_polling_state.json")

    return plugin


@pytest.fixture
def sample_github_repo() -> dict:
    return {
        "id": 123456789,
        "name": "AstrBot",
        "full_name": "Soulter/AstrBot",
        "owner": {
            "login": "Soulter",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345678",
        },
        "description": "A multi-platform LLM chatbot framework",
        "stargazers_count": 1337,
        "forks_count": 100,
        "open_issues_count": 42,
        "language": "Python",
        "html_url": "https://github.com/Soulter/AstrBot",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-06-01T00:00:00Z",
    }


@pytest.fixture
def sample_github_issue() -> dict:
    return {
        "id": 987654321,
        "number": 42,
        "title": "Add new feature",
        "body": "This is a sample issue description",
        "user": {
            "login": "contributor",
            "avatar_url": "https://avatars.githubusercontent.com/u/87654321",
        },
        "state": "open",
        "comments": 5,
        "created_at": "2024-06-01T00:00:00Z",
        "updated_at": "2024-06-02T00:00:00Z",
        "html_url": "https://github.com/Soulter/AstrBot/issues/42",
    }


@pytest.fixture
def sample_github_pr() -> dict:
    return {
        "id": 111111111,
        "number": 36,
        "title": "Fix bug in feature X",
        "body": "This PR fixes a critical bug",
        "user": {
            "login": "developer",
            "avatar_url": "https://avatars.githubusercontent.com/u/11111111",
        },
        "state": "open",
        "comments": 3,
        "commits": 5,
        "additions": 100,
        "deletions": 20,
        "changed_files": 8,
        "created_at": "2024-06-01T00:00:00Z",
        "updated_at": "2024-06-02T00:00:00Z",
        "head": {
            "ref": "feature-branch",
            "sha": "abc123def456",
        },
        "base": {
            "ref": "main",
            "sha": "789xyz000",
        },
        "html_url": "https://github.com/Soulter/AstrBot/pull/36",
    }


@pytest.fixture
def sample_subscription_data() -> dict:
    return {
        "group_123": ["Soulter/AstrBot", "Soulter/astrbot_plugin_github_cards"],
        "group_456": ["facebook/react"],
    }


@pytest.fixture
def sample_default_repos_data() -> dict:
    return {
        "user_789": "Soulter/AstrBot",
        "group_123": "facebook/react",
    }


@pytest.fixture
def sample_link_settings_data() -> dict:
    return {
        "user_789": True,
        "group_123": False,
    }
