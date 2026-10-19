"""Static guard for the WotLK baseline probe (WowProbeWotLK).

Same forbidden-action list as the Forever probe. Fails if the Lua source
contains control/action APIs the probe is not allowed to call.
Does not load the addon or talk to a WoW client.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBE = ROOT / "probes" / "WowProbeWotLK" / "WowProbeWotLK.lua"

FORBIDDEN = [
    r"\bTargetNearestEnemy\b",
    r"\bTargetNearest\b",
    r"\bTargetUnit\b",
    r"\bAttackTarget\b",
    r"\bAssistUnit\b",
    r"\bFocusUnit\b",
    r"\bCastSpellByName\b",
    r"\bCastSpellByID\b",
    r"\bCastSpell\b",
    r"\bUseAction\b",
    r"\bMoveForwardStart\b",
    r"\bJumpOrAscendStart\b",
    r"\bStrafeLeftStart\b",
    r"\bTurnOrActionStart\b",
    r"\bInteractUnit\b",
    r"\bConfirmationInteraction\b",
    r"\bSendChatMessage\b",
    r"\bSendAddonMessage\b",
    r"\bSetTracking\b",
    r"\bUseContainerItem\b",
    r"\bRunMacroText\b",
    r"\bRunMacro\b",
    r"\bCameraOrSelectOrMoveStart\b",
    r"\bSpellStopCasting\b",
]

REQUIRED = [
    "GetBuildInfo",
    "InCombatLockdown",
    "GetPlayerMapPosition",
    "UnitExists",
    "C_AssistedCombat",
    "absent_on_335",
    "WowProbeWotLK_Report",
    "PLAYER_TARGET_CHANGED",
]


def main() -> int:
    text = PROBE.read_text(encoding="utf-8")
    hits = [pat for pat in FORBIDDEN if re.search(pat, text)]
    missing = [name for name in REQUIRED if name not in text]
    print(f"probe: {PROBE}")
    print(f"forbidden_hits: {len(hits)}")
    for h in hits:
        print(f"  FORBIDDEN {h}")
    print(f"missing_required: {len(missing)}")
    for m in missing:
        print(f"  MISSING {m}")
    if hits or missing:
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
