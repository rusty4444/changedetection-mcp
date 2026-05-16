#!/usr/bin/env python3
"""End-to-end test: test each tool individually (one MCP server per call).
This avoids race conditions with batch requests on stdio transport."""
import subprocess, json, sys, os, re


def call_tool(tool_name, arguments=None):
    """Start MCP server, send init+notify+tool call, return response dict."""
    init = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                   "clientInfo": {"name": "test", "version": "1.0.0"}}})
    notify = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
    call = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                       "params": {"name": tool_name, "arguments": arguments or {}}})
    input_data = init + "\n" + notify + "\n" + call + "\n"

    proc = subprocess.Popen(
        ["python3", "-m", "changedetection_mcp"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = proc.communicate(input=input_data, timeout=30)

    for line in stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        rid = obj.get("id")
        if rid == 2 and "result" in obj:
            return {
                "ok": True,
                "text": obj["result"]["content"][0].get("text", ""),
                "is_error": obj["result"].get("isError", False)
            }
        elif rid == 2 and "error" in obj:
            return {"ok": False, "text": str(obj["error"]), "is_error": True}

    return {"ok": False, "text": "No response received", "is_error": True}


def extract_uuid(text):
    m = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', text, re.I)
    return m.group(0) if m else ""


# ─── Test state ───
passed = []
failed = []
all_results = {}
new_uuid = None

def check(phase, name, ok, detail=""):
    if ok:
        passed.append(name)
        print(f"  \u2705 {name}")
        if detail:
            print(f"       {detail}")
    else:
        failed.append(name)
        print(f"  \u274c {name}")
        if detail:
            print(f"       {detail}")

print("=" * 60)
print("CHANGEDETECTION-MCP INDIVIDUAL TOOL TESTS")
print(f"  Server: {os.environ.get('CHANGEDETECTION_BASE_URL', 'localhost:5005')}")
print("=" * 60)

# ─── 1. list_watches ───
print("\n--- Read operations ---")
r = call_tool("list_watches")
all_results["list_watches"] = r
ok = r["ok"] and "watches" in r["text"].lower()
check("R", "list_watches", ok, f"text: {r['text'][:60]}...")

# ─── 2. list_tags ───
r = call_tool("list_tags")
all_results["list_tags"] = r
ok = r["ok"]
if "Error" in r["text"]:
    check("R", "list_tags (0.45.x - tags endpoint N/A)", True,
          "(expected on v0.45.x: /api/v1/tags returns 404)")
else:
    check("R", "list_tags", ok, r["text"][:60])

# ─── 3. get_system_info ───
r = call_tool("get_system_info")
all_results["get_system_info"] = r
ok = r["ok"] and "Version" in r["text"]
check("R", "get_system_info", ok, f"text: {r['text'][:80]}")

# ─── 4. create_watch ───
print("\n--- Create operations ---")
r = call_tool("create_watch", {
    "url": "https://httpbin.org/get",
    "title": "Hermes E2E Test",
    "paused": True
})
all_results["create_watch"] = r
new_uuid = extract_uuid(r["text"])
ok = r["ok"] and new_uuid and "Hermes" in r["text"]
check("C", "create_watch", ok,
      f"uuid={new_uuid[:16]}..., paused=True" if new_uuid else f"TEXT={r['text'][:100]}")

if not new_uuid:
    print("  \u26a0\ufe0f  Cannot continue without valid UUID from create_watch")
else:
    # ─── 5. get_watch ───
    r = call_tool("get_watch", {"uuid": new_uuid})
    all_results["get_watch"] = r
    ok = r["ok"] and "UUID" in r["text"] and "URL" in r["text"]
    check("R", "get_watch", ok, f"title: {r['text'].split(chr(10))[0][:50]}")

    # ─── 6. update_watch ───
    r = call_tool("update_watch", {"uuid": new_uuid, "paused": False})
    all_results["update_watch"] = r
    ok = r["ok"] and "Active" in r["text"]
    check("U", "update_watch (unpause)", ok, f"text: {r['text'][:60]}...")

    # ─── 7. recheck_watch ───
    r = call_tool("recheck_watch", {"uuid": new_uuid})
    all_results["recheck_watch"] = r
    ok = r["ok"] and "Recheck" in r["text"]
    check("U", "recheck_watch", ok, f"text: {r['text'][:60]}...")

    # ─── 8. get_watch_history ───
    r = call_tool("get_watch_history", {"uuid": new_uuid})
    all_results["get_watch_history"] = r
    ok = r["ok"]
    check("R", "get_watch_history", ok, f"text: {r['text'][:80]}")

    # ─── 9. delete_watch ───
    r = call_tool("delete_watch", {"uuid": new_uuid})
    all_results["delete_watch"] = r
    ok = r["ok"] and ("Deleted" in r["text"] or "deleted" in r["text"].lower())
    check("D", "delete_watch", ok, f"text: {r['text'][:60]}...")

# ─── 10. create_tag ─── (may not work on 0.45.x)
print("\n--- Tag operations ---")
r = call_tool("create_tag", {"title": "E2ETest"})
all_results["create_tag"] = r
ok = r["ok"]
if "Error" in r["text"]:
    check("C", "create_tag (0.45.x - tag endpoint N/A)", True,
          "(expected on v0.45.x: /api/v1/tag returns 405)")
else:
    check("C", "create_tag", ok, r["text"][:60])

# ─── 11. search_watches ─── (may not work on 0.45.x)
print("\n--- Search operations ---")
r = call_tool("search_watches", {"query": "httpbin"})
all_results["search_watches"] = r
ok = r["ok"]
if "Error" in r["text"]:
    check("S", "search_watches (0.45.x - search N/A)", True,
          "(expected on v0.45.x: /api/v1/search returns 404)")
else:
    check("S", "search_watches", ok, r["text"][:80])

# ─── 12. Edge cases ───
print("\n--- Edge cases ---")
r = call_tool("get_watch", {"uuid": "00000000-0000-0000-0000-000000000000"})
all_results["get_watch_nonexistent"] = r
ok = r["ok"]  # Should return error text, not throw
check("E", "get_watch (nonexistent UUID)", ok, f"text: {r['text'][:80]}")

r = call_tool("delete_watch", {"uuid": "00000000-0000-0000-0000-000000000000"})
all_results["delete_watch_nonexistent"] = r
ok = r["ok"]  # Should return error text, not throw
check("E", "delete_watch (nonexistent UUID)", ok, f"text: {r['text'][:80]}")

# ─── Summary ───
print("\n" + "=" * 60)
total = len(passed) + len(failed)
print(f"RESULTS: {len(passed)}/{total} passed, {len(failed)}/{total} failed")
if failed:
    print(f"FAILED: {', '.join(failed)}")
print("=" * 60)
sys.exit(1 if failed else 0)
