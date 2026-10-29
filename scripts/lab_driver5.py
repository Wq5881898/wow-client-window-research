"""Session-2 lab driver v5: SetCursorPos-based clicks, 1024x768 UI coords."""
import ctypes
import ctypes.wintypes as wt
import struct
import sys
import time
from pathlib import Path

import win32con
import win32gui
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / 'driver5.log'

u = ctypes.windll.user32
g = ctypes.windll.gdi32


def log(*a):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(' '.join(str(x) for x in a) + '\n')


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', wt.WORD), ('wScan', wt.WORD), ('dwFlags', wt.DWORD),
                ('time', wt.DWORD), ('dwExtraInfo', ctypes.c_void_p)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [('dx', wt.LONG), ('dy', wt.LONG), ('mouseData', wt.DWORD),
                ('dwFlags', wt.DWORD), ('time', wt.DWORD),
                ('dwExtraInfo', ctypes.c_void_p)]


class INPUTUNION(ctypes.Union):
    _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [('type', wt.DWORD), ('union', INPUTUNION)]


SendInput = u.SendInput


def press(vk):
    i = INPUT()
    i.type = 1
    i.union.ki = KEYBDINPUT(vk, 0, 0, 0, None)
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    i.union.ki.dwFlags = win32con.KEYEVENTF_KEYUP
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))


def char(c):
    i = INPUT()
    i.type = 1
    i.union.ki = KEYBDINPUT(0, ord(c), win32con.KEYEVENTF_UNICODE, 0, None)
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    i.union.ki.dwFlags |= win32con.KEYEVENTF_KEYUP
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))


def type_text(text, delay=0.05):
    for c in text:
        char(c)
        time.sleep(delay)


def type_text2(text, delay=0.05, hwnd=None):
    """Alternate injection: VK with scancode 0, no extended flag, longer gaps."""
    for c in text:
        if c == ' ':
            post_key(hwnd, 0x20, 0x39)
            time.sleep(delay)
            continue
        i = INPUT()
        i.type = 1
        i.union.ki = KEYBDINPUT(0, ord(c), win32con.KEYEVENTF_UNICODE, 0, None)
        r1 = SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
        time.sleep(max(delay, 0.03))
        i.union.ki.dwFlags = win32con.KEYEVENTF_UNICODE | win32con.KEYEVENTF_KEYUP
        r2 = SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
        if r1 != 1 or r2 != 1:
            log('type2 dropped', repr(c), r1, r2, ctypes.GetLastError())
        time.sleep(delay)


def click_abs(x, y):
    u.SetCursorPos(int(x), int(y))
    time.sleep(0.15)
    i = INPUT()
    i.type = 0
    i.union.mi = MOUSEINPUT(0, 0, 0, win32con.MOUSEEVENTF_LEFTDOWN, 0, None)
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    time.sleep(0.05)
    i.union.mi.dwFlags = win32con.MOUSEEVENTF_LEFTUP
    SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
    log('clicked', x, y, 'cursor', win32gui.GetCursorPos())


def click_raw(x, y, hold=0.4):
    u.SetCursorPos(int(x), int(y))
    time.sleep(0.15)
    u.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(hold)
    u.mouse_event(0x0004, 0, 0, 0, 0)
    log('raw clicked', x, y, 'hold', hold, 'cursor', win32gui.GetCursorPos())


def post_key(hwnd, vk, sc=0x1C):
    lp = (sc << 16) | 1
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, lp)
    time.sleep(0.05)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk, lp | 0xC0000000)


def type_text3(hwnd, text, delay=0.05):
    """WM_CHAR via PostMessage: reliable text entry in windowed mode."""
    for c in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(c), 0)
        time.sleep(delay)


def click_si(x, y, hold=0.3):
    u.SetCursorPos(int(x), int(y))
    time.sleep(0.15)
    seq = [
        MOUSEINPUT(0, 0, 0, 0, 0, None),
        MOUSEINPUT(0, 0, 0, win32con.MOUSEEVENTF_LEFTDOWN, 0, None),
        MOUSEINPUT(0, 0, 0, win32con.MOUSEEVENTF_LEFTUP, 0, None),
    ]
    for idx, mi in enumerate(seq):
        i = INPUT()
        i.type = 0
        i.union.mi = mi
        n = SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
        log('si input', idx, 'sent', n, 'err', ctypes.GetLastError())
        time.sleep(hold)
    log('si clicked', x, y, 'cursor', win32gui.GetCursorPos())


