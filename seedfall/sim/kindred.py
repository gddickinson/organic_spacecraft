"""Who may stand a watch, who may walk ashore, and who minds.

`data/kindred.py` holds the views; this asks them about a real place and a
real person. Three questions and nothing else:

- **May they sign on here?** A hiring board is a fact about a place, and a
  place that will not have a frame ashore will not put one on its board.
- **May they walk down the gangway?** The same ladder, one rung further: a
  crew can be aboard a hull at a port that will not admit half of it, and
  that is a decision rather than a bug — it costs the people who are kept
  aboard, every port you make.
- **What does it cost to carry a mixed crew?** Nothing at all on a
  Freeholds run and rather a lot in Charter space, and the difference is
  the whole point of a creed.

**Read-only, and derived.** Nothing here is saved: a standing is a function
of the place, the officer's lineage and the powers' own tables, so it cannot
drift from them and an old chronicle gets it on load.
"""

from __future__ import annotations

from ..data import kindred as table
from ..data.lineages import LINEAGES_BY_ID
from . import lifespan

#: The conviction that makes somebody mind. Everything else on the bridge
#: argues about the Bloom, the licence and the money; this one argues about
#: the people standing next to them.
PURIST = "purist"


def kind_of(officer, game=None) -> str:
    """Which category this person is sorted into by anybody who sorts."""
    lineage = lifespan.lineage_of(officer, game)
    return table.class_of(getattr(lineage, "id", "wet"))


def standing(game, place, lineage_id: str) -> dict:
    """What this gate makes of that sort of being.

    The view is the power's; the government and the law level are the
    procedure laid over it. Returned whole because a screen wants all of it:
    the band, the reason, and which of the three did the tightening.
    """
    kind = table.class_of(lineage_id)
    faction = getattr(place, "faction", "") or ""
    band = table.view_of(faction, kind)
    why = []
    if faction:
        why.append(f"{faction.title()} ground")
    # A holding of your own answers to nobody, which is most of the reason
    # to plant one.
    if getattr(place, "mine", False) or getattr(place, "kind", "") == "ship":
        return {"band": "welcome", "kind": kind, "why": ["your own deck"],
                "papers": False, "refused": False}
    from . import authority
    digit, gov_name, _note = authority.government(game, place)
    bite = table.GOV_BITE.get(digit, 0) if digit >= 0 else 0
    if bite:
        was = band
        band = table.harder(band, bite)
        # **A government tightens; only the law shuts a gate.** Without this
        # an ordinary Charter bureaucracy turned *watched* into *refused*
        # and half the sector would not admit a frame at all — measured on a
        # Fleet Hub, where six of eight substrates were refused outright.
        if band == "refused" and was != "refused":
            band = "watched"
        why.append(f"{gov_name.lower()}" if bite > 0 else
                   f"{gov_name.lower()}, and nobody checking")
    law = int(getattr(place, "law", 0) or 0)
    own = table.view_of(faction, kind)
    # **The law shuts a gate the power already disfavours, and no other.**
    # Without the `own` test a law-10 doctrinal world refused *everybody*,
    # including the substrates its own creed welcomes — the Dry Choir's
    # capital would not admit a Dry Choir recording, which is absurd and was
    # measured.
    if law >= table.LAW_CLOSES and own in ("watched", "refused"):
        band = "refused"
        why.append(f"law level {law}")
    elif law >= table.LAW_PAPERS:
        band = table.harder(band, 1)
        if band == "refused":
            band = "watched"
        why.append(f"law level {law}")
    return {"band": band, "kind": kind, "why": why,
            "papers": band in ("licensed", "watched"),
            "refused": band == "refused"}


def may_sign(game, place, lineage_id: str) -> tuple:
    """Whether this sort of being could be hired here, and what stops it."""
    got = standing(game, place, lineage_id)
    if got["refused"]:
        name = table.CLASS_NAME.get(got["kind"], got["kind"])
        return False, (f"{name} are not permitted ashore here — "
                       + ", ".join(got["why"]) + ".")
    return True, ""


def ashore(game, place, officer) -> dict:
    """What happens to this person at this gate."""
    lineage = lifespan.lineage_of(officer, game)
    return standing(game, place, getattr(lineage, "id", "wet"))


def kept_aboard(game, place) -> list:
    """Everybody the watch would have to leave on the hull.

    The line a captain actually wants before granting shore leave: *who does
    not get to go*. Nothing else in the game could answer it.
    """
    out = []
    for officer in lifespan.active(getattr(game, "officers", []) or []):
        got = ashore(game, place, officer)
        if got["refused"]:
            out.append({"officer": officer, "standing": got})
    return out


def complement(game) -> dict:
    """What the bridge is made of, counted by substrate and by class."""
    lineages: dict = {}
    classes: dict = {}
    for officer in lifespan.active(getattr(game, "officers", []) or []):
        got = lifespan.lineage_of(officer, game)
        lineages[got.id] = lineages.get(got.id, 0) + 1
        kind = table.class_of(got.id)
        classes[kind] = classes.get(kind, 0) + 1
    return {"lineages": lineages, "classes": classes,
            "kinds": len(classes), "heads": sum(lineages.values())}


