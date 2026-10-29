"""Install a bounded read-only OnUpdate recorder through external chat commands."""
import hashlib
import argparse
import json
import re
import time

import lab_driver5 as d
from lab_distance_scenarios import command
from lab_feedback_correction import SOURCE, capture
from lab_short_input_calibration import timed_hold
from summarize_target_scenarios import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, choices=(0.08, 0.09642223536365996, 0.115), default=0.09642223536365996)
    parser.add_argument('--walk', action='store_true')
    args = parser.parse_args()
    prefix = 'framemotion_' + str(time.time_ns()) + '_'
    path = ROOT / 'results' / (prefix + 'trace.json')
    result = {'prefix': prefix, 'status': 'STARTED', 'walk_toggle_requested': args.walk}
    toggled = False
    def save():
        path.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    save()
    try:
        hwnd = d.find_game_window()
        if not hwnd:
            raise RuntimeError('No game window')
        d.ensure_foreground(hwnd)
        result['baseline'] = capture(hwnd, 'baseline', prefix)
        if args.walk:
            d.post_key(hwnd, 0x6F, 0x35)  # NUMPAD DIVIDE: default toggle run/walk
            toggled = True
            time.sleep(1)
        command(hwnd, '/run SetMapToCurrentZone()')
        command(hwnd, '/run WPF=CreateFrame("Frame"); WPT={}; WowProbeWotLK_Report.frame_trace=WPT')
        command(hwnd, '/run function WPRecord(e) local x,y=GetPlayerMapPosition("player"); WPT[#WPT+1]=string.format("%.6f,%.6f,%.9f,%.9f,%.4f,%.6f",GetTime(),e,x,y,GetUnitSpeed("player"),GetPlayerFacing()) end')
        command(hwnd, '/run WPF:SetScript("OnUpdate",function(s,e) if not WPStart then return end if GetTime()-WPStart>6 or #WPT>=1000 then s:SetScript("OnUpdate",nil) return end WPRecord(e) end)')
        command(hwnd, '/run WPStart=GetTime()')
        row = {'requested_seconds': args.seconds}
        result['input'] = row
        timed_hold(hwnd, row['requested_seconds'], row)
        time.sleep(6)
        if toggled:
            d.post_key(hwnd, 0x6F, 0x35)
            toggled = False
            result['restore_toggle_sent'] = True
        result['final'] = capture(hwnd, 'final', prefix)
        raw = SOURCE.read_bytes()
        text = raw.decode('utf-8-sig')
        match = re.search(r'\["frame_trace"\] = \{(.*?)\n\s*\}', text, re.S)
        if not match:
            raise RuntimeError('Missing frame trace')
        rows = re.findall(r'"([0-9.,-]+)"', match.group(1))
        frames = [dict(zip(('time', 'elapsed', 'x', 'y', 'speed', 'facing'), map(float, row.split(',')))) for row in rows]
        assert 0 < len(frames) <= 1000
        assert all(a['time'] <= b['time'] for a, b in zip(frames, frames[1:]))
        moving = [i for i, f in enumerate(frames) if f['speed'] > 0]
        assert moving, 'No positive-speed frames'
        first, last = moving[0], moving[-1]
        assert first > 0 and last + 1 < len(frames), 'Movement not bracketed by stationary frames'
        result['frames'] = frames
        result['source_sha256'] = hashlib.sha256(raw).hexdigest()
        result['summary'] = {
            'frame_count': len(frames), 'moving_frame_count': len(moving),
            'first_to_last_positive_speed_seconds': frames[last]['time'] - frames[first]['time'],
            'stationary_bracket_seconds': frames[last+1]['time'] - frames[first-1]['time'],
            'positive_speed_values': sorted({frames[i]['speed'] for i in moving}),
            'min_frame_elapsed': min(f['elapsed'] for f in frames),
            'max_frame_elapsed': max(f['elapsed'] for f in frames),
            'trace_dy': frames[-1]['y'] - frames[0]['y'],
            'snapshot_dy': result['final']['meta']['y'] - result['baseline']['meta']['y'],
        }
        result['status'] = 'COMPLETED'
        save()
        d.log('frame motion result', str(path))
    except Exception as exc:
        result['status'] = 'FAILED'
        result['error'] = str(exc)
        save()
        raise
    finally:
        if toggled:
            d.post_key(hwnd, 0x6F, 0x35)
            result['restore_toggle_sent'] = True
            save()


if __name__ == '__main__':
    main()
