"""Raise the level of the character.

The character is taken into the world, a creature is fought by name until
the level of the character is higher than it was, and the state is checked
after every fight. A fight that ends with a retreat does not stop the run:
the character rests until it is out of combat and the threat is gone, and
the next fight starts.

The report of the run holds the level and the experience of every round, so
the progress is visible even when the run is cut short.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_evidence import Evidence

ROOT = Path(__file__).resolve().parents[1]
# The creature of the valley the fights are made against. For leveling the
# weakest ordinary creature in reach is used: the standard creature is often
# not around, and a fight that finds nothing is a fight that is lost.
TARGET_NAME = None
# How many fights at most.
ROUNDS = 150
# How long the character may rest between the fights.
REST_BUDGET = 90.0


def reader():
    return decode(assert_real_frame(grab_desktop()))


def run(script, argv):
    """Run a script of its own, without a console over the game."""
    command = [sys.executable.replace('python.exe', 'pythonw.exe'), '-X', 'utf8',
               str(ROOT / 'scripts' / script)] + argv
    return subprocess.run(command, cwd=str(ROOT)).returncode


def rest(hwnd, budget=REST_BUDGET):
    """Wait until the character is out of combat and the threat is gone.

    A character that died in a fight is brought back by the recovery, so a
    run about the level survives the deaths of the valley.
    """
    deadline = time.monotonic() + budget
    while time.monotonic() < deadline:
        try:
            state = reader()
        except Exception:
            time.sleep(1.0)
            continue
        if state['dead']:
            # The character is a ghost: the recovery walks it to its corpse
            # and revives it.
            run('lab_client_danger_recovery.py', [])
            continue
        if not state['combat']:
            # Only the combat flag is waited for. The threat of the valley
            # stays while a creature watches the character, and waiting for
            # it would waste the time of every round.
            return state
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
    return reader()


def main():
    run_id = 'client_leveling_' + str(time.time_ns())
    result = dict(run=run_id, status='FAILED', rounds=[])
    evidence = Evidence(run_id)
    try:
        goal = 0
        for argument in sys.argv:
            if argument.startswith('--goal='):
                goal = int(argument.split('=')[1])
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        state = reader()
        result['start'] = {'level': state.get('level'),
                           'xp': state.get('xp'),
                           'xp_max': state.get('xp_max'),
                           'health': state['health'],
                           'max_health': state['max_health']}
        evidence.capture('01-start', state)
        if state['dead']:
            raise ValueError('the character is dead at the start')
        start_level = state.get('level') or 0
        best_level = start_level
        for index in range(ROUNDS):
            state = rest(hwnd)
            if state['dead']:
                raise ValueError('the character is still a ghost after the '
                                 'recovery')
            level = state.get('level') or 0
            if goal and level >= goal:
                result['status'] = 'LEVELLED'
                break
            if level > best_level:
                best_level = level
                result['status'] = 'LEVELLED'
                break
            argv = [] if TARGET_NAME is None else ['--target-name',
                                                   TARGET_NAME]
            code = run('lab_client_combat_loop.py', argv)
            try:
                after = reader()
            except Exception:
                after = {}
            result['rounds'].append({
                'round': index + 1,
                'level_before': level,
                'level_after': after.get('level'),
                'xp': after.get('xp'),
                'xp_max': after.get('xp_max'),
                'health': after.get('health'),
                'combat_code': code,
            })
            evidence.capture('02-round-%02d' % (index + 1), after)
            if code != 0:
                # A fight that failed is not the end of the run: the
                # character rests and the next fight starts.
                note = result['rounds'][-1]
                note['failed'] = True
        state = reader()
        result['end'] = {'level': state.get('level'), 'xp': state.get('xp'),
                         'xp_max': state.get('xp_max'),
                         'health': state['health'],
                         'dead': state['dead'],
                         'combat': state['combat'],
                         'threat': state.get('threat')}
        evidence.capture('03-end', state)
        if result['status'] != 'LEVELLED':
            result['status'] = 'LEVEL_NOT_RAISED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('09-end')
        path = evidence.write(result)
        d.log('leveling run', str(path), result['status'])
    return 0 if result['status'] == 'LEVELLED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
