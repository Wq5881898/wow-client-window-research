"""Three bounded forward pulses with host timing and persisted position samples."""
import ctypes
import argparse
import json
import statistics
import time

import lab_driver5 as d
from lab_feedback_correction import capture
from summarize_target_scenarios import ROOT


def timed_hold(hwnd, seconds, row):
    if d.win32gui.GetForegroundWindow() != hwnd:
        raise RuntimeError('Game not foreground')
    i = d.INPUT()
    i.type = 1
    i.union.ki = d.KEYBDINPUT(0x57, 0, 0, 0, None)
    start = time.perf_counter()
    try:
        row['keydown_sent'] = d.SendInput(1, ctypes.byref(i), ctypes.sizeof(i))
        down_done = time.perf_counter()
        row['keydown_call_seconds'] = down_done - start
        if row['keydown_sent'] != 1:
            raise RuntimeError('Key down failed')
        time.sleep(seconds)
    finally:
        before_up = time.perf_counter()
        i.union.ki.dwFlags = 2
        row['keyup_sent'] = d.SendInput(1, ctypes.byref(i), ctypes.sizeof(i))
        end = time.perf_counter()
        row['keydown_start_to_keyup_start_seconds'] = before_up - start
        row['keyup_call_seconds'] = end - before_up
        if row['keyup_sent'] != 1:
            raise RuntimeError('Key up failed')
    time.sleep(0.8)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repeat96', action='store_true')
    args = parser.parse_args()
    durations = (0.09642223536365996,) * 3 if args.repeat96 else (0.05, 0.10, 0.15)
    prefix = 'shortinput_' + str(time.time_ns()) + '_'
    path = ROOT / 'results' / (prefix + 'calibration.json')
    result = {'prefix': prefix, 'status': 'STARTED', 'pulses': [],
              'mode': 'repeat96' if args.repeat96 else 'three_durations',
              'scope': 'host SendInput call timing, not client key receipt timing; normalized map coordinates'}
    def save():
        path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    save()
    try:
        hwnd = d.find_game_window()
        if not hwnd:
            raise RuntimeError('No game window')
        d.ensure_foreground(hwnd)
        previous = capture(hwnd, 'baseline', prefix)
        result['baseline'] = previous
        assert abs(previous['meta']['facing']) < 0.01
        for index, seconds in enumerate(durations, 1):
            row = {'requested_seconds': seconds}
            result['pulses'].append(row)
            save()
            timed_hold(hwnd, seconds, row)
            save()
            current = capture(hwnd, 'pulse' + str(index), prefix)
            row['sample'] = current
            a, b = previous['meta'], current['meta']
            row['delta'] = {k: b[k] - a[k] for k in ('x', 'y', 'facing')}
            assert b['sample_time'] > a['sample_time']
            assert abs(row['delta']['x']) <= 5e-6 and abs(row['delta']['facing']) <= 0.01
            assert row['delta']['y'] < 0, 'No forward displacement'
            row['dy_per_requested_second'] = row['delta']['y'] / seconds
            row['dy_per_host_second'] = row['delta']['y'] / row['keydown_start_to_keyup_start_seconds']
            previous = current
            save()
        result['final'] = capture(hwnd, 'final', prefix)
        result['stationary_delta'] = {k: result['final']['meta'][k] - previous['meta'][k] for k in ('x', 'y', 'facing')}
        assert all(v == 0 for v in result['stationary_delta'].values())
        if args.repeat96:
            dy = [r['delta']['y'] for r in result['pulses']]
            host = [r['keydown_start_to_keyup_start_seconds'] for r in result['pulses']]
            result['repeat_statistics'] = {
                'mean_dy': statistics.mean(dy), 'range_dy': max(dy) - min(dy),
                'sample_stdev_dy': statistics.stdev(dy),
                'host_seconds_min': min(host), 'host_seconds_max': max(host),
                'expected_dy_from_previous_calibration': -0.00029155611991876773,
                'prediction_errors_dy': [v + 0.00029155611991876773 for v in dy],
            }
        result['status'] = 'COMPLETED'
        save()
        d.log('short input result', str(path))
    except Exception as exc:
        result['status'] = 'FAILED'
        result['error'] = str(exc)
        save()
        raise


if __name__ == '__main__':
    main()
