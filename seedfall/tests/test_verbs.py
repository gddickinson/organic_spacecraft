"""Every verb in the game, driven once.

Splitting `combat.py` when it crossed five hundred lines left fleeing and
hailing calling names that no longer existed. Nothing noticed: `test_ui.py`
renders every screen, and rendering a screen does not press its buttons.

The trap that made it invisible is worth stating plainly, because it defeats
the obvious version of this check: **Qt swallows exceptions raised inside a
slot**. It prints a traceback to stderr and carries on, so `button.click()`
returns perfectly happily and a naive test sees nothing wrong. Catching them
needs `sys.excepthook`.

Each control is clicked on a *fresh* game, because clicking one can end the
engagement, spend the money or fly the ship somewhere the next one needs.
"""

from __future__ import annotations

import sys

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import encounters
from ..sim import minigames
from ..sim import customs as customs_sim
from ..sim import dig as dig_sim
from ..sim import expedition as expedition_sim
from ..sim import ventures as venture_sim
from ..sim.ship import build_layers, make_ship
from .harness import Suite


class _Trap:
    """Collects what Qt would otherwise print and forget."""

    def __init__(self):
        self.caught: list[tuple[str, str]] = []
        self._previous = None

    def __enter__(self):
        self._previous = sys.excepthook
        sys.excepthook = self._hook
        return self

    def __exit__(self, *_exc):
        sys.excepthook = self._previous
        return False

    def _hook(self, kind, value, _tb):
        self.caught.append((kind.__name__, str(value)[:120]))


def _wrecked(seed: str):
    """A hull with nothing left: no money, no crew, no air, no stores.

    Controls stay enabled in states their handlers were never written for, and
    a broken ship is where a missing guard actually bites.
    """
    game = new_game(seed)
    game.credits = 0
    game.ship.cargo = {}
    game.stores = {}
    game.officers = []
    game.ship.o2 = 0.05
    game.ship.crew = 1
    for layer in game.ship.layers[:-1]:
        layer.hp = 0
    game.recompute()
    return game


def _stocked(seed: str):
    """A game with the money, standing and hardware to enable most controls."""
    game = new_game(seed)
    game.credits = 900000
    game.ship.fitted.append("seed_bay")
    for tech in ("bioleach", "melanin", "oect", "intima", "xenobiology"):
        game.research.unlocked.append(tech)
    game.recompute()
    for key in ("alloy", "ore", "biomass", "volatiles", "phosphate"):
        game.stores[key] = 9000
    game.ship.cargo = {"ore": 60, "volatiles": 40}
    for body in game.system.bodies:
        body.surveyed = True
    for power in ("charter", "concordat", "freeholds", "sanhedrin"):
        game.rep[power] = 70
    escort = make_ship("vesper", ["mag_lance", "reaction_organ", "opsin_eyes"],
                       "Kestrel")
    build_layers(escort, game.bonuses)
    game.fleet.append(escort)
    venture_sim.start(game, RNG(f"v-{seed}"), "charter")
    return game


def _dirty(seed: str):
    """Stocked, and parked on a dock that will seize what is in the hold.

    The quiet word and the vent control only exist in this state, so the
    ordinary port sweep never touches either of them.
    """
    game = _stocked(seed)
    dest = next((s for s in game.galaxy.systems if s.port
                 and customs_sim.outlaws(s.port.faction, "wildseed")), None)
    if dest is not None:
        game.location_id = dest.id
    game.ship.cargo["wildseed"] = 24
    return game


