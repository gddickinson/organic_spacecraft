"""Fieldwork — everything the crew does off the ship.

Excavating a relic site, taking relics apart in a laboratory, buying somebody
else's field notes, seizing them off a wreck, and putting a landing party on the
ground. All of it takes days off the ship's clock and returns plain data.
"""

from __future__ import annotations

from ..data.xenotech import CULTURES_BY_ID, XENOTECH_BY_ID
from . import inquiry
from . import notes as notes_sim
from . import research as research_sim
from . import xeno as xeno_sim
from .actions import jump_quote
from . import flight
from .crew import grant_xp
from .ship import add_cargo, apply_damage, cargo_free

def has_laboratory(game) -> bool:
    """A polyp lab aboard, or a reef or reactivated array in this system."""
    from ..data.colonies import COLONIES_BY_ID
    if "polyp_lab" in game.ship.fitted and "polyp_lab" not in game.ship.disabled:
        return True
    if "ossuary_archive" in game.ship.fitted:
        return True
    for c in game.colonies:
        if not (c.online and c.system_id == game.location_id):
            continue
        fx = COLONIES_BY_ID[c.class_id].effects
        if fx.get("medical") or fx.get("xenoyard"):
            return True
    return False


def excavate(game, body_index: int) -> dict:
    """Dig a relic site. Yields understanding, relics, and occasionally a hole."""
    body = game.system.bodies[body_index]
    if not body.relic or not body.relic_found:
        return {"ok": False, "why": "Nothing here has been found worth digging."}
    tech = XENOTECH_BY_ID.get(body.relic)
    if tech is None:
        return {"ok": False, "why": "The site is unreadable."}

    r = game.rng("dig")
    days = 12 + r.int(0, 8)
    game.advance_days(days)
    if game.dead:
        return {"ok": True, "dead": True}

    lab = has_laboratory(game)
    worked = body.digs
    # Each return trip to the same site yields less; the easy material goes first.
    fatigue = max(0.25, 1 - worked * 0.28)
    points = xeno_sim.dig_value(r, game.ship_stats.scan, lab) * fatigue
    _points, done = xeno_sim.add_study(game, tech.id, points)
    body.digs += 1

    relics = 0
    if r.chance(0.55 * fatigue):
        room = cargo_free(game.ship, game.ship_stats)
        relics = min(r.int(1, 2), int(room / 0.2))
        if relics > 0:
            add_cargo(game.ship, "xenolith", relics)

    research_sim.grant(game.research, round(points * 0.5))
    inquiry.add(game.research, "reading", points * 0.55)
    grant_xp(game.officers, "science", 30)

    mishap = None
    if r.chance(0.16):
        dmg = r.int(20, 70)
        apply_damage(game.ship, dmg)
        mishap = ("The face collapsed onto the lander. Nobody was lost and the "
                  f"hull took {dmg}.")

    game.add_log(f"Excavated {tech.name} at {body.name}: "
                 f"{round(points)} points of understanding.",
                 "good" if done else "")
    return {"ok": True, "tech": tech, "points": points, "relics": relics,
            "days": days, "incorporated": done, "lab": lab, "mishap": mishap,
            "exhausted": fatigue <= 0.3}


def analyse(game, tech_id: str, count: int) -> dict:
    """Take relics apart in a laboratory to understand a specific technology."""
    tech = XENOTECH_BY_ID.get(tech_id)
    if tech is None:
        return {"ok": False, "why": "No such technology."}
    if xeno_sim.is_incorporated(game, tech_id):
        return {"ok": False, "why": f"{tech.name} is already yours."}
    held = game.ship.cargo.get("xenolith", 0)
    n = min(count, int(held))
    if n < 1:
        return {"ok": False, "why": "No relics aboard to take apart."}

    lab = has_laboratory(game)
    days = 4 + n * 2
    game.advance_days(days)
    if game.dead:
        return {"ok": True, "dead": True}

    add_cargo(game.ship, "xenolith", -n)
    points = xeno_sim.analyse_value(n, lab, game.ship_stats.research)
    _p, done = xeno_sim.add_study(game, tech_id, points)
    grant_xp(game.officers, "science", 20 * n)
    game.add_log(f"Analysed {n} relic(s) toward {tech.name}: "
                 f"{round(points)} points.", "good" if done else "")
    return {"ok": True, "tech": tech, "points": points, "used": n,
            "days": days, "incorporated": done, "lab": lab}


def buy_field_notes(game, tech_id: str) -> dict:
    """Somebody else's excavation notes, for sale at a port."""
    tech = XENOTECH_BY_ID.get(tech_id)
    if tech is None:
        return {"ok": False, "why": "No such technology."}
    if xeno_sim.is_incorporated(game, tech_id):
        return {"ok": False, "why": f"{tech.name} is already yours."}
    sysm = game.system
    if not sysm.port:
        return {"ok": False, "why": "No port here."}
    price = xeno_notes_price(game, tech)
    if game.credits < price:
        return {"ok": False, "why": f"They want {round(price)} credits for it."}

    game.credits -= price
    r = game.rng("notes")
    points = tech.study * r.float(0.16, 0.28)
    _p, done = xeno_sim.add_study(game, tech_id, points)
    game.adjust_rep(sysm.port.faction, 1)
    game.add_log(f"Bought field notes on {tech.name}: {round(points)} points.",
                 "good" if done else "")
    return {"ok": True, "tech": tech, "points": points, "price": price,
            "incorporated": done}


