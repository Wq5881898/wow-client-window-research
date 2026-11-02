"""Print what the client says about a few position APIs.

The client of 3.3.5a may not offer every API of the later clients, so the
availability is asked in the client itself and the answer is read from the
chat frame.
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_chat_guard import ensure_focus, ensure_chat_closed

CODE = ('local ok,a,b=pcall(GetUnitPosition,"player") '
        'print("UP",tostring(GetUnitPosition),tostring(ok),tostring(a),tostring(b)) '
        'local c,d2=pcall(function() return GetPlayerMapPosition("player") end) '
        'print("MP",tostring(c),tostring(d2)) '
        'local e,f=pcall(function() return UnitPosition("player") end) '
        'print("UPos",tostring(e),tostring(f))')


def main():
    hwnd = d.find_game_window()
    if not hwnd:
        print('no game window')
        return 1
    ensure_focus(hwnd)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.6)
    for character in '/run ' + CODE:
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.01)
    time.sleep(0.3)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(2.0)
    out = Path(__file__).resolve().parents[1] / '.cache' / 'desktop-check' / 'api-probe.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    grab_desktop().save(out)
    print('saved', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
