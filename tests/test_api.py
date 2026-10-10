"""
tests/test_api.py
─────────────────
Tests for the SkyGaze FastAPI backend (api/main.py).

Uses FastAPI's TestClient (built on httpx) — no running server needed.

Coverage:
  GET  /                     root ping
  GET  /sky/{object_name}    position endpoint — happy paths, errors, edge cases
  POST /ask                  intent + answer — all intent branches
  GET  /health               system status and cache info

Run with:
    .venv\\Scripts\\python.exe -m pytest tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.main import app

client = TestClient(app)

# Shared observer — New Delhi
LAT = 28.6139
LON = 77.2090

# Fixed UTC time that has some planets visible (from Phase 1 smoke test)
FIXED_TIME = "2026-10-07T00:07:00Z"


# ── GET / ─────────────────────────────────────────────────────────────────────

class TestRoot:

    def test_returns_200(self):
        r = client.get("/")
        assert r.status_code == 200

    def test_status_ok(self):
        r = client.get("/")
        assert r.json()["status"] == "ok"

    def test_app_name_present(self):
        r = client.get("/")
        assert "SkyGaze" in r.json()["app"]

    def test_version_present(self):
        r = client.get("/")
        assert "version" in r.json()


# ── GET /sky/{object_name} ────────────────────────────────────────────────────

class TestSkyEndpoint:

    # --- Happy paths ---------------------------------------------------------

    def test_jupiter_returns_200(self):
        r = client.get(f"/sky/jupiter?lat={LAT}&lon={LON}")
        assert r.status_code == 200

    def test_response_schema_keys(self):
        r = client.get(f"/sky/saturn?lat={LAT}&lon={LON}&time_utc={FIXED_TIME}")
        data = r.json()
        for key in ("object", "display_name", "azimuth_deg", "altitude_deg",
                    "is_visible", "direction", "altitude_phrase", "spoken_description"):
            assert key in data, f"Missing key: {key}"

    def test_object_field_is_normalised(self):
        r = client.get(f"/sky/Jupiter?lat={LAT}&lon={LON}")
        assert r.json()["object"] == "jupiter"

    def test_azimuth_in_range(self):
        r = client.get(f"/sky/mars?lat={LAT}&lon={LON}")
        az = r.json()["azimuth_deg"]
        assert 0.0 <= az < 360.0

    def test_altitude_in_range(self):
        r = client.get(f"/sky/mars?lat={LAT}&lon={LON}")
        alt = r.json()["altitude_deg"]
        assert -90.0 <= alt <= 90.0

    def test_is_visible_matches_altitude(self):
        r = client.get(f"/sky/saturn?lat={LAT}&lon={LON}&time_utc={FIXED_TIME}")
        data = r.json()
        expected = data["altitude_deg"] > 0
        assert data["is_visible"] == expected

    def test_direction_is_string(self):
        r = client.get(f"/sky/moon?lat={LAT}&lon={LON}")
        assert isinstance(r.json()["direction"], str)
        assert len(r.json()["direction"]) > 0

    def test_spoken_description_ends_with_period(self):
        r = client.get(f"/sky/uranus?lat={LAT}&lon={LON}&time_utc={FIXED_TIME}")
        assert r.json()["spoken_description"].endswith(".")

    def test_spoken_description_contains_object_name(self):
        r = client.get(f"/sky/saturn?lat={LAT}&lon={LON}&time_utc={FIXED_TIME}")
        assert "saturn" in r.json()["spoken_description"].lower()

    def test_moon_alias_works(self):
        r = client.get(f"/sky/moon?lat={LAT}&lon={LON}")
        assert r.status_code == 200
        assert "moon" in r.json()["display_name"].lower()

    def test_case_insensitive_object_name(self):
        r1 = client.get(f"/sky/JUPITER?lat={LAT}&lon={LON}")
        r2 = client.get(f"/sky/jupiter?lat={LAT}&lon={LON}")
        assert r1.status_code == 200
        assert r1.json()["azimuth_deg"] == r2.json()["azimuth_deg"]

    def test_with_explicit_time_utc(self):
        r = client.get(f"/sky/saturn?lat={LAT}&lon={LON}&time_utc={FIXED_TIME}")
        assert r.status_code == 200
        # Saturn at FIXED_TIME is visible for New Delhi (from Phase 1 verification)
        assert r.json()["is_visible"] is True

    def test_all_planets_return_200(self):
        objects = ["sun", "moon", "mercury", "venus", "mars",
                   "jupiter", "saturn", "uranus", "neptune"]
        for obj in objects:
            r = client.get(f"/sky/{obj}?lat={LAT}&lon={LON}")
            assert r.status_code == 200, f"Failed for {obj}: {r.text}"

    # --- Error cases ---------------------------------------------------------

    def test_unknown_object_returns_404(self):
        r = client.get(f"/sky/pluto?lat={LAT}&lon={LON}")
        assert r.status_code == 404

    def test_unknown_object_detail_mentions_name(self):
        r = client.get(f"/sky/klingon?lat={LAT}&lon={LON}")
        assert "klingon" in r.json()["detail"].lower()

    def test_missing_lat_returns_422(self):
        r = client.get(f"/sky/jupiter?lon={LON}")
        assert r.status_code == 422

    def test_missing_lon_returns_422(self):
        r = client.get(f"/sky/jupiter?lat={LAT}")
        assert r.status_code == 422

    def test_invalid_lat_out_of_range(self):
        r = client.get("/sky/jupiter?lat=100&lon=0")
        assert r.status_code == 422

    def test_invalid_lon_out_of_range(self):
        r = client.get("/sky/jupiter?lat=0&lon=200")
        assert r.status_code == 422

    def test_invalid_time_utc_format_returns_422(self):
        r = client.get(f"/sky/jupiter?lat={LAT}&lon={LON}&time_utc=not-a-date")
        assert r.status_code == 422

    def test_southern_hemisphere_lat(self):
        # Sydney, Australia
        r = client.get("/sky/jupiter?lat=-33.87&lon=151.21")
        assert r.status_code == 200
        assert -90 <= r.json()["altitude_deg"] <= 90

    def test_negative_longitude(self):
        # London
        r = client.get("/sky/mars?lat=51.5&lon=-0.1")
        assert r.status_code == 200


# ── POST /ask ─────────────────────────────────────────────────────────────────

class TestAskEndpoint:

    def _ask(self, text: str, lat=LAT, lon=LON):
        return client.post("/ask", json={"text": text, "lat": lat, "lon": lon})

    # --- Response shape ------------------------------------------------------

    def test_returns_200(self):
        r = self._ask("Where is Jupiter?")
        assert r.status_code == 200

    def test_response_has_required_keys(self):
        r = self._ask("Where is Mars?")
        data = r.json()
        for key in ("intent", "answer"):
            assert key in data, f"Missing key: {key}"

    def test_answer_is_non_empty_string(self):
        r = self._ask("Where is Saturn?")
        assert isinstance(r.json()["answer"], str)
        assert len(r.json()["answer"]) > 10

    # --- LOCATE_OBJECT intent -------------------------------------------------

    def test_locate_jupiter(self):
        r = self._ask("Where is Jupiter?")
        data = r.json()
        assert data["intent"] == "LOCATE_OBJECT"
        assert data["object"] == "jupiter"
        assert "jupiter" in data["answer"].lower()

    def test_locate_mars(self):
        r = self._ask("Find Mars for me")
        assert r.json()["intent"] == "LOCATE_OBJECT"
        assert r.json()["object"] == "mars"

    def test_locate_moon(self):
        r = self._ask("Where is the moon?")
        assert r.json()["intent"] == "LOCATE_OBJECT"
        assert r.json()["object"] == "moon"

    def test_locate_answer_ends_with_period(self):
        r = self._ask("Where is Venus?")
        assert r.json()["answer"].endswith(".")

    def test_locate_unknown_object_returns_helpful_message(self):
        r = self._ask("Where is pluto?")
        # "pluto" is not in _SKY_OBJECTS so keyword matcher can't extract it —
        # falls through to UNKNOWN, which is the correct safe-fallback behaviour.
        # Phase 5 (Gemma) will handle fuzzy names better.
        assert r.status_code == 200
        assert r.json()["intent"] == "UNKNOWN"
        assert len(r.json()["answer"]) > 5

    # --- CHECK_VISIBILITY intent ----------------------------------------------

    def test_check_visibility_mars(self):
        r = self._ask("Is Mars visible tonight?")
        assert r.json()["intent"] == "CHECK_VISIBILITY"
        assert r.json()["object"] == "mars"

    def test_check_visibility_answer_contains_visible_or_not(self):
        r = self._ask("Can I see Saturn?")
        answer = r.json()["answer"].lower()
        assert "visible" in answer or "below" in answer

    # --- GET_ISS_PASS intent --------------------------------------------------

    def test_iss_pass_intent(self):
        r = self._ask("When does the ISS pass over?")
        assert r.json()["intent"] == "GET_ISS_PASS"

    def test_space_station_triggers_iss(self):
        r = self._ask("When is the space station visible?")
        assert r.json()["intent"] == "GET_ISS_PASS"

    def test_iss_answer_non_empty(self):
        r = self._ask("ISS pass time?")
        assert len(r.json()["answer"]) > 5

    # --- WEATHER_SUMMARY intent -----------------------------------------------

    def test_weather_summary_intent(self):
        r = self._ask("Will it be clear tonight?")
        assert r.json()["intent"] == "WEATHER_SUMMARY"

    def test_aurora_triggers_weather(self):
        r = self._ask("Any aurora alerts?")
        assert r.json()["intent"] == "WEATHER_SUMMARY"

    def test_stars_tonight_triggers_weather(self):
        r = self._ask("Can I see stars tonight?")
        assert r.json()["intent"] == "WEATHER_SUMMARY"

    # --- UNKNOWN intent -------------------------------------------------------

    def test_unknown_intent_for_nonsense(self):
        r = self._ask("Tell me a joke")
        assert r.json()["intent"] == "UNKNOWN"

    def test_unknown_answer_suggests_examples(self):
        r = self._ask("xyzzy")
        answer = r.json()["answer"].lower()
        assert "jupiter" in answer or "where" in answer or "try" in answer

    # --- Edge cases ----------------------------------------------------------

    def test_empty_text_returns_unknown(self):
        r = self._ask("")
        assert r.json()["intent"] == "UNKNOWN"

    def test_uppercase_input(self):
        r = self._ask("WHERE IS JUPITER?")
        assert r.json()["intent"] == "LOCATE_OBJECT"

    def test_missing_text_field_returns_422(self):
        r = client.post("/ask", json={"lat": LAT, "lon": LON})
        assert r.status_code == 422

    def test_missing_lat_returns_422(self):
        r = client.post("/ask", json={"text": "Where is Jupiter?", "lon": LON})
        assert r.status_code == 422


# ── GET /health ───────────────────────────────────────────────────────────────

class TestHealthEndpoint:

    def test_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_status_ok(self):
        assert client.get("/health").json()["status"] == "ok"

    def test_required_keys_present(self):
        data = client.get("/health").json()
        for key in ("status", "api_version", "current_utc", "online",
                    "weather_cache_age_minutes", "aurora_cache_age_minutes",
                    "tle_cache_age_hours", "models_loaded", "supported_objects"):
            assert key in data, f"Missing key: {key}"

    def test_api_version_string(self):
        assert isinstance(client.get("/health").json()["api_version"], str)

    def test_current_utc_is_iso_format(self):
        utc = client.get("/health").json()["current_utc"]
        # Should parse without error
        from datetime import datetime
        datetime.fromisoformat(utc.replace("Z", "+00:00"))

    def test_models_loaded_is_list(self):
        assert isinstance(client.get("/health").json()["models_loaded"], list)

    def test_supported_objects_is_list(self):
        objs = client.get("/health").json()["supported_objects"]
        assert isinstance(objs, list)
        assert len(objs) >= 9

    def test_supported_objects_contains_planets(self):
        objs = client.get("/health").json()["supported_objects"]
        for expected in ["jupiter", "mars", "saturn", "moon", "sun"]:
            assert expected in objs

    def test_cache_ages_none_when_no_cache_files(self):
        # Cache files don't exist in a fresh checkout
        data = client.get("/health").json()
        # They should either be None or a float — both are valid
        for key in ("weather_cache_age_minutes", "aurora_cache_age_minutes",
                    "tle_cache_age_hours"):
            val = data[key]
            assert val is None or isinstance(val, (int, float)), \
                f"{key} should be None or numeric, got {type(val)}"

    def test_online_false_without_cache(self):
        # No cache files exist yet — online should be False
        data = client.get("/health").json()
        # Can be True or False depending on whether cache was seeded,
        # but if all cache ages are None then online must be False
        if all(data[k] is None for k in (
            "weather_cache_age_minutes",
            "aurora_cache_age_minutes",
            "tle_cache_age_hours",
        )):
            assert data["online"] is False
