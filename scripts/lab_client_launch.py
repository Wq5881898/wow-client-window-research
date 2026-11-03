"""Start the client and fix the display mode before every start.

The client rewrites its own configuration when it exits, so the setting of
the display mode does not survive. Every start of the client goes through
this script, which writes the mode first and then keeps the client as a
child of this process, so the client is not killed with the job of the
driver task.

The mode is the fullscreen mode by default, because the driver reads the
picture of the screen and the panel of the probe has the place of the
fullscreen layout. A file in the cache switches the client to the window
mode, but the driver can not read the picture in that mode yet.
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lab_client_restart import set_fullscreen

ROOT = Path(__file__).resolve().parents[1]
CLIENT = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a')
FLAG = ROOT / '.cache' / 'desktop-check' / 'windowed.flag'
LOG = ROOT / '.cache' / 'desktop-check' / 'launch.txt'


def note(text):
    with LOG.open('a', encoding='utf-8') as stream:
        stream.write('%.3f %s\n' % (time.time(), text))


def main():
    LOG.write_text('', encoding='utf-8')
    fullscreen = not FLAG.exists()
    note('mode fullscreen=%s' % fullscreen)
    note('config %s' % set_fullscreen(fullscreen))
    process = subprocess.Popen([str(CLIENT / 'Wow.exe')], cwd=str(CLIENT))
    note('client pid %s' % process.pid)
    process.wait()
    note('client ended with %s' % process.returncode)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
