"""Restart the game client so a dead character is restored by the server."""
import json
import os
import subprocess
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode
from client_evidence import Evidence

ROOT = Path(__file__).resolve().parents[1]
CLIENT = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a')
EXE = CLIENT / 'Wow.exe'


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


def game_window():
    found = []

    def cb(hwnd, _):
        if win32gui.GetClassName(hwnd) == 'GxWindowClassD3d':
            found.append(hwnd)
        return True
    win32gui.EnumWindows(cb, None)
    return found[0] if found else 0


def main():
    run = 'client_restart_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', steps=[])
    evidence = Evidence(run)
    try:
        hwnd = game_window()
        if hwnd:
            d.post_key(hwnd, win32con.VK_ESCAPE)
            time.sleep(0.6)
            d.post_key(hwnd, win32con.VK_ESCAPE)
            time.sleep(0.6)
            # The client is closed through its own menu so the session ends
            # cleanly and the server stores the character state.
            d.post_key(hwnd, win32con.VK_ESCAPE)
            time.sleep(0.8)
        # Fall back to terminating the process when the menu did not open.
        if game_window():
            subprocess.run(['taskkill', '/IM', 'Wow.exe', '/F'],
                           capture_output=True)
            time.sleep(4.0)
        result['steps'].append({'phase': 'closed'})

        subprocess.Popen([str(EXE)], cwd=str(CLIENT))
        deadline = time.monotonic() + 120
        hwnd = 0
        while time.monotonic() < deadline:
            time.sleep(3.0)
            hwnd = game_window()
            if hwnd:
                break
        if not hwnd:
            raise ValueError('the client window did not appear')
        result['steps'].append({'phase': 'window', 'hwnd': hwnd})
        time.sleep(25.0)
        evidence.capture('01-started')
        result['status'] = 'RESTARTED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        path = evidence.write(result)
        d.log('restart run', path, result['status'])
    return 0 if result['status'] == 'RESTARTED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
