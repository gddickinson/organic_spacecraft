"""A captain who engages every officer's story, for `test_arcs` to fly.

Not a suite. It does what a player would: flies to the place a beat names,
fights, burns, plants or buys a round when a beat waits on it, opens a dark
rim when a story waits past it, and answers every despatch through
`sim/comms.answer` — the door the Despatches board uses. On a last beat it
takes the answer that leaves a signature; elsewhere the first answer the
ship can pay for that the officer will not hold against it.

Travel is priced in days by `galaxy.transit_days` and the calendar moves by
`advance_days`, so every story runs on the clock it would in play; the hull
is simply not flown leg by leg, which is `test_flight`'s business, not this.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.arcs import ARCS_BY_ID, LOYAL_AT, QUIET_DAYS
from ..sim import arcs as arcs_sim
from ..sim import comms as comms_sim
from ..world.galaxy import distance, transit_days


def provisioned(game) -> None:
    """Fed, fuelled and solvent: the captain is a clock here."""
    game.credits = max(game.credits, 200_000)
    game.ship.cargo["biomass"] = max(game.ship.cargo.get("biomass", 0), 120)
    game.ship.cargo["volatiles"] = max(game.ship.cargo.get("volatiles", 0), 60)


def chronicle(seed: str):
    game = new_game(seed)
    provisioned(game)
    return game


def deal(game, officer, arc_id: str) -> None:
    """Give `officer` this story from its first beat, on the usual clock."""
    arcs_sim.assign(game)
    for other in game.officers:
        if other is not officer and other.arc == arc_id:
            other.arc = next(a for a in ARCS_BY_ID
                             if a not in {o.arc for o in game.officers})
    officer.arc, officer.arc_beat = arc_id, 0
    officer.arc_state = {"next": max(int(game.day), QUIET_DAYS) + 1,
                         "chose": []}


def at_beat(game, officer, arc_id: str, index: int, *, met: bool = True):
    """Put `officer` at beat `index` of `arc_id`, armed, and — with `met` —
    its condition already true, so the next day opens it."""
    deal(game, officer, arc_id)
    officer.arc_beat = index
    officer.arc_state = {"chose": ["x"] * index, "armed": int(game.day),
                         "due": int(game.day) + 100, "base": -1.0,
                         "place": game.location_id if met else -1}
    officer.loyalty = 60.0
    if met and ARCS_BY_ID[arc_id].beats[index].trigger == "loyalty":
        officer.loyalty = LOYAL_AT


def opened(game, officer):
    """Advance a day and return the despatch the beat opened."""
    provisioned(game)
    game.advance_days(1)
    sig_id = officer.arc_state.get("sig")
    assert sig_id, f"{officer.arc} beat {officer.arc_beat} did not open"
    return next(s for s in comms_sim.inbox(game) if s.id == sig_id)


def open_region(game, region_id: str) -> None:
    from ..world import regions as world_regions
    if world_regions.region(game.galaxy, region_id) is None:
        world_regions.generate(game.galaxy, region_id, game.day)


def arrive(game, system_id: int) -> None:
    """Get there: the crossing's days on the calendar, then the ship."""
    here, there = game.system, game.galaxy.systems[system_id]
    apart = distance(here, there)
    if apart != float("inf") and system_id != here.id:
        game.advance_days(transit_days(apart, game.ship_stats.speed))
    game.location_id = system_id
    there.visited = True


def fight(game) -> None:
    from . import nemesis_kit as kit
    kit.ended(game, kit.plain_fight(game, "bloom", f"arc-fight-{game.day}"),
              "destroyed")


def burn(game) -> None:
    """Burn a Bloom mass for real, with guns enough for it. Early on the only
    mass is the heart, which no opening hull can touch — so the captain goes
    after a small one thrown next door, as a player would wait for one."""
    from ..sim import actions
    from . import nemesis_kit as kit
    if sum(w.wpn.dmg for w in game.ship_stats.weapons) < 35:
        game.ship = kit.warfit(game)
        game.fleet = [game.ship]
        game.recompute()
    target = next(s for s in game.galaxy.systems
                  if s.id != game.location_id and s.port is None)
    arrive(game, target.id)
    target.bloom = 0.15
    said = actions.burn_bloom(game)
    assert said.get("ok"), f"the burn was refused: {said.get('why')}"


def plant(game) -> None:
    from ..sim import colony as colony_sim
    if "seed_bay" not in game.ship.fitted:
        game.ship.fitted.append("seed_bay")
    if "bioleach" not in game.research.unlocked:
        game.research.unlocked.append("bioleach")
    game.recompute()
    for key in ("alloy", "ore", "biomass", "volatiles"):
        game.stores[key] = max(game.stores.get(key, 0), 9000)
    for system in [game.system] + list(game.galaxy.systems):
        site = next((b for b in system.bodies if b.colony is None
                     and b.kind in ("asteroid", "moon", "rocky")), None)
        if site is None or system.bloom > 0.5:
            continue
        col, _why = colony_sim.found(game, system, site, "radix_mine")
        if col is not None:
            return
    raise AssertionError("nowhere would take a colony")


def _trusted(game, officer) -> None:
    from ..sim import crew as crew_sim
    for _ in range(12):
        if officer.loyalty >= LOYAL_AT:
            return
        crew_sim.pay_bonus(game)


def _pick(game, sig, officer) -> str:
    """The signature on a last beat; else the kindest answer the ship can pay."""
    beat = ARCS_BY_ID[officer.arc].beats[officer.arc_beat]
    if officer.arc_beat == len(ARCS_BY_ID[officer.arc].beats) - 1:
        return next(c.key for c in beat.choices if c.signature)
    options = [(arcs_sim.preview(game, sig, c.key), c.key)
               for c in beat.choices]
    options = [(p["loyalty"], key) for p, key in options if not p["why"]]
    return max(options)[1]


def engage(game, officer) -> None:
    """One turn of attention to this officer's story."""
    if officer.arc_beat >= 3:
        return
    arc = ARCS_BY_ID[officer.arc]
    beat = arc.beats[officer.arc_beat]
    st = officer.arc_state
    if st.get("sig"):
        sig = next(s for s in comms_sim.inbox(game) if s.id == st["sig"])
        assert comms_sim.answer(game, sig.id, _pick(game, sig, officer)), (
            f"{arc.id}: the answer was refused")
        return
    if st.get("armed") is None:
        return
    place = st.get("place")
    if isinstance(place, str):
        open_region(game, place.split(":", 1)[1])
    elif beat.trigger == "place" and place is not None \
            and game.location_id != place:
        arrive(game, place)
    elif beat.trigger == "event":
        {"fight": fight, "burn": burn, "colony": plant}[beat.arg](game)
    elif beat.trigger == "loyalty":
        _trusted(game, officer)


def see_through(game, officer, days: int = 1400) -> int:
    """Engage every story aboard until this officer's is told, or `days`
    pass. Returns the day it ended."""
    start = game.day
    while officer.arc_beat < 3 and game.day - start < days and not game.dead:
        provisioned(game)
        for anyone in list(game.officers):
            if anyone is officer or anyone.arc_state.get("sig"):
                engage(game, anyone)
        game.advance_days(1)
    return game.day

