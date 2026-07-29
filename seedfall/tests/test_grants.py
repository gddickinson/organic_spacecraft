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


def _aggregator_body() -> str:
    """The text of `colony.effects()`, which republishes without consuming."""
    import ast

    path = (pathlib.Path(__file__).resolve().parent.parent
            / "sim" / "colony.py")
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "effects":
            return ast.get_source_segment(text, node) or ""
    raise AssertionError("colony.effects() has moved or been renamed")


def _relays() -> dict[str, set[str]]:
    """effect key -> the aggregate keys `colony.effects()` feeds it into.

    An effect whose only mention is inside the aggregator is consumed only if
    the key it feeds is itself opened somewhere. Following that one hop is
    the difference between `vault`, which reaches `state.py` through
    `has_vault`, and `fabricate`, which reached a flag nobody read.
    """
    import re

    out: dict[str, set[str]] = {}
    for line in _aggregator_body().splitlines():
        outs = re.findall(r'out\[["\'](\w+)["\']\]', line)
        ins = re.findall(r'e\.get\(["\'](\w+)["\']', line)
        for effect in ins:
            out.setdefault(effect, set()).update(outs)
    return out


def _sources(exclude_aggregator: bool = False) -> list[str]:
    root = pathlib.Path(__file__).resolve().parent.parent
    body = _aggregator_body() if exclude_aggregator else ""
    out = []
    for folder in CONSUMERS:
        for path in (root / folder).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if body and body in text:
                text = text.replace(body, "")
            out.append(text)
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
        #
        # It then let two through anyway. `colony.effects()` copied `watch`
        # and `fabricate` into a `watch_systems` set and a `has_fabricator`
        # flag that **no other line in the game ever opened**, and this check
        # counted those copies as consumers. A mention inside a function whose
        # own output nobody reads is not a consumer; it is a place for a dead
        # effect to hide. So the aggregator does not get a vote.
        sources = _sources(exclude_aggregator=True)
        assert len(sources) > 40, len(sources)
        relays = _relays()
        assert relays, "no effect reaches the aggregate at all — has it moved?"

        def read(name: str) -> int:
            return sum(text.count(f'"{name}"') + text.count(f"'{name}'")
                       for text in sources)

        dead = []
        for key in DECLARED:
            hits = read(key) + sum(read(k) for k in relays.get(key, ()))
            if hits == 0:
                who = [c.id for c in COLONIES if key in (c.effects or {})]
                dead.append(f"{key} (declared by {', '.join(who)})")
        assert not dead, (
            f"{len(dead)} effect(s) are granted and read by nothing: "
            + "; ".join(dead))
        return f"{len(DECLARED)} effects declared, every one consumed"

    @check("what the aggregate publishes, something opens")
    def _():
        # The other half of the same fault. `colony.effects()` published
        # `build_systems`, `watch_systems`, `has_medical`, `has_fabricator`,
        # `pop` and `research` — six keys, and the game opened none of them.
        # `research` was the worst: always 0.0 even with five
        # research-yielding colonies online, and added to the bench rate in
        # two places that were therefore adding nothing.
        from ..core.state import new_game

        published = sorted(colony_sim.effects(new_game("keys")))
        assert published, "the aggregate publishes nothing at all"
        sources = _sources(exclude_aggregator=True)
        orphans = [k for k in published
                   if not sum(t.count(f'"{k}"') + t.count(f"'{k}'")
                              for t in sources)]
        assert not orphans, (
            f"`colony.effects()` publishes {orphans}, which nothing outside "
            "it ever reads — either wire them up or stop computing them")
        return f"{len(published)} keys published, every one opened elsewhere"

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

    @check("a picket tells you what happens where you are not")
    def _():
        # `watch` said "Keeps an eye on this system whether or not you are in
        # it" and bought nothing: the sector reported every new infestation
        # anywhere, so a captain already knew. Measured by playing the Bloom
        # forward and reading the log.
        from ..sim import threat

        def reports(watched: bool, seeds: int = 14) -> int:
            heard = 0
            for trial in range(seeds):
                game = new_game(f"picket{trial}")
                far = [s for s in game.galaxy.systems
                       if s.id != game.location_id]
                for system in far[:6]:
                    system.bloom = 0.75
                if watched:
                    game.colonies = [
                        Colony(id=i + 1, class_id="vesper_picket", name="Eye",
                               system_id=s.id, body_id=s.bodies[0].id,
                               need=0, online=True, pop=0)
                        for i, s in enumerate(game.galaxy.systems)
                        if s.id != game.location_id]
                game.recompute()
                for _ in range(40):
                    for kind, text in threat.tick(game, 30, RNG(f"t{trial}")):
                        heard += "Unlicensed growth detected" in text
            return heard

        blind, watching = reports(False), reports(True)
        assert watching > blind, (
            f"growth was reported {watching} times with pickets everywhere "
            f"and {blind} times with none — the watch buys nothing")
        assert blind < watching * 0.6, (
            f"{blind} reports with no eyes out against {watching} with them: "
            "the sector is still telling you almost everything for free")
        return (f"{watching} reports with pickets out, {blind} without")

    @check("a yard of your own makes fabricated fittings cheaper")
    def _():
        # `fabricate` promised "Fabricated parts can be made rather than
        # bought" and its only reader set a flag nothing opened.
        from ..data.chassis import CHASSIS_BY_ID
        from ..data.parts import PARTS
        from ..sim import shipyard

        made = [p.id for p in PARTS
                if getattr(p, "family", None) == "fabricated"][:3]
        assert made, "no fabricated fittings to test with"
        chassis = CHASSIS_BY_ID["pike"]
        bought = shipyard.cost_of(chassis, made, False)
        built = shipyard.cost_of(chassis, made, True)
        assert built["credits"] < bought["credits"], (
            f"a yard of your own changes the bill by nothing: "
            f"{bought['credits']:,} either way")
        # The metal is still the metal — you are making it, not conjuring it.
        for key in bought:
            if key != "credits":
                assert built[key] == bought[key], (
                    f"the yard also conjured {key} out of nothing")
        # And a grown hull's fittings are untouched by a fabricator.
        grown = [p.id for p in PARTS
                 if getattr(p, "family", None) == "grown"][:3]
        gb = shipyard.cost_of(CHASSIS_BY_ID["navis"], grown, False)
        gm = shipyard.cost_of(CHASSIS_BY_ID["navis"], grown, True)
        assert gb == gm, "a fabricator discounted grown fittings"
        # The yard has to be in the system, not merely owned.
        game = new_game("yard")
        assert not colony_sim.fabricating(game, game.location_id)
        elsewhere = next(s for s in game.galaxy.systems
                         if s.id != game.location_id)
        game.colonies = [Colony(id=1, class_id="fab_yard", name="Y",
                                system_id=elsewhere.id,
                                body_id=elsewhere.bodies[0].id,
                                need=0, online=True, pop=400)]
        assert not colony_sim.fabricating(game, game.location_id), (
            "a yard one system over is fabricating for you")
        assert colony_sim.fabricating(game, elsewhere.id)
        # And the yard screen accounts for the smaller number rather than
        # simply printing it.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game.location_id = elsewhere.id
        game.credits = 400_000
        for goods in ("alloy", "silicon", "ore", "biomass"):
            game.stores[goods] = 4000
        game.research.unlocked = list({*game.research.unlocked,
                                       "monocoque", "whipple"})
        game.recompute()
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("yard")
        view = win.views["yard"]
        view.tab = "build"
        view.design_chassis = "pike"
        view.design_fitted = ["ion_cluster", "pdc", "alloy_armour"]
        view.refresh()
        for _ in range(3):
            app.processEvents()
        rows = " ".join(lab.text() for lab in view.findChildren(QLabel)
                        if lab.text())
        win.close()
        assert "yard of yours" in rows, (
            "the bill is smaller and the screen does not say why")
        saved = bought["credits"] - built["credits"]
        return (f"{saved:,} credits off a {bought['credits']:,} hull, metal "
                "unchanged, grown fittings untouched, and the screen says so")

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
