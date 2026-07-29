"""Running the standing programmes, and what becomes of what they find.

See `data/programmes.py` for why this exists: the tech tree is finite and the
game is not, so a bench that has learned everything was accruing points that
nothing could ever spend.

The shape is three questions, and each is answered in one place here:

* **What can this bench run?** A programme whose branch is exhausted.
* **How does a round finish?** The same points that drove the tree, spent
  against a cost that rises each round.
* **What is a finding for?** File it with one power, publish it to all four, or
  sell it. Each consumes the finding; nothing else does.

Findings deliberately buy no hull points and no stat. An endgame bench that
improved the ship would only inflate it; one that pays in standing and credits
feeds the political game instead, which is where the interesting decisions are.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data.factions import FACTIONS_BY_ID
from ..data.programmes import (FILE_RATE, FILE_RIVAL_COST, INTEREST,
                              PROGRAMMES, PROGRAMMES_BY_ID, PUBLISH_SHARE,
                              ROUND_GROWTH, SELL_RATE, WORTH_PER_POINT)
from ..data.tech import TECH


@register
@dataclass
class Finding:
    """One result, owned and not yet spent."""

    programme: str
    #: Which round of that programme produced it, from 1.
    round: int
    #: The day it was finished, for the panel.
    day: int
    #: What it is worth, derived from the round that made it. Stored because
    #: the round cost is a function of the programme's *current* round, which
    #: has moved on by the time anybody files this.
    worth: float


@register
@dataclass
class Programmes:
    """The bench's standing work: what it is running and what it has found."""

    #: programme id -> rounds completed.
    rounds: dict = field(default_factory=dict)
    #: The programme currently being run, and points banked toward its round.
    current: str | None = None
    progress: float = 0.0
    #: Findings in hand, oldest first.
    findings: list = field(default_factory=list)
    #: How many have been filed, published and sold, for the panel and the
    #: chronicle. Kept because "what has this bench been for?" is a question
    #: worth answering years later.
    filed: int = 0
    published: int = 0
    sold: int = 0


def state(game) -> Programmes:
    """The bench's standing work, made if this chronicle has none yet."""
    got = getattr(game, "programmes", None)
    if not isinstance(got, Programmes):
        got = Programmes()
        game.programmes = got
    return got


# ── what is open ───────────────────────────────────────────────────────────

def branch_complete(game, branch: str) -> bool:
    """Is every technology in this branch unlocked?"""
    known = set(game.research.unlocked)
    nodes = [t.id for t in TECH if t.branch == branch]
    return bool(nodes) and all(tid in known for tid in nodes)


def available(game) -> list:
    """Every programme this bench could run, in the order they are listed."""
    return [p for p in PROGRAMMES if branch_complete(game, p.branch)]


def round_cost(game, programme_id: str) -> float:
    """What the *next* round of this programme costs, in research points.

    `base · growth^done`, so the first round is the cheapest thing the bench
    ever does with a spare afternoon and the tenth is twenty times that. The
    rise is the whole reason a finished tree does not become a fountain.
    """
    spec = PROGRAMMES_BY_ID.get(programme_id)
    if spec is None:
        return 0.0
    done = int(state(game).rounds.get(programme_id, 0))
    return spec.base_cost * (ROUND_GROWTH ** done)


def worth_of_round(cost: float) -> float:
    """What a finding from a round of this cost is worth.

    One expression, read by the preview and by the act, because a second copy
    is how this project produced a free treaty and a phantom haggle payment.
    """
    return round(max(0.0, cost) * WORTH_PER_POINT, 2)


def set_programme(game, programme_id: str | None) -> bool:
    """Put the bench on a programme. Switching loses the part-done round."""
    live = state(game)
    if programme_id is None:
        live.current = None
        return True
    if programme_id not in {p.id for p in available(game)}:
        return False
    if live.current != programme_id:
        live.progress = 0.0
    live.current = programme_id
    return True


# ── running ────────────────────────────────────────────────────────────────

def can_take(game) -> bool:
    """Is there a programme ready to receive the tree's spare points?

    Asked *before* the points are taken. `research.take_spare` zeroes what it
    hands over — deliberately, so a day's work cannot be spent twice — which
    means taking it with nowhere to put it destroys it. The first draft did
    exactly that: a bench standing down threw away every point the tree could
    not use, which is the same fault this whole file exists to fix, in a
    fresh costume.
    """
    live = state(game)
    return bool(live.current) and live.current in {p.id for p in available(game)}


