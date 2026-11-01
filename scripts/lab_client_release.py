"""Walk the ghost to the graveyard release point.

The character is a ghost at a graveyard. Releasing the spirit means walking
to the graveyard release point, where the client offers the resurrect dialog.
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
ACCEPT_BUTTON = (960, 252)
VK_FORWARD = 0x57
VK_TURN_LEFT = 0x25


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
        if d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key)) != 1:
            raise RuntimeError('key down failed')
        time.sleep(seconds)
    finally:
        key.union.ki.dwFlags = 2
        if d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key)) != 1:
            raise RuntimeError('key up failed')


def main():
    run = 'client_release_' + str(time.time_ns())
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

        state = reader()
        result['start'] = {'health': state['health'], 'dead': state['dead'],
                           'position': [state['pos_x'], state['pos_y']]}
        evidence.capture('01-start', state)
        if not state['dead']:
            result['status'] = 'ALREADY_ALIVE'
            return 0

        previous = (state['pos_x'], state['pos_y'])
        for step in range(16):
            # Walk in a slow spiral: the graveyard release point is close,
            # but there is no facing readout to aim at it.
            hold(VK_TURN_LEFT, 0.35)
            hold(VK_FORWARD, 0.9)
            time.sleep(0.4)
            try:
                state = reader()
            except ValueError:
                continue
            position = (state['pos_x'], state['pos_y'])
            moved = position != previous
            previous = position
            # The dialog is offered as soon as the ghost reaches the point.
            d.click_si(*ACCEPT_BUTTON)
            time.sleep(0.8)
            try:
                state = reader()
            except ValueError:
                continue
            result['attempts'].append({'step': step, 'moved': moved,
                                       'position': list(position),
                                       'dead': state['dead'],
                                       'health': state['health']})
            if not state['dead']:
                result['status'] = 'RESURRECTED'
                evidence.capture('02-resurrected', state)
                break
        if result['status'] != 'RESURRECTED':
            raise ValueError('the ghost did not reach a release point')
        result['final'] = state
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('release run', path, result['status'])
    return 0 if result['status'] in ('RESURRECTED', 'ALREADY_ALIVE') else 1


if __name__ == '__main__':
    raise SystemExit(main())
