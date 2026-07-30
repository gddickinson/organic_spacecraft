"""The gunner's board: pressed, and read back off the screen.

`test_volley.py` next door holds the sim — what a volley costs the hull, what
will bear, and which set is worth firing. This holds the seat itself, because the
whole gap the station was built for was that `combat` could already fire a chosen
set and **no seat could ask for it**: a check that called `gunnery.volley`
directly would have passed for as long as the bug existed.

Split out when the two together went past five hundred lines.
"""

from __future__ import annotations

from ..sim import gunnery
from .harness import Suite
from .test_volley import ARCS, HOT, LONG, _battle


def _board_text(window) -> str:
    """Every label and button caption on the gunner's board, as one string.

    Only `QLabel` and `QPushButton`, by type. A first draft swept
    `findChildren(object)` and called `text()` on whatever came back inside a
    `try`, which is how you reach a Python wrapper whose C++ object has already
    gone: the full suite segfaulted three suites later, in the 3D renderer, with
    nothing in this file failing. Ask for the types you want.
    """
    from PyQt6.QtWidgets import QLabel, QPushButton

    out: list[str] = []
    for index in range(window.board.count()):
        widget = window.board.itemAt(index).widget()
        if widget is None:
            continue
        if isinstance(widget, (QLabel, QPushButton)):
            out.append(widget.text())
        for kind in (QLabel, QPushButton):
            out.extend(child.text() for child in widget.findChildren(kind))
    return " | ".join(out)


