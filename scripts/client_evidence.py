"""Evidence capture for live client runs.

Every live run stores a start, a middle and an end frame plus the decoded
telemetry, so a result can be audited without trusting the run summary.
"""
import json
import time
from pathlib import Path
from PIL import ImageGrab
import lab_driver5 as d

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'desktop-check'


class Evidence:
    """Collects named frames and the telemetry that goes with them."""

    def __init__(self, run):
        self.run = run
        self.frames = []
        self.states = []
        self._counts = {}

    def _unique_label(self, label):
        """Never write two frames onto the same file.

        A label repeated inside one run would silently overwrite the earlier
        screenshot, so the second use gets an index suffix.
        """
        count = self._counts.get(label, 0) + 1
        self._counts[label] = count
        return label if count == 1 else '%s-%02d' % (label, count)

    def capture(self, label, state=None):
        label = self._unique_label(label)
        path = OUT / ('%s_%s.png' % (self.run, label))
        try:
            d.screenshot(path.name)
            source = 'desktop'
        except Exception as exc:
            path = None
            source = 'capture_failed: ' + repr(exc)
        self.frames.append({'label': label, 'path': str(path) if path else None,
                            'source': source,
                            'host_monotonic': time.monotonic()})
        if state is not None:
            self.states.append({'label': label, 'state': state})
        return self.frames[-1]

    def summary(self):
        return {'run': self.run, 'frames': self.frames, 'states': self.states}

    def write(self, result, extra=None):
        result['evidence'] = self.summary()
        path = ROOT / 'results' / (self.run + '.json')
        with path.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
        return path
