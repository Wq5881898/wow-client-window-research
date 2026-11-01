"""Select the next hostile creature and report its classification."""
import json
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_evidence import Evidence
from client_chat_guard import ensure_chat_closed, close_world_map

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
    run = 'client_pick_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', picks=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        close_world_map(hwnd, reader)
        for step in range(12):
            ensure_chat_closed(hwnd, reader)
            d.post_key(hwnd, win32con.VK_TAB)
            time.sleep(0.7)
            state = reader()
            pick = {'step': step, 'guid': state['target_guid'],
                    'health': state['target_health'],
                    'class_id': state.get('target_class'),
                    'class': state.get('target_class_name'),
                    'range': state['spell_range'],
                    'exists': state['target_exists']}
            result['picks'].append(pick)
            print(pick, flush=True)
            if state['target_exists']:
                evidence.capture('01-picked', state)
                result['status'] = 'PICKED'
                break
        if result['status'] != 'PICKED':
            raise ValueError('no hostile could be selected')
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('02-end')
        path = evidence.write(result)
        d.log('pick run', path, result['status'])
    return 0 if result['status'] == 'PICKED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
