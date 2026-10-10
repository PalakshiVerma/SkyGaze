"""
spatial.py
──────────
Converts raw azimuth and altitude numbers into human-readable phrases
suitable for spoken TTS output.

No AI, no network — pure deterministic maths and lookup tables.

Public API
──────────
    compass_direction(azimuth_deg)           → "east-northeast"
    altitude_phrase(altitude_deg)            → "about a third of the way up the sky"
    describe_position(display_name, az, alt) → "Jupiter is to the east-northeast, ..."

Usage example
─────────────
    from spatial import describe_position
    print(describe_position("Jupiter", 82.3, 37.1))
    # → "Jupiter is to the east-northeast, about a third of the way up the sky."
"""

# ── 16-point compass ─────────────────────────────────────────────────────────
#
# Each entry: (upper_bound_exclusive, label)
# Azimuth is 0–360° clockwise from North.
# We use the midpoint convention: N covers 348.75–11.25°, etc.
# To avoid floating-point boundary issues we normalise azimuth to [0, 360)
# before lookup.

_COMPASS_SECTORS: list[tuple[float, str]] = [
    (11.25,  "north"),
    (33.75,  "north-northeast"),
    (56.25,  "northeast"),
    (78.75,  "east-northeast"),
    (101.25, "east"),
    (123.75, "east-southeast"),
    (146.25, "southeast"),
    (168.75, "south-southeast"),
    (191.25, "south"),
    (213.75, "south-southwest"),
    (236.25, "southwest"),
    (258.75, "west-southwest"),
    (281.25, "west"),
    (303.75, "west-northwest"),
    (326.25, "northwest"),
    (348.75, "north-northwest"),
    # Anything ≥ 348.75 falls back to "north" via the safety return below
]

# ── Altitude buckets ─────────────────────────────────────────────────────────
#
# Each entry: (min_inclusive, max_exclusive, phrase)
# Altitude ranges from −90° (nadir) to +90° (zenith).

_ALTITUDE_BUCKETS: list[tuple[float, float, str]] = [
    (-90.0,  0.0,  "below the horizon"),
    (  0.0,  5.0,  "very low on the horizon"),
    (  5.0, 15.0,  "low in the sky"),
    ( 15.0, 30.0,  "fairly low in the sky"),
    ( 30.0, 50.0,  "about a third of the way up the sky"),
    ( 50.0, 70.0,  "about halfway up the sky"),
    ( 70.0, 85.0,  "high in the sky"),
    ( 85.0, 90.01, "nearly overhead"),   # 90.01 so exactly 90 is captured
]


# ── Public functions ──────────────────────────────────────────────────────────

def compass_direction(azimuth_deg: float) -> str:
    """
    Convert an azimuth in decimal degrees to a 16-point compass label.

    Parameters
    ----------
    azimuth_deg : float
        Azimuth in degrees, any value (will be normalised to [0, 360)).

    Returns
    -------
    str
        One of the 16 compass point strings, e.g. "east-northeast".

    Examples
    --------
    >>> compass_direction(0)
    'north'
    >>> compass_direction(90)
    'east'
    >>> compass_direction(360)
    'north'
    >>> compass_direction(-10)
    'north-northwest'
    """
    # Normalise to [0, 360)
    az = azimuth_deg % 360.0

    for upper, label in _COMPASS_SECTORS:
        if az < upper:
            return label

    # Safety fallback — should be unreachable with the table above
    return "north"


def altitude_phrase(altitude_deg: float) -> str:
    """
    Convert an altitude in decimal degrees to a natural-language phrase.

    Parameters
    ----------
    altitude_deg : float
        Altitude in degrees, −90 to +90.

    Returns
    -------
    str
        A descriptive phrase, e.g. "about a third of the way up the sky".

    Examples
    --------
    >>> altitude_phrase(37)
    'about a third of the way up the sky'
    >>> altitude_phrase(-5)
    'below the horizon'
    >>> altitude_phrase(90)
    'nearly overhead'
    """
    for lo, hi, phrase in _ALTITUDE_BUCKETS:
        if lo <= altitude_deg < hi:
            return phrase

    # Clamp out-of-range values gracefully
    if altitude_deg < -90.0:
        return "below the horizon"
    return "nearly overhead"  # > 90 (shouldn't happen but safe)


def describe_position(display_name: str, azimuth_deg: float, altitude_deg: float) -> str:
    """
    Produce a complete spoken-style sentence describing where an object is.

    Parameters
    ----------
    display_name : str
        Human-friendly object name, e.g. "Jupiter", "the Moon".
    azimuth_deg : float
        Azimuth in degrees.
    altitude_deg : float
        Altitude in degrees.

    Returns
    -------
    str
        A natural sentence, e.g.:
        "Jupiter is to the east-northeast, about a third of the way up the sky."
        "The Moon is below the horizon right now."

    Examples
    --------
    >>> describe_position("Jupiter", 82.3, 37.1)
    'Jupiter is to the east-northeast, about a third of the way up the sky.'
    >>> describe_position("the Moon", 227.3, -5.0)
    'The Moon is below the horizon right now.'
    """
    direction = compass_direction(azimuth_deg)
    alt_phrase = altitude_phrase(altitude_deg)

    # Capitalise first letter of display name for sentence start
    name_cap = display_name[0].upper() + display_name[1:]

    if altitude_deg <= 0.0:
        return f"{name_cap} is below the horizon right now."

    return f"{name_cap} is to the {direction}, {alt_phrase}."


def full_description(position_dict: dict) -> str:
    """
    Convenience wrapper: takes the dict returned by tools/astro.get_position()
    and returns a spoken sentence.

    Parameters
    ----------
    position_dict : dict
        Must contain keys: display_name, azimuth_deg, altitude_deg.
        If key "error" is present, returns the error message instead.

    Returns
    -------
    str
        Spoken sentence or error string.

    Examples
    --------
    >>> from tools.astro import get_position
    >>> pos = get_position("jupiter", lat=28.6, lon=77.2)
    >>> full_description(pos)
    'Jupiter is to the ...'
    """
    if "error" in position_dict:
        return f"Sorry, I couldn't find that object. {position_dict['error']}"

    return describe_position(
        position_dict["display_name"],
        position_dict["azimuth_deg"],
        position_dict["altitude_deg"],
    )


# ── CLI demo ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        ("Jupiter",  82.3,  37.1),
        ("the Moon", 227.3, -5.0),
        ("Mars",     270.0, 49.0),
        ("Venus",    0.0,   2.0),
        ("Saturn",   359.9, 88.0),
        ("Mercury",  180.0, 0.0),
        ("Uranus",   315.0, 72.5),
    ]

    print(f"{'Object':<12} {'Az':>7}  {'Alt':>7}  {'Sentence'}")
    print("─" * 80)
    for name, az, alt in test_cases:
        sentence = describe_position(name, az, alt)
        print(f"{name:<12} {az:>6.1f}°  {alt:>6.1f}°  {sentence}")
