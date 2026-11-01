"""Pure decision layer. Never sends input; recovery decisions require a driver."""
from client_live_state import Freshness


class ControlGuard:
    def __init__(self, target_guid=None, timeout=1.0, low_health=0.70):
        self.freshness = Freshness(timeout)
        self.target_guid = target_guid
        self.low_health = low_health
        self.latched = None

    def reject(self, reason):
        self.latched = {'decision': 'RECOVERY_REQUIRED', 'reason': reason}
        return self.latched

    def observe(self, state, now, window_visible=True):
        if self.latched:
            return self.latched
        if not window_visible:
            # A hidden or minimised window cannot be observed; the screen may
            # show another surface even though the client still runs.
            return self.reject('window_not_visible')
        try:
            fresh = self.freshness.observe(state, now)
        except ValueError as exc:
            return self.reject(str(exc))
        if state['dead']:
            return self.reject('player_dead')
        if state['max_health'] <= 0 or not 0 <= state['health'] <= state['max_health']:
            return self.reject('invalid_health')
        if state['health'] / state['max_health'] <= self.low_health:
            return self.reject('low_health')
        if self.target_guid is not None:
            if not state['target_exists'] or state['target_guid'] != self.target_guid:
                return self.reject('target_identity_changed')
        if self.target_guid is None:
            # Combat without a bound target is unsafe regardless of heartbeat warmup.
            if state['combat']:
                return self.reject('unexpected_combat')
            if not fresh:
                return {'decision': 'WAIT', 'reason': 'heartbeat_warmup'}
            return {'decision': 'OBSERVE_ONLY', 'reason': 'noncombat_live'}
        if state['target_dead']:
            return {'decision': 'WAIT' if state['combat'] else 'VERIFY_SURVIVAL',
                    'reason': 'target_dead_combat_pending' if state['combat'] else 'target_dead'}
        if state['target_health'] <= 0 or not state['target_attackable']:
            return self.reject('invalid_live_target')
        if state['casting']:
            return {'decision': 'WAIT', 'reason': 'casting'}
        if not state['spell_learned'] or state['spell_range'] != 1:
            return self.reject('spell_unavailable_or_range_unknown')
        # Range/learned alone do not prove facing, mana cost, cooldown or a recovery route.
        return {'decision': 'ACTION_GATE_PENDING', 'reason': 'spell_feedback_and_recovery_not_verified'}

    def unavailable(self, reason='capture_or_decode_failed'):
        return self.reject(reason)
