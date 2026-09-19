"""The sky, on the screens: the Sky strip, the chart's rings, the shelter mark.

Rendered on Qt's offscreen platform and pressed, not merely built. The
strip's Observe states days and evidence, and the press is held to them; the
chart is painted with and without its overlay and the pixels compared; the
Pilot's board and the Helm say whether the crew is out of a flare, and the
Helm's shadow button puts it there. Building every screen changes nothing in
the save — viewing never changes the sky.
"""

from __future__ import annotations

import json

from .qtkit import use_offscreen

use_offscreen()


def _encoded(game) -> str:
    """The save, less the two states the chart's own painting makes on first
    sight (`weave.ensure`, the hostiles' ledger) — older than the sky, and
    not what this suite is asking about."""
    from ..core import save as save_mod
    raw = save_mod.encode({"game": game})["game"]
    for lazy in ("weave", "hostiles_state"):
        raw.pop(lazy, None)
    return json.dumps(raw, sort_keys=True, default=str)


def run(suite) -> bool:
    from PyQt6.QtWidgets import QLabel, QPushButton

    from ..sim import inquiry
    from ..sim import phenomena as sky_sim
    from ..sim import phenomena_science as science
    from ..ui import audio, sky_chart, theme
    from ..ui.star_chart import StarChart
    from . import phenomena_kit as kit
    from . import qtkit
    from .test_audio import Recorder

    check = suite.check
    app = qtkit.app()
    app.setStyleSheet(theme.stylesheet())

    def texts(widget, kind=QLabel) -> list:
        return [w.text() for w in widget.findChildren(kind)]

    def press(widget, start: str) -> None:
        hit = [b for b in widget.findChildren(QPushButton)
               if b.text().startswith(start) and b.isEnabled()]
        assert hit, (start, texts(widget, QPushButton))
        hit[0].click()

    @check("the Sky strip says what is live, and Observe is its preview, "
           "at both sizes")
    def _():
        said = []
        for size in ((1040, 680), (1360, 880)):
            game, comet = kit.find(f"ui-sky-{size[0]}", "comet")
            kit.at(game, comet, 1)
            win = qtkit.main_window(game, size)
            win.show()
            win.go("system")
            view = win.views["system"]
            shown = " ".join(texts(view))
            assert "The sky" in shown and "Comet passage" in shown, shown
            quote = science.observe_quote(game)
            day, held = game.day, inquiry.held(game.research, "phenomena")
            press(view, "Observe")
            assert game.day - day == quote["days"]
            assert abs(inquiry.held(game.research, "phenomena") - held
                       - quote["evidence"]) < 1e-9
            said.append(f"{size[0]}: {quote['days']} d, "
                        f"{quote['evidence']:g} evidence")
            win.close()
        assert len(said) == 2
        return "; ".join(said)

    @check("the chart rings what is live and forecast, and viewing changes "
           "nothing")
    def _():
        game, comet = kit.find("ui-sky-chart", "comet")
        kit.at(game, comet, 1)
        game.advance_days(20)
        win = qtkit.main_window(game, (1360, 880))
        win.show()
        before = _encoded(game)
        for screen in ("system", "helm", "despatches", "codex", "map"):
            win.go(screen)
        chart = win.views["map"].chart
        assert isinstance(chart, StarChart)
        marked = [e for e, how in sky_sim.visible(game)]
        assert marked, "nothing on the chart to ring"
        live = chart.grab().toImage()
        real = sky_chart.draw
        sky_chart.draw = lambda *a, **k: None
        try:
            chart.repaint()
            bare = chart.grab().toImage()
        finally:
            sky_chart.draw = real
        moved = sum(1 for x in range(0, live.width(), 3)
                    for y in range(0, live.height(), 3)
                    if live.pixel(x, y) != bare.pixel(x, y))
        assert moved > 40, moved
        assert _encoded(game) == before, "looking at the sky changed it"
        win.close()
        return (f"{len(marked)} phenomena marked, {moved} sampled pixels "
                "drawn by the overlay; five screens built, save unchanged")

    @check("the Pilot and the Helm say whether the crew is out of a flare, "
           "and the Helm can put it in a shadow")
    def _():
        game, flare = kit.find("ui-sky-flare", "flare",
                               lambda g, e: e.end - e.start >= 2
                               and len(g.galaxy.systems[e.system_id].bodies))
        kit.at(game, flare)
        game.ship.cargo["volatiles"] = 60
        from ..sim import flight
        flight.hold_at(game, game.system.bodies[-1])
        win = qtkit.main_window(game, (1360, 880))
        win.show()
        win.go("helm")
        helm = win.views["helm"]
        assert "Hard light on this system" in " ".join(texts(helm))
        press(helm, "Keep to the shadow")
        assert game.sky.lee == game.orbit_body and sky_sim.dose(game) == 0.0
        win.go("pilot")
        pilot = " ".join(texts(win.views["pilot"]))
        win.close()
        assert "sheltered" in pilot, pilot
        return "helm panel shown, shadow taken by its button; pilot says sheltered"

    @check("a forecast is a despatch, the codex lists what was watched, and "
           "a flare and the nova are heard once each")
    def _():
        ear = Recorder()
        audio.install(ear)
        try:
            game, flare = kit.find("ui-sky-sound", "flare",
                                   lambda g, e: e.end - e.start >= 2)
            kit.put(game, flare.system_id)
            kit.on_day(game, max(1, flare.start - 30))
            win = qtkit.main_window(game, (1360, 880))
            game.advance_days(flare.start - game.day)
            if science.observe_quote(game)["ok"]:
                science.observe(game)
            mark = len(ear.heard)
            win.refresh()
            win.refresh()
            flares = ear.played(mark).count("flare")
            win.go("despatches")
            board = " ".join(texts(win.views["despatches"]))
            win.go("codex")
            codex = win.views["codex"]
            codex._switch("sky")
            shown = " ".join(texts(codex))
            kit.open_cradle(game)
            game.advance_days(1)
            game.day = game.sky.nova.begins - 1
            game.advance_days(1)
            mark = len(ear.heard)
            win.refresh()
            novas = ear.played(mark).count("nova")
            win.close()
        finally:
            audio.install(None)
        assert flares == 1, ear.heard[-6:]
        assert novas == 1, ear.heard[-6:]
        assert "Forecast" in board, board[:300]
        assert "Observed phenomena" in shown and "Stellar flare" in shown
        return "flare heard once, nova once; forecasts on the board; codex lists"

    return True
