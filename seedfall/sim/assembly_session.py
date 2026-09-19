"""When the Assembly sits, where, what it tables, and what comes of it.

**Each sitting has its own luck.** The day it sits and what it tables are
drawn from `luck(game, session, tag)` — a generator keyed on the chronicle's
seed and the sitting's number — never from `game.rng`, which advances with
every call. So the agenda is the same whoever looks at it and whenever, and
opening the screen cannot reroll a sitting.

The agenda is drawn when it is published (`NOTICE_DAYS` ahead) and stored,
weighted by the sector as it stands then: growth tables the levy, a war
tables a ceasefire, a hot sector tables the contraband accord.
"""

from __future__ import annotations

import math

from ..core.rng import RNG
from ..data.assembly import (NOTICE_DAYS, RESOLUTIONS, RESOLUTIONS_BY_ID,
                             SEAT_ORDER, SESSION_DAYS, SESSION_JITTER, TABLED)
from ..data.factions import FACTIONS_BY_ID
from . import assembly
from . import assembly_vote as vote
from . import diplomacy as dip
from . import renown_perks

#: How far a system may lie off the straight run between two capitals and
#: still be on a "capital lane" for the Convoy Escort Mandate, in light
#: years. Measured over four sectors, 2.5 ly puts 9-14 of 42 systems on the
#: lanes: the busy middle of the map, not all of it.
CORRIDOR_LY = 2.5

#: A pair this cold gets a border treaty tabled. A ceasefire is tabled only
#: for a war (`war.WAR_AT`): tabled at -45 it passed 33 times in 36, and its
#: -40 floor then soaked up every blockade and censure for the term — the
#: floors alone lifted idle sectors' mean relation by +32 to +52 in five
#: years, which is Concord arriving with nobody brokering it.
BORDER_AT = -25.0

#: An embargo is tabled on the most isolated power only if it is this
#: isolated — its mean relation with the other three.
EMBARGO_AT = -15.0

CLERK = ("assembly", "Clerk of the Assembly")


def luck(game, session: int, tag: str) -> RNG:
    """The generator for one sitting's `tag`. Never `game.rng`."""
    return RNG(f"{game.seed}:assembly:{session}:{tag}")


# ── where and when ─────────────────────────────────────────────────────────

def seat_system(game, power: str):
    """Where this power hosts: its capital, else its largest quay."""
    from . import exchequer
    held = exchequer.holdings(game, power)
    if not held:
        return None
    caps = [s for s in held if s.port.capital]
    return caps[0] if caps else max(held, key=lambda s: (s.port.level, -s.id))


def seat(game, state) -> tuple[str | None, object | None]:
    """The next host and its system, skipping a power that holds no quay."""
    for step in range(len(SEAT_ORDER)):
        power = SEAT_ORDER[(state.turn + step) % len(SEAT_ORDER)]
        system = seat_system(game, power)
        if system is not None:
            return power, system
    return None, None


def present(game) -> bool:
    """Is the captain in the chamber — at the seat, alive and aboard?"""
    got = assembly.state(game)
    if got is None or game.dead:
        return False
    _power, system = seat(game, got)
    return system is not None and game.location_id == system.id


def schedule(game, state, first: bool = False) -> None:
    """Set the next sitting's day: a season on, give or take the jitter."""
    nxt = state.session + 1
    jitter = luck(game, nxt, "day").int(-SESSION_JITTER, SESSION_JITTER)
    state.next_day = int(game.day) + SESSION_DAYS + jitter
    state.announced = False
    if not first:
        state.turn = (state.turn + 1) % len(SEAT_ORDER)


# ── the order paper ────────────────────────────────────────────────────────

def _pairs():
    return [(a, b) for i, a in enumerate(dip.POWERS) for b in dip.POWERS[i + 1:]]


def _lanes(game) -> list[int]:
    """Systems within `CORRIDOR_LY` of the run between any two capitals."""
    caps = [s for s in game.galaxy.systems
            if getattr(s, "port", None) is not None and s.port.capital]
    out = set()
    for i, a in enumerate(caps):
        for b in caps[i + 1:]:
            for s in game.galaxy.systems:
                if _off_line(s, a, b) <= CORRIDOR_LY:
                    out.add(s.id)
    return sorted(out)


def _off_line(s, a, b) -> float:
    dx, dy = b.x - a.x, b.y - a.y
    span = dx * dx + dy * dy
    t = 0.0 if span <= 0 else max(0.0, min(1.0, ((s.x - a.x) * dx
                                                 + (s.y - a.y) * dy) / span))
    return math.dist((s.x, s.y), (a.x + t * dx, a.y + t * dy))


