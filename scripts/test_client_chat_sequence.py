import unittest
from client_chat_sequence import ChatSequence, spell_result


class ChatTests(unittest.TestCase):
    def test_cooperative_submit_once(self):
        sequence = ChatSequence('/cast Frost Armor', 0)
        actions = []
        for i in range(100):
            action = sequence.step(i * .1, True)
            if action:
                actions.append(action)
        self.assertEqual(actions[0], ('key', 13))
        self.assertEqual(actions[-1], ('key', 13))
        self.assertEqual(''.join(v for k, v in actions if k == 'char'), '/cast Frost Armor')
        self.assertEqual(sum(k == 'key' for k, _ in actions), 2)

    def test_abort_before_submit(self):
        for now, permitted in [(0.1, False), (9, True)]:
            sequence = ChatSequence('/cast Frost Armor', 0)
            sequence.step(0, True)
            with self.assertRaises(ValueError):
                sequence.step(now, permitted)
            self.assertIsNone(sequence.step(10, True))
            self.assertFalse(sequence.submitted)

    def test_event_outcomes(self):
        before = dict(cast_failed=0, ui_errors=0, cast_succeeded=65535,
                      event_spell=0, event_kind=0)
        self.assertEqual(spell_result(before, before, 168), 'PENDING')
        after = dict(before, cast_succeeded=0, event_spell=168, event_kind=2)
        self.assertEqual(spell_result(before, after, 168), 'SUCCEEDED')
        self.assertEqual(spell_result(before, dict(after, event_spell=133), 168), 'AMBIGUOUS')
        self.assertEqual(spell_result(before, dict(after, ui_errors=1), 168), 'FAILED')


if __name__ == '__main__':
    unittest.main()
