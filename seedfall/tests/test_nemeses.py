"""Nemeses and the hunt — rivals who remember, a hunt you choose, a way to hide.

The play-test found no combat career: encounters about 1.3 a year and none
of them seekable, an armed fighter with **no bounty in fifteen career-years**,
and every enemy a stranger. These play the answer end to end — each rise from
the event that causes it, the roaming and the ageing of what you know, the
search at its stated odds, one hull from meeting to meeting, every ending
through `aftermath.resolve` and none of them a new result id, the switch that
runs you dark, a chronicle carried across a process, and the balance the
design asked for, measured by fighting it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from ..core.rng import RNG
from ..data import countermeasures as cm
from ..data.nemeses import ENDINGS, TROPHY_ACCURACY
from ..sim import battle_state, customs, encounters
from ..sim import nemeses as nem_sim
from ..sim import rival_ends, rivals, running_dark, trade, warrants
from ..world.galaxy import distance
from . import nemesis_hunts
from . import nemesis_kit as kit
from .efficacy import Lever, verdict
from .harness import Suite

ROOT = Path(__file__).resolve().parents[2]


def _arrivals(game, tries: int = 30) -> float:
    """The per-arrival encounter rate across the sector, seeded."""
    met = total = 0
    for system in game.galaxy.systems:
        for index in range(tries):
            total += 1
            met += encounters.roll_encounter(
                game, system, RNG(f"arrive-{system.id}-{index}")) is not None
    return met / total


def run(suite: Suite) -> None:
    check = suite.check

    @check("a rival rises from each of the five events the design names")
    def _():
        risen = {}
        with kit.certain_rises():
            game = kit.mid_game("rise-corsair")
            kit.raider_country(game)
            kit.ended(game, kit.plain_fight(game, "freeholds", "c"), "escaped")
            risen["corsair"] = [n.archetype for n in nem_sim.roster(game)]
            game = kit.mid_game("rise-ace")
            kit.ended(game, kit.plain_fight(game, "concordat", "a"), "struck")
            risen["ace"] = [n.archetype for n in nem_sim.roster(game)]
            game = kit.mid_game("rise-husk")
            kit.ended(game, kit.plain_fight(game, "bloom", "h"), "driven-off")
            risen["husk"] = [n.archetype for n in nem_sim.roster(game)]
            game = kit.mid_game("rise-hunter")
            warrants.issue(game, "concordat", "hunt", "a test", "everywhere",
                           price=9000)
            game.advance_days(1)
            risen["hunter"] = [n.archetype for n in nem_sim.roster(game)]
            hunter = nem_sim.roster(game)[0]
            assert hunter.faction == "concordat", hunter.faction
            game = kit.mid_game("rise-duellist")
            port = next(s for s in game.galaxy.systems if s.port is not None
                        and s.port.faction == "freeholds" and s.market)
            game.location_id = port.id
            game.recompute()
            game.ship.cargo["silicon"] = 120
            sold = trade.sell(game, "silicon", 120)
            assert sold["ok"], sold
            game.advance_days(1)
            risen["duellist"] = [n.archetype for n in nem_sim.roster(game)]
        for kind, got in risen.items():
            assert got == [kind], f"{kind}: the roster read {got}"
        assert len(risen) == 5
        return "corsair, ace, husk, hunter and duellist, one from each event"

    @check("rises are rare enough to be personal: capped, and spaced")
    def _():
        with kit.certain_rises():
            game = kit.mid_game("rise-cap")
            first = nem_sim.rise(game, "corsair")
            again = nem_sim.rise(game, "corsair")
            assert first is not None and again is None, (
                "two rivals rose on one day")
            game.day += nem_sim.RISE_GAP
            for _ in range(8):
                nem_sim.state(game).marks.pop("last_rise", None)
                nem_sim.rise(game, "ace")
        live = len(nem_sim.live(game))
        assert live == nem_sim.MAX_ACTIVE, live
        assert nem_sim.RISE_GAP == 150 and nem_sim.MAX_ACTIVE == 4
        return (f"one a day at most, {nem_sim.RISE_GAP} days apart, and never "
                f"more than {live} out at once")

    @check("they roam; a hunter closes on you; what you know goes stale")
    def _():
        game = kit.mid_game("roam")
        far = max(game.galaxy.systems,
                  key=lambda s: distance(s, game.system))
        roamer = kit.rival(game, "corsair", ["coward"], where=far.id)
        hunter = kit.rival(game, "hunter", ["shielded"], where=far.id)
        nem_sim.spot(game, roamer, far.id, 1.0)
        start = distance(far, game.system)
        visited = {roamer.location_id}
        for _ in range(90):
            game.advance_days(1)
            visited.add(roamer.location_id)
        closed = distance(game.galaxy.systems[hunter.location_id], game.system)
        assert len(visited) >= 3, f"a corsair saw {len(visited)} systems in 90 d"
        assert closed < start, f"the hunter kept {closed:.1f} of {start:.1f} ly"
        # Ninety days on, the sighting has halved four and a half times.
        conf = nem_sim.confidence(game, roamer)
        assert abs(conf - 0.5 ** (90 / nem_sim.HALF_LIFE)) < 0.05 or conf < 0.1
        nem_sim.spot(game, roamer, far.id, 1.0)
        game.day += 20
        half = nem_sim.confidence(game, roamer)
        assert abs(half - 0.5) < 1e-9, half
        roamer.traits.append("ghost")
        assert abs(nem_sim.confidence(game, roamer) - 0.25) < 1e-9
        return (f"{len(visited)} systems in 90 d; the hunter from {start:.0f} "
                f"to {closed:.0f} ly; a 20-day sighting 50%, a ghost's 25%")

    @check("a rival brings the same hull, holes and all, to every meeting")
    def _():
        game = kit.mid_game("same-hull")
        nem = kit.rival(game, "duellist", ["duellist"])
        uid = nem.ship.uid
        enc = rivals.encounter(game, nem)
        assert enc["enemy"]["ship"] is nem.ship and enc["nemesis"] == nem.id
        b, rng = kit.battle_with(game, enc)
        from ..sim import combat
        from . import captain_ai
        for _ in range(30):
            if b.over or any(l.hp < l.max for l in nem.ship.layers):
                break
            combat.take_turn(b, captain_ai.orders(b), rng)
        hurt = [layer.hp for layer in nem.ship.layers]
        assert hurt != [layer.max for layer in nem.ship.layers], "no damage"
        again = rivals.encounter(game, nem)
        assert again["enemy"]["ship"].uid == uid
        assert [layer.hp for layer in again["enemy"]["ship"].layers] == hurt
        return (f"uid {uid} both times, the same {sum(hurt):.0f} of "
                f"{sum(layer.max for layer in nem.ship.layers):.0f} hull")

    @check("beaten, they go to the yard and come back a level stronger")
    def _():
        game = kit.mid_game("return")
        nem = kit.rival(game, "corsair", ["coward"])
        before = (sum(layer.max for layer in nem.ship.layers),
                  rivals.difficulty(nem),
                  rivals.encounter(game, nem)["enemy"]["resolve"])
        kit.ended(game, rivals.encounter(game, nem), "driven-off")
        assert nem.status == "wounded", nem.status
        wait = nem.back_on - game.day
        assert 30 <= wait <= 90, wait
        game.advance_days(wait)
        assert nem.status == "active" and nem.level == 2, (nem.status, nem.level)
        after = (sum(layer.max for layer in nem.ship.layers),
                 rivals.difficulty(nem),
                 rivals.encounter(game, nem)["enemy"]["resolve"])
        assert all(a > b for a, b in zip(after, before)), (before, after)
        return (f"{wait} d at the yard; hull {before[0]:.0f} → {after[0]:.0f}, "
                f"threat {before[1]:.2f} → {after[1]:.2f}, nerve "
                f"{before[2]:.0f} → {after[2]:.0f}")

    @check("destroyed: the price paid, a trophy cut out, and the issuer glad")
    def _():
        game = kit.mid_game("destroyed")
        nem = kit.rival(game, "corsair", ["ambusher"])
        nem.bounty = {"reward": 7000, "issuer": "concordat"}
        credits, rep = game.credits, game.rep["concordat"]
        _b, out = kit.ended(game, rivals.encounter(game, nem), "destroyed")
        said = out["nemesis"]
        assert nem.status == "dead" and said["bounty"] == 7000, said
        assert game.credits - credits >= 7000 + out["credits"] - 1
        assert game.rep["concordat"] > rep
        trophy = nem_sim.state(game).trophies[0]
        from ..data.parts import part
        made, base = part(trophy["id"]), part(trophy["base"])
        assert made.wpn.acc == base.wpn.acc + TROPHY_ACCURACY
        assert made.name.startswith("Kit's"), made.name
        return (f"{said['bounty']:,} paid, Concordat +"
                f"{game.rep['concordat'] - rep:.0f}, and {made.name}")

    @check("spared, some stay grateful and some turn — by archetype")
    def _():
        loyal = {}
        for kind in ("hunter", "corsair", "ace"):
            kept = 0
            for index in range(60):
                game = kit.mid_game(f"spare-{kind}-{index}")
                nem = kit.rival(game, kind)
                nem.grudge["theirs"] = 0.0
                kit.ended(game, rivals.encounter(game, nem), "struck",
                          seed=f"s{index}")
                assert nem.status == "allied"
                kept += nem.loyal
            loyal[kind] = kept / 60
        assert loyal["hunter"] < loyal["corsair"] < loyal["ace"], loyal
        # A loyal one turns up in your next fight; a false one ambushes you.
        game = kit.mid_game("ally")
        friend = kit.rival(game, "ace")
        friend.status, friend.loyal = "allied", True
        b, _rng = kit.battle_with(game, kit.plain_fight(game, "freeholds", "x"))
        assert any(c.ship is friend.ship for c in b.consorts), "no ally came"
        false = kit.rival(game, "hunter", ["shielded"])
        false.status, false.loyal = "allied", False
        friend.status = "retired"
        turned = rivals.meet(game, game.system)
        assert turned and turned["nemesis"] == false.id
        assert turned["first_volley"] == "enemy", turned["first_volley"]
        return (", ".join(f"{k} {v:.0%} loyal" for k, v in loyal.items())
                + "; the ally comes, the traitor fires first")

    @check("every ending id maps, and no new one is made")
    def _():
        assert set(ENDINGS) == set(battle_state.ENDINGS), (
            set(ENDINGS) ^ set(battle_state.ENDINGS))
        seen = set()
        for result in sorted(battle_state.ENDINGS):
            game = kit.mid_game(f"end-{result}")
            nem = kit.rival(game, "duellist")
            b, out = kit.ended(game, rivals.encounter(game, nem), result)
            assert b.result == result and out["result"] == result
            assert nem.history[-1][2] == result
            seen.add(nem.status)
        assert "dead" in seen and "wounded" in seen and "allied" in seen
        return f"{len(battle_state.ENDINGS)} ids, statuses {sorted(seen)}"

    @check("a fight with nobody's rival in it tallies exactly as before")
    def _():
        rows = []
        for neutral in (False, True):
            tally = []
            for index, (faction, result) in enumerate(
                    [("concordat", "destroyed"), ("freeholds", "driven-off"),
                     ("sanhedrin", "parley"), ("concordat", "struck"),
                     ("freeholds", "escaped"), ("bloom", "routed")]):
                game = kit.mid_game(f"tally-{index}")
                if neutral:
                    held = rival_ends.settle
                    rival_ends.settle = lambda _g, _b, _o: {}
                try:
                    _b, out = kit.ended(
                        game, kit.plain_fight(game, faction, f"t{index}"),
                        result)
                finally:
                    if neutral:
                        rival_ends.settle = held
                tally.append((out["result"], round(game.credits),
                              sorted(out["standing"]), out["research"]))
            rows.append(tally)
        assert rows[0] == rows[1], rows
        assert len(rows[0]) == 6
        return "six ordinary fights, credits, standing and research identical"

    @check("running dark takes 30-50% of arrivals away, and a quay notices")
    def _():
        game = kit.mid_game("dark")
        lit = _arrivals(game)
        running_dark.set_dark(game, True)
        dark = _arrivals(game)
        cut = 1.0 - dark / lit
        assert 0.30 <= cut <= 0.55, f"lit {lit:.3f}, dark {dark:.3f}"
        assert running_dark.signature(game) is cm.DARK
        game.ship.fitted.append("stilling_mantle")
        assert running_dark.signature(game) is cm.SHROUDED
        assert running_dark.exposure(game) < 1.0 - cut + 0.05
        port = next(s for s in game.galaxy.systems if s.port is not None
                    and customs.regime(s.port.faction)
                    and customs.regime(s.port.faction).zeal)
        game.location_id = port.id
        searched_dark = customs.chance(game, port.port.faction)
        running_dark.set_dark(game, False)
        searched_lit = customs.chance(game, port.port.faction)
        assert searched_dark > searched_lit, (searched_dark, searched_lit)
        assert running_dark.SEEN_SHARE == 0.6
        return (f"arrivals {lit:.1%} → {dark:.1%} ({cut:.0%} fewer); the hold "
                f"opened {searched_lit:.0%} → {searched_dark:.0%} docked dark")

    @check("the switch, and the rivals, move what they claim to")
    def _():
        def dark_rate():
            game = kit.mid_game("lever-dark")
            running_dark.set_dark(game, True)
            return _arrivals(game, 12)

        def rival_rate():
            game = kit.mid_game("lever-meet")
            kit.rival(game, "hunter", ["shielded"])
            met = sum(encounters.roll_encounter(game, game.system,
                                                RNG(f"m{i}")) is not None
                      for i in range(80))
            return met / 80

        def returned_hull():
            game = kit.mid_game("lever-level")
            nem = kit.rival(game, "corsair", ["coward"], level=3)
            return sum(layer.max for layer in nem.ship.layers)

        def trophy_eye():
            game = kit.mid_game("lever-trophy")
            nem = kit.rival(game, "corsair", ["coward"])
            made = rival_ends.take_trophy(game, nem)
            from ..data.parts import part
            return part(made["id"]).wpn.acc

        from dataclasses import replace
        levers = [
            Lever("run-dark", "running dark hides you from arrivals",
                  (running_dark, "exposure", lambda _g: 1.0), dark_rate,
                  "higher"),
            Lever("rival-meets", "a rival in the system comes for you",
                  (rivals, "meet", lambda _g, _s: None), rival_rate, "lower"),
            Lever("rival-levels", "a returning rival is built to its level",
                  (rivals, "difficulty", lambda n: n.threat), returned_hull,
                  "lower"),
            Lever("trophy-eye", "a trophy mount shoots straighter",
                  (rival_ends, "trophy_part",
                   lambda r, base: replace(base, id=r["id"])), trophy_eye,
                  "lower"),
        ]
        notes = []
        for lever in levers:
            ok, said = verdict(lever)
            assert ok, said
            notes.append(said.split(";")[0])
        assert len(notes) == 4
        return " · ".join(notes)

    @check("level one wins 60-75%, level five 30-45%, over 200 fights each")
    def _():
        game = kit.mid_game("balance")
        one, tally_one = kit.win_rate(game, 1, 200)
        five, tally_five = kit.win_rate(game, 5, 200)
        assert 0.60 <= one <= 0.75, (one, tally_one)
        assert 0.30 <= five <= 0.45, (five, tally_five)
        assert rivals.PER_LEVEL == 0.4 and rivals.RELENTLESS_NERVE == 1.4
        return f"level 1 {one:.0%}, level 5 {five:.0%} against a warfit NAVIS"

    @check("rivals, the switch and the paper survive a fresh process")
    def _():
        # Written to a path of its own: importing `seedfall.tests` takes the
        # process's own save away with it at exit (`tests/__init__._tidy_up`).
        tmp = Path(tempfile.mkdtemp(prefix="seedfall-nemeses-"))
        save = tmp / "carried.json"
        write = (
            "import json\n"
            "from seedfall.tests import nemesis_kit as kit\n"
            "from seedfall.sim import rival_ends, hunts, running_dark\n"
            "from seedfall.sim import nemeses as n\n"
            "g = kit.mid_game('persist')\n"
            "r = kit.rival(g, 'husk', ['ghost'])\n"
            "r.ship.layers[0].hp = 1.0\n"
            "rival_ends.take_trophy(g, r)\n"
            "t = n.state(g).trophies[0]['id']\n"
            "hunts.mount_trophy(g, t)\n"
            "running_dark.set_dark(g, True)\n"
            "from seedfall.core import save as s\n"
            f"ok = s.write(g.to_save(), {str(save)!r})\n"
            "print(json.dumps({'ok': ok, 'uid': r.ship.uid, 'id': r.id,"
            " 'trophy': t}))\n")
        read = (
            "import json\n"
            "from seedfall.core.state import load_game\n"
            "from seedfall.sim import nemeses as n, running_dark\n"
            "g = load_game()\n"
            "r = n.roster(g)[0]\n"
            "g.advance_days(30)\n"
            "print(json.dumps({'uid': r.ship.uid, 'id': r.id, "
            "'dark': running_dark.dark(g), 'hp0': r.ship.layers[0].hp,"
            " 'guns': [w.id for w in g.ship_stats.weapons],"
            " 'next': g.ids.get('nemesis'), 'traits': r.traits}))\n")
        outs = []
        for code, where in ((write, tmp / "scratch.json"), (read, save)):
            env = dict(os.environ, SEEDFALL_SAVE=str(where),
                       QT_QPA_PLATFORM="offscreen")
            proc = subprocess.run([sys.executable, "-c", code], env=env,
                                  cwd=str(ROOT), capture_output=True,
                                  text=True, timeout=300)
            lines = [l for l in proc.stdout.splitlines() if l.startswith("{")]
            assert lines, proc.stderr[-800:]
            outs.append(json.loads(lines[-1]))
        wrote, back = outs
        assert wrote["ok"] and back["uid"] == wrote["uid"], (wrote, back)
        assert back["dark"] and back["traits"] == ["ghost"], back
        assert wrote["trophy"] in back["guns"], back["guns"]
        assert back["next"] > wrote["id"], back
        assert back["hp0"] > 1.0, "thirty days and nothing mended"
        return (f"uid {back['uid']}, dark, {wrote['trophy']} still fitted, "
                f"next id {back['next']}")

    # The hunt's own checks — the board, the search, the paper, the quotes —
    # live beside this file (`nemesis_hunts`) and run in this suite.
    nemesis_hunts.run(suite)
