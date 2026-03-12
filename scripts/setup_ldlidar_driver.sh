#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/ldrobotSensorTeam/ldlidar_stl_ros2.git"
REPO_TAG="v3.0.3"
WS_ROOT="/ws"
SRC_DIR="${WS_ROOT}/src"
PKG_DIR="${SRC_DIR}/ldlidar_stl_ros2"

mkdir -p "${SRC_DIR}"

if [[ -d "${PKG_DIR}/.git" ]]; then
  echo "[lidar-setup] Existing ldlidar_stl_ros2 found, updating..."
  git -C "${PKG_DIR}" fetch --tags origin
  git -C "${PKG_DIR}" checkout -f "${REPO_TAG}"
else
  echo "[lidar-setup] Cloning ldlidar_stl_ros2 (${REPO_TAG})..."
  git clone --depth 1 --branch "${REPO_TAG}" "${REPO_URL}" "${PKG_DIR}"
fi

echo "[lidar-setup] Building workspace..."
"${WS_ROOT}/scripts/ws_build.sh"

echo "[lidar-setup] Done."
