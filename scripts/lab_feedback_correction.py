"""One bounded feedback correction, with fresh persisted snapshots at each step."""
import hashlib
import argparse
import json
import re
import time
from pathlib import Path

import lab_driver5 as d
from lab_distance_scenarios import command, hold
from lab_newbie_roundtrip import sample
from lab_position_feedback import decide
from summarize_target_scenarios import ROOT, scalar_fields

SOURCE = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a\WTF\Account\GM01\AzerothCore\Probehuman\SavedVariables\WowProbeWotLK.lua')


def capture(hwnd, scene, prefix):
    before = SOURCE.stat().st_mtime_ns
    sample(hwnd, scene, prefix)
    command(hwnd, '/reload')
    deadline = time.monotonic() + 30
    while SOURCE.stat().st_mtime_ns == before and time.monotonic() < deadline:
        time.sleep(1)
    if SOURCE.stat().st_mtime_ns == before:
        raise RuntimeError('SavedVariables did not update')
    time.sleep(10)
    raw = SOURCE.read_bytes()
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    for block in re.split(r'^\t{2}\{\n', text, flags=re.M)[1:]:
        match = re.search(r'^\t{3}\["meta"\] = \{\n(.*?)^\t{3}\},', block, re.M | re.S)
        if not match:
            continue
        meta = scalar_fields(match.group(1), 4)
        if meta.get('scene') != prefix + scene:
            continue
        records = [scalar_fields(b, 5) for b in re.split(r'^\t{4}\{\n', block, flags=re.M)[1:]]
        obs = {r['probe_id']: r for r in records if r.get('probe_id') in (
            'G4.name.player', 'G4.health.player', 'G4.combat.player', 'G4.name.target', 'G3.subzone')}
        assert obs['G4.name.player']['value'] == 'Probehuman'
        assert obs['G4.health.player']['value'] == 52
        assert obs['G4.combat.player']['value_status'] == 'NIL'
        assert obs['G4.name.target']['value_status'] == 'NIL'
        assert obs['G3.subzone']['value'] == 'Northshire Valley'
        assert meta['speed'] == 0 and 0 < meta['x'] < 1 and 0 < meta['y'] < 1
        return {'meta': meta, 'observations': obs, 'source_sha256': hashlib.sha256(raw).hexdigest()}
    raise RuntimeError('Fresh scene missing: ' + prefix + scene)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reverse', action='store_true')
    args = parser.parse_args()
    prefix = 'feedback_' + str(time.time_ns()) + '_'
    output = ROOT / 'results' / (prefix + 'correction.json')
    result = {'prefix': prefix, 'status': 'STARTED', 'correction_count': 0,
              'displacement_direction': 'back' if args.reverse else 'forward'}
    def save():
        output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    save()
    try:
        hwnd = d.find_game_window()
        if not hwnd:
            raise RuntimeError('No game window in this session')
        d.ensure_foreground(hwnd)
        result['baseline'] = capture(hwnd, 'baseline', prefix)
        target = result['baseline']['meta']
        assert abs(target['facing']) < 0.01, 'Calibration requires near-zero facing'
        save()
        if d.win32gui.GetForegroundWindow() != hwnd:
            raise RuntimeError('Game lost foreground before displacement')
        hold(0x53 if args.reverse else 0x57, 0.15)
        result['displaced'] = capture(hwnd, 'displaced', prefix)
        decision = decide(target, result['displaced']['meta'])
        result['before_decision'] = decision
        save()
        assert decision['status'] == 'CORRECTION_REQUIRED'
        assert abs(decision['dx']) <= 5e-6 and 5e-6 < abs(decision['dy']) < 0.001
        control = json.loads((ROOT / 'results/newbie_roundtrip_2026-10-24.json').read_text(encoding='utf-8'))
        m = control['runs']
        if decision['dy'] > 0:
            key = 0x57
            rate = (m['newbie_roundtrip_forward']['meta']['y'] - m['newbie_roundtrip_baseline']['meta']['y']) / 0.15
        else:
            key = 0x53
            rate = (m['newbie_roundtrip_back']['meta']['y'] - m['newbie_roundtrip_forward']['meta']['y']) / 0.15
        duration = -decision['dy'] / rate
        assert 0.02 <= duration <= 0.4
        result['plan'] = {'key': chr(key), 'seconds': duration, 'calibrated_dy_per_second': rate}
        save()
        if d.win32gui.GetForegroundWindow() != hwnd:
            raise RuntimeError('Game lost foreground before correction')
        hold(key, duration)
        result['correction_count'] = 1
        save()
        result['corrected'] = capture(hwnd, 'corrected', prefix)
        result['after_decision'] = decide(target, result['corrected']['meta'])
        result['status'] = result['after_decision']['status']
        save()
        time.sleep(10)
        result['final'] = capture(hwnd, 'final', prefix)
        result['final_decision'] = decide(target, result['final']['meta'])
        result['stationary_delta'] = {k: result['final']['meta'][k] - result['corrected']['meta'][k]
                                      for k in ('x', 'y', 'facing')}
        assert all(v == 0 for v in result['stationary_delta'].values()), 'Final sample drift'
        times = [result[s]['meta']['sample_time'] for s in ('baseline', 'displaced', 'corrected', 'final')]
        assert all(a < b for a, b in zip(times, times[1:])), 'Non-increasing sample times'
        result['status'] = result['final_decision']['status']
        save()
        d.log('feedback correction result', str(output), result['status'])
    except Exception as exc:
        result['status'] = 'FAILED'
        result['error'] = str(exc)
        save()
        raise


if __name__ == '__main__':
    main()
