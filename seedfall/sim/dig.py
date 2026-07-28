"""Working a dig, layer by layer.

A dig holds where in the site the trench has got to and what has come out of
it. Understanding is banked as each layer is finished rather than at the end,
so a dig abandoned after the casing is worth the casing — which is what makes
stopping a real option rather than a way of throwing the whole thing away.

Like a crossing and an approach, it lives on the `Game`: a site half dug is
something you can put down.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ..core.save import register
from ..data.strata import FINDS, METHODS_BY_ID, SPOILS, STRATA
from ..data.xenotech import XENOTECH_BY_ID
from . import inquiry
from . import research as research_sim
from . import xeno as xeno_sim
from .crew import grant_xp
from .ship import add_cargo, apply_damage, cargo_free

_uid = itertools.count(1)


@register
@dataclass
class Dig:
    id: int
    body_index: int
    body_name: str
    tech_id: str
    #: Which system the trench is in. A body index alone is meaningless: it
    #: used to be resolved against whatever system the ship was in *now*, so
    #: working a dig from anywhere else read a different body's fatigue, or
    #: raised IndexError against a shorter body list. -1 means an old save,
    #: migrated on first use.
    system_id: int = -1
    layer: int = 0
    days: int = 0
    points: float = 0.0
    relics: float = 0.0
    finds: list = field(default_factory=list)
    log: list = field(default_factory=list)
    over: bool = False
    outcome: str = ""

    @property
    def definition(self):
        return XENOTECH_BY_ID.get(self.tech_id)

    @property
    def stratum(self):
        return STRATA[self.layer] if self.layer < len(STRATA) else None

    @property
    def depth(self) -> str:
        return f"{min(self.layer + 1, len(STRATA))} of {len(STRATA)}"


def say(dig: Dig, text: str, kind: str = "") -> None:
    dig.log.append((dig.days, text, kind))
    if len(dig.log) > 60:
        dig.log.pop(0)


def begin(game, body_index: int) -> dict:
    body = game.system.bodies[body_index]
    if not body.relic or not body.relic_found:
        return {"ok": False, "why": "Nothing here has been found worth digging."}
    tech = XENOTECH_BY_ID.get(body.relic)
    if tech is None:
        return {"ok": False, "why": "The site is unreadable."}
    if xeno_sim.is_incorporated(game, tech.id):
        return {"ok": False, "why": "You already understand what is down there."}

    dig = Dig(id=next(_uid), body_index=body_index, body_name=body.name,
              system_id=game.location_id, tech_id=tech.id)
    say(dig, f"A trench opened on {body.name}. Four strata to the bottom.", "")
    return {"ok": True, "dig": dig}


def site_of(game, dig: Dig):
    """The body the trench is actually in, wherever the ship has got to."""
    if dig.system_id is None or dig.system_id < 0:
        dig.system_id = game.location_id          # a save from before this
    system = game.galaxy.systems[dig.system_id]
    if dig.body_index >= len(system.bodies):
        return None
    return system.bodies[dig.body_index]


def at_site(game, dig: Dig) -> bool:
    return dig.system_id in (None, -1) or game.location_id == dig.system_id


def _fatigue(game, dig: Dig) -> float:
    """A site worked before gives up less. The easy material goes first."""
    body = site_of(game, dig)
    return max(0.25, 1 - (body.digs if body else 0) * 0.28)


def spoil_chance(stratum, method) -> float:
    """How likely this layer is to come apart, worked this way.

    Deep material is fragile and hurrying is rough on it; the two multiply.
    This is the whole reason `careful` exists, so it is worth being able to
    switch off on its own and watch the difference.
    """
    return min(0.85, stratum.fragility * method.care)


def layer_value(game, dig: Dig, method_id: str) -> dict:
    """What this layer would be worth, worked this way."""
    stratum = dig.stratum
    method = METHODS_BY_ID.get(method_id)
    if stratum is None or method is None:
        return {}
    tech = dig.definition
    total = float(tech.study if tech else 200)
    return {
        "points": total * stratum.share * method.yield_mul * _fatigue(game, dig),
        "relics": stratum.relics * method.yield_mul,
        "spoil": spoil_chance(stratum, method),
        "collapse": method.collapse,
        "days": method.days,
    }


def work(game, dig: Dig, method_id: str, rng) -> dict:
    """Take one stratum. Banks what comes out of it before going deeper."""
    if dig.over:
        return {"ok": False, "why": "The trench is closed."}
    if not at_site(game, dig):
        return {"ok": False, "why": f"The trench is on {dig.body_name}, and "
                                    "you are not there."}
    stratum = dig.stratum
    method = METHODS_BY_ID.get(method_id)
    if stratum is None or method is None:
        return {"ok": False, "why": "Not a way of working it."}

    worth = layer_value(game, dig, method_id)
    dig.days += method.days
    game.advance_days(method.days)
    if game.dead:
        dig.over = True
        dig.outcome = "lost"
        return {"ok": True, "dead": True}

    out = {"ok": True, "stratum": stratum, "method": method,
           "spoiled": False, "collapsed": False, "find": None}

    if method.collapse and rng.chance(method.collapse):
        damage = rng.int(20, 70)
        apply_damage(game.ship, damage)
        out["collapsed"] = True
        say(dig, f"The face came in. The hull took {damage}.", "bad")

    if rng.chance(worth["spoil"]):
        out["spoiled"] = True
        name, text = rng.pick(SPOILS)
        out["spoil_name"], out["spoil_text"] = name, text
        say(dig, f"{name}. {text}", "warn")
        gained = worth["points"] * 0.25
        relics = 0.0
    else:
        gained = worth["points"]
        relics = worth["relics"]
        pool = FINDS.get(stratum.id)
        if pool:
            name, text = rng.pick(pool)
            out["find"] = (name, text)
            dig.finds.append(name)
            say(dig, f"{name}. {text}", "good")
        else:
            say(dig, f"{stratum.name} lifted cleanly.", "good")

    # Banked now, not at the end: a dig stopped after the casing is worth the
    # casing, which is the whole reason stopping is a choice.
    _bank(game, dig, gained, relics)
    out["points"] = gained
    out["relics"] = relics

    dig.layer += 1
    if dig.layer >= len(STRATA):
        return {**out, **finish(game, dig)}
    return out


def _bank(game, dig: Dig, points: float, relics: float) -> None:
    if points > 0:
        dig.points += points
        _gained, done = xeno_sim.add_study(game, dig.tech_id, points)
        research_sim.grant(game.research, round(points * 0.5))
        inquiry.add(game.research, "reading", points * 0.55)
        if done:
            say(dig, f"{dig.definition.name} is understood.", "good")
    if relics > 0:
        room = cargo_free(game.ship, game.ship_stats)
        taken = min(relics, max(0.0, room))
        if taken > 0:
            add_cargo(game.ship, "xenolith", taken)
            dig.relics += taken
    grant_xp(game.officers, "science", 12)


def stop(game, dig: Dig) -> dict:
    """Backfill and leave. What is banked is banked."""
    dig.over = True
    dig.outcome = "backfilled"
    site = site_of(game, dig)
    if site is not None:
        site.digs += 1
    say(dig, "Backfilled. The rest of it is still down there.", "")
    game.add_log(f"Left the {dig.body_name} dig after {dig.days} days with "
                 f"{round(dig.points)} points of understanding.", "")
    return {"ok": True, "stopped": True}


def finish(game, dig: Dig) -> dict:
    dig.over = True
    dig.outcome = "bottomed"
    body = site_of(game, dig)
    if body is not None:
        body.digs += 1
        body.relic_found = False
    say(dig, "The trench is at the bottom. There is nothing under this.", "good")
    game.add_log(f"Bottomed the {dig.body_name} dig: {round(dig.points)} points "
                 f"toward {dig.definition.name}.", "good")
    return {"ok": True, "bottomed": True}
