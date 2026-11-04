"""Write the windows of the client to a file.

The task runs without a console, so the report goes to a file.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32api
import win32gui
import win32process

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'


def main():
    lines = []
    pids = []
    import subprocess
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Wow.exe'],
                            capture_output=True)
    for chunk in result.stdout.split(b'\r\n'):
        if b'Wow.exe' in chunk and b'INFO' not in chunk:
            try:
                pids.append(int(chunk.split()[1]))
            except Exception:
                pass
    lines.append('client pids %s' % pids)

    def cb(hwnd, _):
        try:
            pid = win32process.GetWindowThreadProcessId(hwnd)[1]
        except Exception:
            return True
        if pid not in pids:
            return True
        try:
            lines.append('window %s class=%s text=%r rect=%s visible=%s' % (
                hwnd, win32gui.GetClassName(hwnd),
                win32gui.GetWindowText(hwnd), win32gui.GetWindowRect(hwnd),
                win32gui.IsWindowVisible(hwnd)))
        except Exception as exc:
            lines.append('window %s is gone: %r' % (hwnd, exc))
        return True

    win32gui.EnumWindows(cb, None)
    lines.append('desktop %s %s' % (win32api.GetSystemMetrics(0),
                                   win32api.GetSystemMetrics(1)))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'client-windows.txt').write_text('\n'.join(lines), encoding='utf-8')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        import traceback
        (OUT / 'client-windows.txt').write_text(
            traceback.format_exc(), encoding='utf-8')
        raise
