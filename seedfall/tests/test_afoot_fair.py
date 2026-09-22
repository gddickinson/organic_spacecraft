"""Afoot keeps faith: the rules a play-test found bent, held straight.

- somebody left lying on a deck **where people live is found and brought
  home**, hurt; on a dead hull they are left for good;
- **a stun wears off** — it is never carried home as a wound — and an
  officer at their station **keeps the wound** the last walk left them;
- **nothing is rolled twice for the asking**: persuasion is once a person,
  a refused press spends no luck, and anything rolled for in a fight is the
  round's act;
- **a bribe buys one witness**: what somebody else saw is still a crime;
- **your own are not targets**, and **your own people's lockers are not
  loot**;
- **a stop has teeth**: asked for papers and walking on is evasion;
- **what happened stays happened**: a tie met this season does not come
  back tomorrow; a claimed prize's hold sails with her;
- **a calm party rides a lift together**, and nobody stands on anybody.
"""

from __future__ import annotations

from ..sim import (afoot, afoot_acts, afoot_ends, afoot_fight, afoot_incidents,
                   afoot_map)
from ..sim.afoot_state import Actor, party
from . import afoot_kit
from .harness import Suite


def _out(game, keys=None, kind="port"):
    site = next(s for s in afoot.sites(game) if s.kind == kind and s.ok)
    got = afoot.begin(game, site.key, keys or afoot_kit.everybody(game)[:2])
    assert got["ok"], got
    return game.afoot


def _npc(walk, me, **kw) -> Actor:
    """Somebody standing beside the first of the party."""
    g = afoot_map.ground(walk, me.deck)
    taken = {(a.x, a.y) for a in walk.actors if a.deck == me.deck}
    spot = next((me.x + dx, me.y + dy) for dx, dy in afoot_map.STEPS
                if g.passable(me.x + dx, me.y + dy)
                and (me.x + dx, me.y + dy) not in taken)
    who = Actor(id=8000 + len(walk.actors), name=kw.pop("name", "Somebody"),
                side="npc", folk=kw.pop("folk", "patron"), deck=me.deck,
                x=spot[0], y=spot[1], hp=10, hp_max=10,
                stats={"str": 7, "dex": 7, "end": 7, "int": 7, "edu": 7,
                       "soc": 7}, **kw)
    walk.actors.append(who)
    return who


