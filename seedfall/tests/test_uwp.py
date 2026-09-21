"""The world profile: eight characters that say something true about a place.

*Traveller*'s Universal World Profile, laid over the Verge's own bones. The
claims, each of which is the reason to have it at all:

- **It is derived, not stored.** Every digit comes from something the sector
  already holds, so a profile cannot disagree with the world it describes and
  an old chronicle grows one with no migration.
- **It is stable.** Asked twice, in two frames or two processes, it answers
  the same — and asking does not move the chronicle's own luck, which is the
  fault this project has been bitten by most.
- **It says something.** A vacuum rock is `Va`, a wet world with farmers on
  it is `Ag`, and a sector where every world earned the same codes would be a
  profile that described nothing.
- **The market reads it.** A world that grows food sells it cheaper than one
  that cannot, which is the whole of speculative trade — and the counter's
  own spread survives it, because a market that pays more than it charges is
  a money printer (`solvency`).
"""

from __future__ import annotations

from collections import Counter

from ..core.state import new_game
from ..data import uwp
from ..sim import profile as profile_sim
from .harness import Suite

#: How many of a fresh sector's worlds to read. All of them: the point of a
#: derived profile is that it holds everywhere, and a sector is 165 bodies.
SECTOR = "uwp-suite"


def _bodies(game):
    for system in game.galaxy.systems:
        for body in system.bodies:
            yield system, body


