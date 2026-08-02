"""Where the gates are, what they link, and which of them are lit.

The sites and the links are **derived** from the galaxy's own seed, the way
anchorages and traffic are: a sector always has the same Weave, in the same
places, with no migration to write and nothing extra in the save. What is
*stored* is only what a captain can change — which dark anchors have been
woken, and which new ones they paid to lay.

**Where the ancient sites are.** Farthest-point sampling: take the system
nearest the middle of the sector, then repeatedly take whichever system is
furthest from everything chosen so far. That spreads nine anchors across
sixty-eight light years without any of them landing on top of another, and it
is deterministic, so the Verge Anchor is the Verge Anchor in every chronicle
grown from that seed.

**What links what.** A ring through the sites in the order they lie around the
sector's centre, plus a few chords across it. The ring makes the network
legible — you can see it, and follow it — and the chords are what make holding
one system worth something, because without them every route is forced.

`sim/gates.py` does the acts: using a link, waking an anchor, laying one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..core.rng import RNG
from ..core.save import register
from ..data.gates import (ANCIENT_CHORDS, ANCIENT_LIT, ANCIENT_NAMES,
                          ANCIENT_SITES)
from ..world.galaxy import distance


@register
@dataclass
class WeaveState:
    """What the captain has changed about the Weave. Everything else derives."""

    #: System ids whose ancient anchor has been woken.
    woken: list = field(default_factory=list)
    #: New anchors laid, as (system_id, kind).
    built: list = field(default_factory=list)
    #: Transits made, for the chronicle and the codex.
    transits: int = 0
    #: Tolls paid, all told.
    tolls: float = 0.0


@dataclass(frozen=True)
class Gate:
    """One anchor, where it stands and what it reaches."""

    system_id: int
    name: str
    kind: str                 # ancient | charter | yours
    lit: bool
    #: System ids on the other end of its rings.
    links: tuple = ()

    @property
    def id(self) -> str:
        return f"gate:{self.system_id}"


def ensure(game) -> WeaveState:
    if getattr(game, "weave", None) is None:
        game.weave = WeaveState()
    return game.weave


# ── where they are ─────────────────────────────────────────────────────────

#: `sites`, `ancient_links` and `lit_at_dawn` by galaxy seed. See `sites`.
_SHAPE: dict = {}


def _key(galaxy) -> tuple:
    """What a galaxy's shape depends on: its seed, and nothing else.

    A `Galaxy` is generated deterministically from its seed and is never added
    to afterwards — the one `systems.append` in `world/galaxy.py` runs while it
    is being built. The system count rides along as a cheap guard against a
    galaxy assembled some other way.
    """
    return (galaxy.seed, len(galaxy.systems))


def sites(galaxy) -> list[int]:
    """The ancient anchor systems, spread across the sector.

    Farthest-point sampling, which is deterministic and needs no luck at all
    beyond the tie-break: the same galaxy always grows the same Weave.

    **And it is answered once per galaxy, because it was costing the game its
    responsiveness.** This is O(sites x systems) with a `min` over the chosen
    set inside the loop, and every question about where a hull is walks
    `track.at` -> `traffic.in_system` -> `_busyness` -> `weave.gate_at` ->
    `gates` -> here. Profiled on the Pilot screen, one button press ran
    `world.galaxy.distance` **151,728 times** and took 48.7 ms — a visible
    stutter on every click. Nothing about the answer can change inside a
    chronicle, so it is computed once and kept.
    """
    hit = _SHAPE.get(("sites", _key(galaxy)))
    if hit is not None:
        return hit
    systems = galaxy.systems
    if len(systems) <= 2:
        return [s.id for s in systems]
    mid_x = sum(s.x for s in systems) / len(systems)
    mid_y = sum(s.y for s in systems) / len(systems)
    first = min(systems, key=lambda s: math.hypot(s.x - mid_x, s.y - mid_y))
    chosen = [first.id]
    want = min(ANCIENT_SITES, len(systems))
    while len(chosen) < want:
        far, best = None, -1.0
        for s in systems:
            if s.id in chosen:
                continue
            near = min(distance(s, systems[c]) for c in chosen)
            if near > best:
                far, best = s.id, near
        if far is None:
            break
        chosen.append(far)
    _SHAPE[("sites", _key(galaxy))] = chosen
    return chosen


def _ring_order(galaxy, ids: list[int]) -> list[int]:
    """The sites sorted by where they lie around the sector's middle."""
    systems = galaxy.systems
    mid_x = sum(s.x for s in systems) / len(systems)
    mid_y = sum(s.y for s in systems) / len(systems)
    return sorted(ids, key=lambda i: math.atan2(systems[i].y - mid_y,
                                                systems[i].x - mid_x))


def ancient_links(galaxy) -> dict:
    """The ancient rings: system id -> the system ids it is paired with."""
    hit = _SHAPE.get(("links", _key(galaxy)))
    if hit is not None:
        return hit
    ids = sites(galaxy)
    if len(ids) < 2:
        return {i: () for i in ids}
    order = _ring_order(galaxy, ids)
    pairs: dict = {i: set() for i in ids}
    for index, here in enumerate(order):
        there = order[(index + 1) % len(order)]
        if here != there:
            pairs[here].add(there)
            pairs[there].add(here)
    # Chords. Seeded on the galaxy so a sector's Weave is its own, and drawn
    # between sites that are not already neighbours.
    rng = RNG(f"weave:{galaxy.seed}")
    for _ in range(ANCIENT_CHORDS):
        for _try in range(24):
            a = order[rng.int(0, len(order) - 1)]
            b = order[rng.int(0, len(order) - 1)]
            if a != b and b not in pairs[a]:
                pairs[a].add(b)
                pairs[b].add(a)
                break
    out = {i: tuple(sorted(v)) for i, v in pairs.items()}
    _SHAPE[("links", _key(galaxy))] = out
    return out


