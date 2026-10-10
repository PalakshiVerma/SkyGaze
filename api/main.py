"""
api/main.py
───────────
SkyGaze FastAPI backend.

Endpoints
─────────
  GET  /                       Health ping
  GET  /sky/{object}           Azimuth + altitude for a sky object
  POST /ask                    Natural-language question → spoken answer (LLM wired in Phase 5)
  GET  /health                 System status, cache ages, models loaded

Run locally:
  uvicorn api.main:app --reload

Docs:
  http://localhost:8000/docs
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ── Path fix so imports work when run from repo root ─────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.astro import get_position, list_supported_objects
from spatial import full_description, compass_direction, altitude_phrase

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SkyGaze API",
    description=(
        "Voice-guided stargazing assistant backend. "
        "Computes celestial positions deterministically — the LLM never does the maths."
    ),
    version="0.1.0",
)

# Allow Streamlit UI (same machine or cross-origin in dev) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Cache directory ───────────────────────────────────────────────────────────

CACHE_DIR = ROOT / "cache"


def _cache_age_minutes(filename: str) -> Optional[float]:
    """Return age of a cache file in minutes, or None if it doesn't exist."""
    path = CACHE_DIR / filename
    if not path.exists():
        return None
    mtime = path.stat().st_mtime
    age_seconds = datetime.now(timezone.utc).timestamp() - mtime
    return round(age_seconds / 60, 1)


# ── Request / Response models ─────────────────────────────────────────────────

class SkyObjectResponse(BaseModel):
    object: str             = Field(description="Normalised object name")
    display_name: str       = Field(description="Human-friendly name, e.g. 'the Moon'")
    azimuth_deg: float      = Field(description="Compass bearing 0–360°, north=0")
    altitude_deg: float     = Field(description="Degrees above horizon; negative = below")
    is_visible: bool        = Field(description="True when altitude > 0°")
    direction: str          = Field(description="16-point compass label, e.g. 'east-northeast'")
    altitude_phrase: str    = Field(description="Natural altitude description")
    spoken_description: str = Field(description="Complete spoken sentence for TTS")


class AskRequest(BaseModel):
    text: str               = Field(description="Natural-language question from the user")
    lat:  float             = Field(description="Observer latitude in decimal degrees")
    lon:  float             = Field(description="Observer longitude in decimal degrees")


class AskResponse(BaseModel):
    intent: str             = Field(description="Parsed intent (stub until Phase 5)")
    object: Optional[str]   = Field(default=None, description="Target object if applicable")
    answer: str             = Field(description="Spoken-style answer")
    note:   Optional[str]   = Field(default=None, description="Developer note")


class HealthResponse(BaseModel):
    status: str
    api_version: str
    current_utc: str
    online: bool
    weather_cache_age_minutes: Optional[float]
    aurora_cache_age_minutes:  Optional[float]
    tle_cache_age_hours:       Optional[float]
    models_loaded: list[str]
    supported_objects: list[str]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", summary="Root ping")
def root():
    """Quick liveness check — returns API name and version."""
    return {"status": "ok", "app": "SkyGaze API", "version": "0.1.0"}


