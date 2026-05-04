#!/usr/bin/env python3
from __future__ import annotations

import math

import rclpy
from geometry_msgs.msg import PoseStamped, Quaternion
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.node import Node


PARAM_DEFAULTS = {
    "enabled": False,
    "send_goal_on_start": False,
    "goal_frame": "odom",
    "goal_x": 0.0,
    "goal_y": 0.0,
    "goal_yaw": 0.0,
}


def yaw_to_quaternion(yaw):
    q = Quaternion()
    q.z = math.sin(yaw * 0.5)
    q.w = math.cos(yaw * 0.5)
    return q


class TeddyNavGoalNode(Node):
    def __init__(self):
        super().__init__("teddy_nav_goal")

        for name, default in PARAM_DEFAULTS.items():
            self.declare_parameter(name, default)

        self.enabled = self.param("enabled")
        self.send_goal_on_start = self.param("send_goal_on_start")
        self.goal_sent = False
        self.nav_client = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self.timer = self.create_timer(0.5, self.on_timer)

        self.get_logger().info(
            "teddy nav goal enabled=%s send_goal_on_start=%s"
            % (self.enabled, self.send_goal_on_start)
        )

    def param(self, name):
        return self.get_parameter(name).value

    def on_timer(self):
        if not self.enabled or not self.send_goal_on_start or self.goal_sent:
            return

        if not self.nav_client.wait_for_server(timeout_sec=0.1):
            self.get_logger().warning("navigate_to_pose action server not available yet")
            return

        goal = NavigateToPose.Goal()
        goal.pose = PoseStamped()
        goal.pose.header.frame_id = self.param("goal_frame")
        goal.pose.header.stamp = self.get_clock().now().to_msg()
        goal.pose.pose.position.x = self.param("goal_x")
        goal.pose.pose.position.y = self.param("goal_y")
        goal.pose.pose.orientation = yaw_to_quaternion(self.param("goal_yaw"))

        self.nav_client.send_goal_async(goal)
        self.goal_sent = True
        self.get_logger().info(
            "sent teddy nav goal x=%.2f y=%.2f yaw=%.2f"
            % (
                goal.pose.pose.position.x,
                goal.pose.pose.position.y,
                self.param("goal_yaw"),
            )
        )


def main(args=None):
    rclpy.init(args=args)
    node = TeddyNavGoalNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
