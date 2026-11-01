"""List the top level windows of the interactive session."""
import json
from pathlib import Path
import win32gui

ROOT = Path(__file__).resolve().parents[1]
rows = []


def cb(hwnd, _):
    try:
        rows.append({'hwnd': hwnd, 'class': win32gui.GetClassName(hwnd),
                     'title': win32gui.GetWindowText(hwnd),
                     'visible': bool(win32gui.IsWindowVisible(hwnd)),
                     'rect': win32gui.GetWindowRect(hwnd),
                     'foreground': win32gui.GetForegroundWindow() == hwnd})
    except Exception as exc:
        rows.append({'error': repr(exc)})
    return True


win32gui.EnumWindows(cb, None)
out = ROOT / '.cache' / 'desktop-check' / 'windows.json'
out.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
print('wrote', out)
