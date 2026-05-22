#!/usr/bin/env python3
import os
import shlex
import sys

try:
    import yaml
except ImportError as exc:
    print(
        f"echo '[camera-config] Missing python yaml support: {exc}. Install python3-yaml.' >&2",
        file=sys.stdout,
    )
    print("exit 1", file=sys.stdout)
    sys.exit(0)


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_CONFIG = os.path.join(REPO_ROOT, "config", "camera_params.yaml")


def to_shell(value):
    if isinstance(value, bool):
        return "1" if value else "0"
    return str(value)


def pick(env_name, default):
    value = os.environ.get(env_name)
    if value is not None and value != "":
        return value
    return default


def require(section, section_name, key):
    if key not in section or section[key] is None:
        raise SystemExit(f"missing required {section_name}.{key} in camera config")
    return section[key]


def normalize_choice(value, *, false_value=None, true_value=None):
    if isinstance(value, bool):
        if value and true_value is not None:
            return true_value
        if not value and false_value is not None:
            return false_value
    return value


def scaled_size(size_value, scale_value):
    try:
        size = int(size_value)
        scale = float(scale_value)
    except (TypeError, ValueError):
        return size_value
    return max(1, int(round(size * scale)))


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CAMERA_CONFIG_FILE", DEFAULT_CONFIG)
    if not os.path.exists(config_path):
        print(f"echo '[camera-config] Config file not found: {config_path}' >&2", file=sys.stdout)
        print("exit 1", file=sys.stdout)
        return

    with open(config_path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    stream = data.get("camera_stream", {})
    detector = data.get("teddy_detector", {})

    denoise = normalize_choice(require(stream, "camera_stream", "denoise"), false_value="off", true_value="auto")
    debug_stream_scale = require(detector, "teddy_detector", "debug_stream_scale")

    values = {
        "CAMERA_CONFIG_FILE": config_path,
        "WIDTH": pick("WIDTH", require(stream, "camera_stream", "width")),
        "HEIGHT": pick("HEIGHT", require(stream, "camera_stream", "height")),
        "FPS": pick("FPS", require(stream, "camera_stream", "fps")),
        "BITRATE": pick("BITRATE", require(stream, "camera_stream", "bitrate_bps")),
        "INTRA": pick("INTRA", require(stream, "camera_stream", "intra")),
        "LOW_LATENCY": pick("LOW_LATENCY", to_shell(require(stream, "camera_stream", "low_latency"))),
        "FLUSH_OUTPUT": pick("FLUSH_OUTPUT", to_shell(require(stream, "camera_stream", "flush_output"))),
        "PC_JITTER_MS": pick("PC_JITTER_MS", require(stream, "camera_stream", "pc_jitter_ms")),
        "CAM_PORT": pick("CAM_PORT", require(stream, "camera_stream", "local_udp_port")),
        "PORT": pick("PORT", require(detector, "teddy_detector", "debug_stream_port")),
        "AWB": pick("AWB", require(stream, "camera_stream", "awb")),
        "AWB_GAINS": pick("AWB_GAINS", require(stream, "camera_stream", "awb_gains")),
        "BRIGHTNESS": pick("BRIGHTNESS", require(stream, "camera_stream", "brightness")),
        "CONTRAST": pick("CONTRAST", require(stream, "camera_stream", "contrast")),
        "SATURATION": pick("SATURATION", require(stream, "camera_stream", "saturation")),
        "SHARPNESS": pick("SHARPNESS", require(stream, "camera_stream", "sharpness")),
        "EV": pick("EV", require(stream, "camera_stream", "ev")),
        "DENOISE": pick("DENOISE", denoise),
        "METERING": pick("METERING", require(stream, "camera_stream", "metering")),
        "TUNING_FILE": pick("TUNING_FILE", require(stream, "camera_stream", "tuning_file")),
        "MEKK4_CAM_WIDTH": pick("MEKK4_CAM_WIDTH", require(stream, "camera_stream", "width")),
        "MEKK4_CAM_HEIGHT": pick("MEKK4_CAM_HEIGHT", require(stream, "camera_stream", "height")),
        "MEKK4_CAM_FPS": pick("MEKK4_CAM_FPS", require(stream, "camera_stream", "fps")),
        "MEKK4_NCNN_MODEL": pick("MEKK4_NCNN_MODEL", require(detector, "teddy_detector", "model_path")),
        "MEKK4_CONF": pick("MEKK4_CONF", require(detector, "teddy_detector", "conf")),
        "MEKK4_IMGSZ": pick("MEKK4_IMGSZ", require(detector, "teddy_detector", "imgsz")),
        "MEKK4_CENTER_TOL": pick("MEKK4_CENTER_TOL", require(detector, "teddy_detector", "center_tol")),
        "MEKK4_STATUS_LOG_PERIOD_SEC": pick(
            "MEKK4_STATUS_LOG_PERIOD_SEC",
            require(detector, "teddy_detector", "status_log_period_sec"),
        ),
        "MEKK4_SHOW": pick("MEKK4_SHOW", to_shell(require(detector, "teddy_detector", "show_gui"))),
        "MEKK4_DEBUG_STREAM": pick(
            "MEKK4_DEBUG_STREAM",
            to_shell(require(detector, "teddy_detector", "stream_debug_video")),
        ),
        "MEKK4_DEBUG_STREAM_PORT": pick(
            "MEKK4_DEBUG_STREAM_PORT",
            require(detector, "teddy_detector", "debug_stream_port"),
        ),
        "MEKK4_DEBUG_STREAM_SCALE": pick("MEKK4_DEBUG_STREAM_SCALE", debug_stream_scale),
        "MEKK4_DEBUG_STREAM_FPS": pick(
            "MEKK4_DEBUG_STREAM_FPS",
            require(detector, "teddy_detector", "debug_stream_fps"),
        ),
        "MEKK4_DEBUG_STREAM_BITRATE": pick(
            "MEKK4_DEBUG_STREAM_BITRATE",
            require(detector, "teddy_detector", "debug_stream_bitrate_bps"),
        ),
        "MEKK4_DEBUG_STREAM_ENCODER": pick(
            "MEKK4_DEBUG_STREAM_ENCODER",
            require(detector, "teddy_detector", "debug_stream_encoder"),
        ),
        "MEKK4_DEBUG_STREAM_WIDTH": pick(
            "MEKK4_DEBUG_STREAM_WIDTH",
            scaled_size(require(stream, "camera_stream", "width"), debug_stream_scale),
        ),
        "MEKK4_DEBUG_STREAM_HEIGHT": pick(
            "MEKK4_DEBUG_STREAM_HEIGHT",
            scaled_size(require(stream, "camera_stream", "height"), debug_stream_scale),
        ),
    }

    for key, value in values.items():
        print(f"export {key}={shlex.quote(to_shell(value))}")


if __name__ == "__main__":
    main()
