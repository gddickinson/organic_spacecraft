"""What the ship brings to a fight that has not started yet.

Measured, on a fresh chronicle with nothing shooting:

    the battle screen      2 labels — "No engagement / Nothing is shooting
                           at you", and a Back button
    the gunner's window    1 label
    hulls in the system    5

So a captain could see five hulls on the chart and had nowhere at all to ask
the only question that matters about them: *what happens if one of those turns
on me?* Every number needed to answer it existed — `sim/assessment.py` weighs
two hulls against each other, `sim/firing.py` says which mounts bear,
`sim/gunnery.py` prices a volley in heat, `sim/stations.py` says what taking a
seat is worth — and every one of them takes a `Battle`, which is a thing that
only exists once you are already being shot at.

**So the report is a dry run of the fight, not a second set of formulas.**
`sparring` builds the same `Battle` the game would build if that hull opened
fire — through `combat.start`, off `encounters.make_enemy`, at the band a real
engagement opens at because it does not pass one — and then every figure is
read off it with the functions the fight itself uses. There is no arithmetic
here that a fight would not do. That is the same rule the docking forecast and
the turn plan are held to: a forecast is a *rehearsal of the act*, and anything
else is a second door waiting to disagree.

The ship it rehearses with is a copy. A readiness report a captain opens
twenty times an hour may not put a scratch on the hull, and `combat` is full of
functions that spend ammunition and add heat.
"""

from __future__ import annotations

import copy

from . import assessment, combat, consorts as consort_sim, encounters
from . import firing, gunnery, stations, tactical as tac, traffic
from ..core.rng import RNG

#: What a report is quoted against when there is no particular hull to name:
#: the faction that actually has hulls here, so "what if this goes wrong"
#: means the patrol on the chart rather than an abstraction.
FALLBACK_FACTION = "freeholds"


def opponent(game, hull=None) -> dict:
    """The enemy the game itself would build out of a hull on the chart."""
    faction = (getattr(hull, "faction", None)
               or (traffic.present_factions(game) or [FALLBACK_FACTION])[0])
    rng = RNG(f"{game.seed}:readiness:{getattr(hull, 'id', 'anyone')}")
    made = encounters.make_enemy(rng, faction,
                                 encounters.typical_threat(game))
    if hull is not None:
        made["name"] = f"{hull.name} ({hull.kind_name})" if hasattr(
            hull, "kind_name") else hull.name
        made["faction"] = hull.faction
    return made


def sparring(game, hull=None):
    """The fight that is not happening, built the way a real one is.

    No `band` argument on purpose. `ui/battle_view.begin` does not pass one
    either, so the opening range is `combat.start`'s and there is exactly one
    answer to what "opening range" means. A constant here would be a second.

    No `rng` argument either: with one, `tactical.initial_layout` scatters the
    opening aspect, and a readiness board that reshuffles the geometry every
    time it repaints is a board nobody can read. Bow-on at the opening band is
    the honest neutral case, and the aspect a captain can change is exactly
    what the *live* plot is for.
    """
    ship = copy.deepcopy(game.ship)
    return combat.start(
        ship, game.ship_stats, opponent(game, hull),
        bonuses=game.bonuses, officers=game.officers,
        rep=game.rep.get(getattr(hull, "faction", None), 0.0),
        game=None, fleet=[copy.deepcopy(s) for s in consort_sim.escorts_of(game)])


def volley_cost(b) -> dict:
    """What everything that bears would cost the hull, priced by the trigger."""
    bearing = [shot.mount_id for shot in gunnery.mounts(b) if shot.can_fire]
    quoted = gunnery.quote(b, bearing)
    return {
        "mounts": len(bearing),
        "heat": quoted["heat_added"],
        "now": quoted["heat_now"],
        "after": quoted["heat_after"],
        "cap": gunnery.ceiling(b.player),
        "fault": gunnery.fault_line(b.player),
        "over": quoted["heat_after"] > gunnery.fault_line(b.player),
    }


def report(game, hull=None) -> dict:
    """Everything a tactical board needs about a fight nobody has started."""
    return of(sparring(game, hull), game)


