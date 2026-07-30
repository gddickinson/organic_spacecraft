"""What the people aboard consume, which is not the same thing for all of them.

The opening screen sells you a **Dry Choir** lineage on one promise: *"no air
to run out of, no morale to lose."* The daily tick then ran the same block for
everybody — the intima made air, the air ran down when it was breached, and
when it hit zero it killed eight percent of your crew a day whether or not a
single one of them had lungs. A recording suffocated on schedule. That is the
defect this project keeps finding, in its purest form: a screen promising a
consequence the simulation never read.

So consumption is per lineage now, and it is drawn from commodities the
economy already trades — deliberately, because an upkeep bill payable in a
currency nobody sells is not a decision, it is a tax.

- **Wet** crew eat biomass and breathe what the intima makes.
- **Grafted** crew eat rather less and want magnetite for the seams.
- **Dry Choir** recordings eat nothing, breathe nothing, and want silicon and
  magnetite to keep rewriting themselves — and a real slice of the power
  budget, which is the thing that actually constrains them.
- **Xenoforms** want volatiles, and a trace of xenolith nobody can explain.

Running short is not instant death. `shortfall` accumulates, and what it costs
depends on what is missing: a wet crew that has not eaten loses morale and then
people; a dry lineage short of metals loses *levels*, because what degrades is
the copy. Both are slow enough to be a problem you can see coming and fix.
"""

from __future__ import annotations

from ..data.lineages import LINEAGES_BY_ID, of_stock
from .lifespan import active, lineage_of

#: Days of going short before it starts costing anything. A crossing that
#: arrives one day light should not kill anybody.
GRACE = 6.0

#: Days of shortfall that cost one crew member, once past grace.
PER_LOSS = 9.0


def complement(game, company: bool = False) -> dict:
    """How many of each lineage the flag carries, officers and hands together.

    The headcount (`ship.crew`) has no individual lineage — it is the captain's
    own stock, which is what "you crew them" on the opening screen means.
    Officers may differ: ports recruit from whoever is in them.

    `company=True` counts the crews of hulls sailing in company as well, which
    is what **stores** are asked for: a consort is the captain's own people in
    the captain's own second hull and it eats out of the same hold. It was not,
    and nothing else charged for it either — measured, ordering a thirty-crew
    escort out changed the day's demand not at all, so a fleet was free to keep.
    Air and power are *not* asked with it: every hull breathes and generates for
    itself, and `game.ship.o2` is this hull's tank.
    """
    from . import consorts

    out: dict = {}
    mine = of_stock(getattr(getattr(game, "beginning", None), "stock", None))
    hands = max(0, int(getattr(game.ship, "crew", 0)))
    if company:
        hands += sum(max(0, int(getattr(s, "crew", 0)))
                     for s in consorts.escorts_of(game))
    if hands:
        out[mine] = hands
    for officer in active(getattr(game, "officers", [])):
        key = lineage_of(officer, game).id
        out[key] = out.get(key, 0) + 1
    return out


def demand(game, company: bool = True) -> dict:
    """Tonnes per day the people aboard want, by commodity.

    Scaled by how many of them are asleep: a vitrified crew eats a twentieth
    of what a working one does, which is most of the reason to do it.
    """
    from . import dormancy
    _ageing, fed = dormancy.rates(game, None)
    want: dict = {}
    for lineage_id, count in complement(game, company).items():
        lineage = LINEAGES_BY_ID.get(lineage_id)
        if not lineage:
            continue
        for commodity, rate in lineage.upkeep.items():
            want[commodity] = want.get(commodity, 0.0) + rate * count * fed
    return want


def draw(game) -> float:
    """Kilowatts the complement pulls, which a dry crew notices and you should.

    A Choir hull is not cheaper to run, it is differently expensive: nothing to
    eat, but sixteen times the power draw per head.
    """
    total = 0.0
    for lineage_id, count in complement(game).items():
        lineage = LINEAGES_BY_ID.get(lineage_id)
        if lineage:
            total += lineage.draw * count
    return total


