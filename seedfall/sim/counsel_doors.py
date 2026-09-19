"""The counsel sources for the doors the later systems opened: the next
step on the leading ending track, the Reaches, the Assembly, a trading
house, a bounty, the living hull and (behind a guard) an officer's arc.

Same rules as `sim/counsel_sources`: a move is offered only when its act
would go through today, or with the act's own refusal in `blocked`.
"""

from __future__ import annotations

from .counsel_kit import S, hop_to, in_market, nearest
from .counsel_sources import HUNT_FIRE, HUNT_HULL, SITTING_DAYS

#: The purse a charter is suggested at: the fee (waived for a Captain), the
#: house's reserve and a used TENDER all-in — `reviews/.../changes/lines.md`
#: measured ₡27,231 for the bot's one hull.
HOUSE_PURSE = 30_000


#: Where the next rung ranks: below the desk's best run (70) on the track
#: that merely leads, above it on a road the captain chose to follow — a
#: rich careful captain otherwise flew freight for three years with a melt
#: head fitted and never dived (measured, seeds s2 and s3).
RUNG, CHOSEN = 58, 75


def milestone(game, track: str | None) -> list:
    """The next rung on the road counsel steers by, and the act that climbs
    it when there is one to press here."""
    from . import renown
    if track is None:
        return []
    row = renown.next_step(game, track)
    if row is None:
        return []
    chosen = bool(renown.ensure(game).course == track)
    # Only a move that does something is promoted; "look at the Voyage" is
    # never worth more than a real errand.
    return [dict(s, weight=CHOSEN) if chosen and s["verb"] != "go" else s
            for s in _rung(game, track, row)]


#: Days into a career before counsel asks which road to follow.
CHOOSE_AFTER = 90


def choose(game) -> list:
    """No road chosen yet: say so, once the first season is over.

    Measured on the careful captain, seeds s1-s5 over five years: steering
    by whichever track merely leads (the Cartel's quotes, nearly always)
    reached no ending at all; following Genesis reached it on nine seeds of
    ten (s1-s10)."""
    from . import renown
    st = renown.state(game)
    if game.day < CHOOSE_AFTER or (st is not None and st.course):
        return []
    lead = renown.leading(game)
    return [S("course", "Choose a road to follow",
              "Ten endings, each a ladder on the Voyage"
              + (f"; {lead.title()} is furthest along" if lead else "")
              + ". Follow one and counsel steers by it.", "empire", "voyage",
              weight=30)]


def _rung(game, track: str, row: dict) -> list:
    m = row["milestone"]
    terms = row["terms"]
    pays = f" It pays {terms['words']}." if terms["words"] else ""
    why = f"Next on the road to {track.title()}: {m.feeds}.{pays}"
    if m.fact in ("dives", "contact"):      # contact is made on a dive, too
        if not game.ship_stats.can_dive:
            return _to_yard(game, "Fit a melt head",
                            "Nothing gets under the ice without one. " + why)
        dive = _dive_here(game)
        if dive is not None:
            return [S("milestone", f"Dive at {game.system.bodies[dive].name}",
                      why, "system", verb="dive", args={"body": dive},
                      weight=RUNG)]
        ocean = nearest(game, lambda s: s.visited and any(
            b.biome == "subsurface" and b.surveyed for b in s.bodies))
        move = hop_to(game, ocean) if ocean else None
        if move:
            return [S("milestone", f"Make for the ocean at {ocean.name}",
                      why, "map", system=ocean.id, weight=RUNG, **move)]
    return [S("milestone", m.name, why, m.screen or "empire",
              "voyage" if not m.screen else "", weight=RUNG)]


def _to_yard(game, title: str, why: str) -> list:
    """The shipyard screen here, or the next jump toward the nearest yard."""
    here = game.system
    if here.port and "shipyard" in here.port.services:
        return [S("milestone", title, why, "yard", weight=RUNG)]
    yard = nearest(game, lambda s: s.port is not None
                   and "shipyard" in s.port.services)
    move = hop_to(game, yard) if yard else None
    if not move:
        return []
    return [S("milestone", f"{title} at {yard.name}", why, "map",
              system=yard.id, weight=RUNG, **move)]


def _dive_here(game) -> int | None:
    if not game.ship_stats.can_dive:
        return None
    from .ship import hull_pct
    if hull_pct(game.ship) < 0.6:
        return None
    return next((i for i, b in enumerate(game.system.bodies)
                 if b.biome == "subsurface"), None)


