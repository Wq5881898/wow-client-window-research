from __future__ import annotations

import argparse
import ctypes
import json
import platform
import sys
import time
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

VK_CODES = {
    **{str(i): 0x30 + i for i in range(10)},
    **{chr(ord("A") + i): 0x41 + i for i in range(26)},
    **{f"F{i}": 0x6F + i for i in range(1, 13)},
    "SPACE": 0x20,
    "TAB": 0x09,
}
EFFECTS = {"ok", "no_effect", "wrong_effect", "unknown", "blocked", "forbidden"}
ULONG_PTR = wintypes.WPARAM


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]


def build_key_inputs(vk_code: int) -> ctypes.Array:
    return (INPUT * 2)(
        INPUT(type=1, ki=KEYBDINPUT(vk_code, 0, 0, 0, 0)),
        INPUT(type=1, ki=KEYBDINPUT(vk_code, 0, 0x0002, 0, 0)),
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Foreground-only single-key input probe. Dry-run is the default; "
            "live mode requires explicit arming and one manual confirmation per trial."
        )
    )
    parser.add_argument("--key", default="1", help="0-9, A-Z, F1-F12, SPACE, or TAB")
    parser.add_argument("--window-title", default="World of Warcraft", help="Expected foreground window title")
    parser.add_argument("--contains-title", action="store_true", help="Match title by substring instead of exact text")
    parser.add_argument("--trials", type=int, default=1, help="Number of manually initiated trials (positive integer)")
    parser.add_argument("--arm-delay", type=float, default=3.0, help="Seconds allowed to focus the target window")
    parser.add_argument("--live", action="store_true", help="Actually send input; omitted means dry-run")
    parser.add_argument("--output", type=Path, help="Optional JSON output path")
    args = parser.parse_args()

    args.key = args.key.upper()
    if args.key not in VK_CODES:
        parser.error("unsupported key; use 0-9, A-Z, F1-F12, SPACE, or TAB")
    if args.trials < 1:
        parser.error("--trials must be a positive integer")
    if not 1.0 <= args.arm_delay <= 10.0:
        parser.error("--arm-delay must be between 1 and 10 seconds")
    if args.contains_title and len(args.window_title.strip()) < 3:
        parser.error("substring title must contain at least 3 characters")
    if not args.window_title.strip():
        parser.error("--window-title cannot be empty")
    return args


def title_matches(actual: str, expected: str, contains: bool) -> bool:
    actual_normalized = actual.strip().casefold()
    expected_normalized = expected.strip().casefold()
    if contains:
        return expected_normalized in actual_normalized
    return actual_normalized == expected_normalized


def get_foreground_title() -> str:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def send_key(vk_code: int) -> tuple[bool, int]:
    if platform.system() != "Windows":
        raise RuntimeError("live input is supported only on Windows")

    inputs = build_key_inputs(vk_code)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    user32.SendInput.restype = wintypes.UINT
    sent = user32.SendInput(2, inputs, ctypes.sizeof(INPUT))
    error = ctypes.get_last_error() if sent != 2 else 0
    return sent == 2, error


def prompt_effect() -> str:
    prompt = "Effect [ok/no_effect/wrong_effect/unknown/blocked/forbidden]: "
    while True:
        answer = input(prompt).strip().lower()
        if answer in EFFECTS:
            return answer
        print("Enter one of: " + ", ".join(sorted(EFFECTS)))


def write_result(path: Path, result: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def default_output() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return RESULTS / f"t2_input_probe_{stamp}.json"


def dry_run(args: argparse.Namespace, output: Path) -> int:
    result = {
        "schema_version": 1,
        "instrument": "foreground_single_key_probe",
        "mode": "dry-run",
        "started_at_utc": utc_now(),
        "finished_at_utc": utc_now(),
        "key": args.key,
        "requested_trials": args.trials,
        "window_match_mode": "contains" if args.contains_title else "exact",
        "records": [],
        "summary": {"sent": 0, "not_sent": args.trials},
        "limitations": [
            "Dry-run sends no input.",
            "This instrument cannot establish in-game effect, authorization, or account safety.",
        ],
    }
    write_result(output, result)
    print(f"Dry-run only: no input sent. Wrote {output}")
    return 0


def live_run(args: argparse.Namespace, output: Path) -> int:
    if platform.system() != "Windows":
        print("Live mode requires Windows.", file=sys.stderr)
        return 2

    print("LIVE MODE: one key-down/key-up pair per manually armed trial.")
    print("The target title is used for matching but is not stored in the result.")
    if input('Type "SEND ONE KEY" to arm live mode: ').strip() != "SEND ONE KEY":
        print("Not armed; no input sent.")
        return 2

    result = {
        "schema_version": 1,
        "instrument": "foreground_single_key_probe",
        "mode": "live",
        "started_at_utc": utc_now(),
        "finished_at_utc": None,
        "key": args.key,
        "requested_trials": args.trials,
        "window_match_mode": "contains" if args.contains_title else "exact",
        "records": [],
        "summary": {},
        "limitations": [
            "Effect and restriction status are manually reported by the operator.",
            "A successful SendInput call does not establish in-game effect, authorization, or account safety.",
        ],
    }

    stop_reason = "completed"
    try:
        for index in range(1, args.trials + 1):
            command = input(f"Trial {index}/{args.trials}: Enter to arm, or q to stop: ").strip().lower()
            if command == "q":
                stop_reason = "operator_stop"
                break
            print(f"Focus the target window within {args.arm_delay:.1f}s. Ctrl+C cancels.")
            time.sleep(args.arm_delay)
            actual_title = get_foreground_title()
            matched = title_matches(actual_title, args.window_title, args.contains_title)
            record = {
                "trial": index,
                "attempted_at_utc": utc_now(),
                "foreground_match": matched,
                "send_status": "not_sent",
                "os_error": 0,
                "effect": "not_observed",
            }
            if not matched:
                record["send_status"] = "refused_foreground_mismatch"
                result["records"].append(record)
                stop_reason = "foreground_mismatch"
                print("Foreground title mismatch; no input sent. Stopping fail-closed.")
                break

            success, error = send_key(VK_CODES[args.key])
            record["send_status"] = "sent" if success else "send_error"
            record["os_error"] = error
            if not success:
                result["records"].append(record)
                stop_reason = "send_error"
                print(f"SendInput failed with Windows error {error}; stopping.")
                break
            record["effect"] = prompt_effect()
            result["records"].append(record)
            if record["effect"] in {"wrong_effect", "blocked", "forbidden"}:
                stop_reason = record["effect"]
                print(f"Stopping on {record['effect']}.")
                break
    except KeyboardInterrupt:
        stop_reason = "keyboard_interrupt"
        print("\nInterrupted; no further input will be sent.")

    records = result["records"]
    result["finished_at_utc"] = utc_now()
    result["summary"] = {
        "stop_reason": stop_reason,
        "records": len(records),
        "sent": sum(row["send_status"] == "sent" for row in records),
        "ok_effects": sum(row["effect"] == "ok" for row in records),
        "unexpected_effects": sum(row["effect"] == "wrong_effect" for row in records),
        "restriction_reports": sum(row["effect"] in {"blocked", "forbidden"} for row in records),
    }
    write_result(output, result)
    print(f"Wrote de-identified trial records to {output}")
    return 0 if stop_reason == "completed" else 1


def main() -> int:
    args = parse_args()
    output = args.output.resolve() if args.output else default_output()
    if args.live:
        return live_run(args, output)
    return dry_run(args, output)


if __name__ == "__main__":
    raise SystemExit(main())
