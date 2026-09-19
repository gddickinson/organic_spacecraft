"""The living hull: what a grown body makes of what it has been through.

A grown hull used to change after launch only by refit, exactly like a
welded one. Now it remembers. Every act that loads the body — a hit, a spell
over the heat cap, a crossing, a season at a dim star, tonnes mined, a
survey, a dive, a hard burn — is **recorded on the hull that did it**, on one
of the channels in `data/adaptations.CHANNELS`, and when a channel crosses a
threshold an adaptation **emerges**: a small permanent change with a gain and
a cost. The captain may encourage it (growth material, sets in sooner),
suppress it (it fades and the channel is drawn down), or ignore it — and an
ignored one sets in by itself after `AUTO_SET_DAYS`. The organism does not
wait for permission.

Three things this module is the one door for:

- **Recording.** `record(ship, channel, amount)` is the whole of what an act
  site calls, and a hull that cannot adapt records nothing — so fabricated
  and synthetic hulls never carry stress, never emerge, never set in.
- **The effect on the numbers.** `apply` is called once, at the end of
  `ship.stats()`: a percentage multiplies the computed stat, an absolute
  adds, and a stat with a hard range is held to it. Nothing else touches it.
- **The clock.** `tick` runs in the ship-time phase, because biology runs on
  the crew's clock: a hard burn that skips three quarters of the days aboard
  skips three quarters of the setting-in too.

Every choice has a quote that the act spends exactly: `encourage_quote`,
`suppress_quote`, `prune_quote`.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data.adaptations import (ADAPTATIONS, ADAPTATIONS_BY_ID, AUTO_SET_DAYS,
                                BUDGET_MAX, BUDGET_STEPS, CHANNELS,
                                DARK_BELOW, DRAW_DOWN, ENCOURAGE_COST,
                                ENCOURAGE_DAYS, GLARE_FROM,
                                HYBRID_BUDGET_LESS, PRUNE_CREDITS, PRUNE_DAYS,
                                RATE, REFERENCE_HULL, STRESS_CAP)
from ..data.chassis import CHASSIS_BY_ID, FAMILY_LABEL
from . import stores

#: Where a channel stops filling: `STRESS_CAP` of its highest threshold.
CEILING = {channel: STRESS_CAP * max(a.threshold for a in ADAPTATIONS
                                     if a.channel == channel)
           for channel in CHANNELS}

#: The hard range of each stat an adaptation can move — the same bounds
#: `ship.stats()` holds them to, so research, refit and adaptation stacked
#: together still land inside them. `test_adaptation` drives every stat to
#: its edge and checks.
BOUNDS = {
    "evade": (0.0, 0.7), "scan": (0.0, 1.0), "crew_guard": (0.0, 0.85),
    "speed": (0.2, None), "jump": (1.0, None), "sensor": (0.5, None),
    "cargo": (0.0, None), "armour": (0.0, None), "heat_cap": (1.0, None),
    "vent": (0.0, None), "regen": (0.0, None), "mine": (0.0, None),
    "phos": (0.0, None), "o2_days": (1.0, None), "conceal": (-0.45, 0.45),
}


# ── the body ────────────────────────────────────────────────────────────────

def family(ship) -> str:
    chassis = CHASSIS_BY_ID.get(getattr(ship, "chassis", ""))
    return chassis.family if chassis else ""


def adapts(ship) -> bool:
    """Whether this hull's body answers load at all."""
    return RATE.get(family(ship), 0.0) > 0


def budget(ship) -> int:
    """How many adaptations this body has room for."""
    if not adapts(ship):
        return 0
    hull = CHASSIS_BY_ID[ship.chassis].hull
    room = next((n for top, n in BUDGET_STEPS if hull < top), BUDGET_MAX)
    if family(ship) == "hybrid":
        room = max(1, room - HYBRID_BUDGET_LESS)
    return room


def _size(ship) -> float:
    """This body against a NAVIS, which the costs are written for."""
    return CHASSIS_BY_ID[ship.chassis].hull / REFERENCE_HULL


def open_to(ship) -> list:
    """Every adaptation this family can grow, carried or not."""
    kind = family(ship)
    return [a for a in ADAPTATIONS if kind in a.families]


