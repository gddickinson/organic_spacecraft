"""Moving a vote before the Assembly sits — and what each way of doing it costs.

Four ways, and each is paid for in something different:

- **Petition** spends standing with the power you ask. The price rises each
  time you ask the same power at one sitting.
- **Pay** spends credits, into that power's purse. Each payment to the same
  power at one sitting buys half the last, and the other three remember that
  votes were bought (`sim/grudge`).
- **Leak** spends a piece of intelligence on the sponsor — a chart of one of
  their systems, or a field note from one — and turns the other three against
  the motion. The sponsor knows who, and it costs standing with them.
- **Speak**: be at the seat on the day. Comms and standing carry your voice to
  every power, on every motion you have taken a side on.

Every act has a `preview` that states the swing, the cost and the side
effects, and `lobby` performs **exactly** what `preview` said —
`tests/test_assembly` does both and compares. **Nothing here gains standing.**
Petitioning spends it, leaking spends it, paying and speaking leave it alone,
so no loop of lobbying can come out ahead on standing.
"""

from __future__ import annotations

import copy

from ..data.factions import FACTIONS_BY_ID
from . import assembly
from . import assembly_vote as vote
from . import diplomacy as dip

#: What a petition moves, and what it first costs in standing. Each further
#: petition to the same power at one sitting costs `PETITION_RISE` times the
#: last: the first two are a favour, the fourth is an imposition.
PETITION_SWING = 2.5
PETITION_COST = 5.0
PETITION_RISE = 1.6

#: Below this standing, after paying for it, a power does not hear a
#: petition at all. -25 is where "Distrusted" begins.
PETITION_FLOOR = -25.0

#: What a payment costs, and what the first one moves. Each further payment
#: to the same power at one sitting buys `PAY_DECAY` of the last.
PAY_PRICE = 8000
PAY_SWING = 3.0
PAY_DECAY = 0.5

#: How hard the other three remember a bought vote, as a memory's salience.
#: A slight weighs -9 a unit (`sim/memory.WEIGHT`), so -5.4 of feeling each.
PAY_NOTICED = 0.6

#: What a leak turns each of the other three powers, and what it costs with
#: the sponsor — in standing, and in memory.
LEAK_SWING = 2.0
LEAK_COST = 6.0
LEAK_NOTICED = 0.8

#: A speech: this much with nobody on the comms console, plus this per point
#: of the ship's diplomacy (`ship.stats`, five hundredths per comms level),
#: all scaled by standing from half at nothing to one and a half at Kin+.
SPEECH_BASE = 1.0
SPEECH_PER_DIPLOMACY = 10.0

ACTS = ("petition", "pay", "leak")


def position(game, key: str, side: str) -> dict:
    """Say where the captain stands on a motion: "for", "against" or ""."""
    state = assembly.ensure(game)
    if vote.find(game, key) is None:
        return {"ok": False, "why": "That is not on the order paper."}
    if side not in ("for", "against", ""):
        return {"ok": False, "why": f"No such side: {side!r}."}
    if side:
        state.positions[key] = side
    else:
        state.positions.pop(key, None)
    return {"ok": True, "side": side}


def _times(state, act: str, power: str) -> int:
    return int(state.acts.get(f"{act}|{power}", 0))


def intelligence(game, power: str) -> list[str]:
    """Unspent intelligence on this power: its charted systems and the field
    notes filed in its space. What a leak is made of."""
    spent = set(assembly.ensure(game).spent)
    systems = game.galaxy.systems
    theirs = {s.id for s in systems if power in (
        s.faction, getattr(getattr(s, "port", None), "faction", None))}
    out = [f"chart:{sid}" for sid in sorted(getattr(game, "charts_made", {}) or {},
                                            key=str)
           if str(sid).isdigit() and int(sid) in theirs]
    names = {s.name: s.id for s in systems}
    for filed in getattr(game, "field_notes", None) or []:
        if names.get(filed.system) in theirs:
            out.append(f"note:{filed.note_id}")
    return [k for k in out if k not in spent]


def _feeling_after(game, power: str, text: str, salience: float) -> float:
    """What remembering this would move a power's own feeling by — worked
    out on a copy of its mind, so the quote is the memory's own arithmetic."""
    from . import grudge
    from . import memory as memory_sim
    held = memory_sim.minds(game).get(grudge.key_for(power))
    mind = copy.deepcopy(held) if held is not None else memory_sim.Mind(
        key=grudge.key_for(power), name=power, kind="faction")
    before = mind.impression()
    mind.remember(game.day, "slight", text, salience)
    return round(mind.impression() - before, 2)


def _bought_text(power: str) -> str:
    return f"you bought the {FACTIONS_BY_ID[power].short}'s vote at the Assembly"


def _leak_text() -> str:
    return "you leaked our papers to the Assembly"


