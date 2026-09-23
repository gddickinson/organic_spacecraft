"""Diplomacy's acts: what an overture costs, moves, and is remembered as.

Split out of `sim/diplomacy.py` at 500 lines, along the file's own section
rule. What stays there is the *state* of the Verge's politics — relations
between the powers, treaties, how courting a power tapers, the Concord
condition. What is here is the captain *doing* something about it: which
overtures are open, the dry run the board quotes (`preview`), the refusal
asked before a credit is spent, and the act itself (`perform`), kept side by
side because a forecast that reads a different function from the act is the
bug this project has found more than any other. `diplomacy` re-exports every
name, so `dip.perform` and `dip.preview` answer where they always did.

The helpers that stay in `diplomacy` are imported inside each function:
`diplomacy` imports this module to re-export it, so a module-level import in
this direction is a cycle whichever of the two loads first.
"""

from __future__ import annotations

from ..data.diplomacy import (ACTIONS_BY_ID, BROKER_WEIGHT, DENOUNCE_WEIGHT,
                              TREATY_WEIGHT)
from ..data.factions import FACTIONS_BY_ID
from . import loyalty, stores


def available(game, faction: str, other: str | None = None) -> list[tuple]:
    """(action, ok, reason) for every diplomatic move against this faction.

    `other` is the second party where there is one — whom you would denounce,
    or whom you would broker with. **It has to be here**, because the work's
    own cooldown is keyed on the target rather than the seat you order it
    from (`_work_key`), and a gate that only asked about the seat offered
    moves the act then refused: measured in a play session, *Denounce a
    rival — Concordat* was lit and answered "that ground was worked 0 days
    ago — not for another 90", which is a button doing nothing but saying no.
    """
    from .diplomacy import ensure, has_treaty
    state = ensure(game)
    rep = game.rep.get(faction, 0)
    out = []
    for action in ACTIONS_BY_ID.values():
        ok, why = True, ""
        ready = state.cooldowns.get(f"{action.id}|{faction}", -9999)
        work = _work_key(action.id, faction, other)
        if work is not None:
            ready = max(ready, state.cooldowns.get(work, -9999))
        if game.day < ready:
            ok, why = False, f"Not for another {ready - game.day:.0f} day(s)."
        elif rep < action.min_rep:
            ok, why = False, f"They will not hear it below {action.min_rep:g} standing."
        elif action.id == "treaty" and has_treaty(game, faction):
            ok, why = False, "Already signed."
        elif action.cost_credits and game.credits < action.cost_credits:
            ok, why = False, f"Costs {action.cost_credits:,} credits."
        elif action.cost_goods:
            cid, amount = action.cost_goods
            if stores.held(game, cid) < amount:
                ok, why = False, f"Needs {amount} {cid}."
        out.append((action, ok, why))
    return out


def _merged(rows: list) -> list:
    """One line per power. The screen is read by a person.

    Brokering charges a third party twice over — once as an enemy of each
    principal — and quoting that as two separate lines meant the board
    promised the Freeholds -3.30 and then again -4.90 while the act moved
    them -8.20. Both halves were true and neither was the number.

    (Hoisted: `preview` and `perform` each carried an identical nested copy,
    which is how two doors drift apart.)
    """
    order, total = [], {}
    for who, amount in rows:
        if who not in total:
            order.append(who)
        total[who] = total.get(who, 0.0) + amount
    return [(who, round(total[who], 2)) for who in order]


