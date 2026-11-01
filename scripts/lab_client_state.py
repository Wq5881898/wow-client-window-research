"""Report the current live telemetry of the client."""
import json
import sys
import time
from pathlib import Path
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame

ROOT = Path(__file__).resolve().parents[1]


def main():
    hwnd = d.find_game_window()
    out = ROOT / '.cache' / 'desktop-check' / 'state-report.json'
    if not hwnd:
        out.write_text(json.dumps({'error': 'no game window'}), encoding='utf-8')
        print('no game window')
        return 1
    try:
        d.ensure_foreground(hwnd)
    except Exception as exc:
        print('foreground failed', exc)
    try:
        state = decode(assert_real_frame(grab_desktop()))
    except Exception as exc:
        out.write_text(json.dumps({'error': repr(exc), 'hwnd': hwnd}),
                       encoding='utf-8')
        raise
    report = {k: state.get(k) for k in (
        'protocol', 'health', 'max_health', 'power', 'combat', 'dead',
        'spell_learned', 'spell_range', 'target_exists', 'target_attackable',
        'target_health', 'target_guid', 'pos_x', 'pos_y', 'facing',
        'cast_started', 'cast_succeeded', 'cast_failed', 'ui_errors',
        'event_kind', 'event_spell', 'last_reason', 'last_error_reason',
        'spell_bits', 'known_spells', 'frost_armor')}
    report['events'] = state['events']
    out.write_text(json.dumps(report, indent=2), encoding='utf-8')
    d.log('state report', str(out), 'ok')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
