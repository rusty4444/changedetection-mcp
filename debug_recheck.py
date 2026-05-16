"""Debug recheck API response format."""
import httpx

h = {"x-api-key": "54e4350420a0e96b4f01c815e20095a5", "Content-Type": "application/json"}
base = "http://localhost:5005/api/v1"

# Create a watch first
r = httpx.post(f"{base}/watch", headers=h, json={"url": "https://httpbin.org/get", "paused": True}, timeout=5)
uuid = r.json()["uuid"]
print(f"Created: {uuid}")

# Try recheck via GET with recheck param
r2 = httpx.get(f"{base}/watch/{uuid}", headers=h, params={"recheck": "1"}, timeout=5)
print(f"RECHECK status: {r2.status_code}")
print(f"RECHECK text: [{r2.text[:200]}]")
print(f"RECHECK content-type: {r2.headers.get('content-type', '?')}")

# Try json
try:
    j = r2.json()
    print(f"RECHECK json type: {type(j).__name__}")
    if isinstance(j, dict):
        print(f"RECHECK json keys: {list(j.keys())[:15]}")
    elif isinstance(j, str):
        print(f"RECHECK json string: {j[:100]}")
except Exception as e:
    print(f"RECHECK json error: {e}")

# Also test without recheck
r3 = httpx.get(f"{base}/watch/{uuid}", headers=h, timeout=5)
print(f"GET (no recheck) status: {r3.status_code}")
try:
    j3 = r3.json()
    print(f"GET json type: {type(j3).__name__}")
    if isinstance(j3, dict):
        print(f"GET json keys: {list(j3.keys())[:15]}")
except Exception as e:
    print(f"GET json error: {e}")

# Cleanup
httpx.delete(f"{base}/watch/{uuid}", headers=h, timeout=5)
print("Done")
