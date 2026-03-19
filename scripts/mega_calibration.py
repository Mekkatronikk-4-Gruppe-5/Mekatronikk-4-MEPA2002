#!/usr/bin/env python3
import argparse
import math
import sys
import time

import serial


IGNORED_PREFIXES = ("EVENT ", "MEGA_KEYBOARD_READY")


def read_line(ser: serial.Serial, timeout: float, ignored_prefixes: tuple[str, ...] = ()) -> str | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        raw = ser.readline()
        if not raw:
            continue
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            continue
        if any(text.startswith(prefix) for prefix in ignored_prefixes):
            print(f"[mega-cal] .. {text}")
            continue
        return text
    return None


def send_command(ser: serial.Serial, command: str) -> None:
    ser.write((command + "\n").encode("utf-8"))
    ser.flush()


def expect_reply(
    ser: serial.Serial,
    command: str,
    expected_prefix: str,
    timeout: float,
    ignored_prefixes: tuple[str, ...] = IGNORED_PREFIXES,
) -> str:
    print(f"[mega-cal] -> {command}")
    send_command(ser, command)
    reply = read_line(ser, timeout, ignored_prefixes=ignored_prefixes)
    if reply is None:
        raise RuntimeError(f"timeout waiting for reply to {command!r}")
    print(f"[mega-cal] <- {reply}")
    if not reply.startswith(expected_prefix):
        raise RuntimeError(
            f"unexpected reply to {command!r}: expected prefix {expected_prefix!r}, got {reply!r}"
        )
    return reply


def parse_encoder_reply(reply: str, label: str) -> int:
    parts = reply.split()
    if len(parts) != 2 or parts[0] != label:
        raise RuntimeError(f"failed to parse {label} reply: {reply!r}")
    try:
        return int(parts[1])
    except ValueError as exc:
        raise RuntimeError(f"failed to parse {label} count from {reply!r}") from exc


def read_encoders(ser: serial.Serial, timeout: float, swap_sides: bool = False) -> tuple[int, int]:
    left_reply = expect_reply(ser, "ENC1", "ENC1 ", timeout)
    right_reply = expect_reply(ser, "ENC2", "ENC2 ", timeout)
    first = parse_encoder_reply(left_reply, "ENC1")
    second = parse_encoder_reply(right_reply, "ENC2")
    if swap_sides:
        return second, first
    return first, second


def make_both_command(left_value: int, right_value: int, swap_sides: bool) -> str:
    if swap_sides:
        left_value, right_value = right_value, left_value
    return f"BOTH {left_value} {right_value}"


def verify_keyboard_firmware(ser: serial.Serial, timeout: float) -> str:
    firmware = expect_reply(ser, "ID", "MEGA_", timeout)
    if firmware != "MEGA_KEYBOARD_DRIVE":
        raise RuntimeError(
            "mega_calibration.py expects mega_keyboard_drive firmware, "
            f"but board reported {firmware!r}"
        )
    expect_reply(ser, "PING", "PONG", timeout)
    expect_reply(ser, "STOP", "OK STOP", timeout)
    return firmware


def reset_encoders(ser: serial.Serial, timeout: float) -> None:
    expect_reply(ser, "RESET ENC1", "OK RESET ENC1", timeout)
    expect_reply(ser, "RESET ENC2", "OK RESET ENC2", timeout)


def drive_for(
    ser: serial.Serial,
    command: str,
    duration_s: float,
    send_period_s: float,
    settle_time_s: float,
    timeout: float,
) -> None:
    deadline = time.monotonic() + max(0.0, duration_s)
    while True:
        print(f"[mega-cal] -> {command}")
        send_command(ser, command)
        now = time.monotonic()
        if now >= deadline:
            break
        time.sleep(min(send_period_s, max(0.0, deadline - now)))

    expect_reply(ser, "STOP", "OK STOP", timeout)
    time.sleep(max(0.0, settle_time_s))


def print_encoder_summary(start_left: int, start_right: int, end_left: int, end_right: int) -> tuple[int, int]:
    delta_left = end_left - start_left
    delta_right = end_right - start_right
    print()
    print("[mega-cal] Encoder summary")
    print(f"[mega-cal]   start: left={start_left} right={start_right}")
    print(f"[mega-cal]   end:   left={end_left} right={end_right}")
    print(f"[mega-cal]   delta: left={delta_left} right={delta_right}")
    return delta_left, delta_right


