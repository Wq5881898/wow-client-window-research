"""Locate the graveyard release point from the minimap and use it.

The minimap carries a yellow exclamation mark for the nearby resurrection
NPC. Clicking it turns the camera to that marker, which makes the world
click position of the NPC known.
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
MINIMAP_MARK = (1771, 150)
GRAVEYARD_MARK = (1834, 166)
ACCEPT_BUTTON = (960, 252)


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


def main():
    run = 'client_minimap_nav_' + str(time.time_ns())
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
        result['start'] = {'health': state['health'], 'dead': state['dead']}
        if not state['dead']:
            result['status'] = 'ALREADY_ALIVE'
            return 0

        for _ in range(4):
            # The minimap marker turns the camera onto the target.
            d.click_si(*MINIMAP_MARK)
            time.sleep(1.2)
            evidence.capture('01-camera-turned')
            # The dialog of the release point is accepted in the middle of
            # the screen.
            d.click_si(*ACCEPT_BUTTON)
            time.sleep(1.2)
            try:
                state = reader()
            except ValueError:
                result['attempts'].append({'error': 'decode failed'})
                continue
            result['attempts'].append({'dead': state['dead'],
                                       'health': state['health']})
            if not state['dead']:
                result['status'] = 'RESURRECTED'
                evidence.capture('02-resurrected', state)
                break
        if result['status'] != 'RESURRECTED':
            # The release point is the graveyard marker on the minimap.
            for _ in range(4):
                d.click_si(*GRAVEYARD_MARK)
                time.sleep(1.2)
                d.click_si(*ACCEPT_BUTTON)
                time.sleep(1.2)
                try:
                    state = reader()
                except ValueError:
                    continue
                result['attempts'].append({'mark': 'graveyard',
                                           'dead': state['dead'],
                                           'health': state['health']})
                if not state['dead']:
                    result['status'] = 'RESURRECTED'
                    evidence.capture('02-resurrected', state)
                    break
        if result['status'] != 'RESURRECTED':
            raise ValueError('the release point did not revive the character')
        result['final'] = state
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('minimap nav run', path, result['status'])
    return 0 if result['status'] in ('RESURRECTED', 'ALREADY_ALIVE') else 1


if __name__ == '__main__':
    raise SystemExit(main())
