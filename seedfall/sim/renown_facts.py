"""What a milestone reads: named numbers, each computed from state the rules
already keep.

`FACTS` is the registry `data/milestones` names by key. Every function takes
the game and returns a number; nothing here writes. The daily check computes
only the facts some unreached milestone still asks for (`sim/renown.check`),
so a captain with most of the ladder climbed pays for almost none of this.

A fact written `"<module>:<key>"` is read from `seedfall.sim.<module>`'s
`progress(game)` dict behind an import guard — the door the Kith, phenomena
and officer arcs (built alongside this) expose, so their milestones are one
row each once they land, and a tree without them reads zero.
"""

from __future__ import annotations

import importlib

from ..data.tech import STARTING_TECH, TECH_BY_ID

#: A hull this big or bigger is "NAVIS size" for Lineage's third step.
NAVIS_HULL = 1400

#: Facts read from `RenownState.counts`, which only acts done since renown
#: existed have fed: a chronicle from before it reads nought for these.
COUNTED = ("sales", "survey_sales", "fights", "victories", "talked_down",
           "dives", "cleansed")


def _count(game, key: str) -> float:
    """A counter kept by `sim/renown.note` for acts that leave no state."""
    st = getattr(game, "renown", None)
    return float(getattr(st, "counts", {}).get(key, 0)) if st else 0.0


def _battles(game, *results) -> float:
    """Engagements settled (`aftermath.resolve` counts each by its end)."""
    st = getattr(game, "renown", None)
    counts = getattr(st, "counts", {}) if st else {}
    return float(sum(v for k, v in counts.items() if k.startswith("battle:")
                     and (not results or k[7:] in results)))


def _flag(key: str):
    return lambda g: 1.0 if (getattr(g, "flags", None) or {}).get(key) else 0.0


def _surveyed(game) -> float:
    return float(sum(1 for s in game.galaxy.systems for b in s.bodies
                     if b.surveyed))


def _quotes(game) -> float:
    """Living prices on the register, counted as the Cartel counts them."""
    from . import market as market_sim
    systems = game.galaxy.systems
    return float(sum(1 for k in game.register if str(k).isdigit()
                     and int(k) < len(systems)
                     and systems[int(k)].market is not None
                     and systems[int(k)].region == "verge"
                     and market_sim.confidence(
                         market_sim.age_of(game, int(k))) > 0.5))


def _quote_share(game) -> float:
    markets = sum(1 for s in game.galaxy.systems
                  if s.market is not None and s.region == "verge")
    return _quotes(game) / markets if markets else 0.0


def _learned(game) -> list:
    return [t for t in game.research.unlocked if t not in STARTING_TECH]


def _tier(game) -> float:
    return float(max((TECH_BY_ID[t].tier for t in _learned(game)
                      if t in TECH_BY_ID), default=0))


def _xenotech(game) -> float:
    from . import xeno
    return float(len(xeno.incorporated(game)))


def _online(game) -> list:
    return [c for c in game.colonies if c.online]


def _works(game) -> float:
    from . import works
    return float(sum(len(works.done(c)) for c in _online(game)))


def _nemeses(game, status: str | None = None) -> float:
    hunt = getattr(game, "hunt", None)
    roster = getattr(hunt, "nemeses", None) or []
    return float(sum(1 for n in roster
                     if status is None or n.status == status))


def _bounties(game) -> float:
    hunt = getattr(game, "hunt", None)
    if hunt is None:
        return 0.0
    raiders = len((hunt.marks or {}).get("collected", {}))
    return float(raiders + sum(1 for r in hunt.taken if r.get("done")))


def _trophies(game) -> float:
    hunt = getattr(game, "hunt", None)
    return float(len(getattr(hunt, "trophies", None) or []))


def _bloom_fought(game) -> float:
    from . import responses
    return 1.0 if responses.fought(game) > 0 else 0.0


def _clean_days(game) -> float:
    law = getattr(game, "law", None)
    filed = [c.filed_on for c in getattr(law, "charges", None) or []
             if c.filed_on >= 0]
    return float(game.day - max(filed) if filed else game.day)


