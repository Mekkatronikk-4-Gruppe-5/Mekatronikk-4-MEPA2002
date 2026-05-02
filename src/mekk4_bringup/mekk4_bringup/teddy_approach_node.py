#!/usr/bin/env python3
from __future__ import annotations

import math
import re
import time

import rclpy
from geometry_msgs.msg import PoseStamped, Quaternion, Twist
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String


STATUS_RE = re.compile(r"(?P<key>[A-Za-z_]+)=(?P<value>[^ ]+)")


def yaw_to_quaternion(yaw: float) -> Quaternion:
    half = yaw * 0.5
    q = Quaternion()
    q.z = math.sin(half)
    q.w = math.cos(half)
    return q


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def parse_status(text: str) -> dict[str, str]:
    return {match.group("key"): match.group("value") for match in STATUS_RE.finditer(text)}


class TeddyApproachNode(Node):
    def __init__(self) -> None:
        super().__init__("teddy_approach")

        self.declare_parameter("enabled", False)
        self.declare_parameter("status_topic", "/teddy_detector/status")
        self.declare_parameter("cmd_vel_topic", "/cmd_vel_manual")
        self.declare_parameter("publish_period_s", 0.05)
        self.declare_parameter("lost_timeout_s", 0.5)
        self.declare_parameter("linear_speed", 0.08)
        self.declare_parameter("angular_kp", 1.2)
        self.declare_parameter("min_angular_speed", 0.0)
        self.declare_parameter("max_angular_speed", 0.8)
        self.declare_parameter("center_tolerance", 0.10)
        self.declare_parameter("scan_topic", "/lidar")
        self.declare_parameter("stop_lidar_distance_m", 0.0)
        self.declare_parameter("stop_lidar_front_angle_rad", 0.20)
        self.declare_parameter("stop_lidar_min_points", 3)
        self.declare_parameter("stop_lidar_timeout_s", 0.5)
        self.declare_parameter("drive_when_not_centered", False)
        self.declare_parameter("use_nav_goal", False)
        self.declare_parameter("send_goal_on_start", False)
        self.declare_parameter("goal_frame", "odom")
        self.declare_parameter("goal_x", 0.0)
        self.declare_parameter("goal_y", 0.0)
        self.declare_parameter("goal_yaw", 0.0)

        self._enabled = self.get_parameter("enabled").get_parameter_value().bool_value
        status_topic = self.get_parameter("status_topic").get_parameter_value().string_value
        cmd_vel_topic = self.get_parameter("cmd_vel_topic").get_parameter_value().string_value
        publish_period_s = self.get_parameter("publish_period_s").get_parameter_value().double_value
        self._lost_timeout_s = self.get_parameter("lost_timeout_s").get_parameter_value().double_value
        self._linear_speed = self.get_parameter("linear_speed").get_parameter_value().double_value
        self._angular_kp = self.get_parameter("angular_kp").get_parameter_value().double_value
        self._min_angular_speed = (
            self.get_parameter("min_angular_speed").get_parameter_value().double_value
        )
        self._max_angular_speed = (
            self.get_parameter("max_angular_speed").get_parameter_value().double_value
        )
        self._center_tolerance = self.get_parameter("center_tolerance").get_parameter_value().double_value
        scan_topic = self.get_parameter("scan_topic").get_parameter_value().string_value
        self._stop_lidar_distance_m = (
            self.get_parameter("stop_lidar_distance_m").get_parameter_value().double_value
        )
        self._stop_lidar_front_angle_rad = (
            self.get_parameter("stop_lidar_front_angle_rad").get_parameter_value().double_value
        )
        self._stop_lidar_min_points = (
            self.get_parameter("stop_lidar_min_points").get_parameter_value().integer_value
        )
        self._stop_lidar_timeout_s = (
            self.get_parameter("stop_lidar_timeout_s").get_parameter_value().double_value
        )
        self._drive_when_not_centered = (
            self.get_parameter("drive_when_not_centered").get_parameter_value().bool_value
        )
        self._use_nav_goal = self.get_parameter("use_nav_goal").get_parameter_value().bool_value
        self._send_goal_on_start = (
            self.get_parameter("send_goal_on_start").get_parameter_value().bool_value
        )

        if self._min_angular_speed < 0.0:
            raise ValueError("min_angular_speed must be zero or greater")
        if self._max_angular_speed < self._min_angular_speed:
            raise ValueError("max_angular_speed must be greater than or equal to min_angular_speed")
        if self._stop_lidar_distance_m < 0.0:
            raise ValueError("stop_lidar_distance_m must be zero or greater")
        if self._stop_lidar_front_angle_rad < 0.0:
            raise ValueError("stop_lidar_front_angle_rad must be zero or greater")
        if self._stop_lidar_min_points < 1:
            raise ValueError("stop_lidar_min_points must be at least 1")
        if self._stop_lidar_timeout_s < 0.0:
            raise ValueError("stop_lidar_timeout_s must be zero or greater")

        self._cmd_pub = self.create_publisher(Twist, cmd_vel_topic, 10)
        self._status_sub = self.create_subscription(String, status_topic, self._on_status, 10)
        self._scan_sub = self.create_subscription(LaserScan, scan_topic, self._on_scan, 10)
        self._timer = self.create_timer(publish_period_s, self._on_timer)
        self._nav_client = ActionClient(self, NavigateToPose, "navigate_to_pose")

        self._last_seen_at = -1.0
        self._last_dx = 0.0
        self._last_front_distance = math.inf
        self._last_front_points = 0
        self._last_scan_at = -1.0
        self._last_count = 0
        self._nav_goal_sent = False
        self._last_mode = ""

        if self._enabled and self._use_nav_goal and self._send_goal_on_start:
            self._send_nav_goal()

        self.get_logger().info(
            "teddy approach enabled=%s status=%s cmd=%s scan=%s nav_goal=%s"
            % (self._enabled, status_topic, cmd_vel_topic, scan_topic, self._use_nav_goal)
        )

    def _on_status(self, msg: String) -> None:
        fields = parse_status(msg.data)
        count_text = fields.get("teddy_count")
        if count_text is None:
            return

        self._last_count = int(count_text)
        dx_text = fields.get("dx")
        if self._last_count > 0 and dx_text is not None:
            self._last_dx = float(dx_text)
            self._last_seen_at = time.monotonic()

    def _on_scan(self, msg: LaserScan) -> None:
        front_ranges = []
        angle = msg.angle_min
        for distance in msg.ranges:
            if (
                abs(angle) <= self._stop_lidar_front_angle_rad
                and math.isfinite(distance)
                and msg.range_min <= distance <= msg.range_max
            ):
                front_ranges.append(float(distance))
            angle += msg.angle_increment

        self._last_front_points = len(front_ranges)
        self._last_front_distance = min(front_ranges) if front_ranges else math.inf
        self._last_scan_at = time.monotonic()

    def _send_nav_goal(self) -> None:
        if self._nav_goal_sent:
            return
        if not self._nav_client.wait_for_server(timeout_sec=0.1):
            self.get_logger().warning("navigate_to_pose action server not available yet")
            return

        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = self.get_parameter("goal_frame").get_parameter_value().string_value
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = self.get_parameter("goal_x").get_parameter_value().double_value
        goal.pose.pose.position.y = self.get_parameter("goal_y").get_parameter_value().double_value
        yaw = self.get_parameter("goal_yaw").get_parameter_value().double_value
        goal.pose.pose.orientation = yaw_to_quaternion(yaw)

        self._nav_client.send_goal_async(goal)
        self._nav_goal_sent = True
        self.get_logger().info(
            "sent teddy search goal x=%.2f y=%.2f yaw=%.2f"
            % (goal.pose.pose.position.x, goal.pose.pose.position.y, yaw)
        )

    def _on_timer(self) -> None:
        if not self._enabled:
            return

        if self._use_nav_goal and self._send_goal_on_start and not self._nav_goal_sent:
            self._send_nav_goal()

        now = time.monotonic()
        seen = self._last_seen_at >= 0.0 and (now - self._last_seen_at) <= self._lost_timeout_s
        if not seen:
            self._log_mode("waiting_for_teddy")
            return

        cmd = Twist()
        centered = abs(self._last_dx) <= self._center_tolerance
        lidar_fresh = (
            self._last_scan_at >= 0.0 and (now - self._last_scan_at) <= self._stop_lidar_timeout_s
        )
        lidar_close = (
            centered
            and self._stop_lidar_distance_m > 0.0
            and lidar_fresh
            and self._last_front_points >= self._stop_lidar_min_points
            and self._last_front_distance <= self._stop_lidar_distance_m
        )
        if lidar_close:
            self._cmd_pub.publish(cmd)
            self._log_mode("close_enough_lidar")
            return

        if not centered:
            raw_angular = -self._angular_kp * self._last_dx
            angular = math.copysign(
                max(abs(raw_angular), self._min_angular_speed),
                raw_angular,
            )
            cmd.angular.z = clamp(angular, -self._max_angular_speed, self._max_angular_speed)
        if centered or self._drive_when_not_centered:
            cmd.linear.x = self._linear_speed
        self._cmd_pub.publish(cmd)
        self._log_mode("centering" if not centered else "approaching")

    def _log_mode(self, mode: str) -> None:
        if mode == self._last_mode:
            return
        self.get_logger().info(f"mode={mode}")
        self._last_mode = mode


def main(args=None) -> None:
    rclpy.init(args=args)
    node = TeddyApproachNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
