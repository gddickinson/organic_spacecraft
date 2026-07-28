"""Allegiance checks — you cannot be everybody's courier at once.

`contracts.py` did not import `diplomacy`. Six powers, a relations matrix that
starts hostile in most pairs, and the work you actually did all day touched
none of it: completing a job moved the issuer's standing and nothing else. You
could run the Charter's deliveries, collect a Concordat bounty and take
Freehold prospecting money in the same week while all three were at each
other's throats, and every one of them thought better of you for it.

The point of the fix is not the penalty. It is that brokering the peace now
pays for itself in daily play, instead of being something you did once at the
end for an ending.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.factions import FACTIONS_BY_ID
from ..sim import allegiance
from ..sim import contracts as contract_sim
from ..sim import diplomacy as dip
from .harness import Suite

POWERS = ("charter", "concordat", "freeholds", "sanhedrin")


def _peace(game, level: float = 25.0) -> None:
    """Broker every pair up to `level`."""
    for i, a in enumerate(POWERS):
        for b in POWERS[i + 1:]:
            dip.shift_relation(game, a, b, level - dip.relation(game, a, b))


def _war(game, level: float = -90.0) -> None:
    for i, a in enumerate(POWERS):
        for b in POWERS[i + 1:]:
            dip.shift_relation(game, a, b, level - dip.relation(game, a, b))


def _delivered(game, issuer: str, rep: int = 5):
    """Build a delivery, satisfy it, and let the clock notice."""
    target = game.location_id
    job = contract_sim.Contract(
        id=9000, kind="deliver", issuer=issuer, issued_at=target,
        title="Carry 3 t of Ore Pellets", posting="A test posting.",
        target_system=target, commodity="ore", amount=3.0,
        reward=1000, rep=rep, deadline=game.day + 500, accepted=True)
    game.contracts.append(job)
    game.ship.cargo["ore"] = 10
    events = contract_sim.check(game)
    assert any(c is job and out == "done" for c, out in events), (
        f"the delivery did not complete: {[(c.title, o) for c, o in events]}")
    return job


def run(suite: Suite) -> None:
    check = suite.check

    @check("nobody minds a cordial sector, everybody minds a war")
    def _():
        calm = new_game("calm")
        _peace(calm)
        for power in POWERS:
            assert not allegiance.offended_by(calm, power), (
                f"{power}'s friends still object at +25 all round")

        hot = new_game("hot")
        _war(hot)
        for power in POWERS:
            minded = allegiance.offended_by(hot, power)
            assert len(minded) == len(POWERS) - 1, (
                f"only {len(minded)} powers mind {power} at total war")
            assert all(sev >= 0.99 for _o, sev in minded), (
                f"war reads as a mild disagreement: {minded}")
        return "0 objections at peace, 3 apiece at war"

    @check("brokering a rift down is worth doing by degrees")
    def _():
        # A flat penalty below some threshold would make dragging a pair from
        # implacable to merely bad worth precisely nothing, which is the
        # opposite of what the diplomacy layer is for.
        game = new_game("degrees")
        costs = []
        for level in (-90.0, -60.0, -40.0, -20.0, -5.0):
            dip.shift_relation(game, "charter", "concordat",
                               level - dip.relation(game, "charter", "concordat"))
            paid = dict(allegiance.price(game, "charter", 10))
            costs.append(paid.get("concordat", 0.0))
        assert costs == sorted(costs, reverse=True), (
            f"the cost does not fall as the rift closes: {costs}")
        assert costs[0] > costs[-2] > 0, "no gradient worth brokering for"
        assert costs[-1] == 0, "a cordial pair still objects"
        return " → ".join(f"{c:g}" for c in costs) + " as -90 becomes -5"

    @check("completing a job actually charges the issuer's enemies")
    def _():
        game = new_game("charge")
        _war(game)
        before = {p: game.rep.get(p, 0) for p in POWERS}
        job = _delivered(game, "charter", rep=5)
        assert game.rep["charter"] > before["charter"], "the issuer did not pay"
        assert job.cost, "nothing was recorded against the job"
        for other in ("concordat", "freeholds", "sanhedrin"):
            assert game.rep.get(other, 0) < before[other], (
                f"{other} is at war with the Charter and did not mind")
        return f"charter +5, and {allegiance.phrase(job.cost)}"

    @check("the board does not lie about what a job will cost")
    def _():
        # The line on the card and the standing that actually moves have to be
        # the same number, or the screen is worse than no screen.
        game = new_game("honest")
        _war(game, -50.0)
        quoted = dict(allegiance.price(game, "concordat", 5))
        assert quoted, "nothing quoted in a hostile sector"
        before = {p: game.rep.get(p, 0) for p in POWERS}
        _delivered(game, "concordat", rep=5)
        for other, cost in quoted.items():
            moved = before[other] - game.rep.get(other, 0)
            assert abs(moved - cost) < 0.001, (
                f"quoted {other} −{cost} and actually moved −{moved}")
        said, _tint = allegiance.note(game, "concordat", 5)
        assert said and "cost" in said, f"the card says {said!r}"
        return f"{len(quoted)} quoted costs, all matched to the penny"

    @check("serving one power makes you its partisan, not everyone's friend")
    def _():
        loyal = new_game("partisan")
        for _ in range(30):
            loyal.adjust_rep("charter", 5)
            allegiance.charge(loyal, "charter", 5)
        assert loyal.rep["charter"] >= 70, "thirty jobs and not even Trusted"
        enemies = [p for p in ("concordat", "freeholds")
                   if loyal.rep.get(p, 0) < -20]
        assert len(enemies) == 2, (
            "the Charter's enemies do not mind you being its courier: "
            + str({p: round(loyal.rep.get(p, 0)) for p in POWERS}))
        return ("charter " + f"{loyal.rep['charter']:+.0f}, "
                + ", ".join(f"{p} {loyal.rep.get(p, 0):+.0f}" for p in enemies))

    @check("brokering the peace first pays for itself")
    def _():
        # This is the whole point. Before, the relations matrix mattered once,
        # at the Concord ending. Now it changes what an ordinary week is worth.
        def career(brokered: bool) -> dict:
            game = new_game("careers")
            if brokered:
                _peace(game, 25.0)
            for index in range(28):
                power = POWERS[index % len(POWERS)]
                game.adjust_rep(power, 5)
                allegiance.charge(game, power, 5)
            return {p: game.rep.get(p, 0) for p in POWERS}

        raw, calm = career(False), career(True)
        assert sum(calm.values()) > sum(raw.values()) * 1.3, (
            f"peace buys almost nothing: {sum(raw.values()):.0f} → "
            f"{sum(calm.values()):.0f}")
        for power in POWERS:
            assert calm[power] >= raw[power], (
                f"{power} came out worse for the sector being at peace")
        return (f"same 28 jobs: {sum(raw.values()):.0f} total standing hostile, "
                f"{sum(calm.values()):.0f} at peace")

    @check("nobody takes offence on behalf of the Bloom")
    def _():
        game = new_game("bloom-offence")
        _war(game)
        for power in POWERS:
            minded = [o for o, _s in allegiance.offended_by(game, power)]
            assert "bloom" not in minded, "the Bloom has an opinion on couriers"
            assert "abyssals" not in minded, (
                "something nobody has ever seen is keeping score")
        return "the hostile and hidden powers stay out of it"

    @check("a broker who also works can still reach the Concord")
    def _():
        # The penalty must shape the order you do things in, not close the
        # ending: make peace, then make friends.
        game = new_game("concord-path")
        _peace(game, 30.0)
        for index in range(80):
            power = POWERS[index % len(POWERS)]
            game.adjust_rep(power, 5)
            allegiance.charge(game, power, 5)
        kin = [p for p in POWERS if game.rep.get(p, 0) >= 70]
        assert len(kin) == len(POWERS), (
            "working every power up to Kin is impossible even at peace: "
            + str({p: round(game.rep.get(p, 0)) for p in POWERS}))
        return f"all {len(kin)} powers at Kin with the sector at peace"
