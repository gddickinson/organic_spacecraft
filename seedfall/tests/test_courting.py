"""Courting a power in front of the power it is at war with.

Measured before anything was touched: a captain with money could sit at 92,
100, 100 and 100 with all four powers **while two of those powers were at −67
with each other**. The three gift overtures — tribute, intelligence, relief —
added standing with their target and cost nothing anywhere else, so the
relations matrix was scenery. There was no side to take, and `broker`, the one
action that moves that matrix, bought nothing you could not get by ignoring it.

`sim/allegiance.py` already knew how to price this and was already wired to
contracts, treaties and territory. Gifts now go through it too: a gift is a
public act, and what it costs you is what the rift is actually worth.

Then playing it found the trap. Below −60 standing every overture was refused
and the only move left was `denounce`, which makes it worse — a captain at
−100 with unlimited credits courted a power for 120 sessions and moved them
not one point. Tribute is the door now, which is what its own blurb always
said it was.

The claims:

- **A gift is seen** by whoever the recipient is at odds with, and the
  forecast on the screen is exactly what the gift does.
- **Nobody minds when there is no rift.**
- **You cannot serve both sides of a feud** — measured, 34 against 100.
- **Brokering pays**, in what courting costs afterwards.
- **There is always a way back**, and it is slow and expensive.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.diplomacy import ACTIONS_BY_ID
from ..sim import allegiance, diplomacy as dp
from .harness import Suite

#: The three overtures that are simply a gift to one power.
GIFTS = ("tribute", "intelligence", "relief")


def _rich(seed: str):
    """A captain who can afford every overture — including `intelligence`,
    whose price is survey evidence and not money. Forgetting that quietly
    skipped a third of the forecast comparisons."""
    game = new_game(seed)
    game.credits = 500_000
    for goods in ("biomass", "survey", "volatiles"):
        game.stores[goods] = 5000
    return game


def _feud(game, a: str, b: str, value: float) -> None:
    """Hold two powers at a fixed opinion of each other."""
    dp.shift_relation(game, a, b, value - dp.relation(game, a, b))


def _court(targets, sessions: int = 40, rift: float = -70.0) -> dict:
    """Court `targets` while the Concordat and Freeholds are implacable."""
    game = _rich("dilemma")
    for _ in range(sessions):
        _feud(game, "concordat", "freeholds", rift)
        game.credits = 500_000
        for goods in ("biomass", "survey", "volatiles"):
            game.stores[goods] = 5000
        for power in targets:
            for action, ok, _why in dp.available(game, power):
                if action.id in GIFTS and ok:
                    dp.perform(game, action.id, power)
        game.advance_days(15)
        if game.dead or game.victory:
            break
    return {p: game.rep.get(p, 0) for p in ("concordat", "freeholds")}


def run(suite: Suite) -> None:
    check = suite.check

    @check("a gift is seen by whoever the recipient is at war with")
    def _():
        game = _rich("seen")
        _feud(game, "concordat", "freeholds", -70)
        before = dict(game.rep)
        res = dp.perform(game, "relief", "concordat")
        assert res["ok"], res
        gained = game.rep["concordat"] - before.get("concordat", 0)
        lost = before.get("freeholds", 0) - game.rep["freeholds"]
        assert gained > 0, "the gift bought nothing with its target"
        assert lost > 0, (
            "the Concordat and the Freeholds are implacable and a gift to one "
            "of them cost nothing with the other — the matrix is scenery")
        # Not a token gesture either: a real share of what you gained.
        assert lost >= gained * 0.4, (
            f"gained {gained:.1f} and it cost {lost:.1f} with their enemy — "
            "not enough to make anybody choose")
        assert any("Noted elsewhere" in line for line in res["lines"]), (
            f"the result never mentions who else saw it: {res['lines']}")
        return f"+{gained:.0f} with the Concordat, −{lost:.0f} with their enemy"

    @check("nobody minds a gift to a power they are not at odds with")
    def _():
        game = _rich("calm")
        for a in dp.POWERS:
            for b in dp.POWERS:
                if a != b:
                    _feud(game, a, b, 30)          # everyone getting along
        before = dict(game.rep)
        res = dp.perform(game, "relief", "concordat")
        assert res["ok"], res
        for power in dp.POWERS:
            if power == "concordat":
                continue
            assert game.rep.get(power, 0) >= before.get(power, 0) - 1e-9, (
                f"{power} is on good terms with everyone and still took "
                "offence at a relief run")
        assert not any("Noted elsewhere" in line for line in res["lines"]), (
            f"a peaceful sector still reported hurt feelings: {res['lines']}")
        # Note for whoever breaks this next: two independent guards hold it
        # up — the `value >= INDIFFERENT` early return in `severity()` and the
        # `s > 0` filter in `offended_by()`. Removing either one alone leaves
        # the other standing, so this check only bites when the filter goes.
        # That is defence in depth rather than a hole in the check.
        return "a quiet sector costs nothing to be generous in"

    @check("the forecast is exactly what the overture does")
    def _():
        checked = 0
        for gift in GIFTS:
            for power in dp.POWERS:
                game = _rich(f"fc-{gift}-{power}")
                _feud(game, "concordat", "freeholds", -55)
                said = dict(dp.preview(game, gift, power)["standing"])
                before = {p: game.rep.get(p, 0) for p in dp.POWERS}
                res = dp.perform(game, gift, power)
                if not res.get("ok"):
                    continue
                for who, delta in said.items():
                    moved = game.rep.get(who, 0) - before[who]
                    # Standing clamps at ±100; only compare where it did not.
                    if abs(game.rep.get(who, 0)) >= 99.9:
                        continue
                    assert abs(moved - delta) < 0.05, (
                        f"{gift} to {power}: the screen promised {who} "
                        f"{delta:+.1f} and it moved {moved:+.1f}")
                    checked += 1
        assert checked > 20, checked
        return f"{checked} promised movements, every one landing as stated"

    @check("you cannot serve both sides of a feud")
    def _():
        # The measurement the whole change exists for. Held at an implacable
        # rift so drift cannot quietly wash it out mid-experiment.
        both = _court(("concordat", "freeholds"))
        one = _court(("concordat",))
        assert one["concordat"] > 80, (
            f"committing to one side only reached {one['concordat']:.0f} — "
            "picking a side has to actually work")
        # The gap, not the absolute figure: even-handedness currently lands
        # at 69 against a Kin threshold of 70, and asserting *that* would be a
        # check balanced on one point of standing.
        assert both["concordat"] < one["concordat"] - 25, (
            f"courting both sides reached {both['concordat']:.0f} against "
            f"{one['concordat']:.0f} for picking one — even-handedness costs "
            "almost nothing, so there is no side to take")
        for power, value in both.items():
            assert value < 80, (
                f"courting both sides of an implacable feud still got "
                f"{power} to {value:.0f} — you can be everyone's friend")
        return (f"serving one: {one['concordat']:.0f} (and "
                f"{one['freeholds']:.0f} with the other side) · trying to "
                f"serve both: {both['concordat']:.0f} and "
                f"{both['freeholds']:.0f}, neither at Kin")

    @check("brokering a feud makes both sides cheaper to court")
    def _():
        # `broker` moved a number nothing read. This is its purpose.
        game = _rich("payoff")
        _feud(game, "concordat", "freeholds", -60)

        def toll() -> float:
            return -sum(d for _p, d in dp.preview(game, "relief", "concordat")
                        ["standing"] if d < 0)

        angry = toll()
        _feud(game, "concordat", "freeholds", 20)     # settled
        settled = toll()
        assert angry > 0, "an implacable feud costs nothing to court across"
        assert settled < angry * 0.5, (
            f"courting the Concordat costs {angry:.1f} standing elsewhere "
            f"during the feud and {settled:.1f} after it is settled — "
            "brokering buys nothing")
        return (f"courting across the feud costs {angry:.1f}; once brokered, "
                f"{settled:.1f}")

    @check("there is always a way back, and it is slow")
    def _():
        # Found by playing: below -60 every overture was refused and the only
        # move left was `denounce`. A captain at the floor with unlimited
        # credits courted a power for 120 sessions and gained nothing at all.
        game = _rich("floor")
        game.rep["freeholds"] = -100
        open_now = [a.id for a, ok, _w in dp.available(game, "freeholds") if ok]
        assert [i for i in open_now if i != "denounce"], (
            "at the floor the only thing you can do to a power is denounce "
            "them, which makes it worse — there is no way back")

        days = 0
        while days < 3000 and game.rep["freeholds"] < 0:
            game.credits = 900_000
            for goods in ("biomass", "survey", "volatiles"):
                game.stores[goods] = 9000
            for action, ok, _why in dp.available(game, "freeholds"):
                if action.id in GIFTS and ok:
                    dp.perform(game, action.id, "freeholds")
            game.advance_days(15)
            days += 15
            if game.dead or game.victory:
                break
        assert game.rep["freeholds"] >= 0, (
            f"{days} days of steady tribute from the floor and they are still "
            f"at {game.rep['freeholds']:.0f}")
        assert days > 300, (
            f"climbing out of total disgrace took {days} days — falling out "
            "with a power has to mean something")
        return f"−100 back to nothing took {days} days of tribute"

    @check("the screen states the whole price before you commit")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = _rich("screen")
        _feud(game, "concordat", "freeholds", -70)
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("diplomacy")
        for _ in range(3):
            app.processEvents()
        view = win.views["diplomacy"]
        for button in view.findChildren(QPushButton):
            if button.text().strip() == "Concordat":
                button.click()
                break
        for _ in range(3):
            app.processEvents()
        rows = [lab.text() for lab in view.findChildren(QLabel) if lab.text()]
        win.close()

        # The gain and the cost both on the card, and the cost named.
        assert any("standing" in r and r.strip().startswith("+") for r in rows), (
            "no card states what an overture buys")
        assert any("standing" in r and r.strip().startswith("-") for r in rows), (
            "the cards state what a gift buys and never what it costs "
            "elsewhere — the captain finds out afterwards")
        expected = -dp.preview(game, "relief", "concordat")["standing"][1][1]
        assert any(f"-{expected:.0f} standing" in r for r in rows), (
            f"no row shows the {expected:.0f} standing this costs with the "
            "Freeholds")
        return "gain and price both on the card, per power"

    @check("a gift with nothing to gain costs nobody anything")
    def _():
        # `price()` is asked for a weight; a zero or negative one must not
        # invent a charge out of nowhere.
        game = _rich("zero")
        _feud(game, "concordat", "freeholds", -70)
        assert allegiance.price(game, "concordat", 0) == []
        assert allegiance.price(game, "concordat", -5) == []
        # And `denounce`, which gains nothing, keeps its own arithmetic rather
        # than picking up an allegiance charge on top.
        assert ACTIONS_BY_ID["denounce"].gain == 0
        moved = dp.preview(game, "denounce", "charter", "freeholds")["standing"]
        assert all(who != "concordat" or delta > 0 for who, delta in moved), (
            f"denouncing the Freeholds charged us with the Concordat, who "
            f"dislike them: {moved}")
        return "no gain, no charge"