def _unclaimed(game) -> list[int]:
    return [s.id for s in game.galaxy.systems if not s.faction]


def _mean_regard(game, power: str) -> float:
    others = [p for p in dip.POWERS if p != power]
    return sum(dip.relation(game, power, o) for o in others) / len(others)


def _candidate(game, res, rng):
    """(weight, params, sponsor) for one instrument today, or None."""
    params: dict = {}
    weight = res.weight
    if res.shape == "power":
        target = min(dip.POWERS, key=lambda p: (_mean_regard(game, p), p))
        if _mean_regard(game, target) > EMBARGO_AT:
            return None
        params["power"] = target
        sponsor = min((p for p in dip.POWERS if p != target),
                      key=lambda p: (dip.relation(game, p, target), p))
        return weight, params, sponsor
    if res.shape == "pair":
        cold = sorted(_pairs(), key=lambda ab: (dip.relation(game, *ab), ab))
        from . import war
        edge = war.WAR_AT if res.id == "ceasefire" else BORDER_AT
        cold = [ab for ab in cold if dip.relation(game, *ab) <= edge]
        if not cold:
            return None
        a, b = cold[0] if res.id == "ceasefire" else rng.pick(cold)
        params.update(a=a, b=b)
        if res.id == "ceasefire":
            weight = 2.5
            third = [p for p in dip.POWERS if p not in (a, b)]
            sponsor = max(third, key=lambda p: (
                min(dip.relation(game, p, a), dip.relation(game, p, b)), p))
        else:
            from . import exchequer
            weight = 0.8
            sponsor = min((a, b), key=lambda p: (
                len(exchequer.holdings(game, p)), p))
        return weight, params, sponsor
    if res.shape == "lanes":
        params["systems"] = _lanes(game)
    elif res.shape == "unclaimed":
        params["systems"] = _unclaimed(game)
    if res.shape and not params["systems"]:
        return None
    if res.pressure == "bloom":
        weight *= 1.0 + 6.0 * vote.bloom_share(game)
    elif res.pressure == "smuggling":
        weight *= 1.0 + 2.0 * vote.heat(game)
    keen = [(res.stance[p], p) for p in dip.POWERS if res.stance[p] > 0]
    sponsor = rng.weighted(keen) if keen else max(
        dip.POWERS, key=lambda p: res.stance[p])
    return weight, params, sponsor


def draw(game, state) -> list:
    """The order paper for the next sitting, from its own luck."""
    rng = luck(game, state.session + 1, "agenda")
    # Neither what is in force nor what was just voted down. A lost motion
    # tabled again at once is the same vote with the same losers: measured on
    # one sector, a refused ceasefire came back fourteen sittings running and
    # each refusal cost the war pair another six points, which is how a war
    # the Assembly was meant to end became one it made worse.
    live = {a.key for a in assembly.in_force(game)} | lost_last(state)
    pool = []
    for res in RESOLUTIONS:
        got = _candidate(game, res, rng)
        if got is None or got[0] <= 0:
            continue
        weight, params, sponsor = got
        item = assembly.Tabled(key=_key(res.id, params), res_id=res.id,
                               sponsor=sponsor, params=params)
        if item.key not in live:
            pool.append((weight, item))
    count = rng.int(*TABLED)
    out = []
    while pool and len(out) < count:
        item = rng.weighted(pool)
        pool = [(w, i) for w, i in pool if i is not item]
        out.append(item)
    return out


def lost_last(state) -> set:
    """The motions the last sitting voted down: rested for one sitting."""
    if not state.history:
        return set()
    return {r["key"] for r in state.history[-1].get("results", ())
            if not r.get("passed")}


def _key(res_id: str, params: dict) -> str:
    named = [params[k] for k in ("power", "a", "b") if k in params]
    return ":".join([res_id] + named)


def announce(game, state) -> None:
    """Publish the order paper, and send it out."""
    state.agenda = draw(game, state)
    state.agenda = renown_perks.motion(game, state.agenda)   # an Admiral's
    state.announced = True
    power, system = seat(game, state)
    if system is None:
        return
    lines = [f"{vote.title(t)} — tabled by the "
             f"{FACTIONS_BY_ID[t.sponsor].short}: {vote.words(t)}."
             for t in state.agenda]
    from . import comms
    comms.send(game, CLERK[0], CLERK[1], "news",
               f"The Assembly sits at {system.name} on day {state.next_day}",
               f"The {FACTIONS_BY_ID[power].short} host the sitting at "
               f"{system.name}. On the order paper:\n" + "\n".join(lines),
               system_id=system.id)
    game.add_log(f"The Assembly will sit at {system.name} on day "
                 f"{state.next_day}: {len(state.agenda)} motions tabled.", "")


