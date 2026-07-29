"""Harbourmasters: who runs the quay, what they think of you, what you know.

A port was a bag of services with nobody in it. `sim/memory.py` has supported
minds keyed for ports since it was written, and a fresh chronicle's `minds`
store is empty and stays empty — nothing ever put a person behind a counter
you return to fifty times.

Two halves, deliberately split:

- **Who they are is derived.** Name, temperament, what they want, and which
  lever could exist against them, all seeded from the port id. Same chronicle,
  same person, no save migration — the same choice `anchorage` and `traffic`
  make.
- **What passed between you is stored**, in the `minds` that already persist.
  Regard, what they remember, which levers you have actually found, and which
  favours are running.

The politics is in the third thing. Dealing honestly at a quay makes somebody
*helpful* and stops there; `DEALING_CAP` is a wall you cannot trade through.
Past it you need either something they want or something they would rather you
did not say — and leaning on a lever gets you the favour and costs you the
regard, because being leant on is not the same as being helped.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data.lore import CREW_FIRST, CREW_LAST
from ..data.officials import (BANDS, CAP_PER_LEAN, DEALING_CAP,
                              FAVOURS_BY_ID, LEAN_MULTIPLIER, LEVERS,
                              LEVERS_BY_ID, PER_DEALING, START_REGARD,
                              TEMPERS)
from . import memory as memory_sim

#: What a harbourmaster's mind is keyed on.
KEY = "port:{system}"


def key_for(system) -> str:
    return KEY.format(system=system.id)


def identity(system) -> dict:
    """Who runs this quay. Derived, stable, and never stored.

    Seeded on the port and system only, so it cannot drift between calls or
    across a reload — the same rule an anchorage obeys, for the same reason.
    """
    port = getattr(system, "port", None)
    if port is None:
        return {}
    rng = RNG(f"official:{system.id}:{port.id}")
    temper = TEMPERS[rng.int(0, len(TEMPERS) - 1)]
    name = (f"{CREW_FIRST[rng.int(0, len(CREW_FIRST) - 1)]} "
            f"{CREW_LAST[rng.int(0, len(CREW_LAST) - 1)]}")
    # Which lever *could* exist here. Whether you have found it is another
    # matter entirely, and lives in the mind rather than here.
    fits = [lever for lever in LEVERS
            if not lever.tempers or temper.id in lever.tempers]
    lever = fits[rng.int(0, len(fits) - 1)] if fits else None
    return {"name": name, "temper": temper, "lever": lever,
            "title": "Harbourmaster", "system": system.id}


def mind(game, system):
    """The stored half: what has actually passed between you."""
    who = identity(system)
    if not who:
        return None
    return memory_sim.mind_for(
        game, key_for(system), name=who["name"], kind="port",
        persona="harbourmaster")


def _store(mind_obj) -> dict:
    """The official-specific state, kept on the mind so it is saved with it."""
    got = getattr(mind_obj, "office", None)
    if not got:
        got = {"regard": START_REGARD, "levers": [], "favours": {},
               "once": [], "dealings": 0, "leant": 0}
        mind_obj.office = got
    # A mind written before this field existed comes back with an empty dict.
    for key, default in (("regard", START_REGARD), ("levers", []),
                         ("favours", {}), ("once", []),
                         ("dealings", 0), ("leant", 0)):
        got.setdefault(key, default)
    return got


def regard(game, system) -> float:
    who = mind(game, system)
    return _store(who)["regard"] if who is not None else 0.0


def band(value: float) -> tuple[str, str]:
    name, tint = BANDS[0][1], BANDS[0][2]
    for floor, label, colour in BANDS:
        if value >= floor:
            name, tint = label, colour
    return name, tint


def adjust(game, system, delta: float, why: str = "") -> float:
    """Move what they think of you, and let them remember why."""
    who = mind(game, system)
    if who is None:
        return 0.0
    store = _store(who)
    store["regard"] = max(-100.0, min(100.0, store["regard"] + delta))
    if why:
        memory_sim.note(game, key_for(system), "dealing", why,
                        salience=min(2.0, abs(delta) / 12.0),
                        name=who.name, entity="port")
    return store["regard"]


def dealt_with(game, system, worth: float = 1.0) -> float:
    """Ordinary honest business at this quay.

    Capped: trading with somebody makes them helpful and never devoted. The
    last stretch has to come from what they want or what they fear.
    """
    who = mind(game, system)
    if who is None:
        return 0.0
    store = _store(who)
    store["dealings"] += 1
    ceiling = cap_for(store)
    if store["regard"] >= ceiling:
        return store["regard"]
    gain = min(PER_DEALING * worth, ceiling - store["regard"])
    store["regard"] += gain
    return store["regard"]


# ── levers ─────────────────────────────────────────────────────────────────

def cap_for(store) -> float:
    """How far honest dealing alone can carry you with this person.

    Falls each time you have leant on them. You can trade your way back into
    being useful; you cannot trade your way back into being liked.
    """
    return max(0.0, DEALING_CAP - CAP_PER_LEAN * store.get("leant", 0))


def known_levers(game, system) -> list:
    who = mind(game, system)
    if who is None:
        return []
    return [LEVERS_BY_ID[lid] for lid in _store(who)["levers"]
            if lid in LEVERS_BY_ID]


def has_lever(game, system) -> bool:
    return bool(known_levers(game, system))


def learn_lever(game, system, source: str = "") -> dict:
    """Find out the thing there is to know. Returns what was learned.

    Deliberately not a purchase with a price tag: you learn it by dealing with
    somebody long enough, or by turning it up somewhere else. `available` says
    when a route is open and why it is not.
    """
    who = mind(game, system)
    if who is None:
        return {"ok": False, "why": "There is no quay here."}
    person = identity(system)
    lever = person.get("lever")
    if lever is None:
        return {"ok": False, "why": "There is nothing to know about them."}
    store = _store(who)
    if lever.id in store["levers"]:
        return {"ok": False, "why": "You already know."}
    store["levers"].append(lever.id)
    memory_sim.note(game, key_for(system), "known",
                    f"You learned about {person['name']}"
                    + (f" — {source}." if source else "."),
                    salience=1.6, name=who.name, entity="port")
    return {"ok": True, "lever": lever,
            "text": lever.learned.format(who=person["name"])}


def can_learn(game, system) -> tuple[bool, str]:
    """Whether the thing is findable yet, and what would make it findable.

    Learning is earned rather than bought: enough dealings that people talk to
    you at this quay, or a decoded recording that mentions the place.
    """
    who = mind(game, system)
    if who is None:
        return False, "There is no quay here."
    person = identity(system)
    if person.get("lever") is None:
        return False, "There is nothing to know about them."
    store = _store(who)
    if store["levers"]:
        return False, "You already know."
    if store["dealings"] < 6:
        return False, (f"Nobody at this quay talks to a stranger. "
                       f"{store['dealings']} of 6 dealings.")
    if store["regard"] < 18:
        return False, ("They keep you at arm's length. Deal squarely here "
                       "first.")
    return True, ""


# ── favours ────────────────────────────────────────────────────────────────

def favour_running(game, system, favour_id: str) -> int:
    """Days left on a favour, or 0."""
    who = mind(game, system)
    if who is None:
        return 0
    until = _store(who)["favours"].get(favour_id, 0)
    return max(0, until - game.day)


def pending_once(game, system, favour_id: str) -> bool:
    """Is a one-shot favour sitting here waiting to be used?"""
    who = mind(game, system)
    return who is not None and favour_id in _store(who)["once"]


def spend_once(game, system, favour_id: str) -> bool:
    """Use up a one-shot favour. True if there was one to use."""
    who = mind(game, system)
    if who is None:
        return False
    store = _store(who)
    if favour_id not in store["once"]:
        return False
    store["once"].remove(favour_id)
    return True


def active_favours(game, system) -> list:
    who = mind(game, system)
    if who is None:
        return []
    store = _store(who)
    out = [(FAVOURS_BY_ID[fid], until - game.day)
           for fid, until in store["favours"].items()
           if fid in FAVOURS_BY_ID and until > game.day]
    # A one-shot is held rather than dated. Reported as 0 days left, which the
    # screen reads as "good once" — otherwise a favour you are holding, and
    # have paid regard for, appears nowhere at all.
    out += [(FAVOURS_BY_ID[fid], 0)
            for fid in store["once"] if fid in FAVOURS_BY_ID]
    return out


def anywhere(game, favour_id: str) -> bool:
    """Is this favour running at the quay you are standing at?

    True for a dated favour inside its window and for a one-shot that has been
    granted and not yet used.
    """
    system = game.system
    return (favour_running(game, system, favour_id) > 0
            or pending_once(game, system, favour_id))


def preview(game, system, favour_id: str, lean: bool) -> dict:
    """What asking will cost, before you ask."""
    favour = FAVOURS_BY_ID.get(favour_id)
    who = mind(game, system)
    if favour is None or who is None:
        return {}
    person = identity(system)
    temper = person["temper"]
    store = _store(who)
    cost = favour.regard * temper.price / max(0.3, temper.bend)
    out = {"favour": favour, "lean": lean, "cost": 0.0, "spends_lever": False,
           "lines": [], "ok": True, "why": ""}
    if lean:
        levers = known_levers(game, system)
        if not levers:
            out["ok"] = False
            out["why"] = "You have nothing to hold over them."
            return out
        out["spends_lever"] = True
        out["cost"] = -cost * LEAN_MULTIPLIER
        out["lines"].append(
            f"{levers[0].holds.format(who=person['name'])} They will do it, "
            "and they will not forget being asked this way.")
        out["lines"].append(f"Their regard falls by {abs(out['cost']):.0f}, "
                            "and the lever is spent.")
    else:
        out["cost"] = -cost
        if store["regard"] < favour.needs_regard:
            out["ok"] = False
            out["why"] = (f"They would want to think better of you than "
                          f"{store['regard']:.0f} before doing that. "
                          f"{favour.needs_regard:.0f} would do it.")
        out["lines"].append(f"Costs {cost:.0f} of their regard — a favour is "
                            "spent, not banked.")
    if favour.lasts:
        out["lines"].append(f"Holds for {favour.lasts} days at this quay.")
    return out


def ask(game, system, favour_id: str, lean: bool = False) -> dict:
    """Ask for something. Returns what happened, matching `preview` exactly."""
    plan = preview(game, system, favour_id, lean)
    if not plan or not plan["ok"]:
        return {"ok": False, "why": plan.get("why", "Not here.")}
    favour = plan["favour"]
    who = mind(game, system)
    store = _store(who)
    person = identity(system)

    if plan["spends_lever"]:
        levers = known_levers(game, system)
        store["levers"].remove(levers[0].id)
        store["leant"] += 1
        memory_sim.note(game, key_for(system), "leant",
                        f"You leant on {person['name']} to get "
                        f"{favour.name.lower()}.", salience=2.0,
                        name=who.name, entity="port")
    else:
        memory_sim.note(game, key_for(system), "favour",
                        f"{person['name']} did you a favour: "
                        f"{favour.name.lower()}.", salience=1.2,
                        name=who.name, entity="port")

    store["regard"] = max(-100.0, min(100.0, store["regard"] + plan["cost"]))
    if favour.lasts:
        store["favours"][favour.id] = game.day + favour.lasts
    elif favour.id not in store["once"]:
        # A favour that lasts no days is a favour good *once*. There was no
        # such thing: `if favour.lasts:` simply dropped it, so "a quiet price"
        # cost 12.7 regard, recorded nothing, and the code in `trade` that
        # reads it could never once fire. Measured before this: quoted 36/t,
        # paid 36/t, regard 60.0 → 47.3, and nothing else changed at all.
        store["once"].append(favour.id)
    return {"ok": True, "favour": favour, "leant": plan["spends_lever"],
            "regard": store["regard"]}


def describe(game, system) -> dict:
    """Everything a screen needs about the person behind the counter."""
    person = identity(system)
    if not person:
        return {}
    who = mind(game, system)
    store = _store(who)
    value = store["regard"]
    name, tint = band(value)
    return {
        "name": person["name"], "title": person["title"],
        "temper": person["temper"], "regard": value,
        "band": name, "tint": tint,
        "dealings": store["dealings"], "leant": store["leant"],
        "levers": known_levers(game, system),
        "favours": active_favours(game, system),
        "cap": cap_for(store),
        "capped": value >= cap_for(store),
    }
