"""Parser acceptance/failure tests use synthetic SavedVariables, not live evidence."""
import unittest
from client_snapshot_task import inspect, inspect_displacement


def fixture(scene='new_run', character='Probehuman'):
    meta = {'scene': scene, 'x': .48, 'y': .43, 'facing': 1e-8, 'speed': 0, 'sample_time': 123.0}
    import json
    lines = ['\t\t{', '\t\t\t["meta"] = {']
    lines += ['\t'*4 + f'[{json.dumps(k)}] = {json.dumps(v)},' for k, v in meta.items()]
    lines += ['\t\t\t},', '\t\t\t["records"] = {']
    for key, value, status in (
        ('G4.name.player', character, 'OK'), ('G4.health.player', 52, 'OK'),
        ('G4.combat.player', None, 'NIL'), ('G4.name.target', None, 'NIL'),
        ('G3.subzone', 'Northshire Valley', 'OK')):
        lines += ['\t'*4 + '{', '\t'*5 + f'["probe_id"] = {json.dumps(key)},',
                  '\t'*5 + f'["value_status"] = {json.dumps(status)},']
        if value is not None:
            lines += ['\t'*5 + f'["value"] = {json.dumps(value)},']
        lines += ['\t'*4 + '},']
    return ('\n'.join(lines + ['\t\t\t},', '\t\t},']) + '\n').encode()


class SnapshotTests(unittest.TestCase):
    def test_displacement_requires_new_time_and_changed_position(self):
        before = inspect(fixture(), 'new_run', 'Probehuman')
        after = inspect(fixture().replace(b'123.0', b'124.0').replace(
            b'"x"] = 0.48', b'"x"] = 0.4801'), 'new_run', 'Probehuman')
        self.assertEqual(inspect_displacement(before, after)['status'], 'DISPLACEMENT_VERIFIED')
        with self.assertRaises(ValueError):
            inspect_displacement(before, before)
        unchanged = inspect(fixture().replace(b'123.0', b'124.0'), 'new_run', 'Probehuman')
        with self.assertRaises(ValueError):
            inspect_displacement(before, unchanged)

    def test_accepted(self):
        result = inspect(fixture(), 'new_run', 'Probehuman')
        self.assertEqual(result['status'], 'SNAPSHOT_ACCEPTED')
        self.assertFalse(result['movement_issued'])

    def test_wrong_character_missing_and_duplicate_scene(self):
        for raw, scene in ((fixture(character='Other'), 'new_run'), (fixture(), 'old_run'),
                           (fixture()+fixture(), 'new_run')):
            with self.assertRaises(ValueError):
                inspect(raw, scene, 'Probehuman')

    def test_bad_state_and_truncation(self):
        for raw in (fixture().replace(b'"speed"] = 0', b'"speed"] = 1'),
                    fixture().replace(b'"x"] = 0.48', b'"x"] = 0.0'), fixture()[:100]):
            with self.assertRaises(ValueError):
                inspect(raw, 'new_run', 'Probehuman')

    def test_expected_self_target_and_mismatch(self):
        raw = fixture().replace(
            b'["probe_id"] = "G4.name.target",\n\t\t\t\t\t["value_status"] = "NIL",',
            b'["probe_id"] = "G4.name.target",\n\t\t\t\t\t["value_status"] = "OK",\n\t\t\t\t\t["value"] = "Probehuman",')
        self.assertEqual(inspect(raw, 'new_run', 'Probehuman', 'Probehuman')['status'], 'SNAPSHOT_ACCEPTED')
        with self.assertRaises(ValueError):
            inspect(raw, 'new_run', 'Probehuman')
        with self.assertRaises(ValueError):
            inspect(fixture(), 'new_run', 'Probehuman', 'Probehuman')


if __name__ == '__main__':
    unittest.main()
