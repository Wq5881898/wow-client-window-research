"""Supervised recovery telemetry: read-only on-screen coordinates, external inputs."""
import argparse
import time

import lab_driver5 as d
from lab_distance_scenarios import command, hold


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--key', type=lambda s: int(s, 0))
    parser.add_argument('--seconds', type=float, default=0.2)
    parser.add_argument('--resurrect', action='store_true')
    args = parser.parse_args()
    hwnd = d.find_game_window()
    if not hwnd:
        raise RuntimeError('no game window')
    d.ensure_foreground(hwnd)
    if d.win32gui.GetForegroundWindow() != hwnd:
        raise RuntimeError('foreground lost')
    if args.key:
        hold(args.key, args.seconds)
    if args.resurrect:
        d.click_si(960, 230, hold=0.1)
        time.sleep(0.5)
        hold(0x41, 4)
        time.sleep(30)
    command(hwnd, '/run SetMapToCurrentZone(); RecoveryText=RecoveryText or UIParent:CreateFontString(nil,"OVERLAY","GameFontNormalLarge"); RecoveryText:SetPoint("TOP",0,-180)')
    command(hwnd, '/run local x,y=GetPlayerMapPosition("player"); local a,b=GetCorpseMapPosition(); RecoveryText:SetText(format("P %.5f %.5f C %.5f %.5f F %.3f HP %d G %s",x,y,a,b,GetPlayerFacing(),UnitHealth("player"),tostring(UnitIsGhost("player"))))')
    command(hwnd, '/run RecoveryText:SetText(RecoveryText:GetText().." Combat "..tostring(UnitAffectingCombat("player")).." Dead "..tostring(UnitIsDeadOrGhost("player")).." Speed "..GetUnitSpeed("player"))')
    d.screenshot('recovery_' + str(time.time_ns()) + '.png')


if __name__ == '__main__':
    main()
