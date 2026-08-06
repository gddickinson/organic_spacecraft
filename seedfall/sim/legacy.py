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

#: A situation left unanswered this long is decided in your absence, at its
#: worst answer — the same principle the law's tribunals run on. Without it,
#: never answering was a strategy: an open situation blocks the next one, so
#: ignoring the first collapsed an epoch's pressure ceiling to pure drift
#: and made the slow epochs guaranteed triumphs by inattention.
ABSENCE_DAYS = 120


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


def rested(game) -> bool:
    """A final epoch has closed and the chronicle sails on.

    The clock reads this beside `in_epoch`: once the last age has been lived
    through — no sequel followed it — no further ending is *detected*, and
    the calendar keeps running. Without it, `check_victory` re-detected the
    still-true condition on the tick after the close and `advance_days`
    early-returned for ever: a frozen calendar with no signal, which the
    module docstring's own promise ("the next one begins") forbids.
    """
    lg = held(game)
    return lg is not None and lg.over


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
    # Everyone hears about this. It is the largest thing that has happened in
    # the Verge and it is the player's doing, so every power holds a memory of
    # it and their envoys will bring it up.
    from . import memory as memory_sim
    memory_sim.broadcast(game, "news",
                         f"the Verge turned over into {epoch.name}, and it was "
                         "your doing", salience=1.4,
                         tags=["epoch", epoch.id], among=("faction", "port"))
    from . import comms as comms_sim
    comms_sim.send(game, "news", "Sector bulletin", "news",
                   f"The Verge turns: {epoch.name}", epoch.opening)
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
        return [("bad", epoch.failure)] + _close(game, "failure")
    if game.day - lg.began >= epoch.hold_days:
        return [("good", epoch.triumph)] + _close(game, "triumph")

    # A question ignored long enough answers itself, badly.
    pending = getattr(game, "situation", None)
    if (pending is not None and not pending.over
            and pending.definition is not None
            and game.day - pending.day >= ABSENCE_DAYS):
        scenario = pending.definition
        worst = max(scenario.answers,
                    key=lambda a: a.effect.get("pressure", 0.0))
        apply(game, worst.effect)
        if scenario.id not in lg.answered:
            lg.answered.append(scenario.id)
        game.situation = None
        out.append(("bad", f"{scenario.title}: decided in your absence — "
                           f"{worst.label}."))

    if lg.since_last >= CADENCE and getattr(game, "situation", None) is None:
        lg.since_last = 0.0
        pending = [sid for sid in epoch.scenarios if sid not in lg.answered]
        if pending:
            sid = rng.pick(pending)
            game.situation = Situation(scenario_id=sid, day=game.day)
            scenario = SCENARIOS_BY_ID[sid]
            out.append(("warn", f"{scenario.title}. It wants an answer."))
    return out


def _close(game, outcome: str) -> list:
    """Close the epoch, and turn the age or let the chronicle rest.

    Returns log lines. A sequel (`data/epochs.sequel_*`) opens through the
    same `begin` the endings dialog uses, which records this epoch into the
    history; with no sequel the chronicle *rests* — see `rested`.
    """
    lg = held(game)
    lg.over = True
    lg.outcome = outcome
    game.situation = None
    epoch = lg.definition
    sequel = ""
    if epoch is not None:
        sequel = (epoch.sequel_failure if outcome == "failure"
                  else epoch.sequel_triumph)
    if sequel and EPOCHS_BY_ID.get(sequel) is not None:
        told = begin(game, sequel)
        if told.get("ok"):
            return [("warn" if outcome == "failure" else "good",
                     f"The age turns: {EPOCHS_BY_ID[sequel].name}.")]
    return [("", "The chronicle rests. What happens next is not an ending; "
                 "it is just what happens next.")]


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
