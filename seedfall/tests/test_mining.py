"""Mining checks — extraction as a decision rather than a rate.

Working a body used to be "pick a number of days". These hold the methods to
being genuinely different bargains, and hold the seam model to the one
invariant that keeps a captain from being stranded: fuel is always reachable.

Two faults found by working bodies out and watching:

- **A phosphate rig or a harvest tendril stripped a body for ever.**
  `actions.extract` depleted at `st.mine + st.drink`, and `raise_rate` lifts
  material with four rigs. A hull carrying only a phosphate rig raised 0.507 t a
  day and wore the body down by *exactly zero*, so `worked_out` never fired. An
  infinite source is not a slow one.
- **The forecast was out by 2% on a bioleach and 45% on a bore.** `prospect`
  estimated the average rate at the midpoint of what was left and multiplied by
  days and a `WORKING_LOSS` fudge, and its error tracked how fast the method
  depletes — so the figure a captain compares methods on was biased *by the
  method being compared*. It is a dry run now, and matches the act to within a
  fraction of a per cent.
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
        # **Not "exactly nothing", which was an artefact of free repair.**
        # A mining ship carries no biomass, so once `ship.repair_tick` had to
        # be paid for in feedstock it stopped erasing the wear a skim inflicts
        # inside the run. The wear was always there; the hull just healed it
        # back for nothing. Measured over twenty runs a side:
        #
        #     leach 0.30%   skim 0.54%   cut 1.15%   bore 3.12%
        #
        # The claim worth making is the one the ordering supports — a skim is
        # the gentle way to work a body — and it is a comparison rather than a
        # zero, so nothing about how repair is paid for can flatter it.
        assert skim_w < cut_w, (
            f"skimming wore {skim_w:.2%} of the hull against {cut_w:.2%} for "
            "an open cut — it is not the gentle method")
        assert skim_w < bore_w * 0.5, (
            f"skimming wore {skim_w:.2%} against a bore's {bore_w:.2%}")
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

    @check("a body gives up the same whichever rigs you skew to")
    def _():
        # **The exploit.** `actions.extract` depleted the body at
        # `st.mine + st.drink`, and `raise_rate` lifts material with four rigs.
        # So a phosphate rig and a harvest tendril raised material and wore the
        # body down by nothing: fit a token mining root beside them and one
        # asteroid gave up **8,427 t over 283 spells instead of 140 t over 8** —
        # sixty times its worth.
        #
        # Not infinite, because `extract` refuses a hull with no mining root and
        # no harvest tendril at all — which is what a first draft of this check
        # claimed and had to withdraw. Sixty times is enough.
        def total(skew, seed="skew"):
            game = new_game(seed)
            game.recompute()
            index = next(i for i, b in enumerate(game.system.bodies)
                         if b.kind in ("asteroid", "moon", "rocky"))
            for b in game.system.bodies:
                b.surveyed = True
            body = game.system.bodies[index]
            game.credits = 5_000_000
            for key in ("volatiles", "biomass"):
                game.stores[key] = 10 ** 6
            real = mining.roll_event
            mining.roll_event = lambda *a, **k: None
            got, spells = 0.0, 0
            try:
                while not mining.worked_out(body) and spells < 900:
                    game.ship.cargo = {}
                    game.recompute()
                    for attr, value in skew.items():
                        setattr(game.ship_stats, attr, value)
                    out = extract(game, index, 10, "bore")
                    if not out.get("ok"):
                        break
                    got += sum(out.get("got", {}).values())
                    spells += 1
            finally:
                mining.roll_event = real
            return got, spells

        plain, plain_spells = total({"mine": 3.2, "phos": 0.1,
                                     "drink": 0.8, "graze": 0.3})
        skewed, skewed_spells = total({"mine": 0.1, "phos": 3.2,
                                       "drink": 0.0, "graze": 3.2})
        assert plain > 10, plain
        ratio = skewed / plain
        assert ratio < 2.5, (
            f"a hull skewed to phosphate and harvest took {skewed:.0f} t off the "
            f"body against {plain:.0f} t for an ordinary one — {ratio:.0f} times "
            "as much. A rig that lifts material has to wear the body down, or "
            "the body is a fountain")
        assert skewed_spells < plain_spells * 4, (
            f"{skewed_spells} spells against {plain_spells}: the skewed hull is "
            "still working a body that should have finished")

        # And the arithmetic behind it: every rig `raise_rate` lifts with is a
        # rig `rig_of` counts.
        class _Rig:
            """A stand-in carrying only the four rig ratings."""

            def __init__(self, **kw):
                for attr in ("mine", "phos", "drink", "graze"):
                    setattr(self, attr, kw.get(attr, 0.0))

        _game, _index, body = _ready("every-rig")
        for _cid, attr in mining.RIGS:
            stats = _Rig(**{attr: 3.2})
            lifts = mining.raise_rate(body, "bore", stats)
            assert lifts > 0.01, (attr, lifts)
            assert mining.rig_of(stats) > 0, (
                f"a {attr} rig lifts {lifts:.3f} t a day and wears the body "
                "down by nothing")
        return (f"ordinary {plain:.0f} t in {plain_spells} spells · skewed "
                f"{skewed:.0f} t in {skewed_spells} — {ratio:.1f}x, was 60x")

    @check("the prospect is what the working actually gives up")
    def _():
        # The forecast against the act, which is what a captain chooses a method
        # on. Events are silenced for the comparison: a strike is a windfall and
        # a mishap is an accident, and a forecast that promised the average of
        # them would be wrong on every individual run. They are checked to be
        # noise either side rather than a bias, below.
        game, index, body = _ready("prospect")
        game.credits = 5_000_000
        for key in ("volatiles", "biomass"):
            game.stores[key] = 10 ** 6

        def work_out(method_id, quiet=True):
            g, i, b = _ready(f"pros-{method_id}")
            g.credits = 5_000_000
            for key in ("volatiles", "biomass"):
                g.stores[key] = 10 ** 6
            if not mining.reachable(b, method_id):
                return None
            said = mining.prospect(b, method_id, g.ship_stats)
            real = mining.roll_event
            if quiet:
                mining.roll_event = lambda *a, **k: None
            got, days, spells = 0.0, 0, 0
            try:
                while not mining.worked_out(b) and spells < 500:
                    g.ship.cargo = {}
                    g.recompute()
                    out = extract(g, i, 5, method_id)
                    if not out.get("ok"):
                        break
                    got += sum(out.get("got", {}).values())
                    days += out.get("days", 0)
                    spells += 1
                    if g.dead:
                        break
            finally:
                mining.roll_event = real
            return said, got, days

        looked, worst = 0, 0.0
        lines = []
        for method in METHODS:
            r = work_out(method.id)
            if r is None:
                continue
            said, got, days = r
            assert said["total"] > 0 and said["days"] > 0, (method.id, said)
            off = abs(got - said["total"]) / said["total"]
            worst = max(worst, off)
            assert off < 0.05, (
                f"{method.id}: the screen forecast {said['total']:.1f} t and the "
                f"working gave up {got:.1f} — {off:.0%} out. A forecast whose "
                "error depends on the method is a forecast that tilts the "
                "comparison it exists to inform")
            assert abs(days - said["days"]) <= 6, (
                f"{method.id}: forecast {said['days']:.0f} days, took {days}")
            looked += 1
            lines.append(f"{method.id} {said['total']:.0f}t/{got:.0f}t")
        assert looked >= 3, looked
        return " · ".join(lines) + f" — worst {worst:.1%} out"

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
