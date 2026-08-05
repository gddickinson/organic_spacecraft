"""One way in to everything: the channel, and what it offers.

A player flew to a Weave anchor and could not work out how to use it. They
were right to be stuck — an anchor is a place in the system with no services,
and the panel that rides a ring lives on the sector chart, so the thing they
had flown to offered "Open holdings" and nothing else.

`sim/hail.py` is the general answer: given anything `sim/track` can put a
cursor on, who it is, what it says, and what can be done — each option
carrying whether it is available and *why not* when it is not.

The claims:

- **Everything answers.** Every kind of contact in a real system yields a
  greeting and at least one option, so no object is a dead end.
- **A refusal says why**, because a menu that greys a button without a reason
  is the thing this replaced.
- **The anchor explains itself**, dark or lit, at the anchor.
- **It promises nothing the sim will refuse** — every option's availability
  is the door's own answer.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import hail
from ..sim import track as track_sim
from ..sim import weave as weave_sim
from .harness import Suite


def _gate_system(seed: str = "verge-7"):
    game = new_game(seed)
    sid = next((s for s in weave_sim.sites(game.galaxy)
                if weave_sim.gate_at(game, s)), None)
    if sid is not None:
        game.location_id = sid
    game.recompute()
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("everything you can put a cursor on answers, and offers something")
    def _():
        game = _gate_system()
        kinds, dead = set(), []
        for contact in track_sim.contacts(game):
            said = hail.greeting(game, contact)
            options = hail.options(game, contact)
            kinds.add(contact.kind)
            assert said, f"{contact.name} returned nothing at all"
            if contact.kind == "star":
                continue          # a star is allowed to have nothing to say
            if not options:
                dead.append(f"{contact.name} ({contact.kind})")
        assert not dead, f"contacts with nothing to do: {dead}"
        assert {"body", "anchorage", "hull"} <= kinds, kinds
        return f"{len(kinds)} kinds of contact, every one of them answering"

    @check("a refusal names its reason, never a grey button on its own")
    def _():
        game = _gate_system()
        silent = []
        for contact in track_sim.contacts(game):
            for option in hail.options(game, contact):
                if not option.ok and not (option.why or option.blurb):
                    silent.append(f"{contact.name}: {option.label}")
        assert not silent, f"refused without a reason: {silent}"
        return "every refusal on every contact says why"

    @check("the anchor explains itself, at the anchor")
    def _():
        # The defect in one line: the thing the player flew to said only
        # that it was dark.
        game = _gate_system()
        gate = weave_sim.gate_at(game, game.location_id)
        assert gate is not None, "this fixture has no anchor to stand at"
        contact = next(c for c in track_sim.contacts(game)
                       if c.kind == "anchorage" and c.name == gate.name)
        options = hail.options(game, contact)
        ids = {o.id.split(":", 1)[0] for o in options}
        assert "conn" in ids, "no way to fly to it"
        if gate.lit:
            assert "step" in ids or "nowhere" in ids, (
                f"a lit anchor offers neither a transit nor a reason: {ids}")
        else:
            wake = next(o for o in options if o.id == "wake")
            assert not wake.ok and wake.why, (
                "a dark anchor offers waking with no word on what it needs")
            assert "weavecraft" in wake.why.lower() or "know" in wake.why.lower(), (
                f"the reason does not name what is missing: {wake.why!r}")
        return (f"{gate.name} is {'lit' if gate.lit else 'dark'}, and the "
                f"channel says what that means and what it would take")

    @check("what the menu offers is what the sim allows")
    def _():
        # The menu asks the doors rather than keeping its own rules, so an
        # option can never promise something the game will refuse. Checked
        # against `berthing.can_conn`, which every contact carries.
        from ..sim import berthing as berth_sim
        game = _gate_system()
        wrong = []
        for contact in track_sim.contacts(game):
            fly = next((o for o in hail.options(game, contact)
                        if o.id == "conn"), None)
            if fly is None:
                continue
            ok, _why = berth_sim.can_conn(game, contact)
            if fly.ok != ok:
                wrong.append(f"{contact.name}: menu {fly.ok}, sim {ok}")
        assert not wrong, f"the menu and the sim disagree: {wrong}"
        return "every offer of the conn matches what berthing would say"
