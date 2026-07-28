"""The Bloom, and the ways the chronicle can end.

The Bloom is not an enemy fleet. It is a growth curve. Left alone it doubles,
spreads along the shortest hops, and converts whole systems into more of itself —
because the one thing anybody removed from it was the instruction to stop.
"""

from __future__ import annotations

from ..data.lore import VICTORIES
from ..world.galaxy import distance
from .colony import bloom_attack

SPREAD_INTERVAL = 30    # days between growth ticks


def bloom_systems(game):
    return [s for s in game.galaxy.systems if s.bloom > 0.02]


def bloom_burden(game) -> float:
    return sum(s.bloom for s in game.galaxy.systems if s.bloom > 0.02)


def tick(game, days: float, rng) -> list[tuple[str, str]]:
    """Grow and spread. Returns log events; sets ``game.overgrown`` if it wins."""
    game.bloom_clock += days
    events: list[tuple[str, str]] = []

    while game.bloom_clock >= SPREAD_INTERVAL:
        game.bloom_clock -= SPREAD_INTERVAL
        systems = game.galaxy.systems
        held = [s for s in systems if s.bloom > 0.02]

        for s in held:
            s.bloom = min(1.0, s.bloom + 0.025 + s.bloom * 0.035)
            for col in bloom_attack(game, s, rng):
                events.append(("bad", f"{col.name} has been overgrown and is lost."))

        # A mature system throws a seed at its nearest clean neighbour.
        for s in [x for x in held if x.bloom > 0.6]:
            clean = sorted((t for t in systems if t.bloom < 0.02 and distance(s, t) < 11),
                           key=lambda t: distance(s, t))
            if clean and rng.chance(0.14):
                clean[0].bloom = 0.10
                events.append(("bad", f"Unlicensed growth detected at {clean[0].name}."))

        game.bloom_total = bloom_burden(game)

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
    return {"cut": cut,
            "backlash": round(cut * 260 * rng.float(0.6, 1.3)),
            "cleared": system.bloom <= 0.02}, ""


# ── victory ────────────────────────────────────────────────────────────────

def victory_progress(game) -> dict[str, tuple[float, float, bool]]:
    """id -> (have, need, achieved)."""
    total = len(game.galaxy.systems)
    infested = len(bloom_systems(game))
    kin = sum(1 for f in ("charter", "concordat", "freeholds", "sanhedrin")
              if game.rep.get(f, 0) >= 70)
    online = [c for c in game.colonies if c.online]
    pop = sum(c.pop for c in online)
    has_ark = (game.ship.chassis == "leviathan"
               or any(s.chassis == "leviathan" for s in game.fleet))

    return {
        "containment": (total - infested, total, infested == 0 and game.day > 30),
        "exodus": (1 if has_ark else 0, 1, has_ark and game.flags.get("exodus_launched")),
        "concord": (kin, 4, kin >= 4),
        "genesis": (1 if game.flags.get("contact_made") else 0, 1,
                    bool(game.flags.get("contact_made"))
                    and "firstcontact" in game.research.unlocked),
        "dominion": (min(len(online), 12), 12, len(online) >= 12 and pop >= 1_000_000),
    }


def check_victory(game) -> str | None:
    progress = victory_progress(game)
    for vid, *_ in VICTORIES:
        if progress.get(vid, (0, 1, False))[2]:
            return vid
    return None
