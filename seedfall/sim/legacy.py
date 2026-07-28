"""Life after an ending: an epoch, a pressure, and situations to answer.

An ending used to be a dialog followed by `clear_save()` and a fresh chronicle.
This makes it a turn in the sector's history instead. Reaching one rewrites the
world once, starts a new clock in place of the Bloom, and begins putting
situations in front of you that have to be answered.

Two project rules govern the shape:

- **Anything you can be in the middle of is a field on the `Game` with an
  `.over` flag**, so it survives a save. A situation waiting on an answer is
  exactly that, so it is `game.situation` and the window's navigation guard
  diverts to it like a battle or an open trench.
- **A choice states its consequence.** Every answer carries an `effect` dict
  and a sentence describing it, and `apply()` reads that same dict — so the
  card cannot promise what the game will not do. `test_legacy` performs each
  answer and compares.

An epoch can end again, well or badly, and the next one begins. The chronicle
keeps every one of them in `game.legacy.history`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data.epochs import EPOCHS_BY_ID
from ..data.scenarios import SCENARIOS_BY_ID
from .ship import apply_damage, hull_pct

#: Pressure at or above this closes the epoch badly.
BREAK = 1.0

#: How often a situation arrives, in days.
CADENCE = 90


@register
@dataclass
class Situation:
    """One scenario waiting on an answer. Lives on the Game; survives a save."""
    scenario_id: str
    day: int = 0
    over: bool = False
    chosen: int = -1

    @property
    def definition(self):
        return SCENARIOS_BY_ID.get(self.scenario_id)


@register
@dataclass
class Legacy:
    """The epoch you are living in, and the ones you have already lived."""
    epoch: str
    began: int = 0
    pressure: float = 0.0
    since_last: float = 0.0
    answered: list = field(default_factory=list)
    history: list = field(default_factory=list)   # (epoch id, outcome, day)
    outcome: str = ""
    over: bool = False

    @property
    def definition(self):
        return EPOCHS_BY_ID.get(self.epoch)


def held(game) -> Legacy | None:
    return getattr(game, "legacy", None)


def in_epoch(game) -> bool:
    lg = held(game)
    return lg is not None and not lg.over


def begin(game, ending: str) -> dict:
    """Carry on past an ending. Returns what changed, for the dialog to read."""
    epoch = EPOCHS_BY_ID.get(ending)
    if epoch is None:
        return {"ok": False, "why": "That ending has no aftermath."}

    previous = held(game)
    history = list(previous.history) if previous else []
    if previous is not None:
        history.append((previous.epoch, previous.outcome or "closed", game.day))

    game.legacy = Legacy(epoch=epoch.id, began=game.day, history=history)
    # The ending has been taken; the chronicle is running again.
    game.victory = None
    game.ending = ""
    game.dead = False
    game.overgrown = False
    _rewrite(game, epoch)
    game.add_log(f"— {epoch.name} —", "good")
    game.add_log(epoch.opening, "")
    return {"ok": True, "epoch": epoch}


def _rewrite(game, epoch) -> None:
    """What the world becomes. One pass, once, when the epoch opens."""
    if epoch.id in ("containment", "exodus"):
        # The Bloom is beaten or left behind; the sector stops being eaten.
        for system in game.galaxy.systems:
            system.bloom = 0.0
        game.bloom_total = 0.0
        game.bloom_clock = 0.0
    if epoch.id == "ruin":
        # It is all of it, everywhere. Nothing to clean and nothing to reach.
        for system in game.galaxy.systems:
            system.bloom = max(system.bloom, 0.95)
    if epoch.id == "concord":
        for faction_id in list(game.rep):
            if faction_id not in ("bloom",):
                game.rep[faction_id] = max(game.rep.get(faction_id, 0), 60)
    game.flags[f"epoch_{epoch.id}"] = True


def gauge(game) -> dict:
    """Where the pressure stands, for the readout."""
    lg = held(game)
    if lg is None or lg.definition is None:
        return {}
    epoch = lg.definition
    lasted = game.day - lg.began
    return {"epoch": epoch, "pressure": lg.pressure, "gauge": epoch.gauge,
            "days": lasted, "hold": epoch.hold_days,
            "left": max(0, epoch.hold_days - lasted),
            "over": lg.over, "outcome": lg.outcome}


def tick(game, days: float, rng) -> list:
    """Advance the epoch. Returns log lines."""
    lg = held(game)
    if lg is None or lg.over or lg.definition is None:
        return []
    epoch = lg.definition
    out = []
    lg.pressure = min(1.5, lg.pressure + epoch.rate * days)
    lg.since_last += days

    if lg.pressure >= BREAK:
        _close(game, "failure")
        return [("bad", epoch.failure)]
    if game.day - lg.began >= epoch.hold_days:
        _close(game, "triumph")
        return [("good", epoch.triumph)]

    if lg.since_last >= CADENCE and getattr(game, "situation", None) is None:
        lg.since_last = 0.0
        pending = [sid for sid in epoch.scenarios if sid not in lg.answered]
        if pending:
            sid = rng.pick(pending)
            game.situation = Situation(scenario_id=sid, day=game.day)
            scenario = SCENARIOS_BY_ID[sid]
            out.append(("warn", f"{scenario.title}. It wants an answer."))
    return out


def _close(game, outcome: str) -> None:
    lg = held(game)
    lg.over = True
    lg.outcome = outcome
    game.situation = None


def offer(game) -> dict:
    """The situation waiting, if any, with every answer and what it does."""
    pending = getattr(game, "situation", None)
    if pending is None or pending.over or pending.definition is None:
        return {}
    scenario = pending.definition
    return {"scenario": scenario, "title": scenario.title,
            "text": scenario.text,
            "answers": [{"label": a.label, "says": a.says,
                         "effect": dict(a.effect)} for a in scenario.answers]}


def answer(game, index: int) -> dict:
    """Take one of the answers. Applies exactly the effect the card stated."""
    pending = getattr(game, "situation", None)
    if pending is None or pending.over:
        return {"ok": False, "why": "Nothing is waiting."}
    scenario = pending.definition
    if scenario is None or index >= len(scenario.answers):
        return {"ok": False, "why": "Not one of the answers."}

    chosen = scenario.answers[index]
    applied = apply(game, chosen.effect)
    pending.over = True
    pending.chosen = index
    lg = held(game)
    if lg is not None and scenario.id not in lg.answered:
        lg.answered.append(scenario.id)
    game.situation = None
    game.add_log(f"{scenario.title}: {chosen.label}.", "")
    return {"ok": True, "answer": chosen, "applied": applied}


def apply(game, effect: dict) -> dict:
    """The one place an effect is read. What the card says is this dict."""
    done = {}
    lg = held(game)
    if "pressure" in effect and lg is not None:
        lg.pressure = max(0.0, min(1.5, lg.pressure + effect["pressure"]))
        done["pressure"] = effect["pressure"]
    if "credits" in effect:
        game.credits = max(0.0, game.credits + effect["credits"])
        done["credits"] = effect["credits"]
    for faction_id, delta in effect.get("rep", {}).items():
        game.adjust_rep(faction_id, delta)
        done.setdefault("rep", {})[faction_id] = delta
    if "hull" in effect:
        layers = sum(layer.max for layer in game.ship.layers)
        apply_damage(game.ship, abs(effect["hull"]) * layers)
        done["hull"] = hull_pct(game.ship)
    for key, amount in effect.get("stores", {}).items():
        game.stores[key] = max(0.0, game.stores.get(key, 0) + amount)
        done.setdefault("stores", {})[key] = amount
    if "research" in effect:
        from . import research as research_sim
        research_sim.grant(game.research, effect["research"])
        done["research"] = effect["research"]
    if effect.get("flag"):
        game.flags[effect["flag"]] = True
        done["flag"] = effect["flag"]
    if effect.get("close") and lg is not None:
        _close(game, effect["close"])
        done["close"] = effect["close"]
    return done


def summary(game) -> list:
    """Every epoch this chronicle has lived through, oldest first."""
    lg = held(game)
    if lg is None:
        return []
    out = [(EPOCHS_BY_ID.get(eid), outcome, day)
           for eid, outcome, day in lg.history]
    out.append((lg.definition, lg.outcome or "under way", game.day))
    return [row for row in out if row[0] is not None]
