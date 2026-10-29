"""Compare fixed adjacent-duration traces without assuming causal quantization."""
import json
from summarize_target_scenarios import ROOT


def main():
    ids = ('1793164241132578100', '1793163000287441400', '1793164554469934200')
    rows = []
    for run_id in ids:
        filename = f'framemotion_{run_id}_trace.json'
        data = json.loads((ROOT / 'results' / filename).read_text(encoding='utf-8'))
        assert data['status'] == 'COMPLETED'
        frames = data['frames']
        moving = [i for i, f in enumerate(frames) if f['speed'] > 0]
        assert moving == list(range(moving[0], moving[-1] + 1))
        assert abs(data['summary']['trace_dy'] - data['summary']['snapshot_dy']) < 2e-9
        rows.append({'source': filename, 'requested_seconds': data['input']['requested_seconds'],
                     'host_seconds': data['input']['keydown_start_to_keyup_start_seconds'],
                     **data['summary']})
    result = {'runs': rows, 'scope': 'one selected trace per duration; normalized map coordinates',
              'adjacent_abs_dy_increases': [abs(b['snapshot_dy']) - abs(a['snapshot_dy']) for a, b in zip(rows, rows[1:])]}
    (ROOT / 'results/frame_duration_comparison_2026-10-28.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