def run(suite: Suite) -> None:
    check = suite.check

    @check("the fallen are brought home from where people live, and a stun is never a wound")
    def _():
        game = afoot_kit.fresh("fair-fallen")
        walk = _out(game)
        captain, mate = party(walk)[:2]
        afoot_fight.hurt(game, walk, mate, mate.hp + 2)
        assert mate.status == "down"
        afoot_fight.hurt(game, walk, captain, captain.hp + 3, stun=True)
        afoot_ends.leave(game, walk)
        officer = next(o for o in game.officers if o.id == mate.officer)
        assert not officer.retired, "an officer left down on a quay died"
        assert game.wounds.get(str(officer.id), 0) > 0
        assert "captain" not in game.wounds, game.wounds
        # And at their station on your own hull, the wound is still there.
        walk = _out(game, ["captain"], kind="ship")
        aboard = next((a for a in walk.actors if a.officer == officer.id),
                      None)
        if aboard is not None:
            assert aboard.hp < aboard.hp_max, "the wound healed on the way"
        return (f"{officer.name} came home hurt; the captain's stun "
                "wore off")

    @check("nothing is rolled twice for the asking, and a refused press spends no luck")
    def _():
        game = afoot_kit.fresh("fair-dice")
        walk = _out(game, ["captain"])
        me = party(walk)[0]
        other = _npc(walk, me, mood="wary")
        was = game.rng_seed
        bad = afoot.talk(game, me.id, other.id, "no-such-topic")
        bad2 = afoot.act(game, me.id, "no-such-act")
        assert not bad["ok"] and not bad2["ok"]
        assert game.rng_seed == was, "a refused press moved the dice"
        first = afoot.talk(game, me.id, other.id, "persuade")
        again = afoot.talk(game, me.id, other.id, "persuade")
        assert first.get("ok") and not again["ok"], again
        # In a fight, a rolled word is the round's act.
        walk.mode = "action"
        third = _npc(walk, me, mood="wary", name="Another")
        assert afoot.talk(game, me.id, third.id, "persuade").get("ok")
        assert me.acted, "talking in a fight cost nothing"
        return "persuaded once, refused twice without a throw"

    @check("a bribe buys one witness, and your own are not targets")
    def _():
        from ..sim import afoot_said
        game = afoot_kit.fresh("fair-bribe")
        walk = _out(game, ["captain"])
        me = party(walk)[0]
        cop = _npc(walk, me, folk="constable", name="Constable")
        clerk = _npc(walk, me, folk="clerk", name="Clerk")
        walk.seen_doing = [["theft", "charter", 1.0, [cop.id]],
                           ["assault", "charter", 1.0, [cop.id, clerk.id]]]
        afoot_said.forget(walk, cop.id)
        assert [row[0] for row in walk.seen_doing] == ["assault"]
        game.afoot = None
        walk = _out(game, ["captain"], kind="ship")
        me = party(walk)[0]
        crew = next((a for a in walk.actors if a.side == "npc"
                     and (a.officer >= 0 or a.folk == "hand")), None)
        assert crew is not None, "nobody aboard to test on"
        got = afoot.attack(game, me.id, crew.id)
        assert not got["ok"] and "one of yours" in got["why"], got
        return "the paid constable forgot only what they alone saw"

    @check("a stop walked past is evasion, and what happened this season stays happened")
    def _():
        game = afoot_kit.fresh("fair-stop")
        walk = _out(game, ["captain"])
        me = party(walk)[0]
        cop = _npc(walk, me, folk="constable", name="Constable",
                   mood="wary")
        cop.incident = "stop"
        cop.talked.append("hailed")
        for _n in range(afoot_incidents.STOP_PATIENCE + 1):
            afoot_incidents.tick(game, walk)
        assert cop.mood == "hostile", cop.mood
        assert any(row[0] == "evasion" for row in walk.seen_doing)
        afoot_incidents.meet(game, "tie:7:creditor")
        assert afoot_incidents._met(game, "tie:7:creditor")
        game.day += 200
        assert not afoot_incidents._met(game, "tie:7:creditor")
        return "ignored the watch: hostile, and on file; a tie waits a season"

    @check("a claimed prize keeps her hold, and a calm party rides a lift together")
    def _():
        game = afoot_kit.fresh("fair-prize")
        hull = afoot_kit.struck(game)
        assert afoot.begin_prize(game, hull, "concordat",
                                 ["captain"])["ok"]
        walk = game.afoot
        walk.prize_done = "taken"
        for stack in walk.things:
            if stack.kind == "cargo":
                stack.state = "claimed"
        me = party(walk)[0]
        stack = next(t for t in walk.things if t.kind == "cargo")
        g = afoot_map.ground(walk, stack.deck)
        me.deck, (me.x, me.y) = stack.deck, next(
            (stack.x + dx, stack.y + dy) for dx, dy in afoot_map.STEPS
            if g.passable(stack.x + dx, stack.y + dy))
        offered = [a.id for a in afoot_acts.offer(game, walk, me)
                   if a.target == stack.id]
        assert "take" not in offered, offered
        game.afoot = None
        game = afoot_kit.fresh("fair-lift")
        walk = _out(game, afoot_kit.everybody(game)[:3], kind="ship")
        lift = next((t for t in walk.things if t.kind == "lift"
                     and t.link >= 0 and t.deck == party(walk)[0].deck),
                    None)
        if lift is None:
            return "a claimed prize keeps her hold (a one-deck hull: no lift)"
        lead, *rest = party(walk)
        lead.x, lead.y = lift.x, lift.y
        for mate in rest:
            spot = next(s for s in afoot_map.reach(walk, lead, 2)
                        if s != (lead.x, lead.y) and not any(
                            (a.x, a.y) == s and a.deck == lead.deck
                            for a in walk.actors))
            mate.deck, (mate.x, mate.y) = lead.deck, spot
        assert afoot.act(game, lead.id, "lift", lift.id)["ok"]
        decks = {a.deck for a in party(walk)}
        squares = [(a.deck, a.x, a.y) for a in party(walk)]
        assert len(decks) == 1, "somebody was left a deck behind"
        assert len(set(squares)) == len(squares), "two stood on one square"
        return (f"a claimed prize keeps her hold; {len(party(walk))} rode "
                "the lift together, each on a square of their own")
