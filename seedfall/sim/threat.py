"""The Bloom, and the ways the chronicle can end.

The Bloom is not an enemy fleet. It is a growth curve. Left alone it doubles,
spreads along the shortest hops, and converts whole systems into more of itself —
because the one thing anybody removed from it was the instruction to stop.
"""

from __future__ import annotations

from ..data.lore import VICTORIES
from ..data.chassis import CHASSIS_BY_ID
from ..world.galaxy import distance
from .ship import hull_pct
from .colony import bloom_attack, ward_at, watching
from . import loyalty
from . import bloom as bloom_sim
from . import responses as response_sim
from . import diplomacy as dip_sim

SPREAD_INTERVAL = 30    # days between growth ticks

#: Thresholds for the endings that are counted rather than flagged.
LINEAGE_HULLS = 4          # grown hulls of your own, still flying
#: Share of the sector's *markets* whose prices you have written down. Not an
#: absolute count: a sector has 17 to 24 markets across seeds, so the first
#: version of this asked for 25 and was unreachable in every one of them —
#: the same defect as a work gated behind a technology that does not exist.
CARTEL_SHARE = 0.9
CARTEL_PURSE = 1_500_000
RUIN_SHARE = 0.9           # of the sector held by the Bloom, and you alive


def bloom_systems(game):
    return [s for s in game.galaxy.systems if s.bloom > 0.02]


def bloom_burden(game) -> float:
    return sum(s.bloom for s in game.galaxy.systems if s.bloom > 0.02)


def tick(game, days: float, rng) -> list[tuple[str, str]]:
    """Grow and spread. Returns log events; sets ``game.overgrown`` if it wins."""
    game.bloom_clock += days
    events: list[tuple[str, str]] = []
    bloom_sim.decay_resistance(game, days)

    while game.bloom_clock >= SPREAD_INTERVAL:
        game.bloom_clock -= SPREAD_INTERVAL
        systems = game.galaxy.systems
        held = [s for s in systems if s.bloom > 0.02]

        stage = bloom_sim.ensure(game).definition
        provoked = response_sim.growth_multiplier(game)
        for s in held:
            # A monitor both slows the growth and burns back what it can reach.
            # A fully-watched system holds its line and slowly loses ground; it
            # will not clear a heavy infestation on its own, which is what the
            # guns on your own hull are for.
            ward = ward_at(game, s.id)
            # Everything it has answered makes it grow harder from here on.
            growth = ((0.025 + s.bloom * 0.035) * stage.growth * provoked
                      * (1 - ward)
                      - ward * (0.020 + s.bloom * 0.030))
            s.bloom = max(0.0, min(1.0, s.bloom + growth))
            for col in bloom_attack(game, s, rng):
                events.append(("bad", f"{col.name} has been overgrown and is lost."))
                # The sector hears about it: every power and quay holds a
                # memory of the loss, which is what an envoy brings up later.
                from . import memory as memory_sim
                memory_sim.broadcast(game, "news",
                                     f"{col.name} was overgrown and lost", 0.9,
                                     tags=["bloom", "colony"],
                                     among=("faction", "port"))

        # The Weave is a road, and the Bloom is not fussy about who laid it.
        # Distance means nothing to a lit ring: growth crosses sixty light
        # years as easily as six. This is the price of the network, and it is
        # why waking an anchor is a decision rather than a purchase.
        from . import gates as gates_sim
        for here, there, share in gates_sim.bloom_links(game):
            target = systems[there]
            ward = ward_at(game, there)
            # Scaled by the same stage and provocation as everything else it
            # does. A flat carry was a growth channel that did not care what
            # the Bloom had been through, and it swamped the check that says
            # provoking it makes it grow faster — 31.8 against 33.4, when the
            # provoked run should be the larger. It uses the roads harder for
            # the same reasons it does everything else harder.
            carried = share * stage.growth * provoked * (1 - ward)
            if carried <= 0:
                continue
            was = target.bloom
            target.bloom = max(0.0, min(1.0, target.bloom + carried))
            if was < 0.02 <= target.bloom:
                loyalty.record(game, "bloom_spread")
                events.append(
                    ("bad", f"{target.name} has taken growth off the ring "
                            f"from {systems[here].name}. The Weave carries "
                            "more than cargo."))

        # A mature system throws a seed at its nearest clean neighbour.
        for s in [x for x in held if x.bloom > 0.6]:
            clean = sorted((t for t in systems if t.bloom < 0.02 and distance(s, t) < 11),
                           key=lambda t: distance(s, t))
            if clean and rng.chance(0.14 * stage.spread
                                    * (1 - ward_at(game, clean[0].id))):
                clean[0].bloom = 0.10
                loyalty.record(game, "bloom_spread")
                # Only if somebody of yours is looking. The sector used to
                # report every new infestation anywhere, which is why the
                # `watch` a picket grants bought nothing: you already knew.
                if (clean[0].id == game.location_id
                        or watching(game, clean[0].id)):
                    events.append(
                        ("bad", f"Unlicensed growth detected at "
                                f"{clean[0].name}."))

        game.bloom_total = bloom_burden(game)
        events.extend(bloom_sim.review_stage(game, game.bloom_total))
        events.extend(bloom_sim.tick_instars(game, SPREAD_INTERVAL, rng))
        if len([s for s in systems if s.bloom > 0.02]) >= len(systems) // 2:
            b = bloom_sim.beat(game, "half_the_verge")
            if b:
                events.append(b)

    # If it takes the whole sector there is nothing left to play for.
    if all(s.bloom > 0.5 for s in game.galaxy.systems):
        game.overgrown = True
    return events


