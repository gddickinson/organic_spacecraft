"""What a crew may be made of, and who will have it aboard.

The Verge had five substrates and all five of them were *people*. There are
walking machines in `sim/robots.py` that nobody could put on a bridge, a
faction whose whole creed is **"substrate is an implementation detail"**, and
clinics that will grow a person to order — and a crew list could hold none of
it. Eight lineages now (`data/lineages.py`), and this is the layer that
decides where any of them may stand.

**A creed is an attitude, and nobody had ever read one.** The four powers
have said what they think since the first commit — *One biology, many
bodies* (Charter), *Built, not bred* (Concordat), *Whatever flies, flies for
us* (Freeholds), *Substrate is an implementation detail* (the Dry Choir) —
and none of it reached a hiring board or a customs gate. It does now, and it
is most of what makes one port different from another for a mixed crew.

Three things tighten or loosen it, in this order:

- **Whose ground it is.** The faction's own view of that sort of being.
- **What sort of government.** A religious dictatorship and a balkanised
  world are harder on anything unusual than a company port is; a
  participating democracy is easier than either.
- **The law level.** Not a view but a *procedure*: the higher it runs, the
  more of what is merely watched becomes papers, and what needed papers
  becomes a refusal at the gate.

And **the hull matters**, because a berth is a place to live: who turns up on
a board is weighted by what the ship is made of, so a Concordat fabricated
hull draws frames and a grown one draws the wet and the vat-grown. That is
the whole of "depending on the type and origin of the ship", stated as a
table.
"""

from __future__ import annotations

#: What sort of thing a lineage is, as far as anybody minding is concerned.
#: Not the substrate — `data/lineages.py` has that — but the *category* a
#: customs officer, a hiring hall or a xenophobe sorts people into.
CLASSES = (
    ("born", "Born", "grown in a body, the ordinary way"),
    ("vat", "Vat-grown", "grown to a specification somebody paid for"),
    ("graft", "Grafted", "flesh with metal through it"),
    ("recorded", "Recorded", "a person who is a copy of a person"),
    ("machine", "Machine", "a frame with a hull number"),
    ("alien", "Not from here", "nothing the Verge grew"),
)
CLASS_NAME = {cid: name for cid, name, _note in CLASSES}
CLASS_NOTE = {cid: note for cid, _name, note in CLASSES}

CLASS_OF = {
    "wet": "born", "vatborn": "vat", "grafted": "graft",
    "dry": "recorded", "mind": "recorded", "frame": "machine",
    "xeno": "alien", "kith": "alien",
}

#: The four bands, hardest last. A band is a *procedure*, not an opinion:
#: welcome is a nod at the gate, licensed is a form, watched is a form and
#: somebody reading it, refused is the gate shut.
BANDS = ("welcome", "licensed", "watched", "refused")
BAND_NOTE = {
    "welcome": "nobody at the gate looks twice",
    "licensed": "papers, and a fee for them",
    "watched": "papers, a wait, and somebody reading them",
    "refused": "not permitted ashore here at all",
}

#: What each power thinks, read straight off the creed it has always had.
#: Anything a power has no view on is `licensed` — the Verge's default is
#: paperwork rather than welcome or refusal.
FACTION_VIEW = {
    # "One biology, many bodies." Flesh in all its forms, and a deep unease
    # about anything that is not.
    "charter": {"born": "welcome", "vat": "licensed", "graft": "welcome",
                "recorded": "watched", "machine": "watched",
                "alien": "refused"},
    # "Built, not bred." A yard does not care what walks into it, provided
    # it can be certified — and a frame certifies more easily than a person.
    "concordat": {"born": "welcome", "vat": "welcome", "graft": "welcome",
                  "recorded": "licensed", "machine": "welcome",
                  "alien": "watched"},
    # "Whatever flies, flies for us."
    "freeholds": {"born": "welcome", "vat": "welcome", "graft": "welcome",
                  "recorded": "welcome", "machine": "welcome",
                  "alien": "licensed"},
    # "Substrate is an implementation detail." The one power that means it.
    "sanhedrin": {"born": "welcome", "vat": "welcome", "graft": "welcome",
                  "recorded": "welcome", "machine": "welcome",
                  "alien": "welcome"},
    "abyssals": {"born": "watched", "vat": "watched", "graft": "watched",
                 "recorded": "licensed", "machine": "licensed",
                 "alien": "welcome"},
    "kith": {"born": "licensed", "vat": "licensed", "graft": "licensed",
             "recorded": "watched", "machine": "watched",
             "alien": "welcome"},
}
DEFAULT_VIEW = "licensed"

