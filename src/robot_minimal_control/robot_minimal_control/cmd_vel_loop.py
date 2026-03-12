#!/usr/bin/env python3
import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class CmdVelLoop(Node):
    def __init__(self):
        super().__init__('cmd_vel_loop')

        # Publiserer til ROS-topic /cmd_vel (bridgen tar resten)
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # 20 Hz loop
        self.timer = self.create_timer(0.05, self.on_timer)

        self.t = 0.0
        self.get_logger().info("Publishing /cmd_vel (ROS) -> bridged to Gazebo /cmd_vel")

    def on_timer(self):
        now = self.get_clock().now().nanoseconds * 1e-9

        msg = Twist()
        msg.linear.x = 0.0
        msg.angular.z = 0.0 * math.sin(now)

        self.pub.publish(msg)


def main():
    rclpy.init()
    node = CmdVelLoop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # Send et "stop" før vi dør
        stop = Twist()
        node.pub.publish(stop)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()