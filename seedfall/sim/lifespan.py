"""Time passing, and what it does to whoever is aboard to feel it.

Nobody aged. A chronicle could run six years of clock — and the long ones run
twenty — and the officer who signed on at thirty-four signed off at thirty-four.
The game already had a clock that mattered for everything else: deadlines,
markets, colony gestation, research. It did not matter for people.

Now it does, and it matters *differently* depending on what somebody is made
of, which is the point. A wet navigator has maybe fifty working years. A graft
has a century and a half and a maintenance bill. A Dry Choir recording does not
age at all in the sense the word usually means; it drifts, losing a little
fidelity with every rewrite, and six hundred years later there is no longer
much agreement about what it originally was.

Three things happen here, in order of how often you notice them:

- **Ageing.** Every officer gets older by `days × lineage.ageing`. Nothing
  else. Most of a chronicle is spent here and nothing visible happens.
- **Decline.** Past `prime`, an officer sheds `decline` levels a year. It is
  slow: a wet officer loses about a level every seventeen years, so a long
  career is a real arc rather than a cliff.
- **The end.** Past `span` the chance of not waking rises steeply. They are
  not deleted; `retired` is set, they stop counting for stats, and the ship's
  log says what happened in the lineage's own words.

`age_of` is the single place that answers "how old is this person", because
saves written before any of this existed have no age at all and something has
to invent a plausible one exactly once.
"""

from __future__ import annotations

from ..data.lineages import DEFAULT, LINEAGES_BY_ID, of_stock

#: Days in a year, everywhere. The stardate already runs on 365.
YEAR = 365.0

#: Chance per year past `span` that an officer does not see the year out. It
#: compounds, so it is a slope and not a wall: at 1.0 the last of a wet crew
#: are gone a decade or so past ninety-six rather than all at once.
END_SLOPE = 0.34

#: An officer is never worked below this. A level-zero officer is a crash
#: waiting to happen in half a dozen places that divide by level.
FLOOR = 1


def lineage_of(officer, game=None):
    """What this officer is made of. Falls back to the captain's own stock."""
    got = getattr(officer, "lineage", None)
    if not got and game is not None:
        got = of_stock(getattr(getattr(game, "beginning", None), "stock", None))
    return LINEAGES_BY_ID.get(got or DEFAULT, LINEAGES_BY_ID[DEFAULT])


def age_of(officer, game=None) -> float:
    """This officer's age in years, inventing one only if there is none.

    Every save written before lineages existed has officers with no age. They
    cannot all be born on the day the feature shipped — that would make a
    twenty-year chronicle's bridge crew younger than the chronicle. So the
    first ask assigns a plausible working age and stores it.
    """
    got = getattr(officer, "age", None)
    if got is not None:
        return float(got)
    lineage = lineage_of(officer, game)
    # Experienced people are older people: a level-5 officer did not get there
    # in a fortnight. Scaled to the lineage so a recording is not "34".
    share = 0.46 + 0.055 * min(8, getattr(officer, "level", 1))
    born = lineage.prime * share
    try:
        officer.age = born
    except Exception:                                  # frozen or exotic
        return born
    return born


def stage(officer, game=None) -> str:
    """Where in their run this officer is: one word for a screen."""
    lineage = lineage_of(officer, game)
    age = age_of(officer, game)
    if age < lineage.prime * 0.45:
        return "young"
    if age < lineage.prime:
        return "prime"
    if age < lineage.span:
        return "declining"
    return "past their span"


def years_left(officer, game=None) -> float:
    """Roughly how long they have, in clock years rather than their own.

    Divided by `ageing`, so a graft's forty remaining years of *self* are
    nearly seventy years of chronicle — which is the number a captain
    planning a two-hundred-day crossing actually wants.
    """
    lineage = lineage_of(officer, game)
    own = max(0.0, lineage.span - age_of(officer, game))
    return own / max(0.01, lineage.ageing)


def note(officer, game=None) -> str:
    """One line about this officer's time, for the crew screen."""
    lineage = lineage_of(officer, game)
    age = age_of(officer, game)
    where = stage(officer, game)
    if where == "past their span":
        return (f"{lineage.name} · {age:.0f}, past what the lineage usually "
                "manages. Every crossing is a favour.")
    if where == "declining":
        return (f"{lineage.name} · {age:.0f}, and slowing. About "
                f"{years_left(officer, game):.0f} years of clock left in them.")
    if where == "prime":
        return f"{lineage.name} · {age:.0f}, at their best."
    return f"{lineage.name} · {age:.0f}, and new to it."


def tick(game, days: float, rng) -> list:
    """Age everyone aboard. Returns (kind, text) lines for the log.

    Called once from `advance_days`, which is the only clock.
    """
    if days <= 0:
        return []
    out: list = []
    years = days / YEAR
    for officer in list(getattr(game, "officers", [])):
        if getattr(officer, "retired", False):
            continue
        lineage = lineage_of(officer, game)
        was = age_of(officer, game)
        officer.age = was + years * lineage.ageing
        crossed = officer.age

        # Decline, once past prime. Applied on the years actually lived, so a
        # long crossing costs exactly what a long time in port would.
        if crossed > lineage.prime:
            over = min(years * lineage.ageing, crossed - lineage.prime)
            officer.wear = getattr(officer, "wear", 0.0) + over * lineage.decline
            shed = int(officer.wear)
            if shed > 0 and officer.level > FLOOR:
                drop = min(shed, officer.level - FLOOR)
                officer.level -= drop
                officer.wear -= drop
                out.append(("warn", f"{officer.name} is not what they were. "
                                    f"{lineage.name} lineage, {crossed:.0f} "
                                    "years old."))

        # The end. Compounding per year, so it is a slope not a wall.
        if crossed > lineage.span:
            over = crossed - lineage.span
            odds = 1.0 - (1.0 - min(0.9, END_SLOPE * over / 10.0)) ** \
                max(0.0, years * lineage.ageing)
            if odds > 0 and rng.chance(min(0.85, odds)):
                officer.retired = True
                out.append(("bad", f"{officer.name} {lineage.ending}, "
                                   f"{crossed:.0f} years old. The berth is "
                                   "open."))
    return out


def active(officers) -> list:
    """Officers still standing a watch. The one place `retired` is read."""
    return [o for o in officers or [] if not getattr(o, "retired", False)]


def crossing_note(game, days: float) -> str:
    """What a crossing of this length will do to the people flying it.

    The helm and the jump screen both ask. A number of days means nothing
    until somebody tells you it is four years of somebody's life.
    """
    if days < 60:
        return ""
    lineage = LINEAGES_BY_ID[of_stock(
        getattr(getattr(game, "beginning", None), "stock", None))]
    years = days / YEAR * lineage.ageing
    if years < 0.25:
        return ""
    who = active(getattr(game, "officers", []))
    ageing = f"{years:.1f} years of ageing" if years >= 1 else \
        f"{years * 12:.0f} months of ageing"
    at_risk = [o for o in who
               if age_of(o, game) + years > lineage_of(o, game).span]
    line = f"{days:.0f} days is {ageing} for a {lineage.name} crew."
    if at_risk:
        names = ", ".join(o.name for o in at_risk[:3])
        line += f" {names} may not be aboard at the other end."
    return line
