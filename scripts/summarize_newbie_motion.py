"""Extract dedicated newbie motion samples from SavedVariables."""
import hashlib
import json
import math
import re
from pathlib import Path

from summarize_target_scenarios import ROOT, scalar_fields


def main():
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
        if not scene.startswith('newbie_motion_'):
            continue
        records = [scalar_fields(b, 5) for b in re.split(r'^\t{4}\{\n', block, flags=re.M)[1:]]
        observations = {r['probe_id']: r for r in records if r.get('probe_id') in (
            'G4.name.player', 'G4.health.player', 'G4.combat.player', 'G3.subzone')}
        assert observations['G4.name.player']['value'] == 'Probehuman'
        assert observations['G4.health.player']['value'] == 52
        assert observations['G4.combat.player']['value_status'] == 'NIL'
        assert meta['speed'] == 0
        runs[scene] = {'meta': meta, 'observations': observations}
    stages = ('stationary', 'back', 'forward', 'left', 'right', 'turnleft', 'turnright', 'final')
    missing = [s for s in stages if 'newbie_motion_' + s not in runs]
    deltas = {}
    for previous, current in zip(stages, stages[1:]):
        if previous in missing or current in missing:
            continue
        a = runs['newbie_motion_' + previous]['meta']
        b = runs['newbie_motion_' + current]['meta']
        deltas[current] = {
            'from': previous, 'dx': b['x'] - a['x'], 'dy': b['y'] - a['y'],
            'facing_delta': math.atan2(math.sin(b['facing'] - a['facing']),
                                       math.cos(b['facing'] - a['facing'])),
        }
    output = {'source_sha256': hashlib.sha256(raw).hexdigest(), 'runs': runs,
              'missing_stages': missing, 'adjacent_deltas': deltas,
              'position_units': 'normalized map coordinates; not yards',
              'time_note': 'samples span client restarts; sample_time is not a shared timeline'}
    (ROOT / 'results' / 'newbie_motion_2026-10-21.json').write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for name, run in runs.items():
        m = run['meta']
        print(name, {k: m[k] for k in ('x', 'y', 'facing', 'speed', 'sample_time')})
    print('missing_stages', missing)
    print('adjacent_deltas', deltas)


if __name__ == '__main__':
    main()
