"""Compare the three explicitly selected frame traces, retaining source hashes."""
import hashlib
import json
from summarize_target_scenarios import ROOT


def main():
    ids = ('1793160660040551800', '1793162694384670000', '1793163000287441400')
    rows = []
    for run_id in ids:
        path = ROOT / 'results' / f'framemotion_{run_id}_trace.json'
        raw = path.read_bytes()
        data = json.loads(raw)
        assert data['status'] == 'COMPLETED'
        frames = data['frames']
        moving = [i for i, f in enumerate(frames) if f['speed'] > 0]
        assert moving == list(range(moving[0], moving[-1] + 1)), 'Multiple motion segments'
        assert data['input']['keydown_sent'] == data['input']['keyup_sent'] == 1
        assert abs(data['summary']['trace_dy'] - data['summary']['snapshot_dy']) < 2e-9
        rows.append({'source': path.name, 'sha256': hashlib.sha256(raw).hexdigest(),
                     'host_seconds': data['input']['keydown_start_to_keyup_start_seconds'],
                     **data['summary']})
    result = {'runs': rows,
              'snapshot_dy_range': max(r['snapshot_dy'] for r in rows) - min(r['snapshot_dy'] for r in rows),
              'moving_frame_counts': sorted({r['moving_frame_count'] for r in rows}),
              'scope': 'three selected traces; no causal attribution from unchanged frame counts'}
    (ROOT / 'results/frame_motion_repeats_2026-10-28.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
