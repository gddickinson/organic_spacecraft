"""Tactical combat on a five-band range track.

Two things make this different from the usual exchange of fire. First, damage
lands on a stack of named layers — a grown hull sheds its epidermis, gives up its
rind, and only really cares once the pneumostat opens. Second, killing the other
ship is not the only way to win: every combatant has a resolve, and a hull that
simply refuses to die will break the other side's will to keep paying for the
ammunition. TESTUDO doctrine, fitted as a mechanic.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.util import clamp
from .battle_state import Battle, Side
from . import doctrine
from . import stations as st_mod
from . import tactical as tac
from .abilities import use_ability as _fire_ability
from .enemy_ai import enemy_turn as _enemy_turn
from . import consorts as consort_sim
from . import parley
from ..data.part_types import BANDS
from ..data.parts import part
from .ship import (Ship, Stats, add_cargo, hull_pct, is_breached, is_destroyed,
                   stats)

VARIANCE = (0.82, 1.18)
MAX_TURNS = 40

GRIND_TURN = 9      # turns of clean fighting before either side starts wanting out

#: personality -> (close preference, fire chance, flee chance)
def start(player_ship, player_stats, enemy, *, bonuses=None, officers=(),
          rep=0.0, no_parley=False, band=3, game=None, rng=None,
          fleet=()) -> Battle:
    b = Battle(
        player=Side(player_ship, player_stats, "player"),
        enemy=Side(enemy["ship"], enemy["stats"], enemy.get("personality", "balanced")),
        enemy_name=enemy.get("name", "Unknown contact"),
        enemy_faction=enemy.get("faction"),
        no_parley=no_parley, rep=rep,
        bonuses=dict(bonuses or {}), officers=list(officers), game=game,
        loot=dict(enemy.get("loot", {})),
    )
    b.enemy.resolve = enemy.get("resolve", 100)
    if rng is not None:
        b.player.body, b.enemy.body = tac.initial_layout(rng, band)
    else:
        b.player.body = tac.Body2D(0, 0, 0, 0)
        b.enemy.body = tac.Body2D(0, -(band + 0.5) * tac.BAND_UNITS, 180, 0)

    if fleet:
        consort_sim.deploy(b, list(fleet), rng, bonuses)
        names = ", ".join(c.name for c in b.consorts)
        _say(b, f"In company: {names}.", "good")
    _say(b, f"{b.enemy_name} at {BANDS[b.band].lower()} range, "
            f"{round(b.range_units)} units off.", "warn")
    return b


def _say(b: Battle, text: str, kind: str = "") -> None:
    b.log.append((b.turn, text, kind))
    if len(b.log) > 220:
        b.log.pop(0)


def _who(b: Battle, s: Side) -> str:
    if s is b.player:
        return b.player.ship.name
    if s is b.enemy:
        return b.enemy_name
    return getattr(s, "name", None) or s.ship.name


# ── shooting ───────────────────────────────────────────────────────────────

def _fire(b: Battle, frm: Side, to: Side, weapon_id: str, rng,
          scale: float = 1.0) -> None:
    w = part(weapon_id)
    if w is None or w.wpn is None:
        return
    # The band is between these two hulls. For the flag and its enemy that is
    # b.band; for a consort out on a flank it is emphatically not.
    band = tac.band_for(tac.separation(frm.body, to.body))
    pen = w.wpn.bears_at(band)
    if pen > 0.6:
        _say(b, f"{_who(b, frm)} cannot bring the {w.name} to bear at this range.", "dim")
        return
    in_arc, gap = st_mod.bears_on(frm, to, w)
    if not in_arc:
        _say(b, f"The {w.name} will not train that far — {round(gap)}° outside its "
                f"{tac.arc_name(tac.arc_of(w)).lower()} arc.", "dim")
        return

    if w.wpn.ammo:
        cid, per = w.wpn.ammo
        if frm.ship.cargo.get(cid, 0) < per:
            _say(b, f"{_who(b, frm)}: the {w.name} is dry — no {cid} in the hold.", "dim")
            return
        add_cargo(frm.ship, cid, -per)

    frm.ship.heat += w.wpn.heat
    seeking = "seeking" in w.wpn.traits

    if seeking and to.st.flak > 0 and rng.chance(clamp(0.22 * to.st.flak, 0, 0.72)):
        _say(b, f"{_who(b, to)}'s point defence swats the {w.name} round out of the sky.",
             "dim")
        return

    evade = 0.0 if seeking else to.st.evade + (0.08 if to.braced else 0)
    directed = frm.station == "gunnery"
    officers = b.officers if frm is b.player else ()
    acc = (frm.st.accuracy + w.wpn.acc - pen - frm.blind * 0.3 - frm.jammed * 0.25
           + (frm.ship.morale - 0.7) * 0.15
           + st_mod.accuracy_modifier(frm, directed, officers))
    if not rng.chance(clamp(acc - evade, 0.05, 0.95)):
        _say(b, f"{w.name} misses {_who(b, to)}.", "dim")
        return

    dmg = w.wpn.dmg * rng.float(*VARIANCE) * scale
    if to.braced:
        dmg *= 0.72
    if to.interpose > 0:
        dmg *= 0.45
        to.interpose -= 1
        _say(b, f"{_who(b, to)} interposes its carapace.", "dim")
    # Armour soaks, but never entirely: something always gets through, or two
    # well-armoured hulls would shoot at each other until the sun went out.
    dmg = max(w.wpn.dmg * 0.15, dmg - to.st.armour)

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

    dealt = _apply_to_layers(b, to, dmg, w.wpn.traits, rng)
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
    _apply_traits(b, frm, to, w, rng)


def _salvo(b: Battle, frm: Side, to: Side, rng) -> None:
    """Everything that can bear, fired together.

    This is what weapon mounts are for: a battleship's five hardpoints only
    matter if they all speak at once. The cost is heat and ammunition, which is
    why a single aimed shot stays a real option.
    """
    band = tac.band_for(tac.separation(frm.body, to.body))
    bearing = [w for w in frm.st.weapons
               if w.wpn.bears_at(band) <= 0.5 and st_mod.bears_on(frm, to, w)[0]]
    if not bearing:
        _say(b, f"{_who(b, frm)} has nothing that will bear at this range.", "dim")
        return
    _say(b, f"{_who(b, frm)} fires everything that will bear — "
            f"{len(bearing)} mount(s).", "dim")
    for w in bearing:
        if is_destroyed(to.ship):
            break
        _fire(b, frm, to, w.id, rng)


def _apply_to_layers(b: Battle, to: Side, dmg: float, traits, rng) -> float:
    layers = to.ship.layers
    idx = next((i for i, l in enumerate(layers) if l.hp > 0), -1)
    if idx < 0:
        return 0.0
    if "pierce" in traits:
        nxt = next((i for i, l in enumerate(layers) if i > idx and l.hp > 0), -1)
        if nxt > 0:
            idx = nxt

    # The guard is an epsilon, not half a point of damage. At 0.5 it silently
    # swallowed the armour floor above — `max(dmg * 0.15, dmg - armour)` is
    # 0.45 for a three-damage weapon — so the Photic Flash Organ, which is the
    # only armament a new captain starts with, dealt *exactly nothing* to any
    # armoured hull while the log said "hits for 0" every turn. Measured over
    # 360 engagements: every one ended on morale with both hulls at 100%.
    # The loop still terminates: each pass either empties a layer or exhausts
    # what is left.
    left, total, first = dmg, 0.0, True
    while left > 0.001 and idx < len(layers):
        L = layers[idx]
        if L.hp <= 0:
            idx += 1
            continue
        mult = 2 if (first and "ablate" in traits) else 1
        applied = min(L.hp, left * mult)
        L.hp -= applied
        total += applied / mult
        left -= applied / mult
        if L.hp <= 0:
            _say(b, f"— {L.name} of {_who(b, to)} is gone.", "warn")
            if L.critical:
                _breach(b, to, rng)
            if L.life:
                _say(b, f"— {_who(b, to)} is on bottled air.", "warn")
        first = False
        idx += 1
    return total


def _breach(b: Battle, to: Side, rng) -> None:
    lost = max(1, round(to.ship.crew * rng.float(0.04, 0.14) * (1 - to.st.crew_guard)))
    to.ship.crew = max(0, to.ship.crew - lost)
    to.resolve -= 18
    to.ship.morale = max(0.0, to.ship.morale - 0.12)
    _say(b, f"PRESSURE BREACH on {_who(b, to)} — {lost} lost to vacuum.", "bad")


def _apply_traits(b: Battle, frm: Side, to: Side, w, rng) -> None:
    t = w.wpn.traits
    if "blind" in t:
        to.blind = 2
        _say(b, f"{_who(b, to)} is dazzled.", "dim")
    if "grapple" in t:
        to.grappled = 2
        _say(b, f"Tendrils have hold of {_who(b, to)}.", "dim")
    if "emp" in t:
        to.ship.heat += 8
        if rng.chance(0.35):
            _disable(b, to, rng)
    if "board" in t and rng.chance(0.42):
        _disable(b, to, rng, "Spores have rooted in")
    if "plunder" in t:
        carried = [(cid, n) for cid, n in to.ship.cargo.items() if n > 0]
        if carried:
            cid, n = rng.pick(carried)
            take = min(n, max(1, round(n * 0.3)))
            add_cargo(to.ship, cid, -take)
            add_cargo(frm.ship, cid, take)
            _say(b, f"{round(take)} t of {cid} torn out of {_who(b, to)}'s hold.", "warn")


def _disable(b: Battle, to: Side, rng, verb: str = "A surge knocks out") -> None:
    live = [pid for pid in to.ship.fitted if pid not in to.ship.disabled and part(pid)]
    if not live:
        return
    victim = rng.pick(live)
    to.ship.disabled.append(victim)
    to.st = stats(to.ship, b.bonuses, b.officers if to is b.player else ())
    _say(b, f"{verb} {_who(b, to)}'s {part(victim).name}.", "warn")


# ── abilities ──────────────────────────────────────────────────────────────

# ── turn resolution ────────────────────────────────────────────────────────


def take_turn(b: Battle, action: dict, rng) -> Battle:
    """Run one full exchange. ``action`` is the player's choice."""
    if b.over:
        return b
    b.player.braced = False
    kind = action.get("type")

    # Legacy orders map onto the stations so older callers keep working.
    if kind == "move":
        b.player.station = "helm"
        b.player.helm_order = "close" if action.get("dir", 1) < 0 else "open"
        kind = "station"
    elif kind in ("fire", "salvo"):
        b.player.station = "gunnery"
    elif kind == "brace":
        b.player.station = "engineering"
    elif kind == "station":
        order = st_mod.ORDERS_BY_ID.get(action.get("order", ""))
        if order is None:
            return b
        b.player.station = order.station
        if order.station == "helm":
            b.player.helm_order = order.id
        b.pending_order = order.id

    if kind == "station":
        _run_stations(b, rng)
        _run_consorts(b, rng)
        if not b.over and isDestroyedSafe(b.enemy.ship):
            return _finish(b, "destroyed")
        if not b.over:
            broke = _enemy_turn(b, rng, _say, _fire, _salvo, use_ability)
        if broke:
            return _finish(b, broke)
        if not b.over and isDestroyedSafe(b.player.ship):
            return _finish(b, "lost")
        if not b.over:
            _end_of_turn(b, rng)
        return b

    if kind == "fire":
        _fire(b, b.player, b.enemy, action["weapon_id"], rng)
    elif kind == "salvo":
        _salvo(b, b.player, b.enemy, rng)
    elif kind == "ability":
        use_ability(b, b.player, action["id"], rng)
    elif kind == "move":
        if b.player.grappled:
            _say(b, "The grapple holds you at contact range.", "warn")
        else:
            b.band = int(clamp(b.band + action["dir"], 0, 4))
            _say(b, f"You manoeuvre to {BANDS[b.band].lower()} range.")
    elif kind == "brace":
        b.player.braced = True
        b.player.resolve += 6
        b.player.ship.heat = max(0.0, b.player.ship.heat - b.player.st.vent)
        _say(b, "You turn the thickest tissue into the fire and hold.", "good")
    elif kind == "hail":
        return parley.hail(b, rng, _ops())
    elif kind == "flee":
        return parley.flee(b, rng, _ops())

    _run_consorts(b, rng)
    if not b.over and is_destroyed(b.enemy.ship):
        return _finish(b, "destroyed")
    if not b.over:
        broke = _enemy_turn(b, rng, _say, _fire, _salvo, use_ability)
        if broke:
            return _finish(b, broke)
    if not b.over and is_destroyed(b.player.ship):
        return _finish(b, "lost")
    if not b.over:
        _end_of_turn(b, rng)
    return b


