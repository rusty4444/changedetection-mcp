"""Tests for the query parameters sent to the snapshot-difference endpoint."""

import httpx

from changedetection_mcp import client


class _FakeResponse:
    text = "(added) Version 5.19.6"

    def raise_for_status(self) -> None:
        pass


def _capture_params(monkeypatch) -> dict:
    captured: dict = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params", {})
        return _FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)
    return captured


def test_no_markup_defaults_to_false(monkeypatch):
    # Sending no_markup=true makes the server wrap every line in
    # @added_PLACEMARKER_OPEN/@removed_PLACEMARKER_CLOSE sentinels instead of
    # readable "(added) ..." prefixes.
    captured = _capture_params(monkeypatch)

    client.get_snapshot_diff("watch-1", "previous", "latest")

    assert captured["params"]["no_markup"] == "false"


def test_default_params_request_a_changes_only_text_diff(monkeypatch):
    captured = _capture_params(monkeypatch)

    client.get_snapshot_diff("watch-1", "previous", "latest")

    assert captured["params"]["format"] == "text"
    assert captured["params"]["changesOnly"] == "true"
    assert captured["params"]["ignoreWhitespace"] == "true"


def test_no_markup_can_still_be_opted_into(monkeypatch):
    captured = _capture_params(monkeypatch)

    client.get_snapshot_diff("watch-1", "previous", "latest", no_markup=True)

    assert captured["params"]["no_markup"] == "true"


def test_timestamps_are_placed_in_the_request_path(monkeypatch):
    captured = _capture_params(monkeypatch)

    client.get_snapshot_diff("watch-1", "1767507456", "1785824349")

    assert captured["url"].endswith("/watch/watch-1/difference/1767507456/1785824349")