def preview(game, action_id: str, faction: str,
            other: str | None = None) -> dict:
    """What an overture will move, without moving it.

    The screen listed a cost and never a benefit, so tribute at twelve
    thousand credits for nine points of standing looked the same as relief at
    forty tonnes of biomass for eleven — about six times better per credit.
    And a treaty quietly charged standing with the signatory's enemies, which
    was stated nowhere.
    """
    from . import allegiance
    from .diplomacy import POWERS, courtship, offer_gain, relation

    action = ACTIONS_BY_ID.get(action_id)
    if action is None:
        return {}
    gain = offer_gain(game, action, faction)
    out = {"standing": [], "relations": None, "gain": gain,
           "courtship": courtship(game.rep.get(faction, 0.0))}


    if action_id == "denounce":
        if other is None:
            return out
        out["standing"].append((other, -14.0))
        # Tapered through `courtship` exactly as `perform` pays it — the
        # board must quote the number the act will move.
        for power in POWERS:
            if power != other and relation(game, power, other) < -15:
                out["standing"].append(
                    (power, 6.0 * courtship(game.rep.get(power, 0.0))))
        out["standing"] += [
            (power, -cost) for power, cost
            in allegiance.price_attack(game, other, DENOUNCE_WEIGHT,
                                       except_={faction, other})]
        out["relations"] = (faction, other, -8.0)
        out["standing"] = _merged(out["standing"])
    elif action_id == "broker":
        if other is None:
            return out
        # Each side is thanked according to what it already thinks of you.
        other_gain = offer_gain(game, action, other)
        out["standing"] = [(faction, gain), (other, other_gain)]
        pair = {faction, other}
        out["standing"] += [(power, -cost) for power, cost
                            in allegiance.price(game, faction, BROKER_WEIGHT,
                                                pair)]
        out["standing"] += [(power, -cost) for power, cost
                            in allegiance.price(game, other, BROKER_WEIGHT,
                                                pair)]
        out["relations"] = (faction, other, 28.0)
        out["standing"] = _merged(out["standing"])
    elif action_id == "treaty":
        from . import accord
        out["standing"] = [(faction, gain)]
        # The half nobody was told about.
        out["standing"] += [(power, -cost)
                            for power, cost in allegiance.price(game, faction,
                                               TREATY_WEIGHT)]
        out["standing"] = _merged(out["standing"])
        # And the instrument itself. `perform` reads the same `worth`, so the
        # rows the desk prints and the lines the dialogue prints after signing
        # are the same dry run — the figure cannot be quoted and then not paid.
        out["accord"] = accord.worth(game, faction)
    else:
        # A gift is a public act. Courting one power in front of the power it
        # is losing a war to used to cost exactly nothing — which is why a
        # captain could sit at 100 with all four while two of them were at
        # −67 with each other.
        out["standing"] = [(faction, gain)]
        out["standing"] += [(power, -cost) for power, cost
                            in allegiance.price(game, faction, gain)]
        out["standing"] = _merged(out["standing"])
    return out


def _spend(game, action) -> None:
    if action.cost_credits:
        game.credits -= action.cost_credits
    if action.cost_goods:
        cid, amount = action.cost_goods
        stores.take(game, cid, amount)


def _work_key(action_id: str, faction: str, other: str | None) -> str | None:
    """The cooldown key for the *work*, not the seat it was ordered from.

    Keyed on the initiator alone, a two-party overture could be run again
    the same day from the other seat: brokering the same pair from both
    sides paid double for double the fee with no cooldown at all, and a
    denunciation of one power could be farmed from every court in the
    sector — +18 with three powers, free, repeatable. Brokering B with A
    *is* brokering A with B, and a denunciation is of its target, whoever
    you said it to.

    **The work has its own namespace**, and it did not: the seat's key is
    `f"{action}|{faction}"`, so a denunciation *made at* the Charter's court
    wrote `denounce|charter` — the very key that asks whether the Charter
    may be denounced. Denouncing anybody from a court shut that court off
    as a target for ninety days, from every seat in the sector, for a reason
    no screen could state. Keyed with `@`, the two cannot collide.
    """
    if action_id == "broker" and other:
        return f"{action_id}@{'@'.join(sorted((faction, other)))}"
    if action_id == "denounce" and other:
        return f"{action_id}@{other}"
    return None


