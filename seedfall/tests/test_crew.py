"""Crew checks — officers who notice how the ship is run.

An officer used to be a stat block with a wage: it modified rolls, levelled up
and never had an opinion. These hold the loyalty layer to the two promises that
make it worth having — that what you do pulls officers apart rather than
together, and that how they feel is felt at the stations.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.convictions import CONVICTIONS, RESTLESS, START, WALKOUT
from ..sim import loyalty
from ..sim import stations as st_mod
from ..sim.crew import make_officer
from .harness import Suite


def _bridge(convictions, level: int = 3, start: float = 60.0):
    """A game whose bridge holds one officer of each named conviction."""
    game = new_game("bridge")
    game.credits = 500000
    rng = RNG("bridge-mix")
    game.officers = []
    for index, cid in enumerate(convictions):
        officer = make_officer(rng, "science", level)
        officer.conviction = cid
        officer.loyalty = start
        officer.name = f"Officer {index}"
        game.officers.append(officer)
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("every conviction reacts to something the game can report")
    def _():
        # A conviction whose events are never raised is flavour text with a
        # loyalty field attached.
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[1]
        source = "\n".join(p.read_text() for p in root.rglob("*.py")
                           if p.name not in ("convictions.py", "test_crew.py"))
        unreported = []
        for conviction in CONVICTIONS:
            assert conviction.reacts, f"{conviction.id} reacts to nothing"
            for event in conviction.reacts:
                if f'"{event}"' not in source:
                    unreported.append(f"{conviction.id}:{event}")
        assert not unreported, (
            "convictions react to events nothing ever raises: "
            + ", ".join(sorted(unreported)))
        return f"{len(CONVICTIONS)} convictions, every event raised somewhere"

    @check("the same act pulls a bridge apart rather than together")
    def _():
        g = _bridge(("burner", "xenophile", "purse", "licence"))
        for event in ("bloom_kill", "bloom_kill", "bloom_cleansed", "treaty"):
            loyalty.record(g, event)
        values = [loyalty.loyalty_of(o) for o in g.officers]
        spread = max(values) - min(values)
        assert spread > 20, (
            f"four convictions ended within {spread:.0f} of each other")
        burner = next(o for o in g.officers if o.conviction == "burner")
        xeno = next(o for o in g.officers if o.conviction == "xenophile")
        assert loyalty.loyalty_of(burner) > loyalty.loyalty_of(xeno), (
            "burning the Bloom pleased the xenologist more than the veteran")
        return f"spread {spread:.0f} points across four convictions"

    @check("loyalty is felt at the crew stations, not just on the roster")
    def _():
        g = _bridge(("shipmate",), level=4)
        officer = g.officers[0]
        officer.stat = "nav"
        readings = {}
        for value in (95.0, 60.0, 20.0, 4.0):
            officer.loyalty = value
            readings[value] = st_mod.officer_level(g.officers, "nav")
        assert readings[95.0] > readings[60.0], "devotion bought nothing"
        assert readings[20.0] < readings[60.0], "restlessness cost nothing"
        assert readings[4.0] < readings[20.0], "mutiny cost nothing further"
        return " · ".join(f"{v:.0f}→{lvl:.2f}" for v, lvl in readings.items())

    @check("a year of missed payroll costs you the bridge")
    def _():
        g = new_game("unpaid")
        g.credits = 0
        started = len(g.officers)
        assert started, "no officers to lose"
        month = None
        for index in range(1, 37):
            g.advance_days(30)
            if len(g.officers) < started:
                month = index
                break
        assert month is not None, (
            f"three years unpaid and nobody left: "
            f"{[round(loyalty.loyalty_of(o)) for o in g.officers]}")
        return f"first walkout in month {month}"

    @check("paying properly keeps a bridge willing")
    def _():
        g = new_game("paid")
        g.credits = 500000
        for _ in range(12):
            g.advance_days(30)
        assert len(g.officers) == 3, "lost an officer while paying on time"
        mood = loyalty.summary(g)
        assert mood["mean"] > START, (
            f"a well-run year left them at {mood['mean']:.0f}, below the "
            f"{START:.0f} they signed on with")
        assert not mood["restless"], "someone is restless on a paid, quiet ship"
        return f"mean loyalty {mood['mean']:.0f} after a year"

    @check("what the pill says is what the officer does")
    def _():
        # The bands used to be named on their own scale, so an officer reading
        # "Mutinous" was mechanically merely restless.
        g = _bridge(("purse",))
        officer = g.officers[0]
        seen = {}
        for value in (4.0, WALKOUT + 1, RESTLESS + 1, 70.0, 92.0):
            officer.loyalty = value
            seen[loyalty.band(officer)[0]] = loyalty.effective_level(officer)
        assert seen["Mutinous"] < seen["Restless"] < seen["Steady"], (
            f"the bands do not track performance: {seen}")
        assert seen["Steady"] < seen["Willing"] < seen["Devoted"], (
            f"the good bands do not track performance: {seen}")
        officer.loyalty = WALKOUT - 1
        assert loyalty.band(officer)[0] == "Mutinous", (
            "an officer about to walk out does not read as mutinous")
        return " · ".join(f"{k} {v:.2f}" for k, v in seen.items())

    @check("convictions and loyalty survive a save and reload")
    def _():
        import json

        from ..core.save import decode, encode

        g = new_game("persist-crew")
        for officer, value in zip(g.officers, (91.0, 55.0, 19.0)):
            officer.loyalty = value
        before = [(o.id, o.conviction, o.loyalty) for o in g.officers]
        reloaded = decode(json.loads(json.dumps(encode(g))))
        after = [(o.id, o.conviction, o.loyalty) for o in reloaded.officers]
        assert before == after, f"crew changed over a save: {before} != {after}"
        assert all(loyalty.conviction_of(o) is not None for o in reloaded.officers), (
            "an officer came back believing nothing")
        return f"{len(after)} officers kept their convictions and loyalty"
