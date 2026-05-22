#!/usr/bin/env python3
from __future__ import annotations

import math

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.time import Time
from std_msgs.msg import Empty
from tf2_ros import Buffer, TransformException, TransformListener


class GoHomeNode(Node):
    def __init__(self):
        super().__init__("go_home")

        self.declare_parameter("global_frame", "odom")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("goal_topic", "/goal_pose")
        self.declare_parameter("home_pose_topic", "/home_pose")
        self.declare_parameter("trigger_topic", "/teddy_grab/done")
        self.declare_parameter("save_delay_s", 3.0)
        self.declare_parameter("lookup_timeout_s", 0.2)
        self.declare_parameter("home_pose_publish_period_s", 1.0)

        self.global_frame = str(self.get_parameter("global_frame").value)
        self.base_frame = str(self.get_parameter("base_frame").value)
        self.save_delay_s = float(self.get_parameter("save_delay_s").value)
        self.lookup_timeout_s = float(self.get_parameter("lookup_timeout_s").value)

        self.home_pose = None
        self.started_at = self.now_s()
        self.last_wait_log = -math.inf

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.goal_pub = self.create_publisher(PoseStamped, self.get_parameter("goal_topic").value, 10)
        self.home_pose_pub = self.create_publisher(
            PoseStamped,
            self.get_parameter("home_pose_topic").value,
            10,
        )
        self.create_subscription(Empty, self.get_parameter("trigger_topic").value, self.on_trigger, 10)
        self.save_timer = self.create_timer(0.5, self.try_save_home_pose)
        self.home_pose_timer = self.create_timer(
            float(self.get_parameter("home_pose_publish_period_s").value),
            self.publish_home_pose,
        )

        self.get_logger().info(
            "saving home pose from %s->%s after %.1fs"
            % (self.global_frame, self.base_frame, self.save_delay_s)
        )

    def now_s(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def try_save_home_pose(self):
        if self.home_pose is not None:
            return

        now = self.now_s()
        if now - self.started_at < self.save_delay_s:
            return

        try:
            transform = self.tf_buffer.lookup_transform(
                self.global_frame,
                self.base_frame,
                Time(),
                timeout=Duration(seconds=self.lookup_timeout_s),
            )
        except TransformException as exc:
            if now - self.last_wait_log >= 2.0:
                self.get_logger().warning(
                    "waiting for TF %s->%s: %s" % (self.global_frame, self.base_frame, exc)
                )
                self.last_wait_log = now
            return

        pose = PoseStamped()
        pose.header.frame_id = self.global_frame
        pose.pose.position.x = transform.transform.translation.x
        pose.pose.position.y = transform.transform.translation.y
        pose.pose.position.z = 0.0
        pose.pose.orientation = transform.transform.rotation
        self.home_pose = pose
        self.save_timer.cancel()

        self.get_logger().info(
            "saved home pose x=%.3f y=%.3f" % (pose.pose.position.x, pose.pose.position.y)
        )
        self.publish_home_pose()

    def on_trigger(self, _msg):
        if self.home_pose is None:
            self.get_logger().warning("go home requested, but no home pose is saved yet")
            return

        goal = self.current_home_pose_msg()
        self.goal_pub.publish(goal)
        self.get_logger().info("published home goal")

    def publish_home_pose(self):
        if self.home_pose is None:
            return
        self.home_pose_pub.publish(self.current_home_pose_msg())

    def current_home_pose_msg(self):
        msg = PoseStamped()
        msg.header.frame_id = self.home_pose.header.frame_id
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose = self.home_pose.pose
        return msg


def main(args=None):
    rclpy.init(args=args)
    node = GoHomeNode()
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
