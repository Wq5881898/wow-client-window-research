"""Type a chat command and look at the answer of the client.

The character does not move at all, not even one quantum of the map
position, and the camera sits inside a wall. The server may still hold the
character, and a command of the server can free it.

The script types a command into the chat of the client, waits for the
answer and saves the picture of the chat area, so that the answer can be
read from the screen.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_driver5 as d
import win32con
import win32gui
from client_capture import grab_desktop
from client_evidence import Evidence
from client_parent_run import stamp
from client_chat_guard import ensure_chat_closed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'

# The area of the chat of the client in the picture.
CHAT = (0, 640, 900, 1000)


def send(hwnd, text):
    """Type the text into the chat of the client and submit it."""
    ensure_chat_closed(hwnd, lambda: None)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.6)
    for character in text:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.05)
    time.sleep(0.3)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(1.5)


def main():
    run = 'client_chat_command_' + str(time.time_ns())
    result = stamp(dict(run=run, status='FAILED', commands=[]), sys.argv)
    evidence = Evidence(run)
    try:
        hwnd = d.game_window()
        d.ensure_foreground(hwnd)
        time.sleep(1.0)
        commands = []
        for argument in sys.argv[1:]:
            if argument.startswith('--say='):
                # The command line of a task splits at the spaces, so a
                # space in the text is written as an underline.
                commands.append(argument.split('=', 1)[1].replace('_', ' '))
        if not commands:
            raise ValueError('explicit --say= command required')
        for index, command in enumerate(commands):
            send(hwnd, command)
            time.sleep(2.0)
            picture = grab_desktop()
            path = OUT / ('%s_%d.png' % (run, index))
            picture.save(str(path))
            picture.crop(CHAT).save(str(OUT / ('%s_%d_chat.png'
                                               % (run, index))))
            result['commands'].append({'command': command, 'picture': str(path)})
        result['status'] = 'TYPED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('03-end')
        path = evidence.write(result)
        d.log('chat command', str(path), result['status'])
    return 0 if result['status'] == 'TYPED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
