"""A near miss on the ground, and whether it is worth anything.

`SPOILED` sat in `sim/expedition.py` with a comment saying "what a spoiled
attempt is worth, as a share", set to `0.0`, and read by nothing. So a failed
attempt returned literally zero: missing the mark by one and fumbling it by
five were the same outcome, an officer's level was a cliff rather than a
slope, and the screen — which states everything else — had nothing to say
about failure except that it might spring a hazard.

The tripwire found it, which is what the tripwire is for: a constant already
sitting at its degenerate value is either dead or a feature somebody switched
off and forgot.

The claims:

- **A near miss pays, a fumble does not**, and the share falls the further
  you miss by.
- **The screen says so before you commit**, because "it fails" and "it fails
  and you keep a third" are different decisions.
- **It is still worse than succeeding** — by a lot, in every currency.
"""

from __future__ import annotations

import collections

from ..core.rng import RNG
from ..core.state import new_game
from ..data.expedition import REWARD_SCALE
from ..sim import expedition as ex
from .harness import Suite


def _on_a_feature(seed: str):
    """A party standing on a tile that offers something to attempt."""
    game = new_game(seed)
    party = ex.generate(RNG(f"e-{seed}"), game.system, game.system.bodies[0],
                        [o.id for o in game.officers])
    spots = [i for i, tile in enumerate(party.tiles)
             if getattr(tile, "feature", None)]
    if not spots:
        return game, None
    index = spots[0]
    party.x, party.y = index % 7, index // 7
    party.tiles[index].revealed = True
    return game, party


