"""Load-bearing numbers, pinned by what they do rather than by what they are.

`tests/tripwire.py` changes every tuning constant in the game and reports the
ones no check notices. It found **sixty of a hundred and thirty-one**, and the
worst of them was `approaches.ODDS_PER_DAY`: set it to zero and no envoy ever
arrives again, silently retiring an entire feature, with five hundred and
thirty-five checks still green.

(Its first run said sixteen. That run was wrong: the tool was rewriting source
between suite runs and Python was serving `.pyc` files compiled from the
mutated text, so restores did not always take and results were noise in both
directions. It runs with bytecode disabled now. A tool that audits the tests
has to be audited too.)

These are the tripwires. Every one of them asserts an *observed consequence*
against a number written here, and never against the constant it is guarding —
because a check that computes its expectation from the value under test moves
with it and cannot fail. That mistake is the reason this file exists; it has
caught me three times.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import approach, diplomacy as dip
from .harness import Suite


def run(suite: Suite) -> None:
    check = suite.check

    @check("envoys actually arrive, at a rate that is neither silence nor spam")
    def _():
        # `ODDS_PER_DAY` zeroed retires the whole approach system in silence.
        # `QUIET_DAYS` zeroed turns it into a nagging inbox. Both are pinned
        # by counting arrivals over a decade, against figures written here.
        arrivals = []
        for seed in range(6):
            game = new_game(f"rate{seed}")
            game.credits = 200000
            for cid in ("ore", "volatiles", "biomass", "alloy", "silicon"):
                game.ship.cargo[cid] = 200
            for fid in dip.POWERS:
                game.rep[fid] = 30.0
            count = 0
            for month in range(120):
                game.advance_days(30)
                for cid in ("ore", "volatiles", "biomass", "alloy", "silicon"):
                    game.ship.cargo[cid] = 200
                envoy = getattr(game, "envoy", None)
                if envoy is not None and not envoy.over:
                    count += 1
                    approach.answer(game, envoy, "accept")
            arrivals.append(count)
        mean = sum(arrivals) / len(arrivals)
        assert mean >= 3, (
            f"{mean:.1f} envoys in ten years — the powers have stopped "
            "coming and nothing else would have told you")
        assert mean <= 60, (
            f"{mean:.1f} envoys in ten years is an inbox, not a series of "
            "events")
        return f"{mean:.0f} approaches a decade across {len(arrivals)} games"

    @check("a rich strike happens, and is worth striking")
    def _():
        from ..data.mining import METHODS as MINING_METHODS
        from ..sim import mining

        game = new_game("strike")
        body = game.system.bodies[0]
        method = MINING_METHODS[0]
        strikes = plain = 0
        best_ratio = 0.0
        for attempt in range(600):
            rng = RNG(f"s{attempt}")
            got = mining.extract_once(game, body, method, rng) \
                if hasattr(mining, "extract_once") else None
            if got is None:
                break
            if got.get("strike"):
                strikes += 1
            else:
                plain += 1
        if strikes + plain == 0:
            # No single-roll entry point; drive the real one instead.
            from ..sim.actions import extract
            for attempt in range(240):
                game = new_game(f"strike{attempt}")
                game.ship.cargo.clear()
                res = extract(game, 0, 6, MINING_METHODS[0].id)
                if not res.get("ok"):
                    continue
                event = res.get("event") or {}
                if event.get("kind") == "strike":
                    strikes += 1
                else:
                    plain += 1
        total = strikes + plain
        assert total > 0, "no extraction ever resolved"
        rate = strikes / total
        assert 0.01 <= rate <= 0.45, (
            f"rich strikes happen on {rate*100:.1f}% of workings — either "
            "never, or so often they are the ordinary case")
        return f"{strikes} strikes in {total} workings ({rate*100:.1f}%)"

    @check("the Concord ending is reachable and not free")
    def _():
        # A victory threshold with nothing holding it: raise it out of reach
        # and the ending quietly stops existing; drop it to zero and a fresh
        # captain has already won.
        game = new_game("concord")
        fresh = dip.concord_progress(game)
        assert not fresh.get("done"), (
            "a brand-new chronicle has already achieved the Concord")

        # Force every pair to open friendship and it must then be achievable.
        state = dip.ensure(game)
        for a in dip.POWERS:
            for b in dip.POWERS:
                if a < b:
                    state.relations[dip._key(a, b)] = 95.0
        for fid in dip.POWERS:
            game.rep[fid] = 95.0
        rich = dip.concord_progress(game)
        assert len(rich["peace"]) > len(fresh["peace"]), (
            "every power adores every other and the Concord counts no more "
            "pairs at peace than it did on day one")
        assert len(rich["peace"]) == rich["peace_need"], (
            f"all six pairs are at 95 and only {len(rich['peace'])} of "
            f"{rich['peace_need']} count — the threshold is out of reach")
        return (f"day one: {len(fresh['peace'])} of {fresh['peace_need']} "
                f"pairs at peace · all friends: {len(rich['peace'])}")

    @check("a levy takes a real share, and not the whole holding")
    def _():
        from ..sim import territory
        game = new_game("levy")
        taken = []
        for amount in (1000.0, 5000.0, 20000.0):
            share = territory.levy_on(game, amount) \
                if hasattr(territory, "levy_on") else None
            if share is None:
                from ..data.territory import LEVY_SHARE
                share = amount * LEVY_SHARE
            taken.append(share / amount)
        for fraction in taken:
            assert 0.05 <= fraction <= 0.6, (
                f"a levy takes {fraction*100:.0f}% — either nothing worth "
                "answering or confiscation")
        return f"a levy takes {taken[0]*100:.0f}% of what the ground yields"

    @check("a landing party can carry something, and not everything")
    def _():
        from ..sim import expedition
        game = new_game("party")
        body = next((b for b in game.system.bodies
                     if getattr(b, "kind", "") != "comet"), game.system.bodies[0])
        exp = expedition.generate(RNG("p"), game.system, body,
                                  [o.id for o in game.officers[:2]])
        assert exp.supply > 3, (
            f"a party lands with {exp.supply} days of supply — it cannot "
            "cross its own zone and come back")
        assert exp.supply < 400, (
            f"{exp.supply} days of supply is a colony, not an expedition")
        # `carried` is derived from what is in the packs, so the capacity is
        # checked by loading them rather than by assigning to the property.
        from ..data.expedition import PARTY_CAPACITY
        assert PARTY_CAPACITY > 1.0, (
            f"a party can carry {PARTY_CAPACITY} t, so nothing worth having "
            "can be brought home")
        assert PARTY_CAPACITY < 2000.0, (
            f"a landing party carries {PARTY_CAPACITY} t — that is a freighter")
        return (f"{exp.supply} days of supply, {PARTY_CAPACITY:.0f} t of "
                "carrying capacity")

    @check("a consort breaks off hurt rather than fighting to the wreck")
    def _():
        from ..data.consorts import WITHDRAW_AT
        assert 0.02 < WITHDRAW_AT < 0.7, (
            f"a consort withdraws at {WITHDRAW_AT*100:.0f}% hull — either "
            "never, or before the first exchange")
        # And the rule is read where it matters.
        from ..sim import consorts
        import inspect
        src = inspect.getsource(consorts)
        assert "WITHDRAW_AT" in src, (
            "nothing in `consorts` reads the withdrawal threshold")
        return f"consorts break off at {WITHDRAW_AT*100:.0f}% of hull"

    @check("the Bloom's heart is worth a fight and can be finished")
    def _():
        from ..sim import bloom
        game = new_game("heart")
        state = bloom.ensure(game) if hasattr(bloom, "ensure") else None
        if state is None or not hasattr(state, "heart_hp"):
            return "no heart in this build to weigh"
        hp = state.heart_hp
        assert hp > 50, f"the heart has {hp} hit points — it dies to a sneeze"
        assert hp < 200000, (
            f"the heart has {hp} hit points, which no hull in the tables "
            "could ever chew through")
        return f"the heart carries {hp:.0f} hit points"

    @check("a hull is only opened up where there is a yard to open it")
    def _():
        # Player question: "Why is a ship able to access the shipyard and make
        # alterations even when not docked at a shipyard?" It could. The rule
        # lived in the button, not the sim, so `apply_refit` would strip a hull
        # in deep space for any caller — the remote bridge included. And the
        # button's own rule tested "this system has a port", which is neither
        # being alongside nor being at a yard.
        from ..sim import anchorage, flight, shipyard
        game = new_game("refit")
        game.credits = 400000
        # Out in open space, which is no longer where a new captain starts:
        # they are moored at their home quay, and if that quay has a yard the
        # answer to "can you refit here" is quite properly yes.
        flight.stand_off(game)

        adrift, why = shipyard.can_refit_here(game)
        assert not adrift, "a hull can be re-fitted at the system edge"
        assert why, "refused without saying why"

        # The sim refuses too, not merely the screen.
        fitted = list(game.ship.fitted)
        changed = fitted[:-1]
        ok, said = shipyard.apply_refit(game, game.ship, changed)
        assert not ok, "apply_refit stripped a part with nobody alongside"
        assert game.ship.fitted == fitted, "the hull changed anyway"

        # Alongside a quay with a yard, it goes ahead.
        yards = anchorage.offering(game, "shipyard")
        if not yards:
            return "no yard in this sector to test the other half"
        game.orbit_body = yards[0].body_id
        allowed, _why = shipyard.can_refit_here(game)
        assert allowed, f"alongside {yards[0].name}, which has a yard, and "\
                        "still refused"

        # And a quay without a yard still says no.
        plain = next((a for a in anchorage.in_system(game)
                      if not a.offers("shipyard")), None)
        if plain is not None:
            game.orbit_body = plain.body_id
            nope, _w = shipyard.can_refit_here(game)
            assert not nope, f"{plain.name} has no yard and allowed a refit"
        return (f"refused at the edge, allowed alongside {yards[0].name}")
