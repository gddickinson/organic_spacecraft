"""What a ground option is worth, and whether the officer you send shows in it.

`odds_for` was written to end "(science, difficulty 3)" — a string that is a
one-in-three with a green officer and five-in-six with a veteran, and said
nothing about what success paid. It now states the chance, the officer, the
prize and the risk.

It stated the prize as the bare `REWARD_SCALE` band, which is what the roll is
drawn from before `attempt` multiplies it by `1 + margin * MARGIN_BONUS`. So
the card read the same at every officer level while the payout did not.
Measured on "Cut a sample", 800 attempts a level:

    level 0   quoted 8–26 ore   paid up to 32.2
    level 3   quoted 8–26 ore   paid up to 41.6
    level 5   quoted 8–26 ore   paid up to 47.8

Twenty-eight of forty-two option-and-level pairs paid over their quoted
ceiling. **Skill moved the odds on the screen and moved the prize in secret**,
which is half of what an officer is worth and the half nobody was told. A
captain choosing between sending the veteran and keeping them aboard was
reading one of the two numbers that decides it.

The quote is conditioned on the officer now: the smallest and largest margin
that officer can roll on a success, multiplied through. "Cut a sample" reads
8–32 for a green hand and 9–45 for a level-four one.

The claims:

- **The quoted prize bounds what is actually paid**, over every option, every
  officer level, measured by playing. The general one.
- **A better officer is quoted a better prize**, not merely better odds.
- **The quoted chance is the observed rate.**
- **The card on the ground prints it.**
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.expedition import FEATURES
from ..sim import expedition as exp_sim
from ..sim.expedition import MARGIN_BONUS, REWARD_SCALE
from .harness import Suite


class _Hand:
    """An officer of a chosen stat and level, with an id the hazards can use."""

    _next = 0

    def __init__(self, stat: str, level: int) -> None:
        _Hand._next += 1
        self.stat, self.level, self.id = stat, level, _Hand._next
        self.name = f"{stat[:4]}-{level}"


#: One galaxy, reused. Generating a fresh one per attempt made this suite
#: take minutes to say the same thing.
_GAME = None


def _at(feature_id: str, seed: int = 0):
    """A party standing on a chosen feature, with supply to spare."""
    global _GAME
    if _GAME is None:
        _GAME = new_game("prospect")
    body = next(b for s in _GAME.galaxy.systems for b in s.bodies)
    party = exp_sim.generate(RNG(f"pro-{seed}"), _GAME.system, body, [], 9000)
    party.here.feature = feature_id
    party.here.resolved = False
    return party


def _rolls(feature_id: str, index: int, officers, trials: int) -> dict:
    """Play the same attempt many times. Returns what actually happened.

    One party, re-presented with the same feature: `attempt` only reads the
    tile, the officers and the die, so resetting the tile is the whole of it.
    """
    party = _at(feature_id)
    wins, paid = 0, []
    for trial in range(trials):
        party.here.feature = feature_id
        party.here.resolved = False
        party.supply = 9000
        party.injured = []
        got = exp_sim.attempt(party, index, officers,
                              RNG(f"r{feature_id}{index}{trial}"))
        if got.get("success"):
            wins += 1
            if got.get("amount"):
                paid.append(round(got["amount"]))
    return {"rate": wins / trials, "paid": paid}


def _priced():
    """Every (feature, option index, reward) that pays a measurable amount."""
    for fid, feature in FEATURES.items():
        for index, (_label, stat, _diff, reward) in enumerate(feature.options):
            if stat and REWARD_SCALE.get(reward, (0, 0))[1]:
                yield fid, index, reward


def run(suite: Suite) -> None:
    check = suite.check

    @check("the prize on the card is the prize the ground pays")
    def _():
        # The general one, swept rather than sampled: every priced option at
        # three officer levels, played four hundred times each. Measured
        # against `round(amount)`, which is the figure the log reports and the
        # one a captain sees.
        outside, checked = [], 0
        for fid, index, _reward in _priced():
            stat = FEATURES[fid].options[index][1]
            for level in (0, 2, 4):
                officers = [_Hand(stat, level)]
                said = exp_sim.odds_for(_at(fid), index, officers)
                got = _rolls(fid, index, officers, 400)
                if not got["paid"]:
                    continue
                checked += 1
                if max(got["paid"]) > said["high"]:
                    outside.append(f"{fid}/{index} lvl {level}: quoted up to "
                                   f"{said['high']}, paid {max(got['paid'])}")
                if min(got["paid"]) < said["low"]:
                    outside.append(f"{fid}/{index} lvl {level}: quoted from "
                                   f"{said['low']}, paid {min(got['paid'])}")
        assert not outside, (
            f"{len(outside)} option(s) paid outside the quoted band: "
            f"{outside[:4]}")
        assert checked >= 30, checked
        return (f"{checked} option-and-level pairs, 400 attempts each, every "
                "payout inside its quote")

    @check("a better officer is quoted a better prize, not just better odds")
    def _():
        # The finding. Before, the band was the bare scale at every level, so
        # the card was identical for a green hand and a veteran.
        widened, flat = 0, []
        for fid, index, reward in _priced():
            stat = FEATURES[fid].options[index][1]
            green = exp_sim.odds_for(_at(fid), index, [_Hand(stat, 0)])
            good = exp_sim.odds_for(_at(fid), index, [_Hand(stat, 4)])
            if good["high"] > green["high"]:
                widened += 1
            else:
                flat.append(f"{fid}/{index} ({reward}): {green['high']} either way")
        assert not flat, (
            f"{len(flat)} option(s) quote the same top prize whoever is sent: "
            f"{flat[:4]}")
        # And it is worth something real, not a rounding difference.
        stat = FEATURES["seam"].options[0][1]
        green = exp_sim.odds_for(_at("seam"), 0, [_Hand(stat, 0)])
        good = exp_sim.odds_for(_at("seam"), 0, [_Hand(stat, 4)])
        assert good["high"] >= green["high"] * 1.2, (
            f"a level-four hand is quoted {good['high']} against a green "
            f"hand's {green['high']} — not enough to be worth reading")

        # Both ends. Where even the worst success carries margin, the floor
        # of the band has to leave the bare scale as well — otherwise the
        # card promises a payout that can no longer happen. Sampling cannot
        # settle this: the corner of the band is rare on a wide scale like
        # credits, so it is asked of the quote directly.
        floors = []
        for fid, index, reward in _priced():
            stat = FEATURES[fid].options[index][1]
            difficulty = FEATURES[fid].options[index][2]
            bare = REWARD_SCALE[reward][0]
            if bare < 5:
                # A sample or a xenolith is counted in ones. A pip of margin
                # on a floor of 1 rounds straight back to 1, so there is no
                # rise to look for and its absence proves nothing.
                continue
            for level in (4, 5):
                if 1 + level - (difficulty + 2) <= 0:
                    continue          # a 1 on the die still scrapes in
                band = exp_sim.odds_for(_at(fid), index, [_Hand(stat, level)])
                if band["low"] <= bare:
                    floors.append(f"{fid}/{index} lvl {level}: floor still "
                                  f"{band['low']}, the bare scale")
        assert not floors, (
            f"{len(floors)} band(s) quote a floor their officer can no longer "
            f"pay: {floors[:4]}")
        return (f"{widened} options quote a wider prize for a veteran; a seam "
                f"reads {green['low']}–{green['high']} green and "
                f"{good['low']}–{good['high']} at level four")

    @check("the quoted chance is the rate the ground actually gives")
    def _():
        # The half that was already right, held there — the prize fix must not
        # have disturbed it.
        worst, checked = 0.0, 0
        for fid, index, _reward in _priced():
            stat = FEATURES[fid].options[index][1]
            for level in (0, 3):
                officers = [_Hand(stat, level)]
                said = exp_sim.odds_for(_at(fid), index, officers)
                got = _rolls(fid, index, officers, 500)
                checked += 1
                worst = max(worst, abs(said["chance"] - got["rate"]))
        assert worst < 0.08, (
            f"the worst forecast was {worst:.0%} off the played rate")
        assert checked >= 20, checked
        return (f"{checked} forecasts, worst {worst:.0%} from the rate over "
                "500 attempts")

    @check("the margin bonus is a named number, used in both places")
    def _():
        # It was a bare 0.12 inside `attempt`, which is why the forecast could
        # not quote it. Measured rather than read: the top of a quote has to
        # move when the constant does.
        assert 0.0 < MARGIN_BONUS < 0.5, MARGIN_BONUS
        stat = FEATURES["seam"].options[0][1]
        band = exp_sim.odds_for(_at("seam"), 0, [_Hand(stat, 4)])
        base = REWARD_SCALE["ore"][1]
        best_margin = max(0, 6 + 4 - (FEATURES["seam"].options[0][2] + 2))
        assert band["high"] == round(base * (1 + best_margin * MARGIN_BONUS)), (
            f"the quote {band['high']} is not the scale {base} carried through "
            f"{best_margin} pips of margin")
        return (f"{MARGIN_BONUS:g} a pip, carried into the quote: "
                f"{base} becomes {band['high']}")

    @check("the card on the ground prints the prize it will pay")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        seen = {}
        for level in (0, 4):
            game = new_game("card")
            for officer in game.officers:
                officer.level = level
            party = exp_sim.generate(RNG("card"), game.system,
                                     game.system.bodies[0],
                                     [o.id for o in game.officers], 40)
            party.here.feature = "seam"
            party.here.resolved = False
            game.expedition = party
            win = MainWindow(game)
            win.toast = lambda *a, **k: None
            win.go("ground")
            for _ in range(3):
                app.processEvents()
            rows = " ".join(lab.text() for lab in
                            win.views["ground"].findChildren(QLabel)
                            if lab.text())
            win.close()
            said = exp_sim.odds_for(party, 0, game.officers)
            assert f"{said['low']}–{said['high']} ore" in rows, (
                f"at level {level} the card does not quote "
                f"{said['low']}–{said['high']} ore")
            seen[level] = said["high"]
        assert seen[4] > seen[0], (
            f"the card quotes {seen[0]} either way — sending the veteran "
            "reads as free")
        return (f"the seam card reads up to {seen[0]} ore green and "
                f"{seen[4]} at level four")
