"""One bounded client observation task; run on the interactive desktop."""
import hashlib
import argparse
import json
import time
from pathlib import Path

import lab_driver5 as d
from client_snapshot_task import inspect, inspect_displacement
from lab_distance_scenarios import command, hold
from lab_newbie_roundtrip import sample

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a\WTF\Account\GM01\AzerothCore\Probehuman\SavedVariables\WowProbeWotLK.lua')


def main():
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--target-cycle', action='store_true')
    modes.add_argument('--forward-step', action='store_true')
    args = parser.parse_args()
    run_id = 'client_observe_' + str(time.time_ns())
    output = ROOT / 'results' / (run_id + '.json')
    result = {'run_id': run_id, 'status': 'STARTED', 'movement_issued': False,
              'stages': [], 'source': str(SOURCE)}

    def save():
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

    save()
    try:
        hwnd = d.find_game_window()
        if not hwnd:
            raise RuntimeError('no window in this interactive session')
        d.ensure_foreground(hwnd)
        if d.win32gui.GetForegroundWindow() != hwnd:
            raise RuntimeError('foreground not acquired')
        result['stages'].append('WINDOW_READY')
        before = SOURCE.read_bytes() if SOURCE.exists() else b''
        result['before_sha256'] = hashlib.sha256(before).hexdigest()
        sample(hwnd, 'snapshot', run_id + '_')
        result['stages'].append('SAMPLE_REQUESTED')
        save()
        requested = time.time_ns()
        command(hwnd, '/reload')
        deadline = time.monotonic() + 40
        scene = run_id + '_snapshot'
        last_candidate = None
        result['transient_read_errors'] = 0
        while time.monotonic() < deadline:
            try:
                if SOURCE.exists() and SOURCE.stat().st_mtime_ns >= requested:
                    raw = SOURCE.read_bytes()
                    if raw != before and scene.encode() in raw:
                        digest = hashlib.sha256(raw).hexdigest()
                        if digest == last_candidate:
                            break
                        last_candidate = digest
            except (PermissionError, FileNotFoundError):
                result['transient_read_errors'] += 1
            time.sleep(1)
        else:
            raise TimeoutError('fresh persisted scene not received within 40 seconds')
        result['stages'].append('FRESH_PERSISTED_SCENE')
        backup = ROOT / '.cache' / 'client-observations' / (run_id + '.lua')
        backup.parent.mkdir(parents=True, exist_ok=True)
        with backup.open('xb') as handle:
            handle.write(raw)
        result['local_raw_backup'] = str(backup)
        result['acceptance'] = inspect(raw, scene, 'Probehuman')
        result['stages'].append('ACCEPTED')
        if args.target_cycle or args.forward_step:
            stage_key = 'target_cycle' if args.target_cycle else 'forward_step'
            result[stage_key] = []
            actions = (('self', '/targetexact Probehuman', 'Probehuman'),
                       ('cleared', '/cleartarget', None)) if args.target_cycle else (
                           ('moved', 'HOLD_W_0.2_SECONDS', None),)
            for label, action, target in actions:
                # The previous reload must finish before issuing another chat command.
                time.sleep(10)
                if d.win32gui.GetForegroundWindow() != hwnd:
                    raise RuntimeError('foreground lost before action')
                result[stage_key].append({'stage': label, 'action_requested': action})
                save()
                if args.forward_step:
                    result['movement_issued'] = True
                    save()
                    hold(0x57, 0.2)
                else:
                    command(hwnd, action)
                result[stage_key][-1]['action_returned'] = True
                save()
                sample(hwnd, label, run_id + '_')
                action_requested = time.time_ns()
                command(hwnd, '/reload')
                until = time.monotonic() + 40
                previous_digest = None
                while time.monotonic() < until:
                    try:
                        if SOURCE.stat().st_mtime_ns >= action_requested:
                            current_raw = SOURCE.read_bytes()
                            if (run_id + '_' + label).encode() in current_raw:
                                digest = hashlib.sha256(current_raw).hexdigest()
                                if digest == previous_digest:
                                    break
                                previous_digest = digest
                    except (PermissionError, FileNotFoundError):
                        result['transient_read_errors'] += 1
                    time.sleep(1)
                else:
                    raise TimeoutError('fresh target stage not persisted: ' + label)
                stage_backup = backup.with_name(run_id + '_' + label + '.lua')
                with stage_backup.open('xb') as handle:
                    handle.write(current_raw)
                result[stage_key][-1].update(
                    acceptance=inspect(current_raw, run_id + '_' + label, 'Probehuman', target),
                    local_raw_backup=str(stage_backup))
                save()
            if args.forward_step:
                result['displacement'] = inspect_displacement(
                    result['acceptance'], result[stage_key][-1]['acceptance'])
                result['stages'].append('FORWARD_STEP_VERIFIED')
            else:
                result['stages'].append('TARGET_CYCLE_VERIFIED')
        result['status'] = 'COMPLETED'
        time.sleep(10)
        d.screenshot(run_id + '_after-reload.png')
        save()
        d.log('client observation result', str(output), result['status'])
        return 0
    except Exception as exc:
        result['status'] = 'FAILED'
        result['error'] = f'{type(exc).__name__}: {exc}'
        save()
        d.log('client observation result', str(output), result['error'])
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
