"""The hunt's checks — board, search, paper and quotes. Not a suite:
`test_nemeses` runs these in its own, split out at the length rule.

Every act the Hunts tab offers is quoted by the function its button reads,
and each pair is driven through both doors here: the odds a search states and
the rate it finds at, a buy-off's fee and the purse, a trophy's terms and the
fitting, a raider's paper and the purse that pays it.
"""

from __future__ import annotations

from ..sim import exchequer, hunts, piracy, reach
from ..sim import nemeses as nem_sim
from ..sim import rival_ends
from . import nemesis_kit as kit


def run(suite) -> None:
    check = suite.check

    @check("a search finds a rival at the odds it states, over 300 tries")
    def _():
        game = kit.mid_game("search")
        nem = kit.rival(game, "hunter", ["shielded"])
        key = f"nemesis:{nem.id}"
        quote = hunts.search_odds(game, key, 3)
        assert quote["ok"] and 0.2 < quote["find"] < 0.95, quote
        found = 0
        for index in range(300):
            nem.location_id = game.location_id
            nem.status = "active"
            nem_sim.spot(game, nem, game.location_id, 1.0)
            out = hunts.search(game, key, 3)
            assert out["days"] <= 3, out
            found += bool(out["found"])
        rate = found / 300
        spread = 3.5 * (quote["find"] * (1 - quote["find"]) / 300) ** 0.5
        assert abs(rate - quote["find"]) < spread, (
            f"stated {quote['find']:.3f}, found {rate:.3f}")
        # A dark quarry is harder: the same search, a quarter the signature.
        nem.archetype = "corsair"
        dark = hunts.search_odds(game, key, 3)
        assert dark["find"] < quote["find"] * 0.6, (dark, quote)
        return (f"stated {quote['find']:.0%}, found {rate:.0%} of 300; a "
                f"dark quarry {dark['find']:.0%}")

    @check("every quote on the hunt panel is what its act does")
    def _():
        game = kit.mid_game("quotes")
        duel = kit.rival(game, "duellist", ["coward"])
        game.credits = 200_000
        terms = hunts.buy_off_terms(game, duel.id)
        before = game.credits
        assert hunts.buy_off(game, duel.id)["ok"]
        assert before - game.credits == terms["price"] and duel.status == "retired"
        # A Freehold gun will not graft to a grown hull, and the quote says so
        # in the words the act refuses with.
        rival_ends.take_trophy(game, kit.rival(game, "corsair", ["coward"]))
        alien = nem_sim.state(game).trophies[0]["id"]
        refused = hunts.trophy_terms(game, alien)
        assert not refused["ok"] and "graft" in refused["why"], refused
        assert hunts.mount_trophy(game, alien)["why"] == refused["why"]
        rival_ends.take_trophy(game, kit.rival(game, "husk", ["ghost"]))
        tid = nem_sim.state(game).trophies[-1]["id"]
        mount = hunts.trophy_terms(game, tid)
        assert mount["ok"], mount
        fitted = list(game.ship.fitted)
        assert hunts.mount_trophy(game, tid)["ok"]
        gone = [p for p in fitted if p not in game.ship.fitted]
        assert gone == ([mount["off"]] if mount["off"] else []), gone
        assert tid in game.ship.fitted
        assert any(w.id == tid for w in game.ship_stats.weapons)
        rival_ends.take_trophy(game, kit.rival(game, "ace", ["duellist"]))
        other = nem_sim.state(game).trophies[-1]["id"]
        sale = hunts.trophy_terms(game, other)
        before = game.credits
        assert hunts.sell_trophy(game, other)["ok"]
        assert game.credits - before == sale["worth"] > 0
        return (f"a fee of {terms['price']:,}; a mount off for the "
                f"{mount['replaces'] or 'empty slot'}; a sale at "
                f"{sale['worth']:,}")

    @check("the board posts raiders and rivals, and taking one gives a sighting")
    def _():
        game = kit.mid_game("board")
        port = next(s for s in game.galaxy.systems if s.port is not None
                    and any(r["kind"] == "raider"
                            for r in hunts.board(game, s)))
        game.location_id = port.id
        nem = kit.rival(game, "corsair", ["coward"],
                        where=game.galaxy.systems[-1].id)
        nem.bounty = {"reward": 5000, "issuer": "charter"}
        rows = hunts.board(game)
        kinds = {r["kind"] for r in rows}
        assert kinds == {"raider", "nemesis"}, kinds
        took = hunts.take(game, f"nemesis:{nem.id}")
        assert took["ok"] and nem.last_seen[0] == nem.location_id
        assert abs(nem_sim.confidence(game, nem) - 0.9) < 1e-9
        raider = next(r for r in rows if r["kind"] == "raider")
        assert hunts.take(game, raider["key"])["ok"]
        assert not hunts.take(game, raider["key"])["ok"], "taken twice"
        game.location_id = raider["system_id"]
        found = None
        for _ in range(12):
            out = hunts.search(game, raider["key"], 10)
            if out["found"]:
                found = out["encounter"]
                break
        assert found is not None, "twelve searches found no raider"
        credits = game.credits
        kit.ended(game, found, "destroyed")
        assert game.credits - credits >= raider["reward"]
        assert not hunts.taken(game) or all(
            r["key"] != raider["key"] for r in hunts.taken(game))
        return (f"{len(rows)} rows; {raider['name']} found and paid "
                f"{raider['reward']:,}")

    @check("a raider's paper: posted where raiders work, and paid by a purse")
    def _():
        game = kit.mid_game("paper")
        ports = [s for s in game.galaxy.systems if s.port is not None]
        rows = [(p, r) for p in ports for r in hunts.board(game, p)
                if r["kind"] == "raider"]
        assert rows, "no board in the sector posts a raider"
        for port, row in rows:
            there = game.galaxy.systems[row["system_id"]]
            assert piracy.raider_chance(game, there) > 0, row["where"]
            assert row["system_id"] in reach.component(game, start=port.id)
        port, row = rows[0]
        game.location_id = port.id
        assert hunts.take(game, row["key"])["ok"]
        game.location_id = row["system_id"]
        record = hunts.taken(game)[0]
        met = None
        for _ in range(15):
            out = hunts.search(game, row["key"], 10)
            if out["found"]:
                met = out["encounter"]
                break
        assert met is not None, "fifteen searches found nothing"
        hull = met["enemy"]["ship"]
        hull.layers[0].hp = 0.0
        again = hunts._raider_meeting(game, record, None)
        assert again["enemy"]["ship"] is hull and hull.layers[0].hp < \
            hull.layers[0].max, "the raider came back whole"
        purse = exchequer.purse(game, row["issuer"]).credits
        credits = game.credits
        _b, out = kit.ended(game, again, "driven-off")
        paid = out["nemesis"]["bounty"]
        assert paid == row["reward"] * hunts.DRIVEN_SHARE, (paid, row["reward"])
        assert abs((purse - exchequer.purse(game, row["issuer"]).credits)
                   - paid) < 1e-6, "the price did not come out of a purse"
        assert game.credits - credits >= paid
        assert not any(r["key"] == row["key"] for r in hunts.board(game, port))
        assert hunts.DRIVEN_SHARE == 0.5 and hunts.RAIDER_MEND == 0.01
        return (f"{len(rows)} raider postings, all where raiders work and in "
                f"reach; {row['name']} driven off for {paid:,.0f} out of the "
                f"{row['issuer']} purse")

    @check("a power posts no paper its purse cannot honour")
    def _():
        game = kit.mid_game("broke")
        port = next(p for p in game.galaxy.systems if p.port is not None
                    and any(r["kind"] == "raider"
                            for r in hunts.board(game, p)))
        exchequer.purse(game, port.port.faction).credits = 100.0
        left = [r for r in hunts.board(game, port) if r["kind"] == "raider"]
        assert not left, left
        nem = kit.rival(game, "corsair", ["coward"])
        nem.bounty = {"reward": 5000, "issuer": port.port.faction}
        credits = game.credits
        said = rival_ends._destroyed(game, nem)
        assert said["bounty"] == 100.0 and game.credits - credits == 100.0
        assert nem_sim.by_id(game, nem.id).status == "dead"
        return "an empty purse posts nothing, and pays only what it holds"