def breathers(game) -> int:
    """How many aboard would actually die if the air stopped."""
    return sum(count for lineage_id, count in complement(game).items()
               if LINEAGES_BY_ID.get(lineage_id, None)
               and LINEAGES_BY_ID[lineage_id].breathes)


def _take(game, commodity: str, amount: float) -> float:
    """Spend from the hold first, then stores. Returns what was not found."""
    short = amount
    held = game.ship.cargo.get(commodity, 0.0)
    if held > 0:
        taken = min(held, short)
        left = held - taken
        if left <= 0.0001:
            game.ship.cargo.pop(commodity, None)
        else:
            game.ship.cargo[commodity] = left
        short -= taken
    if short > 0.0001:
        stored = game.stores.get(commodity, 0.0)
        if stored > 0:
            taken = min(stored, short)
            game.stores[commodity] = stored - taken
            short -= taken
    return max(0.0, short)


def forecast(game, days: float) -> dict:
    """What a crossing of this length will eat, and whether it is aboard.

    The helm asks before you commit to two hundred days. A jump that starves
    the crew on day ninety should say so on day zero — the whole reason this
    function exists rather than only `tick`.
    """
    want = demand(game)
    out = {"days": days, "need": {}, "short": {}, "ok": True}
    for commodity, rate in want.items():
        need = rate * days
        if need <= 0.00001:
            continue
        out["need"][commodity] = need
        have = (game.ship.cargo.get(commodity, 0.0)
                + game.stores.get(commodity, 0.0))
        if have < need:
            out["short"][commodity] = need - have
            out["ok"] = False
    return out


def note(game, days: float) -> str:
    """One line for a screen: what this crossing needs, and what is missing."""
    plan = forecast(game, days)
    if not plan["need"]:
        return ""
    bill = ", ".join(f"{v:.1f} t {k}" for k, v in sorted(plan["need"].items()))
    if plan["ok"]:
        return f"{days:.0f} days of upkeep: {bill}. It is aboard."
    missing = ", ".join(f"{v:.1f} t {k}" for k, v in sorted(plan["short"].items()))
    return (f"{days:.0f} days of upkeep: {bill}. You are short {missing} — "
            "they will start going without.")


def tick(game, days: float, rng) -> list:
    """Feed everyone aboard. Returns (kind, text) lines for the log."""
    if days <= 0:
        return []
    out: list = []
    want = demand(game)
    missing = []
    for commodity, rate in want.items():
        need = rate * days
        if need <= 0.00001:
            continue
        short = _take(game, commodity, need)
        if short > need * 0.02:
            missing.append(commodity)

    if not missing:
        # Eating properly walks the debt back down, so one bad leg is not a
        # permanent mark against the crew.
        game.short_days = max(0.0, getattr(game, "short_days", 0.0) - days * 0.5)
        return out

    game.short_days = getattr(game, "short_days", 0.0) + days
    over = game.short_days - GRACE
    if over <= 0:
        if rng.chance(0.3):
            out.append(("warn", "The stores are not keeping up with what the "
                                f"crew needs: short of {', '.join(missing)}."))
        return out

    # Past grace it costs people. Which people, and how, depends on what ran
    # out — a dry lineage short of metals does not starve, it degrades.
    lost = int(over / PER_LOSS)
    if lost > 0:
        game.short_days -= lost * PER_LOSS
        wet = breathers(game)
        if wet > 0 and any(c in ("biomass",) for c in missing):
            gone = min(wet, lost)
            game.ship.crew = max(0, game.ship.crew - gone)
            out.append(("bad", f"{gone} of the crew are dead of hunger. There "
                               "was nothing left in the hold to give them."))
        else:
            hit = [o for o in active(game.officers) if o.level > 1]
            if hit:
                who = rng.pick(hit)
                who.level -= 1
                out.append(("bad", f"{who.name} has gone without the metals "
                                   "the lineage needs. Something did not come "
                                   "back the same."))
        if game.ship.crew <= 0 and not active(game.officers):
            game.die("Nobody left aboard to hold the watch.")
    elif rng.chance(0.25):
        out.append(("warn", f"Still short of {', '.join(missing)}. It is "
                            "starting to tell."))
    return out
