"""The memoir, and the Hall of Captains.

At an ending or a death the game writes a one-page career record — from the
milestones, the ranks, the rivals, the regions opened, the colonies, the
officers' arcs and the ending itself — keeps it on the chronicle (the
Aftermath screen shows it) and appends it to the **Hall of Captains**: a
file beside the save, kept across chronicles and slots, which "New" never
deletes and the title screen lists.

The Hall follows the save wherever it is redirected, as the named slots do
(`core/slots.slot_dir`): `hall.json` beside the player's `save.json`, and
`<stem>.hall.json` beside any other save — a test run's file is named for
its process in a shared temp folder, and one Hall there would be every
run's. Written staged-and-renamed, like the save.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from ..core import save as save_mod

HALL_NAME = "hall.json"
#: The Hall keeps the most recent this many careers.
HALL_KEPT = 200


def hall_path() -> Path:
    here = save_mod.save_path()
    if here.name == save_mod.SAVE_NAME:
        return here.parent / HALL_NAME
    return here.with_name(here.stem + ".hall.json")


def hall() -> list:
    """Every career in the Hall, newest first. A damaged file reads empty."""
    try:
        rows = json.loads(hall_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = rows if isinstance(rows, list) else []
    return sorted((r for r in rows if isinstance(r, dict)),
                  key=lambda r: -float(r.get("written", 0)))


def _keep(entry: dict) -> bool:
    path = hall_path()
    rows = [r for r in hall() if r.get("key") != entry["key"]]
    rows = ([entry] + rows)[:HALL_KEPT]
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        tmp.replace(path)
        return True
    except OSError:
        return False


# ── the page ───────────────────────────────────────────────────────────────

def _ending(game) -> tuple[str, str]:
    """(the ending's name, how it came)."""
    from ..data.lore import VICTORIES
    if game.victory:
        name = next((v[1] for v in VICTORIES if v[0] == game.victory),
                    game.victory)
        return name, "triumph"
    if game.ending == "overgrown":
        return "Overgrown", "lost"
    return "Lost", "lost"


def compose(game) -> dict:
    """The career as a page: plain data, so the save, the Hall and the
    screen all hold the same thing."""
    from ..data.chassis import CHASSIS_BY_ID
    from . import renown
    from .renown_facts import fact
    st = renown.ensure(game)
    rank = renown.rank(game)
    name, outcome = _ending(game)
    chassis = CHASSIS_BY_ID.get(game.ship.chassis)
    rows = sorted(((day, renown.BY_ID[mid]) for mid, day in st.achieved.items()
                   if mid in renown.BY_ID), key=lambda r: r[0])
    hunt = getattr(game, "hunt", None)
    rivals = [(n.name, n.status) for n in getattr(hunt, "nemeses", None) or []
              if n.status in ("dead", "allied")]
    regions = [r.name for r in getattr(game.galaxy, "regions", None) or []]
    lines = [f"{game.ship.name}, {chassis.name if chassis else game.ship.chassis}"
             f"-class. {rank['name']}, {st.score} renown."]
    if st.titles:
        lines.append("Called " + ", ".join(f"«{t}»" for t in st.titles) + ".")
    cause = (game.death_reason or "").rstrip(".")
    lines.append(f"{game.day} days in command. {name}"
                 + (f": {cause}" if cause else "") + ".")
    lines.append(f"{len(rows)} of {len(renown.ALL)} milestones on the "
                 "Registry's record.")
    # The rungs of the career: each rank, and the milestones worth more
    # than a day's work (15 renown and up) or on an ending's road — the
    # last twelve of them.
    names = {rid: n for rid, n, _need in renown.RANKS}
    events = [(d, f"made {names.get(rid, rid)}") for rid, d in st.ranks[1:]]
    events += [(d, m.name) for d, m in rows if m.renown >= 15 or m.track]
    for day, what in sorted(events)[-12:]:
        lines.append(f"Day {day} — {what[0].upper() + what[1:]}.")
    if rivals:
        lines.append("Rivals: " + "; ".join(
            f"{who} {'destroyed' if how == 'dead' else 'turned'}"
            for who, how in rivals) + ".")
    if regions:
        lines.append("Opened beyond the rim: " + ", ".join(regions) + ".")
    colonies = int(fact(game, "colonies"))
    if colonies:
        lines.append(f"{colonies} colonies online, "
                     f"{int(fact(game, 'citizens')):,} citizens.")
    arcs = int(fact(game, "arcs:finished"))
    if arcs:
        lines.append(f"{arcs} officers' stories carried to their end.")
    return {"key": (st.memoir or {}).get("key")
            or f"{game.seed}:{time.time_ns():x}",
            "ship": game.ship.name, "seed": game.seed, "day": int(game.day),
            "ending": name, "outcome": outcome, "rank": rank["name"],
            "score": st.score, "titles": list(st.titles),
            "milestones": len(rows), "lines": lines}


def record(game) -> dict | None:
    """Write the memoir once, at an ending or a death: onto the chronicle
    and into the Hall. Returns it, or None when there is nothing to end."""
    if not (game.victory or game.dead):
        return None
    from . import renown
    st = renown.ensure(game)
    name, _how = _ending(game)
    held = getattr(st, "memoir", None) or {}
    if held.get("ending") == name and held.get("day") == int(game.day):
        return held
    page = compose(game)
    page["written"] = time.time()
    st.memoir = page
    _keep(page)
    return page


def settle(game) -> None:
    """The clock's door: an ending or a death reached today is written up.
    One line in `core/sectortime.reckoning` (endings, the overgrown loss);
    `Game.die` calls `record` for every other death."""
    if game.victory or game.dead:
        record(game)


def page_of(game) -> dict | None:
    st = getattr(game, "renown", None)
    return getattr(st, "memoir", None) or None
