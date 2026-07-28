"""Field-note checks — what the ground told you has to survive the flight home.

A recovered note was a string in `expedition.lore`, printed once in the report
dialog and thrown away with the expedition object. It never reached the `Game`,
never appeared in the codex, and `REWARD_SCALE["lore"]` was (0, 0), so finding
one granted nothing whatever. Three feature options across two features existed
only to show a sentence and take it away again, and eight written discoveries
sat in the data where no player could ever read them twice — under a comment
calling them "the reason anyone reads an expedition report twice".
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.fieldnotes import NOTES, NOTES_BY_ID
from ..data.inquiry import EVIDENCE_BY_ID
from ..sim import expedition as exp_sim
from ..sim import fieldwork
from ..sim import inquiry
from ..sim import notes as notes_sim
from .harness import Suite


def _landed(seed: str):
    """A game with a party on the ground somewhere landable."""
    game = new_game(seed)
    body = next(b for s in game.galaxy.systems for b in s.bodies
                if b.kind not in ("gas", "star"))
    system = next(s for s in game.galaxy.systems if body in s.bodies)
    game.location_id = system.id
    rng = RNG(f"n-{seed}")
    party = exp_sim.generate(rng, system, body,
                             [o.id for o in game.officers], 40)
    game.expedition = party
    return game, party, rng


def _read_the_room(game, party, rng, times: int = 14) -> list[str]:
    """Work a wreck repeatedly for its notes."""
    index = None
    for _ in range(times):
        party.here.feature = "wreck"
        party.here.resolved = False
        if index is None:
            index = next(i for i, o in enumerate(exp_sim.options_here(party))
                         if o[3] == "lore")
        exp_sim.attempt(party, index, game.officers, rng)
    return list(party.lore)


def run(suite: Suite) -> None:
    check = suite.check

    @check("every note is coherent and is evidence of something")
    def _():
        assert NOTES, "there are no field notes at all"
        seen = set()
        for note in NOTES:
            assert note.id not in seen, f"duplicate note id {note.id}"
            seen.add(note.id)
            assert note.title and note.text, f"{note.id} says nothing"
            assert note.evidence in EVIDENCE_BY_ID, (
                f"{note.id} is evidence of {note.evidence!r}, which is not a "
                "track the bench recognises")
            assert note.worth > 0, f"{note.id} is worth nothing to anybody"
        tracks = {n.evidence for n in NOTES}
        assert len(tracks) >= 2, f"every note feeds the same track: {tracks}"
        return (f"{len(NOTES)} notes across {len(tracks)} evidence tracks, "
                f"{sum(n.worth for n in NOTES):g} points in all")

    @check("a note found in the field is still there when you get home")
    def _():
        # The whole bug: it used to be printed once and dropped with the
        # expedition object, which recovery sets to None.
        game, party, rng = _landed("survives")
        found = _read_the_room(game, party, rng)
        assert found, "no notes came up in fourteen attempts at a wreck"
        exp_sim.finish(party, "returned")
        out = fieldwork.conclude_expedition(game)
        assert game.expedition is None, "the party is still down there"
        assert out["notes"], "the report mentions no notes"
        kept = {f.note_id for f in notes_sim.held(game)}
        assert kept == set(found), f"filed {kept}, found {set(found)}"
        for filed in notes_sim.held(game):
            assert filed.body and filed.system, "filed with no provenance"
            assert filed.definition is not None, f"{filed.note_id} is unreadable"
        return f"{len(kept)} note(s) filed with where and when"

    @check("bringing one home counts on the bench")
    def _():
        game, party, rng = _landed("evidence")
        note = NOTES[0]
        before = inquiry.held(game.research, note.evidence)
        banked = game.research.banked
        res = notes_sim.file(game, note.id, "Somewhere", "Some system")
        assert res["ok"], res.get("why")
        after = inquiry.held(game.research, note.evidence)
        assert after > before, (
            f"{note.evidence} evidence did not move: {before} → {after}")
        assert abs((after - before) - note.worth) < 0.01, (
            f"worth {note.worth}, banked {after - before}")
        assert game.research.banked > banked, "no research came of it"
        return (f"{note.worth:g} points of "
                f"{EVIDENCE_BY_ID[note.evidence].name.lower()}, and research")

    @check("the same note is not filed twice, but still reads for something")
    def _():
        game, party, rng = _landed("dup")
        note = NOTES[1]
        first = notes_sim.file(game, note.id, "A", "B")
        held_after_first = len(notes_sim.held(game))
        before = inquiry.held(game.research, note.evidence)
        second = notes_sim.file(game, note.id, "C", "D")
        assert not first["duplicate"] and second["duplicate"]
        assert len(notes_sim.held(game)) == held_after_first, (
            "the same note was shelved twice")
        gained = inquiry.held(game.research, note.evidence) - before
        assert 0 < gained < note.worth, (
            f"a corroborating read gave {gained} against {note.worth} fresh")
        return f"{note.worth:g} the first time, {gained:g} the second"

    @check("every note is reachable, and the draw prefers new ones")
    def _():
        game, party, rng = _landed("reach")
        seen = set()
        for index in range(400):
            note = notes_sim.draw(game, RNG(f"draw-{index}"))
            seen.add(note.id)
            if len(seen) == len(NOTES):
                break
        assert seen == {n.id for n in NOTES}, (
            f"notes that never come up: {sorted({n.id for n in NOTES} - seen)}")

        # With all but one shelved, the draw must offer the one that is left.
        for note in NOTES[:-1]:
            notes_sim.file(game, note.id, "A", "B")
        assert notes_sim.unfound(game) == [NOTES[-1]]
        drawn = {notes_sim.draw(game, RNG(f"last-{i}")).id for i in range(20)}
        assert drawn == {NOTES[-1].id}, (
            f"the draw still offers notes already on the shelf: {drawn}")
        return f"all {len(NOTES)} reachable; the draw prefers what you lack"

    @check("a stranded party loses the cargo, not what they read")
    def _():
        # Stranding costs 60% of the haul. A thing somebody read and remembered
        # is not cargo and should not fall out of a rucksack.
        game, party, rng = _landed("stranded")
        found = _read_the_room(game, party, rng)
        assert found
        exp_sim.finish(party, "stranded")
        fieldwork.conclude_expedition(game)
        kept = {f.note_id for f in notes_sim.held(game)}
        assert kept == set(found), (
            f"stranding cost them what they had already read: {kept}")
        return f"{len(kept)} note(s) home despite being stranded"

    @check("the shelf survives being put down")
    def _():
        import os
        import tempfile

        from ..core import save as save_mod
        from ..core.state import load_game

        game, party, rng = _landed("resume")
        _read_the_room(game, party, rng)
        exp_sim.finish(party, "returned")
        fieldwork.conclude_expedition(game)
        before = [(f.note_id, f.body, f.system, f.day)
                  for f in notes_sim.held(game)]
        assert before, "nothing to save"

        os.environ["HOME"] = tempfile.mkdtemp()
        save_mod.write({"game": game})
        back = load_game()
        after = [(f.note_id, f.body, f.system, f.day)
                 for f in notes_sim.held(back)]
        assert after == before, f"{after} != {before}"
        assert notes_sim.summary(back)["held"] == len(before)
        return f"{len(before)} note(s), with provenance, came back"

    @check("nothing in the data is unreachable from the ground")
    def _():
        # A note nobody can find is a note nobody wrote. Which features offer
        # the reward at all is the thing that decides it.
        from ..data.expedition import FEATURES
        sources = [f.id for f in FEATURES.values()
                   if any(o[3] == "lore" for o in f.options)]
        assert sources, "no feature in the game yields a field note"
        summary = notes_sim.summary(new_game("counts"))
        assert summary["total"] == len(NOTES)
        assert summary["held"] == 0, "a new chronicle starts with notes filed"
        return (f"{len(sources)} feature(s) yield notes: {', '.join(sources)}")
