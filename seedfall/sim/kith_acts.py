"""Acts at a Kith gathering: gifts, asking first, debts, a berth, passage and
the accord.

**No posted prices.** A gathering takes a gift from the hold and answers it
by what it thinks of the good (`kith_world.prefs`, hidden): prized, welcome,
plain, or an offence. What the gift is *worth* to it is the good's base price
times `WORTH[reaction]`; it answers in songglass a quarter more generously
than that (`GENEROSITY`), and **the surplus is its own gift, owed back**. The
next gift pays the debt first. A debt left `DEBT_DAYS` becomes an insult.

**Preview equals act.** `preview_gift` and `offer` read one outcome function,
`_outcome`; the preview weighs it over what is *known* of the gathering's
taste — seen in an exchange (certain), told when you asked (as sure as the
telling was), or nothing (the prior every gathering is drawn from) — and
states the chance the gift itself is misread. With a taste seen and nothing
to misread, the preview is the act to the tonne.

Every act that can be misread rolls through `kith.roll` on
`kith.misread_odds`, the same number the screen shows.
"""

from __future__ import annotations

from ..data import kith as data
from ..data.commodities import BY_ID, bulk_of
from . import kith, kith_world as world
from .ship import add_cargo, cargo_free


def _sid(game) -> str:
    return str(game.location_id)


def debt_at(game, sid: str | None = None) -> list:
    """[owed, since day, insulted] at a gathering; [0, day, False] if none."""
    state = kith.ensure(game)
    return list(state.debts.get(sid or _sid(game), [0.0, game.day, False]))


def known(game, cid: str, sid: str | None = None) -> list | None:
    """What the captain knows of this gathering's taste for a good."""
    state = kith.ensure(game)
    return state.known_prefs.get(sid or _sid(game), {}).get(cid)


def belief(game, cid: str) -> dict:
    """Reaction → probability, from what is known here, honestly weighted."""
    said = known(game, cid)
    if said is None:
        return world.prior(cid)
    reaction, source, odds = said
    if source == "seen":
        return {r: float(r == reaction) for r in data.REACTIONS}
    # Told: right with the odds it was heard at, else the prior's shape.
    base = world.prior(cid)
    return {r: (1.0 - odds) * float(r == reaction) + odds * base[r]
            for r in data.REACTIONS}


def _outcome(game, sid: str, value: float, reaction: str) -> dict:
    """What one gift of `value` does, answered as `reaction`. Pure."""
    state = kith.ensure(game)
    owed, since, insulted = state.debts.get(sid, [0.0, game.day, False])
    worth = value * data.WORTH[reaction]
    paid = min(owed, worth)
    answered = (worth - paid) * data.GENEROSITY
    left = owed - paid + (answered - (worth - paid))
    thanked = state.thanked.get(sid)
    rep = 0.0
    if reaction == "offended":
        rep = data.OFFENCE_STANDING
    elif thanked is None or game.day - thanked >= data.GIFT_STANDING_DAYS:
        # Regard, and a debt cleared, count once in `GIFT_STANDING_DAYS` at a gathering:
        # measured, a debt-paid point on every gift made standing a matter
        # of splitting one hold into four gifts (+52 in 80 days at one).
        rep = min(data.GIFT_STANDING_CAP, worth / data.GIFT_STANDING_PER)
        if owed > 0 and paid >= owed - 1e-9:
            rep += data.DEBT_PAID_STANDING
    base = BY_ID[data.SONGGLASS].base
    return {"reaction": reaction, "worth": round(worth, 2),
            "paid": round(paid, 2), "answered": round(answered, 2),
            "songglass": round(answered / base, 2), "debt": round(left, 2),
            "standing": round(rep, 2)}


