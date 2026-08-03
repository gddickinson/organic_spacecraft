"""Standing the watches of a crossing.

A transit holds what a crossing has spent so far and what it has left. The
helm commits to a burn, and then the crossing is flown a watch at a time: each
one may bring something that wants an answer, and every answer costs time,
reaction mass or the hull.

Nothing is charged up front. A crossing you abort halfway costs you the half
you flew, which is the point of being able to abort it.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ..core.save import register
from . import crew as crew_sim
from ..data.watches import EVENT_CHANCE, WATCHES, WATCHES_BY_ID, watches_for
from . import flight
from .ship import add_cargo, add_heat, apply_damage

_uid = itertools.count(1)


@register
@dataclass
class Transit:
    id: int
    body_index: int
    body_name: str
    burn: str
    watches: int
    stood: int = 0
    days_spent: int = 0
    fuel_spent: float = 0.0
    days_planned: int = 0
    fuel_planned: float = 0.0
    event: str | None = None
    log: list = field(default_factory=list)
    over: bool = False
    outcome: str = ""

    @property
    def progress(self) -> float:
        return self.stood / self.watches if self.watches else 1.0

    @property
    def at_destination(self) -> bool:
        return self.stood >= self.watches


def say(transit: Transit, text: str, kind: str = "") -> None:
    transit.log.append((transit.days_spent, text, kind))
    if len(transit.log) > 60:
        transit.log.pop(0)


def begin(game, body_index: int, burn_id: str) -> dict:
    """Commit to a crossing. Returns the transit, or why not.

    **A live conn is settled first, not abandoned.** A transfer teleports the
    hull across the system; a flight left on `game.conn` would carry its
    frame, its spend and its elapsed hours across that jump, and the conn
    window would re-apply the old offset on top of the new position. The
    flight is broken off and billed through `berthing.commit` — the same
    door every other exit uses — so nothing is flown for free and nothing
    teleports.
    """
    body = game.system.bodies[body_index]
    if game.orbit_body == body.id:
        return {"ok": False, "why": "You are already there."}
    from . import berthing as berth_sim
    berth_sim.secure_underway(game)
    quote = flight.quote(game, body, burn_id)
    held = game.ship.cargo.get("volatiles", 0)
    if held < quote["fuel"]:
        return {"ok": False,
                "why": f"That burn needs {quote['fuel']} t of reaction mass; "
                       f"you have {int(held)}. You can always coast."}

    transit = Transit(id=next(_uid), body_index=body_index, body_name=body.name,
                      burn=burn_id, watches=watches_for(quote["days"]),
                      days_planned=quote["days"], fuel_planned=quote["fuel"])
    say(transit, f"{quote['burn'].name} to {body.name}: "
                 f"{quote['days']} days planned, {quote['fuel']} t of mass.",
        "")
    # And what the crew make of the length of it. `data/lineages.py` has
    # written a `time_sense` line per lineage since it was written — "a season
    # out of a life that has a season to spare", against "long enough to be
    # tedious, not long enough to matter" — and no player had ever seen one,
    # because nothing read the field. A hundred days is a different thing to a
    # wet crew and to a lineage of recordings, and now the crossing says so.
    felt = crew_sim.how_it_feels(game, quote["days"])
    if felt:
        say(transit, felt, "dim")
    return {"ok": True, "transit": transit, "quote": quote}


def _eligible(game, transit) -> list:
    hot = flight.path_note(game, game.system.bodies[transit.body_index],
                           transit.burn) is not None
    return [w for w in WATCHES if not w.hot_only or hot]


def stand(game, transit: Transit, rng) -> dict:
    """Fly one watch. Returns what came up, if anything."""
    if transit.over:
        return {"ok": False, "why": "The crossing is finished."}
    if transit.event:
        return {"ok": False, "why": "The watch is waiting on an answer."}

    share = max(1, round(transit.days_planned / transit.watches))
    fuel = transit.fuel_planned / transit.watches
    _spend(game, transit, days=share, fuel=fuel)
    transit.stood += 1
    if game.dead:
        transit.over = True
        transit.outcome = "lost"
        return {"ok": True, "dead": True}

    # The last watch can bring something too — gating this on not yet being
    # at the destination meant the final leg was always uneventful, which is
    # exactly the leg a captain is most tired and least stocked for.
    pool = _eligible(game, transit)
    if pool and rng.chance(EVENT_CHANCE):
        watch = rng.weighted([(w.weight, w) for w in pool])
        transit.event = watch.id
        say(transit, watch.name, watch.tint)
        return {"ok": True, "watch": watch}

    if transit.at_destination:
        return finish(game, transit)
    say(transit, "A quiet watch.", "dim")
    return {"ok": True, "quiet": True}


def _spend(game, transit: Transit, days: int = 0, fuel: float = 0.0) -> None:
    if fuel > 0:
        held = game.ship.cargo.get("volatiles", 0)
        add_cargo(game.ship, "volatiles", -min(fuel, held))
        transit.fuel_spent += min(fuel, held)
    if days > 0:
        transit.days_spent += days
        game.advance_days(days)
        # A crossing is tedious, and how tedious depends on who is aboard.
        # See `crew.tedium`: the per-lineage figure has been in the tables
        # since they were written and nothing read it, so a hundred days was
        # the same to a wet crew as to a lineage of recordings.
        crew_sim.bear_tedium(game, days)


def options(transit: Transit) -> list:
    watch = WATCHES_BY_ID.get(transit.event or "")
    return list(watch.options) if watch else []


def choose(game, transit: Transit, option_id: str, rng) -> dict:
    """Answer the watch. Every answer costs one of the three things."""
    watch = WATCHES_BY_ID.get(transit.event or "")
    if watch is None:
        return {"ok": False, "why": "Nothing is waiting."}
    option = next((o for o in watch.options if o.id == option_id), None)
    if option is None:
        return {"ok": False, "why": "Not one of the choices."}

    transit.event = None
    _spend(game, transit, days=option.days, fuel=option.fuel)
    if option.damage:
        apply_damage(game.ship, option.damage)
    if option.heat:
        add_heat(game.ship, option.heat, game.ship_stats.heat_cap)

    out = {"ok": True, "option": option, "went_wrong": False}
    if option.risk and rng.chance(option.risk):
        out["went_wrong"] = True
        if option.risk_damage:
            apply_damage(game.ship, option.risk_damage)
        if option.risk_days:
            _spend(game, transit, days=option.risk_days, fuel=0.0)
        say(transit, option.risk_text or "It went badly.", "bad")
    else:
        say(transit, f"{option.label}.", "")

    for cid, amount in option.salvage.items():
        add_cargo(game.ship, cid, amount)
        say(transit, f"{round(amount)} t of {cid} aboard.", "good")
    if option.research:
        from . import inquiry, research as research_sim
        research_sim.grant(game.research, option.research)
        inquiry.add(game.research, "hardware", option.research * 0.5)

    if option.aborts:
        return abort(game, transit)
    if game.dead:
        transit.over = True
        transit.outcome = "lost"
        return {**out, "dead": True}
    if transit.at_destination:
        return {**out, **finish(game, transit)}
    return out


def abort(game, transit: Transit) -> dict:
    """Give it up and stay where you are. What is spent is spent."""
    transit.over = True
    transit.outcome = "aborted"
    say(transit, "The burn is cut. You are where you were, minus the mass.",
        "warn")
    game.add_log(f"Crossing to {transit.body_name} abandoned after "
                 f"{transit.days_spent} days.", "warn")
    return {"ok": True, "aborted": True}


def finish(game, transit: Transit) -> dict:
    transit.over = True
    transit.outcome = "arrived"
    body = game.system.bodies[transit.body_index]
    flight.hold_at(game, body)
    say(transit, f"Alongside {body.name}.", "good")
    game.add_log(f"Arrived at {body.name}: {transit.days_spent} days, "
                 f"{round(transit.fuel_spent)} t of reaction mass.", "good")
    return {"ok": True, "arrived": True, "body": body}


def summary(transit: Transit) -> dict:
    return {"stood": transit.stood, "watches": transit.watches,
            "days": transit.days_spent, "fuel": transit.fuel_spent,
            "planned_days": transit.days_planned,
            "planned_fuel": transit.fuel_planned,
            "over": transit.over, "outcome": transit.outcome}
