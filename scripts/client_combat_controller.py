"""Combat-period control state machine.

Pure decision layer: it never sends input. It decides what the driver is
allowed to attempt next, and when the run must fall back to recovery.

Every branch is tied to evidence that the protocol actually carries, so a
missing signal becomes an explicit "not ready" instead of a silent guess.
"""
from client_live_state import Freshness

# Health fraction at which the run leaves the fight. Design value, not
# measured: it has never been validated against a real incoming hit rate.
LOW_HEALTH_RATIO = 0.70

# Reason codes emitted by the probe for a failed cast.
REASON_RANGE = 1
REASON_MANA = 2
REASON_COOLDOWN = 3
REASON_INVALID_TARGET = 4
REASON_FACING = 5
REASON_LINE_OF_SIGHT = 6

# Reasons a cast may be retried rather than treated as a hard failure.
RETRYABLE_REASONS = (REASON_RANGE, REASON_FACING, REASON_LINE_OF_SIGHT)


class CombatController:
    def __init__(self, target_guid, spell_id, timeout=1.0,
                 low_health=LOW_HEALTH_RATIO, max_attempts=4):
        self.target_guid = target_guid
        self.spell_id = spell_id
        self.freshness = Freshness(timeout)
        self.low_health = low_health
        self.max_attempts = max_attempts
        self.attempts = 0
        self.last_event_serial = None
        self.finished = False
        self.recovery = None

    def _recover(self, reason):
        self.recovery = {'decision': 'RECOVER', 'reason': reason}
        return self.recovery

    def bind_target(self, state):
        """Confirm the target identity before any action is allowed."""
        if not state['target_exists']:
            return self._recover('no_target')
        if state['target_guid'] != self.target_guid:
            return self._recover('target_identity_mismatch')
        if not state['target_attackable']:
            return self._recover('target_not_attackable')
        if state['target_dead'] or state['target_health'] <= 0:
            return self._recover('target_already_dead')
        return {'decision': 'BOUND', 'reason': 'target_confirmed'}

    def observe(self, state, now, window_visible=True):
        """Advance the state machine by one observation."""
        if self.recovery:
            return self.recovery
        if self.finished:
            return {'decision': 'DONE', 'reason': 'run_finished'}
        if not window_visible:
            return self._recover('window_not_visible')
        try:
            fresh = self.freshness.observe(state, now)
        except ValueError as exc:
            return self._recover(str(exc))

        if state['dead']:
            return self._recover('player_dead')
        if state['max_health'] <= 0 or not 0 <= state['health'] <= state['max_health']:
            return self._recover('invalid_health')
        if state['health'] / state['max_health'] <= self.low_health:
            return self._recover('low_health')

        # The bound target must still be the same entity for the whole fight.
        if not state['target_exists']:
            return self._recover('target_lost')
        if state['target_guid'] != self.target_guid:
            return self._recover('target_identity_changed')

        if state['target_dead'] or state['target_health'] <= 0:
            # Death of the target does not end the run: the player must be
            # seen alive and out of combat for a sustained period.
            self.finished = True
            return {'decision': 'VERIFY_SURVIVAL',
                    'reason': 'target_dead' if state['combat'] else 'target_dead_out_of_combat'}

        if state['casting']:
            return {'decision': 'WAIT', 'reason': 'casting'}
        if not fresh:
            return {'decision': 'WAIT', 'reason': 'heartbeat_warmup'}

        if not state['spell_learned']:
            return self._recover('spell_not_learned')
        if state['spell_range'] == 0:
            return {'decision': 'CLOSE_DISTANCE', 'reason': 'out_of_range'}
        if state['spell_range'] != 1:
            return self._recover('spell_range_unknown')

        # A failed cast that the probe already reported must not be retried
        # blindly; the reason decides whether closing distance can help.
        failure = self._latest_failure(state)
        if failure is not None:
            reason = failure['reason']
            if reason in (REASON_MANA, REASON_COOLDOWN):
                return {'decision': 'WAIT', 'reason': 'spell_' + str(reason)}
            if reason == REASON_INVALID_TARGET:
                return self._recover('cast_invalid_target')
            if reason in RETRYABLE_REASONS:
                return {'decision': 'CLOSE_DISTANCE', 'reason': 'cast_' + str(reason)}

        if self.attempts >= self.max_attempts:
            return self._recover('attempt_budget_exhausted')
        return {'decision': 'CAST_ALLOWED', 'reason': 'ready',
                'attempt': self.attempts + 1}

    def record_attempt(self):
        self.attempts += 1

    def _latest_failure(self, state):
        """Return the newest failed cast event for the bound spell, if any."""
        events = state.get('events') or []
        for event in reversed(events):
            if not event.get('serial'):
                continue
            if event.get('serial') == self.last_event_serial:
                continue
            if event.get('kind') in (3, 4) and event.get('spell') == self.spell_id:
                self.last_event_serial = event['serial']
                return event
        return None
