"""Restart the game client so a dead character is restored by the server."""
import json
import os
import subprocess
import sys
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

# A process that is started by a scheduled task belongs to the job of that
# task. When the task ends, the job is closed and the client is killed with
# it. That is why the client left a few minutes after a restart. The flag
# takes the client out of the job; if the job does not allow that, a task of
# its own starts it and stays alive as long as the client runs.
DETACHED = 0x01000000
RUN_TASK = 'WowClientRun'


def start_client():
    """Start the client so that it outlives the task that starts it."""
    try:
        subprocess.Popen([str(EXE)], cwd=str(CLIENT),
                         creationflags=DETACHED)
        return 'detached'
    except Exception as exc:
        d.log('detached start failed', repr(exc))
    # A task that is still marked as running refuses to start a second
    # time, so the old one is removed first. The client needs its own
    # directory, otherwise it starts in the directory of the task and
    # leaves again right away.
    subprocess.run(['schtasks', '/delete', '/tn', RUN_TASK, '/f'],
                   capture_output=True)
    command = 'cmd /c cd /d "%s" && Wow.exe' % CLIENT
    subprocess.run(['schtasks', '/create', '/tn', RUN_TASK, '/tr', command,
                    '/sc', 'once', '/st', '00:00', '/f'],
                   capture_output=True)
    time.sleep(2.0)
    result = subprocess.run(['schtasks', '/run', '/tn', RUN_TASK],
                            capture_output=True)
    return 'task' if result.returncode == 0 else 'failed'


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


def set_fullscreen(enabled):
    """Switch the client between the fullscreen mode and the window mode.

    The client of the fullscreen mode is not exclusive: every other window
    covers it, and it shrinks its own window when it loses the focus. The
    window mode gives a window that can be raised, so the driver can always
    see and click the client.
    """
    path = CLIENT / 'WTF' / 'Config.wtf'
    text = path.read_text(encoding='utf-8', errors='replace')
    wanted = 'SET gxWindow "%d"' % (1 if enabled else 0)
    if wanted in text:
        return wanted
    lines = []
    replaced = False
    for line in text.splitlines():
        if line.startswith('SET gxWindow'):
            lines.append(wanted)
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        lines.append(wanted)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8', errors='replace')
    return wanted


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

        wanted = '--fullscreen' in sys.argv
        result['steps'].append({'phase': 'mode',
                                'fullscreen': wanted,
                                'config': set_fullscreen(wanted)})
        result['steps'].append({'phase': 'started',
                                'how': start_client()})
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
