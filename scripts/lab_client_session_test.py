"""Find out whether starting a task kills the client.

The interactive session is rebuilt from time to time and the client leaves
with it. The system log says "the system session changed from N to M" every
few minutes. This script does the whole experiment inside one task, so the
experiment itself does not start any further task: it starts the client,
waits, starts a harmless task and watches whether the client is still there.
"""
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_client_restart

NOOP_TASK = 'WowNoopTask'
NOOP = 'cmd /c exit 0'


def wow_pids():
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Wow.exe', '/FO', 'CSV',
                          '/NH'], capture_output=True, text=True,
                         encoding='gbk', errors='replace')
    return [line.split(',')[1].strip('"') for line in out.stdout.splitlines()
            if line.startswith('"Wow.exe"')]


def session_events():
    """The session changes of the last minutes, from the system log."""
    out = subprocess.run(['powershell', '-NoProfile', '-Command',
                          "Get-WinEvent -FilterHashtable @{LogName='System';"
                          " Id=566} -MaxEvents 6 |"
                          " ForEach-Object { $_.TimeCreated.ToString('HH:mm:ss') }"],
                         capture_output=True, text=True, encoding='gbk',
                         errors='replace')
    return out.stdout.strip().replace('\n', ' ')


def main():
    print('pids before      ', wow_pids(), flush=True)
    print('session events   ', session_events(), flush=True)
    lab_client_restart.main()
    time.sleep(40)
    print('after start      ', wow_pids(), flush=True)
    print('session events   ', session_events(), flush=True)
    # A harmless task is started, exactly as the driver scripts do.
    subprocess.run(['schtasks', '/delete', '/tn', NOOP_TASK, '/f'],
                   capture_output=True)
    subprocess.run(['schtasks', '/create', '/tn', NOOP_TASK, '/tr', NOOP,
                    '/sc', 'once', '/st', '00:00', '/f'], capture_output=True)
    time.sleep(3)
    subprocess.run(['schtasks', '/run', '/tn', NOOP_TASK], capture_output=True)
    time.sleep(25)
    print('after noop task  ', wow_pids(), flush=True)
    print('session events   ', session_events(), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
