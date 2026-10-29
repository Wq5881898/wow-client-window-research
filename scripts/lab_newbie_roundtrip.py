"""Same-run short forward/backward motion with four position snapshots."""
import sys
import argparse
import time

import lab_driver5 as d
from lab_distance_scenarios import command, hold


def sample(hwnd, name, prefix):
    command(hwnd, '/wp once ' + prefix + name)
    command(hwnd, '/run SetMapToCurrentZone()')
    command(hwnd, '/run local r=WowProbeWotLK_Report.runs local m=r[#r].meta m.x,m.y=GetPlayerMapPosition("player") m.facing=GetPlayerFacing() m.speed=GetUnitSpeed("player") m.sample_time=GetTime()')
    d.screenshot(prefix + name + '.png')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--compensated', action='store_true')
    parser.add_argument('--trial', type=int, choices=range(1, 4))
    args = parser.parse_args()
    prefix = 'newbie_compensated_' if args.compensated else 'newbie_roundtrip_'
    if args.trial:
        if not args.compensated:
            parser.error('--trial requires --compensated')
        prefix += 'trial' + str(args.trial) + '_'
    hwnd = d.find_game_window()
    if not hwnd:
        print('No game window in current interactive session', flush=True)
        return 1
    d.ensure_foreground(hwnd)
    command(hwnd, '/run GameMenuFrame:Hide()')
    sample(hwnd, 'baseline', prefix)
    hold(0x57, 0.15)
    sample(hwnd, 'forward', prefix)
    hold(0x53, 0.15 * 7 / 4.5 if args.compensated else 0.15)
    sample(hwnd, 'back', prefix)
    time.sleep(10)
    sample(hwnd, 'final', prefix)
    command(hwnd, '/reload')
    time.sleep(10)
    d.log('roundtrip task done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
