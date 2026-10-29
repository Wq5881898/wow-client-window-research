"""Kill Wow, relaunch via WoWLabLaunch task, poll until window appears."""
import sys
import time
import subprocess
from pathlib import Path

sys.path.insert(0, r'C:\APP\opencode\project\WoW自动化预研\scripts')
import lab_driver5 as d

LOG = Path(r'C:\APP\opencode\project\WoW自动化预研\.cache\desktop-check\relaunch.log')


def log(*a):
    line = ' '.join(str(x) for x in a)
    print(line, flush=True)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def wow_pids():
    out = subprocess.check_output(
        'tasklist /FI "IMAGENAME eq Wow.exe" /FO CSV /NH', shell=True
    ).decode('gbk', 'ignore')
    pids = []
    for line in out.splitlines():
        parts = line.strip().split(',')
        if len(parts) > 1 and parts[0].strip('"').lower() == 'wow.exe':
            pids.append(int(parts[1].strip('"')))
    return pids


def main():
    for p in wow_pids():
        subprocess.run(f'taskkill /PID {p} /F', shell=True)
        log('killed', p)
    time.sleep(3)
    subprocess.run('schtasks /Run /TN "WoWLabLaunch"', shell=True)
    log('task launched')
    deadline = time.time() + 120
    while time.time() < deadline:
        time.sleep(2)
        hwnd = d.find_game_window()
        if hwnd:
            log('window appeared hwnd', hwnd)
            d.screenshot('relaunch-win.png')
            return 0
        pids = wow_pids()
        if not pids:
            log('process gone')
            return 2
    log('timeout no window, pids', wow_pids())
    d.screenshot('relaunch-timeout.png')
    return 1


if __name__ == '__main__':
    sys.exit(main())
