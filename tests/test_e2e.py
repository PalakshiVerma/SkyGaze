# -*- coding: utf-8 -*-
"""
tests/test_e2e.py
-----------------
End-to-end tests that call the LIVE running API (port 8000).
These validate the full request pipeline as the UI would use it.

Requires the API to be running:
    uvicorn api.main:app --reload --port 8000

Run with:
    .venv\\Scripts\\python.exe -m pytest tests/test_e2e.py -v
"""

import pytest
import requests

BASE = "http://127.0.0.1:8000"
LAT, LON = 28.6139, 77.2090


def api_is_up():
    try:
        return requests.get(f"{BASE}/", timeout=2).status_code == 200
    except Exception:
        return False


# Skip all tests if API is not running
pytestmark = pytest.mark.skipif(
    not api_is_up(),
    reason="FastAPI server not running on port 8000 — start with: uvicorn api.main:app --reload",
)


class TestLiveAPI:

    # -- Root -----------------------------------------------------------------

    def test_root_returns_ok(self):
        r = requests.get(f"{BASE}/")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    # -- Sky endpoint ---------------------------------------------------------

    def test_sky_jupiter_live(self):
        r = requests.get(f"{BASE}/sky/jupiter", params={"lat": LAT, "lon": LON})
        assert r.status_code == 200
        data = r.json()
        assert 0 <= data["azimuth_deg"] < 360
        assert -90 <= data["altitude_deg"] <= 90
        assert data["spoken_description"].endswith(".")

    def test_sky_moon_live(self):
        r = requests.get(f"{BASE}/sky/moon", params={"lat": LAT, "lon": LON})
        assert r.status_code == 200
        assert "moon" in r.json()["display_name"].lower()

    def test_sky_all_objects_live(self):
        objects = ["sun", "moon", "mercury", "venus", "mars",
                   "jupiter", "saturn", "uranus", "neptune"]
        for obj in objects:
            r = requests.get(f"{BASE}/sky/{obj}", params={"lat": LAT, "lon": LON})
            assert r.status_code == 200, f"Failed for {obj}"

    def test_sky_unknown_returns_404(self):
        r = requests.get(f"{BASE}/sky/pluto", params={"lat": LAT, "lon": LON})
        assert r.status_code == 404

    # -- Ask endpoint (full round-trip) ---------------------------------------

    def test_ask_where_is_jupiter(self):
        r = requests.post(f"{BASE}/ask", json={
            "text": "Where is Jupiter?", "lat": LAT, "lon": LON
        })
        assert r.status_code == 200
        data = r.json()
        assert data["intent"] == "LOCATE_OBJECT"
        assert data["object"] == "jupiter"
        assert "jupiter" in data["answer"].lower()
        assert data["answer"].endswith(".")

    def test_ask_where_is_moon(self):
        r = requests.post(f"{BASE}/ask", json={
            "text": "Where is the Moon?", "lat": LAT, "lon": LON
        })
        assert r.status_code == 200
        assert r.json()["intent"] == "LOCATE_OBJECT"

    def test_ask_visibility_mars(self):
        r = requests.post(f"{BASE}/ask", json={
            "text": "Is Mars visible tonight?", "lat": LAT, "lon": LON
        })
        assert r.status_code == 200
        data = r.json()
        assert data["intent"] == "CHECK_VISIBILITY"
        answer = data["answer"].lower()
        assert "visible" in answer or "below" in answer

    def test_ask_iss_pass(self):
        r = requests.post(f"{BASE}/ask", json={
            "text": "When does the ISS pass?", "lat": LAT, "lon": LON
        })
        assert r.status_code == 200
        assert r.json()["intent"] == "GET_ISS_PASS"

    def test_ask_weather(self):
        r = requests.post(f"{BASE}/ask", json={
            "text": "Can I see stars tonight?", "lat": LAT, "lon": LON
        })
        assert r.status_code == 200
        assert r.json()["intent"] == "WEATHER_SUMMARY"

    def test_ask_unknown(self):
        r = requests.post(f"{BASE}/ask", json={
            "text": "What is the meaning of life?", "lat": LAT, "lon": LON
        })
        assert r.status_code == 200
        assert r.json()["intent"] == "UNKNOWN"

    def test_ask_all_quick_questions(self):
        """Simulate every quick-tap question from the UI sidebar."""
        quick = [
            "Where is Jupiter?",
            "Where is the Moon?",
            "Where is Mars?",
            "Where is Saturn?",
            "Is Venus visible?",
            "Is Mars visible tonight?",
            "When does the ISS pass?",
            "Can I see stars tonight?",
        ]
        for q in quick:
            r = requests.post(f"{BASE}/ask", json={
                "text": q, "lat": LAT, "lon": LON
            })
            assert r.status_code == 200, f"Failed for: {q}"
            assert len(r.json()["answer"]) > 5, f"Empty answer for: {q}"

    # -- Health endpoint ------------------------------------------------------

    def test_health_live(self):
        r = requests.get(f"{BASE}/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert len(data["supported_objects"]) >= 9

    # -- UI helper simulation -------------------------------------------------

    def test_sky_at_a_glance_pipeline(self):
        """
        Simulates what ui/app.py does for the 'sky at a glance' grid:
        calls /sky for each object and collects visible ones.
        """
        objects = ["Sun", "Moon", "Mercury", "Venus", "Mars",
                   "Jupiter", "Saturn", "Uranus", "Neptune"]
        visible = []
        for obj in objects:
            r = requests.get(f"{BASE}/sky/{obj.lower()}",
                             params={"lat": LAT, "lon": LON})
            assert r.status_code == 200
            data = r.json()
            if data["is_visible"]:
                visible.append(data["display_name"])

        # Just verify the pipeline runs without errors.
        # Number of visible objects depends on time of day.
        print(f"\nVisible right now over New Delhi: {visible or ['none']}")
        assert isinstance(visible, list)
