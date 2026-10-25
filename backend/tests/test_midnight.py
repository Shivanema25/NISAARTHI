"""Automated tests for deterministic midnight rollover and time arithmetic."""

import pytest
from app.engine.time_utils import (
    calculate_arrival,
    calculate_available_time,
    is_time_within_window,
    parse_time_to_minutes,
    minutes_to_time_str,
)


def test_case_a_same_day():
    """Case A: Departure 02:15, Deadline 03:00 -> 45 minutes on the same calendar day."""
    available_mins, day_offset = calculate_available_time("02:15", "03:00")
    assert available_mins == 45
    assert day_offset == 0


def test_case_b_overnight_rollover():
    """Case B: Departure 23:40, Deadline 00:30 -> 50 minutes, deadline on the following calendar day."""
    available_mins, day_offset = calculate_available_time("23:40", "00:30")
    assert available_mins == 50
    assert day_offset == 1


def test_equal_clock_times_rule():
    """Equal departure and deadline (02:15 -> 02:15) represents next calendar day occurrence (1440 mins)."""
    available_mins, day_offset = calculate_available_time("02:15", "02:15")
    assert available_mins == 1440
    assert day_offset == 1


def test_arrival_calculation_overnight():
    """A journey starting at 23:40 with duration 35 minutes arrives at 00:15 (+1 day offset)."""
    arrival_time, day_offset = calculate_arrival("23:40", 35)
    assert arrival_time == "00:15"
    assert day_offset == 1


def test_arrival_calculation_same_day():
    """A journey starting at 02:15 with duration 30 minutes arrives at 02:45 (0 day offset)."""
    arrival_time, day_offset = calculate_arrival("02:15", 30)
    assert arrival_time == "02:45"
    assert day_offset == 0


def test_journey_misses_cross_midnight_deadline():
    """A departure at 23:40 with deadline 00:00 provides 20 minutes; a 30m journey misses deadline."""
    available_mins, day_offset = calculate_available_time("23:40", "00:00")
    assert available_mins == 20
    assert day_offset == 1

    arrival_time, arr_day_offset = calculate_arrival("23:40", 30)
    assert arrival_time == "00:10"
    assert arr_day_offset == 1
    assert 30 > available_mins  # Overdue by 10 minutes


def test_is_time_within_window_overnight():
    """Test operational windows crossing midnight (e.g. 23:00-05:00)."""
    # 02:15 is inside 23:00-05:00
    assert is_time_within_window("02:15", "23:00-05:00") is True
    # 23:30 is inside 23:00-05:00
    assert is_time_within_window("23:30", "23:00-05:00") is True
    # 05:00 is inside 23:00-05:00
    assert is_time_within_window("05:00", "23:00-05:00") is True
    # 05:01 is outside 23:00-05:00
    assert is_time_within_window("05:01", "23:00-05:00") is False
    # 22:59 is outside 23:00-05:00
    assert is_time_within_window("22:59", "23:00-05:00") is False


def test_is_time_within_window_daytime():
    """Test daytime operational window (e.g. 06:00-22:30)."""
    assert is_time_within_window("12:00", "06:00-22:30") is True
    assert is_time_within_window("02:15", "06:00-22:30") is False
    assert is_time_within_window("23:40", "06:00-22:30") is False


def test_invalid_time_strings_raise_value_error():
    """Malformed time strings must raise ValueError."""
    with pytest.raises(ValueError):
        parse_time_to_minutes("25:00")
    with pytest.raises(ValueError):
        parse_time_to_minutes("02:60")
    with pytest.raises(ValueError):
        parse_time_to_minutes("2:15")
    with pytest.raises(ValueError):
        parse_time_to_minutes("invalid")