def preview_gift(game, cid: str, tonnes: float) -> dict:
    """What offering this would do: each reaction's outcome, weighted by what
    is known here, and the stated chance the gift is misread outright."""
    ok, why = kith.can(game, "gift")
    have = float(game.ship.cargo.get(cid, 0.0))
    tonnes = max(0.0, min(float(tonnes), have))
    if ok and tonnes <= 0:
        ok, why = False, "None of that aboard."
    good = BY_ID.get(cid)
    if ok and good is None:
        ok, why = False, f"No such good: {cid}."
    value = tonnes * (good.base if good else 0)
    sid = _sid(game)
    weights = belief(game, cid) if good else {}
    odds = kith.misread_odds(game, "gift") if ok else 0.0
    outcomes = {r: _outcome(game, sid, value, r) for r in data.REACTIONS
                if weights.get(r, 0.0) > 0}
    clean = 1.0 - odds
    expect = {key: round(sum(clean * weights[r] * outcomes[r][key]
                             for r in outcomes), 2)
              for key in ("worth", "songglass", "standing", "paid")}
    expect["standing"] = round(expect["standing"]
                               + odds * data.MISREAD_STANDING, 2)
    said = known(game, cid)
    return {"ok": ok, "why": why, "cid": cid, "tonnes": tonnes,
            "value": round(value, 2), "weights": weights,
            "outcomes": outcomes, "misread": odds,
            "fight": round(odds * data.FIGHT_SHARE, 4), "expect": expect,
            "source": said[1] if said else "", "debt": debt_at(game)}


def _collect(game, sid: str) -> float:
    """Take on whatever songglass this gathering kept for a full hold."""
    state = kith.ensure(game)
    kept = float(state.held.get(sid, 0.0))
    if kept <= 0:
        return 0.0
    room = cargo_free(game.ship, game.ship_stats) / bulk_of(data.SONGGLASS)
    take = round(min(kept, room), 2)
    if take > 0:
        add_cargo(game.ship, data.SONGGLASS, take)
    if kept - take > 1e-6:
        state.held[sid] = round(kept - take, 2)
    else:
        state.held.pop(sid, None)
    return take


def offer(game, cid: str, tonnes: float) -> dict:
    """Hand a gift from the hold to the gathering here, and take its answer."""
    said = preview_gift(game, cid, tonnes)
    if not said["ok"]:
        return {"ok": False, "why": said["why"]}
    state = kith.ensure(game)
    sid, tonnes = _sid(game), said["tonnes"]
    collected = _collect(game, sid)
    add_cargo(game.ship, cid, -tonnes)
    name = game.system.port.name
    if kith.roll(game, said["misread"]):
        game.adjust_rep(data.FACTION, data.MISREAD_STANDING)
        text = (f"{name} read the gift of {tonnes:g} t {BY_ID[cid].short} "
                "as something else entirely. It is gone, and so is some of "
                "their regard.")
        game.add_log(text, "bad")
        kith.note(state, game.day, "misread", text)
        out = {"ok": True, "misread": True, "tonnes": tonnes,
               "standing": data.MISREAD_STANDING, "collected": collected}
        if kith.roll(game, data.FIGHT_SHARE):
            out["encounter"] = kith.fight(game, "The gift was read as a "
                                                "threat.")
        return out
    reaction = world.prefs(game.galaxy, game.system)[cid]
    got = _outcome(game, sid, said["value"], reaction)
    game.adjust_rep(data.FACTION, got["standing"])
    if got["standing"] > 0 and reaction != "offended":
        state.thanked[sid] = int(game.day)
    if got["debt"] > 1e-6:
        owed = state.debts.get(sid, [0.0, game.day, False])
        # A fresh surplus restarts the wait; an old insult stays an insult.
        since = game.day if got["paid"] >= owed[0] - 1e-9 else owed[1]
        state.debts[sid] = [got["debt"], int(since), bool(owed[2])
                            and got["paid"] < owed[0] - 1e-9]
    else:
        state.debts.pop(sid, None)
    state.given[sid] = state.given.get(sid, 0.0) + got["worth"]
    state.known_prefs.setdefault(sid, {})[cid] = [reaction, "seen", 0.0]
    state.exchanges += 1
    spoken = list(data.SPOKEN[reaction])
    if got["paid"] > 0:
        spoken += data.SPOKEN["debt"]
    for sign in dict.fromkeys(spoken):
        kith.teach(state, sign, data.EXCHANGE_TEACH)
    room = cargo_free(game.ship, game.ship_stats) / bulk_of(data.SONGGLASS)
    aboard = round(min(got["songglass"], room), 2)
    if aboard > 0:
        add_cargo(game.ship, data.SONGGLASS, aboard)
    if got["songglass"] - aboard > 1e-6:
        state.held[sid] = round(state.held.get(sid, 0.0)
                                + got["songglass"] - aboard, 2)
    text = (f"{name} took {tonnes:g} t {BY_ID[cid].short} as {reaction} and "
            f"answered with {got['songglass']:g} t of songglass.")
    game.add_log(text, "warn" if reaction == "offended" else "good")
    kith.note(state, game.day, reaction, text)
    out = {"ok": True, "misread": False, **got, "tonnes": tonnes,
           "aboard": aboard, "collected": collected}
    out["graft"] = _graft(game, sid)
    return out