def reaches(game) -> list:
    """A deep anchor with its project begun: the next step, or the relight."""
    from . import relight
    for row in relight.standing(game):
        if row["open"] or row["done"] == 0:
            continue
        spec = row["region"]
        said = relight.preview(game, spec.id)
        if said["ok"]:
            return [S("relight", f"Relight the anchor to {spec.name}",
                      f"₡{said['credits']:,}, the goods and {said['days']} "
                      "days, and the region behind it opens.", "system",
                      verb="relight", args={"region": spec.id}, weight=45)]
        anchor = game.galaxy.systems[row["anchor_id"]]
        if said["here"] or anchor.id == game.location_id:
            return [S("relight", f"The anchor to {spec.name}", said["why"],
                      "system", verb="relight", args={"region": spec.id},
                      weight=44, blocked=said["why"])]
        move = hop_to(game, anchor)
        if move:
            return [S("relight", f"Make for the anchor at {anchor.name}",
                      said["why"], "map", system=anchor.id, weight=44,
                      **move)]
    return []


def assembly(game) -> list:
    """The next sitting, if it is near and you are not at the seat."""
    from . import assembly as assembly_sim, assembly_session
    st = assembly_sim.state(game)
    if st is None or not st.announced:
        return []
    days = st.next_day - game.day
    if not 0 < days <= SITTING_DAYS:
        return []
    _power, seat = assembly_session.seat(game, st)
    if seat is None or seat.id == game.location_id:
        return []
    move = hop_to(game, seat)
    if not move:
        return []
    return [S("assembly", f"The Assembly sits at {seat.name}",
              f"In {days} days, with {len(st.agenda)} motions on the order "
              "paper. Present, your speech moves votes.", "map",
              system=seat.id, weight=35, **move)]


def house(game) -> list:
    """A charter when the purse can carry a house; a line for an idle hull."""
    from . import freightlines, haulers
    held = getattr(game, "house", None)
    if held is None:
        if not in_market(game) or game.credits < HOUSE_PURSE:
            return []
        terms = freightlines.charter_terms(game)
        if not terms["ok"]:
            return []
        fee = f"₡{terms['fee']:,}" if terms["fee"] else "no fee — waived"
        return [S("house", "Charter a trading house here",
                  f"{fee}, ₡{terms['upkeep']:,} a month. A hauler of your "
                  "own on a line earns while you fly.", "empire", "house",
                  verb="charter", weight=55)]
    idle = [ship for ship, ok, _why in haulers.haulers(game) if ok]
    if idle:
        return [S("line", f"Put the {idle[0].name} on a line",
                  "A hauler of yours is standing idle; the new-line dialog "
                  "prices the desk's three best runs.", "empire", "house",
                  weight=55)]
    return []


def bounty(game) -> list:
    """Paper you can win: a raider, when the guns and the hull are up to it."""
    from . import hunts
    from .ship import hull_pct
    if not in_market(game) or hunts.taken(game):
        return []
    fire = sum(w.wpn.dmg for w in game.ship_stats.weapons)
    if fire < HUNT_FIRE or hull_pct(game.ship) < HUNT_HULL:
        return []
    rows = [r for r in hunts.board(game) if not r["taken"]
            and r["kind"] == "raider"]
    if not rows:
        return []
    row = max(rows, key=lambda r: (r["reward"], -r["system_id"]))
    return [S("bounty", f"Take the paper on the {row['name']}",
              f"₡{row['reward']:,} from the {row['issuer'].title()}, working "
              f"{row['where']}. Your guns throw {fire:.0f}.", "law", "hunts",
              verb="take_bounty", args={"key": row["key"]}, weight=50)]


def body(game) -> list:
    """An adaptation emerging, waiting on encourage, suppress or leave it."""
    from . import adaptation
    ship = game.ship
    if not adaptation.adapts(ship) or not getattr(ship, "emerging", None):
        return []
    return [S("adaptation", "The hull is changing",
              "An adaptation is emerging. Encourage it, suppress it, or it "
              "sets in by itself.", "ship", "body", weight=45)]


def arcs(game) -> list:
    """An officer's arc beat waiting (`sim/arcs`, when it has landed)."""
    from .renown_facts import wave_b
    if wave_b(game, "arcs:waiting") <= 0:
        return []
    return [S("arc", "An officer wants a word",
              "A beat of an officer's story is waiting in the despatches.",
              "despatches", weight=40)]


def save_money(game) -> list:
    """Nothing better to do at a quay with survey data aboard: sell it."""
    if not in_market(game) or game.ship.cargo.get("survey", 0) < 1:
        return []
    return [S("sell_survey", "Sell the survey data",
              "Survey sets in the hold are worth money at this counter.",
              "port", "market", verb="sell_survey", weight=66)]
