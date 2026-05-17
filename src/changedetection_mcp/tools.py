"""MCP server tools for ChangeDetection.io."""

from __future__ import annotations

import os
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from . import client as api


DEFAULT_ACTION_LIMIT_PER_WATCH = 3
ACTION_LIMIT_ENV_VAR = "CHANGEDETECTION_MCP_ACTION_LIMIT_PER_WATCH"

# Per-process fuse armed by get_snapshot_diff(). A missing key means no active
# fuse for that watch; a present key tracks the remaining mutating MCP actions.
_watch_action_budgets: dict[str, int] = {}


def register_tools(mcp: FastMCP) -> None:
    """Register all ChangeDetection.io MCP tools."""

    # ── Watches ──────────────────────────────────────────────────────────

    @mcp.tool()
    async def list_watches(
        tag: Annotated[str | None, Field(description="Optional tag name to filter by")] = None,
    ) -> str:
        """List all watched URLs with their current status."""
        try:
            data = api.list_watches(tag=tag)
            return _format_watch_list(data)
        except Exception as e:
            return f"Error listing watches: {e}"

    @mcp.tool()
    async def get_watch(
        uuid: Annotated[str, Field(description="The watch UUID")],
    ) -> str:
        """Get detailed information about a specific watch."""
        try:
            data = api.get_watch(uuid)
            return _format_watch_detail(data)
        except Exception as e:
            return f"Error getting watch {uuid}: {e}"

    @mcp.tool()
    async def create_watch(
        url: Annotated[str, Field(description="The URL to watch for changes")],
        title: Annotated[str | None, Field(description="Optional human-readable title for the watch")] = None,
        tag: Annotated[str | None, Field(description="Optional tag/group name to organise this watch under")] = None,
        minutes_between_checks: Annotated[int | None, Field(description="Check interval in minutes (default: 60). Set null for server default.")] = 60,
        paused: Annotated[bool | None, Field(description="Start paused (True) or active immediately (False, default)")] = False,
    ) -> str:
        """Create a new URL watch to monitor for changes."""
        kwargs: dict[str, Any] = {}
        if title:
            kwargs["title"] = title
        if tag:
            resolved = _resolve_tag_uuid(tag)
            kwargs["tag"] = resolved or tag
        if minutes_between_checks is not None and minutes_between_checks > 0:
            kwargs["time_between_check"] = {
                "hours": minutes_between_checks // 60,
                "minutes": minutes_between_checks % 60,
            }
        if paused is not None:
            kwargs["paused"] = paused
        try:
            data = api.create_watch(url, **kwargs)
            # create_watch only returns {"uuid": "..."}, fetch full detail
            if "uuid" in data and "url" not in data:
                data = api.get_watch(data["uuid"])
            return _format_watch_detail(data)
        except Exception as e:
            return f"Error creating watch: {e}"

    @mcp.tool()
    async def update_watch(
        uuid: Annotated[str, Field(description="The watch UUID")],
        title: Annotated[str | None, Field(description="New title for the watch")] = None,
        url: Annotated[str | None, Field(description="New URL to monitor")] = None,
        paused: Annotated[bool | None, Field(description="Pause (True) or resume (False) the watch")] = None,
        minutes_between_checks: Annotated[int | None, Field(description="New check interval in minutes. Set null to keep existing.")] = None,
        tag: Annotated[str | None, Field(description="New tag / group assignment")] = None,
    ) -> str:
        """Update an existing watch's settings."""
        blocked = _consume_watch_action(uuid, "update_watch")
        if blocked:
            return blocked
        kwargs: dict[str, Any] = {}
        if title is not None:
            kwargs["title"] = title
        if url is not None:
            kwargs["url"] = url
        if paused is not None:
            kwargs["paused"] = paused
        if minutes_between_checks is not None and minutes_between_checks > 0:
            kwargs["time_between_check"] = {
                "hours": minutes_between_checks // 60,
                "minutes": minutes_between_checks % 60,
            }
        if tag is not None:
            resolved = _resolve_tag_uuid(tag)
            kwargs["tag"] = resolved or tag
        try:
            data = api.update_watch(uuid, **kwargs)
            return _format_watch_detail(data)
        except Exception as e:
            return f"Error updating watch {uuid}: {e}"

    @mcp.tool()
    async def delete_watch(
        uuid: Annotated[str, Field(description="The watch UUID to delete")],
    ) -> str:
        """Permanently delete a watch and all its history."""
        blocked = _consume_watch_action(uuid, "delete_watch")
        if blocked:
            return blocked
        try:
            result = api.delete_watch(uuid)
            if result.get("deleted"):
                return f"Deleted watch `{uuid}`"
            return f"Deleted watch {uuid}"
        except Exception as e:
            return f"Error deleting watch {uuid}: {e}"

    @mcp.tool()
    async def recheck_watch(
        uuid: Annotated[str, Field(description="The watch UUID to recheck")],
    ) -> str:
        """Trigger an immediate recheck of a watch URL."""
        blocked = _consume_watch_action(uuid, "recheck_watch")
        if blocked:
            return blocked
        try:
            data = api.recheck_watch(uuid)
            return f"Recheck triggered for {data.get('title', uuid)}\n{_format_watch_detail(data)}"
        except Exception as e:
            return f"Error rechecking watch {uuid}: {e}"

    # ── History & Diffs ─────────────────────────────────────────────────

    @mcp.tool()
    async def get_watch_history(
        uuid: Annotated[str, Field(description="The watch UUID")],
    ) -> str:
        """List the snapshot history (timestamps) for a watched URL."""
        try:
            timestamps = api.get_watch_history(uuid)
            if not timestamps:
                return f"No history found for watch {uuid}"
            lines = [f"• {ts}" for ts in timestamps[-20:]]  # last 20
            total = len(timestamps)
            shown = min(20, total)
            return f"**{total} snapshots** (showing last {shown}):\n" + "\n".join(lines)
        except Exception as e:
            return f"Error getting history for {uuid}: {e}"

    @mcp.tool()
    async def get_snapshot_diff(
        uuid: Annotated[str, Field(description="The watch UUID")],
        from_timestamp: Annotated[str, Field(description="Earlier snapshot timestamp. Use 'latest' or 'previous' as shortcuts.")],
        to_timestamp: Annotated[str, Field(description="Later snapshot timestamp. Use 'latest' or 'previous' as shortcuts.")],
        action_limit: Annotated[
            int | None,
            Field(
                description=(
                    "Maximum mutating actions this MCP server will allow for this "
                    "watch after returning the diff. Defaults to "
                    "CHANGEDETECTION_MCP_ACTION_LIMIT_PER_WATCH (3). Set 0 to disable."
                )
            ),
        ] = None,
    ) -> str:
        """Get the diff between two snapshots of a watched URL."""
        try:
            diff = api.get_snapshot_diff(uuid, from_timestamp, to_timestamp)
            fuse_message = _arm_watch_action_limit(uuid, action_limit)
            return f"{diff}\n\n{fuse_message}" if diff else fuse_message
        except Exception as e:
            return f"Error getting diff: {e}"

    # ── Tags ────────────────────────────────────────────────────────────

    @mcp.tool()
    async def list_tags() -> str:
        """List all tag groups used to organise watches."""
        try:
            data = api.list_tags()
            # Handle both {"tags": [...]} and flat dict formats
            if isinstance(data, dict):
                raw_tags = data.get("tags", [])
                # Check if it's a flat dict keyed by UUID
                if not raw_tags and data:
                    raw_tags = [v for v in data.values() if isinstance(v, dict)]
            else:
                raw_tags = data or []
            if not raw_tags:
                return "No tags configured."
            lines = [
                f"• **{t.get('title', t.get('name', '?'))}** (`{t.get('uuid', t.get('id', '?'))}`)"
                for t in raw_tags
            ]
            return f"**{len(lines)} tags:**\n" + "\n".join(lines)
        except Exception as e:
            return f"Error listing tags: {e}"

    @mcp.tool()
    async def create_tag(
        title: Annotated[str, Field(description="The tag display name")],
    ) -> str:
        """Create a new tag/group for organising watches."""
        try:
            data = api.create_tag(title)
            return f"Created tag: {data.get('title', data.get('name', title))}"
        except Exception as e:
            return f"Error creating tag: {e}"

    # ── Search ──────────────────────────────────────────────────────────

    @mcp.tool()
    async def search_watches(
        query: Annotated[str, Field(description="Search term")],
        tag: Annotated[str | None, Field(description="Optional tag name to narrow results")] = None,
    ) -> str:
        """Search watches by URL or title."""
        try:
            data = api.search_watches(query, tag=tag)
            return _format_watch_list(data)
        except Exception as e:
            return f"Error searching: {e}"

    # ── System ──────────────────────────────────────────────────────────

    @mcp.tool()
    async def get_system_info() -> str:
        """Get ChangeDetection.io server stats and health."""
        try:
            info = api.get_system_info()
            return (
                f"**ChangeDetection.io**\n"
                f"• Version: {info.get('version', '?')}\n"
                f"• Uptime: {info.get('uptime', '?')}\n"
                f"• Watches: {info.get('watch_count', '?')}\n"
                f"• Tags: {info.get('tag_count', '?')}"
            )
        except Exception as e:
            return f"Error getting system info: {e}"


