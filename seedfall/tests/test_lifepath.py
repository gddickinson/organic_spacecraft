"""Two dice and a life lived: Traveller's grammar, and the people it makes.

The claims:

- **The grammar is exact.** `checks.chance` is a count over all thirty-six
  outcomes, not an estimate, and it is the same arithmetic `checks.roll`
  uses — so a screen that quotes the odds before a button is pressed cannot
  quote something the roll will not honour. That is this project's
  *preview equals act* rule, applied to a die.
- **The ladder is a ladder.** Harder is harder, a skill is worth something,
  and being untrained is worse than being merely bad.
- **A record is a history, not a build.** Every officer comes out with a
  service, a rank, skills with levels, and things that happened to them —
  and the things that happened are not the same thing four times.
- **It is derived and stable.** Asked twice, in two processes, it answers the
  same, it costs the chronicle no luck, and it stores nothing.
"""

from __future__ import annotations

from collections import Counter

from ..core.rng import RNG
from ..core.state import new_game
from ..data import careers as table
from ..sim import checks
from ..sim import lifepath as life_sim
from .harness import Suite

#: How many officers to make before believing anything about the spread.
CROWD = ("life-a", "life-b", "life-c", "life-d", "life-e", "life-f")


def run(suite: Suite) -> None:
    check = suite.check

    @check("the odds a screen quotes are the odds the dice actually give")
    def _():
        rng = RNG("odds")
        for skill, score, how in ((0, 7, "average"), (2, 10, "difficult"),
                                  (-3, 4, "routine"), (1, 8, "formidable")):
            want = checks.chance(skill, score, how)
            hits = sum(1 for _n in range(4000)
                       if checks.roll(rng, skill, score, how).ok)
            got = hits / 4000
            assert abs(got - want) < 0.03, (skill, score, how, want, got)
        # Exact, not approximate: an average check with no modifiers is the
        # classic 8+ on 2d6, which is fifteen of thirty-six.
        assert abs(checks.chance(0, 7, "average") - 15 / 36) < 1e-9
        assert checks.chance(0, 7, "simple") > checks.chance(0, 7, "average")
        return (f"8+ on 2d6 is {checks.chance(0, 7):.1%}; four settings "
                "rolled four thousand times each, all within 3 points")

    @check("harder is harder, skill helps, and untrained is its own penalty")
    def _():
        ladder = [checks.chance(0, 7, cid)
                  for cid, _name, _dm in checks.DIFFICULTIES]
        assert ladder == sorted(ladder, reverse=True), ladder
        assert ladder[0] == 1.0, ladder[0]          # simple: cannot fail
        # A level of skill is worth about a sixth of the range at the middle.
        assert checks.chance(2, 7) > checks.chance(0, 7) > checks.chance(-3, 7)
        # Untrained is the floor however the caller spells it.
        assert checks.chance(-1, 7) == checks.chance(checks.UNTRAINED, 7)
        # And a characteristic is worth what the table says.
        assert checks.modifier(7) == 0 and checks.modifier(15) == 3
        assert checks.modifier(1) == -2 and checks.modifier(0) == -3
        # The Effect is the margin, and it is what turns a roll into a story.
        rng = RNG("effect")
        got = checks.roll(rng, 4, 12, "simple")
        assert got.ok and got.effect == got.total - checks.TARGET
        assert checks.Check(12, 4, 3, 6, 0).exceptional
        assert checks.Check(2, 0, -3, -6, 0).disaster
        return ("ladder " + " ".join(f"{c:.0%}" for c in ladder)
                + f"; untrained {checks.UNTRAINED:+d}")

    @check("every officer has a history, and it is a history and not a list")
    def _():
        seen, careers, skills, events = 0, Counter(), Counter(), 0
        deepest = 0
        for seed in CROWD:
            game = new_game(seed)
            for officer in game.officers:
                record = life_sim.of(game, officer)
                seen += 1
                assert record.terms, f"{officer.name} served nothing"
                assert record.career_name and record.rank, record
                assert record.ended, f"{officer.name} never left anything"
                assert record.age >= table.ENTRY_AGE, record.age
                careers[record.career] += 1
                for name, level in record.skills.items():
                    assert name in table.SKILLS, name
                    assert level >= 0, (name, level)
                    skills[name] += 1
                    deepest = max(deepest, level)
                # The same thing must not happen to somebody four times.
                told = [t.event for t in record.terms if t.event]
                assert len(told) == len(set(told)), told
                events += len(told)
                for cid in checks.CHARACTERISTIC_IDS:
                    assert 1 <= record.score(cid) <= 15, (cid, record)
        assert len(careers) >= 4, dict(careers)
        assert deepest >= 2, f"nobody in {seen} officers got past {deepest}"
        return (f"{seen} officers across {len(careers)} careers, "
                f"{len(skills)} skills, {events} events, deepest level "
                f"{deepest}")

    @check("a record is derived: same every time, and it costs no luck")
    def _():
        game = new_game("life-same")
        officer = game.officers[0]
        was = game.rng_seed
        first = life_sim.of(game, officer)
        again = life_sim.of(game, officer)
        assert game.rng_seed == was, "reading a record moved the chronicle"
        assert life_sim.says(first) == life_sim.says(again), "two histories"
        assert first.characteristics == again.characteristics
        assert first.skills == again.skills
        # A fresh game on the same seed makes the same person.
        twin = new_game("life-same")
        other = next(o for o in twin.officers if o.id == officer.id)
        third = life_sim.of(twin, other)
        assert third.skills == first.skills, (third.skills, first.skills)
        # And nothing was written to the officer.
        assert not any(f.startswith("life") or f.startswith("career")
                       for f in vars(officer)), sorted(vars(officer))
        return (f"{officer.name}: {first.career_name} {first.rank}, read "
                "three times the same and stored nowhere")

    @check("a history explains the job they hold")
    def _():
        """An engineer who came up through the Yards is a person; one whose
        past has nothing to do with engines is a die wearing a name."""
        fitting, seen = 0, 0
        for seed in CROWD:
            game = new_game(seed)
            for officer in game.officers:
                record = life_sim.of(game, officer)
                want = table.BY_STATION.get(officer.role, ())
                if not want:
                    continue
                seen += 1
                if record.career in want:
                    fitting += 1
        assert seen and fitting / seen >= 0.6, (fitting, seen)
        # And the fallback is a real career rather than a hole.
        for career in table.CAREERS:
            assert career.skills, career.id
            assert career.ranks, career.id
            assert career.mishaps and career.events, career.id
            assert career.qualify[0] in checks.CHARACTERISTIC_IDS, career.id
            assert career.survive[0] in checks.CHARACTERISTIC_IDS, career.id
            for name in career.skills + (career.officer_skills or ()):
                assert name in table.SKILLS, (career.id, name)
        for station, rows in table.BY_STATION.items():
            for cid in rows:
                assert cid in table.CAREER_BY_ID, (station, cid)
        return (f"{fitting} of {seen} officers came up through a service "
                f"their station draws from; {len(table.CAREERS)} careers all "
                "complete")

    @check("a career can throw somebody out, and the years take something")
    def _():
        mishaps, terms, aged = 0, 0, 0
        for seed in CROWD:
            game = new_game(seed)
            for officer in game.officers:
                record = life_sim.of(game, officer)
                terms += len(record.terms)
                mishaps += sum(1 for t in record.terms if t.mishap)
                if record.age > table.AGEING_FROM:
                    aged += 1
        assert mishaps, "nobody in the Verge ever had a career go wrong"
        assert mishaps < terms * 0.5, (mishaps, terms)
        # Ageing bites, and only after Traveller's own thirty-four.
        game = new_game("life-old")
        officer = game.officers[0]
        record = life_sim.of(game, officer)
        young = life_sim.Record(characteristics=dict(record.characteristics),
                                age=30)
        life_sim._age(young, RNG("young"), 3)
        assert young.characteristics == record.characteristics, (
            "the years took something off somebody who is thirty")
        return (f"{mishaps} mishaps over {terms} terms; {aged} officers past "
                f"{table.AGEING_FROM}")

    @check("the bridge can be asked who is best at something")
    def _():
        game = new_game("life-best")
        found = 0
        for name in ("engineer", "gunnery", "broker", "medic", "astrogation"):
            level, who = life_sim.skill_aboard(game, name)
            assert level >= checks.UNTRAINED, (name, level)
            if who is not None:
                found += 1
                assert life_sim.of(game, who).skill(name) == level
        assert found, "nobody aboard is trained in anything at all"
        # A retired officer is not aboard.
        for officer in game.officers:
            officer.retired = True
        level, who = life_sim.skill_aboard(game, "engineer")
        assert who is None and level == checks.UNTRAINED, (level, who)
        return f"{found} of 5 skills held by somebody on the bridge"

    @check("the screens print who they were before the berth")
    def _():
        from PyQt6.QtWidgets import QLabel
        from .qtkit import app as _app
        from .qtkit import main_window
        keep = _app()
        game = new_game("life-ui")
        win = main_window(game, (1360, 880))
        officer = next(o for o in game.officers if not o.retired)
        record = life_sim.of(game, officer)

        def said_on(screen: str, tab: str) -> str:
            win.go(screen)
            view = win.views[screen]
            view.tab = tab
            view.refresh()
            for _ in range(4):
                keep.processEvents()
            return " ".join(lab.text() for lab in view.findChildren(QLabel)
                            if lab.text())

        # The service belongs to both: the Ship screen's Crew tab names it
        # beside the story, and the whole sheet is the Crew screen's.
        ship = said_on("ship", "crew")
        assert record.career_name in ship, (
            f"{officer.name}'s service is not on the Ship screen's Crew tab")
        win.views["crew"].open_sheet(officer)
        sheet = said_on("crew", "sheet")
        assert record.career_name in sheet, "no service on the sheet"
        assert "STR" in sheet and "SOC" in sheet, "no characteristics shown"
        assert record.rank in sheet, "no rank on the sheet"
        win.close()
        keep.processEvents()
        return (f"{officer.name} reads as {record.career_name} "
                f"{record.rank} on both screens")
