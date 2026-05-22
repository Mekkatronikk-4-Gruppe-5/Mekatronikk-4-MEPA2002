#!/usr/bin/env python3
from __future__ import annotations

import math
from collections.abc import Sequence


def front_window_indices(
    range_count: int,
    angle_min: float,
    angle_increment: float,
    half_angle: float,
) -> tuple[int, int]:
    """Return the half-open range index window inside +/- half_angle."""
    if range_count <= 0 or angle_increment <= 0.0 or half_angle < 0.0:
        return 0, 0

    first = math.ceil((-half_angle - angle_min) / angle_increment)
    last = math.floor((half_angle - angle_min) / angle_increment)
    start = max(0, first)
    stop = min(range_count, last + 1)
    if stop <= start:
        return 0, 0
    return start, stop


def nearest_valid_range_in_window(
    ranges: Sequence[float],
    start: int,
    stop: int,
    range_min: float,
    range_max: float,
    angle_min: float,
    angle_increment: float,
) -> tuple[float, int, float]:
    """Find nearest finite range in [start, stop) without copying or sorting."""
    nearest = math.inf
    nearest_angle = 0.0
    valid_count = 0

    for index in range(start, stop):
        distance = ranges[index]
        if not math.isfinite(distance) or distance < range_min or distance > range_max:
            continue
        valid_count += 1
        if distance < nearest:
            nearest = float(distance)
            nearest_angle = angle_min + (index * angle_increment)

    return nearest, valid_count, nearest_angle
