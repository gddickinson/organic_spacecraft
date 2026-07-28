"""Player actions that span several modules — travel, survey, extraction, dive.

The GUI calls these and reacts to what comes back; none of them touch Qt.
"""

from __future__ import annotations

from ..world.galaxy import distance, transit_days
from ..world.planets import survey_body
from . import mining
from . import research as research_sim
from . import rumours as rumour_sim
from .crew import grant_xp
from .encounters import roll_encounter, roll_event
from .ship import add_cargo, apply_damage, cargo_free, hull_pct
from .threat import cleanse
from . import flight


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
    flight.arrive_in_system(game)
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
    for kind, text in rumour_sim.resolve(game, system_id):
        game.add_log(text, kind)

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
    # An event that charges you (the Freehold skiff with volatiles to sell)
    # must not put the treasury underwater. You buy what you can pay for, and
    # any goods that came with the offer scale down to match.
    share = 1.0
    cost = fx.get("credits", 0)
    if cost < 0:
        affordable = min(-cost, max(0.0, game.credits))
        share = affordable / -cost if cost else 1.0
        game.credits -= affordable
    elif cost:
        game.credits += cost
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
        take = min(n * share, room)
        if take > 0:
            add_cargo(game.ship, cid, take)


# ── surveying ──────────────────────────────────────────────────────────────

def survey(game, body_index: int) -> dict:
    """Chart a body. The ship flies alongside first."""
    flight.ensure_at(game, body_index)
    system = game.system
    body = system.bodies[body_index]
    r = game.rng("survey")
    days = 2 + round(3 * (1 - game.ship_stats.scan))
    game.advance_days(days)

    found = survey_body(body, game.ship_stats.scan, r)
    research_sim.grant(game.research, found["research"])

    # Surveying the origin system is how the heart is located.
    from . import bloom as bloom_sim
    if bloom_sim.ensure(game).heart_system == game.location_id:
        revealed = bloom_sim.reveal_heart(game)
        if revealed:
            game.add_log(revealed[1], revealed[0])
            found["heart"] = True
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


def extract(game, body_index: int, days: int,
            method_id: str = mining.DEFAULT_METHOD) -> dict:
    """Work a body for a spell. How you work it is most of the decision."""
    flight.ensure_at(game, body_index)
    body = game.system.bodies[body_index]
    st = game.ship_stats
    if st.mine <= 0 and st.drink <= 0:
        return {"ok": False, "why": "No mining root or harvest tendril fitted."}

    method = mining.METHODS_BY_ID.get(method_id, mining.METHODS_BY_ID[
        mining.DEFAULT_METHOD])
    if method.needs and getattr(st, method.needs, 0) <= 0:
        return {"ok": False, "why": "Nothing fitted that can work it that way."}
    if not mining.reachable(body, method.id):
        return {"ok": False, "why": "Nothing that reaches is worth the trouble."}
    afford, why = mining.can_afford(game, method.id, days)
    if not afford:
        return {"ok": False, "why": why}

    mining.spend_upkeep(game, method.id, days)
    game.advance_days(days)
    if game.dead:
        return {"ok": True, "dead": True, "days": days}

    r = game.rng("dig")
    event = mining.roll_event(game, body, method.id, r)
    spoil = event.get("spoil", 0.0) if event and event["kind"] == "mishap" else 0.0
    bonus = event.get("bonus", 0.0) if event and event["kind"] == "strike" else 0.0

    got: dict[str, float] = {}

    def take(cid: str, rig: float) -> None:
        amount = mining.rate_for(body, method.id, cid, rig) * days
        amount *= (1 - spoil) * (1 + bonus)
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

    wear = mining.apply_wear(game, method.id, days)
    mining.deplete(game, body, method.id, days, st.mine + st.drink)
    grant_xp(game.officers, "engineering", days * 2)

    summary = ", ".join(f"{round(v)} t {k}" for k, v in got.items())
    game.add_log(f"{method.name} at {body.name}: {summary}." if summary
                 else f"Nothing worth having at {body.name}.",
                 "good" if summary else "dim")
    if event and event["kind"] == "mishap":
        game.add_log(f"{event['mishap'].name} at {body.name}.", "bad")
    return {"ok": True, "got": got, "days": days, "method": method,
            "event": event, "wear": wear}


