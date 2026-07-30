"""Whose word it is: a rumour's source, and whether the buyer knows yours.

Two fields had been written since the day their features shipped and read by
nobody at all.

**`Rumour.heard_at`** — the port you were told it at. Truth was
`not rng.chance(kind.unreliable)`, a per-kind coin flip, so a story about the far
side of the sector told at a lonely outpost by people who have never been within
forty light-years of it was exactly as good as one about the next star over told
at a Fleet Hub where a dozen hulls a week put in.

**`Mind.met` and `Mind.first_met`** — how many times somebody has dealt with you
and since when. Every decision in the game came from standing, which is what you
have *done*, and nothing came from acquaintance, which is who you *are* to them.
A captain who had traded at the same quay for six years and one who arrived last
week were the same stranger.

The claims are measured over samples big enough to see a rate in, because both
mechanisms are probabilistic:

- **where you heard it decides how often it is true** — and the desk's own trust
  figure is that rate, not a separate opinion about it;
- **the price follows the source**, and the price shown is the price charged;
- **the quay counts as well as the distance**;
- **a buyer who knows you pays more for a survey**, and both halves of knowing
  count — twenty dealings in a month is not the same as twenty over five years.
"""

from __future__ import annotations

from statistics import mean

from ..core.state import new_game
from ..data.charts import KNOWN_WORTH
from ..data.rumours import (BEST_ODDS, FAR_LY, FAR_UNRELIABLE, KINDS_BY_ID,
                            LOCAL_LY, QUAY_TRUST, WORST_ODDS)
from ..sim import charts as chart_sim
from ..sim import intel as intel_sim
from ..sim import memory as memory_sim
from ..sim import rumours as rumour_sim
from ..sim import services as service_sim
from ..world.galaxy import distance
from .harness import Suite


def _mill(seeds: int = 6, months: int = 6) -> list:
    """Every story the sector's ports tell over a few months, with its source."""
    out = []
    for seed in range(seeds):
        game = new_game(f"prov-{seed}")
        for system in [s for s in game.galaxy.systems if s.port]:
            game.location_id = system.id
            for month in range(months):
                rng = game.rng(f"rumour-{system.id}-{month}")
                for story in rumour_sim.circulating(game, system, rng):
                    out.append((game, story, rumour_sim.provenance(game, story)))
    return out


