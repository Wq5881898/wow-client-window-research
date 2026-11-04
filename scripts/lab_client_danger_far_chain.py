"""The chain of the danger zone with a longer way out of the graveyard.

The chain is: restart, enter the world, walk a route out of the zone and
die there, recover the corpse, walk back to the graveyard, die a second
time on the way, and check the state after a log in. Every part is a
separate script, and the session of the machine is rebuilt from time to
time, so the chain is repeated while it does not finish.
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'
LOG = OUT / 'danger-far-chain.txt'

# The route leaves the place where the ghost appears. Every point is walked
# to and looked at for a hostile, and the water of the lake is part of the
# way: the character can die there, far away from the graveyard.
ROUTE = ['0.54,0.44', '0.54,0.50', '0.46,0.50']


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


def main():
    LOG.write_text('', encoding='utf-8')
    attempts = 6
    for attempt in range(1, attempts + 1):
        note('== attempt %d of %d ==' % (attempt, attempts))
        code = run('lab_client_restart.py', [])
        note('   restart -> %s' % code)
        if not wait_for_window():
            note('   no window')
            continue
        code = run('lab_client_enter_character.py', ['--character', 'Probehuman'])
        note('   enter -> %s' % code)
        if code != 0:
            continue
        code = run('lab_client_danger_setup.py', ['--route'] + ROUTE)
        note('   setup (walk out and die) -> %s' % code)
        if code != 0:
            continue
        code = run('lab_client_danger_recovery.py', ['--die-again'])
        note('   recovery -> %s' % code)
        if code != 0:
            continue
        code = run('lab_client_relogin_verify.py', ['--character', 'Probehuman'])
        note('   relogin -> %s' % code)
        if code == 0:
            note('the chain finished')
            return 0
    note('the chain did not finish')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