def find_game_window():
    found = []

    def cb(hwnd, _):
        if win32gui.GetClassName(hwnd) == 'GxWindowClassD3d':
            found.append(hwnd)
        return True
    win32gui.EnumWindows(cb, None)
    return found[0] if found else 0


def ensure_foreground(hwnd, x=40, y=30, w=1200, h=800):
    if not win32gui.IsWindowVisible(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.5)
    if win32gui.GetWindowRect(hwnd)[0] < -10000:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.5)
    if win32gui.GetClassName(hwnd) != 'GxWindowClassD3d':
        win32gui.SetWindowPos(hwnd, 0, x, y, w, h, win32con.SWP_NOZORDER)
        time.sleep(0.5)
    try:
        win32gui.LockSetForegroundWindow(2)  # LSFW_LOCK
    except Exception:
        pass
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:
        log('SetForegroundWindow failed', e)
        u.keybd_event(0x12, 0, 0, 0)
        u.keybd_event(0x12, 0, 2, 0)
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
    try:
        win32gui.UnlockSetForegroundWindow(1)  # LSFW_UNLOCK
    except Exception:
        pass
    time.sleep(0.8)
    return win32gui.GetWindowRect(hwnd)


def client_to_screen(hwnd, ux, uy):
    l, t, r, b = win32gui.GetClientRect(hwnd)
    cw, ch = r - l, b - t
    px, py = int(ux * cw / 1024), int(uy * ch / 768)
    pt = wt.POINT(px, py)
    u.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y


def click_ui(hwnd, ux, uy):
    """Click using 1024x768 UI coords, scaled to current client size."""
    x, y = client_to_screen(hwnd, ux, uy)
    click_abs(x, y)


def screenshot(name):
    w = u.GetSystemMetrics(0)
    h = u.GetSystemMetrics(1)
    sdc = u.GetDC(0)
    mdc = g.CreateCompatibleDC(sdc)
    bmp = g.CreateCompatibleBitmap(sdc, w, h)
    g.SelectObject(mdc, bmp)
    g.BitBlt(mdc, 0, 0, w, h, sdc, 0, 0, 0x00CC0020)
    bmi = ctypes.create_string_buffer(40)
    struct.pack_into('<i', bmi, 0, 40)
    struct.pack_into('<i', bmi, 4, w)
    struct.pack_into('<i', bmi, 8, -h)
    struct.pack_into('<h', bmi, 12, 1)
    struct.pack_into('<h', bmi, 14, 24)
    stride = (w * 3 + 3) & ~3
    buf = ctypes.create_string_buffer(stride * h)
    lines = g.GetDIBits(mdc, bmp, 0, h, buf, bmi, 0)
    img = Image.frombuffer('RGB', (w, h), buf.raw, 'raw', 'BGR', stride, 1)
    path = OUT / name
    img.save(path)
    u.ReleaseDC(0, sdc)
    g.DeleteDC(mdc)
    g.DeleteObject(bmp)
    log('screenshot', path, 'lines', lines)
    return path