def cleanse(game, system, rng):
    """Burn out a Bloom mass. Expensive, and it fights back."""
    if system.bloom <= 0.02:
        return None, "Nothing here to burn."
    firepower = sum(w.wpn.dmg for w in game.ship_stats.weapons)
    need = 25 + system.bloom * 55
    if firepower < need:
        return None, ("Insufficient firepower — you would need about "
                      f"{round(need)} points of armament against a mass this size.")
    cut = min(system.bloom, 0.25 + (firepower - need) / 300 + rng.float(0, 0.15))
    system.bloom = max(0.0, system.bloom - cut)
    # The burn is made with the fitted guns, so it teaches the Bloom what it
    # was burned with — combat already reported its hits per family and the
    # cleanse, the larger provocation, reported nothing, which left "it is
    # adapting everywhere at once" with nothing to adapt against.
    for w in game.ship_stats.weapons:
        bloom_sim.record_damage(game, w.family, w.wpn.dmg)
    if system.bloom <= 0.02:
        loyalty.record(game, "bloom_cleansed")
    return {"cut": cut,
            "backlash": round(cut * 260 * rng.float(0.6, 1.3)),
            "cleared": system.bloom <= 0.02}, ""


# ── victory ────────────────────────────────────────────────────────────────

def victory_progress(game) -> dict[str, tuple[float, float, bool]]:
    """id -> (have, need, achieved)."""
    total = len(game.galaxy.systems)
    infested = len(bloom_systems(game))
    concord = dip_sim.concord_progress(game)
    kin = len(concord["kin"]) + len(concord["peace"])
    kin_need = concord["kin_need"] + concord["peace_need"]
    online = [c for c in game.colonies if c.online]
    pop = sum(c.pop for c in online)
    has_ark = (game.ship.chassis == "leviathan"
               or any(s.chassis == "leviathan" for s in game.fleet))

    # Five more ways to finish, each measured off machinery that already
    # exists. None of them is gated behind any of the others.
    from ..data.xenotech import XENOTECH
    from . import xeno as xeno_sim
    grown_line = [s for s in game.fleet
                  if CHASSIS_BY_ID.get(s.chassis)
                  and CHASSIS_BY_ID[s.chassis].family == "grown"]
    understood = [t for t in XENOTECH if xeno_sim.is_incorporated(game, t.id)]
    markets = [s for s in game.galaxy.systems if s.market]
    priced = len([k for k in game.register if str(k).isdigit()])
    cartel_need = max(1, int(len(markets) * CARTEL_SHARE))
    crewless = (CHASSIS_BY_ID.get(game.ship.chassis)
                and CHASSIS_BY_ID[game.ship.chassis].family == "synthetic"
                and not game.officers)
    drowned = len(bloom_systems(game))

    return {
        "containment": (total - infested, total,
                        infested == 0 and bloom_sim.heart_dead(game)
                        and game.day > 30),
        "exodus": (1 if has_ark else 0, 1, has_ark and game.flags.get("exodus_launched")),
        "concord": (kin, kin_need, concord["done"]),
        "genesis": (1 if game.flags.get("contact_made") else 0, 1,
                    bool(game.flags.get("contact_made"))
                    and "firstcontact" in game.research.unlocked),
        "dominion": (min(len(online), 12), 12, len(online) >= 12 and pop >= 1_000_000),
        "lineage": (len(grown_line), LINEAGE_HULLS,
                    len(grown_line) >= LINEAGE_HULLS
                    and "licence" in game.research.unlocked),
        "xenarch": (len(understood), len(XENOTECH),
                    len(understood) >= len(XENOTECH)),
        "cartel": (min(priced, cartel_need), cartel_need,
                   priced >= cartel_need and game.credits >= CARTEL_PURSE),
        "apostasy": (1 if crewless else 0, 1,
                     bool(crewless) and game.rep.get("sanhedrin", 0) >= 75),
        "ruin": (drowned, total,
                 drowned >= total * RUIN_SHARE and not game.dead
                 and hull_pct(game.ship) > 0.25),
    }


def check_victory(game) -> str | None:
    progress = victory_progress(game)
    for vid, *_ in VICTORIES:
        if progress.get(vid, (0, 1, False))[2]:
            return vid
    return None
