"""Test whether Frost Armor lets the fight outpace the regeneration.

Frost Armor slows the attacker of the character and, in this client, the
chilling effect also slows the creature that is hit by frost spells. If the
target moves slowly it stays in combat longer, which gives the slow fireball
a chance to finish it before the regeneration.
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
from client_facing import CastProbe, sweep_toward

ROOT = Path(__file__).resolve().parents[1]
WALK = 0x57
TURN = 0x25


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


def hold(vk, seconds):
    import ctypes
    key = d.INPUT()
    key.type = 1
    key.union.ki = d.KEYBDINPUT(vk, 0, 0, 0, None)
    try:
        d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key))
        time.sleep(seconds)
    finally:
        key.union.ki.dwFlags = 2
        d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key))


def send(hwnd, text, settle=0.8):
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.4)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.04)
    time.sleep(0.2)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(settle)


def main():
    run = 'client_frost_armor_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', samples=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        # Find a hostile and get in range.
        state = None
        for _ in range(16):
            d.post_key(hwnd, win32con.VK_TAB)
            time.sleep(0.6)
            candidate = reader()
            if candidate['target_exists'] and candidate['target_attackable']:
                state = candidate
                break
            hold(WALK, 1.6)
            hold(TURN, 0.35)
        if state is None:
            raise ValueError('no hostile in view')
        for _ in range(12):
            if state['spell_range'] == 1:
                break
            d.post_key(hwnd, win32con.VK_TAB)
            time.sleep(0.4)
            hold(WALK, 0.8)
            state = reader()
        if state['spell_range'] != 1:
            raise ValueError('the target could not be reached')
        result['target'] = {'guid': state['target_guid'],
                            'health': state['target_health']}
        evidence.capture('01-target', state)

        # Put the armour up before the fight.
        send(hwnd, '/cast Frost Armor', settle=2.0)
        state = reader()
        result['frost_armor'] = state['frost_armor']
        evidence.capture('02-armour', state)
        if not state['frost_armor']:
            raise ValueError('Frost Armor did not apply')

        # Now the fight: the sweep turns until the spell lands, and the
        # health of the target is sampled all the way.
        started = time.monotonic()
        lowest = state['target_health']
        while time.monotonic() - started < 40:
            def attempt():
                send(hwnd, '/cast Fireball', settle=1.0)
                return reader()
            probe = CastProbe(attempt, reader, 133, settle=0.4)
            steps, after = sweep_toward(probe, max_steps=8)
            lowest = min(lowest, after['target_health'])
            result['samples'].append({
                'elapsed': round(time.monotonic() - started, 2),
                'health': after['target_health'],
                'lowest': lowest,
                'dead': after['target_dead'],
                'exists': after['target_exists'],
                'combat': after['combat'],
                'turn_steps': steps,
                'cast_succeeded': after['cast_succeeded'],
            })
            if after['target_dead'] or not after['target_exists']:
                result['killed'] = True
                break
        result['lowest_health'] = lowest
        result['status'] = 'MEASURED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('frost armor run', path, result['status'])
    return 0 if result['status'] == 'MEASURED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
