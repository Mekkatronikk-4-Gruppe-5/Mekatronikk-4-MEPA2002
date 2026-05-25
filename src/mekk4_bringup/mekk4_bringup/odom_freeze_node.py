#!/usr/bin/env python3
from __future__ import annotations

import copy

import rclpy
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Bool
from tf2_ros import TransformBroadcaster


class OdomFreezeNode(Node):
    def __init__(self) -> None:
        super().__init__("odom_freeze")

        self.declare_parameter("input_odom_topic", "odom_raw")
        self.declare_parameter("output_odom_topic", "odom")
        self.declare_parameter("freeze_topic", "/mega/freeze_odom")
        self.declare_parameter("publish_tf", True)

        input_odom_topic = str(self.get_parameter("input_odom_topic").value)
        output_odom_topic = str(self.get_parameter("output_odom_topic").value)
        freeze_topic = str(self.get_parameter("freeze_topic").value)
        publish_tf = bool(self.get_parameter("publish_tf").value)

        self._frozen = False
        self._held_odom: Odometry | None = None
        self._last_output_odom: Odometry | None = None

        self._odom_pub = self.create_publisher(Odometry, output_odom_topic, 10)
        self._tf_broadcaster = TransformBroadcaster(self) if publish_tf else None
        self.create_subscription(Odometry, input_odom_topic, self._on_odom, 10)
        self.create_subscription(Bool, freeze_topic, self._on_freeze, 10)

        self.get_logger().info(
            "Odom freeze node forwarding %s -> %s, freeze_topic=%s, publish_tf=%s"
            % (input_odom_topic, output_odom_topic, freeze_topic, publish_tf)
        )

    def _on_freeze(self, msg: Bool) -> None:
        if msg.data and not self._frozen:
            self._held_odom = copy.deepcopy(self._last_output_odom)
            self.get_logger().info("Odom output frozen")
        elif not msg.data and self._frozen:
            self.get_logger().info("Odom output unfrozen")
        self._frozen = msg.data

    def _on_odom(self, msg: Odometry) -> None:
        if self._frozen:
            if self._held_odom is None:
                self._held_odom = copy.deepcopy(msg)
            out = copy.deepcopy(self._held_odom)
            out.header.stamp = msg.header.stamp
            out.twist.twist.linear.x = 0.0
            out.twist.twist.linear.y = 0.0
            out.twist.twist.linear.z = 0.0
            out.twist.twist.angular.x = 0.0
            out.twist.twist.angular.y = 0.0
            out.twist.twist.angular.z = 0.0
        else:
            out = copy.deepcopy(msg)
            self._held_odom = None

        self._last_output_odom = copy.deepcopy(out)
        self._odom_pub.publish(out)
        self._publish_tf(out)

    def _publish_tf(self, odom: Odometry) -> None:
        if self._tf_broadcaster is None:
            return

        transform = TransformStamped()
        transform.header.stamp = odom.header.stamp
        transform.header.frame_id = odom.header.frame_id
        transform.child_frame_id = odom.child_frame_id
        transform.transform.translation.x = odom.pose.pose.position.x
        transform.transform.translation.y = odom.pose.pose.position.y
        transform.transform.translation.z = odom.pose.pose.position.z
        transform.transform.rotation = odom.pose.pose.orientation
        self._tf_broadcaster.sendTransform(transform)


def main() -> None:
    rclpy.init()
    node = OdomFreezeNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
