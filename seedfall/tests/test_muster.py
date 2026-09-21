"""The crew, whole: a muster book, a sheet per person, and every watch.

Four claims:

- **The muster book is about the crew, not about a person.** The complement,
  the watch bill and the ship's own abilities are read off the same officers
  and agree with the per-person modules they are derived from — the best
  level aboard in a skill is the same number `lifepath.skill_aboard` gives,
  because it is the same question asked once instead of forty times.
- **A station is held by somebody who can do it.** A career is only weighted
  towards a station, so the dice could produce a Chief Engineer who had never
  touched a drive. `careers.STATION_SKILLS` closes that, and nothing is ever
  taken away from somebody who really did learn it.
- **Reading a crew changes nothing.** Opening the screen, sorting it five
  ways and reading six sheets costs the chronicle no luck, writes nothing to
  a saved officer and answers the same every time.
- **The screen decides nothing.** Every button on it is an act in `sim/`,
  the price it quotes is the price charged, and paying somebody off through
  the Crew screen leaves the same game as paying them off anywhere else.
"""

from __future__ import annotations

from collections import Counter

from ..core.state import new_game
from ..data import careers as career_table
from ..data.lore import CREW_ROLES
from ..data.screens import KEY_FOR, SCREENS
from ..sim import crew as crew_sim
from ..sim import lifepath as life_sim
from ..sim import loyalty as loyalty_sim
from ..sim import roster as roster_sim
from .harness import Suite

CROWD = ("muster-a", "muster-b", "muster-c", "muster-d")