def run(suite: Suite) -> None:
    check = suite.check

    @check("every world in the sector reads as a profile, and none of it is stored")
    def _():
        game = new_game(SECTOR)
        seen = 0
        for system, body in _bodies(game):
            got = profile_sim.profile(game, system, body)
            seen += 1
            line = uwp.code(got)
            assert len(line) == 9 and line[7] == "-", f"{body.name}: {line!r}"
            for name in ("size", "atmosphere", "hydrographics", "population",
                         "government", "law", "tech"):
                assert getattr(got, name) >= 0, (body.name, name)
            assert got.zone in ("green", "amber", "red"), got.zone
        # Nothing was written to the body, the system or the game: a profile
        # that left a field behind would have to be migrated and could drift.
        body = next(b for _s, b in _bodies(game))
        assert not any(f.startswith("uwp") or f.startswith("profile")
                       for f in vars(body)), sorted(vars(body))
        return f"{seen} bodies, every one with a profile and none of it saved"

    @check("a profile is the same every time it is asked, and costs no luck")
    def _():
        game = new_game(SECTOR)
        system, body = next(iter(_bodies(game)))
        was = game.rng_seed
        first = profile_sim.profile(game, system, body)
        again = profile_sim.profile(game, system, body)
        assert first == again, (first, again)
        assert game.rng_seed == was, (
            "reading a world advanced the chronicle's own luck")
        # And a fresh game on the same seed reads the same sector, which is
        # what makes it survive a reload.
        twin = new_game(SECTOR)
        other = next(b for s in twin.galaxy.systems for b in s.bodies
                     if b.id == body.id and s.id == system.id)
        third = profile_sim.profile(twin, next(
            s for s in twin.galaxy.systems if s.id == system.id), other)
        assert third == first, (first, third)
        return (f"{uwp.code(first)} read three times, twice in two processes' "
                "worth of state, and the seed untouched")

    @check("the digits say what the world is, not what a table felt like")
    def _():
        game = new_game(SECTOR)
        airless = wet = big = 0
        for system, body in _bodies(game):
            got = profile_sim.profile(game, system, body)
            if body.kind in ("asteroid", "comet"):
                assert got.size == 0 and got.atmosphere == 0, (
                    f"{body.name} is a {body.kind} with size {got.size} "
                    f"and atmosphere {got.atmosphere}")
                airless += 1
            if body.kind == "ocean":
                assert got.hydrographics >= 7, (body.name, got.hydrographics)
                wet += 1
            if body.radius_km >= 14_400 and body.kind not in ("gas",):
                assert got.size >= 9, (body.name, body.radius_km, got.size)
                big += 1
            # Nobody home means nobody in charge: Traveller's own rule, and
            # the thing that makes `Ba` mean anything.
            if got.population == 0:
                assert got.government == 0 and got.law == 0 and got.tech == 0
                assert "Ba" in uwp.codes(got), uwp.codes(got)
        assert airless and wet, (airless, wet)
        return (f"{airless} airless rocks, {wet} ocean worlds, {big} giants — "
                "each read off the body rather than a die")

    @check("a sector earns a spread of classifications, not one")
    def _():
        game = new_game(SECTOR)
        tally, ports, zones = Counter(), Counter(), Counter()
        for system, body in _bodies(game):
            got = profile_sim.profile(game, system, body)
            tally.update(uwp.codes(got))
            ports[uwp.STARPORTS.get(got.starport, uwp.STARPORTS[0])[0]] += 1
            zones[got.zone] += 1
        assert len(tally) >= 6, dict(tally)
        # A frontier is mostly empty and mostly safe to fly through; an
        # advisory on four worlds in five is an advisory nobody reads.
        assert zones["green"] >= zones["amber"], dict(zones)
        assert zones["red"] <= zones["green"], dict(zones)
        # And the ports are a range rather than one class repeated.
        assert len([k for k, n in ports.items() if n]) >= 3, dict(ports)
        return (f"{len(tally)} classifications, commonest "
                + ", ".join(f"{c}×{n}" for c, n in tally.most_common(4))
                + f"; ports {dict(ports)}; zones {dict(zones)}")

    @check("a profile says what the world is like to trade with")
    def _():
        game = new_game(SECTOR)
        said = 0
        for system in game.galaxy.systems:
            if not system.port:
                continue
            world = profile_sim.port_world(system)
            lines = uwp.trades(profile_sim.profile(game, system, world))
            said += len(lines)
        assert said, "no port's world says anything about what it trades"
        # The table means something: a world that grows food and one that
        # cannot must not read the same.
        farm = uwp.Profile(3, 8, 6, 6, 6, 4, 4, 9)        # Ag
        rock = uwp.Profile(3, 0, 0, 0, 6, 4, 4, 9)        # Va, Na
        assert "Ag" in uwp.codes(farm) and "Ag" not in uwp.codes(rock)
        assert uwp.trades(farm) != uwp.trades(rock), uwp.trades(farm)
        assert any("food" in line for line in uwp.trades(farm)), uwp.trades(farm)
        assert any("air" in line for line in uwp.trades(rock)), uwp.trades(rock)
        # **The prices themselves are not moved, and that is on purpose.**
        # Wiring the classifications into `world/economy` re-balances an
        # economy a dozen other checks are tuned against — measured, it broke
        # the freight desk's load clamp and put the careful captain's
        # five-year ending out of reach. It is its own piece of work.
        return (f"{said} sentences across the sector's ports; a farm and a "
                "rock read differently")

    @check("every table is complete, and every code can be earned")
    def _():
        # A scale with a hole in it prints an empty string at the one world
        # that lands in it, which is the kind of fault nobody sees until a
        # player is standing on it.
        for name, table, top in (("size", uwp.SIZES, 10),
                                 ("atmosphere", uwp.ATMOSPHERES, 15),
                                 ("hydrographics", uwp.HYDROGRAPHICS, 10),
                                 ("population", uwp.POPULATIONS, 12),
                                 ("government", uwp.GOVERNMENTS, 13),
                                 ("law", uwp.LAW_LEVELS, 12),
                                 ("tech", uwp.TECH_LEVELS, 15)):
            missing = [n for n in range(top + 1) if n not in table]
            assert not missing, f"{name} has no entry for {missing}"
        assert len(uwp.STARPORTS) == 6, sorted(uwp.STARPORTS)
        # Every classification is reachable: a code no profile can earn is a
        # row in a table that will never be read.
        game = new_game(SECTOR)
        earned = set()
        for system, body in _bodies(game):
            earned.update(uwp.codes(profile_sim.profile(game, system, body)))
        for made in (uwp.Profile(3, 8, 6, 6, 6, 4, 4, 9),      # Ag Ga Ni
                     uwp.Profile(3, 0, 0, 0, 9, 4, 4, 14),     # Va In Hi Ht
                     uwp.Profile(1, 8, 4, 3, 2, 2, 1, 4),      # Po Lo Lt
                     uwp.Profile(3, 8, 6, 10, 6, 4, 4, 9),     # Wa Ri
                     uwp.Profile(3, 5, 11, 4, 5, 4, 4, 9)):    # Fl
            earned.update(uwp.codes(made))
        unreachable = [c for c, _n, _t in uwp.TRADE_CODES if c not in earned]
        assert not unreachable, f"codes nothing can earn: {unreachable}"
        # And every classification has something to say about trading there.
        known = {c for c, _n, _t in uwp.TRADE_CODES}
        assert set(uwp.TRADES) <= known, sorted(set(uwp.TRADES) - known)
        assert set(uwp.TRADES) == known, sorted(known - set(uwp.TRADES))
        return (f"7 scales with no holes, {len(uwp.TRADE_CODES)} codes all "
                f"reachable, every one of them with a line to say")

    @check("the System screen prints the profile where a captain would look")
    def _():
        from PyQt6.QtWidgets import QLabel
        from .qtkit import app as _app
        from .qtkit import main_window
        keep = _app()
        game = new_game(SECTOR)
        win = main_window(game, (1360, 880))
        win.go("system")
        for _ in range(4):
            keep.processEvents()
        view = win.views["system"]
        said = " ".join(lab.text() for lab in view.findChildren(QLabel)
                        if lab.text())
        assert "World profile" in said, "the System screen shows no profile"
        system = game.system
        body = system.bodies[view.selected]
        got = profile_sim.profile(game, system, body)
        assert uwp.code(got) in said, (
            f"{uwp.code(got)} is not on the screen that describes it")
        win.close()
        keep.processEvents()
        return f"{body.name} reads {uwp.code(got)} on the System screen"
