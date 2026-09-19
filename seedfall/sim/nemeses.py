"""Named rivals: who rises, where they go, when they come back, and what you
know about where they are.

The play-test found no combat career. Encounters came about 1.3 times a year
and could not be sought, a fighter bot finished **no bounty in fifteen
career-years**, and an enemy was forgotten the moment the fight ended — every
meeting was with a stranger. The machinery for something better was all
here: minds that remember (`sim/memory`), warrants with a price on them
(`sim/warrants`), prize and aftermath, traffic with positions. A nemesis is
what those add up to once somebody holds on to the enemy.

This module holds the rival and the state; `sim/rivals.py` builds the fight
and spends its outcome through `aftermath.resolve`, the one door; and
`sim/hunts.py` is the other direction — the board, the search, the trophy.

**Luck here is keyed, never the day's stream.** Every roll is
`RNG(seed:what:id:day)`: the day's `r` is shared by every phase in
`clock._one_step`, and a draw from it would move the luck of everything
after this phase whether or not a rival existed. With none on the roster
this module draws nothing at all, so a chronicle without one is the
chronicle it always was.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core import ids
from ..core.rng import RNG
from ..core.save import register
from ..data.nemeses import ARCHETYPES_BY_ID, NAMES, TAUNTS
from ..world.galaxy import distance

#: At most this many are out there — active or refitting — at once.
MAX_ACTIVE = 4
LEVEL_MAX = 5

#: Days between two rivals rising, so each one arrives as somebody rather
#: than as weather. With the triggers below this makes one to three in a
#: career's first two years, which is what the design asked for.
RISE_GAP = 150

#: How long a beaten rival spends at the yard, in days.
RETURN_DAYS = (30, 90)

#: Chance a rival moves on, per day, before `pursuit` quickens it.
MOVE_ODDS = 0.15
#: How far one hop of a rival's roaming reaches, in light years — about a
#: drive's rated jump, which is three neighbours in a forty-two-star sector.
REACH_LY = 10.0

#: Chance a rival hears where you are on a day you run lit. A warrant
#: hunter always does: somebody's paper is telling them.
HEAR_ODDS = 0.2

#: Days for a sighting's confidence to halve. A ghost's goes twice as fast.
HALF_LIFE = 20.0

#: A port within this many light years of a rival hears of it, at this
#: daily chance, and so do you if you are standing on the quay.
RUMOUR_LY = 20.0
RUMOUR_ODDS = 0.05
RUMOUR_CONF = 0.6

#: What a hunted rival's hull mends per day, as a share of its whole.
MEND = 0.03

#: Days between two taunts from the same rival — a threat a day is spam.
TAUNT_GAP = 30

#: Rises, per trigger. A hunt warrant always grows a face; the others are
#: odds on the event, which is what keeps them personal rather than routine.
RISE_ODDS = {"corsair": 0.35, "ace": 0.6, "husk": 0.5, "duellist": 1.0,
             "hunter": 1.0}

#: What the cartel will stand of a captain selling under it at Freehold
#: counters before it sends somebody, in credits of goods brought and sold.
UNDERCUT_AT = 60_000.0

#: A price on a rival's hull, per point of the threat it was built to.
BOUNTY_PER_THREAT = 2400.0


@register
@dataclass
class Nemesis:
    """One rival, with a name, a hull that persists, and a memory of you."""
    id: int
    name: str
    archetype: str
    level: int = 1
    traits: list = field(default_factory=list)
    #: A registered `Ship`: the same uid and the same holes from one meeting
    #: to the next, mended while they are away.
    ship: object | None = None
    #: The colours they sail under, for the fight and for the law.
    faction: str | None = None
    #: `encounters.draw_threat` on the day they rose; each level adds to it.
    threat: float = 1.0
    #: Both directions, 0 to 100: `theirs` is what they hold against you,
    #: `yours` what you hold against them.
    grudge: dict = field(default_factory=dict)
    #: active | wounded | dead | allied | retired
    status: str = "active"
    back_on: int = -1
    #: What *you* know: [system id, day, confidence then]. `confidence`
    #: decays it; nothing else may read the list raw.
    last_seen: list = field(default_factory=list)
    location_id: int = 0
    #: What *they* know of you: [system id, day]. Only a lit hull is heard.
    trail: list = field(default_factory=list)
    #: [day, system id, result id, words] — every meeting.
    history: list = field(default_factory=list)
    #: {"reward": credits, "issuer": power} or None.
    bounty: dict | None = None
    pronoun: str = "she"
    retreats: int = 0
    #: Decided when they are spared: grateful, or biding their time.
    loyal: bool = True
    taunted: int = -9999


@register
@dataclass
class HuntState:
    """Everything the rivalry keeps: the roster, the switch, the paper held."""
    nemeses: list = field(default_factory=list)
    #: The transponder, off. `sim/running_dark.py` is the only writer.
    dark: bool = False
    #: Bounties accepted off a board — dicts, see `sim/hunts.take`.
    taken: list = field(default_factory=list)
    #: Every trophy mount won: {id, owner, base, state} where state is
    #: held | mounted | sold. Kept after it is fitted, because a fitting is
    #: looked up by id and this is what registers it (see below).
    trophies: list = field(default_factory=list)
    #: Counters the triggers keep: warrants already answered, the cartel's
    #: ledger, the last rise, raiders already collected.
    marks: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # **A trophy is a fitting, and fittings are looked up by id.** A
        # chronicle resumed in a fresh process has never registered this
        # one, so the hull it is bolted to would lose it on the first
        # `stats`. Decoding the state is the first thing a load does, which
        # makes this the one moment that is always early enough.
        from . import rival_ends
        for record in self.trophies:
            rival_ends.register_trophy(record)


def state(game) -> HuntState:
    held = getattr(game, "hunt", None)
    if held is None:
        held = HuntState()
        game.hunt = held
    return held


def roster(game) -> list:
    """Every rival there has been, living or not, oldest first."""
    held = getattr(game, "hunt", None)
    return list(held.nemeses) if held is not None else []


def active(game) -> list:
    return [n for n in roster(game) if n.status == "active"]


def live(game) -> list:
    """Out there or coming back — what the cap counts."""
    return [n for n in roster(game) if n.status in ("active", "wounded")]


def by_id(game, nid):
    return next((n for n in roster(game) if n.id == nid), None)


def by_ship(game, ship):
    """The rival this hull belongs to, if any. The same object, or the same
    uid — a reload makes a copy, and a uid is what survives it."""
    uid = getattr(ship, "uid", None)
    for nem in roster(game):
        if nem.ship is not None and (nem.ship is ship or nem.ship.uid == uid):
            return nem
    return None


def archetype(nem):
    return ARCHETYPES_BY_ID[nem.archetype]


# ── what you know ──────────────────────────────────────────────────────────

def half_life(nem) -> float:
    return HALF_LIFE / (2.0 if "ghost" in nem.traits else 1.0)


def confidence(game, nem) -> float:
    """How far to trust the last sighting today, 0 to 1."""
    if not nem.last_seen:
        return 0.0
    _where, day, conf = nem.last_seen
    age = max(0.0, float(game.day) - float(day))
    return float(conf) * 0.5 ** (age / half_life(nem))


def sighting(game, nem) -> dict:
    """The last sighting as a screen wants it: where, how old, how sure."""
    if not nem.last_seen:
        return {"system_id": None, "where": "nobody knows", "age": None,
                "conf": 0.0}
    where, day, _conf = nem.last_seen
    return {"system_id": int(where),
            "where": game.galaxy.systems[int(where)].name,
            "age": int(game.day - day), "conf": confidence(game, nem)}


def spot(game, nem, system_id: int, conf: float) -> None:
    """A fresh sighting. The only writer of `last_seen`."""
    nem.last_seen = [int(system_id), int(game.day), float(conf)]


# ── rising ─────────────────────────────────────────────────────────────────

def can_rise(game, kind: str) -> bool:
    """Room on the roster, and long enough since the last one."""
    if len(live(game)) >= MAX_ACTIVE:
        return False
    if kind == "hunter":
        return True           # posted paper is a decision, not a coincidence
    last = state(game).marks.get("last_rise")
    return last is None or game.day - int(last) >= RISE_GAP


def rise(game, kind: str, *, faction: str | None = None, near=None,
         cause: str = "", odds: float | None = None) -> Nemesis | None:
    """A name you will hear again. Returns the rival, or None if not today."""
    from . import rivals
    rng = RNG(f"{game.seed}:rise:{kind}:{game.day}:{len(roster(game))}")
    chance = RISE_ODDS.get(kind, 0.0) if odds is None else odds
    if not can_rise(game, kind) or not rng.chance(chance):
        return None
    arch = ARCHETYPES_BY_ID[kind]
    held = state(game)
    home = near if near is not None else game.system
    taken = {n.name for n in held.nemeses}
    if kind == "husk":
        from ..data.lore import HULL_NAMES
        name = rng.pick([n for n in HULL_NAMES["charter"] if n not in taken]
                        or HULL_NAMES["charter"])
        pronoun = "it"
    else:
        name, pronoun = rng.pick([p for p in NAMES if p[0] not in taken]
                                 or list(NAMES))
    from . import encounters
    nem = Nemesis(id=ids.next_id("nemesis", game), name=name, archetype=kind,
                  faction=(faction if arch.sails == "" else arch.sails),
                  threat=encounters.draw_threat(game, rng),
                  location_id=home.id, pronoun=pronoun,
                  grudge={"theirs": 40.0 + rng.float(0, 20), "yours": 10.0})
    nem.traits = [rng.pick(list(arch.traits))]
    if rng.chance(0.5):
        nem.traits.append(rng.pick([t for t in arch.traits
                                    if t not in nem.traits]))
    rivals.refit(game, nem, rng)
    if arch.wanted:
        nem.bounty = {"reward": _reward(nem),
                      "issuer": _issuer(game, home, kind)}
    spot(game, nem, home.id, 1.0)
    nem.trail = [game.location_id, int(game.day)]
    held.nemeses.append(nem)
    held.marks["last_rise"] = int(game.day)
    remember(game, nem, "slight", cause or arch.origin, 1.2)
    taunt(game, nem, "rise")
    game.add_log(f"A name is going round the quays: {nem.name}, "
                 f"{arch.name.lower()}. {cause or arch.origin}", "warn")
    return nem


def _reward(nem) -> int:
    from . import rivals
    return int(round(BOUNTY_PER_THREAT * rivals.difficulty(nem), -2))


def _issuer(game, home, kind: str) -> str:
    """Who pays for this one: the Charter for its own lost hull, otherwise
    the power whose quay sits nearest where the raiding is."""
    if kind == "husk":
        return "charter"
    ports = [s for s in game.galaxy.systems if s.port is not None
             and s.port.faction in ("charter", "concordat", "sanhedrin")]
    if not ports:
        return "concordat"
    return min(ports, key=lambda s: distance(s, home)).port.faction


def undercut(game, system, worth: float) -> None:
    """A sale at a Freehold counter: the cartel keeps the ledger. Called by
    `trade.sell`; the duellist rises from the daily tick once it is full."""
    port = getattr(system, "port", None)
    if port is None or port.faction != "freeholds" or worth <= 0:
        return
    marks = state(game).marks
    marks["undercut"] = float(marks.get("undercut", 0.0)) + float(worth)


def _rises(game) -> list:
    """The triggers the calendar sees: posted paper, and the cartel's patience."""
    out = []
    from . import warrants as warrants_sim
    held = getattr(game, "hunt", None)
    answered = set(held.marks.get("warrants", [])) if held else set()
    for warrant in warrants_sim.in_force(game):
        if warrant.bite != "hunt" or warrant.id in answered:
            continue
        marks = state(game).marks
        marks["warrants"] = sorted(answered | {warrant.id})
        answered.add(warrant.id)
        from ..data.factions import FACTIONS_BY_ID
        who = getattr(FACTIONS_BY_ID.get(warrant.power), "short", warrant.power)
        if rise(game, "hunter", faction=warrant.power,
                cause=f"{who} paper on your hull found a taker."):
            out.append(("bad", f"Somebody has taken the {who} paper on you."))
    if held is not None and held.marks.get("undercut", 0.0) >= UNDERCUT_AT:
        if rise(game, "duellist", cause="The cartel has noticed who is "
                                        "selling under it."):
            held.marks["undercut"] = 0.0
    return out