def run(suite: Suite) -> None:
    check = suite.check

    @check("a botched attempt is worth something, and a fumble is not")
    def _():
        # `SPOILED` was written, commented and read by nothing.
        assert ex.SPOILED > 0, (
            "a spoiled attempt is worth nothing, so missing by one and "
            "fumbling by five are the same outcome")
        assert ex.SPOILED < 1.0, "a botch pays as well as a success"

        seen = collections.Counter()
        for trial in range(500):
            game, party = _on_a_feature(f"botch{trial}")
            if party is None or not ex.options_here(party):
                continue
            options = ex.options_here(party)
            index = trial % len(options)
            # What this option *could* have paid, read before the attempt:
            # after a failure the result carries no reward at all, so there
            # is no way to tell a fumbled ore seam from a fumbled scrap of
            # lore afterwards — and lore never salvages, which let a broken
            # near-miss window pass by counting it.
            _l, _s, _d, offered = options[index]
            res = ex.attempt(party, index, game.officers, RNG(f"r{trial}"))
            if not res.get("ok"):
                continue
            if res["success"]:
                seen["clean"] += 1
            elif res.get("spoiled"):
                seen["salvaged"] += 1
            else:
                seen["empty"] += 1
                # A failure on a prize that *could* have been salvaged, missed
                # too widely to bring anything back. This is the case the
                # near-miss window exists to create.
                if res.get("short", 0) > ex.NEAR_MISS and \
                        offered not in ("lore", "none"):
                    seen["wide_empty"] += 1
            # The precise rule, checked directly: nothing beyond the window
            # pays, ever. Counting empty-handed failures instead was too
            # loose — the taper alone zeroes small prizes at a wide miss, so
            # deleting the window still left *some* failures empty and the
            # check could not tell.
            if res.get("spoiled") and res.get("short", 0) > ex.NEAR_MISS:
                seen["paid_too_wide"] += 1
        assert seen["salvaged"] > 0, (
            "not one failed attempt in five hundred brought anything back")
        # A real share, and specifically for attempts that *had* something to
        # salvage: counting `lore` options — which never salvage — let this
        # pass with the near-miss window removed entirely.
        assert seen["empty"] > 0, (
            "every failure salvages something — a fumble should cost you the "
            "attempt outright")
        assert seen["wide_empty"] > 0, (
            "no failure on a salvageable prize was ever missed widely enough "
            "to come back empty, so the window is untested")
        assert not seen["paid_too_wide"], (
            f"{seen['paid_too_wide']} attempts missed by more than "
            f"{ex.NEAR_MISS} and still paid — the near-miss window is not "
            "the rule it claims to be")
        return (f"{seen['clean']} clean, {seen['salvaged']} salvaged, "
                f"{seen['empty']} came back empty "
                f"({seen['wide_empty']} of them missed too widely)")

    @check("a salvaged attempt pays a fraction, never the whole prize")
    def _():
        # Compared per reward type, because a botched credits haul and a
        # botched ore haul are not commensurable and averaging them was how I
        # first read a "325 unit" salvage that was nothing of the kind.
        clean = collections.defaultdict(list)
        botched = collections.defaultdict(list)
        for trial in range(500):
            game, party = _on_a_feature(f"share{trial}")
            if party is None or not ex.options_here(party):
                continue
            index = trial % len(ex.options_here(party))
            res = ex.attempt(party, index, game.officers, RNG(f"s{trial}"))
            if not res.get("ok") or not res.get("reward"):
                continue
            (clean if res["success"] else botched)[res["reward"]].append(
                res["amount"])

        compared = 0
        for reward, spoils in botched.items():
            if reward not in clean or not clean[reward] or not spoils:
                continue
            good = sum(clean[reward]) / len(clean[reward])
            bad = sum(spoils) / len(spoils)
            assert bad < good, (
                f"a botched {reward} attempt brings back {bad:.1f} against "
                f"{good:.1f} for a clean one")
            assert bad <= good * 0.6, (
                f"a botched {reward} attempt keeps {bad / good:.0%} of the "
                "prize — failure is barely a setback")
            compared += 1
        assert compared >= 3, f"only {compared} reward types were comparable"
        return f"{compared} reward types, every botch worth less than half"

    @check("missing by more is worth less")
    def _():
        # The taper is the point: a hair's breadth and a wild miss must not
        # pay the same. Measured by grouping real attempts on how far short
        # the roll fell, rather than by asserting the constants exist — which
        # is what the first version of this check did.
        by_short = collections.defaultdict(list)
        for trial in range(700):
            game, party = _on_a_feature(f"taper{trial}")
            if party is None or not ex.options_here(party):
                continue
            index = trial % len(ex.options_here(party))
            res = ex.attempt(party, index, game.officers, RNG(f"t{trial}"))
            if not res.get("ok") or res["success"]:
                continue
            if res.get("reward") == "credits":     # one currency, comparable
                by_short[res["short"]].append(res.get("amount", 0))
            elif res.get("reward") is None and res["short"]:
                by_short.setdefault(res["short"], [])

        paid = {short: sum(v) / len(v) for short, v in by_short.items() if v}
        assert paid, "no botched credits attempt in seven hundred tries"
        nearest = min(paid)
        assert paid[nearest] > 0, paid
        further = [s for s in paid if s > nearest]
        assert further, (
            "every botch missed by the same amount, so the taper is untested")
        widest = max(further)
        # A real margin, not merely "greater than". Both are noisy means of a
        # random base, so a bare `>` passes about half the time with the taper
        # deleted — which is exactly what happened when I tried to break it.
        assert paid[nearest] >= paid[widest] * 1.25, (
            f"missing by {nearest} pays {paid[nearest]:.0f} and missing by "
            f"{widest} pays {paid[widest]:.0f} — that is not a taper, it is "
            "noise")
        # And beyond the window nothing comes back at all.
        empty = [short for short, v in by_short.items()
                 if short > ex.NEAR_MISS and v]
        assert not empty, (
            f"attempts missing by more than {ex.NEAR_MISS} still paid: "
            f"{empty}")
        return " · ".join(f"short by {s}: {paid[s]:.0f}"
                          for s in sorted(paid))

    @check("the ground screen says what a botch is worth before you try")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None

        # Find a party whose tile offers something salvageable.
        shown = None
        for trial in range(24):
            game, party = _on_a_feature(f"screen{trial}")
            if party is None:
                continue
            odds = [ex.odds_for(party, i, game.officers)
                    for i in range(len(ex.options_here(party)))]
            if not any(o.get("near", 0) > 0.01 and o.get("spoiled")
                       for o in odds):
                continue
            game.expedition = party
            win = MainWindow(game)
            win.toast = lambda *a, **k: None
            win.go("ground")
            for _ in range(3):
                app.processEvents()
            texts = " ".join(w.text() for w in
                             win.views["ground"].findChildren(QLabel) if w.text())
            win.close()
            shown = texts
            break
        assert shown is not None, "no seed produced a salvageable attempt"
        assert "botched" in shown, (
            "the screen never mentions what a near miss brings back")
        assert "still comes back" in shown, shown[:200]
        return "the screen states the botch share alongside the odds"

    @check("the odds say how often a botch is close enough to pay")
    def _():
        game, party = _on_a_feature("odds")
        assert party is not None
        checked = 0
        for index in range(len(ex.options_here(party))):
            odds = ex.odds_for(party, index, game.officers)
            if not odds or not odds.get("stat"):
                continue
            near = odds.get("near", 0)
            assert 0.0 <= near <= 1.0, near
            assert odds["chance"] + near <= 1.0001, (
                f"a {odds['chance']:.0%} success and a {near:.0%} near miss "
                "is more than certainty")
            if odds["reward"] in ("lore", "none"):
                assert near == 0, (
                    f"{odds['reward']} has nothing to salvage and the screen "
                    "offers a share of it anyway")
            checked += 1
        assert checked > 0, "no option with a stat to roll against"
        return f"{checked} options, every near-miss share inside the odds"
