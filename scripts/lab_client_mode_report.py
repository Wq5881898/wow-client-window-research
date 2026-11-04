"""Report how the client is set up and whether the telemetry reads.

The mode of the client, the size of its window and the state of the probe
are written to a file, because the driver tasks run without a console.
"""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32gui
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame, name_hash
import lab_driver5 as d

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'
CONFIG = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a\WTF\Config.wtf')


def main():
    report = {}
    text = CONFIG.read_text(encoding='utf-8', errors='replace')
    report['config_gxWindow'] = [line for line in text.splitlines()
                                 if line.startswith('SET gxWindow')]
    report['config_gxResolution'] = [line for line in text.splitlines()
                                    if line.startswith('SET gxResolution')]
    try:
        hwnd = d.game_window()
        report['client_window'] = win32gui.GetWindowRect(hwnd)
        report['client_class'] = win32gui.GetClassName(hwnd)
    except Exception as exc:
        report['client_window'] = 'no window: %r' % (exc,)
    try:
        state = decode(assert_real_frame(grab_desktop()))
        report['telemetry'] = 'ok'
        for key in ('protocol', 'health', 'max_health', 'dead', 'combat',
                    'pos_x', 'pos_y', 'facing', 'corpse_exists',
                    'player_guid', 'target_name_hash', 'target_guid',
                    'threat'):
            report[key] = state.get(key)
        report['hash_of_probehuman'] = name_hash('Probehuman')
    except Exception as exc:
        report['telemetry'] = 'failed: %r' % (exc,)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'mode-report.json').write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
