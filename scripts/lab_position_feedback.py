"""Capture a stationary position, then evaluate against a recorded baseline."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

from summarize_target_scenarios import ROOT, scalar_fields


def decide(target, current, tolerance=5e-6):
    dx, dy = current['x'] - target['x'], current['y'] - target['y']
    facing = math.atan2(math.sin(current['facing'] - target['facing']),
                        math.cos(current['facing'] - target['facing']))
    if abs(facing) > 0.01 or current['speed'] != 0:
        status = 'STATE_MISMATCH'
    elif max(abs(dx), abs(dy)) <= tolerance:
        status = 'ARRIVED'
    else:
        status = 'CORRECTION_REQUIRED'
    return {'status': status, 'dx': dx, 'dy': dy, 'facing_error': facing,
            'axis_tolerance': tolerance, 'movement_issued': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        a = dict(x=0.0, y=0.0, facing=0.0, speed=0)
        assert decide(a, dict(a, y=5e-6))['status'] == 'ARRIVED'
        assert decide(a, dict(a, y=5.1e-6))['status'] == 'CORRECTION_REQUIRED'
        assert decide(a, dict(a, y=-5.1e-6))['status'] == 'CORRECTION_REQUIRED'
        assert decide(a, dict(a, facing=2*math.pi))['status'] == 'ARRIVED'
        assert decide(a, dict(a, speed=1))['status'] == 'STATE_MISMATCH'
        assert decide(a, dict(a, facing=0.02))['status'] == 'STATE_MISMATCH'
        print('6 decision boundary checks passed')
        return
    if args.capture:
        import time
        import lab_driver5 as d
        from lab_newbie_roundtrip import sample
        from lab_distance_scenarios import command
        hwnd = d.find_game_window()
        if not hwnd:
            raise RuntimeError('No game window in current session')
        d.ensure_foreground(hwnd)
        sample(hwnd, 'current', 'newbie_feedback_')
        command(hwnd, '/reload')
        time.sleep(10)
        return
    source = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a\WTF\Account\GM01\AzerothCore\Probehuman\SavedVariables\WowProbeWotLK.lua')
    raw = source.read_bytes()
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    samples = []
    for block in re.split(r'^\t{2}\{\n', text, flags=re.M)[1:]:
        match = re.search(r'^\t{3}\["meta"\] = \{\n(.*?)^\t{3}\},', block, re.M | re.S)
        if not match:
            continue
        meta = scalar_fields(match.group(1), 4)
        if meta.get('scene') != 'newbie_feedback_current':
            continue
        records = [scalar_fields(b, 5) for b in re.split(r'^\t{4}\{\n', block, flags=re.M)[1:]]
        obs = {r['probe_id']: r for r in records if r.get('probe_id') in (
            'G4.name.player', 'G4.health.player', 'G4.combat.player', 'G4.name.target', 'G3.subzone')}
        assert obs['G4.name.player']['value'] == 'Probehuman'
        assert obs['G4.health.player']['value'] == 52
        assert obs['G4.combat.player']['value_status'] == 'NIL'
        assert obs['G4.name.target']['value_status'] == 'NIL'
        assert obs['G3.subzone']['value'] == 'Northshire Valley'
        assert all(math.isfinite(meta[k]) for k in ('x', 'y', 'facing', 'speed'))
        assert 0 < meta['x'] < 1 and 0 < meta['y'] < 1
        samples.append({'meta': meta, 'observations': obs})
    assert samples, 'No feedback sample; capture first'
    target_path = ROOT / 'results/newbie_compensated_trial1_2026-10-28.json'
    target = json.loads(target_path.read_text(encoding='utf-8'))['runs']['newbie_compensated_trial1_baseline']['meta']
    output = {'source_sha256': hashlib.sha256(raw).hexdigest(), 'target_source': str(target_path),
              'target': target, 'current': samples[-1], 'decision': decide(target, samples[-1]['meta']),
              'scope': 'offline decision after reload; normalized axis tolerance; no movement controller'}
    (ROOT / 'results/newbie_feedback_2026-10-28.json').write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(output['decision'], indent=2))


if __name__ == '__main__':
    main()
