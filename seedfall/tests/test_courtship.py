"""What an overture is worth to a power that already likes you.

Nothing in diplomacy had a diminishing return. `gain` was a flat number on the
action, multiplied by the ship's diplomacy bonus and handed over: forty tonnes
of biomass moved a power sitting at 95 exactly as far as one sitting at 0.

Measured by playing it — a captain with money doing nothing but pressing the
four buttons on the diplomacy screen, never leaving port, never taking a
risk — **the Concord arrived on day 855.** Two and a third years for the
sector's whole political condition, at 460,000 credits and 1,270 tonnes of
biomass, and it landed on day 855, 930 and 840 across three sectors: not a
challenge, a shopping list on a cooldown timer. All four powers finished
pinned at the ceiling, 100 apiece.

`courtship()` is the curve, squared so that the early climb is untouched and
the last stretch is where the work is. Three relief parcels still carry a
stranger to Correct; Kin costs eleven where a flat rate charged seven. The
same captain now takes 3.2 years, spends 576,000–628,000 credits and about
1,700 tonnes, and finishes with the powers sitting *at* Kin — 70 to 73 —
rather than pinned at the ceiling, because past Kin there is little worth
buying.

The floor is 0.30 and must not go lower. Standing erodes on its own: the
sector's churn takes a power at 90 down to 83 inside two years. At floors of
0.08 and 0.15 an ally could no longer be held there at all, and
`test_politics`'s determined broker reached the Concord in two games of four
— an ending made unreachable is a worse fault than one made too cheap.

`offer_gain()` is the other half. `preview` and `perform` each carried their
own copy of the gain expression, which is the arrangement that has previously
produced a free treaty, an ungranted favour and a phantom haggle payment in
this same file. One function decides it now, and this suite holds it there.

The claims:

- **Nothing computes an overture's worth except `offer_gain`.** The general
  one, asked of the source, so a third door cannot appear.
- **What the screen promises is what the overture does**, swept over every
  action, every power and every standing.
- **An overture is worth less to a power that already thinks well of you**,
  measured by playing rather than read off the curve.
- **Courting a stranger still costs what it always did.**
- **The screen says why the numbers got small.**
"""

from __future__ import annotations

import pathlib
import re

from ..core.state import new_game
from ..data.diplomacy import ACTIONS, ACTIONS_BY_ID, COURTSHIP_KNEE
from ..sim import diplomacy as dip
from .harness import Suite

#: Any other reading of an action's declared gain. `offer_gain` is the one
#: sanctioned place, the way `ship.add_heat` is for heat.
RAW = re.compile(r"\.gain\b")


def _sources():
    root = pathlib.Path(__file__).resolve().parent.parent
    for folder in ("sim", "core", "world", "ui", "bridge", "data"):
        for path in (root / folder).rglob("*.py"):
            yield path


def _rich(seed: str, standing: float | None = None):
    """A captain who can afford any overture, at a chosen standing."""
    game = new_game(seed)
    game.credits = 5_000_000
    game.ship.cargo.update({"survey": 999, "biomass": 999})
    if standing is not None:
        for power in dip.POWERS:
            game.rep[power] = float(standing)
    return game


def _parcels_to(target: float, start: float = 0.0) -> int:
    """Relief parcels needed to carry one power from `start` to `target`."""
    game = _rich("climb")
    game.rep["concordat"] = float(start)
    action = ACTIONS_BY_ID["relief"]
    count = 0
    while game.rep["concordat"] < target and count < 500:
        game.adjust_rep("concordat", dip.offer_gain(game, action, "concordat"))
        count += 1
    assert game.rep["concordat"] >= target, (
        f"never reached {target} from {start} in 500 parcels")
    return count


