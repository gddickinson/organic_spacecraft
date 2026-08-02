"""The captain's own enemies: a mark that lasts, and is read in one place.

Hostility was derived and only derived. `sim/traffic` built every hull with
`hostile=ERRANDS[errand][2]` — a raider is hostile, a freighter is not — so the
game had an opinion about who your enemies were and the captain had none.

The two things this has to get right are both about *one door*. The mark cannot
live on a `Contact` or a `Hull`, because both are rebuilt from nothing on every
call; and the captain's mark and the errand's answer have to meet in exactly one
place, or a chart and a board will disagree about the same ship.
"""

from __future__ import annotations

from ..core.state import load_game, new_game
from ..sim import hostiles as hostiles_sim
from ..sim import track as track_sim
from ..sim import traffic as traffic_sim
from .harness import Suite


def _a_hull(game):
    return next(c for c in track_sim.contacts(game) if c.kind == "hull")


def run(suite: Suite) -> None:
    check = suite.check

    @check("a mark outlives the contact it was put on")
    def _():
        # `track.contacts` and `traffic.in_system` rebuild their objects every
        # call — that is what makes the Kestrel you hailed yesterday the same
        # Kestrel today. Setting `hostile` on one would last until the next
        # redraw, which is why the mark is on the chronicle instead.
        game = new_game("hostile")
        hull = _a_hull(game)
        assert not hull.hostile, f"{hull.name} starts hostile; pick another seed"

        assert hostiles_sim.mark(game, hull.hull_id) is True
        assert hostiles_sim.mark(game, hull.hull_id) is False, "marked twice"

        # A *fresh* contact, built after the mark, carries it.
        again = next(c for c in track_sim.contacts(game)
                     if c.hull_id == hull.hull_id)
        assert again is not hull, "the fixture handed back the same object"
        assert again.hostile, (
            f"{again.name} was marked and a newly built contact says "
            f"hostile={again.hostile}")
        assert again.tint == "warn", (
            f"a marked hull is drawn as {again.tint!r}, not as trouble")

        assert hostiles_sim.clear(game, hull.hull_id) is True
        assert hostiles_sim.clear(game, hull.hull_id) is False
        back = next(c for c in track_sim.contacts(game)
                    if c.hull_id == hull.hull_id)
        assert not back.hostile, "the mark could not be taken off"
        return f"{hull.name} marked, rebuilt hostile, and cleared again"

    @check("the mark and the errand meet in one place, so every screen agrees")
    def _():
        # If the two answers met anywhere but `traffic`, some readers would
        # see the mark and others would not. These are the readers that
        # matter, asked directly rather than through the screen that shows
        # them: `hostiles()`, the readiness board, and the mesh count.
        from ..sim import readiness as readiness_sim
        game = new_game("hostile")
        hull = _a_hull(game)
        was = [h.name for h in traffic_sim.hostiles(game)]
        assert hull.name not in was, was

        hostiles_sim.mark(game, hull.hull_id)
        now = [h.name for h in traffic_sim.hostiles(game)]
        assert hull.name in now, (
            f"{hull.name} is marked and traffic.hostiles says {now}")

        board = readiness_sim.board(game) if hasattr(readiness_sim, "board") \
            else None
        if board:
            row = next((r for r in board if r["name"] == hull.name), None)
            assert row is not None and row["hostile"], (
                f"the readiness board does not read {hull.name} as hostile")
            # Hostiles sort to the top, which is the whole point of the board.
            assert board[0]["hostile"], "a hostile hull is not at the top"

        # And the summary line a screen prints counts her.
        said = traffic_sim.summary(game)
        assert any(ch.isdigit() for ch in said), said
        return (f"traffic.hostiles {was} -> {now}; the board and the summary "
                f"follow from the same door")

    @check("a marked enemy is still an enemy after the chronicle is reloaded")
    def _():
        # A player act that does not survive a save is a player act the game
        # forgot. `Grudges` is registered with `core/save` like every other
        # stored state.
        game = new_game("hostile")
        hull = _a_hull(game)
        hostiles_sim.mark(game, hull.hull_id)
        assert game.save() is True, "the chronicle would not save"

        back = load_game()
        assert back is not None, "the chronicle would not load"
        assert type(back.hostiles_state).__name__ == "Grudges", (
            f"the mark came back as {type(back.hostiles_state).__name__}")
        assert hostiles_sim.marked(back) == [hull.hull_id], (
            f"marks after loading: {hostiles_sim.marked(back)}")
        rebuilt = next(c for c in track_sim.contacts(back)
                       if c.hull_id == hull.hull_id)
        assert rebuilt.hostile, f"{hull.name} came back friendly"

        # An older save with no such state still opens, and reads as no marks.
        fresh = new_game("hostile")
        fresh.hostiles_state = None
        assert hostiles_sim.marked(fresh) == []
        assert not _a_hull(fresh).hostile
        return f"{hull.name} reloaded still marked, and an old save opens clean"

    @check("marking costs nothing and tells nobody")
    def _():
        # It is a note to yourself, not a declaration. `allegiance.price_attack`
        # prices moving against a power and is what a *denunciation* spends;
        # a mark spends nothing, so a captain can watch somebody without
        # picking a fight with their friends.
        game = new_game("hostile")
        hull = _a_hull(game)
        before_rep = dict(game.rep)
        before_credits, before_day = game.credits, game.day
        lines = len(game.log)

        hostiles_sim.mark(game, hull.hull_id)

        assert dict(game.rep) == before_rep, (
            f"marking moved standing: {before_rep} -> {dict(game.rep)}")
        assert game.credits == before_credits, "marking cost money"
        assert game.day == before_day, "marking took time"
        assert len(game.log) == lines, (
            "sim/hostiles wrote to the log; the screen that marks says so, "
            "and a sim door that also narrates is two doors")

        said = hostiles_sim.note(game, hull)
        assert "marked" in said.lower(), said
        body = next(c for c in track_sim.contacts(game) if c.kind == "body")
        assert "not a hull" in hostiles_sim.note(game, body), (
            hostiles_sim.note(game, body))
        return f"no standing, no money, no time; “{said[:52]}…”"
