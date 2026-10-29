"""Session-2 task runner: rewrite WoWLabDesktopCheck action and run it in the interactive session."""
import subprocess
import sys
import time

PY = r'C:\APP\Python\python.exe'
DRIVER = r'C:\APP\opencode\project\WoW自动化预研\scripts\lab_driver5.py'
LOG = r'C:\APP\opencode\project\WoW自动化预研\.cache\desktop-check\driver5.log'
PS = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'


def run(args, wait=8, tail=3):
    before = 0
    try:
        with open(LOG, encoding='utf-8') as f:
            before = sum(1 for _ in f)
    except FileNotFoundError:
        pass
    argstr = '"{}" {}'.format(DRIVER, ' '.join(args))
    ps = (
        "$a = New-ScheduledTaskAction -Execute '{}' -Argument '{}'; "
        "$p = New-ScheduledTaskPrincipal -UserId 'qrz' -LogonType Interactive -RunLevel Highest; "
        "Register-ScheduledTask -TaskName 'WoWLabDesktopCheck' -Action $a -Principal $p -Force | Out-Null; "
        "Start-ScheduledTask -TaskName 'WoWLabDesktopCheck'"
    ).format(PY, argstr)
    subprocess.run([PS, '-NoProfile', '-Command', ps], check=True)
    time.sleep(wait)
    with open(LOG, encoding='utf-8') as f:
        lines = f.read().splitlines()
    print('\n'.join(lines[before:]))
    for _ in range(10):
        time.sleep(2)
        with open(LOG, encoding='utf-8') as f:
            new = f.read().splitlines()[before:]
        if new and ('screenshot' in new[-1] or 'no game window' in new[-1] or 'done' in new[-1]):
            break
    with open(LOG, encoding='utf-8') as f:
        print('\n'.join(f.read().splitlines()[before:]))


if __name__ == '__main__':
    wait = 8
    args = sys.argv[1:]
    if args and args[0] == '--wait':
        wait = int(args[1])
        args = args[2:]
    run(args, wait=wait)
