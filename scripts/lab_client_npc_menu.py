"""Open the resurrection NPC menu and capture it for pixel measurement."""
import time
from pathlib import Path
import win32con
import win32gui
import lab_driver5 as d
from client_capture import grab_desktop
from client_evidence import Evidence

GRAVEYARD_NPC = (200, 142)


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
    evidence = Evidence('menu_probe')
    hwnd = d.find_game_window()
    if not hwnd:
        print('no window')
        return 1
    d.ensure_foreground(hwnd)
    hide_consoles()
    d.post_key(hwnd, win32con.VK_ESCAPE)
    time.sleep(0.8)
    d.post_key(hwnd, win32con.VK_ESCAPE)
    time.sleep(0.8)
    # Select the resurrection NPC first so the nameplate turns interactive.
    d.click_si(200, 142)
    time.sleep(0.6)
    # Then right click its body to open the interaction menu.
    d.right_click(230, 280)
    time.sleep(1.2)
    image = grab_desktop()
    image.save('.cache/desktop-check/npc-menu.png')
    image.crop((0, 100, 400, 350)).resize((1200, 750)).save(
        '.cache/desktop-check/npc-menu-zoom.png')
    print('saved')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
