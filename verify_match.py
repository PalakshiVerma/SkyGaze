"""
Verify our engine against Stellarium at the matched time: 2026-10-07 00:07 UTC
(Stellarium appears to be set to midnight UTC / 05:30 IST)
"""
from tools.astro import get_position
from datetime import datetime, timezone

LAT, LON = 28.6139, 77.2090
# Best match time from scan
T = datetime(2026, 10, 7, 0, 7, 0, tzinfo=timezone.utc)

# Values from Stellarium (converted from DMS to decimal)
stellarium = {
    "saturn":  (268 + 21/60 + 27/3600,   7 + 1/60 + 17/3600),   # 268.357°  +7.021°
    "uranus":  (261 + 52/60 + 17/3600,  61 + 5/60 + 27/3600),   # 261.871° +61.091°
    "neptune": (270 + 25/60 + 51/3600,  -(0 + 36/60 + 34/3600)),# 270.431°  -0.609°
}

print(f"Verification at {T.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print(f"Observer: New Delhi (lat={LAT}, lon={LON})\n")
print(f"{'Object':<10} {'Our Az':>9} {'Stell Az':>9} {'ΔAz':>6}  {'Our Alt':>8} {'Stell Alt':>10} {'ΔAlt':>6}  {'Match?'}")
print("─" * 80)

all_ok = True
for name, (saz, salt) in stellarium.items():
    r = get_position(name, LAT, LON, T)
    daz  = abs(r["azimuth_deg"]  - saz)
    dalt = abs(r["altitude_deg"] - salt)
    ok = daz <= 1.0 and dalt <= 1.0
    if not ok:
        all_ok = False
    flag = "✅" if ok else "❌"
    print(
        f"{name:<10} {r['azimuth_deg']:>8.2f}° {saz:>8.2f}°  {daz:>5.2f}°"
        f"  {r['altitude_deg']:>7.2f}° {salt:>9.2f}°  {dalt:>5.2f}°  {flag}"
    )

print("─" * 80)
print(f"\n{'✅ All within 1° tolerance — astronomy engine verified!' if all_ok else '❌ Some values outside tolerance.'}")
