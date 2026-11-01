"""Non-combat verification of the v3 telemetry: protocol, events and aura.

The chat request is typed step by step while capture continues, so the
heartbeat never sees a gap long enough to look stale.
"""
import json
import time
from pathlib import Path
from PIL import ImageGrab
import win32gui
import win32con
import lab_driver5 as d
from client_live_state import decode, assert_real_frame
from client_control_guard import ControlGuard
from client_window_state import window_observable
from client_chat_sequence import ChatSequence

ROOT = Path(__file__).resolve().parents[1]
SPELL = 168


def main():
    run = 'client_live_v3_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', samples=[], inputs=[])
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        guard = ControlGuard()
        sequence = None
        before = None
        submitted_at = None
        start = time.monotonic()

        while time.monotonic() - start < 20:
            now = time.monotonic()
            image = assert_real_frame(ImageGrab.grab())
            state = decode(image)
            decision = guard.observe(state, now, window_observable(hwnd))
            if decision['decision'] == 'RECOVERY_REQUIRED':
                raise ValueError(decision['reason'])
            result['samples'].append(dict(host_monotonic=now, control=decision, **state))

            if sequence is None:
                if now - start < 2:
                    time.sleep(.03)
                    continue
                if state['protocol'] != 3:
                    raise ValueError('expected protocol 3, got ' + str(state['protocol']))
                if state['combat'] or state['dead'] or state['target_exists']:
                    raise ValueError('non-combat baseline required')
                if not state['pos_x'] or not state['pos_y']:
                    raise ValueError('position fields not decoded')
                before = state
                result['before'] = before
                sequence = ChatSequence('/cast Frost Armor', now)

            action = sequence.step(now, decision['decision'] == 'OBSERVE_ONLY')
            if action:
                if not window_observable(hwnd):
                    raise ValueError('client window not observable before input')
                kind, value = action
                if kind == 'char':
                    win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(value), 0)
                else:
                    d.post_key(hwnd, value)
                result['inputs'].append(dict(host_monotonic=now, kind=kind, value=value))

            if sequence.submitted:
                if submitted_at is None:
                    submitted_at = now
                if now - submitted_at >= 3:
                    after = state
                    result['after'] = after
                    if (after['cast_succeeded'] - before['cast_succeeded']) % 65536 != 1:
                        raise ValueError('expected exactly one success event')
                    if after['cast_failed'] != before['cast_failed']:
                        raise ValueError('cast failure observed')
                    if after['ui_errors'] != before['ui_errors']:
                        raise ValueError('UI error observed')
                    if after['event_kind'] != 2 or after['event_spell'] != SPELL:
                        raise ValueError('event kind/spell mismatch')
                    if not after['frost_armor']:
                        raise ValueError('Frost Armor aura not confirmed')
                    queued = [event for event in after['events'] if event['serial']]
                    if not queued:
                        raise ValueError('event queue empty')
                    if queued[-1]['kind'] != 2 or queued[-1]['spell'] != SPELL:
                        raise ValueError('queue head mismatch')
                    if queued[-1]['at'] != after['event_ms']:
                        raise ValueError('queue timestamp mismatch')
                    result['queued'] = queued
                    result['status'] = 'LIVE_V3_NONCOMBAT_VERIFIED'
                    break
            time.sleep(.03)
        else:
            raise ValueError('overall timeout')
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        rows = result['samples']
        result['max_capture_gap_seconds'] = max(
            (b['host_monotonic'] - a['host_monotonic'] for a, b in zip(rows, rows[1:])),
            default=0)
        path = ROOT / 'results' / (run + '.json')
        with path.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
    return 0 if result['status'] == 'LIVE_V3_NONCOMBAT_VERIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