def clear_field():
    for _ in range(60):
        press(win32con.VK_BACK)
        time.sleep(0.008)
    time.sleep(0.2)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'shot'
    hwnd = find_game_window()
    log('=== mode', mode, 'hwnd', hwnd)
    if not hwnd:
        log('no game window')
        return 1
    ensure_foreground(hwnd)
    if mode == 'esc':
        press(win32con.VK_ESCAPE)
        time.sleep(1)
        screenshot('wow-07-esc.png')
    elif mode == 'okay':
        click_ui(hwnd, 890, 612)
        time.sleep(1)
        screenshot('wow-07-okay.png')
    elif mode == 'login':
        user = sys.argv[2] if len(sys.argv) > 2 else 'GM01'
        pwd = sys.argv[3] if len(sys.argv) > 3 else '123321'
        click_ui(hwnd, 382, 352)
        time.sleep(0.3)
        clear_field()
        type_text(user)
        time.sleep(0.4)
        press(win32con.VK_TAB)
        time.sleep(0.3)
        clear_field()
        type_text(pwd)
        time.sleep(0.4)
        screenshot('wow-07-before-enter.png')
        press(win32con.VK_RETURN)
        log('login submitted', user)
        time.sleep(4)
        screenshot('wow-07-after-enter.png')
    elif mode == 'enter':
        ux = float(sys.argv[2]) if len(sys.argv) > 2 else 512
        uy = float(sys.argv[3]) if len(sys.argv) > 3 else 729
        click_ui(hwnd, ux, uy)
        log('enter world clicked', ux, uy)
        time.sleep(2)
        screenshot('wow-09a-afterclick.png')
        if win32gui.GetClassName(hwnd) == 'GxWindowClassD3d':
            win32gui.PostMessage(hwnd, win32con.WM_NCLBUTTONDOWN, 2, 0)
            win32gui.PostMessage(hwnd, win32con.WM_NCLBUTTONUP, 2, 0)
            log('sent WM_NCLBUTTON to frame')
        click_raw(*client_to_screen(hwnd, ux, uy))
        time.sleep(2)
        click_raw(*client_to_screen(hwnd, ux, uy))
        time.sleep(35)
        screenshot('wow-09-enterworld.png')
    elif mode == 'chat':
        # close any open input box, then open a fresh one and clear it
        press(0x1B)
        time.sleep(0.6)
        press(0xBF)
        time.sleep(0.6)
        clear_field()
        cmd = sys.argv[2] if len(sys.argv) > 2 else 'wowprobe once test'
        if cmd.startswith('/'):
            type_text(cmd[1:])
        else:
            type_text(cmd)
        time.sleep(0.5)
        screenshot('wow-10-typed.png')
        press(win32con.VK_RETURN)
        time.sleep(3)
        screenshot('wow-10-chat.png')
    elif mode == 'shot':
        screenshot(sys.argv[2] if len(sys.argv) > 2 else 'wow-shot5.png')
    elif mode == 'click':
        ux = float(sys.argv[2]) if len(sys.argv) > 2 else 512
        uy = float(sys.argv[3]) if len(sys.argv) > 3 else 729
        log('client rect', win32gui.GetClientRect(hwnd), 'win rect', win32gui.GetWindowRect(hwnd))
        click_ui(hwnd, ux, uy)
        time.sleep(1.5)
        screenshot('wow-click-%d-%d.png' % (ux, uy))
    elif mode == 'rawclick':
        x, y = int(sys.argv[2]), int(sys.argv[3])
        click_raw(x, y)
        time.sleep(1.5)
        screenshot('wow-rawclick-%d-%d.png' % (x, y))
    elif mode == 'siclick':
        x, y = int(sys.argv[2]), int(sys.argv[3])
        click_si(x, y)
        time.sleep(2)
        screenshot('wow-siclick-%d-%d.png' % (x, y))
    elif mode == 'key':
        vk = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x0D
        press(vk)
        log('key pressed', hex(vk))
        time.sleep(2)
        screenshot('wow-key-%s.png' % hex(vk)[2:])
    elif mode == 'sendit':
        press(0x1B)
        time.sleep(0.6)
        press(0xBF)
        time.sleep(0.6)
        clear_field()
        cmd = sys.argv[2] if len(sys.argv) > 2 else 'wowprobe once test'
        if cmd.startswith('/'):
            cmd = cmd[1:]
        type_text2(cmd)
        time.sleep(0.5)
        screenshot('wow-10-typed.png')
        press(0x0D)
        log('sendit enter sent')
        time.sleep(3)
        screenshot('wow-10-chat.png')
    elif mode == 'run':
        # execute Lua via /run (no slash typing needed); wrap in pcall
        code = sys.argv[2] if len(sys.argv) > 2 else 'print(1)'
        press(0x1B)
        time.sleep(0.6)
        press(0xBF)
        time.sleep(0.6)
        clear_field()
        type_text2('run ' + code)
        time.sleep(0.5)
        press(0x0D)
        log('run sent')
        time.sleep(3)
        screenshot('wow-run.png')
    elif mode == 'postenter':
        # submit chat box via posted WM_KEYDOWN/WM_KEYUP (windowed mode)
        lp = 0x001C0001
        win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, 0x0D, lp)
        time.sleep(0.08)
        win32gui.PostMessage(hwnd, win32con.WM_KEYUP, 0x0D, lp | 0xC0000000)
        log('postenter sent')
        time.sleep(3)
        screenshot('wow-postenter.png')
    elif mode == 'postchat':
        cmd = sys.argv[2] if len(sys.argv) > 2 else 'wowprobe once test'
        if cmd.startswith('/'):
            cmd = cmd[1:]
        # close leftover box, open fresh, clear
        post_key(hwnd, 0x1B)
        time.sleep(0.5)
        post_key(hwnd, 0xBF, 0x0E)
        time.sleep(0.5)
        for _ in range(60):
            post_key(hwnd, 0x0E)
        time.sleep(0.3)
        type_text3(hwnd, cmd)
        time.sleep(0.4)
        screenshot('wow-10-typed.png')
        press(0x0D)
        log('postchat sent', cmd)
        time.sleep(3)
        screenshot('wow-10-chat.png')
    elif mode == 'postkey':
        vk = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0xBF
        lp = ((int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x0E) << 16) | 1
        win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, lp)
        time.sleep(0.08)
        win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk, lp | 0xC0000000)
        log('postkey sent', hex(vk))
        time.sleep(2)
        screenshot('wow-postkey-%s.png' % hex(vk)[2:])
    elif mode == 'entervk':
        # VK_RETURN with scan code 0x1C (the combination that worked in entertest2)
        i = INPUT()
        i.type = 1
        i.union.ki = KEYBDINPUT(0x1C, 0x1C, 0, 0, None)
        SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
        time.sleep(0.05)
        i.union.ki.dwFlags = win32con.KEYEVENTF_KEYUP
        SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
        log('entervk sent')
        time.sleep(3)
        screenshot('wow-entervk.png')
    elif mode == 'numenter':
        i = INPUT()
        i.type = 1
        i.union.ki = KEYBDINPUT(0x0D, 0x1C, win32con.KEYEVENTF_EXTENDEDKEY, 0, None)
        SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
        time.sleep(0.05)
        i.union.ki.dwFlags = win32con.KEYEVENTF_EXTENDEDKEY | win32con.KEYEVENTF_KEYUP
        SendInput(1, ctypes.byref(i), ctypes.sizeof(INPUT))
        log('numenter sent')
        time.sleep(3)
        screenshot('wow-numenter.png')
    elif mode == 'chat2':
        press(0x1B)
        time.sleep(0.6)
        press(0xBF)
        time.sleep(0.6)
        clear_field()
        cmd = sys.argv[2] if len(sys.argv) > 2 else 'wowprobe once test'
        if cmd.startswith('/'):
            cmd = cmd[1:]
        type_text2(cmd)
        time.sleep(0.5)
        screenshot('wow-10-typed.png')
        press(win32con.VK_RETURN)
        time.sleep(3)
        screenshot('wow-10-chat.png')
    elif mode == 'wait':
        secs = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        name = sys.argv[3] if len(sys.argv) > 3 else 'wow-wait.png'
        time.sleep(secs)
        screenshot(name)
    elif mode == 'tab':
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        for _ in range(n):
            press(0x09)
            time.sleep(0.25)
        time.sleep(1)
        screenshot('wow-tab-%d.png' % n)
    elif mode == 'clickin':
        ux = float(sys.argv[2]) if len(sys.argv) > 2 else 512
        uy = float(sys.argv[3]) if len(sys.argv) > 3 else 729
        l, t, r, b = win32gui.GetClientRect(hwnd)
        cw, ch = r - l, b - t
        px, py = int(ux * cw / 1024), int(uy * ch / 768)
        lp = py * 65536 + px
        log('clickin client', px, py)
        win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 1, lp)
        time.sleep(0.3)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, 1, lp)
        time.sleep(0.3)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lp)
        time.sleep(2)
        screenshot('wow-clickin-%d-%d.png' % (ux, uy))
    elif mode == 'clickmsg':
        ux = float(sys.argv[2]) if len(sys.argv) > 2 else 512
        uy = float(sys.argv[3]) if len(sys.argv) > 3 else 729
        l, t, r, b = win32gui.GetClientRect(hwnd)
        cw, ch = r - l, b - t
        px, py = int(ux * cw / 1024), int(uy * ch / 768)
        lp = py * 65536 + px
        log('clickmsg client', px, py)
        win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, 1, lp)
        time.sleep(0.3)
        win32gui.PostMessage(hwnd, 0x0200, 0x0201, lp)  # MS_WINI_LBUTTONDOWN
        time.sleep(0.3)
        win32gui.PostMessage(hwnd, 0x0200, 0x0202, lp)  # MS_WINI_LBUTTONUP
        time.sleep(2)
        screenshot('wow-clickmsg-%d-%d.png' % (ux, uy))
    elif mode == 'move':
        u.SetCursorPos(int(sys.argv[2]), int(sys.argv[3]))
        log('cursor moved to', win32gui.GetCursorPos())
    return 0


if __name__ == '__main__':
    sys.exit(main())
