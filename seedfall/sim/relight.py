"""Relighting a deep anchor: the mid-game project that opens a region.

A deep anchor stands on the Verge's rim from the first day, dark, and drawn on
the chart so a captain has somewhere to aim. Three things wake it, in order,
and the preview states all three before any of them is spent:

1. **Read it.** A deep survey of a body in the anchor's system — the one way
   of looking that reaches what is buried (`data/surveys` "deep"). Recorded
   by `note_survey`, which `sim/survey.perform` calls with the method used.
2. **Know what it is doing.** The Deep Weave technology, a tier-3 node fed by
   survey and specimen evidence (`data/tech`, `data/inquiry.TECH_MIX`).
3. **Pay for it, there.** Credits and materials out of the one door
   (`sim/stores`), and `RELIGHT_DAYS` of work through `advance_days`.

Then the region is generated (`world/regions.generate`) — not before — and
the gate burns: instant, toll-free transit through `sim/gates`, and a road
the Bloom walks like any ring the captain lit (`gates.bloom_links`).

**Preview equals act.** `preview` and `relight` read the same constants and
`relight` returns what it spent; `test_reaches` performs one and compares.
"""

from __future__ import annotations

from ..data.gates import BLOOM_CARRY, BLOOM_CARRY_FLOOR
from ..data.regions import (DEEP_TECH, READ_METHOD, REGIONS, REGIONS_BY_ID,
                            RELIGHT_CREDITS, RELIGHT_DAYS, RELIGHT_GOODS)
from ..data.tech import TECH_BY_ID
from ..world import regions as world_regions
from . import kith_world, stores, weave


def anchor_of(game, region_id: str) -> int | None:
    """The Verge system this region's deep anchor stands in."""
    return world_regions.anchors(game.galaxy).get(region_id)


def region_at(game, system_id: int) -> str | None:
    """The region whose deep anchor stands in this system, if any."""
    for rid, sid in world_regions.anchors(game.galaxy).items():
        if sid == system_id:
            return rid
    return None


def is_open(game, region_id: str) -> bool:
    return world_regions.region(game.galaxy, region_id) is not None


def is_read(game, region_id: str) -> bool:
    """Has a deep survey been made in this anchor's system?"""
    return anchor_of(game, region_id) in weave.ensure(game).read


def note_survey(game, method_id: str) -> str | None:
    """Record a deep survey made at a deep anchor. Returns the region read.

    Called by `sim/survey.perform` with the method it used, which is the only
    way to know: a body keeps how well it was seen, never how.
    """
    if method_id != READ_METHOD:
        return None
    rid = region_at(game, game.location_id)
    if rid is None:
        return None
    state = weave.ensure(game)
    if game.location_id in state.read:
        return rid
    state.read.append(game.location_id)
    spec = REGIONS_BY_ID[rid]
    game.add_log(f"The deep survey reads the anchor at {game.system.name}: it "
                 f"is not dead, only dark, and it is aimed at {spec.name}.",
                 "good")
    return rid


def bloom_risk(game, region_id: str) -> dict:
    """What opening this door does for the Bloom, in the gates' own terms."""
    sid = anchor_of(game, region_id)
    here = game.galaxy.systems[sid] if sid is not None else None
    bloom = float(getattr(here, "bloom", 0.0) or 0.0)
    carries = bloom >= BLOOM_CARRY_FLOOR
    return {"bloom": bloom, "carries": carries, "floor": BLOOM_CARRY_FLOOR,
            "share": BLOOM_CARRY,
            "per_season": round(bloom * BLOOM_CARRY, 4) if carries else 0.0}


