"""Summarize normalized map position samples, without converting to yards."""
import hashlib
import json
import math
import re

from summarize_target_scenarios import ROOT, SOURCE, scalar_fields


def main():
    raw = SOURCE.read_bytes()
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    runs = {}
    for block in re.split(r'^\t{2}\{\n', text, flags=re.M)[1:]:
        match = re.search(r'^\t{3}\["meta"\] = \{\n(.*?)^\t{3}\},', block, re.M | re.S)
        if not match:
            continue
        meta = scalar_fields(match.group(1), 4)
        scene = meta.get('scene', '')
        if not scene.startswith('flat_'):
            continue
        records = [scalar_fields(b, 5) for b in re.split(r'^\t{4}\{\n', block, flags=re.M)[1:]]
        runs[scene] = {'meta': meta, 'observations': {
            r['probe_id']: r for r in records if r.get('probe_id') in (
                'G4.health.player', 'G4.combat.player', 'G4.name.target', 'G3.zone', 'G3.subzone')}}
    def delta(a, b):
        am, bm = runs[a]['meta'], runs[b]['meta']
        return [bm['motion_x'] - am['motion_x'], bm['motion_y'] - am['motion_y']]
    forward = delta('flat_setup', 'flat_forward')
    back = delta('flat_forward', 'flat_back')
    residual = delta('flat_setup', 'flat_back')
    stationary = delta('flat_back', 'flat_stationary')
    if math.hypot(*forward) == 0 or math.hypot(*back) == 0:
        raise ValueError('movement not observed')
    if sum(a * b for a, b in zip(forward, back)) >= 0:
        raise ValueError('return movement is not opposite')
    result = {'source_sha256': hashlib.sha256(raw).hexdigest(), 'runs': runs,
              'normalized_map_deltas': {'forward': forward, 'back': back, 'residual': residual,
                                        'stationary': stationary},
              'limitations': ['normalized map units are not yards',
                              'motion metadata captured after snapshot via external /run',
                              'GM mode remains on; one sample per direction']}
    output = ROOT / 'results' / 'flat_motion_2026-10-21.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
