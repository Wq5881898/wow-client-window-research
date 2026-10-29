"""Validate same-run stationary samples without executing SavedVariables Lua."""
import hashlib
import json
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
        if not scene.startswith('newbie_continuous_'):
            continue
        records = [scalar_fields(b, 5) for b in re.split(r'^\t{4}\{\n', block, flags=re.M)[1:]]
        observations = {r['probe_id']: r for r in records if r.get('probe_id') in (
            'G4.name.player', 'G4.health.player', 'G4.combat.player', 'G4.name.target', 'G3.subzone')}
        assert observations['G4.name.player']['value'] == 'Probehuman'
        assert observations['G4.health.player']['value'] == 52
        assert observations['G4.combat.player']['value_status'] == 'NIL'
        assert observations['G4.name.target']['value_status'] == 'NIL'
        assert observations['G3.subzone']['value'] == 'Northshire Valley'
        assert meta['speed'] == 0 and 0 < meta['x'] < 1 and 0 < meta['y'] < 1
        runs[scene] = {'meta': meta, 'observations': observations}
    scenes = ['newbie_continuous_' + str(i) for i in range(1, 4)]
    assert set(runs) == set(scenes), 'Missing or unexpected scenes'
    baseline = runs[scenes[0]]['meta']
    deltas = []
    previous_time = baseline['sample_time'] - 1
    for scene in scenes:
        m = runs[scene]['meta']
        assert m['sample_time'] > previous_time
        previous_time = m['sample_time']
        delta = {k: m[k] - baseline[k] for k in ('x', 'y', 'facing')}
        assert all(v == 0 for v in delta.values()), (scene, delta)
        deltas.append({'scene': scene, 'elapsed': m['sample_time'] - baseline['sample_time'], **delta})
    output = {'source_sha256': hashlib.sha256(raw).hexdigest(), 'runs': runs,
              'baseline_deltas': deltas, 'checks_passed': True,
              'scope': 'three same-script stationary snapshots; reload only after final sample; not continuous telemetry'}
    path = ROOT / 'results' / 'newbie_continuous_2026-10-24.json'
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(deltas, ensure_ascii=False, indent=2))
    print('checks passed:', path)


if __name__ == '__main__':
    main()
