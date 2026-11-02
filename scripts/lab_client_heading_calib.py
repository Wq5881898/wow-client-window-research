"""Measure how the client turns and how it walks.

The heading of the client is given in radians and the position in the
normalised map coordinates of the zone. The script presses the arrow keys
and the forward key for a known time and prints what the client did, so the
sign of the turn, the turn rate and the direction of the walk can be taken
from the client itself and not from an assumption.

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
    time.sleep(0.2)
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
    time.sleep(0.4)


hwnd = d.find_game_window()
if not hwnd:
    raise SystemExit('no game window')
hide_consoles()
d.ensure_foreground(hwnd)

VK_FORWARD = 0x57
VK_LEFT = 0x25
VK_RIGHT = 0x27

print('focus', win32gui.GetForegroundWindow() == hwnd)
before = read_state()
print('before  pos=%.5f,%.5f facing=%.4f speed=%.1f' % (
    before['pos_x'], before['pos_y'], before['facing'], before['speed']))

hold(VK_RIGHT, 1.0, hwnd)
after = read_state()
delta = (after['facing'] - before['facing']) % (2 * math.pi)
print('RIGHT 1.0s  facing %.4f -> %.4f  delta=%+.4f rad  rate=%.2f rad/s' % (
    before['facing'], after['facing'], after['facing'] - before['facing'],
    (after['facing'] - before['facing'])))

hold(VK_LEFT, 1.0, hwnd)
after2 = read_state()
print('LEFT  1.0s  facing %.4f -> %.4f  delta=%+.4f rad  rate=%.2f rad/s' % (
    after['facing'], after2['facing'], after2['facing'] - after['facing'],
    (after2['facing'] - after['facing'])))

hold(VK_FORWARD, 2.0, hwnd)
after3 = read_state()
dx = after3['pos_x'] - after2['pos_x']
dy = after3['pos_y'] - after2['pos_y']
print('W     2.0s  pos %.5f,%.5f -> %.5f,%.5f  dx=%+.5f dy=%+.5f '
      'speed=%.1f' % (after2['pos_x'], after2['pos_y'], after3['pos_x'],
                      after3['pos_y'], dx, dy, after3['speed']))
if dx or dy:
    print('  direction of the step: atan2(dx,dy)=%.4f rad, heading=%.4f rad, '
          'difference=%+.4f' % (math.atan2(dx, dy), after3['facing'],
                                math.atan2(dx, dy) - after3['facing']))
