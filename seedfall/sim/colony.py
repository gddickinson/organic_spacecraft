"""Colonies — the empire layer.

You plant a seed and leave; it gestates for a year or two and then yields, every
day, wherever you happen to be.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ..core.save import register
from ..data.colonies import COLONIES_BY_ID, colonies_for
from ..data.factions import FACTIONS_BY_ID
from . import loyalty, territory, works
from ..world.economy import make_market
from ..world.galaxy import Port

_uid = itertools.count(1)

#: Days short before a holding is called starving, and how often it is
#: mentioned after that. Once when it starts, then once a year — not once a
#: day, which is what buried every other line in the chronicle.
STARVING_SAID = 30.0
STARVING_AGAIN = 365.0


@register
@dataclass
class Colony:
    id: int
    class_id: str
    name: str
    system_id: int
    body_id: str
    need: int
    days: float = 0.0
    online: bool = False
    pop: float = 0.0
    starving: float = 0.0
    works: list = field(default_factory=list)   # finished works, by id
    job: str | None = None                      # the work under way
    job_days: float = 0.0
    #: A power taking a share, because it annexed the ground underneath.
    tithe_to: str | None = None
    #: Held against a claimant who wanted it handed over. They come for it.
    defiant: bool = False

    @property
    def definition(self):
        return COLONIES_BY_ID[self.class_id]


def _held(game, key: str) -> float:
    """How much of a material the player can reach: depot plus the hold."""
    if key == "credits":
        return game.credits
    return game.stores.get(key, 0) + game.ship.cargo.get(key, 0)


def can_found(game, system, body, class_id: str) -> tuple[bool, str]:
    c = COLONIES_BY_ID.get(class_id)
    if c is None:
        return False, "Unknown class."
    if body.kind not in c.sites:
        return False, f"{c.name} will not take root on that."
    if body.colony is not None:
        return False, "Something is already growing there."
    if c.tech and c.tech not in game.research.unlocked:
        return False, "Not yet researched."
    if system.bloom > 0.5:
        return False, "The Bloom holds this system."
    # Somebody else's register is not a wall, but it is not nothing either.
    allowed, why = territory.welcome(game, system)
    if not allowed:
        return False, why
    if c.family == "grown" and not game.ship_stats.can_colonise:
        return False, ("No seed bay fitted — you cannot gestate a seed out here. "
                       "Refit one at a port.")
    for key, need in c.cost.items():
        have = _held(game, key)
        if have < need:
            return False, f"Short of {key}: need {need:g}, have {int(have)}."
    return True, ""


def _spend(game, cost: dict) -> None:
    for key, need in cost.items():
        if key == "credits":
            game.credits -= need
            continue
        owed = need
        from_store = min(game.stores.get(key, 0), owed)
        game.stores[key] = game.stores.get(key, 0) - from_store
        owed -= from_store
        if owed > 0:
            game.ship.cargo[key] = game.ship.cargo.get(key, 0) - owed
            if game.ship.cargo[key] <= 0.0001:
                game.ship.cargo.pop(key, None)


def _gestation_help(game, system_id: int) -> float:
    """A GRAVID nursery in-system speeds every gestation around it."""
    for k in game.colonies:
        if (k.online and k.system_id == system_id
                and COLONIES_BY_ID[k.class_id].effects.get("gestation")):
            return 0.8
    return 0.0


def found(game, system, body, class_id: str):
    ok, why = can_found(game, system, body, class_id)
    if not ok:
        return None, why
    # **The licence finally means something.** It was a tradeable commodity
    # with a price, no issuing authority, no revocation and no register of who
    # held one — "the whole containment regime rests on this being
    # unforgeable, which it is not". It can be taken away now, and a captain
    # whose plan was an empire of holdings has a great deal to lose by
    # offending the one power that signs for germination.
    from . import enforce as enforce_sim
    licensed, refusal = enforce_sim.may_seed(game)
    if not licensed:
        return None, refusal
    c = COLONIES_BY_ID[class_id]
    _spend(game, c.cost)

    speed = 1 + game.bonuses.get("growth", 0) + _gestation_help(game, system.id)
    col = Colony(id=next(_uid), class_id=class_id,
                 name=f"{c.name} · {body.name}", system_id=system.id,
                 body_id=body.id, need=max(10, round(c.days / speed)))
    body.colony = col.id
    game.colonies.append(col)
    loyalty.record(game, "colony")
    # Planting on somebody's register is a position, the same as taking their
    # rival's work. It is allowed; it is not free.
    moved = territory.charge_trespass(game, system)
    if moved:
        power = FACTIONS_BY_ID[moved[0][0]].short
        game.add_log(f"{col.name} is inside {power}'s declared space, and they "
                     "have noticed.", "warn")
    return col, ""


#: What a tonne of the commonest colony outputs is worth, for a rough payback.
#: Deliberately a flat figure rather than a market lookup: a forecast that
#: swings with whichever port you happen to be standing in is a forecast nobody
#: can compare classes with.
_WORTH = {"ore": 42, "volatiles": 38, "phosphate": 340, "biomass": 66,
          "alloy": 155, "silicon": 880, "xenolith": 3600, "xenopharma": 1240,
          "survey": 460, "credits": 1.0, "research": 90}


def forecast(game, system, body, class_id: str) -> dict:
    """What planting this class here would give you, before you commit.

    The dialog showed a price and a gestation time and nothing else, so a Free
    Port at 74,000 credits looked much like a RADIX Mine at 12,000 — one makes
    260 credits a day and the other 2.6 tonnes of ore, and the screen named
    neither.
    """
    definition = COLONIES_BY_ID.get(class_id)
    if definition is None:
        return {}
    probe = Colony(id=0, class_id=class_id, name=definition.name,
                   system_id=system.id, body_id=body.id, need=1,
                   online=True, pop=definition.pop)
    yields = works.yields_of(probe)
    upkeep = works.upkeep_of(probe)
    effects = works.effects_of(probe)

    a_day = sum(amount * _WORTH.get(key, 0) for key, amount in yields.items())
    a_day -= sum(amount * _WORTH.get(key, 0) for key, amount in upkeep.items())
    # What holding one *more* adds to the bill for the whole empire. The
    # card quoted a colony as though it were the only one you had, so the
    # twentieth Grove read exactly as well as the first.
    admin = works.admin_next(sum(1 for c in game.colonies if c.online))
    a_day -= admin
    outlay = float(definition.cost.get("credits", 0))
    outlay += sum(amount * _WORTH.get(key, 0)
                  for key, amount in definition.cost.items() if key != "credits")
    speed = 1 + game.bonuses.get("growth", 0) + _gestation_help(game, system.id)
    return {
        "yields": yields, "upkeep": upkeep, "effects": effects,
        "a_day": a_day, "outlay": outlay, "admin": admin,
        "days": max(10, round(definition.days / speed)),
        "payback": (outlay / a_day) if a_day > 0 else None,
    }


def tick(game, days: float) -> tuple[dict, list]:
    """Advance every colony. Returns (materials gained, log events)."""
    gains: dict[str, float] = {}
    events: list[tuple[str, str]] = []
    admin = works.admin_each(sum(1 for c in game.colonies if c.online))

    for col in game.colonies:
        c = col.definition
        if not col.online:
            col.days += days
            if col.days >= col.need:
                col.online = True
                col.pop = c.pop
                events.append(("good", f"{col.name} has matured and is online."))
                if c.effects.get("port"):
                    opened = open_harbour(game, game.galaxy.systems[col.system_id])
                    if opened:
                        events.append(("good", f"{opened.name} now has a market "
                                               "flying your colours."))
            continue

        affordable = True
        # Every holding past the first makes every holding dearer to run —
        # `works.admin_total` says why. Charged as part of the colony's own
        # bill so an over-extended empire starves at the edges, which is
        # the honest consequence and the machinery that already exists.
        owing = dict(works.upkeep_of(col))
        owing["credits"] = owing.get("credits", 0.0) + admin
        for key, n in owing.items():
            owed = n * days
            have = game.credits if key == "credits" else game.stores.get(key, 0)
            if have < owed:
                affordable = False
                break
            if key == "credits":
                game.credits -= owed
            else:
                game.stores[key] -= owed
        if not affordable:
            # **Said when it becomes true, and again only if it is still
            # true much later.** `MAX_STEP` is one day, so "past thirty days
            # short" fired *every day* for ever: measured, 90 identical
            # entries in 120 days. The log holds 300, so one starving
            # holding wiped every other piece of news inside four months —
            # and being `bad` it stood a long wait down daily as well.
            was = col.starving
            col.starving += days
            if was <= STARVING_SAID < col.starving:
                events.append(("bad", f"{col.name} is starving — yields have "
                                      "stopped."))
            elif (int(was // STARVING_AGAIN)
                  != int(col.starving // STARVING_AGAIN)):
                events.append(("bad", f"{col.name} has been starving for "
                                      f"{col.starving / 365:.1f} year(s). It "
                                      "produces nothing until it is fed."))
            continue
        if col.starving:
            events.append(("good", f"{col.name} is being fed again."))
        col.starving = 0

        finished = works.advance(game, col, days)
        events.extend(finished)
        # A work can grant the port effect just as a colony class can, and a
        # harbour that never opens is not a harbour. Maturation is not the only
        # moment a settlement becomes somewhere you can tie up.
        if finished and works.effects_of(col).get("port"):
            opened = open_harbour(game, game.galaxy.systems[col.system_id])
            if opened:
                events.append(("good", f"{opened.name} now has a market "
                                       "flying your colours."))

        produced = {key: n * days
                    for key, n in works.crewed_yields(game, col).items()}
        # A power that annexed the ground takes its share off the top, before
        # any of it reaches your stores — **and it is said out loud.** The return
        # here used to be thrown away, so thirty per cent of a holding's output
        # disappeared with no line in the log and nobody the richer for it.
        levied = territory.collect_tithe(game, col, produced, days)
        if levied:
            short = FACTIONS_BY_ID[levied["power"]].short \
                if levied["power"] in FACTIONS_BY_ID else levied["power"]
            what = ", ".join(f"{amount:.1f} t {cid}"
                             for cid, amount in sorted(levied["goods"].items()))
            events.append(("warn", f"{short} took the levy off {col.name} — "
                                   f"{what}, worth about "
                                   f"{round(levied['worth']):,}."))
        for key, amount in produced.items():
            if key == "credits":
                game.credits += amount
            elif key == "research":
                game.research.banked += amount
            else:
                game.stores[key] = game.stores.get(key, 0) + amount
                gains[key] = gains.get(key, 0) + amount
        ceiling = works.pop_ceiling(col)
        if ceiling:
            col.pop = min(ceiling, col.pop + ceiling * 0.0008 * days)
    return gains, events


def open_harbour(game, system):
    """A Free Port puts a market where there was none. Returns the system, or
    None if the system already had a harbour of its own."""
    if system.port is not None:
        return None
    system.port = Port("outpost", "Free Port", 2, ("market", "repair", "recruit"),
                       "freeholds", independent=True, player_built=True)
    system.market = make_market(game.rng("harbour"), system)
    return system


def close_harbour(game, system) -> bool:
    """Take the harbour away again if the last Free Port there is gone."""
    if not (system.port and system.port.player_built):
        return False
    still = any(c.online and c.system_id == system.id
                and COLONIES_BY_ID[c.class_id].effects.get("port")
                for c in game.colonies)
    if still:
        return False
    system.port = None
    system.market = None
    return True


def effects(game) -> dict:
    """Aggregate colony effects the rest of the game asks about."""
    # Only what something actually reads. `build_systems`, `watch_systems`,
    # `has_medical`, `has_fabricator` and `pop` were all published here and
    # opened by nothing — and two of them were the *only* mention of their
    # effect anywhere, so `test_grants` counted this function as the consumer
    # and called `fabricate` and `watch` live. A key nobody reads is not a
    # consumer; it is a place for one to hide.
    out = {"sensor_by_system": {}, "has_vault": False,
           "diplomacy": 0.0, "count": 0}
    for col in game.colonies:
        if not col.online:
            continue
        e = works.effects_of(col)
        out["count"] += 1
        if e.get("sensor"):
            key = col.system_id
            out["sensor_by_system"][key] = out["sensor_by_system"].get(key, 0) + e["sensor"]
        out["has_vault"] |= bool(e.get("vault"))
        out["diplomacy"] += e.get("diplomacy", 0)
    return out


def watching(game, system_id: int) -> bool:
    """Is anything of yours keeping an eye on this system?

    `watch` is declared by the VESPER Picket, the Monitor Station and the
    Relay Choir, and it read "Keeps an eye on this system whether or not you
    are in it" while buying nothing at all: the only line that touched it
    filled a `watch_systems` set that no other line in the game ever opened.
    """
    return any(works.effects_of(c).get("watch")
               for c in game.colonies
               if c.online and c.system_id == system_id)


def drifting(game, system_id: int) -> bool:
    """Is a CHORUS Node of yours holding this system on the plot?

    Beside `watching` and for the same reason: a predicate the game asks, rather
    than a key published into `effects()` that nothing opens. `drift` is declared
    by the CHORUS Node colony and reads "Reads the traffic: other hulls in this
    system stay plotted" — which was true of nothing at all until
    `traffic.mesh_reaches` began asking this.
    """
    return any(works.effects_of(c).get("drift")
               for c in game.colonies
               if c.online and c.system_id == system_id)


def fabricating(game, system_id: int) -> bool:
    """Can fabricated parts be made here rather than bought?

    `fabricate` is declared by the Fabricator Yard and the Refinery Platform
    and the codex promises "Fabricated parts can be made rather than bought".
    The only line that read it set a `has_fabricator` flag nothing opened, so
    46,000 credits of yard changed the bill by nothing at all.
    """
    return any(works.effects_of(c).get("fabricate")
               for c in game.colonies
               if c.online and c.system_id == system_id)


#: How much ward counts as a defence at all.
#:
#: **A threshold, because the quantity became continuous.** Both places that
#: ask "is this warded" tested `> 0.0`, which was right when a ward could only
#: come from a built work worth 0.28 — and wrong the moment machines started
#: contributing, because a teleoperated guard nine AU from its supervisor is
#: worth about 1e-7 and that is greater than zero. It armed a world with a
#: hand that could not have lifted a spanner.
#:
#: Set below a third of what one machine standing right there is worth (0.09)
#: and above what a preplanned one yields from across a system (0.0097), so
#: real help counts and a hand out of contact does not.
WARD_ENOUGH = 0.02


def is_warded(game, system_id: int) -> bool:
    """Is anything here actually defending the place? The one door.

    `sim/control` and `sim/interdiction` both used to test `ward_at() > 0.0`
    for themselves, which is the same question asked twice — and both were
    wrong in the same way at the same moment.
    """
    return ward_at(game, system_id) >= WARD_ENOUGH


def ward_at(game, system_id: int) -> float:
    """How strongly a system is defended, 0..0.9.

    Works *and* machines. Until `robots.ward_from` this counted only what had
    been built — so twenty classes of machine, four of them carrying a ground
    duty, defended nothing anywhere in the game, and a captain who left guards
    on a holding had left them to do nothing.

    What they are worth is a function of how far away their supervisor is
    standing, which is the one place in this game where `robots.grip` decides
    something a power can feel: see `sim/robots.ward_from`.
    """
    from . import telepresence as tele_sim
    built = sum(works.effects_of(c).get("ward", 0.0)
                for c in game.colonies
                if c.online and c.system_id == system_id)
    return min(0.9, built + tele_sim.ward_from(game, system_id))


#: How much of an attack a megastructure simply shrugs off.
#:
#: `megastructure` was declared by the ARCA Habitat and read by **nothing** —
#: 400,000 credits, 2,600 tonnes of ore and nine hundred days for a flag that
#: no line of the game consulted. So a five-by-ten-kilometre drum of spun rock
#: with a million people inside was overgrown on exactly the same roll as a
#: lichen farm.
#:
#: Not immunity: the docstring below is right that given years enough the
#: Bloom gets everything unattended, and a drum is no exception. It stacks
#: with a ward the way a hull's own armour stacks with an escort.
MEGASTRUCTURE_GUARD = 0.85


def bloom_attack(game, system, rng) -> list[Colony]:
    """The Bloom eats colonies it reaches — unless something is shooting back.

    A station that wards the system also has guns pointed at its own
    perimeter, so it is markedly harder to overgrow than the farm next door.
    It is not immortal: given years enough, the Bloom gets everything
    unattended. Losses are reported to the bridge — some of them built the
    place.

    (There were two string literals here. The first was the docstring and the
    second — the one that explained anything — was a discarded expression.)
    """
    here = [c for c in game.colonies if c.system_id == system.id]
    system_ward = ward_at(game, system.id)
    lost = []
    for col in here:
        fx = COLONIES_BY_ID[col.class_id].effects
        guard = min(0.92, system_ward + fx.get("ward", 0.0) * 0.5)
        if fx.get("megastructure"):
            guard = min(0.97, max(guard, MEGASTRUCTURE_GUARD))
        if rng.chance(0.30 * system.bloom * (1 - guard)):
            body = next((b for b in system.bodies if b.id == col.body_id), None)
            if body:
                body.colony = None
            lost.append(col)
    if lost:
        game.colonies = [c for c in game.colonies if c not in lost]
        close_harbour(game, system)
        loyalty.record(game, "colony_lost", scale=len(lost))
    return lost


__all__ = ["Colony", "can_found", "found", "tick", "effects", "bloom_attack",
           "colonies_for", "COLONIES_BY_ID", "MEGASTRUCTURE_GUARD"]
