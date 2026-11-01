"""Fight a weak target to the end and confirm the survival check.

The chicken of Goldshire has one health point, so the fight is one cast
long. The run has to observe the death, leave the fight and report the
survival of the character.
"""
import json
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_evidence import Evidence
from client_chat_guard import ensure_chat_closed, ensure_focus, close_world_map
from client_facing import CastProbe, sweep_toward

ROOT = Path(__file__).resolve().parents[1]
FIREBALL = 133
WALK = 0x57
TURN = 0x25
TURN_LEFT = 0x25


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


def hold(vk, seconds, hwnd=None):
    import ctypes
    if hwnd is not None:
        ensure_focus(hwnd)
    key = d.INPUT()
    key.type = 1
    key.union.ki = d.KEYBDINPUT(vk, 0, 0, 0, None)
    try:
        if d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key)) != 1:
            raise RuntimeError('key down failed')
        time.sleep(seconds)
    finally:
        key.union.ki.dwFlags = 2
        if d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key)) != 1:
            raise RuntimeError('key up failed')


def send(hwnd, text, reader, settle=0.8):
    ensure_chat_closed(hwnd, reader)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.4)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.04)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)
    return reader()


def main():
    run = 'client_chicken_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', timeline=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        def note(phase, detail):
            result['timeline'].append({'phase': phase,
                                       'host_monotonic': time.monotonic(),
                                       'detail': detail})

        close_world_map(hwnd, reader)
        state = reader()
        if state['dead']:
            raise ValueError('the character is a ghost')
        evidence.capture('01-start', state)
        note('baseline', {'health': state['health'],
                          'position': [state['pos_x'], state['pos_y']]})

        # The chicken has one health point, so one cast is enough.
        send(hwnd, '/target Chicken', reader, settle=1.2)
        state = reader()
        if not state['target_exists']:
            raise ValueError('no chicken in view')
        note('target', {'guid': state['target_guid'],
                        'health': state['target_health'],
                        'range': state['spell_range']})
        evidence.capture('02-target', state)

        # Walk into spell range.
        for _ in range(12):
            if state['spell_range'] == 1:
                break
            ensure_chat_closed(hwnd, reader)
            d.post_key(hwnd, win32con.VK_TAB)
            time.sleep(0.4)
            hold(WALK, 0.8, hwnd)
            state = reader()
        if state['spell_range'] != 1:
            raise ValueError('the chicken could not be reached')
        note('in_range', {'range': state['spell_range'],
                           'position': [state['pos_x'], state['pos_y']]})

        # The sweep turns until the spell lands.
        def attempt():
            send(hwnd, '/cast Fireball', reader, settle=1.2)
            return reader()

        probe = CastProbe(attempt, reader, FIREBALL, settle=0.4)
        steps, after = sweep_toward(probe, max_steps=16, hwnd=hwnd)
        note('cast', {'turn_steps': steps,
                      'target_health': after['target_health'],
                      'target_dead': after['target_dead'],
                      'target_exists': after['target_exists'],
                      'cast_succeeded': after['cast_succeeded']})
        evidence.capture('03-after-cast', after)
        if after['target_exists'] and not after['target_dead']:
            raise ValueError('the target is still alive')

        # The survival check: alive and out of combat for a while.
        quiet = 0
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            state = reader()
            if state['dead']:
                raise ValueError('the character died')
            if state['combat']:
                quiet = 0
            else:
                quiet += 1
                if quiet >= 6:
                    break
            time.sleep(0.4)
        if state['combat']:
            raise ValueError('still in combat at the end of the fight')
        note('survived', {'health': state['health'], 'combat': state['combat'],
                          'dead': state['dead']})
        evidence.capture('04-survived', state)
        result['outcome'] = 'target_defeated'
        result['status'] = 'FIGHT_COMPLETED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('05-end')
        path = evidence.write(result)
        d.log('chicken fight run', path, result['status'])
    return 0 if result['status'] == 'FIGHT_COMPLETED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
