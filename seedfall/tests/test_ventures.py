"""Taking a side in somebody else's venture, and what the screen says it costs.

The powers run ventures whether or not you are watching — an embargo, a claim
filed on a system, two of them talking in a room nobody will name — and you
may back one, work against it, or let it happen.

The panel showed the odds as they stood and two buttons. It never said that
pressing one takes a 51% venture to **81%** and the other to **21%**: a thirty
point swing either way, which is the whole reason to intervene. It priced
backing and said nothing at all about what opposing costs — which is −14
standing with the power and +8 with whoever they are against. And neither
button mentioned that being right afterwards pays again: +8 for backing a
winner, +5 with every rival for opposing a loser.

Those last two were bare numbers inside `_resolve`. They are `RIGHT_BACKED`
and `RIGHT_OPPOSED` in `data/ventures.py` now, read by the forecast and by the
outcome, which is what `TREATY_WEIGHT` was extracted to end.

The claims:

- **The preview is what intervening does.** The general one.
- **Both stances are costed**, on the screen, before either button.
- **The odds move the way the forecast says.**
- **Being right pays what was promised.**
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.factions import FACTIONS_BY_ID
from ..data.ventures import RIGHT_BACKED, RIGHT_OPPOSED, SWAY, VENTURES
from ..sim import diplomacy as dip, ventures
from .harness import Suite

KINDS = tuple(v.id for v in VENTURES)


def _with_venture(seed: str, kind: str | None = None):
    """A game with a venture running, of a given kind if one turns up."""
    game = new_game(seed)
    game.credits = 400_000
    rng = RNG(f"v-{seed}")
    for _ in range(400):
        ventures.tick(game, 30, rng)
        game.advance_days(30)
        live = [v for v in ventures.live(game)
                if kind is None or v.kind == kind]
        if live:
            return game, live[0]
        if game.dead or game.victory:
            break
    return game, None


def _rep(game) -> dict:
    return {p: game.rep.get(p, 0.0) for p in dip.POWERS}


def run(suite: Suite) -> None:
    check = suite.check

    @check("what the forecast promises is what taking a side does")
    def _():
        # The general question, over both stances and as many kinds as turn up.
        checked, kinds = 0, set()
        for kind in KINDS:
            for stance in ("back", "oppose"):
                game, venture = _with_venture(f"fc-{kind}-{stance}", kind)
                if venture is None:
                    continue
                kinds.add(kind)
                said = ventures.preview(game, venture, stance)
                was, credits = _rep(game), game.credits
                res = ventures.intervene(game, venture, stance)
                assert res.get("ok"), res
                now = _rep(game)
                for who, delta in said["rep"].items():
                    if abs(now[who]) >= 99.9:
                        continue           # clamped
                    moved = now[who] - was[who]
                    assert abs(moved - delta) < 0.05, (
                        f"{kind}/{stance}: promised {who} {delta:+.1f}, "
                        f"moved {moved:+.1f}")
                    checked += 1
                spent = game.credits - credits
                assert abs(spent - said["credits"]) < 1, (
                    f"{kind}/{stance}: promised {said['credits']:+,} credits, "
                    f"moved {spent:+,}")
                checked += 1
                # And the odds land where the forecast said they would.
                assert abs(ventures.odds(game, venture)
                           - said["odds_after"]) < 1e-9, (
                    f"{kind}/{stance}: promised odds "
                    f"{said['odds_after']:.0%}, got "
                    f"{ventures.odds(game, venture):.0%}")
                checked += 1
        assert len(kinds) >= 4, sorted(kinds)
        assert checked > 25, checked
        return (f"{checked} promised movements over {len(kinds)} kinds, "
                "every one landing")

    @check("taking a side moves the odds, and by how much is stated")
    def _():
        game, venture = _with_venture("sway")
        assert venture is not None
        plain = ventures.odds(game, venture)
        backed = ventures.preview(game, venture, "back")
        against = ventures.preview(game, venture, "oppose")
        assert backed["odds_after"] > plain, (backed["odds_after"], plain)
        assert against["odds_after"] < plain, (against["odds_after"], plain)
        # The stated swing is the real one, not a decoration beside it.
        assert abs((backed["odds_after"] - plain) - SWAY) < 1e-9 \
            or backed["odds_after"] >= 0.949, (
            f"backing moved the odds {backed['odds_after'] - plain:+.2f} "
            f"against a sway of {SWAY}")
        assert backed["odds_now"] == plain and against["odds_now"] == plain
        return (f"{plain:.0%} as it stands · {backed['odds_after']:.0%} "
                f"backed · {against['odds_after']:.0%} opposed")

    @check("opposing is costed too, not only backing")
    def _():
        # The panel priced one button and left the other bare.
        game, venture = _with_venture("both")
        assert venture is not None
        against = ventures.preview(game, venture, "oppose")
        assert against["rep"], "opposing costs nothing with anybody"
        assert against["rep"][venture.power] < 0, (
            f"working against {venture.power} costs nothing with them")
        assert against["credits"] == 0, (
            "opposing takes credits — the panel prices only backing")
        if venture.other:
            assert against["rep"].get(venture.other, 0) > 0, (
                "opposing a venture aimed at somebody buys nothing with them")
        return " · ".join(f"{FACTIONS_BY_ID[w].short} {d:+.0f}"
                          for w, d in against["rep"].items())

    @check("being right afterwards pays what was promised")
    def _():
        # End to end through `_resolve`, which reads the same constants the
        # forecast does — they were bare numbers in the function body.
        seen = {"backed": 0, "opposed": 0}
        for trial in range(40):
            for stance in ("back", "oppose"):
                game, venture = _with_venture(f"right{trial}-{stance}")
                if venture is None:
                    continue
                said = ventures.preview(game, venture, stance)
                ventures.intervene(game, venture, stance)
                was = _rep(game)
                ventures._resolve(game, venture, RNG(f"res{trial}{stance}"))
                now = _rep(game)
                if venture.stance == "backed" and venture.succeeded:
                    moved = now[venture.power] - was[venture.power]
                    assert moved >= RIGHT_BACKED - 0.01, (
                        f"backed a venture that came off and gained "
                        f"{moved:+.1f}, promised {RIGHT_BACKED:+.0f}")
                    assert said["if_right"].get(venture.power) == RIGHT_BACKED
                    seen["backed"] += 1
                elif venture.stance == "opposed" and not venture.succeeded:
                    for who, delta in said["if_right"].items():
                        if abs(now[who]) >= 99.9:
                            continue
                        assert now[who] - was[who] >= delta - 0.01, (
                            f"{who}: promised {delta:+.0f} for being right, "
                            f"moved {now[who] - was[who]:+.1f}")
                    seen["opposed"] += 1
            if seen["backed"] and seen["opposed"]:
                break
        assert seen["backed"] and seen["opposed"], seen
        return (f"{seen['backed']} backed winners and {seen['opposed']} "
                "opposed losers, each paid as forecast")

    @check("a side once taken cannot be taken again")
    def _():
        game, venture = _with_venture("once")
        assert venture is not None
        assert ventures.intervene(game, venture, "back")["ok"]
        for stance in ("back", "oppose"):
            again = ventures.intervene(game, venture, stance)
            assert not again.get("ok"), (
                f"{stance} was allowed after already taking a side")
        venture.resolved = True
        assert not ventures.can_intervene(game, venture, "back")[0]
        return "one side, once, and nothing after it settles"

    @check("the panel states both stances before either button")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
        from ..ui import ventures_panel

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game, venture = _with_venture("screen")
        assert venture is not None

        class _View:
            def take_side(self, _v, _s):
                pass

        panel = ventures_panel.build(_View(), game)
        holder = QWidget()
        QVBoxLayout(holder).addWidget(panel)
        for _ in range(3):
            app.processEvents()
        rows = [lab.text() for lab in holder.findChildren(QLabel) if lab.text()]
        blob = " ".join(rows)

        assert "If you back it" in rows, "the panel does not cost backing"
        assert "If you work against it" in rows, (
            "the panel offers a button to work against it and never says what "
            "that costs")
        for stance in ("back", "oppose"):
            plan = ventures.preview(game, venture, stance)
            arrow = (f"{round(plan['odds_now'] * 100)}% → "
                     f"{round(plan['odds_after'] * 100)}%")
            assert arrow in blob, (
                f"the panel never states that {stance} moves the odds "
                f"{arrow}")
        return "both stances costed, odds stated, before either button"
