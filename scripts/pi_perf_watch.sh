#!/usr/bin/env bash
set -euo pipefail

INTERVAL="${INTERVAL:-5}"
PATTERN="${PATTERN:-rpicam|gst|x264|python|ros|teddy|mega|ldlidar|nav2|controller_server|planner_server|bt_navigator|collision_monitor|docker}"

echo "[pi-perf-watch] interval=${INTERVAL}s pattern=${PATTERN}" >&2
echo "[pi-perf-watch] Ctrl-C to stop." >&2

while true; do
  echo
  date '+=== %F %T ==='

  if command -v vcgencmd >/dev/null 2>&1; then
    vcgencmd measure_temp || true
    vcgencmd measure_clock arm || true
    vcgencmd get_throttled || true
  fi

  echo "--- top matching processes ---"
  ps -eo pid,ppid,pcpu,pmem,comm,args --sort=-pcpu \
    | awk -v pattern="${PATTERN}" 'NR == 1 || $0 ~ pattern { print }' \
    | head -25

  if command -v docker >/dev/null 2>&1; then
    echo "--- docker stats ---"
    docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.PIDs}}' || true
  fi

  sleep "${INTERVAL}"
done
