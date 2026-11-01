"""Report the state of the client window and the foreground window."""
import json
import time
from pathlib import Path
import win32gui
import lab_driver5 as d

ROOT = Path(__file__).resolve().parents[1]


def main():
    hwnd = d.find_game_window()
    rows = {'hwnd': hwnd}
    if hwnd:
        rows['foreground'] = win32gui.GetForegroundWindow()
        rows['is_foreground'] = win32gui.GetForegroundWindow() == hwnd
        rows['visible'] = bool(win32gui.IsWindowVisible(hwnd))
        rows['iconic'] = bool(win32gui.IsIconic(hwnd))
        rows['rect'] = win32gui.GetWindowRect(hwnd)
        rows['cursor'] = win32gui.GetCursorPos()
    rows['foreground_class'] = None
    rows['foreground_title'] = None
    foreground = win32gui.GetForegroundWindow()
    if foreground:
        rows['foreground_class'] = win32gui.GetClassName(foreground)
        rows['foreground_title'] = win32gui.GetWindowText(foreground)
    out = ROOT / '.cache' / 'desktop-check' / 'window-state.json'
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
    d.log('window state', str(out), 'ok')
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
