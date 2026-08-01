"""Voice and memory checks — and the game must be whole with no model at all.

The binding constraint on this whole feature: SEEDFALL ships with no network
and the suite is hermetic. So the language model is off by default, every
speaking path has a written fallback, and **no check here ever makes a network
call** — `llm.complete` is stubbed and what is measured is the offline voice.

If these pass with the model unreachable, the feature is optional in the way it
claims to be.
"""

from __future__ import annotations

import os
import tempfile

from ..core import llm
from ..core.state import new_game
from ..data.personas import MOODS, PERSONAS, PERSONAS_BY_ID
from ..sim import memory as memory_sim
from ..sim import voice as voice_sim
from .harness import Suite


class _NoNetwork:
    """Fails the check loudly if anything tries to reach a model."""

    def __enter__(self):
        self.calls = 0
        self._complete, self._provider = llm.complete, llm.provider

        def refuse(*_a, **_k):
            self.calls += 1
            raise AssertionError("a check tried to reach a language model")
        llm.complete = refuse
        llm.provider = lambda: None
        llm.reset()
        return self

    def __exit__(self, *_exc):
        llm.complete, llm.provider = self._complete, self._provider
        llm.reset()
        return False


def run(suite: Suite) -> None:
    check = suite.check

    @check("the game speaks with no model reachable at all")
    def _():
        with _NoNetwork():
            assert not llm.enabled(), "something answered in a hermetic check"
            game = new_game("silent")
            said = 0
            for persona in PERSONAS:
                for mood in MOODS:
                    result = voice_sim.speak(
                        game, f"probe:{persona.id}:{mood}",
                        name=f"{persona.name} {mood}", persona=persona.id,
                        situation=mood)
                    line = result["line"]
                    assert line and line.strip(), (
                        f"{persona.id}/{mood} said nothing")
                    assert "{" not in line and "}" not in line, (
                        f"{persona.id}/{mood} leaked a frame slot: {line!r}")
                    assert result["source"] == "written"
                    assert len(line) < 400, f"{persona.id}/{mood}: {line[:80]}"
                    said += 1
        return f"{len(PERSONAS)} personas × {len(MOODS)} moods = {said} lines"

    @check("every persona covers every mood, and says something different")
    def _():
        for persona in PERSONAS:
            missing = [m for m in MOODS if not persona.frames.get(m)]
            assert not missing, f"{persona.id} has no frame for {missing}"
            assert persona.register and persona.address
        # And two personas must not be the same persona wearing a hat.
        with _NoNetwork():
            game = new_game("distinct")
            lines = {}
            for persona in PERSONAS:
                lines[persona.id] = voice_sim.speak(
                    game, f"same:{persona.id}", persona=persona.id,
                    name="Speaker", situation="warn")["line"]
            assert len(set(lines.values())) == len(lines), (
                f"personas that say the same thing: {lines}")
        return f"{len(PERSONAS)} personas, {len(MOODS)} moods each, all distinct"

    @check("a speaker turns cold at the impression it says it does")
    def _():
        # `voice.COLD_AT` and `WARM_AT` decide the mood a speaker answers in,
        # and **no check anywhere referenced either** — swept at double and
        # half, the whole suite stayed green. Real, load-bearing and held by
        # nothing, which is the state `tests/tripwire.py` exists to find.
        #
        # Bracketed with absolute impressions. Measured through `mood_for`:
        # both gates are inclusive, so a mind at exactly -18 is already cold
        # and one at -17 is not.
        assert (voice_sim.COLD_AT, voice_sim.WARM_AT) == (-18.0, 18.0), (
            f"the bars moved to {voice_sim.COLD_AT}/{voice_sim.WARM_AT}; the "
            "impressions below bracket -18 and +18 with absolute values and "
            "must be re-bracketed by hand, which is the point of them")

        class Speaker:
            """Just enough of a mind for `mood_for`, and nothing more."""
            persona = "plain"

            def __init__(self, value):
                self._value = value

            def impression(self):
                return self._value

        def mood(value):
            return voice_sim.mood_for(Speaker(value))

        assert mood(-17.0) != "cold", (
            "a speaker one point short of cold is already cold")
        assert mood(-18.0) == "cold", (
            "a speaker at exactly the bar is not cold; the gate is `<=`")
        assert mood(-40.0) == "cold"
        assert mood(+17.0) != "warm", (
            "a speaker one point short of warm is already warm")
        assert mood(+18.0) == "warm", (
            "a speaker at exactly the bar is not warm; the gate is `>=`")
        assert mood(0.0) == "greet", (
            f"an indifferent speaker answers {mood(0.0)!r} rather than plainly")
        return "greet at -17, cold at -18, warm at +18"

    @check("what a mind holds changes what it says")
    def _():
        with _NoNetwork():
            game = new_game("holds")
            neutral = voice_sim.speak(game, "captain:a", name="Ordell",
                                      persona="captain", situation="greet")
            memory_sim.note(game, "captain:b", "betrayal",
                            "you left them under fire at Vaux Deep", 1.6,
                            tags=["combat"], name="Ordell")
            memory_sim.note(game, "captain:b", "theft",
                            "you lifted a cargo that was theirs", 1.2,
                            tags=["trade"])
            sour = voice_sim.speak(game, "captain:b", name="Ordell",
                                   persona="captain", situation="greet")
            memory_sim.note(game, "captain:c", "rescue",
                            "you came for them at Tarn Span", 1.5,
                            tags=["combat"], name="Ordell")
            memory_sim.note(game, "captain:c", "alliance",
                            "you stood with them against the Bloom", 1.2)
            sweet = voice_sim.speak(game, "captain:c", name="Ordell",
                                    persona="captain", situation="greet")

            assert sour["mood"] == "cold", sour
            assert sweet["mood"] == "warm", sweet
            assert sour["impression"] < neutral["impression"] < sweet["impression"]
            assert "Vaux Deep" in sour["line"] or "cargo" in sour["line"], (
                f"the grudge was not brought up: {sour['line']!r}")
            assert "Tarn Span" in sweet["line"] or "stood" in sweet["line"]
        return (f"same speaker: {sour['impression']:+.0f} cold, "
                f"{neutral['impression']:+.0f} neutral, "
                f"{sweet['impression']:+.0f} warm")

    @check("recall brings up what fits the situation, not what is newest")
    def _():
        game = new_game("recall")
        mind = memory_sim.mind_for(game, "port:x", name="Vell", kind="port")
        mind.remember(10, "smuggling", "the hold you brought through", 1.0,
                      ["customs"])
        for day in range(11, 24):
            mind.remember(day, "trade", f"a routine cargo on day {day}", 0.5,
                          ["trade"])
        brought_up = mind.recall(tags=["customs"], about="player", limit=1)
        assert brought_up and "hold you brought" in brought_up[0].text, (
            f"a customs desk led with {brought_up[0].text!r}")
        newest = mind.recall(tags=["trade"], about="player", limit=1)
        assert "routine" in newest[0].text
        return "a customs desk raises the seizure; a counter raises the cargo"

    @check("an old slight fades, and a large one outlasts it")
    def _():
        game = new_game("fade")
        mind = memory_sim.mind_for(game, "captain:f", name="F", kind="captain")
        small = mind.remember(0, "slight", "a small thing", 0.4)
        large = mind.remember(0, "betrayal", "a large thing", 1.6)
        before = mind.impression()
        mind.decay(1200)
        after = mind.impression()
        assert abs(after) < abs(before), (
            f"nothing faded over three years: {before:.1f} → {after:.1f}")
        assert large.salience > small.salience
        assert mind.grudge()[0].kind == "betrayal", (
            "the grudge does not name the worst thing")
        return (f"impression {before:+.0f} → {after:+.0f} over 1,200 days; "
                f"the betrayal is still the reason")

    @check("minds survive a save, and so does what they think of you")
    def _():
        os.environ["HOME"] = tempfile.mkdtemp()
        from ..core import save as save_mod
        from ..core.state import load_game

        game = new_game("remember")
        memory_sim.note(game, "faction:charter", "betrayal",
                        "you ran the blockade at Kessel Gate", 1.5,
                        tags=["combat"], name="The Charter", entity="faction")
        before = memory_sim.impression_of(game, "faction:charter")
        game.advance_days(5)
        save_mod.write({"game": game})
        back = load_game()
        assert back is not None
        held = memory_sim.minds(back).get("faction:charter")
        assert held is not None, "the mind did not survive"
        assert any("Kessel Gate" in m.text for m in held.memories)
        assert abs(held.impression() - memory_sim.impression_of(
            game, "faction:charter")) < 0.01
        with _NoNetwork():
            line = voice_sim.hail(back, "faction:charter", situation="greet")
        assert line
        return (f"impression {before:+.0f} kept across a save; the reloaded "
                f"Charter still says so")

    @check("real events write real memories")
    def _():
        # The whole point: this is not a separate system bolted on. A finished
        # contract, a seizure and a kill each leave a record.
        from ..core.rng import RNG
        from ..sim import contracts as contract_sim

        game = new_game("events")
        rng = RNG("events")
        offered = contract_sim.generate(rng, game, game.system)
        assert offered, "no contract to finish"
        taken = offered[0]
        contract_sim.accept(game, taken)
        contract_sim._pay(game, taken)
        issuer = memory_sim.minds(game).get(f"faction:{taken.issuer}")
        assert issuer is not None, "nobody remembered the contract"
        assert any(m.kind == "contract" and m.source == "direct"
                   for m in issuer.memories), [m.kind for m in issuer.memories]
        assert issuer.impression() > 0
        return (f"{taken.issuer} remembers finishing "
                f"{taken.title[:34]!r} and thinks better of you for it")

    @check("a speaker draws on its own kind of past")
    def _():
        """Found by playing a live window: the ship's computer said "before any
        of this, *they* were refused a berth" — a captain's backstory, because
        the caller could not say what kind of thing was speaking.
        """
        with _NoNetwork():
            game = new_game("kinds")
            wrong = []
            for key, persona, kind, wants in (
                    ("ship:a", "ship", "ship", "hull"),
                    ("port:a", "harbourmaster", "port", "quay"),
                    ("faction:charter", "envoy", "faction", "they"),
                    ("officer:a", "officer", "officer", "they")):
                mind = memory_sim.mind_for(game, key, name="X", kind=kind,
                                           persona=persona)
                priors = [m.text for m in mind.memories if m.source == "prior"]
                assert priors, f"{kind} has no past at all"
                if not any(wants in text for text in priors):
                    wrong.append(f"{kind}: {priors[:1]}")
            assert not wrong, f"speakers given the wrong kind of past: {wrong}"
        return "ships, quays, powers and officers each remember their own kind"

    @check("nobody says their own title twice")
    def _():
        # "Harbourmaster Vell, harbourmaster." A frame that prefixes a title
        # onto a name that already carries it.
        with _NoNetwork():
            game = new_game("titles")
            for persona in PERSONAS:
                for mood in MOODS:
                    said = voice_sim.speak(
                        game, f"t:{persona.id}:{mood}",
                        name=f"{persona.name} Vell", persona=persona.id,
                        situation=mood)["line"].lower()
                    head = said.split(".")[0]
                    word = persona.name.split()[0].lower().rstrip("'s")
                    assert head.count(word) <= 1, (
                        f"{persona.id}/{mood} says {word!r} twice: {head!r}")
        return f"{len(PERSONAS)} personas × {len(MOODS)} moods, no doubled titles"

    @check("the model switch is off unless it is deliberately turned on")
    def _():
        was = os.environ.get(llm.SWITCH)
        try:
            os.environ.pop(llm.SWITCH, None)
            llm.reset()
            assert not llm.enabled(), "a model is live with the switch unset"
            assert llm.complete("anything") is None
            assert "Off." in llm.describe()
            os.environ[llm.SWITCH] = "0"
            llm.reset()
            assert not llm.enabled(), "'0' did not mean off"
        finally:
            if was is None:
                os.environ.pop(llm.SWITCH, None)
            else:
                os.environ[llm.SWITCH] = was
            llm.reset()
        return "off by default, off when set to 0, and complete() returns None"
