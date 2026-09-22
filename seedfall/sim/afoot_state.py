"""A walk in progress: the decks, the rooms, the things and the people on them.

**You can be in the middle of one, so it lives on the `Game`** — the rule
every other thing you can be part-way through follows (an expedition, a
trench, an envoy). `game.afoot` is a `Walk`; every field of every class here
is declared and defaulted, so `core/save` writes all of it and a walk saved
between two moves resumes in a fresh process exactly where it stood.

The plan itself is derived (`sim/afoot_gen.py`) from the seed and the site,
and then *copied in*: a deck's terrain is a handful of short strings, and
keeping it means a walk never changes shape under the party because a venue
opened while they were in it.

Terrain is one character a square:

- `#` wall, `=` window (a wall you can see through), ` ` nothing at all;
- `.` a room's floor, `,` a corridor's.

Everything else on a deck is a `Thing` or an `Actor`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register

WALL, WINDOW, VOID, FLOOR, HALL = "#", "=", " ", ".", ","
#: Open ground outside any building: regolith, a field, a street.
GROUND = "_"
#: Squares somebody can stand on, before things and people are counted.
OPEN = (FLOOR, HALL, GROUND)
#: Squares nobody can see through.
BLIND = (WALL, VOID)


@register
@dataclass
class Deck:
    """One level of a plan."""

    name: str
    rows: list = field(default_factory=list)
    #: What the party has seen, one character a square: "1" seen, "0" not.
    seen: list = field(default_factory=list)
    #: grown | fabricated | hybrid | synthetic | xeno | station | habitat |
    #: settlement — how it is laid out and how it is drawn.
    style: str = "fabricated"
    #: False on a deck with nothing to breathe: a Dry Choir hull, a holed
    #: derelict. Anybody not sealed in a suit is hurt every round.
    air: bool = True
    #: False where the open ground outside the buildings (`_`) has nothing to
    #: breathe: an airless moon, a rock. The sheds hold air; the street does
    #: not.
    outside_air: bool = True
    #: The weight on the floor, in gravities. **Nothing in the Verge makes a
    #: floor pull**: a hull or a quay is weightless, a Habitat Girdle's spun
    #: berths four-tenths, a ring or a drum what its spin gives, the ground
    #: its world's own. Below `afoot_map.WEIGHTLESS` people drift.
    g: float = 1.0
    #: A floor that closes on itself — a spun ring's level, a drum's inside,
    #: drawn unrolled: walk off one end and you come on at the other.
    wrap: bool = False

    @property
    def w(self) -> int:
        return len(self.rows[0]) if self.rows else 0

    @property
    def h(self) -> int:
        return len(self.rows)

    def at(self, x: int, y: int) -> str:
        if 0 <= y < len(self.rows) and 0 <= x < len(self.rows[y]):
            return self.rows[y][x]
        return VOID

    def was_seen(self, x: int, y: int) -> bool:
        if 0 <= y < len(self.seen) and 0 <= x < len(self.seen[y]):
            return self.seen[y][x] == "1"
        return False


@register
@dataclass
class Room:
    """A named space on a deck."""

    id: int
    name: str
    kind: str
    deck: int
    x: int
    y: int
    w: int
    h: int
    #: The concourse door this room is (`data/venues.py`), if it is one.
    venue: str = ""
    #: The fitting this room holds (`data/parts.py`), aboard a hull.
    part: str = ""
    #: Named on the map once anybody in the party has seen inside.
    known: bool = False
    #: Which squares of the box (x, y, w, h) are the room, one row a string
    #: of "1" and "0". A room is whatever shape its structure gave it — the
    #: curve of a hull, a sector of a ring — and the box is only its bounds.
    mask: list = field(default_factory=list)

    def holds(self, deck: int, x: int, y: int) -> bool:
        if not (deck == self.deck and self.x <= x < self.x + self.w
                and self.y <= y < self.y + self.h):
            return False
        if not self.mask:
            return True
        return self.mask[y - self.y][x - self.x] == "1"

    def cells(self) -> list:
        """Every square of the room."""
        return [(self.x + i, self.y + j) for j in range(self.h)
                for i in range(self.w) if self.holds(self.deck, self.x + i,
                                                     self.y + j)]


@register
@dataclass
class Thing:
    """Something standing on a deck (`data/afoot_things.py`)."""

    id: int
    kind: str
    deck: int
    x: int
    y: int
    name: str = ""
    #: open | shut | locked | broken | searched | hacked | done | ""
    state: str = ""
    #: A lock's grade, 0 for none (`afoot_things.LOCKS`).
    lock: int = 0
    #: What is in it: kit ids, "cargo:<id>:<tonnes>", "evidence:<kind>:<n>",
    #: "study:<n>", "intel:<text>".
    holds: list = field(default_factory=list)
    room: int = -1
    #: A lift's partner: the id of the lift it arrives at.
    link: int = -1
    note: str = ""


@register
@dataclass
class Actor:
    """Somebody on a deck: one of yours, or anybody else."""

    id: int
    name: str
    #: "party" or "npc".
    side: str
    #: The archetype (`data/afoot_folk.py`), or captain / officer / robot.
    folk: str
    deck: int
    x: int
    y: int
    hp: int
    hp_max: int
    officer: int = -1
    robot: int = -1
    #: friendly | neutral | wary | hostile | surrendered | fled
    mood: str = "neutral"
    #: up | down (bleeding) | stable (down, not bleeding) | dead | gone
    status: str = "up"
    mp: int = 0
    acted: bool = False
    #: "" | sneak | watch — a stance held until changed.
    stance: str = ""
    aim: int = 0
    weapon: str = ""
    armour: str = ""
    #: Kit ids on their person this walk (the consumables are spent here).
    kit: list = field(default_factory=list)
    spent: list = field(default_factory=list)
    #: An NPC's own scores and skills. A party member's are read afresh.
    stats: dict = field(default_factory=dict)
    skills: dict = field(default_factory=dict)
    faction: str = ""
    #: Has this NPC noticed the party, and for how many rounds since has
    #: it seen nobody (`afoot_ai.LOST_AFTER`)?
    aware: bool = False
    lost: int = 0
    #: Where a keeper keeps station: [deck, x, y].
    post: list = field(default_factory=list)
    room: int = -1
    #: Topics already raised with them, so a bribe is not paid twice.
    talked: list = field(default_factory=list)
    #: The id of a downed ally being carried, or -1.
    carrying: int = -1
    #: Stamina a stun weapon took. It wears off, and is never a wound.
    numb: int = 0
    #: Lines said to the party so far: somebody works through what they
    #: have to say before they say any of it twice.
    spoke: int = 0
    #: Zero-G skill, for the party (−3 untrained): who moves and shoots
    #: weightless without drifting. The people who live aboard are at home
    #: in it whatever this says.
    zero_g: int = -3
    #: Rounds left pinned by suppressing fire: they hold their ground and
    #: shoot worse (`afoot_arms.PINNED`).
    pinned: int = 0
    #: An incident that put them here, and whose past they come out of.
    incident: str = ""
    tie: str = ""
    note: str = ""

    @property
    def standing(self) -> bool:
        return self.status == "up"

    @property
    def hostile(self) -> bool:
        return self.side == "npc" and self.mood == "hostile" and self.standing


@register
@dataclass
class Walk:
    """One walk: where, who, and how far it has got."""

    id: int
    #: The site's key (`sim/afoot_sites.py`) and what it is.
    site: str
    kind: str
    name: str
    system_id: int = -1
    place_id: str = ""
    faction: str = ""
    law: int = 0
    tech: int = 9
    decks: list = field(default_factory=list)
    rooms: list = field(default_factory=list)
    things: list = field(default_factory=list)
    actors: list = field(default_factory=list)
    round: int = 1
    #: Six seconds a round, plus whatever resting and working cost.
    seconds: int = 0
    #: calm | action
    mode: str = "calm"
    #: The party member the screen has in hand.
    selected: int = -1
    #: The deck the screen is looking at.
    viewing: int = 0
    log: list = field(default_factory=list)
    #: Goals a site sets, as [id, words, done].
    goals: list = field(default_factory=list)
    #: What has been found and is banked on the way out.
    found: dict = field(default_factory=dict)
    #: Crimes somebody saw, as [what, power, severity, [who saw it]].
    seen_doing: list = field(default_factory=list)
    incidents: list = field(default_factory=list)
    over: bool = False
    outcome: str = ""
    #: How the party got here (`sim/crossing`): dock | boat | shuttle |
    #: suits, or "aboard" for a walk that needed no crossing. It is what
    #: decides how much of what they find can come home — the way back is
    #: the way they came (`sim/crossing.lift_t`).
    way: str = "aboard"
    #: A struck hull being boarded (a `Ship`), whose she was, and what the
    #: captain decided about her once aboard.
    prize: object = None
    prize_faction: str = ""
    prize_done: str = ""
    #: Bumped whenever a thing changes, so a cached sight map knows.
    version: int = 0
    next_uid: int = 1


# ── small reads every other afoot module shares ────────────────────────────

def uid(walk: Walk) -> int:
    """A fresh id for an actor, a thing or a room in this walk."""
    got = walk.next_uid
    walk.next_uid += 1
    return got


def say(walk: Walk, text: str, kind: str = "") -> None:
    """A line in the walk's own log, newest last."""
    walk.log.append((walk.round, text, kind))
    if len(walk.log) > 200:
        del walk.log[0]


