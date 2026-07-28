"""Every feature has to move something.

`test_reachable.py` proves a function is called; it cannot prove the call
matters. The Bloom's growth multiplier was consumed by `summary()` from the day
it was written while contributing nothing to the simulation, and a reachability
check passes on that happily. This is the stronger claim: switch the feature
off, run the same seeded scenario, and the world has to come out different.

The harness is only worth having if it can fail, so there are two checks on the
harness itself — one that an inert feature is caught, and one that every lever's
patch genuinely changes the number rather than quietly missing its target.
"""

from __future__ import annotations

from .efficacy import Lever, measure, neutralised, verdict
from .harness import Suite
from .levers import LEVERS, LEVERS_BY_ID


def run(suite: Suite) -> None:
    check = suite.check

    @check("every lever names something that exists and can be switched off")
    def _():
        for lever in LEVERS:
            module, attribute, replacement = lever.patch
            assert hasattr(module, attribute), (
                f"{lever.id} patches {module.__name__}.{attribute}, which does "
                "not exist — the substitution would raise rather than test")
            assert callable(getattr(module, attribute)), (
                f"{lever.id} patches something that is not callable")
            assert callable(replacement), f"{lever.id} has a non-callable stand-in"
            assert lever.what and lever.direction in ("lower", "higher", "differs")
        assert len(LEVERS_BY_ID) == len(LEVERS), "two levers share an id"
        return f"{len(LEVERS)} levers, all pointing at something real"

    @check("switching a feature off actually changes the measurement")
    def _():
        # A patch that misses its target leaves the two runs identical, and the
        # lever then passes or fails for reasons that have nothing to do with
        # the feature. Every lever has to demonstrate its own bite.
        inert = []
        for lever in LEVERS:
            live, dead = measure(lever)
            if live == dead:
                inert.append(f"{lever.id} (both runs {live:.4g})")
        assert not inert, (
            "levers whose patch changed nothing — the substitution is missing "
            "its target:\n      " + "\n      ".join(inert))
        return f"all {len(LEVERS)} substitutions bite"

    @check("the harness catches a feature that does nothing")
    def _():
        # A decorative feature, built deliberately: a function nothing depends
        # on. If the harness passes this, it would pass the Bloom multiplier.
        from . import efficacy

        class Decoration:
            @staticmethod
            def looks_important(_game=None) -> float:
                return 3.0

        module = Decoration()
        fake = Lever("decorative", "a number nobody uses",
                     patch=(module, "looks_important", lambda _g=None: 1.0),
                     probe=lambda: 42.0, direction="differs")
        ok, note = efficacy.verdict(fake)
        assert not ok, (
            "the harness passed a feature that changes nothing at all: " + note)
        # And the patch is undone afterwards, or later levers read a stub.
        assert module.looks_important() == 3.0, (
            "neutralised() left its replacement in place")
        return "an inert feature fails, and the substitution is cleaned up"

    for lever in LEVERS:
        @check(f"it matters that {lever.what}")
        def _(lever=lever):
            ok, note = verdict(lever)
            assert ok, note
            return note.split("; ")[0]
