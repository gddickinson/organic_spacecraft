"""The Kith's gift economy: no posted price, an answer, and what is owed.

The claims, in the spec's order (`reviews/2026-09-17/innovations/02-kith.md`);
contact and the lexicon are in `test_kith.py`:

- **The gift preview is honest** given what is known — seen, told, or
  nothing but the prior.
- **A debt unpaid becomes an insult**, on the day, not the day before.
- **A gathering's counter refuses a trade**, with the reason.
- **Songglass trades in the Verge**: made nowhere there, bought dear.
- **A graft fits only a grown hull**, and answers its adaptation.
- **The accord unlocks the Kith hulls**, grown only at a gathering.
- **The Concord is unchanged**, and the Kith are in no hostile pool.
- **A misreading costs what it says**, and a share of them is a fight;
  **standing from gifts** is capped and counted once in ten days.
"""

from __future__ import annotations

from ..data import kith as data
from ..data.chassis import CHASSIS, CHASSIS_BY_ID
from ..data.commodities import BY_ID
from ..data.factions import THE_POWERS
from ..sim import kith, kith_acts, kith_world
from ..world.galaxy import verge
from . import kith_kit as kit
from .efficacy import Lever, verdict
from .harness import Suite


def run(suite: Suite) -> None:
    check = suite.check

    @check("the gift preview is honest given what is known")
    def _():
        game = kit.at_gathering("kith-honest")
        kit.fluent(game, 1.0)                  # nothing to misread
        cid = kit.good_taken_as(game, ("prized", "welcome"))
        game.ship.cargo[cid] = 30
        first = kith_acts.preview_gift(game, cid, 10)
        assert first["source"] == "" and first["weights"] == kith_world.prior(cid)
        kith_acts.offer(game, cid, 10)
        said = kith_acts.preview_gift(game, cid, 10)
        assert said["source"] == "seen" and said["misread"] == 0.0
        (reaction, row), = said["outcomes"].items()
        got = kith_acts.offer(game, cid, 10)
        for key in ("reaction", "worth", "paid", "songglass", "debt",
                    "standing"):
            assert got[key] == row[key], (key, got[key], row[key])
        assert said["expect"]["songglass"] == got["songglass"]
        # The prior is what gatherings are: condensate across 60 of them.
        prized = total = 0
        for seed in ("kith-honest", "kith-place", "kith-odds"):
            g = kit.opened(seed)
            for system in kith_world.gatherings(g.galaxy):
                for good in data.PRIORS:
                    total += 1
                    prized += kith_world.prefs(g.galaxy, system)[good] == \
                        max(kith_world.prior(good).items(), key=lambda r: r[1])[0]
        share = prized / total
        assert share > 0.6, share
        return (f"{cid}: seen as {reaction}, previewed {row['songglass']} t, "
                f"given {got['songglass']} t; the prior's likeliest answer came "
                f"up {share:.0%} of {total} draws")

    @check("a debt unpaid becomes an insult on the day, and a gift pays first")
    def _():
        assert data.DEBT_DAYS == 90 and data.INSULT_STANDING == -10.0
        game = kit.at_gathering("kith-debt")
        kit.fluent(game, 1.0)
        cid = kit.good_taken_as(game, ("prized", "welcome"))
        game.ship.cargo[cid] = 20
        got = kith_acts.offer(game, cid, 10)
        owed = kith_acts.debt_at(game)
        assert abs(owed[0] - got["worth"] * (data.GENEROSITY - 1)) < 0.05
        game.advance_days(89)
        assert not kith_acts.debt_at(game)[2]
        rep = kith.standing(game)
        game.advance_days(1)
        assert kith_acts.debt_at(game)[2], "ninety days and no insult"
        assert abs(kith.standing(game) - (rep + data.INSULT_STANDING)) < 1e-9
        assert "owes" in kith_acts.ask(game, "ore")["why"]
        paid = kith_acts.offer(game, cid, 10)
        assert abs(paid["paid"] - min(owed[0], paid["worth"])) < 0.05
        return (f"owed {owed[0]:,.0f} after a gift worth {got['worth']:,.0f}; "
                f"day 89 quiet, day 90 an insult ({data.INSULT_STANDING:+g}); "
                f"the next gift paid {paid['paid']:,.0f} first")

    @check("a gathering's counter refuses a trade, and says where to go")
    def _():
        from ..sim import trade
        game = kit.at_gathering("kith-gate")
        game.ship.cargo["ore"] = 10
        for said in (trade.buy(game, "ore", 5), trade.sell(game, "ore", 5)):
            assert not said["ok"] and "gift" in said["why"], said
        assert game.ship.cargo["ore"] == 10
        home = kit.opened("kith-gate")
        kit.put(home, next(s.id for s in verge(home.galaxy) if s.port))
        home.ship.cargo["ore"] = 10
        assert trade.sell(home, "ore", 5)["ok"]
        return "buy and sell refused at the gathering; a Verge counter trades"

    @check("songglass is made nowhere in the Verge and bought dear by two")
    def _():
        from ..core.state import new_game
        from ..sim import market, trade
        closed = new_game("kith-glass")
        assert not any(s.market and data.SONGGLASS in s.market.stock
                       for s in closed.galaxy.systems)
        game = kit.opened("kith-glass")
        buyers = [s for s in verge(game.galaxy)
                  if s.market and data.SONGGLASS in s.market.stock]
        assert buyers and {s.port.faction for s in buyers} <= set(
            data.SONGGLASS_BUYERS)
        best = max(buyers, key=lambda s: market.quote_sell(game, s, "songglass"))
        price = market.quote_sell(game, best, "songglass")
        assert price > BY_ID["songglass"].base * 1.1, price
        kit.put(game, best.id)
        game.ship.cargo["songglass"] = 10
        money = game.credits
        sold = trade.sell(game, "songglass", 10)
        assert sold["ok"] and game.credits - money == sold["net"] > 0
        return (f"{len(buyers)} buyers; the best pays ₡{price:,} a tonne "
                f"against a base of ₡{BY_ID['songglass'].base:,}")

    @check("a graft fits only a grown hull, and answers its adaptation")
    def _():
        from ..data.parts import parts_available
        from ..sim.shipyard import validate
        for chassis in CHASSIS:
            ok = validate(chassis, ["chorus_lens"])[0]
            assert ok == (chassis.family == "grown"), (chassis.id, ok)
        navis = CHASSIS_BY_ID["navis"]
        game = kit.at_gathering("kith-graft")
        assert "chorus_lens" not in {p.id for p in parts_available(
            "sensor", navis, game.research.unlocked)}
        game.research.unlocked.append("kith_chorus_lens")
        assert "chorus_lens" in {p.id for p in parts_available(
            "sensor", navis, game.research.unlocked)}

        fitted = [p for p in game.ship.fitted if p != "opsin_eyes"]

        def scan():
            game.ship.fitted = fitted + ["chorus_lens"]
            game.ship.adaptations = ["acute_opsins"]
            return game.recompute().scan
        ok, why = verdict(Lever("graft", "a lens set in acute eyes sees more",
                                (kith, "synergy", lambda ship: []), scan,
                                "lower"))
        assert ok, why
        grown = sum(1 for c in CHASSIS if c.family == "grown")
        return f"fits {grown} grown classes of {len(CHASSIS)}; {why.split(';')[0]}"

    @check("the accord unlocks the Kith hulls, grown only at a gathering")
    def _():
        from ..sim import shipyard
        game = kit.at_gathering("kith-accord")
        drifter = CHASSIS_BY_ID["drifter"]
        assert drifter.family == "xeno" and drifter.tech == data.ACCORD_GATE
        assert not shipyard.can_build_here(game, game.system, drifter)[0]
        kit.fluent(game, 1.0)
        game.rep["kith"] = 45
        out = kith_acts.sign_accord(game)
        assert out["ok"] and not out["misread"] and game.kith.accord >= 0
        assert shipyard.can_build_here(game, game.system, drifter)[0]
        hub = next(s for s in verge(game.galaxy)
                   if s.port and "shipyard" in s.port.services)
        assert not shipyard.can_build_here(game, hub, drifter)[0]
        crew = len(game.officers)
        game.officers = [o for o in game.officers if o.stat != "nav"]
        took = kith_acts.take_pilot(game)
        assert took["ok"] and took["officer"].lineage == "kith", took
        assert game.kith.pilot == 2 and len(game.officers) <= crew
        return (f"accord on day {game.kith.accord}: DRIFTER and CHOIR-COLONY "
                f"grow at {game.system.port.name} and at no Verge yard; "
                f"{took['officer'].name} signed on")

    @check("the Concord is the four powers', and no pool holds the Kith")
    def _():
        from ..sim import diplomacy as dip
        from ..sim import encounters
        from ..core.rng import RNG
        assert dip.POWERS == ("charter", "concordat", "freeholds", "sanhedrin")
        assert "kith" not in THE_POWERS
        game = kit.at_gathering("kith-concord")
        before = dip.concord_progress(game)
        for rep in (-100, 100):
            game.rep["kith"] = rep
            assert dip.concord_progress(game) == before
        game.rep["kith"] = -100
        met = set()
        for n in range(400):
            enc = encounters.roll_encounter(game, game.system,
                                            RNG(f"kith-pool-{n}"))
            if enc:
                met.add(enc["enemy"]["faction"])
        assert "kith" not in met, met
        provoked = kith.fight(game, "A test.")
        assert provoked["enemy"]["faction"] == "kith"
        return (f"400 arrivals at a gathering at −100 met {sorted(met) or 'nothing'}"
                f"; a misreading met a {provoked['enemy']['name']}")

    @check("a misreading costs four points, and three in ten are a fight")
    def _():
        assert data.MISREAD_STANDING == -4.0 and data.FIGHT_SHARE == 0.3
        game = kit.at_gathering("kith-misread")
        game.ship.cargo["ore"] = 5000
        misread = fights = 0
        while misread < 400:
            kit.fluent(game, 0.4, ("exchange",))   # held: exchanges teach
            rep = kith.standing(game)
            got = kith_acts.offer(game, "ore", 1)
            if got["misread"]:
                misread += 1
                fights += bool(got.get("encounter"))
                assert abs(kith.standing(game) - rep - (-4.0)) < 1e-9
            game.rep["kith"] = 0.0
        share = fights / misread
        assert 0.23 < share < 0.37, share
        return f"{misread} misreadings, each −4; {share:.0%} of them a fight"

    @check("a gift's standing is capped at three, once in ten days a gathering")
    def _():
        assert (data.GIFT_STANDING_CAP, data.GIFT_STANDING_DAYS,
                data.OFFENCE_STANDING) == (3.0, 10, -3.0)
        game = kit.at_gathering("kith-thanks")
        kit.fluent(game, 1.0)
        cid = kit.good_taken_as(game, ("prized", "welcome"))
        game.ship.cargo[cid] = 400
        big = kith_acts.offer(game, cid, 100)     # worth far past the cap
        assert big["standing"] == 3.0, big
        game.advance_days(9)
        assert kith_acts.offer(game, cid, 10)["standing"] == 0.0
        game.advance_days(1)
        again = kith_acts.offer(game, cid, 10)
        assert again["standing"] > 0.0, again
        bad = kit.good_taken_as(game, ("offended",)) or "silicon"
        if kit.truth(game, bad) == "offended":
            game.ship.cargo[bad] = 5
            assert kith_acts.offer(game, bad, 5)["standing"] == -3.0
        return (f"+{big['standing']:g} for {big['worth']:,.0f} of worth; "
                f"nothing on day 9, +{again['standing']:g} on day 10")

    @check("a gathering grows its graft at 15,000 given, and a debt cleared counts")
    def _():
        assert (data.GRAFT_AT, data.DEBT_PAID_STANDING) == (15000.0, 1.0)
        game = kit.at_gathering("kith-grown")
        kit.fluent(game, 1.0)
        game.rep["kith"] = 15
        graft = kith_world.graft_of(game.galaxy, game.system)
        cid = kit.good_taken_as(game, ("welcome",)) or "phosphate"
        game.ship.cargo[cid] = 5000
        worth = data.WORTH[kit.truth(game, cid)] * BY_ID[cid].base
        under = int(14_999 // worth)
        got = kith_acts.offer(game, cid, under)
        assert got["graft"] == "" and graft.gate not in game.research.unlocked
        game.advance_days(10)
        owed = kith_acts.debt_at(game)[0]
        more = kith_acts.offer(game, cid, max(1, -(-owed // worth)))
        assert more["graft"] == graft.part, more
        assert graft.gate in game.research.unlocked
        # The second gift cleared the first's surplus: +1 on its regard.
        regard = min(data.GIFT_STANDING_CAP,
                     more["worth"] / data.GIFT_STANDING_PER)
        assert abs(more["standing"] - (regard + 1.0)) < 0.01, more
        return (f"{got['worth']:,.0f} given: nothing; past 15,000: a "
                f"{graft.part.replace('_', ' ')}; the debt cleared, +1")

    @check("a berth takes five days and mends; passage charts every gathering")
    def _():
        assert data.BERTH_DAYS == 5 and data.PILOT_LEVEL == 4
        game = kit.at_gathering("kith-berth")
        kit.fluent(game, 0.8)
        game.rep["kith"] = 20
        for layer in game.ship.layers:
            layer.hp = layer.max * 0.5
        said = kith_acts.preview_ask(game, "berth")
        day = game.day
        kit.fluent(game, 1.0)                     # nothing left to misread
        out = kith_acts.berth(game)
        assert out["ok"] and not out["misread"], out
        assert game.day - day == said["days"] == 5
        assert all(layer.hp == layer.max for layer in game.ship.layers)
        game.kith.charted = [game.location_id]
        told = kith_acts.passage(game)
        places = {s.id for s in kith_world.gatherings(game.galaxy)}
        assert told["ok"] and set(game.kith.charted) == places
        assert places <= set(game.discovered["systems"])
        game.kith.history = [[0, "x", "y"]] * 70
        kith.note(game.kith, game.day, "z", "last")
        assert len(game.kith.history) == kith.HISTORY_KEEP == 60
        return (f"berth: {out['mended']:,.0f} hp mended in 5 days; passage: "
                f"{len(told['told'])} gatherings sung onto the chart")
