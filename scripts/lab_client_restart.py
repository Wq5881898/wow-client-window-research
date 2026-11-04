"""Restart the game client so a dead character is restored by the server."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import win32con
import win32gui
import win32process
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
PYTHONW = r'C:\APP\Python\pythonw.exe'
# The launcher reads the display mode from this file: the client is in the
# fullscreen mode without it and in the window mode with it.
MODE_FLAG = ROOT / '.cache' / 'desktop-check' / 'windowed.flag'


def client_processes():
    """The number of running instances of the client.

    The output of tasklist is in the code page of the machine, so it is not
    decoded as text.
    """
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Wow.exe'],
                            capture_output=True)
    return result.stdout.count(b'Wow.exe')


def task_state():
    """The state of the task that starts the client."""
    command = ('(Get-ScheduledTask -TaskName %s -ErrorAction SilentlyContinue)'
               '.State' % RUN_TASK)
    result = subprocess.run(['powershell', '-NoProfile', '-Command', command],
                            capture_output=True, text=True)
    return result.stdout.strip()


def ensure_task():
    """Make sure the task that starts the client exists.

    The action of the task is the launcher, so the display mode is written
    before every start and the client keeps no console window that could
    cover the game.
    """
    if task_state():
        return 'present'
    action = ('"%s" -X utf8 "%s"' % (PYTHONW, ROOT / 'scripts' /
                                     'lab_client_launch.py'))
    subprocess.run(['schtasks', '/create', '/tn', RUN_TASK, '/tr', action,
                    '/sc', 'once', '/st', '00:00', '/f'],
                   capture_output=True)
    return 'created'


def start_client():
    """Start the client so that it outlives the task that starts it.

    A task that is still running refuses to start a second time, so the old
    one is ended first and the task is waited for. The client is started by
    the launcher, which writes the display mode and keeps the client as its
    own child.
    """
    ensure_task()
    for attempt in range(4):
        subprocess.run(['schtasks', '/end', '/tn', RUN_TASK], capture_output=True)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if task_state() == 'Ready':
                break
            time.sleep(1.0)
        # A second instance of the client only shows a dialog that there is
        # one already, and the game window of the real client is missing
        # then. Every old instance is ended before a new one is started.
        subprocess.run(['taskkill', '/IM', 'Wow.exe', '/F'], capture_output=True)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if not client_processes():
                break
            time.sleep(1.0)
        time.sleep(2.0)
        result = subprocess.run(['schtasks', '/run', '/tn', RUN_TASK],
                                capture_output=True)
        if result.returncode == 0:
            # The scheduler accepts the start of a task that is still busy
            # without an error, but the client does not come then. The
            # process is the proof that the task really did its work.
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                if client_processes():
                    return 'task'
                time.sleep(1.0)
    return 'failed'


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


def client_pids():
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Wow.exe'],
                            capture_output=True)
    pids = []
    for chunk in result.stdout.split(b'\r\n'):
        if b'Wow.exe' not in chunk or b'INFO' in chunk:
            continue
        try:
            pids.append(int(chunk.split()[1]))
        except Exception:
            pass
    return pids


def client_dialogs():
    """The modal dialogs of the client.

    A client that was killed leaves a dialog behind on the next start, and
    the game window does not come while the dialog is open.
    """
    pids = client_pids()
    found = []

    def cb(hwnd, _):
        try:
            if win32process.GetWindowThreadProcessId(hwnd)[1] not in pids:
                return True
            if win32gui.GetClassName(hwnd) != '#32770':
                return True
            texts = []
            win32gui.EnumChildWindows(
                hwnd,
                lambda child, _acc: texts.append(
                    (child, win32gui.GetClassName(child),
                     win32gui.GetWindowText(child))) or True,
                None)
            found.append({'hwnd': hwnd, 'text': win32gui.GetWindowText(hwnd),
                          'children': texts})
        except Exception:
            pass
        return True

    win32gui.EnumWindows(cb, None)
    return found


def dismiss_dialog(dialog):
    """Close a dialog of the client with its own buttons."""
    lines = []
    for child, cls, text in dialog['children']:
        lines.append('%s %r' % (cls, text))
    for child, cls, text in dialog['children']:
        if cls.lower().startswith('button') and text.strip():
            win32gui.PostMessage(child, 0x00F5, 0, 0)  # BM_CLICK
            lines.append('clicked %r' % text)
            return '\n'.join(lines)
    win32gui.PostMessage(dialog['hwnd'], win32con.WM_CLOSE, 0, 0)
    lines.append('closed the dialog')
    return '\n'.join(lines)


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
    wanted = 'SET gxWindow "%d"' % (0 if enabled else 1)
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

        wanted = '--window' not in sys.argv
        MODE_FLAG.parent.mkdir(parents=True, exist_ok=True)
        if wanted:
            MODE_FLAG.unlink(missing_ok=True)
        else:
            MODE_FLAG.write_text('windowed\n', encoding='utf-8')
        result['steps'].append({'phase': 'mode',
                                'fullscreen': wanted,
                                'config': set_fullscreen(wanted)})
        result['steps'].append({'phase': 'started',
                                'how': start_client()})
        deadline = time.monotonic() + 120
        hwnd = 0
        dialogs = []
        while time.monotonic() < deadline:
            time.sleep(3.0)
            hwnd = game_window()
            if hwnd:
                break
            for dialog in client_dialogs():
                report = dismiss_dialog(dialog)
                dialogs.append(report)
                result['steps'].append({'phase': 'dialog', 'report': report})
        result['steps'].append({'phase': 'dialogs', 'count': len(dialogs)})
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
