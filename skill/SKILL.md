# ChangeDetection.io — MCP Server & Hermes Skill

## Overview

[ChangeDetection.io](https://github.com/dgtlmoon/changedetection.io) is a self-hosted or SaaS tool for monitoring web pages for changes — price drops, restock alerts, content updates, defacement monitoring. It's one of the most popular self-hosted tools (31k+ GitHub stars).

This skill pairs the **changedetection-mcp** MCP server with Hermes-native features (cron scheduling, multi-platform delivery) to create a powerful watch-and-notify loop.

## When to Use

- User asks to "watch this page" or "monitor this URL for changes"
- User needs to be notified about price drops, restocks, or content updates
- User wants to check what changed on a page overnight
- User wants to set up recurring checks with delivery to Telegram/Discord/email

**Don't use for:** One-off checks (use `web_extract` or `browser_navigate` instead). This is for *ongoing monitoring*.

## Prerequisites

1. **ChangeDetection.io instance** — self-hosted at `http://localhost:5000` (or any URL) or use the SaaS plan at `https://changedetection.io`
2. **API key** — found in Settings → API tab in the ChangeDetection.io dashboard
3. **changedetection-mcp installed** — `pip install changedetection-mcp` (or run from source)

## Setup

### Option A: MCP Server (any MCP client)

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "changedetection": {
      "command": "changedetection-mcp",
      "env": {
        "CHANGEDETECTION_BASE_URL": "http://localhost:5000",
        "CHANGEDETECTION_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Option B: Hermes Config (recommended for Hermes users)

```bash
# Install the MCP server
pip install changedetection-mcp

# Add as an MCP server to Hermes
hermes mcp add changedetection --command "changedetection-mcp"
```

Then set env vars in `~/.hermes/.env`:

```bash
CHANGEDETECTION_BASE_URL=http://localhost:5000
CHANGEDETECTION_API_KEY=your-api-key
```

## Usage Examples

### Create a watch

```
Can you watch https://example.com/product-page for price changes? Check hourly.
```

The agent will call `create_watch` with the URL and check interval.

### List my watches

```
Show me all my active watches.
```

→ Calls `list_watches()`

### Check for changes

```
What changed on my watched page in the last 24 hours?
```

→ Calls `get_watch_history()` then `get_snapshot_diff()`. The diff call arms the per-watch action fuse, limiting follow-up mutating actions for that watch.

### Control follow-up action limits

```
Show me what changed on this noisy watch, but allow at most one follow-up action.
```

→ Calls `get_snapshot_diff(..., action_limit=1)`. Use `action_limit=0` only when the user explicitly wants the fuse disabled for that watch.

### Set up persistent monitoring with cron

```
Every morning at 9am, check all my watches and send me a summary of what changed.
```

→ The agent can set up a Hermes cronjob that queries changedetection and delivers to your home channel.

### Pause/resume

```
Pause the watch on example.com till next week.
```

→ Calls `update_watch(paused=True)`

## Common Pitfalls

1. **API key not set** — The MCP server will exit with an error if `CHANGEDETECTION_API_KEY` is missing. Always set it in `.env` or the MCP client config.
2. **Self-hosted URL wrong** — Default is `http://localhost:5000`. If using Docker with a different port or host, set `CHANGEDETECTION_BASE_URL` explicitly.
3. **`latest`/`previous` in diff** — These are convenience aliases for the most recent snapshots. If no changes occurred, the diff will be empty.
4. **Watches created paused** — New watches start active by default. Pass `paused=True` to `create_watch` if you want to set up but not start monitoring yet.
5. **Rate limiting** — Setting `minutes_between_checks` too low (under 5 minutes) may get you rate-limited, especially on the SaaS plan. 1 hour is a safe default.
6. **Noisy diff cascades** — `get_snapshot_diff` arms a per-watch action fuse (default 3) so one noisy page cannot trigger unlimited `recheck_watch`, `update_watch`, or `delete_watch` calls. Raise `action_limit` only when needed; set `CHANGEDETECTION_MCP_ACTION_LIMIT_PER_WATCH=0` or call with `action_limit=0` to disable.

## Verification Checklist

- [ ] `changedetection-mcp` runs without errors: `CHANGEDETECTION_BASE_URL=... CHANGEDETECTION_API_KEY=... changedetection-mcp`
- [ ] `list_watches` returns your existing watches
- [ ] `create_watch` can add a new URL
- [ ] `get_snapshot_diff` returns meaningful diffs (test with a URL you know changes)
- [ ] Hermes cron delivery works end-to-end if using scheduled checks

## Config Reference

| Env Var | Default | Description |
|---------|---------|-------------|
| `CHANGEDETECTION_BASE_URL` | `http://localhost:5000` | Base URL of your ChangeDetection.io instance |
| `CHANGEDETECTION_API_KEY` | — | API key from Settings → API tab |
| `CHANGEDETECTION_MCP_ACTION_LIMIT_PER_WATCH` | `3` | Mutating actions allowed after each `get_snapshot_diff` per watch. `0` disables the fuse. |

## MCP Tool Reference

| Tool | Description |
|------|-------------|
| `list_watches` | List all watches, optional tag filter |
| `get_watch` | Full details of a single watch |
| `create_watch` | Create a new watch (URL, title, tag, interval) |
| `update_watch` | Update a watch (pause/resume, rename, change interval) |
| `delete_watch` | Delete a watch and history |
| `recheck_watch` | Trigger immediate recheck |
| `get_watch_history` | List snapshot timestamps |
| `get_snapshot_diff` | Diff between two snapshots; arms the per-watch follow-up action fuse (`action_limit`) |
| `search_watches` | Full-text search |
| `list_tags` | List tag groups |
| `create_tag` | Create a tag/group |
| `get_system_info` | Server stats and version |
