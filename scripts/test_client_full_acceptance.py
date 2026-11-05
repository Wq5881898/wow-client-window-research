"""The post conditions of the standard acceptance (A4).

The exit code of a step is not enough to say that the chain is done. The
checks are tested here with the results that the review named as
counterexamples: a fight that ended with a retreat, a result that cannot
be read, a step that wrote no result at all, a result of another run and
a recovery without the second death.
"""
import json
import tempfile
import unittest
from pathlib import Path

import lab_client_full_acceptance as acceptance
from client_parent_run import stamp


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

    def test_a_step_that_wrote_no_result_is_rejected(self):
        # A missing result may not be skipped: the step has to show what it
        # promised, and a step without a result has shown nothing.
        record = {'steps': [{'step': 'combat', 'code': 0, 'result': None}]}
        problems = acceptance.problems_of(record)
        self.assertTrue(problems)
        self.assertIn('combat', problems[0])

    def test_a_recovery_that_did_not_finish_is_rejected(self):
        path = write_result(self.directory, 'recovery.json', {
            'status': 'FAILED'})
        record = {'steps': [{'step': 'danger_recovery', 'code': 0,
                             'result': path}]}
        problems = acceptance.problems_of(record)
        self.assertTrue(problems)

    def test_a_recovery_without_the_second_death_is_rejected(self):
        # The recovery reports RECOVERED even when it found no hostile
        # creature, so the second death has to be asked for by itself.
        path = write_result(self.directory, 'recovery.json', {
            'status': 'RECOVERED', 'second_death': 'no hostile in reach'})
        record = {'steps': [{'step': 'danger_recovery', 'code': 0,
                             'result': path}]}
        problems = acceptance.problems_of(record)
        self.assertTrue(problems)

    def test_a_recovery_with_the_second_death_is_a_pass(self):
        path = write_result(self.directory, 'recovery.json', {
            'status': 'RECOVERED', 'second_death': 'happened'})
        record = {'steps': [{'step': 'danger_recovery', 'code': 0,
                             'result': path}]}
        self.assertEqual(acceptance.problems_of(record), [])

    def test_a_step_without_a_post_condition_is_not_checked(self):
        record = {'steps': [{'step': 'restart', 'code': 0, 'result': None}]}
        self.assertEqual(acceptance.problems_of(record), [])

    def test_a_result_of_another_run_is_rejected(self):
        path = write_result(self.directory, 'combat.json', {
            'run': 'combat', 'status': 'COMBAT_LOOP_COMPLETED',
            'outcome': 'target_defeated', 'parent_run': 'another_run'})
        record = {'steps': [{'step': 'combat', 'code': 0, 'result': path}]}
        problems = acceptance.problems_of(record, 'this_run')
        self.assertTrue(problems)

    def test_a_result_of_this_run_is_accepted(self):
        path = write_result(self.directory, 'combat.json', {
            'run': 'combat', 'status': 'COMBAT_LOOP_COMPLETED',
            'outcome': 'target_defeated', 'parent_run': 'this_run'})
        record = {'steps': [{'step': 'combat', 'code': 0, 'result': path}]}
        self.assertEqual(acceptance.problems_of(record, 'this_run'), [])

    def test_a_file_that_does_not_hold_its_own_run_is_rejected(self):
        path = write_result(self.directory, 'combat.json', {
            'run': 'another_combat', 'status': 'COMBAT_LOOP_COMPLETED',
            'outcome': 'target_defeated', 'parent_run': 'this_run'})
        record = {'steps': [{'step': 'combat', 'code': 0, 'result': path}]}
        problems = acceptance.problems_of(record, 'this_run')
        self.assertTrue(problems)

    def test_the_conditions_of_the_steps_are_defined(self):
        self.assertEqual(sorted(acceptance.REQUIRED),
                         ['combat', 'danger_recovery', 'danger_setup',
                          'enter', 'relogin'])

    def test_every_step_of_the_chain_is_known(self):
        for name, script, argv, extra in acceptance.STEPS:
            self.assertIn(name, acceptance.RESULT_PREFIX)
            self.assertTrue(Path(acceptance.ROOT / 'scripts' / script).exists())


class ParentRunTests(unittest.TestCase):
    def test_the_parent_is_read_from_the_arguments(self):
        result = stamp({}, ['script.py', '--parent-run', 'run-1',
                            '--attempt', '2'])
        self.assertEqual(result['parent_run'], 'run-1')
        self.assertEqual(result['parent_attempt'], 2)

    def test_a_step_without_a_parent_is_left_alone(self):
        result = stamp({}, ['script.py'])
        self.assertNotIn('parent_run', result)

    def test_an_attempt_that_is_not_a_number_is_ignored(self):
        result = stamp({}, ['script.py', '--parent-run', 'run-1',
                            '--attempt', 'x'])
        self.assertNotIn('parent_attempt', result)


if __name__ == '__main__':
    unittest.main()