def hulls(game) -> list:
    """The flagship and every hull in the fleet, once each."""
    out = [game.ship]
    out += [s for s in getattr(game, "fleet", []) if s is not game.ship]
    return out


# ── recording ───────────────────────────────────────────────────────────────

def record(ship, channel: str, amount: float) -> float:
    """Put `amount` of load on one channel of this hull. Returns what stuck.

    The one call an act site makes. Harmless on anything: a missing ship, a
    welded one or an enemy's (it is their body) all simply record what their
    family allows. An unknown channel is a typo at the call site and raises.
    """
    ceiling = CEILING[channel]
    rate = RATE.get(family(ship), 0.0) if ship is not None else 0.0
    if rate <= 0 or not amount or amount < 0:
        return 0.0
    was = float(ship.stress.get(channel, 0.0))
    ship.stress[channel] = min(ceiling, was + float(amount) * rate)
    return ship.stress[channel] - was


def fleet_record(game, channel: str, amount: float) -> None:
    """Record an act the flag's escorts made too — they crossed with her."""
    from .consorts import escorts_of
    for ship in [game.ship] + escorts_of(game):
        record(ship, channel, amount)


def sky(game, ship_n: int) -> str:
    """Days under a dim star or a glaring one, for the flag and her escorts.

    Returns the channel it recorded on, or "" under an ordinary star. The
    days of a crossing count at the star it arrives at: `jump_to` sets the
    location before the clock runs, and the approach is where a star's light
    is felt.
    """
    heat = float(getattr(game.system, "heat", 0.5))
    channel = ("dark" if heat < DARK_BELOW
               else "glare" if heat >= GLARE_FROM else "")
    if channel and ship_n > 0:
        fleet_record(game, channel, ship_n)
    return channel


# ── emergence ───────────────────────────────────────────────────────────────

def crossed(ship) -> list:
    """Adaptations whose threshold this body has passed and does not carry."""
    return [a for a in open_to(ship) if a.id not in ship.adaptations
            and ship.stress.get(a.channel, 0.0) >= a.threshold]


def next_step(ship, channel: str):
    """The next threshold on a channel this body could still cross, or None."""
    ahead = [a for a in open_to(ship)
             if a.channel == channel and a.id not in ship.adaptations]
    return min(ahead, key=lambda a: a.threshold, default=None)


def _choose(game, ship, ready: list) -> tuple:
    """(what emerges, what triggered it). The most over-stressed channel
    triggers; a xeno body then draws what it grows from everything it could.

    The draw is seeded from the chronicle, the hull and the day rather than
    taken from `game.rng`, so a xeno emergence does not shift the day's one
    stream of luck for everything after it.
    """
    order = {a.id: i for i, a in enumerate(ADAPTATIONS)}
    trigger = max(ready, key=lambda a: (ship.stress[a.channel] / a.threshold,
                                        -order[a.id]))
    if family(ship) != "xeno":
        return trigger, trigger
    pool = [a for a in open_to(ship) if a.id not in ship.adaptations]
    rng = RNG(f"{game.seed}:adapt:{ship.uid}:{game.ship_day}")
    return rng.pick(pool), trigger


def _draw_down(ship, trigger) -> float:
    """Starve a channel back past the threshold that fired (`DRAW_DOWN`)."""
    left = min(ship.stress.get(trigger.channel, 0.0),
               DRAW_DOWN * trigger.threshold)
    ship.stress[trigger.channel] = left
    return left


