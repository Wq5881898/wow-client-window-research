"""Compare independent compensated trials and verify between-trial continuity."""
import json
import statistics
from summarize_target_scenarios import ROOT


def main():
    rows = []
    previous = None
    first = None
    for trial in range(1, 4):
        path = ROOT / 'results' / f'newbie_compensated_trial{trial}_2026-10-28.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        prefix = f'newbie_compensated_trial{trial}_'
        baseline = data['runs'][prefix + 'baseline']['meta']
        final = data['runs'][prefix + 'final']['meta']
        first = first or baseline
        gap = {k: baseline[k] - previous[k] for k in ('x', 'y', 'facing')} if previous else None
        if gap:
            assert all(v == 0 for v in gap.values()), gap
            assert baseline['sample_time'] > previous['sample_time']
        rows.append({'trial': trial, 'residual': data['return_residual'],
                     'between_trial_delta': gap,
                     'reduction_fraction': data['comparison']['residual_reduction_fraction']})
        previous = final
    dy = [r['residual']['dy'] for r in rows]
    output = {'trials': rows, 'mean_abs_dy': statistics.mean(abs(v) for v in dy),
              'max_abs_dy': max(abs(v) for v in dy),
              'cumulative_delta': {k: previous[k] - first[k] for k in ('x', 'y', 'facing')},
              'elapsed_seconds': previous['sample_time'] - first['sample_time'],
              'scope': 'three trials, reload between trials, normalized map coordinates'}
    (ROOT / 'results' / 'newbie_compensated_repeats_2026-10-28.json').write_text(
        json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
