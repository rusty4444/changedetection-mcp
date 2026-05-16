"""MCP server tools for ChangeDetection.io."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import client as api


def register_tools(mcp: FastMCP) -> None:
    """Register all ChangeDetection.io MCP tools."""

    # ── Watches ──────────────────────────────────────────────────────────

    @mcp.tool()
    async def list_watches(
        tag: str | None = None,
    ) -> str:
        """List all watched URLs with their current status.

        Args:
            tag: Optional tag name to filter by.
        """
        try:
            data = api.list_watches(tag=tag)
            return _format_watch_list(data)
        except Exception as e:
            return f"Error listing watches: {e}"

    @mcp.tool()
    async def get_watch(
        uuid: str,
    ) -> str:
        """Get detailed information about a specific watch.

        Args:
            uuid: The watch UUID.
        """
        try:
            data = api.get_watch(uuid)
            return _format_watch_detail(data)
        except Exception as e:
            return f"Error getting watch {uuid}: {e}"

    @mcp.tool()
    async def create_watch(
        url: str,
        title: str | None = None,
        tag: str | None = None,
        minutes_between_checks: int | None = 60,
        paused: bool | None = False,
    ) -> str:
        """Create a new URL watch to monitor for changes.

        Args:
            url: The URL to watch for changes.
            title: Optional human-readable title for the watch.
            tag: Optional tag/group name to organise this watch under.
            minutes_between_checks: How often to check (default 60). Use 0 for default.
            paused: Start paused (True) or active immediately (False, default).
        """
        kwargs: dict[str, Any] = {}
        if title:
            kwargs["title"] = title
        if tag:
            kwargs["tag"] = tag
        if minutes_between_checks and minutes_between_checks > 0:
            kwargs["time_between_check"] = {"hours": max(1, minutes_between_checks // 60), "minutes": minutes_between_checks % 60}
        if paused is not None:
            kwargs["paused"] = paused
        try:
            data = api.create_watch(url, **kwargs)
            return _format_watch_detail(data)
        except Exception as e:
            return f"Error creating watch: {e}"

    @mcp.tool()
    async def update_watch(
        uuid: str,
        title: str | None = None,
        url: str | None = None,
        paused: bool | None = None,
        minutes_between_checks: int | None = None,
        tag: str | None = None,
    ) -> str:
        """Update an existing watch's settings.

        Args:
            uuid: The watch UUID.
            title: New title.
            url: New URL to monitor.
            paused: Pause (True) or resume (False) the watch.
            minutes_between_checks: New check interval in minutes.
            tag: New tag / group assignment.
        """
        kwargs: dict[str, Any] = {}
        if title is not None:
            kwargs["title"] = title
        if url is not None:
            kwargs["url"] = url
        if paused is not None:
            kwargs["paused"] = paused
        if minutes_between_checks is not None:
            kwargs["time_between_check"] = {"hours": max(1, minutes_between_checks // 60), "minutes": minutes_between_checks % 60}
        if tag is not None:
            kwargs["tag"] = tag
        try:
            data = api.update_watch(uuid, **kwargs)
            return _format_watch_detail(data)
        except Exception as e:
            return f"Error updating watch {uuid}: {e}"

    @mcp.tool()
    async def delete_watch(
        uuid: str,
    ) -> str:
        """Permanently delete a watch and all its history.

        Args:
            uuid: The watch UUID to delete.
        """
        try:
            api.delete_watch(uuid)
            return f"Deleted watch {uuid}"
        except Exception as e:
            return f"Error deleting watch {uuid}: {e}"

    @mcp.tool()
    async def recheck_watch(
        uuid: str,
    ) -> str:
        """Trigger an immediate recheck of a watch URL.

        Args:
            uuid: The watch UUID to recheck.
        """
        try:
            data = api.recheck_watch(uuid)
            return f"Recheck triggered for {data.get('title', uuid)}\n{_format_watch_detail(data)}"
        except Exception as e:
            return f"Error rechecking watch {uuid}: {e}"

    # ── History & Diffs ─────────────────────────────────────────────────

    @mcp.tool()
    async def get_watch_history(
        uuid: str,
    ) -> str:
        """List the snapshot history (timestamps) for a watched URL.

        Args:
            uuid: The watch UUID.
        """
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
        uuid: str,
        from_timestamp: str,
        to_timestamp: str,
    ) -> str:
        """Get the diff between two snapshots of a watched URL.

        Use 'latest' and 'previous' as shortcuts for the most recent
        and second-most-recent snapshots.

        Args:
            uuid: The watch UUID.
            from_timestamp: Earlier snapshot timestamp, 'latest', or 'previous'.
            to_timestamp: Later snapshot timestamp, 'latest', or 'previous'.
        """
        try:
            diff = api.get_snapshot_diff(uuid, from_timestamp, to_timestamp)
            return diff
        except Exception as e:
            return f"Error getting diff: {e}"

    # ── Tags ────────────────────────────────────────────────────────────

    @mcp.tool()
    async def list_tags() -> str:
        """List all tag groups used to organise watches."""
        try:
            data = api.list_tags()
            if not data:
                return "No tags configured."
            lines = [f"• **{t.get('title', t.get('name', '?'))}** ({t.get('uuid', t.get('id', '?'))})" for t in data.get("tags", [])]
            return f"**{len(lines)} tags:**\n" + "\n".join(lines)
        except Exception as e:
            return f"Error listing tags: {e}"

    @mcp.tool()
    async def create_tag(
        title: str,
    ) -> str:
        """Create a new tag/group for organising watches.

        Args:
            title: The tag display name.
        """
        try:
            data = api.create_tag(title)
            return f"Created tag: {data.get('title', data.get('name', title))}"
        except Exception as e:
            return f"Error creating tag: {e}"

    # ── Search ──────────────────────────────────────────────────────────

    @mcp.tool()
    async def search_watches(
        query: str,
        tag: str | None = None,
    ) -> str:
        """Search watches by URL or title.

        Args:
            query: Search term.
            tag: Optional tag name to narrow results.
        """
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


def _format_watch_list(data: dict[str, Any]) -> str:
    """Pretty-print a list response."""
    watches = data.get("watches", []) if isinstance(data, dict) else data
    if not watches:
        return "No watches found."
    lines = []
    for w in watches:
        title = w.get("title") or w.get("url", "?")
        uuid = w.get("uuid", w.get("id", "?"))
        status = "⏸ Paused" if w.get("paused") else "▶ Active"
        tag_str = f" [{w.get('tag', '')}]" if w.get("tag") else ""
        lines.append(f"• **{title}**{tag_str} — {status} (`{uuid}`)")
    return f"**{len(lines)} watches:**\n" + "\n".join(lines)


def _format_watch_detail(w: dict[str, Any]) -> str:
    """Pretty-print a single watch."""
    title = w.get("title") or w.get("url", "Unknown")
    uuid = w.get("uuid", w.get("id", "?"))
    url = w.get("url", "?")
    status = "⏸ Paused" if w.get("paused") else "▶ Active"
    muted = " 🔇" if w.get("notification_muted") else ""
    tag = f"\n• **Tag:** {w['tag']}" if w.get("tag") else ""
    interval = w.get("time_between_check")
    interval_str = f"\n• **Check interval:** {interval}" if interval else ""

    # Last checked
    last = w.get("last_checked", w.get("last_check"))
    last_str = f"\n• **Last checked:** {last}" if last else ""

    # Last changed
    changed = w.get("last_changed", w.get("previous_md5"))
    changed_str = f"\n• **Last changed:** {changed}" if changed else ""

    return (
        f"**{title}**{muted}\n"
        f"• **UUID:** `{uuid}`\n"
        f"• **URL:** {url}\n"
        f"• **Status:** {status}"
        f"{tag}"
        f"{interval_str}"
        f"{last_str}"
        f"{changed_str}"
    )
