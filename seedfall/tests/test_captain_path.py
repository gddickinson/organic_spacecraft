"""The captain's own life, played out rather than handed to them.

`sim/lifepath.py` already gave the captain a service record — terms, ranks,
a mishap, a muster-out — worked out from the origin they picked and an age
the game chose. That is a *biography*. Traveller's opening is not a
biography: it is one decision made four or five times, **another term or
out**, with the survival throw in front of you each time.

`sim/captain_path.py` is that decision. The claims:

- **The dice are the sector's, not the button's.** A term has the outcome it
  was always going to have; closing the dialog and opening it again does not
  shop for a better one. The choice is where to stop.
- **Only the decision is stored** — the service and the number of terms —
  and the record is derived by replaying, so a save carries two small fields
  and no history that could go stale.
- **The odds quoted are the odds thrown.** Preview equals act, as everywhere
  else in this game.
- **A mishap ends it**, and what is left is what they walk away with.
- **Skipping it changes nothing.** Every chronicle begun before this has the
  captain it always had.
- **And what was played is what the rest of the game reads** — the skills
  reach the checks that ask for them.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data import careers as table
from ..sim import afoot_people, beginning as beginning_sim
from ..sim import captain_path as path_sim
from ..sim import checks, lifepath
from .harness import Suite


def _played(game, service: str, terms: int):
    """Enlist and serve up to `terms`, stopping early at a mishap."""
    path = path_sim.begin(game, service)
    while path.terms < terms and path_sim.may_serve(path)[0]:
        path_sim.serve(path)
    path_sim.muster(path)
    return path


def run(suite: Suite) -> None:
    check = suite.check

    @check("a term has the outcome it was always going to have")
    def _():
        game = new_game("shopping")
        rows = []
        for service in [c.id for c in path_sim.services()][:4]:
            once = _played(game, service, 4)
            again = _played(game, service, 4)
            assert once.terms == again.terms, (service, once.terms)
            assert ([t.skill for t in once.record.terms]
                    == [t.skill for t in again.record.terms]), service
            assert (once.record.characteristics
                    == again.record.characteristics), service
            # And serving one at a time is the same life as serving four.
            step = path_sim.begin(game, service)
            for _n in range(4):
                if not path_sim.may_serve(step)[0]:
                    break
                path_sim.serve(step)
            assert ([t.skill for t in step.record.terms]
                    == [t.skill for t in once.record.terms]), service
            rows.append((service, once.terms))
        assert len(rows) >= 4, rows
        return ("four services played twice each and one term at a time, "
                "every throw identical: "
                + " · ".join(f"{s} {n}" for s, n in rows))

    @check("only the decision is stored, and the record is replayed from it")
    def _():
        import json

        from ..core.save import decode, encode
        game = new_game("stored-life")
        path = _played(game, "hauler", 3)
        path_sim.finish(path, game.beginning)
        assert game.beginning.service == "hauler"
        assert game.beginning.service_terms == path.terms
        # Nothing else went on: a save carries two fields, not a history.
        blob = json.dumps(encode(game))
        assert "service_terms" in blob
        back = decode(json.loads(blob))
        mine = afoot_people.captain_record(game)
        theirs = afoot_people.captain_record(back)
        assert mine.career_name == theirs.career_name, (mine, theirs)
        assert mine.skills == theirs.skills
        assert [t.skill for t in mine.terms] == [t.skill for t in theirs.terms]
        return (f"{mine.career_name}, {len(mine.terms)} terms and "
                f"{len(mine.skills)} skills, all of it off two saved fields")

    @check("the odds quoted are the odds thrown")
    def _():
        rows = 0
        for service in [c.id for c in path_sim.services()]:
            game = new_game(f"priced-{service}")
            path = path_sim.begin(game, service)
            while path_sim.may_serve(path)[0]:
                said = path_sim.odds(path)
                got = path_sim.serve(path)
                term = got["term"]
                # The throw the term actually made, against the forecast the
                # screen printed a moment earlier.
                assert term.survived is not None, term
                want = checks.chance(0, said["survive_score"],
                                     term.survived.how)
                assert abs(want - said["survive"]) < 1e-9, (want, said)
                rows += 1
                if got["over"]:
                    break
        assert rows >= 12, rows
        return (f"{rows} terms across every service, each one thrown at the "
                "chance the screen had already printed")

    @check("a mishap ends it, and they leave with what they have")
    def _():
        found = None
        for n in range(20):
            game = new_game(f"mishap-{n}")
            for service in [c.id for c in path_sim.services()]:
                path = path_sim.begin(game, service)
                while path_sim.may_serve(path)[0]:
                    got = path_sim.serve(path)
                    if got["mishap"]:
                        found = (service, path, got["mishap"])
                        break
                if found:
                    break
            if found:
                break
        assert found, "nobody was thrown out of anything in twenty sectors"
        service, path, mishap = found
        assert path.over, "the career carried on past the mishap"
        assert not path_sim.may_serve(path)[0]
        assert path.record.ended == mishap, (path.record.ended, mishap)
        assert path.record.skills, "they left with nothing at all"
        assert path_sim.odds(path) == {}, "a finished career is still pricing"
        return (f"{service}, term {path.terms}: {mishap[:60]} — and they "
                f"keep {len(path.record.skills)} skill(s)")

    @check("skipping it leaves the captain exactly as they were")
    def _():
        game = new_game("skipped")
        assert path_sim.played(game.beginning) == ("", 0)
        assert path_sim.record_for(game, game.beginning) is None
        before = afoot_people.captain_record(game)
        # The origin-derived captain, unchanged: this is what a chronicle
        # begun before any of this has, and it must keep having it.
        assert before.career_name and before.terms, before
        again = afoot_people.captain_record(game)
        assert before.skills == again.skills
        assert before.characteristics == again.characteristics
        return (f"no life played: the captain is still {before.career_name}, "
                f"{len(before.terms)} terms, {len(before.skills)} skills")

    @check("what was played is the captain the rest of the game reads")
    def _():
        game = new_game("is-read")
        path = _played(game, "drifter", 4)
        path_sim.finish(path, game.beginning)
        record = afoot_people.captain_record(game)
        assert record.career == "drifter", record.career
        assert record.station == "captain"
        assert record.name == afoot_people.captain_name(game)
        # The skills are the ones the checks ask for, and they reach them.
        for name, level in record.skills.items():
            assert record.skill(name) == level
        assert record.skill("nothing_like_this") == checks.UNTRAINED
        # And the thing that reads a captain's streetwise sees this one.
        from ..sim import patrons
        skill, score, who = patrons._skill(game)
        assert isinstance(skill, int) and isinstance(score, int)
        assert who, who
        return (f"a drifter of {len(record.terms)} terms is who the bridge "
                f"has; {len(record.skills)} skills reach the checks that "
                "ask for them")

    @check("a played captain can still fly the ship they bought")
    def _():
        """The ship goes on top of the life, whichever way the life came.

        A captain whose history is *derived* has always had the two things
        owning a starship gives anybody — a point of standing and enough
        command and stick to run their own hull. A played one returned
        early and got neither, so four terms in the Clinical Service bought
        you a captain who could not fly.
        """
        from ..sim.afoot_people import COMMAND
        rows = []
        for service in [c.id for c in path_sim.services()]:
            game = new_game(f"aboard-{service}")
            plain = afoot_people.captain_record(game).score("soc")
            path = _played(game, service, 2)
            path_sim.finish(path, game.beginning)
            record = afoot_people.captain_record(game)
            for name, level in COMMAND.items():
                assert record.skill(name) >= level, (service, name,
                                                     record.skill(name))
            # And the life underneath is still theirs: nothing was taken.
            for name, level in path.record.skills.items():
                assert record.skill(name) >= level, (service, name)
            # Standing is a characteristic and a drifter may well have
            # rolled a poor one; what owning the hull adds is the *point*,
            # not a floor.
            assert record.score("soc") == min(
                15, path.record.score("soc") + 1), (service,
                                                    record.score("soc"),
                                                    path.record.score("soc"))
            rows.append((service, record.score("soc"), plain))
        assert len(rows) >= 5, rows
        return (f"{len(rows)} played captains, every one of them holding "
                f"{', '.join(sorted(COMMAND))}, every skill their own life "
                "taught them, and one more point of standing for the hull")

    @check("nobody serves for ever, and every service will take a captain")
    def _():
        game = new_game("bounds")
        offered = path_sim.services()
        assert len(offered) >= 5, offered
        assert {c.id for c in offered} == set(table.CAREER_BY_ID), offered
        longest = 0
        for career in offered:
            path = path_sim.begin(game, career.id)
            for _n in range(path_sim.MOST_TERMS + 4):
                if not path_sim.may_serve(path)[0]:
                    break
                path_sim.serve(path)
            assert path.terms <= path_sim.MOST_TERMS, (career.id, path.terms)
            longest = max(longest, path.terms)
            ok, why = path_sim.may_serve(path)
            assert not ok and why, (career.id, ok, why)
        assert longest >= 2, longest
        return (f"{len(offered)} services, none of them serving past "
                f"{path_sim.MOST_TERMS} terms; the longest run was {longest}")

    @check("two services make two different captains")
    def _():
        game = new_game("different")
        made = {}
        for service in [c.id for c in path_sim.services()]:
            path = _played(game, service, 4)
            made[service] = (tuple(sorted(path.record.skills)),
                             path.record.rank)
        assert len(made) >= 5, made
        assert len(set(made.values())) >= len(made) - 1, made
        return (f"{len(made)} services, {len(set(made.values()))} distinct "
                "captains out of them")
