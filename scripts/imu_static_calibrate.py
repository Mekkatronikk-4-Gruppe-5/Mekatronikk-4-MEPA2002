#!/usr/bin/env python3
"""Compatibility wrapper for the packaged IMU calibrator."""

from __future__ import annotations

import os
import sys

try:
    from mekk4_bringup.imu_static_calibrate import main
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'mekk4_bringup')))
    from mekk4_bringup.imu_static_calibrate import main


if __name__ == '__main__':
    main()
