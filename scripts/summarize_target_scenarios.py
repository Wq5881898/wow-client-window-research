"""Summarize Blizzard-formatted SavedVariables without executing Lua."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a\WTF\Account\GM01\AzerothCore\Syra\SavedVariables\WowProbeWotLK.lua')
SCENES = ('target_none_control', 'target_self_control', 'target_npc_lothos',
          'target_cleared_control')


def scalar_fields(text, indent):
    fields = {}
    pattern = r'^' + '\t' * indent + r'\["([^"\n]+)"\] = ("(?:[^"\\]|\\.)*"|true|false|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?),$'
    for key, value in re.findall(pattern, text, re.M):
        fields[key] = json.loads(value)
    return fields


def main():
    raw = SOURCE.read_bytes()
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    runs = {}
    for block in re.split(r'^\t\t\{\n', text, flags=re.M)[1:]:
        meta_match = re.search(r'^\t{3}\["meta"\] = \{\n(.*?)^\t{3}\},', block, re.M | re.S)
        if not meta_match:
            continue
        meta = scalar_fields(meta_match.group(1), 4)
        scene = meta.get('scene')
        if scene not in SCENES:
            continue
        records = [scalar_fields(record, 5) for record in
                   re.split(r'^\t\t\t\t\{\n', block, flags=re.M)[1:]]
        records = [r for r in records if 'probe_id' in r]
        runs[scene] = {
            'meta': meta,
            'record_count': len(records),
            'target': {r['probe_id']: r for r in records if '#' not in r['api']
                       if r['probe_id'].startswith('G4.') and
                       r['probe_id'].endswith('.target')},
            'target_additional_returns': [r for r in records if '#' in r['api']
                                          and r['probe_id'].endswith('.target')],
            'events': [r for r in records if r['probe_id'].startswith('EVT.')],
        }
    if set(runs) != set(SCENES):
        raise ValueError('Missing scenes: ' + str(set(SCENES) - set(runs)))
    expected = [None, 'Syra', 'Lothos Riftwaker', None]
    for scene, name in zip(SCENES, expected):
        run = runs[scene]
        actual = run['target']['G4.name.target'].get('value')
        if actual != name or run['record_count'] < 84:
            raise ValueError(f'{scene}: unexpected target/count {actual!r}')
    result = {
        'source': str(SOURCE),
        'source_sha256': hashlib.sha256(raw).hexdigest(),
        'scope': 'local AzerothCore 3.3.5a; external chat commands; read-only add-on',
        'parser': 'Blizzard SavedVariables indentation; scalar fields only',
        'runs': runs,
    }
    output = ROOT / 'results' / 'target_scenarios_2026-10-20.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for scene, run in runs.items():
        target = run['target']
        print(scene, 'records=', run['record_count'],
              'name=', target['G4.name.target'].get('value'),
              'health=', target['G4.health.target'].get('value'),
              'events=', [e['api'] for e in run['events']])
    print(output)


if __name__ == '__main__':
    main()
