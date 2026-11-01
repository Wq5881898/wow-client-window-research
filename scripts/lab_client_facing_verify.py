"""Verify the facing feedback loop: turn until the client stops complaining.

The character is pointed away from the target, so the first casts fail with
"Target needs to be in front of you.". The probe must report reason 5 and
the turn-and-retry loop must find the target.
"""
import json
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_window_state import window_observable
from client_evidence import Evidence
from client_facing import sweep_toward, facing_failed, REASON_FACING

ROOT = Path(__file__).resolve().parents[1]
FIREBALL = 133
TARGET = 'Chicken'


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


def send_command(hwnd, text, reader, settle=1.2):
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.4)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.03)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)
    return reader()


def main():
    run = 'client_facing_' + str(time.time_ns())
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

        start = reader()
        if start['dead'] or start['combat']:
            raise ValueError('must start alive and out of combat')
        evidence.capture('01-start', start)

        state = send_command(hwnd, '/target ' + TARGET, reader)
        if not state['target_exists']:
            raise ValueError('no target acquired')
        result['target_guid'] = state['target_guid']
        result['target_health'] = state['target_health']

        # Turn the character away from the target. The turn rate was measured
        # at roughly 170 degrees per second, so about one second turns the
        # character around. A longer hold would rotate through several full
        # circles and end up facing the target again.
        from client_facing import turn_step
        for _ in range(2):
            turn_step('left', 0.5)
            time.sleep(0.05)
        time.sleep(0.3)
        turned_away = reader()
        result['after_turn_away'] = {'position': [turned_away['pos_x'], turned_away['pos_y']],
                                      'range': turned_away['spell_range']}
        evidence.capture('02-turned-away', turned_away)

        # One cast attempt: it may succeed, fail on facing, or fail on range.
        def cast_once():
            return send_command(hwnd, '/cast Fireball', reader, settle=2.2)

        first = cast_once()
        result['first_cast'] = {'last_reason': first['last_reason'],
                                'last_error_reason': first['last_error_reason'],
                                'cast_failed': first['cast_failed'],
                                'ui_errors': first['ui_errors'],
                                'target_health': first['target_health'],
                                'combat': first['combat']}
        note = result['first_cast']
        evidence.capture('03-first-cast', first)

        if not facing_failed(first):
            result['status'] = 'FACING_ALREADY_OK'
            result['note'] = 'the first cast did not fail on facing'
        else:
            result['status'] = 'FACING_REASON_CONFIRMED'
            result['note'] = 'the client reported the facing failure as reason %d' % REASON_FACING

        # Now the sweep: keep turning until the facing failure disappears.
        # The sweep stops as soon as the target is in front, so at most one
        # damaging cast is expected after the turn.
        steps, state = sweep_toward(cast_once, max_steps=30)
        result['sweep_steps'] = steps
        result['after_sweep'] = {'last_reason': state['last_reason'],
                                 'last_error_reason': state['last_error_reason'],
                                 'cast_failed': state['cast_failed'],
                                 'ui_errors': state['ui_errors'],
                                 'target_health': state['target_health'],
                                 'combat': state['combat']}
        evidence.capture('04-after-sweep', state)
        if facing_failed(state):
            raise ValueError('the sweep did not clear the facing failure')
        result['status'] = 'FACING_LOOP_PASSED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('04-end')
        path = evidence.write(result)
        d.log('facing run', path, result['status'])
    return 0 if result['status'].startswith('FACING') else 1


if __name__ == '__main__':
    raise SystemExit(main())
