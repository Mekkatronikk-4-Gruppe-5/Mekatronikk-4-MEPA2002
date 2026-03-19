#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

detect_mega_port() {
  local candidate resolved

  for candidate in /dev/serial/by-id/*; do
    [[ -e "${candidate}" ]] || continue
    resolved="$(readlink -f "${candidate}")"
    case "${candidate} ${resolved}" in
      *Arduino*|*arduino*|*Mega*|*mega*|*ttyACM*|*ttyUSB*)
        printf '%s\n' "${resolved}"
        return 0
        ;;
    esac
  done

  for candidate in /dev/ttyACM* /dev/ttyUSB*; do
    [[ -e "${candidate}" ]] || continue
    printf '%s\n' "${candidate}"
    return 0
  done

  return 1
}

MEGA_PORT="${MEGA_PORT:-}"
MEGA_BAUDRATE="${MEGA_BAUDRATE:-115200}"

if [[ -z "${MEGA_PORT}" ]]; then
  MEGA_PORT="$(detect_mega_port)" || {
    echo "[mega-cal] Could not auto-detect Arduino Mega serial device." >&2
    echo "[mega-cal] Set it manually, for example: MEGA_PORT=/dev/ttyACM0 make mega-calibrate ARGS='snapshot'" >&2
    exit 1
  }
fi

if [[ ! -e "${MEGA_PORT}" ]]; then
  echo "[mega-cal] Serial device not found: ${MEGA_PORT}" >&2
  exit 1
fi

if ! python3 -c 'import serial' >/dev/null 2>&1; then
  echo "[mega-cal] Missing python3 serial support on host." >&2
  echo "[mega-cal] Install it with: sudo apt install python3-serial" >&2
  exit 1
fi

if [[ "$#" -eq 0 ]]; then
  set -- snapshot
fi

python3 "${SCRIPT_DIR}/mega_calibration.py" \
  "$@" \
  --port "${MEGA_PORT}" \
  --baudrate "${MEGA_BAUDRATE}"
