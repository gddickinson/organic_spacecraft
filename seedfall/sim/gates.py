"""Using the Weave, waking what is dark, and laying anchors of your own.

`sim/weave.py` says where the gates are and which are burning. This is what a
captain can do about it.

**Transit is instant.** It is the only act in the game that does not spend the
calendar, and that is deliberate: a sector sixty-eight light years across with
a ten light year jump range is a sector where most of the map is scenery, and
the Weave is what turns the far side of it into somewhere you can be this
afternoon. What it spends instead is money, and standing, and — through the
Bloom — the sector's safety.

**A toll to whoever holds the far end.** Which makes the Weave a political
object. A power that thinks well of you halves it; one that does not will not
open at all. Nothing else in the game charges you for being disliked in quite
this way, and it is the reason to keep a quay sweet at the other end of the
sector from everything else you care about.

**Waking is expensive and needs both halves of the knowledge.** `weavecraft`
requires Xenolith Metallurgy *and* the Foldrunner Coil — you cannot wake one
of these by understanding only the physics or only the material. That is the
ancient-and-modern mixture the whole system is built on.

**And the Bloom uses it.** See `bloom_links`, which `sim/threat.py` calls on
every growth tick. A lit link hands a share of the source's infestation to the
far end regardless of the light years between them. One link is survivable; a
fully-woken Weave with something bad on it is how a sector dies.
"""

from __future__ import annotations

from ..data.factions import FACTIONS_BY_ID
from ..data.gates import (BLOOM_CARRY, BLOOM_CARRY_FLOOR, BUILD_CREDITS,
                          BUILD_DAYS, BUILD_GOODS, BUILD_REACH_LY, BUILD_TECH,
                          GATE_KINDS, TOLL_BASE, TOLL_PER_LY,
                          TOLL_REFUSED_BELOW, TOLL_STANDING_SWING, WAKE_CREDITS,
                          WAKE_DAYS, WAKE_GOODS, WAKE_TECH)
from ..world.galaxy import distance
from . import weave
from .ship import add_cargo


def holder(game, system_id: int) -> str | None:
    """Whose space the far end of a link is in."""
    return getattr(game.galaxy.systems[system_id], "faction", None)


def toll(game, from_id: int, to_id: int) -> dict:
    """What one hop costs, and whether they will open at all.

    Priced on the light years the hop saves rather than on the hop itself: a
    gate that lands you next door is worth little and one that throws you
    across the sector is worth a great deal, which is also the order a
    captain would rank them in.
    """
    span = distance(game.galaxy.systems[from_id], game.galaxy.systems[to_id])
    who = holder(game, to_id)
    standing = game.rep.get(who, 0.0) if who else 0.0
    # Kin halves it, hated nearly doubles it.
    scale = 1.0 - TOLL_STANDING_SWING * (standing / 100.0)
    fee = round(max(0.0, (TOLL_BASE + TOLL_PER_LY * span) * scale))
    refused = bool(who) and standing < TOLL_REFUSED_BELOW
    return {
        "from": from_id, "to": to_id, "ly": span, "credits": fee,
        "holder": who, "standing": standing, "refused": refused,
        "why": (f"{FACTIONS_BY_ID[who].short} will not open the ring for you."
                if refused else ""),
    }


def route(game, to_id: int, from_id: int | None = None) -> list[int] | None:
    """The shortest chain of lit links from here to there, or None.

    Breadth-first, so a captain is offered the fewest tolls rather than the
    fewest light years — the light years are free, which is the whole point.
    """
    start = game.location_id if from_id is None else from_id
    live = weave.network(game)
    if start not in live or to_id not in live:
        return None
    if start == to_id:
        return []
    seen = {start: None}
    queue = [start]
    while queue:
        here = queue.pop(0)
        for there in live.get(here, ()):
            if there in seen:
                continue
            seen[there] = here
            if there == to_id:
                path, node = [], to_id
                while node is not None and node != start:
                    path.append(node)
                    node = seen[node]
                return list(reversed(path))
            queue.append(there)
    return None


