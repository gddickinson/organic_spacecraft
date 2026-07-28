"""Render every major screen offscreen, for the README.

Run with ``python -m seedfall.tests.capture [outdir]``. Builds one developed
chronicle so the screens have something in them — a charted sector, colonies,
contracts, a programme under way, a party on the ground — and grabs each view
at a consistent size.
"""

from __future__ import annotations

import pathlib
import sys

from ..core.rng import RNG
from ..core.state import new_game
from ..data.tech import TECH
from ..data.xenotech import XENOTECH
from ..sim import charts as chart_sim
from ..sim import colony as colony_sim
from ..sim import contracts as contract_sim
from ..sim import dig as dig_sim
from ..sim import diplomacy as dip_sim
from ..sim import encounters
from ..sim import expedition as exp_sim
from ..sim import inquiry
from ..sim import market as market_sim
from ..sim import research as research_sim
from ..sim.ship import build_layers, make_ship

SIZE = (1560, 1000)


def _developed(seed: str = "seedfall"):
    """A chronicle a few years in, with something on every screen."""
    game = new_game(seed)
    game.credits = 480_000
    game.day = 900

    ship = make_ship("navis", ["slug_battery", "mag_lance", "carapace",
                               "reaction_organ", "opsin_eyes", "chemo_gut",
                               "seed_bay", "mining_root", "cargo_villi",
                               "radiator_bloom", "silicon_core"],
                     "Patient Increment")
    build_layers(ship, game.bonuses)
    game.ship = ship
    for tech in ("bioleach", "melanin", "oect", "intima", "xenobiology",
                 "monocoque", "aicore"):
        if tech not in game.research.unlocked:
            game.research.unlocked.append(tech)
    game.recompute()

    ship.cargo = {"ore": 62, "volatiles": 48, "biomass": 30, "survey": 6,
                  "xenolith": 2}
    for key in ("alloy", "ore", "biomass", "volatiles", "phosphate"):
        game.stores[key] = 2400

    # A sector somebody has actually flown: half of it charted and noted.
    for index, system in enumerate(game.galaxy.systems):
        if index % 2 == 0:
            system.visited = True
            for body in system.bodies:
                body.surveyed = True
            system.scanned = True
            chart_sim.stamp(game, system)
            if system.market:
                market_sim.note_prices(game, system, 0, 0)
    for body in game.system.bodies:
        body.surveyed = True

    # A programme under way, with evidence on the shelves.
    for kind in ("survey", "specimen", "hardware", "reading"):
        inquiry.add(game.research, kind, 260)
    project = next(t for t in research_sim.researchable(game.research.unlocked))
    research_sim.set_project(game.research, project.id)
    inquiry.set_approach(game.research, "parallel")
    game.research.progress = project.cost * 0.4

    # Standing worth having, and a sector whose politics have moved.
    game.rep.update({"charter": 62, "concordat": 34, "freeholds": 48,
                     "sanhedrin": 21})
    dip_sim.shift_relation(game, "charter", "freeholds", 30)
    dip_sim.shift_relation(game, "concordat", "freeholds", -18)

    # Work in hand.
    port = next(s for s in game.galaxy.systems if s.port)
    for contract in contract_sim.generate(RNG("board"), game, port)[:3]:
        contract_sim.accept(game, contract)

    # Something planted and grown.
    site = next((b for b in game.system.bodies
                 if b.kind in ("rocky", "moon", "asteroid")), None)
    if site is not None:
        colony, _why = colony_sim.found(game, game.system, site, "radix_mine")
        if colony:
            colony.online = True
            colony.days = colony.need
            colony.pop = colony.definition.pop
    return game


def _shot(app, win, view_id: str, out: pathlib.Path, name: str,
          setup=None) -> None:
    if setup:
        setup(win)
    win.go(view_id)
    for _ in range(5):
        app.processEvents()
    win.grab().save(str(out / f"{name}.png"))
    print(f"  {name}.png")


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    out = pathlib.Path(argv[0] if argv else "assets/seedfall")
    out.mkdir(parents=True, exist_ok=True)

    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication

    from ..ui import theme
    from ..ui.window import MainWindow

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    game = _developed()
    win = MainWindow(game)
    win.resize(*SIZE)
    win.dialog = lambda *a, **k: None
    win.confirm = lambda *a, **k: True
    win.toast = lambda *a, **k: None
    win.show()
    print("rendering:")

    _shot(app, win, "map", out, "01-sector")
    _shot(app, win, "system", out, "02-system")
    _shot(app, win, "helm", out, "03-helm")

    def port_market(w):
        w.views["port"].tab = "market"
    _shot(app, win, "port", out, "04-port", port_market)

    def port_contracts(w):
        w.views["port"].tab = "contracts"
    _shot(app, win, "port", out, "05-contracts", port_contracts)

    _shot(app, win, "diplomacy", out, "06-diplomacy")
    _shot(app, win, "tech", out, "07-research")
    _shot(app, win, "empire", out, "08-holdings")

    def yard(w):
        w.views["yard"].tab = "build"
    _shot(app, win, "yard", out, "09-shipyard", yard)

    def start_battle(w):
        w.views["battle"].begin(
            {"enemy": encounters.make_enemy(RNG("shot"), "concordat", 1.6),
             "intro": "A Yards hull lights you up and does not answer the hail."})
    _shot(app, win, "battle", out, "10-battle", start_battle)
    win.battle = None

    def land(w):
        body = next(b for b in w.game.system.bodies
                    if b.kind not in ("gas", "star"))
        party = exp_sim.generate(RNG("land"), w.game.system, body,
                                 [o.id for o in w.game.officers], 40)
        party.here.feature = "wreck"
        party.here.resolved = False
        for tile in party.tiles[:22]:
            tile.seen = True
        w.game.expedition = party
    _shot(app, win, "ground", out, "11-ground", land)
    game.expedition = None

    def trench(w):
        body = next((b for b in w.game.system.bodies if b.relic),
                    w.game.system.bodies[0])
        body.relic = body.relic or XENOTECH[0].id
        body.relic_found = True
        started = dig_sim.begin(w.game, w.game.system.bodies.index(body))
        if started.get("ok"):
            w.game.dig = started["dig"]
            dig_sim.work(w.game, w.game.dig, "careful", RNG("trench"))
    _shot(app, win, "dig", out, "12-dig", trench)
    game.dig = None

    def bench(w):
        from ..sim import minigames as mg
        w.views["docking"].begin("Fleet Hub")
        d = w.game.docking
        mg.correct(d, mg.AXES[0][0], 18, RNG("dock"))
    _shot(app, win, "docking", out, "13-docking", bench)
    game.docking = None

    def notes(w):
        from ..sim import notes as notes_sim
        for note_id in ("breach", "manifest", "emission", "vent"):
            notes_sim.file(w.game, note_id, "Solace Span I", "Solace Span")
        w.views["codex"].tab = "notes"
    _shot(app, win, "codex", out, "14-codex", notes)

    win.close()
    print(f"\n{len(list(out.glob('*.png')))} screens in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
