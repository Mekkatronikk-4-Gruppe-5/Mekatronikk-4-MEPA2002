#!/usr/bin/env python3
import argparse
import sys
import time

import serial


def read_line(ser: serial.Serial, timeout: float) -> str | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        raw = ser.readline()
        if not raw:
            continue
        text = raw.decode("utf-8", errors="replace").strip()
        if text:
            return text
    return None


def send_command(ser: serial.Serial, command: str) -> None:
    ser.write((command + "\n").encode("utf-8"))
    ser.flush()


def expect_reply(ser: serial.Serial, command: str, expected_prefix: str, timeout: float) -> str:
    print(f"[mega-test] -> {command}")
    send_command(ser, command)
    reply = read_line(ser, timeout)
    if reply is None:
        raise RuntimeError(f"timeout waiting for reply to {command!r}")
    print(f"[mega-test] <- {reply}")
    if not reply.startswith(expected_prefix):
        raise RuntimeError(
            f"unexpected reply to {command!r}: expected prefix {expected_prefix!r}, got {reply!r}"
        )
    return reply


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test for an Arduino Mega over USB serial.")
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
        help="Seconds to wait for each reply",
    )
    args = parser.parse_args()

    try:
        with serial.Serial(args.port, args.baudrate, timeout=0.2, write_timeout=1.0) as ser:
            print(f"[mega-test] Opened {args.port} @ {args.baudrate}")
            time.sleep(max(0.0, args.post_open_wait))
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            expect_reply(ser, "ID", "MEGA_SMOKETEST", args.reply_timeout)
            expect_reply(ser, "PING", "PONG", args.reply_timeout)
            expect_reply(ser, "LED ON", "OK LED ON", args.reply_timeout)
            time.sleep(0.2)
            expect_reply(ser, "LED OFF", "OK LED OFF", args.reply_timeout)
            print("[mega-test] Success: Mega responded to ID/PING and toggled LED.")
            return 0
    except serial.SerialException as exc:
        print(f"[mega-test] Serial error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"[mega-test] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
