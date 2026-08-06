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

#: Inside this range a mature system seeds its neighbour at full chance.
#: The cutoff used to be absolute, and it sat on the shoulder of the
#: generated-gap distribution — see the seeding loop in `tick`.
SPREAD_LY = 11.0

#: A sector whose every mature system is out of range of clean ground makes
#: one forced throw after this many stalled growth ticks (~3 years), then
#: counts again. Deterministic on purpose: a probability here either
#: re-paced every slow sector (0.35 killed the five-year playability floor
#: — a naive captain starved in a sector 37/42 drowned by day 1644) or was
#: too rare to trust. Three stalled years says "the Bloom always finds a
#: way" without making it artillery.
STALL_TICKS = 36

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


def _seed_system(game, target, events) -> None:
    """One new infestation, reported only if somebody of yours is looking.

    The sector used to report every new infestation anywhere, which is why
    the `watch` a picket grants bought nothing: you already knew.
    """
    target.bloom = 0.10
    loyalty.record(game, "bloom_spread")
    if target.id == game.location_id or watching(game, target.id):
        events.append(("bad",
                       f"Unlicensed growth detected at {target.name}."))


def known_bloom(game) -> dict:
    """What the captain can actually see of the Bloom. **The one door.**

    `sim/intel.sees_bloom` exists so the chart cannot show infestation
    nobody has looked at — that is what a picket's `watch` is sold on, and
    what makes visiting a system worth the reaction mass. The Holdings
    panel went round it: it counted every infested system in the sector and
    printed the sector-wide burden, so the fog covered the map and not the
    one number the game is about.

    `unscouted` is the honest remainder — how many systems nothing of yours
    has looked at — so the panel can say *at least* rather than pretending
    the census is complete.
    """
    from . import intel as intel_sim
    seen = [s for s in game.galaxy.systems if intel_sim.sees_bloom(game, s)]
    held = [s for s in seen if s.bloom > 0.02]
    return {"systems": held,
            "count": len(held),
            "burden": sum(s.bloom for s in held),
            "seen": len(seen),
            "total": len(game.galaxy.systems),
            "unscouted": len(game.galaxy.systems) - len(seen)}


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
                # And the captain hears about it the way news travels — a
                # courier from that system, as old as the crossing. The log
                # line above only fires where somebody of yours is looking;
                # the despatch is how the rest of the sector reaches you.
                from . import comms as comms_sim
                comms_sim.send(game, "news", "Sector bulletin", "news",
                               f"{col.name} is lost",
                               f"{col.name} has been overgrown. The last "
                               "boats out carried what they could.",
                               system_id=s.id)

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
        # When *no* mature system anywhere has clean ground in range, the
        # sector as a whole makes one long throw instead — spores riding
        # ordinary traffic across the gap, slowly. The hard cutoff alone
        # sat on the shoulder of the generated-gap distribution (22.5% of
        # sectors put the origin's nearest clean system past SPREAD_LY), so
        # one sector in five generated an antagonist that could never leave
        # home: 90 of 500 inert at day 0. The first fix let every saturated
        # system throw long once its neighbourhood filled in, and six
        # long-fixture sectors drowned ~40% faster — the stall is the
        # *sector's* condition, so the long throw is the sector's one move.
        throwers = [x for x in held if x.bloom > 0.6]
        ground_in_range = False
        for s in throwers:
            clean = sorted((t for t in systems
                            if t.bloom < 0.02 and distance(s, t) < SPREAD_LY),
                           key=lambda t: distance(s, t))
            if clean and rng.chance(0.14 * stage.spread
                                    * (1 - ward_at(game, clean[0].id))):
                _seed_system(game, clean[0], events)
            ground_in_range = ground_in_range or bool(clean)
        if throwers and not ground_in_range:
            stalled = int(game.flags.get("bloom_stalled", 0)) + 1
            game.flags["bloom_stalled"] = stalled
            if stalled >= STALL_TICKS:
                game.flags["bloom_stalled"] = 0
                spear = min(((s, t) for s in throwers for t in systems
                             if t.bloom < 0.02),
                            key=lambda pair: distance(*pair), default=None)
                if spear is not None:
                    _seed_system(game, spear[1], events)
        else:
            game.flags.pop("bloom_stalled", None)

        game.bloom_total = bloom_burden(game)
        events.extend(bloom_sim.review_stage(game, game.bloom_total))
        events.extend(bloom_sim.tick_instars(game, SPREAD_INTERVAL, rng))
        if len([s for s in systems if s.bloom > 0.02]) >= len(systems) // 2:
            b = bloom_sim.beat(game, "half_the_verge")
            if b:
                events.append(b)

    # If it takes the whole sector there is nothing left to play for — or
    # if it takes every harbour in it, which happens sooner and is the
    # condition a player can actually watch closing. The old test needed
    # all forty-two systems past half, which arrived about 180 days *after*
    # Ruin could fire; victory is checked first, so a living captain could
    # not lose to the Bloom at all and pure passivity was rewarded with an
    # ending. Harbours are what a hull needs to go on existing.
    systems = game.galaxy.systems
    harbours = [s for s in systems if s.port]
    if all(s.bloom > 0.5 for s in systems) or (
            harbours and all(s.bloom > 0.5 for s in harbours)):
        game.overgrown = True
    return events


