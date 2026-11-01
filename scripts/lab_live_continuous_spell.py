"""Non-combat cooperative chat input with uninterrupted capture/guard lifetime."""
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
from client_chat_sequence import ChatSequence, spell_result


def main():
    run = 'client_continuous_spell_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', samples=[], inputs=[])
    sequence = None
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        guard = ControlGuard()
        start = time.monotonic()
        before = None
        submitted_at = None
        while time.monotonic() - start < 15:
            image = assert_real_frame(ImageGrab.grab())
            now = time.monotonic()
            state = decode(image)
            decision = guard.observe(state, now, window_observable(hwnd))
            result['samples'].append(dict(host_monotonic=now, control=decision, **state))
            if decision['decision'] == 'RECOVERY_REQUIRED':
                raise ValueError(decision['reason'])
            if state['protocol'] != 2 or state['target_exists'] or state['speed'] != 0:
                raise ValueError('protocol 2, no target and stationary required')
            if sequence is None and now - start >= 2:
                if decision['decision'] != 'OBSERVE_ONLY':
                    raise ValueError('baseline not ready')
                before = state
                result['before'] = before
                sequence = ChatSequence('/cast Frost Armor', now)
            if sequence is not None:
                action = sequence.step(now, decision['decision'] == 'OBSERVE_ONLY')
                if action:
                    # Recheck focus immediately before the one external input operation.
                    if d.u.GetForegroundWindow() != hwnd:
                        raise ValueError('foreground lost before input')
                    kind, value = action
                    if kind == 'char':
                        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(value), 0)
                    else:
                        d.post_key(hwnd, value)
                    result['inputs'].append(dict(host_monotonic=now, kind=kind, value=value))
                if sequence.submitted:
                    if submitted_at is None:
                        submitted_at = now
                    outcome = spell_result(before, state, 168)
                    if outcome in ('FAILED', 'AMBIGUOUS'):
                        raise ValueError('spell outcome ' + outcome)
                    if now - submitted_at >= 4:
                        if outcome != 'SUCCEEDED' or not state['frost_armor']:
                            raise ValueError('success event and aura not confirmed')
                        result['after'] = state
                        result['status'] = 'CONTINUOUS_NONCOMBAT_SPELL_VERIFIED'
                        image.save(d.OUT / (run + '_verified.png'))
                        break
            time.sleep(.03)
        else:
            raise ValueError('overall timeout')
    except Exception as exc:
        if sequence:
            sequence.cancel()
        result['error'] = repr(exc)
        if hwnd:
            d.screenshot(run + '_failure.png')
    finally:
        rows = result['samples']
        result['max_capture_gap_seconds'] = max(
            (b['host_monotonic'] - a['host_monotonic'] for a, b in zip(rows, rows[1:])), default=0)
        path = Path(__file__).resolve().parents[1] / 'results' / (run + '.json')
        with path.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
    return 0 if result['status'] == 'CONTINUOUS_NONCOMBAT_SPELL_VERIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
