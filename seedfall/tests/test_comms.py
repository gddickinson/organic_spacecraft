"""Somebody is calling, and how long it took to get here means something.

Nothing in the Verge ever spoke to the captain: things happened and the only
record was a line in the player's own log, in the player's own voice. A
`Signal` has a sender, a body, sometimes a question — and a delay.

The delay is the claim worth holding. **Nothing is broadcast through a ring**:
a gate moves mass, so a despatch crosses the Weave aboard a courier that waits
for a slot, transits, and rebroadcasts. That gives three regimes, and the
distance between them is the point:

* inside a system it is a radio call and arrives today;
* across the lit Weave it is **carried**, and what it costs is the *gates* —
  not how far apart the two ends are in space;
* off the network there is nothing to carry it, so it goes at light speed and
  a system with no lit anchor is years out of date.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data import signals as sig_data
from ..sim import comms
from ..sim import weave as weave_sim
from .harness import Suite


def _lit_pair(game):
    """Two different systems both burning, if the chronicle has any."""
    net = weave_sim.network(game)
    for sid, others in net.items():
        for other in others:
            if other != sid:
                return sid, other
    return None, None


def run(suite: Suite) -> None:
    check = suite.check

    @check("inside a system, somebody calling you is a radio call")
    def _():
        game = new_game("comms")
        sig = comms.send(game, "control", "Fleet Hub", "control",
                         "Cleared", "Mast four is yours.")
        assert sig.due_day == game.day, (
            f"a call from the quay you are orbiting took "
            f"{sig.due_day - game.day:.2f} days")
        assert sig in [s for s in comms.inbox(game)], "it never arrived"
        assert comms.unread(game) == 1
        comms.read(game, sig.id)
        assert comms.unread(game) == 0
        return f"same-system traffic arrives on day {game.day:.0f}, unread → read"

    @check("across the Weave it is carried, and the gates set the price")
    def _():
        game = new_game("comms")
        here, there = _lit_pair(game)
        if here is None:
            return "no lit pair in this chronicle to measure"
        carried = comms.path_days(game, here, there)
        assert carried is not None and carried > 0.0, (
            "a hop across the lit Weave was free, which is broadcasting")
        # And it is the *gate* that decides, not the distance: a courier's
        # hop out of a system costs what that system's ring costs.
        leg = comms.carried_days(game, here)
        assert abs(carried - leg) < 1.0, (
            f"one hop cost {carried:.2f} d against the {leg:.2f} d its own "
            "ring quotes")
        from ..world.galaxy import distance
        by_id = {s.id: s for s in game.galaxy.systems}
        apart = distance(by_id[here], by_id[there])
        assert carried < apart * sig_data.DAYS_PER_LY, (
            "carrying it is no faster than light, so the Weave buys nothing")
        return (f"{apart:.1f} ly in {carried * 24:,.1f} h carried, against "
                f"{apart * sig_data.DAYS_PER_LY:,.0f} d at light speed")

    @check("off the network, news is years old")
    def _():
        game = new_game("comms")
        net = weave_sim.network(game)
        dark = next((s.id for s in game.galaxy.systems if s.id not in net),
                    None)
        if dark is None:
            return "every system in this chronicle is on the lit Weave"
        lag = comms.lag_days(game, dark, game.system.id)
        assert comms.path_days(game, dark, game.system.id) is None, (
            "the system picked is on the lit Weave after all")
        # Word still crosses aboard hulls flying their own drives — slowly.
        # What must hold is that it is *far* dearer than a relay, which is
        # the whole case for lighting an anchor.
        assert lag > 10.0, (
            f"news from off the Weave took {lag:.1f} days, which is no worse "
            "than carrying it")
        best = min((comms.carried_days(game, s) for s in
                    weave_sim.network(game)), default=None)
        if best is not None:
            assert lag > best * 5.0, (
                f"{lag:.1f} d off the Weave against {best:.2f} d on it — the "
                "relay is buying nothing")
        # Which of the two slow regimes this was: a hull can carry word
        # anywhere it can fly, and only a system behind a gap no jumping
        # closes falls back to light.
        from ..world.galaxy import distance
        by_id = {s.id: s for s in game.galaxy.systems}
        apart = distance(by_id[dark], by_id[game.system.id])
        how = ("shipped" if abs(lag - apart * sig_data.DAYS_PER_LY_SHIPPED)
               < 1e-6 else "light, with nothing able to reach it")
        return (f"from an unlit system {apart:.1f} ly off: {lag:,.0f} d "
                f"({how}), against {(best or 0) * 24:,.1f} h a hop carried")

    @check("a question waits until it is answered, and then stops")
    def _():
        game = new_game("comms")
        sig = comms.send(
            game, "harbour", "Fleet Hub", "control", "Berth fee",
            "Forty credits for the mast, or stand off and we say no more.",
            replies=(("pay", "Pay it"), ("stand", "Stand off")))
        assert sig.asks, "a signal with answers is not asking"
        assert [s.id for s in comms.asking(game)] == [sig.id]
        assert not comms.answer(game, sig.id, "argue"), (
            "it accepted an answer it never offered")
        assert comms.answer(game, sig.id, "pay")
        assert not sig.asks and sig.answered == "pay"
        assert not comms.asking(game), "it is still waiting after an answer"
        assert not comms.answer(game, sig.id, "stand"), (
            "it let the captain answer twice")
        return "offered two answers, refused a third, and closed on the first"

    @check("the sector speaks when something changes, and says which way")
    def _():
        from ..data.factions import FACTIONS
        game = new_game("regard")
        game.advance_days(2)
        quiet = len(comms.inbox(game))
        # Nothing changed, so nobody writes: the traffic is derived from what
        # moved, not rolled each day.
        game.advance_days(3)
        assert len(comms.inbox(game)) == quiet, (
            "the powers wrote to a captain who did nothing")
        who = FACTIONS[0].id
        game.adjust_rep(who, 40)
        game.advance_days(1)
        game.adjust_rep(who, -80)
        game.advance_days(1)
        said = [s for s in comms.inbox(game) if s.channel == "power"]
        assert len(said) >= 2, f"{len(said)} despatches after two moves"
        warm = [s for s in said if "say so where it counts" in s.body]
        cold = [s for s in said if "doors heavier" in s.body]
        assert warm and cold, (
            "a rise and a fall read the same way — measured once with the "
            f"warmth table keyed in the wrong case: {[s.body[:40] for s in said]}")
        return (f"{len(said)} despatches: {len(warm)} warmer, {len(cold)} "
                "colder, and silence when nothing moved")

    @check("what was said survives a save and a reload")
    def _():
        import os
        import tempfile
        from pathlib import Path
        from ..core import save as save_mod
        game = new_game("comms")
        comms.send(game, "charter", "The GESTALT Charter", "power",
                   "Noted", "Your licence stands.",
                   replies=(("thanks", "Acknowledge"),))
        with tempfile.TemporaryDirectory() as tmp:
            was = os.environ.get(save_mod.SAVE_ENV)
            os.environ[save_mod.SAVE_ENV] = str(Path(tmp) / "s.json")
            try:
                assert save_mod.write({"game": game})
                back = save_mod.read()
            finally:
                if was is None:
                    os.environ.pop(save_mod.SAVE_ENV, None)
                else:
                    os.environ[save_mod.SAVE_ENV] = was
        loaded = back.get("game")
        got = comms.inbox(loaded)
        assert len(got) == 1, f"{len(got)} signals came back of one"
        assert got[0].asks, "the question was lost in the save"
        assert got[0].name == "The GESTALT Charter", got[0].name
        return "one unanswered despatch, reloaded with its question intact"

    @check("the store does not grow for ever")
    def _():
        game = new_game("comms")
        for n in range(200):
            sig = comms.send(game, "news", "Bulletin", "news",
                             f"Item {n}", "Something happened somewhere.")
            comms.read(game, sig.id)
        dropped = comms.sweep(game, keep=120)
        assert dropped, "nothing was swept from a store of two hundred"
        assert len(comms.inbox(game)) <= 120, len(comms.inbox(game))
        # An unanswered question is never swept, however old.
        asked = comms.send(game, "harbour", "Fleet Hub", "control", "Answer?",
                           "Well?", replies=(("yes", "Yes"),))
        for n in range(200):
            comms.read(game, comms.send(game, "news", "Bulletin", "news",
                                        f"More {n}", "And another.").id)
        comms.sweep(game, keep=50)
        assert any(s.id == asked.id for s in comms.inbox(game)), (
            "an unanswered question was swept away")
        return f"{dropped} read items dropped; the open question kept"
