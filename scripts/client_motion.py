"""The measured motion constants of the client.

The rate of the turn was measured on this client with the probe
``scripts/lab_client_turn_rate.py``: the heading changes by 2.66 radians
per second while the left key is held, and by the same amount in the
other direction while the right key is held. The value of pi that was
assumed before is about a fifth too large, so every turn with it passes
the wanted heading and the walk circles around the target.

The measurement of 2026-11-06: 2.702, 2.613, 2.660 and 2.791 radians per
second for four turns of half a second each.
"""

# Radians per second of the heading.
TURN_RATE = 2.66
