import ctypes
import ctypes.wintypes as wt
import sys

log = open(r'C:\APP\opencode\project\WoW自动化预研\.cache\enum.log', 'w', encoding='utf-8')


def p(*a):
    s = ' '.join(str(x) for x in a)
    log.write(s + '\n')
    log.flush()
    print(s)


u = ctypes.windll.user32
p('user32 loaded', u)


class DEV(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("DeviceName", ctypes.c_char * 32),
        ("DeviceString", ctypes.c_char * 128),
        ("StateFlags", wt.DWORD),
        ("DeviceID", ctypes.c_char * 128),
        ("DeviceKey", ctypes.c_char * 128),
    ]


class MODE(ctypes.Structure):
    _fields_ = [
        ("dmSize", wt.DWORD),
        ("dmDriverExtra", wt.DWORD),
        ("dmFields", wt.DWORD),
        ("dmOrientation", wt.DWORD),
        ("dmPaperSize", wt.DWORD),
        ("dmPaperLength", wt.DWORD),
        ("dmPaperWidth", wt.DWORD),
        ("dmScale", wt.DWORD),
        ("dmCopies", wt.DWORD),
        ("dmDefaultSource", wt.DWORD),
        ("dmPrintQuality", wt.DWORD),
        ("dmSpec", wt.DWORD),
        ("dmPosition", wt.DWORD),
        ("dmDisplayOrientation", wt.DWORD),
        ("dmDisplayFixedOutput", wt.DWORD),
        ("dmColor", ctypes.c_short),
        ("dmDuplex", ctypes.c_short),
        ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short),
        ("dmCollate", ctypes.c_short),
        ("dmFormName", ctypes.c_char * 32),
        ("dmLogPixels", wt.WORD),
        ("dmBitsPerPel", wt.DWORD),
        ("dmPelsWidth", wt.DWORD),
        ("dmPelsHeight", wt.DWORD),
        ("dmDisplayFlags", wt.DWORD),
        ("dmDisplayFrequency", wt.DWORD),
        ("dmICMMethod", wt.DWORD),
        ("dmICMIntent", wt.DWORD),
        ("dmMediaType", wt.DWORD),
        ("dmDitherType", wt.DWORD),
        ("dmReserved1", wt.DWORD),
        ("dmReserved2", wt.DWORD),
        ("dmPanningWidth", wt.DWORD),
        ("dmPanningHeight", wt.DWORD),
    ]


i = 0
p('sizeof DEV', ctypes.sizeof(DEV), 'MODE', ctypes.sizeof(MODE))
while True:
    d = DEV()
    d.cb = ctypes.sizeof(DEV)
    r = u.EnumDisplayDevicesA(None, i, ctypes.byref(d), 0)
    p('EnumDisplayDevicesA returned', r, 'for index', i)
    if not r:
        break
    p(f"[{i}] {d.DeviceName.decode(errors='replace')} | "
      f"{d.DeviceString.decode(errors='replace')} | flags={d.StateFlags}")
    modes = set()
    j = 0
    while True:
        m = MODE()
        m.dmSize = ctypes.sizeof(MODE)
        if u.EnumDisplaySettingsA(d.DeviceName, j, ctypes.byref(m)):
            modes.add((m.dmPelsWidth, m.dmPelsHeight, m.dmDisplayFrequency, m.dmBitsPerPel))
            j += 1
        else:
            break
    hi = sorted(modes, reverse=True)[:5]
    p(f"    modes={len(modes)} top={hi}")
    i += 1
log.close()
