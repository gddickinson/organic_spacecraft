"""How the other side fights.

The enemy runs the same stations you do: it steers for the range its mounts want,
turns to bring fixed arcs onto you, and shoots when something bears. It does not
cheat the geometry — if its lance is pointing the wrong way it has to come about
like anybody else.
"""

from __future__ import annotations

from . import stations as st_mod
from . import tactical as tac
from .ship import hull_pct, is_destroyed

STYLES = {
    "aggressive": (0.55, 0.90, 0.05),
    "balanced": (0.35, 0.80, 0.18),
    "cautious": (0.15, 0.65, 0.40),
    "feral": (0.80, 0.95, 0.00),
}


def enemy_turn(b, rng, _say, _fire, _salvo, use_ability) -> str | None:
    """Run the enemy's turn. Returns an outcome id if it breaks off."""
    e = b.enemy
    close, fire_p, flee_p = STYLES.get(e.personality, STYLES["balanced"])

    if e.resolve <= 0 or (hull_pct(e.ship) < 0.25 and rng.chance(flee_p)):
        if not e.grappled:
            return "driven-off"
        _say(b, f"{b.enemy_name} tries to break away and cannot — the grapple holds.",
             "good")

    if e.ship.heat > e.st.heat_cap and any(p.ability.id == "vent" for p in e.st.abilities):
        if use_ability(b, e, "vent", rng):
            return
    if hull_pct(e.ship) < 0.5 and rng.chance(0.55):
        for aid in ("regrow", "interpose", "seal"):
            if any(p.ability.id == aid for p in e.st.abilities) and not e.cd.get(aid):
                if use_ability(b, e, aid, rng):
                    return

    usable = [w for w in e.st.weapons if w.wpn.bears_at(b.band) <= 0.25]
    if usable and rng.chance(fire_p):
        # Hot or badly hurt, they pick one shot; otherwise they empty the broadside.
        restrained = e.ship.heat > e.st.heat_cap * 0.7 or rng.chance(0.25)
        if restrained or len(usable) == 1:
            _fire(b, e, b.player, rng.pick(usable).id, rng)
        else:
            _salvo(b, e, b.player, rng)
        return

    # Nothing bears: steer for the range its mounts want, and turn onto us if
    # its arcs are fixed forward.
    if e.st.weapons:
        want = round(sum((w.wpn.bands[0] + w.wpn.bands[1]) / 2
                         for w in e.st.weapons) / len(e.st.weapons))
        fixed = any(tac.arc_of(w) == "fore" for w in e.st.weapons)
    else:
        want, fixed = 4, False

    if want < b.band:
        order = "close"
    elif want > b.band:
        order = "open"
    else:
        order = "comeabout" if fixed else "hold"
    e.station = "helm"
    st_mod.run_helm(e, b.player, order, True, ())
    _say(b, f"{b.enemy_name} manoeuvres — {order.replace('comeabout', 'coming about')}.",
         "dim")
