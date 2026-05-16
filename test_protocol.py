#!/usr/bin/env python3
"""Quick MCP protocol test using communicate() pattern."""
import subprocess, json, sys

init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
               "clientInfo": {"name": "test", "version": "1.0.0"}}})
notify = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
tool_req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

input_data = init_req + "\n" + notify + "\n" + tool_req + "\n"

proc = subprocess.Popen(
    ["python3", "-m", "changedetection_mcp"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
)
stdout, stderr = proc.communicate(input=input_data, timeout=15)

if stderr:
    for line in stderr.strip().split("\n"):
        print(f"STDERR: {line}", file=sys.stderr)

lines = [l for l in stdout.strip().split("\n") if l.strip()]
print(f"Got {len(lines)} response(s)")
for line in lines:
    obj = json.loads(line)
    method = obj.get("method", "response")
    rid = obj.get("id", "?")
    if "result" in obj:
        r = obj["result"]
        if isinstance(r, dict) and "tools" in r:
            tools = r["tools"]
            print(f"  tools/list: {len(tools)} tools")
            for t in tools:
                props = t.get("inputSchema", {}).get("properties", {})
                print(f"    - {t['name']:30s} ({len(props):2d} params)")
        elif isinstance(r, dict) and "protocolVersion" in r:
            si = r.get("serverInfo", {})
            print(f"  initialize: {si.get('name','?')} v{si.get('version','?')}")
        else:
            print(f"  id={rid}: {str(r)[:120]}")
    elif "error" in obj:
        print(f"  ERROR id={rid}: {obj['error']}")
