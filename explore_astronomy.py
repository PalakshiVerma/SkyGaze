"""
Exploration script for astronomy-engine.
Prints azimuth and altitude for Sun, Moon, and all planets
at the current time for a hardcoded location.

Run with:
    .venv\Scripts\python.exe explore_astronomy.py
"""

import astronomy
from datetime import datetime, timezone

# ── Observer location (change to your own) ──────────────────────────────────
LATITUDE  = 28.6139   # New Delhi, India
LONGITUDE = 77.2090
# ────────────────────────────────────────────────────────────────────────────

def get_horizontal(body: astronomy.Body, observer: astronomy.Observer, time: astronomy.Time):
    """Return (azimuth, altitude) for a solar-system body."""
    equatorial = astronomy.Equator(body, time, observer, ofdate=True, aberration=True)
    horizontal = astronomy.Horizon(time, observer, equatorial.ra, equatorial.dec, refraction=astronomy.Refraction.Normal)
    return horizontal.azimuth, horizontal.altitude


def main():
    now_utc = datetime.now(timezone.utc)
    print(f"Observer : lat={LATITUDE}°  lon={LONGITUDE}°")
    print(f"Time UTC : {now_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'─' * 52}")
    print(f"{'Object':<12} {'Azimuth':>10}  {'Altitude':>10}  {'Visible'}")
    print(f"{'─' * 52}")

    observer = astronomy.Observer(LATITUDE, LONGITUDE, 0)
    time = astronomy.Time.Make(
        now_utc.year, now_utc.month, now_utc.day,
        now_utc.hour, now_utc.minute, float(now_utc.second)
    )

    bodies = [
        astronomy.Body.Sun,
        astronomy.Body.Moon,
        astronomy.Body.Mercury,
        astronomy.Body.Venus,
        astronomy.Body.Mars,
        astronomy.Body.Jupiter,
        astronomy.Body.Saturn,
        astronomy.Body.Uranus,
        astronomy.Body.Neptune,
    ]

    for body in bodies:
        try:
            az, alt = get_horizontal(body, observer, time)
            visible = "✅ yes" if alt > 0 else "❌ below horizon"
            print(f"{body.name:<12} {az:>9.2f}°  {alt:>9.2f}°  {visible}")
        except Exception as e:
            print(f"{body.name:<12} ERROR: {e}")

    print(f"{'─' * 52}")
    print("Done. Compare these values against Stellarium for the same time.")


if __name__ == "__main__":
    main()
