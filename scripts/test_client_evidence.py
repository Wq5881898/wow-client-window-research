import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))

import client_evidence


class EvidenceLabelTest(unittest.TestCase):
    def test_repeated_label_gets_a_suffix(self):
        with TemporaryDirectory() as tmp:
            client_evidence.OUT = Path(tmp)
            evidence = client_evidence.Evidence('run')
            evidence.capture('05-damage')
            evidence.capture('05-damage')
            evidence.capture('05-damage')
            labels = [frame['label'] for frame in evidence.frames]
            self.assertEqual(labels, ['05-damage', '05-damage-02', '05-damage-03'])

    def test_distinct_labels_are_untouched(self):
        with TemporaryDirectory() as tmp:
            client_evidence.OUT = Path(tmp)
            evidence = client_evidence.Evidence('run')
            evidence.capture('01-start')
            evidence.capture('02-mid')
            evidence.capture('01-start')
            labels = [frame['label'] for frame in evidence.frames]
            self.assertEqual(labels, ['01-start', '02-mid', '01-start-02'])

    def test_same_label_does_not_overwrite_the_first_file(self):
        with TemporaryDirectory() as tmp:
            client_evidence.OUT = Path(tmp)
            evidence = client_evidence.Evidence('run')
            first = evidence.capture('frame')
            second = evidence.capture('frame')
            self.assertNotEqual(first['path'], second['path'])


if __name__ == '__main__':
    unittest.main()
