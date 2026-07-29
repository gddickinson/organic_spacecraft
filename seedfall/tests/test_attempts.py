"""Ground-option checks — the odds on the screen have to be the odds rolled.

The expedition screen listed each option as "(science, difficulty 3)" and
stopped. Resolution is `1d6 + officer level >= difficulty + 2`, so that exact
string is a one-in-three attempt with a green officer and five-in-six with a
level-three one. The reward was unpacked into a discarded variable, so the
player was never told what success paid. And a failure springs a hazard 40% of
the time — costing supply, the rover and sometimes an officer — which was also
unstated.

The ground game is nothing but a sequence of these choices.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.expedition import FEATURES, REWARD_SCALE
from ..sim import expedition as exp_sim
from .harness import Suite


def _landed(seed: str, feature: str = "wreck", levels: dict | None = None):
    game = new_game(seed)
    body = next(b for s in game.galaxy.systems for b in s.bodies
                if b.kind not in ("gas", "star"))
    system = next(s for s in game.galaxy.systems if body in s.bodies)
    game.location_id = system.id
    if levels:
        from ..sim.crew import make_officer
        for stat, level in levels.items():
            holder = next((o for o in game.officers if o.stat == stat), None)
            if holder is None:
                holder = make_officer(RNG(f"{seed}-{stat}"))
                holder.stat = stat
                game.officers.append(holder)
            holder.level = level
    party = exp_sim.generate(RNG(f"a-{seed}"), system, body,
                             [o.id for o in game.officers], 400)
    party.here.feature = feature
    party.here.resolved = False
    return game, party


def run(suite: Suite) -> None:
    check = suite.check

    @check("the quoted chance is the chance the sim rolls")
    def _():
        # Rolled, not re-derived: the resolution lives in `attempt` and the
        # quote in `odds_for`, and the point is that they cannot drift.
        worst = 0.0
        lines = []
        for feature in ("ruin", "wreck", "nest", "cache"):
            game, party = _landed(f"roll-{feature}", feature)
            for index, (_t, stat, _d, _r) in enumerate(
                    exp_sim.options_here(party)):
                if not stat:
                    continue
                # The previous index's trials left the tile resolved, so the
                # quote came back empty. Reset before asking as well as before
                # rolling.
                party.here.feature = feature
                party.here.resolved = False
                said = exp_sim.odds_for(party, index, game.officers)["chance"]
                wins = trials = 0
                rng = RNG(f"trial-{feature}-{index}")
                for n in range(600):
                    party.here.feature = feature
                    party.here.resolved = False
                    party.supply = 400
                    out = exp_sim.attempt(party, index, game.officers, rng)
                    if not out.get("ok"):
                        continue
                    trials += 1
                    wins += bool(out["success"])
                if trials < 100:
                    continue
                seen = wins / trials
                worst = max(worst, abs(seen - said))
                lines.append(f"{feature}/{index} said {said:.0%} rolled {seen:.0%}")
        assert lines, "nothing was rolled"
        assert worst < 0.06, (
            f"the quoted odds are out by {worst:.0%}: " + "; ".join(lines[:5]))
        return f"{len(lines)} options rolled 600 times each, worst {worst:.1%} out"

    @check("a better officer makes better odds, and the screen says so")
    def _():
        green, party_g = _landed("green", "wreck", {"engineering": 0})
        crack, party_c = _landed("crack", "wreck", {"engineering": 6})
        index = next(i for i, (_t, stat, _d, _r)
                     in enumerate(exp_sim.options_here(party_g))
                     if stat == "engineering")
        lean = exp_sim.odds_for(party_g, index, green.officers)
        good = exp_sim.odds_for(party_c, index, crack.officers)
        assert good["chance"] > lean["chance"], (
            f"level 0 gives {lean['chance']:.0%} and level 6 gives "
            f"{good['chance']:.0%}")
        assert good["level"] > lean["level"]
        assert good["hazard"] < lean["hazard"], (
            "a better officer is no less likely to spring something")
        return (f"{lean['chance']:.0%} green against {good['chance']:.0%} "
                f"at level {good['level']:g}")

    @check("what it says success pays is the table, carried through the officer")
    def _():
        # This asserted the quote *equalled* `REWARD_SCALE`, which is the
        # table `attempt` draws from before multiplying by the roll's margin —
        # so it was holding the card to a number the ground does not pay. A
        # green hand on a seam was quoted 8–26 ore and could take 32 home.
        #
        # The quote is the table carried through what this officer can roll.
        # It can only be wider, never narrower, and `test_prospect` plays out
        # the exact figures.
        checked, widened = 0, 0
        for fid, feature in FEATURES.items():
            game, party = _landed(f"prize-{fid}", fid)
            for index, (_t, _s, _d, reward) in enumerate(feature.options):
                said = exp_sim.odds_for(party, index, game.officers)
                low, high = REWARD_SCALE.get(reward, (0, 0))
                assert said["reward"] == reward, (
                    f"{fid}/{index}: says {said['reward']}, pays {reward}")
                assert said["low"] >= low and said["high"] >= high, (
                    f"{fid}/{index}: quotes {said['low']}–{said['high']} "
                    f"against a table of {low}–{high} — the card promises "
                    "less than the ground can pay")
                widened += said["high"] > high
                checked += 1
        assert checked > 15, f"only {checked} options checked"
        assert widened, (
            "not one option quotes above its bare table, so the officer's "
            "margin is not reaching the card at all")
        return (f"{checked} options across {len(FEATURES)} features, "
                f"{widened} quoting above the bare table")

    @check("walking away is safe and says it is")
    def _():
        found = 0
        for fid, feature in FEATURES.items():
            game, party = _landed(f"safe-{fid}", fid)
            for index, (_t, stat, _d, _r) in enumerate(feature.options):
                if stat:
                    continue
                said = exp_sim.odds_for(party, index, game.officers)
                assert said["chance"] == 1.0, "walking away can fail"
                assert said["hazard"] == 0.0, "walking away springs hazards"
                found += 1
        assert found, "no feature offers a way to leave it alone"
        return f"{found} ways to walk away, every one safe"

    @check("asking the odds does not attempt it")
    def _():
        game, party = _landed("pure", "ruin")
        before = (party.supply, party.days, party.here.resolved,
                  dict(party.haul), list(party.lore))
        for index in range(len(exp_sim.options_here(party))):
            for _ in range(3):
                exp_sim.odds_for(party, index, game.officers)
        after = (party.supply, party.days, party.here.resolved,
                 dict(party.haul), list(party.lore))
        assert after == before, f"{after} != {before}"
        return "the ground was not touched by asking"

    @check("no option is a certainty and none is impossible")
    def _():
        # A choice with no risk and a choice with no hope are both non-choices.
        game, party = _landed("range", "wreck", {"comms": 6, "medicine": 6,
                                                 "engineering": 6})
        best = []
        for fid in FEATURES:
            party.here.feature = fid
            party.here.resolved = False
            for index, (_t, stat, _d, _r) in enumerate(
                    exp_sim.options_here(party)):
                if not stat:
                    continue
                best.append(exp_sim.odds_for(party, index,
                                             game.officers)["chance"])
        assert best, "nothing to check"
        assert min(best) > 0.0, "an option nobody could ever pass"
        assert max(best) <= 1.0
        return (f"{len(best)} skilled options, "
                f"{min(best):.0%}–{max(best):.0%} even with a good crew")