def _graft(game, sid: str) -> str:
    """A gathering given enough grows you the graft it grows. Its part id."""
    graft = world.graft_of(game.galaxy, game.system)
    unlocked = game.research.unlocked
    if (graft is None or graft.gate in unlocked
            or kith.ensure(game).given.get(sid, 0.0) < data.GRAFT_AT
            or kith.standing(game) < data.TOLERATED):
        return ""
    unlocked.append(graft.gate)
    game.recompute()
    from ..data.parts import part
    text = (f"{game.system.port.name} gives you the growing of a "
            f"{part(graft.part).name}: any nursery can now graft one to a "
            "grown hull.")
    game.add_log(text, "good")
    kith.note(game.kith, game.day, "graft", text)
    return graft.part


def ask(game, cid: str) -> dict:
    """"More?" — ask what the gathering thinks of a good before giving it.

    Answered once per good: asked again, they sing the same answer. The
    answer can be misheard, at the stated odds, and you will not know it.
    """
    ok, why = kith.can(game, "ask")
    if ok and debt_at(game)[2]:
        ok, why = False, "They will not answer a hand that owes them."
    if ok and known(game, cid) is not None:
        ok, why = False, "You already know what they think of it."
    if ok and cid not in BY_ID:
        ok, why = False, f"No such good: {cid}."
    if not ok:
        return {"ok": False, "why": why}
    state = kith.ensure(game)
    odds = kith.misread_odds(game, "ask")
    truth = world.prefs(game.galaxy, game.system)[cid]
    heard = truth
    if kith.roll(game, odds):
        order = data.REACTIONS
        heard = order[(order.index(truth) + 1) % len(order)]
    state.known_prefs.setdefault(_sid(game), {})[cid] = [heard, "told", odds]
    for sign in data.SPOKEN["ask"]:
        kith.teach(state, sign, data.EXCHANGE_TEACH / 2)
    return {"ok": True, "heard": heard, "odds": odds}


def come_due(game) -> list:
    """Debts left too long become insults. Called by `kith.tick`."""
    state = getattr(game, "kith", None)
    out = []
    for sid, (owed, since, insulted) in list(state.debts.items()) \
            if state is not None else []:
        if insulted or owed <= 0 or game.day - since < data.DEBT_DAYS:
            continue
        state.debts[sid] = [owed, since, True]
        game.adjust_rep(data.FACTION, data.INSULT_STANDING)
        name = game.galaxy.systems[int(sid)].port.name
        text = (f"{name} has waited {data.DEBT_DAYS} days for its gift to be "
                "answered. The silence is an insult now.")
        game.add_log(text, "bad")
        kith.note(state, game.day, "insult", text)
        out.append(sid)
    return out


# ── asking for more than a gift ────────────────────────────────────────────

def preview_ask(game, act: str) -> dict:
    """A berth, passage or the accord: may it be asked, and at what odds."""
    ok, why = kith.can(game, act)
    if ok and act != "accord" and debt_at(game)[2]:
        ok, why = False, "They will not hear a hand that owes them."
    odds = kith.misread_odds(game, act) if kith.met(game) else 0.0
    return {"ok": ok, "why": why, "act": act, "misread": odds,
            "fight": round(odds * data.FIGHT_SHARE, 4),
            "days": data.BERTH_DAYS if act == "berth" else 0,
            "standing": kith.standing(game)}


