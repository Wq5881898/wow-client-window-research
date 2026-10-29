"""Extract range controls from standard SavedVariables; never execute Lua."""
import hashlib
import json
import re

from summarize_target_scenarios import ROOT, SOURCE, scalar_fields


def main():
    raw = SOURCE.read_bytes()
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    runs = {}
    for block in re.split(r'^\t\t\{\n', text, flags=re.M)[1:]:
        match = re.search(r'^\t{3}\["meta"\] = \{\n(.*?)^\t{3}\},', block, re.M | re.S)
        if not match:
            continue
        meta = scalar_fields(match.group(1), 4)
        scene = meta.get('scene', '')
        if not scene.startswith('distance_'):
            continue
        records = [scalar_fields(b, 5) for b in re.split(r'^\t{4}\{\n', block, flags=re.M)[1:]]
        runs[scene] = {'meta': meta, 'observations': {
            r['probe_id']: r for r in records if r.get('probe_id') in (
                'G4.name.target', 'G4.guid.target', 'G4.range.target',
                'G4.health.player', 'G4.combat.player', 'G3.pos_raw') and '#' not in r.get('api', '')}}
    for scene, run in runs.items():
        print(scene, {k: v.get('value', v.get('value_status')) for k, v in run['observations'].items()})
    valid = ('distance_near', 'distance_far', 'distance_farther_4s', 'distance_recovered')
    guids = {runs[s]['observations']['G4.guid.target'].get('value') for s in valid}
    if len(guids) != 1 or None in guids:
        raise ValueError('range comparison must retain the same target GUID')
    for scene, expected in zip(valid, (1, 1, None, 1)):
        if runs[scene]['observations']['G4.range.target'].get('value') != expected:
            raise ValueError('unexpected range state: ' + scene)
    result = {'source_sha256': hashlib.sha256(raw).hexdigest(),
              'excluded_scenes': {'distance_back_2s': 'target cleared by Escape; not a range control'},
              'limitations': ['farther sample includes falling/lava and vertical displacement',
                              'GM mode enabled; not representative of ordinary character survival',
                              'latest run per scene; raw SavedVariables retains earlier attempts'],
              'runs': runs}
    (ROOT / 'results' / 'distance_scenarios_2026-10-21.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