def run(suite: Suite) -> None:
    check = suite.check

    @check("nothing decides what an overture buys except offer_gain")
    def _():
        # The general question, asked of the source. Two copies of this
        # expression is exactly how the treaty came to be free through one
        # door and priced through the other.
        raw = []
        for path in _sources():
            if path.name == "diplomacy.py" and path.parent.name == "sim":
                continue                      # where `offer_gain` itself lives
            if path.name == "diplomacy.py" and path.parent.name == "data":
                continue                      # where `gain` is declared
            for number, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), 1):
                if RAW.search(line):
                    raw.append(f"{path.name}:{number}")
        assert not raw, (
            f"{len(raw)} place(s) read an action's gain without the courtship "
            f"curve: {raw}")
        # And inside `sim/diplomacy.py` there is exactly one such reading.
        body = (pathlib.Path(__file__).resolve().parent.parent
                / "sim" / "diplomacy.py").read_text(encoding="utf-8")
        inside = [l.strip() for l in body.splitlines() if RAW.search(l)]
        assert len(inside) == 1, (
            f"{len(inside)} readings of `gain` in sim/diplomacy.py, so the "
            f"forecast and the act can drift apart again: {inside}")
        return "one place decides what an overture is worth"

    @check("what the screen promises is what the overture does")
    def _():
        # Swept over every action, every power and five standings, because
        # the courtship curve is applied where the promise is made and the
        # promise is what the panel draws.
        bad, checked = [], 0
        for standing in (-80.0, 0.0, 30.0, 60.0, 90.0):
            for action in ACTIONS:
                for who in dip.POWERS:
                    game = _rich(f"agree{standing:.0f}", standing)
                    other = next(p for p in dip.POWERS if p != who)
                    said = dip.preview(game, action.id, who, other)
                    was = {p: game.rep.get(p, 0.0) for p in dip.POWERS}
                    if not dip.perform(game, action.id, who, other).get("ok"):
                        continue
                    for power, delta in said["standing"]:
                        if abs(was[power] + delta) >= 100:
                            continue           # clamped at the ceiling
                        moved = game.rep.get(power, 0.0) - was[power]
                        checked += 1
                        if abs(moved - delta) > 0.05:
                            bad.append(f"{action.id}/{who}@{standing:.0f}: "
                                       f"promised {power} {delta:+.2f}, "
                                       f"moved {moved:+.2f}")
        assert not bad, f"{len(bad)} forecast(s) the act did not honour: {bad}"
        assert checked > 150, checked
        return f"{checked} promised movements over five standings, all landing"

    @check("an overture is worth less to a power that already likes you")
    def _():
        # Measured by performing the same act, not by reading the curve.
        rows, seen = [], []
        for action in ACTIONS:
            if not action.gain:
                continue                      # denounce buys nothing directly
            moved = []
            for standing in (0.0, 50.0, 85.0):
                game = _rich(f"less{action.id}", standing)
                was = game.rep.get("concordat", 0.0)
                res = dip.perform(game, action.id, "concordat", "charter")
                if not res.get("ok"):
                    moved = []
                    break
                moved.append(game.rep.get("concordat", 0.0) - was)
            if len(moved) != 3:
                continue
            seen.append(action.id)
            assert moved[0] > moved[1] > moved[2] + 1e-9, (
                f"{action.id}: an overture moves a stranger {moved[0]:+.2f}, a "
                f"friend {moved[1]:+.2f} and an ally {moved[2]:+.2f} — "
                "goodwill costs the same at every standing")
            rows.append(f"{action.id} {moved[0]:+.1f}/{moved[1]:+.1f}"
                        f"/{moved[2]:+.1f}")
        assert len(seen) >= 3, seen
        return "at 0/50/85 standing: " + " · ".join(rows)

    @check("courting a stranger still costs what it always did")
    def _():
        # The curve must not have been paid for by making the opening tedious.
        # Below the knee an overture is worth exactly its declared value.
        game = _rich("stranger", 0.0)
        for action in ACTIONS:
            if not action.gain:
                continue
            full = action.gain * (1 + game.ship_stats.diplomacy)
            assert abs(dip.offer_gain(game, action, "concordat") - full) < 1e-9, (
                f"{action.id} is discounted at zero standing")
        assert abs(dip.courtship(COURTSHIP_KNEE) - 1.0) < 1e-9
        # And the early climb is the same handful of parcels it always was.
        early = _parcels_to(COURTSHIP_KNEE)
        assert early <= 3, (
            f"{early} relief parcels merely to be noticed — the opening has "
            "been made a grind")
        return (f"{early} parcels to {COURTSHIP_KNEE:g} standing, at full "
                "declared value throughout")

    @check("reaching Kin is an investment, not a formality")
    def _():
        # The case the curve exists for. At a flat rate the whole climb to the
        # Concord standing was seven parcels; anything that cheap cannot be
        # the sector's political condition.
        flat = -(-int(dip.CONCORD_STANDING) // int(ACTIONS_BY_ID["relief"].gain))
        real = _parcels_to(dip.CONCORD_STANDING)
        assert real >= flat + 4, (
            f"{real} parcels to reach Kin against {flat} at a flat rate — the "
            "curve is not doing enough to be worth having")
        # And the last stretch is dearer than the first — per point of
        # standing, not per parcel. Comparing the counts directly was the
        # wrong shape: the climb to Kin covers seventy points and the stretch
        # above it only twenty-five, so the shorter one can cost fewer
        # parcels while being far more expensive for what it buys.
        top = _parcels_to(95.0, dip.CONCORD_STANDING)
        early = real / dip.CONCORD_STANDING
        late = top / (95.0 - dip.CONCORD_STANDING)
        assert late > early * 1.5, (
            f"{late:.3f} parcels per point above Kin against {early:.3f} "
            "below it — goodwill costs much the same wherever you stand")
        return (f"{real} parcels to Kin (flat rate: {flat}); the stretch "
                f"above it costs {late / early:.1f}x as much per point")

    @check("no overture costs something and buys nothing you can see")
    def _():
        # The floor exists so that a gift is never worthless. Asserting
        # `courtship(100) >= COURTSHIP_FLOOR` proved nothing — it reads its
        # expectation off the constant it is meant to guard, and passed
        # happily with the floor set to zero.
        #
        # The real criterion is the panel's: it prints standing as `{:+.0f}`,
        # so anything under half a point renders "+0 standing" beside a bill
        # for forty tonnes. That is a dead button, which is the same defect
        # the watch options had.
        blind = []
        game = _rich("ceiling", 99.0)
        for action in ACTIONS:
            if not (action.cost_credits or action.cost_goods):
                continue                     # free to offer; nothing at stake
            said = dip.preview(game, action.id, "charter", "concordat")
            standing = max((abs(d) for _p, d in said["standing"]), default=0.0)
            relation = abs(said["relations"][2]) if said.get("relations") else 0
            if round(standing) < 1 and round(relation) < 1:
                blind.append(f"{action.id} ({action.name})")
        assert not blind, (
            f"at the ceiling these cost real resources and show the captain "
            f"nothing they buy: {blind}")
        return (f"{len(ACTIONS)} overtures, every priced one still visibly "
                "worth something at 99 standing")

    @check("the screen says why the numbers got small")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.diplomacy_view import standing_figure
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        seen = {}
        for standing in (0.0, 80.0):
            game = _rich(f"screen{standing:.0f}", standing)
            win = MainWindow(game)
            win.toast = lambda *a, **k: None
            win.go("diplomacy")
            for _ in range(3):
                app.processEvents()
            texts = [lab.text() for lab in
                     win.views["diplomacy"].findChildren(QLabel) if lab.text()]
            rows = " ".join(texts)
            win.close()
            seen[standing] = rows
            # Whatever the standing, the panel prints the real figure.
            for action in ACTIONS:
                if not action.gain:
                    continue
                said = dip.preview(game, action.id, "charter", "concordat")
                gain = next((d for p, d in said["standing"] if p == "charter"),
                            None)
                if gain is None:
                    continue
                shown = standing_figure(gain)
                assert f"{shown} standing" in rows, (
                    f"at {standing:.0f} standing the panel does not say "
                    f"{action.name} is worth {shown}")
            # And nothing on the card reads as "-0 standing", which is what
            # a penalty of a tenth of a point used to round to: it looks like
            # a bug and tells the captain nothing. Whole label texts, not a
            # substring of the joined blob — "+10 standing" ends in
            # "0 standing" and made the first draft of this fail on itself.
            zeros = [t for t in texts if t in ("-0 standing", "+0 standing")]
            assert not zeros, (
                f"the card shows {zeros}, which is either nothing or a "
                "rounding artefact and reads as neither")
        assert "stranger" not in seen[0.0], (
            "a power that has never met you is described as already thinking "
            "well of you")
        assert "stranger" in seen[80.0], (
            "overtures are worth a fraction of their declared value and the "
            "screen offers no explanation at all")
        return "the panel prints the real figure, and says why above the knee"
