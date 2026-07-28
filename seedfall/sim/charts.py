"""Pricing a survey by what is actually in it.

`intel.survey_value()` was `460 + 210 * len(bodies)`, which is to say it priced
a chart by weight. A system holding a buried Abyssal site, an ore grade worth
crossing the sector for and something the instruments could not account for
fetched the same as five bare rocks — and both fetched about a fiftieth of what
any other hour of the game pays.

A chart is information. It is worth what it says, and it is worth that to
somebody in particular.
"""

from __future__ import annotations

from ..data.charts import (APPETITES, APPETITES_BY_FACTION, FRESH_DAYS,
                           PRIZED, STALE_FLOOR, WORTH)
from ..data.factions import FACTIONS_BY_ID
from ..world.galaxy import distance

#: Resources a buyer is actually paying to hear about.
USEFUL = ("ore", "phosphate", "volatiles", "biomass")

#: Body kinds a colony could sit on.
SITES = ("rocky", "moon", "asteroid", "ice", "ocean")


def components(game, system) -> dict[str, float]:
    """What is in this system, in the units the price list uses."""
    out = {"base": 1.0, "body": float(len(system.bodies)), "ore": 0.0,
           "life": 0.0, "anomaly": 0.0, "relic": 0.0, "site": 0.0,
           "port": 1.0 if system.port else 0.0, "route": 0.0,
           "bloom": float(system.bloom)}
    for body in system.bodies:
        out["ore"] += sum(body.resources.get(key, 0.0) for key in USEFUL)
        out["life"] += len(body.lifeforms)
        out["anomaly"] += 1.0 if body.anomaly else 0.0
        out["relic"] += 1.0 if body.relic else 0.0
        out["site"] += 1.0 if body.kind in SITES else 0.0
    return out


def _reach(game, system, faction: str | None) -> float:
    """How far this system is from the buyer's nearest holding, in ly.

    Somebody pays more to hear about ground they cannot easily reach
    themselves — which is the whole argument for a survey ship existing.
    """
    if not faction:
        return 0.0
    theirs = [s for s in game.galaxy.systems if s.faction == faction
              or (s.port and s.port.faction == faction)]
    if not theirs:
        return 0.0
    return min(distance(system, s) for s in theirs)


def _made(game) -> dict:
    """When each chart was finished. Created on first use for old saves."""
    if getattr(game, "charts_made", None) is None:
        game.charts_made = {}
    # Chart dates used to live in `game.register`, which is the *price*
    # register: `market.best_markets` walks every value in it and reads
    # `.sell`, so an integer day in there crashed the port screen the moment
    # you had charted anything. Migrate any old save on the way past.
    stale = [k for k in list(game.register) if str(k).startswith("chart:")]
    for key in stale:
        game.charts_made[str(key).split(":", 1)[1]] = game.register.pop(key)
    return game.charts_made


def freshness(game, system) -> float:
    """A chart made long ago is worth less. The sector moves."""
    made = _made(game).get(str(system.id))
    if made is None:
        return 1.0
    age = max(0, game.day - int(made))
    if age >= FRESH_DAYS:
        return STALE_FLOOR
    return 1.0 - (1.0 - STALE_FLOOR) * (age / FRESH_DAYS)


def value_to(game, system, faction: str | None) -> int:
    """What this buyer pays for a complete chart of this system."""
    parts = components(game, system)
    parts["route"] = _reach(game, system, faction)
    appetite = APPETITES_BY_FACTION.get(faction or "")
    prizes = set(appetite.prizes) if appetite else set()

    total = 0.0
    for key, amount in parts.items():
        if amount <= 0:
            continue
        worth = WORTH[key] * amount
        if key in prizes:
            worth *= PRIZED
        total += worth

    total *= appetite.keen if appetite else 1.0
    total *= freshness(game, system)
    total *= 1 + game.ship_stats.trade
    return max(1, round(total))


def best_buyer(game, system) -> tuple[str | None, int]:
    """Who pays most for this chart, and how much."""
    offers = [(a.faction, value_to(game, system, a.faction)) for a in APPETITES]
    if not offers:
        return None, value_to(game, system, None)
    return max(offers, key=lambda t: t[1])


def offers(game, system) -> list[tuple[str, int, str]]:
    """Every power's offer for this chart, best first."""
    out = [(a.faction, value_to(game, system, a.faction), a.line)
           for a in APPETITES]
    return sorted(out, key=lambda t: -t[1])


def note(game, system) -> str:
    """One line on why this chart is worth what it is."""
    parts = components(game, system)
    said = []
    if parts["relic"]:
        said.append(f"{int(parts['relic'])} buried site(s)")
    if parts["anomaly"]:
        said.append(f"{int(parts['anomaly'])} anomal{'y' if parts['anomaly'] == 1 else 'ies'}")
    if parts["life"]:
        said.append(f"{int(parts['life'])} organism(s)")
    if parts["ore"] > 1.5:
        said.append("rich ground")
    if parts["port"]:
        said.append("a working quay")
    if parts["bloom"] > 0.15:
        said.append("Bloom in it")
    if not said:
        said.append(f"{int(parts['body'])} bodies and nothing remarkable")
    return ", ".join(said)


def stamp(game, system) -> None:
    """Record when this chart was completed, so it can go stale."""
    made = _made(game)
    made.setdefault(str(system.id), game.day)


def buyer_line(faction: str | None) -> str:
    appetite = APPETITES_BY_FACTION.get(faction or "")
    return appetite.line if appetite else ""


def buyer_name(faction: str | None) -> str:
    fac = FACTIONS_BY_ID.get(faction or "")
    return fac.short if fac else "Nobody in particular"
