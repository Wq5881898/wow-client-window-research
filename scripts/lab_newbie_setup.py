"""Interactive-session setup for a dedicated new-character test baseline."""
import sys
import time

import lab_driver5 as d
from lab_flat_motion import command


def main():
    hwnd = d.find_game_window()
    if not hwnd:
        return 1
    d.ensure_foreground(hwnd)
    mode = sys.argv[1]
    if mode == 'logout':
        command(hwnd, '/logout')
        time.sleep(25)
    elif mode == 'name':
        d.type_text3(hwnd, 'Probehuman')
    elif mode == 'baseline':
        command(hwnd, '.gm off')
        command(hwnd, '.gm')
        d.screenshot('newbie-gm-state.png')
        command(hwnd, '/wp once newbie_baseline')
        command(hwnd, '/run SetMapToCurrentZone()')
        command(hwnd, '/run local r=WowProbeWotLK_Report.runs local m=r[#r].meta m.race=UnitRace("player") m.class=UnitClass("player") m.map_x,m.map_y=GetPlayerMapPosition("player")')
        command(hwnd, '/run print("BASELINE",UnitName("player"),UnitLevel("player"),GetZoneText(),GetSubZoneText(),GetPlayerMapPosition("player"))')
        command(hwnd, '/reload')
        time.sleep(8)
    else:
        raise ValueError(mode)
    d.screenshot('newbie-' + mode + '.png')
    return 0


if __name__ == '__main__':
    sys.exit(main())
