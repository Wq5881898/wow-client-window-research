"""Measure the direction of the walk for several headings.

The heading of the client is given in radians and the position in the
normalised map coordinates of the zone. The script turns the character to a
series of headings, walks a short distance at each of them and prints the
step that followed. The table tells how the heading and the map coordinates
belong together, without assuming anything about the axes.

Nothing else may run while this script runs: another script that hides its
console takes the focus away from the client and the keys are lost.
"""
import ctypes
import math
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame

VK_FORWARD = 0x57
VK_LEFT = 0x25
VK_RIGHT = 0x27
TURN_RATE = math.pi


def hide_consoles():
    def cb(hwnd, _):
        try:
            cls = win32gui.GetClassName(hwnd)
            title = win32gui.GetWindowText(hwnd)
        except Exception:
            return True
        if cls == 'ConsoleWindowClass' or 'python.exe' in title.lower():
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            except Exception:
                pass
        return True
    win32gui.EnumWindows(cb, None)


def read_state():
    for _ in range(8):
        try:
            return decode(assert_real_frame(grab_desktop()))
        except Exception:
            time.sleep(1.0)
    raise SystemExit('no telemetry')


def hold(vk, seconds, hwnd):
    d.ensure_foreground(hwnd)
    time.sleep(0.15)
    key = d.INPUT()
    key.type = 1
    key.union.ki = d.KEYBDINPUT(vk, 0, 0, 0, None)
    if d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key)) != 1:
        raise RuntimeError('key down failed')
    try:
        time.sleep(seconds)
    finally:
        key.union.ki.dwFlags = 2
        d.SendInput(1, ctypes.byref(key), ctypes.sizeof(key))
    time.sleep(0.3)


def wrap(angle):
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


hwnd = d.find_game_window()
if not hwnd:
    raise SystemExit('no game window')
hide_consoles()
d.ensure_foreground(hwnd)

print('heading  dx        dy        step      angle(dx,dy)  direction')
for index in range(8):
    target = index * math.pi / 4
    for _ in range(6):
        state = read_state()
        error = wrap(target - state['facing'])
        if abs(error) < 0.08:
            break
        # The left arrow key raises the heading, the right one lowers it.
        vk = VK_LEFT if error > 0 else VK_RIGHT
        hold(vk, min(0.9, abs(error) / TURN_RATE), hwnd)
    before = read_state()
    hold(VK_FORWARD, 1.2, hwnd)
    after = read_state()
    dx = after['pos_x'] - before['pos_x']
    dy = after['pos_y'] - before['pos_y']
    step = math.hypot(dx, dy)
    angle = math.atan2(dx, dy)
    print('%7.3f  %+.5f  %+.5f  %.5f  %+.4f  %s' % (
        after['facing'], dx, dy, step, angle,
        'moved' if step > 0.0005 else 'blocked'))
