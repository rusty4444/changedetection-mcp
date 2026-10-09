"""Tests for normalising ChangeDetection.io's UUID-keyed API responses."""

import httpx

from changedetection_mcp import client, tools


# ── Watch lists ──────────────────────────────────────────────────────

# Shape returned by /watch and /search: keyed by UUID, and the watch body
# carries no "uuid" of its own.
UUID_KEYED_WATCHES = {
    "11111111-1111-4111-8111-111111111111": {"title": "First", "url": "https://example.com/1"},
    "22222222-2222-4222-8222-222222222222": {"title": "Second", "url": "https://example.com/2"},
}


def test_uuid_key_is_folded_into_each_watch():
    watches = client._watches_to_list(UUID_KEYED_WATCHES)

    assert [w["uuid"] for w in watches] == list(UUID_KEYED_WATCHES)
    assert [w["title"] for w in watches] == ["First", "Second"]


def test_uuid_in_body_wins_over_the_key():
    watches = client._watches_to_list({"stale-key": {"uuid": "real-uuid", "title": "T"}})

    assert watches[0]["uuid"] == "real-uuid"


def test_list_shaped_response_passes_through():
    already_a_list = [{"uuid": "u1", "title": "T"}]

    assert client._watches_to_list(already_a_list) == already_a_list


def test_formatted_watch_list_shows_uuids_not_placeholders():
    rendered = tools._format_watch_list(client._watches_to_list(UUID_KEYED_WATCHES))

    # Every uuid-taking tool is unreachable if this regresses to "?".
    assert "`11111111-1111-4111-8111-111111111111`" in rendered
    assert "`?`" not in rendered


# ── History ──────────────────────────────────────────────────────────


def _history_via_client(monkeypatch, payload) -> list[str]:
    """Drive client.get_watch_history() against a stubbed API response."""

    class _FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self):
            return payload

    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: _FakeResponse())
    return client.get_watch_history("watch-1")


def test_history_dict_is_reduced_to_timestamps_oldest_first(monkeypatch):
    # /watch/<uuid>/history returns {timestamp: snapshot_path}, so the raw
    # dict cannot be sliced for "most recent N" — tools.py does timestamps[-20:].
    timestamps = _history_via_client(
        monkeypatch,
        {
            "1771320086": "/datastore/b.txt",
            "1767507456": "/datastore/a.txt.br",
            "1785824349": "/datastore/c.txt",
        },
    )

    assert timestamps == ["1767507456", "1771320086", "1785824349"]
    assert timestamps[-2:] == ["1771320086", "1785824349"]


def test_history_sorts_numerically_not_lexically(monkeypatch):
    # Lexical ordering would put "9..." after "10..." and mis-report "latest".
    timestamps = _history_via_client(
        monkeypatch, {"9999999999": "/late.txt", "10000000000": "/later.txt"}
    )

    assert timestamps[-1] == "10000000000"


def test_history_tolerates_non_numeric_keys(monkeypatch):
    timestamps = _history_via_client(monkeypatch, {"latest": "/l.txt", "1767507456": "/a.txt"})

    assert timestamps == ["1767507456", "latest"]
