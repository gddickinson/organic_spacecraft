"""The Weave: instant crossings, and what they cost the sector.

A hull's jump range is ten light years. The sector is sixty-eight across with
a median pair distance of twenty-nine, so a fresh captain reaches **three
systems of forty-one** and the rest of the Verge is scenery. The interstellar
model itself is not the problem — four crossing profiles with real dilation
and a two-clock trade between reaction mass, the crew's lifespan and the work
they would otherwise have done. The problem is reach.

The Weave is nine ancient anchors, derived from the galaxy's seed by
farthest-point sampling so they are landmarks and need no save migration,
paired in a ring with chords across it. Three burn at dawn. Transit through a
lit ring is **instant** — the only act in the game that does not spend the
calendar — and pays a toll to whoever holds the far end, which is what makes
the network a political object rather than a convenience.

And it is a road for the Bloom. Measured, differenced against the same
chronicle with the carry disabled: a system on the far end of one lit ring
went from clean to **0.70 infested in 180 days**, against 0.00 without. That
is the decision the whole system exists to pose, and it is why waking an
anchor is not simply an upgrade.

The claims:

- **The same sector always grows the same Weave**, in a fresh process.
- **A ring burns only when both ends do**, so the first anchor you wake buys
  nothing at all — which is the shape of the progression.
- **Transit is instant, and the toll follows your standing.**
- **Every gate agrees with the act it guards.**
- **The Bloom crosses a lit ring**, and the measurement is differenced.
- **The Weave opens the sector**, measured against what a drive alone reaches.
"""

from __future__ import annotations

import subprocess
import sys

from ..core.state import new_game
from ..data.gates import (ANCIENT_LIT, ANCIENT_SITES, BUILD_GOODS,
                          TOLL_REFUSED_BELOW, WAKE_GOODS)
from ..sim import gates as gates_sim
from ..sim import reach as reach_sim
from ..sim import track as track_sim
from ..sim import weave as weave_sim
from ..world.galaxy import distance
from .harness import Suite


