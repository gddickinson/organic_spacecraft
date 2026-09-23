"""The captain's own life, played out rather than handed to them.

`sim/lifepath.py` gives every officer a service record — terms of four
years, a throw to survive each one, a throw to be promoted, a skill, a
mishap, a muster-out — and it gives the captain one too, worked out from
the origin they picked and an age the game chose. That is a *biography*,
and Traveller's opening is not a biography. It is one decision made four or
five times: **serve another term, or get out while you still can.**

This is that decision. `ui/beginning_path.py` offers it; the rules are here.

- **The dice are the sector's, not the button's.** Every throw comes off
  `RNG(f"{seed}:captain-path:{service}")`, so a term has the outcome it was
  always going to have and closing the dialog to open it again does not
  shop for a better one. The choice is where to stop, which is the choice
  Traveller actually offers.
- **Only the decision is stored.** `beginning.Choices` keeps the service
  and how many terms were served, and the record is *derived by replaying*
  — the way every other record in this game is derived. Nothing goes on a
  save that could go stale, and a chronicle begun before this existed still
  has a captain: the origin-derived one, unchanged.
- **One derivation, asked for a length.** `_build` is the whole of it, and
  serving a term is asking it for one more. A generator held on the path
  would do as well until somebody asks for the same captain in another
  process, which is the thing this project builds everything else to
  survive.
- **The risk is priced first.** `odds` quotes the survival throw before the
  term is taken, because a gamble a screen will not price is not a gamble,
  it is a surprise.

A mishap does here what it does to an officer: the career ends. A captain
thrown out of the Charter Navy in their second term has three skills and a
grievance, and that is a better opening than a tidy one.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.rng import RNG
from ..data import careers as table
from . import checks, lifepath

#: The most terms anybody plays out — `lifepath.MOST_TERMS`, re-exported
#: rather than re-chosen, because a captain is not a different sort of
#: person from the officers they hire.
MOST_TERMS = lifepath.MOST_TERMS


@dataclass
class Path:
    """A life being played. Transient: only `service` and the number of
    terms outlive the dialog (`sim/beginning.Choices`)."""

    seed: str
    service: str
    record: object
    career: object
    rank_at: int = 0
    over: bool = False

    @property
    def terms(self) -> int:
        return len(self.record.terms)


def services() -> list:
    """Every service a captain may put themselves forward for.

    All of them. An officer's career is weighted to the station they hold,
    because their history has to explain the job they do; a captain holds
    no station and has nobody to explain themselves to.
    """
    return list(table.CAREERS)


def _build(seed: str, service: str, terms: int) -> tuple:
    """The record after exactly this many terms. **The one derivation.**

    Returns `(record, career, rank_at, rng)` — the generator too, because
    ageing and the muster-out are thrown after the last term and have to
    come off the same stream.
    """
    rng = RNG(f"{seed}:captain-path:{service}")
    record = lifepath.Record(name="", station="captain")
    record.characteristics = lifepath._roll_characteristics(rng, None)
    career = table.CAREER_BY_ID[service]
    rank_at = 0
    if terms > 0:
        fallbacks = [c.id for c in table.CAREERS if c.id != service]
        career, _served, rank_at = lifepath.serve_out(
            rng, record, service, fallbacks, terms, career=career)
    # The record reads properly while it is being played, not only once it
    # is finished: a panel showing "— , 3 terms, aged 18" halfway through is
    # a panel describing nobody. Ageing and the muster-out stay out of here
    # — they are thrown once, at the end, in `record_for`.
    record.age = table.ENTRY_AGE + len(record.terms) * table.TERM_YEARS
    record.career, record.career_name = career.id, career.name
    record.rank = career.ranks[min(rank_at, len(career.ranks) - 1)]
    return record, career, rank_at, rng


def begin(game, service: str) -> Path:
    """Enlist. Rolls the characteristics and nothing else."""
    seed = getattr(game, "seed", "verge") if game is not None else "verge"
    record, career, rank_at, _rng = _build(seed, service, 0)
    return Path(seed=seed, service=service, record=record, career=career,
                rank_at=rank_at)


def odds(path: Path) -> dict:
    """What the next term asks of them, priced before it is taken.

    So a screen can say "Endurance 9, survival on 5+, 83%" rather than
    inviting a captain to guess.
    """
    if path.over:
        return {}
    career = path.career
    stat, target = career.survive
    up_stat, up_target = career.advance
    return {
        "survive_stat": stat,
        "survive_score": path.record.score(stat),
        "survive": checks.chance(0, path.record.score(stat),
                                 lifepath._how(target)),
        "advance_stat": up_stat,
        "advance_score": path.record.score(up_stat),
        "advance": (checks.chance(0, path.record.score(up_stat),
                                  lifepath._how(up_target))
                    if up_stat in checks.CHARACTERISTIC_IDS else 0.0),
        "rank": career.ranks[min(path.rank_at, len(career.ranks) - 1)],
        "term": path.terms + 1,
    }


def may_serve(path: Path) -> tuple:
    """May they take another term? `(ok, why)`."""
    if path.over:
        return False, (path.record.ended or "That career is finished.")
    if path.terms >= MOST_TERMS:
        return False, (f"{MOST_TERMS} terms is "
                       f"{MOST_TERMS * table.TERM_YEARS} years. Nobody is "
                       "taking another.")
    return True, ""


def serve(path: Path) -> dict:
    """One more term. Rebuilt from the top, so the throws cannot be shopped."""
    ok, why = may_serve(path)
    if not ok:
        return {"ok": False, "why": why}
    wanted = path.terms + 1
    record, career, rank_at, _rng = _build(path.seed, path.service, wanted)
    path.record, path.career, path.rank_at = record, career, rank_at
    got = record.terms[-1]
    if got.mishap or len(record.terms) < wanted:
        path.over = True
    return {"ok": True, "term": got, "over": path.over,
            "career": career.name, "mishap": got.mishap}


def muster(path: Path) -> dict:
    """Get out. Whatever the service owes is settled in `record_for`."""
    path.over = True
    if not path.record.ended:
        path.record.ended = (f"Left the {path.career.name} of their own "
                             "accord.")
    return {"ok": True, "terms": path.terms}


def played(choices) -> tuple:
    """`(service, terms)` off the beginning, or `("", 0)` if nobody played."""
    service = getattr(choices, "service", "") or ""
    if service not in table.CAREER_BY_ID:
        return "", 0
    return service, max(0, int(getattr(choices, "service_terms", 0) or 0))


def finish(path: Path, choices) -> None:
    """Write the decision — and only the decision — onto the beginning."""
    choices.service = path.service
    choices.service_terms = path.terms


def record_for(game, choices, name: str = ""):
    """The captain's record as they played it, or None if they did not.

    None is every chronicle begun before this existed and every captain who
    skipped the dialog, and `afoot_people.captain_record` still derives one
    from their origin and their years exactly as it did.
    """
    service, terms = played(choices)
    if not service:
        return None
    seed = getattr(game, "seed", "verge") if game is not None else "verge"
    record, career, rank_at, rng = _build(seed, service, terms)
    served = len(record.terms)
    lifepath._age(record, rng, served)
    lifepath._muster(record, rng, career, served)
    if not record.ended:
        record.ended = f"Left the {career.name} of their own accord."
    record.name, record.station = name, "captain"
    return record


def says(path: Path) -> list:
    """The record so far, in the words a screen shows."""
    return lifepath.says(path.record) if path.record is not None else []
