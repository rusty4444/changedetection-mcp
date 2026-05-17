# ChangeDetection.io MCP Server

An MCP (Model Context Protocol) server that gives AI agents native access to [ChangeDetection.io](https://github.com/dgtlmoon/changedetection.io) — the open-source website change detection and monitoring platform.

## Features

- **Watch Management** — Create, list, update, delete, and trigger rechecks on watches
- **Change History** — Browse snapshot history and get diffs between any two points in time
- **Per-watch action fuse** — `get_snapshot_diff` arms a configurable limit on follow-up mutating actions for that watch so one noisy page cannot cascade into unlimited rechecks or edits
- **Tag Management** — Organise watches with tags/groups
- **Search** — Full-text search through watches by URL or title
- **System Info** — Quick health and stats readout

## Why This Exists

No MCP server existed for ChangeDetection.io despite it being one of the most popular self-hosted tools (31k+ GitHub stars). This server fills that gap, letting AI agents:

- "Watch this product page and notify me when it changes"
- "Show me all my failed watches"
- "What changed on this page yesterday?"
- "Set up a watch for this job listing"

## Quick Start

### Prerequisites

- A running ChangeDetection.io instance (self-hosted or SaaS)
- An API key from Settings → API

### Installation

```bash
pip install changedetection-mcp
```

### Configuration

Add to your MCP client config (Claude Desktop, Cursor, Hermes Agent, etc.):

```json
{
  "mcpServers": {
    "changedetection": {
      "command": "changedetection-mcp",
      "env": {
        "CHANGEDETECTION_BASE_URL": "http://localhost:5000",
        "CHANGEDETECTION_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Usage with Hermes Agent

Create `~/.hermes/skills/changedetection/SKILL.md` (see `skill/` directory) or configure as an MCP server:

```bash
hermes mcp add changedetection --command "changedetection-mcp"
hermes config set changedetection.base_url "http://localhost:5000"
hermes config set changedetection.api_key "your-api-key"
```

## API Coverage

| Tool | Description |
|------|-------------|
| `list_watches` | List all watches (optional tag filter, limit/offset) |
| `get_watch` | Get full details of a single watch |
| `create_watch` | Create a new watch from a URL |
| `update_watch` | Update an existing watch (pause, rename, change schedule, etc.) |
| `delete_watch` | Delete a watch and all its history |
| `recheck_watch` | Trigger an immediate recheck |
| `get_watch_history` | List change history snapshots for a watch |
| `get_snapshot_diff` | Get diff between two snapshots |
| `search_watches` | Full-text search by URL or title |
| `list_tags` | List all tags/groups |
| `create_tag` | Create a tag for organisation |
| `get_system_info` | Get server stats (watch count, uptime, version) |

## Safety Fuse: Per-Watch Action Limit

When an agent asks for a page diff, that diff can prompt follow-up actions such as immediate rechecks, watch edits, or deletes. To stop one noisy site from triggering a cascade, `get_snapshot_diff` arms a per-watch fuse before returning.

By default, each diff allows **3 mutating MCP actions** for that watch. The fuse applies to:

- `recheck_watch`
- `update_watch`
- `delete_watch`

After the budget is exhausted, those tools return a clear blocked message instead of calling the ChangeDetection.io API. The fuse is in-process and per watch UUID; watches without an armed fuse are unaffected.

Configuration:

```bash
# Default: 3. Set 0 to disable the fuse globally.
export CHANGEDETECTION_MCP_ACTION_LIMIT_PER_WATCH=3
```

Per call, override the default with the optional `action_limit` argument on `get_snapshot_diff`:

```text
get_snapshot_diff(uuid="...", from_timestamp="previous", to_timestamp="latest", action_limit=1)
```

Use `action_limit=0` to disable the fuse for that watch, or call `get_snapshot_diff` again with a higher value to re-arm it.

## Development

```bash
git clone https://github.com/rusty4444/changedetection-mcp.git
cd changedetection-mcp
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## License

MIT — see `LICENSE`.
