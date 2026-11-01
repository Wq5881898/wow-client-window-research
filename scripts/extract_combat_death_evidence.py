"""Extract one historical scene without requiring alive/noncombat acceptance."""
import hashlib
import json
import re
from pathlib import Path

from summarize_target_scenarios import scalar_fields

ROOT = Path(__file__).resolve().parents[1]
RUN = 'client_combat_1793257929895289600'


def main():
    source = ROOT / '.cache' / 'client-observations' / (RUN + '.lua')
    raw = source.read_bytes()
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    scenes = []
    for block in re.split(r'^\t{2}\{\n', text, flags=re.M)[1:]:
        match = re.search(r'^\t{3}\["meta"\] = \{\n(.*?)^\t{3}\},', block, re.M | re.S)
        if not match:
            continue
        meta = scalar_fields(match.group(1), 4)
        if meta.get('scene') != RUN + '_snapshot':
            continue
        records = [scalar_fields(b, 5) for b in re.split(r'^\t{4}\{\n', block, flags=re.M)[1:]]
        scenes.append({'meta': meta, 'player_observations': [r for r in records if
                       r.get('probe_id') in ('G4.name.player', 'G4.dead.player',
                       'G4.combat.player', 'G4.health.player', 'G4.healthmax.player',
                       'G4.power.player', 'G4.powermax.player', 'G4.name.target')]})
    if len(scenes) != 1:
        raise ValueError('expected one exact historical scene')
    files = [source, ROOT / 'results' / (RUN + '.json')]
    files += [ROOT / '.cache' / 'desktop-check' / name for name in (
        RUN + '_cast-request.png', RUN + '_after-cast.png', RUN + '_snapshot.png',
        'combat-final-check.png', 'recovery-confirmed.png')]
    result = {'schema': 'client-combat-death-evidence-v1', 'run_id': RUN,
              'scope': 'historical extraction, not a new experiment or success acceptance',
              'scene': scenes[0], 'evidence_files': []}
    for path in files:
        data = path.read_bytes()
        result['evidence_files'].append({'path': str(path.relative_to(ROOT)),
            'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    output = ROOT / 'results' / (RUN + '_death_evidence.json')
    with output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(output)


if __name__ == '__main__':
    main()
