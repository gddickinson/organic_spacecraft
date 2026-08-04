"""How a chronicle ends, and the offer to carry on past it.

Split out of `ui/window.py` when that file went past five hundred lines, along
a seam that was already marked in it — the window owns the chrome, the views
and the navigation; this owns what happens when the sector's story stops.

`MainWindow.check_ending` stays as a two-line door onto `reached` below,
because nine screens call it and every check that stubs a window relies on it
being a method.

**An ending is a turn in the sector's history, not necessarily a stop.** Every
one opens an epoch — the world is rewritten once and a new clock starts in
place of the Bloom — so the dialog offers to carry on as well as to begin
again.
"""

from __future__ import annotations

from ..data.lore import ENDINGS, VICTORIES
from .widgets import label


def reached(win) -> bool:
    """Has the chronicle ended? Shows the ending if so."""
    g = win.game
    if g.victory:
        name = next((v[1] for v in VICTORIES if v[0] == g.victory), "Ending")
        _show(win, name, ENDINGS.get(g.victory, ""), ending=g.victory)
        return True
    if g.dead:
        key = g.ending or "lost"
        name = "Overgrown" if key == "overgrown" else "The chronicle ends"
        # The game has always known why; it simply never said.
        _show(win, name, ENDINGS.get(key, ENDINGS["lost"]), g.death_reason)
        return True
    return False


def _show(win, heading: str, text: str, cause: str = "",
          ending: str = "") -> None:
    """The ending itself, and what the captain may do next."""
    from ..data.epochs import EPOCHS_BY_ID
    from ..sim import legacy as legacy_sim

    g = win.game
    stats_line = (f"Stardate {g.day} days · {len(g.discovered['systems'])} "
                  f"systems visited · {g.discovered['lifeforms']} organisms "
                  f"catalogued · {len(g.colonies)} colonies planted.")
    body = [text]
    if cause:
        body.append(label(cause, "", "warn", wrap=True))
    body.append(label(stats_line, "note", wrap=True))

    epoch = EPOCHS_BY_ID.get(ending)
    choices = [("Begin again", "again")]
    if epoch is not None:
        body.append(label(f"What follows: {epoch.name}. {epoch.pressure}",
                          "", "chloro", wrap=True))
        choices.insert(0, (f"Carry on into {epoch.name}", "carry"))

    picked = win.dialog(heading, body, choices)
    if picked == "carry" and epoch is not None:
        legacy_sim.begin(g, ending)
        win.save()
        win.go("legacy")
        return
    if picked != "again":
        # Escape, or the title bar's close. Dismissing an ending is "not
        # now", never "begin again" — this used to fall through into
        # `clear_save()` and destroy a chronicle that could have carried on.
        # `check_ending` will present it again.
        return
    # No `clear_save()` before the title screen: its own buttons clear the
    # save at the moment a new game exists, so cancelling it costs nothing.
    from .title import start_new_chronicle
    start_new_chronicle(win)
