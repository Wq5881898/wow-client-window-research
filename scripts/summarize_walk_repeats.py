"""Three fixed walking traces and independent run-mode recovery."""
import json
import statistics
from summarize_target_scenarios import ROOT


def main():
    rows = []
    for run_id in ('1793165607701264100', '1793169990334700100', '1793170325831435300'):
        name = f'framemotion_{run_id}_trace.json'
        data = json.loads((ROOT / 'results' / name).read_text(encoding='utf-8'))
        assert data['status'] == 'COMPLETED'
        assert data['summary']['positive_speed_values'] == [2.5]
        assert data['restore_toggle_sent']
        assert data['input']['requested_seconds'] == 0.09642223536365996
        assert abs(data['summary']['trace_dy'] - data['summary']['snapshot_dy']) < 2e-9
        rows.append({'source': name, 'host_seconds': data['input']['keydown_start_to_keyup_start_seconds'], **data['summary']})
    restored_name = 'framemotion_1793170669162135700_trace.json'
    restored = json.loads((ROOT / 'results' / restored_name).read_text(encoding='utf-8'))
    assert restored['status'] == 'COMPLETED'
    assert restored['summary']['positive_speed_values'] == [7.0]
    dy = [r['snapshot_dy'] for r in rows]
    result = {'runs': rows, 'mean_dy': statistics.mean(dy),
              'range_dy': max(dy) - min(dy), 'sample_stdev_dy': statistics.stdev(dy),
              'recovery_source': restored_name, 'recovery_summary': restored['summary'],
              'scope': 'three walking samples at different starting positions; displacement spread, not return error'}
    (ROOT / 'results/walk_repeats_2026-10-28.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
