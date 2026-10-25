"""Deterministic midnight and clock arithmetic utilities for Nisaarthi.

Follows Asia/Kolkata timezone conventions. Calculates elapsed durations
using unambiguous minute arithmetic rather than string comparisons.
"""

import re
from typing import Tuple

TIME_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
MINUTES_PER_DAY = 1440  # 24 * 60


def parse_time_to_minutes(time_str: str) -> int:
    """Parse 'HH:MM' string into minutes since 00:00.

    Raises:
        ValueError if the format is not valid 24-hour HH:MM.
    """
    clean_str = time_str.strip()
    match = TIME_REGEX.match(clean_str)
    if not match:
        raise ValueError(f"Invalid time format '{time_str}'. Expected HH:MM in 24-hour format.")
    hours = int(match.group(1))
    minutes = int(match.group(2))
    return hours * 60 + minutes


def minutes_to_time_str(total_minutes: int) -> str:
    """Convert minutes since 00:00 into 'HH:MM' formatted string."""
    norm_mins = total_minutes % MINUTES_PER_DAY
    hours = norm_mins // 60
    minutes = norm_mins % 60
    return f"{hours:02d}:{minutes:02d}"


def calculate_available_time(departure_time: str, deadline: str) -> Tuple[int, int]:
    """Calculate available minutes between departure and required arrival deadline.

    Rules:
    - If deadline > departure: Available on same calendar day (day offset = 0).
    - If deadline == departure: Documented rule — deadline is interpreted as the
      next occurrence 24 hours (1440 minutes) later (day offset = 1).
    - If deadline < departure: Journey crosses midnight into following calendar day
      (day offset = 1).

    Returns:
        (available_minutes, deadline_day_offset)
    """
    dep_mins = parse_time_to_minutes(departure_time)
    dead_mins = parse_time_to_minutes(deadline)

    if dead_mins > dep_mins:
        available = dead_mins - dep_mins
        day_offset = 0
    elif dead_mins == dep_mins:
        # Equal clock times rule: next calendar day (+24 hours)
        available = MINUTES_PER_DAY
        day_offset = 1
    else:
        # Crosses midnight
        available = (dead_mins + MINUTES_PER_DAY) - dep_mins
        day_offset = 1

    return available, day_offset


def calculate_arrival(departure_time: str, duration_minutes: int) -> Tuple[str, int]:
    """Calculate estimated arrival clock time and arrival day offset relative to departure.

    Args:
        departure_time: Clock time 'HH:MM'.
        duration_minutes: Total elapsed journey duration in minutes.

    Returns:
        (arrival_time_str, arrival_day_offset)
    """
    if duration_minutes < 0:
        raise ValueError(f"Duration cannot be negative, got {duration_minutes}.")

    dep_mins = parse_time_to_minutes(departure_time)
    total_arr_mins = dep_mins + duration_minutes

    day_offset = total_arr_mins // MINUTES_PER_DAY
    arrival_str = minutes_to_time_str(total_arr_mins)
    return arrival_str, day_offset


def is_time_within_window(time_str: str, window_str: str) -> bool:
    """Check if time_str ('HH:MM') falls within operating window ('HH:MM-HH:MM').

    Correctly handles overnight windows such as '23:00-05:00'.
    """
    if not window_str or "-" not in window_str:
        return True  # If no window defined, assumed unrestricted

    start_str, end_str = window_str.split("-", 1)
    t = parse_time_to_minutes(time_str)
    start = parse_time_to_minutes(start_str)
    end = parse_time_to_minutes(end_str)

    if start <= end:
        # Same-day operational window (e.g., 06:00 to 22:30)
        return start <= t <= end
    else:
        # Overnight operational window (e.g., 23:00 to 05:00)
        return t >= start or t <= end
