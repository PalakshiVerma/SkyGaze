"""
tools/astro.py
──────────────
Computes azimuth and altitude for solar-system objects given an observer
location and a UTC time.

The LLM never calls this directly — the tool router in api/main.py does.
All maths is deterministic; no AI or network required.

Usage example
─────────────
    from tools.astro import get_position
    from datetime import datetime, timezone

    result = get_position("jupiter", lat=28.6139, lon=77.2090)
    print(result["spoken_description"])
    # → "Jupiter is to the east, about a third of the way up the sky."
"""

import astronomy
from datetime import datetime, timezone
from typing import Optional


# ── Fixed stars: RA (hours), Dec (degrees), distance (light-years) ───────────
#
# astronomy-engine supports up to 8 user-defined stars (Star1..Star8).
# We define the most commonly asked-about bright stars here.
# RA/Dec are J2000 equatorial coordinates.

_STAR_CATALOGUE: list[tuple[astronomy.Body, str, str, float, float, float]] = [
    # (Body,           key,           display name,        RA hrs,   Dec °,   dist ly)
    (astronomy.Body.Star1, "polaris",   "Polaris (North Star)",  2.5303,  89.2641, 447.0),
    (astronomy.Body.Star2, "sirius",    "Sirius",                6.7525, -16.7161,   8.6),
    (astronomy.Body.Star3, "canopus",   "Canopus",               6.3992, -52.6957, 310.0),
    (astronomy.Body.Star4, "arcturus",  "Arcturus",             14.2610,  19.1822,  37.0),
    (astronomy.Body.Star5, "vega",      "Vega",                 18.6157,  38.7837,  25.0),
    (astronomy.Body.Star6, "betelgeuse","Betelgeuse",            5.9195,   7.4071, 700.0),
    (astronomy.Body.Star7, "rigel",     "Rigel",                 5.2423,  -8.2017, 860.0),
    (astronomy.Body.Star8, "antares",   "Antares",              16.4901, -26.4320, 550.0),
]

# Register all stars with the library at import time
for _body, _key, _name, _ra, _dec, _dist in _STAR_CATALOGUE:
    astronomy.DefineStar(_body, _ra, _dec, _dist)

# Build star key → Body and display name lookups
_STAR_BODY_MAP:    dict[str, astronomy.Body] = {k: b for b, k, *_ in _STAR_CATALOGUE}
_STAR_DISPLAY_MAP: dict[str, str]            = {k: n for _, k, n, *_ in _STAR_CATALOGUE}

# Common aliases that map to a canonical star key
_STAR_ALIASES: dict[str, str] = {
    "north star":    "polaris",
    "pole star":     "polaris",
    "lodestar":      "polaris",
    "dog star":      "sirius",
    "evening star":  "venus",   # Venus alias — routes to planet
    "morning star":  "venus",
    "scorpion heart":"antares",
    "hunter shoulder":"betelgeuse",
    "hunter foot":   "rigel",
}


# ── Object name → astronomy.Body mapping ────────────────────────────────────

_BODY_MAP: dict[str, astronomy.Body] = {
    # Sun
    "sun":       astronomy.Body.Sun,
    # Moon
    "moon":      astronomy.Body.Moon,
    "the moon":  astronomy.Body.Moon,
    # Planets
    "mercury":   astronomy.Body.Mercury,
    "venus":     astronomy.Body.Venus,
    "earth":     astronomy.Body.Earth,
    "mars":      astronomy.Body.Mars,
    "jupiter":   astronomy.Body.Jupiter,
    "saturn":    astronomy.Body.Saturn,
    "uranus":    astronomy.Body.Uranus,
    "neptune":   astronomy.Body.Neptune,
    # Stars (merged in)
    **_STAR_BODY_MAP,
}

# Human-friendly display names
_DISPLAY_NAME: dict[str, str] = {
    "sun":       "the Sun",
    "moon":      "the Moon",
    "the moon":  "the Moon",
    "mercury":   "Mercury",
    "venus":     "Venus",
    "earth":     "Earth",
    "mars":      "Mars",
    "jupiter":   "Jupiter",
    "saturn":    "Saturn",
    "uranus":    "Uranus",
    "neptune":   "Neptune",
    **_STAR_DISPLAY_MAP,
}

