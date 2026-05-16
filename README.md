# ChangeDetection.io MCP Server

An MCP (Model Context Protocol) server that gives AI agents native access to [ChangeDetection.io](https://github.com/dgtlmoon/changedetection.io) — the open-source website change detection and monitoring platform.

## Features

- **Watch Management** — Create, list, update, delete, and trigger rechecks on watches
- **Change History** — Browse snapshot history and get diffs between any two points in time
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
