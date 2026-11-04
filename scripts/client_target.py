"""Select a hostile creature of the client.

The tab key selects the next hostile in sight. The chat is not used for it:
the chat input takes the focus away from the game and the panel of the
probe stops being updated while it is open.
"""
import time

import win32con

import lab_driver5 as d


def select_hostile(hwnd, reader, steps=12, ordinary=True, prefer_hash=None):
    """Return the state of a hostile, or None when there is none in reach.

    The weakest ordinary creature in reach is used, so a drill against it
    ends quickly. When a name hash is given, the creature with that name is
    used instead, so a drill can be made against a fixed creature.
    """
    seen = []
    found = []
    named = []
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
        if prefer_hash is not None and state.get('target_name_hash') == prefer_hash:
            named.append(state)
        found.append(state)
    if named:
        return named[0]
    if not found:
        return None
    return min(found, key=lambda s: s['target_health'])


def sweep_for_hostile(hwnd, reader, spots, steps=8, timeout=45.0):
    """Walk over a few places and look for a hostile at each of them.

    The creatures roam, so the place where they were seen before is often
    empty. Walking over a few places around it and looking again is more
    reliable than standing at one point.
    """
    from client_walk import walk_to
    for spot in spots:
        walk_to(hwnd, reader, spot, timeout=timeout)
        state = select_hostile(hwnd, reader, steps=steps)
        if state is not None:
            return state
    return None
