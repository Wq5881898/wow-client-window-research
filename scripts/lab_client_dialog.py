"""Read the text of the dialog that blocks the client."""
import json
from pathlib import Path
import win32gui
import win32process

ROOT = Path(__file__).resolve().parents[1]


def collect(hwnd, depth=0, out=None):
    if out is None:
        out = []
    try:
        cls = win32gui.GetClassName(hwnd)
        title = win32gui.GetWindowText(hwnd)
    except Exception:
        return out
    if title:
        out.append(dict(hwnd=hwnd, depth=depth, cls=cls, title=title))
    for child in _children(hwnd):
        collect(child, depth + 1, out)
    return out


def _children(parent):
    result = []
    try:
        win32gui.EnumChildWindows(parent, lambda h, _: result.append(h) or True, None)
    except Exception:
        pass
    return result


rows = []


def cb(hwnd, _):
    try:
        cls = win32gui.GetClassName(hwnd)
        title = win32gui.GetWindowText(hwnd)
    except Exception:
        return True
    if cls == '#32770':
        rows.extend(collect(hwnd))
    return True


win32gui.EnumWindows(cb, None)
for row in rows:
    print(row)
(ROOT / '.cache' / 'desktop-check' / 'dialog.json').write_text(
    json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
