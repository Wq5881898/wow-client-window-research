"""The standard acceptance of the client route in one run.

The run is: restart the client, enter the world, close the combat loop,
make the character die in the danger zone, recover it, walk back to the
graveyard, die a second time on the way, and check the state after a log
in. Every part is a script of its own and writes its own result, and the
run reports which parts were done.

The session of the machine is rebuilt from time to time, so the run is
repeated while it does not finish.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'
LOG = OUT / 'full-acceptance.txt'
SUMMARY = ROOT / 'results' / 'client_full_acceptance.json'

STEPS = [
    ('restart', 'lab_client_restart.py', []),
    ('enter', 'lab_client_enter_character.py', ['--character', 'Probehuman']),
    ('combat', 'lab_client_combat_loop.py', []),
    ('danger_setup', 'lab_client_danger_setup.py',
     ['--walk-to', '0.50390', '0.44147']),
    ('danger_recovery', 'lab_client_danger_recovery.py', ['--die-again']),
    ('relogin', 'lab_client_relogin_verify.py', ['--character', 'Probehuman']),
]

# The file name each step writes its result under.
RESULT_PREFIX = {
    'restart': 'client_restart_',
    'enter': 'client_enter_',
    'combat': 'client_combat_',
    'danger_setup': 'client_danger_setup_',
    'danger_recovery': 'client_danger_recovery_',
    'relogin': 'client_relogin_',
}

# What a step has to show before the chain counts as done.
REQUIRED = {
    'combat': lambda result: (result.get('status') == 'COMBAT_LOOP_COMPLETED'
                              and result.get('outcome') == 'target_defeated'),
    'danger_setup': lambda result: result.get('status') == 'DEAD',
    'danger_recovery': lambda result: result.get('status') == 'RECOVERED',
    'relogin': lambda result: result.get('status') == 'VERIFIED',
}


def problems_of(record):
    """The steps that did not show what the chain promised.

    The exit code of a step is not enough: a fight that ended with a
    retreat returns zero as well. Every step that has a post condition is
    checked against the result it wrote.
    """
    problems = []
    for step in record['steps']:
        check = REQUIRED.get(step['step'])
        if check is None or not step.get('result'):
            continue
        result = read(step['result'])
        if result is None:
            problems.append(step['step'] + ': the result is unreadable')
        elif not check(result):
            problems.append('%s: %s' % (step['step'], result.get('status')))
    return problems


def note(text):
    with LOG.open('a', encoding='utf-8') as stream:
        stream.write(text + '\n')


def wait_for_window(timeout=150.0):
    import lab_driver5 as d
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            d.game_window()
            return True
        except Exception:
            time.sleep(3.0)
    return False


def run(script, argv):
    command = [sys.executable.replace('python.exe', 'pythonw.exe'), '-X', 'utf8',
               str(ROOT / 'scripts' / script)] + argv
    return subprocess.run(command, cwd=str(ROOT)).returncode


def results_of(prefix):
    """The result files of the given kind with their time."""
    files = sorted((ROOT / 'results').glob(prefix + '*.json'),
                   key=lambda p: p.stat().st_mtime)
    return files


def latest(prefix):
    files = results_of(prefix)
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text(encoding='utf-8'))
    except Exception:
        return None


def read(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception:
        return None


def main():
    LOG.write_text('', encoding='utf-8')
    attempts = 5
    report = {'run': 'client_full_acceptance_' + str(time.time_ns()),
              'attempts': [], 'status': 'FAILED'}
    for attempt in range(1, attempts + 1):
        note('== attempt %d of %d ==' % (attempt, attempts))
        record = {'attempt': attempt, 'steps': []}
        failed = False
        for name, script, argv in STEPS:
            if name == 'enter' and not wait_for_window():
                record['steps'].append({'step': name, 'code': None,
                                        'error': 'no client window'})
                failed = True
                break
            # The result of the step is the file that the step wrote, so the
            # report can point at it and not at the newest file of the kind.
            before = set(results_of(RESULT_PREFIX[name]))
            code = run(script, argv)
            fresh = [path for path in results_of(RESULT_PREFIX[name])
                     if path not in before]
            path = str(fresh[-1]) if fresh else None
            record['steps'].append({'step': name, 'code': code,
                                    'result': path})
            note('   %s -> %s' % (name, code))
            if code != 0:
                failed = True
                break
        # The exit code of a step is not enough: the step has to show what
        # the chain promises. A fight that ended with a retreat is not a
        # fight that was won.
        problems = problems_of(record)
        record['problems'] = problems
        report['attempts'].append(record)
        if not failed and not problems:
            report['status'] = 'ACCEPTED'
            break
        note('   the attempt failed, the run starts again')
    report['combat'] = latest('client_combat_')
    report['danger_recovery'] = latest('client_danger_recovery_')
    report['relogin'] = latest('client_relogin_')
    # The report of a run is written under the name of the run, so a later
    # run does not overwrite the evidence of this one.
    path = ROOT / 'results' / ('client_full_acceptance_%s.json' % report['run'])
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                    encoding='utf-8')
    report['report'] = str(path)
    SUMMARY.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                       encoding='utf-8')
    note('status %s' % report['status'])
    return 0 if report['status'] == 'ACCEPTED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
