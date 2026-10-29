"""Validate observed walking speed and post-toggle running recovery."""
import json
from summarize_target_scenarios import ROOT


def main():
    rows = []
    for label, run_id, speed in (
        ('run_control', '1793163000287441400', 7.0),
        ('walk', '1793165607701264100', 2.5),
        ('restored_run', '1793166009480494200', 7.0),
    ):
        name = f'framemotion_{run_id}_trace.json'
        data = json.loads((ROOT / 'results' / name).read_text(encoding='utf-8'))
        assert data['status'] == 'COMPLETED'
        assert data['summary']['positive_speed_values'] == [speed]
        assert data['input']['requested_seconds'] == 0.09642223536365996
        rows.append({'label': label, 'source': name, **data['summary']})
    ratio = abs(rows[1]['snapshot_dy'] / rows[0]['snapshot_dy'])
    result = {'runs': rows, 'walk_run_displacement_ratio': ratio,
              'displacement_reduction_fraction': 1-ratio,
              'base_speed_ratio': 2.5/7, 'restored_run_speed_verified': True,
              'scope': 'single walking sample; normalized map coordinates; not minimum-step calibration'}
    (ROOT / 'results/walk_comparison_2026-10-28.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
