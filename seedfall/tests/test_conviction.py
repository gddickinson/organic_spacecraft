"""What the bridge notices: every event an officer has an opinion about.

`data/convictions.py` gives each officer a set of things they react to, with a
number beside each. Five of those numbers were never once delivered:

- **`promoted`**, +5 to every officer aboard whatever they believe, because it
  is in `UNIVERSAL`. `crew.grant_xp` returns the list of people it has just
  promoted — that is what the return value is *for* — and all eight call sites
  threw it away. A career built over a decade moved nobody and was not even
  written in the log.
- **`licence_served` and `free_served`**, +11 each, the largest single thing
  either of those convictions believes in. A Charter partisan could run
  Charter commissions for ten years and feel it only as the same
  `commission_done` that everybody else felt.
- **`burner_served` and `xeno_served`**, +11 and +13 — unreachable, because
  those convictions have no aligned power, and duplicating `bloom_cleansed`
  and `xeno_incorporated`, which do fire. Removed rather than left in the data
  claiming something untrue.

The claims:

- **Every event a conviction declares is delivered by something.** The general
  one, and the reason the other four were found.
- **A promotion is noticed** — by the ship, by the person, and in the log.
- **Serving a power pleases its partisans and nobody else.**
- **Loyalty still bites**: an unpaid bridge still empties.
"""

from __future__ import annotations

import pathlib

from ..core.state import new_game
from ..data.convictions import (CONVICTIONS, PROMOTION_OWN, RESTLESS,
                                UNIVERSAL, WALKOUT)
from ..sim import loyalty
from ..sim.crew import grant_xp
from .harness import Suite

#: Events whose names the sim builds rather than writes — `loyalty.served`
#: composes `f"{conviction.id}_served"`, so a search of the source cannot see
#: them. Each one is proved to fire by a check in this file instead.
COMPOSED = {"licence_served", "free_served"}

#: Where a consumer could live. `data/` declares them; `tests/` proves nothing.
SOURCES = ("sim", "core", "ui", "world", "bridge")


def _declared() -> set:
    out = set(UNIVERSAL)
    for conviction in CONVICTIONS:
        out |= set(conviction.reacts)
    return out


def _blob() -> str:
    root = pathlib.Path(__file__).resolve().parent.parent
    return "\n".join(path.read_text(encoding="utf-8")
                     for folder in SOURCES
                     for path in (root / folder).rglob("*.py"))


