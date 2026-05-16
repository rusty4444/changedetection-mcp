"""API client for ChangeDetection.io REST API."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import httpx

_BASE_URL: str | None = None
_API_KEY: str | None = None


def configure(base_url: str, api_key: str) -> None:
    """Set credentials from caller-provided values (env vars are fallback)."""
    global _BASE_URL, _API_KEY
    _BASE_URL = base_url.rstrip("/")
    _API_KEY = api_key


def _get_base_url() -> str:
    url = _BASE_URL or os.environ.get("CHANGEDETECTION_BASE_URL", "http://localhost:5000")
    return url.rstrip("/") + "/api/v1"


def _get_api_key() -> str:
    return _API_KEY or os.environ.get("CHANGEDETECTION_API_KEY", "")


def _headers() -> dict[str, str]:
    return {
        "x-api-key": _get_api_key(),
        "Content-Type": "application/json",
    }


# ── Watches ──────────────────────────────────────────────────────────


def list_watches(tag: str | None = None) -> dict[str, Any]:
    """Return all watches.  Optionally filter by tag."""
    params: dict[str, str] = {}
    if tag:
        params["tag"] = tag
    r = httpx.get(f"{_get_base_url()}/watch", headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def get_watch(uuid: str) -> dict[str, Any]:
    """Return a single watch's full config + state."""
    r = httpx.get(f"{_get_base_url()}/watch/{uuid}", headers=_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


def create_watch(url: str, **kwargs: Any) -> dict[str, Any]:
    """Create a new watch.  Returns the created watch dict."""
    body: dict[str, Any] = {"url": url}
    body.update(kwargs)
    r = httpx.post(f"{_get_base_url()}/watch", headers=_headers(), json=body, timeout=15)
    r.raise_for_status()
    return r.json()


def update_watch(uuid: str, **kwargs: Any) -> dict[str, Any]:
    """Update a watch.  Supports partial updates (only keys you provide change)."""
    body = {k: v for k, v in kwargs.items() if v is not None}
    r = httpx.put(f"{_get_base_url()}/watch/{uuid}", headers=_headers(), json=body, timeout=15)
    r.raise_for_status()
    return r.json()


def delete_watch(uuid: str) -> dict[str, Any]:
    """Delete a watch and all its history."""
    r = httpx.delete(f"{_get_base_url()}/watch/{uuid}", headers=_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


def recheck_watch(uuid: str) -> dict[str, Any]:
    """Trigger an immediate recheck and return updated watch."""
    r = httpx.get(
        f"{_get_base_url()}/watch/{uuid}",
        headers=_headers(),
        params={"recheck": "1"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


# ── History & diffs ──────────────────────────────────────────────────


def get_watch_history(uuid: str) -> list[str]:
    """Return list of snapshot timestamps for a watch."""
    r = httpx.get(f"{_get_base_url()}/watch/{uuid}/history", headers=_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


def get_snapshot_diff(
    uuid: str,
    from_timestamp: str,
    to_timestamp: str,
    *,
    format: str = "text",
    no_markup: bool = True,
    changes_only: bool = True,
    ignore_whitespace: bool = True,
) -> str:
    """Get a human-readable diff between two snapshots."""
    params = {
        "format": format,
        "no_markup": str(no_markup).lower(),
        "changesOnly": str(changes_only).lower(),
        "ignoreWhitespace": str(ignore_whitespace).lower(),
    }
    r = httpx.get(
        f"{_get_base_url()}/watch/{uuid}/difference/{from_timestamp}/{to_timestamp}",
        headers=_headers(),
        params=params,
        timeout=15,
    )
    r.raise_for_status()
    return r.text


# ── Tags ─────────────────────────────────────────────────────────────


def list_tags() -> dict[str, Any]:
    """List all tags/groups."""
    r = httpx.get(f"{_get_base_url()}/tags", headers=_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


def create_tag(title: str) -> dict[str, Any]:
    """Create a new tag/group."""
    r = httpx.post(f"{_get_base_url()}/tag", headers=_headers(), json={"title": title}, timeout=15)
    r.raise_for_status()
    return r.json()


# ── Search ───────────────────────────────────────────────────────────


def search_watches(query: str, tag: str | None = None, partial: bool = True) -> dict[str, Any]:
    """Search watches by URL or title."""
    params: dict[str, str] = {"q": query}
    if tag:
        params["tag"] = tag
    if partial:
        params["partial"] = "1"
    r = httpx.get(f"{_get_base_url()}/search", headers=_headers(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()


# ── System ───────────────────────────────────────────────────────────


def get_system_info() -> dict[str, Any]:
    """Return server health and stats."""
    r = httpx.get(f"{_get_base_url()}/systeminfo", headers=_headers(), timeout=10)
    r.raise_for_status()
    return r.json()
