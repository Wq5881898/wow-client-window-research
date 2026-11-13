"""Decide what to do when a cast does not work.

The client tells the driver why a cast failed.  The codes come from the
error text of the client, the probe turns them into numbers:

    1  the target is out of range
    2  not enough mana
    3  the spell is not ready
    4  no target, invalid target or a dead target
    5  the target needs to be in front of the character
    6  no line of sight

These codes are the only signal about the target that the client gives,
so the fight uses them instead of guessing.

A "needs to be in front" error means the target is close enough and only
the direction is wrong.  The answer is a quarter turn and another cast;
three quarter turns cover most of the circle and cost about two seconds
each.  When they are not enough the turn becomes finer, because a target
can also hide just behind the shoulder of the character.

An "out of range" error means the direction is not the problem, so the
driver must close the distance.  The client does not tell where the target
is, so the driver can only search for it.
"""
REASON_RANGE = 1
REASON_MANA = 2
REASON_NOT_READY = 3
REASON_NO_TARGET = 4
REASON_FACING = 5
REASON_LINE_OF_SIGHT = 6

# A quarter turn with the measured turn rate of about 2.9 rad/s.
QUARTER_TURN_SECONDS = 0.55
# A finer step of about 40 degrees, used after the quarter turns.
FINE_TURN_SECONDS = 0.25

QUARTER_TURNS = 3
FINE_TURNS = 8

# The character leaves the fight below this health unless the target is
# nearly dead.
LOW_HEALTH = 110
LOW_HEALTH_EXEMPT_TARGET = 47
MIN_POWER = 18


def decide(state, *, quarter_turns=0, fine_turns=0):
    """The action for one observation of a fight.

    The state needs the fields the probe reports: last_error_reason,
    health, max_health, power, target_health, spell_range, target_exists,
    target_dead and dead.
    """
    if state.get('dead') or state.get('health', 0) <= 0:
        return {'action': 'retreat', 'reason': 'dead'}
    if not state.get('target_exists') or state.get('target_dead') \
            or state.get('target_health', 0) <= 0:
        return {'action': 'verify', 'reason': 'target_gone'}
    if state.get('health', 0) < LOW_HEALTH \
            and state.get('target_health', 0) > LOW_HEALTH_EXEMPT_TARGET:
        return {'action': 'retreat', 'reason': 'health_recovery_threshold'}
    if state.get('power', 0) < MIN_POWER:
        return {'action': 'rest', 'reason': 'mana_recovery_threshold'}
    if state.get('spell_range') == 0:
        return {'action': 'approach', 'reason': 'out_of_range'}
    reason = state.get('last_error_reason') or 0
    if reason == REASON_FACING:
        if quarter_turns < QUARTER_TURNS:
            return {'action': 'turn', 'seconds': QUARTER_TURN_SECONDS,
                    'reason': 'facing_quarter_turn',
                    'count': 'quarter'}
        if fine_turns < FINE_TURNS:
            return {'action': 'turn', 'seconds': FINE_TURN_SECONDS,
                    'reason': 'facing_fine_turn', 'count': 'fine'}
        return {'action': 'retreat', 'reason': 'facing_not_found'}
    if reason == REASON_RANGE:
        return {'action': 'approach', 'reason': 'out_of_range'}
    if reason == REASON_LINE_OF_SIGHT:
        return {'action': 'turn', 'seconds': QUARTER_TURN_SECONDS,
                'reason': 'no_line_of_sight', 'count': 'fine'}
    if reason == REASON_MANA:
        return {'action': 'rest', 'reason': 'mana_recovery_threshold'}
    if reason == REASON_NOT_READY:
        return {'action': 'wait', 'reason': 'spell_not_ready'}
    if reason == REASON_NO_TARGET:
        return {'action': 'verify', 'reason': 'no_target'}
    return {'action': 'cast', 'reason': 'ready'}
