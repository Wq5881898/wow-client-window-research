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


def enter(attempts=3):
    for attempt in range(attempts):
        sys.argv = ['lab_client_enter_character.py', '--character', 'Probehuman']
        if lab_client_enter_character.main() == 0:
            return True
        print('enter failed, waiting and trying again', flush=True)
        time.sleep(30)
    return False


def main():
    print('== restart ==', flush=True)
    lab_client_restart.main()
    if not wait_for_window():
        print('the client did not get a window', flush=True)
        return 1
    time.sleep(10)
    print('== enter the character ==', flush=True)
    if not enter():
        print('could not enter the character', flush=True)
        return 1
    time.sleep(5)
    print('== combat closure ==', flush=True)
    sys.argv = ['lab_client_combat_loop.py']
    return lab_client_combat_loop.main()


if __name__ == '__main__':
    raise SystemExit(main())