@app.get(
    "/sky/{object_name}",
    response_model=SkyObjectResponse,
    summary="Get position of a sky object",
    tags=["Astronomy"],
)
def get_sky_object(
    object_name: str,
    lat: float = Query(..., description="Observer latitude (decimal degrees, north positive)"),
    lon: float = Query(..., description="Observer longitude (decimal degrees, east positive)"),
    time_utc: Optional[str] = Query(
        default=None,
        description="ISO-8601 UTC datetime, e.g. 2026-10-07T18:00:00. Defaults to now.",
    ),
):
    """
    Return the current (or specified-time) azimuth and altitude for a solar-system object.

    Supported objects: sun, moon, mercury, venus, mars, jupiter, saturn, uranus, neptune.

    Example:
        GET /sky/jupiter?lat=28.6139&lon=77.2090
    """
    # Parse optional time
    parsed_time: Optional[datetime] = None
    if time_utc:
        try:
            parsed_time = datetime.fromisoformat(time_utc.replace("Z", "+00:00"))
            if parsed_time.tzinfo is None:
                parsed_time = parsed_time.replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid time_utc format '{time_utc}'. Use ISO-8601, e.g. 2026-10-07T18:00:00Z",
            )

    # Validate lat/lon ranges
    if not (-90 <= lat <= 90):
        raise HTTPException(status_code=422, detail=f"lat must be between -90 and 90, got {lat}")
    if not (-180 <= lon <= 180):
        raise HTTPException(status_code=422, detail=f"lon must be between -180 and 180, got {lon}")

    # Compute position
    result = get_position(object_name, lat, lon, parsed_time)

    if "error" in result:
        raise HTTPException(
            status_code=404,
            detail=result["error"],
        )

    direction    = compass_direction(result["azimuth_deg"])
    alt_phrase   = altitude_phrase(result["altitude_deg"])
    spoken       = full_description(result)

    return SkyObjectResponse(
        object=result["object"],
        display_name=result["display_name"],
        azimuth_deg=result["azimuth_deg"],
        altitude_deg=result["altitude_deg"],
        is_visible=result["is_visible"],
        direction=direction,
        altitude_phrase=alt_phrase,
        spoken_description=spoken,
    )


@app.post(
    "/ask",
    response_model=AskResponse,
    summary="Ask a natural-language question about the sky",
    tags=["Assistant"],
)
def ask(request: AskRequest):
    """
    Accepts a natural-language question and returns a spoken-style answer.

    **Phase 5 note:** The LLM (Gemma) intent parser is not yet wired in.
    This endpoint currently uses a simple keyword matcher as a placeholder
    so the Streamlit UI has something real to call. Full intent parsing
    arrives in Phase 5.

    Example request body:
        { "text": "Where is Jupiter?", "lat": 28.6139, "lon": 77.2090 }
    """
    text_lower = request.text.strip().lower()

    # ── Simple keyword intent matcher (placeholder for Gemma in Phase 5) ─────
    intent, target_object = _simple_intent_match(text_lower)

    if intent == "LOCATE_OBJECT" and target_object:
        result = get_position(target_object, request.lat, request.lon)
        if "error" in result:
            return AskResponse(
                intent=intent,
                object=target_object,
                answer=f"Sorry, I don't know about '{target_object}'. "
                       f"I can find: {', '.join(list_supported_objects())}.",
                note="Object not found in astronomy database.",
            )
        answer = full_description(result)
        return AskResponse(
            intent=intent,
            object=target_object,
            answer=answer,
            note="Keyword matcher active — Gemma LLM wires in Phase 5.",
        )

    elif intent == "CHECK_VISIBILITY" and target_object:
        result = get_position(target_object, request.lat, request.lon)
        if "error" not in result:
            vis = "visible" if result["is_visible"] else "not visible"
            answer = (
                f"{result['display_name']} is {vis} right now. "
                f"{full_description(result)}"
            )
        else:
            answer = f"Sorry, I couldn't find '{target_object}'."
        return AskResponse(
            intent=intent,
            object=target_object,
            answer=answer,
            note="Keyword matcher active — Gemma LLM wires in Phase 5.",
        )

    elif intent == "GET_ISS_PASS":
        return AskResponse(
            intent=intent,
            object="ISS",
            answer="ISS pass prediction is coming in Phase 7. Stay tuned!",
            note="Satellite tracking not yet implemented.",
        )

    elif intent == "WEATHER_SUMMARY":
        return AskResponse(
            intent=intent,
            answer="Weather and aurora data will be available after Phase 8. "
                   "Run POST /prepare while online to fetch forecasts.",
            note="Weather cache not yet implemented.",
        )

    else:
        return AskResponse(
            intent="UNKNOWN",
            answer=(
                "I'm not sure what you're asking. Try something like: "
                "'Where is Jupiter?', 'Is Mars visible?', or 'When does the ISS pass?'"
            ),
            note="No matching intent found. Gemma LLM will improve this in Phase 5.",
        )


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="System health and cache status",
    tags=["System"],
)
def health():
    """
    Returns the current system status including:
    - API version and UTC time
    - Online/offline state (based on whether cache files exist)
    - Age of cached weather, aurora and TLE data
    - Which models are loaded (populated in Phase 4 & 5)
    """
    weather_age = _cache_age_minutes("weather.json")
    aurora_age  = _cache_age_minutes("aurora.json")
    tle_age_min = _cache_age_minutes("iss_tle.txt")
    tle_age_hrs = round(tle_age_min / 60, 2) if tle_age_min is not None else None

    # Consider "online-prepared" if all three caches exist and are < 24 hours old
    cache_fresh = all(
        age is not None and age < 24 * 60
        for age in [weather_age, aurora_age, tle_age_min]
    )

    return HealthResponse(
        status="ok",
        api_version="0.1.0",
        current_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        online=cache_fresh,
        weather_cache_age_minutes=weather_age,
        aurora_cache_age_minutes=aurora_age,
        tle_cache_age_hours=tle_age_hrs,
        models_loaded=[],       # populated in Phase 4 (Whisper) and Phase 5 (Gemma)
        supported_objects=list_supported_objects(),
    )