# ── the sitting ────────────────────────────────────────────────────────────

def sit(game) -> list[dict]:
    """Count every vote on the order paper, and let it land. Returns what
    each motion came to, as the history keeps it."""
    state = assembly.ensure(game)
    if not state.announced:
        announce(game, state)
    power, system = seat(game, state)
    here = present(game)
    results = []
    for item in state.agenda:
        told = vote.forecast(game, item.key, present=here)
        moved = vote.moves(told["votes"], told["scores"], told["passes"])
        for pair, delta in moved.items():
            dip.shift_relation(game, *pair.split("|"), delta)
        res = RESOLUTIONS_BY_ID[item.res_id]
        if told["passes"]:
            assembly.enact(game, item, game.day, res.term)
            shift = res.extra.get("shift")
            if shift:
                dip.shift_relation(game, shift[0], shift[1], shift[2])
            # A ceasefire's floor, once. Held every day of the term it soaked
            # up every vote the two lost to each other as well as every
            # blockade: +20 mean relation per idle sector on its own (range
            # +4 to +32 over ten), and the idle Assembly a +10 peacemaker.
            # Lifted once, idle sectors end at +3.7 with 49% passing; the key
            # still keeps them out of war (`war.at_war`) for the whole term.
            lift = res.extra.get("lift")
            if lift is not None and "a" in item.params:
                a, b = item.params["a"], item.params["b"]
                low = dip.relation(game, a, b)
                if low < lift:
                    dip.shift_relation(game, a, b, lift - low)
        results.append({"key": item.key, "res": item.res_id,
                        "name": vote.title(item), "sponsor": item.sponsor,
                        "votes": dict(told["votes"]), "passed": told["passes"],
                        "moved": moved, "side": state.positions.get(item.key, "")})
        _count(state, item, told["passes"])
    if here and any(state.positions.get(t.key) for t in state.agenda):
        game.add_log(f"You spoke before the Assembly at {system.name}. "
                     "Four powers heard you out.", "good")
    state.history = (state.history + [{
        "session": state.session + 1, "day": int(game.day),
        "seat": power or "", "system": system.name if system else "",
        "present": here, "results": results}])[-assembly.HISTORY_KEPT:]
    _report(game, system, results)
    state.session += 1
    state.agenda, state.lobby, state.positions, state.acts = [], {}, {}, {}
    schedule(game, state)
    return results


def _count(state, item, passed: bool) -> None:
    """Tabled and passed, all time and by instrument — the manual's rate."""
    for key in ("all", item.res_id):
        row = state.tallies.setdefault(key, [0, 0])
        row[0] += 1
        row[1] += int(passed)


def _report(game, system, results) -> None:
    from . import comms
    lines = []
    for r in results:
        said = ", ".join(f"{FACTIONS_BY_ID[p].short} {v}"
                         for p, v in sorted(r["votes"].items()))
        lines.append(f"{r['name']}: {'PASSED' if r['passed'] else 'lost'} "
                     f"({said}).")
        game.add_log(f"The Assembly: {r['name']} "
                     f"{'passed' if r['passed'] else 'was lost'}.",
                     "good" if r["passed"] else "")
    if system is not None and lines:
        comms.send(game, CLERK[0], CLERK[1], "news",
                   f"The Assembly has risen at {system.name}",
                   "\n".join(lines), system_id=system.id)


def expire(game, state) -> None:
    """Strike out what has lapsed, and say so."""
    lapsed = [a for a in state.active if a.until <= game.day]
    if not lapsed:
        return
    state.active = [a for a in state.active if a.until > game.day]
    state.rev += 1
    for act in lapsed:
        game.add_log(f"The Assembly's {vote.title(act)} has lapsed.", "")


def tick(game, days: float) -> None:
    """Publish when the notice falls due, sit on the day, lapse, hold."""
    state = assembly.ensure(game)
    if not state.announced and game.day >= state.next_day - NOTICE_DAYS:
        announce(game, state)
    if game.day >= state.next_day:
        sit(game)
    expire(game, state)
    assembly.hold(game)
