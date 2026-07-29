"""Powers coming to you, for reasons drawn from what has actually happened.

`sim/diplomacy.py` runs one way: you spend, standing moves. The powers only
`drift`. So the four of them are a vending machine, and a captain can ignore
the board for twenty years without anyone knocking.

This is the other direction, and the rule it obeys is that **every approach
has to be caused**. A power asks for volatiles because its own quays are short
of volatiles. It asks you to denounce the Freeholds because it is losing to
the Freeholds. It warns you off a rival because you have been carrying that
rival's cargo. Nothing here fires because a die came up; the die only decides
*when*, among reasons that already exist.

An approach is something you can be in the middle of, so it lives on `Game`
with an `.over` flag like a battle or an open trench, and `window.go()` will
not let you wander off mid-conversation.

Three answers, all previewed before you commit: take it, push back for a
better price, or refuse. Letting the window lapse is refusing quietly and
costs the same — an offer with no clock is not a decision, it is a button that
waits forever.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data.approaches import (APPROACHES_BY_ID, ODDS_PER_DAY, QUIET_DAYS)
from ..data.commodities import TRADE_IDS
from ..data.diplomacy import TREATY_WEIGHT
from ..data.factions import FACTIONS_BY_ID
from . import allegiance
from . import diplomacy as dip
from .ship import add_cargo

#: Relation below which a power counts as losing a rivalry badly enough to
#: want it said out loud.
LOSING = -30.0

#: Standing at which a power will propose terms itself.
COURTED = 62.0

#: How much of the posted price a requisition offers. They know it is under.
REQUISITION_SHARE = 0.72


@register
@dataclass
class Envoy:
    """A power's proposition, waiting on an answer."""
    kind: str
    faction: str
    #: The other power involved, for denunciations and warnings.
    rival: str | None = None
    #: What they want, if it is cargo.
    goods: str | None = None
    amount: float = 0.0
    #: What they are paying, or what they are demanding.
    credits: int = 0
    #: The day the offer lapses.
    expires: int = 0
    over: bool = False
    choice: str | None = None
    #: Set once, when the offer is haggled, so it cannot be milked.
    pushed: bool = False
    log: list = field(default_factory=list)

    @property
    def action(self):
        return APPROACHES_BY_ID.get(self.kind)


def _short(faction: str) -> str:
    got = FACTIONS_BY_ID.get(faction)
    return got.short if got else faction.title()


def _market_price(game, commodity: str) -> float:
    """Roughly what a tonne fetches, for pricing a requisition honestly."""
    from ..data.commodities import BY_ID
    got = BY_ID.get(commodity)
    return float(getattr(got, "base", 60) if got else 60)


#: Supply at or below which a quay counts as genuinely short. `Stock.supply`
#: sits near 1.0 in a balanced market and falls as the shelves empty.
SHORT_SUPPLY = 0.8

#: Tonnes you must be carrying before a power bothers asking for it.
MIN_REQUISITION = 4


def _shortage(game, faction: str, aboard: bool = True) -> tuple[str, float] | None:
    """A commodity this power's own space is short of, and how badly.

    Read off the markets in systems it holds, so the ask is caused by the
    economy rather than invented. The first version read a `demand` mapping
    that does not exist on `Market` — it has `stock`, keyed by commodity, with
    a `supply` that falls as the shelves empty. `getattr(..., {})` returned an
    empty dict every time and requisitions could never fire at all.

    Restricted to what is actually in your hold, which is both the flavour —
    "somebody has looked at what you are carrying" — and the only way the ask
    is answerable. Without it every power turned out to be short of
    `wildseed`, which nothing stocks and no captain hauls: a shortage that is
    real in the data and meaningless as a request.
    """
    worst = None
    for system in game.galaxy.systems:
        if system.faction != faction or not system.market:
            continue
        for cid, stock in getattr(system.market, "stock", {}).items():
            if cid not in TRADE_IDS:
                continue
            if aboard and game.ship.cargo.get(cid, 0) < MIN_REQUISITION:
                continue
            supply = float(getattr(stock, "supply", 1.0))
            if supply > SHORT_SUPPLY:
                continue
            if worst is None or supply < worst[1]:
                worst = (cid, supply)
    return worst