def _rich(seed: str):
    """A captain who can pay for anything, so only the rules bite."""
    game = new_game(seed)
    game.credits = 20_000_000
    game.research.unlocked = list({*game.research.unlocked, "weavecraft"})
    for goods in (WAKE_GOODS, BUILD_GOODS):
        for cid, need in goods.items():
            game.stores[cid] = need * 20
    game.recompute()
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("the same sector always grows the same Weave")
    def _():
        # Derived, like anchorages and traffic: nothing about where the
        # anchors stand is in the save, so there is no migration to write and
        # no way for two chronicles of one seed to disagree. Checked in a
        # fresh process, because a hash seeded per-run would pass in this one.
        game = new_game("weave-stable")
        mine = (weave_sim.sites(game.galaxy),
                {k: list(v) for k, v in
                 weave_sim.ancient_links(game.galaxy).items()},
                weave_sim.lit_at_dawn(game.galaxy))
        code = (
            "from seedfall.core.state import new_game;"
            "from seedfall.sim import weave;"
            "g=new_game('weave-stable');"
            "print(weave.sites(g.galaxy));"
            "print({k:list(v) for k,v in weave.ancient_links(g.galaxy).items()});"
            "print(weave.lit_at_dawn(g.galaxy))")
        done = subprocess.run([sys.executable, "-c", code],
                             capture_output=True, text=True, timeout=180)
        assert done.returncode == 0, done.stderr[-400:]
        lines = done.stdout.strip().split("\n")
        assert str(mine[0]) == lines[0], (
            f"the anchors moved between processes: {mine[0]} vs {lines[0]}")
        assert str(mine[1]) == lines[1], "the rings moved between processes"
        assert str(mine[2]) == lines[2], "what is lit moved between processes"
        assert len(mine[0]) == ANCIENT_SITES, mine[0]
        assert len(mine[2]) == ANCIENT_LIT, mine[2]

        # And they are spread, not clustered — that is what the sampling is for.
        spans = [distance(game.galaxy.systems[a], game.galaxy.systems[b])
                 for i, a in enumerate(mine[0]) for b in mine[0][i + 1:]]
        assert min(spans) > 8.0, (
            f"two anchors are {min(spans):.1f} ly apart, which is inside a "
            "starting jump range — the Weave would be pointless there")
        return (f"{len(mine[0])} anchors, identical in a second process, "
                f"nearest pair {min(spans):.0f} ly apart")

    @check("a ring burns only when both ends do")
    def _():
        # The shape of the progression, and the reason waking is a decision.
        # An anchor lit on its own is a very expensive ring standing in the
        # dark; it is the *second* one that buys anything.
        game = _rich("pairs")
        dark = [g for g in weave_sim.gates(game) if not g.lit]
        assert dark, "every anchor is already burning"
        # One whose neighbours are all dark, so lighting it can do nothing.
        lonely = next((g for g in dark
                       if all(not weave_sim.gate_at(game, o).lit
                              for o in g.links)), None)
        assert lonely is not None, "no anchor is isolated in the dark"

        game.location_id = lonely.system_id
        before = len(weave_sim.network(game))
        out = gates_sim.wake(game)
        assert out["ok"], out
        assert out["links"] == 0, (
            f"lighting an anchor whose every neighbour is dark answered with "
            f"{out['links']} ring(s)")
        assert weave_sim.gate_at(game, lonely.system_id).lit
        assert weave_sim.reachable(game, lonely.system_id) == [], (
            "an anchor alone in the dark can take you somewhere")
        assert len(weave_sim.network(game)) == before, (
            "the live network grew for an anchor with nothing to talk to")

        # Light one of its neighbours and the ring answers.
        neighbour = lonely.links[0]
        game.location_id = neighbour
        second = gates_sim.wake(game)
        assert second["ok"], second
        assert second["links"] >= 1, second
        assert lonely.system_id in weave_sim.reachable(game, neighbour), (
            "both ends are burning and the ring still does not run")
        return ("one anchor lit alone answers nothing; its neighbour lit too "
                f"and {second['links']} ring(s) run")

    @check("you cannot wake what you do not understand")
    def _():
        # `_rich` grants Weavecraft, so every other check here flies with it
        # already known — and a mutation that removed the requirement passed
        # the lot. This is the one that asks a captain who has not done the
        # reading. Weavecraft wants the metallurgy *and* the fold physics,
        # which is the ancient-and-modern mixture the system is built on.
        from ..data.tech import TECH_BY_ID

        spec = TECH_BY_ID["weavecraft"]
        assert set(spec.reqs) == {"xenoalloy", "foldrunner"}, spec.reqs

        game = new_game("unlearned")
        game.credits = 20_000_000
        for cid, need in WAKE_GOODS.items():
            game.stores[cid] = need * 20
        game.research.unlocked = [t for t in game.research.unlocked
                                  if t != "weavecraft"]
        game.recompute()
        dark = next(g for g in weave_sim.gates(game) if not g.lit)
        game.location_id = dark.system_id
        ok, why = gates_sim.can_wake(game)
        assert not ok and "knows how" in why, (ok, why)
        was = list(weave_sim.ensure(game).woken)
        assert not gates_sim.wake(game)["ok"], "woke it without the knowledge"
        assert weave_sim.ensure(game).woken == was, "it lit anyway"
        assert not gates_sim.can_build(game)[0]

        # Learn it and the same anchor answers.
        game.research.unlocked = list({*game.research.unlocked, "weavecraft"})
        assert gates_sim.can_wake(game)[0], gates_sim.can_wake(game)[1]
        assert gates_sim.wake(game)["ok"]
        return ("refused without Weavecraft, which wants Xenolith Metallurgy "
                "and the Foldrunner Coil both; granted with it")

    @check("transit is instant, and the toll follows your standing")
    def _():
        game = _rich("tolls")
        lit = weave_sim.lit_at_dawn(game.galaxy)
        game.location_id = lit[0]
        runs = weave_sim.reachable(game, game.location_id)
        assert runs, "the opening Weave goes nowhere"
        dest = runs[0]

        said = gates_sim.quote(game, dest)
        assert said["days"] == 0, (
            f"a Weave crossing costs {said['days']} days — it is supposed to "
            "be the one thing that does not spend the calendar")
        assert said["ly_saved"] > 15, said["ly_saved"]
        assert said["credits"] > 0, "the ring opened for nothing"

        # Standing moves the price, both ways. The first draft guarded this
        # whole block behind `if far.faction:` — and where the far end had no
        # owner it silently ran nothing at all, so a mutation that made the
        # toll ignore standing entirely, and one that opened the ring to a
        # power that loathed you, both went unnoticed. The far end is *given*
        # an owner now, so the rule is always exercised.
        far = game.galaxy.systems[dest]
        far.faction = far.faction or "charter"
        game.rep[far.faction] = 100
        dear = gates_sim.quote(game, dest)["credits"]
        game.rep[far.faction] = 0
        middling = gates_sim.quote(game, dest)["credits"]
        assert dear < middling * 0.75, (
            f"a power that thinks the world of you charges ₡{dear:,} against "
            f"₡{middling:,} for a stranger — standing barely moves the toll")

        # **Absolute, deliberately not `TOLL_REFUSED_BELOW - 5`.** Derived
        # from the constant, this moved with it — double the bar to -80 and
        # the standing became -85, still under, still refused, still green —
        # so the bar swept as protected while nothing held it. Where it
        # actually sits is bracketed below.
        game.rep[far.faction] = -100.0
        shut = gates_sim.quote(game, dest)
        assert not shut["ok"] and "not open" in shut["why"], (
            f"a power that loathes you opened the ring anyway: {shut}")
        assert not gates_sim.can_use(game, dest)[0]
        assert not gates_sim.use(game, dest)["ok"], (
            "refused by the quote and let through by the act")
        game.rep[far.faction] = 40

        # And the bar is where it says it is, bracketed a point either side
        # with absolute standings. Measured through `gates.toll`: the ring
        # opens at -40.0 and is shut at -40.5, so the gate is a strict `<`.
        assert TOLL_REFUSED_BELOW == -40.0, (
            f"the bar moved to {TOLL_REFUSED_BELOW}; the standings below "
            "bracket -40 with absolute values and must be re-bracketed by "
            "hand, which is the point of them")
        game.rep[far.faction] = -39.0
        assert gates_sim.quote(game, dest)["ok"], (
            "standing -39 is above the bar and the ring stayed shut")
        game.rep[far.faction] = -41.0
        assert not gates_sim.quote(game, dest)["ok"], (
            "standing -41 is under the bar and the ring opened anyway")
        game.rep[far.faction] = 40

        before_day, before_credits = game.day, game.credits
        out = gates_sim.use(game, dest)
        assert out["ok"], out
        assert game.location_id == dest, "the ring did not move the ship"
        assert game.day == before_day, (
            f"the calendar moved {game.day - before_day} days on an instant "
            "crossing")
        assert game.credits == before_credits - out["credits"], (
            "the toll charged is not the toll quoted")
        assert weave_sim.ensure(game).transits == 1
        return (f"{out['ly_saved']:.0f} light years for ₡{out['credits']:,.0f} "
                "and no time at all; standing moves the price")

    @check("every gate agrees with the act it guards")
    def _():
        # The sweep this project runs on every `can_*`. It caught a live
        # button on the berths board once; the Weave has three of them.
        import collections
        disagree: collections.Counter = collections.Counter()
        checked = 0
        for seed in range(4):
            for purse in (20_000_000, 0):
                game = _rich(f"weave-gate-{seed}")
                game.credits = purse
                for sid in [g.system_id for g in weave_sim.gates(game)][:6]:
                    game.location_id = sid
                    ok, why = gates_sim.can_wake(game)
                    got = gates_sim.wake(game)
                    checked += 1
                    if ok != bool(got.get("ok")):
                        disagree[f"can_wake: gate {ok}, act "
                                 f"{bool(got.get('ok'))} ({why[:28]})"] += 1
                    ok, why = gates_sim.can_build(game)
                    got = gates_sim.build(game)
                    checked += 1
                    if ok != bool(got.get("ok")):
                        disagree[f"can_build: gate {ok}, act "
                                 f"{bool(got.get('ok'))} ({why[:28]})"] += 1
                    for dest in weave_sim.reachable(game, sid)[:2]:
                        ok, why = gates_sim.can_use(game, dest)
                        was = game.location_id
                        got = gates_sim.use(game, dest)
                        checked += 1
                        if ok != bool(got.get("ok")):
                            disagree[f"can_use: gate {ok}, act "
                                     f"{bool(got.get('ok'))} ({why[:28]})"] += 1
                        game.location_id = was
        assert not disagree, (
            f"{sum(disagree.values())} disagreement(s): {list(disagree)[:4]}")
        assert checked > 60, checked
        return f"{checked} gate-and-act pairs across waking, laying and using"

    @check("the Bloom crosses a lit ring")
    def _():
        # Differenced against the same chronicle with the carry disabled,
        # because the sector grows its own infestation and a raw reading
        # would be measuring that.
        def played(carry: bool) -> float:
            # An anchor the captain woke, because those are the only rings
            # that carry: the ones burning at dawn have been burning for four
            # centuries and the sector's state already includes whatever they
            # spread. What changes the Verge is what you light.
            game = _rich("bloomroad")
            dark = next(g for g in weave_sim.gates(game) if not g.lit)
            game.location_id = dark.system_id
            gates_sim.wake(game)
            neighbour = next(o for o in dark.links)
            if not weave_sim.gate_at(game, neighbour).lit:
                game.location_id = neighbour
                gates_sim.wake(game)
            live = weave_sim.network(game)
            source = dark.system_id
            assert source in live, "the woken pair does not run"
            far = live[source][0]
            game.galaxy.systems[source].bloom = 0.7
            game.galaxy.systems[far].bloom = 0.0
            if not carry:
                original = gates_sim.bloom_links
                gates_sim.bloom_links = lambda _g: []
            try:
                for _ in range(6):
                    game.advance_days(30)
            finally:
                if not carry:
                    gates_sim.bloom_links = original
            return game.galaxy.systems[far].bloom

        with_ring = played(True)
        without = played(False)
        assert with_ring > without + 0.2, (
            f"a lit ring off a 70%-infested system carried {with_ring:.2f} "
            f"against {without:.2f} with the carry off — the Weave is not a "
            "road for anything but you")

        # A clean system exports nothing, so the network is not a permanent
        # leak. This has to be asked of a ring that actually *runs*: the
        # first draft woke a single anchor whose neighbours were dark, so no
        # link existed and the list came back empty whatever the floor said.
        game = _rich("bloomroad")
        dark = next(g for g in weave_sim.gates(game) if not g.lit)
        game.location_id = dark.system_id
        gates_sim.wake(game)
        neighbour = dark.links[0]
        if not weave_sim.gate_at(game, neighbour).lit:
            game.location_id = neighbour
            gates_sim.wake(game)
        assert dark.system_id in weave_sim.network(game), (
            "no ring runs, so the floor would not be exercised")
        for system in game.galaxy.systems:
            system.bloom = 0.0
        assert gates_sim.bloom_links(game) == [], (
            "a clean sector is still handing growth across the rings")
        game.galaxy.systems[dark.system_id].bloom = 0.9
        assert gates_sim.bloom_links(game), (
            "an infested system on a ring the captain lit exports nothing")

        untouched = new_game("bloomroad")
        for system in untouched.galaxy.systems:
            system.bloom = 0.9
        assert gates_sim.bloom_links(untouched) == [], (
            "a sector the captain has not touched is being charged for rings "
            "the powers have run for four hundred years")
        return (f"far end of one ring: {with_ring:.2f} infested with the "
                f"carry on, {without:.2f} with it off")

    @check("the Weave opens a sector a drive cannot")
    def _():
        # Why any of this exists, measured across seeds rather than one —
        # this project has been caught before by a conclusion that turned out
        # to be seed luck. `reach.component` is what the chart already uses
        # to say what chained jumping can get to.
        rows, opened_total = [], 0
        for seed in range(5):
            game = _rich(f"opens-{seed}")
            lit = weave_sim.lit_at_dawn(game.galaxy)
            game.location_id = lit[0]
            by_drive = set(reach_sim.component(game))
            at_dawn = set(weave_sim.reachable(game, game.location_id))
            assert at_dawn, f"seed {seed}: the opening Weave reaches nowhere"

            for gate in weave_sim.gates(game):
                if not gate.lit:
                    game.location_id = gate.system_id
                    gates_sim.wake(game)
            game.location_id = lit[0]
            full = set(weave_sim.reachable(game, game.location_id))
            drive_now = set(reach_sim.component(game))
            opened = full - drive_now
            opened_total += len(opened)
            rows.append((len(drive_now), len(full), len(opened)))
            assert full > at_dawn, (
                f"seed {seed}: waking every anchor left the network at "
                f"{len(full)} against {len(at_dawn)} at dawn")
            assert opened, (
                f"seed {seed}: a fully lit Weave opens nothing the drive "
                f"could not already hop to ({len(drive_now)} systems)")

        assert opened_total >= 15, (
            f"across five sectors the Weave opened {opened_total} systems no "
            "amount of hopping reaches, which is not worth the machinery")
        worst = min(r[2] for r in rows)
        return (" · ".join(f"drive {d}, Weave {w} ({o} new)"
                           for d, w, o in rows)
                + f" — never fewer than {worst} newly opened")

    @check("the chart draws the Weave and the panel works it")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.map_view import StarChart
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = _rich("weave-ui")
        game.location_id = weave_sim.lit_at_dawn(game.galaxy)[0]
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.resize(1400, 980)
        win.show()
        win.go("map")
        for _ in range(3):
            app.processEvents()
        text = " ".join(lab.text() for lab in win.views["map"].findChildren(QLabel)
                        if lab.text())
        assert "The Weave" in text, "the chart never mentions the Weave"
        assert "Through the ring" in text, (
            "standing on a lit anchor and the panel offers no crossing")

        chart = win.views["map"].findChild(StarChart)
        assert chart is not None
        image = chart.grab().toImage()
        gold = sum(1 for x in range(0, image.width(), 2)
                   for y in range(0, image.height(), 2)
                   if (image.pixelColor(x, y).red() > 150
                       and image.pixelColor(x, y).green() > 110
                       and image.pixelColor(x, y).blue() < 110))
        win.close()
        assert gold > 60, (
            f"only {gold} gold samples on the chart — the lit rings are not "
            "being drawn")
        return f"the panel offers crossings and {gold} samples of lit ring"
