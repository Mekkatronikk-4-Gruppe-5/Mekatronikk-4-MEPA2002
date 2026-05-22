#!/usr/bin/env python3
from __future__ import annotations

import math
import os
import re
import subprocess
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from sensor_msgs.msg import Imu, LaserScan
from std_msgs.msg import String


STATUS_RE = re.compile(r"(?P<key>[A-Za-z_]+)=(?P<value>[^ ]+)")
CLK_TCK = os.sysconf(os.sysconf_names["SC_CLK_TCK"])


@dataclass(slots=True)
class TopicStats:
    name: str
    stamps: deque[float]
    last_age_s: float | None = None
    last_infer_ms: float | None = None

    def add(self, now: float) -> None:
        self.stamps.append(now)

    def hz(self) -> float:
        if len(self.stamps) < 2:
            return 0.0
        dt = self.stamps[-1] - self.stamps[0]
        if dt <= 0.0:
            return 0.0
        return (len(self.stamps) - 1) / dt

    def gap_s(self, now: float) -> float:
        if not self.stamps:
            return math.inf
        return now - self.stamps[-1]


class PerformanceMonitorNode(Node):
    def __init__(self) -> None:
        super().__init__("performance_monitor")

        self._report_period_s = self._param_float("report_period_s", 5.0)
        self._window_s = self._param_float("window_s", 10.0)
        self._top_process_count = self._param_int("top_process_count", 8)
        self._process_keywords = self._param_list(
            "process_keywords",
            [
                "teddy_detector",
                "teddy_approach",
                "teddy_grab",
                "mega_driver",
                "bno085",
                "ldlidar",
                "controller_server",
                "planner_server",
                "bt_navigator",
                "collision_monitor",
                "python",
                "gst-launch",
                "x264enc",
            ],
        )

        self._topics: dict[str, TopicStats] = {}
        self._last_total_jiffies: int | None = None
        self._last_proc_jiffies: dict[int, int] = {}
        self._cpu_count = os.cpu_count() or 1

        qos = QoSProfile(
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10,
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
        )
        self._subscribe("/teddy_detector/status", String, self._on_detector_status, qos)
        self._subscribe("/lidar", LaserScan, self._on_topic("/lidar"), qos)
        self._subscribe("/imu/data", Imu, self._on_topic("/imu/data"), qos)
        self._subscribe("/odom", Odometry, self._on_topic("/odom"), qos)
        self._subscribe("/cmd_vel", Twist, self._on_topic("/cmd_vel"), qos)
        self._subscribe("/cmd_vel_teddy", Twist, self._on_topic("/cmd_vel_teddy"), qos)

        self._summary_pub = self.create_publisher(String, "/performance/summary", 10)
        self.create_timer(self._report_period_s, self._report)
        self.get_logger().info(
            "performance monitor active: report_period_s=%.1f window_s=%.1f"
            % (self._report_period_s, self._window_s)
        )

    def _param_float(self, name: str, default: float) -> float:
        self.declare_parameter(name, default)
        return float(self.get_parameter(name).value)

    def _param_int(self, name: str, default: int) -> int:
        self.declare_parameter(name, default)
        return int(self.get_parameter(name).value)

    def _param_list(self, name: str, default: list[str]) -> list[str]:
        self.declare_parameter(name, default)
        value = self.get_parameter(name).value
        return [str(item) for item in value]

    def _subscribe(self, topic: str, msg_type, callback, qos: QoSProfile) -> None:
        self._topics[topic] = TopicStats(topic, deque(maxlen=max(2, int(self._window_s * 50))))
        self.create_subscription(msg_type, topic, callback, qos)

    def _on_topic(self, topic: str):
        def callback(_msg) -> None:
            self._topics[topic].add(time.monotonic())

        return callback

    def _on_detector_status(self, msg: String) -> None:
        now = time.monotonic()
        stats = self._topics["/teddy_detector/status"]
        stats.add(now)
        fields = {match.group("key"): match.group("value") for match in STATUS_RE.finditer(msg.data)}
        stats.last_age_s = self._parse_float(fields.get("age"))
        stats.last_infer_ms = self._parse_float(fields.get("infer_ms"))

    @staticmethod
    def _parse_float(value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def _report(self) -> None:
        now = time.monotonic()
        topic_parts = []
        for topic, stats in self._topics.items():
            hz = stats.hz()
            gap = stats.gap_s(now)
            if topic == "/teddy_detector/status":
                topic_parts.append(
                    "%s %.2fHz gap=%.2fs age=%s infer_ms=%s"
                    % (
                        topic,
                        hz,
                        gap,
                        self._fmt(stats.last_age_s, "s"),
                        self._fmt(stats.last_infer_ms, "ms"),
                    )
                )
            else:
                topic_parts.append("%s %.2fHz gap=%.2fs" % (topic, hz, gap))

        system = self._system_status()
        processes = self._process_status()
        summary = " | ".join(topic_parts + system + processes)

        msg = String()
        msg.data = summary
        self._summary_pub.publish(msg)
        self.get_logger().info(summary)

    @staticmethod
    def _fmt(value: float | None, unit: str) -> str:
        if value is None:
            return "unknown"
        return "%.3f%s" % (value, unit) if unit == "s" else "%.0f%s" % (value, unit)

    def _system_status(self) -> list[str]:
        parts = []
        temp = self._run_text(["vcgencmd", "measure_temp"])
        if temp:
            parts.append(temp)
        throttled = self._run_text(["vcgencmd", "get_throttled"])
        if throttled:
            parts.append(throttled)
        return parts

    @staticmethod
    def _run_text(command: list[str]) -> str:
        try:
            completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=0.2)
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return completed.stdout.strip()

    def _process_status(self) -> list[str]:
        total_jiffies = self._read_total_jiffies()
        proc_rows = self._read_matching_processes()
        if total_jiffies is None:
            return []

        if self._last_total_jiffies is None:
            self._last_total_jiffies = total_jiffies
            self._last_proc_jiffies = {pid: jiffies for pid, jiffies, _, _ in proc_rows}
            return ["proc_cpu=warming_up"]

        total_delta = max(1, total_jiffies - self._last_total_jiffies)
        self._last_total_jiffies = total_jiffies

        ranked = []
        next_proc_jiffies = {}
        for pid, jiffies, rss_kb, label in proc_rows:
            previous = self._last_proc_jiffies.get(pid, jiffies)
            next_proc_jiffies[pid] = jiffies
            cpu_pct = ((jiffies - previous) / total_delta) * 100.0 * self._cpu_count
            ranked.append((cpu_pct, rss_kb, pid, label))

        self._last_proc_jiffies = next_proc_jiffies
        ranked.sort(reverse=True)
        return [
            "pid=%d cpu=%.1f%% rss=%.1fMB %s" % (pid, cpu, rss_kb / 1024.0, label[:80])
            for cpu, rss_kb, pid, label in ranked[: self._top_process_count]
        ]

    @staticmethod
    def _read_total_jiffies() -> int | None:
        try:
            first_line = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0]
        except OSError:
            return None
        values = first_line.split()[1:]
        return sum(int(value) for value in values)

    def _read_matching_processes(self) -> list[tuple[int, int, int, str]]:
        rows = []
        keywords = tuple(self._process_keywords)
        for proc_dir in Path("/proc").iterdir():
            if not proc_dir.name.isdigit():
                continue
            pid = int(proc_dir.name)
            try:
                cmdline = (proc_dir / "cmdline").read_bytes().replace(b"\x00", b" ").decode(
                    "utf-8",
                    errors="replace",
                )
                stat = (proc_dir / "stat").read_text(encoding="utf-8")
                status = (proc_dir / "status").read_text(encoding="utf-8")
            except OSError:
                continue

            label = cmdline.strip() or self._stat_comm(stat)
            if not any(keyword in label for keyword in keywords):
                continue

            jiffies = self._proc_jiffies(stat)
            rss_kb = self._rss_kb(status)
            if jiffies is not None:
                rows.append((pid, jiffies, rss_kb, label))
        return rows

    @staticmethod
    def _stat_comm(stat: str) -> str:
        start = stat.find("(")
        stop = stat.rfind(")")
        if start < 0 or stop <= start:
            return ""
        return stat[start + 1 : stop]

    @staticmethod
    def _proc_jiffies(stat: str) -> int | None:
        stop = stat.rfind(")")
        if stop < 0:
            return None
        fields = stat[stop + 2 :].split()
        try:
            utime = int(fields[11])
            stime = int(fields[12])
        except (IndexError, ValueError):
            return None
        return utime + stime

    @staticmethod
    def _rss_kb(status: str) -> int:
        for line in status.splitlines():
            if line.startswith("VmRSS:"):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        return int(parts[1])
                    except ValueError:
                        return 0
        return 0


def main() -> None:
    rclpy.init()
    node = PerformanceMonitorNode()
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
