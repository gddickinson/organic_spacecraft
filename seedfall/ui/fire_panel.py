"""The fire control: what may be fired on, at what range, and the act itself.

`sim/engage` has decided since it landed who may be fired on and at what band
the fight opens — and **nothing in `ui/` could reach it**. The console offered
Break off, Make orbit, Close and berth, Hold, Kill relative motion, Secure and
the clock, and not one word about weapons. The range a pilot flew for was a
number no screen would spend.

**A refusal is printed, never greyed.** That is the discipline `sim/clearance`
holds for a berth and the reason `engage.may_engage` returns a sentence rather
than a bool: a button that goes grey teaches nothing, and "The guns answer to
the conn, and the conn is flying an approach — break off first" teaches the
pilot what to do next. So the button is always live and pressing it either
opens fire or says why not.

**The battle `engage` built is the battle that gets fought.** `ui/battle_view`
has its own `begin`, which takes an *encounter dict* and constructs a `Battle`
of its own with no band — so routing a conn engagement through it would throw
away the range the flying earned and open every fight at the default. Measured:
`open_fire` on a contact 2,700 km off returns a battle at band 2, and handing
that battle straight to the window keeps band 2 on the screen. There is one
door here and it is `engage.open_fire`.

The seam is `(win, game, conn)` rather than a window, because the Pilot screen
holds its own free flight while the conn window keeps one on the game. Both can
answer those three.
"""

from __future__ import annotations

from ..sim import engage as engage_sim
from ..sim import hostiles as hostiles_sim
from .widgets import Panel, button, note


def ranged(game, conn, contacts) -> list:
    """`(km, contact)` for everything, nearest first — measured once.

    **Every range on this screen used to be measured on demand**, and the
    demand was thirty-two times a click: `in_view`, the contact rows, the
    fly-at buttons, the board and the triggers each asked again. Every ask
    walks `track.at` -> `traffic.in_system`, which rebuilds the system's
    traffic from nothing. Profiled, that was 27 rebuilds per button press.
    Measure once, hand the answer down.
    """
    if conn is None:
        return []
    rows = [(engage_sim.range_km(game, conn, c), c) for c in contacts]
    return sorted(rows, key=lambda row: row[0])


def targets(rows, limit: int = 6) -> list:
    """Hulls the guns can actually reach, nearest first.

    **Rendered and read, the first draft offered to open fire on a hull
    1,293,058,866 km away** and called it extreme range, because `band_for`
    clamps to the last band so everything past `engage.reach_km` reads as
    merely far. Four of the five hulls on seed "fire" were like that, the
    worst 129,306 times past reach.

    Printing a refusal is the discipline for a *plausible* no — a world, an
    approach in progress, an empty rack. It is not a reason to put a trigger
    under something half a system away. Those are counted below the board
    instead, so the pilot knows they are out there.
    """
    reach = engage_sim.reach_km()
    return [c for km, c in rows
            if getattr(c, "kind", "") == "hull" and km <= reach][:limit]


def board(game, conn, rows) -> Panel:
    """The gunner's list: every hull, its range, and what firing would mean.

    `engage.note` is the one door for that sentence — it is what the pilot
    reads before committing, and it says the band in the same words
    `sim/combat` uses, so the board cannot promise a fight the model will not
    give.
    """
    panel = Panel("Fire control")
    seen = targets(rows)
    hulls = [c for _km, c in rows if getattr(c, "kind", "") == "hull"]
    beyond = len(hulls) - len(seen)
    if not seen:
        panel.add(note(
            f"Nothing is within {engage_sim.reach_km():,.0f} km of her."
            + (f" {beyond} hull(s) are out there, all further off than the "
               f"guns will reach." if beyond else
               " There is nothing out there to open fire on.")))
        return panel
    km_of = {id(c): km for km, c in rows}
    for contact in seen:
        km = km_of.get(id(contact))
        ok, _why = engage_sim.may_engage(game, conn, contact, km)
        flag = " ✕ marked" if hostiles_sim.is_marked(
            game, getattr(contact, "hull_id", "")) else ""
        panel.add_row(contact.name + flag,
                      engage_sim.note(game, conn, contact, km),
                      "warn" if not ok or flag else "")
    if beyond:
        panel.add(note(f"{beyond} more hull(s) in the system, all beyond the "
                       f"{engage_sim.reach_km():,.0f} km the guns reach."))
    return panel


def buttons(win, game, conn, rows) -> list:
    """One Open fire button per hull in range. Always live; never greyed."""
    return [button(f"Open fire on {c.name}",
                   lambda _=False, k=c: open_fire(win, game, conn, k),
                   kind="flat")
            for c in targets(rows, limit=4)]


def marks(win, game, rows, after=None) -> list:
    """A mark to set or take off, per hull in range.

    Marking is free and tells nobody — see `sim/hostiles`. What it buys is
    that every chart and board in the sector reads her as an enemy, because
    `sim/traffic` is where the captain's mark and the errand's answer meet.
    """
    out = []
    for contact in targets(rows, limit=4):
        hull_id = getattr(contact, "hull_id", "")
        on = hostiles_sim.is_marked(game, hull_id)
        out.append(button(
            (f"Clear the mark on {contact.name}" if on
             else f"Mark {contact.name} hostile"),
            lambda _=False, k=contact: _flip(win, game, k, after),
            kind="flat"))
    return out


def _flip(win, game, contact, after=None) -> None:
    hull_id = getattr(contact, "hull_id", "")
    if hostiles_sim.is_marked(game, hull_id):
        hostiles_sim.clear(game, hull_id)
        game.add_log(f"The mark is off {contact.name}.", "")
    else:
        hostiles_sim.mark(game, hull_id)
        game.add_log(f"{contact.name} is marked an enemy. It costs nothing "
                     f"and tells nobody.", "warn")
    if after is not None:
        after()
    win.refresh()


def open_fire(win, game, conn, contact) -> bool:
    """Open fire, or say why not. Returns whether a fight began.

    The refusal goes to the log as well as the toast, because a pilot who
    presses a button and gets a sentence should be able to read it again.
    """
    ok, why = engage_sim.may_engage(game, conn, contact)
    if not ok:
        win.toast(why, "warn")
        game.add_log(why, "")
        return False
    battle, why = engage_sim.open_fire(game, conn, contact,
                                       game.rng("engagement"))
    if battle is None:
        win.toast(why, "warn")
        game.add_log(why, "")
        return False
    game.add_log(
        f"Opened fire on {contact.name} at "
        f"{engage_sim.range_km(game, conn, contact):,.0f} km.", "bad")
    # **Handed over, not rebuilt.** `battle_view.begin` would construct a
    # second `Battle` from an encounter dict and lose the band with it.
    win.battle = battle
    win.go("battle")
    return True
