"""Afoot in a career: counsel, the Academy, renown, the captain, and what a walk meets.

- **counsel** suggests the dead hull adrift and the officer nobody has had a
  word with, and its act puts the party on the deck;
- **the Academy** has a course on foot, and the sim records each lesson;
- **renown** reads a career on foot, and the captain's record is a life
  played out like any officer's;
- **the Kith sing, and are answered** — the lexicon learned a sign at a
  time — and **a relic gives itself up in stages**;
- **trouble**: a quarrel aboard, a shakedown, a brawl, and your own works
  failing, striking or sabotaged — each met head on, each let be, and a
  holding's yield moved by what was done.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data import afoot_incidents as incident_table
from ..data.lessons import CHAPTERS_BY_ID, lessons_in
from ..sim import (afoot, afoot_deeds, afoot_holdings, afoot_kith,
                   afoot_people, afoot_trouble, checks, counsel, counsel_doors,
                   places, tutorial_watch)
from ..sim.afoot_state import Thing, party, uid
from . import afoot_kit, kith_kit
from .harness import Suite


def _out(game, kind="ship", keys=("captain",)):
    site = next(s for s in afoot.sites(game) if s.kind == kind and s.ok)
    assert afoot.begin(game, site.key, list(keys))["ok"]
    return game.afoot


def run(suite: Suite) -> None:
    check = suite.check

    @check("counsel names a dead hull to board and an officer to see, and its act walks")
    def _():
        game, site = afoot_kit.at_wreck(("raider_hulk",))
        ids = {s["id"]: s for s in counsel_doors.afoot(game)}
        assert "afoot:wreck" in ids, ids
        officer = game.officers[0]
        officer.loyalty = counsel_doors.WORD_LOYALTY - 10
        game.day += counsel_doors.WORD_OVERDUE + 1
        word = next((s for s in counsel_doors.afoot(game)
                     if s["id"] == "afoot:word"), None)
        assert word is not None and officer.name in word["title"], word
        got = counsel.act(game, ids["afoot:wreck"])
        assert got["ok"], got
        assert game.afoot is not None and game.afoot.kind == "wreck"
        return f"board “{ids['afoot:wreck']['title']}”; {word['title']}"

    @check("the Academy has a course on foot, and the sim records each lesson")
    def _():
        chapter = CHAPTERS_BY_ID["afoot"]
        lessons = lessons_in("afoot")
        assert [l.watch for l in lessons] == ["walked", "talked_afoot",
                                               "fought_afoot"], lessons
        game = afoot_kit.fresh("career-lessons")
        walk = _out(game, "port")
        assert tutorial_watch.did(game, "walked")
        me = party(walk)[0]
        other = next(a for a in walk.actors if a.side == "npc"
                     and a.standing and a.mood != "hostile")
        other.deck, other.x, other.y = me.deck, me.x + 1, me.y
        afoot.talk(game, me.id, other.id, "greet")
        assert tutorial_watch.did(game, "talked_afoot")
        other.mood = "hostile"
        me.weapon = "shotgun"
        afoot.attack(game, me.id, other.id)
        assert tutorial_watch.did(game, "fought_afoot")
        return f"“{chapter.title}”: {', '.join(l.title for l in lessons)}"

    @check("renown reads a career on foot, and the captain has lived a life")
    def _():
        game = afoot_kit.fresh("career-renown")
        walk = _out(game)
        afoot.act(game, party(walk)[0].id, "leave",
                  next(t.id for t in walk.things
                       if t.kind in ("airlock", "gangway")))
        if game.afoot is not None:
            from ..sim import afoot_ends
            afoot_ends.leave(game, walk)
        said = afoot.progress(game)
        assert said["walks"] >= 1 and said["kinds"] >= 1, said
        life = afoot_people.captain_record(game)
        again = afoot_people.captain_record(game)
        assert life.terms and life.career_name and life.rank, life
        assert life.skills == again.skills, "the captain lived twice"
        assert life.skills.get("leadership", -3) >= 1, life.skills
        return (f"{said['walks']} walk on the tally; the captain: "
                f"{len(life.terms)} terms in {life.career_name}")

    @check("the Kith sing a phrase, and answered it is learned")
    def _():
        game = kith_kit.at_gathering("career-kith")
        game.orbit_body = next(p.body_id for p in places.in_system(game)
                               if p.kind == "port")
        walk = _out(game, "kith")
        me = party(walk)[0]
        kith = next(a for a in walk.actors if a.folk in ("kith", "kith_elder"))
        afoot_kith.on_sing(game, walk, me, kith, None, RNG("sing"))
        sign = kith.note.split(":")[-1]
        from ..sim import kith as kith_sim
        kith_sim.ensure(game).lexicon.clear()
        hard = afoot_kith.difficulty(game, kith)
        kith_kit.fluent(game, afoot_kith.EASY_AT)
        assert (hard, afoot_kith.difficulty(game, kith)) == (
            "very_difficult", "average"), hard
        kith_sim.ensure(game).lexicon[sign] = 0.2
        before = kith_sim.comprehension(game, sign)
        for n in range(80):
            got = afoot_kith.on_answer(game, walk, me, kith, None,
                                       RNG(f"answer:{n}"))
            if got["check"].ok:
                break
        assert got["check"].ok, "no answer ever landed"
        assert kith_sim.comprehension(game, sign) > before
        return (f"very difficult to a stranger, average to the fluent; "
                f"“{sign}” from {before:.0%} to "
                f"{kith_sim.comprehension(game, sign):.0%}")

    @check("a relic gives itself up in three stages, and the sentries stand down")
    def _():
        game = afoot_kit.fresh("career-relic")
        walk = _out(game)
        me = party(walk)[0]
        relic = Thing(id=uid(walk), kind="relic", deck=me.deck, x=me.x + 1,
                      y=me.y, holds=["study:30"], name="the relic")
        walk.things.append(relic)
        sentry = next(a for a in walk.actors if a.side == "npc")
        sentry.folk, sentry.deck, sentry.mood = "sentry", me.deck, "hostile"
        stages = []
        for _n in range(600):
            me.acted, walk.mode = False, "calm"
            got = afoot.act(game, me.id, "study", relic.id)
            if got.get("stage"):
                stages.append(got["stage"])
            if relic.state == "attuned":
                break
        assert relic.state == "attuned", (relic.state, stages)
        assert sentry.mood == "surrendered", sentry.mood
        # What it was for is very difficult: past an untrained captain, so
        # it is read here by a trained xenologist's roll.
        roll = next(r for n in range(200) for r in [checks.roll(
            RNG(f"relic:{n}"), 3, 12, "very_difficult", 1)] if r.ok)
        got = afoot_deeds._relic(game, walk, me, relic, roll)
        stages.append(got["stage"])
        assert relic.state == "studied" and not relic.holds, relic
        assert walk.found["study"]["relic"] > 30 * 3.5, walk.found["study"]
        return (" → ".join(stages)
                + f", {walk.found['study']['relic']:.0f} of study banked")

    @check("a quarrel, a shakedown and a brawl are met or let be, and it tells")
    def _():
        game = afoot_kit.fresh("career-trouble")
        for officer, creed in zip(game.officers[:2], ("licence", "purist")):
            officer.conviction = creed          # they differ over a parley
        walk = _out(game)
        pair = afoot_trouble._pair(game, walk)
        assert pair is not None, "two clashing officers, and no quarrel"
        if not any(a.incident == "quarrel" for a in walk.actors):
            assert afoot_trouble.spawn(game, walk, None, "quarrel", RNG("q"))
        officers = [afoot_people.officer_of(game, a.officer)
                    for a in walk.actors if a.incident == "quarrel"]
        before = [o.loyalty for o in officers]
        afoot_trouble.left(game, walk)
        assert len(officers) == 2 and all(
            o.loyalty < w for o, w in zip(officers, before)), officers
        game.afoot = None
        game = new_port_at_law(0)
        walk = _out(game, "port")
        site = next(s for s in afoot.sites(game) if s.kind == "port")
        assert afoot_trouble.spawn(game, walk, site, "shakedown", RNG("s"))
        hard = next(a for a in walk.actors if a.incident == "shakedown")
        hard.talked.append("hailed")
        for _n in range(afoot_trouble.PATIENCE + 1):
            afoot_trouble.tick(game, walk)
        assert hard.mood == "hostile", hard.mood
        assert afoot_trouble.spawn(game, walk, site, "brawl", RNG("b"))
        drunk = next(a for a in walk.actors if a.incident == "brawl")
        game.credits = 1_000
        from ..sim.afoot_talk import Topic
        afoot_trouble.on_round(game, walk, party(walk)[0], drunk,
                               Topic("round", "", cost=30), RNG("r"))
        assert drunk.mood == "friendly" and not drunk.incident
        return ("an unsettled quarrel cost both of them; an ignored toll "
                "came for it; a round ended a brawl")

    @check("your own works fail, strike and are sabotaged — and the yield moves")
    def _():
        game = afoot_kit.settle(afoot_kit.fresh("career-works"))
        site = next(s for s in afoot.sites(game)
                    if s.kind == "holding" and s.mine)
        assert afoot.begin(game, site.key, ["captain"])["ok"]
        walk = game.afoot
        colony = afoot_holdings.colony_of(game, walk)
        assert colony is not None
        assert afoot_holdings.spawn(game, walk, site, "strike", RNG("w"))
        afoot_holdings.resolved(game, walk, "strike")
        up = afoot_holdings.factor(game, colony)
        assert afoot_holdings.spawn(game, walk, site, "breakdown", RNG("x"))
        afoot_holdings.left(game, walk)
        down = afoot_holdings.factor(game, colony)
        game.day += incident_table.WORKS_DAYS + 1
        after = afoot_holdings.factor(game, colony)
        assert up > 1.0 > down and after == 1.0, (up, down, after)
        return (f"set right, the works run at {up:.2f}; left, {down:.2f}; "
                "a month on, as they were")


def new_port_at_law(law: int):
    """A chronicle standing at a quay whose law has been read as `law`."""
    game = afoot_kit.fresh(f"career-lawless-{law}")
    from ..sim import afoot_sites
    real = afoot_sites._from_place

    def lawless(g, place):
        from dataclasses import replace
        return replace(real(g, place), law=law)
    afoot_sites._from_place = lawless
    try:
        afoot.sites(game)
    finally:
        afoot_sites._from_place = real
    return game
