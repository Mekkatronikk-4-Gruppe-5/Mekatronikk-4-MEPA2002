#!/usr/bin/env python3
"""Record a stationary IMU sample window and write a bias YAML file."""

from __future__ import annotations

import argparse
import statistics
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
import yaml


class ImuStaticCalibrator(Node):
    def __init__(self, topic: str, duration_s: float, out_path: str) -> None:
        super().__init__("imu_static_calibrator")
        self.topic = topic
        self.duration_s = duration_s
        self.out_path = out_path
        self._samples: list[tuple[float, float, float, float, float, float]] = []
        self._start: float | None = None
        self.create_subscription(Imu, topic, self._cb, 10)
        self.get_logger().info(f"Listening to {topic} for {duration_s:.1f}s")

    def _cb(self, msg: Imu) -> None:
        now = time.time()
        if self._start is None:
            self._start = now
        if now - self._start <= self.duration_s:
            la = msg.linear_acceleration
            av = msg.angular_velocity
            self._samples.append((la.x, la.y, la.z, av.x, av.y, av.z))

    def summarize_and_write(self) -> None:
        sample_count = len(self._samples)
        if sample_count == 0:
            self.get_logger().error("No IMU samples collected")
            return

        columns = list(zip(*self._samples))
        means = [statistics.mean(column) for column in columns]
        stds = [statistics.pstdev(column) for column in columns]

        self.get_logger().info(f"Samples: {sample_count}")
        self.get_logger().info(
            "Linear accel mean (m/s^2): x=%0.4f y=%0.4f z=%0.4f" % tuple(means[0:3])
        )
        self.get_logger().info(
            "Linear accel std  (m/s^2): x=%0.4f y=%0.4f z=%0.4f" % tuple(stds[0:3])
        )
        self.get_logger().info(
            "Angular vel mean (rad/s): x=%0.6f y=%0.6f z=%0.6f" % tuple(means[3:6])
        )
        self.get_logger().info(
            "Angular vel std  (rad/s): x=%0.6f y=%0.6f z=%0.6f" % tuple(stds[3:6])
        )

        bias = {
            "linear_acceleration_bias": {
                "x": float(means[0]),
                "y": float(means[1]),
                "z": float(means[2]),
            },
            "angular_velocity_bias": {
                "x": float(means[3]),
                "y": float(means[4]),
                "z": float(means[5]),
            },
            "linear_acceleration_std": {
                "x": float(stds[0]),
                "y": float(stds[1]),
                "z": float(stds[2]),
            },
            "angular_velocity_std": {
                "x": float(stds[3]),
                "y": float(stds[4]),
                "z": float(stds[5]),
            },
            "samples": sample_count,
            "duration_s": self.duration_s,
            "topic": self.topic,
        }

        output_path = Path(self.out_path).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(bias, handle, sort_keys=True)
        self.get_logger().info(f"Wrote bias file: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="/imu/data")
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--out", default="config/imu_static_bias.yaml")
    args = parser.parse_args()

    rclpy.init()
    node = ImuStaticCalibrator(args.topic, args.duration, args.out)
    try:
        start_time = time.time()
        while rclpy.ok() and time.time() - start_time < args.duration + 0.5:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass

    node.summarize_and_write()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()