# ── Format helpers ───────────────────────────────────────────────────

# Cache for resolving tag names → UUIDs
_tag_cache: dict[str, str] | None = None


def _default_action_limit_per_watch() -> int:
    """Return the configured default per-watch action limit."""
    raw = os.environ.get(ACTION_LIMIT_ENV_VAR)
    if raw is None or raw == "":
        return DEFAULT_ACTION_LIMIT_PER_WATCH
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_ACTION_LIMIT_PER_WATCH


def _arm_watch_action_limit(uuid: str, action_limit: int | None) -> str:
    """Arm or disable the per-watch mutating-action fuse."""
    limit = _default_action_limit_per_watch() if action_limit is None else max(0, int(action_limit))
    if limit == 0:
        _watch_action_budgets.pop(uuid, None)
        return f"Action fuse disabled for watch `{uuid}`."

    _watch_action_budgets[uuid] = limit
    plural = "action" if limit == 1 else "actions"
    return f"Action fuse armed for watch `{uuid}`: {limit} mutating {plural} remaining."


def _consume_watch_action(uuid: str, action_name: str) -> str | None:
    """Consume one action from an armed watch fuse; return an error if exhausted."""
    remaining = _watch_action_budgets.get(uuid)
    if remaining is None:
        return None
    if remaining <= 0:
        return (
            f"Action limit reached for watch `{uuid}`; `{action_name}` was blocked. "
            "Call `get_snapshot_diff` with a higher `action_limit` to re-arm the fuse, "
            "or with `action_limit=0` to disable it for this watch."
        )

    _watch_action_budgets[uuid] = remaining - 1
    return None


