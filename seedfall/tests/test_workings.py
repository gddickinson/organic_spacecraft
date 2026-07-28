"""Mining checks — a rig stops when there is nowhere to put what it raises.

`extract()` computed the haul for the whole spell, took `min(amount,
cargo_free)` and then depleted the body for the full duration regardless.
Measured: sixty days on a body with an empty hold took 106.2 t and worked it
out by 0.384. With the hold 97% full it took 10.2 t — and worked the body out
by the identical 0.384. Ninety-six tonnes raised and thrown away, a third of
the body spent, sixty days gone, and nothing anywhere said so: the panel quoted
tonnes a day and offered "Work it — 30 days" with no forecast at all.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import mining
from ..sim.actions import extract
from ..sim.ship import cargo_free
from .harness import Suite


def _sited(seed: str, fill: float = 0.0):
    """A game parked at the richest body in the home system."""
    game = new_game(seed)
    for body in game.system.bodies:
        body.surveyed = True
    index = max(range(len(game.system.bodies)),
                key=lambda i: sum(game.system.bodies[i].resources.values()))
    if fill:
        game.ship.cargo = {"alloy": game.ship_stats.cargo * fill}
    return game, index, game.system.bodies[index]


def run(suite: Suite) -> None:
    check = suite.check

    @check("a full hold does not cost you the body as well")
    def _():
        # The bug, stated as a comparison. Both runs lift what they can carry;
        # only one of them used to leave the body worth returning to.
        roomy, index, body = _sited("cost", 0.0)
        extract(roomy, index, 60, "cut")
        spent_free = body.depleted

        tight, index2, body2 = _sited("cost", 0.97)
        result = extract(tight, index2, 60, "cut")
        spent_full = body2.depleted
        lifted = sum(result.get("got", {}).values())

        assert spent_free > 0.1, "the roomy run barely touched it"
        assert spent_full < spent_free * 0.4, (
            f"a hold with no room still cost {spent_full:.3f} of the body "
            f"against {spent_free:.3f} with room for the lot")
        assert result["cut_short"], "the working did not stop early"
        assert result["days"] < 60, f"it ran the full {result['days']} days"
        return (f"{lifted:.0f} t in {result['days']} days for "
                f"{spent_full:.3f} of the body, against {spent_free:.3f} "
                "for the whole spell")

    @check("depletion follows what was actually lifted")
    def _():
        # Not merely smaller — proportional. A quarter of the haul should cost
        # about a quarter of the body.
        full, index, body = _sited("prop", 0.0)
        extract(full, index, 60, "cut")
        whole = body.depleted

        # Leave room for a quarter of what the spell would actually raise,
        # measured rather than assumed. Picking a fill fraction blind made the
        # first version of this check pass without any capping happening at
        # all, on a seed whose body simply raised less than the hold.
        part, index2, body2 = _sited("prop", 0.0)
        st = part.ship_stats
        whole_haul = mining.raise_rate(body2, "cut", st) * 60
        want = whole_haul * 0.25
        part.ship.cargo = {"alloy": max(0.0, st.cargo - want)}
        result = extract(part, index2, 60, "cut")
        assert result["cut_short"], "no capping happened; the check is vacuous"
        share = result["days"] / 60
        assert abs(body2.depleted / whole - share) < 0.06, (
            f"lifted {share:.0%} of the spell and paid "
            f"{body2.depleted / whole:.0%} of the depletion")
        return (f"{share:.0%} of the spell cost "
                f"{body2.depleted / whole:.0%} of the body")

    @check("with room, the whole spell runs")
    def _():
        game, index, body = _sited("roomy", 0.0)
        result = extract(game, index, 30, "cut")
        assert result["ok"] and not result["cut_short"], "cut short with room"
        assert result["days"] == 30, f"ran {result['days']} of 30"
        room = result["room"]
        assert sum(result["got"].values()) <= room + 0.01
        return f"30 of 30 days, {sum(result['got'].values()):.0f} t into {room:.0f} t of room"

    @check("the forecast is what the working does")
    def _():
        # The panel prints this. It has to be the truth.
        checked = 0
        for fill in (0.0, 0.5, 0.9, 0.97):
            game, index, body = _sited("forecast", fill)
            st = game.ship_stats
            room = cargo_free(game.ship, st)
            said = mining.days_of_room(body, "cut", st, room, 60)
            raised = mining.raise_rate(body, "cut", st) * said
            result = extract(game, index, 60, "cut")
            if not result.get("ok"):
                continue
            assert result["days"] == said, (
                f"forecast {said} days, worked {result['days']}")
            got = sum(result["got"].values())
            # Strikes and mishaps move the haul; the forecast is the plan.
            assert got <= raised * 1.35 + 0.5, (
                f"forecast {raised:.1f} t and it raised {got:.1f} t")
            checked += 1
        assert checked >= 3, f"only {checked} forecasts flown"
        return f"{checked} spells, days exactly as forecast"

    @check("a hold with no room is refused, not wasted")
    def _():
        game, index, body = _sited("nowhere", 1.0)
        assert cargo_free(game.ship, game.ship_stats) < 1
        before_day, before_dep = game.day, body.depleted
        result = extract(game, index, 60, "cut")
        assert not result["ok"], "it worked the body with nowhere to put it"
        assert body.depleted == before_dep, "the body was worked anyway"
        assert game.day == before_day, (
            f"{game.day - before_day} days spent on a refused working")
        return f"refused: {result['why']!r}"

    @check("a full hold is not a stranding")
    def _():
        # Refusing to work a body with nowhere to put the ore is right, and it
        # created a deadlock: no room to mine ice for reaction mass, no mass to
        # jump on, and the only way to dump anything was the contraband panel,
        # which appears solely when carrying contraband at a hostile port. The
        # playability bot span on it forever — extract refused, no time passed,
        # and the year limit was never reached.
        from ..sim import trade as trade_sim
        game, index, body = _sited("stranded", 1.0)
        game.ship.cargo["volatiles"] = 0
        assert cargo_free(game.ship, game.ship_stats) < 1
        assert not extract(game, index, 30, "cut")["ok"]

        spare = max(game.ship.cargo, key=lambda c: game.ship.cargo[c])
        vented = trade_sim.jettison(game, spare)
        assert vented["ok"], vented.get("why")
        assert cargo_free(game.ship, game.ship_stats) > 1, "venting freed nothing"
        result = extract(game, index, 30, "cut")
        assert result["ok"], f"still stranded: {result.get('why')}"
        assert sum(result["got"].values()) > 0, "mined nothing after venting"
        return (f"vented {vented['tonnes']:.0f} t and worked "
                f"{result['days']} days for "
                f"{sum(result['got'].values()):.0f} t")

    @check("the gentle methods are still the ones that keep a body")
    def _():
        # The decision this whole system exists for. Boring is fastest and
        # costs the most ground; bioleach is nearly as quick per day and takes
        # a seventh as much out.
        out = {}
        for method in ("cut", "bore", "leach"):
            game, index, body = _sited(f"methods-{method}", 0.0)
            game.stores["biomass"] = 3000
            game.ship.cargo = {"volatiles": 60}
            game.research.unlocked.append("bioleach")
            game.recompute()
            result = extract(game, index, 30, method)
            if not result.get("ok"):
                continue
            lifted = sum(result["got"].values())
            out[method] = (lifted, body.depleted,
                           lifted / max(0.001, body.depleted))
        assert len(out) == 3, f"only {list(out)} could be worked"
        assert out["bore"][0] > out["cut"][0], "boring lifts no more than cutting"
        assert out["bore"][1] > out["leach"][1] * 2, (
            "boring is no harder on the body than leaching")
        assert out["leach"][2] > out["bore"][2], (
            "leaching recovers no more per point of depletion than boring")
        return " · ".join(f"{k} {v[0]:.0f} t at {v[1]:.2f}" for k, v in out.items())
