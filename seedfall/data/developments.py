"""What people have put on a world, from a city down to a hole in the ground.

The game knew two sorts of place on a planet: a *settlement* — one flat
thing at nine hundred heads, whoever owns it (`data/settlements.py`) — and
six kinds of ground base (`data/establishments.py`). There was no ladder
between a mining camp and a capital, nothing abandoned, and nothing that had
ever been anything else.

These are the rungs, and they are deliberately the words a player would use.
Each carries what a screen needs (a name, a mark, a colour), what the
placement needs (how many it holds, what ground it wants), and what the
walking layer needs (`style`, which `sim/afoot_sites` already reads to pick
a deck plan, so walking into one of these needs no new plumbing).

`falls_to` is the taxonomy's own decay: what a place *becomes* when its
reason goes. A mine whose seam runs out is an abandoned mine, and a town
that loses its mine is a ruin — which is how a world ends up with a history
you can read off the map.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Development:
    """One kind of thing on a world's surface."""

    id: str
    name: str
    #: One letter for the map, because colours collide under deuteranopia —
    #: the same rule `ui/expedition_view` already draws features by.
    mark: str
    tint: str
    blurb: str
    #: Roughly how many live there. Nought for something nobody lives in.
    heads: int
    #: What the walking layer builds it as (`sim/afoot_sites.STYLE`).
    style: str
    #: Terrain it wants to sit on, and terrain it will not.
    likes: tuple = ()
    avoids: tuple = ()
    #: Wants a coast — somewhere a cell of standing water is adjacent.
    coastal: bool = False
    #: What it becomes when its reason goes, or "" if it is already that.
    falls_to: str = ""
    #: True for somewhere nobody is: what a landing party finds rather than
    #: somebody it can talk to.
    empty: bool = False


DEVELOPMENTS: tuple = (
    Development(
        "city", "City", "C", "lumen",
        "Towers, tunnels and a hundred thousand people who have never been "
        "off this world. Whatever else is on this planet answers to it.",
        heads=120_000, style="settlement",
        likes=("plain", "basin"), avoids=("scarp", "crevasse", "vent"),
        coastal=True, falls_to="ruin"),
    Development(
        "town", "Town", "T", "chloro",
        "A few thousand, a landing field, a market that runs on the days "
        "the shuttle comes, and somebody who calls themselves the mayor.",
        heads=4_000, style="settlement",
        likes=("plain", "basin", "forest"), avoids=("scarp", "crevasse"),
        falls_to="ruin"),
    Development(
        "village", "Village", "v", "chloro",
        "Forty families, a well, a mast and a shared tractor. It is here "
        "because somebody's grandmother stopped here.",
        heads=200, style="settlement",
        likes=("plain", "forest", "basin"), avoids=("scarp", "vent"),
        falls_to="ruin"),
    Development(
        "outpost", "Outpost", "o", "steel",
        "Six people, a dish and a fuel bladder, put here to watch "
        "something. Nobody is from an outpost.",
        heads=6, style="station",
        likes=("ridge", "plain", "dunes", "shelf"), avoids=(),
        falls_to="abandoned"),
    Development(
        "mine", "Mining operation", "M", "osteo",
        "A rig, a spoil heap and a shift that never stops. Whatever this "
        "world has that is worth lifting, it is coming out here.",
        heads=400, style="settlement",
        likes=("ridge", "scarp", "crevasse", "dunes"), avoids=("forest",),
        falls_to="abandoned_mine"),
    Development(
        "farm", "Agricultural station", "f", "chloro",
        "Tanks, lamps and hectares under film. It feeds whatever else is "
        "on this world, and it is the first thing a siege starves.",
        heads=150, style="settlement",
        likes=("plain", "basin", "forest"), avoids=("scarp", "crevasse",
                                                    "dunes"),
        coastal=True, falls_to="abandoned"),
    Development(
        "research", "Research station", "r", "xeno",
        "A handful of people a long way from anywhere, looking at one "
        "thing very carefully.",
        heads=30, style="station",
        likes=("crevasse", "vent", "shelf", "ridge"), avoids=(),
        falls_to="abandoned"),
    Development(
        "garrison", "Garrison", "g", "warn",
        "Somebody's soldiers, a landing field and a fence. It is here "
        "because of what is under it or who is near it.",
        heads=250, style="station",
        likes=("ridge", "plain"), avoids=("crevasse",),
        falls_to="abandoned"),
    # ── and what is left when the reason goes ─────────────────────────────
    Development(
        "abandoned", "Abandoned station", "a", "dim",
        "Still standing, still sealed, and nobody has answered the mast in "
        "years. What is inside is whatever was not worth the lift.",
        heads=0, style="station", empty=True),
    Development(
        "abandoned_mine", "Worked-out mine", "x", "dim",
        "The seam ran out. The rig is still bolted to the rock and the "
        "spoil heap is still warm in the middle.",
        heads=0, style="settlement", empty=True),
    Development(
        "ruin", "Ruin", "R", "osteo",
        "Streets with nothing on them. Whatever this was, it was bigger "
        "than whatever is on this world now.",
        heads=0, style="settlement", empty=True),
    Development(
        "wreck", "Downed hull", "w", "warn",
        "Something came down here and did not go up again.",
        heads=0, style="station", empty=True),
)
DEVELOPMENTS_BY_ID = {d.id: d for d in DEVELOPMENTS}

#: The rungs a living place can be, biggest first. `sim/worldsites` walks
#: this to spend a world's population on the places that hold it.
LADDER = ("city", "town", "village", "outpost")

#: The works a world has besides its people: what a population of any size
#: puts on the ground because of what the ground is.
WORKS = ("mine", "farm", "research", "garrison")

#: How far apart two places of these kinds have to be, in cells. A city
#: does not have another city next door; an outpost can be anywhere.
APART = {"city": 6, "town": 4, "village": 2, "outpost": 1,
         "mine": 2, "farm": 2, "research": 2, "garrison": 2}
