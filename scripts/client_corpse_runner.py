"""State machine that walks a dead character to its corpse and revives it.

The task has four phases:

1. ``SEEK_CORPSE`` - the character is a ghost and has to walk to the spot
   where its corpse lies. The probe reports the heading of the character and
   the position of the corpse, so the direction is known.
2. ``AT_CORPSE`` - the character is close enough and the client offers the
   resurrect dialog.
3. ``ACCEPT`` - the dialog is confirmed with a click.
4. ``VERIFY`` - the character has to be alive, out of combat and still.

The conventions between the heading and the map were measured on the client
and not assumed:

* the map x grows to the east and the map y to the south;
* the heading grows counter clockwise from the north;
* walking at the heading h moves the position by (-sin h, -cos h);
* the left arrow key raises the heading and the right one lowers it.

The machine never sends input itself. It only decides what the driver
should do next, so every branch can be tested without a client.
"""
import math

# The client offers the resurrect dialog when the ghost stands on its corpse.
# The distance is measured in the normalised map coordinates, so it is not a
# distance in yards.
CORPSE_RANGE = 0.004

# A heading error that is worth correcting with a turn.
TURN_TOLERANCE = 0.10

# The longest time the whole task may take.
TIME_BUDGET = 180.0

# A step that is smaller than this does not count as movement.
MOVEMENT_EPSILON = 0.0004


def wrap(angle):
    """Bring an angle into the range of minus pi to plus pi."""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


def bearing_to(state):
    """The heading that points from the character to its corpse.

    Walking at the heading h moves the position by (-sin h, -cos h), so the
    heading towards a target is the one whose direction points at it.
    """
    return math.atan2(state['pos_x'] - state['corpse_x'],
                      state['pos_y'] - state['corpse_y'])


def corpse_distance(state):
    """The distance between the character and its corpse."""
    dx = state['corpse_x'] - state['pos_x']
    dy = state['corpse_y'] - state['pos_y']
    return math.hypot(dx, dy)


class CorpseRunner:
    """Decides what to do next while the character walks to its corpse.

    A graveyard is surrounded by a fence, so the direct line to the corpse
    can be blocked. When a walk does not bring the character closer, the
    machine leaves the direct line and tries a detour.
    """

    def __init__(self, accept_point=(960, 230), time_budget=TIME_BUDGET):
        self.accept_point = accept_point
        self.time_budget = time_budget
        self.started = None
        self.phase = 'IDLE'
        self.accept_attempts = 0
        self.history = []
        self.last_action = None
        self.last_distance = None
        self.stuck = 0
        self.avoid = 0.0
        self.avoid_side = 1

    def _elapsed(self, now):
        if self.started is None:
            self.started = now
        return now - self.started

    def _detour(self, distance):
        """Leave the direct line when the last walk did not help."""
        if self.last_action == 'WALK' and self.last_distance is not None:
            if distance >= self.last_distance - MOVEMENT_EPSILON:
                self.stuck += 1
                self.avoid_side = -self.avoid_side
                self.avoid = self.avoid_side * min(1.6, 0.45 + 0.3 * self.stuck)
            else:
                self.stuck = 0
                self.avoid = 0.0
        self.last_distance = distance

    def observe(self, state, now):
        """Return the next action of the run."""
        elapsed = self._elapsed(now)
        if elapsed > self.time_budget:
            self.phase = 'FAILED'
            return {'action': 'GIVE_UP', 'reason': 'time_budget',
                    'elapsed': elapsed}

        # Already alive: the task is done.
        if not state['dead']:
            self.phase = 'DONE'
            return {'action': 'DONE', 'reason': 'alive',
                    'health': state['health']}

        if not state.get('corpse_exists'):
            self.phase = 'FAILED'
            return {'action': 'GIVE_UP', 'reason': 'no_corpse',
                    'elapsed': elapsed}

        distance = corpse_distance(state)
        self._detour(distance)
        record = {'phase': self.phase, 'distance': distance,
                  'facing': state['facing'], 'elapsed': elapsed,
                  'avoid': self.avoid}
        self.history.append(record)

        # The dialog can only be accepted when the ghost stands on the corpse.
        if distance > CORPSE_RANGE:
            self.phase = 'SEEK_CORPSE'
            wanted = bearing_to(state) + self.avoid
            error = wrap(wanted - state['facing'])
            record['bearing_error'] = error
            if abs(error) > TURN_TOLERANCE:
                # The left arrow key raises the heading, the right one
                # lowers it.
                direction = 'left' if error > 0 else 'right'
                self.last_action = 'TURN'
                return {'action': 'TURN', 'direction': direction,
                        'error': error, 'distance': distance}
            self.last_action = 'WALK'
            return {'action': 'WALK', 'distance': distance}

        # The character is on the corpse: the client offers the dialog.
        self.phase = 'AT_CORPSE'
        self.accept_attempts += 1
        self.last_action = 'ACCEPT'
        if self.accept_attempts > 6:
            self.phase = 'FAILED'
            return {'action': 'GIVE_UP', 'reason': 'dialog_not_accepted',
                    'elapsed': elapsed}
        return {'action': 'ACCEPT', 'point': self.accept_point,
                'attempt': self.accept_attempts}
