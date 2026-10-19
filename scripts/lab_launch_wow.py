"""Launch WoW in the interactive console session and capture the result."""
import json
import subprocess
import sys
import time
from pathlib import Path

import win32api
import win32gui
import win32process

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'
OUT.mkdir(parents=True, exist_ok=True)
GAME = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a')

args = sys.argv[1:]
proc = subprocess.Popen([str(GAME / 'Wow.exe')] + args, cwd=str(GAME))
result = {'pid': proc.pid, 'args': args}
time.sleep(25)

# Enumerate windows of the game
wins = []
def cb(hwnd, _):
    _, p = win32process.GetWindowThreadProcessId(hwnd)
    if p == proc.pid:
        wins.append({
            'hwnd': hwnd,
            'title': win32gui.GetWindowText(hwnd),
            'visible': bool(win32gui.IsWindowVisible(hwnd)),
            'class': win32gui.GetClassName(hwnd),
        })
    return True
win32gui.EnumWindows(cb, None)
result['windows'] = wins

# Check if process is still alive
result['alive'] = proc.poll() is None
if not result['alive']:
    result['returncode'] = proc.returncode

(OUT / 'launch-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