def actor(walk: Walk, actor_id: int):
    return next((a for a in walk.actors if a.id == actor_id), None)


def thing(walk: Walk, thing_id: int):
    return next((t for t in walk.things if t.id == thing_id), None)


def party(walk: Walk, standing: bool = False) -> list:
    return [a for a in walk.actors if a.side == "party"
            and a.status != "gone" and (a.standing or not standing)]


def others(walk: Walk) -> list:
    return [a for a in walk.actors if a.side == "npc"
            and a.status not in ("gone", "dead")]


def actor_at(walk: Walk, deck: int, x: int, y: int):
    """Whoever is standing, or lying, on this square."""
    return next((a for a in walk.actors if a.deck == deck and a.x == x
                 and a.y == y and a.status not in ("gone",)
                 and not _carried(walk, a)), None)


def things_at(walk: Walk, deck: int, x: int, y: int) -> list:
    return [t for t in walk.things if t.deck == deck and t.x == x
            and t.y == y]


def room_at(walk: Walk, deck: int, x: int, y: int):
    return next((r for r in walk.rooms if r.holds(deck, x, y)), None)


def _carried(walk: Walk, who) -> bool:
    return any(a.carrying == who.id for a in walk.actors if a.id != who.id)


def touch(walk: Walk) -> None:
    """Something that blocks or hides has changed: forget cached sight."""
    walk.version += 1
