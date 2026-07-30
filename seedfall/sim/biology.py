"""What you can make sense of on the ground, and what you can only bag.

`Lifeform.metabolism` is the identity key behind the two strings the survey
screens print, and **nothing read the key itself** — so the catalogue could not
group by it and nothing could ask whether the captain had any business
understanding what they were looking at. A radiotroph and a photoautotroph were
the same row with different words.

`data/lifeforms.METABOLISM_TECH` pairs each of the eight biochemistries with the
node in the tech tree that *is* that biochemistry, which the tree's own names give
away — the Sabatier Loop makes methane, trehalose vitrification is cryptobiosis,
Deinococcus is the radiation organism. So:

**A specimen is worth more to somebody who knows what it is doing.** Catalogue a
piezophile with no piezolyte physiology and you have a jar of tissue: it counts,
it goes in the register, and it yields less than it would to a captain who can
read it. Which closes a loop that was already half built — `data/inquiry.py` has
the metabolism branch of research running on **60% specimen evidence**, so the
specimens fund the branch that explains the specimens.

**One door.** `worth` is the only place a specimen's research value is decided,
and the survey screens quote it through `explain`. It used to be computed inside
`world/planets.survey_body` — a layer that cannot ask what the captain knows —
and moving it here is what let the answer depend on the reader.
"""

from __future__ import annotations

from ..data.lifeforms import METABOLISM_TECH, METABOLISMS, UNDERSTOOD_WORTH
from ..data.tech import TECH_BY_ID

#: What a catalogued specimen is worth in research, before asking who is
#: holding it. Lifted out of `world/planets.py`, where it sat as a bare 0.25 in
#: the middle of the survey arithmetic.
SPECIMEN_SHARE = 0.25


def tech_for(metabolism: str) -> str | None:
    """The technology that explains this biochemistry, if the tree has one."""
    return METABOLISM_TECH.get(metabolism)


def known_tech(game, tech_id: str | None) -> bool:
    """Is this node in hand? A provisional result counts — it works, and it
    does not work as well as the paper says."""
    if not tech_id:
        return False
    research = game.research
    return (tech_id in research.unlocked
            or tech_id in (getattr(research, "provisional", ()) or ()))


def understood(game, lifeform) -> bool:
    """Can anybody aboard say what this organism is doing?"""
    return known_tech(game, tech_for(getattr(lifeform, "metabolism", "")))


def worth(game, lifeform) -> int:
    """The research one catalogued specimen yields *to this captain*.

    The one door. `world/planets.survey_body` used to add `lf.value * 0.25`
    itself, which is a layer deciding what a specimen is worth without being
    able to ask who found it.
    """
    base = getattr(lifeform, "value", 0) * SPECIMEN_SHARE
    if not understood(game, lifeform):
        base *= UNDERSTOOD_WORTH
    return round(base)


def harvest(game, lifeforms) -> dict:
    """What a survey's catch is worth, and how much of it was legible.

    Returned as a whole rather than a number, because the screens want to say
    *which* of them nobody could read — a captain who knows they are leaving
    value on the ground has a reason to go back once the bench catches up.
    """
    got = list(lifeforms or ())
    read = [lf for lf in got if understood(game, lf)]
    return {
        "research": sum(worth(game, lf) for lf in got),
        "count": len(got),
        "read": len(read),
        "blind": [lf for lf in got if lf not in read],
    }


def explain(game, lifeform) -> str:
    """One line on whether this is a specimen or a puzzle."""
    metabolism = getattr(lifeform, "metabolism", "")
    tech_id = tech_for(metabolism)
    if understood(game, lifeform):
        tech = TECH_BY_ID.get(tech_id)
        return (f"{tech.name} explains it" if tech
                else "the bench can read this one")
    tech = TECH_BY_ID.get(tech_id)
    if tech is None:
        return "nothing in the tree explains this biochemistry yet"
    return (f"nobody aboard can read it — {tech.name} would, at "
            f"{tech.cost:,} points")


def catalogue(game) -> list[dict]:
    """Every organism you have catalogued, grouped by what it runs on.

    The grouping the metabolism key was declared for. Sorted by how much of
    each biochemistry you have found, so the deepest column reads first.
    """
    seen: dict[str, list] = {}
    for system in game.galaxy.systems:
        for body in system.bodies:
            for lifeform in getattr(body, "lifeforms", ()) or ():
                if not getattr(lifeform, "catalogued", False):
                    continue
                seen.setdefault(lifeform.metabolism, []).append(
                    {"lifeform": lifeform, "body": body, "system": system})
    out = []
    for metabolism, name, note, mult in METABOLISMS:
        rows = seen.get(metabolism, [])
        if not rows:
            continue
        tech_id = tech_for(metabolism)
        tech = TECH_BY_ID.get(tech_id)
        out.append({
            "metabolism": metabolism,
            "name": name,
            "note": note,
            "multiplier": mult,
            "rows": rows,
            "tech": tech,
            "understood": known_tech(game, tech_id),
        })
    out.sort(key=lambda row: (-len(row["rows"]), row["name"]))
    return out


def summary(game) -> dict:
    """The catalogue in one line, and what is still illegible."""
    groups = catalogue(game)
    found = sum(len(row["rows"]) for row in groups)
    read = sum(len(row["rows"]) for row in groups if row["understood"])
    return {
        "kinds": len(groups),
        "found": found,
        "read": read,
        "blind": found - read,
        "of": len(METABOLISMS),
    }