def harbours_left(game) -> tuple[int, int]:
    """Ports not yet drowned, and how many there were. The loss, as a bar."""
    harbours = [s for s in game.galaxy.systems if s.port]
    return len([s for s in harbours if s.bloom <= 0.5]), len(harbours)


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

def victory_progress(game, seen_only: bool = False) -> dict:
    """id -> (have, need, achieved).

    `seen_only` fogs the *displayed* containment figure — a bar reading
    38 of 42 tells a captain who has scouted nothing that four systems are
    infested, which is the census `intel.sees_bloom` refuses the chart.
    **The achieved flag is never fogged**: winning is decided by what is
    true, not by what has been looked at, or a captain could take
    Containment by keeping their eyes shut.
    """
    total = len(game.galaxy.systems)
    infested = len(bloom_systems(game))
    shown = known_bloom(game)["count"] if seen_only else infested
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
    # A cartel corners *living* prices. This counted register keys — quotes
    # twenty years stale, and ports that have since closed — so the ending
    # credited a filing cabinet. A quote counts while `market.confidence`
    # still believes it and the port is still trading.
    from . import market as market_sim
    priced = len([k for k in game.register if str(k).isdigit()
                  and game.galaxy.systems[int(k)].market is not None
                  and market_sim.confidence(
                      market_sim.age_of(game, int(k))) > 0.5])
    cartel_need = max(1, int(len(markets) * CARTEL_SHARE))
    crewless = (CHASSIS_BY_ID.get(game.ship.chassis)
                and CHASSIS_BY_ID[game.ship.chassis].family == "synthetic"
                and not game.officers)
    drowned = len(bloom_systems(game))

    return {
        # **The husk counts, because it is half the work.** The bar read
        # `clean systems / all systems`, so an untouched sector on day 227
        # showed 38 of 42 and a nearly-full green bar — "very nearly won"
        # for a captain who had not fired a shot and had not yet found
        # Kessel's Reach. The heart is the other half of the condition and
        # is now the other half of the measure.
        "containment": (total - shown + (total if bloom_sim.heart_dead(game)
                                         else 0),
                        total * 2,
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
        # **Outlived, not waited out.** The goal on the card is "Outlive the
        # sector", and the prose is a captain who "was right about all of
        # it" — but the test was 90% drowned and a hull over a quarter,
        # which total passivity satisfies on its own about 180 days before
        # the loss could fire. Living through it means having been *in* it:
        # something of yours still standing, or a record of having fought.
        "ruin": (drowned, total,
                 drowned >= total * RUIN_SHARE and not game.dead
                 and hull_pct(game.ship) > 0.25 and _stood_through_it(game)),
    }


def _stood_through_it(game) -> bool:
    """Did the captain live through the sector's fall, or merely outlast it?

    Either something of theirs is still standing in it, or *they* have at
    some point cost the Bloom something — a record of having been present
    at what happened. Waiting a decade in a quiet system with the door shut
    is neither.

    The record is `responses.fought`, which only the captain's own acts
    feed. The first version read `provocation > 0` and the fired-response
    list — and the powers' containment flotillas provoke on the clock, so
    the guard was satisfied by NPCs: `advance_days` alone took Ruin on day
    2,338, exactly the passivity this function exists to refuse.
    """
    if any(c.online for c in game.colonies):
        return True
    return response_sim.fought(game) > 0


def check_victory(game) -> str | None:
    progress = victory_progress(game)
    for vid, *_ in VICTORIES:
        if progress.get(vid, (0, 1, False))[2]:
            return vid
    return None
