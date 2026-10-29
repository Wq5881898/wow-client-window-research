"""Interactive-session target controls; the add-on remains read-only."""
import sys
import time

import lab_driver5 as d


def command(hwnd, text):
    if len(text) > 255:
        raise ValueError('chat command exceeds 255 characters')
    d.press(0x0D)
    time.sleep(0.4)
    d.type_text3(hwnd, text)
    time.sleep(0.3)
    d.post_key(hwnd, 0x0D)
    time.sleep(1)
    d.log('target experiment command', text)


def main():
    hwnd = d.find_game_window()
    if not hwnd:
        return 1
    d.ensure_foreground(hwnd)
    command(hwnd, '/run GameMenuFrame:Hide()')
    cases = [
        ('/cleartarget', 'target_none_control'),
        ('/target Syra', 'target_self_control'),
        ('/targetexact Lothos Riftwaker', 'target_npc_lothos'),
        ('/cleartarget', 'target_cleared_control'),
    ]
    for action, scene in cases:
        command(hwnd, action)
        command(hwnd, '/wp once ' + scene)
        d.screenshot(scene + '.png')
    command(hwnd, '/reload')
    time.sleep(10)
    d.screenshot('target-scenarios-flushed.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