# ── Intent keyword matcher (placeholder until Phase 5 LLM) ───────────────────

_SKY_OBJECTS = [
    "sun", "moon", "mercury", "venus", "mars",
    "jupiter", "saturn", "uranus", "neptune",
    # Bright stars
    "polaris", "sirius", "canopus", "arcturus",
    "vega", "betelgeuse", "rigel", "antares",
]

# Multi-word aliases checked before single-word scan
_SKY_ALIASES: dict[str, str] = {
    "north star":     "polaris",
    "pole star":      "polaris",
    "lodestar":       "polaris",
    "dog star":       "sirius",
    "evening star":   "venus",
    "morning star":   "venus",
    "the moon":       "moon",
    "scorpion heart": "antares",
}

_LOCATE_KEYWORDS  = ["where", "find", "show", "locate", "position", "direction"]
_VISIBLE_KEYWORDS = ["visible", "can i see", "see tonight", "is it up", "rise", "set"]
_ISS_KEYWORDS     = ["iss", "space station", "international space"]
_WEATHER_KEYWORDS = ["weather", "cloud", "aurora", "clear", "stars tonight"]


def _simple_intent_match(text: str) -> tuple[str, Optional[str]]:
    """
    Keyword-based intent matcher used until Gemma is wired in (Phase 5).
    Returns (intent, object_name_or_None).
    """
    # ISS check first (before generic locate)
    if any(kw in text for kw in _ISS_KEYWORDS):
        return "GET_ISS_PASS", None

    # Weather / aurora
    if any(kw in text for kw in _WEATHER_KEYWORDS):
        return "WEATHER_SUMMARY", None

    # Find which sky object is mentioned.
    # Multi-word aliases ("north star", "dog star", ...) are checked first so
    # they resolve before the single-word name scan.
    mentioned = next(
        (_SKY_ALIASES[alias] for alias in _SKY_ALIASES if alias in text), None
    )
    if mentioned is None:
        mentioned = next((obj for obj in _SKY_OBJECTS if obj in text), None)
    if mentioned is None and "the moon" in text:
        mentioned = "moon"

    # Visibility question
    if any(kw in text for kw in _VISIBLE_KEYWORDS) and mentioned:
        return "CHECK_VISIBILITY", mentioned

    # Locate question (default if an object is mentioned)
    if mentioned:
        return "LOCATE_OBJECT", mentioned

    return "UNKNOWN", None


# ── Dev entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
