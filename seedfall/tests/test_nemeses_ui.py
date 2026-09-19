"""The hunt, on the screens: the Hunts tab, the switch, the rings, the header.

Rendered on Qt's offscreen platform and pressed, not merely built. The Hunts
tab's numbers are read off the widgets and held against `sim/hunts` — a
button that said 16% while the search rolled something else would be the
defect the Law screen was written to refuse.
"""

from __future__ import annotations

from .qtkit import use_offscreen

use_offscreen()


def _scene(seed: str):
    """A chronicle at a quay with a rival seen here, one away, and paper."""
    from ..sim import hunts
    from ..sim import nemeses as nem_sim
    from . import nemesis_kit as kit
    game = kit.mid_game(seed)
    game.ship.cargo = {"ore": 20, "volatiles": 60}
    port = next(p for p in game.galaxy.systems if p.port is not None
                and any(r["kind"] == "raider" for r in hunts.board(game, p)))
    game.location_id = port.id
    here = kit.rival(game, "hunter", ["shielded"])
    nem_sim.spot(game, here, port.id, 0.8)
    away = kit.rival(game, "corsair", ["ghost"],
                     where=game.galaxy.systems[-1].id)
    away.bounty = {"reward": 6400, "issuer": "concordat"}
    nem_sim.spot(game, away, away.location_id, 1.0)
    game.recompute()
    return game, here, away


def run(suite) -> bool:
    from PyQt6.QtWidgets import QLabel, QPushButton

    from ..sim import hunts, rivals, running_dark
    from ..ui import theme
    from . import qtkit

    check = suite.check
    app = qtkit.app()
    app.setStyleSheet(theme.stylesheet())

    def texts(widget, kind=QLabel) -> list:
        return [w.text() for w in widget.findChildren(kind)]

    @check("the Hunts tab shows dossiers, the board and the search, at both "
           "sizes, and its odds are the search's")
    def _():
        said = []
        for size in ((1040, 680), (1360, 880)):
            game, here, away = _scene(f"ui-hunts-{size[0]}")
            win = qtkit.main_window(game, size)
            win.show()
            win.go("law")
            view = win.views["law"]
            tabs = [b for b in view.findChildren(QPushButton)
                    if b.text() == "Hunts"]
            assert tabs, "no Hunts tab on the Law screen"
            tabs[0].click()
            for _ in range(3):
                app.processEvents()
            labels = texts(view)
            assert here.name in labels and away.name in labels, labels[:12]
            buttons = texts(view, QPushButton)
            quote = hunts.search_odds(game, f"nemesis:{here.id}", 3)
            want = f"Search — {quote['odds']:.0%}"
            assert want in buttons, (want, [b for b in buttons
                                            if b.startswith("Search")])
            assert "Take the paper" in buttons, buttons
            wide = view.widget().minimumSizeHint().width()
            assert wide <= view.viewport().width() + 2, (
                f"the tab wants {wide}px of a {view.viewport().width()}px "
                "column")
            said.append(f"{size[0]}×{size[1]}: {want}")
            win.close()
        assert len(said) == 2
        return "; ".join(said)

    @check("the heading bar's chip and the Ship screen's row both flip it")
    def _():
        game, _here, _away = _scene("ui-dark")
        win = qtkit.main_window(game)
        win.show()
        assert win.dark_chip.text() == "LIT"
        assert "fewer meetings" in win.dark_chip.toolTip()
        win.dark_chip.click()
        app.processEvents()
        assert running_dark.dark(game) and win.dark_chip.text() == "DARK"
        win.go("ship")
        row = [b for b in win.views["ship"].findChildren(QPushButton)
               if b.text() == "Light her up"]
        assert row, "no transponder row on the Ship screen"
        row[0].click()
        app.processEvents()
        assert not running_dark.dark(game)
        assert win.dark_chip.text() == "LIT"
        assert any("Transponder on" in line[1] for line in game.log[-3:])
        win.close()
        return "chip LIT → DARK, the Ship screen's row back to LIT, logged"

    @check("the chart rings where a rival was last seen, fading with age")
    def _():
        from PyQt6.QtGui import QImage
        game, _here, away = _scene("ui-rings")
        win = qtkit.main_window(game)
        win.show()
        win.go("map")
        chart = win.views["map"].chart
        for _ in range(3):
            app.processEvents()

        def lit() -> int:
            """Ring-red pixels in the annulus the ring is drawn on."""
            image = chart.grab().toImage().convertToFormat(
                QImage.Format.Format_RGB32)
            at = chart._to_screen(game.galaxy.systems[away.location_id])
            count = 0
            for dx in range(-16, 17):
                for dy in range(-16, 17):
                    if not 9 <= (dx * dx + dy * dy) ** 0.5 <= 14:
                        continue
                    x, y = int(at.x()) + dx, int(at.y()) + dy
                    if 0 <= x < image.width() and 0 <= y < image.height():
                        c = image.pixelColor(x, y)
                        count += c.red() > c.green() + 40
            return count

        fresh = lit()
        away.last_seen = []
        gone = lit()
        assert fresh > gone + 10, (fresh, gone)
        win.close()
        return f"{fresh} red pixels round the sighting, {gone} without it"

    @check("an engagement with a rival names the meeting in its heading")
    def _():
        game, here, _away = _scene("ui-battle")
        here.history.append([game.day - 30, game.location_id, "driven-off",
                             "You drove them off"])
        win = qtkit.main_window(game)
        win.show()
        win.begin_combat(rivals.encounter(game, here), "law")
        app.processEvents()
        labels = texts(win.views["battle"])
        header = [t for t in labels if "Second meeting" in t]
        assert header, [t for t in labels if "meeting" in t]
        assert "drove her off" in header[0], header[0]
        win.battle = None
        win.close()
        return header[0]

    return True                 # an optional suite that ran says so
