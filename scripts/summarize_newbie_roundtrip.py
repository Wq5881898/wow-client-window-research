"""Validate same-run roundtrip snapshots."""
import hashlib
import argparse
import json
import re
from pathlib import Path
from summarize_target_scenarios import ROOT, scalar_fields


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compensated', action='store_true')
    parser.add_argument('--trial', type=int, choices=range(1, 4))
    args = parser.parse_args()
    prefix = 'newbie_compensated_' if args.compensated else 'newbie_roundtrip_'
    if args.trial:
        if not args.compensated:
            parser.error('--trial requires --compensated')
        prefix += 'trial' + str(args.trial) + '_'
    source = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a\WTF\Account\GM01\AzerothCore\Probehuman\SavedVariables\WowProbeWotLK.lua')
    raw = source.read_bytes()
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    runs = {}
    for block in re.split(r'^\t{2}\{\n', text, flags=re.M)[1:]:
        match = re.search(r'^\t{3}\["meta"\] = \{\n(.*?)^\t{3}\},', block, re.M | re.S)
        if not match:
            continue
        meta = scalar_fields(match.group(1), 4)
        scene = meta.get('scene', '')
        if scene not in {prefix + n for n in ('baseline', 'forward', 'back', 'final')}:
            continue
        records = [scalar_fields(b, 5) for b in re.split(r'^\t{4}\{\n', block, flags=re.M)[1:]]
        obs = {r['probe_id']: r for r in records if r.get('probe_id') in ('G4.name.player', 'G4.health.player', 'G4.combat.player', 'G4.name.target', 'G3.subzone')}
        assert obs['G4.name.player']['value'] == 'Probehuman'
        assert obs['G4.health.player']['value'] == 52
        assert obs['G4.combat.player']['value_status'] == 'NIL'
        assert obs['G4.name.target']['value_status'] == 'NIL'
        assert obs['G3.subzone']['value'] == 'Northshire Valley'
        assert meta['speed'] == 0
        runs[scene] = {'meta': meta, 'observations': obs}
    names = ['baseline', 'forward', 'back', 'final']
    assert set(runs) == {prefix + n for n in names}
    m = [runs[prefix + n]['meta'] for n in names]
    assert all(a['sample_time'] < b['sample_time'] for a, b in zip(m, m[1:]))
    assert all(0 < a['x'] < 1 and 0 < a['y'] < 1 for a in m)
    forward_dy = m[1]['y'] - m[0]['y']
    backward_dy = m[2]['y'] - m[1]['y']
    assert forward_dy * backward_dy < 0, 'Expected opposite nonzero motion'
    assert all(m[2][k] == m[3][k] for k in ('x', 'y', 'facing')), 'Final drift'
    backward_seconds = 0.15 * 7 / 4.5 if args.compensated else 0.15
    expected_ratio = (4.5 * backward_seconds) / (7.0 * 0.15)
    measured_ratio = abs(backward_dy / forward_dy)
    speed_analysis = {
        'source': r'C:\Azerothcore\azerothcore-wotlk\src\server\game\Entities\Unit\Unit.cpp:92-96',
        'base_run_speed': 7.0, 'base_run_back_speed': 4.5,
        'forward_seconds': 0.15, 'backward_seconds': backward_seconds,
        'expected_backward_forward_ratio': expected_ratio,
        'measured_backward_forward_ratio': measured_ratio,
        'ratio_relative_error': measured_ratio / expected_ratio - 1,
        'predicted_residual_dy': forward_dy * (1 - expected_ratio),
        'prediction_error_dy': m[2]['y'] - m[0]['y'] - forward_dy * (1 - expected_ratio),
        'equal_distance_backward_seconds_for_0_15_forward': 0.15 * 7 / 4.5,
        'scope': 'source defaults and observed y displacement; not live speed measurement',
    }
    diffs = []
    for name, cur in zip(names, m):
        diffs.append({'stage': name, 'dx_from_baseline': cur['x'] - m[0]['x'], 'dy_from_baseline': cur['y'] - m[0]['y'], 'facing_delta': cur['facing'] - m[0]['facing'], 'sample_time': cur['sample_time']})
    result = {'source_sha256': hashlib.sha256(raw).hexdigest(), 'runs': runs, 'diffs': diffs,
              'return_residual': {'dx': m[2]['x'] - m[0]['x'], 'dy': m[2]['y'] - m[0]['y'], 'facing': m[2]['facing'] - m[0]['facing']},
              'final_residual': {'dx': m[3]['x'] - m[0]['x'], 'dy': m[3]['y'] - m[0]['y'], 'facing': m[3]['facing'] - m[0]['facing']}}
    result['speed_analysis'] = speed_analysis
    if args.compensated:
        control = json.loads((ROOT / 'results' / 'newbie_roundtrip_2026-10-24.json').read_text(encoding='utf-8'))
        old = abs(control['return_residual']['dy'])
        result['comparison'] = {'control_abs_dy': old,
                                'compensated_abs_dy': abs(result['return_residual']['dy']),
                                'residual_reduction_fraction': 1 - abs(result['return_residual']['dy']) / old}
        print(json.dumps(result['comparison'], indent=2))
    filename = 'newbie_compensated_2026-10-28.json' if args.compensated else 'newbie_roundtrip_2026-10-24.json'
    if args.trial:
        filename = 'newbie_compensated_trial' + str(args.trial) + '_2026-10-28.json'
    path = ROOT / 'results' / filename
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'diffs': diffs, 'return_residual': result['return_residual'], 'final_residual': result['final_residual']}, ensure_ascii=False, indent=2))
    print(json.dumps(speed_analysis, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
