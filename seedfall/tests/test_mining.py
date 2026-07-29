"""Mining checks — extraction as a decision rather than a rate.

Working a body used to be "pick a number of days". These hold the methods to
being genuinely different bargains, and hold the seam model to the one
invariant that keeps a captain from being stranded: fuel is always reachable.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.mining import METHODS, METHODS_BY_ID
from ..sim import mining
from ..sim.actions import extract
from ..sim.ship import cargo_free, hull_pct
from .harness import Suite


def _ready(seed: str):
    """A game parked at the richest body in the home system, hold empty."""
    game = new_game(seed)
    game.credits = 200000
    game.stores["biomass"] = 900
    game.ship.cargo = {"volatiles": 60}
    for body in game.system.bodies:
        body.surveyed = True
    index = max(range(len(game.system.bodies)),
                key=lambda i: sum(game.system.bodies[i].resources.values()))
    return game, index, game.system.bodies[index]


def run(suite: Suite) -> None:
    check = suite.check

    @check("fuel is never buried where an open cut cannot reach it")
    def _():
        # A captain with no bore, no reaction mass and volatiles at depth two
        # has no way out of that. The same applies to whatever a body is
        # advertised as: a rock listed as ore-bearing must yield ore.
        stranding = []
        headline = []
        for seed in ("a", "b", "c"):
            game = new_game(seed)
            for system in game.galaxy.systems:
                for body in system.bodies:
                    for seam in mining.seams(body):
                        if seam["resource"] == "volatiles" and seam["depth"] > 1:
                            stranding.append(f"{body.name}")
                    if not body.resources:
                        continue
                    best = max(body.resources.items(), key=lambda kv: kv[1])
                    if best[1] <= 0.01:
                        continue
                    depth = next((s["depth"] for s in mining.seams(body)
                                  if s["resource"] == best[0]), 0)
                    if depth > 1:
                        headline.append(f"{body.name}/{best[0]}")
        assert not stranding, f"fuel out of reach at {stranding[:4]}"
        assert not headline, f"headline seam needs a bore at {headline[:4]}"
        return "fuel and headline seams reachable across three galaxies"

    @check("seams are stable — the same rock hides the same thing")
    def _():
        game = new_game("stable")
        body = game.system.bodies[0]
        first = [(s["resource"], s["depth"]) for s in mining.seams(body)]
        for _ in range(5):
            again = [(s["resource"], s["depth"]) for s in mining.seams(body)]
            assert again == first, f"seams moved between reads: {again} != {first}"
        other = new_game("stable").system.bodies[0]
        twin = [(s["resource"], s["depth"]) for s in mining.seams(other)]
        assert twin == first, "the same seed grew different seams"
        return f"{len(first)} seams, stable across reads and runs"

    @check("the methods are genuinely different bargains")
    def _():
        results = {}
        for method in METHODS:
            tonnes = wear = depletion = 0.0
            ran = 0
            for seed in range(20):
                game, index, body = _ready(f"bargain-{seed}")
                before_hull = hull_pct(game.ship)
                before_dep = body.depleted
                res = extract(game, index, 60, method.id)
                if not res.get("ok") or res.get("dead"):
                    continue
                ran += 1
                tonnes += sum(res["got"].values())
                wear += max(0.0, before_hull - hull_pct(game.ship))
                depletion += body.depleted - before_dep
            if ran:
                results[method.id] = (tonnes / ran, wear / ran, depletion / ran)

        assert "cut" in results and "bore" in results, "a core method never ran"
        cut_t, cut_w, cut_d = results["cut"]
        bore_t, bore_w, bore_d = results["bore"]
        skim_t, skim_w, skim_d = results["skim"]

        assert bore_t > cut_t * 1.3, (
            f"a deep bore is not worth it: {bore_t:.0f} t vs {cut_t:.0f} t")
        assert bore_w > cut_w, "a deep bore costs no more hull than an open cut"
        assert bore_d > cut_d, "a deep bore is no harder on the body"
        assert skim_w == 0.0, "skimming wore the hull"
        assert skim_d < cut_d, "skimming took as much out of the body"
        return " · ".join(f"{k} {v[0]:.0f}t/{v[1]:.1%}hull/{v[2]:.0%}dep"
                          for k, v in results.items())

    @check("a method that cannot reach anything is refused")
    def _():
        game, index, body = _ready("reach")
        # Bury everything: no method but a bore should be offered.
        deep = [s for s in mining.seams(body) if s["depth"] == 2]
        shallow = mining.reachable(body, "skim")
        if not deep and not shallow:
            return "nothing to test with on this body"
        offers = dict((m.id, (ok, why)) for m, ok, why in mining.available(game, body))
        for method_id, (ok, _why) in offers.items():
            reach = bool(mining.reachable(body, method_id))
            assert ok == (reach and _needs_met(game, method_id)), (
                f"{method_id} offered={ok} but reachable={reach}")
        blocked = extract(game, index, 30, "leach") if not _needs_met(game, "leach") \
            else {"ok": True}
        if not blocked.get("ok"):
            assert blocked["why"], "refused without saying why"
        return f"{len(offers)} methods, each offered only when it reaches"

    @check("upkeep is charged, and refused when it cannot be paid")
    def _():
        game, index, _body = _ready("upkeep")
        game.stores["biomass"] = 0
        game.ship.cargo = {"volatiles": 60}
        need = mining.upkeep_for("leach", 30)
        assert need.get("biomass", 0) > 0, "leaching costs nothing to run"
        afford, why = mining.can_afford(game, "leach", 30)
        assert not afford and why, "leaching ran with no biomass"

        game.stores["biomass"] = 500
        before = game.stores["biomass"]
        assert mining.can_afford(game, "leach", 30)[0]
        mining.spend_upkeep(game, "leach", 30)
        spent = before - game.stores["biomass"]
        assert abs(spent - need["biomass"]) < 0.01, (
            f"charged {spent:.1f} rather than {need['biomass']:.1f}")
        return f"leaching 30 days costs {need['biomass']:.0f} t of biomass"

    @check("working a body out makes it stop paying")
    def _():
        game, index, body = _ready("exhaust")
        first = extract(game, index, 60, "bore")
        assert first["ok"]
        early = sum(first["got"].values())
        for _ in range(6):
            game.ship.cargo = {"volatiles": 60}     # keep room in the hold
            extract(game, index, 90, "bore")
        assert body.depleted > 0.8, f"six seasons of boring left it at {body.depleted:.0%}"
        game.ship.cargo = {"volatiles": 60}
        last = extract(game, index, 60, "bore")
        if last["ok"]:
            # Not finished yet, but plainly on the way out.
            late = sum(last["got"].values())
            assert late < early * 0.5, (
                f"a worked-out body still pays {late:.0f} t against "
                f"{early:.0f} t")
            return (f"{early:.0f} t fresh → {late:.0f} t at "
                    f"{body.depleted:.0%} worked out")
        # A body that is finished refuses the rig outright now. It used to sit
        # at the cap paying a token tonne a session for ever, which is what
        # this check was written against.
        assert "worked out" in last["why"].lower(), last
        return (f"{early:.0f} t fresh, then the body refused the rig at "
                f"{body.depleted:.0%} worked out")

    @check("deep work is where the mishaps are")
    def _():
        from ..core.rng import RNG
        counts = {}
        for method in METHODS:
            mishaps = 0
            for seed in range(120):
                game, _index, body = _ready(f"risk-{seed % 6}")
                event = mining.roll_event(game, body, method.id, RNG(f"r{seed}"))
                mishaps += bool(event and event["kind"] == "mishap")
            counts[method.id] = mishaps
        assert counts["bore"] > counts["cut"] > counts["skim"], (
            f"risk does not rise with depth: {counts}")
        assert counts["skim"] == 0, "skimming the surface went wrong"
        return " · ".join(f"{k} {v}/120" for k, v in counts.items())


def _needs_met(game, method_id: str) -> bool:
    method = METHODS_BY_ID[method_id]
    return not method.needs or getattr(game.ship_stats, method.needs, 0) > 0
