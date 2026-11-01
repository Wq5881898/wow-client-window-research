"""Bring the character out of combat and back to a safe baseline.

Handles the ghost state as well: a dead character cannot walk away from the
creature that killed it, so the release button is pressed first.
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

ROOT = Path(__file__).resolve().parents[1]
RESURRECT = (960, 252)
# At a graveyard the ghost waits for the resurrection NPC instead of showing
# the "Resurrect now?" dialog. Right clicking the NPC opens a menu whose
# "Accept Resurrect" entry revives the character on the spot.
GRAVEYARD_NPC = (200, 142)
ACCEPT_RESURRECT = (203, 192)
VK_FORWARD = 0x57
VK_TURN_LEFT = 0x25
MAX_HOLD = 2.0


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


def main():
    run = 'client_safe_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', steps=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        state = reader()
        evidence.capture('01-start', state)
        result['start'] = {'health': state['health'], 'dead': state['dead'],
                           'combat': state['combat'],
                           'position': [state['pos_x'], state['pos_y']]}

        if state['dead']:
            # Close a menu that may still be open from an earlier attempt.
            d.post_key(hwnd, win32con.VK_ESCAPE)
            time.sleep(0.5)
            # A ghost cannot run away, so the release comes first. Two
            # layouts exist: outside a graveyard the client shows a
            # "Resurrect now?" dialog, at a graveyard the ghost waits for
            # the resurrection NPC. The dialog is tried first, then the NPC
            # menu is used.
            deadline = time.monotonic() + 90
            released = False
            attempts = 0
            while time.monotonic() < deadline:
                if attempts % 4 == 3:
                    # Select the resurrection NPC, open its menu and pick
                    # "Accept Resurrect".
                    d.click_si(*GRAVEYARD_NPC)
                    time.sleep(0.4)
                    d.right_click(*GRAVEYARD_NPC)
                    time.sleep(0.6)
                    d.click_si(*ACCEPT_RESURRECT)
                else:
                    d.click_si(*RESURRECT)
                attempts += 1
                time.sleep(1.5)
                try:
                    state = reader()
                except ValueError:
                    continue
                if not state['dead']:
                    released = True
                    break
            evidence.capture('02-resurrected', state)
            if not released:
                raise ValueError('still a ghost after release')
            result['resurrected'] = {'health': state['health'],
                                     'attempts': attempts,
                                     'position': [state['pos_x'], state['pos_y']]}

        # Turn and run repeatedly: a chasing mob follows the old heading.
        for attempt in range(12):
            hold(VK_TURN_LEFT, 0.4)
            hold(VK_FORWARD, MAX_HOLD)
            time.sleep(0.3)
            state = reader()
            result['steps'].append({'attempt': attempt, 'health': state['health'],
                                    'combat': state['combat'],
                                    'dead': state['dead'],
                                    'position': [state['pos_x'], state['pos_y']]})
            if not state['combat'] and not state['dead']:
                break
        evidence.capture('03-after-escape', state)
        if state['dead']:
            raise ValueError('character died during the escape')
        if state['combat']:
            raise ValueError('still in combat after the escape routine')
        result['status'] = 'SAFE'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('04-end')
        path = evidence.write(result)
        d.log('safe run', path, result['status'])
    return 0 if result['status'] == 'SAFE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