def run(suite: Suite) -> None:
    check = suite.check

    @check("the muster book answers about the crew, not about one person")
    def _():
        seen = 0
        for seed in CROWD:
            game = new_game(seed)
            said = roster_sim.muster(game)
            aboard = roster_sim.active(game)
            assert said["officers"] == len(aboard), said
            assert said["heads"] == said["officers"] + said["hands"]
            assert said["wages"] == crew_sim.daily_wages(aboard)
            assert said["loyalty"] == loyalty_sim.summary(game)["mean"]
            # The watch bill names every station once, and the holes show.
            rows = roster_sim.stations(game)
            assert [r["id"] for r in rows] == [r[0] for r in CREW_ROLES]
            held = {r["id"] for r in rows if r["officer"] is not None}
            assert held == {o.role for o in aboard}, (held, rows)
            # The ship's abilities are the same numbers, asked once.
            for row in roster_sim.abilities(game):
                level, who = life_sim.skill_aboard(game, row["skill"])
                assert level == row["level"], (row["skill"], level, row)
                assert who is not None
                seen += 1
            for name in roster_sim.missing(game):
                assert name in career_table.SKILLS, name
                assert life_sim.skill_aboard(game, name)[1] is None, name
        assert seen >= 4 * 4, seen
        return (f"{len(CROWD)} crews, {seen} abilities, every one of them the "
                "same number `skill_aboard` gives")

    @check("the person holding a station can do the job it is named for")
    def _():
        short, seen = [], 0
        for seed in CROWD + ("muster-e", "muster-f"):
            game = new_game(seed)
            for officer in roster_sim.active(game):
                pair = career_table.STATION_SKILLS.get(officer.role, ())
                if not pair:
                    continue
                record = life_sim.of(game, officer)
                seen += 1
                if record.skill(pair[0]) < 1:
                    short.append((officer.role_name, record.skill(pair[0])))
                assert record.skill(pair[1]) >= 0, (officer.role, pair)
        assert seen >= 6, seen
        assert not short, f"stations held by somebody untrained in them: {short}"
        # And nothing is taken away: a career that really taught it keeps it.
        game = new_game("muster-keep")
        officer = next(o for o in game.officers if o.role in
                       career_table.STATION_SKILLS)
        record = life_sim.of(game, officer)
        best = max(record.skills.values())
        assert best >= 1, record.skills
        return (f"{seen} officers, every one of them trained in their own "
                f"station; deepest skill aboard one bridge is {best}")

    @check("reading a crew costs the chronicle nothing and stores nothing")
    def _():
        game = new_game("muster-read")
        was, day = game.rng_seed, game.day
        first = [roster_sim.card(game, o) for o in roster_sim.active(game)]
        for order, _name in roster_sim.ORDERS:
            rows = roster_sim.roll(game, order)
            assert len(rows) == len(roster_sim.active(game)), order
            assert len({o.id for o in rows}) == len(rows), order
        roster_sim.abilities(game)
        roster_sim.ties_ashore(game)
        roster_sim.departed(game)
        roster_sim.wage_bill(game)
        assert game.rng_seed == was, "reading the crew moved the chronicle"
        assert game.day == day
        again = [roster_sim.card(game, o) for o in roster_sim.active(game)]
        for one, two in zip(first, again):
            assert one["best"] == two["best"] and one["wants"] == two["wants"]
            assert one["career"] == two["career"]
        for officer in game.officers:
            assert not any(f.startswith("person") or f.startswith("record")
                           for f in vars(officer)), sorted(vars(officer))
        # An order is an ordering, not a filter: by loyalty is sorted by it.
        by = roster_sim.roll(game, "loyalty")
        levels = [loyalty_sim.loyalty_of(o) for o in by]
        assert levels == sorted(levels), levels
        assert len(first) >= 1
        return (f"{len(first)} sheets read twice over "
                f"{len(roster_sim.ORDERS)} orders, no luck spent")

    @check("the Crew screen opens on every tab and shows everybody aboard")
    def _():
        from PyQt6.QtWidgets import QLabel
        from .qtkit import app as _app
        from .qtkit import main_window
        keep = _app()
        game = new_game("muster-ui")
        system = next(s for s in game.galaxy.systems if s.port and s.market)
        game.location_id = system.id
        names = [o.name for o in roster_sim.active(game)]
        counted = Counter()
        for size in ((1040, 680), (1440, 900)):
            win = main_window(game, size)
            win.go("crew")
            view = win.views["crew"]
            for tab in ("roster", "sheet", "watches", "book"):
                view.tab = tab
                view.refresh()
                for _ in range(4):
                    keep.processEvents()
                said = " ".join(lab.text() for lab in
                                view.findChildren(QLabel) if lab.text())
                assert "The crew" in said or "aboard" in said, tab
                counted[tab] += len(said)
            # The roster names everybody, and the sheet reads whoever is asked.
            view.tab = "roster"
            view.refresh()
            for _ in range(4):
                keep.processEvents()
            said = " ".join(lab.text() for lab in view.findChildren(QLabel)
                            if lab.text())
            for name in names:
                assert name in said, f"{name} is not on the roster"
            for officer in roster_sim.active(game):
                view.open_sheet(officer)
                for _ in range(3):
                    keep.processEvents()
                page = " ".join(lab.text() for lab in
                                view.findChildren(QLabel) if lab.text())
                assert officer.name in page, officer.name
                assert life_sim.of(game, officer).career_name in page
            win.close()
            keep.processEvents()
        assert all(counted[t] > 200 for t in counted), dict(counted)
        assert KEY_FOR["crew"] and len(
            {k for _s, _l, k in SCREENS}) == len(SCREENS)
        # A bridge with nobody on it is a screen, not a crash: the captain is
        # standing every watch, and the mess deck is still there to fill.
        bare = new_game("muster-alone")
        bare.officers = []
        alone = main_window(bare, (1040, 680))
        alone.go("crew")
        view = alone.views["crew"]
        for tab in ("roster", "sheet", "watches", "book"):
            view.tab = tab
            view.refresh()
            for _ in range(3):
                keep.processEvents()
            said = " ".join(lab.text() for lab in view.findChildren(QLabel)
                            if lab.text())
            assert said, f"the {tab} tab is blank with nobody aboard"
            if tab in ("roster", "sheet"):
                assert "mess deck" in said.lower(), said[:120]
        alone.close()
        keep.processEvents()
        return (f"four tabs at two sizes, {len(names)} sheets read, and an "
                f"empty bridge; rail key '{KEY_FOR['crew']}'")

    @check("every button on the crew screen is an act in the sim")
    def _():
        from .qtkit import app as _app
        from .qtkit import main_window
        keep = _app()
        game = new_game("muster-acts")
        game.credits = 90_000
        win = main_window(game, (1360, 880))
        win.go("crew")
        view = win.views["crew"]

        # A bonus costs exactly what the screen quoted, and no more.
        quoted = roster_sim.muster(game)["bonus"]
        held = game.credits
        view.bonus()
        keep.processEvents()
        assert game.credits == held - quoted, (held, game.credits, quoted)

        # Shore leave is a week, and the week actually passes.
        day = game.day
        view.shore_leave()
        keep.processEvents()
        assert game.day >= day + crew_sim.SHORE_LEAVE_DAYS, (day, game.day)

        # Signing hands on charges the fee and fills berths.
        hands, purse = game.ship.crew, game.credits
        view.sign_on(5)
        keep.processEvents()
        assert game.ship.crew == hands + 5, game.ship.crew
        assert game.credits < purse

        # Paying somebody off empties their station, everywhere.
        officer = roster_sim.active(game)[0]
        view.open_sheet(officer)
        keep.processEvents()
        view.pay_off(officer)
        keep.processEvents()
        assert officer not in game.officers, "the officer is still aboard"
        rows = roster_sim.stations(game)
        empty = [r for r in rows if r["id"] == officer.role]
        assert empty and empty[0]["officer"] is None, rows
        # And the screen falls back to somebody who is actually aboard.
        assert view.officer() is not officer
        win.close()
        keep.processEvents()
        return (f"bonus {quoted:,} charged to the credit, seven days passed, "
                f"five hands signed, {officer.name.split()[0]} paid off")