def preview(game, act: str, power: str | None, key: str) -> dict:
    """What `lobby` would do, without doing it. The act does exactly this."""
    state = assembly.ensure(game)
    item = vote.find(game, key)
    out = {"ok": False, "why": "", "act": act, "power": power, "key": key,
           "swing": {}, "standing": {}, "credits": 0, "feeling": {},
           "intel": ""}
    if item is None:
        out["why"] = "That is not on the order paper."
        return out
    side = state.positions.get(key, "")
    if not side:
        out["why"] = "Say whether you are for it or against it first."
        return out
    sign = 1.0 if side == "for" else -1.0
    if act == "leak":
        power = out["power"] = item.sponsor
    if power not in dip.POWERS or act not in ACTS:
        out["why"] = "Nobody to lobby, or no such way of doing it."
        return out
    n = _times(state, act, power)
    if act == "petition":
        cost = round(PETITION_COST * PETITION_RISE ** n, 1)
        rep = game.rep.get(power, 0.0)
        if rep - cost < PETITION_FLOOR:
            out["why"] = (f"The {FACTIONS_BY_ID[power].short} would not hear "
                          f"it: {cost:g} standing from {rep:+.0f} leaves them "
                          "distrusting you.")
            return out
        out["swing"][power] = round(sign * PETITION_SWING, 2)
        out["standing"][power] = round(max(-100.0, rep - cost) - rep, 2)
    elif act == "pay":
        if game.credits < PAY_PRICE:
            out["why"] = f"A vote costs {PAY_PRICE:,}; you hold {game.credits:,.0f}."
            return out
        out["credits"] = -PAY_PRICE
        out["swing"][power] = round(sign * PAY_SWING * PAY_DECAY ** n, 2)
        for other in dip.POWERS:
            if other != power:
                out["feeling"][other] = _feeling_after(
                    game, other, _bought_text(power), PAY_NOTICED)
    else:
        if side != "against":
            out["why"] = "A leak only hurts a motion, and you are for this one."
            return out
        intel = intelligence(game, power)
        if not intel:
            out["why"] = (f"You hold nothing on the {FACTIONS_BY_ID[power].short}"
                          ": chart one of their systems, or bring a field note "
                          "out of their space.")
            return out
        out["intel"] = intel[0]
        rep = game.rep.get(power, 0.0)
        out["standing"][power] = round(max(-100.0, rep - LEAK_COST) - rep, 2)
        out["feeling"][power] = _feeling_after(game, power, _leak_text(),
                                               LEAK_NOTICED)
        for other in dip.POWERS:
            if other != power:
                out["swing"][other] = -LEAK_SWING
    out["ok"] = True
    out["before"] = vote.forecast(game, key)
    out["after"] = _after(game, key, out["swing"])
    return out


def _after(game, key: str, swing: dict) -> dict:
    """The forecast with this swing added, worked out on the real record and
    put back — so it is the forecast's own arithmetic, not a copy of it."""
    state = assembly.ensure(game)
    was = dict(state.lobby.get(key, {}))
    try:
        row = state.lobby.setdefault(key, {})
        for power, delta in swing.items():
            row[power] = round(row.get(power, 0.0) + delta, 2)
        return vote.forecast(game, key)
    finally:
        if was:
            state.lobby[key] = was
        else:
            state.lobby.pop(key, None)


def lobby(game, act: str, power: str | None, key: str) -> dict:
    """Do it. Exactly `preview`, which is asked first and returned."""
    told = preview(game, act, power, key)
    if not told["ok"]:
        return told
    state = assembly.ensure(game)
    power = told["power"]
    for who, delta in told["standing"].items():
        game.adjust_rep(who, delta)
    game.credits += told["credits"]
    row = state.lobby.setdefault(key, {})
    for who, delta in told["swing"].items():
        row[who] = round(row.get(who, 0.0) + delta, 2)
    tag = f"{act}|{power}"
    state.acts[tag] = int(state.acts.get(tag, 0)) + 1
    from . import grudge
    if act == "pay":
        from . import exchequer
        exchequer.purse(game, power).credits += -told["credits"]
        for other in told["feeling"]:
            grudge.note(game, other, "slight", _bought_text(power),
                        PAY_NOTICED, tags=["assembly", "bribe"])
    elif act == "leak":
        state.spent.append(told["intel"])
        grudge.note(game, power, "slight", _leak_text(), LEAK_NOTICED,
                    tags=["assembly", "leak"])
    item = vote.find(game, key)
    short = FACTIONS_BY_ID[power].short
    game.add_log({"petition": f"You petitioned the {short} on the "
                              f"{vote.title(item)}.",
                  "pay": f"You paid the {short} for their vote on the "
                         f"{vote.title(item)}. It will be noticed.",
                  "leak": f"You leaked the {short}'s papers on the "
                          f"{vote.title(item)}."}[act],
                 "warn" if act != "petition" else "")
    return told


def speech(game, key: str) -> dict:
    """What speaking on this motion would swing each power by, if the
    captain is at the seat on the day — {} when they have taken no side."""
    side = assembly.ensure(game).positions.get(key, "")
    if not side:
        return {}
    sign = 1.0 if side == "for" else -1.0
    return {p: round(sign * vote.speech(game, p), 2) for p in dip.POWERS}
