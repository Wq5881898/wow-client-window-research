"""Restart the client, enter the standard role and run the combat closure.

The interactive session of the machine is rebuilt from time to time, and the
client leaves when that happens. The whole sequence therefore runs in one
process, so nothing is lost between the steps.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lab_client_restart
import lab_client_enter_character
import lab_client_combat_loop
import lab_driver5 as d


def wait_for_window(timeout=180.0):
    """The client needs about a minute before it has a window."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            d.game_window()
            return True
        except Exception:
            time.sleep(3.0)
    return False


def enter():
    """One try to enter the character; the caller starts over on failure."""
    sys.argv = ['lab_client_enter_character.py', '--character', 'Probehuman']
    return lab_client_enter_character.main() == 0


def main():
    """Run the whole sequence, repeating it while the client leaves.

    The interactive session of the machine is rebuilt every few minutes and
    the client leaves with it. A run that dies in the middle is therefore
    simply started again, as long as the session holds.
    """
    attempts = 10
    for attempt in range(1, attempts + 1):
        print('== attempt %d of %d ==' % (attempt, attempts), flush=True)
        lab_client_restart.main()
        if not wait_for_window(120.0):
            print('the client did not get a window', flush=True)
            continue
        print('== enter the character ==', flush=True)
        if not enter():
            print('could not enter the character, starting again', flush=True)
            continue
        print('== combat closure ==', flush=True)
        sys.argv = ['lab_client_combat_loop.py']
        if lab_client_combat_loop.main() == 0:
            return 0
        print('the combat closure did not finish, starting again', flush=True)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
