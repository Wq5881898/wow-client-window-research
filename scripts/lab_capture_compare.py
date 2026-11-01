"""Compare capture paths inside the session that owns the game window."""
import time
from pathlib import Path
import lab_driver5 as d
from client_capture import grab_desktop, grab_window

OUT = Path(__file__).resolve().parents[1] / '.cache' / 'desktop-check'


def fingerprint(image):
    return image.resize((32, 18)).tobytes()


if __name__ == '__main__':
    hwnd = d.find_game_window()
    d.log('probe hwnd', hwnd)
    if not hwnd:
        raise SystemExit('no game window')
    a = grab_desktop()
    time.sleep(2)
    b = grab_desktop()
    d.log('desktop differs', fingerprint(a) != fingerprint(b), a.size)
    a.save(OUT / 'capture-desktop-a.png')
    b.save(OUT / 'capture-desktop-b.png')
    try:
        wa = grab_window(hwnd)
        time.sleep(2)
        wb = grab_window(hwnd)
        d.log('window differs', fingerprint(wa) != fingerprint(wb), wa.size)
        wa.save(OUT / 'capture-window-a.png')
        wb.save(OUT / 'capture-window-b.png')
    except Exception as exc:
        d.log('window capture failed', repr(exc))
