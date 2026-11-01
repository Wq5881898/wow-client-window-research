"""Offline acceptance of a unique SavedVariables scene; never executes Lua/input."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from summarize_target_scenarios import scalar_fields


def inspect(raw, scene, character, expected_target=None):
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    matches = []
    for block in re.split(r'^\t{2}\{\n', text, flags=re.M)[1:]:
        match = re.search(r'^\t{3}\["meta"\] = \{\n(.*?)^\t{3}\},', block, re.M | re.S)
        if not match:
            continue
        meta = scalar_fields(match.group(1), 4)
        if meta.get('scene') != scene:
            continue
        records = [scalar_fields(b, 5) for b in re.split(r'^\t{4}\{\n', block, flags=re.M)[1:]]
        ids = ('G4.name.player', 'G4.health.player', 'G4.combat.player', 'G4.name.target', 'G3.subzone')
        obs = {}
        for record in records:
            key = record.get('probe_id')
            if key in ids:
                if key in obs:
                    raise ValueError('duplicate probe: ' + key)
                obs[key] = record
        if set(obs) != set(ids):
            raise ValueError('missing required probes')
        if obs['G4.name.player'].get('value') != character:
            raise ValueError('character mismatch')
        health = obs['G4.health.player'].get('value')
        if not isinstance(health, (int, float)) or isinstance(health, bool) or health <= 0:
            raise ValueError('character not alive')
        if obs['G4.combat.player'].get('value_status') != 'NIL':
            raise ValueError('combat or unknown combat state')
        target = obs['G4.name.target']
        if expected_target is None:
            if target.get('value_status') != 'NIL':
                raise ValueError('target not clear')
        elif target.get('value_status') != 'OK' or target.get('value') != expected_target:
            raise ValueError('target mismatch')
        if obs['G3.subzone'].get('value') != 'Northshire Valley':
            raise ValueError('unexpected subzone')
        for key in ('x', 'y', 'facing', 'speed', 'sample_time'):
            value = meta.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError('invalid numeric field: ' + key)
        if not (0 < meta['x'] < 1 and 0 < meta['y'] < 1) or meta['speed'] != 0:
            raise ValueError('invalid map position or not stationary')
        matches.append({'meta': meta, 'observations': obs})
    if len(matches) != 1:
        raise ValueError('exactly one unique scene required')
    return {'status': 'SNAPSHOT_ACCEPTED', 'sample': matches[0],
            'source_sha256': hashlib.sha256(raw).hexdigest(), 'movement_issued': False,
            'scope': 'persisted snapshot only; scene matching does not prove current live state'}


def inspect_displacement(before, after):
    """Compare accepted stationary snapshots; map deltas are not world yards."""
    first = before['sample']['meta']
    last = after['sample']['meta']
    if last['sample_time'] <= first['sample_time']:
        raise ValueError('movement sample not newer than baseline')
    dx, dy = last['x'] - first['x'], last['y'] - first['y']
    distance = math.hypot(dx, dy)
    if distance <= 1e-7:
        raise ValueError('no observable displacement')
    return {'status': 'DISPLACEMENT_VERIFIED', 'dx': dx, 'dy': dy,
            'normalized_map_distance': distance, 'units': 'normalized map coordinates'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--scene', required=True)
    parser.add_argument('--character', default='Probehuman')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = inspect(args.source.read_bytes(), args.scene, args.character)
    except (ValueError, OSError) as exc:
        result = {'status': 'REJECTED', 'error': str(exc), 'movement_issued': False}
    # Never overwrite an experiment result.
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'SNAPSHOT_ACCEPTED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
