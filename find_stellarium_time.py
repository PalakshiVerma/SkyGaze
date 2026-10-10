"""
Scans through UTC hours today to find which time matches
Stellarium's reported Saturn az=268.36, alt=+7.02
(from user's Stellarium screenshot)
"""
from tools.astro import get_position
from datetime import datetime, timezone, timedelta

LAT, LON = 28.6139, 77.2090

# Target from Stellarium
TARGET = {
    "saturn":  (268.36,  7.02),
    "uranus":  (261.87, 61.09),
    "neptune": (270.43, -0.61),
}

print("Scanning UTC hours to find matching time...\n")
print(f"{'UTC Time':<22} {'Saturn Az':>10} {'Saturn Alt':>11} {'ΔAz':>7} {'ΔAlt':>7}")
print("─" * 65)

base = datetime(2026, 10, 7, 0, 0, 0, tzinfo=timezone.utc)
for hour in range(24):
    for minute in [0, 15, 30, 45]:
        t = base + timedelta(hours=hour, minutes=minute)
        r = get_position("saturn", LAT, LON, t)
        daz  = abs(r["azimuth_deg"]  - TARGET["saturn"][0])
        dalt = abs(r["altitude_deg"] - TARGET["saturn"][1])
        if daz < 5 and dalt < 5:
            print(f"{t.strftime('%Y-%m-%d %H:%M UTC'):<22} {r['azimuth_deg']:>10.2f}° {r['altitude_deg']:>10.2f}°  {daz:>6.2f}°  {dalt:>6.2f}°  ← MATCH")
        elif daz < 15 and dalt < 15:
            print(f"{t.strftime('%Y-%m-%d %H:%M UTC'):<22} {r['azimuth_deg']:>10.2f}° {r['altitude_deg']:>10.2f}°  {daz:>6.2f}°  {dalt:>6.2f}°")
