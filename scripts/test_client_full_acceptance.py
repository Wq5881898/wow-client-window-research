"""The post conditions of the standard acceptance (A4).

The exit code of a step is not enough to say that the chain is done. The
checks are tested here with the results that the review named as
counterexamples: a fight that ended with a retreat, a result that cannot be
read, and a recovery that did not finish.
"""
import json
import tempfile
import unittest
from pathlib import Path

import lab_client_full_acceptance as acceptance


def write_result(directory, name, payload):
    path = Path(directory) / name
    path.write_text(json.dumps(payload), encoding='utf-8')
    return str(path)


class AcceptancePostConditionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp(prefix='acceptance-')

    def test_a_fight_that_ended_with_a_retreat_is_not_a_pass(self):
        path = write_result(self.directory, 'combat.json', {
            'status': 'COMBAT_LOOP_COMPLETED', 'outcome': 'recovered'})
        record = {'steps': [{'step': 'combat', 'code': 0, 'result': path}]}
        problems = acceptance.problems_of(record)
        self.assertTrue(problems)
        self.assertIn('combat', problems[0])

    def test_a_fight_with_a_kill_is_a_pass(self):
        path = write_result(self.directory, 'combat.json', {
            'status': 'COMBAT_LOOP_COMPLETED', 'outcome': 'target_defeated'})
        record = {'steps': [{'step': 'combat', 'code': 0, 'result': path}]}
        self.assertEqual(acceptance.problems_of(record), [])

    def test_a_result_that_cannot_be_read_is_rejected(self):
        path = str(Path(self.directory) / 'missing.json')
        record = {'steps': [{'step': 'combat', 'code': 0, 'result': path}]}
        problems = acceptance.problems_of(record)
        self.assertTrue(problems)

    def test_a_recovery_that_did_not_finish_is_rejected(self):
        path = write_result(self.directory, 'recovery.json', {
            'status': 'FAILED'})
        record = {'steps': [{'step': 'danger_recovery', 'code': 0,
                             'result': path}]}
        problems = acceptance.problems_of(record)
        self.assertTrue(problems)

    def test_a_step_without_a_post_condition_is_not_checked(self):
        record = {'steps': [{'step': 'restart', 'code': 0, 'result': None}]}
        self.assertEqual(acceptance.problems_of(record), [])

    def test_the_four_conditions_are_defined(self):
        self.assertEqual(sorted(acceptance.REQUIRED),
                         ['combat', 'danger_recovery', 'danger_setup',
                          'relogin'])


if __name__ == '__main__':
    unittest.main()