def print_straight_calibration(distance_m: float, delta_left: int, delta_right: int) -> None:
    if delta_left == 0 or delta_right == 0:
        raise RuntimeError("encoder delta was zero; cannot compute meters per tick")

    left_m_per_tick = abs(distance_m / delta_left)
    right_m_per_tick = abs(distance_m / delta_right)
    mean_m_per_tick = (left_m_per_tick + right_m_per_tick) / 2.0

    print()
    print("[mega-cal] Straight calibration")
    print(f"[mega-cal]   distance_m={distance_m:.6f}")
    print(f"[mega-cal]   left_m_per_tick={left_m_per_tick:.9f}")
    print(f"[mega-cal]   right_m_per_tick={right_m_per_tick:.9f}")
    print(f"[mega-cal]   mean_m_per_tick={mean_m_per_tick:.9f}")
    print("[mega-cal] YAML snippet:")
    print(f"left_m_per_tick: {left_m_per_tick:.9f}")
    print(f"right_m_per_tick: {right_m_per_tick:.9f}")
    print(f"mean_m_per_tick: {mean_m_per_tick:.9f}")


def print_spin_calibration(
    angle_deg: float,
    left_m_per_tick: float,
    right_m_per_tick: float,
    delta_left: int,
    delta_right: int,
) -> None:
    angle_rad = math.radians(abs(angle_deg))
    if angle_rad == 0.0:
        raise RuntimeError("angle_deg must be non-zero")

    left_distance = abs(delta_left) * left_m_per_tick
    right_distance = abs(delta_right) * right_m_per_tick
    track_width_eff_m = (left_distance + right_distance) / angle_rad

    print()
    print("[mega-cal] Spin calibration")
    print(f"[mega-cal]   angle_deg={angle_deg:.6f}")
    print(f"[mega-cal]   left_distance_m={left_distance:.6f}")
    print(f"[mega-cal]   right_distance_m={right_distance:.6f}")
    print(f"[mega-cal]   track_width_eff_m={track_width_eff_m:.9f}")
    print("[mega-cal] YAML snippet:")
    print(f"track_width_eff_m: {track_width_eff_m:.9f}")


def print_straight_trim_calibration(
    delta_left: int,
    delta_right: int,
    current_left_cmd_scale: float,
    current_right_cmd_scale: float,
    left_m_per_tick: float,
    right_m_per_tick: float,
) -> None:
    left_metric = abs(delta_left)
    right_metric = abs(delta_right)
    metric_label = "ticks"

    if left_m_per_tick > 0.0 and right_m_per_tick > 0.0:
        left_metric *= left_m_per_tick
        right_metric *= right_m_per_tick
        metric_label = "meters"

    if left_metric == 0.0 or right_metric == 0.0:
        raise RuntimeError("encoder delta was zero; cannot compute straight-trim suggestion")

    ratio = right_metric / left_metric if left_metric > right_metric else left_metric / right_metric
    suggested_left_cmd_scale = current_left_cmd_scale
    suggested_right_cmd_scale = current_right_cmd_scale
    faster_side = "balanced"

    if left_metric > right_metric:
        faster_side = "left"
        suggested_left_cmd_scale = current_left_cmd_scale * ratio
    elif right_metric > left_metric:
        faster_side = "right"
        suggested_right_cmd_scale = current_right_cmd_scale * ratio

    print()
    print("[mega-cal] Straight trim")
    print(f"[mega-cal]   comparison_metric={metric_label}")
    print(f"[mega-cal]   left_metric={left_metric:.9f}")
    print(f"[mega-cal]   right_metric={right_metric:.9f}")
    print(f"[mega-cal]   faster_side={faster_side}")
    print(
        f"[mega-cal]   current_left_cmd_scale={current_left_cmd_scale:.9f}"
    )
    print(
        f"[mega-cal]   current_right_cmd_scale={current_right_cmd_scale:.9f}"
    )
    print(
        f"[mega-cal]   suggested_left_cmd_scale={suggested_left_cmd_scale:.9f}"
    )
    print(
        f"[mega-cal]   suggested_right_cmd_scale={suggested_right_cmd_scale:.9f}"
    )
    print("[mega-cal] YAML snippet:")
    print(f"left_cmd_scale: {suggested_left_cmd_scale:.9f}")
    print(f"right_cmd_scale: {suggested_right_cmd_scale:.9f}")


