"""Select a hostile creature of the client.

The tab key selects the next hostile in sight. The chat is not used for it:
the chat input takes the focus away from the game and the panel of the
probe stops being updated while it is open.
"""
import time

import win32con

import lab_driver5 as d


def select_hostile(hwnd, reader, steps=12, ordinary=True):
    """Return the state of a hostile, or None when there is none in reach.

    The weakest ordinary creature in reach is used, so a drill against it
    ends quickly.
    """
    seen = []
    found = []
    for _ in range(steps):
        d.post_key(hwnd, win32con.VK_TAB)
        time.sleep(0.7)
        state = reader()
        if not state['target_exists']:
            continue
        guid = state['target_guid']
        if guid in seen:
            continue
        seen.append(guid)
        if not state['target_attackable']:
            continue
        if ordinary and state.get('target_class') != 1:
            continue
        found.append(state)
    if not found:
        return None
    return min(found, key=lambda s: s['target_health'])
