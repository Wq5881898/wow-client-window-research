"""Check whether the client is still alive and responsive.

The driver distinguishes a frozen client from a driver that is blocked for
another reason. The probe of the client updates its sequence number on every
frame, so a growing sequence means the client is running, and a stalled
one means it is not.
"""
import json
import time
from pathlib import Path
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame

ROOT = Path(__file__).resolve().parents[1]


def main():
    samples = []
    for index in range(12):
        started = time.monotonic()
        try:
            state = decode(assert_real_frame(grab_desktop()))
            samples.append({
                'index': index,
                'sequence': state['sequence'],
                'game_ms': state['game_ms'],
                'health': state['health'],
                'dead': state['dead'],
                'combat': state['combat'],
                'target_exists': state['target_exists'],
                'decode_seconds': round(time.monotonic() - started, 3),
                'error': None,
            })
        except Exception as exc:
            samples.append({'index': index, 'error': repr(exc),
                            'decode_seconds': round(time.monotonic() - started, 3)})
        time.sleep(0.5)
    out = ROOT / '.cache' / 'desktop-check' / 'liveness.json'
    out.write_text(json.dumps(samples, indent=2), encoding='utf-8')
    d.log('liveness report', str(out), 'ok')
    print(json.dumps(samples, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