def of(b, game) -> dict:
    """The same report, off whichever battle it is handed.

    **Split from `report` because the board has to work both ways.** The
    tactical window kept calling `report` while an engagement was running, so
    it built a *rehearsal* against a hull the sector might send and printed it
    under a title naming the ship actually shooting: the window said
    "Freeholds GRAFT «Margin Call», turn 1" across the top and "against
    Charter CORAL «Long Consent»" underneath. Caught by rendering the window
    mid-fight and reading the picture, which is the only way that class of
    fault ever shows up — every individual number was correct.

    One report, two ways to get a battle: `sparring` rehearses one, and a
    live engagement is simply passed in.
    """
    heat = volley_cost(b)
    return {
        "against": b.enemy_name,
        "band": b.band,
        "band_name": combat.BANDS[b.band],
        "weight": assessment.weight(b),
        "guns": assessment.mounts(b),
        "shots": firing.solution(b.player, b.enemy, b.band),
        "wants": assessment.preferred_band(b.player),
        "outrun": assessment.can_outrun(b),
        "heat": heat,
        "seats": stations.seat_value(b.player, game.officers),
        "consorts": [c.name for c in b.consorts],
        "turn_to_bear": firing.turn_to_bear(b.player, b.enemy),
        #: Where the opponent sits relative to the bow, for the boresights to
        #: mark. Off the sparring geometry rather than worked out again, so a
        #: sight showing a mount bearing is a mount `firing.solution` agrees
        #: bears.
        "bearing": tac.relative_bearing(b.player.body, b.enemy.body),
        "battle": b,
    }


def threats(game) -> list:
    """Hulls in this system, nearest first, with what each one is.

    Distance comes from `traffic.reach_to`, which measures from
    `flight.ship_position` — the one door — so this list moves when the ship
    does. Before there *was* one door it could not: the ship had no position
    in a system, so every hull in it read as the same distance away.

    **In AU, and the field says so.** `berthing.reach_to` and
    `traffic.reach_to` are two functions of the same name in different
    modules answering in different units, and the first draft of this divided
    the AU figure by a million and reported a hull three astronomical units
    off as being at zero.
    """
    here = traffic.in_system(game)
    out = []
    for hull in here:
        out.append({
            "hull": hull,
            "name": hull.name,
            "kind": hull.kind_name,
            "faction": hull.faction,
            "hostile": hull.hostile,
            "range_au": traffic.reach_to(game, hull),
            "bearing": traffic.bearing_to(game, hull),
            "doing": hull.doing,
        })
    return sorted(out, key=lambda row: (not row["hostile"], row["range_au"]))


#: Kilometres in an astronomical unit. `traffic` answers in AU and a captain
#: two hundred thousand km from something does not want to read "0.00 AU".
KM_PER_AU = 149_597_870.7


def span(au: float) -> str:
    """A distance a captain can read, in the units that suit it.

    "Alongside" is not a rounding: it is `berthing.REACH_KM`, the game's own
    threshold for close enough to take the conn to — so a hull this list calls
    alongside is one the conn will actually open on. A hull holding station at
    the body you are moored to comes out at exactly zero AU, because in the
    flight model that is precisely where it is.
    """
    from . import berthing
    km = au * KM_PER_AU
    if km <= berthing.REACH_KM:
        return "alongside"
    if au < 0.01:
        return f"{km:,.0f} km"
    return f"{au:.2f} AU"


def _off(au: float) -> str:
    """`span` as a phrase — "alongside" takes no "off" after it."""
    said = span(au)
    return said if said == "alongside" else f"{said} off"


def standing(game) -> str:
    """One line: is anything out there, and does it mean you harm."""
    rows = threats(game)
    hostile = [r for r in rows if r["hostile"]]
    if hostile:
        near = hostile[0]
        return (f"{len(hostile)} hostile of {len(rows)} hulls here — "
                f"{near['name']} {_off(near['range_au'])}.")
    if rows:
        return (f"{len(rows)} hulls here, none of them hostile. Nearest "
                f"{rows[0]['name']}, {_off(rows[0]['range_au'])}.")
    return "Nothing else under way in this system."