def refusal(game, action_id: str, faction: str, other: str | None) -> str:
    """Why this overture cannot be made, or "" if it can — **asked before a
    credit is spent**. Inside `perform` these sat after `_spend` and both
    cooldowns, so a brokerage the third party would not attend cost 20,000
    credits, shut that pair for 150 days, and refused an honest one after.
    """
    from .diplomacy import BROKER_INVITE, offer_gain
    if action_id == "denounce" and other is None:
        return "Denounce whom?"
    # An overture whose whole deliverable is standing, aimed at a ledger with
    # no room left, is refused before it is paid for — the same rule the
    # brokerage learned. Treaty and broker still deliver instruments at the
    # cap, so only the pure-standing family is turned away.
    if action_id in ("tribute", "intelligence", "relief"):
        action = ACTIONS_BY_ID.get(action_id)
        if action is not None and offer_gain(game, action, faction) < 0.5:
            return (f"{FACTIONS_BY_ID[faction].short} could not think "
                    "better of you than they already do.")
    if action_id != "broker":
        return ""
    if other is None:
        return "Broker between whom?"
    if game.rep.get(other, 0) < BROKER_INVITE:
        return (f"{FACTIONS_BY_ID[other].short} would not sit down at "
                "your invitation.")
    return ""


def perform(game, action_id: str, faction: str, other: str | None = None) -> dict:
    """Carry out a diplomatic move. Returns what happened."""
    from . import allegiance
    from .diplomacy import (POWERS, courtship, ensure, offer_gain, relation,
                            shift_relation)

    state = ensure(game)
    action = ACTIONS_BY_ID.get(action_id)
    if action is None:
        return {"ok": False, "why": "No such overture."}
    ok, why = next(((o, w) for a, o, w in available(game, faction, other)
                    if a.id == action_id), (False, "Unavailable."))
    if not ok:
        return {"ok": False, "why": why}
    pair_key = _work_key(action_id, faction, other)
    if pair_key is not None:
        ready = state.cooldowns.get(pair_key, -9999)
        if game.day < ready:
            return {"ok": False,
                    "why": (f"That ground was worked "
                            f"{action.cooldown - (ready - game.day):.0f} "
                            "day(s) ago — not for another "
                            f"{ready - game.day:.0f}.")}

    said = refusal(game, action_id, faction, other)
    if said:
        return {"ok": False, "why": said}
    _spend(game, action)
    state.cooldowns[f"{action_id}|{faction}"] = game.day + action.cooldown
    if pair_key is not None:
        state.cooldowns[pair_key] = game.day + action.cooldown
    lines: list[str] = []
    gain = offer_gain(game, action, faction)


    if action_id == "denounce":
        game.adjust_rep(other, -14)
        # Everyone who dislikes the denounced thinks better of you — through
        # `courtship`, like every other gain. Flat, the +6 was untapered at
        # any standing because denounce's `action.gain` is 0 and only the
        # gain went through the curve — a hole straight past COURTSHIP_FLOOR,
        # the constant added to stop standing being bought at a flat rate.
        for power in POWERS:
            if power == other:
                continue
            if relation(game, power, other) < -15:
                game.adjust_rep(power,
                                6 * courtship(game.rep.get(power, 0.0)))
                lines.append(f"{FACTIONS_BY_ID[power].short} appreciated it.")
        shift_relation(game, faction, other, -8)
        # And whoever is close to them takes it personally. Denouncing a
        # power thanked everyone already at odds with them and charged
        # nobody at all — so in a sector you had spent years pacifying, the
        # loudest act on the board was still free.
        seen = allegiance.charge_attack(game, other, DENOUNCE_WEIGHT,
                                        except_={faction, other})
        if seen:
            lines.append(f"Their friends noticed: {allegiance.phrase(seen)}.")
        if other == "charter":
            loyalty.record(game, "denounce_charter")
        lines.append(f"{FACTIONS_BY_ID[other].short} will remember this.")
    elif action_id == "broker":
        before = relation(game, faction, other)
        after = shift_relation(game, faction, other, 28)
        other_gain = offer_gain(game, action, other)
        game.adjust_rep(faction, gain)
        game.adjust_rep(other, other_gain)
        # Seating two powers at a table is the most public thing on the
        # board, and it was the only act that cost nothing with anybody
        # else — though a third power at odds with both has just watched you
        # end the quarrel it was profiting from. Both principals are exempt:
        # you are not offending either of them by serving the other.
        pair = {faction, other}
        seen = allegiance.charge(game, faction, BROKER_WEIGHT, except_=pair)
        seen += allegiance.charge(game, other, BROKER_WEIGHT, except_=pair)
        lines.append(f"{FACTIONS_BY_ID[faction].short} and "
                     f"{FACTIONS_BY_ID[other].short}: {before:+.0f} → {after:+.0f}.")
        if seen:
            lines.append(f"Noted elsewhere: {allegiance.phrase(seen)}.")
    elif action_id == "treaty":
        from . import accord
        # Quote the instrument before signing it: `shared` is what they hold and
        # you cannot see, and appending the name to `treaties` is what makes the
        # berthing clause bite, so both figures have to be taken from the state
        # this side of the act.
        told = accord.worth(game, faction)
        state.treaties.append(faction)
        loyalty.record(game, "treaty")
        game.adjust_rep(faction, gain)
        # Signing with one power cools you with its enemies — by how much the
        # rift is actually worth, rather than the flat -4 this used to be,
        # which made brokering a war down to a grudge worth nothing.
        allegiance.charge(game, faction, TREATY_WEIGHT)
        # And the two clauses that are not a joke. They were a joke as well
        # until this cycle: the act appended a name to a list and the sentence
        # below promised berthing and charts on the strength of it.
        accord.hand_over(game, faction)
        lines.append("Signed. Berthing, charts, and a clause about the Bloom.")
        lines.append(accord.berth_line(told))
        lines.append(accord.charts_line(told))
    else:
        game.adjust_rep(faction, gain)
        lines.append(f"{FACTIONS_BY_ID[faction].short} standing +{gain:.0f}.")
        # And whoever they are at odds with saw you do it.
        seen = allegiance.charge(game, faction, gain)
        if seen:
            lines.append(f"Noted elsewhere: {allegiance.phrase(seen)}.")

    _remember(game, action_id, action, faction, other)
    game.add_log(f"{action.name} — {FACTIONS_BY_ID[faction].short}.", "good")
    return {"ok": True, "action": action, "lines": lines}


