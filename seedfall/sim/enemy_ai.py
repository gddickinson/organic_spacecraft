"""How the other side fights.

The enemy runs the same stations you do: it steers for the range its mounts want,
turns to bring fixed arcs onto you, and shoots when something bears. It does not
cheat the geometry — if its lance is pointing the wrong way it has to come about
like anybody else.
"""

from __future__ import annotations

from . import consorts
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
    """Run the enemy's turn. Returns an outcome id if it breaks off.

    One seat a turn, chosen by need, and the guns work whichever it is —
    undirected unless the seat is gunnery, which is the price the player
    pays for the same choice. It used to return the moment it fired (so it
    never moved and shot in one turn), never ran its engineering section at
    all, gated its mounts on the band with no arc test, and left
    ``station = "helm"`` set for ever after its first manoeuvre — a
    permanent −0.22 to its own gunnery.
    """
    from . import turnplan
    e = b.enemy
    _close, fire_p, flee_p = STYLES.get(e.personality, STYLES["balanced"])

    if e.resolve <= 0 or (hull_pct(e.ship) < 0.25 and rng.chance(flee_p)):
        if not e.grappled:
            return "driven-off"
        _say(b, f"{b.enemy_name} tries to break away and cannot — the grapple holds.",
             "good")

    # Who they shoot at. A screening consort is trying to be the answer.
    mark = consorts.choose_target(b, rng)
    bearing = turnplan.bearing_set(e, mark)

    # The seat, by need: the section when the hull is cooking or open, the
    # helm when the geometry is wrong, the guns otherwise.
    if e.ship.heat > e.st.heat_cap:
        e.station = "engineering"
        vented = (any(p.ability.id == "vent" for p in e.st.abilities)
                  and use_ability(b, e, "vent", rng))
        if not vented:
            said = st_mod.run_engineering(e, "vent", True, ())
            if said:
                _say(b, f"{b.enemy_name}: {said}.", "dim")
    elif hull_pct(e.ship) < 0.5 and rng.chance(0.55) and _mend(b, e, rng, use_ability):
        e.station = "engineering"
    elif any(layer.hp <= 0 for layer in e.ship.layers):
        e.station = "engineering"
        said = st_mod.run_engineering(e, "damage_control", True, ())
        if said:
            _say(b, f"{b.enemy_name}: {said}.", "dim")
    else:
        if e.st.weapons:
            want = round(sum((w.wpn.bands[0] + w.wpn.bands[1]) / 2
                             for w in e.st.weapons) / len(e.st.weapons))
            fixed = any(tac.arc_of(w) == "fore" for w in e.st.weapons)
        else:
            want, fixed = 4, False
        band = tac.band_for(tac.separation(e.body, mark.body))
        if want < band:
            order = "close"
        elif want > band:
            order = "open"
        elif not bearing:
            order = "comeabout" if fixed else "close"
        else:
            order = None
        if order:
            e.station = "helm"
            st_mod.run_helm(e, mark, order, True, ())
            _say(b, f"{b.enemy_name} manoeuvres — "
                    f"{order.replace('comeabout', 'coming about')}.", "dim")
        else:
            e.station = "gunnery"

    # The guns, with whatever bears after the turn — through the same arc
    # test as every player-side selector (`turnplan.bearing_set`), which is
    # the rule `sim/firing.py` documents and the old band-only gate broke.
    bearing = turnplan.bearing_set(e, mark)
    if bearing and rng.chance(fire_p):
        if mark is not b.player:
            _say(b, f"{b.enemy_name} shifts its guns onto {mark.name}.", "dim")
        # Hot or badly hurt, they pick one shot; otherwise they empty the broadside.
        restrained = e.ship.heat > e.st.heat_cap * 0.7 or rng.chance(0.25)
        if restrained or len(bearing) == 1:
            _fire(b, e, mark, rng.pick(bearing).id, rng)
        else:
            _salvo(b, e, mark, rng)


def _mend(b, e, rng, use_ability) -> bool:
    """Spend the seat on whichever mending ability is up, if one is."""
    for aid in ("regrow", "interpose", "seal"):
        if (any(p.ability.id == aid for p in e.st.abilities)
                and not e.cd.get(aid) and use_ability(b, e, aid, rng)):
            return True
    return False
