"""Bounded relative mouse guidance using game-internal read-only feedback."""
import math
from client_live_state import name_hash


class CursorController:
    def __init__(self, target, focus_name, max_steps=40, tolerance=5):
        self.target = target
        self.focus_hash = name_hash(focus_name)
        self.max_steps = max_steps
        self.tolerance = tolerance
        self.steps = 0
        self.last_sequence = None

    def observe(self, state):
        if state.get('protocol', 0) < 15:
            return {'action': 'STOP', 'reason': 'cursor_feedback_missing'}
        if state['dead'] or state['combat']:
            return {'action': 'STOP', 'reason': 'unsafe_player'}
        if state['sequence'] == self.last_sequence:
            return {'action': 'WAIT', 'reason': 'same_frame'}
        self.last_sequence = state['sequence']
        x, y = state['ui_cursor_x'], state['ui_cursor_y']
        dx, dy = self.target[0] - x, self.target[1] - y
        if abs(dx) <= self.tolerance and abs(dy) <= self.tolerance:
            if state['mouse_focus_hash'] == self.focus_hash:
                return {'action': 'READY'}
            return {'action': 'STOP', 'reason': 'hover_identity_mismatch'}
        if self.steps >= self.max_steps:
            return {'action': 'STOP', 'reason': 'step_budget'}
        self.steps += 1
        # Small bounded impulses; never extrapolate a large unverified gain.
        def impulse(error):
            if abs(error) <= self.tolerance:
                return 0
            return int(math.copysign(1 if abs(error) < 200 else 3, error))
        return {'action': 'MOVE', 'dx': impulse(dx), 'dy': -impulse(dy)}
