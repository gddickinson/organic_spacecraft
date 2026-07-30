"""The walk back to the lander: costed, said out loud, and worth knowing.

The ground poses one piece of arithmetic. A party carries `supply` in days; a
step spends one day on ground already crossed and up to three on ground it has
not, times whatever the weather is doing. Reach the pad and the haul comes up,
capped at what four people can lift. Run out first and the party is stranded:
40% of that, and the rest stays where it fell.

**The screen showed "Supply · 7 days" and never said how far away the lander
was.** `tests/ground_ai.py` had already written the consequence down for the
driver — "the one decision the ground actually poses ... was invisible to a
driver that never walked home" — and the captain was in exactly the same
position, with 60% of a hold riding on it.

And the long chronicle proved nobody had ever driven the other side of it:
measured over ten years, **50 landings stranded, 32 aborted, and not one
returned.** The whole intended ending of an expedition — walk back, lift, bank
it — had never been exercised by a played game.

The claims:

- **The quote is what the walk spends**, step for step, on the walks where the
  weather holds — and the module says it prices the weather it can see.
- **It routes over ground the party knows**, and a tie goes to their own
  footprints rather than fresh terrain.
- **It says when the supplies will not cover it**, in those words.
- **The screen prints it.**
- **Knowing the price is worth something**: a leader who turns back on a costed
  two days' spare beats one working from tile counts at the same margin.
- **And a decade of chronicles now brings parties home**, which is the coverage
  this whole thing was missing.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import expedition as exp_sim
from ..sim import wayhome as wayhome_sim
from ..sim.fieldwork import launch_expedition
from .harness import Suite


def _landed(seed: str, supply: int | None = None):
    """A party on the ground, ready to be walked about."""
    game = new_game(seed)
    body = next((i for i, b in enumerate(game.system.bodies)
                 if b.kind not in ("gas", "star")), None)
    if body is None:
        return None, None
    game.system.bodies[body].surveyed = True
    game.ship.cargo["biomass"] = 60
    if not launch_expedition(game, body,
                             [o.id for o in game.officers], 0).get("ok"):
        return None, None
    if supply is not None:
        game.expedition.supply = supply
    return game, game.expedition


def _wander(game, exp, rng, steps: int = 5):
    """Walk away from the pad, so there is a route to price."""
    for _ in range(steps):
        for dx, dy in ((0, -1), (1, 0), (-1, 0), (0, 1)):
            if exp.over:
                return
            if exp.tile(exp.x + dx, exp.y + dy) is None:
                continue
            if exp_sim.move(exp, dx, dy, game.officers, rng).get("ok"):
                break


def hops_direct(exp, lx: int, ly: int) -> list:
    """The straight line at the pad, ignoring what the ground costs."""
    out = []
    x, y = exp.x, exp.y
    while (x, y) != (lx, ly):
        x += (lx > x) - (lx < x)
        y += (ly > y) - (ly < y)
        out.append((x, y))
    return out


def run(suite: Suite) -> None:
    check = suite.check

    @check("the quote is what the walk actually spends")
    def _():
        # Forecast against act, which for the ground means: price the route,
        # then walk it and count the days. The quote is explicitly "at this
        # weather" — `step_cost` reads the front that is blowing now — so the
        # walks where a front arrives partway are counted separately rather than
        # quietly widening the tolerance.
        exact = weathered = 0
        for index in range(24):
            game, exp = _landed(f"quote-{index}")
            if exp is None:
                continue
            rng = RNG(f"q{index}")
            _wander(game, exp, rng, steps=4)
            if exp.over or (exp.x, exp.y) == exp_sim.LANDER:
                continue
            said = wayhome_sim.cost(exp)
            way = wayhome_sim.route(exp)
            assert way, "away from the pad and no route back"
            was_weather = getattr(exp, "weather", None)
            before = exp.days
            steady = True
            pinned = wayhome_sim.standing(exp)["pinned"]
            for x, y in way:
                if exp.over:
                    break
                # A pinned party sits it out, which is what the quote now counts
                # — `standing` adds the front's remaining days. Before it did,
                # this check was refused at the first step by a katabatic gale
                # while the panel promised three days to spare.
                guard = 0
                while wayhome_sim.standing(exp)["pinned"] and guard < 30:
                    guard += 1
                    exp_sim.shelter(exp, rng)
                    pinned = True
                    if exp.over:
                        break
                if exp.over:
                    break
                got = exp_sim.move(exp, x - exp.x, y - exp.y, game.officers, rng)
                assert got.get("ok"), (
                    f"the route said step to {(x, y)} and the ground refused: "
                    f"{got.get('why')}")
                # Every step, not the two ends. A front that arrives at step one
                # and has blown through by step four leaves the endpoints equal
                # and the bill changed — which is the same "at either end"
                # mistake this project has made in a check before.
                if getattr(exp, "weather", None) != was_weather:
                    steady = False
            spent = exp.days - before
            if steady and not pinned:
                assert spent == said, (
                    f"quoted {said} days and the walk spent {spent}, with the "
                    "weather unchanged throughout")
                exact += 1
            else:
                weathered += 1
        assert exact >= 6, f"only {exact} walks in settled weather"
        return (f"{exact} walks priced to the day; {weathered} more re-priced "
                "by a front arriving partway, which is the risk and not an error")

    @check("it routes over ground the party knows, by their own tracks")
    def _():
        game, exp = _landed("known")
        assert exp is not None
        rng = RNG("known")
        _wander(game, exp, rng, steps=5)
        way = wayhome_sim.route(exp)
        assert way, "no route home"
        for x, y in way:
            tile = exp.tile(x, y)
            assert tile.seen or tile.visited, (
                f"the route crosses {(x, y)}, which nobody has laid eyes on")
        walked = sum(1 for x, y in way if exp.tile(x, y).visited)
        assert walked == len(way), (
            f"{len(way) - walked} of {len(way)} steps home are over fresh "
            "ground when the party's own tracks lead back")

        # And it is genuinely the cheapest, not merely a path: no straight line
        # over the same ground can beat it.
        straight = []
        x, y = exp.x, exp.y
        while (x, y) != exp_sim.LANDER:
            x += (exp_sim.LANDER[0] > x) - (exp_sim.LANDER[0] < x)
            y += (exp_sim.LANDER[1] > y) - (exp_sim.LANDER[1] < y)
            straight.append((x, y))
        naive = sum(exp_sim.step_cost(exp, exp.tile(sx, sy))
                    for sx, sy in straight
                    if exp.tile(sx, sy) is not None)
        assert wayhome_sim.cost(exp) <= naive, (
            f"the route costs {wayhome_sim.cost(exp)} and walking straight at "
            f"the pad costs {naive}")
        return (f"{len(way)} steps home, every one over ground they have "
                f"crossed, at {wayhome_sim.cost(exp)} days against "
                f"{naive} straight at the pad")

    @check("a party that cannot afford the walk is told so")
    def _():
        game, exp = _landed("short")
        assert exp is not None
        rng = RNG("short")
        _wander(game, exp, rng, steps=5)
        need = wayhome_sim.cost(exp)
        assert need > 1, need

        exp.supply = need + 4
        easy = wayhome_sim.standing(exp)
        assert easy["ok"] and not easy["stranding"], easy
        assert easy["spare"] == 4, easy

        exp.supply = max(0, need - 2)
        tight = wayhome_sim.standing(exp)
        assert tight["stranding"] and not tight["ok"], tight
        assert "short of the lander" in tight["why"], tight
        assert "strand" in tight["why"], tight
        return (f"{need} days to walk: {easy['spare']} to spare reads clear, "
                f"two short reads {tight['why']!r}")

    @check("the ground screen says how far the lander is")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game, exp = _landed("screen")
        assert exp is not None
        rng = RNG("screen")
        _wander(game, exp, rng, steps=4)
        way = wayhome_sim.standing(exp)
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        # "ground", which is what `window.py` registers the view under.
        win.go("ground")
        view = win.views["ground"]
        view.refresh()
        for _ in range(3):
            app.processEvents()
        said = " ".join(lab.text() for lab in view.findChildren(QLabel)
                        if lab.text())
        win.close()
        assert "The walk home" in said, (
            f"the ground screen never mentions getting back: {said[:400]}")
        assert f"{way['days']} days" in said, (
            f"the walk costs {way['days']} days and the screen says otherwise")
        assert f"{way['spare']} day(s) to spare" in said, (
            "the screen gives the cost and leaves the captain to subtract")
        return (f"the panel reads {way['days']} days over {way['steps']} steps "
                f"with {way['spare']} to spare")

    @check("a leader who knows the price can hold a smaller reserve")
    def _():
        # The payoff, measured against the rule that was there before: tiles to
        # the pad with terrain and weather ignored. At the same margin the costed
        # walk should strand fewer parties, because four tiles of fresh scarp in
        # a dust storm is twelve days and reads as four.
        from . import ground_ai

        def tile_count_leader(game, exp, rng, margin=2, cap=300):
            steps = 0
            while not exp.over and steps < cap:
                steps += 1
                if exp.supply <= ground_ai.steps_home(exp) + margin:
                    if exp.at_lander:
                        exp_sim.lift_off(exp)
                        break
                    exp_sim.move(exp, *ground_ai._towards(exp, *exp_sim.LANDER),
                                 game.officers, rng)
                    continue
                if exp_sim.options_here(exp):
                    exp_sim.attempt(exp, 0, game.officers, rng)
                else:
                    exp_sim.move(exp, *ground_ai._towards(
                        exp, rng.int(0, exp_sim.W - 1),
                        rng.int(0, exp_sim.H - 1)), game.officers, rng)
            return exp

        def sweep(driver, margin=2, runs=24):
            home = stranded = 0
            for index in range(runs):
                game, exp = _landed(f"walk-{index}")
                if exp is None:
                    continue
                driver(game, exp, RNG(f"w{index}"), margin=margin)
                if exp.outcome == "returned":
                    home += 1
                elif exp.outcome == "stranded":
                    stranded += 1
            return home, stranded

        blind_home, blind_lost = sweep(tile_count_leader)
        told_home, told_lost = sweep(ground_ai.play)
        assert told_lost < blind_lost, (
            f"the costed walk stranded {told_lost} parties and the tile count "
            f"stranded {blind_lost} — knowing the price bought nothing")
        assert told_home > blind_home, (
            f"{told_home} returned against {blind_home}")
        return (f"at two days' margin: {told_home} home / {told_lost} stranded "
                f"knowing the price, against {blind_home} / {blind_lost} "
                "counting tiles")

    @check("it takes the cheap way round, and not over ground nobody has seen")
    def _():
        # Two mutations survived the checks above because a natural landing zone
        # does not tell them apart: the reveal has usually seen every tile near
        # the party, and the cheapest route is usually also the shortest. So this
        # builds a zone where hop-count and cost disagree, and where the direct
        # line crosses ground nobody has laid eyes on.
        #
        #   * a corridor of *visited* tiles, longer in steps and cheap per step
        #   * a direct line of dear terrain, one tile of which is unseen
        game, exp = _landed("maze")
        assert exp is not None
        dear = max(exp_sim.TERRAIN, key=lambda k: exp_sim.TERRAIN[k].cost)
        cheap = min(exp_sim.TERRAIN, key=lambda k: exp_sim.TERRAIN[k].cost)
        assert exp_sim.TERRAIN[dear].cost > exp_sim.TERRAIN[cheap].cost + 1, (
            "no two terrains differ enough to tell a detour from a shortcut")

        exp.weather = None                      # price the ground, not a front
        for tile in exp.tiles:
            tile.terrain = dear
            tile.visited = False
            tile.seen = True
        exp.x, exp.y = 0, 0
        lx, ly = exp_sim.LANDER
        # The long way: down the left edge and along the bottom, all of it walked.
        corridor = [(0, y) for y in range(1, ly + 1)] + \
                   [(x, ly) for x in range(1, lx + 1)]
        for cx, cy in corridor:
            tile = exp.tile(cx, cy)
            tile.terrain, tile.visited = cheap, True
        # And the direct line is *tempting*: cheap ground, fewer steps, and
        # nobody has laid eyes on any of it. A router that will plan over unseen
        # tiles takes it; one that will not walks the long way round. Making the
        # shortcut dear as well proved nothing — avoiding it cost the router
        # nothing either way, and the mutation that dropped the rule survived.
        blind = []
        for bx, by in hops_direct(exp, lx, ly)[:-1]:
            tile = exp.tile(bx, by)
            tile.terrain, tile.visited, tile.seen = cheap, False, False
            blind.append((bx, by))
        assert blind, "no unseen shortcut to resist"

        way = wayhome_sim.route(exp)
        assert way, "no route at all"
        assert not any(step in blind for step in way), (
            f"the route {way} crosses {blind}, which nobody has laid eyes on — "
            "cheap ground and a shorter walk, and still not knowable")
        # Not the step count: the router may legitimately cut a diagonal corner
        # off the corridor, which it does — eight steps rather than nine, all of
        # it still on walked ground. What matters is *which* ground.
        assert all(exp.tile(x, y).visited for x, y in way), (
            [(x, y, exp.tile(x, y).terrain, exp.tile(x, y).visited)
             for x, y in way])
        assert all(exp.tile(x, y).terrain == cheap for x, y in way), way
        assert all(exp.tile(x, y).seen for x, y in way), way
        assert len(way) > len(hops_direct(exp, lx, ly)), (
            "the cheap way round is not longer in steps, so this case cannot "
            "tell a router that counts hops from one that counts days")
        long_way = wayhome_sim.cost(exp)

        # What the direct line would have cost, for the record: fewer steps,
        # dearer ground. A router that counts hops instead of days takes it.
        hops = hops_direct(exp, lx, ly)
        direct = sum(exp_sim.step_cost(exp, exp.tile(hx, hy)) for hx, hy in hops)
        assert long_way >= direct, (
            f"the detour costs {long_way} and the unseen shortcut {direct} — "
            "the shortcut has to be the tempting one or the rule is untested")
        return (f"{len(way)} known steps at {long_way} days taken over a "
                f"{len(hops)}-step unseen shortcut at {direct}, on a zone of "
                f"{dear} with a walked {cheap} corridor")

    @check("days the party cannot move are counted, not wished away")
    def _():
        # **The defect the walking check found.** Some fronts pin a party where
        # it stands. The first version of the quote ignored them and told a party
        # held fast by a katabatic gale "4 days home, 3 to spare" — a trap, since
        # those days go whatever anybody wants and the walk has not started. A
        # party with exactly enough supply for the route would have stranded
        # while the panel said it was fine.
        from ..data.weather import WEATHERS_BY_ID
        from ..sim import weather as weather_sim

        pinning = next((w for w in WEATHERS_BY_ID.values() if w.pinned), None)
        assert pinning is not None, "no weather in the game pins a party"

        game, exp = _landed("pinned")
        assert exp is not None
        rng = RNG("pinned")
        _wander(game, exp, rng, steps=4)
        if (exp.x, exp.y) == exp_sim.LANDER or exp.over:
            game, exp = _landed("pinned-2")
            _wander(game, exp, RNG("pinned-2"), steps=3)

        exp.weather = None
        clear = wayhome_sim.standing(exp)
        assert not clear["pinned"] and clear["waiting"] == 0, clear

        exp.weather = pinning.id
        exp.weather_until = exp.days + 3
        held = wayhome_sim.standing(exp)
        assert held["pinned"], held
        assert held["waiting"] == 3, held
        # The waiting is isolated rather than compared against the clear-weather
        # figure: a gale that pins a party also makes every step dearer once it
        # lifts, so 4 days clear became 19 — sixteen for the walk at gale rates
        # and three sitting still. Measured that way round, the claim is exactly
        # "the days nobody can move are in the total".
        assert held["days"] - wayhome_sim.cost(exp) == held["waiting"] == 3, (
            f"{held['days']} days quoted, {wayhome_sim.cost(exp)} of walking, "
            f"and {held['waiting']} pinned — they do not add up")
        assert held["days"] > clear["days"], (clear["days"], held["days"])
        assert held["spare"] < clear["spare"], (clear, held)
        assert pinning.name in held["why"] and "nothing moves" in held["why"], (
            held["why"])
        assert weather_sim.pinned(exp), "the sim disagrees that they are held"
        return (f"{pinning.name} for 3 days: {clear['days']} → "
                f"{held['days']} days home, and the panel says why")

    @check("a decade of one chronicle now brings parties home")
    def _():
        # The coverage this began with. 50 stranded, 32 aborted and zero returned
        # over ten years meant `lift_off`, `can_lift` and the whole banked-haul
        # path were never driven by the long game at all.
        import collections

        from . import chronicle

        ends = collections.Counter()
        real = exp_sim.finish

        def spy(exp, how):
            ends[how] += 1
            return real(exp, how)

        exp_sim.finish = spy
        try:
            game = new_game("chronicle-ground")
            chronicle.play(game, years=6)
        finally:
            exp_sim.finish = real
        assert ends, "six years and nobody landed at all"
        assert ends.get("returned", 0) >= 3, (
            f"landings ended {dict(ends)} — the party still never walks back")
        return (f"six years: " + " · ".join(f"{n} {k}"
                                            for k, n in ends.most_common()))
