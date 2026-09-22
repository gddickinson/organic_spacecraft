"""Who somebody was before they came aboard, played out rather than rolled.

*Traveller* makes a character by living their life first: terms of four
years, a roll to survive each one, a roll to be promoted, a skill learned,
and sometimes a mishap that throws them out early. What comes out is a
history, and the numbers are a consequence of it. That is the opposite of a
build, and it is why people still play a game from 1977.

SEEDFALL's officers already had a name, a station, a level, a trait and a
lineage — five facts that never added up to a person. This turns them into
one: six characteristics, a service, a rank, a list of skills with levels,
and the four or five things that actually happened to them.

**Derived, never stored** — the same rule the world profile follows, and for
the same reasons. An officer's record is a pure function of what the
chronicle already knows about them (their id, station, level, trait, lineage
and age) and the sector's seed, so:

- no field is added to a saved dataclass and no migration is needed;
- an officer from a two-year-old save has a service record the moment this
  ships;
- two screens asking in the same frame get the same answer, and asking does
  not move `game.rng`, which a screen must never do.

The rolls are `sim/checks.py`'s — the same 2d6 grammar the rest of the game
will use — so a player who learns to read a survival throw has learned to
read every throw.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.rng import RNG
from ..data import careers as table
from . import checks
from . import lifespan

#: The most terms anybody serves before they are simply too old for it. Six
#: is 24 years and puts a lifer at 42, which is about where the Verge's
#: officers actually are.
MOST_TERMS = 6

#: What a mishap does to the career: it ends. Traveller lets you roll to stay
#: and this does not, because an officer who was thrown out is a better story
#: than one who nearly was, and the record has to be readable in six lines.
#:
#: What ageing costs, per term past `careers.AGEING_FROM`: one point off one
#: physical characteristic, which is slow enough to be a fact of life rather
#: than a punishment.
AGEING_BITE = 1
PHYSICAL = ("str", "dex", "end")

#: Odds at or above which a term was not worth remarking on. A service
#: record's "worst year" line is there to say somebody was in real danger;
#: at nine in ten it is saying nothing.
RISKY = 0.90


@dataclass
class Term:
    """One four-year stretch, and what came of it."""

    career: str
    career_name: str
    number: int
    rank: str
    #: What was learned, and what happened.
    skill: str = ""
    event: str = ""
    #: Set when this is the term that ended the career.
    mishap: str = ""
    #: The throws, kept so a screen can show the odds somebody actually faced.
    survived: object = None
    advanced: object = None


#: How often a term deepens a skill the person already has rather than
#: starting a new one. **Without this everybody comes out flat.** Measured on
#: a fresh crew: picking freely from a career's six skills over three terms
#: gave officers Admin 0, Engineer 0, Vacc Suit 0 and nothing above zero, so
#: a "Chief Engineer" read as somebody who had been shown each job once.
#: Traveller characters specialise because the tables are small and the terms
#: are many; this is the same pressure, stated.
DEEPEN = 0.55


@dataclass
class Record:
    """A whole service history: who they were before the berth."""

    name: str = ""
    station: str = ""
    characteristics: dict = field(default_factory=dict)
    skills: dict = field(default_factory=dict)
    terms: list = field(default_factory=list)
    benefits: list = field(default_factory=list)
    age: int = table.ENTRY_AGE
    #: The career they gave the most of their life to, and how it ended.
    career: str = ""
    career_name: str = ""
    rank: str = ""
    ended: str = ""

    def skill(self, name: str) -> int:                  # noqa: A003
        """Their level in one skill; `checks.UNTRAINED` if never taught it."""
        return self.skills.get(name, checks.UNTRAINED)

    def score(self, name: str) -> int:
        """One characteristic, 0-15."""
        return self.characteristics.get(name, 7)


def _roll_characteristics(rng, officer) -> dict:
    """Six scores, 2d6 each, then bent by what the officer already is.

    The bending is the point: an officer the game has already decided is a
    Chief Engineer of level 4 with the Yards trait should not read as a
    feeble one. The dice give the spread and the record gives the shape.
    """
    got = {c: rng.int(1, 6) + rng.int(1, 6) for c in checks.CHARACTERISTIC_IDS}
    level = int(getattr(officer, "level", 1) or 1)
    lean = table.BY_STATION.get(getattr(officer, "role", ""), ())
    career = table.CAREER_BY_ID.get(lean[0]) if lean else None
    if career is not None:
        # Whatever got them in is what they are good at.
        got[career.qualify[0]] = min(15, got[career.qualify[0]] + 1 + level // 2)
        got[career.survive[0]] = min(15, got[career.survive[0]] + level // 3)
    trait = getattr(officer, "trait_id", None)
    if trait in ("charter", "freehold"):
        got["soc"] = min(15, got["soc"] + 2)
    elif trait in ("yards", "wetwired"):
        got["int"] = min(15, got["int"] + 2)
    elif trait in ("veteran", "reckless"):
        got["end"] = min(15, got["end"] + 2)
    elif trait == "quiet":
        got["int"] = min(15, got["int"] + 1)
        got["dex"] = min(15, got["dex"] + 1)
    return got


def _careers_for(rng, officer) -> tuple:
    """Which service they went into, and what they fell back on.

    Weighted to the station they hold, because an officer's history should
    explain the job they do. A drifter is always possible: not everybody's
    life goes to plan, and the record is better for saying so.
    """
    lean = list(table.BY_STATION.get(getattr(officer, "role", ""), ()))
    if not lean:
        lean = [c.id for c in table.CAREERS]
    first = rng.weighted([(6, lean[0])] +
                         [(3, cid) for cid in lean[1:]] +
                         [(2, "drifter")])
    rest = [cid for cid in lean if cid != first] + ["drifter", "hauler"]
    return first, rest


def _terms_wanted(rng, officer, age) -> int:
    """How long they served, from their level and their age.

    A level-4 officer who is forty has a career behind them; a level-1 who is
    twenty-four has one term and a lot to learn. Both are read off what the
    chronicle already says rather than invented.

    **The age is asked of `lifespan.age_of`, not of the field.** An officer
    written before lineages existed has no age, and the first thing to ask
    for one *invents and stores it* — so this read `None` until any screen
    showed somebody's years and a different number afterwards, and the same
    officer had two service records in one session depending on which tab had
    been opened first. Measured on a fresh chronicle: three of three records
    changed career, terms or skills on the second read.
    """
    level = int(getattr(officer, "level", 1) or 1)
    if age:
        by_age = max(1, int((float(age) - table.ENTRY_AGE) / table.TERM_YEARS))
        return max(1, min(MOST_TERMS, by_age))
    return max(1, min(MOST_TERMS, level + rng.int(0, 1)))


def _learn(record: Record, name: str) -> str:
    """Take a level in a skill, or a first level in it. Returns what to say."""
    if not name:
        return ""
    now = record.skills.get(name, -1)
    record.skills[name] = now + 1 if now >= 0 else 0
    level = record.skills[name]
    return f"{name.replace('_', ' ').title()} {level}"


def of(game, officer) -> Record:
    """One officer's service record. Cheap, stable, and stored nowhere.

    Seeded from the chronicle and the officer's own id, so the same person
    has the same history in every frame, every screen and every process.
    """
    seed = getattr(game, "seed", "verge") if game is not None else "verge"
    rng = RNG(f"{seed}:life:{getattr(officer, 'id', 0)}")
    record = Record(name=getattr(officer, "name", ""),
                    station=getattr(officer, "role", ""))
    record.characteristics = _roll_characteristics(rng, officer)
    first, fallbacks = _careers_for(rng, officer)
    wanted = _terms_wanted(rng, officer, lifespan.age_of(officer, game))
    career = table.CAREER_BY_ID[first]
    served, rank_at = 0, 0
    while served < wanted:
        served += 1
        got = _serve(rng, record, career, served, rank_at)
        record.terms.append(got)
        if got.mishap:
            record.ended = got.mishap
            # Thrown out. Anybody with years left goes somewhere that will
            # have them, which in the Verge is usually nobody.
            if served < wanted and fallbacks:
                career = table.CAREER_BY_ID[fallbacks.pop(0)]
                rank_at = 0
                continue
            break
        if got.advanced is not None and got.advanced.ok:
            rank_at = min(len(career.ranks) - 1, rank_at + 1)
            # A rank is worth something: Traveller hands out a skill with
            # every promotion, and it is most of why a long career reads
            # differently from a short one.
            pool = list(career.skills) + list(career.officer_skills or ())
            got.skill += " · " + _learn(record, _pick_skill(rng, record, pool))
    record.age = table.ENTRY_AGE + served * table.TERM_YEARS
    record.career = career.id
    record.career_name = career.name
    record.rank = career.ranks[min(rank_at, len(career.ranks) - 1)]
    _age(record, rng, served)
    _muster(record, rng, career, served)
    _qualify(record, officer)
    _bought(game, record, officer)
    _staged(game, record, officer)
    if not record.ended:
        record.ended = f"Left the {career.name} of their own accord."
    return record


def _bought(game, record: Record, officer) -> None:
    """Fold on what a concourse has done to them since they signed on.

    A service record is *derived* and may be recomputed at will; a fitted
    cortex link and a course somebody paid for are **facts**, and they live
    on the save (`sim/clinic.py`, `game.fitted` and `game.taught`). Folding
    them on here rather than at the twenty places that read a record is what
    makes a muscle weave show up in the gunnery check, the boarding action,
    the ship's abilities table and the officer's own sheet at once.

    Nothing is taken away and nothing goes past `SCORE_CAP`: a treatment is
    a floor under a characteristic, never a replacement for a life.
    """
    if game is None:
        return
    from ..data import treatments as clinic_table
    key = str(getattr(officer, "id", 0))
    for tid in (getattr(game, "fitted", None) or {}).get(key, []):
        got = clinic_table.TREATMENT_BY_ID.get(tid)
        if got is None:
            continue
        for cid, delta in got.gives.items():
            if cid in record.characteristics:
                record.characteristics[cid] = min(
                    clinic_table.SCORE_CAP,
                    record.characteristics[cid] + delta)
        if got.skill:
            record.skills[got.skill] = max(record.skills.get(got.skill, -1), 0)
    for name, levels in (getattr(game, "taught", None) or {}).get(
            key, {}).items():
        if name in table.SKILLS:
            record.skills[name] = record.skills.get(name, -1) + int(levels)


def _staged(game, record: Record, officer) -> None:
    """Fold on where they are in their run, and how far apart their clocks are.

    `data/stages.py` is what a stretch of life is worth — the green are
    quick and unlistened-to, the declining slow and worth hearing — and what
    decades lived beyond the body's years do to somebody. Both are deltas on
    the six scores, kept between 1 and the clinic's cap like everything else
    folded on here.
    """
    from ..data import treatments as clinic_table
    for got in (lifespan.stage_of(officer, game).gives,
                lifespan.gap_of(officer, game).gives):
        for cid, delta in got.items():
            if cid in record.characteristics:
                record.characteristics[cid] = max(1, min(
                    clinic_table.SCORE_CAP,
                    record.characteristics[cid] + delta))


def _qualify(record: Record, officer) -> None:
    """Make sure they can do the job the crew list says they do.

    A career is only *weighted* towards a station, so the dice could leave a
    Chief Engineer who had never touched a drive and a Navigator who could
    not plot — which reads as a broken crew list rather than as an unlucky
    life. Their station's own skill is brought up to what their level claims
    and the one beside it to trained, and **nothing is ever taken away**: an
    engineer who really did spend four terms learning it keeps all of it.
    """
    pair = table.STATION_SKILLS.get(record.station or "", ())
    if not pair:
        return
    want = max(1, min(4, int(getattr(officer, "level", 1) or 1) - 1))
    record.skills[pair[0]] = max(record.skills.get(pair[0], -1), want)
    # A station may name more than two: the first is brought to what their
    # level claims, and everything beside it to trained.
    for beside in pair[1:]:
        record.skills[beside] = max(record.skills.get(beside, -1), 0)


def _serve(rng, record: Record, career, number: int, rank_at: int) -> Term:
    """One term: survive it, learn something, and see what happened."""
    rank = career.ranks[min(rank_at, len(career.ranks) - 1)]
    term = Term(career=career.id, career_name=career.name, number=number,
                rank=rank)
    stat, target = career.survive
    term.survived = checks.roll(
        rng, skill=0, score=record.score(stat), how=_how(target),
        about=f"{career.name}, term {number}", what="Survival")
    if not term.survived.ok:
        term.mishap = rng.pick(career.mishaps) if career.mishaps else \
            f"Invalided out of the {career.name}."
        # A mishap still teaches something: four years is four years.
        term.skill = _learn(record, rng.pick(career.skills))
        return term
    pool = list(career.skills)
    if rank_at >= 3 and career.officer_skills:
        pool += list(career.officer_skills)
    term.skill = _learn(record, _pick_skill(rng, record, pool))
    if career.events:
        term.event = _pick_event(rng, record, career)
    stat, target = career.advance
    if stat in checks.CHARACTERISTIC_IDS:
        term.advanced = checks.roll(
            rng, skill=0, score=record.score(stat), how=_how(target),
            about=f"{career.name}, term {number}", what="Advancement")
    return term


def _pick_skill(rng, record: Record, pool: list) -> str:
    """What this term teaches: usually more of what they already do."""
    held = [name for name in pool if name in record.skills]
    if held and rng.chance(DEEPEN):
        return rng.pick(held)
    fresh = [name for name in pool if name not in record.skills]
    return rng.pick(fresh or pool)


def _pick_event(rng, record: Record, career) -> str:
    """Something that happened, and not the same something twice.

    A record that said "caught a fault nobody else had seen" three terms
    running read as a bug, which it was: the pick had no memory.
    """
    told = {term.event for term in record.terms if term.event}
    left = [line for line in career.events if line not in told]
    if not left:
        return ""
    return rng.pick(left) if rng.chance(0.75) else ""


def _how(target: int) -> str:
    """A career's own 2d6 target as one of the grammar's difficulties.

    Traveller writes a career's throws as "survive 5+"; this game says every
    check is against eight with a difficulty modifier, so the two are the
    same sentence in different words and the conversion lives here once.
    """
    dm = checks.TARGET - int(target)
    best, gap = "average", 99
    for cid, _name, value in checks.DIFFICULTIES:
        if abs(value - dm) < gap:
            best, gap = cid, abs(value - dm)
    return best


def _age(record: Record, rng, served: int) -> None:
    """What the years take. Nothing before thirty-four, then a little."""
    if record.age <= table.AGEING_FROM:
        return
    over = (record.age - table.AGEING_FROM) // table.TERM_YEARS + 1
    for _step in range(over):
        which = rng.pick(PHYSICAL)
        record.characteristics[which] = max(
            1, record.characteristics.get(which, 7) - AGEING_BITE)


def _muster(record: Record, rng, career, served: int) -> None:
    """What they walked away with. One thing a term, and no more than three."""
    if not career.benefits:
        return
    for _step in range(min(3, max(1, served // 2))):
        got = rng.pick(career.benefits)
        if got not in record.benefits:
            record.benefits.append(got)


# ── what the rest of the game asks ─────────────────────────────────────────

def skill_aboard(game, name: str) -> tuple:
    """The best level in one skill anywhere on the bridge, and whose it is.

    The question every check about the *ship* wants answered: not "is the
    captain good at this" but "is there anybody aboard who is". Returns
    `(level, who)`, with `checks.UNTRAINED` and None when nobody is.
    """
    best, who = checks.UNTRAINED, None
    for officer in getattr(game, "officers", []) or []:
        if getattr(officer, "retired", False):
            continue
        got = of(game, officer).skill(name)
        if got > best:
            best, who = got, officer
    return best, who


def says(record: Record) -> list:
    """The service record as a screen would print it.

    A term names its service only when the service *changed* — a record that
    said "Concordat Yards" on all four lines was four copies of one fact,
    and the one thing worth seeing is the year somebody was thrown out of
    one thing and into another.
    """
    career = table.CAREER_BY_ID.get(record.career)
    said = [f"{record.career_name} — {record.rank}, "
            f"{len(record.terms)} term(s), aged {record.age}."]
    if career is not None:
        said.append(career.blurb)
    was = ""
    for term in record.terms:
        line = f"  {term.number}. "
        if term.career != was:
            line += f"{term.career_name}, "
            was = term.career
        line += term.rank.lower()
        if term.skill:
            line += f" — {term.skill}"
        said.append(line)
        if term.event:
            said.append(f"     {term.event}")
        if term.mishap:
            said.append(f"     {term.mishap}")
    if record.ended:
        said.append(record.ended)
    hard = _hardest(record)
    if hard:
        said.append(hard)
    if record.benefits:
        said.append("Came away with: " + ", ".join(record.benefits) + ".")
    return said


def _hardest(record: Record) -> str:
    """The worst throw they faced, and the odds it was at.

    The line that turns a service record into a story somebody tells: a
    picket who came through four terms at 41% a term is a different person
    from one who served four terms at 83%, and neither of them chose it.
    """
    rows = [t for t in record.terms if t.survived is not None]
    if not rows:
        return ""
    worst = min(rows, key=lambda t: checks.chance(
        t.survived.skill, 7, t.survived.how))
    got = checks.chance(0, record.score(
        table.CAREER_BY_ID[worst.career].survive[0]), worst.survived.how)
    # Only when it was actually dangerous. "Worst year: 97% to come through
    # it" is a line about nothing, and a drifter's life is not perilous in
    # this model however hard it is.
    if got >= RISKY:
        return ""
    return (f"Worst year: term {worst.number}, "
            f"{worst.survived.how.replace('_', ' ')} odds — {got:.0%} to "
            "come through it.")


def characteristics_line(record: Record) -> str:
    """The six scores on one line, as a character sheet writes them."""
    return "  ".join(
        f"{cid.upper()} {record.score(cid)}{_dm(record.score(cid))}"
        for cid, _name, _note in checks.CHARACTERISTICS)


def _dm(score: int) -> str:
    got = checks.modifier(score)
    return f" ({got:+d})" if got else ""


def skills_line(record: Record) -> str:
    """Every skill they hold, best first."""
    if not record.skills:
        return "No training anybody wrote down."
    rows = sorted(record.skills.items(), key=lambda r: (-r[1], r[0]))
    return "  ".join(f"{name.replace('_', ' ').title()} {level}"
                     for name, level in rows)
