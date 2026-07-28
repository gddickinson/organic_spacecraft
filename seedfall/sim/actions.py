"""Player actions that span several modules — travel, survey, extraction, dive.

The GUI calls these and reacts to what comes back; none of them touch Qt.
"""

from __future__ import annotations

from ..world.galaxy import distance, transit_days
from ..world.planets import extraction_rate, survey_body
from . import research as research_sim
from .crew import grant_xp
from .encounters import roll_encounter, roll_event
from .ship import add_cargo, apply_damage, cargo_free, hull_pct
from .threat import cleanse


def jump_quote(game, target) -> dict:
    """Can we make this jump, and what will it cost?"""
    ly = distance(game.system, target)
    st = game.ship_stats
    return {"ly": ly, "in_range": ly <= st.jump,
            "days": transit_days(ly, st.speed),
            "fuel": max(1, round(ly * 0.9))}


def jump_to(game, system_id: int) -> dict:
    target = game.galaxy.systems[system_id]
    q = jump_quote(game, target)
    if not q["in_range"]:
        return {"ok": False, "why": f"Out of reach — {q['ly']:.1f} ly against a "
                                    f"{game.ship_stats.jump:.1f} ly range."}
    if game.ship.cargo.get("volatiles", 0) < q["fuel"]:
        have = int(game.ship.cargo.get("volatiles", 0))
        return {"ok": False, "why": f"Not enough reaction mass: {q['fuel']} t of "
                                    f"volatiles needed, {have} aboard."}

    add_cargo(game.ship, "volatiles", -q["fuel"])
    game.location_id = system_id
    game.advance_days(q["days"])
    if game.dead:
        return {"ok": True, "days": q["days"], "dead": True}

    r = game.rng("arrive")
    first = not target.visited
    target.visited = True
    if first and system_id not in game.discovered["systems"]:
        game.discovered["systems"].append(system_id)
        research_sim.grant(game.research, 12)
    game.add_log(f"Arrived at {target.name}"
                 + (" — first hull here to log it." if first else "."),
                 "good" if first else "")

    out = {"ok": True, "days": q["days"], "first": first,
           "event": None, "encounter": None}
    ev = roll_event(r)
    if ev:
        out["event"] = ev
        _apply_event(game, ev["effect"])
    enc = roll_encounter(game, target, r)
    if enc:
        out["encounter"] = enc
    return out


def _apply_event(game, fx: dict) -> None:
    if not fx:
        return
    if fx.get("credits"):
        game.credits += fx["credits"]
    if fx.get("research"):
        research_sim.grant(game.research, fx["research"])
    if fx.get("damage"):
        apply_damage(game.ship, fx["damage"])
    if fx.get("heat"):
        game.ship.heat += fx["heat"]
    if fx.get("morale"):
        game.ship.morale = max(0.0, min(1.0, game.ship.morale + fx["morale"]))
    for cid, n in (fx.get("cargo") or {}).items():
        room = cargo_free(game.ship, game.ship_stats)
        take = min(n, room)
        if take > 0:
            add_cargo(game.ship, cid, take)


# ── surveying ──────────────────────────────────────────────────────────────

def survey(game, body_index: int) -> dict:
    system = game.system
    body = system.bodies[body_index]
    r = game.rng("survey")
    days = 2 + round(3 * (1 - game.ship_stats.scan))
    game.advance_days(days)

    found = survey_body(body, game.ship_stats.scan, r)
    research_sim.grant(game.research, found["research"])
    game.discovered["lifeforms"] += len(found["lifeforms"])
    if found["anomaly"]:
        game.discovered["anomalies"] += 1
    if found["new_body"]:
        game.discovered["bodies"] += 1
    grant_xp(game.officers, "science", 25)

    free = cargo_free(game.ship, game.ship_stats)
    data = min(found["data"], int(free / 0.1))
    if data > 0:
        add_cargo(game.ship, "survey", data)

    system.scanned = all(b.surveyed for b in system.bodies)
    game.add_log(f"Survey of {body.name}: {len(found['lifeforms'])} organism(s) "
                 "catalogued" + (", and something else entirely"
                                 if found["anomaly"] else "") + ".",
                 "good" if found["anomaly"] else "")
    found.update({"days": days, "data": data, "body": body})
    return found


