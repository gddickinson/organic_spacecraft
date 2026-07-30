"""The game state, and the clock that moves it.

Everything else reads a :class:`Game` and calls :meth:`Game.advance_days`.
Nothing else owns time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..data.chassis import CHASSIS_BY_ID
from ..data.factions import FACTIONS
from ..data.tech import STARTING_TECH, bonuses
from ..sim import allegiance
from ..sim import colony as colony_sim
from ..sim import crew as crew_sim
from ..sim import lifespan as lifespan_sim
from ..sim import customs as customs_sim
from ..sim import inquiry as inquiry_sim
from ..sim import market as market_sim
from ..sim import diplomacy as dip_sim
from ..sim import responses as response_sim
from ..sim import ventures as venture_sim
from ..sim import legacy as legacy_sim
from ..sim import memory as memory_sim
from ..sim import loyalty as loyalty_sim
from ..sim import research as research_sim
from ..sim import shipyard as shipyard_sim
from ..sim import threat as threat_sim
from ..sim import xeno as xeno_sim
from ..sim import chains as chain_sim
from ..sim import contracts as contract_sim
from ..sim import territory as territory_sim
from ..sim import upkeep as upkeep_sim
from ..data.territory import SEIZED as TERRITORY_SEIZED
from ..sim.ship import (Ship, build_layers, cool, is_breached, make_ship,
                        repair_tick, stats)
from ..world.economy import tick_market
from ..world.galaxy import Galaxy, generate_sector
from . import save as save_mod
from .rng import RNG
from .save import register

START_FIT = [
    "reaction_organ", "intima_bloom", "radiator_bloom", "opsin_eyes",
    "bioelectric_net", "silicon_core", "sphincter_seal", "ablative_shed",
    "photic_flash", "mining_root", "cargo_villi", "crew_girdle",
]

MASK = 0xFFFFFFFF


@register
@dataclass
class Game:
    seed: str
    galaxy: Galaxy
    ship: Ship
    fleet: list[Ship]
    officers: list
    research: research_sim.Research
    rep: dict[str, float]
    day: int = 0
    credits: float = 18000
    stores: dict[str, float] = field(default_factory=dict)
    location_id: int = 0
    orbit_body: str | None = None
    #: The radius from that body's centre, in km, that the ship is holding.
    #: Zero means an orbit whose height nobody chose — which is every orbit
    #: made before the conn could be asked for one, and is read as standard.
    orbit_alt_km: float = 0.0
    colonies: list = field(default_factory=list)
    building: list = field(default_factory=list)
    flags: dict = field(default_factory=dict)
    log: list = field(default_factory=list)
    discovered: dict = field(default_factory=dict)
    xeno_study: dict[str, float] = field(default_factory=dict)
    expedition: object | None = None
    contracts: list = field(default_factory=list)
    shocks: list = field(default_factory=list)
    ventures: list = field(default_factory=list)
    transit: object | None = None
    dig: object | None = None
    docking: object | None = None
    decoding: object | None = None
    decoding_tech: str | None = None
    faction_power: dict = field(default_factory=dict)
    #: Per-faction memory of what you have been caught carrying. Decays.
    scrutiny: dict = field(default_factory=dict)
    #: A power waiting on an answer about ground you hold.
    demand: object | None = None
    #: Who is under, how, and since when. A state rather than something you
    #: are part-way through — you can fly, fight and trade with half the crew
    #: asleep. See `sim/dormancy.py`.
    sleep: object | None = None
    #: A power that has come to *you* with a proposition. Like a battle or an
    #: open trench it is something you can be part-way through, so it lives
    #: here with an `.over` flag. See `sim/approach.py`.
    envoy: object | None = None
    #: What landing parties brought back that was not cargo.
    field_notes: list = field(default_factory=list)
    register: dict = field(default_factory=dict)
    #: Day each system's chart was completed. Kept apart from
    #: `register`, which holds price Quotes and nothing else.
    charts_made: dict = field(default_factory=dict)
    #: Who the captain is: stock, origin, hull, posting, crew. Saved, because
    #: the aftermath and the codex both want to know how this one started.
    beginning: object | None = None
    #: Substrate bonuses from the stock, folded in by `recompute`.
    stock_fx: dict = field(default_factory=dict)
    #: Life after an ending: which epoch, how much pressure, what has been
    #: answered. See `sim/legacy.py`.
    legacy: object | None = None
    #: A situation waiting on an answer. Like a battle or an open trench, it is
    #: something you can be in the middle of, so it lives here.
    situation: object | None = None
    #: What everyone in the Verge remembers about you. See `sim/memory.py`.
    minds: dict = field(default_factory=dict)
    #: Player settings, every one of which does something. `sim/options.py`.
    options: object | None = None
    #: The tutorial, if one is running. Like everything you can be part-way
    #: through it lives here and carries an `.over` flag.
    tutorial: object | None = None
    commissions: list = field(default_factory=list)
    rumours: list = field(default_factory=list)
    charts: list = field(default_factory=list)
    charts_sold: list = field(default_factory=list)
    boards: dict = field(default_factory=dict)
    diplomacy: object | None = None
    #: The powers' treasuries: what each earns from its ports, what holding
    #: them costs, and what it has built or given up. See `sim/exchequer.py`.
    exchequer: object | None = None
    #: Which powers have been licensed which of the captain's processes, and
    #: what was paid for each. See `sim/industry.py`.
    industries: object | None = None
    #: The bench's standing work once the tech tree is finished — which
    #: programme it is on, the rounds it has completed and the findings in
    #: hand. A declared field rather than an attribute `programmes.state`
    #: attaches on demand, because the save codec encodes declared fields and
    #: nothing else: set on the side, a chronicle's findings and rounds came
    #: back from a reload as an empty bench.
    programmes: object | None = None
    #: The Weave: which dark anchors have been woken and which laid. Where
    #: the gates *are* is derived from the galaxy's seed, like anchorages.
    weave: object | None = None
    bloom_state: object | None = None
    bloom_clock: float = 0.0
    bloom_total: float = 0.0
    victory: str | None = None
    dead: bool = False
    overgrown: bool = False
    ending: str | None = None
    death_reason: str = ""
    rng_seed: int = 1
    #: Sub-day remainder carried by `advance_days`, so the calendar stays
    #: whole without losing the fractions callers pass.
    _part_day: float = 0.0
    #: Proper time: days the hull and the people in it have actually lived.
    #: `day` is the Verge's clock and drives every deadline; this one drives
    #: ageing, upkeep, repair and research. They diverge whenever a crossing
    #: is flown at dilation, which is the whole point — time is relative, and
    #: a crew that skipped four years did not do four years of work either.
    ship_day: int = 0
    _part_ship: float = 0.0

    # Derived, never saved — recomputed by recompute() on load.
    bonuses: dict = field(default_factory=dict, compare=False,
                          metadata={"transient": True})
    ship_stats: object = field(default=None, compare=False,
                               metadata={"transient": True})
    colony_fx: dict = field(default_factory=dict, compare=False,
                            metadata={"transient": True})

    # ── access ─────────────────────────────────────────────────────────────

    @property
    def system(self):
        return self.galaxy.systems[self.location_id]

    def system_by_id(self, sid: int):
        return self.galaxy.systems[sid]

    def rng(self, tag: str = "") -> RNG:
        """A generator that advances with the save, so reloads do not reroll luck."""
        self.rng_seed = (self.rng_seed * 1664525 + 1013904223) & MASK
        return RNG(f"{self.seed}:{tag}:{self.rng_seed}")

    def add_log(self, text: str, kind: str = "") -> None:
        self.log.append((self.day, text, kind))
        if len(self.log) > 300:
            self.log.pop(0)

    def adjust_rep(self, faction_id: str, delta: float) -> None:
        self.rep[faction_id] = max(-100, min(100, self.rep.get(faction_id, 0) + delta))
        # An officer who believes in the licence takes your standing with the
        # Charter personally. The function doing this existed from the day
        # convictions were written and was called by nothing.
        loyalty_sim.align(self, faction_id, delta)

    # ── derived values ─────────────────────────────────────────────────────

    def recompute(self):
        """Recompute derived values after any change to ship, crew or research."""
        self.bonuses = bonuses(
            self.research.unlocked,
            getattr(self.research, 'provisional', ()))
        # What you are made of is a passive bonus like any other. Without this
        # the opening screen's "superb instruments" was a sentence the
        # simulation never read — the exact defect this project keeps finding.
        for key, value in self.stock_fx.items():
            self.bonuses[key] = self.bonuses.get(key, 0.0) + value
        # Alien work you have incorporated counts alongside your own research.
        for key, value in xeno_sim.bonuses(self).items():
            self.bonuses[key] = self.bonuses.get(key, 0.0) + value
        self.colony_fx = colony_sim.effects(self)
        self.ship_stats = stats(self.ship, self.bonuses, self.officers)
        self.ship_stats.diplomacy += self.colony_fx.get("diplomacy", 0)
        # A signed treaty is berthing rights and a tariff line, which is worth
        # something at every quay. The function computing it existed from the
        # day treaties were added and was called by nothing at all.
        self.ship_stats.trade += dip_sim.treaty_bonus(self)
        return self.ship_stats

    # ── the clock ──────────────────────────────────────────────────────────

    def advance_days(self, n: float, dilation: float = 1.0) -> None:
        """The only clock in the game, and the only place `day` is written.

        The work lives in `core/clock.py`; see it for the sector-time versus
        ship-time split. This stays the single entry point so nothing else
        ever writes the calendar.
        """
        from . import clock
        clock.advance_days(self, n, dilation)

    def die(self, reason: str = "") -> None:
        """Loss — unless a TARDIGRADE vault is holding a copy of the lineage."""
        if self.colony_fx.get("has_vault") and not self.flags.get("vault_used"):
            self.flags["vault_used"] = True
            ship = make_ship("spore",
                             ["reaction_organ", "intima_bloom", "opsin_eyes",
                              "bioelectric_net"], "Second Instar")
            build_layers(ship, self.bonuses)
            self.ship = ship
            self.fleet.append(ship)
            self.credits = max(self.credits, 3000)
            self.recompute()
            self.add_log("The vault opened. A second instar germinated from the "
                         "archived canon. Everything else is gone.", "warn")
            return
        self.dead = True
        self.ending = "lost"
        self.death_reason = reason

    # ── persistence ────────────────────────────────────────────────────────

    def to_save(self) -> dict:
        return {"game": self}

    def save(self) -> bool:
        return save_mod.write(self.to_save())


def new_game(seed: str | None = None, systems: int = 42, choices=None) -> Game:
    """Open a chronicle. `choices` is a `sim.beginning.Choices`.

    With no choices this is *exactly* the game as it shipped, deliberately:
    the whole suite is written against that opening, so a default that quietly
    differed would leave every check passing while measuring something else.
    `beginning.apply` is a set of deltas, and the default origin's deltas are
    all zero.
    """
    import random
    from ..sim import beginning as beginning_sim
    seed_str = seed or f"verge-{random.randrange(10 ** 9):x}"
    rng = RNG(f"{seed_str}:start")
    choices = choices or beginning_sim.default()

    galaxy = generate_sector(seed_str, systems)
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
    )
    start.visited = True
    start.scanned = True
    # The hull did not launch yesterday: there is a shakedown cruise's worth of
    # its own data already on the bench.
    inquiry_sim.add(game.research, "survey", 55)
    inquiry_sim.add(game.research, "specimen", 25)
    beginning_sim.apply(game, choices, rng)
    game.recompute()
    game.add_log(f"The {ship.name} is under way from {start.name}.", "good")
    if not beginning_sim.is_default(choices):
        game.add_log(beginning_sim.blurb(choices), "")
    return game


def _pick_start(galaxy: Galaxy):
    charter = [s for s in galaxy.systems if s.faction == "charter" and s.port]
    if charter:
        return next((s for s in charter if s.port.capital), charter[0])
    return next((s for s in galaxy.systems if s.port), galaxy.systems[0])


def load_game() -> Game | None:
    data = save_mod.read()
    if not data:
        return None
    game = data.get("game")
    if not isinstance(game, Game):
        return None
    # The active ship must be the same object as its entry in the fleet, or
    # damage would apply to a copy.
    for i, f in enumerate(game.fleet):
        if f.uid == game.ship.uid:
            game.fleet[i] = game.ship
            break
    # A chronicle saved before there were two clocks has lived every day the
    # Verge has. Left at zero, a twenty-year captain's crew would be younger
    # than the chronicle and their whole span would come back.
    if not game.ship_day and game.day:
        game.ship_day = game.day
    game.recompute()
    return game


def has_save() -> bool:
    return save_mod.exists()


def clear_save() -> None:
    save_mod.clear()
