"""Supervised single-spell experiment. External slash input, read-only Lua capture."""
import argparse
import hashlib
import json
import time

import lab_driver5 as d
from client_snapshot_task import inspect
from lab_client_observe import ROOT, SOURCE
from lab_distance_scenarios import command, hold
from lab_newbie_roundtrip import sample


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cast', action='store_true')
    parser.add_argument('--approach', action='store_true')
    parser.add_argument('--finish-current', action='store_true')
    args = parser.parse_args()
    if args.cast or args.finish_current:
        parser.error('combat execution paused after death; implement live health/aggro feedback before another attempt')
    run = 'client_combat_' + str(time.time_ns())
    result = {'run_id': run, 'status': 'STARTED', 'cast_requested': False}
    output = ROOT / 'results' / (run + '.json')
    def save():
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save()
    try:
        hwnd = d.find_game_window()
        if not hwnd:
            raise RuntimeError('no interactive window')
        d.ensure_foreground(hwnd)
        if args.finish_current:
            hold(0x27, 0.4)
            command(hwnd, '/cast Fireball')
            time.sleep(4)
            command(hwnd, '/cast Fireball')
            time.sleep(5)
            d.screenshot(run + '_finish.png')
            result['status'] = 'FINISH_REQUESTED'
            save()
            return 0
        if args.approach:
            if d.win32gui.GetForegroundWindow() != hwnd:
                raise RuntimeError('foreground lost before approach')
            result['movement_requested'] = 'S_2_SECONDS'
            save()
            hold(0x53, 2)
        command(hwnd, '/targetexact Diseased Young Wolf')
        if args.cast:
            # Face the southern lawn; this is a supervised site-specific turn.
            hold(0x25, 1.0)
            command(hwnd, '/run CombatLab={damage=0,success=0,incoming=0}; CombatLabFrame=CreateFrame("Frame"); CombatLabFrame:RegisterEvent("COMBAT_LOG_EVENT_UNFILTERED")')
            command(hwnd, '/run CombatLabFrame:SetScript("OnEvent",function(_,e,t,k,s,sn,sf,d,dn,df,a,b,c,v) if s==UnitGUID("player") then CombatLab[k]=(CombatLab[k] or 0)+(k=="SPELL_DAMAGE" and v or 1) end end)')
            command(hwnd, '/run CombatLabError=CreateFrame("Frame"); CombatLabError:RegisterEvent("UI_ERROR_MESSAGE"); CombatLabError:SetScript("OnEvent",function(_,e,a) CombatLab.error=tostring(a) end)')
            if d.win32gui.GetForegroundWindow() != hwnd:
                raise RuntimeError('foreground lost')
            result['cast_requested'] = True
            save()
            command(hwnd, '/cast Fireball')
            d.screenshot(run + '_cast-request.png')
            time.sleep(5)
            # Bounded follow-up casts finish a level-1 target rather than leaving aggro.
            command(hwnd, '/cast Fireball')
            time.sleep(5)
            command(hwnd, '/cast Fireball')
            time.sleep(10)
            d.screenshot(run + '_after-cast.png')
        sample(hwnd, 'snapshot', run + '_')
        command(hwnd, '/run local r=WowProbeWotLK_Report.runs local m=r[#r].meta m.target_health=UnitHealth("target") m.target_guid=UnitGUID("target") m.fireball=GetSpellInfo(133) m.spell_range=IsSpellInRange("Fireball","target") m.target_level=UnitLevel("target")')
        if args.cast:
            command(hwnd, '/run local r=WowProbeWotLK_Report.runs local m=r[#r].meta m.spell_damage=CombatLab.SPELL_DAMAGE or 0 m.cast_success=CombatLab.SPELL_CAST_SUCCESS or 0 m.cast_error=CombatLab.error')
        shot = d.screenshot(run + '_snapshot.png')
        requested = time.time_ns()
        command(hwnd, '/run if not UnitAffectingCombat("player") then ReloadUI() end')
        deadline, previous = time.monotonic() + 40, None
        while time.monotonic() < deadline:
            try:
                if SOURCE.stat().st_mtime_ns >= requested:
                    raw = SOURCE.read_bytes()
                    if (run + '_snapshot').encode() in raw:
                        digest = hashlib.sha256(raw).hexdigest()
                        if digest == previous:
                            break
                        previous = digest
            except (PermissionError, FileNotFoundError):
                pass
            time.sleep(1)
        else:
            raise TimeoutError('combat sample not persisted')
        backup = ROOT / '.cache' / 'client-observations' / (run + '.lua')
        with backup.open('xb') as handle:
            handle.write(raw)
        result.update(local_raw_backup=str(backup), screenshot=str(shot))
        result['acceptance'] = inspect(raw, run + '_snapshot', 'Probehuman', 'Diseased Young Wolf')
        result['status'] = 'PREFLIGHT_ACCEPTED'
        if args.cast:
            meta = result['acceptance']['sample']['meta']
            if meta.get('spell_damage', 0) <= 0 or meta.get('cast_success', 0) <= 0:
                raise ValueError('successful damaging spell not observed')
            result['status'] = 'SPELL_DAMAGE_VERIFIED'
        save()
        return 0
    except Exception as exc:
        result.update(status='FAILED', error=f'{type(exc).__name__}: {exc}')
        save()
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
