"""List nearby hostile units with their health, for picking a drill target."""
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
    run = 'client_scan_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', scans=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()

        def reader():
            return decode(assert_real_frame(grab_desktop()))

        names = ['Diseased Young Wolf', 'Wolf', 'Diseased Wolf', 'Wolf Pup',
                 'Old Wolf', 'Sickly Vulture', 'Carrion Vulture',
                 'Rotting Corpse', 'Gar在本']
        for name in names:
            if '在本' in name:
                continue
            d.post_key(hwnd, win32con.VK_RETURN)
            time.sleep(0.4)
            for character in '/target ' + name:
                win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
                time.sleep(0.03)
            time.sleep(0.3)
            d.post_key(hwnd, win32con.VK_RETURN)
            time.sleep(1.2)
            state = reader()
            scan = {'name': name, 'exists': state['target_exists'],
                    'attackable': state['target_attackable'],
                    'health': state['target_health'],
                    'guid': state['target_guid']}
            result['scans'].append(scan)
            print(scan, flush=True)
        evidence.capture('01-scan', reader())
        result['status'] = 'SCANNED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('02-end')
        path = evidence.write(result)
        d.log('scan run', path, result['status'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
