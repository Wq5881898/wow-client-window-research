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

# Target health at or below which a vanishing target counts as a kill.
KILL_HEALTH_THRESHOLD = 5

# The smallest drop of the target health that counts as progress. A creature
# with a high resistance takes less than that, so the fight can never end.
MIN_TARGET_PROGRESS = 5

# Reasons a vanishing target can still be treated as a kill.
KILL_REASONS = ('target_gone_after_hit', 'target_dead', 'target_dead_out_of_combat')


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
        self.last_target_health = None
        self.successful_casts = 0
        self.target_recovered = False
        self.recoveries = 0
        # The health of the target before the last cast, so the drop that the
        # cast caused can be judged.
        self.cast_health_before = None

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
        # The baseline of the health is taken at the binding, so the first
        # observation is not mistaken for a recovery.
        self.last_target_health = state['target_health']
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

        # Count confirmed hits first: the kill check below needs this evidence.
        self._count_successful_casts(state)

        # The bound target must still be the same entity for the whole fight.
        if not state['target_exists']:
            # A target that vanishes right after our hits is a kill, not a loss.
            if self.successful_casts > 0 and self.last_target_health is not None:
                self.finished = True
                return {'decision': 'VERIFY_SURVIVAL',
                        'reason': 'target_gone_after_hit',
                        'last_target_health': self.last_target_health,
                        'successful_casts': self.successful_casts}
            return self._recover('target_lost')
        if state['target_guid'] != self.target_guid:
            return self._recover('target_identity_changed')
        # A creature that leaves combat regenerates. When the health of the
        # bound target rises, the fight was lost and has to start over
        # instead of waiting for spells that can never outpace the recovery.
        if (self.last_target_health is not None
                and state['target_health'] > self.last_target_health):
            # The target recovered its health, so the fight starts over
            # instead of running out of attempts.
            self.target_recovered = True
            self.recoveries += 1
            self.last_target_health = state['target_health']
            self.attempts = 0
            return {'decision': 'CAST_ALLOWED', 'reason': 'target_recovered',
                    'attempt': 1}
        self.last_target_health = state['target_health']

        if state['target_dead'] or state['target_health'] <= 0:
            # Death of the target does not end the run: the player must be
            # seen alive and out of combat for a sustained period.
            self.finished = True
            return {'decision': 'VERIFY_SURVIVAL',
                    'reason': 'target_dead' if state['combat'] else 'target_dead_out_of_combat'}
        # A creature with a high resistance takes almost no damage, so the
        # fight would never end. The check runs on the drop that was
        # actually observed after a cast, never between two quiet frames.
        if self.cast_health_before is not None:
            drop = self.cast_health_before - state['target_health']
            self.cast_health_before = None
            if 0 < drop < MIN_TARGET_PROGRESS:
                return self._recover('target_resists')
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
            if reason == REASON_FACING:
                # The target is not in front. The client has no facing
                # readout, so the driver turns blindly and lets the error
                # code decide when the target came into view.
                return {'decision': 'TURN', 'reason': 'cast_' + str(reason)}
            if reason in RETRYABLE_REASONS:
                return {'decision': 'CLOSE_DISTANCE', 'reason': 'cast_' + str(reason)}
        if state.get('last_error_reason') == REASON_FACING:
            return {'decision': 'TURN', 'reason': 'cast_' + str(REASON_FACING)}

        if self.attempts >= self.max_attempts:
            return self._recover('attempt_budget_exhausted')
        return {'decision': 'CAST_ALLOWED', 'reason': 'ready',
                'attempt': self.attempts + 1}

    def record_attempt(self, target_health=None):
        self.attempts += 1
        if target_health is not None:
            self.cast_health_before = target_health

    def heartbeat(self, state, now):
        """Keep the freshness tracker alive without making a decision.

        Used while a cast is in flight: the observation stream must continue
        or a long cast looks like a dead link.
        """
        try:
            self.freshness.observe(state, now)
        except ValueError:
            return False
        return True

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

    def _count_successful_casts(self, state):
        """Track confirmed successful casts on the bound spell."""
        for event in state.get('events') or []:
            if event.get('kind') == 2 and event.get('spell') == self.spell_id:
                self.successful_casts = max(self.successful_casts, event.get('serial', 0))
        return self.successful_casts
