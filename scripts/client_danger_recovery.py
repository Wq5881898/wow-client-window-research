"""State machine for the recovery of a character that died in a danger zone.

The task has four parts:

1. ``GHOST`` - the character is a ghost and has to walk to its corpse. The
   probe reports the heading of the character and the position of the corpse,
   so the direction is known and the walk is not blind.
2. ``REVIVE`` - the ghost stands on the corpse and the client offers the
   resurrect dialog, which is confirmed.
3. ``ESCAPE`` - the character is alive again and has to leave the danger
   zone. It follows the path it walked as a ghost back to the graveyard, so
   the way back is one the server accepts and not a straight line.
4. ``SAFE`` - the character is at the graveyard, alive and out of combat.

If the character dies a second time, the new corpse is picked up and the
run starts again. The length of the walked path is the distance to the
graveyard that can be compared between the two corpses.

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

from client_path_memory import PathMemory

# The client offers the resurrect dialog when the ghost stands on its corpse.
# The distance is measured in the normalised map coordinates, so it is not a
# distance in yards.
CORPSE_RANGE = 0.004

# A heading error that is worth correcting with a turn.
TURN_TOLERANCE = 0.10

# The longest time the whole task may take. A walk across the valley takes
# a few minutes, so the budget has to be generous. A corpse that lies far
# from the graveyard makes the ghost walk around the rocks on the way, and
# that walk is slow.
TIME_BUDGET = 2400.0

# A walk step lasts longer when there is far to go: the reading of the
# telemetry costs about as much time as the walk itself.
WALK_MIN = 1.2
WALK_MAX = 2.0
WALK_PER_UNIT = 10.0

# A step that is smaller than this does not count as movement.
MOVEMENT_EPSILON = 0.0004

# The distance to the graveyard at which the character is considered safe.
SAFE_RANGE = 0.010


def wrap(angle):
    """Bring an angle into the range of minus pi to plus pi."""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


def bearing_to(state, target):
    """The heading that points from the character to a target.

    Walking at the heading h moves the position by (-sin h, -cos h), so the
    heading towards a target is the one whose direction points at it.
    """
    return math.atan2(state['pos_x'] - target[0],
                      state['pos_y'] - target[1])


def distance_to(state, target):
    """The distance between the character and a target."""
    return math.hypot(target[0] - state['pos_x'],
                      target[1] - state['pos_y'])


class DangerRecovery:
    """Decides what to do next while a dead character is recovered."""

    def __init__(self, accept_point=(960, 230), time_budget=TIME_BUDGET,
                 corpse_range=CORPSE_RANGE, safe_range=SAFE_RANGE):
        self.accept_point = accept_point
        self.time_budget = time_budget
        self.corpse_range = corpse_range
        self.safe_range = safe_range
        self.started = None
        self.phase = 'IDLE'
        self.memory = PathMemory()
        self.graveyard = None
        self.corpses = []
        self.route = []
        self.route_index = 0
        self.accept_attempts = 0
        self.release_attempts = 0
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
                self.avoid = self.avoid_side * min(0.9, 0.35 + 0.2 * self.stuck)
            else:
                self.stuck = 0
                self.avoid = 0.0
        self.last_distance = distance

    def _start_death(self, state):
        """A new death.

        The character lies on the ground where it fell, and that is not the
        graveyard: the spirit has to be released first. Only when the ghost
        appears does the client tell where the graveyard is, and that spot
        is the anchor of the route back.
        """
        self.phase = 'DEAD_BODY'
        self.memory = PathMemory()
        self.graveyard = None
        self.death_position = (state['pos_x'], state['pos_y'])
        self.route = []
        self.route_index = 0
        self.accept_attempts = 0
        self.release_attempts = 0
        self.stuck = 0
        self.avoid = 0.0
        self.last_action = None
        self.last_distance = None

    def _ghost_target(self, state):
        """The position of the corpse the ghost has to reach."""
        return (state['corpse_x'], state['corpse_y'])

    def observe(self, state, now):
        """Return the next action of the run."""
        elapsed = self._elapsed(now)
        if elapsed > self.time_budget:
            self.phase = 'FAILED'
            return {'action': 'GIVE_UP', 'reason': 'time_budget',
                    'elapsed': elapsed}

        if state['dead']:
            if self.phase not in ('DEAD_BODY', 'RELEASING', 'GHOST', 'REVIVE'):
                self._start_death(state)
            if not state.get('corpse_exists'):
                # The client shows the window of the death until the spirit
                # is released. The spot of the corpse is only known after
                # that, because the client does not keep it while the
                # character is still lying on the ground.
                self.phase = 'RELEASING'
                self.release_attempts += 1
                if self.release_attempts > 4:
                    self.phase = 'FAILED'
                    return {'action': 'GIVE_UP', 'reason': 'no_corpse',
                            'elapsed': elapsed}
                return {'action': 'RELEASE',
                        'attempt': self.release_attempts}
            if self.phase in ('DEAD_BODY', 'RELEASING'):
                # The spirit was released and the ghost appeared at the
                # graveyard. That spot is the anchor of the route back and
                # it is not the place where the character fell.
                self.phase = 'GHOST'
                self.graveyard = (state['pos_x'], state['pos_y'])
            # Every step of the ghost is a step the server accepts, so the
            # path of the ghost is the feasible path back to the graveyard.
            self.memory.record(state['pos_x'], state['pos_y'])
            target = self._ghost_target(state)
            distance = distance_to(state, target)
            self._detour(distance)
            record = {'phase': self.phase, 'distance': distance,
                      'facing': state['facing'], 'elapsed': elapsed,
                      'avoid': self.avoid}
            self.history.append(record)
            if distance > self.corpse_range:
                wanted = bearing_to(state, target) + self.avoid
                error = wrap(wanted - state['facing'])
                record['bearing_error'] = error
                if abs(error) > TURN_TOLERANCE:
                    # The left arrow key raises the heading of the client,
                    # the right one lowers it.
                    direction = 'left' if error > 0 else 'right'
                    self.last_action = 'TURN'
                    return {'action': 'TURN', 'direction': direction,
                            'error': error, 'distance': distance}
                self.last_action = 'WALK'
                return {'action': 'WALK', 'distance': distance,
                        'target': target,
                        'seconds': min(WALK_MAX,
                                       max(WALK_MIN,
                                           distance * WALK_PER_UNIT))}

            # The ghost stands on the corpse: the client offers the dialog.
            self.phase = 'REVIVE'
            self.accept_attempts += 1
            self.last_action = 'ACCEPT'
            self.corpses.append({'corpse': list(target),
                                 'path_length': self.memory.length()})
            if self.accept_attempts > 6:
                self.phase = 'FAILED'
                return {'action': 'GIVE_UP', 'reason': 'dialog_not_accepted',
                        'elapsed': elapsed}
            return {'action': 'ACCEPT', 'point': self.accept_point,
                    'attempt': self.accept_attempts}

        # The character is alive.
        if self.phase == 'GHOST' or self.phase == 'REVIVE':
            # The revival was confirmed. The way back to the graveyard is the
            # path that was walked here, in the other direction.
            self.phase = 'ESCAPE'
            self.route = self.memory.route_back(state['pos_x'], state['pos_y'])
            self.route_index = 0
            self.stuck = 0
            self.avoid = 0.0
            self.last_action = None
            self.last_distance = None

        if not self.route:
            self.phase = 'SAFE'
            return {'action': 'DONE', 'reason': 'alive',
                    'health': state['health']}

        # The waypoints that are already reached are skipped, so the run
        # cannot stand still on the waypoint it starts from.
        while (self.route_index < len(self.route) - 1
               and distance_to(state, self.route[self.route_index])
               <= self.safe_range):
            self.route_index += 1
        target = self.route[self.route_index]
        distance = distance_to(state, target)
        self._detour(distance)
        if self.stuck >= 3 and self.graveyard:
            # The path of the ghost is not always walkable for the living
            # character: the ghost flies over the rocks, the character does
            # not. When the way is blocked, the straight line to the
            # graveyard is the next try.
            self.route = [self.graveyard]
            self.route_index = 0
            self.stuck = 0
            self.avoid = 0.0
            self.last_action = None
            self.last_distance = None
            return {'action': 'WALK', 'distance': distance,
                    'target': self.graveyard,
                    'seconds': min(WALK_MAX,
                                   max(WALK_MIN, distance * WALK_PER_UNIT))}
        if (self.route_index == len(self.route) - 1
                and distance <= self.safe_range):
            self.phase = 'SAFE'
            return {'action': 'DONE', 'reason': 'safe',
                    'health': state['health'],
                    'graveyard_distance': distance}

        wanted = bearing_to(state, target) + self.avoid
        error = wrap(wanted - state['facing'])
        if abs(error) > TURN_TOLERANCE:
            direction = 'left' if error > 0 else 'right'
            self.last_action = 'TURN'
            return {'action': 'TURN', 'direction': direction,
                    'error': error, 'distance': distance}
        self.last_action = 'WALK'
        return {'action': 'WALK', 'distance': distance, 'target': target,
                'seconds': min(WALK_MAX,
                               max(WALK_MIN, distance * WALK_PER_UNIT))}