# ── the calendar ───────────────────────────────────────────────────────────

def tick(game, n: int, r=None) -> list:
    """A day for every rival: rises, roaming, mending, rumours, returns.

    Logs its own lines and hands them back. `r` is the day's stream and is
    deliberately not drawn from — see the module note.
    """
    from . import rival_ends
    lines = _rises(game)
    held = getattr(game, "hunt", None)
    days = max(0, int(n))
    if held is not None and days:
        rival_ends.ashore(game)
        for nem in list(held.nemeses):
            rng = RNG(f"{game.seed}:nemesis:{nem.id}:{game.day}")
            if nem.status == "wounded" and game.day >= nem.back_on:
                lines.extend(rival_ends.come_back(game, nem, rng))
            elif nem.status == "active":
                _hear(game, nem, rng, days)
                _move(game, nem, rng, days)
                _mend(nem, days)
                lines.extend(_rumour(game, nem, rng, days))
    for kind, text in lines:
        game.add_log(text, kind)
    return lines


def neighbours(game, system_id: int) -> list:
    here = game.galaxy.systems[system_id]
    return [s for s in game.galaxy.systems
            if s is not here and distance(s, here) <= REACH_LY]


def _daily(p: float, days: int) -> float:
    return 1.0 - (1.0 - min(1.0, p)) ** days


