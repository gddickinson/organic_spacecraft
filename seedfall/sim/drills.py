"""Running a gunnery drill: what turns up, what counts, and how it went.

`data/drills.py` says what a drill *is*; this makes one happen. Three jobs and
they are deliberately separate, because the middle one runs sixty times a
second and the other two do not:

- **`begin`** builds the sky: the seat, the hull you are standing on, and the
  first wave already out there.
- **`tick`** is the clock — it advances the action, lets later waves arrive on
  their own schedule, and re-reads the directive list.
- **`judge`** is the debrief: what was asked, what was done, and a rating that
  is about *how* rather than whether.

**The directive list is read, never written.** Every line is a question about
the state of the action — is every corvette gone, has the mast come off, did
anything get through — so it cannot drift out of step with what actually
happened, and a drill that is reloaded mid-action comes back saying the same
thing. It is FreeSpace 2's directive gauge, and the reason that gauge works is
exactly this: it is a view, not a tally.
"""

from __future__ import annotations

import math

from ..core.rng import RNG
from ..data import drills as table
from ..data.drill_types import primary, secondary
from . import foes, skirmish, turret as turret_sim

#: What a `Spawn` names its guns with, resolved here so the content table
#: holds no numbers. A name nobody has written is no gun at all, which is a
#: quieter failure than a crash and is caught by `tests/test_turret`.
GUNS = {"LIGHT": foes.LIGHT, "MEDIUM": foes.MEDIUM, "HEAVY": foes.HEAVY,
        "SIEGE": foes.SIEGE, "LANCE": foes.LANCE, "RACK": foes.RACK,
        "TUBES": foes.TUBES}

#: What each rating wants, as a share of the drill's marks. A pass is the
#: primaries; everything above it is how much of the rest you took.
RATINGS = ((0.95, "Exemplary"), (0.8, "Good"), (0.62, "Pass"),
           (0.4, "Marginal"), (0.0, "Failed"))


def _place(spawn, index: int, count: int) -> tuple:
    """Where one of a group starts, in the hull's frame.

    Spread across a piece of sky rather than stacked on one bearing: a wave
    that arrives as a single point is one target, and the whole difficulty of
    a pack is that they are in different parts of your arc.
    """
    share = 0.0 if count <= 1 else (index / (count - 1)) - 0.5
    bearing = math.radians(spawn.spread * share)
    rise = math.radians(spawn.rise)
    flat = math.cos(rise) * spawn.at_km
    return (math.sin(bearing) * flat, math.cos(bearing) * flat,
            math.sin(rise) * spawn.at_km)


def _hatch(action, spawn, rng) -> list:
    """One group, as contacts on the plot."""
    made = []
    for index in range(max(1, spawn.count)):
        name = spawn.name if spawn.count <= 1 else f"{spawn.name} {index + 1}"
        contact = foes.make(
            f"{spawn.kind}-{len(action.contacts)}-{index}", name, spawn.kind,
            _place(spawn, index, spawn.count),
            behaviour=spawn.behaviour, stand_km=spawn.stand_km,
            pace=spawn.pace, hostile=spawn.hostile,
            guns=tuple(GUNS[g] for g in spawn.guns if g in GUNS))
        if spawn.parts:
            foes.fit(contact, *spawn.parts)
        action.contacts.append(contact)
        made.append(contact)
    return made


def begin(drill, rng=None, ship=None) -> skirmish.Skirmish:
    """Open the drill: a seat, a hull, and whatever is already out there."""
    rng = rng or RNG(f"drill:{drill.id}")
    seat = turret_sim.make(drill.seat, at=(0.0, 0.25, 0.9))
    action = skirmish.open_action(
        seat, [], hull="the training hull", hp=drill.hull,
        max_hp=drill.hull, evade=drill.evade, setting=drill.setting)
    action.log.append(drill.brief)
    _run_waves(action, drill, rng, first=True)
    return action


