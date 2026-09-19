"""The rules the 2026-09-17 review found bent, performed and compared.

Not exploits — `test_exploits` holds those — but places where the game said
one thing and did another, or did the right thing at the wrong time:

- **The Bloom was a wall, not a slope**: 2-12 of 42 systems for three years,
  then the sector in two.
- **A lost battle killed you only in the window.**
- **Envoys arrived from day one** and "Leave it for now" left nothing.
- **Starting pockets ran from 2 to 42 systems.**
- **A survey commission paid for surveys made before it was taken.**
- **A shortage price read as a price** long after the shortage ended.
- **The bench said it was short every few days.**
- **The tutorial and the ending cards counted from memory.**
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..core.util import spelled
from ..data.factions import KIN, THE_POWERS
from ..data.lessons import CHAPTERS_BY_ID, LESSONS_BY_ID
from ..data.lore import VICTORIES
from ..data.shocks import SHOCKS
from ..data.tech import TECH
from ..sim import aftermath, approach, combat, contracts, encounters
from ..sim import inquiry, market, passage, reach, research, threat, upkeep
from ..sim.actions import jump_quote
from .harness import Suite


def _fed(game, days: int = 200) -> None:
    game.credits = max(game.credits, 60_000)
    for cid, a_day in upkeep.demand(game).items():
        game.ship.cargo[cid] = max(game.ship.cargo.get(cid, 0), a_day * days)


def _milestones(seed: str) -> tuple:
    """Days to a quarter and to three-quarters of the sector, idle and fed."""
    game = new_game(seed)
    n = len(game.galaxy.systems)
    quarter = None
    while game.day < 3650 and not game.dead:
        _fed(game)
        game.advance_days(30)
        held = len(threat.bloom_systems(game))
        if quarter is None and held >= n / 4:
            quarter = game.day
        if held >= 3 * n / 4:
            return quarter, game.day
    return quarter, None


def run(suite: Suite) -> None:
    check = suite.check

    @check("the Bloom comes on a slope, not a wall")
    def _():
        # Measured before, on these three: a quarter of the sector on days
        # 900, 1,350 and 1,440, and a quarter to three-quarters in 720-1,050
        # days — quiet, then everything. After: 780, 870, 720 and 1,110-1,380.
        rows = [_milestones(seed) for seed in ("pace-a", "pace-c", "alpha-1")]
        assert all(q and t for q, t in rows), f"it never got there: {rows}"
        quarter = sum(q for q, _t in rows) / len(rows)
        fall = sum(t - q for q, t in rows) / len(rows)
        assert quarter <= 1100, (
            f"a quarter of the sector took {quarter:.0f} days on average — the "
            "pressure is arriving late again")
        assert fall >= 950, (
            f"a quarter to three-quarters in {fall:.0f} days — the back half "
            "is a cliff again")
        assert threat.THROW_RATE == 0.30 and threat.THROW_AT == 0.35
        return (f"a quarter by day {quarter:.0f}, three-quarters "
                f"{fall:.0f} days after that (mean of three)")

    @check("a lost battle kills the captain in the sim, once")
    def _():
        game = new_game("lost-at-sea")
        rng = RNG("lost")
        battle = combat.start(game.ship, game.ship_stats,
                              encounters.make_enemy(rng, "freeholds", 0.6),
                              rng=rng, game=game)
        battle.result, battle.over = "lost", True
        out = aftermath.resolve(game, battle, rng)
        assert game.dead and game.ending == "lost", (
            "the hull was lost and the captain walked away from it")
        assert out["died"] and game.death_reason == "Destroyed in action."
        again = aftermath.resolve(game, battle, rng)
        assert again["already"], "the same defeat was resolved twice"
        # A vault still answers it: the one door is `Game.die`.
        saved = new_game("lost-with-a-vault")
        saved.colony_fx["has_vault"] = True
        other = combat.start(saved.ship, saved.ship_stats,
                             encounters.make_enemy(rng, "freeholds", 0.6),
                             rng=rng, game=saved)
        other.result, other.over = "lost", True
        aftermath.resolve(saved, other, rng)
        assert not saved.dead and saved.ship.chassis == "spore", (
            "the vault did not open")
        return "dead on a lost engagement, and a vault still opens"

    @check("no envoy in the first two months, and 'leave it' leaves it")
    def _():
        game = new_game("envoy-grace")
        game.credits = 200_000
        for cid in ("ore", "volatiles", "biomass", "alloy", "silicon"):
            game.ship.cargo[cid] = 200
        for fid in approach.dip.POWERS:
            game.rep[fid] = 30.0
        for attempt in range(approach.GRACE_DAYS):
            game.day = attempt
            assert not approach.tick(game, 30, RNG(f"g{attempt}")), (
                f"an envoy on day {attempt}")
        game.day = approach.GRACE_DAYS
        came = next((a for a in range(200)
                     if approach.tick(game, 30, RNG(f"late{a}"))), None)
        assert came is not None, "nobody came after the grace either"
        envoy = game.envoy
        assert approach.holds(game)
        terms = approach.set_aside(game, envoy)
        assert terms["ok"] and not approach.holds(game), terms
        from ..core import clock
        assert not clock._awaiting_answer(game), "the clock still waits on it"
        game.day = terms["until"]
        said = approach.tick(game, 1, RNG("back"))
        if not envoy.over:
            assert said and "again" in said[0][1] and approach.holds(game), said
        return (f"none in {approach.GRACE_DAYS} days of asking; set aside "
                f"until day {terms['until']}, then back at the door")

    @check("a boxed-in opening is given a way out; a wide one is not touched")
    def _():
        # Measured on these forty before: 15 opened on fewer than eight
        # systems and 14 on one power's ports, the worst on two.
        boxed = lanes = 0
        for index in range(40):
            game = new_game(f"pocket-{index}")
            within = reach.component(game)
            powers = {game.galaxy.systems[i].port.faction for i in within
                      if game.galaxy.systems[i].port}
            assert len(within) >= passage.MIN_POCKET and len(powers) >= 2, (
                f"pocket-{index} opens on {len(within)} systems and "
                f"{len(powers)} power(s)")
            got = passage.lanes(game)
            lanes += len(got)
            if got:
                boxed += 1
                a, b = got[0]
                game.location_id = a.id
                assert jump_quote(game, b)["in_range"], "the lane is not flyable"
                assert "Charted lane" in reach.note(game)
                assert any("pilots have filed" in t for _d, t, _k in game.log)
        assert 10 <= boxed <= 20 and lanes <= 2 * boxed, (boxed, lanes)
        return (f"40 openings, every one at least {passage.MIN_POCKET} systems "
                f"and two powers; {boxed} given {lanes} lane(s), the rest none")

    @check("a survey commission counts only what was charted after it")
    def _():
        game = new_game("commission-count")
        target = next(s for s in game.galaxy.systems if len(s.bodies) >= 4
                      and s.id != game.location_id)
        for body in target.bodies[:2]:
            body.surveyed, body.surveyed_on = True, 0
        game.day = 5
        job = contracts.Contract(id=1, kind="survey", issuer="charter",
                                 issued_at=game.location_id, title="t",
                                 posting="p", target_system=target.id,
                                 amount=2, reward=100, rep=1, deadline=400)
        assert contracts.accept(game, job)[0]
        contracts.check(game)
        assert job.progress == 0 and not job.done, (
            f"two bodies charted before the job counted: {job.progress}")
        for body in target.bodies[2:4]:
            body.surveyed, body.surveyed_on = True, game.day
        contracts.check(game)
        assert job.done, "surveys made after taking it did not count"
        return "two charted beforehand counted 0; two after, and it paid"

    @check("a shortage price is marked, and discounted once it is over")
    def _():
        game = new_game("shock-quote")
        port = next(s for s in game.galaxy.systems
                    if s.market and "biomass" in s.market.stock)
        blight = next(k for k in SHOCKS if k.id == "blight")
        game.shocks.append(market.Shock(id=1, kind=blight.id, system_id=port.id,
                                        commodity="biomass", until=40))
        market.apply_to_markets(game)
        market.note_prices(game, port)
        quote = game.register[str(port.id)]
        assert quote.shocked.get("biomass") == 40, quote.shocked
        game.day = 20
        live = next(r for r in market.best_markets(game, "biomass", limit=99)
                    if r["system"] is port)
        game.day = 41
        game.shocks.clear()
        over = next(r for r in market.best_markets(game, "biomass", limit=99)
                    if r["system"] is port)
        plain = market.confidence(41)
        assert abs(live["confidence"] - market.confidence(20)) < 1e-9
        assert abs(over["confidence"] - plain * market.SHOCK_SPENT) < 1e-9, over
        return (f"confidence {live['confidence']:.2f} while it lasted, "
                f"{over['confidence']:.2f} after (age alone says {plain:.2f})")

    @check("the bench says it is short once per shortage")
    def _():
        # Measured before: a quarter chance a day — a line every one to five
        # days for as long as the programme wanted what nobody was carrying.
        game = new_game("quiet-bench")
        tech = next(iter(research.researchable(game.research.unlocked)))
        research.set_project(game.research, tech.id)
        inquiry.store(game.research).clear()
        for _ in range(4):
            _fed(game)
            game.advance_days(30)
        said = [t for _d, t, _k in game.log if "The bench is short" in t]
        assert 1 <= len(said) <= 2, f"{len(said)} shortage lines in 120 days"
        return f"{len(said)} line(s) in 120 starved days"

    @check("the tutorial and the ending cards count from the data")
    def _():
        research_then = LESSONS_BY_ID["research"].then
        assert f"{spelled(len(TECH))} nodes" in research_then, research_then
        assert CHAPTERS_BY_ID["powers"].blurb.lower().startswith(
            spelled(len(THE_POWERS)))
        assert "survey" not in LESSONS_BY_ID["sell"].ask.lower(), (
            "lesson nine asks for survey data before the first survey")
        pairs = len(THE_POWERS) * (len(THE_POWERS) - 1) // 2
        concord = next(v for v in VICTORIES if v[0] == "concord")[3]
        assert f"{spelled(pairs)} pairs" in concord, concord
        game = new_game("apostasy-kin")
        game.ship.chassis, game.officers = "cantor", []
        game.recompute()
        game.rep["sanhedrin"] = KIN - 1
        assert not threat.victory_progress(game)["apostasy"][2]
        game.rep["sanhedrin"] = KIN
        assert threat.victory_progress(game)["apostasy"][2], (
            "the card says Kin and Kin does not take it")
        return (f"{len(TECH)} nodes, {len(THE_POWERS)} powers, {pairs} pairs; "
                f"Apostasy at Kin ({KIN}) and not a point under")
