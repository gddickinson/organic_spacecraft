"""Opening a chronicle: the hull, the crew, the berth and the first day.

Split out of `core/state.py` when it reached five hundred lines, along the
same seam `core/loading.py` came off: `state` says what a chronicle *is*,
`loading` says whether the one on disk can be played, and this says how a new
one begins. Re-exported from `state`, so `state.new_game` is still the door
every caller uses.

`Game` and `START_FIT` are imported inside `new_game` rather than at the top,
because `state` imports this module at its own foot: a top-level import here
would be a ring, and the first thing to import `core.state_begin` directly
would break on it.
"""

from __future__ import annotations

from ..data.chassis import CHASSIS_BY_ID
from ..data.factions import FACTIONS
from ..data.tech import STARTING_TECH
from ..sim import crew as crew_sim
from ..sim import inquiry as inquiry_sim
from ..sim import research as research_sim
from ..sim.ship import make_ship
from ..world.galaxy import Galaxy, generate_sector
from . import ids as ids_mod
from .rng import RNG


def new_game(seed: str | None = None, systems: int = 42,
             choices=None):
    """Open a chronicle. `choices` is a `sim.beginning.Choices`.

    With no choices this is *exactly* the game as it shipped, deliberately:
    the whole suite is written against that opening, so a default that quietly
    differed would leave every check passing while measuring something else.
    `beginning.apply` is a set of deltas, and the default origin's deltas are
    all zero.
    """
    import random
    from ..sim import beginning as beginning_sim, passage as passage_sim
    from .state import START_FIT, Game
    seed_str = seed or f"verge-{random.randrange(10 ** 9):x}"
    rng = RNG(f"{seed_str}:start")
    choices = choices or beginning_sim.default()

    galaxy = generate_sector(seed_str, systems)
    # A fresh book of ids for this chronicle, bound before the first hull and
    # officer are made — see `core/ids.bind`.
    book = ids_mod.bind({})
    start = (_pick_start(galaxy) if beginning_sim.is_default(choices)
             else beginning_sim.start_system(galaxy, choices.posting))

    if beginning_sim.is_default(choices):
        chassis = CHASSIS_BY_ID["navis"]
        ship = make_ship("navis", list(START_FIT), choices.name)
    else:
        chassis = CHASSIS_BY_ID[choices.hull]
        known = set(STARTING_TECH) | set(
            beginning_sim.ORIGINS_BY_ID[choices.origin].tech)
        ship = make_ship(chassis.id,
                         beginning_sim.fit_for(chassis, known), choices.name)
    ship.crew = beginning_sim.launch_crew(choices, chassis)
    # Provisioned for what this crew actually consumes — `opening_hold` is the
    # one place that decides, so the opening screen's forecast cannot drift
    # away from what the hold actually contains. It did, within an hour of
    # provisioning starting to depend on lineage.
    ship.cargo = beginning_sim.opening_hold(
        getattr(choices, "stock", None) or "wet", ship.crew)

    game = Game(
        seed=seed_str, galaxy=galaxy, ship=ship, fleet=[ship],
        officers=crew_sim.starting_crew(rng),
        research=research_sim.Research(unlocked=list(STARTING_TECH)),
        rep={f.id: float(f.start_rep) for f in FACTIONS},
        location_id=start.id,
        stores={"ore": 0, "volatiles": 0, "phosphate": 0, "biomass": 0,
                "silicon": 0, "alloy": 0},
        discovered={"systems": [start.id], "bodies": 0, "lifeforms": 0, "anomalies": 0},
        rng_seed=rng.int(1, 2 ** 30),
        ids=book,
    )
    start.visited = True
    start.scanned = True
    # Moored where the log says you are. The opening line reads "under way
    # from <port>" and the game placed the hull at a fixed point four AU out
    # on the system's edge with `orbit_body` unset — so every contact in the
    # system, the home quay included, measured light-minutes away,
    # `berthing.can_conn` refused all of them, and the conn opened on nothing
    # with controls that correctly did nothing. From turn one.
    _moor_at_home(game, start)
    from ..sim import craft as craft_sim
    craft_sim.give(game)                          # a launch in her cradle
    # The hull did not launch yesterday: there is a shakedown cruise's worth of
    # its own data already on the bench.
    inquiry_sim.add(game.research, "survey", 55)
    inquiry_sim.add(game.research, "specimen", 25)
    beginning_sim.apply(game, choices, rng)
    game.recompute()
    game.add_log(f"The {ship.name} is under way from {start.name}.", "good")
    passage_sim.chart(game)       # a boxed-in opening's way out; see there
    if not beginning_sim.is_default(choices):
        game.add_log(beginning_sim.blurb(choices), "")
    return game


def _pick_start(galaxy: Galaxy):
    charter = [s for s in galaxy.systems if s.faction == "charter" and s.port]
    if charter:
        return next((s for s in charter if s.port.capital), charter[0])
    return next((s for s in galaxy.systems if s.port), galaxy.systems[0])


def _moor_at_home(game, start) -> None:
    """Put a new captain **made fast at their home quay**: the hull at its
    berth, the crew free to walk across. A player found the chronicle opening
    with the hull hundreds of kilometres off the Fleet Hub on the flight deck
    while its doors stood open to them.

    Nothing to do in a system with no port: `flight.stand_off` leaves them
    holding at the arrival radius, which is what a jump into an empty system
    means and is now written down rather than assumed.
    """
    from ..sim import anchorage as anchorage_sim
    from ..sim import flight as flight_sim
    body, _index = anchorage_sim.anchor_body(start)
    if body is not None:
        flight_sim.hold_at(game, body)
        if getattr(start, "port", None) is not None:
            game.berth = game.ashore = f"port-{start.id}"
    else:
        flight_sim.stand_off(game)