def run(suite: Suite) -> None:
    check = suite.check

    @check("where you heard it decides how often it is true")
    def _():
        told = _mill()
        assert len(told) > 800, len(told)
        near = [s.true for _g, s, p in told if p["far"] < 0.25]
        far = [s.true for _g, s, p in told if p["far"] > 0.6]
        assert len(near) > 150 and len(far) > 150, (len(near), len(far))
        near_rate, far_rate = mean(near), mean(far)
        assert near_rate > far_rate + 0.15, (
            f"local stories come true {near_rate:.0%} of the time and stories "
            f"from the far side of the sector {far_rate:.0%} — where you heard "
            "it is not reaching the truth of it")

        # **And the figure the desk shows is that rate**, not a second opinion
        # about it. The panel prints `trust` as "this many turn out true", so it
        # had better be how many turn out true.
        for band, rows in (("local", [(s, p) for _g, s, p in told
                                      if p["far"] < 0.25]),
                           ("far", [(s, p) for _g, s, p in told
                                    if p["far"] > 0.6])):
            said = mean([p["trust"] for _s, p in rows])
            got = mean([s.true for s, _p in rows])
            assert abs(said - got) < 0.06, (
                f"{band}: the desk says {said:.0%} of these turn out true and "
                f"{got:.0%} of them do")
        return (f"{len(told)} stories: {near_rate:.0%} true from local sources, "
                f"{far_rate:.0%} from the far side")

    @check("heard_at is what is being read, not the distance from anywhere else")
    def _():
        # The direct test that the *field* is consumed: move where the story was
        # told and nothing else, and the answer has to change.
        game = new_game("heard-where")
        ports = [s for s in game.galaxy.systems if s.port]
        target = max(game.galaxy.systems,
                     key=lambda s: distance(s, ports[0]))
        story = rumour_sim.Rumour(id=1, kind="rich", system_id=target.id,
                                  heard_at=ports[0].id)
        far = rumour_sim.provenance(game, story)
        nearest = min((s for s in ports if s.id != target.id),
                      key=lambda s: distance(s, target))
        story.heard_at = nearest.id
        near = rumour_sim.provenance(game, story)
        assert near["trust"] > far["trust"], (
            f"told at {ports[0].name} ({far['light_years']:.0f} ly off) it is "
            f"worth {far['trust']:.0%}, and at {nearest.name} "
            f"({near['light_years']:.0f} ly off) {near['trust']:.0%}")
        assert near["light_years"] < far["light_years"]
        return (f"the same story is {far['trust']:.0%} good at "
                f"{far['light_years']:.0f} ly and {near['trust']:.0%} at "
                f"{near['light_years']:.0f} ly")

    @check("a busy quay hears better than a quiet one")
    def _():
        # Distance held still, traffic varied: the other half of provenance.
        game = new_game("quay-heard")
        pair = [s for s in game.galaxy.systems if s.port][:1]
        quay = pair[0]
        target = next(s for s in game.galaxy.systems if s.id != quay.id)
        story = rumour_sim.Rumour(id=2, kind="wreck", system_id=target.id,
                                  heard_at=quay.id)
        seen = {}
        for level in (1, 2, 3):
            quay.port.level = level
            seen[level] = rumour_sim.provenance(game, story)["trust"]
        assert seen[3] > seen[1], (
            f"an outpost's word is worth {seen[1]:.0%} and a hub's "
            f"{seen[3]:.0%}")
        assert abs((seen[3] - seen[1]) - 2 * QUAY_TRUST) < 1e-9, (
            f"two levels of quay moved trust by {seen[3] - seen[1]:.3f}")
        return " · ".join(f"level {k} {v:.0%}" for k, v in seen.items())

    @check("the price follows the source, and it is the price charged")
    def _():
        told = _mill(seeds=3)
        best = max(told, key=lambda row: row[2]["trust"])
        # Within one kind, because the kinds have base prices from 700 to 2,200
        # — the dearest lead in the sector is a dear *kind*, not a good source,
        # and comparing across them reads backwards.
        same = [(g, s, p) for g, s, p in told if s.kind == best[1].kind]
        near = mean([rumour_sim.price_of(g, s) for g, s, p in same
                     if p["far"] < 0.25] or [0])
        far = mean([rumour_sim.price_of(g, s) for g, s, p in same
                    if p["far"] > 0.6] or [0])
        assert near > far, (
            f"{KINDS_BY_ID[best[1].kind].name}: a local source is quoted "
            f"{near:,.0f} and a distant one {far:,.0f}")

        # And the counter charges what the desk quoted. The panel prints
        # `price_of`; `services.buy_rumour` had its own copy of the number
        # until this cycle, which is the arrangement that has produced a free
        # treaty and a phantom haggle payment elsewhere in this project.
        game, story, _p = best
        quoted = rumour_sim.price_of(game, story)
        game.credits = quoted + 500
        res = service_sim.buy_rumour(game, story, True, game.rng("pay"))
        assert res["ok"], res
        assert res["price"] == quoted, (res["price"], quoted)
        assert abs(game.credits - 500) < 1e-6, (
            f"quoted {quoted:,} and took {quoted + 500 - game.credits:,.0f}")
        return (f"{KINDS_BY_ID[best[1].kind].name}: {near:,.0f} from a local "
                f"source against {far:,.0f} from a distant one; charged "
                f"{quoted:,} and took {quoted:,}")

    @check("nothing is certain and nothing is hopeless")
    def _():
        told = _mill(seeds=4)
        trusts = [p["trust"] for _g, _s, p in told]
        assert max(trusts) <= BEST_ODDS + 1e-9, max(trusts)
        assert min(trusts) >= WORST_ODDS - 1e-9, min(trusts)
        # And the range is actually used, or the bounds are decoration.
        assert max(trusts) - min(trusts) > 0.25, (
            f"every story in the sector is worth between {min(trusts):.0%} and "
            f"{max(trusts):.0%}; the geography is not reaching the odds")
        return (f"{min(trusts):.0%} to {max(trusts):.0%} across "
                f"{len(trusts)} stories")

    @check("a buyer who knows you pays more for a survey")
    def _():
        game = new_game("acq-worth")
        system = game.galaxy.systems[3]
        stranger = intel_sim.survey_value(game, system, "charter")
        assert chart_sim.acquaintance(game, "charter")["met"] == 0

        for index in range(memory_sim.MET_FULL):
            memory_sim.note(game, "faction:charter", "trade",
                            f"an honest cargo, {index}", name="Charter",
                            entity="faction")
        game.day = int(memory_sim.YEARS_FULL * 365)
        known = chart_sim.acquaintance(game, "charter")
        assert known["trust"] > 0.95, known
        familiar = intel_sim.survey_value(game, system, "charter")
        assert familiar > stranger, (
            f"a stranger is paid {stranger:,} and somebody they have dealt "
            f"with {known['met']} times over {known['years']:.0f} years is "
            f"paid {familiar:,}")
        lift = familiar / stranger - 1.0
        assert abs(lift - KNOWN_WORTH) < 0.02, (
            f"being fully known is worth {lift:.0%}")

        # And it is only ever a lift: an office that has never met you pays the
        # base rather than a penalty, because the base is what a chart is worth.
        assert chart_sim.acquaintance(game, None)["trust"] == 0.0
        assert intel_sim.survey_value(game, system, None) > 0
        return (f"{stranger:,} from a stranger, {familiar:,} once they know "
                f"you — {lift:.0%}")

    @check("both halves of knowing somebody count")
    def _():
        # `met` alone would make a busy fortnight the same as a long
        # acquaintance, and `first_met` alone would reward doing nothing for
        # years. Measured against each other on the same mind.
        game = new_game("acq-halves")
        key = "faction:concordat"
        for index in range(memory_sim.MET_FULL * 2):
            memory_sim.note(game, key, "trade", f"cargo {index}",
                            name="Concordat", entity="faction")
        game.day = 20
        busy = memory_sim.acquaintance(game, key)

        game2 = new_game("acq-halves-2")
        for index in range(3):
            memory_sim.note(game2, key, "trade", f"cargo {index}",
                            name="Concordat", entity="faction")
        game2.day = int(memory_sim.YEARS_FULL * 365)
        old = memory_sim.acquaintance(game2, key)

        assert busy["trust"] < 1.0, (
            f"twenty-four dealings inside a month reads as {busy['trust']:.0%} "
            "acquaintance; that is a busy quarter, not a friendship")
        assert old["trust"] < 1.0, (
            f"three dealings spread over {old['years']:.0f} years reads as "
            f"{old['trust']:.0%}; showing up is not the same as dealing")
        assert busy["trust"] > old["trust"], (
            f"business {busy['trust']:.0%} against years {old['trust']:.0%}: "
            "business is meant to weigh more")
        # A mind nobody has ever met is a stranger, not an error.
        blank = memory_sim.acquaintance(game, "faction:nobody")
        assert blank["trust"] == 0.0 and not blank["known"]
        assert "stranger" in blank["words"]
        return (f"24 dealings in a month {busy['trust']:.0%} · 3 over "
                f"{memory_sim.YEARS_FULL:.0f} years {old['trust']:.0%}")

    @check("the office says what you are to it, in words")
    def _():
        # The readout is the whole point of reviving the field: a number the
        # player cannot see is a number that may as well not exist.
        game = new_game("acq-words")
        key = "faction:sanhedrin"
        assert "stranger" in memory_sim.acquaintance(game, key)["words"]
        seen = []
        for index in range(memory_sim.MET_FULL + 2):
            memory_sim.note(game, key, "trade", f"cargo {index}",
                            name="Sanhedrin", entity="faction")
            game.day = int(index * memory_sim.YEARS_FULL * 365
                           / (memory_sim.MET_FULL + 1))
            seen.append(memory_sim.acquaintance(game, key)["words"])
        assert len({w for w in seen}) >= 3, (
            f"the office describes every stage of an acquaintance the same "
            f"way: {set(seen)}")
        assert "know exactly who you are" in seen[-1], seen[-1]
        for words in seen:
            assert "dealings" in words
        return f"{len(set(seen))} distinct readings, ending “{seen[-1]}”"

    @check("the numbers put a real decision on the desk")
    def _():
        # Tripwires. Each one is pinned by what it does to a decision rather
        # than by repeating its own value.
        assert LOCAL_LY < FAR_LY, (LOCAL_LY, FAR_LY)
        assert FAR_UNRELIABLE > 1.4, (
            "distance barely changes how good a story is")
        assert 0.02 < QUAY_TRUST < 0.15, QUAY_TRUST
        assert 0.10 < KNOWN_WORTH < 0.60, KNOWN_WORTH

        # **Both marks have to sit inside the sector's own geography**, or the
        # scale is decoration. The first draft used 12 and 55 light-years, which
        # is the 12th and the 96th percentile of the 4,264 port-to-system
        # distances a sector actually has: three per cent of stories reached the
        # far end and the whole top of the range did nothing.
        game = new_game("prov-scale")
        ports = [s for s in game.galaxy.systems if s.port]
        spans = [distance(a, b) for a in ports for b in game.galaxy.systems
                 if a.id != b.id]
        share = len([d for d in spans if d < LOCAL_LY]) / len(spans)
        beyond = len([d for d in spans if d > FAR_LY]) / len(spans)
        assert 0.03 < share < 0.35, (
            f"{share:.0%} of the sector is inside {LOCAL_LY:.0f} ly of a port; "
            "a local source is meant to be uncommon and worth having")
        assert 0.08 < beyond < 0.5, (
            f"{beyond:.0%} of the sector is beyond {FAR_LY:.0f} ly, so the far "
            "end of the scale is either never reached or reached by everything")

        # And a well-sourced story is worth paying for. Compared within one
        # kind: the kinds have base prices from 700 to 2,200, so the dearest
        # lead in the sector against the cheapest says nothing about sources.
        told = _mill(seeds=2)
        gaps = []
        for kind in {s.kind for _g, s, _p in told}:
            same = [(g, s, p) for g, s, p in told if s.kind == kind]
            near = [rumour_sim.price_of(g, s) for g, s, p in same
                    if p["far"] < 0.25]
            far = [rumour_sim.price_of(g, s) for g, s, p in same
                   if p["far"] > 0.6]
            if near and far:
                gaps.append(mean(near) / mean(far))
        assert gaps and min(gaps) > 1.15, (
            f"within a kind, a local source costs {min(gaps):.2f}x a distant "
            "one — the price is not following the provenance")
        return (f"{share:.0%} of pairs local, {beyond:.0%} beyond the far "
                f"mark; a local lead costs {min(gaps):.2f}–{max(gaps):.2f}x a "
                "distant one of the same kind")