def _run_waves(action, drill, rng, first: bool = False) -> list:
    """Bring in every wave whose moment has come. Returns what it said."""
    said = []
    for index, wave in enumerate(drill.waves):
        if index in action.waves_in:
            continue
        if wave.at > action.clock and not (first and wave.at <= 0.0):
            continue
        for spawn in wave.spawn:
            _hatch(action, spawn, rng)
        action.waves_in.append(index)
        if wave.say:
            said.append(wave.say)
            action.log.append(wave.say)
    return said


def tick(action, drill, rng, seconds: float = skirmish.STEP) -> dict:
    """One slice of a drill: the action, then the waves, then the directives."""
    got = skirmish.tick(action, rng, seconds)
    if action.over:
        return got
    said = _run_waves(action, drill, rng)
    got.setdefault("said", []).extend(said)
    rows = directives(action, drill)
    # **Not while there is a wave still to come.** The brief is the whole
    # drill, and an exercise that ended the moment the first pair of drones
    # was down never showed the gunner the pair that crosses — measured, the
    # pass drill called itself complete at 4.7 seconds of a 35-second
    # schedule and the second wave was never flown against.
    waiting = len(action.waves_in) < len(drill.waves)
    if drill.seconds and action.clock >= drill.seconds:
        _call_it(action, drill, rows)
    elif any(row["failed"] for row in rows if row["primary"]):
        _call_it(action, drill, rows)
    elif not waiting and all(row["done"] for row in rows if row["primary"]):
        _call_it(action, drill, rows)
    return got


def _call_it(action, drill, rows) -> None:
    """The action is finished with; say which way."""
    won = all(row["done"] for row in rows if row["primary"])
    skirmish.finish(action, "won" if won else "lost",
                    "Exercise complete." if won else "Exercise called.")


# ── the directive list ─────────────────────────────────────────────────────

def _of_kind(action, of: str) -> list:
    """Every contact a directive is about: by kind, or by name, or all."""
    rows = [c for c in action.contacts if c.hostile or of == "consort"]
    if not of:
        return [c for c in rows if c.hostile]
    return [c for c in rows
            if c.kind == of or c.name.startswith(of)] or \
        [c for c in action.contacts if c.kind == of or c.name.startswith(of)]


def _answer(action, drill, aim) -> tuple:
    """`(done, failed, how it stands)` for one directive, read fresh."""
    if aim.kind == "clear":
        rows = _of_kind(action, aim.of)
        left = [c for c in rows if not c.dead]
        return (not left and bool(rows), False,
                f"{len(rows) - len(left)} of {len(rows)}")
    if aim.kind == "silence":
        rows = _of_kind(action, aim.of)
        quiet = [c for c in rows if foes.silenced(c) or c.dead]
        return (bool(rows) and len(quiet) == len(rows), False,
                f"{len(quiet)} of {len(rows)}")
    if aim.kind == "cripple":
        rows = _of_kind(action, aim.of)
        lame = [c for c in rows if foes.crippled(c)]
        return bool(lame), False, f"{len(lame)}"
    if aim.kind == "wreck":
        gone = _wrecked(action, aim.of)
        return bool(gone), False, f"{gone} off"
    if aim.kind == "stop":
        got = _got_through(action, aim.of)
        return not got, bool(got), f"{got} through"
    if aim.kind == "under":
        # A time *limit*, which is the opposite question to `survive` and was
        # written as one by mistake: "inside ninety seconds" read as "have
        # you been here ninety seconds", so finishing early failed it.
        return (action.clock <= aim.seconds, action.clock > aim.seconds,
                f"{action.clock:,.0f} s of {aim.seconds:,.0f}")
    if aim.kind == "survive":
        if aim.share:
            share = action.hp / action.max_hp if action.max_hp else 0.0
            return share >= aim.share, action.hp <= 0.0, f"{share:.0%}"
        want = aim.seconds or drill.seconds
        return (action.clock >= want, action.hp <= 0.0,
                f"{action.clock:,.0f} of {want:,.0f} s")
    if aim.kind == "protect":
        rows = [c for c in action.contacts if not c.hostile]
        alive = [c for c in rows if not c.dead]
        return (bool(rows) and len(alive) == len(rows),
                len(alive) < len(rows), f"{len(alive)} of {len(rows)}")
    if aim.kind == "accuracy":
        fired = action.turret.fired
        share = action.turret.hits / fired if fired else 0.0
        return share >= aim.share and fired >= 6, False, f"{share:.0%}"
    if aim.kind == "spare":
        hurt = _spared(action, aim.of)
        return not hurt, bool(hurt), "untouched" if not hurt else "hit"
    return False, False, ""