def run(suite: Suite) -> None:
    check = suite.check

    @check("every event a conviction declares is delivered by something")
    def _():
        # The general question. It found `promoted` and the four `_served`
        # events in one pass, which no amount of testing the events that do
        # fire would have done.
        declared = _declared()
        assert len(declared) > 25, len(declared)
        blob = _blob()
        dead = sorted(event for event in declared
                      if event not in COMPOSED
                      and f'"{event}"' not in blob and f"'{event}'" not in blob)
        assert not dead, (
            f"{len(dead)} event(s) officers have opinions about that nothing "
            f"ever records: {dead}")
        # And nothing sits in the allowance that is not actually composed.
        for event in COMPOSED:
            assert event.endswith("_served"), event
            assert any(event in c.reacts for c in CONVICTIONS), (
                f"{event} is excused from the search and no conviction wants "
                "it — the allowance is covering nothing")
        return (f"{len(declared)} events, {len(declared) - len(COMPOSED)} "
                f"found in the source and {len(COMPOSED)} composed")

    @check("a promotion is noticed by the ship, the officer, and the log")
    def _():
        game = new_game("promo")
        before = {o.id: loyalty.loyalty_of(o) for o in game.officers}
        was = {o.id: o.level for o in game.officers}
        logged = len(game.log)
        gained = grant_xp(game.officers, "science", 900, game=game)
        assert gained, "nobody was promoted by nine hundred points of science"
        # A promotion is a level. Reporting one without raising it passed
        # every other assertion here.
        for officer in gained:
            assert officer.level > was[officer.id], (
                f"{officer.name} was reported promoted at level "
                f"{officer.level}, the same as before")
        after = {o.id: loyalty.loyalty_of(o) for o in game.officers}

        risen = gained[0]
        others = [o for o in game.officers if o.id != risen.id]
        assert others, "a one-officer bridge cannot show the difference"
        own = after[risen.id] - before[risen.id]
        ship = after[others[0].id] - before[others[0].id]
        assert ship > 0, (
            f"the ship felt {ship:+.1f} for a promotion — `promoted` is in "
            "UNIVERSAL and is supposed to reach everybody")
        assert own > ship, (
            f"the officer promoted felt {own:+.1f} and a bystander felt "
            f"{ship:+.1f} — their own career should be worth more to them")
        assert abs(own - (ship + PROMOTION_OWN)) < 0.01, (own, ship)
        assert len(game.log) > logged, "a promotion was not written down"
        assert any(risen.name in str(line[1]) and "is made" in str(line[1])
                   for line in game.log[logged:]), game.log[logged:]
        return (f"{risen.name} feels {own:+.1f}, the rest of the bridge "
                f"{ship:+.1f}, and it is in the log")

    @check("a promotion with no game to tell moves nobody")
    def _():
        # The parameter is optional so old callers keep working; it must be
        # inert, not half-applied.
        game = new_game("quiet")
        before = {o.id: loyalty.loyalty_of(o) for o in game.officers}
        was = {o.id: o.level for o in game.officers}
        gained = grant_xp(game.officers, "science", 900)
        assert gained, gained
        assert all(o.level > was[o.id] for o in gained), "reported, not raised"
        after = {o.id: loyalty.loyalty_of(o) for o in game.officers}
        assert before == after, "loyalty moved without a game to record it"
        return "levels rise, nothing else does"

    @check("serving a power pleases its partisans and nobody else")
    def _():
        aligned = [c for c in CONVICTIONS if c.aligned
                   and f"{c.id}_served" in c.reacts]
        assert len(aligned) >= 2, [c.id for c in aligned]
        rows = []
        for conviction in aligned:
            game = new_game(f"serve-{conviction.id}")
            assert len(game.officers) >= 2, "need a bystander"
            game.officers[0].conviction = conviction.id
            game.officers[1].conviction = next(
                c.id for c in CONVICTIONS if c.id != conviction.id)
            before = {o.id: loyalty.loyalty_of(o) for o in game.officers}
            loyalty.served(game, conviction.aligned)
            after = {o.id: loyalty.loyalty_of(o) for o in game.officers}
            partisan = after[game.officers[0].id] - before[game.officers[0].id]
            bystander = after[game.officers[1].id] - before[game.officers[1].id]
            want = conviction.reacts[f"{conviction.id}_served"]
            assert abs(partisan - want) < 0.01, (
                f"{conviction.id}: felt {partisan:+.1f} for work done for "
                f"{conviction.aligned}, and declares {want:+.1f}")
            assert abs(bystander) < 0.01, (
                f"an officer who believes something else felt {bystander:+.1f}")
            rows.append(f"{conviction.id} {partisan:+.0f}")
        # And nobody is moved by a power nobody follows.
        game = new_game("nofaction")
        assert loyalty.served(game, None) == []
        return " · ".join(rows) + " · bystanders unmoved"

    @check("finishing a commission is what delivers it")
    def _():
        # End to end through `contracts._pay`, which is what completing work
        # actually calls — not `served` on its own.
        from ..core.rng import RNG
        from ..sim import contracts

        game = new_game("paid")
        conviction = next(c for c in CONVICTIONS if c.aligned
                          and f"{c.id}_served" in c.reacts)
        game.officers[0].conviction = conviction.id
        board = contracts.generate(RNG("paid"), game, game.system)
        job = next((c for c in board if c.issuer == conviction.aligned), None)
        if job is None:
            job = board[0]
            job.issuer = conviction.aligned
        before = loyalty.loyalty_of(game.officers[0])
        contracts._pay(game, job)
        after = loyalty.loyalty_of(game.officers[0])
        moved = after - before
        # At least the whole of what the conviction declares. `_pay` also
        # adjusts standing, which drags partisans along at a quarter rate via
        # `loyalty.align` — worth about +1.25 on its own, and enough to
        # satisfy a bare "it moved" assertion with `served` deleted entirely.
        want = conviction.reacts[f"{conviction.id}_served"]
        assert moved >= want - 0.01, (
            f"a commission for {conviction.aligned} moved its partisan "
            f"{moved:+.1f}, and {conviction.id} declares {want:+.0f} for it — "
            "that is standing dragging them, not the work")
        return (f"a {conviction.aligned} commission moves a {conviction.id} "
                f"officer {moved:+.1f}, declared {want:+.0f}")

    @check("an unpaid bridge still empties")
    def _():
        # The other half: none of this may quietly make loyalty toothless.
        game = new_game("broke")
        game.ship.morale = 0.2
        months = 0
        while game.officers and months < 36:
            loyalty.tick(game, 30, paid=False)
            months += 1
        assert not game.officers, (
            f"three years unpaid and {len(game.officers)} still aboard at "
            f"{[round(loyalty.loyalty_of(o)) for o in game.officers]}")
        assert months > 6, (
            f"the whole bridge walked in {months} months, which is not a "
            "slow burn, it is a trapdoor")
        assert WALKOUT < RESTLESS, (WALKOUT, RESTLESS)
        return f"unpaid, the last of them was gone after {months} months"
