"""Exploration checks — knowing a system, and being told about one.

Discovery used to be a single boolean: a system was visited or it was not.
These hold the intel ladder to being a ladder, and hold rumours to the two
things that make them worth having — that they are usually right, and that
reading a noticeboard does not quietly rewrite the sector.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.rumours import KINDS
from ..sim import intel
from ..sim import rumours as rumour_sim
from .harness import Suite


def _fingerprint(game):
    """Everything a rumour could plant, so browsing can be shown not to."""
    return (
        tuple(s.bloom for s in game.galaxy.systems),
        tuple(s.note for s in game.galaxy.systems),
        tuple(b.relic for s in game.galaxy.systems for b in s.bodies),
        tuple(b.anomaly is None for s in game.galaxy.systems for b in s.bodies),
        tuple(tuple(sorted(b.resources.items()))
              for s in game.galaxy.systems for b in s.bodies),
    )


def run(suite: Suite) -> None:
    check = suite.check

    @check("knowledge of a system is a ladder, not a switch")
    def _():
        g = new_game("ladder")
        g.credits = 90000
        far = next(s for s in g.galaxy.systems if intel.level(g, s) == 0)
        seen = [intel.level(g, far)]

        assert intel.buy_chart(g, far)["ok"], "could not buy a chart"
        seen.append(intel.level(g, far))

        far.visited = True
        seen.append(intel.level(g, far))

        for body in far.bodies:
            body.surveyed = True
        seen.append(intel.level(g, far))

        assert seen == [0, 1, 2, 3], f"the ladder does not climb: {seen}"
        names = [intel.LEVELS[x][0] for x in seen]
        assert len(set(names)) == 4, "two rungs read the same"
        return " → ".join(names)

    @check("a chart cannot be bought twice, or bought without funds")
    def _():
        g = new_game("chart-guard")
        far = next(s for s in g.galaxy.systems if intel.level(g, s) == 0)
        g.credits = 0
        broke = intel.buy_chart(g, far)
        assert not broke["ok"], "bought a chart with no money"

        g.credits = 90000
        assert intel.buy_chart(g, far)["ok"]
        again = intel.buy_chart(g, far)
        assert not again["ok"], "sold the same chart twice"
        return "refused when broke, and refused a second time"

    @check("only a complete survey is worth selling, and only once")
    def _():
        g = new_game("survey-sale")
        target = next(s for s in g.galaxy.systems if s.bodies and s is not g.system)
        assert not intel.sellable(g), "something was sellable before any survey"

        # Half-surveyed is not a survey.
        for body in target.bodies[:-1]:
            body.surveyed = True
        assert target not in intel.sellable(g), "a partial survey was sellable"
        refused = intel.sell_survey(g, target, None)
        assert not refused["ok"], "sold an incomplete survey"

        target.bodies[-1].surveyed = True
        assert target in intel.sellable(g), "a complete survey was not sellable"
        before = g.credits
        sold = intel.sell_survey(g, target, None)
        assert sold["ok"] and g.credits > before, "selling paid nothing"
        twice = intel.sell_survey(g, target, None)
        assert not twice["ok"], "sold the same survey twice"
        assert target not in intel.sellable(g), "still listed after selling"
        return f"{len(target.bodies)} bodies sold for {sold['value']:,}"

    @check("reading a noticeboard does not rewrite the sector")
    def _():
        # circulating() decides truth, and a truth test with side effects would
        # seed bloom and bury relics across the sector merely because the desk
        # was drawn. It is drawn on every refresh.
        g = new_game("purity")
        before = _fingerprint(g)
        for index in range(30):
            rumour_sim.circulating(g, g.system, g.rng(f"browse-{index}"))
        assert _fingerprint(g) == before, (
            "merely looking at the rumour desk changed the galaxy")
        return "30 passes over the desk, nothing moved"

    @check("a rumour taken up is usually true, and true ones plant something")
    def _():
        true_count = total = 0
        changed = 0
        for seed in range(30):
            g = new_game(f"rum-{seed}")
            before = _fingerprint(g)
            for rumour in rumour_sim.circulating(g, g.system, g.rng("hear")):
                rumour_sim.take(g, rumour)
                total += 1
                true_count += bool(rumour.true)
            if _fingerprint(g) != before:
                changed += 1
        assert total, "no rumours were generated at all"
        rate = true_count / total
        assert 0.5 < rate < 0.9, f"rumours are true {rate:.0%} of the time"
        assert changed > 20, (
            f"only {changed}/30 games changed when rumours were taken up — "
            "true rumours are not planting what they claim")
        return f"{total} taken, {rate:.0%} true, {changed}/30 galaxies committed"

    @check("a port does not tell you the same kind of story three times")
    def _():
        repeats = 0
        for seed in range(40):
            g = new_game(f"dupe-{seed}")
            kinds = [r.kind for r in rumour_sim.circulating(g, g.system, g.rng("k"))]
            if len(set(kinds)) < len(kinds):
                repeats += 1
        assert not repeats, f"{repeats}/40 ports repeated a rumour kind"
        return f"40 ports, {len(KINDS)} kinds, no repeats"

    @check("arriving settles what was said about the place")
    def _():
        g = new_game("resolve")
        g.credits = 90000
        target = next(s for s in g.galaxy.systems if s.id != g.location_id)
        rumour = rumour_sim.circulating(g, g.system, g.rng("say"))[0]
        rumour.system_id = target.id
        rumour_sim.take(g, rumour)
        assert rumour_sim.about(g, target.id), "the rumour was not filed"

        events = rumour_sim.resolve(g, target.id)
        assert events, "arriving said nothing about a rumour"
        assert rumour.resolved, "the rumour is still open after arriving"
        assert not rumour_sim.about(g, target.id), "still listed as outstanding"
        assert rumour_sim.resolve(g, target.id) == [], "it resolved twice"
        return f"{len(events)} story settled on arrival"

    @check("intel and rumours survive a save and reload")
    def _():
        import json

        from ..core.save import decode, encode

        g = new_game("persist-explore")
        g.credits = 90000
        far = next(s for s in g.galaxy.systems if intel.level(g, s) == 0)
        intel.buy_chart(g, far)
        for rumour in rumour_sim.circulating(g, g.system, g.rng("hear"))[:2]:
            rumour_sim.take(g, rumour, paid=True)
        held_before = [(r.kind, r.system_id, r.true) for r in rumour_sim.held(g)]

        back = decode(json.loads(json.dumps(encode(g))))
        assert intel.level(back, back.galaxy.systems[far.id]) == 1, (
            "the bought chart was lost")
        held_after = [(r.kind, r.system_id, r.true) for r in rumour_sim.held(back)]
        assert held_after == held_before, f"{held_after} != {held_before}"
        return f"{len(held_after)} leads and 1 chart came back"
