"""The cast of the driver has to stop when the character is in danger.

The check that watches the character while a spell is in the air used to be
ignored by the executor, so a cast that had to be stopped went on and the
character died in the fight. The test drives the executor with a fake
reader and a fake keyboard and counts what was typed, so no input reaches
the desktop.
"""
import unittest

import lab_client_combat_loop as loop


def state(**overrides):
    """A telemetry reading of a character that is well."""
    result = dict(sequence=1, game_ms=100, health=52, max_health=52,
                  power=100, combat=False, dead=False, target_health=42,
                  target_max_health=42, spell_range=1, spell_learned=True,
                  casting=False, speed=0.0, target_guid='0xABC',
                  target_exists=True, target_attackable=True,
                  target_dead=False, pos_x=0.5, pos_y=0.43, facing=0.0,
                  event_serial=0, cast_started=0, cast_succeeded=0,
                  cast_failed=0, ui_errors=0)
    result.update(overrides)
    return result


class FakeReader:
    """A reader that hands out the states it was given."""

    def __init__(self, states):
        self.states = list(states)
        self.calls = 0

    def __call__(self):
        reading = self.states[min(self.calls, len(self.states) - 1)]
        self.calls += 1
        return reading


class CastCancellationTests(unittest.TestCase):
    def setUp(self):
        self.typed = []
        self.keys = []
        self.originals = (loop.d.post_key, loop.win32gui.PostMessage,
                          loop.hold)
        loop.d.post_key = lambda hwnd, key: self.keys.append(key)
        loop.win32gui.PostMessage = (
            lambda hwnd, message, char, extra: self.typed.append(chr(char)))
        loop.hold = self.fake_hold
        self.addCleanup(self.restore)

    def fake_hold(self, vk, seconds, stop=None):
        """A key that is released as soon as the run stops it."""
        self.keys.append(('down', vk))
        if stop is not None:
            stop.wait(3.0)
        self.keys.append(('up', vk))

    def restore(self):
        (loop.d.post_key, loop.win32gui.PostMessage,
         loop.hold) = self.originals

    def test_a_cast_that_is_stopped_raises(self):
        reader = FakeReader([state(health=10)])
        with self.assertRaises(loop.ActionCancelled) as caught:
            loop.cast(1, '/cast Fireball', reader,
                      on_tick=lambda s: 'low_health')
        self.assertEqual(caught.exception.reason, 'low_health')

    def test_a_stopped_cast_does_not_type_the_whole_command(self):
        reader = FakeReader([state()])
        with self.assertRaises(loop.ActionCancelled):
            loop.cast(1, '/cast Fireball', reader,
                      on_tick=lambda s: 'low_health')
        self.assertNotEqual(''.join(self.typed), '/cast Fireball')

    def test_a_cast_that_may_go_on_types_the_command(self):
        reader = FakeReader([state(), state(cast_succeeded=1)])
        after = loop.cast(1, '/cast Fireball', reader,
                          on_tick=lambda s: None)
        self.assertEqual(after['cast_succeeded'], 1)
        self.assertEqual(''.join(self.typed), '/cast Fireball')

    def test_a_reader_that_fails_stops_the_cast(self):
        def broken():
            raise ValueError('the panel is gone')
        with self.assertRaises(loop.ActionCancelled) as caught:
            loop.cast(1, '/cast Fireball', broken, on_tick=lambda s: None)
        self.assertEqual(caught.exception.reason, loop.STOP_READING)

    def test_a_movement_that_is_stopped_releases_the_key(self):
        reader = FakeReader([state(health=10)])
        states, reason = loop.move_while_watching(
            1, loop.VK_FORWARD, 2.0, reader,
            deadline_check=lambda s: 'low_health')
        self.assertEqual(reason, 'low_health')
        self.assertTrue(states)
        self.assertIn(('up', loop.VK_FORWARD), self.keys)

    def test_a_movement_that_may_go_on_keeps_the_key_held(self):
        reader = FakeReader([state()])
        states, reason = loop.move_while_watching(
            1, loop.VK_FORWARD, 0.3, reader, deadline_check=lambda s: None)
        self.assertIsNone(reason)
        self.assertTrue(states)
        self.assertIn(('up', loop.VK_FORWARD), self.keys)


if __name__ == '__main__':
    unittest.main()
