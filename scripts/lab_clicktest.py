"""Session-2: click game window center, then screenshot, to test if mouse
clicks move the camera."""
import sys
import time
from pathlib import Path

import win32con
import win32gui

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import lab_driver5 as d5

hwnd = d5.find_game_window()
d5.log('=== clicktest hwnd', hwnd)
if hwnd:
    d5.ensure_foreground(hwnd)
    l, t, r, b = win32gui.GetClientRect(hwnd)
    d5.click_ui(hwnd, 512, 384)
    time.sleep(0.5)
    d5.click_ui(hwnd, 512, 384)
    time.sleep(1)
    d5.screenshot('wow-12-clicktest.png')
