"""The fleet action at a contested system, and whether one hull matters.

The claim task #114 set: fly the same battle twice, once fighting and once
hiding, and the outcome differs — one hull measurably mattering without
commanding anything.

**The scale it asked for does not exist and was not built.** "A battle of two
hundred hulls" against an economy that sustains a mean of 23 in the whole
sector (measured over six: 25, 26, 23, 24, 20, 22). Measured over eight sectors
flown a decade each, a contested system carries **2 to 4 hulls, median 3**, and
three of those eight sectors never went to war at all. So the thing modelled
here is a skirmish over a quay, which is what the game can pay for — and it is
also why a single hull can tip one.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import armada, diplomacy as dip, fleets, ventures, war
from .harness import Suite


def _contested(seed: str = "armada"):
    """A sector with a war on, and the heaviest contested system in it."""
    game = new_game(seed)
    dip.ensure(game)
    dip.shift_relation(game, "charter", "freeholds", -200)
    acts = armada.actions(game)
    assert acts, f"{seed}: a war is on and nothing is contested"
    return game, acts[0]


def _annexation(game, system, power):
    v = ventures.Venture(id=7001, kind="annex", power=power,
                         place=system.id, until=game.day + 200)
    ventures.ensure(game).append(v)
    return v


def run(suite: Suite) -> None:
    check = suite.check

    @check("a contested system names a holder and a challenger")
    def _():
        game, (system, (keeps, other), here) = _contested()
        assert keeps == system.port.faction, "the holder is not whose quay it is"
        assert other != keeps and war.at_war(game, keeps, other), (
            "the challenger is not somebody the holder is fighting")
        assert here.get(keeps, 0) and here.get(other, 0), (
            f"one of the two sides has no hulls: {here}")
        # Derived: asking twice gives the same answer, and nothing was stored.
        assert armada.sides(game, system) == (keeps, other)
        assert not hasattr(game, "armada"), "an action got written to the game"
        return (f"{system.name}: {keeps} {here[keeps]} against "
                f"{other} {here[other]}")

    @check("at peace there is no action anywhere")
    def _():
        # The module has to be inert when nobody is fighting, or it invents a
        # war out of two powers who merely both have ports.
        game = new_game("armada-peace")
        dip.ensure(game)
        assert not war.wars(game), "this sector starts at war; pick another"
        assert armada.actions(game) == [], (
            "nobody is at war and yet something is contested")
        for system in game.galaxy.systems:
            assert armada.sides(game, system) is None
            assert armada.note(game, system) == fleets.note(game, system), (
                "at peace the note should be the ordinary on-station line")
        # And a squadron that is merely *present* is not a contest. In play
        # this cannot arise — hulls only reach somebody else's system through
        # `war.spoils` — so the `at_war` filter in `sides` is unreachable by
        # flying, and a mutation deleting it left every check here green. It
        # is constructed instead, because the filter is what makes the module
        # mean "contested" rather than "crowded".
        held = next(s for s in game.galaxy.systems
                    if getattr(s, "port", None) is not None)
        keeps = held.port.faction
        friend = next(p for p in dip.POWERS
                      if p != keeps and not war.at_war(game, keeps, p))
        was = fleets.squadron_at
        try:
            fleets.squadron_at = lambda g, s, _w=was: (
                {keeps: 2, friend: 3} if s.id == held.id else _w(g, s))
            assert armada.sides(game, held) is None, (
                f"{friend} has three hulls over {keeps}'s quay and they are "
                "not at war, and that reads as a fleet action")
        finally:
            fleets.squadron_at = was
        return "no war, no action, and the note falls back to `fleets`"

    @check("your hull counts only when you are there AND have taken a side")
    def _():
        # Either alone is not enough. An opinion from three jumps away is not
        # a hull in the line, and a hull in the line with no opinion is a
        # bystander.
        game, (system, (keeps, other), _here) = _contested()
        v = _annexation(game, system, other)
        elsewhere = next(s.id for s in game.galaxy.systems if s.id != system.id)

        game.location_id = elsewhere
        v.stance = "backed"
        assert armada.committed(game, system) is None, "counted from elsewhere"

        game.location_id = system.id
        v.stance = "none"
        assert armada.committed(game, system) is None, "counted with no side taken"

        v.stance = "backed"
        assert armada.committed(game, system) == other
        v.stance = "opposed"
        assert armada.committed(game, system) == keeps, (
            "opposing the annexation should put you with the holder")

        # And the hull is actually in the count, not merely acknowledged.
        v.stance = "backed"
        with_us = armada.strength_at(game, system)
        game.location_id = elsewhere
        without = armada.strength_at(game, system)
        assert with_us[other] == without.get(other, 0) + 1, (
            f"present and committed and the line is unchanged: {without} -> "
            f"{with_us}")
        return "present + committed, and only then"

    @check("the same annexation, fought or hidden from, comes out differently")
    def _():
        # **Task #114's claim, and the stance is held fixed so this measures
        # the hull and not the opinion.** Moving only the ship: measured
        # +0.083 backing and -0.042 opposing on a 2-against-1 at Ferron
        # Hollow. The first version of this compared "away and neutral"
        # against "present and backing" and reported +0.383, which is mostly
        # `ventures.SWAY` — the player's opinion, which already counted before
        # any of this existed.
        game, (system, (keeps, other), _here) = _contested()
        v = _annexation(game, system, other)
        elsewhere = next(s.id for s in game.galaxy.systems if s.id != system.id)
        moved = {}
        for stance in ("backed", "opposed"):
            v.stance = stance
            game.location_id = elsewhere
            away = ventures.odds(game, v)
            game.location_id = system.id
            there = ventures.odds(game, v)
            moved[stance] = there - away
        assert moved["backed"] > 0.02, (
            f"turning up to fight for the annexation moved its odds by "
            f"{moved['backed']:+.3f} — one hull does not matter")
        assert moved["opposed"] < -0.02, (
            f"turning up to fight against it moved its odds by "
            f"{moved['opposed']:+.3f}")
        return (f"one hull, stance held: {moved['backed']:+.3f} for, "
                f"{moved['opposed']:+.3f} against")

    @check("the balance runs from all theirs to all ours, and is even in between")
    def _():
        game, (system, (keeps, other), here) = _contested()
        game.location_id = None
        for power in (keeps, other):
            b = armada.balance(game, system, power)
            assert -1.0 <= b <= 1.0, f"{power} balance {b}"
        # The two sides see it as mirror images when only they are present.
        if len(here) == 2:
            assert abs(armada.balance(game, system, keeps)
                       + armada.balance(game, system, other)) < 1e-9, (
                "the two sides do not see the same fight")
        lone = next((s for s in game.galaxy.systems
                     if len(fleets.squadron_at(game, s)) == 1), None)
        assert lone is not None
        only = next(iter(fleets.squadron_at(game, lone)))
        assert armada.balance(game, lone, only) == 1.0, (
            "a power alone over a system does not have it all")
        empty = next(s for s in game.galaxy.systems
                     if not fleets.squadron_at(game, s))
        assert armada.balance(game, empty, keeps) == 0.0, (
            "nobody is there and somebody is winning")
        return (f"{armada.balance(game, system, keeps):+.2f} to {keeps}, "
                f"{armada.balance(game, system, other):+.2f} to {other}")
