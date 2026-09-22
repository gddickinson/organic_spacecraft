"""The game state, and the clock that moves it.

Everything else reads a :class:`Game` and calls :meth:`Game.advance_days`.
Nothing else owns time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..data.tech import bonuses
from ..sim import colony as colony_sim
from ..sim import diplomacy as dip_sim
from ..sim import loyalty as loyalty_sim
from ..sim import research as research_sim
from ..sim import xeno as xeno_sim
from ..sim.ship import Ship, build_layers, make_ship, stats
from ..world.galaxy import Galaxy
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
    #: Where the hull is when it is alongside *nothing*, in AU. Written by
    #: `sim/flight.stand_off` and read through `sim/flight.ship_position`,
    #: which is the one door. Alongside a body the position is the body's,
    #: worked out from the calendar rather than copied here — a copy would go
    #: stale the first time the clock moved, and a hull in orbit is not parked
    #: in space. None both for that case and for a save written before there
    #: was a position at all.
    ship_xy: tuple | None = None
    #: Things that have been shoved off station and have not got back yet,
    #: by contact id. See `sim/knock.py`: `track.at` adds what each has come
    #: to, so a struck quay is off station everywhere the game reads a
    #: position rather than only in the log line about hitting it.
    knocks: dict = field(default_factory=dict)
    #: Traffic addressed to this captain — see `sim/comms.py`. Declared here
    #: rather than attached on first use, because `core/save` walks a
    #: dataclass's *fields*: an attribute set at runtime is invisible to it,
    #: and an unanswered despatch that does not survive a reload is a
    #: question the game forgot it asked.
    signals: list = field(default_factory=list)
    signal_marks: dict = field(default_factory=dict)
    #: The radius from that body's centre, in km, that the ship is holding.
    #: Zero means an orbit whose height nobody chose — which is every orbit
    #: made before the conn could be asked for one, and is read as standard.
    orbit_alt_km: float = 0.0
    #: **The berth the hull is made fast to** (`sim/anchorage` id), or ""
    #: when it is only in orbit — near things, alongside nothing a crew can
    #: walk across to. Set by coming alongside (`sim/crossing.dock`, or a
    #: conn that ends alongside), cleared whenever the hull moves
    #: (`sim/flight.hold_at`, `stand_off`). A new chronicle starts made fast
    #: at its home quay.
    berth: str = ""
    #: The place the crew has crossed to (`sim/places` id): by the gangway,
    #: the ship's boat, their shuttle or suits on a line (`sim/crossing`).
    #: A place's doors are open to a crew that is across. Cleared with the
    #: berth.
    ashore: str = ""
    colonies: list = field(default_factory=list)
    #: Machines you own — see `sim/robots.py`. Hands that are not people, and
    #: kept apart from `officers` because almost nothing about them is the
    #: same: they are built rather than hired, worn rather than tired, and
    #: what they are worth depends on how far away they are working.
    robots: list = field(default_factory=list)
    building: list = field(default_factory=list)
    flags: dict = field(default_factory=dict)
    #: What the captain owns personally, by `data/kit.py` id, and what is on
    #: account at a counting house. Both are the captain's rather than the
    #: ship's: a hull is sold, a hold is emptied, and the coat and the money
    #: in the bank are still yours. See `sim/shore.py`.
    kit: list = field(default_factory=list)
    deposited: float = 0.0
    #: What a concourse has done to the people aboard (`sim/clinic.py`), all
    #: three keyed by the officer's id **as a string**, because a save is
    #: JSON and JSON has no integer keys — a dict keyed by `officer.id` came
    #: back from a reload keyed by `"3"` and silently belonged to nobody.
    #: `fitted` is what is in them and stays in them; `taught` is skills paid
    #: for and learned, added on top of the derived service record; `iced` is
    #: who is in cold storage, and where, and since when.
    fitted: dict = field(default_factory=dict)
    taught: dict = field(default_factory=dict)
    iced: list = field(default_factory=list)
    #: Standing arrangements with a clinic: who is on anagathics, since
    #: when, and how far they are paid up. Traveller's whole economy turns
    #: on a payment falling due; this is the first one in the Verge that
    #: goes on costing after the ship has left.
    courses: list = field(default_factory=list)
    log: list = field(default_factory=list)
    discovered: dict = field(default_factory=dict)
    xeno_study: dict[str, float] = field(default_factory=dict)
    expedition: object | None = None
    contracts: list = field(default_factory=list)
    shocks: list = field(default_factory=list)
    ventures: list = field(default_factory=list)
    transit: object | None = None
    dig: object | None = None
    #: **Who is flying her, and from where.** One `sim/conn.Conn` for the
    #: whole ship: the Pilot screen and the Conn window are two views of it,
    #: not two flights. Measured before this existed: 290.9 km flown and 60
    #: minutes elapsed on the Pilot screen, and opening the Conn showed a ship
    #: 12.0 km out with full tanks and no time passed — two independent
    #: flights of one hull.
    #:
    #: It belongs here for the reason `ui/window.py` gives beside the other
    #: such states: "an approach, an exchange and a crossing all belong to the
    #: game rather than to the window — a save taken in the middle of one used
    #: to lose it."
    #: **Not saved, deliberately, and that is not a shrug.** A `Conn` holds a
    #: `sim/targets.Target`, a clearance and a sky, none of which
    #: `core/save.register` knows — writing it produced a save that would not
    #: read back at all: "save refers to unknown type 'Target'". Leaving it
    #: out keeps saving exactly as it was before the conn moved here, which is
    #: to say a flight does not survive a save. Making it survive is a matter
    #: of registering the chain, and is worth doing on its own.
    conn: object | None = field(default=None, compare=False,
                                metadata={"transient": True})
    #: Her craft, and the sortie one is out on — transient (`sim/craft.py`).
    craft: list = field(default_factory=list)
    sortie: object | None = field(default=None, compare=False,
                                  metadata={"transient": True})
    #: The engagement, while one is running. Like the envoy and the situation
    #: above, it is something you can be in the middle of, so it lives here —
    #: and it has to, because rules ask whether the shooting has started
    #: (`sim/craft.can_launch` refuses a sortie mid-battle). It was kept on
    #: the window alone, so that refusal had never once fired and
    #: `ui/gunnery_view` read an attribute that did not exist. Transient:
    #: time does not pass while you are being shot at, and a save taken
    #: mid-fight would restore a fight nothing could finish.
    battle: object | None = field(default=None, compare=False,
                                  metadata={"transient": True})
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
    #: What the powers have on you: charges, judgment debts and the warrants
    #: in force. One saved object for the whole governance layer — see
    #: `sim/law.py`, which is the only thing allowed to build one.
    law: object | None = None
    #: The powers' treasuries: what each earns from its ports, what holding
    #: them costs, and what it has built or given up. See `sim/exchequer.py`.
    exchequer: object | None = None
    #: Which powers have been licensed which of the captain's processes, and
    #: what was paid for each. See `sim/industry.py`.
    industries: object | None = None
    #: People the powers have put on the ground, what each works, and when it
    #: was founded. See `sim/settlement.py`.
    settlements: list = field(default_factory=list)
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
    #: Hulls the captain has marked as enemies. See `sim/hostiles`.
    hostiles_state: object | None = None
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
    #: The id counters (`core/ids.py`), written at every save so a chronicle
    #: resumed in a fresh process never issues an id it already holds.
    ids: dict = field(default_factory=dict)
    #: Days of hunger banked against the crew (`sim/upkeep.py`). Set at
    #: runtime until 2026-09 and therefore dropped by every reload — a crew
    #: twelve days from losing a hand came back with a clean slate.
    short_days: float = 0.0
    #: Seconds spent flying by hand, for the tutorial's "fly five minutes".
    conn_seconds: float = 0.0
    #: The fraction of a crew member a failing lineage has shed, carried so
    #: the losses come as a slope and survive a save.
    crew_leaving: float = 0.0
    hunt: object | None = None  # innovation 3, nemeses: sim/nemeses.HuntState
    house: object | None = None  # innovation 5: sim/freightlines.TradingHouse
    assembly: object | None = None  #: Innovation 6, the Assembly: sim/assembly
    kith: object | None = None  #: Innovation 2, the Kith: sim/kith.KithState
    renown: object | None = None  #: Innovation 9, renown: sim/renown
    sky: object | None = None  #: Innovation 7, the living sky: sim/phenomena
    #: Afoot (`sim/afoot.py`): a walk in progress, if a party is out on a
    #: deck; the stamina each of them is still missing from the last one, by
    #: officer id as a string (and "captain"); and what the walks have left
    #: behind them — emptied lockers by site and season, the words had with
    #: officers, the fallen, and a short history.
    afoot: object | None = None
    wounds: dict = field(default_factory=dict)
    walked: dict = field(default_factory=dict)
    #: Stakes held in the trade's establishments (`sim/establishments.py`),
    #: by place id: what was paid, and the day the takings were last shared
    #: and last reported.
    stakes: dict = field(default_factory=dict)

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
        # Officers *and* the machines standing a watch. One door, because a
        # bridge does not care what a hand is made of — `sim/robots.standing`
        # hands back objects shaped the way `ship.stats` already reads, with
        # the level each machine is actually working at where it stands.
        from ..sim import craft as craft_sim
        from ..sim import robots as robots_sim
        # An officer out in a craft is not at their station (`sim/craft`):
        # the cockpit is not the bridge, and the numbers say so while they
        # are away.
        self.ship_stats = stats(
            self.ship, self.bonuses,
            craft_sim.at_stations(self) + robots_sim.standing(self))
        # And what the machines *do*, as opposed to what they stand. A watch is
        # a level on a stat the bridge reads; a duty is a pair of hands on the
        # hull — a Hullwright's welding, a Stevedore's stowing, a Scarab's rig.
        # Both land on `Stats` because that is the one door everything
        # downstream already asks: `mining.rig_of` walks the rig stats,
        # `repair_tick` reads regen, `damage` reads crew_guard.
        for key, value in robots_sim.aboard_effects(self).items():
            setattr(self.ship_stats, key,
                    getattr(self.ship_stats, key, 0.0) + value)
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

    def wait_days(self, days: int, ignoring=()) -> dict:
        """Sit still for a spell, standing down on news worth a hand.

        The door for a *voluntary* wait — `clock.wait_days` says why it is
        not the same call as `advance_days`, which stays exact for work
        that bills its own time.
        """
        from . import clock
        return clock.wait_days(self, days, ignoring)

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
        from ..sim import memoir as memoir_sim      # the career, written up
        memoir_sim.record(self)

    # ── persistence ────────────────────────────────────────────────────────

    def to_save(self) -> dict:
        return {"game": self}

    def save(self) -> bool:
        return save_mod.write(self.to_save())


# Loading, checking and clearing the chronicle on disk live in `core/loading.py`
# (split out at 500 lines); opening a new one lives in `core/state_begin.py`
# (split out the same way, the second time this file reached the ceiling).
# Both are re-exported, so `state.load_game` and `state.new_game` stay the door.
from .loading import (begin_new, clear_save, has_save,  # noqa: E402,F401
                      load_game, load_problem, validate)
from .state_begin import new_game  # noqa: E402,F401