def add_common_serial_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--port", required=True, help="Serial device path, for example /dev/ttyACM0")
    parser.add_argument("--baudrate", type=int, default=115200, help="Serial baudrate")
    parser.add_argument(
        "--post-open-wait",
        type=float,
        default=2.5,
        help="Seconds to wait after opening the port (Mega often resets on open)",
    )
    parser.add_argument(
        "--reply-timeout",
        type=float,
        default=2.0,
        help="Seconds to wait for commands that are expected to reply",
    )
    parser.add_argument(
        "--swap-sides",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Treat Mega M1/ENC1 as robot right and M2/ENC2 as robot left (default: enabled)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Calibration helper for mega_keyboard_drive encoder and motion tests."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    snapshot = subparsers.add_parser("snapshot", help="Print current encoder and state information")
    add_common_serial_args(snapshot)

    straight = subparsers.add_parser(
        "straight",
        help="Reset encoders, drive straight for a fixed duration, and optionally compute meters/tick",
    )
    add_common_serial_args(straight)
    straight.add_argument("--pwm", type=int, default=90, help="PWM magnitude to use (0-255)")
    straight.add_argument("--duration", type=float, default=1.6, help="Seconds to drive straight")
    straight.add_argument(
        "--direction",
        choices=("forward", "reverse"),
        default="forward",
        help="Direction to drive during the calibration run",
    )
    straight.add_argument(
        "--distance-m",
        type=float,
        default=0.0,
        help="Measured traveled distance in meters; if set, meters-per-tick is computed",
    )
    straight.add_argument(
        "--send-period",
        type=float,
        default=0.2,
        help="Seconds between repeated BOTH commands so the Mega watchdog stays armed",
    )
    straight.add_argument(
        "--settle-time",
        type=float,
        default=0.25,
        help="Seconds to wait after STOP before reading final encoders",
    )

    straight_trim = subparsers.add_parser(
        "straight-trim",
        help="Reset encoders, drive straight for a fixed duration, and suggest LEFT_CMD_SCALE/RIGHT_CMD_SCALE",
    )
    add_common_serial_args(straight_trim)
    straight_trim.add_argument("--pwm", type=int, default=90, help="PWM magnitude to use (0-255)")
    straight_trim.add_argument(
        "--duration",
        type=float,
        default=1.6,
        help="Seconds to drive straight while comparing left/right encoder motion",
    )
    straight_trim.add_argument(
        "--direction",
        choices=("forward", "reverse"),
        default="forward",
        help="Direction to drive during the trim run",
    )
    straight_trim.add_argument(
        "--current-left-cmd-scale",
        type=float,
        default=1.0,
        help="Current LEFT_CMD_SCALE value, used when suggesting the next value",
    )
    straight_trim.add_argument(
        "--current-right-cmd-scale",
        type=float,
        default=1.0,
        help="Current RIGHT_CMD_SCALE value, used when suggesting the next value",
    )
    straight_trim.add_argument(
        "--left-m-per-tick",
        type=float,
        default=0.0,
        help="Optional calibrated left meters-per-tick; used to compare physical distance instead of raw ticks",
    )
    straight_trim.add_argument(
        "--right-m-per-tick",
        type=float,
        default=0.0,
        help="Optional calibrated right meters-per-tick; used to compare physical distance instead of raw ticks",
    )
    straight_trim.add_argument(
        "--send-period",
        type=float,
        default=0.2,
        help="Seconds between repeated BOTH commands so the Mega watchdog stays armed",
    )
    straight_trim.add_argument(
        "--settle-time",
        type=float,
        default=0.25,
        help="Seconds to wait after STOP before reading final encoders",
    )

    spin = subparsers.add_parser(
        "spin",
        help="Reset encoders, spin in place for a fixed duration, and optionally compute effective track width",
    )
    add_common_serial_args(spin)
    spin.add_argument("--pwm", type=int, default=75, help="PWM magnitude to use (0-255)")
    spin.add_argument("--duration", type=float, default=1.2, help="Seconds to spin in place")
    spin.add_argument(
        "--direction",
        choices=("cw", "ccw"),
        default="cw",
        help="Spin direction: cw sends left forward / right reverse",
    )
    spin.add_argument(
        "--angle-deg",
        type=float,
        default=0.0,
        help="Measured absolute rotation angle in degrees; if set, effective track width is computed",
    )
    spin.add_argument(
        "--left-m-per-tick",
        type=float,
        default=0.0,
        help="Calibrated left meters-per-tick from a straight-line run",
    )
    spin.add_argument(
        "--right-m-per-tick",
        type=float,
        default=0.0,
        help="Calibrated right meters-per-tick from a straight-line run",
    )
    spin.add_argument(
        "--send-period",
        type=float,
        default=0.2,
        help="Seconds between repeated BOTH commands so the Mega watchdog stays armed",
    )
    spin.add_argument(
        "--settle-time",
        type=float,
        default=0.25,
        help="Seconds to wait after STOP before reading final encoders",
    )

    return parser


def handle_snapshot(ser: serial.Serial, args: argparse.Namespace) -> int:
    verify_keyboard_firmware(ser, args.reply_timeout)
    left, right = read_encoders(ser, args.reply_timeout, swap_sides=args.swap_sides)
    state = expect_reply(ser, "STATE", "STATE ", args.reply_timeout)
    print()
    print("[mega-cal] Snapshot")
    print(f"[mega-cal]   left_ticks={left}")
    print(f"[mega-cal]   right_ticks={right}")
    print(f"[mega-cal]   {state}")
    return 0


def handle_straight(ser: serial.Serial, args: argparse.Namespace) -> int:
    verify_keyboard_firmware(ser, args.reply_timeout)
    reset_encoders(ser, args.reply_timeout)
    start_left, start_right = read_encoders(ser, args.reply_timeout, swap_sides=args.swap_sides)

    pwm = max(0, min(255, abs(args.pwm)))
    signed_pwm = pwm if args.direction == "forward" else -pwm
    command = make_both_command(signed_pwm, signed_pwm, args.swap_sides)

    print()
    print("[mega-cal] Straight run")
    print(f"[mega-cal]   command={command}")
    print(f"[mega-cal]   duration_s={args.duration:.3f}")
    print(f"[mega-cal]   send_period_s={args.send_period:.3f}")

    drive_for(ser, command, args.duration, args.send_period, args.settle_time, args.reply_timeout)
    end_left, end_right = read_encoders(ser, args.reply_timeout, swap_sides=args.swap_sides)
    delta_left, delta_right = print_encoder_summary(start_left, start_right, end_left, end_right)

    if args.distance_m > 0.0:
        print_straight_calibration(args.distance_m, delta_left, delta_right)

    return 0


def handle_spin(ser: serial.Serial, args: argparse.Namespace) -> int:
    verify_keyboard_firmware(ser, args.reply_timeout)
    reset_encoders(ser, args.reply_timeout)
    start_left, start_right = read_encoders(ser, args.reply_timeout, swap_sides=args.swap_sides)

    pwm = max(0, min(255, abs(args.pwm)))
    left_pwm, right_pwm = (pwm, -pwm) if args.direction == "cw" else (-pwm, pwm)
    command = make_both_command(left_pwm, right_pwm, args.swap_sides)

    print()
    print("[mega-cal] Spin run")
    print(f"[mega-cal]   command={command}")
    print(f"[mega-cal]   duration_s={args.duration:.3f}")
    print(f"[mega-cal]   send_period_s={args.send_period:.3f}")

    drive_for(ser, command, args.duration, args.send_period, args.settle_time, args.reply_timeout)
    end_left, end_right = read_encoders(ser, args.reply_timeout, swap_sides=args.swap_sides)
    delta_left, delta_right = print_encoder_summary(start_left, start_right, end_left, end_right)

    if args.angle_deg > 0.0:
        if args.left_m_per_tick <= 0.0 or args.right_m_per_tick <= 0.0:
            raise RuntimeError(
                "spin calibration needs --left-m-per-tick and --right-m-per-tick when --angle-deg is set"
            )
        print_spin_calibration(
            args.angle_deg,
            args.left_m_per_tick,
            args.right_m_per_tick,
            delta_left,
            delta_right,
        )

    return 0


def handle_straight_trim(ser: serial.Serial, args: argparse.Namespace) -> int:
    verify_keyboard_firmware(ser, args.reply_timeout)
    reset_encoders(ser, args.reply_timeout)
    start_left, start_right = read_encoders(ser, args.reply_timeout, swap_sides=args.swap_sides)

    pwm = max(0, min(255, abs(args.pwm)))
    signed_pwm = pwm if args.direction == "forward" else -pwm
    command = make_both_command(signed_pwm, signed_pwm, args.swap_sides)

    print()
    print("[mega-cal] Straight trim run")
    print(f"[mega-cal]   command={command}")
    print(f"[mega-cal]   duration_s={args.duration:.3f}")
    print(f"[mega-cal]   send_period_s={args.send_period:.3f}")

    drive_for(ser, command, args.duration, args.send_period, args.settle_time, args.reply_timeout)
    end_left, end_right = read_encoders(ser, args.reply_timeout, swap_sides=args.swap_sides)
    delta_left, delta_right = print_encoder_summary(start_left, start_right, end_left, end_right)
    print_straight_trim_calibration(
        delta_left,
        delta_right,
        args.current_left_cmd_scale,
        args.current_right_cmd_scale,
        args.left_m_per_tick,
        args.right_m_per_tick,
    )
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        with serial.Serial(args.port, args.baudrate, timeout=0.2, write_timeout=1.0) as ser:
            print(f"[mega-cal] Opened {args.port} @ {args.baudrate}")
            time.sleep(max(0.0, args.post_open_wait))
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            if args.mode == "snapshot":
                return handle_snapshot(ser, args)
            if args.mode == "straight":
                return handle_straight(ser, args)
            if args.mode == "straight-trim":
                return handle_straight_trim(ser, args)
            if args.mode == "spin":
                return handle_spin(ser, args)

            raise RuntimeError(f"unsupported mode: {args.mode}")
    except serial.SerialException as exc:
        print(f"[mega-cal] Serial error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"[mega-cal] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
