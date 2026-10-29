"""Read-only inventory of evidence referenced by this conversation.

Writes only a new inventory report; does not repair, recreate or overwrite evidence.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    groups = {
        'current_p3': [
            'agent_wow_batch_p3_batch01.json', 'agent_wow_task_p3_batch01_unit1.json',
            'agent_wow_task_p3_batch01_unit1.actions.jsonl',
            'agent_wow_task_p3_batch01_unit1.checkpoint.json',
            'agent_wow_bridge_p3_batch01_unit1.packets.json',
            'p3_batch01_position_audit.json',
            'agent_wow_bridge_p3_position_reconcile01.json',
            'agent_wow_bridge_p3_position_reconcile01.packets.json',
        ],
        'task_evidence_audit': ['task_unit_evidence_audit_2026-10-28.json'] + [
            f'agent_wow_task_{r}.{s}'
            for r in ('run99_task_unit', 'run100_task_unit', 'run102_task_unit_repeat',
                      'run103_task_unit_repeat', 'run104_task_unit_repeat', 'run105_task_unit_repeat',
                      'run106_task_unit_repeat', 'run107_task_unit_repeat')
            for s in ('json', 'actions.jsonl', 'checkpoint.json')],
        'login_boundary': [
            'agent_wow_bridge_run100_task_unit.packets.json',
            'agent_wow_bridge_run101_collection_verify.packets.json',
            'agent_wow_task_run111_movement_boundary.json',
            'agent_wow_bridge_run112_movement_verify.packets.json',
            'agent_wow_task_run113_confirmed_combat.json',
            'agent_wow_bridge_run114_postcombat_verify.packets.json'],
        'newbie': [
            'newbie_baseline_2026-10-21.json', 'newbie_motion_2026-10-21.json',
            'newbie_continuous_2026-10-24.json', 'newbie_roundtrip_2026-10-24.json',
            'newbie_compensated_2026-10-28.json', 'newbie_compensated_repeats_2026-10-28.json',
            'newbie_feedback_2026-10-28.json'] + [
                f'newbie_compensated_trial{i}_2026-10-28.json' for i in range(1, 4)],
        'correction_and_timing': [
            'feedback_1793144509847049200_correction.json',
            'feedback_1793145428516415500_correction.json',
            'shortinput_1793146919965631400_calibration.json',
            'shortinput_1793147865465805500_calibration.json'],
        'frame_motion': [f'framemotion_{n}_trace.json' for n in (
            '1793160660040551800', '1793162694384670000', '1793163000287441400',
            '1793164241132578100', '1793164554469934200', '1793165607701264100',
            '1793166009480494200', '1793169990334700100', '1793170325831435300',
            '1793170669162135700')] + [
            'frame_motion_repeats_2026-10-28.json', 'frame_duration_comparison_2026-10-28.json',
            'walk_comparison_2026-10-28.json', 'walk_repeats_2026-10-28.json'],
    }

    def inspect(path):
        if not path.is_file():
            return {'status': 'MISSING'}
        raw = path.read_bytes()
        try:
            text = raw.decode('utf-8-sig')
            if path.suffix == '.jsonl':
                for line in text.splitlines():
                    if line.strip():
                        json.loads(line)
                if not text.strip():
                    raise ValueError('empty JSONL')
            else:
                json.loads(text)
            return {'status': 'PARSEABLE', 'bytes': len(raw)}
        except (ValueError, UnicodeError) as exc:
            return {'status': 'CORRUPT', 'bytes': len(raw), 'error': str(exc)}

    result = {'scope': 'presence and UTF-8/JSON syntax only; not original hash or semantic verification',
              'groups': {}, 'results_json_inventory': {}}
    for group, names in groups.items():
        rows = {name: inspect(ROOT / 'results' / name) for name in names}
        result['groups'][group] = rows
        print(group, {s: sum(r['status'] == s for r in rows.values())
                      for s in ('MISSING', 'CORRUPT', 'PARSEABLE')})
    for path in sorted((ROOT / 'results').glob('*.json')):
        result['results_json_inventory'][path.name] = inspect(path)
    counts = {s: sum(r['status'] == s for r in result['results_json_inventory'].values())
              for s in ('CORRUPT', 'PARSEABLE')}
    print('all results/*.json', counts)
    output = ROOT / 'docs' / 'conversation_evidence_inventory_2026-10-29.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(output)


if __name__ == '__main__':
    main()
