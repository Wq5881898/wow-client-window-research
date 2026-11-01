"""Recover the client and capture through the game's own screenshot command.

The desktop screen DC returns black while the interactive session is
disconnected, so verification uses files the client itself writes.
"""
import json
import time
from pathlib import Path
import lab_driver5 as d
from lab_distance_scenarios import command

SCREENSHOTS = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a\Screenshots')
SAVED = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a\WTF\Account\GM01'
             r'\AzerothCore\Probehuman\SavedVariables\WowProbeWotLK.lua')
OUT = Path(__file__).resolve().parents[1] / '.cache' / 'desktop-check'
ENTER_WORLD = (958, 992)


def newest_screenshot(after):
    candidates = [p for p in SCREENSHOTS.iterdir()
                  if p.suffix.lower() in ('.jpg', '.png') and p.stat().st_mtime > after]
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def recover_and_capture(hwnd, name, timeout=45):
    marker = time.time()
    before_save = SAVED.stat().st_mtime if SAVED.exists() else 0
    d.click_si(*ENTER_WORLD)
    time.sleep(4)
    command(hwnd, '/screenshot')
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = newest_screenshot(marker)
        if found:
            target = OUT / (name + found.suffix.lower())
            target.write_bytes(found.read_bytes())
            return {'source': str(found), 'copy': str(target),
                    'size': found.stat().st_size,
                    'saved_variables_mtime': SAVED.stat().st_mtime}
        time.sleep(1)
    return {'source': None, 'saved_variables_mtime':
            SAVED.stat().st_mtime if SAVED.exists() else 0,
            'saved_variables_changed': SAVED.stat().st_mtime > before_save
            if SAVED.exists() else False}


if __name__ == '__main__':
    hwnd = d.find_game_window()
    if not hwnd:
        raise RuntimeError('no game window')
    result = recover_and_capture(hwnd, 'game-screenshot-' + str(time.time_ns()))
    print(json.dumps(result, indent=2))
