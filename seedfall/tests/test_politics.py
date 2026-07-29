"""Politics checks — powers that act on their own account.

Diplomacy modelled how the factions regarded you and each other and then waited
for you to move. These hold ventures to actually changing the sector, and hold
the background churn to not quietly foreclosing an ending the player is
entitled to reach.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.diplomacy import CONCORD_RELATION
from ..data.factions import FACTIONS_BY_ID
from ..data.ventures import VENTURES, VENTURES_BY_ID
from ..sim import diplomacy as dip
from ..sim import ventures as venture_sim
from .harness import Suite


def _pairs(game):
    return [dip.relation(game, a, b)
            for i, a in enumerate(dip.POWERS) for b in dip.POWERS[i + 1:]]


def _years(game, count: int) -> None:
    for _ in range(count):
        game.advance_days(365)


def run(suite: Suite) -> None:
    check = suite.check

    @check("every venture can name itself and has somewhere to happen")
    def _():
        game = new_game("venture-text")
        for kind in VENTURES:
            venture = venture_sim.Venture(
                id=1, kind=kind.id, power="charter",
                other="freeholds" if kind.needs_other else None,
                place=0 if kind.needs_place else None, until=100)
            for template in (kind.premise, kind.success, kind.failure):
                text = venture_sim.describe(game, venture, template)
                assert "{" not in text, f"{kind.id} left a field unfilled: {text}"
                assert len(text) > 30, f"{kind.id} says almost nothing"
            assert kind.days[0] > 0 and kind.days[1] >= kind.days[0]
            assert kind.back_cost > 0, f"{kind.id} is free to back"
        return f"{len(VENTURES)} ventures, all legible"

    @check("the powers act without being prompted")
    def _():
        game = new_game("acting")
        game.credits = 500000
        _years(game, 12)
        all_of = venture_sim.ensure(game)
        assert all_of, "twelve years and no power did anything"
        resolved = [v for v in all_of if v.resolved]
        assert resolved, "nothing ever resolved"
        kinds = {v.kind for v in all_of}
        assert len(kinds) >= 3, f"only {len(kinds)} kinds ever ran"
        assert any(v.succeeded for v in resolved), "nothing ever succeeded"
        assert any(not v.succeeded for v in resolved), "nothing ever failed"
        return (f"{len(all_of)} ventures over 12 years, {len(kinds)} kinds, "
                f"{len(resolved)} resolved")

    @check("a venture that comes off changes the sector")
    def _():
        game = new_game("annexation")
        rng = RNG("annex")
        free = [s for s in game.galaxy.systems if s.faction is None]
        assert free, "nowhere unclaimed to annex"
        target = free[0]
        venture = venture_sim.Venture(id=1, kind="annex", power="charter",
                                      place=target.id, until=game.day)
        game.ventures = [venture]
        venture.stance = "backed"          # push the odds up
        for _ in range(20):
            if target.faction is not None:
                break
            venture.resolved = False
            venture.until = game.day
            venture_sim._resolve(game, venture, rng)
        assert target.faction == "charter", (
            "twenty successful annexations and the system is still unclaimed")

        # And a courtship moves the two powers together.
        before = dip.relation(game, "charter", "sanhedrin")
        court = venture_sim.Venture(id=2, kind="courtship", power="charter",
                                    other="sanhedrin", until=game.day)
        court.succeeded = True
        venture_sim._apply(game, court, rng)
        assert dip.relation(game, "charter", "sanhedrin") > before, (
            "a rapprochement changed nothing")
        return f"{target.name} annexed; a courtship warmed a pair"

    @check("taking a side costs standing and moves the odds")
    def _():
        game = new_game("sides")
        game.credits = 200000
        rng = RNG("sides")
        venture = venture_sim.start(game, rng, "charter")
        assert venture is not None, "no venture to take a side in"

        neutral = venture_sim.odds(game, venture)
        before_power = game.rep.get(venture.power, 0)
        res = venture_sim.intervene(game, venture, "back")
        assert res["ok"], res.get("why")
        assert game.rep.get(venture.power, 0) > before_power, "backing bought nothing"
        assert venture_sim.odds(game, venture) > neutral, "backing moved no odds"

        again = venture_sim.intervene(game, venture, "oppose")
        assert not again["ok"], "took both sides of the same venture"

        other = new_game("sides")
        other.credits = 200000
        second = venture_sim.start(other, RNG("sides"), "charter")
        base = venture_sim.odds(other, second)
        rep_before = other.rep.get(second.power, 0)
        venture_sim.intervene(other, second, "oppose")
        assert other.rep.get(second.power, 0) < rep_before, "opposing cost nothing"
        assert venture_sim.odds(other, second) < base, "opposing moved no odds"
        return "backing and opposing both cost, and both move the odds"

    @check("backing a venture is refused when you cannot pay")
    def _():
        game = new_game("broke-politics")
        game.credits = 0
        venture = venture_sim.start(game, RNG("broke"), "concordat")
        assert venture is not None
        ok, why = venture_sim.can_intervene(game, venture, "back")
        assert not ok and why, "backed a venture with no money"
        res = venture_sim.intervene(game, venture, "back")
        assert not res["ok"], "paid with money it did not have"
        assert game.credits == 0, "credits went negative"
        # Opposing is always affordable — it costs standing, not money.
        assert venture_sim.can_intervene(game, venture, "oppose")[0]
        return "backing needs the fee; opposing needs only nerve"

    @check("background politics do not foreclose the Concord")
    def _():
        # Every blockade and censure used to be a permanent debit, so a decade
        # of churn drove every pair far below the Concord threshold and left an
        # ending unreachable through no fault of the player.
        readings = {}
        for years in (0, 10, 25):
            worst = []
            for seed in range(6):
                game = new_game(f"concord-{seed}")
                game.credits = 500000
                _years(game, years)
                worst.append(min(_pairs(game)))
            readings[years] = sum(worst) / len(worst)
        assert readings[25] <= readings[0] + 1, "relations only ever improve"
        assert readings[25] > readings[10] - 12, (
            f"relations are still sliding at 25 years: {readings}")

        # The emergent numbers alone are a weak signal — they plateau against
        # the -100 floor either way. Test the mechanism that stops the ratchet:
        # a grievance nobody is maintaining has to fade.
        game = new_game("fade")
        a, b = dip.POWERS[0], dip.POWERS[1]
        base = dip.relation(game, a, b)
        dip.shift_relation(game, a, b, -40)
        pushed = dip.relation(game, a, b)
        assert pushed < base, "shifting a relation did nothing"
        for _ in range(20):
            dip.drift(game, 365)
        healed = dip.relation(game, a, b)
        assert healed > pushed + 10, (
            f"a grievance never faded: {pushed:.0f} → {healed:.0f} after "
            "twenty years of nobody maintaining it")
        assert healed <= base + 0.5, "drift overshot its own baseline"
        return (" · ".join(f"{k}y {v:+.0f}" for k, v in readings.items())
                + f" · a -40 grievance fades {pushed:.0f} → {healed:.0f}")

    @check("a determined broker can still reach the Concord")
    def _():
        # Four seeds and a bar of three was a coin flip dressed as a check.
        # Measured over seventy-two games, a determined broker reaches the
        # Concord between 56% and 68% of the time — so `wins >= 3 of 4` had
        # roughly an even chance of failing on any given day, and passed for
        # a long time on luck. It duly went red for an economy change that a
        # fixed-length control showed had no political effect whatever: same
        # 322 ventures, standing and relations within noise, and the apparent
        # 53%-against-75% gap vanished (21/36 against 22/36) the moment the
        # same comparison was run on a fresh range of seeds.
        #
        # Twenty games and a floor well under the measured rate. The whole
        # run costs about a second.
        #
        # **The bot courts as well as brokers, and that is the point.** It
        # used to broker and nothing else, which was a complete strategy
        # while a settlement cost nothing with anybody. It no longer is:
        # seating two powers at a table is the most public act on the board
        # and a third power at odds with both now pays attention. Measured
        # at the current weight — brokering alone reaches the Concord 6 times
        # in 20, brokering *and* keeping everyone sweet 19 times in 20. The
        # premise changed, so the captain being modelled changed with it;
        # the bar below is the same one, and it clears it far better.
        trials, wins = 20, 0
        for seed in range(trials):
            game = new_game(f"broker-{seed}")
            game.credits = 10 ** 9
            for cid in ("biomass", "survey"):
                game.ship.cargo[cid] = 999_999
            for power in dip.POWERS:
                game.rep[power] = 90
            game.recompute()
            done = False
            for _ in range(15):
                for _ in range(12):
                    game.advance_days(30)
                    ranked = sorted((dip.relation(game, a, b), a, b)
                                    for i, a in enumerate(dip.POWERS)
                                    for b in dip.POWERS[i + 1:])
                    for value, a, b in ranked:
                        if value >= CONCORD_RELATION:
                            continue
                        if dip.perform(game, "broker", a, b).get("ok"):
                            break
                    # Mend what the settlements cost, worst standing first.
                    for power in sorted(dip.POWERS,
                                        key=lambda q: game.rep.get(q, 0)):
                        for aid in ("relief", "intelligence", "tribute"):
                            if dip.perform(game, aid, power).get("ok"):
                                break
                if dip.concord_progress(game)["done"]:
                    done = True
                    break
            wins += done
        rate = wins / trials
        assert rate >= 0.35, (
            f"Concord reached in only {wins}/{trials} determined games — a "
            "captain with a billion credits, Kin with all four powers and "
            "fifteen years of brokering should get there most of the time")
        assert rate < 1.0, (
            f"all {trials} determined games reached the Concord: the churn "
            "the powers generate has stopped being able to undo the work")
        return (f"Concord reached in {wins}/{trials} games against the churn "
                f"({rate:.0%})")

    @check("ventures survive a save and reload")
    def _():
        import json

        from ..core.save import decode, encode

        game = new_game("persist-politics")
        game.credits = 200000
        venture = venture_sim.start(game, RNG("persist"), "freeholds")
        assert venture is not None
        venture_sim.intervene(game, venture, "oppose")
        before = (venture.kind, venture.power, venture.other, venture.place,
                  venture.until, venture.stance)

        back = decode(json.loads(json.dumps(encode(game))))
        live = venture_sim.live(back)
        assert len(live) == 1, "the venture was lost"
        got = live[0]
        after = (got.kind, got.power, got.other, got.place, got.until, got.stance)
        assert after == before, f"{after} != {before}"
        return f"a {VENTURES_BY_ID[got.kind].name.lower()} came back, still opposed"
