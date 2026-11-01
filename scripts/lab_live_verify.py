"""Bounded non-combat live capture and self-target/clear acceptance."""
import json
import time
from pathlib import Path
from PIL import ImageGrab
import lab_driver5 as d
from lab_distance_scenarios import command
from client_live_state import decode, Freshness, assert_real_frame
from client_control_guard import ControlGuard
from client_window_state import window_observable

ROOT = Path(__file__).resolve().parents[1]


def main():
    run = 'client_live_' + str(time.time_ns())
    rows = []
    result = {'run': run, 'status': 'FAILED', 'samples': rows}
    hwnd = d.find_game_window()
    if not hwnd:
        raise RuntimeError('no game window')
    d.ensure_foreground(hwnd)

    def capture(phase, duration=3):
        tracker = Freshness()
        guard = ControlGuard()
        end = time.monotonic() + duration
        last = None
        while time.monotonic() < end:
            start = time.monotonic()
            if not window_observable(hwnd):
                raise ValueError('client window not observable')
            image = assert_real_frame(ImageGrab.grab())
            try:
                state = decode(image)
            except ValueError:
                image.save(d.OUT / (run + '_decode_failure.png'))
                raise
            if state['dead'] or state['combat'] or state['health'] != state['max_health']:
                raise ValueError('unsafe non-combat baseline')
            live = tracker.observe(state)
            decision = guard.observe(state, time.monotonic())
            if decision['decision'] == 'RECOVERY_REQUIRED':
                raise ValueError(decision['reason'])
            row = dict(phase=phase, host_monotonic=time.monotonic(),
                       capture_decode_ms=(time.monotonic() - start) * 1000,
                       live=live, control=decision, **state)
            rows.append(row)
            last = state
            time.sleep(0.05)
        if not any(row['live'] for row in rows if row['phase'] == phase):
            raise ValueError('heartbeat did not advance')
        image.save(d.OUT / (run + '_' + phase + '.png'))
        return last

    try:
        before = capture('baseline')
        if before['target_exists']:
            raise ValueError('baseline target not empty')
        command(hwnd, '/targetexact Probehuman')
        target = capture('self_target')
        if not target['target_exists'] or target['target_guid'] == '0x0000000000000000':
            raise ValueError('self target absent')
        if target['target_attackable'] or target['target_health'] != target['health']:
            raise ValueError('unexpected self target state')
        command(hwnd, '/cleartarget')
        after = capture('cleared')
        if after['target_exists']:
            raise ValueError('target not cleared')
        frozen = Freshness()
        frozen.observe(after, now=0)
        try:
            frozen.observe(after, now=1.01)
        except ValueError:
            result['frozen_frame_rejected'] = True
        else:
            raise ValueError('frozen frame accepted')
        try:
            decode(ImageGrab.grab().crop((900, 400, 1200, 700)))
        except ValueError:
            result['missing_panel_rejected'] = True
        else:
            raise ValueError('missing panel accepted')
        result['status'] = 'LIVE_NONCOMBAT_VERIFIED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        path = ROOT / 'results' / (run + '.json')
        with path.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
        d.log('live verification', path, result['status'])
    return 0 if result['status'] == 'LIVE_NONCOMBAT_VERIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
