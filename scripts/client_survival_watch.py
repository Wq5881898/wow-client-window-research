"""The quiet time of the character after a fight.

The run may only call itself a success when the character stayed alive, out
of combat, still and observed for a continuous time. A condition that is
broken resets the time, so a fight that ends in the last second of the
observation does not pass, and a picture that repeats itself does not
count as an observation.

The watcher holds no client state, so every branch can be tested without a
client.
"""

# The reasons the quiet time is broken.
BROKEN_DEAD = 'player_dead'
BROKEN_COMBAT = 'in_combat'
BROKEN_MOVING = 'moving'
BROKEN_IDENTITY = 'player_identity_changed'
BROKEN_STALE = 'observation_stale'


class SurvivalWatch:
    """The continuous quiet time of the character.

    The time is grown by the gap between two observations, so a watcher
    that is fed once a second and one that is fed once every tenth of a
    second measure the same thing. A broken condition sets the time back
    to zero, so only an unbroken stretch counts.
    """

    def __init__(self, required=30.0, player_guid=None):
        self.required = required
        self.player_guid = player_guid
        self.quiet = 0.0
        self.last = None
        self.last_sequence = None
        self.samples = 0
        self.resets = 0
        self.breaks = []

    def observe(self, state, now):
        """Feed one observation. Returns the reason the quiet time broke.

        None means the observation was quiet and the time grew.
        """
        self.samples += 1
        reason = self._check(state)
        if reason is not None:
            self.resets += 1
            self.breaks.append(reason)
            self.quiet = 0.0
        elif self.last is not None:
            self.quiet += max(0.0, now - self.last)
        self.last = now
        self.last_sequence = state.get('sequence')
        return reason

    def _check(self, state):
        """The reason this observation is not quiet, or None."""
        if state.get('dead'):
            return BROKEN_DEAD
        if state.get('combat'):
            return BROKEN_COMBAT
        if state.get('speed'):
            return BROKEN_MOVING
        if (self.player_guid is not None
                and state.get('player_guid') != self.player_guid):
            return BROKEN_IDENTITY
        sequence = state.get('sequence')
        if (self.last_sequence is not None
                and sequence == self.last_sequence):
            # The panel shows the same picture as the sample before, so the
            # client was not observed at all.
            return BROKEN_STALE
        return None

    @property
    def passed(self):
        """True when the character was quiet long enough."""
        return self.quiet >= self.required

    def summary(self):
        """The state of the watcher for the result of the run."""
        return {'quiet': round(self.quiet, 1), 'required': self.required,
                'samples': self.samples, 'resets': self.resets,
                'breaks': self.breaks}
