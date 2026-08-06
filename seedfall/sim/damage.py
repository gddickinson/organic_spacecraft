"""A hit: which layer takes it, what breaches, and the words for it.

Carries the two log helpers as well — `_say` and `_who` — because this is
where most of an engagement's lines come from, and `combat` importing them
back is a shorter dependency than the reverse.

Lifted out of `combat.py` when the firing picture pushed that file past five
hundred lines. Nothing here decides *whether* a shot happens — `combat._fire`
owns that, and `sim/firing.py` reports it. This is only what a hit does once
it has landed.
"""

from __future__ import annotations

from ..core.util import clamp
from ..data.parts import part
from . import loyalty as loyalty_sim
from .battle_state import Battle, Side
from .ship import add_cargo, add_heat, is_breached, stats


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
                _breach(b, to, rng, lethal="nonlethal" not in traits)
            if L.life:
                _say(b, f"— {_who(b, to)} is on bottled air.", "warn")
        first = False
        idx += 1
    return total


def _breach(b: Battle, to: Side, rng, lethal: bool = True) -> None:
    """A critical layer has gone. Vacuum takes people — unless the thing
    that opened the hull carries `nonlethal`, a trait the glossary has
    always glossed "never kills crew" and nothing ever read: the Photic
    Flash Organ, the one armament every new captain starts with, vented
    crew exactly like a railgun. The fright and the shame land either way.
    """
    lost = 0
    if lethal:
        lost = max(1, round(to.ship.crew * rng.float(0.04, 0.14)
                            * (1 - to.st.crew_guard)))
        to.ship.crew = max(0, to.ship.crew - lost)
    to.resolve -= 18
    to.ship.morale = max(0.0, to.ship.morale - 0.12)
    if lethal:
        _say(b, f"PRESSURE BREACH on {_who(b, to)} — {lost} lost to vacuum.",
             "bad")
    else:
        _say(b, f"PRESSURE BREACH on {_who(b, to)} — suits hold; "
                "nobody is lost.", "warn")


def _apply_traits(b: Battle, frm: Side, to: Side, w, rng) -> None:
    t = w.wpn.traits
    if "blind" in t:
        to.blind = 2
        _say(b, f"{_who(b, to)} is dazzled.", "dim")
    if "grapple" in t:
        to.grappled = 2
        _say(b, f"Tendrils have hold of {_who(b, to)}.", "dim")
    if "emp" in t:
        add_heat(to.ship, 8, to.st.heat_cap)
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
