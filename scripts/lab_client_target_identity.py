"""Check whether the target identity check really detects a target switch.

The tab key cycles through the hostile units in view. The probe reports the
guid of the selected unit, so switching the target has to change it.
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
    run = 'client_target_identity_' + str(time.time_ns())
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

        for step in range(8):
            d.post_key(hwnd, win32con.VK_TAB)
            time.sleep(0.7)
            state = reader()
            sample = {'step': step, 'guid': state['target_guid'],
                      'health': state['target_health'],
                      'exists': state['target_exists'],
                      'attackable': state['target_attackable'],
                      'range': state['spell_range']}
            result['samples'].append(sample)
            print(sample, flush=True)
        result['status'] = 'SAMPLED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('01-end')
        path = evidence.write(result)
        d.log('target identity run', path, result['status'])
    return 0 if result['status'] == 'SAMPLED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
