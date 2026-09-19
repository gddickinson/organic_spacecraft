"""The two perks that are acts rather than numbers: a motion of your own at
the Assembly (Admiral of the Verge) and your name on the chart (Legend).

The other four are read where they bite, one line each, through
`sim/renown.perk`: a full quay holds you a berth (`sim/control.free`), the
charter fee is waived (`sim/freightlines.charter_terms`), recruits come a
level better (`sim/crew.pool_at`), and the standing floor is held daily
(`sim/renown.hold`). Every act here has its terms first, and the act does
exactly what the terms said.
"""

from __future__ import annotations

from ..data.milestones import TABLE_EVERY
from . import renown


# ── a motion of your own ───────────────────────────────────────────────────

def _live(game) -> set:
    from . import assembly, assembly_session
    st = assembly.ensure(game)
    return {a.key for a in assembly.in_force(game)} | \
        assembly_session.lost_last(st)


def motions(game) -> list:
    """The instruments the Assembly could table for you today, as
    `assembly_session` would frame them (its own candidate rule), less what
    is in force or was just voted down."""
    from ..data.assembly import RESOLUTIONS
    from . import assembly, assembly_session
    st = assembly.ensure(game)
    rng = assembly_session.luck(game, st.session + 1, "captain")
    live = _live(game)
    out = []
    for res in RESOLUTIONS:
        got = assembly_session._candidate(game, res, rng)
        if got is None:
            continue
        _weight, params, sponsor = got
        item = assembly.Tabled(key=assembly_session._key(res.id, params),
                               res_id=res.id, sponsor=sponsor, params=params)
        if item.key not in live:
            out.append(item)
    return out


def table_terms(game) -> dict:
    """Whether a motion can be named now, and why not."""
    st = renown.ensure(game)
    if not renown.perk(game, "table"):
        return {"ok": False, "why": "The Assembly tables a captain's motion "
                                    "for an Admiral of the Verge."}
    last = st.motion.get("day")
    if last is not None and game.day - last < TABLE_EVERY:
        return {"ok": False, "why": f"You named a motion on day {last}; "
                                    f"the next on day {last + TABLE_EVERY}."}
    options = motions(game)
    if not options:
        return {"ok": False, "why": "Nothing the four would sit on is "
                                    "open to be tabled today."}
    return {"ok": True, "why": "", "options": options}


def table(game, key: str) -> dict:
    """Name the motion; it goes on the next order paper published."""
    terms = table_terms(game)
    if not terms["ok"]:
        return terms
    item = next((t for t in terms["options"] if t.key == key), None)
    if item is None:
        return {"ok": False, "why": "That motion is not open to be tabled."}
    st = renown.ensure(game)
    st.motion = {"res": item.res_id, "key": item.key, "day": int(game.day),
                 "sponsor": item.sponsor, "params": dict(item.params)}
    from . import assembly_vote as vote
    game.add_log(f"You have named a motion for the next sitting: "
                 f"{vote.title(item)}.", "good")
    return {"ok": True, "item": item}


def motion(game, agenda: list) -> list:
    """The order paper, with the captain's motion on it if one is waiting.
    One line in `assembly_session.announce`; the motion is spent."""
    st = renown.state(game)
    held = st.motion if st is not None else {}
    if not held or "used" in held or not renown.perk(game, "table"):
        return agenda
    from . import assembly
    if held["key"] in {t.key for t in agenda} | _live(game):
        held["used"] = int(game.day)
        return agenda
    held["used"] = int(game.day)
    return list(agenda) + [assembly.Tabled(
        key=held["key"], res_id=held["res"], sponsor=held["sponsor"],
        params=dict(held.get("params", {})))]


# ── your name on the chart ─────────────────────────────────────────────────

def name_of(game) -> str:
    return f"{game.ship.name}'s Reach"


def name_terms(game, system_id: int) -> dict:
    st = renown.ensure(game)
    if not renown.perk(game, "name"):
        return {"ok": False, "why": "A system is named for a Legend."}
    if st.named:
        return {"ok": False, "why": f"{st.named['now']} already carries "
                                    "your name."}
    systems = game.galaxy.systems
    if not 0 <= system_id < len(systems):
        return {"ok": False, "why": "No such system."}
    system = systems[system_id]
    if not system.visited:
        return {"ok": False, "why": "You would name a star you have been to."}
    return {"ok": True, "why": "", "was": system.name,
            "now": name_of(game)}


def name_system(game, system_id: int) -> dict:
    terms = name_terms(game, system_id)
    if not terms["ok"]:
        return terms
    system = game.galaxy.systems[system_id]
    system.name = terms["now"]
    renown.ensure(game).named = {"system": system_id, "was": terms["was"],
                                 "now": terms["now"], "day": int(game.day)}
    game.add_log(f"{terms['was']} is {terms['now']} on every chart in the "
                 "Verge from today.", "good")
    return {"ok": True, **terms}
