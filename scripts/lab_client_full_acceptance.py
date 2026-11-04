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
    ('combat', 'lab_client_combat_loop.py',
     ['--target-name', 'Diseased Young Wolf']),
    ('danger_setup', 'lab_client_danger_setup.py',
     ['--walk-to', '0.50390', '0.44147']),
    ('danger_recovery', 'lab_client_danger_recovery.py', ['--die-again']),
    ('relogin', 'lab_client_relogin_verify.py', ['--character', 'Probehuman']),
]


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


def latest(prefix):
    files = sorted((ROOT / 'results').glob(prefix + '*.json'),
                   key=lambda p: p.stat().st_mtime)
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text(encoding='utf-8'))
    except Exception:
        return None


def main():
    LOG.write_text('', encoding='utf-8')
    attempts = 5
    report = {'attempts': [], 'status': 'FAILED'}
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
            code = run(script, argv)
            record['steps'].append({'step': name, 'code': code})
            note('   %s -> %s' % (name, code))
            if code != 0:
                failed = True
                break
        report['attempts'].append(record)
        if not failed:
            report['status'] = 'ACCEPTED'
            break
        note('   the attempt failed, the run starts again')
    report['combat'] = latest('client_combat_')
    report['danger_recovery'] = latest('client_danger_recovery_')
    report['relogin'] = latest('client_relogin_')
    SUMMARY.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                       encoding='utf-8')
    note('status %s' % report['status'])
    return 0 if report['status'] == 'ACCEPTED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