def dive(game, body_index: int) -> dict:
    """NEREUS work: through the crust and into the ocean."""
    flight.ensure_at(game, body_index)
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


def strike_heart(game) -> dict:
    """Burn the original germination. It takes more than one visit."""
    from . import bloom as bloom_sim
    fp = sum(w.wpn.dmg for w in game.ship_stats.weapons)
    if fp < 40:
        return {"ok": False,
                "why": "You would need serious armament to make an impression."}
    r = game.rng("heart")
    res = bloom_sim.strike_heart(game, fp, r)
    if not res.get("ok"):
        return res
    game.advance_days(8)
    apply_damage(game.ship, res["backlash"])
    game.adjust_rep("charter", 10)
    if res["destroyed"]:
        game.add_log("The First Instar is dead. Whatever else is still growing "
                     "out here, it is growing on its own now.", "good")
    else:
        left = res["left"]
        game.add_log(f"Burned into the heart at Kessel's Reach. It is still "
                     f"there — roughly {round(left)} of it.", "warn")
    if hull_pct(game.ship) <= 0:
        game.die("Destroyed at the heart of the Bloom.")
        res["dead"] = True
    return res


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


def is_stranded(game) -> bool:
    """No fuel for any reachable system, and no way to make any here."""
    from ..world.galaxy import in_range
    reach = in_range(game.galaxy.systems, game.system, game.ship_stats.jump)
    fuel = game.ship.cargo.get("volatiles", 0)
    if any(fuel >= jump_quote(game, s)["fuel"] for s in reach):
        return False
    if game.system.port and game.system.market:
        # A port can always sell you fuel, if you can pay for anything at all.
        cheapest = min((jump_quote(game, s)["fuel"] for s in reach), default=99)
        from ..world.economy import buy_price
        price = buy_price(game.system.market, "volatiles",
                          game.rep.get(game.system.port.faction, 0)) or 40
        if game.credits >= price * (cheapest - fuel):
            return False
    # Can we make our own out of ice in this system?
    if game.ship_stats.drink > 0 and any(
            b.resources.get("volatiles", 0) > 0.05 for b in game.system.bodies):
        return False
    return bool(reach)


def distress_call(game) -> dict:
    """Broadcast for a tow. Somebody always comes; nobody comes for free."""
    from ..world.galaxy import nearest_port
    if not is_stranded(game):
        return {"ok": False, "why": "You are not stranded — you can still move."}
    port = nearest_port(game.galaxy.systems, game.system)
    if port is None:
        return {"ok": False, "why": "There is no port left in the Verge to answer."}

    faction = port.port.faction
    days = 20 + game.rng("tow").int(5, 25)
    game.advance_days(days)
    if game.dead:
        return {"ok": True, "dead": True}
    game.location_id = port.id
    port.visited = True
    game.adjust_rep(faction, -12)
    add_cargo(game.ship, "volatiles", 20)
    game.credits = max(0.0, game.credits - 2000)
    game.add_log(f"Answered by {faction}. Towed to {port.name}; they logged it, "
                 "and they will remember.", "warn")
    return {"ok": True, "port": port, "days": days, "faction": faction}


def launch_exodus(game) -> dict:
    """Take the ark and go. This ends the chronicle."""
    ark = (game.ship if game.ship.chassis == "leviathan"
           else next((s for s in game.fleet if s.chassis == "leviathan"), None))
    if ark is None:
        return {"ok": False, "why": "You have no LEVIATHAN. Twelve drums, or nothing."}
    berths = sum(c.pop for c in game.colonies if c.online)
    game.flags["exodus_launched"] = True
    game.add_log("The trunk meristem stood down. The Verge is a light behind you.",
                 "good")
    game.advance_days(1)
    return {"ok": True, "ark": ark, "carried": berths}


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
