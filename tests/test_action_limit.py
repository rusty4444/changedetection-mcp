import os

from changedetection_mcp import tools


def setup_function():
    tools._watch_action_budgets.clear()


def teardown_function():
    tools._watch_action_budgets.clear()
    os.environ.pop("CHANGEDETECTION_MCP_ACTION_LIMIT_PER_WATCH", None)


def test_diff_arms_default_per_watch_action_limit(monkeypatch):
    monkeypatch.delenv("CHANGEDETECTION_MCP_ACTION_LIMIT_PER_WATCH", raising=False)

    message = tools._arm_watch_action_limit("watch-1", None)

    assert "armed" in message
    assert "3 mutating actions" in message
    assert tools._consume_watch_action("watch-1", "recheck_watch") is None
    assert tools._consume_watch_action("watch-1", "update_watch") is None
    assert tools._consume_watch_action("watch-1", "delete_watch") is None

    blocked = tools._consume_watch_action("watch-1", "recheck_watch")

    assert blocked is not None
    assert "Action limit reached for watch `watch-1`" in blocked
    assert "recheck_watch" in blocked


def test_explicit_action_limit_overrides_default(monkeypatch):
    monkeypatch.setenv("CHANGEDETECTION_MCP_ACTION_LIMIT_PER_WATCH", "9")

    message = tools._arm_watch_action_limit("watch-1", 1)

    assert "1 mutating action" in message
    assert tools._consume_watch_action("watch-1", "update_watch") is None
    assert tools._consume_watch_action("watch-1", "delete_watch") is not None


def test_zero_action_limit_disables_fuse_for_watch(monkeypatch):
    monkeypatch.setenv("CHANGEDETECTION_MCP_ACTION_LIMIT_PER_WATCH", "1")

    message = tools._arm_watch_action_limit("watch-1", 0)

    assert "disabled" in message
    assert tools._consume_watch_action("watch-1", "update_watch") is None
    assert tools._consume_watch_action("watch-1", "delete_watch") is None


def test_env_action_limit_is_clamped_to_zero_for_negative_values(monkeypatch):
    monkeypatch.setenv("CHANGEDETECTION_MCP_ACTION_LIMIT_PER_WATCH", "-4")

    message = tools._arm_watch_action_limit("watch-1", None)

    assert "disabled" in message
    assert tools._consume_watch_action("watch-1", "update_watch") is None
