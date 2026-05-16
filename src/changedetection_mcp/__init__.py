"""MCP server entry point for ChangeDetection.io."""

from __future__ import annotations

import os
import sys

from mcp.server.fastmcp import FastMCP

from . import client as api
from .tools import register_tools

mcp = FastMCP(
    "changedetection",
    description="ChangeDetection.io — AI-native website change monitoring",
)


def main() -> None:
    """Run the MCP server via stdio transport."""
    # Credentials from env (or configured explicitly via client.configure())
    base_url = os.environ.get("CHANGEDETECTION_BASE_URL")
    api_key = os.environ.get("CHANGEDETECTION_API_KEY")

    if not base_url or not api_key:
        print(
            "Error: CHANGEDETECTION_BASE_URL and CHANGEDETECTION_API_KEY must be set.\n"
            "  export CHANGEDETECTION_BASE_URL=http://localhost:5000\n"
            "  export CHANGEDETECTION_API_KEY=your-api-key",
            file=sys.stderr,
        )
        sys.exit(1)

    api.configure(base_url, api_key)
    register_tools(mcp)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
