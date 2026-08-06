"""The way back. Every legal system needs one, and this one has four.

A governance layer with no exit is not a governance layer, it is an ending on
a delay. So there are four doors out, and they are deliberately not equally
open to everybody:

- **Pay.** Discharge the debt a conviction created and the instrument it
  bought lifts itself. This is the ordinary road and the only one that needs
  nothing but money.
- **Buy a pardon.** Through a harbourmaster, with regard — `sim/officials` is
  already the game's corruption layer and its own docstring says what it
  sells: *discretion — a search not run, a berth for a captain whose standing
  does not merit one*. A pardon is the same commodity one size up.
- **Wait.** Nothing prescribes once it has been *filed*, but an interdict is
  reviewed, and a power that has stopped caring lets it lapse.
- **Treaty.** An amnesty is a clause. `sim/accord` has always had exactly two
  real clauses and a joke; this is a third real one, and it is the reason a
  captain deep in trouble with one power might suddenly want very badly to be
  friends with it.

`settled_up` is the load-bearing one and it is called from the clock: an
instrument whose debt is paid must lift *itself*, or the captain pays a fine
and stays interdicted for ever because nobody thought to check.
"""

from __future__ import annotations

from ..data.factions import FACTIONS_BY_ID
from . import law as law_sim

#: What a pardon costs, per point of outstanding exposure, in regard with the
#: harbourmaster who arranges it. Steep: this is the fast road and it should
#: cost a relationship you spent a chronicle building.
REGARD_PER_EXPOSURE = 26.0

#: And in money, per point.
CREDITS_PER_EXPOSURE = 14_000.0

#: A harbourmaster below this will not touch it at all.
NEEDS_REGARD = 55.0

#: Days an interdict stands before a power will consider letting it lapse.
REVIEW_DAYS = 720.0


def settled_up(game) -> list:
    """Lift every instrument whose debt has been discharged. From the clock.

    The one door for "you have paid, so it stops". Warrants do not each watch
    their own debt: they would each have to, and one of them would forget.
    """
    out: list = []
    state = law_sim.ensure(game)
    from . import warrants as warrants_sim
    for warrant in warrants_sim.in_force(game):
        if warrant.charge_id < 0:
            continue
        owing = [d for d in state.debts
                 if d.charge_id == warrant.charge_id and not d.settled]
        if owing:
            continue
        charge = law_sim.charge_by_id(game, warrant.charge_id)
        if charge is None or charge.sanction in ("", "fine"):
            continue
        # A bounty is not lifted by paying the fine that started it: the paper
        # is out there and somebody bought it. That one needs `settle_bounty`.
        if warrant.bite == "hunt":
            continue
        warrants_sim.lift(game, warrant, "discharged")
        who = FACTIONS_BY_ID.get(warrant.power)
        out.append(("", f"{who.short if who else warrant.power}: the matter "
                        "is discharged and the instrument is lifted."))
    return out


def settle_bounty(game, power: str) -> dict:
    """Buy back the paper on your own hull. Always available, always dear.

    The Freeholds' whole character: there is nobody to acquit you and nobody
    to appeal to, but there is always somebody who will take money.
    """
    from . import warrants as warrants_sim
    posted = [w for w in warrants_sim.in_force(game, power)
              if w.bite == "hunt"]
    if not posted:
        return {"ok": False, "why": "There is nothing posted."}
    price = round(sum(w.price for w in posted) * 1.35, -2)
    if game.credits < price:
        return {"ok": False,
                "why": f"Buying it back is ₡{price:,.0f} and you have "
                       f"₡{game.credits:,.0f}."}
    game.credits -= price
    for warrant in posted:
        warrants_sim.lift(game, warrant, "bought back")
    who = FACTIONS_BY_ID.get(power)
    return {"ok": True, "paid": price,
            "said": (f"Bought back for ₡{price:,.0f}. Whoever held it is "
                     "content, and nobody is coming."),
            "lines": [("", f"{who.short if who else power}: the price on "
                           "your hull has been bought back.")]}


def pardon_price(game, power: str) -> dict:
    """What a pardon would cost here. Quoted before it is asked for."""
    from . import dockets
    exposure = dockets.exposure(game, power)
    from . import warrants as warrants_sim
    for warrant in warrants_sim.in_force(game, power):
        exposure += 0.5
    return {"exposure": round(exposure, 2),
            "regard": round(REGARD_PER_EXPOSURE * max(0.5, exposure), 1),
            "credits": round(CREDITS_PER_EXPOSURE * max(0.5, exposure), -2)}


