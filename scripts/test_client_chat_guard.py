import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import client_chat_guard


class ChatGuardTest(unittest.TestCase):
    """The chat input must be closed before the character is moved."""

    def setUp(self):
        self.original_post_key = client_chat_guard.d.post_key
        self.original_focus = client_chat_guard.ensure_focus
        self.keys = []
        client_chat_guard.ensure_focus = lambda hwnd: True

    def tearDown(self):
        client_chat_guard.d.post_key = self.original_post_key
        client_chat_guard.ensure_focus = self.original_focus

    def _install(self, states):
        """A reader that walks through the given chat_open values."""
        self.keys = []
        client_chat_guard.d.post_key = lambda hwnd, vk: self.keys.append(vk)
        index = {'n': 0}

        def reader():
            position = min(index['n'], len(states) - 1)
            index['n'] += 1
            return {'chat_open': states[position]}

        return reader

    def test_a_closed_chat_needs_no_key_press(self):
        reader = self._install([False])
        self.assertTrue(client_chat_guard.close_chat(1, reader))
        self.assertEqual(self.keys, [])

    def test_an_open_chat_is_closed_with_escape(self):
        reader = self._install([True, False])
        self.assertTrue(client_chat_guard.close_chat(1, reader))
        self.assertEqual(len(self.keys), 1)

    def test_a_chat_that_stays_open_is_reported(self):
        reader = self._install([True])
        self.assertFalse(client_chat_guard.close_chat(1, reader))
        self.assertEqual(len(self.keys), 3)

    def test_ensure_chat_closed_raises_when_it_stays_open(self):
        reader = self._install([True])
        with self.assertRaises(ValueError):
            client_chat_guard.ensure_chat_closed(1, reader)

    def test_a_reader_that_fails_is_treated_as_closed(self):
        def reader():
            raise ValueError('no telemetry')

        self.assertFalse(client_chat_guard.chat_open(reader))
        self.assertTrue(client_chat_guard.close_chat(1, reader))


if __name__ == '__main__':
    unittest.main()