def run(suite: Suite) -> None:
    check = suite.check

    @check("the board drives the trigger, pressed through the window")
    def _():
        # Through the window, because the whole gap was that the sim could do
        # this and no seat could ask for it. A check that called
        # `gunnery.volley` directly would have passed throughout.
        from PyQt6.QtWidgets import QApplication

        from .test_ui import _use_offscreen
        _use_offscreen()
        from ..ui.gunner_window import open_gunnery
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        # HOT rather than ARCS: on the mixed-arc hull only three mounts bear and
        # the advice takes all three, so a mutation replacing the trigger with a
        # full salvo fired exactly the same shots and nothing failed. The board
        # has to be checked where what it shows and what a salvo would do differ.
        game, _rng, b = _battle("win", loadout=HOT)
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.battle = b
        gw = open_gunnery(win)

        every = gw.chosen()
        assert len(every) >= 3, every

        # Hold one mount and the volley and the heat both follow.
        slot = next(i for i, s in enumerate(gunnery.mounts(b)) if s.can_fire)
        gw._toggle(slot)
        fewer = gw.chosen()
        assert len(fewer) == len(every) - 1, (every, fewer)
        assert (gunnery.quote(b, fewer)["heat_added"]
                < gunnery.quote(b, every)["heat_added"])

        # The advice is expressed as holds, and agrees with the sim.
        gw._advise()
        assert sorted(gw.chosen()) == sorted(gunnery.advise(b)), (
            gw.chosen(), gunnery.advise(b))

        # Hold everything and the trigger goes dead rather than firing all.
        gw._none()
        assert gw.chosen() == []
        gw.refresh()
        assert not gw.fire_btn.isEnabled(), (
            "with everything held the trigger is still live")

        # And pulling it spends heat on exactly what was shown — which has to be
        # less than a salvo would, or the check cannot tell the two apart.
        gw._advise()
        picked = list(gw.chosen())
        assert len(picked) < len(every), (
            f"the advice picked all {len(every)} bearing mounts, so this hull "
            "cannot distinguish the trigger from a full salvo")
        said = gunnery.quote(b, picked)
        assert said["heat_added"] < gunnery.quote(b, every)["heat_added"]
        gw._fire()
        assert abs(b.player.ship.heat - said["heat_after"]) < 1e-6, (
            f"the window promised {said['heat_after']:.2f} and the hull came "
            f"out at {b.player.ship.heat:.2f}")
        gw.close()
        win.close()
        return (f"{len(every)} bearing, held one → {len(fewer)}, advice "
                f"{len(picked)}, heat landed at {b.player.ship.heat:.1f}")

    @check("a sight draws its arc on both sides of the bow")
    def _():
        # My own bug, and one the screen hid: `arc_span` returns *half-angles* —
        # its docstring says so — and the first draft drew a single wedge from
        # `low` clockwise, putting a fore arc entirely to starboard. It looked
        # plausible because the target happened to be near dead ahead when I
        # looked at it. `ui/tactical_plot.py` had already been fixed for the same
        # thing and left the reason behind: "drawing only one of them is a lie
        # about the ship."
        from PyQt6.QtWidgets import QApplication

        from .test_ui import _use_offscreen
        _use_offscreen()
        from ..ui.mount_sight import MountSight

        app = QApplication.instance() or QApplication([])
        assert app is not None
        _game, _rng, b = _battle("sight", loadout=ARCS)
        shots = {s.arc: s for s in gunnery.mounts(b)}
        assert "broad" in shots and "fore" in shots, sorted(shots)

        def lit(shot):
            """Painted pixels either side of the centreline."""
            widget = MountSight(shot, 0.0)
            widget.resize(160, 160)
            image = widget.grab().toImage()
            left = right = 0
            for y in range(26, 134, 3):
                for x in range(10, 150, 3):
                    px = image.pixel(x, y)
                    bright = (px >> 16 & 255) + (px >> 8 & 255) + (px & 255)
                    if bright < 130:
                        continue
                    if x < 72:
                        left += 1
                    elif x > 88:
                        right += 1
            return left, right

        said = []
        for arc in ("broad", "fore"):
            left, right = lit(shots[arc])
            assert left > 6 and right > 6, (
                f"a {arc} arc drew {left} lit pixels to port and {right} to "
                "starboard — an arc is symmetric about the bow, so one side "
                "being empty means only half of it is drawn")
            lean = abs(left - right) / max(1, left + right)
            assert lean < 0.35, (
                f"a {arc} arc is {lean:.0%} lopsided: {left} port, "
                f"{right} starboard")
            said.append(f"{arc} {left}/{right}")
        return " · ".join(said) + " pixels port/starboard"

    @check("the board says what would fix a mount, and what the last volley did")
    def _():
        # Two fields the declared-field guard found dead, both on the one board
        # whose job they are.
        #
        # `firing.Shot.band_shift` — "bands to close (negative) or open
        # (positive) to reach its envelope" — was read by nobody, so a mount out
        # of range said "range" and left the captain to work out which way.
        # `gunfire.Shot.frm`, `.to` and `.weapon` recorded who fired, at whom,
        # with what, and nothing read any of them: which gun did what existed
        # only as prose in the log, while the gunner pulling the trigger saw a
        # heat number change and nothing else.
        from PyQt6.QtWidgets import QApplication

        from .test_ui import _use_offscreen
        _use_offscreen()
        from ..ui.gunner_window import open_gunnery
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game, _rng, b = _battle("board", loadout=LONG)
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.battle = b
        gw = open_gunnery(win)

        # Nose to nose, where a torpedo banded (3, 4) is three bands short.
        b.enemy.body.x = b.player.body.x + 6
        b.enemy.body.y = b.player.body.y
        assert b.band == 0, (
            f"nose to nose is supposed to be band 0 and reads {b.band}")
        shifted = [x for x in gunnery.mounts(b)
                   if not x.can_fire and x.blocked_by == "range"
                   and x.band_shift]
        assert shifted, (
            "no mount is blocked by range at contact, so this check would pass "
            "without ever testing `band_shift`: "
            + str([(x.name, x.blocked_by, x.band_shift)
                   for x in gunnery.mounts(b)]))
        gw.refresh()
        said = _board_text(gw)
        want = shifted[0]
        phrase = (f"close {abs(want.band_shift)}" if want.band_shift < 0
                  else f"open {want.band_shift}")
        assert phrase in said, (
            f"{want.name} is {want.band_shift} bands out of its envelope and "
            f"the board never says {phrase!r} — it knows which way to go and "
            f"will not say. Board reads: {said!r}")
        # And it says which way, not merely how far: an opposite order would be
        # worse than none.
        wrong = (f"open {abs(want.band_shift)}" if want.band_shift < 0
                 else f"close {want.band_shift}")
        assert wrong not in said, (
            f"the board says {wrong!r} for a mount that needs {phrase!r}")

        # Fire, then check the exchange names the gun, both hulls and the result.
        gw._advise()
        gw._fire()
        gw.refresh()
        said = _board_text(gw)
        assert b.shots, "the volley recorded no shots at all"
        for shot in b.shots[-4:]:
            assert shot.weapon in said, (
                f"{shot.weapon} fired and the board never mentions it")
        names = {shot.frm for shot in b.shots} | {shot.to for shot in b.shots}
        assert any(n in said for n in names), (
            f"the exchange names neither hull: {sorted(names)}")
        theirs = [s for s in b.shots if not s.mine]
        return (f"{len(b.shots)} shot(s) listed, {len(theirs)} of them incoming"
                + (f"; a mount reads {phrase!r}" if shifted else ""))

