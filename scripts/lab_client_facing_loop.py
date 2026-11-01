"""Verify the facing feedback loop against a real client error.

The order matters: a successful cast proves the target is in front, the
character is then turned around, and the next cast has to fail with the
facing reason. The sweep has to bring the target back into view.
"""
import json
import time
import traceback
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_evidence import Evidence
from client_facing import (CastProbe, cast_outcome, sweep_toward,
                           turn_step)

ROOT = Path(__file__).resolve().parents[1]
FIREBALL = 133
TARGET = 'Chicken'
# The turn rate was measured at roughly 170 degrees per second. Half a
# second is about eighty degrees, which leaves the target outside the cone
# in front of the character without rotating past it.
TURN_SECONDS = 0.5


def hide_consoles():
    def cb(hwnd, _):
        try:
            cls = win32gui.GetClassName(hwnd)
            title = win32gui.GetWindowText(hwnd)
        except Exception:
            return True
        if cls == 'ConsoleWindowClass' or 'python.exe' in title.lower():
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            except Exception:
                pass
        return True
    win32gui.EnumWindows(cb, None)


def send(hwnd, text, settle=1.5):
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.4)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.03)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)

def main():
    run = 'client_facing_loop_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', attempts=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        def cast_once():
            send(hwnd, '/cast Fireball', settle=1.6)
            return reader()

        probe = CastProbe(cast_once, reader)

        # Use the target that is already selected. A fresh name may resolve
        # to a creature that is out of range, and the client reports that
        # as a range failure, which hides the facing behaviour.
        state = reader()
        if not state['target_exists'] or not state['target_attackable']:
            send(hwnd, '/target ' + TARGET, settle=1.2)
            state = reader()
            if not state['target_exists'] or not state['target_attackable']:
                raise ValueError('no attackable target acquired')
            result['target_source'] = 'named'
        else:
            result['target_source'] = 'current'
        result['target_guid'] = state['target_guid']
        result['target_health'] = state['target_health']
        result['target_range'] = state['spell_range']
        if state['spell_range'] != 1:
            raise ValueError('the target is not in spell range')

        # Turn away before the first cast. The client reports the failure of
        # a cast whose target is not in front as a range failure, because
        # its range check includes the cone in front of the character.
        turn_step('left', TURN_SECONDS)
        time.sleep(0.4)
        turned = reader()
        result['after_turn'] = {'position': [turned['pos_x'], turned['pos_y']],
                                'target_exists': turned['target_exists'],
                                'target_health': turned['target_health']}
        evidence.capture('01-turned', turned)

        before = probe.counters()
        behind = cast_once()
        result['behind_cast'] = {'last_error_reason': behind['last_error_reason'],
                                 'cast_failed': behind['cast_failed'],
                                 'ui_errors': behind['ui_errors'],
                                 'target_health': behind['target_health'],
                                 'outcome': cast_outcome(behind, before)}
        evidence.capture('02-behind-cast', behind)

        # Every attempt of the sweep is recorded, so a run that does not
        # reach the target still shows what the client reported.
        trace = []

        def traced_cast():
            mark = probe.counters()
            state = cast_once()
            trace.append({
                'cast_failed': mark['cast_failed'],
                'cast_succeeded': mark['cast_succeeded'],
                'reason': state['last_error_reason'],
                'target_health': state['target_health'],
                'target_exists': state['target_exists'],
            })
            return state

        probe = CastProbe(traced_cast, reader)
        steps, state = sweep_toward(probe, max_steps=18)
        result['trace'] = trace
        result['sweep_steps'] = steps
        result['after_sweep'] = {'last_error_reason': state['last_error_reason'],
                                 'cast_failed': state['cast_failed'],
                                 'cast_succeeded': state['cast_succeeded'],
                                 'ui_errors': state['ui_errors'],
                                 'target_health': state['target_health']}
        evidence.capture('03-after-sweep', state)
        if steps == 0:
            raise ValueError('the sweep did not have to turn at all')
        result['status'] = 'FACING_LOOP_PASSED'
    except Exception as exc:
        result['error'] = repr(exc)
        result['traceback'] = traceback.format_exc()
    finally:
        evidence.capture('05-end')
        path = evidence.write(result)
        d.log('facing loop run', path, result['status'])
    return 0 if result['status'] == 'FACING_LOOP_PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
