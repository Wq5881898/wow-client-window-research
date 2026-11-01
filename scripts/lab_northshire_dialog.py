"""Bounded NPC preflight via external chat; Lua only reads identity/range/bindings."""
import hashlib
import json
import time
import sys

import lab_driver5 as d
from client_snapshot_task import inspect
from lab_client_observe import ROOT, SOURCE
from lab_distance_scenarios import command, hold
from lab_newbie_roundtrip import sample


def main():
    if '--approach' in sys.argv:
        hwnd = d.find_game_window()
        d.ensure_foreground(hwnd)
        if d.win32gui.GetForegroundWindow() != hwnd:
            raise RuntimeError('foreground not acquired')
        hold(0x53, 0.8)
        hold(0x45, 0.45)
        time.sleep(2)
        d.screenshot('northshire-approach.png')
        return 0
    if len(sys.argv) > 1 and sys.argv[1] in ('--camera', '--look-back'):
        hwnd = d.find_game_window()
        d.ensure_foreground(hwnd)
        d.u.SetCursorPos(950, 400)
        d.u.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.3)
        try:
            for _ in range(60 if sys.argv[1] == '--look-back' else 27):
                d.u.mouse_event(0x0001, 10 if sys.argv[1] == '--look-back' else 0,
                                0 if sys.argv[1] == '--look-back' else -10, 0, 0)
                time.sleep(0.02)
        finally:
            d.u.mouse_event(0x0004, 0, 0, 0, 0)
        time.sleep(2)
        d.screenshot('northshire-camera.png')
        return 0
    run = 'northshire_dialog_' + str(time.time_ns())
    output = ROOT / 'results' / (run + '.json')
    result = {'run_id': run, 'status': 'STARTED', 'movement_issued': False}
    def save():
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    save()
    try:
        hwnd = d.find_game_window()
        if not hwnd:
            raise RuntimeError('no interactive game window')
        d.ensure_foreground(hwnd)
        if d.win32gui.GetForegroundWindow() != hwnd:
            raise RuntimeError('foreground not acquired')
        command(hwnd, '/targetexact Deputy Willem')
        interacting = '--interact' in sys.argv
        if interacting:
            if d.win32gui.GetForegroundWindow() != hwnd:
                raise RuntimeError('foreground lost before right click')
            d.u.SetCursorPos(750, 460)
            time.sleep(0.3)
            d.u.mouse_event(0x0008, 0, 0, 0, 0)
            try:
                time.sleep(0.15)
            finally:
                d.u.mouse_event(0x0010, 0, 0, 0, 0)
            time.sleep(2)
            result['dialog_screenshot'] = str(d.screenshot(run + '_dialog.png'))
        sample(hwnd, 'npc', run + '_')
        command(hwnd, '/run local r=WowProbeWotLK_Report.runs local m=r[#r].meta m.target_guid=UnitGUID("target") m.interact_range=CheckInteractDistance("target",3) m.interact_key=GetBindingKey("INTERACTTARGET")')
        if interacting:
            command(hwnd, '/run local r=WowProbeWotLK_Report.runs local m=r[#r].meta m.quest_visible=QuestFrame:IsShown() and 1 or 0 m.gossip_visible=GossipFrame:IsShown() and 1 or 0 m.quest_title=GetTitleText()')
        shot = d.screenshot(run + '_selected.png')
        requested = time.time_ns()
        command(hwnd, '/reload')
        deadline = time.monotonic() + 40
        previous = None
        while time.monotonic() < deadline:
            try:
                if SOURCE.stat().st_mtime_ns >= requested:
                    raw = SOURCE.read_bytes()
                    if (run + '_npc').encode() in raw:
                        digest = hashlib.sha256(raw).hexdigest()
                        if previous == digest:
                            break
                        previous = digest
            except (PermissionError, FileNotFoundError):
                pass
            time.sleep(1)
        else:
            raise TimeoutError('NPC preflight not persisted')
        backup = ROOT / '.cache' / 'client-observations' / (run + '.lua')
        with backup.open('xb') as handle:
            handle.write(raw)
        result.update(acceptance=inspect(raw, run + '_npc', 'Probehuman', 'Deputy Willem'),
                      local_raw_backup=str(backup), screenshot=str(shot), status='PREFLIGHT_ACCEPTED')
        if interacting:
            meta = result['acceptance']['sample']['meta']
            if meta.get('quest_visible') != 1 and meta.get('gossip_visible') != 1:
                raise ValueError('NPC dialog not visible')
            result['status'] = 'DIALOG_VERIFIED'
        save()
        time.sleep(10)
        d.screenshot(run + '_after-reload.png')
        return 0
    except Exception as exc:
        result.update(status='FAILED', error=f'{type(exc).__name__}: {exc}')
        save()
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