# Objects for which we never expect a below-horizon answer to be surprising
_ALWAYS_BELOW: frozenset[str] = frozenset({"earth"})


# ── Public API ───────────────────────────────────────────────────────────────

def get_position(
    object_name: str,
    lat: float,
    lon: float,
    time_utc: Optional[datetime] = None,
    elevation_m: float = 0.0,
) -> dict:
    """
    Return the horizontal position of a solar-system object.

    Parameters
    ----------
    object_name : str
        Case-insensitive name, e.g. "Jupiter", "the moon", "mars".
    lat : float
        Observer latitude in decimal degrees (north positive).
    lon : float
        Observer longitude in decimal degrees (east positive).
    time_utc : datetime, optional
        UTC time of observation.  Defaults to now.
    elevation_m : float, optional
        Observer elevation above sea level in metres.  Defaults to 0.

    Returns
    -------
    dict with keys:
        object          str    Normalised object name used internally
        display_name    str    Human-friendly name ("the Moon", "Jupiter")
        azimuth_deg     float  0–360°, north = 0, east = 90
        altitude_deg    float  −90 to +90°, positive = above horizon
        is_visible      bool   True when altitude > 0°
        error           str    Present only on failure; all other keys absent

    Raises
    ------
    Does not raise — errors are returned as {"error": "..."} dicts so the
    API layer can handle them gracefully.
    """
    # ── Normalise input ──────────────────────────────────────────────────────
    key = object_name.strip().lower()

    # Resolve common aliases ("north star" → "polaris", "evening star" → "venus")
    key = _STAR_ALIASES.get(key, key)

    if key not in _BODY_MAP:
        return {
            "error": (
                f"Unknown object '{object_name}'. "
                f"Supported objects: {', '.join(sorted(_BODY_MAP.keys()))}."
            )
        }

    body = _BODY_MAP[key]
    display = _DISPLAY_NAME[key]

    # ── Build time ───────────────────────────────────────────────────────────
    if time_utc is None:
        time_utc = datetime.now(timezone.utc)
    elif time_utc.tzinfo is None:
        # Treat naive datetimes as UTC
        time_utc = time_utc.replace(tzinfo=timezone.utc)

    ast_time = astronomy.Time.Make(
        time_utc.year,
        time_utc.month,
        time_utc.day,
        time_utc.hour,
        time_utc.minute,
        float(time_utc.second) + time_utc.microsecond / 1_000_000,
    )

    # ── Build observer ───────────────────────────────────────────────────────
    observer = astronomy.Observer(lat, lon, elevation_m)

    # ── Compute equatorial → horizontal ─────────────────────────────────────
    equatorial = astronomy.Equator(
        body, ast_time, observer, ofdate=True, aberration=True
    )
    horizontal = astronomy.Horizon(
        ast_time,
        observer,
        equatorial.ra,
        equatorial.dec,
        refraction=astronomy.Refraction.Normal,
    )

    azimuth  = round(horizontal.azimuth, 2)
    altitude = round(horizontal.altitude, 2)
    is_visible = altitude > 0.0

    return {
        "object":       key,
        "display_name": display,
        "azimuth_deg":  azimuth,
        "altitude_deg": altitude,
        "is_visible":   is_visible,
    }


def list_supported_objects() -> list[str]:
    """Return a sorted list of all supported object names."""
    return sorted(_BODY_MAP.keys())


# ── CLI smoke-test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Quick sanity check — run directly to print all positions.
    # Replace lat/lon with your actual location.
    LAT, LON = 28.6139, 77.2090  # New Delhi, India

    print(f"Observer: lat={LAT}  lon={LON}")
    print(f"Time UTC: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
    print(f"{'Object':<14} {'Azimuth':>10}  {'Altitude':>10}  {'Visible'}")
    print("─" * 52)

    objects = [
        "sun", "moon", "mercury", "venus", "mars",
        "jupiter", "saturn", "uranus", "neptune",
    ]

    for name in objects:
        result = get_position(name, LAT, LON)
        if "error" in result:
            print(f"{name:<14} ERROR: {result['error']}")
        else:
            vis = "✅ yes" if result["is_visible"] else "❌ below horizon"
            print(
                f"{result['display_name']:<14} "
                f"{result['azimuth_deg']:>9.2f}°  "
                f"{result['altitude_deg']:>9.2f}°  "
                f"{vis}"
            )
