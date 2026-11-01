"""Leave the world and inspect the character selection screen."""
import json
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_evidence import Evidence

ROOT = Path(__file__).resolve().parents[1]


def hide_consoles():
    def cb(hwnd, _):
        try:
            cls = win32gui.GetClassName(hwnd)
            title = win32gui.GetWindowText(hwnd)
        except Exception:
            return True
        if cls == 'ConsoleWindowClass' or 'python.exe' in title.lower():
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            except Exception:
                pass
        return True
    win32gui.EnumWindows(cb, None)


def main():
    run = 'client_char_select_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', steps=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)
        hide_consoles()
        # Escape opens the game menu; "Logout" leaves the world.
        d.post_key(hwnd, win32con.VK_ESCAPE)
        time.sleep(2.0)
        evidence.capture('01-menu')
        image = grab_desktop()
        image.crop((820,380,1120,700)).resize((900,960)).save(
            '.cache/desktop-check/menu-zoom.png')
        # The character list marks the probe character as a ghost, so it
        # cannot enter the world any more. Another character of the same
        # account is used to check whether the world itself is healthy.
        d.click_si(1592, 155)
        time.sleep(2.0)
        evidence.capture('04-other-character')
        image = grab_desktop()
        image.resize((1200, 675)).save('.cache/desktop-check/char-select2.png')
        result['status'] = 'SELECTED_OTHER'
        print('other character selected')
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        path = evidence.write(result)
        d.log('char select run', path, result['status'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
