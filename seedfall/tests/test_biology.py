"""What you can make sense of on the ground.

`Lifeform.metabolism` was the identity key behind the two strings the survey
screens print, and **nothing read the key itself** — so a radiotroph and a
photoautotroph were the same row with different words, the catalogue could not
group by anything, and nothing asked whether the captain had any business
understanding what they were looking at. `test_declared` carried it on the allowed
list with the reason: *"a catalogue that groups by metabolism is wanted and the
tech tree has a branch of that name to match against."*

The pairing is not invented. Each of the eight biochemistries is matched to the
node that *is* that biochemistry, which the tree's own names give away — the
Sabatier Loop makes methane, trehalose vitrification is cryptobiosis, Deinococcus
is the radiation organism, piezolyte physiology is what a piezophile has.

The claims, all measured by surveying bodies rather than by reading the table:

- **A specimen is worth more to somebody who can read it**, and the arithmetic is
  in one place, so what a screen quotes is what the bench banks.
- **The tree decides**, and two of eight biochemistries are legible on day one —
  the mechanic is neither off nor already won at the start.
- **A survey grants what the catch is worth**, not what the body holds.
- **The catalogue groups by metabolism** and only counts what you catalogued.
- **A body plan is not a biochemistry**: `FORMS` names shapes, and one entry used
  to name a metabolism, which the metabolism field then contradicted.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.lifeforms import (FORMS, METABOLISM_TECH, METABOLISMS,
                              UNDERSTOOD_WORTH)
from ..data.tech import TECH_BY_ID
from ..sim import biology
from ..world.planets import survey_body
from .harness import Suite

#: Words that name a biochemistry rather than a body plan.
CHEMISTRY_STEMS = ("troph", "chemo", "photo", "thermo", "halo", "piezo",
                   "methano", "crypto", "radio")


def _surveyed(seed: str, systems: int = 9, quality: float = 0.9):
    """A chronicle with a stretch of the sector actually catalogued."""
    game = new_game(seed)
    rng = game.rng("catalogue")
    for system in game.galaxy.systems[:systems]:
        for body in system.bodies:
            survey_body(body, quality, rng)
    return game


def _all_biology(game) -> None:
    game.research.unlocked = list(set(game.research.unlocked)
                                 | set(METABOLISM_TECH.values()))


def run(suite: Suite) -> None:
    check = suite.check

    @check("every biochemistry is matched to the technology that explains it")
    def _():
        missing = [m for m, *_ in METABOLISMS if m not in METABOLISM_TECH]
        assert not missing, (
            f"{missing} have no technology to explain them, so nothing the "
            "captain learns will ever make them legible")
        bad = {m: tid for m, tid in METABOLISM_TECH.items()
               if tid not in TECH_BY_ID}
        assert not bad, f"pairings naming a technology that does not exist: {bad}"
        stray = set(METABOLISM_TECH) - {m for m, *_ in METABOLISMS}
        assert not stray, f"pairings for biochemistries that do not exist: {stray}"

        # And the pairing is one-to-one: two metabolisms explained by one node
        # would make a single result legible for two unrelated things.
        techs = list(METABOLISM_TECH.values())
        assert len(set(techs)) == len(techs), (
            f"a technology explains more than one biochemistry: {techs}")
        return (f"{len(METABOLISMS)} biochemistries, each with its own node — "
                + ", ".join(f"{m}→{TECH_BY_ID[t].name}"
                            for m, t in list(METABOLISM_TECH.items())[:3])
                + ", …")

    @check("a specimen is worth more to somebody who can read it")
    def _():
        game = _surveyed("bio-worth")
        rows = biology.catalogue(game)
        assert rows, "nothing was catalogued, so there is nothing to price"
        blind = [row for row in rows if not row["understood"]]
        assert blind, (
            "every biochemistry in this sector is already legible, so the "
            "difference cannot be measured")

        specimen = blind[0]["rows"][0]["lifeform"]
        before = biology.worth(game, specimen)
        assert not biology.understood(game, specimen)
        _all_biology(game)
        after = biology.worth(game, specimen)
        assert biology.understood(game, specimen)
        assert after > before, (
            f"{specimen.name} was worth {before} unread and {after} read")
        assert abs(before - round(after * UNDERSTOOD_WORTH)) <= 1, (
            f"unread is {before} against {after} read; the share is "
            f"{UNDERSTOOD_WORTH}")
        return (f"{specimen.metabolism_name}: {before} points unread, "
                f"{after} once the bench can read it")

    @check("the tree decides, and the start is neither blind nor finished")
    def _():
        game = new_game("bio-start")
        legible = [m for m, *_ in METABOLISMS
                   if biology.known_tech(game, METABOLISM_TECH[m])]
        assert 1 <= len(legible) < len(METABOLISMS), (
            f"{len(legible)} of {len(METABOLISMS)} biochemistries are legible "
            "on day one; the mechanic is either off or already won")
        # The dear ones are the exotic ones, which is what makes researching
        # them a decision rather than a formality.
        costs = {m: TECH_BY_ID[METABOLISM_TECH[m]].cost for m, *_ in METABOLISMS}
        worst = max(costs.values())
        assert worst > 500, (
            f"the dearest biochemistry costs {worst} points; none of this is "
            "worth saving up for")
        for m in legible:
            assert costs[m] <= 200, (
                f"{m} is legible on day one and costs {costs[m]} points, which "
                "is not a starting technology")
        # And each explanation names the node and its price, so the player can
        # see what it would take.
        game2 = _surveyed("bio-words", systems=4)
        said = set()
        for row in biology.catalogue(game2):
            for found in row["rows"]:
                said.add(biology.explain(game2, found["lifeform"]))
        assert len(said) >= 3, said
        for line in said:
            assert "explains it" in line or "would, at" in line, line
        return (f"{len(legible)} of {len(METABOLISMS)} legible at the start; "
                f"the dearest is {worst:,} points")

    @check("a survey grants what the catch is worth to this captain")
    def _():
        # The research for catalogued life used to be added inside
        # `world/planets.survey_body`, a layer that cannot ask who is looking.
        # Now the sim prices the catch, so the same body pays two captains
        # differently — and the same captain the same amount every time.
        from ..sim import survey as survey_sim
        blind_total = read_total = 0
        for seed in ("bio-catch-a", "bio-catch-b"):
            for learned in (False, True):
                game = new_game(seed)
                if learned:
                    _all_biology(game)
                body = next((b for s in game.galaxy.systems for b in s.bodies
                             if b.lifeforms), None)
                assert body is not None
                game.location_id = next(s.id for s in game.galaxy.systems
                                        if body in s.bodies)
                got = survey_body(body, 0.95, game.rng("catch"))
                catch = biology.harvest(game, got["lifeforms"])
                assert catch["count"] == len(got["lifeforms"])
                assert catch["read"] + len(catch["blind"]) == catch["count"]
                if learned:
                    read_total += catch["research"]
                    assert not catch["blind"]
                else:
                    blind_total += catch["research"]
        assert read_total > blind_total, (
            f"the same bodies paid {blind_total} to a captain who could not "
            f"read them and {read_total} to one who could")
        assert survey_sim is not None
        return (f"the same catch: {blind_total} points unread against "
                f"{read_total} read")

    @check("the catalogue groups what you catalogued, and nothing else")
    def _():
        game = _surveyed("bio-group")
        rows = biology.catalogue(game)
        told = biology.summary(game)
        assert rows and told["found"] > 5, told

        # One group per biochemistry, no duplicates, deepest first.
        keys = [row["metabolism"] for row in rows]
        assert len(set(keys)) == len(keys), keys
        sizes = [len(row["rows"]) for row in rows]
        assert sizes == sorted(sizes, reverse=True), sizes
        assert told["found"] == sum(sizes)
        assert told["read"] + told["blind"] == told["found"]

        # Only catalogued organisms, which is what makes the catalogue proof of
        # where you have been rather than a list of what exists.
        listed = {id(row["lifeform"]) for group in rows for row in group["rows"]}
        for system in game.galaxy.systems:
            for body in system.bodies:
                for lifeform in body.lifeforms or ():
                    if lifeform.catalogued:
                        assert id(lifeform) in listed, (
                            f"{lifeform.name} is catalogued and not in the "
                            "catalogue")
                    else:
                        assert id(lifeform) not in listed, (
                            f"{lifeform.name} is in the catalogue and was never "
                            "catalogued")
        fresh = biology.summary(new_game("bio-empty"))
        assert fresh["found"] == 0 and fresh["kinds"] == 0, fresh
        return (f"{told['found']} organisms in {told['kinds']} groups, deepest "
                f"first, {told['blind']} of them unread")

    @check("the line naming a technology spells it the way the tree does")
    def _():
        # **Found by looking at the screen.** The biota line was built with
        # `explain(...).capitalize()`, and `str.capitalize()` lower-cases
        # everything after the first character — so "Mineral Gut would, at 320
        # points" was printed as "mineral gut would", a technology's name in
        # lower case on the screen that is telling you to go and research it.
        from ..ui.survey_panel import _sentence

        game = _surveyed("bio-caps", systems=6)
        rows = biology.catalogue(game)
        assert rows, "nothing catalogued"
        checked = 0
        for group in rows:
            tech = group["tech"]
            for found in group["rows"]:
                line = _sentence(biology.explain(game, found["lifeform"]))
                assert line[:1].isupper(), line
                if tech is not None:
                    assert tech.name in line, (
                        f"{line!r} does not spell {tech.name!r} as the tree "
                        "does")
                    checked += 1
        assert checked > 5, checked
        return (f"{checked} lines, every technology named exactly as "
                "`data/tech.py` spells it")

    @check("a body plan is not a biochemistry")
    def _():
        # **Found by grouping.** `FORMS` is a pool of shapes and habits, and one
        # entry was "chemotrophic reef" — so the generator, which picks the form
        # and the metabolism independently, cheerfully filed a chemotrophic reef
        # as a photoautotroph. Invisible until the catalogue put the two beside
        # each other, and then a contradiction printed on the screen.
        claims = {form: [stem for stem in CHEMISTRY_STEMS if stem in form]
                  for form in FORMS}
        bad = {form: hit for form, hit in claims.items() if hit}
        assert not bad, (
            f"{len(bad)} body plan(s) name a biochemistry instead of a shape: "
            f"{bad} — the metabolism is its own field, and the generator picks "
            "the two independently")
        assert len(FORMS) > 10, len(FORMS)
        return f"{len(FORMS)} body plans, none of them claiming a biochemistry"
