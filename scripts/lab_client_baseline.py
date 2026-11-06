"""The current state of the client, read once for the record.

The script reports what the client shows right now: the session it runs
in, the window that draws it, the version of the probe that is deployed
and the telemetry of the character. It sends no input, so it is safe to
run while the character is doing something.

The report is written under ``results/`` with the name of the run, so the
state of a run can be looked up later.
"""
import ctypes
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_driver5 as d
import win32con
import win32gui
from client_capture import grab_desktop
from client_live_state import decode, assert_real_frame

ROOT = Path(__file__).resolve().parents[1]
CLIENT = Path(r'C:\Azerothcore\wowclient\WOW_3.3.5a')
DEPLOYED = (CLIENT / 'Interface' / 'AddOns' / 'WowProbeWotLK' /
            'WowProbeLive.lua')
REPO = ROOT / 'probes' / 'WowProbeWotLK' / 'WowProbeLive.lua'

# The fields of the telemetry that describe the character and the place.
FIELDS = (
    'protocol', 'sequence', 'game_ms',
    'player_guid', 'level', 'xp', 'xp_max',
    'health', 'max_health', 'power', 'combat', 'dead', 'speed',
    'pos_x', 'pos_y', 'facing',
    'zone_hash', 'subzone_hash', 'map_id',
    'money', 'bag_items', 'cursor_name_hash',
    'known_spells', 'spell_bits', 'frost_armor',
    'target_exists', 'target_attackable', 'target_dead', 'target_health',
    'target_max_health', 'target_guid', 'target_name_hash',
    'target_class_name', 'spell_learned', 'spell_range', 'casting',
    'threat', 'chat_open', 'corpse_exists',
)


def sha256(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except Exception as exc:
        return 'unreadable: ' + repr(exc)


def session_of():
    """The session of this process and whether it is a remote one.

    The client refuses to start in a session that carries the remote mark,
    so the mark is worth reporting: a run in such a session would fail for
    a reason that has nothing to do with the driver.
    """
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    session = ctypes.c_ulong(0)
    kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(session))
    return {'session': session.value,
            'remote': bool(user32.GetSystemMetrics(0x1000)),
            'screen': [user32.GetSystemMetrics(0),
                       user32.GetSystemMetrics(1)]}


def window_of():
    """The window of the client and the window that is in front."""
    hwnd = d.find_game_window()
    foreground = d.u.GetForegroundWindow()
    report = {'hwnd': hwnd, 'foreground': foreground}
    if foreground and foreground != hwnd:
        # Another window was in front. The client of the fullscreen mode
        # shrinks itself when it loses the focus, and then the panel of the
        # probe is not on the screen any more.
        report['foreground_class'] = win32gui.GetClassName(foreground)
        report['foreground_title'] = win32gui.GetWindowText(foreground)
    if hwnd:
        report.update({
            'class': win32gui.GetClassName(hwnd),
            'visible': bool(win32gui.IsWindowVisible(hwnd)),
            'iconic': bool(win32gui.IsIconic(hwnd)),
            'rect': list(win32gui.GetWindowRect(hwnd)),
            'title': win32gui.GetWindowText(hwnd),
        })
    return report


def display_mode():
    """The display mode of the client, read from its own configuration."""
    path = CLIENT / 'WTF' / 'Config.wtf'
    try:
        for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
            if line.startswith('SET gxWindow'):
                return line.strip()
    except Exception as exc:
        return 'unreadable: ' + repr(exc)
    return 'not set'


def main():
    run = 'client_baseline_' + str(time.time_ns())
    report = {'run': run, 'at': time.time()}
    try:
        report['session'] = session_of()
        report['window'] = window_of()
        # The client has to be in front: another window covers the panel of
        # the probe, and the client shrinks itself when it loses the focus.
        hwnd = d.game_window()
        try:
            d.ensure_foreground(hwnd)
        except Exception as exc:
            report['foreground_error'] = repr(exc)
        time.sleep(1.5)
        report['window_after'] = window_of()
        report['display_mode'] = display_mode()
        report['probe'] = {
            'deployed': str(DEPLOYED),
            'deployed_sha256': sha256(DEPLOYED),
            'repo_sha256': sha256(REPO),
            'deployed_exists': DEPLOYED.exists(),
        }
        report['probe']['same'] = (
            report['probe']['deployed_sha256']
            == report['probe']['repo_sha256'])
        report['probe']['protocol'] = None
        for line in DEPLOYED.read_text(encoding='utf-8',
                                       errors='replace').splitlines():
            if 'local PROTOCOL' in line:
                report['probe']['protocol'] = line.strip()
                break
        report['client'] = {'process': None}
        # Two readings a moment apart: the sequence has to move on, or the
        # panel is a picture of the past.
        first = decode(assert_real_frame(grab_desktop()))
        time.sleep(1.0)
        second = decode(assert_real_frame(grab_desktop()))
        report['telemetry'] = {key: first.get(key) for key in FIELDS}
        report['telemetry']['sequence_after'] = second.get('sequence')
        report['telemetry']['game_ms_after'] = second.get('game_ms')
        report['telemetry']['advancing'] = (
            second.get('sequence') != first.get('sequence'))
        report['events'] = second.get('events')
        report['status'] = 'READ'
    except Exception as exc:
        report['error'] = repr(exc)
        report['status'] = 'FAILED'
    path = ROOT / 'results' / (run + '.json')
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False),
                    encoding='utf-8')
    d.log('baseline', str(path), report['status'])
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report['status'] == 'READ' else 1


if __name__ == '__main__':
    raise SystemExit(main())
