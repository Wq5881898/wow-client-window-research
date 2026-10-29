"""Small motion samples on Probehuman; run one inspected stage at a time."""
import sys
import time

import lab_driver5 as d
from lab_distance_scenarios import hold


def command(hwnd, text):
    if len(text) > 255:
        raise ValueError('chat command too long')
    d.post_key(hwnd, 0x1B, 0x01)
    time.sleep(0.4)
    d.post_key(hwnd, 0x0D)
    time.sleep(0.8)
    d.type_text3(hwnd, text)
    time.sleep(0.5)
    d.post_key(hwnd, 0x0D)
    time.sleep(2)


def main():
    stage = sys.argv[1]
    actions = {'stationary': None, 'back': 0x53, 'forward': 0x57,
               'left': 0x41, 'right': 0x44, 'turnleft': 0x25,
               'turnright': 0x27, 'final': None}
    if stage not in actions:
        raise ValueError(stage)
    hwnd = d.find_game_window()
    if not hwnd:
        print('No game window in this session; check Wow.exe and interactive task principal.', flush=True)
        return 1
    d.ensure_foreground(hwnd)
    if actions[stage]:
        hold(actions[stage], 0.15)
    command(hwnd, '/wp once newbie_motion_' + stage)
    command(hwnd, '/run SetMapToCurrentZone()')
    command(hwnd, '/run local r=WowProbeWotLK_Report.runs local m=r[#r].meta m.x,m.y=GetPlayerMapPosition("player") m.facing=GetPlayerFacing() m.speed=GetUnitSpeed("player") m.sample_time=GetTime()')
    d.screenshot('newbie-motion-' + stage + '.png')
    command(hwnd, '/reload')
    time.sleep(8)
    return 0


if __name__ == '__main__':
    sys.exit(main())
