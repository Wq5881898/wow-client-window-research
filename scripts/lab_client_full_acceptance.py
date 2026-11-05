"""The standard acceptance of the client route in one run.

The run is: restart the client, enter the world, close the combat loop,
make the character die in the danger zone, recover it, walk back to the
graveyard, die a second time on the way, and check the state after a log
in. Every part is a script of its own and writes its own result, and the
run reports which parts were done.

The session of the machine is rebuilt from time to time, so the run is
repeated while it does not finish.

The results are bound to the run: every step is told the identity of the
run and writes it into its result, and the summary only accepts a result
that carries this identity. A result that is left over from an earlier run
therefore cannot be taken for the result of this one.
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

# Every step of the chain. The fourth field holds the conditions that go
# beyond the status of the step.
STEPS = [
    ('restart', 'lab_client_restart.py', [], {}),
    ('enter', 'lab_client_enter_character.py',
     ['--character', 'Probehuman'], {}),
    ('combat', 'lab_client_combat_loop.py', [], {}),
    ('danger_setup', 'lab_client_danger_setup.py',
     ['--walk-to', '0.50390', '0.44147'], {}),
    ('danger_recovery', 'lab_client_danger_recovery.py', ['--die-again'],
     {'second_death': True}),
    ('relogin', 'lab_client_relogin_verify.py',
     ['--character', 'Probehuman'], {}),
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
    'enter': lambda result: result.get('status') == 'IN_WORLD',
    'combat': lambda result: (result.get('status') == 'COMBAT_LOOP_COMPLETED'
                              and result.get('outcome') == 'target_defeated'),
    'danger_setup': lambda result: result.get('status') == 'DEAD',
    'danger_recovery': lambda result: result.get('status') == 'RECOVERED',
    'relogin': lambda result: result.get('status') == 'VERIFIED',
}

# The conditions that are not the status of the step. The recovery has to
# show a second death of its own, because a run that found no hostile
# creature reports RECOVERED as well.
EXTRA = {
    'danger_recovery': {
        'second_death': lambda result: result.get('second_death') == 'happened',
    },
}


def problems_of(record, parent=None):
    """The steps that did not show what the chain promised.

    The exit code of a step is not enough: a fight that ended with a
    retreat returns zero as well. Every step that has a post condition is
    checked against the result it wrote, and a step that wrote no result
    at all is a problem of its own: a missing result may not be skipped.
    """
    problems = []
    for step in record['steps']:
        name = step['step']
        check = REQUIRED.get(name)
        extra = EXTRA.get(name, {})
        if check is None and not extra:
            continue
        path = step.get('result')
        if not path:
            problems.append(name + ': the step wrote no result file')
            continue
        result = read(path)
        if result is None:
            problems.append(name + ': the result is unreadable')
            continue
        if check is not None and not check(result):
            problems.append('%s: %s' % (name, result.get('status')))
        for key, condition in extra.items():
            if not condition(result):
                problems.append('%s: %s is missing' % (name, key))
        if parent is not None:
            stamped = result.get('parent_run')
            if stamped != parent:
                problems.append('%s: the result belongs to another run (%s)'
                                % (name, stamped))
            elif result.get('run') != Path(path).stem:
                problems.append('%s: the file does not match the run it '
                                'holds' % name)
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


def run(script, argv, parent=None, attempt=None):
    command = [sys.executable.replace('python.exe', 'pythonw.exe'), '-X', 'utf8',
               str(ROOT / 'scripts' / script)] + argv
    if parent is not None:
        command += ['--parent-run', parent]
    if attempt is not None:
        command += ['--attempt', str(attempt)]
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
    run_id = 'client_full_acceptance_' + str(time.time_ns())
    started = time.monotonic()
    report = {'run': run_id, 'attempts': [], 'status': 'FAILED',
              'started_at': time.time()}
    for attempt in range(1, attempts + 1):
        note('== attempt %d of %d ==' % (attempt, attempts))
        record = {'attempt': attempt, 'steps': [], 'started_at': time.time()}
        failed = False
        for name, script, argv, extra in STEPS:
            if name == 'enter' and not wait_for_window():
                record['steps'].append({'step': name, 'code': None,
                                        'error': 'no client window'})
                failed = True
                break
            # The result of the step is the file that the step wrote, so the
            # report can point at it and not at the newest file of the kind.
            before = set(results_of(RESULT_PREFIX[name]))
            code = run(script, argv, parent=run_id, attempt=attempt)
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
        problems = problems_of(record, run_id)
        record['problems'] = problems
        record['duration'] = round(time.monotonic() - started, 1)
        report['attempts'].append(record)
        if not failed and not problems:
            report['status'] = 'ACCEPTED'
            report['accepted_attempt'] = attempt
            break
        note('   the attempt failed, the run starts again')
    report['duration'] = round(time.monotonic() - started, 1)
    # The results of the steps of this run are the ones the steps wrote.
    # Nothing else is copied into the report, so the report cannot show a
    # result of another run.
    report['results'] = {}
    for attempt in report['attempts']:
        for step in attempt['steps']:
            path = step.get('result')
            if not path:
                continue
            result = read(path)
            if result is None:
                continue
            report['results'][step['step']] = {
                'path': path,
                'status': result.get('status'),
                'outcome': result.get('outcome'),
                'parent_run': result.get('parent_run'),
            }
    # The report of a run is written under the name of the run, so a later
    # run does not overwrite the evidence of this one.
    path = ROOT / 'results' / ('client_full_acceptance_%s.json' % report['run'])
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                    encoding='utf-8')
    report['report'] = str(path)
    # The fixed entry is only an index. The evidence of a run stays in the
    # report of that run, and the index points at it.
    index = {'run': report['run'], 'status': report['status'],
             'report': str(path), 'duration': report['duration'],
             'accepted_attempt': report.get('accepted_attempt'),
             'attempts': [{'attempt': attempt['attempt'],
                           'problems': attempt['problems'],
                           'duration': attempt['duration'],
                           'steps': [{'step': step['step'],
                                      'code': step.get('code'),
                                      'result': step.get('result')}
                                     for step in attempt['steps']]}
                          for attempt in report['attempts']],
             'reports': sorted(str(item) for item in
                               results_of('client_full_acceptance_')
                               if item.name != path.name)}
    SUMMARY.write_text(json.dumps(index, indent=2, ensure_ascii=False),
                        encoding='utf-8')
    note('status %s' % report['status'])
    return 0 if report['status'] == 'ACCEPTED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
