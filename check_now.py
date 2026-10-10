from tools.astro import get_position
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
print(f"Current UTC: {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print()
for name in ["saturn", "uranus", "neptune"]:
    r = get_position(name, 28.6139, 77.2090)
    print(f"{name:<10}  az={r['azimuth_deg']:>8.2f}°   alt={r['altitude_deg']:>8.2f}°   visible={r['is_visible']}")