def _run_consorts(b: Battle, rng) -> None:
    """Your consorts manoeuvre to their standing orders and shoot."""
    if not b.consorts or b.over:
        return
    before = {c.uid for c in b.consorts if not c.out}
    consort_sim.run(b, rng, _say, _fire)
    for c in b.consorts:
        if c.uid in before and is_destroyed(c.ship):
            _say(b, f"{c.name} breaks apart.", "bad")
            b.player.resolve -= 12


def _ops() -> parley.Ops:
    return parley.Ops(say=_say, fire=_fire, salvo=_salvo,
                      use_ability=use_ability, enemy_turn=_enemy_turn,
                      finish=_finish, end_of_turn=_end_of_turn)


def isDestroyedSafe(ship) -> bool:      # noqa: N802 - thin alias for readability
    return is_destroyed(ship)


def use_ability(b: Battle, s: Side, ability_id: str, rng) -> bool:
    """Fire a defensive ability and log what it did."""
    fired, message, kind = _fire_ability(b, s, ability_id, rng)
    if fired and message:
        _say(b, f"{_who(b, s)} {message}", kind)
    return fired


def _run_stations(b: Battle, rng) -> None:
    """Resolve the player's chosen seat, then the two the officers hold."""
    order_id = getattr(b, "pending_order", None)
    order = st_mod.ORDERS_BY_ID.get(order_id or "")
    seat = b.player.station

    helm_text = st_mod.run_helm(b.player, b.enemy,
                                order.id if order and order.station == "helm" else None,
                                seat == "helm", b.officers)
    eng_text = st_mod.run_engineering(
        b.player, order.id if order and order.station == "engineering" else None,
        seat == "engineering", b.officers, b.enemy)

    if order and order.station == "gunnery":
        if order.id == "salvo":
            _salvo(b, b.player, b.enemy, rng)
        elif order.id == "aimed":
            usable = [w for w in b.player.st.weapons
                      if w.wpn.bears_at(b.band) <= 0.5
                      and st_mod.bears_on(b.player, b.enemy, w)[0]]
            if usable:
                best = max(usable, key=lambda w: w.wpn.dmg)
                _fire(b, b.player, b.enemy, best.id, rng)
            else:
                _say(b, "Nothing will bear for an aimed shot.", "dim")
    elif seat != "gunnery":
        # The gunner keeps working while you are elsewhere, less well. With a
        # battle computer they at least stop firing into an empty arc or
        # cooking the mounts past the cap; without one it is salvo, always,
        # whatever the heat and whatever bears.
        chosen = doctrine.order_for(b.player, b.enemy, "gunnery")
        pick = chosen[0] if chosen else "salvo"
        if pick == "salvo":
            _salvo(b, b.player, b.enemy, rng)
        elif pick == "aimed":
            usable = [w for w in b.player.st.weapons
                      if w.wpn.bears_at(b.band) <= 0.5
                      and st_mod.bears_on(b.player, b.enemy, w)[0]]
            if usable:
                _fire(b, b.player, b.enemy,
                      max(usable, key=lambda w: w.wpn.dmg).id, rng)

    bits = [t for t in (helm_text, eng_text) if t]
    if bits:
        _say(b, f"{b.player.ship.name}: {', '.join(bits)}.", "dim")
    b.pending_order = None