def purists(game) -> list:
    """Everybody aboard who minds what the person beside them is made of."""
    return [o for o in lifespan.active(getattr(game, "officers", []) or [])
            if getattr(o, "conviction", None) == PURIST]


def friction(game) -> dict:
    """What a mixed crew costs in goodwill, and who is paying it.

    Nothing at all on a bridge of one substrate, and nothing at all on a
    bridge with nobody who minds — which is the point. A purist among their
    own kind is a person with an opinion; a purist on a bridge of six
    substrates is an argument every watch.
    """
    read = complement(game)
    minders = purists(game)
    if not minders or read["kinds"] <= 1:
        return {"per_day": 0.0, "minders": minders, "others": 0,
                "kinds": read["kinds"]}
    cost = 0.0
    for officer in minders:
        own = table.class_of(getattr(
            lifespan.lineage_of(officer, game), "id", "wet"))
        others = sum(n for kind, n in read["classes"].items() if kind != own)
        cost += others * table.FRICTION_PER_CLASS
    return {"per_day": cost, "minders": minders,
            "others": sum(read["classes"].values()), "kinds": read["kinds"]}


def draw_for(game) -> dict:
    """Which substrates turn up on a board, weighted by what the hull is.

    A berth is somewhere to live. A frame would rather live in a fabricated
    hull with a power bus than in something with a gut, and a Kith body will
    not sign to either.
    """
    from ..data.chassis import CHASSIS_BY_ID
    chassis = CHASSIS_BY_ID.get(getattr(getattr(game, "ship", None),
                                        "chassis", ""))
    family = getattr(chassis, "family", "") if chassis is not None else ""
    return dict(table.HULL_DRAW.get(family, table.DEFAULT_DRAW))


def pick(game, place, rng) -> str:
    """One candidate's substrate: what the hull draws, minus what the gate
    refuses. A board only ever holds people the port would admit."""
    weights = draw_for(game)
    rows = []
    for lineage_id, weight in weights.items():
        if lineage_id not in LINEAGES_BY_ID or weight <= 0:
            continue
        if place is not None and not may_sign(game, place, lineage_id)[0]:
            continue
        rows.append((weight, lineage_id))
    # **A port that will admit nobody has no board.** Falling back to `wet`
    # here put a candidate on a Sanhedrin law-9 gate that refuses everybody,
    # including them — a button that could not be pressed and a person who
    # could not exist.
    if not rows:
        return ""
    return rng.weighted(rows)


def tick(game, days: float) -> list:
    """What carrying a mixed crew costs, day by day.

    Two charges, both in goodwill rather than money, and both of them
    nothing at all on most bridges: the argument at the table (a purist
    among people they will not call shipmates) and the gate (being kept
    aboard while the rest of the watch goes ashore). Called from
    `core/shiptime` beside the clinic's own bill, because it is the same
    sort of thing: a running cost of who you chose to carry.
    """
    if days <= 0:
        return []
    from . import loyalty as loyalty_sim
    from . import places as places_sim
    said, read = [], friction(game)
    if read["per_day"] > 0:
        for officer in read["minders"]:
            loyalty_sim.shift(officer, -read["per_day"] * days)
        # `game.flags`, not an attribute of our own: `core/save.STRICT`
        # refuses anything undeclared, and a private field invented by a sim
        # module took the whole save down.
        flags = getattr(game, "flags", None)
        if flags is not None and not flags.get("kindred_said"):
            flags["kindred_said"] = True
            names = ", ".join(o.name for o in read["minders"])
            said.append(("warn", f"{names} will not call half this bridge "
                                 "shipmates, and it is beginning to show."))
    place = places_sim.current(game)
    # Only while actually alongside. `current` answers with the best place
    # in the system whether or not the hull is at it, and a crossing is not
    # somewhere anybody is being refused entry.
    if (place is not None and getattr(place, "kind", "") != "ship"
            and getattr(place, "here", False)):
        for officer in lifespan.active(getattr(game, "officers", []) or []):
            got = ashore(game, place, officer)
            hit = table.ASHORE_STING.get(got["band"], 0.0)
            if hit:
                loyalty_sim.shift(officer, hit * days)
    return said


# ── what the screens ask ───────────────────────────────────────────────────

def says(game, place) -> list:
    """What this gate makes of the crew you actually have."""
    read = complement(game)
    if not read["heads"]:
        return ["Nobody on the bridge for anybody to have a view about."]
    said = []
    for kind, count in sorted(read["classes"].items(), key=lambda r: -r[1]):
        lineage_id = next(
            (lid for lid in read["lineages"]
             if table.class_of(lid) == kind), "wet")
        got = standing(game, place, lineage_id)
        said.append(f"{table.CLASS_NAME[kind]} ({count}): {got['band']} — "
                    + table.BAND_NOTE[got["band"]]
                    + (" · " + ", ".join(got["why"]) if got["why"] else ""))
    return said
