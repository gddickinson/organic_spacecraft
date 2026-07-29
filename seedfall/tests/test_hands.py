"""The hands: whether the people without names get older, and can be replaced.

A player asked why hands have no ages. Because `ship.crew` was an integer —
a headcount with nothing to hang an age on — so "your crew ages on a long
crossing" was true of the three named officers and of nobody else aboard. A
twenty-year chronicle retired the bridge and left the lower decks untouched,
and sleeping the hands through a crossing saved something no number recorded.

They were also unreplaceable. `ship.crew` moved in exactly one direction:
down, through fighting, hunger, and sleeps somebody did not come up from.
There was no way to sign anybody on at all.

The claims:

- **The mess deck ages** at the lineage's rate, and dormancy slows it exactly
  as it slows an officer's.
- **They age out**, gradually, as the spread carries part of the deck past the
  lineage's span — not all at once.
- **They can be replaced**, at a price, within the berths that exist, and a
  young intake pulls the average down.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import dormancy, lifespan
from .harness import Suite


def _fed(seed: str, years: float, sign_every: int = 0):
    """Run a chronicle with the larder kept full, stopping if it ends."""
    game = new_game(seed)
    game.credits = 400000
    for month in range(int(years * 12)):
        game.stores["biomass"] = 500
        game.advance_days(30)
        if game.dead or game.victory:
            break
        if sign_every and month % (sign_every * 12) == sign_every * 12 - 1:
            lifespan.sign_on(game, min(6, lifespan.berths_free(game)))
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("the hands have an age, and it is not the officers'")
    def _():
        game = new_game("has-age")
        read = lifespan.crew_profile(game)
        assert read["count"] > 0, "nobody is aboard at all"
        assert read["mean"] > 0, (
            "the mess deck has no age — `ship.crew` is a number and nothing "
            "else, which is the whole defect")
        assert 1.0 <= read["spread"] <= 40.0, (
            f"the mess deck's ages spread by {read['spread']:.0f} years — "
            "either one cohort to the day, or three generations aboard")
        assert read["mean"] < read["span"], (
            f"a fresh crew averages {read['mean']:.0f} against a span of "
            f"{read['span']:.0f}")
        return lifespan.crew_note(game)

    @check("a long chronicle ages the mess deck, not only the bridge")
    def _():
        game = _fed("aged", 30)
        years = game.day / 365.0
        start = lifespan.LINEAGES_BY_ID[
            lifespan.of_stock(getattr(game.beginning, "stock", None))
        ].prime * 0.55
        moved = game.ship.crew_age - start
        assert years > 4, f"the chronicle only ran {years:.1f} years"
        assert moved > years * 0.7, (
            f"{years:.0f} years passed and the hands aged {moved:.1f} — the "
            "lower decks are still standing outside time")
        return (f"{years:.0f} years: the mess deck went from {start:.0f} to "
                f"{game.ship.crew_age:.0f}")

    @check("hands age out gradually rather than all at once")
    def _():
        # The spread is what makes this a slope. Without it the whole deck
        # crosses the span on the same day and the hull empties in one tick.
        game = new_game("outlive")
        game.credits = 400000
        lineage = lifespan.crew_profile(game)["lineage"]
        game.ship.crew_age = lineage.span - 4.0
        game.ship.crew = 40
        counts = []
        for _ in range(30):
            game.stores["biomass"] = 500
            game.advance_days(365)
            if game.dead or game.victory:
                break
            counts.append(game.ship.crew)
        assert counts, "the chronicle ended before anybody could age out"
        assert counts[-1] < 40, (
            f"forty hands started four years short of the span and "
            f"{counts[-1]} are still aboard {len(counts)} years later")
        drops = [a - b for a, b in zip(counts, counts[1:]) if a > b]
        assert len(drops) >= 2, (
            f"the deck emptied in {len(drops)} step(s) — that is a cliff, "
            "not a crew ageing out")
        # And the pace is sane in absolute terms: a deck that far past its
        # span should be gone within a working lifetime, not a century, and
        # not inside a single year.
        assert len(counts) >= 2, "the deck emptied before the second year"
        assert counts[-1] <= 40 * 0.5, (
            f"{counts[-1]} of 40 remain after {len(counts)} years past the "
            "span — they are not leaving at any real rate")
        return (f"40 hands fell to {counts[-1]} over {len(counts)} years, in "
                f"{len(drops)} separate losses")

    @check("sleeping through a crossing slows the hands too")
    def _():
        # The saving used to be unmeasurable for the hands, which is exactly
        # why last cycle's `put_under` bug hid: nothing about them was
        # measured.
        awake = new_game("hands-awake")
        under = new_game("hands-under")
        under.research.unlocked.append("trehalose")
        under.stores.update({"trehalose": 900, "biomass": 900})
        awake.stores["biomass"] = 900
        dormancy.put_under(under, "vitrify",
                           dormancy.most_that_can_sleep(under))
        start = lifespan.crew_profile(awake)["mean"]
        for game in (awake, under):
            game.stores["biomass"] = 900
            game.advance_days(365)
        aged_awake = awake.ship.crew_age - start
        aged_under = under.ship.crew_age - start
        assert aged_awake > 0.8, aged_awake
        assert aged_under < aged_awake * 0.5, (
            f"a sleeping mess deck aged {aged_under:.2f} against "
            f"{aged_awake:.2f} awake — the saving does not reach them")
        return (f"a year: {aged_awake:.2f} years on the hands awake, "
                f"{aged_under:.2f} with most of them under")

    @check("hands can be signed on, within the berths that exist")
    def _():
        game = new_game("signon")
        game.credits = 400000
        before = game.ship.crew
        room = lifespan.berths_free(game)
        assert room > 0, "a fresh hull has no room for anybody"

        over, why = lifespan.can_sign_on(game, room + 50)
        assert not over and "berth" in why.lower(), why

        paid = game.credits
        res = lifespan.sign_on(game, 8)
        assert res["ok"], res
        assert game.ship.crew == before + 8, game.ship.crew
        # Against a figure written here, not against `SIGNING_FEE` — asserting
        # `spent == SIGNING_FEE * 8` reads the constant under test and passes
        # whatever it is set to, which is the habit this suite exists to stop.
        # The tripwire caught it on this very check.
        spent = paid - game.credits
        assert 8 * 40 <= spent <= 8 * 6000, (
            f"eight hands cost {spent:,} credits — either free labour or a "
            "hull's worth of wages")
        assert lifespan.berths_free(game) == room - 8

        # And with no money, nobody signs.
        game.credits = 0
        broke, why2 = lifespan.can_sign_on(game, 4)
        assert not broke and "credit" in why2.lower(), why2
        return (f"{before} → {game.ship.crew} hands for "
                f"{lifespan.SIGNING_FEE * 8:,} credits, {room - 8} berths left")

    @check("a young intake pulls the average down")
    def _():
        game = new_game("intake")
        game.credits = 400000
        game.ship.crew_age = 80.0
        game.ship.crew = 20
        before = game.ship.crew_age
        lifespan.sign_on(game, 20)
        after = game.ship.crew_age
        assert after < before - 5, (
            f"twenty new hands moved the average from {before:.0f} to "
            f"{after:.0f}")
        # And the intake is genuinely young, judged against the span rather
        # than against the constant that sets it.
        fresh = new_game("fresh-intake")
        fresh.credits = 400000
        fresh.ship.crew = 1
        fresh.ship.crew_age = 90.0
        span = lifespan.crew_profile(fresh)["span"]
        lifespan.sign_on(fresh, 40)
        assert fresh.ship.crew_age < span * 0.5, (
            f"a fresh intake averages {fresh.ship.crew_age:.0f} against a "
            f"span of {span:.0f} — that is not an intake, it is a pension")
        assert fresh.ship.crew_age > 8, (
            f"the intake averages {fresh.ship.crew_age:.0f}; the quay is "
            "sending children")
        return (f"an old deck at {before:.0f} comes down to {after:.0f}; a "
                f"fresh intake averages {fresh.ship.crew_age:.0f} against a "
                f"{span:.0f}-year span")

    @check("the port says how old the crew is and offers to fix it")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("port-hands")
        game.credits = 60000
        system = next(s for s in game.galaxy.systems if s.port)
        game.location_id = system.id
        game.ship.crew_age = 90.0

        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.views["port"].tab = "crew"
        win.go("port")
        for _ in range(3):
            app.processEvents()
        view = win.views["port"]
        texts = " ".join(w.text() for w in view.findChildren(QLabel) if w.text())
        buttons = [b.text() for b in view.findChildren(QPushButton) if b.text()]
        assert "hands" in texts and "on average" in texts, texts[:200]
        assert "past it" in texts, "an ageing crew is not flagged"
        assert any("Sign on" in b for b in buttons), buttons
        win.close()
        return "the mess deck's age is stated, and berths can be filled"