def _debts_settled(game) -> float:
    law = getattr(game, "law", None)
    return float(sum(1 for d in getattr(law, "debts", None) or []
                     if d.settled))


def _powers(game) -> list:
    from . import diplomacy
    return [game.rep.get(p, 0.0) for p in diplomacy.POWERS]


def _treaties(game) -> float:
    st = getattr(game, "diplomacy", None)
    return float(len(getattr(st, "treaties", None) or []))


def _peace(game) -> float:
    from . import diplomacy
    return float(len(diplomacy.concord_progress(game)["peace"]))


def _weave(game, name: str) -> float:
    st = getattr(game, "weave", None)
    value = getattr(st, name, 0) if st is not None else 0
    return float(len(value) if isinstance(value, list) else value or 0)


def _regions(game) -> float:
    return float(len(getattr(game.galaxy, "regions", None) or []))


def _house(game) -> float:
    return 1.0 if getattr(game, "house", None) is not None else 0.0


def _lines(game) -> float:
    house = getattr(game, "house", None)
    if house is None:
        return 0.0
    return float(len({ln.id for ln in house.lines} | set(house.totals)))


def _trips(game) -> float:
    house = getattr(game, "house", None)
    return float(sum(ln.trips for ln in house.lines)) if house else 0.0


def _sittings(game) -> float:
    st = getattr(game, "assembly", None)
    return float(sum(1 for h in getattr(st, "history", None) or []
                     if h.get("present")))


def _motions_won(game) -> float:
    st = getattr(game, "assembly", None)
    return float(sum(1 for h in getattr(st, "history", None) or []
                     for r in h.get("results", ())
                     if r.get("side") and (r["side"] == "for") == r["passed"]))


def _adaptations(game) -> float:
    return float(sum(len(getattr(s, "adaptations", None) or [])
                     for s in game.fleet))


def _officers(game) -> list:
    from . import lifespan
    return lifespan.active(game.officers)


def _grown(game, big: bool = False) -> float:
    from ..data.chassis import CHASSIS_BY_ID
    from .threat import LINEAGE_EXCLUDES
    out = 0
    for ship in game.fleet:
        chassis = CHASSIS_BY_ID.get(ship.chassis)
        if (chassis is None or chassis.family != "grown"
                or getattr(ship, "launched_on", None) is None
                or ship.chassis in LINEAGE_EXCLUDES):
            continue
        if not big or chassis.hull >= NAVIS_HULL:
            out += 1
    return float(out)


def _ark(game) -> float:
    """How far the ark has grown: its slip's share, or 1 once it flies."""
    if any(s.chassis == "leviathan" for s in game.fleet):
        return 1.0
    return max((j.days / j.need for j in game.building
                if j.chassis_id == "leviathan" and j.need), default=0.0)


def _laid(game) -> float:
    return 1.0 if (any(j.chassis_id == "leviathan" for j in game.building)
                   or any(s.chassis == "leviathan" for s in game.fleet)) \
        else 0.0


def _crewless(game) -> float:
    from ..data.chassis import CHASSIS_BY_ID
    chassis = CHASSIS_BY_ID.get(game.ship.chassis)
    return 1.0 if (chassis is not None and chassis.family == "synthetic"
                   and not game.officers) else 0.0


def _harbours_lost(game) -> float:
    from . import threat
    left, total = threat.harbours_left(game)
    return float(total - left)


def _drowned(game) -> float:
    from ..world.galaxy import verge
    from . import threat
    total = len(verge(game.galaxy))
    return len(threat.bloom_systems(game)) / total if total else 0.0


def _heart(game) -> float:
    from . import bloom
    return 1.0 if bloom.ensure(game).heart_found else 0.0


def wave_b(game, key: str) -> float:
    """`"<module>:<name>"` from `sim/<module>.progress(game)`, or 0.

    The guard is the point: a tree without the module (or with one whose
    `progress` has not got that key yet) reads nothing, and a milestone
    that asks for it simply waits."""
    module, _sep, name = key.partition(":")
    try:
        mod = importlib.import_module(f"{__package__}.{module}")
    except ImportError:
        return 0.0
    progress = getattr(mod, "progress", None)
    if not callable(progress):
        return 0.0
    try:
        said = progress(game)
    except TypeError:
        return 0.0
    value = said.get(name, 0) if isinstance(said, dict) else 0
    if isinstance(value, (list, tuple, set, dict)):
        return float(len(value))
    if isinstance(value, (bool, int, float)):
        return float(value)
    # A word (the nova's phase is one) is not a count: it reads as nothing
    # rather than raising in the daily check.
    return 0.0