def tick(game, ship_n: int) -> list:
    """A day aboard: the sky recorded, emergences made, and setting in.

    Returns log tuples for the phase to write. At most one emergence waits
    per hull; a body with no room left in its budget grows nothing.
    """
    if ship_n <= 0:
        return []
    sky(game, ship_n)
    said, flag_changed = [], False
    for ship in hulls(game):
        if not adapts(ship):
            continue
        waiting = ship.emerging
        if waiting is not None:
            if game.ship_day >= waiting["due"]:
                grown = ADAPTATIONS_BY_ID[waiting["id"]]
                ship.adaptations.append(grown.id)
                ship.emerging = None
                flag_changed = flag_changed or ship is game.ship
                said.append(("good", f"{grown.name} has set in on "
                                     f"{ship.name}. It is part of her now."))
            continue
        if len(ship.adaptations) >= budget(ship):
            continue
        ready = crossed(ship)
        if not ready:
            continue
        grows, trigger = _choose(game, ship, ready)
        if grows is not trigger:
            _draw_down(ship, trigger)
        ship.emerging = {"id": grows.id, "trigger": trigger.id,
                         "since_day": game.ship_day,
                         "due": game.ship_day + AUTO_SET_DAYS,
                         "encouraged": False}
        said.append(("warn", f"Something is growing on {ship.name}: "
                             f"{grows.name.lower()}. Left alone it sets in "
                             f"within {AUTO_SET_DAYS} days."))
    if flag_changed:
        game.recompute()
    return said


# ── the captain's answer ────────────────────────────────────────────────────

def encourage_quote(game, ship=None) -> dict:
    """What feeding the emergence costs, and the ship day it will set in."""
    ship = ship if ship is not None else game.ship
    waiting = ship.emerging
    if waiting is None:
        return {"ok": False, "why": "Nothing is emerging."}
    grows = ADAPTATIONS_BY_ID[waiting["id"]]
    cost = {key: round(n * _size(ship), 1) for key, n in ENCOURAGE_COST.items()}
    due = min(waiting["due"], game.ship_day + ENCOURAGE_DAYS)
    out = {"ok": True, "why": "", "adaptation": grows, "cost": cost,
           "due": due, "days": due - game.ship_day}
    if waiting.get("encouraged"):
        return dict(out, ok=False, why=f"Already fed; it sets in within "
                                       f"{out['days']} days.")
    for key, need, have in stores.lacking(game, cost):
        return dict(out, ok=False, why=f"Short of {key}: needs {need:g}, "
                                       f"you have {have:.1f}.")
    return out


def encourage(game, ship=None) -> dict:
    """Feed it: pay the quoted growth material, and it sets in on the day."""
    ship = ship if ship is not None else game.ship
    quote = encourage_quote(game, ship)
    if not quote["ok"]:
        return quote
    stores.spend(game, quote["cost"])
    ship.emerging["due"] = quote["due"]
    ship.emerging["encouraged"] = True
    game.add_log(f"{quote['adaptation'].name} is being fed. The body is grown "
                 f"by eating the rock; it sets in within {quote['days']} "
                 "days.", "good")
    return {"ok": True, "cost": quote["cost"], "due": quote["due"],
            "days": quote["days"]}


def suppress_quote(ship) -> dict:
    """What letting it fade costs: the channel, drawn back to this."""
    waiting = ship.emerging
    if waiting is None:
        return {"ok": False, "why": "Nothing is emerging."}
    trigger = ADAPTATIONS_BY_ID[waiting.get("trigger", waiting["id"])]
    left = min(ship.stress.get(trigger.channel, 0.0),
               DRAW_DOWN * trigger.threshold)
    return {"ok": True, "why": "", "adaptation": ADAPTATIONS_BY_ID[waiting["id"]],
            "channel": trigger.channel, "left": left,
            "relearn": trigger.threshold - left}


def suppress(game, ship=None) -> dict:
    """Let it fade. The channel is drawn down so it does not come straight
    back — the body forgets some of what taught it."""
    ship = ship if ship is not None else game.ship
    quote = suppress_quote(ship)
    if not quote["ok"]:
        return quote
    waiting = ship.emerging
    left = _draw_down(ship, ADAPTATIONS_BY_ID[waiting.get("trigger",
                                                          waiting["id"])])
    ship.emerging = None
    game.add_log(f"The {quote['adaptation'].name.lower()} on {ship.name} is "
                 "being starved back. It fades.", "")
    return {"ok": True, "channel": quote["channel"], "left": left}


