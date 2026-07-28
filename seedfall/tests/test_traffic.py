"""Other hulls: whether they are anywhere, stay themselves, and mean anything.

The helm plotted the star, the planets and the quays, and not one other ship,
because no other ship had a position. Encounters were rolled on arrival and
thrown away; ventures were a number in a ledger. The Verge looked empty in the
one view where it should look busiest.

Three claims, in rising order of what actually matters:

- **Traffic is somewhere.** Hulls have positions that move with the clock.
- **Traffic stays itself.** Derived state must not depend on the RNG or on a
  reload, or the hull you plotted yesterday is somebody else today.
- **Traffic means something.** A chart showing an unmarked hull loitering has
  to change what happens when you arrive, or it is decoration.
"""

from __future__ import annotations

import math

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import flight, traffic
from ..sim.encounters import roll_encounter
from .harness import Suite


def run(suite: Suite) -> None:
    check = suite.check

    @check("the sector is not empty, and the busy places are the busy ones")
    def _():
        game = new_game("busy")
        counts, ported, bare = {}, [], []
        for system in game.galaxy.systems:
            n = len(traffic.in_system(game, system))
            counts[system.id] = n
            (ported if system.port else bare).append(n)
        assert sum(counts.values()) > 0, "nothing is moving anywhere"
        busy = sum(ported) / max(1, len(ported))
        quiet = sum(bare) / max(1, len(bare))
        assert busy > quiet, (
            f"ports average {busy:.1f} hulls and empty systems {quiet:.1f}")
        return (f"{sum(counts.values())} hulls across {len(counts)} systems · "
                f"ports {busy:.1f} each, unclaimed {quiet:.1f}")

    @check("no two hulls in a system answer to the same name")
    def _():
        # The pools hold four or five names and a capital works five hulls, so
        # two turned up on the chart identically named — which makes "the hull
        # you plotted" meaningless exactly when it starts to matter.
        checked = 0
        for seed in ("dup-a", "dup-b", "dup-c"):
            game = new_game(seed)
            for system in game.galaxy.systems:
                names = [h.name for h in traffic.in_system(game, system)]
                assert len(names) == len(set(names)), (system.name, names)
                ids = [h.id for h in traffic.in_system(game, system)]
                assert len(ids) == len(set(ids)), ids
                checked += 1
        return f"{checked} systems, every hull distinctly named"

    @check("a hull keeps its name through time, luck and a reload")
    def _():
        # Traffic is derived rather than stored, which is what keeps it free
        # of migration. The price is that it must not touch `game.rng()` —
        # that advances with the save, so a reload would reshuffle the sector.
        import os
        import tempfile

        from ..core import save as save_mod
        from ..core.state import load_game

        game = new_game("same")
        first = {(h.id, h.name, h.errand, h.faction)
                 for h in traffic.in_system(game)}
        assert first, "nothing in the home system to keep track of"

        for _ in range(4):
            game.advance_days(23)
            game.rng("noise").int(0, 999)
            again = {(h.id, h.name, h.errand, h.faction)
                     for h in traffic.in_system(game)}
            assert again == first, "the traffic became different ships"

        os.environ["HOME"] = tempfile.mkdtemp()
        save_mod.write({"game": game})
        back = load_game()
        assert back is not None
        after = {(h.id, h.name, h.errand, h.faction)
                 for h in traffic.in_system(back)}
        assert after == first, (
            "a reload replaced the crews: "
            f"{sorted(n for _i, n, _e, _f in first)} became "
            f"{sorted(n for _i, n, _e, _f in after)}")
        return f"{len(first)} hulls unchanged over 92 days and a reload"

    @check("hulls are somewhere, and somewhere sensible")
    def _():
        game = new_game("where")
        moved = 0
        for system in game.galaxy.systems[:14]:
            span = max((flight.orbit_radius(b) for b in system.bodies),
                       default=1.0)
            for hull in traffic.in_system(game, system):
                x, y = traffic.position(game, hull, system)
                out = math.hypot(x, y)
                assert out <= span * 1.35 + 0.5, (
                    f"{hull.name} is {out:.1f} AU out in a {span:.1f} AU "
                    "system")
                assert 0.0 <= hull.along <= 1.0, hull.along
        # And they move. Scanned across the sector rather than only the home
        # system: the first version looked at one system whose hulls all held
        # station, measured nothing, and passed.
        watch = game.galaxy.systems[:14]
        before = {}
        for system in watch:
            for hull in traffic.in_system(game, system):
                if hull.from_body != hull.to_body:
                    before[hull.id] = traffic.position(game, hull, system)
        assert before, "not one hull in fourteen systems is on a run"
        game.advance_days(14)
        for system in watch:
            for hull in traffic.in_system(game, system):
                if hull.id in before:
                    was = before[hull.id]
                    now = traffic.position(game, hull, system)
                    if math.hypot(now[0] - was[0], now[1] - was[1]) > 0.01:
                        moved += 1
        assert moved > len(before) * 0.5, (
            f"only {moved} of {len(before)} hulls on a run moved in a "
            "fortnight")
        return (f"every hull inside its system; {moved} of {len(before)} on "
                "a run moved over a fortnight")

    @check("what is on the chart is what stops you")
    def _():
        # The whole point. If an unmarked hull loitering at the outer bodies
        # does not change what happens when you arrive, it is decoration —
        # and the patrol that jumps you gave no warning it could have given.
        game = new_game("meet")
        named = total = dark_seen = 0
        for index, system in enumerate(game.galaxy.systems):
            plotted = {h.id for h in traffic.in_system(game, system)}
            if any(h.hostile for h in traffic.in_system(game, system)):
                dark_seen += 1
            for attempt in range(12):
                met = roll_encounter(game, system, RNG(f"m{index}-{attempt}"))
                if not met:
                    continue
                total += 1
                if met.get("hull_id"):
                    assert met["hull_id"] in plotted, (
                        f"met {met['hull_id']}, which was not on the chart")
                    # And it is genuinely that hull, not merely tagged with
                    # its id. Checking the linkage alone passed with the name
                    # assignment deleted, which is a check measuring nothing.
                    was = next(h for h in traffic.in_system(game, system)
                               if h.id == met["hull_id"])
                    assert met["enemy"]["ship"].name == was.name, (
                        f"plotted {was.name} and met "
                        f"{met['enemy']['ship'].name}")
                    named += 1
        assert total > 0, "nothing ever happened on arrival"
        assert named > 0, (
            f"{total} encounters and not one was a hull already plotted — "
            "the chart tells you nothing about what you will meet")
        return (f"{named} of {total} encounters were a hull already on the "
                f"chart · {dark_seen} systems running something dark")

    @check("running dark makes a system more dangerous, not just prettier")
    def _():
        # Controlled. The first version compared systems with a dark hull
        # against systems without, and passed with the contribution set to
        # zero — because unmarked hulls appear in portless and bloomed
        # systems, which were already the dangerous ones. It measured the
        # confound, not the effect.
        #
        # So: hold the system fixed and vary only the traffic. Same port, same
        # bloom, same standing — one arrival where something runs dark and one
        # where nothing does.
        game = new_game("risk")
        held = None
        for system in game.galaxy.systems:
            if traffic.hostiles(game, system):
                held = system
                break
        assert held is not None, "nothing in this sector runs dark at all"

        def rate(system, quiet: bool) -> float:
            real = traffic.hostiles
            if quiet:
                traffic.hostiles = lambda _g, _s=None: []
            try:
                return sum(1 for a in range(400)
                           if roll_encounter(game, system,
                                             RNG(f"c{a}"))) / 400
            finally:
                traffic.hostiles = real

        loud = rate(held, quiet=False)
        quiet = rate(held, quiet=True)
        assert loud > quiet, (
            f"{held.name} is jumped on {loud*100:.0f}% of arrivals with an "
            f"unmarked hull present and {quiet*100:.0f}% without — the hull "
            "on the chart changes nothing")
        return (f"same system, same day: {loud*100:.0f}% of arrivals "
                f"contested with something running dark, {quiet*100:.0f}% "
                "without")

    @check("the helm names who else is out here")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        game = new_game("draw-traffic")
        hulls = traffic.in_system(game)
        assert hulls, "the home system has no traffic to draw"
        win = MainWindow(game)
        win.resize(1400, 1200)
        win.go("helm")
        for _ in range(3):
            app.processEvents()
        texts = [w.text() for w in win.views["helm"].findChildren(QLabel)
                 if w.text()]
        for hull in hulls:
            assert any(hull.name in t for t in texts), (
                f"{hull.name} is nowhere on the helm")
        win.close()
        return f"{len(hulls)} hulls named on the helm"
