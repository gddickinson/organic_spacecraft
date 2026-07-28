"""What the monitoring panels read: one honest number per instrument.

The gauges are pop-out windows a player leaves open while flying, so what they
show has to be the live state rather than a snapshot taken when they opened.
Putting the readings here rather than in the widgets means two things: the
layer rule holds (nothing under `sim/` imports Qt), and the suite can check
what an instrument *says* without painting it.

Every reading carries its own limits and a `band` — "good", "watch", "bad" —
so a gauge does not have to re-derive when a number is worrying. The bands are
the sim's own thresholds, not the panel's opinion.
"""

from __future__ import annotations

import math

from ..data.commodities import BY_ID as COMMODITIES_BY_ID
from ..world.galaxy import distance
from .ship import cargo_used, hull_pct, is_breached


def _band(fraction: float, watch: float = 0.5, bad: float = 0.2,
          rising: bool = False) -> str:
    """Where a number sits against its own limits. `rising` inverts it."""
    if rising:
        return "bad" if fraction >= bad else ("watch" if fraction >= watch
                                              else "good")
    return "bad" if fraction <= bad else ("watch" if fraction <= watch
                                          else "good")


def power(game) -> dict:
    st = game.ship_stats
    margin = st.power - st.draw
    share = st.draw / st.power if st.power else 2.0
    return {
        "title": "Power",
        "generated": st.power, "drawn": st.draw, "margin": margin,
        "now": st.draw, "cap": st.power,
        "fraction": min(1.0, share),
        "band": _band(share, watch=0.85, bad=1.0, rising=True),
        "note": ("Brownout — every system is running at "
                 f"{st.brownout * 100:.0f}%." if st.brownout < 1
                 else f"{margin:.0f} spare."),
        "unit": "MW",
    }


def heat(game) -> dict:
    ship = game.ship
    st = game.ship_stats
    cap = max(1.0, st.heat_cap)
    share = ship.heat / cap
    return {
        "title": "Heat",
        "now": ship.heat, "cap": cap, "vent": st.vent,
        "fraction": min(1.5, share),
        "band": _band(share, watch=0.7, bad=1.0, rising=True),
        "note": ("Over the cap — the radiators cannot keep up and the hull is "
                 "cooking." if share >= 1.0
                 else f"Venting {st.vent:.0f} a turn."),
        "unit": "",
    }


def integrity(game) -> dict:
    ship = game.ship
    layers = []
    for layer in ship.layers:
        share = layer.hp / layer.max if layer.max else 1.0
        layers.append({
            "name": layer.name, "hp": layer.hp, "max": layer.max,
            "fraction": max(0.0, min(1.0, share)),
            "critical": bool(layer.critical),
            "band": _band(share, watch=0.55, bad=0.2),
        })
    whole = hull_pct(ship)
    return {
        "title": "Integrity",
        "layers": layers, "fraction": whole,
        "band": "bad" if is_breached(ship) else _band(whole, 0.55, 0.25),
        "note": ("The pressure vessel is open. The crew is on bottled air."
                 if is_breached(ship) else f"{whole * 100:.0f}% of hull."),
        "unit": "%",
    }


def hold(game) -> dict:
    st = game.ship_stats
    used = cargo_used(game.ship)
    cap = max(1.0, st.cargo)
    rows = []
    for cid, tonnes in sorted(game.ship.cargo.items(), key=lambda kv: -kv[1]):
        if tonnes <= 0:
            continue
        commodity = COMMODITIES_BY_ID.get(cid)
        rows.append({"id": cid, "name": commodity.name if commodity else cid,
                     "tonnes": tonnes, "fraction": tonnes / cap})
    share = used / cap
    return {
        "title": "Hold",
        "used": used, "cap": cap, "rows": rows,
        "fraction": min(1.0, share),
        "band": _band(share, watch=0.9, bad=0.99, rising=True),
        "note": (f"{cap - used:.0f} t free." if used < cap
                 else "Full — the rig will not run and nothing can be bought."),
        "unit": "t",
    }


#: What counts as a full tank of air, for the crew dial's scale.
AIR_FULL = 400.0


def crew(game) -> dict:
    st = game.ship_stats
    officers = [{"name": o.name, "role": o.role_name, "stat": o.stat,
                 "level": o.level} for o in game.officers]
    days = st.o2_days
    return {
        "title": "Crew",
        # Every dial reads `now` and `cap`. Without them the crew gauge drew a
        # needle over "0/0 d" while its own caption said "124 days of air" —
        # an instrument disagreeing with itself on the same face.
        "now": days, "cap": AIR_FULL,
        "officers": officers, "berths": st.berths,
        "aboard": game.ship.crew, "o2_days": days,
        "morale": getattr(game, "morale", 1.0),
        "fraction": min(1.0, days / AIR_FULL) if days else 0.0,
        "band": _band(days / AIR_FULL if days else 0.0, watch=0.25, bad=0.08),
        "note": (f"{days:.0f} days of air." if days
                 else "No crew aboard to need any."),
        "unit": "d",
    }


#: How far the scope reaches beyond the sensor rating, as a share.
SCOPE_MARGIN = 1.15


def scope(game) -> dict:
    """What is within sensor range, as bearings and distances.

    Bodies are placed on their real orbits, so this is the same geometry the
    helm flies; the Bloom front is whichever infested systems are inside the
    sensor envelope. Bearings are radians, zero along +x.
    """
    st = game.ship_stats
    here = game.system
    contacts = []
    for index, body in enumerate(here.bodies):
        angle = getattr(body, "angle", 0.0) or (index * 1.1)
        radius = getattr(body, "orbit", index + 1) or (index + 1)
        contacts.append({
            "kind": "body", "name": body.name, "bearing": angle,
            "range": float(radius), "surveyed": bool(body.surveyed),
            "relic": bool(getattr(body, "relic", None)),
        })
    reach = st.sensor * SCOPE_MARGIN
    neighbours = []
    for system in game.galaxy.systems:
        if system.id == here.id:
            continue
        span = distance(system, here)
        if span > reach:
            continue
        neighbours.append({
            "kind": "system", "name": system.name,
            "bearing": math.atan2(system.y - here.y, system.x - here.x),
            "range": span, "bloom": system.bloom,
            "port": bool(system.port),
        })
    return {
        "title": "Scope",
        "sensor": st.sensor, "reach": reach,
        "contacts": contacts, "neighbours": neighbours,
        "fraction": min(1.0, len(neighbours) / 8.0),
        "band": "bad" if any(n["bloom"] > 0.4 for n in neighbours) else "good",
        "note": (f"{len(contacts)} bodies here · {len(neighbours)} stars "
                 f"within {reach:.1f} ly."),
        "unit": "ly",
    }


#: Every instrument, in the order a bridge would lay them out.
INSTRUMENTS = (
    ("power", power), ("heat", heat), ("integrity", integrity),
    ("hold", hold), ("crew", crew), ("scope", scope),
)
INSTRUMENTS_BY_ID = dict(INSTRUMENTS)


def read(game, instrument_id: str) -> dict:
    reader = INSTRUMENTS_BY_ID.get(instrument_id)
    return reader(game) if reader else {}


def all_readings(game) -> dict:
    return {name: reader(game) for name, reader in INSTRUMENTS}
