#!/usr/bin/env python3

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node


class NavCmdVelFlipNode(Node):
    def __init__(self) -> None:
        super().__init__("nav_cmd_vel_flip")

        self.declare_parameter("input_topic", "cmd_vel_smoothed")
        self.declare_parameter("output_topic", "cmd_vel_smoothed_flipped")

        input_topic = self.get_parameter("input_topic").get_parameter_value().string_value
        output_topic = self.get_parameter("output_topic").get_parameter_value().string_value

        self._pub = self.create_publisher(Twist, output_topic, 10)
        self._sub = self.create_subscription(Twist, input_topic, self._on_cmd_vel, 10)

    def _on_cmd_vel(self, msg: Twist) -> None:
        flipped = Twist()
        flipped.linear.x = msg.linear.x
        flipped.linear.y = msg.linear.y
        flipped.linear.z = msg.linear.z
        flipped.angular.x = msg.angular.x
        flipped.angular.y = msg.angular.y
        flipped.angular.z = -msg.angular.z
        self._pub.publish(flipped)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = NavCmdVelFlipNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