def preview(game, region_id: str) -> dict:
    """Everything a relight will take and do, before any of it is spent."""
    spec = REGIONS_BY_ID[region_id]
    sid = anchor_of(game, region_id)
    anchor = game.galaxy.systems[sid] if sid is not None else None
    tech = TECH_BY_ID.get(DEEP_TECH)
    goods = {cid: (need, stores.held(game, cid))
             for cid, need in RELIGHT_GOODS.items()}
    read = is_read(game, region_id)
    known = DEEP_TECH in game.research.unlocked
    paid = (game.credits >= RELIGHT_CREDITS
            and all(have >= need for need, have in goods.values()))
    here = sid is not None and game.location_id == sid
    steps = [
        ("read", read,
         f"A deep survey of a body at {anchor.name if anchor else '—'}."),
        ("tech", known, f"{tech.name if tech else DEEP_TECH} researched."),
        ("pay", paid,
         f"₡{RELIGHT_CREDITS:,.0f} and "
         + ", ".join(f"{need} t {cid}" for cid, need in RELIGHT_GOODS.items())
         + f", paid at the anchor, and {RELIGHT_DAYS} days of work."),
    ]
    why = ""
    if is_open(game, region_id):
        why = f"{spec.name} is already open."
    elif anchor is None:
        why = "This sector has no rim to stand a deep anchor on."
    elif not read:
        why = (f"Nobody has read the anchor. A deep survey of a body at "
               f"{anchor.name} is the first step.")
    elif not known:
        why = f"Nobody aboard knows what it is doing: research {tech.name}."
    elif not here:
        why = f"The work is done at the anchor, at {anchor.name}."
    elif game.credits < RELIGHT_CREDITS:
        why = (f"₡{RELIGHT_CREDITS:,.0f} of work, and you have "
               f"₡{game.credits:,.0f}.")
    else:
        short = next(((cid, need, have) for cid, (need, have) in goods.items()
                      if have < need), None)
        if short:
            why = f"{short[1]} t {short[0]} needed; {short[2]:g} to hand."
    # Not a step — a relit region can be crossed by its gates — but said
    # before the work: the Hollow's lanes want 12 ly, and a captain who
    # relit it on a 10.3 ly drive found every star "beyond reach" (play-test,
    # 2026-09-18). `link` joins every star in the region to every other.
    jump = game.ship_stats.jump
    lanes = (f"{spec.name}'s stars are joined by hops of up to "
             f"{spec.link:g} ly; this hull jumps {jump:.1f} ly"
             + ("." if jump >= spec.link else
                " — past the anchor it would be the gates or a better drive."))
    return {"region": spec, "anchor": anchor, "steps": steps, "lanes": lanes,
            "credits": RELIGHT_CREDITS, "goods": dict(RELIGHT_GOODS),
            "have": {cid: have for cid, (_n, have) in goods.items()},
            "days": RELIGHT_DAYS, "bloom": bloom_risk(game, region_id),
            "here": here, "ok": not why, "why": why}


def can_relight(game, region_id: str) -> tuple[bool, str]:
    """The gate the button greys on — the preview's own verdict."""
    said = preview(game, region_id)
    return said["ok"], said["why"]


def relight(game, region_id: str) -> dict:
    """Relight a deep anchor: pay, work, and open the region behind it."""
    ok, why = can_relight(game, region_id)
    if not ok:
        return {"ok": False, "why": why}
    spec = REGIONS_BY_ID[region_id]
    before = {"credits": game.credits,
              **{cid: stores.held(game, cid) for cid in RELIGHT_GOODS}}
    day = game.day
    stores.spend(game, {"credits": RELIGHT_CREDITS, **RELIGHT_GOODS})
    spent = {key: round(before[key] - stores.held(game, key), 6)
             for key in before}
    game.advance_days(RELIGHT_DAYS)
    if game.dead:
        return {"ok": True, "dead": True, "spent": spent}
    made = world_regions.generate(game.galaxy, region_id, game.day)
    if region_id == "shoals":
        world_regions.open_buyers(game.galaxy)
    kith_world.ensure(game)                 # the Cradle's Kith gatherings
    entry = game.galaxy.systems[made.entry_id]
    game.add_log(f"The deep anchor at {game.system.name} is burning, and on "
                 f"the far side of it is {spec.name}: {entry.name}, and "
                 f"{spec.count - 1} more stars nobody has charted.", "good")
    return {"ok": True, "region": made, "entry": entry, "spent": spent,
            "days": game.day - day}


def standing(game) -> list[dict]:
    """Every deep anchor and where its project stands, for the chart."""
    out = []
    for spec in REGIONS:
        sid = anchor_of(game, spec.id)
        if sid is None:
            continue
        said = preview(game, spec.id)
        out.append({"region": spec, "anchor_id": sid,
                    "open": is_open(game, spec.id),
                    "done": sum(1 for _k, done, _t in said["steps"] if done),
                    "steps": said["steps"], "why": said["why"]})
    return out
