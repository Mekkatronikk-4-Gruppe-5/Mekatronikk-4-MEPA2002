#!/usr/bin/env bash
set -euo pipefail

WS_ROOT="${WS_ROOT:-/ws}"
cd "${WS_ROOT}"

# Clear stale Python package build/install state before colcon build.
# ament_python packages copy setup.py/launch data into build/<pkg>, and a
# deleted launch/data file can remain referenced there even after source files
# are removed from src.
while IFS= read -r pkg_dir; do
  pkg_name="$(basename "${pkg_dir}")"
  rm -rf "${WS_ROOT}/build/${pkg_name}" "${WS_ROOT}/install/${pkg_name}"
done < <(find "${WS_ROOT}/src" -maxdepth 2 -name setup.py -printf '%h\n')

# Also clear any lingering setuptools metadata just in case.
[[ -d "${WS_ROOT}/build" ]] && find "${WS_ROOT}/build" -type d -name '*.egg-info' -prune -exec rm -rf {} +

colcon build --symlink-install

python3 - <<'PY'
from pathlib import Path
import os

old = b"#!/usr/bin/python3\n"
new = b"#!/opt/venv/bin/python3\n"

ws_root = os.environ.get("WS_ROOT", "/ws")
root = Path(ws_root) / "install"
patched = 0

for f in root.rglob("*"):
    if not f.is_file():
        continue
    # vi vil kun treffe <WS_ROOT>/install/<pkg>/lib/<pkg>/<script>
    parts = f.parts
    if "lib" not in parts:
        continue
    i = parts.index("lib")
    if len(parts) < i + 3:
        continue

    try:
        with f.open("rb") as fh:
            first = fh.readline()
        if first == old:
            data = f.read_bytes()
            f.write_bytes(new + data[len(old):])
            patched += 1
    except Exception:
        pass

print(f"shebang patched: {patched} file(s)")
PY
