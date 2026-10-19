"""Close every WoW process and dialog from the interactive desktop session."""
import sys
import time

import win32con
import win32process
import win32gui

def close_dialogs():
    def cb(hwnd, _):
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        def child(child, _):
            text = win32gui.GetWindowText(child)
            if win32gui.GetClassName(child) == 'Button' and text in ('确定', 'OK'):
                win32gui.PostMessage(child, win32con.BM_CLICK, 0, 0)
                print(f'clicked {child} {text}')
            return True
        win32gui.EnumChildWindows(hwnd, child, None)
        return True
    win32gui.EnumWindows(cb, None)

def main():
    close_dialogs()
    time.sleep(1)
    for hwnd in [hwnd for hwnd in win32gui.EnumWindows(lambda h, _: h, None)]:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        title = win32gui.GetWindowText(hwnd)
        if title == 'World of Warcraft':
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            print(f'closed window {hwnd} pid {pid}')
    time.sleep(4)
    close_dialogs()
    return 0

if __name__ == '__main__':
    sys.exit(main())
