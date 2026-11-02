"""Print the raw decoded telemetry of the client."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
import win32con, win32gui


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


hide_consoles()

import time
state = None
for attempt in range(8):
    try:
        state = decode(assert_real_frame(grab_desktop()))
        break
    except Exception as exc:
        print('attempt', attempt, 'failed', exc)
        time.sleep(1.5)
if state is None:
    raise SystemExit('no telemetry')
out = Path(__file__).resolve().parents[1] / '.cache' / 'desktop-check' / 'raw-state.json'
out.write_text(json.dumps(state, indent=2, ensure_ascii=False, default=str),
               encoding='utf-8')
for key in ('protocol', 'health', 'max_health', 'dead', 'combat', 'pos_x',
            'pos_y', 'facing', 'corpse_x', 'corpse_y', 'corpse_exists',
            'unit_x', 'unit_y', 'speed', 'chat_open', 'target_exists'):
    print(f'{key:15} {state.get(key)!r}')
