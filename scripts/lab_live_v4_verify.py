"""Non-combat verification of protocol v4: chat state and target distance.

Capture happens inside the session that owns the game window, so the run
also works when the observer session cannot see the desktop.
"""
import json
import time
from pathlib import Path
import win32con
import lab_driver5 as d
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame
from client_window_state import window_observable
from client_evidence import Evidence

ROOT = Path(__file__).resolve().parents[1]
SELF_NAME = 'Probehuman'


def main():
    run = 'client_live_v4_' + str(time.time_ns())
    result = dict(run=run, status='FAILED', samples=[])
    evidence = Evidence(run)
    hwnd = d.find_game_window()
    try:
        if not hwnd:
            raise ValueError('no game window')
        d.ensure_foreground(hwnd)

        def sample():
            image = assert_real_frame(grab_desktop())
            state = decode(image)
            result['samples'].append(state)
            return state

        def hide_consoles():
            import win32gui
            def cb(h, _):
                try:
                    cls = win32gui.GetClassName(h)
                    title = win32gui.GetWindowText(h)
                except Exception:
                    return True
                if cls == 'ConsoleWindowClass' or 'python.exe' in title.lower():
                    try:
                        win32gui.ShowWindow(h, win32con.SW_HIDE)
                    except Exception:
                        pass
                return True
            win32gui.EnumWindows(cb, None)

        state = sample()
        if state['protocol'] != 4:
            raise ValueError('expected protocol 4, got ' + str(state['protocol']))
        evidence.capture('01-start', state)
        result['protocol'] = state['protocol']

        # A chat box left open by an earlier run must be closed first.
        if state['chat_open']:
            d.post_key(hwnd, win32con.VK_RETURN)
            time.sleep(0.8)
            state = sample()
        if state['chat_open']:
            raise ValueError('chat still open after closing it')
        result['chat_closed_at_baseline'] = True

        # The chat box may already be open from a previous run.
        d.post_key(hwnd, win32con.VK_RETURN)
        time.sleep(0.4)
        opened = None
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            opened = sample()
            if opened['chat_open']:
                break
            time.sleep(0.15)
        if not opened['chat_open']:
            raise ValueError('chat did not report open after Enter')
        evidence.capture('02-chat-open', opened)
        result['chat_open_confirmed'] = True

        d.post_key(hwnd, win32con.VK_RETURN)
        time.sleep(0.5)
        closed = sample()
        if closed['chat_open']:
            raise ValueError('chat still open after second Enter')
        evidence.capture('03-chat-closed', closed)
        result['chat_closed_confirmed'] = True

        from lab_distance_scenarios import command
        command(hwnd, '/targetexact ' + SELF_NAME)
        time.sleep(1.2)
        targeted = sample()
        if not targeted['target_exists']:
            raise ValueError('self target not acquired')
        result['target_distance_self'] = targeted['target_distance']
        if targeted['target_distance'] <= 0:
            # A self target has zero distance; the field must still be present.
            if 'target_distance' not in targeted:
                raise ValueError('target distance field missing')
            result['target_distance_note'] = 'self target reports zero distance'
        evidence.capture('04-targeted', targeted)

        result['status'] = 'LIVE_V4_VERIFIED'
    except Exception as exc:
        result['error'] = repr(exc)
    finally:
        evidence.capture('05-end')
        path = evidence.write(result)
        d.log('v4 verification', path, result['status'])
    return 0 if result['status'] == 'LIVE_V4_VERIFIED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
