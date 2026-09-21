"""A whole person, not a station: where they are from, who they know, what they own.

`sim/lifepath.py` answers what somebody *did* — the terms, the ranks, the
skills. This is everything round it: the world they grew up on, who raised
them, the berths before yours, the people attached to them, what they are
still after, and the things they own.

The seam between the two files is the seam in the person: a service record is
a career and this is a life. Both are **derived and stored nowhere**, from the
officer's own id and the sector's seed, so nothing is added to a saved
dataclass and somebody signed on two years ago has a family today.

**Ties are the part that changes how a crew reads.** A name on a list is a
station; a name with a parent on a belt, a creditor at a Charter port and
somebody who is looking for them is a person you would think twice about
leaving behind. They are dealt out of the career that made them — a picket
leaves rivals and old shipmates, a drifter leaves creditors and hunters —
so the relationships are a consequence of the history rather than a second
random draw beside it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.rng import RNG
from ..data import backgrounds as bg
from ..data import careers as career_table
from ..data import kit as kit_table
from ..data import lore
from . import lifepath

#: How many berths somebody held before this one, by terms served. A drifter
#: with six terms has been everywhere; a three-term Charter officer has had
#: two ships and both were grey.
BERTHS_PER_TERM = 0.6

#: What mustering out is worth in things, and what a career's benefits buy.
#: Traveller hands out cash and kit; this hands out kit, because the cash is
#: long spent by the time somebody signs on with you.
KIT_LEAST, KIT_MOST = 1, 4

#: Which categories a career's people end up owning. The tell of a life: a
#: prospector has survey gear and a survival pack, an Orders ward has papers
#: and a keepsake, a drifter has a blade and something they will not explain.
CAREER_KIT = {
    "charter": ("paper", "luxury", "comp", "armour"),
    "yards": ("tool", "suit", "comp", "keepsake"),
    "hauler": ("paper", "comp", "luxury", "travel"),
    "orders": ("medical", "paper", "keepsake", "survey"),
    "prospector": ("survey", "suit", "tool", "travel"),
    "picket": ("weapon", "armour", "suit", "keepsake"),
    "reach": ("weapon", "medical", "keepsake", "survey"),
    "drifter": ("weapon", "keepsake", "illicit", "tool"),
}


@dataclass
class Tie:
    """One person attached to this one, and which way they lean."""

    kind: str
    name: str
    who: str
    helps: bool
    line: str
    #: Where they are, in the words a crew list uses.
    where: str = ""


@dataclass
class Berth:
    """A ship they were on before yours."""

    ship: str
    kind: str
    years: int
    ended: str


@dataclass
class Person:
    """Everything the game knows about somebody aboard."""

    name: str = ""
    station: str = ""
    record: object = None            # `lifepath.Record` — the service
    homeworld: str = ""
    upbringing: str = ""
    ambition: str = ""
    ties: list = field(default_factory=list)
    berths: list = field(default_factory=list)
    kit: list = field(default_factory=list)

    @property
    def home(self):
        return bg.HOMEWORLD_BY_ID.get(self.homeworld)

    @property
    def raised(self):
        return bg.UPBRINGING_BY_ID.get(self.upbringing)

    @property
    def wants(self):
        return bg.AMBITION_BY_ID.get(self.ambition)

    def owns(self, item_id: str) -> bool:
        return item_id in self.kit

    def friends(self) -> list:
        return [t for t in self.ties if t.helps]

    def trouble(self) -> list:
        return [t for t in self.ties if not t.helps]


def _name(rng) -> str:
    """Somebody the game has not otherwise met, from the same pools."""
    return f"{rng.pick(lore.CREW_FIRST)} {rng.pick(lore.CREW_LAST)}"


def _where(rng) -> str:
    """Where a tie is, said the way a crew list would say it."""
    return rng.pick((
        "at a Charter port", "somewhere in the Freeholds", "on a yard world",
        "with the Orders", "out past the Reaches", "aboard a hauler",
        "nobody knows where", "back home", "in a Concordat yard",
        "on a rock in the belt", "at the Cradle", "in a cell, still"))


def _berths(rng, terms: int) -> list:
    """The ships before yours, oldest first."""
    made, wanted = [], max(0, int(terms * BERTHS_PER_TERM + 0.5))
    seen = set()
    for _n in range(wanted):
        name = f"{rng.pick(bg.BERTH_FIRST)} {rng.pick(bg.BERTH_SECOND)}"
        if name in seen:
            continue
        seen.add(name)
        made.append(Berth(ship=name, kind=rng.pick(bg.BERTH_KINDS),
                          years=rng.int(1, 6),
                          ended=rng.pick(bg.BERTH_ENDINGS)))
    return made


def _ties(rng, record) -> list:
    """Who is attached to them, out of the career that made them.

    Family first, because everybody has some and the game should say so,
    then whatever the service leaves behind. A career that went wrong leaves
    more of the second kind, which is the whole point of a mishap.
    """
    made = []
    wanted = rng.int(bg.TIES_LEAST, bg.TIES_MOST)
    # Family: one or two, and not everybody's is alive or speaking.
    for kind in rng.sample(("parent", "sibling", "child", "partner",
                            "cousin", "estranged"), rng.int(1, 2)):
        made.append(_tie(rng, kind))
    pool = list(bg.CAREER_TIES.get(record.career, ("contact", "oldcrew")))
    # Anybody thrown out of a service left somebody behind who remembers it.
    if any(t.mishap for t in record.terms):
        pool += ["enemy", "creditor", "estranged"]
    while len(made) < wanted and pool:
        made.append(_tie(rng, rng.pick(pool)))
    return made


def _tie(rng, kind: str) -> Tie:
    got = bg.TIE_BY_ID.get(kind) or bg.TIE_BY_ID["contact"]
    who = _name(rng)
    return Tie(kind=got.id, name=got.name, who=who, helps=got.helps,
               line=got.line.format(who=who), where=_where(rng))


def _kit(rng, record, home) -> list:
    """What they own, from the service and where they grew up.

    Nothing expensive: a person signing on to somebody else's hull has what
    a life leaves you with, which is a tool, a coat, a weapon and something
    that is worth nothing to anybody else.
    """
    owned, cats = [], list(CAREER_KIT.get(record.career, ("tool", "keepsake")))
    wanted = min(KIT_MOST, max(KIT_LEAST, len(record.terms)))
    for _n in range(wanted):
        rows = [i for i in kit_table.BY_CATEGORY.get(rng.pick(cats), ())
                if i.cr <= 8_000]
        if rows:
            got = rng.pick(rows)
            if got.id not in owned:
                owned.append(got.id)
    # Everybody keeps one thing from home.
    keepsakes = kit_table.BY_CATEGORY.get("keepsake", ())
    if keepsakes and rng.chance(0.75):
        got = rng.pick(keepsakes)
        if got.id not in owned:
            owned.append(got.id)
    if home is not None and home.id == "ship" and "mag_boots" not in owned:
        owned.append("mag_boots")
    return owned


def of(game, officer) -> Person:
    """The whole of somebody. Cheap, stable, and stored nowhere."""
    seed = getattr(game, "seed", "verge") if game is not None else "verge"
    rng = RNG(f"{seed}:person:{getattr(officer, 'id', 0)}")
    record = lifepath.of(game, officer)
    home = rng.pick(bg.HOMEWORLDS)
    raised = rng.pick(bg.UPBRINGINGS)
    want = rng.pick(bg.AMBITIONS)
    person = Person(name=getattr(officer, "name", ""),
                    station=getattr(officer, "role", ""), record=record,
                    homeworld=home.id, upbringing=raised.id, ambition=want.id)
    # Where you are from and who raised you are worth a level each, which is
    # Traveller's own background skills and the reason two officers of the
    # same career are not the same officer.
    for name in (rng.pick(home.skills) if home.skills else "",
                 rng.pick(raised.skills) if raised.skills else ""):
        if name and name in career_table.SKILLS:
            record.skills.setdefault(name, 0)
    # And a point of whatever that life favours. A belt-born hand has the
    # hands for it and somebody out of a licensed family has the name; this
    # is where the two stop being decoration.
    for lean in (home.lean, raised.lean):
        if lean and lean in record.characteristics:
            record.characteristics[lean] = min(
                15, record.characteristics[lean] + 1)
    person.berths = _berths(rng, len(record.terms))
    person.ties = _ties(rng, record)
    person.kit = _kit(rng, record, home)
    return person


# ── what the screens ask ───────────────────────────────────────────────────

def says(person: Person) -> list:
    """The whole sheet, in the order somebody would read it aloud."""
    said = []
    home, raised, want = person.home, person.raised, person.wants
    if home is not None:
        said.append(f"From: {home.name.lower()} — {home.note}")
    if raised is not None:
        said.append(f"Raised: {raised.name.lower()} — {raised.note}")
    if want is not None:
        said.append(f"Wants: {want.name.lower()} — {want.note}")
        if want.served_by:
            said.append(f"  Served by: {want.served_by}.")
    if person.berths:
        said.append("Berths before this one:")
        for berth in person.berths:
            said.append(f"  {berth.ship}, {berth.kind}, {berth.years} year(s)"
                        f" — {berth.ended}")
    if person.ties:
        said.append("People:")
        for tie in person.ties:
            mark = "·" if tie.helps else "!"
            said.append(f"  {mark} {tie.name}: {tie.line}, {tie.where}")
    if person.kit:
        said.append("Owns: " + ", ".join(
            kit_table.ITEM_BY_ID[i].name for i in person.kit
            if i in kit_table.ITEM_BY_ID) + ".")
    return said


def kit_of(person: Person) -> list:
    """Their possessions as items, heaviest first."""
    rows = [kit_table.ITEM_BY_ID[i] for i in person.kit
            if i in kit_table.ITEM_BY_ID]
    return sorted(rows, key=lambda i: -i.mass)


def carried(person: Person) -> float:
    """What they have about them, in kilograms.

    Anything over `kit.CARRIED` lives aboard rather than on a shoulder — a
    person does not walk down a gangway with an air/raft.
    """
    return sum(i.mass for i in kit_of(person) if i.mass <= kit_table.CARRIED)


def contraband(person: Person, law: int) -> list:
    """What a customs desk at this law level would take off them.

    The whole reason the world profile has a law level: a crew that walks
    ashore at law 8 carrying what was ordinary at law 2 is a problem the
    captain is about to have.
    """
    return [i for i in kit_of(person) if not kit_table.legal_at(i, law)]


def aboard(game) -> list:
    """Everybody standing a watch, as people rather than as records."""
    rows = []
    for officer in getattr(game, "officers", []) or []:
        if getattr(officer, "retired", False):
            continue
        rows.append(of(game, officer))
    return rows


def risk_ashore(game, law: int) -> dict:
    """What the whole bridge is carrying that this world forbids."""
    found, people = [], 0
    for person in aboard(game):
        got = contraband(person, law)
        if got:
            people += 1
            found.extend((person.name, item) for item in got)
    return {"people": people, "items": found,
            "worst": max((i.law for _who, i in found), default=0)}
