"""Try the graveyard resurrection route and report what the client offers."""
import time
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop

NPC_NAMED_PLATE = (200, 142)
NPC_BODY = (230, 280)
SPIRIT_HEALER = (176, 173)


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


def shot(name):
    image = grab_desktop()
    image.save('.cache/desktop-check/%s.png' % name)
    image.crop((0, 100, 400, 350)).resize((1200, 750)).save(
        '.cache/desktop-check/%s-zoom.png' % name)
    print('shot', name)


def main():
    hwnd = d.find_game_window()
    if not hwnd:
        print('no window')
        return 1
    d.ensure_foreground(hwnd)
    hide_consoles()
    for _ in range(2):
        d.post_key(hwnd, win32con.VK_ESCAPE)
        time.sleep(0.6)

    # The menu belongs to the current target, so the NPC has to be the target
    # before the menu is opened. The chat command is the reliable way to
    # change the target; clicking the nameplate is not.
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(0.5)
    for character in '/target Dane Winslow':
        win32gui.PostMessage(hwnd, win32con.WM_CHAR, ord(character), 0)
        time.sleep(0.04)
    time.sleep(0.3)
    d.post_key(hwnd, win32con.VK_RETURN)
    time.sleep(1.5)
    shot('grave-target-npc')
    d.right_click(*NPC_NAMED_PLATE)
    time.sleep(1.2)
    shot('grave-npc-menu')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