def can_pardon(game, system, power: str) -> tuple[bool, str]:
    """Will this harbourmaster arrange it, and can you pay for it?"""
    from . import officials as officials_sim
    from . import wharfage
    if wharfage.holder(game, system) != power:
        who = FACTIONS_BY_ID.get(power)
        return False, (f"This is not a {who.short if who else power} counter. "
                       "It has to be asked at one of theirs.")
    price = pardon_price(game, power)
    if price["exposure"] <= 0:
        return False, "There is nothing to forgive."
    regard = officials_sim.regard(game, system)
    if regard < NEEDS_REGARD:
        return False, (f"They would have to know you a great deal better. "
                       f"({regard:.0f} of {NEEDS_REGARD:.0f})")
    if regard < price["regard"]:
        return False, (f"This is worth more regard than you have here: "
                       f"{price['regard']:.0f} against {regard:.0f}.")
    if game.credits < price["credits"]:
        return False, (f"The fees come to ₡{price['credits']:,.0f} and you "
                       f"have ₡{game.credits:,.0f}.")
    return True, (f"₡{price['credits']:,.0f} and {price['regard']:.0f} of "
                  "what they think of you.")


def pardon(game, system, power: str) -> dict:
    """Have it all go away, at a harbourmaster's discretion."""
    ok, why = can_pardon(game, system, power)
    if not ok:
        return {"ok": False, "why": why}
    from . import officials as officials_sim
    from . import warrants as warrants_sim
    price = pardon_price(game, power)
    game.credits -= price["credits"]
    officials_sim.adjust(game, system, -price["regard"],
                         "a matter made to go away")
    wiped = _wipe(game, power)
    warrants_sim.lift_for(game, power)
    who = FACTIONS_BY_ID.get(power)
    short = who.short if who else power
    return {"ok": True, "wiped": wiped, "paid": price["credits"],
            "said": (f"{wiped} matter(s) closed. Nothing is explained and "
                     "nothing is written down."),
            "lines": [("", f"{short}: the file is closed. Somebody at this "
                           "office owed somebody a favour.")]}


def _wipe(game, power: str) -> int:
    """Close every open charge with a power. Returns how many."""
    closed = 0
    for charge in law_sim.open_charges(game, power):
        charge.state = "closed"
        charge.outcome = "pardoned"
        charge.verdict = "Closed without explanation."
        closed += 1
    return closed


def amnesty(game, power: str) -> list:
    """A treaty clause: the slate, wiped. Once per treaty. From `sim/accord`."""
    state = law_sim.ensure(game)
    if state.amnesty.get(power):
        return []
    from . import warrants as warrants_sim
    wiped = _wipe(game, power)
    lifted = warrants_sim.lift_for(game, power)
    for debt in state.debts:
        if debt.creditor == power and debt.kind != "bond":
            debt.settled = True
    if not (wiped or lifted):
        return []
    state.amnesty[power] = float(game.day)
    who = FACTIONS_BY_ID.get(power)
    return [("", f"{who.short if who else power}: the treaty carries an "
                 f"amnesty. {wiped} matter(s) and {lifted} instrument(s) "
                 "gone with the signing.")]


def tick(game, days: float, rng) -> list:
    """Instruments lapsing, debts discharging them, and treaties forgiving.

    **The amnesty is claimed here rather than at each place a treaty can be
    signed.** There are two of those (`diplomacy.perform` and an envoy's
    `approach`) and there was no reason to believe there would not be a
    third; `amnesty` is idempotent per power, so asking every tick is both
    cheaper and harder to get wrong than remembering to call it.
    """
    out = list(settled_up(game))
    from . import diplomacy as dip_sim
    for power in list(dip_sim.ensure(game).treaties):
        out.extend(amnesty(game, power))
    from . import warrants as warrants_sim
    for warrant in warrants_sim.in_force(game):
        if warrant.bite in ("hunt", "bond"):
            continue
        if float(game.day) - warrant.since < REVIEW_DAYS:
            continue
        # They have stopped caring. Standing is what decides it, because a
        # power that has warmed to you since is the one that stops looking.
        if float(game.rep.get(warrant.power, 0.0)) < 0:
            continue
        if not rng.chance(0.25):
            continue
        warrants_sim.lift(game, warrant, "lapsed")
        who = FACTIONS_BY_ID.get(warrant.power)
        out.append(("", f"{who.short if who else warrant.power}: nobody has "
                        "renewed the instrument against you. It has lapsed."))
    return out
