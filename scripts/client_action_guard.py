"""Stopping an action that is in flight.

A cast of this client needs about a second, and the character can be
dying while the spell is still in the air. A check that reports "stop" is
of no use while the executor keeps on typing the command, so the executor
asks the guard before every step, and the guard is what the thread that
types asks.

The reason is latched: once an action was cancelled, a later check cannot
quietly continue the fight. Only the run itself may clear the guard, and
only when it has decided that the character is safe again.

The guard holds no client state, so every branch can be tested without a
client.
"""

# The reasons an action may be stopped.
STOP_LOW_HEALTH = 'low_health'
STOP_DEAD = 'player_dead'
STOP_IDENTITY = 'target_identity_changed'
STOP_STALE = 'observation_stale'
STOP_READING = 'reading_failed'
STOP_LOST = 'lost_observation'


class ActionCancelled(Exception):
    """The action was stopped before it had finished.

    The reason says which condition stopped it, so the run can put the
    character into the matching branch of the recovery.
    """

    def __init__(self, reason):
        Exception.__init__(self, reason)
        self.reason = reason


class ActionGuard:
    """The reason an action has to stop."""

    def __init__(self):
        self.reason = None

    @property
    def cancelled(self):
        """True while an action has to stay stopped."""
        return self.reason is not None

    def cancel(self, reason):
        """Latch a reason. The first reason is the one that is kept."""
        if self.reason is None and reason:
            self.reason = reason
        return self.reason

    def clear(self):
        """Allow actions again. Only the run itself calls this."""
        self.reason = None

    def check_state(self, state, low_health_ratio, target_guid=None):
        """The reason the action has to stop, or None when it may go on.

        The order matters: a dead character is reported before a low
        health, because the death is the stronger fact and the run has to
        end at once.
        """
        if self.reason is not None:
            return self.reason
        if state.get('dead'):
            return self.cancel(STOP_DEAD)
        maximum = state.get('max_health') or 0
        if maximum and state.get('health', 0) / maximum <= low_health_ratio:
            return self.cancel(STOP_LOW_HEALTH)
        if target_guid is not None and state.get('target_exists'):
            if state.get('target_guid') != target_guid:
                return self.cancel(STOP_IDENTITY)
        return None
