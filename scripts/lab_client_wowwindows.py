"""List every window that belongs to the client process, including children."""
import json
from pathlib import Path
import win32gui
import win32process

ROOT = Path(__file__).resolve().parents[1]
import subprocess

out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Wow.exe', '/FO', 'CSV'],
                     capture_output=True, text=True, encoding='gbk', errors='replace')
pids = [int(line.split(',')[1].strip('"'))
        for line in out.stdout.splitlines() if line.startswith('"Wow.exe"')]
print('pids', pids)

rows = []


def cb(hwnd, _):
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
    except Exception:
        return True
    if pid in pids:
        try:
            rows.append(dict(hwnd=hwnd, pid=pid,
                             cls=win32gui.GetClassName(hwnd),
                             title=win32gui.GetWindowText(hwnd),
                             visible=bool(win32gui.IsWindowVisible(hwnd))))
        except Exception:
            pass
    return True


win32gui.EnumWindows(cb, None)
print('top level windows of the client:', rows)

child = []


def cb2(hwnd, _):
    try:
        parent = win32gui.GetParent(hwnd)
    except Exception:
        return True
    if parent and any(r['hwnd'] == parent for r in rows):
        child.append((parent, hwnd, win32gui.GetClassName(hwnd),
                      win32gui.GetWindowText(hwnd)))
    return True


win32gui.EnumWindows(cb2, None)
print('children:', child)

(ROOT / '.cache' / 'desktop-check').mkdir(parents=True, exist_ok=True)
(ROOT / '.cache' / 'desktop-check' / 'wow-windows.json').write_text(
    json.dumps(dict(pids=pids, windows=rows, children=child), indent=2),
    encoding='utf-8')