def _end_of_turn(b: Battle, rng) -> None:
    for s in (b.player, b.enemy):
        s.ship.heat = max(0.0, s.ship.heat - s.st.vent)
        if s.ship.heat > s.st.heat_cap:
            over = s.ship.heat - s.st.heat_cap
            _say(b, f"{_who(b, s)} is overheating — systems faulting.", "warn")
            s.resolve -= over * 0.3
            if rng.chance(0.25):
                _disable(b, s, rng, "Thermal shutdown takes")
        if is_breached(s.ship):
            s.resolve -= 6
        s.blind = max(0, s.blind - 1)
        s.jammed = max(0, s.jammed - 1)
        s.grappled = max(0, s.grappled - 1)
        for k in list(s.cd):
            s.cd[k] = max(0, s.cd[k] - 1)
        # Living hulls close wounds even mid-fight, slowly.
        if s.st.regen > 0:
            for L in reversed(s.ship.layers):
                if 0 < L.hp < L.max:
                    L.hp = min(L.max, L.hp + L.max * L.regen * s.st.regen * 0.5)
                    break

    b.turn += 1
    # Nobody fights forever. Past a dozen turns without resolution the
    # ammunition and the heat stop being worth it. It starts late deliberately:
    # a decisive hull should still be able to finish the job on its own terms.
    # Nerve goes when a hull is being taken apart and is not giving as good as
    # it gets. This used to be a pure function of the turn counter — and the
    # enemy lost it twice as fast as the player — so a ship with no armament at
    # all drove off a battleship three times in four simply by waiting. The
    # clock term survives only to guarantee the fight ends.
    grind = max(0, b.turn - GRIND_TURN) * 0.12
    for side, other in ((b.player, b.enemy), (b.enemy, b.player)):
        hurt = max(0.0, 1.0 - hull_pct(side.ship))
        behind = max(0.0, (other.dealt - side.dealt) / 220.0)
        # Futility is what makes endurance a real strategy: a hull built to be
        # hit and not break wins by convincing the other side there is no point
        # continuing. Weighted by how little progress the attacker has made, so
        # a ship that *is* being taken apart cannot outlast anybody.
        progress = 1.0 - hull_pct(other.ship)
        futile = max(0.0, (b.turn - GRIND_TURN) / 16.0) * (1.0 - progress)
        side.resolve -= grind + hurt * 3.6 + behind * 2.4 + futile * 1.8

    if b.enemy.resolve <= 0:
        _finish(b, "driven-off")
    elif b.player.resolve <= -40:
        _finish(b, "routed")
    elif b.turn > MAX_TURNS:
        _finish(b, "stalemate")


_ENDINGS = {
    "destroyed": "{enemy} comes apart across three compartments.",
    "driven-off": "{enemy} breaks off. Whatever they came for, it was not worth this.",
    "escaped": "You break contact and run dark.",
    "parley": "They stand down. Somebody on that bridge wanted a reason to.",
    "routed": "You have nothing left to hold with. They let you go.",
    "stalemate": "Neither hull can finish the other. You drift apart, both of you "
                 "poorer and neither of you satisfied.",
    "lost": "{player} is lost.",
}


def _finish(b: Battle, result: str) -> Battle:
    b.over = True
    b.result = result
    line = _ENDINGS.get(result, result).format(enemy=b.enemy_name,
                                               player=b.player.ship.name)
    _say(b, line, "bad" if result == "lost" else "good")
    return b


__all__ = ["Battle", "Side", "start", "take_turn", "use_ability", "BANDS",
           "MAX_TURNS", "GRIND_TURN"]
