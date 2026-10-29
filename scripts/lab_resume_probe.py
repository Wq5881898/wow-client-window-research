"""Run login/probe recovery inside the interactive desktop session."""
import sys
import time

import lab_driver5 as d


def main():
    hwnd = d.find_game_window()
    d.log('resume', sys.argv[1:], 'hwnd', hwnd)
    if not hwnd:
        return 1
    d.ensure_foreground(hwnd)
    mode = sys.argv[1] if len(sys.argv) > 1 else 'shot'
    if mode == 'login':
        d.click_si(*d.client_to_screen(hwnd, 512, 402))
        d.clear_field()
        d.type_text2('GM01')
        d.press(0x09)
        d.clear_field()
        d.type_text2('123321')
        d.click_si(*d.client_to_screen(hwnd, 512, 574))
        time.sleep(12)
    elif mode in ('probe', 'flush'):
        d.press(0x1B)
        time.sleep(0.5)
        d.press(0x0D)
        time.sleep(0.4)
        command = '/reload' if mode == 'flush' else '/wp once session2_recovered'
        d.type_text3(hwnd, command)
        time.sleep(0.5)
        d.screenshot('resume-probe-typed.png')
        d.post_key(hwnd, 0x0D)
        time.sleep(10 if mode == 'flush' else 3)
    d.screenshot('resume-' + mode + '.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
