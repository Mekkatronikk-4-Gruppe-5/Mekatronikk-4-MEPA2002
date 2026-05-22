import math

from mekk4_bringup.scan_utils import front_window_indices, nearest_valid_range_in_window


def test_front_window_indices_limits_to_center_sector():
    start, stop = front_window_indices(
        range_count=9,
        angle_min=-0.4,
        angle_increment=0.1,
        half_angle=0.15,
    )

    assert (start, stop) == (3, 6)


def test_nearest_valid_range_ignores_invalid_values():
    ranges = [2.0, math.inf, 0.04, 0.30, math.nan, 0.20, 4.0]

    distance, count, angle = nearest_valid_range_in_window(
        ranges,
        start=1,
        stop=6,
        range_min=0.05,
        range_max=3.5,
        angle_min=-0.3,
        angle_increment=0.1,
    )

    assert distance == 0.20
    assert count == 2
    assert angle == 0.2