def _resolve_tag_uuid(tag_name: str) -> str | None:
    """Resolve a tag name to its UUID by fetching all tags from the API."""
    global _tag_cache
    try:
        if _tag_cache is None:
            data = api.list_tags()
            _tag_cache = {}
            # Handle both {"tags": [...]} and flat dict formats
            if isinstance(data, dict):
                raw = data.get("tags", [])
                if not raw and data:
                    raw = [v for v in data.values() if isinstance(v, dict)]
            else:
                raw = data or []
            for t in raw:
                name = t.get("title") or t.get("name", "")
                uid = t.get("uuid") or t.get("id", "")
                if name and uid:
                    _tag_cache[name.lower()] = uid
                    _tag_cache[uid.lower()] = uid  # allow passing UUID directly
        return _tag_cache.get(tag_name.lower())
    except Exception:
        return None


def _format_watch_list(data: list[dict[str, Any]]) -> str:
    """Pretty-print a watch list response."""
    if not data:
        return "No watches found."
    lines = []
    for w in data:
        title = w.get("title") or w.get("url", "?")
        uuid = w.get("uuid", w.get("id", "?"))
        status = "⏸ Paused" if w.get("paused") else "▶ Active"
        tag_str = f" [{w.get('tag', '')}]" if w.get("tag") else ""
        last_changed = w.get("last_changed", "")
        changed_str = f" — last changed: {last_changed}" if last_changed else ""
        lines.append(f"• **{title}**{tag_str} — {status} (`{uuid}`){changed_str}")
    return f"**{len(lines)} watches:**\n" + "\n".join(lines)


def _format_watch_detail(w: dict[str, Any]) -> str:
    """Pretty-print a single watch."""
    title = w.get("title") or w.get("url", "Unknown")
    uuid = w.get("uuid", w.get("id", "?"))
    url = w.get("url", "?")
    status = "⏸ Paused" if w.get("paused") else "▶ Active"
    muted = " 🔇" if w.get("notification_muted") else ""
    tag_str = ""
    tags = w.get("tags", [])
    if tags:
        tag_str = f"\n• **Tags:** {', '.join(tags[:5])}" + ("..." if len(tags) > 5 else "")
    elif w.get("tag"):
        tag_str = f"\n• **Tag:** {w['tag']}"

    interval = w.get("time_between_check")
    interval_str = f"\n• **Check interval:** {interval}" if interval else ""

    last = w.get("last_checked", w.get("last_check"))
    last_str = f"\n• **Last checked:** {last}" if last else ""

    changed = w.get("last_changed", w.get("previous_md5"))
    changed_str = f"\n• **Last changed:** {changed}" if changed else ""

    return (
        f"**{title}**{muted}\n"
        f"• **UUID:** `{uuid}`\n"
        f"• **URL:** {url}\n"
        f"• **Status:** {status}"
        f"{tag_str}"
        f"{interval_str}"
        f"{last_str}"
        f"{changed_str}"
    )
