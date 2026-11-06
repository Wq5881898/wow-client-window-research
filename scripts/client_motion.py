"""The measured motion constants of the client.

The current experimental estimate is 2.66 radians per second. The raw
four 0.6-second samples were 2.702, 2.613, 2.618 and 2.791. Readout delay
and input overhead have not been isolated, so these samples do not prove
the older pi-radians/second calibration wrong.
"""

# Experimental estimate, not a universal calibration. Sampling latency and
# key overhead have not been isolated. A larger divisor shortens the turn
# and tends to under-turn; the historical overshoot explanation is withdrawn.
TURN_RATE = 2.66
