"""The perks and the ending tracks, run by `test_renown` (split at the
length rule). Each perk is measured twice — held, and switched off with
`renown_kit.perk_off` — and the number it names has to move.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.milestones import RECRUIT_FLOOR, STANDING_FLOOR, TABLE_EVERY
from ..sim import renown, renown_facts, renown_perks
from . import renown_kit as kit
from .harness import Suite


def _full_hub():
    from ..sim import control, targets, track
    for tag in ("renown-berth", "renown-berth-b", "renown-berth-c"):
        game = new_game(tag)
        hub = next((c for c in track.contacts(game)
                    if c.kind == "anchorage" and c.berth == "hub"), None)
        if hub is not None:
            from ..sim import moorings
            target = targets.target_from_contact(game, hub)
            names = [n for n, _at in moorings.points(target, 0.0)]
            return game, hub, names, control
    raise AssertionError("no Fleet Hub in three sectors")


def run(suite: Suite) -> None:
    check = suite.check

    @check("every perk moves its number, and switched off it does not")
    def _():
        from ..sim import crew, diplomacy, freightlines
        said = []
        # Priority berthing: a full quay offers the captain its first berth.
        game, hub, names, control = _full_hub()
        held = {n: f"Hull {i}" for i, n in enumerate(names)}
        real = control.holders
        control.holders = lambda g, c: dict(held) if c is hub else real(g, c)
        try:
            kit.ranked(game, "captain")
            assert control.free(game, hub) == names[:1]
            with kit.perk_off("berth"):
                assert control.free(game, hub) == []
        finally:
            control.holders = real
        said.append("berth 1/0")
        # The charter fee waived.
        game = new_game("renown-charter")
        port = next(s for s in game.galaxy.systems if s.port
                    and s.port.level >= 2 and not s.port.independent
                    and s.port.faction in diplomacy.POWERS)
        game.location_id = port.id
        game.credits = 50_000
        fee = freightlines.charter_terms(game)["fee"]
        assert fee > 0
        kit.ranked(game, "captain")
        assert freightlines.charter_terms(game)["fee"] == 0
        with kit.perk_off("charter"):
            assert freightlines.charter_terms(game)["fee"] == fee
        said.append(f"charter ₡{fee:,}/0")
        # Better recruits: every candidate a level up, the same candidates.
        game = new_game("renown-recruits")
        port = next(s for s in game.galaxy.systems if s.port)
        base = [o.level for o in crew.pool_at(game, port)]
        kit.ranked(game, "commodore")
        lifted = [o.level for o in crew.pool_at(game, port)]
        assert base and len(base) == len(lifted)
        assert [a - b for a, b in zip(lifted, base)] == [RECRUIT_FLOOR] * len(
            base), (base, lifted)
        with kit.perk_off("recruits"):
            assert [o.level for o in crew.pool_at(game, port)] == base
        said.append(f"recruits +{RECRUIT_FLOOR}")
        # The standing floor, held by the daily tick.
        game = new_game("renown-floor")
        kit.ranked(game, "admiral")
        game.rep["freeholds"] = -50.0
        renown.tick(game)
        assert game.rep["freeholds"] == STANDING_FLOOR
        game.rep["freeholds"] = -50.0
        with kit.perk_off("floor"):
            renown.tick(game)
        assert game.rep["freeholds"] == -50.0
        said.append(f"floor {STANDING_FLOOR:+.0f}")
        # A motion of your own on the next order paper.
        from ..sim import assembly, assembly_session
        game = new_game("renown-table")
        kit.ranked(game, "admiral")
        terms = renown_perks.table_terms(game)
        assert terms["ok"], terms["why"]
        pick = terms["options"][0]
        assert renown_perks.table(game, pick.key)["ok"]
        again = renown_perks.table_terms(game)
        assert not again["ok"] and str(game.day + TABLE_EVERY) in again["why"]
        state = assembly.ensure(game)
        paper = renown_perks.motion(game, [])
        assert [t.key for t in paper] == [pick.key]
        assert renown_perks.motion(game, []) == [], "a motion tabled twice"
        game = new_game("renown-table")
        kit.ranked(game, "admiral")
        renown_perks.table(game, pick.key)
        with kit.perk_off("table"):
            assert renown_perks.motion(game, []) == []
            assert not renown_perks.table_terms(game)["ok"]
        assert state.session == 0 and assembly_session.lost_last(state) == set()
        said.append("motion 1/0")
        # Your name on the chart.
        game = new_game("renown-name")
        home = game.location_id
        was = game.galaxy.systems[home].name
        with kit.perk_off("name"):
            kit.ranked(game, "legend")
            assert not renown_perks.name_system(game, home)["ok"]
        assert game.galaxy.systems[home].name == was
        assert renown_perks.name_system(game, home)["ok"]
        assert game.galaxy.systems[home].name == renown_perks.name_of(game)
        assert not renown_perks.name_system(game, home)["ok"], "named twice"
        said.append(f"name «{renown_perks.name_of(game)}»")
        return "; ".join(said)

    @check("a rank's perks are exactly the ranks' own, in order")
    def _():
        game = new_game("renown-ranks")
        seen = []
        for rid, _name, need in renown.RANKS:
            renown.ensure(game).score = need
            assert renown.rank(game)["id"] == rid
            seen.append(len(renown.perks(game)))
            renown.ensure(game).score = max(0, need - 1)
            if need:
                assert renown.rank(game)["id"] != rid
        assert seen == sorted(seen) and seen[0] == 0 and seen[-1] == 6, seen
        return f"perks held by rank: {seen}"

    @check("the ending tracks read the truth")
    def _():
        from . import careful_captain as cc
        game = new_game("renown-tracks")
        from ..core.rng import RNG
        rng = RNG("renown-tracks")
        plan: dict = {}
        while game.day < 500 and not game.dead:
            day = game.day
            cc.turn(game, rng, plan)
            if game.day == day:
                game.advance_days(1)
        st = renown.state(game)
        ladders = renown.tracks(game)
        assert len(ladders) == 10
        rungs = 0
        for track, rows in ladders.items():
            assert [r["milestone"].step for r in rows] == [1, 2, 3], track
            for row in rows:
                m = row["milestone"]
                assert row["value"] == renown_facts.fact(game, m.fact)
                assert (row["day"] is not None) == (m.id in st.achieved)
                rungs += m.id in st.achieved
        lead = renown.leading(game)
        best = max(((sum(r["day"] is not None for r in rows), t)
                    for t, rows in ladders.items() if t != "ruin"))
        assert sum(r["day"] is not None for r in ladders[lead]) == best[0]
        assert renown.follow(game, "lineage")["ok"]
        assert renown.focus(game) == "lineage"
        assert not renown.follow(game, "ruin")["ok"]
        renown.follow(game, "")
        assert renown.focus(game) == lead
        return (f"day {game.day}: {rungs} rungs reached, leading {lead}; "
                "following a road moves counsel's focus")

    @check("every door counsel knows speaks when it should, and its act "
           "goes through or is refused as shown")
    def _():
        import copy
        from ..sim import counsel, haulers, freightlines, relight, weave
        from ..sim.ship import build_layers, make_ship
        said = {}

        def moves(game, sid):
            out = [m for m in counsel.moves(game) if m["id"].startswith(sid)]
            for m in out:
                got = counsel.act(copy.deepcopy(game), m)
                assert (got["ok"] if not m["blocked"] else
                        got["why"] == m["blocked"]), (m, got)
            return out

        # A bounty, to a hull armed for it, at a quay with paper.
        for tag in ("door-bounty", "door-bounty-b", "door-bounty-c"):
            game = new_game(tag)
            game.ship = make_ship("navis", ["fusion_lance", "fusion_lance",
                                            "fusion_plant", "fusion_plant",
                                            "reaction_organ", "opsin_eyes",
                                            "silicon_core"], game.ship.name)
            build_layers(game.ship, game.bonuses)
            game.fleet = [game.ship]
            game.recompute()
            got = moves(game, "bounty")
            if got:
                said["bounty"] = got[0]["title"]
                break
        assert "bounty" in said, "no bounty offered to an armed captain"
        # A deep anchor read: the next step toward the relight.
        game = new_game("door-relight")
        row = relight.standing(game)[0]
        weave.ensure(game).read.append(row["anchor_id"])
        got = moves(game, "relight")
        assert got, "an anchor read and no word about the relight"
        said["relight"] = got[0]["blocked"] or got[0]["title"]
        # A chartered house with an idle hauler: put her on a line.
        game = new_game("door-line")
        port = next(s for s in game.galaxy.systems if s.port
                    and s.port.level >= 2 and "shipyard" in s.port.services
                    and not s.port.independent)
        game.location_id = port.id
        game.credits = 200_000
        assert freightlines.charter(game)["ok"]
        assert haulers.buy_used(game, "tender")["ok"]
        got = moves(game, "line")
        assert got and got[0]["screen"] == "empire", got
        said["line"] = got[0]["title"]
        # A question on the bridge comes before everything but the urgent.
        from ..sim import approach
        game = new_game("door-envoy")
        for _ in range(400):
            if approach.holds(game):
                break
            game.advance_days(1)
        assert approach.holds(game), "no envoy came in 400 days"
        top = counsel.advise(game)
        assert top[0]["id"] in ("envoy", "fuel", "food", "hull", "hands"), top
        said["envoy"] = next(m for m in top if m["id"] == "envoy")["title"]
        return "; ".join(f"{k}: {v}" for k, v in said.items())
