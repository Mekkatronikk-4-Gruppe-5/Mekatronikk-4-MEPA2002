#!/usr/bin/env python3
import os
import shlex
import sys

try:
    import yaml
except ImportError as exc:
    print(
        f"echo '[robot-cal] Missing python yaml support: {exc}. Install python3-yaml.' >&2",
        file=sys.stdout,
    )
    print("exit 1", file=sys.stdout)
    sys.exit(0)


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT_CONFIG = os.path.join(REPO_ROOT, "config", "robot_calibration.yaml")


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
        raise SystemExit(f"missing required {section_name}.{key} in robot calibration config")
    return section[key]


def main():
    config_path = (
        sys.argv[1]
        if len(sys.argv) > 1
        else os.environ.get("ROBOT_CALIBRATION_FILE", DEFAULT_CONFIG)
    )

    if not os.path.exists(config_path):
        print(f"echo '[robot-cal] Config file not found: {config_path}' >&2", file=sys.stdout)
        print("exit 1", file=sys.stdout)
        return

    with open(config_path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    mega = data.get("mega_driver", {})
    values = {
        "ROBOT_CALIBRATION_FILE": config_path,
        "SWAP_SIDES": pick("SWAP_SIDES", 1 if require(mega, "mega_driver", "swap_sides") else 0),
        "LEFT_CMD_SIGN": pick("LEFT_CMD_SIGN", require(mega, "mega_driver", "left_cmd_sign")),
        "RIGHT_CMD_SIGN": pick("RIGHT_CMD_SIGN", require(mega, "mega_driver", "right_cmd_sign")),
        "ANGULAR_CMD_SIGN": pick(
            "ANGULAR_CMD_SIGN",
            require(mega, "mega_driver", "angular_cmd_sign"),
        ),
        "MIN_NONZERO_PWM": pick(
            "MIN_NONZERO_PWM",
            require(mega, "mega_driver", "min_nonzero_pwm"),
        ),
        "MIN_FORWARD_PWM": pick(
            "MIN_FORWARD_PWM",
            require(mega, "mega_driver", "min_forward_pwm"),
        ),
        "MIN_REVERSE_PWM": pick(
            "MIN_REVERSE_PWM",
            require(mega, "mega_driver", "min_reverse_pwm"),
        ),
        "MIN_TURN_PWM": pick("MIN_TURN_PWM", require(mega, "mega_driver", "min_turn_pwm")),
        "PURE_ROTATION_LINEAR_DEADBAND_MPS": pick(
            "PURE_ROTATION_LINEAR_DEADBAND_MPS",
            require(mega, "mega_driver", "pure_rotation_linear_deadband_mps"),
        ),
        "LEFT_CMD_SCALE": pick("LEFT_CMD_SCALE", require(mega, "mega_driver", "left_cmd_scale")),
        "RIGHT_CMD_SCALE": pick(
            "RIGHT_CMD_SCALE",
            require(mega, "mega_driver", "right_cmd_scale"),
        ),
        "LEFT_TICK_SIGN": pick("LEFT_TICK_SIGN", require(mega, "mega_driver", "left_tick_sign")),
        "RIGHT_TICK_SIGN": pick(
            "RIGHT_TICK_SIGN",
            require(mega, "mega_driver", "right_tick_sign"),
        ),
        "LEFT_M_PER_TICK": pick(
            "LEFT_M_PER_TICK",
            require(mega, "mega_driver", "left_m_per_tick"),
        ),
        "RIGHT_M_PER_TICK": pick(
            "RIGHT_M_PER_TICK",
            require(mega, "mega_driver", "right_m_per_tick"),
        ),
        "TRACK_WIDTH_EFF_M": pick(
            "TRACK_WIDTH_EFF_M",
            require(mega, "mega_driver", "track_width_eff_m"),
        ),
    }

    for key, value in values.items():
        print(f"export {key}={shlex.quote(to_shell(value))}")


if __name__ == "__main__":
    main()