def quote(game, to_id: int) -> dict:
    """Everything about a Weave crossing, before committing to it."""
    hops = route(game, to_id)
    if hops is None:
        return {"ok": False, "why": "No lit ring runs from here to there.",
                "hops": [], "credits": 0, "days": 0}
    tolls = []
    here = game.location_id
    # **A throat and a clock.** Transit is still the only act that does not
    # spend the calendar *for the crossing itself* — what it spends now is
    # the wait for a slot, which is a property of the rings on the way and of
    # how hard the systems they stand in are working them. See
    # `sim/gatetraffic`, and `data/gate_traffic` for why a courier is not
    # held up by the same queue a freighter is.
    from . import gatetraffic
    from . import impulse
    mass = impulse.ship_mass(game)
    held, wide = 0.0, ""
    for step in hops:
        ring = weave.gate_at(game, here)
        fits, why_not = gatetraffic.may_pass(game, ring, mass)
        if not fits and not wide:
            wide = why_not
        held += gatetraffic.wait_days(game, ring)
        tolls.append(toll(game, here, step))
        here = step
    refused = [t for t in tolls if t["refused"]]
    total = sum(t["credits"] for t in tolls)
    saved = distance(game.galaxy.systems[game.location_id],
                     game.galaxy.systems[to_id])
    return {
        "ok": not refused and not wide and game.credits >= total,
        "why": (wide if wide else refused[0]["why"] if refused else
                (f"The tolls come to ₡{total:,.0f} and you have "
                 f"₡{game.credits:,.0f}." if game.credits < total else "")),
        "hops": hops, "tolls": tolls, "credits": total,
        "days": round(held, 2), "wait": round(held, 2), "bore": wide,
        "ly_saved": saved, "refused": bool(refused) or bool(wide),
    }


def can_use(game, to_id: int) -> tuple[bool, str]:
    """The gate on using a gate."""
    # Instruments in force close rings. `sim/enforce.may_pass` asks whose
    # ring this is before refusing, so an interdict by one power does not
    # strand you on another's network — which is what makes the Weave's
    # geography political rather than a single on/off switch.
    from . import enforce as enforce_sim
    passable, refusal = enforce_sim.may_pass(game, to_id)
    if not passable:
        return False, refusal
    if to_id == game.location_id:
        return False, "You are already here."
    here = weave.gate_at(game, game.location_id)
    if here is None or not here.lit:
        return False, "There is no lit anchor in this system."
    said = quote(game, to_id)
    return bool(said["ok"]), said["why"] or ""


def use(game, to_id: int) -> dict:
    """Step through. Instant, and the only thing in the game that is."""
    ok, why = can_use(game, to_id)
    if not ok:
        return {"ok": False, "why": why}
    said = quote(game, to_id)
    state = weave.ensure(game)
    game.credits -= said["credits"]
    state.tolls += said["credits"]
    state.transits += 1

    from . import flight
    target = game.galaxy.systems[to_id]
    game.location_id = to_id
    flight.arrive_in_system(game)
    first = not target.visited
    target.visited = True
    if first and to_id not in game.discovered["systems"]:
        game.discovered["systems"].append(to_id)
    # The crossing is still instant; the *queue* is not. A ring working at
    # its cycle takes you when it takes you.
    # **A queue is only a cost once it is worth a day.** The calendar steps
    # in days, so charging a whole one for a two-hour wait would make every
    # crossing in the sector cost a day — which is the opposite of what the
    # Weave is for. Rounded, not ceilinged: an afternoon is free and a ring
    # that is genuinely backed up takes its day.
    waited = float(said.get("days", 0.0) or 0.0)
    held = int(round(waited))
    if held >= 1:
        game.advance_days(held)
    game.add_log(
        f"Through the Weave to {target.name}: {len(said['hops'])} ring(s), "
        f"₡{said['credits']:,.0f} in tolls, {said['ly_saved']:.0f} light "
        + ("years, and no time at all." if waited < 0.01 else
           f"years, and {waited:.1f} d waiting for a slot."), "good")
    return {"ok": True, "hops": said["hops"], "credits": said["credits"],
            "ly_saved": said["ly_saved"], "first": first,
            "days": round(waited, 2)}


# ── waking what is dark ────────────────────────────────────────────────────

def _afford(game, goods: dict) -> tuple[bool, str]:
    for cid, need in goods.items():
        have = game.ship.cargo.get(cid, 0) + game.stores.get(cid, 0)
        if have < need:
            return False, f"{need} {cid} needed; {have:g} to hand."
    return True, ""


def _spend(game, credits: float, goods: dict) -> None:
    game.credits -= credits
    for cid, need in goods.items():
        from_ship = min(game.ship.cargo.get(cid, 0), need)
        if from_ship:
            add_cargo(game.ship, cid, -from_ship)
        rest = need - from_ship
        if rest > 0:
            game.stores[cid] = max(0.0, game.stores.get(cid, 0) - rest)


def can_wake(game, system_id: int | None = None) -> tuple[bool, str]:
    """May this anchor be woken? The gate the button greys on."""
    system_id = game.location_id if system_id is None else system_id
    gate = weave.gate_at(game, system_id)
    if gate is None:
        return False, "No anchor stands in this system."
    if gate.lit:
        return False, f"{gate.name} is already burning."
    if gate.kind != "ancient":
        return False, "Only the ancient anchors can be woken."
    if system_id != game.location_id:
        return False, "You have to be standing in it."
    if WAKE_TECH not in game.research.unlocked:
        return False, ("Nobody aboard knows how. Weavecraft wants the "
                       "metallurgy and the fold physics both.")
    if game.credits < WAKE_CREDITS:
        return False, (f"₡{WAKE_CREDITS:,.0f} of work, and you have "
                       f"₡{game.credits:,.0f}.")
    ok, why = _afford(game, WAKE_GOODS)
    return (ok, why)


