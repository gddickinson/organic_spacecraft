"""The helm's orrery: what it draws, and what a click on it selects.

Its own suite because the chart got its own module (`ui/orbit_chart.py`) when
`ui/helm_view.py` went past five hundred lines, and because both checks here
work the same unusual way: they ask the **painter** what it was handed rather
than asking the code what it meant to draw. A chart is a picture, and a picture
is the thing to measure.
"""

from __future__ import annotations

import dataclasses
import math

from .test_ui import _use_offscreen

_use_offscreen()


def run(suite) -> bool:
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QEvent, QPointF, QRectF, Qt
        from PyQt6.QtGui import QFontMetricsF, QMouseEvent, QPainter
    except ImportError as err:
        print(f"── orrery ───\n  skipped: PyQt6 not available ({err})\n")
        return False

    from ..core.state import new_game
    from ..sim import anchorage as anchorage_sim
    from ..ui import theme
    from ..ui.orbit_chart import QUAY_HIT
    from ..ui.window import MainWindow

    check = suite.check
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    def chart_for(seed: str):
        win = MainWindow(new_game(seed))
        win.resize(1360, 880)
        win.dialog = lambda *a, **k: None
        win.confirm = lambda *a, **k: False
        win.go("helm")
        chart = next((w for w in win.findChildren(object)
                      if hasattr(w, "place_mark")), None)
        assert chart is not None, f"{seed}: the helm has no orrery"
        return win, chart

    #: `lab8` is named rather than left to luck: across twenty-two seeds it is
    #: the only one with **two quays at one body** — `Fleet Hub` and `Third
    #: Silence`, both at body 0 of Marrow Fall. Every check below would pass
    #: on the other ten without it, which was proved by mutation.
    STACKED = "lab8"
    SEEDS = [f"orrery{i}" for i in range(10)] + [STACKED]

    @check("no two labels on the helm's orrery print across each other")
    def _():
        # Asked of the painter: every `drawText` the chart issues is caught and
        # turned into the rectangle its glyphs will actually occupy. Measured
        # before the fix over these seeds: 83 labels, 3 overlapping pairs, one
        # of them a quay name covered 100% by a hull name. The plot had three
        # label families and only traffic de-cluttered — against a list that
        # collected hull names and nothing else.
        real = QPainter.drawText
        caught: list = []
        on = [False]

        def spy(self, *a):
            if on[0] and a and isinstance(a[0], QRectF) \
                    and isinstance(a[-1], str):
                r, flag, text = a[0], a[1], a[-1]
                fm = QFontMetricsF(self.font())
                w = fm.horizontalAdvance(text)
                x = r.x() + (r.width() - w) / 2 \
                    if flag == Qt.AlignmentFlag.AlignHCenter else r.x()
                caught.append((QRectF(x, r.y(), w, fm.height()), text))
            return real(self, *a)

        seen = 0
        try:
            QPainter.drawText = spy
            for seed in SEEDS:
                win, chart = chart_for(seed)
                caught.clear()
                on[0] = True
                chart.grab()
                on[0] = False
                seen += len(caught)
                for a in range(len(caught)):
                    for b in range(a + 1, len(caught)):
                        if caught[a][0].intersects(caught[b][0]):
                            raise AssertionError(
                                f"seed {seed}: {caught[a][1]!r} and "
                                f"{caught[b][1]!r} print across each other")
                win.close()
        finally:
            QPainter.drawText = real
        assert seen > 40, f"only {seen} labels drawn over {len(SEEDS)} seeds"
        return f"{seen} labels over {len(SEEDS)} seeds, none overlapping"

    @check("every quay gets its own mark, and its own mark selects it")
    def _():
        # `place_mark` offset from the *planet*, so two quays at one body
        # landed on the same point. It serves the painter and the hit test
        # alike — correctly, one door — so both were wrong together: the chart
        # drew one square where there are two stations, and because the hit
        # test takes the nearest mark under 13 px with a strict `d < pd`, the
        # second quay tied and lost. Measured: clicking `Third Silence`'s own
        # mark selected `Fleet Hub`, so it could not be picked at all.
        checked = stacked = 0
        for seed in SEEDS:
            win, chart = chart_for(seed)
            g = win.game
            places = [p for p in anchorage_sim.in_system(g)
                      if p.body_index < len(g.system.bodies)]
            marks = [chart.place_mark(g, p) for p in places]
            spots = {(round(m.x(), 3), round(m.y(), 3)) for m in marks}
            assert len(spots) == len(places), (
                f"seed {seed}: {len(places)} quays share {len(spots)} marks")
            per_body: dict = {}
            for p in places:
                per_body[p.body_index] = per_body.get(p.body_index, 0) + 1
            stacked += sum(1 for n in per_body.values() if n > 1)
            # Distinct is not enough: two marks a pixel apart are distinct and
            # still share one clickable neighbourhood. Quays at the same body
            # must be at least a hit radius apart, or a click a few pixels off
            # the one you meant lands on the other. Proved necessary by
            # mutation — shrinking the fan to 4 px left an earlier version of
            # this check green, because it only ever clicked marks exactly.
            for i, one in enumerate(places):
                for two in places[i + 1:]:
                    if one.body_index != two.body_index:
                        continue
                    a, b = marks[i], marks[places.index(two)]
                    gap = math.dist((a.x(), a.y()), (b.x(), b.y()))
                    assert gap >= QUAY_HIT, (
                        f"seed {seed}: {one.name} and {two.name} sit "
                        f"{gap:.1f} px apart, inside the {QUAY_HIT:.0f} px "
                        "hit radius")

            for place, mark in zip(places, marks):
                # Off-centre, because a captain clicks near a mark and not on
                # it. Nudged toward the middle of the plot, which is where a
                # crowded body's other quays are.
                for dx, dy in ((0.0, 0.0), (4.0, 4.0), (-4.0, -4.0)):
                    chart.place = None
                    chart.mousePressEvent(QMouseEvent(
                        QEvent.Type.MouseButtonPress,
                        QPointF(mark.x() + dx, mark.y() + dy),
                        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                        Qt.KeyboardModifier.NoModifier))
                    assert chart.place == place.id, (
                        f"seed {seed}: clicking {place.name}'s mark "
                        f"{dx:+.0f},{dy:+.0f} off selected {chart.place!r}, "
                        f"not {place.id!r}")
                checked += 1
            # The seat must not depend on the order `in_system` happens to
            # return, or the shipyard a captain clicked yesterday is somewhere
            # else today. Asked by handing the same game back in the opposite
            # order and demanding the same marks — the sort in `_quay_seat` is
            # what makes that true, and removing it is otherwise invisible
            # because reversed seats are still distinct and still clickable.
            if len(places) > 1:
                was = anchorage_sim.in_system
                try:
                    anchorage_sim.in_system = \
                        lambda g_, _w=was: list(reversed(_w(g_)))
                    again = [chart.place_mark(g, p) for p in places]
                finally:
                    anchorage_sim.in_system = was
                for place, before, after in zip(places, marks, again):
                    assert (round(before.x(), 3), round(before.y(), 3)) == \
                           (round(after.x(), 3), round(after.y(), 3)), (
                        f"seed {seed}: {place.name}'s mark moved from "
                        f"({before.x():.1f},{before.y():.1f}) to "
                        f"({after.x():.1f},{after.y():.1f}) when the quays "
                        "were listed in the other order")
            win.close()
        # **The fan is built, not waited for.** This used to require that
        # some seed in the set happened to grow two quays at one body — and
        # once `data/remnants.py` changed what systems hold, no seed in a
        # hundred and sixty did, so the very case the seat fan exists for
        # went untested while the check went on passing. A crowd is made
        # here instead: `place_mark` reads `anchorage_sim.in_system`, which
        # is the same door the ordering check above leans on.
        if not stacked:
            win, chart = chart_for(SEEDS[0])
            g = win.game
            try:
                real = anchorage_sim.in_system
                one = next(p for p in real(g) if p.kind in ("quay", "hub"))
                crowd = [dataclasses.replace(one, id=f"{one.id}-{n}",
                                             name=f"{one.name} {n}")
                         for n in range(3)]
                try:
                    anchorage_sim.in_system = lambda g_, _c=crowd: list(_c)
                    seats = [chart.place_mark(g, p) for p in crowd]
                finally:
                    anchorage_sim.in_system = real
                for i, a in enumerate(seats):
                    for b in seats[i + 1:]:
                        gap = math.dist((a.x(), a.y()), (b.x(), b.y()))
                        assert gap > QUAY_HIT, (
                            f"three quays at one body seat {gap:.1f} px "
                            f"apart, inside the {QUAY_HIT:.0f} px hit radius")
                stacked = len(crowd)
            finally:
                win.close()
        assert stacked, "the fan was neither found nor built"
        return (f"{checked} quays over {len(SEEDS)} seeds, each on its own "
                f"mark; {stacked} body carries more than one")

    return True
