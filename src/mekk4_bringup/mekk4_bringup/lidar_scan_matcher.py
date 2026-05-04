#!/usr/bin/env python3
"""
Lightweight LiDAR scan matcher for odometry estimation.
Performs simple scan-to-scan matching using correlation-based alignment.
Publishes odometry and transforms based on relative scan displacement.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Optional

import numpy as np
import rclpy
from geometry_msgs.msg import Pose, Quaternion, TransformStamped, Twist, Vector3
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Header
from tf2_ros import TransformBroadcaster
import tf_transformations


class LidarScanMatcher(Node):
    """Match consecutive LiDAR scans to estimate local odometry."""

    def __init__(self) -> None:
        super().__init__("lidar_scan_matcher")

        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("odom_frame", "odom")
        self.declare_parameter("lidar_frame", "base_laser")
        self.declare_parameter("max_range", 10.0)
        self.declare_parameter("min_range", 0.15)
        self.declare_parameter("angular_resolution_deg", 1.0)
        self.declare_parameter("correlation_threshold", 0.5)
        self.declare_parameter("publish_tf", True)

        self._base_frame = self.get_parameter("base_frame").get_parameter_value().string_value
        self._odom_frame = self.get_parameter("odom_frame").get_parameter_value().string_value
        self._lidar_frame = self.get_parameter("lidar_frame").get_parameter_value().string_value
        self._max_range = self.get_parameter("max_range").get_parameter_value().double_value
        self._min_range = self.get_parameter("min_range").get_parameter_value().double_value
        self._angular_res = self.get_parameter("angular_resolution_deg").get_parameter_value().double_value
        self._corr_threshold = self.get_parameter("correlation_threshold").get_parameter_value().double_value
        self._publish_tf = self.get_parameter("publish_tf").get_parameter_value().bool_value

        self._tf_broadcaster = TransformBroadcaster(self)

        # Odometry state: cumulative position and orientation in odom frame
        self._odom_x = 0.0
        self._odom_y = 0.0
        self._odom_theta = 0.0
        self._odom_stamp = self.get_clock().now()

        # Scan history for matching
        self._prev_scan_cart: Optional[np.ndarray] = None
        self._prev_scan_stamp = None

        self._sub = self.create_subscription(LaserScan, "/lidar", self._on_scan, 10)
        self._pub_odom = self.create_publisher(Odometry, "/lidar_odom", 10)

        self.get_logger().info(
            f"LidarScanMatcher initialized: frame={self._lidar_frame}, "
            f"range=[{self._min_range}, {self._max_range}], "
            f"correlation_threshold={self._corr_threshold}"
        )

    def _scan_to_cartesian(self, scan: LaserScan) -> np.ndarray:
        """Convert LaserScan to Cartesian points [N, 2]."""
        points = []
        for i, range_val in enumerate(scan.ranges):
            if not (self._min_range <= range_val <= self._max_range):
                continue
            angle = scan.angle_min + i * scan.angle_increment
            x = range_val * math.cos(angle)
            y = range_val * math.sin(angle)
            points.append([x, y])
        return np.array(points, dtype=np.float32)

    def _estimate_transform(
        self, current: np.ndarray, previous: np.ndarray
    ) -> tuple[float, float, float, float]:
        """
        Estimate 2D transform (dx, dy, dtheta, confidence) from previous to current scan.
        Uses simple correlation-based matching.
        Returns: (dx, dy, dtheta, confidence)
        """
        if len(current) < 10 or len(previous) < 10:
            return 0.0, 0.0, 0.0, 0.0

        # Try multiple rotation hypotheses
        best_score = -1.0
        best_theta = 0.0
        best_tx = 0.0
        best_ty = 0.0

        # Grid search over rotation and translation
        for theta_deg in np.arange(-5, 6, 1.0):
            theta = math.radians(theta_deg)
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)

            # Rotate current scan
            rotated = current.copy()
            rotated[:, 0] = current[:, 0] * cos_t - current[:, 1] * sin_t
            rotated[:, 1] = current[:, 0] * sin_t + current[:, 1] * cos_t

            # Estimate translation by point cloud centroid
            prev_center = previous.mean(axis=0)
            curr_center = rotated.mean(axis=0)
            tx = prev_center[0] - curr_center[0]
            ty = prev_center[1] - curr_center[1]

            # Translate
            translated = rotated.copy()
            translated[:, 0] += tx
            translated[:, 1] += ty

            # Compute correlation: fraction of current points near previous points
            score = self._compute_correlation(translated, previous)

            if score > best_score:
                best_score = score
                best_theta = theta
                best_tx = tx
                best_ty = ty

        confidence = max(0.0, best_score)
        return best_tx, best_ty, best_theta, confidence

    def _compute_correlation(self, current: np.ndarray, previous: np.ndarray, match_dist=0.3) -> float:
        """
        Simple correlation: fraction of current points within match_dist of previous points.
        """
        if len(previous) == 0 or len(current) == 0:
            return 0.0

        from scipy.spatial.distance import cdist

        distances = cdist(current, previous, metric="euclidean")
        min_distances = distances.min(axis=1)
        matched = np.sum(min_distances < match_dist)
        return float(matched) / len(current)

    def _on_scan(self, msg: LaserScan) -> None:
        """Process incoming LiDAR scan."""
        current_cart = self._scan_to_cartesian(msg)

        if self._prev_scan_cart is None:
            self._prev_scan_cart = current_cart
            self._prev_scan_stamp = msg.header.stamp
            return

        # Estimate transform
        dx, dy, dtheta, confidence = self._estimate_transform(current_cart, self._prev_scan_cart)

        if confidence < self._corr_threshold:
            self.get_logger().debug(f"Low correlation: {confidence:.2f}, skipping update")
            self._prev_scan_cart = current_cart
            self._prev_scan_stamp = msg.header.stamp
            return

        # Update odometry state
        cos_theta = math.cos(self._odom_theta)
        sin_theta = math.sin(self._odom_theta)
        self._odom_x += dx * cos_theta - dy * sin_theta
        self._odom_y += dx * sin_theta + dy * cos_theta
        self._odom_theta += dtheta

        # Normalize theta to [-pi, pi]
        self._odom_theta = math.atan2(math.sin(self._odom_theta), math.cos(self._odom_theta))

        # Publish odometry
        self._publish_odometry(msg.header.stamp)

        # Update history
        self._prev_scan_cart = current_cart
        self._prev_scan_stamp = msg.header.stamp
        self._odom_stamp = msg.header.stamp

    def _publish_odometry(self, stamp) -> None:
        """Publish Odometry message."""
        odom_msg = Odometry()
        odom_msg.header.stamp = stamp
        odom_msg.header.frame_id = self._odom_frame
        odom_msg.child_frame_id = self._base_frame

        # Position
        odom_msg.pose.pose.position.x = self._odom_x
        odom_msg.pose.pose.position.y = self._odom_y
        odom_msg.pose.pose.position.z = 0.0

        # Orientation (2D -> quaternion)
        quat = tf_transformations.quaternion_from_euler(0, 0, self._odom_theta)
        odom_msg.pose.pose.orientation.x = quat[0]
        odom_msg.pose.pose.orientation.y = quat[1]
        odom_msg.pose.pose.orientation.z = quat[2]
        odom_msg.pose.pose.orientation.w = quat[3]

        # Covariance (rough estimates)
        odom_msg.pose.covariance[0] = 0.1   # x
        odom_msg.pose.covariance[7] = 0.1   # y
        odom_msg.pose.covariance[35] = 0.2  # theta

        # Velocity (not estimated from scan matcher)
        odom_msg.twist.twist.linear.x = 0.0
        odom_msg.twist.twist.linear.y = 0.0
        odom_msg.twist.twist.angular.z = 0.0

        self._pub_odom.publish(odom_msg)

        # Publish TF
        if self._publish_tf:
            transform = TransformStamped()
            transform.header.stamp = stamp
            transform.header.frame_id = self._odom_frame
            transform.child_frame_id = self._base_frame
            transform.transform.translation.x = self._odom_x
            transform.transform.translation.y = self._odom_y
            transform.transform.translation.z = 0.0

            quat = tf_transformations.quaternion_from_euler(0, 0, self._odom_theta)
            transform.transform.rotation.x = quat[0]
            transform.transform.rotation.y = quat[1]
            transform.transform.rotation.z = quat[2]
            transform.transform.rotation.w = quat[3]

            self._tf_broadcaster.sendTransform(transform)


def main() -> None:
    rclpy.init()
    node = LidarScanMatcher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