def wake(game, system_id: int | None = None) -> dict:
    """Light an ancient anchor. Weeks of work and a great deal of money."""
    system_id = game.location_id if system_id is None else system_id
    ok, why = can_wake(game, system_id)
    if not ok:
        return {"ok": False, "why": why}
    gate = weave.gate_at(game, system_id)
    state = weave.ensure(game)
    _spend(game, WAKE_CREDITS, WAKE_GOODS)
    state.woken.append(system_id)
    game.advance_days(WAKE_DAYS)
    if game.dead:
        return {"ok": True, "dead": True}
    live = weave.network(game)
    joined = len(live.get(system_id, ()))
    game.add_log(
        f"{gate.name} is burning. " +
        (f"{joined} ring(s) answer." if joined else
         "Nothing answers yet — the anchors it reaches are still dark."),
        "good")
    return {"ok": True, "gate": gate, "links": joined,
            "reaches": weave.reachable(game, system_id)}


# ── laying your own ────────────────────────────────────────────────────────

def anchor_options(game) -> list[int]:
    """Lit anchors near enough for a new one here to hang off."""
    here = game.galaxy.systems[game.location_id]
    out = []
    for gate in weave.gates(game):
        if not gate.lit or gate.system_id == game.location_id:
            continue
        if distance(here, game.galaxy.systems[gate.system_id]) <= BUILD_REACH_LY:
            out.append(gate.system_id)
    return out


def can_build(game, system_id: int | None = None) -> tuple[bool, str]:
    system_id = game.location_id if system_id is None else system_id
    if system_id != game.location_id:
        return False, "You have to be standing in it."
    if weave.gate_at(game, system_id) is not None:
        return False, "There is already an anchor here."
    if BUILD_TECH not in game.research.unlocked:
        return False, "Nobody aboard knows how to lay one."
    if not anchor_options(game):
        return False, (f"No lit ring within {BUILD_REACH_LY:.0f} light years "
                       "to hang it off.")
    if game.credits < BUILD_CREDITS:
        return False, (f"₡{BUILD_CREDITS:,.0f} of work, and you have "
                       f"₡{game.credits:,.0f}.")
    return _afford(game, BUILD_GOODS)


def build(game, system_id: int | None = None) -> dict:
    """Lay an anchor of your own onto somebody else's ring."""
    system_id = game.location_id if system_id is None else system_id
    ok, why = can_build(game, system_id)
    if not ok:
        return {"ok": False, "why": why}
    state = weave.ensure(game)
    _spend(game, BUILD_CREDITS, BUILD_GOODS)
    state.built.append((system_id, "yours"))
    game.advance_days(BUILD_DAYS)
    if game.dead:
        return {"ok": True, "dead": True}
    name = game.galaxy.systems[system_id].name
    game.add_log(f"{name} Anchor is lit, and it is yours.", "good")
    return {"ok": True, "links": len(weave.network(game).get(system_id, ()))}


# ── what it costs the sector ───────────────────────────────────────────────

def bloom_links(game) -> list[tuple[int, int, float]]:
    """Where growth crosses the Weave this tick: (from, to, share).

    A lit link is a road, and the Bloom is not fussy about who laid it. Only
    a properly infested system exports — below `BLOOM_CARRY_FLOOR` the spores
    do not survive the crossing — and what it hands over is a share of what
    it has, so the danger scales with how bad the source already is.

    **Only rings the captain lit count.** The three anchors burning at dawn
    have been burning for four hundred years; whatever they were going to
    carry, they carried it long ago, and the sector's present state is the
    equilibrium that already includes them. Charging the world afresh for
    them every tick was not a consequence of anything the captain did — it
    perturbed a Bloom balance a dozen long-running checks are calibrated
    against, and made the escalation *jump* stage thresholds rather than
    climb them. What changes the Verge is what you wake.
    """
    state = weave.ensure(game)
    yours = set(state.woken) | {sid for sid, _kind in state.built}
    if not yours:
        return []
    live = weave.network(game)
    out = []
    for here, there_list in live.items():
        source = getattr(game.galaxy.systems[here], "bloom", 0.0)
        if source < BLOOM_CARRY_FLOOR:
            continue
        for there in there_list:
            if here in yours or there in yours:
                out.append((here, there, source * BLOOM_CARRY))
    return out


def kind_name(gate) -> str:
    return GATE_KINDS.get(gate.kind, ("Anchor", ""))[0]


def kind_blurb(gate) -> str:
    return GATE_KINDS.get(gate.kind, ("", ""))[1]
