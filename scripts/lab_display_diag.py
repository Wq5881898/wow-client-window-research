"""Interactive display diagnostics for WoW lab (Session 2)."""
import json
import os
import sys
import time
from pathlib import Path

import ctypes
import win32api
import win32con
import win32gui

out = Path(__file__).resolve().parents[1] / '.cache' / 'desktop-check'
out.mkdir(parents=True, exist_ok=True)

def main():
    res = {'pid': os.getpid(), 'session': ctypes.windll.kernel32.WTSGetActiveConsoleSessionId()}
    res['remote_session'] = ctypes.windll.user32.GetSystemMetrics(0x1000)
    res['displays'] = []
    res['monitors'] = []
    res['modes'] = []

    for i in range(64):
        try:
            d = win32api.EnumDisplayDevices(None, i)
        except Exception:
            break
        modes = []
        for m in range(32):
            try:
                mode = win32api.EnumDisplaySettings(d.DeviceName, m)
            except Exception:
                break
            modes.append((mode.PelsWidth, mode.PelsHeight, mode.BitsPerPel,
                          mode.DisplayFrequency, mode.DisplayFlags))
        try:
            cur = win32api.EnumDisplaySettings(d.DeviceName, -1)
            cur = (cur.PelsWidth, cur.PelsHeight, cur.BitsPerPel, cur.DisplayFrequency, cur.DisplayFlags)
        except Exception:
            cur = None
        res['displays'].append({
            'name': d.DeviceName, 'desc': d.DeviceString, 'flags': d.StateFlags,
            'modes': modes[:6], 'mode_count': len(modes), 'current': cur,
        })

    # enumerate monitors via MonitorFromPoint on a grid
    seen = set()
    for x in range(-2000, 3001, 400):
        for y in range(-2000, 3001, 400):
            try:
                h = win32api.MonitorFromPoint((x, y), 0)
            except Exception:
                continue
            if h in seen:
                continue
            seen.add(h)
            try:
                res['monitors'].append(win32api.GetMonitorInfo(h))
            except Exception:
                pass

    (out / 'display.json').write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding='utf-8')
    print('wrote display.json')

if __name__ == '__main__':
    main()
