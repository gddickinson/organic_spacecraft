"""Afoot, played: whether a walk can be finished, and what it leaves behind.

- **It never jams.** A party leader who plays the way the screens teach
  finishes a walk at every kind of site — the hull, a quay, a drum, a
  holding, dead hulls of every end, a struck prize.
- **Money is never conjured.** No walk ends with more credits than it began
  with: a deck has lockers, not a mint.
- **A walk survives a restart.** Saved between two moves, it resumes in a
  fresh process where it stood, and the next move works.
- **The law was watching.** Hitting somebody where a constable can see it
  is a charge on the file when the party leaves.
- **What is found is kept, and remembered as taken.** A second walk the same
  season finds the lockers already emptied.
- **The captain always comes home; an officer need not.** A party that is
  wiped on a dead hull leaves its downed officers behind, and they are dead
  in the crew's book.
- **A prize is decided through the prize's own doors**, the Bloom counts a
  burned nest as fighting it, and an officer's past turns up by name.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from ..core import save as save_mod
from ..sim import (afoot, afoot_fight, afoot_incidents, afoot_map, law,
                   responses, roster)
from ..sim.afoot_state import Actor, party
from . import afoot_bot, afoot_kit
from .harness import Suite

ROOT = Path(__file__).resolve().parents[2]
WRECKS = ("raider_hulk", "bloom_freighter", "survey_hulk", "liner_wreck",
          "choir_probe")


def _play(game, key: str, keys=None) -> dict:
    got = afoot.begin(game, key, keys or afoot_kit.everybody(game))
    assert got["ok"], (key, got)
    return afoot_bot.play(game)


def _near(walk, me, other) -> None:
    """Stand one of the party next to somebody."""
    g = afoot_map.ground(walk, other.deck)
    taken = {(a.x, a.y) for a in walk.actors if a.deck == other.deck}
    for dx, dy in afoot_map.STEPS:
        spot = (other.x + dx, other.y + dy)
        if g.passable(*spot) and spot not in taken:
            me.deck, (me.x, me.y) = other.deck, spot
            return
    raise AssertionError(f"nowhere to stand beside {other.name}")


def run(suite: Suite) -> None:
    check = suite.check

    @check("a party finishes a walk at every kind of site, and never jams")
    def _():
        done, credits = [], []
        for n in range(3):
            game = afoot_kit.settle(afoot_kit.fresh(f"afoot-play-{n}"))
            for site in afoot.sites(game):
                if not site.ok:
                    continue
                was = game.credits
                got = _play(game, site.key)
                assert not got["jammed"], (site.key, got)
                done.append((site.kind, got["outcome"]))
                credits.append(game.credits - was)
        for wreck in WRECKS:
            game, site = afoot_kit.at_wreck((wreck,))
            was = game.credits
            got = _play(game, site.key)
            assert not got["jammed"], (wreck, got)
            done.append((wreck, got["outcome"]))
            credits.append(game.credits - was)
        game = afoot_kit.fresh("afoot-play-prize")
        assert afoot.begin_prize(game, afoot_kit.struck(game), "concordat",
                                 afoot_kit.everybody(game))["ok"]
        got = afoot_bot.play(game)
        assert not got["jammed"], got
        done.append(("prize", got["outcome"]))
        assert max(credits) <= 0, f"a walk made money: {max(credits)}"
        kinds = sorted({k for k, _o in done})
        return f"{len(done)} walks finished over {kinds}; no walk made money"

    @check("a walk saved between two moves resumes in a fresh process")
    def _():
        game = afoot_kit.fresh("afoot-resume")
        assert afoot.begin(game, f"ship:{game.ship.uid}",
                           afoot_kit.everybody(game)[:2])["ok"]
        walk = game.afoot
        me = party(walk)[0]
        spots = sorted(afoot_map.reach(walk, me, 3))
        afoot.move(game, me.id, *spots[-1])
        where = [me.deck, me.x, me.y]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "afoot.json"
            assert save_mod.write(game.to_save(), path)
            code = (
                "import json\n"
                "from seedfall.core.loading import load_game\n"
                "from seedfall.sim import afoot, afoot_map\n"
                "from seedfall.sim.afoot_state import party\n"
                "g = load_game()\n"
                "w = afoot.current(g)\n"
                "me = party(w)[0]\n"
                "spot = sorted(afoot_map.reach(w, me, 2))[0]\n"
                "moved = afoot.move(g, me.id, *spot)\n"
                "print(json.dumps({'where': [me.deck, me.x, me.y],"
                " 'n': len(w.actors), 'rooms': len(w.rooms),"
                " 'moved': moved['ok'], 'site': w.site}))\n")
            env = dict(os.environ, SEEDFALL_SAVE=str(path),
                       QT_QPA_PLATFORM="offscreen")
            proc = subprocess.run([sys.executable, "-c", code], text=True,
                                  capture_output=True, env=env,
                                  cwd=str(ROOT), timeout=240)
            lines = [l for l in proc.stdout.splitlines() if l.startswith("{")]
            assert lines, proc.stderr[-800:]
            got = json.loads(lines[-1])
        assert got["n"] == len(walk.actors) and got["rooms"] == len(walk.rooms)
        assert got["site"] == walk.site and got["moved"], got
        return (f"resumed at {where} with {got['n']} people aboard; the next "
                "move worked")

    @check("hitting somebody where the watch can see it is a charge on the file")
    def _():
        game = afoot_kit.fresh("afoot-assault")
        port = next(s for s in afoot.sites(game) if s.kind == "port")
        assert afoot.begin(game, port.key, ["captain"])["ok"]
        walk = game.afoot
        me = party(walk)[0]
        me.weapon = "blade"
        victim = next(a for a in walk.actors if a.side == "npc"
                      and a.folk in ("patron", "keeper", "dockhand", "clerk"))
        _near(walk, me, victim)
        cop = Actor(id=8800, name="Constable", side="npc", folk="constable",
                    deck=victim.deck, x=me.x, y=me.y, hp=24, hp_max=24,
                    faction=walk.faction, weapon="stunner",
                    stats={"str": 8, "dex": 8, "end": 8, "int": 7, "edu": 7,
                           "soc": 7})
        _near(walk, cop, me)
        walk.actors.append(cop)
        before = len(law.charges(game))
        afoot.attack(game, me.id, victim.id)
        assert cop.mood == "hostile", "the constable watched and did nothing"
        afoot.surrender(game)
        after = [c for c in law.charges(game)][before:]
        assert any(c.offence == "assault" for c in after), after
        return f"{after[0].power} has it: {after[0].offence}, {after[0].state}"

    @check("what is found is kept, and the lockers stay emptied that season")
    def _():
        game, site = afoot_kit.at_wreck(("liner_wreck", "survey_hulk"))
        kit_before = len(game.kit)
        got = _play(game, site.key)
        assert got["outcome"] == "left", got
        assert len(game.kit) > kit_before or game.research.evidence, \
            "the walk came home with nothing"
        emptied = game.walked.get(site.key, {}).get("0", [])
        assert emptied, "nothing was remembered as taken"
        assert afoot.begin(game, site.key, ["captain"])["ok"]
        walk = game.afoot
        again = [t for t in walk.things if t.id in emptied]
        assert all(t.state == "searched" and not t.holds for t in again), \
            "a second walk found the same lockers full"
        return (f"{len(game.kit) - kit_before} thing(s) kept; {len(emptied)} "
                "container(s) still empty on the second visit")

    @check("the captain always comes home; an officer left down on a wreck does not")
    def _():
        game, site = afoot_kit.at_wreck(("raider_hulk",))
        keys = afoot_kit.everybody(game)[:2]
        assert afoot.begin(game, site.key, keys)["ok"]
        walk = game.afoot
        captain, mate = party(walk)[:2]
        afoot_fight.hurt(game, walk, mate, mate.hp + 2)
        assert mate.status == "down", mate.status
        afoot_fight.hurt(game, walk, captain, 999)
        assert captain.status != "dead", "the captain was killed"
        afoot.end_turn(game)
        assert game.afoot is None, "a wiped party is still out"
        officer = next(o for o in game.officers if o.id == mate.officer)
        assert officer.retired, "the officer left lying there came home"
        book = [r for r in roster.departed(game) if r["officer"] is officer]
        assert book and "Died aboard" in book[0]["note"], book
        return f"the captain was rescued; {officer.name}: {book[0]['note']}"

    @check("a prize is taken, stripped or let go through the prize's own doors")
    def _():
        results = {}
        for how in ("claim", "take", "leave"):
            game = afoot_kit.fresh(f"afoot-prize-{how}")
            hull = afoot_kit.struck(game)
            rep = game.rep.get("concordat", 0.0)
            assert afoot.begin_prize(game, hull, "concordat",
                                     ["captain"])["ok"]
            walk = game.afoot
            me = party(walk)[0]
            if how == "claim":
                bridge = next(r for r in walk.rooms if r.kind == "bridge")
                spot = next(c for c in bridge.cells()
                            if afoot_map.ground(walk, bridge.deck).passable(*c))
                me.deck, (me.x, me.y) = bridge.deck, spot
                assert afoot.act(game, me.id, "claim")["ok"]
                assert hull in game.fleet
            elif how == "take":
                stack = next(t for t in walk.things if t.kind == "cargo")
                _near(walk, me, Actor(id=-1, name="", side="", folk="",
                                      deck=stack.deck, x=stack.x, y=stack.y,
                                      hp=1, hp_max=1))
                held = sum(game.ship.cargo.values())
                assert afoot.act(game, me.id, "take", stack.id)["ok"]
                assert sum(game.ship.cargo.values()) > held
            from ..sim import afoot_ends
            afoot_ends.leave(game, walk)
            results[how] = (walk.prize_done,
                            round(game.rep.get("concordat", 0.0) - rep, 1))
        assert results["claim"][0] == "taken" and results["claim"][1] < 0
        assert results["take"][0] == "stripped"
        assert results["leave"][0] == "released" and results["leave"][1] > 0
        return "; ".join(f"{k}: {v[0]} ({v[1]:+g} standing)"
                         for k, v in results.items())

    @check("burning a Bloom nest out is fighting the Bloom")
    def _():
        game, site = afoot_kit.at_wreck(("bloom_freighter",))
        assert afoot.begin(game, site.key, ["captain"])["ok"]
        walk = game.afoot
        me = party(walk)[0]
        me.weapon = "cutting_torch"
        node = next(t for t in walk.things if t.kind == "spore_node")
        for npc in list(walk.actors):
            if npc.side == "npc":
                npc.status = "gone"
        _near(walk, me, Actor(id=-1, name="", side="", folk="",
                              deck=node.deck, x=node.x, y=node.y, hp=1,
                              hp_max=1))
        was = responses.fought(game)
        for _n in range(12):
            me.acted = False
            afoot.act(game, me.id, "burn", node.id)
            if node.state == "done":
                break
        assert node.state == "done", "twelve tries with a torch and it stands"
        from ..sim import afoot_ends
        afoot_ends.leave(game, walk)
        assert responses.fought(game) > was, "the Bloom did not notice"
        return f"fought {was:g} → {responses.fought(game):g}"

    @check("somebody from an officer's past turns up by name, and seeing them matters")
    def _():
        moved = []
        for n in range(30):
            game = afoot_kit.fresh(f"afoot-tie-{n}")
            port = next((s for s in afoot.sites(game) if s.kind == "port"),
                        None)
            if port is None:
                continue
            assert afoot.begin(game, port.key, afoot_kit.everybody(game))["ok"]
            walk = game.afoot
            tie = next((a for a in walk.actors if a.incident == "tie"), None)
            if tie is None:
                game.afoot = None
                continue
            officer = next(o for o in game.officers
                           if o.id == int(tie.tie.split(":")[0]))
            from ..sim import person
            names = [t.who for t in person.of(game, officer).ties]
            assert tie.name in names, (tie.name, names)
            me = party(walk)[0]
            _near(walk, me, tie)
            was = officer.loyalty
            got = afoot.talk(game, me.id, tie.id, "tie")
            if got.get("ok"):
                moved.append(officer.loyalty - was)
            if len(moved) >= 2:
                break
        assert moved and min(moved) > 0, moved
        return f"{len(moved)} ties met and settled; loyalty +{moved[0]:g}"

    @check("carrying what the law forbids brings the watch to you")
    def _():
        stopped = 0
        for n in range(12):
            game = afoot_kit.fresh(f"afoot-stop-{n}")
            port = next((s for s in afoot.sites(game) if s.kind == "port"
                         and s.law >= 6), None)
            if port is None:
                continue
            game.kit.append("carbine")
            assert afoot.begin(game, port.key, ["captain"], "all")["ok"]
            walk = game.afoot
            if "stop" not in walk.incidents:
                game.afoot = None
                continue
            me = party(walk)[0]
            cop = next(a for a in walk.actors if a.incident == "stop")
            for _round in range(20):
                got = afoot.end_turn(game)
                if any(e.get("kind") == "hail" for e in got["events"]):
                    break
            assert "hailed" in cop.talked, "the constable never came"
            stopped += 1
            assert me.weapon == "carbine"
            break
        assert stopped, "no stop in twelve sectors at law six and over"
        return "the watch walked up and asked for papers"

    @check("a clinic's care closes a wound kept from a walk, and says so first")
    def _():
        from ..sim import clinic, places
        game = afoot_kit.fresh("afoot-care")
        game.credits = 20_000
        officer = game.officers[0]
        game.wounds = {str(officer.id): 9.0}
        place = next((p for p in places.here(game) if p.kind != "ship"
                      and clinic.offered(game, p, "care")), None)
        assert place is not None, "no clinic alongside"
        row = clinic.offered(game, place, "care")[0]
        said = clinic.quote(game, place, officer, row["treatment"].id)
        assert any("wound" in line for line in said["does"]), said["does"]
        got = clinic.buy(game, place, officer, row["treatment"].id)
        assert got["ok"], got
        if got.get("went", True):
            assert str(officer.id) not in game.wounds, game.wounds
        return f"{row['treatment'].name}: {said['does'][-1]}"

    @check("a walk can be driven over the bridge, and nothing else acts while it is out")
    def _():
        import json as json_mod
        from ..bridge.protocol import dispatch
        game = afoot_kit.fresh("afoot-bridge")
        sites = dispatch(game, {"verb": "afoot_sites"})
        assert sites["ok"] and sites["sites"], sites
        key = next(s["key"] for s in sites["sites"] if s["kind"] == "ship")
        began = dispatch(game, {"verb": "afoot_begin",
                                "args": {"site": key, "keys": "captain"}})
        assert began["ok"], began
        seen = dispatch(game, {"verb": "afoot_look"})
        json_mod.dumps(seen)
        assert seen["ok"] and seen["map"] and seen["party"], seen
        jumped = dispatch(game, {"verb": "jump", "args": {"system_id": 0}})
        assert jumped.get("blocked"), jumped
        me = seen["party"][0]
        leave = next(a for a in seen["acts"] if a["id"] == "leave")
        done = dispatch(game, {"verb": "afoot_act", "args": {
            "actor": me["id"], "act": "leave", "target": leave["target"]}})
        assert done["ok"] and game.afoot is None, done
        return (f"looked ({len(seen['map'])}-line map), refused a jump, "
                "and left by the airlock, all over the pipe")

    @check("a fault found aboard and fixed puts hull back")
    def _():
        game = afoot_kit.fresh("afoot-fault")
        from ..sim.ship import apply_damage, hull_pct
        apply_damage(game.ship, 300)
        for n in range(20):
            assert afoot.begin(game, f"ship:{game.ship.uid}", ["captain"])["ok"]
            walk = game.afoot
            fault = next((t for t in walk.things if t.kind == "fault"), None)
            if fault is not None:
                break
            afoot_incidents.snubbed(game, walk)
            game.afoot = None
            game.advance_days(1)
        assert fault is not None, "no fault aboard a hurt hull in 20 days"
        me = party(walk)[0]
        _near(walk, me, Actor(id=-1, name="", side="", folk="",
                              deck=fault.deck, x=fault.x, y=fault.y, hp=1,
                              hp_max=1))
        was = hull_pct(game.ship)
        for _n in range(20):
            me.acted = False
            afoot.act(game, me.id, "repair", fault.id)
            if fault.state == "done":
                break
        assert fault.state == "done"
        assert hull_pct(game.ship) > was, (was, hull_pct(game.ship))
        return f"hull {was:.1%} → {hull_pct(game.ship):.1%}"