def _wrecked(action, kind: str) -> int:
    """How many fittings of a kind have been shot off anything."""
    return sum(1 for c in action.contacts for p in c.parts
               if p.kind == kind and p.dead)


def _spared(action, of: str) -> int:
    """How much of something the gunner was told to leave alone was hit.

    A consort is spared by not being shot; a habitat ring is spared by being
    left on the thing it is bolted to. Both are read off the state rather
    than counted as they happen, so neither can drift.
    """
    if of == "consort":
        return sum(1 for c in action.contacts
                   if not c.hostile and c.hp < c.max_hp)
    return sum(1 for c in action.contacts for p in c.parts
               if p.kind == of and p.hp < p.max_hp)


def _got_through(action, of: str = "") -> int:
    """How many seekers reached the hull. Read off the wrecks they left."""
    return sum(1 for c in action.contacts
               if c.killed_by == "struck home" and (not of or c.kind == of))


def directives(action, drill) -> list:
    """The list on the glass: one row per aim, as it stands right now."""
    rows = []
    for aim in drill.aims:
        done, failed, how = _answer(action, drill, aim)
        rows.append({"id": aim.id, "say": aim.say, "primary": aim.primary,
                     "done": done, "failed": failed, "how": how,
                     "kind": aim.kind})
    return rows


# ── the debrief ────────────────────────────────────────────────────────────

def judge(action, drill) -> dict:
    """What the gunner actually did, and what to call it.

    The rating is the share of *all* the marks, primary and secondary, so a
    gunner who met the brief and nothing else passes and one who took the
    trouble over the rest does not have to be told they did well.
    """
    rows = directives(action, drill)
    got = sum(1 for r in rows if r["done"])
    want = len(rows) or 1
    share = got / want
    won = all(r["done"] for r in rows if r["primary"])
    if not won:
        share = min(share, 0.55)
    rating = next(name for bar, name in RATINGS if share >= bar)
    stand = skirmish.standing(action)
    return {
        "drill": drill.id,
        "name": drill.name,
        "won": won,
        "rating": rating,
        "share": share,
        "met": got,
        "of": want,
        "rows": rows,
        "seconds": action.clock,
        "accuracy": stand["accuracy"],
        "fired": stand["fired"],
        "hits": stand["hits"],
        "killed": len(action.killed),
        "taken": action.taken,
        "hull": stand["hull"],
        "next": table.after(drill.id),
    }


def lines(verdict: dict) -> list:
    """The debrief, as sentences a screen can print."""
    said = [f"{verdict['name']} — {verdict['rating']}.",
            f"{verdict['met']} of {verdict['of']} directives met in "
            f"{verdict['seconds']:,.0f} seconds."]
    if verdict["fired"]:
        said.append(f"{verdict['hits']} of {verdict['fired']} rounds landed "
                    f"({verdict['accuracy']:.0%}).")
    if verdict["killed"]:
        said.append(f"{verdict['killed']} contact(s) destroyed.")
    said.append(f"The hull came home at {verdict['hull']:.0%}, "
                f"{verdict['taken']:,.0f} taken.")
    for row in verdict["rows"]:
        mark = "✓" if row["done"] else ("✗" if row["failed"] else "—")
        said.append(f"  {mark} {row['say']} ({row['how']})")
    return said


def brief(drill) -> list:
    """The words before it starts: what this is and what is wanted."""
    said = [drill.brief, ""]
    for aim in primary(drill):
        said.append(f"  · {aim.say}")
    extra = secondary(drill)
    if extra:
        said.append("")
        said.append("Worth having:")
        for aim in extra:
            said.append(f"  · {aim.say}")
    return said
