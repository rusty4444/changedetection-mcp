#!/usr/bin/env python3
"""Discover available API endpoints on the running changedetection instance."""
import httpx

h = {"x-api-key": "54e4350420a0e96b4f01c815e20095a5", "Content-Type": "application/json"}
base = "http://localhost:5005/api/v1"
first_uuid = "b80d0df5-39c7-4180-a1ca-ed76246030fc"

paths = [
    ("GET", "/watch"),
    ("POST", "/watch", {"url": "http://example.com/test"}),
    ("GET", f"/watch/{first_uuid}"),
    ("PUT", f"/watch/{first_uuid}", {"paused": True}),
    ("DELETE", f"/watch/{first_uuid}"),
    ("GET", f"/watch/{first_uuid}/history"),
    ("GET", f"/watch/{first_uuid}/difference/latest/previous"),
    ("GET", "/systeminfo"),
    ("GET", "/search?q=test"),
    ("GET", "/tags"),
    ("POST", "/tags", {"title": "Test"}),
    ("GET", "/tag"),
    ("POST", "/tag", {"title": "Test"}),
]

for verb, path, *rest in paths:
    body = rest[0] if rest else None
    url = f"{base}{path}"
    try:
        if verb == "GET":
            r = httpx.get(url, headers=h, timeout=5)
        elif verb == "POST":
            r = httpx.post(url, headers=h, json=body, timeout=5)
        elif verb == "PUT":
            r = httpx.put(url, headers=h, json=body, timeout=5)
        elif verb == "DELETE":
            r = httpx.delete(url, headers=h, timeout=5)

        s = r.status_code
        if s == 200 and verb == "GET":
            data = r.json()
            if isinstance(data, dict):
                print(f"  [200] GET {path} ({len(data)} root keys)")
                sample_keys = list(data.keys())[:5]
                for k in sample_keys:
                    v = data[k]
                    if isinstance(v, dict):
                        print(f"     {k}: dict ({len(v)} sub-keys)")
                        sub = list(v.keys())[:8]
                        print(f"       keys: {sub}")
                    else:
                        print(f"     {k}: {type(v).__name__} = {str(v)[:60]}")
            elif isinstance(data, list):
                print(f"  [200] GET {path} ({len(data)} items)")
                if data:
                    print(f"     first item: {str(data[0])[:120]}")
        elif s in (200, 201) and verb == "POST":
            data = r.json()
            print(f"  [201] POST {path} -> uuid: {str(data.get('uuid','?'))[:12]}")
        elif s in (200, 201):
            data = r.json()
            print(f"  [201] POST {path} -> {str(data)[:100]}")
        elif s in (200, 201):
            print(f"  [OK] {verb} {path}")
        else:
            print(f"  [{s}] {verb} {path}: {r.text[:100]}")
    except Exception as e:
        print(f"  [ERR] {verb} {path}: {e}")
