"""Renown and the Voyage: what the suite holds them to.

- every milestone fires on the day its fact reaches its mark, once, and
  never before; the facts read the chronicle's own state, driven through the
  acts that change it;
- a reward pays exactly what its terms said, out of the purse it names;
- every perk moves the number it names, and switched off it does not;
- the ending tracks read the truth;
- counsel: every suggestion over 200 seeded states is actionable, or refused
  with the reason it showed — the top one always actionable;
- the careful captain reaches an ending in five years, and (the same seed)
  does not with the rewards withheld; its first milestone is in days and its
  first rank inside a season;
- the memoir is written at an ending and at a death; the Hall outlasts a new
  chronicle and a process; a chronicle carries renown across a process, and
  an old save is credited without being paid.

The perks and the ending tracks are split into `renown_perks_checks` at the
length rule; this file runs them.
"""

from __future__ import annotations

import copy

from ..core.state import new_game
from ..sim import counsel, exchequer, renown, renown_facts
from . import renown_kit as kit
from .harness import Suite


def _fire(game, values: dict) -> list:
    with kit.facts(values):
        return renown.check(game)


def run(suite: Suite) -> None:
    check = suite.check

    @check("every milestone fires at its mark, once, and not a day before")
    def _():
        rows = list(renown.ALL)
        assert len(rows) >= 90, f"{len(rows)} milestones; the spec asks ~87"
        fired = 0
        for m in rows:
            game = new_game("renown-marks")
            st = renown.ensure(game)
            need = {f: at for f, at in ((m.fact, m.at),) + m.also}
            below = dict(need)
            below[m.fact] = m.at - (0.01 if m.at < 1 else 1)
            _fire(game, below)
            assert m.id not in st.achieved, f"{m.id} fired below its mark"
            _fire(game, need)
            assert m.id in st.achieved, f"{m.id} did not fire at {need}"
            score, held = st.score, dict(st.achieved)
            _fire(game, need)
            assert st.score == score and st.achieved == held, (
                f"{m.id} was granted twice")
            fired += 1
        assert fired == len(rows)
        return f"{fired} milestones, each once at its mark"

    @check("the facts read the chronicle, through the acts that change it")
    def _():
        from ..sim import actions, survey, trade
        game = new_game("renown-facts")
        fact = renown_facts.fact
        assert fact(game, "surveyed") == 0 and fact(game, "sales") == 0
        body = next(i for i, b in enumerate(game.system.bodies)
                    if not b.surveyed)
        assert survey.perform(game, body, "pass")["ok"]
        assert fact(game, "surveyed") == 1
        # A cargo of something this counter did not sell you counts.
        cid = next(c for c in game.system.market.stock if c != "survey")
        game.ship.cargo[cid] = 5
        assert trade.sell(game, cid, 5)["ok"]
        assert fact(game, "sales") == 1
        # And one bought back over the same counter does not.
        trade.buy(game, cid, 3)
        trade.sell(game, cid, 3)
        assert fact(game, "sales") == 1, "a buy-back counted as a sale"
        before = fact(game, "visited")
        near = min((s for s in game.galaxy.systems
                    if s.id != game.location_id and not s.visited),
                   key=lambda s: actions.jump_quote(game, s)["ly"])
        game.ship.cargo["volatiles"] = 200
        assert actions.jump_to(game, near.id)["ok"]
        assert fact(game, "visited") == before + 1
        renown.note(game, "battle:destroyed")
        renown.note(game, "battle:parley")
        assert fact(game, "fights") == 2 and fact(game, "victories") == 1
        assert fact(game, "talked_down") == 1
        game.day = 400
        assert fact(game, "days") == 400 and fact(game, "clean_days") == 400
        game.advance_days(1)
        st = renown.state(game)
        for mid in ("first_look", "underway", "first_sale", "first_fight",
                    "first_win", "talked_down", "year_1", "clean_year"):
            assert mid in st.achieved, f"{mid} not fired from real state"
        return (f"{len(st.achieved)} milestones fired from a played day: "
                + ", ".join(sorted(st.achieved)))

    @check("the counted acts count themselves: a dive, a cleansed system")
    def _():
        from ..sim import actions, threat
        from ..core.rng import RNG
        game = new_game("renown-acts")
        ocean = next(((s, i) for s in game.galaxy.systems
                      for i, b in enumerate(s.bodies)
                      if b.biome == "subsurface"), None)
        assert ocean is not None
        system, index = ocean
        game.location_id = system.id
        from ..core.state import START_FIT
        from ..sim.ship import build_layers, make_ship
        game.ship = make_ship("navis", [p for p in START_FIT
                                        if p != "mining_root"]
                              + ["melt_head"], game.ship.name)
        build_layers(game.ship, game.bonuses)
        game.fleet = [game.ship]
        game.recompute()
        assert game.ship_stats.can_dive, "the melt head did not fit"
        out = actions.dive(game, index)
        assert out["ok"], out.get("why")
        assert renown_facts.fact(game, "dives") == 1
        # A small mass, burned by the lances `test_sim` burns with: cleared.
        from ..sim.ship import make_ship
        target = next(s for s in game.galaxy.systems if s.bloom > 0.02)
        target.bloom = 0.05
        game.location_id = target.id
        game.ship = make_ship("navis", ["fusion_lance", "fusion_lance",
                                        "fusion_plant", "fusion_plant",
                                        "reaction_organ", "opsin_eyes",
                                        "silicon_core"])
        game.fleet.append(game.ship)
        game.recompute()
        before = renown_facts.fact(game, "cleansed")
        out, why = threat.cleanse(game, target, RNG("burn"))
        assert out and out["cleared"], why
        assert renown_facts.fact(game, "cleansed") == before + 1
        out, _why = threat.cleanse(game, target, RNG("burn-again"))
        assert out is None, "a clean system burned twice"
        assert renown_facts.fact(game, "cleansed") == before + 1
        return "a dive counted once; a system cleansed counted once, not twice"

    @check("a reward pays exactly its terms, out of the purse it names")
    def _():
        rows = [m for m in renown.ALL if m.reward is not None]
        assert len(rows) >= 20, f"only {len(rows)} milestones pay anything"
        paid_total = 0
        for m in rows:
            game = new_game("renown-pay")
            # Every other rung already on the record, so this one pays alone.
            renown.ensure(game).achieved = {x.id: 0 for x in renown.ALL
                                            if x.id != m.id}
            terms = renown.reward_terms(game, m)
            purse = (exchequer.purse(game, terms["payer"]).credits
                     if terms["payer"] else None)
            credits, rep = game.credits, dict(game.rep)
            points = game.research.points
            need = {f: at for f, at in ((m.fact, m.at),) + m.also}
            _fire(game, need)
            assert round(game.credits - credits) == terms["credits"], m.id
            if terms["payer"]:
                taken = purse - exchequer.purse(game, terms["payer"]).credits
                assert round(taken) == terms["credits"], (
                    f"{m.id}: the captain got {terms['credits']} and the "
                    f"{terms['payer']} purse lost {taken}")
            for power, delta in terms["standing"].items():
                moved = game.rep[power] - rep[power]
                assert abs(moved - delta) < 1e-6 or game.rep[power] in (
                    -100, 100), f"{m.id}: {power} moved {moved}, said {delta}"
            assert round(game.research.points - points) == terms["research"]
            if terms["title"]:
                assert terms["title"] in renown.state(game).titles
            assert renown.state(game).paid[m.id]["credits"] == terms["credits"]
            paid_total += terms["credits"]
        # A purse that cannot cover it pays what it holds, and says so.
        game = new_game("renown-short")
        gen = renown.BY_ID["gen_1"]
        exchequer.purse(game, "charter").credits = 4_000
        terms = renown.reward_terms(game, gen)
        assert terms["credits"] == 4_000 and terms["short"] == 11_000
        assert "cannot find" in terms["words"]
        before = game.credits
        _fire(game, {"knows_piezolyte": 1})
        assert round(game.credits - before) == 4_000
        assert exchequer.purse(game, "charter").credits == 0
        return (f"{len(rows)} rewards paid as stated, ₡{paid_total:,} from "
                "purses; a short purse paid ₡4,000 of ₡15,000 and said so")

    from . import renown_perks_checks
    renown_perks_checks.run(suite)

    @check("counsel: every move of 200 states goes through, or is refused "
           "for the reason it showed")
    def _():
        games = kit.states(200)
        assert len(games) == 200
        total = top = blocked = 0
        kinds: set = set()
        for game in games:
            moves = counsel.advise(game, 99)
            if not moves:
                continue
            for i, move in enumerate(moves):
                twin = copy.deepcopy(game)
                out = counsel.act(twin, move)
                kinds.add(move["id"].split(":")[0])
                if move["blocked"]:
                    blocked += 1
                    assert not out["ok"] and out["why"] == move["blocked"], (
                        f"{move['id']}: showed «{move['blocked']}», the act "
                        f"said «{out['why']}» (ok={out['ok']})")
                else:
                    assert out["ok"], (f"{move['id']} {move['verb']} "
                                       f"{move['args']}: {out['why']}")
                if i == 0:
                    assert not move["blocked"], "the top move is refused"
                    top += 1
                total += 1
        assert top >= 190, f"only {top} of 200 states had a move"
        assert len(kinds) >= 8, f"only {sorted(kinds)} ever suggested"
        return (f"{total} moves over 200 states ({len(kinds)} kinds: "
                f"{', '.join(sorted(kinds))}); {top} top moves all "
                f"actionable; {blocked} shown with their refusal")

    from . import renown_career_checks
    renown_career_checks.run(suite)
