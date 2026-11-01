"""Report the game window geometry from inside the interactive session."""
import sys
import win32gui
import win32con


def main():
    def cb(hwnd, _):
        if win32gui.GetClassName(hwnd) == 'GxWindowClassD3d':
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            cl, ct, cr, cb_ = win32gui.GetClientRect(hwnd)
            print('window rect', (left, top, right, bottom))
            print('client size', (cr - cl, cb_ - ct))
            print('foreground', win32gui.GetForegroundWindow() == hwnd)
            print('cursor', win32gui.GetCursorPos())
        return True
    win32gui.EnumWindows(cb, None)
    return 0


if __name__ == '__main__':
    sys.exit(main())