def _hear(game, nem, rng, days: int) -> None:
    """A lit hull is heard. A dark one is not — that is the switch's point."""
    from . import running_dark
    if running_dark.dark(game):
        return
    odds = 1.0 if nem.archetype == "hunter" else HEAR_ODDS
    if not rng.chance(_daily(odds, days)):
        return
    moved = not nem.trail or nem.trail[0] != game.location_id
    nem.trail = [game.location_id, int(game.day)]
    if moved and game.day - nem.taunted >= TAUNT_GAP and rng.chance(0.3):
        taunt(game, nem, "before")


def _move(game, nem, rng, days: int) -> None:
    if state(game).marks.get("pinned") == nem.id:
        return                        # lying still while somebody searches
    arch = archetype(nem)
    if not rng.chance(_daily(MOVE_ODDS * (1.0 + arch.pursuit), days)):
        return
    near = neighbours(game, nem.location_id)
    if not near:
        return
    if nem.trail and rng.chance(arch.pursuit):
        goal = game.galaxy.systems[int(nem.trail[0])]
        here = game.galaxy.systems[nem.location_id]
        best = min(near, key=lambda s: distance(s, goal))
        if distance(best, goal) < distance(here, goal):
            nem.location_id = best.id
            return
    if nem.archetype == "husk":
        grown = [s for s in near if s.bloom > 0.02]
        near = grown or near
    nem.location_id = rng.pick(near).id


