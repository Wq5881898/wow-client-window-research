"""Bring the client to the foreground and keep other windows out of the way."""
import time
import win32con
import win32gui
import lab_driver5 as d


def minimize_others(keep):
    """Hide every visible top-level window except the client.

    The scheduled task's own console is hidden too: it would otherwise cover
    the client and corrupt the pixel evidence.
    """
    hidden = []
    own = win32gui.GetConsoleWindow()
    def cb(hwnd, _):
        if hwnd == keep:
            return True
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        try:
            if cls == 'ConsoleWindowClass' or hwnd == own:
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            hidden.append((hwnd, cls, title))
        except Exception:
            pass
        return True
    win32gui.EnumWindows(cb, None)
    return hidden


def main():
    hwnd = d.find_game_window()
    if not hwnd:
        raise RuntimeError('no game window')
    hidden = minimize_others(hwnd)
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    time.sleep(0.4)
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, 1920, 1080, win32con.SWP_NOZORDER)
    time.sleep(0.8)
    d.ensure_foreground(hwnd)
    time.sleep(1.0)
    d.log('foregrounded', hwnd, 'foreground now', win32gui.GetForegroundWindow(),
          'minimized', len(hidden))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
