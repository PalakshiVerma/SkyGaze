"""
tests/test_spatial.py
─────────────────────
Unit tests for spatial.py.

Covers:
  - All 16 compass points (centre values + boundary edges)
  - All altitude buckets (midpoints + boundary edges)
  - describe_position sentence format
  - full_description with both normal and error dicts
  - Edge cases: azimuth 0.0 / 360.0 / negative, altitude 0.0 / 90.0

Run with:
    .venv\\Scripts\\python.exe -m pytest tests/test_spatial.py -v
"""

import pytest
from spatial import compass_direction, altitude_phrase, describe_position, full_description


# ── compass_direction ─────────────────────────────────────────────────────────

class TestCompassDirection:

    # --- Cardinal points (centre values) ------------------------------------

    def test_north_centre(self):
        assert compass_direction(0.0) == "north"

    def test_east_centre(self):
        assert compass_direction(90.0) == "east"

    def test_south_centre(self):
        assert compass_direction(180.0) == "south"

    def test_west_centre(self):
        assert compass_direction(270.0) == "west"

    # --- Intercardinal points (centre values) --------------------------------

    def test_northeast_centre(self):
        assert compass_direction(45.0) == "northeast"

    def test_southeast_centre(self):
        assert compass_direction(135.0) == "southeast"

    def test_southwest_centre(self):
        assert compass_direction(225.0) == "southwest"

    def test_northwest_centre(self):
        assert compass_direction(315.0) == "northwest"

    # --- Secondary intercardinal points (centre values) ----------------------

    def test_north_northeast_centre(self):
        assert compass_direction(22.5) == "north-northeast"

    def test_east_northeast_centre(self):
        assert compass_direction(67.5) == "east-northeast"

    def test_east_southeast_centre(self):
        assert compass_direction(112.5) == "east-southeast"

    def test_south_southeast_centre(self):
        assert compass_direction(157.5) == "south-southeast"

    def test_south_southwest_centre(self):
        assert compass_direction(202.5) == "south-southwest"

    def test_west_southwest_centre(self):
        assert compass_direction(247.5) == "west-southwest"

    def test_west_northwest_centre(self):
        assert compass_direction(292.5) == "west-northwest"

    def test_north_northwest_centre(self):
        assert compass_direction(337.5) == "north-northwest"

    # --- Boundary values -----------------------------------------------------

    def test_exact_0_is_north(self):
        assert compass_direction(0.0) == "north"

    def test_exact_360_wraps_to_north(self):
        assert compass_direction(360.0) == "north"

    def test_just_before_north_northeast_boundary(self):
        # 11.24 should still be north
        assert compass_direction(11.24) == "north"

    def test_at_north_northeast_boundary(self):
        # 11.25 is the start of north-northeast
        assert compass_direction(11.25) == "north-northeast"

    def test_just_before_northeast_boundary(self):
        # 33.74 should still be north-northeast
        assert compass_direction(33.74) == "north-northeast"

    def test_at_northeast_boundary(self):
        assert compass_direction(33.75) == "northeast"

    def test_just_before_east_northeast_boundary(self):
        assert compass_direction(56.24) == "northeast"

    def test_at_east_northeast_boundary(self):
        assert compass_direction(56.25) == "east-northeast"

    def test_at_east_boundary(self):
        assert compass_direction(78.75) == "east"

    def test_at_north_northwest_upper_boundary(self):
        # 348.75 is the lower bound of North per standard 16-point compass.
        # NNW spans 326.25 (inclusive) to 348.75 (exclusive).
        assert compass_direction(348.75) == "north"

    def test_just_under_360_is_north(self):
        # 359.9° is firmly in the North sector (348.75–360)
        assert compass_direction(359.9) == "north"

    # --- Normalisation -------------------------------------------------------

    def test_negative_azimuth_normalised(self):
        # -10° normalises to 350°, which is in the North sector (348.75–360)
        assert compass_direction(-10.0) == "north"

    def test_azimuth_over_360_normalised(self):
        # 450° == 90° == east
        assert compass_direction(450.0) == "east"

    def test_large_negative_azimuth(self):
        # -90° == 270° == west
        assert compass_direction(-90.0) == "west"


# ── altitude_phrase ───────────────────────────────────────────────────────────