def lit_at_dawn(galaxy) -> list[int]:
    """The anchors the powers already use, and built their capitals around.

    Lit as a **chain**, not as three scattered singletons. A link burns only
    when both of its ends do, so lighting the three best-connected anchors
    independently gave a sector with one working link in it and two anchors
    standing on their own in the dark — technically a Weave, and no use to
    anybody trying to learn what a Weave is.

    Ports first for the head of the chain: a system with a quay is a system
    somebody could already reach, and the oldest reason to be able to reach
    anywhere is that there was a gate standing in it.
    """
    ids = sites(galaxy)
    if not ids:
        return []
    links = ancient_links(galaxy)
    ported = [i for i in ids if getattr(galaxy.systems[i], "port", None)]
    pool = ported or ids
    head = max(pool, key=lambda i: (len(links.get(i, ())), -i))
    chain = [head]
    while len(chain) < min(ANCIENT_LIT, len(ids)):
        # Whichever unlit anchor touches the chain and is best connected
        # onward, so the opening Weave is a road rather than a dead end.
        options = [i for i in ids if i not in chain
                   and any(i in links.get(c, ()) for c in chain)]
        if not options:
            options = [i for i in ids if i not in chain]
        chain.append(max(options, key=lambda i: (len(links.get(i, ())), -i)))
    return chain


# ── what is there now ──────────────────────────────────────────────────────

def gates(game) -> list[Gate]:
    """Every anchor in the sector, ancient and laid, lit and dark."""
    state = ensure(game)
    galaxy = game.galaxy
    links = ancient_links(galaxy)
    dawn = set(lit_at_dawn(galaxy))
    woken = set(state.woken)
    out = []
    for index, sid in enumerate(sites(galaxy)):
        out.append(Gate(
            system_id=sid,
            name=ANCIENT_NAMES[index % len(ANCIENT_NAMES)],
            kind="ancient",
            lit=sid in dawn or sid in woken,
            links=links.get(sid, ())))
    for sid, kind in state.built:
        out.append(Gate(system_id=sid,
                        name=f"{galaxy.systems[sid].name} Anchor",
                        kind=kind, lit=True,
                        links=tuple(_built_links(game, sid))))
    return out


def _built_links(game, sid: int) -> list[int]:
    """A laid anchor hangs off whichever lit ring it was anchored to."""
    from ..data.gates import BUILD_REACH_LY
    here = game.galaxy.systems[sid]
    near = []
    for gate in _ancient_gates(game):
        if not gate.lit or gate.system_id == sid:
            continue
        span = distance(here, game.galaxy.systems[gate.system_id])
        if span <= BUILD_REACH_LY:
            near.append((span, gate.system_id))
    near.sort()
    return [gid for _span, gid in near[:2]]


def _ancient_gates(game) -> list[Gate]:
    state = ensure(game)
    links = ancient_links(game.galaxy)
    dawn = set(lit_at_dawn(game.galaxy))
    woken = set(state.woken)
    return [Gate(system_id=sid, name=ANCIENT_NAMES[i % len(ANCIENT_NAMES)],
                 kind="ancient", lit=sid in dawn or sid in woken,
                 links=links.get(sid, ()))
            for i, sid in enumerate(sites(game.galaxy))]


def gate_at(game, system_id: int) -> Gate | None:
    """The anchor standing in a system, if any."""
    return next((g for g in gates(game) if g.system_id == system_id), None)


def network(game) -> dict:
    """The lit Weave: system id -> the system ids you can step to from it.

    A link works only when **both** ends are burning. That is what makes
    waking an anchor a decision rather than a purchase: the first one you
    light does nothing at all until its neighbour is lit too.
    """
    all_gates = {g.system_id: g for g in gates(game)}
    live: dict = {}
    for sid, gate in all_gates.items():
        if not gate.lit:
            continue
        reach = [other for other in gate.links
                 if other in all_gates and all_gates[other].lit]
        # Laid anchors hang off a ring; the ring answers back.
        for other, og in all_gates.items():
            if og.lit and sid in og.links and other not in reach:
                reach.append(other)
        if reach:
            live[sid] = sorted(set(reach))
    return live


def reachable(game, system_id: int) -> list[int]:
    """Everywhere the Weave can carry you from a system, in one step or many.

    One step is instant and one toll; the panel offers the whole component
    because a captain thinks in destinations, not in hops.
    """
    live = network(game)
    if system_id not in live:
        return []
    seen, queue = {system_id}, [system_id]
    while queue:
        here = queue.pop()
        for there in live.get(here, ()):
            if there not in seen:
                seen.add(there)
                queue.append(there)
    seen.discard(system_id)
    return sorted(seen)


def summary(game) -> dict:
    """What the Weave is, for the codex and the chart."""
    all_gates = gates(game)
    lit = [g for g in all_gates if g.lit]
    live = network(game)
    edges = sum(len(v) for v in live.values()) // 2
    state = ensure(game)
    return {
        "gates": len(all_gates), "lit": len(lit), "dark": len(all_gates) - len(lit),
        "links": edges, "joined": len(live),
        "transits": state.transits, "tolls": state.tolls,
        "built": len(state.built), "woken": len(state.woken),
    }