def reasons(game, faction: str) -> list:
    """Every live reason this power might have to approach you, best first.

    Returns (kind, rival) pairs. Empty means they have nothing to say, which
    is the normal state of affairs and should stay that way.
    """
    out = []
    rep = game.rep.get(faction, 0)
    if rep < -10:
        return out                       # they are not talking to you at all

    # Losing a rivalry, and would like it said out loud.
    for rival in dip.POWERS:
        if rival == faction:
            continue
        if dip.relation(game, faction, rival) <= LOSING \
                and game.rep.get(rival, 0) > -20:
            out.append(("denounce_rival", rival))
            break

    # You have been useful to somebody they are losing to.
    for rival in dip.POWERS:
        if rival == faction:
            continue
        if (game.rep.get(rival, 0) - rep) >= 30 \
                and dip.relation(game, faction, rival) < -10:
            out.append(("warning", rival))
            break

    # High standing and no treaty: they will propose it themselves.
    if rep >= COURTED and not dip.has_treaty(game, faction):
        out.append(("treaty_offer", None))

    # Their quays are short of something you might be carrying.
    if rep >= 5 and _shortage(game, faction) is not None:
        out.append(("requisition", None))

    # You are working ground inside their declared space.
    if rep >= -5:
        held = [c for c in game.colonies
                if game.galaxy.systems[c.system_id].faction == faction]
        if held:
            out.append(("levy", None))
    return out


def _build(game, faction: str, kind: str, rival: str | None, rng) -> Envoy:
    action = APPROACHES_BY_ID[kind]
    envoy = Envoy(kind=kind, faction=faction, rival=rival,
                  expires=game.day + action.window)
    if kind == "requisition":
        short = _shortage(game, faction)
        cid = short[0] if short else "volatiles"
        envoy.goods = cid
        envoy.amount = min(float(game.ship.cargo.get(cid, 0)),
                           float(rng.int(4, 18)))
        envoy.credits = int(_market_price(game, cid) * envoy.amount
                            * REQUISITION_SHARE)
    elif kind == "denounce_rival":
        envoy.credits = rng.int(1800, 5200)
    elif kind == "levy":
        held = [c for c in game.colonies
                if game.galaxy.systems[c.system_id].faction == faction]
        envoy.credits = 1400 * len(held) + rng.int(0, 900)
    return envoy


def tick(game, days: float, rng) -> list:
    """Does anybody come calling? Returns (kind, text) lines for the log."""
    if days <= 0 or game.dead or game.victory:
        return []
    state = dip.ensure(game)
    live = getattr(game, "envoy", None)
    if live is not None and not live.over:
        if game.day >= live.expires:
            live.over = True
            live.choice = "lapsed"
            _apply_refusal(game, live)
            return [("warn", f"{_short(live.faction)}'s envoy has gone. You "
                             "did not answer, which is an answer.")]
        return []

    quiet = getattr(state, "approached", None)
    if quiet is None:
        state.approached = quiet = {}

    for faction in dip.POWERS:
        if game.day < quiet.get(faction, -9999) + QUIET_DAYS:
            continue
        got = reasons(game, faction)
        if not got:
            continue
        if not rng.chance(min(0.5, ODDS_PER_DAY * days * len(got))):
            continue
        kind, rival = got[0] if len(got) == 1 else rng.pick(got)
        envoy = _build(game, faction, kind, rival, rng)
        game.envoy = envoy
        quiet[faction] = game.day
        return [("", f"{_short(faction)} has sent somebody to put a "
                     f"proposition to you.")]
    return []


def preview(game, envoy, answer: str) -> dict:
    """What each answer will actually do, before it does it."""
    action = envoy.action
    if action is None:
        return {}
    out = {"answer": answer, "rep": {}, "credits": 0, "offer": 0,
           "goods": None, "relations": None, "lines": []}
    if answer == "accept":
        out["rep"][envoy.faction] = action.accept_rep
        if envoy.kind == "requisition":
            out["credits"] = envoy.credits
            out["goods"] = (envoy.goods, -envoy.amount)
            out["lines"].append(
                f"{envoy.amount:g} t of {envoy.goods} off the manifest, "
                f"{envoy.credits:,} credits on.")
        elif envoy.kind == "levy":
            out["credits"] = -envoy.credits
            out["lines"].append(f"{envoy.credits:,} credits paid over.")
        elif envoy.kind == "denounce_rival":
            out["credits"] = envoy.credits
            out["rep"][envoy.rival] = -18.0
            out["relations"] = (envoy.faction, envoy.rival, -6.0)
            out["lines"].append(
                f"{envoy.credits:,} credits, and {_short(envoy.rival)} hears "
                f"every word of it. It also drives {_short(envoy.faction)} "
                f"and {_short(envoy.rival)} six further apart.")
        elif envoy.kind == "treaty_offer":
            out["lines"].append("A treaty signed at their expense — berthing "
                                "rights and a tariff line.")
            for power, cost in allegiance.price(game, envoy.faction,
                                                TREATY_WEIGHT):
                out["rep"][power] = out["rep"].get(power, 0.0) - cost
        elif envoy.kind == "warning":
            out["lines"].append(
                f"The file closes. Taking {_short(envoy.rival)}'s work again "
                "inside a season will reopen it.")
    elif answer == "refuse":
        out["rep"][envoy.faction] = action.refuse_rep
        if envoy.kind == "levy":
            out["lines"].append("They will file it as a grievance, and "
                                "grievances are counted.")
        out["lines"].append(action.costs.format(
            power=_short(envoy.faction),
            rival=_short(envoy.rival) if envoy.rival else "them"))
        if envoy.kind == "denounce_rival" and envoy.rival:
            out["rep"][envoy.rival] = 3.0
    elif answer == "push":
        if envoy.pushed or action.haggle <= 0:
            out["lines"].append("They have said their piece. There is no "
                                "more room in it.")
        else:
            better = int(envoy.credits * action.haggle)
            way = "more" if envoy.kind != "levy" else "less"
            # `offer`, not `credits`: haggling moves what is *on the table*,
            # and nothing reaches the treasury until you accept. This was
            # reported as `credits`, so the screen printed "Treasury: +794"
            # for a push that pays nothing at all.
            out["offer"] = better if envoy.kind != "levy" else -better
            out["rep"][envoy.faction] = -2.0
            out["lines"].append(
                f"{better:,} credits {way}, and they will think slightly "
                "less of you for the asking.")
    return out


