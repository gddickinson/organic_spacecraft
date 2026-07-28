"""The game state, and the clock that moves it.

Everything else reads a :class:`Game` and calls :meth:`Game.advance_days`.
Nothing else owns time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..data.factions import FACTIONS
from ..data.tech import STARTING_TECH, bonuses
from ..sim import allegiance
from ..sim import colony as colony_sim
from ..sim import crew as crew_sim
from ..sim import customs as customs_sim
from ..sim import inquiry as inquiry_sim
from ..sim import market as market_sim
from ..sim import diplomacy as dip_sim
from ..sim import responses as response_sim
from ..sim import ventures as venture_sim
from ..sim import loyalty as loyalty_sim
from ..sim import research as research_sim
from ..sim import shipyard as shipyard_sim
from ..sim import threat as threat_sim
from ..sim import xeno as xeno_sim
from ..sim import chains as chain_sim
from ..sim import contracts as contract_sim
from ..sim import territory as territory_sim
from ..data.territory import SEIZED as TERRITORY_SEIZED
from ..sim.ship import (Ship, build_layers, is_breached, make_ship, repair_tick,
                        stats)
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
    #: What landing parties brought back that was not cargo.
    field_notes: list = field(default_factory=list)
    register: dict = field(default_factory=dict)
    commissions: list = field(default_factory=list)
    rumours: list = field(default_factory=list)
    charts: list = field(default_factory=list)
    charts_sold: list = field(default_factory=list)
    boards: dict = field(default_factory=dict)
    diplomacy: object | None = None
    bloom_state: object | None = None
    bloom_clock: float = 0.0
    bloom_total: float = 0.0
    victory: str | None = None
    dead: bool = False
    overgrown: bool = False
    ending: str | None = None
    death_reason: str = ""
    rng_seed: int = 1

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
        self.bonuses = bonuses(self.research.unlocked)
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

    def advance_days(self, n: int) -> None:
        """The only clock in the game."""
        if self.dead or self.victory:
            return
        r = self.rng("tick")
        self.day += n
        st = self.ship_stats

        rate = st.research + 0.25 + self.colony_fx.get("research", 0)
        self.research.last_event = None
        done = research_sim.tick(self.research, n, rate, r)
        if self.research.last_event == "setback":
            self.add_log("The programme has gone backwards — a result nobody "
                         "could replicate, and a season spent on it.", "bad")
        elif self.research.last_event == "breakthrough":
            self.add_log("A breakthrough on the bench. Weeks of work fell out "
                         "in an afternoon.", "good")
        if getattr(self.research, "starved", None) and not done:
            short = ", ".join(self.research.starved)
            if r.chance(0.25):
                self.add_log(f"The bench is short of {short}; the programme is "
                             "marking time.", "warn")
        if done:
            self.recompute()
            from ..data.tech import TECH_BY_ID
            self.add_log(f"Research complete: {TECH_BY_ID[done].name}.", "good")

        customs_sim.cool(self, n)

        for colony, power in territory_sim.seizures(self, n, r):
            self.add_log(TERRITORY_SEIZED.format(colony=colony.name), "bad")

        _gains, events = colony_sim.tick(self, n)
        for kind, text in events:
            self.add_log(text, kind)

        for ship in shipyard_sim.tick_builds(self, n):
            self.add_log(f"{ship.name} is complete and standing by.", "good")

        repair_tick(self.ship, n, st)

        # A smelter bay turns ore into alloy on the way home, which is the
        # difference between hauling rock and hauling money.
        if st.refine > 0:
            ore = self.ship.cargo.get("ore", 0)
            smelted = min(ore, st.refine * 1.5 * n)
            if smelted > 0.01:
                self.ship.cargo["ore"] = ore - smelted
                if self.ship.cargo["ore"] <= 0.0001:
                    self.ship.cargo.pop("ore", None)
                self.ship.cargo["alloy"] = self.ship.cargo.get("alloy", 0) + smelted * 0.45

        for sys in self.galaxy.systems:
            if sys.market:
                tick_market(sys.market, n, r)
        for kind, text in market_sim.tick(self, n, r):
            self.add_log(text, kind)
        market_sim.apply_to_markets(self)
        for kind, text in venture_sim.tick(self, n, r):
            self.add_log(text, kind)
        dip_sim.drift(self, n)

        # Payroll. Miss it and the crew notices immediately.
        wages = crew_sim.daily_wages(self.officers) * n
        paid = self.credits >= wages
        if paid:
            self.credits -= wages
        elif r.chance(0.3):
            self.add_log("Payroll missed. The bridge is very quiet.", "bad")

        # Air. The intima makes it; without one you are drawing on a tank.
        life_layer = next((l for l in self.ship.layers if l.life), None)
        air_ok = (not is_breached(self.ship)
                  and (life_layer is None or life_layer.hp > life_layer.max * 0.2))
        if air_ok:
            self.ship.o2 = min(1.0, self.ship.o2 + 0.06 * n)
        else:
            self.ship.o2 -= n / max(1, st.o2_days)
            if self.ship.o2 <= 0:
                self.ship.o2 = 0
                lost = max(1, round(self.ship.crew * 0.08 * n))
                self.ship.crew = max(0, self.ship.crew - lost)
                self.add_log(f"Air is gone. {lost} of the crew did not make it.", "bad")
                loyalty_sim.record(self, "crew_death")
                if self.ship.crew <= 0:
                    self.die("Nobody left aboard to hold the watch.")
                    return

        crew_sim.morale_tick(self.ship, n, paid, is_breached(self.ship), st.morale)
        crew_sim.grant_xp(self.officers, "*", n * 1.5)
        if is_breached(self.ship):
            loyalty_sim.record(self, "breach", scale=min(2.0, n / 10))
        for kind, text in loyalty_sim.tick(self, n, paid):
            self.add_log(text, kind)

        # Notes banked against a technology whose prerequisites have since been
        # met can finally be made sense of.
        for contract, outcome in contract_sim.check(self):
            if outcome == "done":
                self.add_log(f"Contract complete: {contract.title}. "
                             f"Paid {round(contract.reward):,} credits.", "good")
                if contract.cost:
                    self.add_log("Word gets round who you work for — "
                                 f"{allegiance.phrase(contract.cost)}.", "warn")
                for kind, text in chain_sim.on_contract_done(self, contract):
                    self.add_log(text, kind)
            else:
                self.add_log(f"Contract expired: {contract.title}.", "bad")
                for kind, text in chain_sim.on_contract_failed(self, contract):
                    self.add_log(text, kind)

        for tech in xeno_sim.settle(self):
            self.add_log(f"Xenotechnology incorporated: {tech.name}.", "good")

        for kind, text in threat_sim.tick(self, n, r):
            self.add_log(text, kind)
        response_sim.decay(self, n)
        for kind, text in response_sim.check(self, r):
            self.add_log(text, kind)
        if self.overgrown and not self.victory:
            self.dead = True
            self.ending = "overgrown"

        win = threat_sim.check_victory(self)
        if win:
            self.victory = win
        self.recompute()

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


def new_game(seed: str | None = None, systems: int = 42) -> Game:
    import random
    seed_str = seed or f"verge-{random.randrange(10 ** 9):x}"
    rng = RNG(f"{seed_str}:start")

    galaxy = generate_sector(seed_str, systems)
    start = _pick_start(galaxy)

    ship = make_ship("navis", list(START_FIT), "Patient Increment")
    ship.crew = 34
    ship.cargo = {"ore": 12, "volatiles": 20, "biomass": 18}

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
    game.recompute()
    game.add_log(f"The {ship.name} is under way from {start.name}.", "good")
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
    game.recompute()
    return game


def has_save() -> bool:
    return save_mod.exists()


def clear_save() -> None:
    save_mod.clear()