def tick(game, points: float) -> Finding | None:
    """Spend research points on the standing programme. Returns a finding.

    Called with the points the tree could not use — see `core/clock.py`. That
    is the whole fix: the bench's output had nowhere to go once `researchable`
    came back empty, and it went into a number the screen displayed for ever.
    """
    live = state(game)
    if not live.current or points <= 0:
        return None
    if live.current not in {p.id for p in available(game)}:
        return None                     # the branch was somehow un-learned
    live.progress += points
    cost = round_cost(game, live.current)
    if live.progress < cost:
        return None
    live.progress -= cost
    live.rounds[live.current] = int(live.rounds.get(live.current, 0)) + 1
    found = Finding(programme=live.current,
                    round=int(live.rounds[live.current]),
                    day=int(game.day),
                    worth=worth_of_round(cost))
    live.findings.append(found)
    return found


# ── what a finding is for ──────────────────────────────────────────────────

def interest(programme_id: str, power: str) -> float:
    """How much this power cares about that programme's subject."""
    return INTEREST.get(programme_id, {}).get(power, 1.0)


def powers(game) -> list:
    """The powers a finding can be filed with: the real, visible ones."""
    from . import diplomacy as dip
    return [p for p in dip.POWERS
            if p in FACTIONS_BY_ID and not FACTIONS_BY_ID[p].hidden]


def preview(game, finding: Finding, door: str,
            power: str | None = None) -> dict:
    """What a door does with this finding, without doing it.

    Every number a screen shows comes from here, and `spend` reads the same
    function rather than recomputing — the arrangement whose absence has cost
    this project a free treaty, an ungranted favour and a phantom payment.
    """
    spec = PROGRAMMES_BY_ID.get(finding.programme)
    if spec is None:
        return {"ok": False, "why": "No such programme."}
    out = {"ok": True, "door": door, "standing": [], "credits": 0,
           "worth": finding.worth, "subject": spec.subject, "why": ""}

    if door == "sell":
        out["credits"] = int(round(finding.worth * SELL_RATE))
        return out

    if door == "publish":
        out["standing"] = [
            (p, round(finding.worth * FILE_RATE * PUBLISH_SHARE
                      * interest(finding.programme, p), 1))
            for p in powers(game)]
        return out

    if door == "file":
        if power not in powers(game):
            return {"ok": False, "why": "Nobody to file it with."}
        gain = round(finding.worth * FILE_RATE
                     * interest(finding.programme, power), 1)
        moved = [(power, gain)]
        # Filing is partisan, and this project's rule is that a public act is
        # read by everybody. `allegiance.offended_by` is the same door every
        # other public act asks.
        from . import allegiance
        for other, severity in allegiance.offended_by(game, power):
            cost = round(gain * FILE_RIVAL_COST * severity, 1)
            if cost > 0:
                moved.append((other, -cost))
        out["standing"] = moved
        return out

    return {"ok": False, "why": f"No such door: {door}"}


def spend(game, finding: Finding, door: str, power: str | None = None) -> dict:
    """Do it. The finding is consumed either way, and only here."""
    live = state(game)
    if finding not in live.findings:
        return {"ok": False, "why": "That finding is already spent."}
    plan = preview(game, finding, door, power)
    if not plan.get("ok"):
        return plan

    for who, delta in plan["standing"]:
        game.rep[who] = game.rep.get(who, 0) + delta
    if plan["credits"]:
        game.credits += plan["credits"]

    live.findings.remove(finding)
    if door == "file":
        live.filed += 1
    elif door == "publish":
        live.published += 1
    else:
        live.sold += 1

    spec = PROGRAMMES_BY_ID[finding.programme]
    game.add_log(_line(spec, door, power, plan), "good")
    game.recompute()
    return plan


def _line(spec, door: str, power: str | None, plan: dict) -> str:
    """What the chronicle records."""
    if door == "sell":
        return (f"Sold the {spec.name.lower()} findings on the open market for "
                f"{plan['credits']:,} credits. No questions, no thanks.")
    if door == "publish":
        return (f"Published the {spec.name.lower()} findings openly. Four "
                "powers now have them and none of them owes you for it.")
    name = FACTIONS_BY_ID[power].short if power in FACTIONS_BY_ID else power
    return (f"Filed the {spec.name.lower()} findings with the {name} alone. "
            "Everybody else noticed.")


def summary(game) -> dict:
    """What the bench has been for, for the panel."""
    live = state(game)
    return {"running": live.current,
            "rounds": sum(int(n) for n in live.rounds.values()),
            "in_hand": len(live.findings),
            "filed": live.filed, "published": live.published,
            "sold": live.sold,
            "open": [p.id for p in available(game)]}