def extract(game, body_index: int, days: int) -> dict:
    """Long-duration extraction at a body."""
    body = game.system.bodies[body_index]
    st = game.ship_stats
    if st.mine <= 0 and st.drink <= 0:
        return {"ok": False, "why": "No mining root or harvest tendril fitted."}

    game.advance_days(days)
    got: dict[str, float] = {}

    def take(cid: str, rate: float) -> None:
        if rate <= 0:
            return
        amount = extraction_rate(body, cid, rate) * days
        if amount <= 0.01:
            return
        n = min(amount, cargo_free(game.ship, game.ship_stats))
        if n <= 0:
            return
        add_cargo(game.ship, cid, n)
        got[cid] = got.get(cid, 0) + n

    take("ore", st.mine)
    take("phosphate", st.phos)
    take("volatiles", st.drink)
    take("biomass", st.graze)

    body.depleted = min(0.95, body.depleted + days * 0.0016 * (st.mine + st.drink))
    grant_xp(game.officers, "engineering", days * 2)
    summary = ", ".join(f"{round(v)} t {k}" for k, v in got.items())
    game.add_log(f"Extraction at {body.name}: {summary}." if summary
                 else f"Nothing worth having at {body.name}.",
                 "good" if summary else "dim")
    return {"ok": True, "got": got, "days": days}


def dive(game, body_index: int) -> dict:
    """NEREUS work: through the crust and into the ocean."""
    body = game.system.bodies[body_index]
    if not game.ship_stats.can_dive:
        return {"ok": False,
                "why": "No melt-head fitted. You would not get through the crust."}
    if body.biome != "subsurface":
        return {"ok": False, "why": "There is no ocean under that."}

    r = game.rng("dive")
    game.advance_days(18)
    risk = 0.28 - game.ship_stats.armour * 0.01
    if r.chance(max(0.05, risk)):
        dmg = r.int(60, 200)
        apply_damage(game.ship, dmg)
        game.add_log(f"The channel closed early. {dmg} points of hull crushed "
                     "before the tail could refreeze.", "bad")

    found = survey_body(body, min(1.0, game.ship_stats.scan + 0.4), r)
    research_sim.grant(game.research, found["research"] + 60)
    game.discovered["lifeforms"] += len(found["lifeforms"])

    contact = False
    if not game.flags.get("contact_made") and (len(found["lifeforms"]) >= 2
                                               or r.chance(0.35)):
        game.flags["contact_made"] = True
        contact = True
        game.adjust_rep("abyssals", 30)
        game.add_log("Twenty kilometres down, something answered in pressure "
                     "waves — and kept answering.", "good")
    return {"ok": True, "found": found, "contact": contact}


def burn_bloom(game) -> dict:
    """Burn out a Bloom mass. Expensive, and it fights back."""
    system = game.system
    r = game.rng("cleanse")
    res, why = cleanse(game, system, r)
    if res is None:
        return {"ok": False, "why": why}
    game.advance_days(6)
    apply_damage(game.ship, res["backlash"] * 0.5)
    game.adjust_rep("charter", 6)
    game.add_log(f"Burned back the growth at {system.name}. Took "
                 f"{round(res['backlash'] * 0.5)} in return."
                 + (" The system is clean." if res["cleared"] else ""),
                 "good" if res["cleared"] else "warn")
    if hull_pct(game.ship) <= 0:
        game.die("Destroyed burning back the Bloom.")
        res["dead"] = True
    res["ok"] = True
    return res


def transfer(game, cid: str, units: float, to_ship: bool) -> float:
    """Move cargo between the hold and the empire depot."""
    if to_ship:
        room = cargo_free(game.ship, game.ship_stats)
        n = min(units, game.stores.get(cid, 0), room)
        if n <= 0:
            return 0
        game.stores[cid] -= n
        add_cargo(game.ship, cid, n)
        return n
    n = min(units, game.ship.cargo.get(cid, 0))
    if n <= 0:
        return 0
    add_cargo(game.ship, cid, -n)
    game.stores[cid] = game.stores.get(cid, 0) + n
    return n