def _mend(nem, days: int) -> None:
    ship = nem.ship
    if ship is None:
        return
    for layer in ship.layers:
        layer.hp = min(layer.max, layer.hp + layer.max * MEND * days)
    if all(layer.hp >= layer.max for layer in ship.layers):
        ship.disabled.clear()


def _rumour(game, nem, rng, days: int) -> list:
    """Standing on a quay, you hear what the quay hears."""
    here = game.system
    if here.port is None:
        return []
    there = game.galaxy.systems[nem.location_id]
    if distance(here, there) > RUMOUR_LY:
        return []
    odds = RUMOUR_ODDS / (2.0 if "ghost" in nem.traits else 1.0)
    if not rng.chance(_daily(odds, days)):
        return []
    spot(game, nem, there.id, RUMOUR_CONF)
    return [("", f"Word on the quay at {here.port.name}: {nem.name} was seen "
                 f"at {there.name}.")]


# ── what they remember, and what they say ─────────────────────────────────

def remember(game, nem, kind: str, text: str, salience: float = 1.0) -> None:
    """Into the rival's own mind (`sim/memory`), where a voice can find it."""
    from . import memory as memory_sim
    memory_sim.note(game, f"nemesis:{nem.id}", kind, text, salience,
                    tags=["nemesis", nem.archetype], name=nem.name,
                    entity="captain")


def taunt(game, nem, occasion: str) -> None:
    """A despatch from them, through `sim/comms`: it arrives as late as the
    distance says, which is part of the threat."""
    from . import comms
    frames = TAUNTS.get(occasion)
    if not frames:
        return
    rng = RNG(f"{game.seed}:taunt:{nem.id}:{occasion}:{game.day}")
    place = game.galaxy.systems[nem.location_id].name
    body = rng.pick(list(frames)).format(name=nem.name, you=game.ship.name,
                                         place=place)
    comms.send(game, f"nemesis:{nem.id}", nem.name, "personal",
               f"{nem.name}", body, system_id=nem.location_id)
    nem.taunted = int(game.day)
