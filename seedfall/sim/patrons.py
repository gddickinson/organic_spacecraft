"""The person who is asking, and the thing they did not say.

SEEDFALL's board posts work from *offices*: the Charter wants tonnage moved,
an institute wants a system charted. That reads like a freight desk, and
Traveller does not read like a freight desk. There the work comes from a
**patron** — somebody in a room, with a reason — and the first thing anybody
running the game is told about a patron is that the job may not be what they
said it was.

Three things make that a decision rather than a dice roll:

- **A port has a cast, and it is the same cast next year.** Three patrons a
  port (`CAST`), derived from the sector seed and stored nowhere, so the
  fixer at Vaux Hollow is *that* fixer — and `sim/memory.py` keeps what you
  and they have done to each other, the same way it keeps a harbourmaster.
- **What they are tells you most of it.** A Charter factor is dull and
  correct. A fixer pays thirty per cent over the odds, which is the single
  most reliable thing anybody can tell you about the work
  (`data/patrons.PATRONS`).
- **And you can read them before you sign.** One `streetwise` check against
  how guarded they are, with the odds quoted first. Passing it gives you the
  twist's *tell* — the thing you could have noticed — and the check is
  derived from the contract's own id, so it cannot be re-rolled by closing
  the screen and opening it again.

Every twist is something the game can already do to you: a fee that arrives
short, a power that takes an interest, a hold opened at the far end
(`sim/lawlevel.py`). A ticket that turns is the ordinary machinery finding
you, not a special case — which is why one of them is in your favour.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.rng import RNG
from ..data import lore
from ..data.patrons import (GENEROUS_SHARE, HOT_HEAT, PATRONS, PATRONS_BY_ID,
                            SHORT_SHARE, TWISTS, TWISTS_BY_ID)

#: How many patrons work a port. Three is enough for a board to have
#: characters in it and few enough that you learn their names.
CAST = 3

#: How hard reading somebody is, before their own guardedness.
HOW = "average"

#: What a completed ticket is worth to the patron's opinion of you, and what
#: a failed one costs. Read through `sim/memory`, like every other mind.
KEPT, DROPPED = 1.1, 1.4

#: The share of a board that is still an office posting with nobody behind
#: it. Not everything is a person: a standing order renewed quarterly is
#: exactly the thing that has no face, and a board of six faces reads as a
#: cast list rather than as a port.
OFFICE_SHARE = 0.28

#: How much knowing somebody helps you read them, and the most it is ever
#: worth. Dealing with the same fixer four times should tell you things a
#: stranger cannot see, and should not turn into certainty.
KNOWN_DM, KNOWN_MOST = 1, 2


@dataclass(frozen=True)
class Patron:
    """One person who posts work at one port."""

    system_id: int
    slot: int
    kind_id: str
    name: str

    @property
    def what(self):
        return PATRONS_BY_ID[self.kind_id]

    @property
    def key(self) -> str:
        """How `sim/memory` knows them."""
        return f"patron:{self.system_id}:{self.slot}"

    @property
    def id(self) -> str:                                # noqa: A003
        """What a contract carries to name them."""
        return f"{self.system_id}:{self.slot}"

    @property
    def title(self) -> str:
        return f"{self.name}, {self.what.name.lower()}"


_MADE: dict = {}


def cast(game, system) -> tuple:
    """The people who post work at this port. Derived; cheap to ask twice."""
    key = (getattr(game, "seed", "verge"), getattr(system, "id", -1))
    got = _MADE.get(key)
    if got is None:
        rng = RNG(f"{key[0]}:patrons:{key[1]}")
        out = []
        for slot in range(CAST):
            kind = rng.pick(PATRONS)
            name = f"{rng.pick(lore.CREW_FIRST)} {rng.pick(lore.CREW_LAST)}"
            out.append(Patron(int(key[1]), slot, kind.id, name))
        got = _MADE[key] = tuple(out)
    return got


def of(game, contract):
    """Who posted this contract, or None for an office posting."""
    marker = getattr(contract, "patron", "") or ""
    if ":" not in marker:
        return None
    system_id, slot = marker.split(":", 1)
    system = next((s for s in game.galaxy.systems
                   if s.id == int(system_id)), None)
    if system is None:
        return None
    here = cast(game, system)
    return here[int(slot)] if int(slot) < len(here) else None


def posts(patron, kind: str) -> bool:
    """Would this sort of person post this sort of work?"""
    wants = patron.what.posts
    return not wants or kind in wants


# ── writing the ticket ─────────────────────────────────────────────────────

def attach(game, system, contract) -> None:
    """Give a posting a person, and decide what they are not saying.

    Called from `contracts.generate` while the contract is being shaped, so
    the fee the board quotes is the fee the patron would pay — a posting
    that says one number and pays another when you accept it is a lie the
    *game* is telling, which is a different thing entirely from one the
    patron is.

    **Off the ticket's own id, not the board's dice.** The first draft took
    three draws from the generator's rng, which moved every draw after it:
    measured, the careful captain's five-year chronicle diverged on two
    seeds of three and one of them stopped reaching its ending — with the
    twists switched off entirely, which is how it was ruled out as the
    cause. A feature that shifts a shared stream changes every balance
    reading in the game for reasons that have nothing to do with the
    feature. This one adds a person to a posting and nothing else moves.
    """
    here = [p for p in cast(game, system) if posts(p, contract.kind)]
    if not here:
        return
    rng = RNG(f"{getattr(game, 'seed', 'verge')}:ticket:{contract.id}")
    if rng.chance(OFFICE_SHARE):
        return                          # a posting with nobody behind it
    patron = rng.pick(here)
    contract.patron = patron.id
    contract.reward = max(1, round(contract.reward * patron.what.pays))
    if not rng.chance(patron.what.slippery):
        return
    able = [t for t in TWISTS if not t.kinds or contract.kind in t.kinds]
    if able:
        contract.twist = rng.pick(able).id


def twist_of(contract):
    """The twist on this ticket, or None. **Not for a screen** — see `reads`."""
    return TWISTS_BY_ID.get(getattr(contract, "twist", "") or "")


# ── reading them ───────────────────────────────────────────────────────────

def _skill(game) -> tuple:
    """The best read aboard: `(skill, characteristic, who)`.

    **Whoever aboard is best at this does it**, the way a sortie is flown by
    whoever holds the ticket (`sim/craft.best_pilot`). Measured with the
    captain alone: streetwise is untrained on most captains, which is -3,
    and against a fixer's guardedness the odds came out at 0% — a mechanic
    the game offers and nobody in it can ever use. A bridge with a drifter
    or a purser on it can read a room, and that is what they are for.
    """
    from . import afoot_people, lifepath
    best = (afoot_people.captain_record(game).skill("streetwise"),
            afoot_people.captain_record(game).score("soc"),
            afoot_people.captain_name(game))
    for officer in getattr(game, "officers", []) or []:
        life = lifepath.of(game, officer)
        skill = max(life.skill("streetwise"), life.skill("broker"))
        if skill > best[0]:
            best = (skill, life.score("soc"), officer.name)
    return best


def _known(game, patron) -> int:
    """What having dealt with them before is worth to the check."""
    return min(KNOWN_MOST, KNOWN_DM * dealt(game, patron)["met"])


def forecast(game, contract) -> float:
    """How likely you are to read this patron, before you try.

    Quoted on the card, because a check a screen offers without its odds is
    a coin the player cannot price.
    """
    from . import checks
    patron = of(game, contract)
    if patron is None:
        return 0.0
    skill, score, _who = _skill(game)
    return checks.chance(skill, score, HOW,
                         extra=_known(game, patron) - patron.what.guarded)


def reads(game, contract) -> dict:
    """What you can tell about this ticket, before you sign it.

    Derived from the contract's own id, so the answer is the same every
    time the card is drawn: a check you can re-roll by closing a screen is
    not a check, it is a button that says yes eventually.
    """
    from . import checks
    patron = of(game, contract)
    if patron is None:
        return {"ok": False, "why": "Nobody is asking; it is a posting."}
    skill, score, who = _skill(game)
    check = checks.roll(RNG(f"{game.seed}:read:{contract.id}"), skill, score,
                        HOW, extra=_known(game, patron) - patron.what.guarded,
                        what=f"{who} reading {patron.name}")
    twist = twist_of(contract)
    if not check.ok:
        return {"ok": False, "check": check, "patron": patron,
                "line": f"You cannot get a read on {patron.name}."}
    return {"ok": True, "check": check, "patron": patron,
            "twist": twist.id if twist else "",
            "line": twist.tell if twist else
                    (f"{patron.name} is telling you the whole of it. As far "
                     "as you can tell, the posting is the job.")}


def dealt(game, patron) -> dict:
    """Your record with this person, out of `sim/memory`.

    **A read that does not write.** `memory.mind_for` makes a mind when it
    finds none, and gives it a past while it is at it — which is right when
    somebody is being spoken to and quite wrong here, because the board
    asks this for every card on every repaint. A captain who scrolled past
    a posting would have invented three people and their histories. This
    looks; `_note` is the only thing that brings one into being.
    """
    from . import memory as memory_sim
    mind = memory_sim.minds(game).get(patron.key)
    if mind is None:
        return {"met": 0, "kept": 0, "dropped": 0, "mind": None}
    kept = sum(1 for m in getattr(mind, "memories", []) or []
               if getattr(m, "kind", "") == "work")
    dropped = sum(1 for m in getattr(mind, "memories", []) or []
                  if getattr(m, "kind", "") == "failure")
    return {"met": int(getattr(mind, "met", 0) or 0),
            "kept": kept, "dropped": dropped, "mind": mind}


# ── and what they did not say ──────────────────────────────────────────────

def fire(game, contract, paid: int) -> dict:
    """The ticket is finished. What was not on the posting happens now.

    Returns `{"paid": int, "lines": [(text, tint)]}` — the fee actually
    handed over, which `contracts._pay` uses instead of the posted one.
    """
    twist, patron = twist_of(contract), of(game, contract)
    out: dict = {"paid": paid, "lines": []}
    if patron is not None:
        _note(game, patron, contract, kept=True)
    if twist is None:
        return out
    out["twist"] = twist.id
    tint = "good" if twist.good else "bad"
    who = patron.name if patron is not None else "the office"
    if twist.id == "short":
        out["paid"] = max(1, round(paid * SHORT_SHARE))
        out["lines"].append((f"{twist.blurb} {who} is not answering.", tint))
    elif twist.id == "generous":
        out["paid"] = round(paid * (1.0 + GENEROUS_SHARE))
        out["lines"].append((f"{twist.blurb} {who} pays it without being "
                             "asked.", tint))
    elif twist.id == "hot":
        out["lines"].append((twist.blurb, tint))
        _heat(game, contract)
    elif twist.id == "contraband":
        out["lines"].append((twist.blurb, tint))
        out["paid"] = paid
        _fined(game, contract, out)
    return out


def _heat(game, contract) -> None:
    """Somebody who lost by this now knows your hull did it."""
    from . import customs as customs_sim
    from . import dockets
    from ..data.factions import FACTIONS_BY_ID
    others = [f for f in FACTIONS_BY_ID if f != contract.issuer]
    if not others:
        return
    them = RNG(f"{game.seed}:hot:{contract.id}").pick(others)
    customs_sim.add_heat(game, them, HOT_HEAT)
    dockets.allege(game, them, "contraband",
                   f"work done against them under a posting at "
                   f"{_where(game, contract)}", weight=1.0)


def _fined(game, contract, out: dict) -> None:
    """The hold is opened at the far end, and the drums are not yours."""
    from . import customs as customs_sim
    port = getattr(game.system, "port", None)
    faction = getattr(port, "faction", None) or contract.issuer
    fine = min(game.credits, round(out["paid"] * 0.6))
    game.credits -= fine
    customs_sim.add_heat(game, faction, 0.3)
    game.adjust_rep(faction, -6)
    out["lines"].append((f"Fined {fine:,} for what was in them, and it is "
                         "on your file.", "bad"))


def _where(game, contract) -> str:
    system = next((s for s in game.galaxy.systems
                   if s.id == contract.issued_at), None)
    return getattr(system, "name", "a quay")


def failed(game, contract) -> None:
    """A ticket run out or abandoned. The person remembers."""
    patron = of(game, contract)
    if patron is not None:
        _note(game, patron, contract, kept=False)


def _note(game, patron, contract, kept: bool) -> None:
    from . import memory as memory_sim
    kind = contract.definition.name.lower()
    memory_sim.note(
        game, patron.key, "work" if kept else "failure",
        (f"you finished the {kind} they posted" if kept else
         f"you took the {kind} they posted and did not finish it"),
        KEPT if kept else DROPPED,
        tags=["patron", contract.kind], name=patron.name, entity="patron")


def opening(game, contract) -> str:
    """What they say when you sit down — read out on accepting the ticket.

    A patron is a person in a room, and the room is the only part of that a
    screen can show. `PatronKind.line` is what they do with their hands.
    """
    patron = of(game, contract)
    return patron.what.line if patron is not None else ""


def says(game, contract) -> str:
    """One line for a card: who is asking, and what they are like."""
    patron = of(game, contract)
    if patron is None:
        return ""
    record = dealt(game, patron)
    met = record["met"]
    return (f"{patron.title}. " + patron.what.blurb
            + (f" You have dealt with them {met} time"
               f"{'' if met == 1 else 's'} before." if met else ""))