def _apply_refusal(game, envoy) -> None:
    action = envoy.action
    if action is None:
        return
    game.adjust_rep(envoy.faction, action.refuse_rep)
    if envoy.kind == "denounce_rival" and envoy.rival:
        game.adjust_rep(envoy.rival, 3.0)
    if envoy.kind == "levy":
        dip.ensure(game).grievances = getattr(
            dip.ensure(game), "grievances", 0) + 1


def answer(game, envoy, choice: str) -> dict:
    """Take it, push back, or refuse. Returns what happened."""
    action = envoy.action
    if action is None or envoy.over:
        return {"ok": False, "why": "There is nobody waiting."}

    if choice == "push":
        if envoy.pushed or action.haggle <= 0:
            return {"ok": False, "why": "They will not move again."}
        better = int(envoy.credits * action.haggle)
        envoy.credits += better if envoy.kind != "levy" else -better
        envoy.credits = max(0, envoy.credits)
        envoy.pushed = True
        game.adjust_rep(envoy.faction, -2.0)
        envoy.log.append("You pushed, and they moved.")
        return {"ok": True, "pushed": True, "credits": envoy.credits}

    if choice == "refuse":
        envoy.over = True
        envoy.choice = "refuse"
        _apply_refusal(game, envoy)
        return {"ok": True, "refused": True}

    if choice != "accept":
        return {"ok": False, "why": "No such answer."}

    # Accepting. Everything here must match `preview` exactly.
    if envoy.kind == "requisition":
        held = game.ship.cargo.get(envoy.goods, 0)
        if held < envoy.amount:
            return {"ok": False,
                    "why": f"You no longer have {envoy.amount:g} t of "
                           f"{envoy.goods} aboard."}
        add_cargo(game.ship, envoy.goods, -envoy.amount)
        game.credits += envoy.credits
    elif envoy.kind == "levy":
        if game.credits < envoy.credits:
            return {"ok": False, "why": "You cannot cover the levy."}
        game.credits -= envoy.credits
    elif envoy.kind == "denounce_rival":
        game.credits += envoy.credits
        if envoy.rival:
            game.adjust_rep(envoy.rival, -18.0)
            dip.shift_relation(game, envoy.faction, envoy.rival, -6.0)
    elif envoy.kind == "treaty_offer":
        dip.ensure(game).treaties.append(envoy.faction)
        # The same instrument, so the same price. Signing one you proposed
        # charged the signatory's enemies and signing one they offered charged
        # nobody, which made waiting to be asked the way to sign for free.
        allegiance.charge(game, envoy.faction, TREATY_WEIGHT)
    elif envoy.kind == "warning" and envoy.rival:
        game.flags[f"warned_off:{envoy.rival}"] = game.day + 180

    game.adjust_rep(envoy.faction, action.accept_rep)
    envoy.over = True
    envoy.choice = "accept"
    game.recompute()
    return {"ok": True, "accepted": True}


def opening(game, envoy) -> str:
    """The envoy's own words, filled from the situation that produced them."""
    action = envoy.action
    if action is None:
        return ""
    return action.opening.format(
        power=_short(envoy.faction),
        rival=_short(envoy.rival) if envoy.rival else "them",
        goods=envoy.goods or "cargo", amount=envoy.amount,
        credits=envoy.credits)


def asking(game, envoy) -> str:
    """One line stating the ask, in the same terms the preview will honour."""
    action = envoy.action
    if action is None:
        return ""
    return action.ask.format(
        power=_short(envoy.faction),
        rival=_short(envoy.rival) if envoy.rival else "them",
        goods=envoy.goods or "cargo", amount=envoy.amount,
        credits=envoy.credits)
