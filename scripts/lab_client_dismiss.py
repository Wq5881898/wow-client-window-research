"""Close the dialog of the client that blocks the screen.

The client shows a dialog when an add-on produced many errors. The dialog
is modal: the game does not react to anything while it is on the screen.
The button that keeps the add-ons is the second one of the row, so the two
red buttons are looked for and the right one is clicked.
"""
import time
from pathlib import Path
import win32gui
import win32con
import lab_driver5 as d
from client_capture import grab_desktop

ROOT = Path(__file__).resolve().parents[1]


def find_ignore_button(image):
    """The centre of the button that keeps the add-ons, or None.

    The dialog is a dark box with a golden frame in the upper middle of the
    screen. The button that keeps the add-ons is the right one of the two
    buttons below the text.
    """
    width, height = image.size
    pixels = image.convert('RGB').load()
    box = (int(width * 0.40), int(height * 0.17),
           int(width * 0.60), int(height * 0.27))
    dark = 0
    total = 0
    for y in range(box[1], box[3], 3):
        for x in range(box[0], box[2], 3):
            r, g, b = pixels[x, y]
            total += 1
            if r < 70 and g < 70 and b < 70:
                dark += 1
    if not total or dark < total * 0.7:
        return None
    # The two buttons sit under the text; the right one keeps the add-ons.
    return (int(width * 0.545), int(height * 0.283))


def main():
    hwnd = d.game_window()
    d.ensure_foreground(hwnd)
    image = grab_desktop()
    button = find_ignore_button(image)
    if button is None:
        print('no add-on dialog on the screen')
        return 0
    print('clicking ignore at', button)
    d.click_si(*button)
    time.sleep(1.0)
    # The chat input may be open after the dialog was closed.
    d.post_key(hwnd, win32con.VK_ESCAPE)
    time.sleep(0.5)
    out = ROOT / '.cache' / 'desktop-check' / 'after-dismiss.png'
    grab_desktop().save(out)
    print('saved', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