def _misread(game, act: str, said: dict) -> dict | None:
    if not kith.roll(game, said["misread"]):
        return None
    game.adjust_rep(data.FACTION, data.MISREAD_STANDING)
    text = f"The request for {act} was misread. They pull away."
    game.add_log(text, "bad")
    kith.note(game.kith, game.day, "misread", text)
    out = {"ok": True, "misread": True, "standing": data.MISREAD_STANDING}
    if kith.roll(game, data.FIGHT_SHARE):
        out["encounter"] = kith.fight(game, f"The request for {act} was "
                                            "heard as a demand.")
    return out


def berth(game) -> dict:
    """The colony closes round the hull and tends it: whole again, and a
    crew that has slept among lights."""
    said = preview_ask(game, "berth")
    if not said["ok"]:
        return {"ok": False, "why": said["why"]}
    wrong = _misread(game, "a berth", said)
    if wrong is not None:
        return wrong
    game.advance_days(said["days"])
    ship = game.ship
    mended = sum(layer.max - layer.hp for layer in ship.layers)
    for layer in ship.layers:
        layer.hp = layer.max
    ship.disabled = []
    ship.morale = max(ship.morale, 0.8)
    game.recompute()
    text = (f"{said['days']} days in the arms of {game.system.port.name}: "
            "the hull is whole, and the crew slept.")
    game.add_log(text, "good")
    kith.note(game.kith, game.day, "berth", text)
    return {"ok": True, "misread": False, "days": said["days"],
            "mended": round(mended, 1)}


def passage(game) -> dict:
    """They sing the way to every gathering. On the chart from now on."""
    said = preview_ask(game, "passage")
    if not said["ok"]:
        return {"ok": False, "why": said["why"]}
    wrong = _misread(game, "passage", said)
    if wrong is not None:
        return wrong
    state = game.kith
    told = []
    for system in world.gatherings(game.galaxy):
        if system.id not in state.charted:
            state.charted.append(system.id)
            told.append(system.name)
        if system.id not in game.discovered["systems"]:
            game.discovered["systems"].append(system.id)
    text = ("They sing you the way to every gathering: "
            + (", ".join(told) if told else "you knew them all") + ".")
    game.add_log(text, "good")
    kith.note(state, game.day, "passage", text)
    return {"ok": True, "misread": False, "told": told}


def sign_accord(game) -> dict:
    """The accord: sung once, at a gathering, with every domain understood."""
    said = preview_ask(game, "accord")
    if not said["ok"]:
        return {"ok": False, "why": said["why"]}
    wrong = _misread(game, "an accord", said)
    if wrong is not None:
        return wrong
    from . import comms
    state = game.kith
    state.accord, state.pilot = int(game.day), 1
    if data.ACCORD_GATE not in game.research.unlocked:
        game.research.unlocked.append(data.ACCORD_GATE)
    game.adjust_rep(data.FACTION, 10.0)
    game.recompute()
    text = (f"An accord with the Kith, sung at {game.system.port.name}. Their "
            "gatherings will grow you a hull of their own, and one of them "
            "asks to fly with you.")
    game.add_log(text, "good")
    kith.note(state, game.day, "accord", text)
    comms.send(game, "kith:accord", "The Kith", "personal", "The accord",
               text)
    return {"ok": True, "misread": False, "day": state.accord}


def take_pilot(game) -> dict:
    """Sign on the Kith pilot the accord offered."""
    from ..core.rng import RNG
    from . import crew
    state = kith.ensure(game)
    if state.pilot != 1:
        return {"ok": False, "why": ("No Kith has asked to fly with you."
                                     if state.pilot == 0 else
                                     "The Kith pilot is already aboard.")}
    rng = RNG(f"{game.seed}:kith:pilot")
    officer = crew.make_officer(rng, data.PILOT_ROLE, data.PILOT_LEVEL)
    officer.name = rng.pick(data.PILOT_NAMES)
    officer.lineage, officer.age = data.PILOT_LINEAGE, 20.0
    officer.role_name = "Kith pilot"
    ok, why = crew.can_hire(game, officer)
    if not ok:
        return {"ok": False, "why": why}
    got = crew.hire(game, officer)
    state.pilot = 2
    game.recompute()
    return got
