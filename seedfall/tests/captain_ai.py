"""A captain good enough to test combat with.

Driving a fight by repeating one order measures almost nothing: combat is
positional, so a ship whose mounts are all on the beam will never fire a shot
while it steers straight at the enemy. This picks the helm order that suits the
arcs the ship actually carries, and shoots when something bears — which is what
a person does, and the baseline any change to combat should be judged against.
"""

from __future__ import annotations

from collections import Counter

from ..sim import stations as st_mod
from ..sim import tactical as tac


def helm_order_for(side, other) -> str:
    """Turn so that the mounts this hull carries can actually see the target."""
    arcs = Counter(tac.arc_of(w) for w in side.st.weapons)
    if not arcs:
        return "hold"
    want = arcs.most_common(1)[0][0]
    rel = tac.relative_bearing(side.body, other.body)
    if want == "broad":
        return "hold" if 60 <= rel <= 120 else "broadside"
    if want in ("fore", "turret"):
        return "comeabout" if rel > 55 else "close"
    return "close"


def orders(battle) -> dict:
    """One turn's action: shoot if anything bears, otherwise manoeuvre."""
    in_band = [w for w in battle.player.st.weapons
               if w.wpn.bears_at(battle.band) <= 0.5]
    bearing = [w for w in in_band
               if st_mod.bears_on(battle.player, battle.enemy, w)[0]]
    if bearing:
        return {"type": "station", "order": "salvo"}
    if not in_band and battle.band > 2:
        return {"type": "station", "order": "close"}
    return {"type": "station",
            "order": helm_order_for(battle.player, battle.enemy)}
