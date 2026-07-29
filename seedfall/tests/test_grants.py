"""What a colony grants: whether anything reads it, and whether anyone is told.

`megastructure` was declared by the ARCA Habitat — 400,000 credits, 2,600
tonnes of ore, 900 days, a million people — and **read by nothing**. Not one
line of the sim consulted it. So the largest work in the game was, mechanically,
a very good mine: a five-by-ten-kilometre drum of spun rock was overgrown by
the Bloom on exactly the same roll as a lichen farm.

It looked covered, too. Two suites list `megastructure` in a `KNOWN_EFFECTS`
vocabulary, but that set only asserts nobody declares an *unknown* key — never
that a declared one is consumed. A whitelist reads like coverage and is not.

And the founding screen printed `"Grants: " + ", ".join(effects)` — the raw
internal keys. A captain weighing nine hundred days read "Grants: megastructure"
and had no way to find out what it meant, which was just as well.

The claims:

- **Every effect any class declares is read by the sim.** This is the general
  one, and the one that found the bug.
- **Every effect has words**, and they are words rather than the key echoed.
- **The screen prints the words, not the keys.**
- **A megastructure is hard to overgrow, and not impossible.**
"""

from __future__ import annotations

import pathlib

from ..core.rng import RNG
from ..core.state import new_game
from ..data.colonies import COLONIES, EFFECT_TEXT, effect_text
from ..sim import colony as colony_sim
from ..sim.colony import COLONIES_BY_ID, Colony
from .harness import Suite

#: Every effect key any colony class actually declares.
DECLARED = sorted({k for c in COLONIES for k in (c.effects or {})})

#: Where a consumer could live. `data/` is where they are declared and
#: `tests/` proves nothing about the game, so neither counts.
CONSUMERS = ("sim", "core", "world", "ui")


def _sources() -> list[str]:
    root = pathlib.Path(__file__).resolve().parent.parent
    out = []
    for folder in CONSUMERS:
        for path in (root / folder).rglob("*.py"):
            out.append(path.read_text(encoding="utf-8"))
    return out


def _attack(class_id: str, trials: int = 400, bloom: float = 1.0) -> float:
    """How often the Bloom takes this class, planted alone in a system."""
    lost = 0
    for trial in range(trials):
        game = new_game(f"grant{trial}")
        system = game.system
        system.bloom = bloom
        body = system.bodies[0]
        col = Colony(id=1, class_id=class_id, name="X", system_id=system.id,
                     body_id=body.id, need=0, online=True,
                     pop=COLONIES_BY_ID[class_id].pop)
        game.colonies = [col]
        body.colony = col.id
        if colony_sim.bloom_attack(game, system, RNG(f"atk{trial}")):
            lost += 1
    return lost / trials


def run(suite: Suite) -> None:
    check = suite.check

    @check("every effect a colony grants is read by something")
    def _():
        # The general question, and the one that found `megastructure` dead.
        # A whitelist of known keys — which two suites already had — cannot
        # ask this: it checks the vocabulary, not whether anybody listens.
        sources = _sources()
        assert len(sources) > 40, len(sources)
        dead = []
        for key in DECLARED:
            hits = sum(text.count(f'"{key}"') + text.count(f"'{key}'")
                       for text in sources)
            if hits == 0:
                who = [c.id for c in COLONIES if key in (c.effects or {})]
                dead.append(f"{key} (declared by {', '.join(who)})")
        assert not dead, (
            f"{len(dead)} effect(s) are granted and read by nothing: "
            + "; ".join(dead))
        return f"{len(DECLARED)} effects declared, every one consumed"

    @check("every effect has words, and they are not just the key back")
    def _():
        missing = [k for k in DECLARED if k not in EFFECT_TEXT]
        assert not missing, (
            f"no plain-English line for: {', '.join(missing)} — the screen "
            "would print the internal name")
        lazy = [k for k in DECLARED
                if effect_text(k).strip().lower() in (k, k.replace("_", " "))]
        assert not lazy, (
            f"the description for {lazy} is the key with the underscore taken "
            "out, which tells a captain nothing")
        for key in DECLARED:
            words = effect_text(key)
            assert len(words) > 24, f"{key}: {words!r} is not a sentence"
            assert words[0].isupper() and words.rstrip().endswith("."), (
                f"{key}: {words!r}")
        return f"{len(DECLARED)} effects, every one written out"

    @check("the founding screen prints the words and not the keys")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("screen")
        game.research.unlocked = list({*game.research.unlocked,
                                       *(c.tech for c in COLONIES if c.tech)})
        game.credits = 900_000
        for goods in ("biomass", "ore", "phosphate", "spidroin", "volatiles",
                      "alloy", "silicon"):
            game.stores[goods] = 9000
        game.recompute()
        game.system.bodies[0].surveyed = True
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("system")
        view = win.views["system"]
        view.selected = 0

        held = {}
        win.dialog = lambda title, widgets, buttons: held.setdefault(
            "w", widgets) and None
        view._colonise()
        assert held.get("w"), "the founding dialog offered nothing"
        holder = QWidget()
        layout = QVBoxLayout(holder)
        for widget in held["w"]:
            layout.addWidget(widget)
        for _ in range(3):
            app.processEvents()
        texts = [lab.text() for lab in holder.findChildren(QLabel) if lab.text()]
        blob = " ".join(texts)
        win.close()

        shown = [k for k in DECLARED if effect_text(k) in blob]
        assert len(shown) >= 6, (
            f"only {len(shown)} grants were described on the card stack")
        # And the raw keys are gone. `port` and `sensor` are ordinary English,
        # so only the ones that could not be prose are checked.
        internal = [k for k in DECLARED if "_" in k]
        assert internal, internal
        leaked = [k for k in internal if k in blob]
        assert not leaked, (
            f"the screen is still printing internal names: {leaked}")
        return (f"{len(shown)} grants described in words; no internal names "
                f"({', '.join(internal)}) on the screen")

    @check("a megastructure is hard for the Bloom to overgrow")
    def _():
        # What `megastructure` now buys, measured rather than asserted off the
        # constant: a drum against a farm, same system, same pressure.
        farm = _attack("lichen_dome")
        drum = _attack("arca_drum")
        assert farm > 0.15, (
            f"a lichen dome is only taken {farm:.0%} of the time — this "
            "measurement has no pressure in it")
        assert drum < farm * 0.35, (
            f"the ARCA Habitat is overgrown {drum:.0%} of the time against a "
            f"farm's {farm:.0%} — four hundred thousand credits and nine "
            "hundred days buy it nothing the farm has not got")
        return f"farm taken {farm:.0%} of the time, the drum {drum:.0%}"

    @check("a megastructure is not immortal")
    def _():
        # The comment on `bloom_attack` promises that given years enough the
        # Bloom gets everything unattended. A flat immunity would be a much
        # duller thing and would quietly break the containment ending.
        taken = _attack("arca_drum", trials=600)
        assert taken > 0.0, (
            "six hundred attacks and the drum was never once overgrown — "
            "that is immunity, not resistance")
        return f"still taken {taken:.1%} of the time over 600 attacks"
