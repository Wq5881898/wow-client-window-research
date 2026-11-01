"""Non-combat installation check; uses the validated chat injection path."""
import time
import sys
import subprocess
import lab_driver5 as d
from lab_distance_scenarios import command

if __name__ == '__main__':
    if '--launch' in sys.argv:
        subprocess.Popen([r'C:\Azerothcore\wowclient\WOW_3.3.5a\Wow.exe'],
                         cwd=r'C:\Azerothcore\wowclient\WOW_3.3.5a')
        sys.exit(0)
    hwnd = d.find_game_window()
    if not hwnd:
        raise RuntimeError('no game window')
    if '--unlock' in sys.argv:
        # The console session may sit on the lock screen; send Ctrl+Alt+Del.
        import ctypes
        u = ctypes.windll.user32
        u.keybd_event(0x11, 0, 0, 0)
        u.keybd_event(0x12, 0, 0, 0)
        u.keybd_event(0x44, 0, 0, 0)
        u.keybd_event(0x44, 0, 2, 0)
        u.keybd_event(0x12, 0, 2, 0)
        u.keybd_event(0x11, 0, 2, 0)
        d.log('unlock sent')
        sys.exit(0)
    if '--capture' in sys.argv:
        import ctypes
        import win32gui
        from PIL import Image
        d.log('capture start hwnd', hwnd)
        u = ctypes.windll.user32
        g = ctypes.windll.gdi32
        d.log('capture session', u.WTSGetActiveConsoleSessionId(),
              'proc session', ctypes.windll.kernel32.ProcessIdToSessionId(
                  ctypes.windll.kernel32.GetCurrentProcessId(), ctypes.byref(ctypes.c_ulong())))
        hwnd = d.find_game_window()
        d.log('capture hwnd', hwnd, 'iconic', win32gui.IsIconic(hwnd),
              'placement', win32gui.GetWindowPlacement(hwnd))
        # PrintWindow attempt on the game window
        w, h = 1920, 1080
        sdc = u.GetDC(0)
        mdc = g.CreateCompatibleDC(sdc)
        bmp = g.CreateCompatibleBitmap(sdc, w, h)
        g.SelectObject(mdc, bmp)
        ok = u.PrintWindow(hwnd, mdc, 0)
        d.log('printwindow', ok, 'err', ctypes.GetLastError())
        import struct
        bmi = ctypes.create_string_buffer(40)
        struct.pack_into('<i', bmi, 0, 40)
        struct.pack_into('<i', bmi, 4, w)
        struct.pack_into('<i', bmi, 8, -h)
        struct.pack_into('<h', bmi, 12, 1)
        struct.pack_into('<h', bmi, 14, 24)
        stride = (w * 3 + 3) & ~3
        buf = ctypes.create_string_buffer(stride * h)
        g.GetDIBits(mdc, bmp, 0, h, buf, bmi, 0)
        img = Image.frombuffer('RGB', (w, h), buf.raw, 'raw', 'BGR', stride, 1)
        colors = img.getcolors(maxcolors=1000000)
        d.log('printwindow colors', len(colors) if colors else 'many',
              sorted(colors, reverse=True)[:3] if colors else '')
        img.save(d.OUT / 'capture-printwindow.png')
        sys.exit(0)
    if '--windows' in sys.argv:
        import win32gui
        rows = []
        def cb(h, _):
            rows.append((h, win32gui.GetClassName(h), win32gui.GetWindowText(h),
                         win32gui.IsWindowVisible(h), win32gui.GetWindowRect(h)))
            return True
        win32gui.EnumWindows(cb, None)
        for row in rows:
            d.log('window', row)
        d.screenshot('window-diagnostic.png')
        sys.exit(0)
    if '--diagnose' in sys.argv:
        command(hwnd, '/run print("LIVE",tostring(WowProbeLiveFrame),GetCVar("scriptErrors")); if WowProbeLiveFrame then print(WowProbeLiveFrame:GetWidth()) end')
        d.screenshot('live-diagnose.png')
        sys.exit(0)
    if '--quit' in sys.argv:
        command(hwnd, '/quit')
        sys.exit(0)
    if '--mode' in sys.argv:
        import win32gui
        hwnd = d.find_game_window()
        style = win32gui.GetWindowLong(hwnd, -16)
        exstyle = win32gui.GetWindowLong(hwnd, -20)
        WS_POPUP, WS_CAPTION, WS_THICKFRAME, WS_SYSMENU = 0x80000000, 0x00C00000, 0x00040000, 0x00080000
        d.log('mode hwnd', hwnd, 'rect', win32gui.GetWindowRect(hwnd),
              'visible', win32gui.IsWindowVisible(hwnd), 'iconic', win32gui.IsIconic(hwnd),
              'popup', bool(style & WS_POPUP), 'caption', bool(style & WS_CAPTION),
              'thick', bool(style & WS_THICKFRAME), 'sysmenu', bool(style & WS_SYSMENU),
              'exstyle', exstyle, 'foreground', d.u.GetForegroundWindow())
        sys.exit(0)
    if '--grab' in sys.argv:
        from PIL import ImageGrab
        import lab_driver5 as d
        image = ImageGrab.grab()
        colors = image.convert('RGB').getcolors(maxcolors=100000)
        d.log('imagegrab distinct', len(colors) if colors else 'many')
        image.save(d.OUT / 'grab-check.png')
        d.screenshot('dc-check.png')
        sys.exit(0)
    if '--noerr' in sys.argv:
        command(hwnd, '/console scriptErrors 0')
        sys.exit(0)
    command(hwnd, '/console scriptErrors 0')
    command(hwnd, '/run if not UnitAffectingCombat("player") then ReloadUI() end')
    time.sleep(8)
    d.screenshot('live-installed.png')
