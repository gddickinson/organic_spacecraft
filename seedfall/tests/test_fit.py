"""The screens fit the window, and a click costs what it changes.

Review item #21 measured eleven of fifteen screens wider than their column at
the enforced minimum of 1040×680, with horizontal scrolling switched off — all
thirteen of the Port's Sell buttons were past the right edge. #22 found every
one of the battle's twenty orders below the fold at every size up to
1560×1000, and #23 found the ship's log rebuilding sixty entries on every
refresh when nothing had been logged. Each of those is pinned here on a
*shown* window, because a layout is only measured once Qt has laid it out.
"""

from __future__ import annotations

from .test_ui import _use_offscreen

_use_offscreen()


def _shown(app, win, w: int, h: int) -> None:
    win.resize(w, h)
    for _ in range(6):
        app.processEvents()


def run(suite) -> bool:
    try:
        from PyQt6.QtCore import QPoint
        from PyQt6.QtWidgets import (QApplication, QLabel, QPushButton,
                                     QWidget)
    except ImportError as err:
        print(f"── fit ───\n  skipped: PyQt6 not available ({err})\n")
        return False

    from ..core.rng import RNG
    from ..core.state import new_game
    from ..data.screens import SCREENS
    from ..sim import encounters
    from ..ui import theme
    from ..ui.window import MainWindow

    check = suite.check
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    game = new_game("fit-seed")
    port_sys = next(s for s in game.galaxy.systems if s.port)
    game.location_id = port_sys.id
    game.ship.cargo["volatiles"] = 20       # a live Sell button on the board
    game.recompute()
    win = MainWindow(game)
    win.dialog = lambda *a, **k: None
    win.confirm = lambda *a, **k: False
    win.toast = lambda *a, **k: None
    win.show()

    @check("at 1040×680 no screen is wider than its column, and no button "
           "sits past the right edge")
    def _():
        _shown(app, win, 1040, 680)
        over = []
        for sid, _label, _key in SCREENS:
            if sid not in win.views:
                continue
            win.go(sid)
            for _ in range(4):
                app.processEvents()
            view = win.views[sid]
            inner, port = view.widget(), view.viewport()
            if inner.width() > port.width() + 1:
                over.append(f"{sid} +{inner.width() - port.width()}px")
            for b in inner.findChildren(QPushButton):
                if not b.isVisibleTo(inner):
                    continue
                right = b.mapTo(inner, QPoint(0, 0)).x() + b.width()
                if right > port.width() + 1:
                    over.append(f"{sid}: {b.text()!r} ends at {right}px of "
                                f"{port.width()}")
        assert not over, over[:8]
        return f"{len(SCREENS)} screens, every button inside its column"

    @check("on a screen's first frame no wrapped line is shorter than its text")
    def _():
        # The column was sized before its wrapped labels knew their width,
        # so a two-line despatch drew one line tall until the loop came round
        # again — caught in a screenshot, which is one frame (2026-09-18).
        from ..sim import comms
        body = ("The GESTALT Charter has moved you from Cool to Warm. They "
                "will say so where it counts, and the harbourmasters will "
                "hear it before you do.")
        for n in range(2):
            comms.send(game, "charter", "The Charter", "news", f"Word {n}",
                       body, aboard=True)
        _shown(app, win, 1040, 680)
        cut = []
        for sid, _label, _key in SCREENS:
            if sid not in win.views:
                continue
            win.go(sid)
            app.processEvents()                  # one pass: the first frame
            inner = win.views[sid].widget()
            cut += [f"{sid}: {lab.text()[:28]!r} {lab.height()} of "
                    f"{lab.heightForWidth(lab.width())}px"
                    for lab in inner.findChildren(QLabel)
                    if lab.isVisibleTo(inner) and lab.wordWrap()
                    and lab.width() > 0
                    and lab.heightForWidth(lab.width()) > lab.height() + 1]
        assert not cut, cut[:6]
        return f"{len(SCREENS)} screens whole on the first frame"

    @check("a star picked from the list leaves the chart its own height")
    def _():
        # Beside the picked star's long panel, the chart was stretched to
        # 437×1,461 and drew its stars in the middle, off the screen — the
        # visible part was black (play-test, 2026-09-18).
        from PyQt6.QtWidgets import QListWidget
        _shown(app, win, 1360, 880)
        win.go("map")
        _shown(app, win, 1360, 880)
        view = win.views["map"]
        box = view.findChild(QListWidget, "destinations")
        box.itemClicked.emit(box.item(min(5, box.count() - 1)))
        _shown(app, win, 1360, 880)
        chart = view.chart
        tall = chart.heightForWidth(chart.width())
        assert chart.height() <= tall + 1, (
            f"chart {chart.width()}×{chart.height()}, its frame wants {tall}")
        return f"chart {chart.width()}×{chart.height()} after a pick"

    @check("picking a body on the Helm keeps the burn board beside the chart")
    def _():
        # Four burn tabs on one line and the crossing rows unwrapped asked
        # 455 px, and the board fell under the left column, 2,000 px down
        # (play-test, 2026-09-18).
        from ..ui.view_base import WrapRow
        from . import qtkit
        many = new_game("fp-alpha")              # five bodies at the start
        helm = qtkit.main_window(many, (1360, 880))
        helm.show()
        helm.go("helm")
        view = helm.views["helm"]
        widest = 0
        for index in range(len(many.system.bodies)):
            view._pick(index)
            view.refresh()
            _shown(app, helm, 1360, 880)
            row = view.widget().findChildren(WrapRow)[0]
            assert row.across(), (
                f"body {index}: stacked, needs {row.need()} of {row.width()}")
            widest = max(widest, row.need())
        helm.close()
        assert len(many.system.bodies) > 2, "a system with nothing to pick"
        return (f"{len(many.system.bodies)} bodies picked, side by side; "
                f"widest {widest} of {row.width()} px")

    @check("the battle's orders are in view without scrolling at the default "
           "size, and pinned at the minimum")
    def _():
        enemy = encounters.make_enemy(RNG("fit-battle"), "freeholds", 2)
        win.begin_combat({"enemy": enemy, "intro": "fit"}, "system")
        view = win.views["battle"]
        view._act({"type": "brace"})
        told = []
        for w, h in ((1360, 880), (1040, 680)):
            _shown(app, win, w, h)
            orders = view.findChild(QWidget, "battle_orders")
            assert orders is not None, "no orders pane"
            acts = [b for b in orders.findChildren(QPushButton) if b.isVisible()]
            seen = [b for b in acts
                    if b.visibleRegion().boundingRect() == b.rect()]
            assert view.verticalScrollBar().maximum() == 0, (
                f"at {w}×{h} the battle screen itself scrolls "
                f"{view.verticalScrollBar().maximum()} px — the orders are "
                "not pinned")
            if (w, h) == (1360, 880):
                assert len(seen) == len(acts), (
                    f"{len(acts) - len(seen)} of {len(acts)} orders are out of "
                    "view at the default size")
            told.append(f"{w}×{h}: {len(seen)}/{len(acts)} in view")
        win.battle = None
        win.go("map")
        return "; ".join(told)

    @check("the heading bar fits the minimum window and its captions do not "
           "overprint")
    def _():
        _shown(app, win, 1040, 680)
        need = win.hud.minimumSizeHint().width()
        assert need <= 1040, f"the heading bar needs {need}px at 1040"
        caps = [cap for cap, _bar in win.meters.values()]
        boxes = [c.geometry().translated(c.parentWidget().mapTo(win.hud,
                                                                QPoint(0, 0)))
                 for c in caps]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                assert not a.intersects(b), "two meter captions overlap"
        hull = win.hud_stats["hull"]
        assert game.ship.name in hull.full() and hull.toolTip() == hull.full()
        return f"needs {need}px; the ship's name is whole on its tooltip"

    @check("the log folds below the line and opens above it, and the player "
           "can open it anyway")
    def _():
        from ..ui import log_panel
        _shown(app, win, 1040, 680)
        assert win.log_folded and win.log_panel.width() == log_panel.FOLDED
        log_panel.toggle(win)
        app.processEvents()
        assert not win.log_folded, "the fold button did not open it"
        _shown(app, win, 1360, 880)
        assert not win.log_folded and win.log_panel.width() == log_panel.WIDE
        _shown(app, win, 1040, 680)
        assert win.log_folded, "crossing the line again did not fold it"
        _shown(app, win, 1360, 880)
        return f"folds under {log_panel.FOLD_BELOW}px, to {log_panel.FOLDED}px"

    @check("a refresh with nothing logged draws nothing, and new entries are "
           "added at the top")
    def _():
        from ..ui import log_panel
        win.refresh()
        top = win.log_col.itemAt(0).widget()
        count = win.log_col.count()
        win.refresh()
        assert win.log_col.itemAt(0).widget() is top, (
            "an unchanged log was rebuilt")
        for n in range(3):
            game.add_log(f"fit entry {n}", "good" if n else "bad")
        win.refresh()
        assert win.log_col.count() == min(log_panel.SHOWN, count + 3)
        newest = win.log_col.itemAt(0).widget()
        said = " ".join(lb.text() for lb in newest.findChildren(QLabel))
        assert "fit entry 2" in said and said.count("✓") == 1, said
        oldest_new = win.log_col.itemAt(2).widget()
        said = " ".join(lb.text() for lb in oldest_new.findChildren(QLabel))
        assert "✕ fit entry 0" in said, said
        return f"{count} → {win.log_col.count()} entries, glyphs on good and bad"

    @check("the Research tree is changed in place, and what is known folds "
           "into one line")
    def _():
        from ..data.tech import TECH
        from ..sim import research as research_sim
        win.go("tech")
        view = win.views["tech"]
        view.branch = "all"
        view.refresh()
        tree = view._trees["all"]
        before = dict(tree._cards)
        assert tree.sync(game) == 0, "a refresh with nothing new made cards"
        win.refresh()
        assert all(tree._cards[k][1] is before[k][1] for k in before), (
            "a window refresh remade the cards")
        pick = next(t for t in TECH if research_sim.can_research(
            t.id, game.research.unlocked))
        game.research.unlocked.append(pick.id)
        try:
            win.refresh()
            assert pick.id not in tree._cards, "a known technology kept its card"
            assert pick.name in tree._known_text.text()
        finally:
            game.research.unlocked.remove(pick.id)
            win.refresh()
        win.go("map")
        return f"{len(before)} cards kept; {pick.name} folded into the known line"

    @check("a purchase changes the board in place and keeps the quantity typed")
    def _():
        from PyQt6.QtWidgets import QSpinBox
        game.credits = 100_000
        view = win.views["port"]
        view.tab = "market"
        win.go("port")
        app.processEvents()
        spin = view.findChild(QSpinBox, "qty_volatiles")
        buy = view.findChild(QPushButton, "buy_volatiles")
        assert spin is not None and buy is not None
        spin.setValue(25)
        had = game.ship.cargo.get("volatiles", 0)
        buy.click()
        app.processEvents()
        assert game.ship.cargo.get("volatiles", 0) == had + 25
        assert view.findChild(QSpinBox, "qty_volatiles") is spin
        assert spin.value() == 25, f"the quantity went back to {spin.value()}"
        win.go("map")
        return "bought 25 t; the same board, still reading 25"

    @check("rows of panels and lines of buttons wrap when the width is short")
    def _():
        from ..ui.flow import Flow
        from ..ui.view_base import WrapRow
        from ..ui.widgets import button
        # Inside a host, as on a screen: a top-level row would be held at
        # its layout's minimum by Qt, which is not the case being checked.
        host = QWidget()
        host.resize(800, 300)
        row = WrapRow()
        row.setParent(host)
        for _ in range(2):
            box = QWidget()
            box.setMinimumWidth(300)
            row.add(box)
        host.show()
        row.resize(500, 100)
        app.processEvents()
        assert not row.across(), "600 px of panels did not stack in 500"
        row.resize(700, 100)
        app.processEvents()
        assert row.across(), "600 px of panels did not sit side by side in 700"
        host.hide()
        line = Flow([button(f"Order number {n}") for n in range(6)])
        line.setParent(host)
        host.resize(2100, 300)
        host.show()
        line.resize(260, 200)
        app.processEvents()
        narrow = line.per_line()
        line.resize(2000, 200)
        app.processEvents()
        assert len(narrow) > 1 and line.per_line() == [6], (narrow,
                                                           line.per_line())
        host.hide()
        return f"stacked under {row.need()}px; six buttons on {len(narrow)} lines"

    @check("star names on the chart never print over each other")
    def _():
        from ..ui.star_chart import StarChart
        # Every star known, so the chart has a sector's worth of names to
        # keep apart — at day 0 it names two, and two cannot crowd.
        for s in win.game.galaxy.systems:
            s.visited = s.scanned = True
        win.go("map")
        win.refresh()
        _shown(app, win, 1040, 680)
        chart = win.views["map"].findChild(StarChart)
        chart.grab()
        placed = chart.placed
        assert len(placed) >= 20, f"only {len(placed)} names placed — nothing to compare"
        for i, (_a, ra) in enumerate(placed):
            for _b, rb in placed[i + 1:]:
                assert not ra.intersects(rb), "two star names overlap"
        _shown(app, win, 1360, 880)
        return f"{len(placed)} names placed at 1040×680, none overlapping"

    @check("a flat button is not drawn like a disabled one")
    def _():
        from ..ui.widgets import button
        flat = button("Brace", kind="flat")
        off = button("Brace", kind="flat", enabled=False)
        for b in (flat, off):
            b.setStyleSheet("")
            b.resize(120, 30)
        a, b = flat.grab().toImage(), off.grab().toImage()
        differ = sum(1 for x in range(0, 120, 2) for y in range(0, 30, 2)
                     if a.pixelColor(x, y) != b.pixelColor(x, y))
        assert differ > 20, f"only {differ} sampled pixels differ"
        return f"{differ} of 900 sampled pixels differ"

    win.close()
    win.deleteLater()
    app.processEvents()
    return True
