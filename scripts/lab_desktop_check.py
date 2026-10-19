"""Run through an interactive scheduled task to inspect desktop display state."""
import json
import os
import time
import sys
import subprocess
from pathlib import Path

import win32api
import win32gui
from PIL import ImageGrab

out = Path(__file__).resolve().parents[1] / '.cache' / 'desktop-check'
if '--wait' in sys.argv:
    time.sleep(12)
out.mkdir(parents=True, exist_ok=True)
result = {'pid': os.getpid(), 'remote_session': win32api.GetSystemMetrics(0x1000), 'displays': [], 'windows': []}
try:
    for i in range(256):
        try:
            d = win32api.EnumDisplayDevices(None, i)
        except Exception:
            break
        result['displays'].append({'name': d.DeviceName, 'description': d.DeviceString,
                                   'flags': d.StateFlags})
    def window(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            result['windows'].append({'hwnd': hwnd, 'title': win32gui.GetWindowText(hwnd)})
    win32gui.EnumWindows(window, None)
    ImageGrab.grab().save(out / 'desktop.png')
    result['screenshot'] = 'ok'
    if '--launch' in sys.argv and result.get('remote_session') == 0:
        game = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a')
        process = subprocess.Popen([str(game / 'Wow.exe'), '-windowed', '-noip', '-gfxwindow'], cwd=str(game))
        result['game_pid'] = process.pid
except Exception as exc:
    result['error'] = str(exc)
(out / 'status.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