#: How much each sort of government tightens it, in bands. A *procedure*
#: again: a bureaucracy is not hostile, it simply has a form for everything
#: and will find one for you.
GOV_BITE = {
    0: -1,     # nobody speaks for it — nobody asks either
    1: 0,      # a company: the deed decides, and it says nothing about you
    2: -1,     # everyone votes on everything, including about you
    3: 1,      # the same names, always, and they know what they like
    4: 0,
    5: 1,      # authority follows the licence, and you have not got one
    6: 1,      # run from somewhere else, by people who have not met you
    7: 1,      # several governments, none agreed, all of them asking
    8: 1,
    9: 1,
    10: 1,
    11: 0,
    12: 0,
    13: 2,     # the doctrine is the law, and the doctrine has a view
}

#: Where the law level starts turning a view into a procedure. Below the
#: first, nobody is checking; at the second, what was watched is refused.
LAW_PAPERS = 6
LAW_CLOSES = 9

#: Which lineages a hull of each family actually draws to its board. Not a
#: rule about who *may* serve — that is the gate's business — but about who
#: turns up: a berth is somewhere to live, and a frame would rather live in
#: a fabricated hull with a power bus than in something with a gut.
HULL_DRAW = {
    "grown": {"wet": 7, "vatborn": 3, "grafted": 2, "kith": 1},
    "fabricated": {"wet": 4, "grafted": 4, "frame": 3, "vatborn": 2,
                   "mind": 1},
    "hybrid": {"wet": 5, "grafted": 4, "vatborn": 3, "frame": 1},
    "synthetic": {"mind": 5, "frame": 4, "dry": 3, "grafted": 2, "wet": 1},
    "xeno": {"xeno": 4, "kith": 3, "wet": 2, "grafted": 1},
}
DEFAULT_DRAW = {"wet": 6, "grafted": 2, "vatborn": 2}

#: What a crew of mixed kinds costs in goodwill: loyalty a day, per person
#: who minds, per head aboard that is not their own sort. Measured against
#: `loyalty.DRIFT_PER_DAY` (0.0022) — at anything under a tenth the drift
#: simply swallowed it and a month of it read as a *rise*.
#:
#: It compounds on purpose. A purist among their own kind is a person with
#: an opinion; a purist on a bridge of six substrates is an argument every
#: watch, and a month of that should be a crisis rather than a rounding.
FRICTION_PER_CLASS = 0.10

#: How much being treated like that costs somebody's loyalty a day, while
#: the hull is actually alongside. **Only a refusal costs anything.**
#:
#: The first draft charged for papers and for being read, and a well-run
#: year at ordinary ports took an officer from 62 to 46 — measured, and it
#: broke two checks that had been green for months. Paperwork is an
#: irritation; being the one kept aboard while the rest of the watch walks
#: down the gangway is an injury, and only the injury is charged.
ASHORE_STING = {"welcome": 0.0, "licensed": 0.0, "watched": 0.0,
                "refused": -0.06}


def view_of(faction: str, kind: str) -> str:
    """What this power thinks of that sort of being, before anything else."""
    return FACTION_VIEW.get(faction or "", {}).get(kind, DEFAULT_VIEW)


def harder(band: str, steps: int) -> str:
    """Move a band along the ladder, clamped at both ends."""
    at = BANDS.index(band) if band in BANDS else 1
    return BANDS[max(0, min(len(BANDS) - 1, at + steps))]


def class_of(lineage_id: str) -> str:
    """Which category a substrate is sorted into."""
    return CLASS_OF.get(lineage_id or "", "born")
