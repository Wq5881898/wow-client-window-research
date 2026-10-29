"""Three stationary snapshots in one client run; interactive desktop only."""
import time
import lab_driver5 as d
from lab_distance_scenarios import command


def main():
    hwnd = d.find_game_window()
    if not hwnd:
        raise RuntimeError('No game window in current interactive session')
    d.ensure_foreground(hwnd)
    for index in range(1, 4):
        command(hwnd, '/wp once newbie_continuous_' + str(index))
        command(hwnd, '/run SetMapToCurrentZone()')
        command(hwnd, '/run local r=WowProbeWotLK_Report.runs local m=r[#r].meta m.x,m.y=GetPlayerMapPosition("player") m.facing=GetPlayerFacing() m.speed=GetUnitSpeed("player") m.sample_time=GetTime()')
        d.screenshot('newbie-continuous-' + str(index) + '.png')
        if index < 3:
            time.sleep(10)
    command(hwnd, '/reload')
    time.sleep(10)
    d.log('continuous stationary task done')


if __name__ == '__main__':
    main()
