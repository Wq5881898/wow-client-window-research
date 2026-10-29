"""Short, separately inspected movement samples on a flat-area baseline."""
import sys
import time

import lab_driver5 as d
from lab_distance_scenarios import hold


def command(hwnd, text):
    if len(text) > 255:
        raise ValueError('chat command too long')
    d.press(0x0D)
    time.sleep(0.6)
    d.type_text3(hwnd, text)
    time.sleep(0.4)
    d.post_key(hwnd, 0x0D)
    time.sleep(2)


def main():
    mode = sys.argv[1]
    hwnd = d.find_game_window()
    if not hwnd:
        return 1
    d.ensure_foreground(hwnd)
    if mode == 'setup':
        command(hwnd, '.tele goldshire')
        time.sleep(5)
        command(hwnd, '/cleartarget')
    elif mode in ('forward', 'back'):
        hold(0x57 if mode == 'forward' else 0x53, 0.5)
    elif mode != 'stationary':
        raise ValueError(mode)
    command(hwnd, '/wp once flat_' + mode)
    command(hwnd, '/run SetMapToCurrentZone()')
    lua = ('local t=WowProbeWotLK_Report.runs local m=t[#t].meta '
           'local x,y=GetPlayerMapPosition("player") '
           'm.motion_x=x m.motion_y=y m.motion_facing=GetPlayerFacing() '
           'm.motion_speed=GetUnitSpeed("player")')
    command(hwnd, '/run ' + lua)
    d.screenshot('flat-' + mode + '.png')
    command(hwnd, '/reload')
    time.sleep(8)
    return 0


if __name__ == '__main__':
    sys.exit(main())