class TestAltitudePhrase:

    # --- Below horizon -------------------------------------------------------

    def test_far_below_horizon(self):
        assert altitude_phrase(-45.0) == "below the horizon"

    def test_just_below_horizon(self):
        assert altitude_phrase(-0.1) == "below the horizon"

    def test_exactly_zero(self):
        # 0.0 is the start of "very low on the horizon"
        assert altitude_phrase(0.0) == "very low on the horizon"

    # --- Very low ------------------------------------------------------------

    def test_very_low_midpoint(self):
        assert altitude_phrase(2.5) == "very low on the horizon"

    def test_just_before_low_boundary(self):
        assert altitude_phrase(4.9) == "very low on the horizon"

    def test_at_low_boundary(self):
        assert altitude_phrase(5.0) == "low in the sky"

    # --- Low -----------------------------------------------------------------

    def test_low_midpoint(self):
        assert altitude_phrase(10.0) == "low in the sky"

    def test_just_before_fairly_low_boundary(self):
        assert altitude_phrase(14.9) == "low in the sky"

    def test_at_fairly_low_boundary(self):
        assert altitude_phrase(15.0) == "fairly low in the sky"

    # --- Fairly low ----------------------------------------------------------

    def test_fairly_low_midpoint(self):
        assert altitude_phrase(22.0) == "fairly low in the sky"

    def test_just_before_third_up_boundary(self):
        assert altitude_phrase(29.9) == "fairly low in the sky"

    def test_at_third_up_boundary(self):
        assert altitude_phrase(30.0) == "about a third of the way up the sky"

    # --- Third of the way up -------------------------------------------------

    def test_third_up_midpoint(self):
        assert altitude_phrase(40.0) == "about a third of the way up the sky"

    def test_just_before_halfway_boundary(self):
        assert altitude_phrase(49.9) == "about a third of the way up the sky"

    def test_at_halfway_boundary(self):
        assert altitude_phrase(50.0) == "about halfway up the sky"

    # --- Halfway up ----------------------------------------------------------

    def test_halfway_midpoint(self):
        assert altitude_phrase(60.0) == "about halfway up the sky"

    def test_just_before_high_boundary(self):
        assert altitude_phrase(69.9) == "about halfway up the sky"

    def test_at_high_boundary(self):
        assert altitude_phrase(70.0) == "high in the sky"

    # --- High ----------------------------------------------------------------

    def test_high_midpoint(self):
        assert altitude_phrase(77.0) == "high in the sky"

    def test_just_before_overhead_boundary(self):
        assert altitude_phrase(84.9) == "high in the sky"

    def test_at_overhead_boundary(self):
        assert altitude_phrase(85.0) == "nearly overhead"

    # --- Nearly overhead -----------------------------------------------------

    def test_nearly_overhead_midpoint(self):
        assert altitude_phrase(87.5) == "nearly overhead"

    def test_exactly_90(self):
        assert altitude_phrase(90.0) == "nearly overhead"

    # --- Out-of-range clamp --------------------------------------------------

    def test_extreme_below(self):
        assert altitude_phrase(-91.0) == "below the horizon"

    def test_extreme_above(self):
        assert altitude_phrase(91.0) == "nearly overhead"


# ── describe_position ────────────────────────────────────────────────────────

class TestDescribePosition:

    def test_visible_object_sentence_format(self):
        result = describe_position("Jupiter", 82.3, 37.1)
        assert result.startswith("Jupiter is to the")
        assert result.endswith(".")
        assert "east" in result
        assert "third of the way up" in result

    def test_below_horizon_sentence(self):
        result = describe_position("Saturn", 150.0, -10.0)
        assert result == "Saturn is below the horizon right now."

    def test_exactly_zero_altitude_is_below(self):
        # altitude = 0 is the boundary — treated as not visible
        result = describe_position("Mercury", 180.0, 0.0)
        assert result == "Mercury is below the horizon right now."

    def test_capitalises_display_name(self):
        # display_name starting with lowercase should still be capitalised
        result = describe_position("the Moon", 90.0, 45.0)
        assert result.startswith("The Moon")

    def test_nearly_overhead(self):
        result = describe_position("Venus", 0.0, 88.0)
        assert "nearly overhead" in result

    def test_low_on_horizon(self):
        result = describe_position("Mars", 270.0, 3.0)
        assert "very low on the horizon" in result

    def test_sentence_ends_with_period(self):
        result = describe_position("Uranus", 315.0, 72.0)
        assert result.endswith(".")

    def test_correct_compass_in_sentence(self):
        result = describe_position("Neptune", 337.5, 50.0)
        assert "north-northwest" in result


# ── full_description ─────────────────────────────────────────────────────────

class TestFullDescription:

    def test_normal_position_dict(self):
        pos = {
            "display_name": "Jupiter",
            "azimuth_deg":  82.3,
            "altitude_deg": 37.1,
            "is_visible":   True,
        }
        result = full_description(pos)
        assert "Jupiter" in result
        assert result.endswith(".")

    def test_error_dict_returns_error_message(self):
        error_pos = {"error": "Unknown object 'foo'."}
        result = full_description(error_pos)
        assert "Sorry" in result
        assert "foo" in result

    def test_below_horizon_dict(self):
        pos = {
            "display_name": "Saturn",
            "azimuth_deg":  326.0,
            "altitude_deg": -54.0,
            "is_visible":   False,
        }
        result = full_description(pos)
        assert "below the horizon" in result