#: What each overture is, as the power on the other end of it remembers it.
_AS_REMEMBERED = {
    "tribute": ("gift", "you paid tribute when you did not have to", 1.0),
    "relief": ("kindness", "you sent relief when we were short", 1.3),
    "intel": ("gift", "you handed over intelligence that was worth having", 1.0),
    "broker": ("alliance", "you sat us down with {other}", 1.4),
    "treaty": ("alliance", "we signed with you", 1.6),
    "denounce": ("betrayal", "you denounced us in open session", 1.5),
}


def _remember(game, action_id: str, action, faction: str,
              other: str | None) -> None:
    """A power remembers the overture, and the target of a denunciation
    remembers it rather better.

    Standing is a number that decays. This is a dated thing an envoy can name,
    and `sim/grudge.py` turns it into a price and into whether they will put
    work your way.
    """
    from . import grudge as grudge_sim
    entry = _AS_REMEMBERED.get(action_id)
    if entry is None:
        return
    kind, text, weight = entry
    named = FACTIONS_BY_ID.get(other or "")
    body = text.format(other=named.short if named else "them")

    if action_id == "denounce":
        # The one that lands on somebody else.
        if other:
            grudge_sim.note(game, other, kind, body, weight,
                            tags=["politics", "denounce"])
        return
    grudge_sim.note(game, faction, kind, body, weight,
                    tags=["politics", action_id])
