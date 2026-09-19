"""One shot and one salvo: what happens when a mount is fired.

Split out of `sim/combat.py` at 482 lines, which named the section
"shooting" already. `combat` runs the turn — who acts, in what order, when
it is over; this resolves a round from the mount to the layer it lands on:
whether it bears, whether the magazine is dry, point defence, the roll, what
a consort in the way wears, the armour floor, the Bloom's memory of the
weapon, and the log line that says which of those happened. Every caller
passes these in (`enemy_ai`, `consorts`, `parley.Ops`), and `combat`
re-exports them, so `combat._fire` is still the door the checks knock on.
"""

from __future__ import annotations

from ..core.util import clamp
from ..data.parts import part
from . import abilities
from . import consorts as consort_sim
from . import damage
from . import firing
from . import stations as st_mod
from . import tactical as tac
from . import turnplan
from .battle_state import Battle, Side
from .damage import _say, _who
from .ship import add_cargo, add_heat, is_destroyed

VARIANCE = (0.82, 1.18)

#: The most dazzle and jam together may take off accuracy. Unbounded, a
#: refreshed dazzle pinned any opponent at the 0.05 floor for a whole fight
#: — the cheapest organ in the game won 62% of engagements on its own.
DAZZLE_CAP = 0.35


def _fire(b: Battle, frm: Side, to: Side, weapon_id: str, rng,
          scale: float = 1.0) -> None:
    from . import gunfire
    w = part(weapon_id)
    if w is None or w.wpn is None:
        return
    # The band is between these two hulls. For the flag and its enemy that is
    # b.band; for a consort out on a flank it is emphatically not.
    band = tac.band_for(tac.separation(frm.body, to.body))
    pen = w.wpn.bears_at(band)
    if pen > firing.CAN_FIRE:
        _say(b, f"{_who(b, frm)} cannot bring the {w.name} to bear at this range.", "dim")
        gunfire.record(b, frm, to, w.name, w.wpn, gunfire.NO_BEAR)
        return
    in_arc, gap = st_mod.bears_on(frm, to, w)
    if not in_arc:
        _say(b, f"The {w.name} will not train that far — {round(gap)}° outside its "
                f"{tac.arc_name(tac.arc_of(w)).lower()} arc.", "dim")
        gunfire.record(b, frm, to, w.name, w.wpn, gunfire.NO_ARC)
        return

    if w.wpn.ammo:
        cid, per = w.wpn.ammo
        if frm.ship.cargo.get(cid, 0) < per:
            _say(b, f"{_who(b, frm)}: the {w.name} is dry — no {cid} in the hold.", "dim")
            gunfire.record(b, frm, to, w.name, w.wpn, gunfire.DRY)
            return
        add_cargo(frm.ship, cid, -per)

    add_heat(frm.ship, w.wpn.heat, frm.st.heat_cap)
    seeking = "seeking" in w.wpn.traits

    if seeking and to.st.flak > 0 and rng.chance(clamp(0.22 * to.st.flak, 0, 0.72)):
        _say(b, f"{_who(b, to)}'s point defence swats the {w.name} round out of the sky.",
             "dim")
        gunfire.record(b, frm, to, w.name, w.wpn, gunfire.SWATTED)
        return

    evade = 0.0 if seeking else to.st.evade + (0.08 if to.braced else 0)
    directed = frm.station == "gunnery"
    officers = b.officers if frm is b.player else ()
    # Sensory interference saturates (see DAZZLE_CAP): dazzled is a
    # handicap, not the fight's decision.
    dazzle = min(DAZZLE_CAP, (0.22 if frm.blind else 0.0)
                 + (0.25 if frm.jammed else 0.0))
    acc = (frm.st.accuracy + w.wpn.acc - pen - dazzle
           + (frm.ship.morale - 0.7) * 0.15
           + st_mod.accuracy_modifier(frm, directed, officers))
    if not rng.chance(clamp(acc - evade, 0.05, 0.95)):
        _say(b, f"{w.name} misses {_who(b, to)}.", "dim")
        gunfire.record(b, frm, to, w.name, w.wpn, gunfire.MISS)
        return

    dmg = w.wpn.dmg * rng.float(*VARIANCE) * scale
    if to.braced:
        dmg *= 0.72
    if to.interpose > 0:
        dmg *= 0.45
        to.interpose -= 1
        _say(b, f"{_who(b, to)} interposes its carapace.", "dim")
    # A hull interposed between you and the gun wears part of the blow. See
    # `consorts.interception`: the order's `shield` had never been read, so
    # "hold between the enemy and your flag" cost the escort and saved you
    # nothing. Taken before your own armour soaks, because the part the screen
    # wears never reaches your plating at all.
    arriving = 1.0
    if to is b.player and b.consorts:
        whole = dmg
        dmg, worn = consort_sim.interception(b, dmg)
        arriving = dmg / whole if whole > 0 else 1.0
        for screen, share in worn:
            took = damage._apply_to_layers(b, screen, share, w.wpn.traits, rng)
            screen.taken += took
            if took >= 1:
                _say(b, f"{screen.name} takes {round(took)} of it, holding "
                        f"station.", "warn")

    # Armour soaks, but never entirely: something always gets through, or two
    # well-armoured hulls would shoot at each other until the sun went out.
    #
    # The floor is scaled by how much of the blow actually arrived. Flat — a
    # share of the weapon's *nominal* output — it quietly erases interception
    # against an armoured hull, because the part a screen wore never reaches
    # the comparison. Measured over six identical shots at a flag with 34
    # armour: with the floor scaled, a screen cuts what the flag takes from
    # 26.5 to 15.1; with it flat, only to 21.6. A rule that stops armour
    # negating a weapon must not also negate the hull standing in front.
    dmg = max(w.wpn.dmg * 0.15 * arriving, dmg - abilities.armour_of(to))

    # Bloom tissue remembers what killed the last lineage. Keep using one kind
    # of weapon and it stops working; vary the loadout and the memory fades.
    if b.game is not None and b.enemy_faction == "bloom" and to is b.enemy:
        from . import bloom as bloom_sim
        resist = bloom_sim.resistance(b.game, w.family)
        if resist > 0:
            dmg *= 1 - resist
            if rng.chance(0.25):
                _say(b, f"The tissue shrugs off much of the {w.name} — it has "
                        f"seen this before.", "warn")

    dealt = damage._apply_to_layers(b, to, dmg, w.wpn.traits, rng)
    if b.game is not None and b.enemy_faction == "bloom" and to is b.enemy:
        from . import bloom as bloom_sim
        bloom_sim.record_damage(b.game, w.family, dealt)
    frm.dealt += dealt
    to.taken += dealt
    to.resolve -= dealt * 0.10
    frm.resolve += dealt * 0.03
    # "hits for 0" thirty turns running is what a swallowed floor looked like
    # from the bridge, and it reads identically to a weapon that is working.
    # Below a point, say what is actually happening instead of rounding it away.
    if dealt < 1:
        _say(b, f"{w.name} glances off {_who(b, to)} — their armour takes "
                f"almost all of it.", "dim")
    else:
        _say(b, f"{w.name} hits {_who(b, to)} for {round(dealt)}.",
             "good" if frm is b.player else "bad")
    gunfire.record(b, frm, to, w.name, w.wpn, gunfire.HIT, dealt)
    damage._apply_traits(b, frm, to, w, rng)


def _salvo(b: Battle, frm: Side, to: Side, rng) -> None:
    """Everything that can bear, fired together.

    This is what weapon mounts are for: a battleship's five hardpoints only
    matter if they all speak at once. The cost is heat and ammunition, which is
    why a single aimed shot stays a real option.
    """
    # `turnplan.bearing_set` is the one definition of what bears, so the count
    # in this log line, the count under the button and the heat in the hull are
    # the same count.
    bearing = turnplan.bearing_set(frm, to)
    if not bearing:
        _say(b, f"{_who(b, frm)} has nothing that will bear at this range.", "dim")
        return
    _say(b, f"{_who(b, frm)} fires everything that will bear — "
            f"{len(bearing)} mount(s).", "dim")
    for w in bearing:
        if is_destroyed(to.ship):
            break
        _fire(b, frm, to, w.id, rng)