def prune_quote(game, adaptation_id: str, ship=None) -> dict:
    """What a surgeon at a Fleet Hub asks to cut an adaptation back out."""
    ship = ship if ship is not None else game.ship
    credits = round(PRUNE_CREDITS * _size(ship))
    out = {"ok": True, "why": "", "credits": credits, "days": PRUNE_DAYS}
    if adaptation_id not in ship.adaptations:
        return dict(out, ok=False, why="She does not carry that.")
    from . import anchorage
    here = anchorage.docked_at(game)
    if here is None or not here.offers("gestation"):
        return dict(out, ok=False, why="Only a Fleet Hub's gestation bay has "
                                       "the surgeons for it.")
    if game.credits < credits:
        return dict(out, ok=False, why=f"The surgeons want {credits:,}.")
    return out


def prune(game, adaptation_id: str, ship=None) -> dict:
    """Cut it out: the quoted credits, then the quoted days alongside."""
    ship = ship if ship is not None else game.ship
    quote = prune_quote(game, adaptation_id, ship)
    if not quote["ok"]:
        return quote
    cut = ADAPTATIONS_BY_ID[adaptation_id]
    game.credits -= quote["credits"]
    ship.adaptations.remove(adaptation_id)
    _draw_down(ship, cut)
    game.recompute()
    game.add_log(f"The surgeons have cut the {cut.name.lower()} out of "
                 f"{ship.name}.", "good")
    game.advance_days(quote["days"])
    return {"ok": True, "credits": quote["credits"], "days": quote["days"]}


# ── what it does to the numbers ─────────────────────────────────────────────

def fx(ship) -> dict:
    """Every established adaptation's gain and cost, by stat, as
    (fraction of the computed stat, amount added)."""
    out: dict = {}
    for aid in getattr(ship, "adaptations", ()) or ():
        grown = ADAPTATIONS_BY_ID.get(aid)
        if grown is None:           # a row retired since the save was made
            continue
        for effect in grown.gives + grown.takes:
            frac, add = out.get(effect.stat, (0.0, 0.0))
            out[effect.stat] = ((frac + effect.amount, add) if effect.pct
                                else (frac, add + effect.amount))
    from .kith import synergy       # a Kith graft answering what grew here
    for effect in synergy(ship):
        frac, add = out.get(effect.stat, (0.0, 0.0))
        out[effect.stat] = ((frac + effect.amount, add) if effect.pct
                            else (frac, add + effect.amount))
    return out


def apply(stats, ship):
    """Fold the body's adaptations into computed stats. The one place."""
    for stat, (frac, add) in fx(ship).items():
        value = getattr(stats, stat) * (1.0 + frac) + add
        low, high = BOUNDS.get(stat, (None, None))
        if low is not None:
            value = max(low, value)
        if high is not None:
            value = min(high, value)
        setattr(stats, stat, value)
    return stats


def dose_multiplier(ship) -> float:
    """The radiation dose the crew takes, as a multiple of an unadapted
    hull's — read by the Cradle's dose (`sim/regions.dose`); 1.0 for
    anything welded."""
    out = 1.0
    for aid in getattr(ship, "adaptations", ()) or ():
        grown = ADAPTATIONS_BY_ID.get(aid)
        out *= grown.dose if grown else 1.0
    return out


def reading(game) -> list:
    """What the manual says about *this* hull: its room, its rate, its terms.

    Counted from the tables at read time, so the prose never restates a
    number that a retune would make wrong.
    """
    ship = game.ship
    kind = family(ship)
    name = CHASSIS_BY_ID[ship.chassis].name
    if not adapts(ship):
        return [f"Your {name} is {FAMILY_LABEL.get(kind, kind).lower()}: it "
                "never adapts."]
    lines = [f"Your {name} has room for {budget(ship)} adaptation(s) and "
             f"carries {len(ship.adaptations)}.",
             f"{len(open_to(ship))} are open to a "
             f"{FAMILY_LABEL[kind].lower()} body, across "
             f"{len({a.channel for a in open_to(ship)})} channels."]
    if RATE[kind] != 1.0:
        lines.append(f"It answers load at {RATE[kind]:g}x a grown hull's rate"
                     + (", and draws what it grows at random."
                        if kind == "xeno" else "."))
    lines.append(f"Left alone an emergence sets in after {AUTO_SET_DAYS} "
                 f"days; fed, within {ENCOURAGE_DAYS}.")
    return lines
