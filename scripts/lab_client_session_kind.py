"""Report whether the session of the driver is a remote session.

The client of 3.3.5a refuses to start when the session is a remote one, so
the driver has to know it before it tries to start the client.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win32api
import win32ts

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'


def main():
    lines = []
    lines.append('SM_REMOTESESSION %s' % win32api.GetSystemMetrics(0x1000))
    try:
        session = win32ts.WTSGetActiveConsoleSessionId()
        lines.append('active console session %s' % session)
        info = win32ts.WTSQuerySessionInformation(
            win32ts.WTS_CURRENT_SERVER_HANDLE, session,
            win32ts.WTSConnectState)
        lines.append('console state %s' % (info,))
    except Exception as exc:
        lines.append('console session: %r' % (exc,))
    try:
        import win32process
        lines.append('this process session %s' % win32process.ProcessIdToSessionId(
            __import__('os').getpid()))
    except Exception as exc:
        lines.append('session of the process: %r' % (exc,))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'session-report.txt').write_text('\n'.join(lines), encoding='utf-8')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        import traceback
        (OUT / 'session-report.txt').write_text(
            traceback.format_exc(), encoding='utf-8')
        raise
