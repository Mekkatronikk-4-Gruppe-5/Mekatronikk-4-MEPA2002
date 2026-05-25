#!/usr/bin/env bash
set -euo pipefail

INTERVAL_S="${INTERVAL_S:-2}"
PATTERN="${PATTERN:-rpicam|libcamera|gst-launch|x264|ffmpeg|docker|containerd|python|ros2}"

while true; do
  clear
  date '+[perf-watch] %F %T'
  echo "[perf-watch] host processes matching: ${PATTERN}"
  echo
  ps -eo pid,ppid,pcpu,pmem,rss,comm,args --sort=-pcpu \
    | awk -v pattern="${PATTERN}" 'NR == 1 || $0 ~ pattern {print}' \
    | head -n 30
  echo
  if command -v vcgencmd >/dev/null 2>&1; then
    vcgencmd measure_temp || true
    vcgencmd get_throttled || true
  fi
  sleep "${INTERVAL_S}"
done
