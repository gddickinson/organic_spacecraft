"""The tactical station, and whether it tells the truth about a fight.

Measured on a fresh chronicle with nothing shooting:

    the battle screen      2 labels — "No engagement / Nothing is shooting
                           at you", and a Back button
    the gunner's window    1 label
    hulls in the system    5

Combat existed only once it had started. So the decision the whole tactical
model is built to serve — whether to be here at all — was made blind, and
reviewed afterwards in the log.

`sim/readiness.py` answers it by *rehearsing* the fight: the same `Battle`
`combat.start` would build, thrown away, every figure read off it with the
functions the engagement itself uses. The claims:

- **The rehearsal is a rehearsal, not a second formula.** What the board says
  about a fight is what the fight says.
- **It changes nothing.** A captain may open the board a hundred times without
  the hull taking a scratch or the sector's luck moving.
- **The window shows the fight it is titled with.** Not a hypothetical
  opponent under a real opponent's name — which is what it did, and what only
  a picture caught.
- **The board follows the ship**, because the distances come through
  `flight.ship_position` like everything else.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import combat, consorts as consort_sim, encounters, flight
from ..sim import readiness as ready_sim
from .harness import Suite


#: The QApplication, held at module scope on purpose. `_window` builds a
#: window and returns it, so a `keep = _app()` local inside that helper dies
#: on return — and if it was the last Python reference, Qt takes the whole
#: application down with it and every widget in it. The symptom is a
#: `RuntimeError: wrapped C/C++ object of type QLabel has been deleted` on
#: the *next* line, which reads like a Qt mystery and is a lifetime bug.
_HELD = None


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    global _HELD
    _HELD = QApplication.instance() or QApplication([])
    assert _HELD is not None
    return _HELD


def _fighting(seed: str = "fight"):
    """A game with a real engagement running on it."""
    game = new_game(seed)
    rng = game.rng("engagement")
    battle = combat.start(
        game.ship, game.ship_stats,
        encounters.make_enemy(rng, "freeholds", encounters.typical_threat()),
        bonuses=game.bonuses, officers=game.officers, game=game, rng=rng,
        fleet=consort_sim.escorts_of(game))
    return game, battle


def _window(game, battle=None):
    from ..ui.tactical_window import open_tactical
    from ..ui.window import MainWindow
    keep = _app()
    assert keep is not None
    win = MainWindow(game)
    win.toast = lambda *a, **k: None
    win.battle = battle
    window = open_tactical(win)
    window.resize(1120, 780)
    keep.processEvents()
    return win, window


def run(suite: Suite) -> None:
    check = suite.check

    @check("the readiness board is a rehearsal of the fight, not a second sum")
    def _():
        # The one-door claim, asked by taking the rehearsal's own battle and
        # putting it through the *engagement's* functions. Anything the board
        # worked out for itself would show up here as a disagreement.
        from ..sim import assessment, firing, gunnery
        game = new_game("rehearsal")
        report = ready_sim.report(game)
        b = report["battle"]
        assert report["weight"] == assessment.weight(b)
        assert report["band"] == b.band
        live = firing.solution(b.player, b.enemy, b.band)
        assert [s.mount_id for s in report["shots"]] == [s.mount_id for s in live]
        bearing = [s.mount_id for s in gunnery.mounts(b) if s.can_fire]
        assert report["heat"]["heat"] == gunnery.quote(b, bearing)["heat_added"]
        assert report["heat"]["fault"] == gunnery.fault_line(b.player)
        return (f"{len(live)} mount(s) and every figure the engagement's own: "
                f"{report['weight']['verdict']} at "
                f"{report['band_name'].lower()} range")

    @check("opening the board a hundred times costs nothing at all")
    def _():
        # `combat` spends ammunition and adds heat, and a readiness board is
        # something a captain opens on a whim. It rehearses on a copy.
        game = new_game("inert")
        game.ship.heat = 12.0
        before = (game.ship.heat, dict(game.ship.cargo),
                  [layer.hp for layer in game.ship.layers],
                  game.day, game.rng_seed, game.orbit_body, len(game.log))
        for _ in range(100):
            ready_sim.report(game)
        after = (game.ship.heat, dict(game.ship.cargo),
                 [layer.hp for layer in game.ship.layers],
                 game.day, game.rng_seed, game.orbit_body, len(game.log))
        assert before == after, f"{before}\n{after}"
        # And the same report twice running is the same report: a board that
        # reshuffled the opening aspect on every repaint could not be read.
        one, two = ready_sim.report(game), ready_sim.report(game)
        assert one["weight"] == two["weight"] and one["band"] == two["band"]
        # And the rehearsal is held on a *copy* of the hull, asked directly.
        # Measured: `combat.start` writes nothing to the ship it is handed, so
        # the unscathed-hull assertions above pass either way — the copy is
        # insurance against `assessment` and `gunnery` growing a write, and
        # only a structural question can see it.
        assert one["battle"].player.ship is not game.ship, (
            "the rehearsal is holding the real hull")
        assert one["battle"].player.ship.name == game.ship.name
        return ("a hundred reports: no heat, no cargo, no hull, no day, no "
                "luck spent, and the same answer twice")

    @check("the window shows the fight it is titled with")
    def _():
        # The fault a picture caught and no figure could: mid-engagement the
        # window titled itself with the ship actually firing and printed a
        # rehearsal against a hull the sector *might* send — "Freeholds GRAFT
        # «Margin Call», turn 1" over "against Charter CORAL «Long Consent»".
        # Every number on it was correct. It was answering another question.
        from PyQt6.QtWidgets import QLabel
        game, battle = _fighting()
        win, window = _window(game, battle)
        # **The board's own labels, not the window's.** The first version of
        # this read `window.findChildren` — which includes the title — so the
        # assertion "the enemy's name appears" was satisfied by the title it
        # was being compared against, and the mutation that puts the fault
        # back passed it. Measured: the mutation is caught here and nowhere.
        said = " ".join(lab.text() for lab in window.board.findChildren(QLabel)
                        if lab.text())
        title = window.title.text()
        window.close()
        win.close()
        assert battle.enemy_name in title, title
        assert battle.enemy_name in said, (
            f"the window is titled {title!r} and the board is describing "
            f"somebody else: {said[:180]!r}")
        return f"engaged: title and board both on {battle.enemy_name}"

    @check("standing by, it says what is out there and how far")
    def _():
        from PyQt6.QtWidgets import QLabel
        game = new_game("standing")
        win, window = _window(game)
        said = [lab.text() for lab in window.findChildren(QLabel) if lab.text()]
        rows = ready_sim.threats(game)
        listed = window.contacts.count()
        window.close()
        win.close()
        assert rows, "no traffic in this system to report on"
        assert listed == len(rows), (
            f"{len(rows)} hulls in the system and {listed} on the board")
        assert any("Guns" == text for text in said), said[:12]
        assert any("The bridge" == text for text in said), said[:12]
        # The rehearsal is labelled as one. A plot that looks live and is not
        # would be the worst thing on the window.
        assert any("Rehearsal" in text for text in said), (
            "the standing-by plot does not say it is a rehearsal")
        return (f"{listed} hulls listed, the guns, the bridge and a plot that "
                "admits it is a rehearsal")

    @check("the rehearsal holds still between repaints")
    def _():
        # A board that reshuffles the geometry every time it redraws cannot be
        # read, and `tactical.initial_layout` scatters the opening aspect when
        # it is given an rng — which is why `sparring` does not give it one.
        #
        # **Asked of the picture, because the numbers cannot see it.** Handing
        # the layout an rng changes the pair's orientation and the enemy's
        # heading; the band is an argument, the relative bearing is always
        # zero because `initial_layout` puts the enemy dead ahead, and
        # `assessment.weight` has no aspect term. So every figure in the
        # report is identical either way and only the plot moves. Measured:
        # the mutation that passes an rng is caught here and by nothing else.
        game = new_game("still")
        win, window = _window(game)
        first = window.grab().toImage()
        window.refresh()
        _app().processEvents()
        second = window.grab().toImage()
        window.close()
        win.close()
        moved = sum(1 for y in range(0, first.height(), 2)
                    for x in range(0, first.width(), 2)
                    if first.pixel(x, y) != second.pixel(x, y))
        assert moved == 0, (
            f"{moved} samples changed between two repaints of a still ship — "
            "the rehearsal is reshuffling its own geometry")
        return (f"{first.width()}x{first.height()}: two repaints, not one "
                "sample moved")

    @check("the board follows the ship, because the distances do")
    def _():
        # Everything here reads `flight.ship_position` through
        # `traffic.reach_to`. Before there was one door the ship had no
        # position in a system at all and every hull read the same distance.
        game = new_game("moved")
        near = {row["name"]: row["range_au"] for row in ready_sim.threats(game)}
        flight.stand_off(game)
        far = {row["name"]: row["range_au"] for row in ready_sim.threats(game)}
        moved = [name for name in near
                 if abs(near[name] - far.get(name, near[name])) > 0.01]
        assert moved, (
            "the ship moved across the system and not one range changed")
        # And the phrasing: a hull inside the conn's reach is "alongside"
        # because that is the game's own threshold, not a rounding.
        from ..sim import berthing
        assert ready_sim.span(berthing.REACH_KM / ready_sim.KM_PER_AU * 0.9) \
            == "alongside"
        assert ready_sim.span(2.5) == "2.50 AU"
        # The conversion itself, against **written figures** rather than
        # against `KM_PER_AU` — the line above divides by the constant it
        # would be pinning, so it moves with it and pins nothing. Five
        # thousandths of an AU is 747,989 km, and a hull that far off is past
        # the conn's 200,000 km reach and so gets a figure rather than a word.
        assert ready_sim.span(0.005) == "747,989 km", ready_sim.span(0.005)
        # And 0.0012 AU is 179,517 km — inside the conn's reach, so the
        # threshold wins over the figure and the word is the answer.
        assert ready_sim.span(0.0012) == "alongside", ready_sim.span(0.0012)
        return (f"{len(moved)} of {len(near)} ranges moved when the ship did; "
                f"nearest went {min(near.values()):.2f} → "
                f"{min(far.values()):.2f} AU")

    @check("a readiness report describes the sector the encounters come from")
    def _():
        # The opponent is built by `encounters.make_enemy` at the middle of
        # the range `roll_encounter` actually draws, so the board and the
        # ambush describe one sector. Both figures used to be inline literals
        # written twice, and nothing could ask what a typical opponent was.
        # **Against written figures, never against the constants themselves.**
        # The first version of this asserted `typical == FLOOR + SPREAD / 2`,
        # which is the definition rearranged: it moves with both and pins
        # neither, and the tripwire duly reported all four mutations —
        # doubling the floor, zeroing it, doubling the spread, zeroing it —
        # sailing through. Measured on the shipped game, 120 opponents drawn
        # per difficulty:
        #
        #     difficulty 0    median hull 124
        #     difficulty 1    median hull 149      <- the floor
        #     difficulty 2    median hull 208      <- what a report quotes
        #     difficulty 3    median hull 359      <- the ceiling
        #     difficulty 4    median hull 397
        #
        # So a typical opponent is a materially heavier hull than the softest
        # the sector sends and a materially lighter one than the worst, and
        # those are the claims worth holding.
        import statistics
        from ..core.rng import RNG

        def median_hull(difficulty: float) -> float:
            return statistics.median(
                sum(layer.max for layer in
                    encounters.make_enemy(RNG(f"t{i}"), "freeholds",
                                          difficulty)["ship"].layers)
                for i in range(120))

        floor = median_hull(encounters.THREAT_FLOOR)
        typical = median_hull(encounters.typical_threat())
        worst = median_hull(encounters.THREAT_FLOOR + encounters.THREAT_SPREAD)
        assert 130 <= floor <= 175, floor
        assert 190 <= typical <= 240, typical
        assert 320 <= worst <= 400, worst
        assert floor < typical < worst, (floor, typical, worst)
        game = new_game("sector")
        report = ready_sim.report(game)
        # Whoever is actually here, not an abstraction: the named opponent
        # belongs to a faction with a hull in this system.
        from ..sim import traffic
        present = traffic.present_factions(game)
        assert present, "no traffic here to draw an opponent from"
        # And naming a hull changes who the report is against.
        rows = ready_sim.threats(game)
        against = ready_sim.report(game, rows[0]["hull"])
        assert rows[0]["name"] in against["against"], against["against"]
        assert against["against"] != report["against"]
        return (f"median hull {floor:.0f} at the softest the sector sends, "
                f"{typical:.0f} at what a report quotes, {worst:.0f} at the "
                f"worst; named: {against['against']}")
