"""
Quick smoke check against the running server.
Run: .venv\Scripts\python.exe smoke_check.py
"""
import urllib.request
import json

BASE = "http://127.0.0.1:8000"
LAT, LON = 28.6139, 77.2090

checks = [
    ("GET", f"{BASE}/",                                          None),
    ("GET", f"{BASE}/sky/jupiter?lat={LAT}&lon={LON}",          None),
    ("GET", f"{BASE}/sky/saturn?lat={LAT}&lon={LON}",           None),
    ("GET", f"{BASE}/sky/pluto?lat={LAT}&lon={LON}",            None),   # expect 404
    ("GET", f"{BASE}/health",                                   None),
    ("POST",f"{BASE}/ask",  json.dumps({"text": "Where is Jupiter?", "lat": LAT, "lon": LON}).encode()),
    ("POST",f"{BASE}/ask",  json.dumps({"text": "Is Mars visible?",  "lat": LAT, "lon": LON}).encode()),
    ("POST",f"{BASE}/ask",  json.dumps({"text": "When does the ISS pass?", "lat": LAT, "lon": LON}).encode()),
    ("POST",f"{BASE}/ask",  json.dumps({"text": "Can I see stars tonight?", "lat": LAT, "lon": LON}).encode()),
]

print(f"\n{'SkyGaze API Smoke Check':^70}")
print("=" * 70)

all_ok = True
for method, url, body in checks:
    path = url.replace(BASE, "")[:45]
    try:
        req = urllib.request.Request(url, data=body,
              headers={"Content-Type": "application/json"} if body else {})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            status = resp.status
    except urllib.error.HTTPError as e:
        data = json.loads(e.read())
        status = e.code

    ok = (status in (200, 404))   # 404 expected for pluto
    flag = "✅" if ok else "❌"
    if not ok:
        all_ok = False

    # Pick a meaningful preview field
    preview = (
        data.get("spoken_description") or
        data.get("answer") or
        data.get("status") or
        data.get("detail") or
        str(list(data.keys()))
    )
    preview = str(preview)[:55]

    print(f"{flag} {method:<4} {path:<46} {status}  {preview}")

print("=" * 70)
print(f"\n{'✅ All checks passed!' if all_ok else '❌ Some checks failed.'}\n")