FACTS = {
    "surveyed": _surveyed,
    "charted": lambda g: float(len(g.charts_made)),
    "charts_sold": lambda g: float(len(getattr(g, "charts_sold", None) or [])),
    "visited": lambda g: float(sum(1 for s in g.galaxy.systems if s.visited)),
    "lifeforms": lambda g: float(g.discovered.get("lifeforms", 0)),
    "anomalies": lambda g: float(g.discovered.get("anomalies", 0)),
    "landed": _flag("landed"),
    "dug": _flag("dug"),
    "mined": _flag("mined"),
    "fights": lambda g: max(_battles(g), _flag("fought")(g)),
    "victories": lambda g: _battles(g, "destroyed", "struck"),
    "talked_down": lambda g: _battles(g, "parley"),
    "quotes": _quotes,
    "quote_share": _quote_share,
    "contracts": lambda g: float(sum(1 for c in g.contracts if c.done)),
    "taken": lambda g: float(len(g.contracts)),
    "sales": lambda g: _count(g, "sales"),
    "survey_sales": lambda g: _count(g, "survey_sales"),
    "commissions": lambda g: float(sum(1 for c in g.commissions
                                       if getattr(c, "done", False))),
    "credits": lambda g: float(g.credits),
    "techs": lambda g: float(len(_learned(g))),
    "tier": _tier,
    "xenotech": _xenotech,
    "colonies": lambda g: float(len(_online(g))),
    "citizens": lambda g: float(sum(c.pop for c in _online(g))),
    "works": _works,
    "fleet": lambda g: float(len(g.fleet)),
    "rivals": lambda g: _nemeses(g),
    "rivals_dead": lambda g: _nemeses(g, "dead"),
    "rivals_allied": lambda g: _nemeses(g, "allied"),
    "bounties": _bounties,
    "trophies": _trophies,
    "bloom_fought": _bloom_fought,
    "clean_days": _clean_days,
    "debts_settled": _debts_settled,
    "tolerated": lambda g: float(sum(1 for r in _powers(g) if r >= 15)),
    "trusted": lambda g: float(sum(1 for r in _powers(g) if r >= 40)),
    "choir": lambda g: float(g.rep.get("sanhedrin", 0.0)),
    "treaties": _treaties,
    "peace": _peace,
    "transits": lambda g: _weave(g, "transits"),
    "woken": lambda g: _weave(g, "woken"),
    "anchors_read": lambda g: _weave(g, "read"),
    "regions": _regions,
    "house": _house,
    "lines": _lines,
    "trips": _trips,
    "sittings": _sittings,
    "motions_won": _motions_won,
    "adaptations": _adaptations,
    "officer_level": lambda g: float(max((o.level for o in _officers(g)),
                                         default=0)),
    "stations": lambda g: float(len(_officers(g))),
    "days": lambda g: float(g.day),
    "cleansed": lambda g: _count(g, "cleansed"),
    "dives": lambda g: _count(g, "dives"),
    "contact": _flag("contact_made"),
    "heart": _heart,
    "grown": lambda g: _grown(g),
    "grown_big": lambda g: _grown(g, big=True),
    "ark_known": lambda g: 1.0 if "multifront" in g.research.unlocked else 0.0,
    "ark_laid": _laid,
    "ark_grown": _ark,
    "knows_piezolyte": (lambda g: 1.0 if "piezolyte" in g.research.unlocked
                        else 0.0),
    "crewless": _crewless,
    "harbours_lost": _harbours_lost,
    "drowned": _drowned,
}


def fact(game, key: str) -> float:
    """One fact by key; a `module:name` key goes through `wave_b`."""
    fn = FACTS.get(key)
    if fn is not None:
        return fn(game)
    if ":" in key:
        return wave_b(game, key)
    raise KeyError(f"no fact called {key!r}")
