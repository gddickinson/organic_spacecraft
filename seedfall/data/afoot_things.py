"""The things on a deck: what they block, what they hide, what can be done to them.

A deck plan is walls and floor, and everything else on it is a **thing**: a
door, a locker, a counter somebody stands behind, a console, a lift, an
airlock, a crate of somebody's cargo, a relic, a node of the Bloom. A thing
is a kind (this table) plus a little state on the walk (`sim/afoot_state`):
open, locked, searched, hacked, burned.

Four properties decide how a thing sits on the map, and they are the only
four the geometry ever asks:

- **blocks** — nobody can stand on it;
- **opaque** — nobody can see through it;
- **cover** — 1 for half cover, 2 for full, to somebody standing next to it
  with it between them and the gun;
- **verbs** — what a person standing next to it can do.

The verbs are a closed vocabulary. Each one is a function in
`sim/afoot_acts.py`, and `tests/test_afoot` holds that every verb named here
has one.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThingKind:
    """One sort of thing that can stand on a deck."""

    id: str
    name: str
    blocks: bool = False
    opaque: bool = False
    cover: int = 0
    verbs: tuple = ()
    #: The colour it is drawn in (`ui/theme.TINTS`).
    tint: str = "dim"
    note: str = ""


#: Every verb a thing can offer, and the words for it. `sim/afoot_acts`
#: holds one function per id; nothing may name a verb that is not here.
VERBS = {
    "open": "Open it",
    "close": "Close it",
    "unlock": "Work the lock",
    "force": "Force it",
    "breach": "Blow it",
    "search": "Search it",
    "hack": "Get into it",
    "read": "Read what is on it",
    "take": "Take it",
    "repair": "Fix it",
    "burn": "Burn it out",
    "study": "Study it",
    "rest": "Rest here",
    "lift": "Ride it",
    "leave": "Leave this way",
    "serve": "Ask for service",
}

THINGS: tuple = (
    # ── ways through ──────────────────────────────────────────────────────
    ThingKind("door", "Door", blocks=False, opaque=True,
              verbs=("open", "close", "unlock", "force", "breach"),
              tint="steel", note="Shut, it hides what is behind it."),
    ThingKind("hatch", "Sphincter", blocks=False, opaque=True,
              verbs=("open", "close", "unlock", "force", "breach"),
              tint="chloro", note="Grown doors: a ring of muscle that opens "
                                  "when it is asked the right way."),
    ThingKind("lift", "Lift", verbs=("lift",), tint="lumen",
              note="Up or down a deck."),
    ThingKind("airlock", "Airlock", verbs=("leave",), tint="lumen",
              note="The way you came in, and the way out."),
    ThingKind("gangway", "Gangway", verbs=("leave",), tint="lumen",
              note="The berth, and your own hull beyond it."),
    # ── furniture: cover and something to stand behind ────────────────────
    ThingKind("counter", "Counter", blocks=True, cover=1, verbs=("serve",),
              tint="osteo", note="Somebody stands behind it and sells."),
    ThingKind("table", "Table", blocks=True, cover=1, tint="dim"),
    ThingKind("desk", "Desk", blocks=True, cover=1, verbs=("search",),
              tint="dim"),
    ThingKind("rack", "Rack", blocks=True, cover=1, tint="steel"),
    ThingKind("bench", "Bench", blocks=True, cover=1, verbs=("search",),
              tint="lumen", note="Instruments, samples, and notes."),
    ThingKind("plant", "Planting", blocks=True, cover=1, tint="chloro"),
    ThingKind("pillar", "Pillar", blocks=True, opaque=True, cover=2,
              tint="dim"),
    ThingKind("machinery", "Machinery", blocks=True, opaque=True, cover=2,
              tint="osteo",
              note="Loud, hot, and something to get behind."),
    ThingKind("bed", "Bed", blocks=True, cover=1, verbs=("rest",),
              tint="dim", note="Somewhere to lie down for a watch."),
    ThingKind("medbed", "Medical bed", blocks=True, cover=1,
              verbs=("rest",), tint="lumen",
              note="Rest here with a medic by, and wounds close faster."),
    # ── things with something in them ─────────────────────────────────────
    ThingKind("locker", "Locker", blocks=True, cover=1,
              verbs=("search", "unlock", "force"), tint="steel"),
    ThingKind("crate", "Crate", blocks=True, cover=1,
              verbs=("search", "force"), tint="osteo"),
    ThingKind("strongbox", "Strongbox", blocks=True, cover=1,
              verbs=("unlock", "force", "search"), tint="osteo",
              note="Somebody's private store, and a proper lock on it."),
    ThingKind("cargo", "Cargo", blocks=True, cover=2, opaque=True,
              verbs=("take",), tint="osteo",
              note="Tonnes of it, stacked, and a manifest on the side."),
    ThingKind("console", "Console", blocks=True, cover=1,
              verbs=("hack", "read"), tint="lumen",
              note="What the place knows about itself."),
    ThingKind("relic", "Relic", blocks=True, cover=1, verbs=("study",),
              tint="xeno", note="Old work. Nobody alive made it."),
    ThingKind("body", "Body", verbs=("search",), tint="warn",
              note="Somebody who did not leave."),
    ThingKind("tank", "Tank", blocks=True, opaque=True, cover=2,
              tint="lumen", note="Water, reaction mass, or something worse."),
    ThingKind("couch", "Couch", blocks=True, cover=1, verbs=("rest",),
              tint="xeno"),
    ThingKind("pool", "Pool", blocks=True, cover=0, tint="lumen",
              note="Warm water, which is the luxury in a sealed hull."),
    ThingKind("cradle", "Cradle", blocks=True, opaque=True, cover=2,
              tint="osteo", note="Where a hull is laid down, or opened up."),
    ThingKind("pod", "Lifeboat", verbs=("leave",), tint="lumen",
              note="A way off in a hurry."),
    ThingKind("rubble", "Wreckage", blocks=True, opaque=True, cover=2,
              tint="dim", note="What used to be the deckhead."),
    # ── hazards ───────────────────────────────────────────────────────────
    ThingKind("spore_node", "Spore node", blocks=True, cover=1,
              verbs=("burn", "study"), tint="warn",
              note="Where the Bloom here is rooted. Burn it and it stops."),
    ThingKind("spores", "Spores", tint="warn",
              note="Bad air. Anybody without a filter chokes on it."),
    ThingKind("breach", "Hull breach", tint="warn",
              note="Vacuum. Anybody not sealed in a suit is hurt by it."),
    ThingKind("fault", "Fault", verbs=("repair",), tint="warn",
              note="Something aboard that is failing, and should not be."),
)
THING_BY_ID = {t.id: t for t in THINGS}

#: The kinds that are doors, which several rules ask about.
DOORS = ("door", "hatch")

#: The kinds that are ways off the map. A lifeboat is one, in a hurry.
EXITS = ("airlock", "gangway", "pod")

#: The kinds that hurt whoever stands in them, what keeps it out, and how
#: much a round it costs somebody who is not protected.
HAZARDS = {"spores": ("filters", 2), "breach": ("sealed", 3)}

#: What a lock is worth, as a check difficulty: an ordinary door, a secured
#: one, a strongbox and a vault. `sim/afoot_acts` reads it for the odds.
LOCKS = {1: "routine", 2: "average", 3: "difficult", 4: "very_difficult"}