def xeno_notes_price(game, tech) -> int:
    """What a port charges for notes — the Dry Choir has the best and knows it."""
    base = tech.study * 26
    fac = game.system.port.faction if game.system.port else None
    if fac == "sanhedrin":
        base *= 0.8
    elif fac == "freeholds":
        base *= 0.95
    elif fac == "charter":
        base *= 1.15
    return round(base * (1 - game.ship_stats.trade * 0.4))


def seize_notes(game, faction_id: str, rng) -> dict | None:
    """Salvage from a kill: somebody else's understanding, taken intact."""
    odds = {"sanhedrin": 0.55, "freeholds": 0.30, "concordat": 0.18,
            "charter": 0.22, "bloom": 0.05}
    if not rng.chance(odds.get(faction_id, 0.15)):
        return None
    target = xeno_sim.best_unfinished(game)
    if target is None:
        return None
    points = target.study * rng.float(0.10, 0.22)
    _p, done = xeno_sim.add_study(game, target.id, points)
    return {"tech": target, "points": points, "incorporated": done}


def launch_expedition(game, body_index: int, officer_ids: list[int],
                      load: int = 1) -> dict:
    """Put a landing party down. Costs biomass for supplies and time to descend."""
    from . import expedition as exp_sim
    flight.ensure_at(game, body_index)
    body = game.system.bodies[body_index]
    from ..world.planets import BODY_KINDS
    if not BODY_KINDS[body.kind][2]:
        return {"ok": False, "why": "Nothing to stand on down there."}
    if game.expedition is not None and not game.expedition.over:
        return {"ok": False, "why": "A party is already on the ground."}
    if not body.surveyed:
        return {"ok": False, "why": "Survey it from orbit first."}
    from ..data.expedition import SUPPLY_LOADS
    label, tonnes, days = SUPPLY_LOADS[max(0, min(load, len(SUPPLY_LOADS) - 1))]
    if game.ship.cargo.get("biomass", 0) < tonnes:
        return {"ok": False,
                "why": f"{label} needs {tonnes} t of biomass; you have "
                       f"{int(game.ship.cargo.get('biomass', 0))}."}

    add_cargo(game.ship, "biomass", -tonnes)
    game.advance_days(3)
    if game.dead:
        return {"ok": True, "dead": True}
    game.expedition = exp_sim.generate(game.rng("landing"), game.system, body,
                                       list(officer_ids), supply=days)
    from . import contracts as contract_sim
    contract_sim.note_landing(game, game.system.id, body.id)
    game.add_log(f"Landing party down on {body.name}.", "good")
    return {"ok": True, "expedition": game.expedition}


def conclude_expedition(game) -> dict:
    """Bank what the party brought back and take the ship's time for it."""
    from . import expedition as exp_sim
    exp = game.expedition
    if exp is None:
        return {"ok": False, "why": "No party in the field."}
    if not exp.over:
        exp_sim.finish(exp, "aborted")

    haul = exp_sim.haul_kept(exp)
    study = exp_sim.study_kept(exp)
    game.advance_days(max(1, exp.days // 3))

    stowed: dict[str, float] = {}
    for key, amount in haul.items():
        if key == "research":
            research_sim.grant(game.research, amount)
            inquiry.add(game.research, "specimen", amount * 0.5)
            stowed["research"] = amount
        elif key == "credits":
            game.credits += amount
            stowed["credits"] = amount
        elif key == "sample":
            room = cargo_free(game.ship, game.ship_stats)
            n = min(amount, room)
            if n > 0:
                add_cargo(game.ship, "xenopharma", n)
                stowed["xenopharma"] = n
        else:
            room = cargo_free(game.ship, game.ship_stats)
            n = min(amount, room)
            if n > 0:
                add_cargo(game.ship, key, n)
                stowed[key] = n

    # What the ground told you is filed against the game rather than printed
    # once and dropped with the expedition object.
    system_name = game.galaxy.systems[exp.system_id].name
    notes = [notes_sim.file(game, note_id, exp.body_name, system_name)
             for note_id in exp.lore]
    notes = [n for n in notes if n.get("ok")]

    incorporated = None
    if study > 0:
        target = xeno_sim.best_unfinished(game)
        if target is not None:
            _p, done = xeno_sim.add_study(game, target.id, study)
            incorporated = target if done else None
            stowed["study"] = study

    for oid in exp.injured:
        officer = next((o for o in game.officers if o.id == oid), None)
        if officer and officer.level > 1:
            officer.level -= 1        # convalescence costs experience

    game.expedition = None
    game.add_log(f"Landing party recovered from {exp.body_name} after "
                 f"{exp.days} days.", "good" if exp.outcome != "stranded" else "warn")
    return {"ok": True, "outcome": exp.outcome, "stowed": stowed,
            "notes": notes, "days": exp.days, "injured": len(exp.injured),
            "incorporated": incorporated, "body": exp.body_name}
