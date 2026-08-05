"""Wars, and the one thing they have to do: move a quay to somebody else.

The claim this suite is here to make is not that a battle readout exists. It is
that a war reaches a captain who never fires a shot — through the counter, the
customs desk and whose books a port's income lands in.

Measured before any of it existed, over 1,800 days across three sectors with 15
to 18 ventures running to resolution:

    system.faction changed hands            0, 2, 2 systems
    of those, taken from another power      0, 0, 0
    port.faction changed hands              0, 0, 0

`ventures._claimable` asked for `s.faction is None`, so annexation could only
take *unclaimed* ground. The map filled in and never changed hands.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import diplomacy as dip
from ..sim import exchequer, ventures, war
from .harness import Suite


def _sector(seed: str):
    game = new_game(seed)
    dip.ensure(game)
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("a war is a reading of the relation matrix, not a stored flag")
    def _():
        game = _sector("war-read")
        a, b = "charter", "freeholds"
        dip.shift_relation(game, a, b, -200)
        assert dip.relation(game, a, b) <= war.WAR_AT
        assert war.at_war(game, a, b), "relation is past the threshold and yet no war"
        assert (tuple(sorted((a, b)))) in war.wars(game)
        assert b in war.belligerents(game, a) and a in war.belligerents(game, b)

        # And it ends when the relation does, with nothing to clean up — which
        # is the whole point of deriving it. A stored flag would need a peace.
        dip.shift_relation(game, a, b, 300)
        assert dip.relation(game, a, b) > war.WAR_AT
        assert not war.at_war(game, a, b), (
            f"relation is {dip.relation(game, a, b):.0f} and they are still at war")
        assert war.wars(game) == [] or (tuple(sorted((a, b)))) not in war.wars(game)
        assert war.at_war(game, a, a) is False, "a power is at war with itself"
        return f"war at <= {war.WAR_AT:.0f}, and gone again when it lifts"

    @check("taking a system in war moves the quay, not only the register")
    def _():
        # The distinction is deliberate and `exchequer.holdings` depends on it:
        # annexing empty ground moves `system.faction` and leaves whoever built
        # the berth owning the berth. Taking a system off somebody you are
        # fighting has to move both, or the war changes nothing a trader meets.
        game = _sector("war-take")
        dip.shift_relation(game, "charter", "freeholds", -200)
        spoils = war.spoils(game, "charter")
        assert spoils, "at war with freeholds and nothing of theirs is takeable"
        target = spoils[0]
        was = target.port.faction
        assert was == "freeholds"
        before = len(exchequer.holdings(game, "freeholds"))

        venture = ventures.Venture(id=9001, kind="annex", power="charter",
                                   place=target.id, until=game.day)
        ventures.ensure(game).append(venture)
        venture.succeeded = True
        ventures._apply(game, venture, RNG("take"))

        assert target.port.faction == "charter", (
            f"{target.name} was taken and the quay still answers to "
            f"{target.port.faction}")
        assert target.faction == "charter", "the register did not follow"
        # The consequence that reaches a captain: the income, and therefore the
        # fleet it pays for, is on somebody else's books now.
        assert target in exchequer.holdings(game, "charter")
        assert target not in exchequer.holdings(game, "freeholds")
        assert len(exchequer.holdings(game, "freeholds")) == before - 1
        return (f"{target.name}: {was} -> charter, and it left "
                f"{was}'s books with it")

    @check("annexing empty ground still leaves the berth where it was")
    def _():
        # The other half, and the one a mutation is most likely to break: peace
        # time expansion must not start seizing quays.
        #
        # The unclaimed-but-ported system is **constructed, not looked for**.
        # The first version of this check searched the sector for one, found
        # none, and returned "no unclaimed system carries a port here" — a
        # green tick against nothing at all, which is precisely the failure
        # this project keeps finding elsewhere.
        game = _sector("war-empty")
        empty = next(s for s in game.galaxy.systems
                     if getattr(s, "port", None) is not None
                     and s.port.faction == "freeholds")
        empty.faction = None                     # nobody has it on the register
        was = empty.port.faction
        assert not war.at_war(game, "charter", was), (
            "this check is about peacetime expansion and they are at war")
        venture = ventures.Venture(id=9002, kind="annex", power="charter",
                                   place=empty.id, until=game.day)
        ventures.ensure(game).append(venture)
        venture.succeeded = True
        ventures._apply(game, venture, RNG("empty"))
        assert empty.faction == "charter", "the register should still move"
        assert empty.port.faction == was, (
            f"expansion into unclaimed ground took the quay too: {was} -> "
            f"{empty.port.faction}")
        return f"register moved, quay stayed with {was}"

    @check("a power at war goes for its enemy's quays, not for empty space")
    def _():
        # Making the spoils claimable was not enough. Measured over ten sectors
        # and 3,600 days before this: 46 of 49 annexations landed on a system
        # with no port at all, because open ground outnumbers spoils about
        # three to one and the pick was uniform.
        game = _sector("war-aim")
        dip.shift_relation(game, "charter", "freeholds", -200)
        spoils = {s.id for s in war.spoils(game, "charter")}
        assert spoils, "nothing to take"
        rng = RNG("aim")
        picked = []
        for _ in range(20):
            options = ventures._claimable(game, "charter")
            want = [s for s in war.spoils(game, "charter") if s.bloom < 0.5]
            picked.append(rng.pick(want or options).id)
        astray = [p for p in picked if p not in spoils]
        assert not astray, (
            f"{len(astray)} of {len(picked)} wartime annexations aimed at "
            "something that was not the enemy's")
        return f"{len(picked)}/{len(picked)} wartime picks were enemy holdings"

    @check("a decade of sectors produces wars, and quays that change hands")
    def _():
        # The claim the flight itself can make, rather than a constructed one.
        wars = taken = 0
        for i in range(6):
            game = _sector(f"w{i}")
            before = {s.id: s.port.faction for s in game.galaxy.systems
                      if getattr(s, "port", None) is not None}
            seen = set()
            for _ in range(24):                       # 3,600 days
                game.advance_days(150)
                seen.update(war.wars(game))
            wars += len(seen)
            by_id = {s.id: s for s in game.galaxy.systems}
            # A quay that *closed* is not a quay that changed hands: a
            # power poor enough to retrench gives a berth up altogether
            # (`exchequer._retrench`), and infestation now costs income, so
            # that happens where once it could not.
            taken += sum(1 for k, v in before.items()
                         if by_id[k].port is not None
                         and by_id[k].port.faction != v)
        assert wars, "six sectors and a decade each, and nobody fell out"
        assert taken, (
            f"{wars} wars over six sectors and not one quay changed hands")
        return f"{wars} wars over 6 sectors x 3,600 days, {taken} quays taken"
