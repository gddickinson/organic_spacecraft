"""Diplomacy — actions, treaties, and how the powers regard one another.

Your standing with a faction is one axis. The other is how the factions feel
about each other, which you can move by taking sides, by brokering, and by being
seen to be worth listening to. Concord requires both.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data.diplomacy import (BROKER_WEIGHT, DENOUNCE_WEIGHT, TREATY_WEIGHT,
                              ACTIONS_BY_ID, AGENDAS,
                              CONCORD_RELATION, CONCORD_STANDING,
                              COURTSHIP_FALLOFF, COURTSHIP_FLOOR,
                              COURTSHIP_KNEE,
                              INITIAL_RELATIONS, RELATION_BANDS)
from ..data.factions import FACTIONS_BY_ID
from . import loyalty

POWERS = ("charter", "concordat", "freeholds", "sanhedrin")


@register
@dataclass
class DiplomaticState:
    relations: dict[str, float] = field(default_factory=dict)
    treaties: list[str] = field(default_factory=list)
    cooldowns: dict[str, int] = field(default_factory=dict)   # "action|faction" -> day
    #: `favours` used to sit here, read by nobody: the favours the game
    #: actually keeps are per-official, in `officials._store(...)["favours"]`,
    #: and it was that unrelated dict which made the declared-field guard
    #: excuse this one for a whole cycle.


def _key(a: str, b: str) -> str:
    return "|".join(sorted((a, b)))


def ensure(game) -> DiplomaticState:
    """Created on first use so existing saves keep working."""
    if getattr(game, "diplomacy", None) is None:
        state = DiplomaticState()
        for (a, b), value in INITIAL_RELATIONS.items():
            state.relations[_key(a, b)] = float(value)
        game.diplomacy = state
    return game.diplomacy


# ── relations between the powers ───────────────────────────────────────────

def relation(game, a: str, b: str) -> float:
    return ensure(game).relations.get(_key(a, b), 0.0)


def shift_relation(game, a: str, b: str, delta: float) -> float:
    state = ensure(game)
    k = _key(a, b)
    state.relations[k] = max(-100.0, min(100.0, state.relations.get(k, 0.0) + delta))
    return state.relations[k]


def relation_band(value: float) -> tuple[str, str]:
    out = RELATION_BANDS[0]
    for band in RELATION_BANDS:
        if value >= band[0]:
            out = band
    return out[1], out[2]


def drift(game, days: float) -> None:
    """Grievances fade toward where the sector rests.

    Without this the powers ratchet one way: every blockade and censure is a
    permanent debit, and a decade of background politics quietly forecloses
    the Concord ending no matter what the player does. Events still dominate
    over any short period — this only pulls at what nobody is maintaining.
    """
    state = ensure(game)
    for (a, b), base in INITIAL_RELATIONS.items():
        key = _key(a, b)
        value = state.relations.get(key)
        if value is None:
            continue
        state.relations[key] = value + (base - value) * min(0.5, 0.00035 * days)


def courtship(rep: float) -> float:
    """What an overture is worth to a power that already thinks well of you.

    Full value while they barely know you, tapering as they come to regard
    you as Kin. Diplomacy had no diminishing return of any kind: the same
    forty tonnes of biomass moved a power at 95 exactly as far as one at 0,
    so standing was a commodity bought at a flat rate and the Concord — the
    sector's whole political condition — could be shopped for in two years
    without leaving port.
    """
    if rep <= COURTSHIP_KNEE:
        return 1.0
    span = 100.0 - COURTSHIP_KNEE
    reached = min(1.0, (rep - COURTSHIP_KNEE) / span)
    return max(COURTSHIP_FLOOR, (1.0 - reached) ** COURTSHIP_FALLOFF)


def offer_gain(game, action, faction: str) -> float:
    """The standing an overture actually buys — the one place this is decided.

    `preview` and `perform` each carried their own copy of this expression,
    which is the arrangement that has produced a free treaty, an ungranted
    favour and a phantom haggle payment in this file's history.
    """
    base = action.gain * (1 + game.ship_stats.diplomacy)
    return base * courtship(game.rep.get(faction, 0.0))


def rivals_of(game, faction: str) -> list[str]:
    """Powers this one is currently on bad terms with."""
    return [p for p in POWERS
            if p != faction and relation(game, faction, p) < -15]


# ── treaties ───────────────────────────────────────────────────────────────

def has_treaty(game, faction: str) -> bool:
    return faction in ensure(game).treaties


def treaty_bonus(game) -> float:
    """Signed treaties make everyone slightly easier to trade with."""
    return 0.03 * len(ensure(game).treaties)


# ── acting ─────────────────────────────────────────────────────────────────

def available(game, faction: str) -> list[tuple]:
    """(action, ok, reason) for every diplomatic move against this faction."""
    state = ensure(game)
    rep = game.rep.get(faction, 0)
    out = []
    for action in ACTIONS_BY_ID.values():
        ok, why = True, ""
        ready = state.cooldowns.get(f"{action.id}|{faction}", -9999)
        if game.day < ready:
            ok, why = False, f"Not for another {ready - game.day} day(s)."
        elif rep < action.min_rep:
            ok, why = False, f"They will not hear it below {action.min_rep:g} standing."
        elif action.id == "treaty" and has_treaty(game, faction):
            ok, why = False, "Already signed."
        elif action.cost_credits and game.credits < action.cost_credits:
            ok, why = False, f"Costs {action.cost_credits:,} credits."
        elif action.cost_goods:
            cid, amount = action.cost_goods
            held = game.ship.cargo.get(cid, 0) + game.stores.get(cid, 0)
            if held < amount:
                ok, why = False, f"Needs {amount} {cid}."
        out.append((action, ok, why))
    return out


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

    action = ACTIONS_BY_ID.get(action_id)
    if action is None:
        return {}
    gain = offer_gain(game, action, faction)
    out = {"standing": [], "relations": None, "gain": gain,
           "courtship": courtship(game.rep.get(faction, 0.0))}

    def _merged(rows: list) -> list:
        """One line per power. The screen is read by a person.

        Brokering charges a third party twice over — once as an enemy of each
        principal — and quoting that as two separate lines meant the board
        promised the Freeholds -3.30 and then again -4.90 while the act moved
        them -8.20. Both halves were true and neither was the number.
        """
        order, total = [], {}
        for who, amount in rows:
            if who not in total:
                order.append(who)
            total[who] = total.get(who, 0.0) + amount
        return [(who, round(total[who], 2)) for who in order]

    if action_id == "denounce":
        if other is None:
            return out
        out["standing"].append((other, -14.0))
        for power in POWERS:
            if power != other and relation(game, power, other) < -15:
                out["standing"].append((power, 6.0))
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
        from_ship = min(game.ship.cargo.get(cid, 0), amount)
        if from_ship:
            game.ship.cargo[cid] = game.ship.cargo.get(cid, 0) - from_ship
            if game.ship.cargo[cid] <= 0.0001:
                game.ship.cargo.pop(cid, None)
        rest = amount - from_ship
        if rest > 0:
            game.stores[cid] = max(0.0, game.stores.get(cid, 0) - rest)


def perform(game, action_id: str, faction: str, other: str | None = None) -> dict:
    """Carry out a diplomatic move. Returns what happened."""
    from . import allegiance

    state = ensure(game)
    action = ACTIONS_BY_ID.get(action_id)
    if action is None:
        return {"ok": False, "why": "No such overture."}
    ok, why = next(((o, w) for a, o, w in available(game, faction)
                    if a.id == action_id), (False, "Unavailable."))
    if not ok:
        return {"ok": False, "why": why}

    _spend(game, action)
    state.cooldowns[f"{action_id}|{faction}"] = game.day + action.cooldown
    lines: list[str] = []
    gain = offer_gain(game, action, faction)

    def _merged(rows: list) -> list:
        """One line per power. The screen is read by a person.

        Brokering charges a third party twice over — once as an enemy of each
        principal — and quoting that as two separate lines meant the board
        promised the Freeholds -3.30 and then again -4.90 while the act moved
        them -8.20. Both halves were true and neither was the number.
        """
        order, total = [], {}
        for who, amount in rows:
            if who not in total:
                order.append(who)
            total[who] = total.get(who, 0.0) + amount
        return [(who, round(total[who], 2)) for who in order]

    if action_id == "denounce":
        if other is None:
            return {"ok": False, "why": "Denounce whom?"}
        game.adjust_rep(other, -14)
        # Everyone who dislikes the denounced thinks better of you.
        for power in POWERS:
            if power == other:
                continue
            if relation(game, power, other) < -15:
                game.adjust_rep(power, 6)
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
        if other is None:
            return {"ok": False, "why": "Broker between whom?"}
        if game.rep.get(other, 0) < 40:
            return {"ok": False, "why": f"{FACTIONS_BY_ID[other].short} would not "
                                        "sit down at your invitation."}
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
    def _merged(rows: list) -> list:
        """One line per power. The screen is read by a person.

        Brokering charges a third party twice over — once as an enemy of each
        principal — and quoting that as two separate lines meant the board
        promised the Freeholds -3.30 and then again -4.90 while the act moved
        them -8.20. Both halves were true and neither was the number.
        """
        order, total = [], {}
        for who, amount in rows:
            if who not in total:
                order.append(who)
            total[who] = total.get(who, 0.0) + amount
        return [(who, round(total[who], 2)) for who in order]

    if action_id == "denounce":
        # The one that lands on somebody else.
        if other:
            grudge_sim.note(game, other, kind, body, weight,
                            tags=["politics", "denounce"])
        return
    grudge_sim.note(game, faction, kind, body, weight,
                    tags=["politics", action_id])


def agenda_bonus(game, faction: str, commodity: str) -> float:
    """Selling a power what it is chronically short of is worth extra standing."""
    agenda = AGENDAS.get(faction)
    return 1.6 if agenda and agenda.wants == commodity else 1.0


# ── the Concord condition ──────────────────────────────────────────────────

def concord_progress(game) -> dict:
    """Kin with four powers, and those powers not at each other's throats."""
    kin = [p for p in POWERS if game.rep.get(p, 0) >= CONCORD_STANDING]
    pairs = [(a, b) for i, a in enumerate(POWERS) for b in POWERS[i + 1:]]
    at_peace = [(a, b) for a, b in pairs if relation(game, a, b) >= CONCORD_RELATION]
    return {"kin": kin, "kin_need": len(POWERS),
            "peace": at_peace, "peace_need": len(pairs),
            "done": len(kin) == len(POWERS) and len(at_peace) == len(pairs)}


def summary(game) -> dict:
    state = ensure(game)
    return {"treaties": list(state.treaties),
            "relations": {f"{a}|{b}": relation(game, a, b)
                          for i, a in enumerate(POWERS) for b in POWERS[i + 1:]}}