def run(suite: Suite) -> bool:
    try:
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QPushButton
    except ImportError as err:      # pragma: no cover - no Qt, no verbs
        print(f"── verbs ───\n  skipped: {err}\n")
        return False

    from ..ui import theme
    from ..ui.window import MainWindow, NAV

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())
    check = suite.check

    def window(seed: str, screen: str, tab: str | None = None,
               state=None):
        game = (state or _stocked)(seed)
        win = MainWindow(game)
        win.resize(1500, 1000)
        win.dialog = lambda *a, **k: None
        win.confirm = lambda *a, **k: True
        win.toast = lambda *a, **k: None
        win.show()
        if screen == "battle":
            win.views["battle"].begin(
                {"enemy": encounters.make_enemy(RNG(f"e-{seed}"), "freeholds", 1.0),
                 "intro": "A hull lights you up."})
        elif screen == "ground":
            body = next(b for b in game.system.bodies
                        if b.kind not in ("gas", "star"))
            game.expedition = expedition_sim.generate(
                RNG(f"x-{seed}"), game.system, body,
                [o.id for o in game.officers], 40)
        elif screen == "docking":
            win.docking = minigames.start_docking(
                game.rng("dock"), "Fleet Hub", game.ship_stats, game.officers)
        elif screen == "decoding":
            win.decoding = minigames.start_decoding(
                game.rng("decode"), "a xenolith", game.ship_stats, game.officers)
        elif screen == "demand":
            from ..sim import territory as territory_sim
            system = game.system
            system.faction = None
            system.bloom = 0.0
            body = next(b for b in system.bodies
                        if b.kind in ("asteroid", "moon", "rocky"))
            game.credits = 2_000_000
            for key in ("alloy", "ore", "biomass", "volatiles", "phosphate"):
                game.stores[key] = 90000
            from ..sim import colony as colony_sim
            col, _why = colony_sim.found(game, system, body, "radix_mine")
            if col is not None:
                system.faction = "charter"
                game.demand = territory_sim.Demand(
                    system_id=system.id, power="charter",
                    worth=20000)
        elif screen == "dig":
            from ..data.xenotech import XENOTECH
            body = next((b for b in game.system.bodies if b.relic),
                        game.system.bodies[0])
            body.relic = body.relic or XENOTECH[0].id
            body.relic_found = True
            game.dig = dig_sim.begin(
                game, game.system.bodies.index(body))["dig"]
        if tab is not None:
            setattr(win.views[screen], "tab", tab)
        win.go(screen)
        for _ in range(3):
            app.processEvents()
        return game, win

    def controls(win, screen):
        return [b for b in win.views[screen].findChildren(QPushButton)
                if b.isEnabled() and b.text()]

    def drive(screen: str, tab: str | None = None,
              state=None) -> tuple[int, list]:
        """Click every enabled control on this screen, one per fresh game.

        Modal dialogs are neutralised for the duration. A control can kill the
        chronicle — a survey that flies a wrecked hull for seventeen days will
        — and an ending whose dialog returns nothing falls through to starting
        a new chronicle, which opens the *opening* dialog. That runs its own
        event loop and waits for an answer nobody is going to give: the suite
        stopped dead for ten minutes on one button. `interact.py` learned the
        same lesson from the shipyard's name prompt.
        """
        from PyQt6.QtWidgets import QDialog, QInputDialog
        held_exec, held_text = QDialog.exec, QInputDialog.getText
        QDialog.exec = lambda self, *a, **k: 0
        QInputDialog.getText = staticmethod(lambda *a, **k: ("Test Hull", True))
        try:
            return _drive(screen, tab, state)
        finally:
            QDialog.exec = held_exec
            QInputDialog.getText = held_text

    def _drive(screen: str, tab: str | None = None,
               state=None) -> tuple[int, list]:
        _game, win = window(f"{screen}-probe", screen, tab, state)
        labels = [b.text() for b in controls(win, screen)]
        win.close()

        broken = []
        for index, label in enumerate(labels):
            _g, w = window(f"{screen}-{index}", screen, tab, state)
            found = controls(w, screen)
            if index >= len(found):
                continue
            with _Trap() as trap:
                try:
                    found[index].click()
                    for _ in range(3):
                        app.processEvents()
                except Exception as err:      # noqa: BLE001 - reporting it
                    trap.caught.append((type(err).__name__, str(err)[:120]))
            for kind, message in trap.caught:
                where = f"{screen}/{tab}" if tab else screen
                broken.append(f"{where}/{label!r}: {kind} {message}")
            w.close()
        return len(labels), broken

    @check("every control on every standing screen runs")
    def _():
        total, broken = 0, []
        for screen, *_rest in NAV:
            count, bad = drive(screen)
            total += count
            broken.extend(bad)
        assert not broken, (f"{len(broken)} of {total} controls raised:\n      "
                            + "\n      ".join(broken[:6]))
        return f"{total} controls across {len(NAV)} screens, all clean"

    @check("every control in an engagement runs")
    def _():
        # Where the flee and hail regression lived. Disengaging and hailing are
        # only reachable with a battle in progress, so no amount of rendering
        # the standing screens would ever have touched them.
        total, broken = drive("battle")
        assert total >= 10, f"only {total} controls found in an engagement"
        assert not broken, ("controls that raised mid-engagement:\n      "
                            + "\n      ".join(broken[:6]))
        return f"{total} controls in an engagement, all clean"

    @check("every control on the ground runs")
    def _():
        total, broken = drive("ground")
        assert total >= 5, f"only {total} controls found on an expedition"
        assert not broken, ("controls that raised on the ground:\n      "
                            + "\n      ".join(broken[:6]))
        return f"{total} controls on an expedition, all clean"

    @check("every control on a dirty quay runs")
    def _():
        total, broken = drive("port", "market", state=_dirty)
        assert total >= 6, f"only {total} controls on a dirty quay"
        assert not broken, ("controls that raised with contraband aboard:\n      "
                            + "\n      ".join(broken[:6]))
        return f"{total} controls with a hold full of contraband, all clean"

    @check("every control answering a demand runs")
    def _():
        total, broken = drive("demand")
        assert total >= 3, f"only {total} controls on the demand screen"
        assert not broken, ("controls that raised answering a power:\n      "
                            + "\n      ".join(broken[:6]))
        return f"{total} controls answering a power, all clean"

    @check("every control in an open trench runs")
    def _():
        # A trench is only reachable with a dig on the game, so the standing
        # screens never touch it — the same blind spot the flee and hail
        # regression lived in.
        total, broken = drive("dig")
        assert total >= 4, f"only {total} controls found in a trench"
        assert not broken, ("controls that raised in the trench:\n      "
                            + "\n      ".join(broken[:6]))
        return f"{total} controls in a trench, all clean"

    @check("every control behind every port tab runs")
    def _():
        # Most of the game's verbs live at a port, and three of its four tabs
        # are only reachable by switching to them — rendering the screen shows
        # the market and nothing else.
        total, broken = 0, []
        for tab in ("market", "contracts", "services", "crew"):
            count, bad = drive("port", tab)
            total += count
            broken.extend(bad)
        assert total >= 40, f"only {total} controls found across the port tabs"
        assert not broken, ("controls that raised at a port:\n      "
                            + "\n      ".join(broken[:6]))
        return f"{total} controls across four port tabs, all clean"

    @check("both mini-games run from every control")
    def _():
        total, broken = 0, []
        for screen in ("docking", "decoding"):
            count, bad = drive(screen)
            total += count
            broken.extend(bad)
        assert total >= 15, f"only {total} controls across both mini-games"
        assert not broken, ("controls that raised in a mini-game:\n      "
                            + "\n      ".join(broken[:6]))
        return f"{total} controls across the approach and the bench, all clean"

    @check("every control still runs on a wrecked ship")
    def _():
        # No money, no crew, no air, a hull open to space. Controls stay
        # enabled in states their handlers were never written for.
        total, broken = 0, []
        for screen, *_rest in NAV:
            count, bad = drive(screen, state=_wrecked)
            total += count
            broken.extend(bad)
        assert total >= 40, f"only {total} controls enabled on a wreck"
        assert not broken, ("controls that raised on a wrecked ship:\n      "
                            + "\n      ".join(broken[:6]))
        return f"{total} controls with nothing left aboard, all clean"

    @check("a real drop-down click does not take the process with it")
    def _():
        """The player's crash, reproduced the way they found it.

        Every driver in this suite chooses from a combo with `setCurrentIndex`
        or by emitting `activated`. Neither opens a popup, and the crash lives
        entirely inside the popup's event filter — which is how five hundred
        checks missed a segfault a player hit by clicking a drop-down.

        `popup_probe` sends real mouse events to the popup's viewport. It runs
        as its own process because the failure is a signal, not an exception:
        asserted in-process it would not fail the check, it would kill the
        suite. Verified to exit 139 with the fix backed out.
        """
        import os
        import subprocess
        import sys

        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        done = subprocess.run(
            [sys.executable, "-m", "seedfall.tests.popup_probe"],
            capture_output=True, text=True, env=env, timeout=300,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))))
        # Qt's offscreen plugin chats to stderr about raise() and keyboard
        # grabbing; the probe's own verdict is on stdout.
        lines = [ln for ln in done.stdout.strip().splitlines()
                 if ln and "qt.qpa" not in ln and "plugin does not" not in ln]
        said = lines[-1] if lines else "(no output)"
        assert done.returncode == 0, (
            f"exit {done.returncode}"
            + " — a drop-down click segfaulted the process, exactly as the "
              "player reported" if done.returncode < 0 or done.returncode == 139
            else f"exit {done.returncode}: {said}")
        return said

    @check("a control survives its own signal")
    def _():
        """The rule `widgets.defer` exists for, tested where it actually bites.

        A player segfaulted the game choosing from a combo box. The handler
        called `refresh()`, which freed the combo while its own popup
        container was still delivering the mouse release that dismissed it —
        Qt then filtered an event on freed memory and the process died in
        `QComboBoxPrivateContainer::eventFilter`.

        524 checks missed it because the driver sets `currentIndex`
        programmatically, which never opens a popup and never takes that path.
        So test the invariant instead of the path: **after emitting its own
        signal, the widget must still exist.** With `defer` the rebuild
        happens on the next turn of the loop and it does; without, it is a
        corpse before the emit returns.
        """
        from PyQt6 import sip
        from PyQt6.QtWidgets import QComboBox

        checked, dead = 0, []
        for screen, *_rest in NAV:
            _game, probe = window(f"sig-{screen}", screen)
            count = len(probe.findChildren(QComboBox))
            probe.close()
            # A fresh window per combo. Collecting them once and firing each in
            # turn walked straight into the bug under test: the first deferred
            # rebuild frees every other combo in the list, and the next
            # `setCurrentIndex` is a use-after-delete in the *check*.
            for index in range(count):
                _g, win = window(f"sig-{screen}-{index}", screen)
                combos = win.findChildren(QComboBox)
                if index >= len(combos):
                    win.close()
                    continue
                combo = combos[index]
                if combo.count() < 2:
                    win.close()
                    continue
                combo.setCurrentIndex(1)
                combo.activated.emit(1)
                if sip.isdeleted(combo):
                    dead.append(f"{screen}: a combo was freed by its own "
                                "`activated` handler")
                checked += 1
                for _ in range(3):
                    app.processEvents()
                win.close()
        assert not dead, "\n      ".join(dead)
        assert checked > 0, "no combo boxes found on any screen to test"
        return f"{checked} combo boxes, every one alive after its own signal"

    @check("an exception inside a Qt slot is actually caught")
    def _():
        # The whole check rests on this. Qt prints a traceback for an exception
        # raised in a slot and carries on, so `click()` returns happily and a
        # naive test sees nothing. If this stops working, the checks above go
        # quietly green whatever is broken.
        from PyQt6.QtWidgets import QPushButton

        button = QPushButton("boom")

        def explode():
            raise RuntimeError("deliberate")

        button.clicked.connect(explode)
        with _Trap() as trap:
            button.click()
            for _ in range(3):
                app.processEvents()
        assert trap.caught, (
            "an exception raised inside a Qt slot went unnoticed — the trap "
            "is not working and the verb checks are worthless")
        kind, message = trap.caught[0]
        assert kind == "RuntimeError" and "deliberate" in message
        return f"trapped {kind} from inside a slot"

    # Controls that are not buttons live next door, driven with this suite's
    # offscreen app and fixtures. Split out when this file crossed 500 lines.
    from . import test_controls
    test_controls.run(suite, app, window, _stocked, NAV, _Trap)

    return True
