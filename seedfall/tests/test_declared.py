"""Nothing is declared in the tables and then read by nobody.

`test_reachable.py` asks this of functions and has earned its keep repeatedly —
most recently catching `orbits.nearest_height`, written and never wired in. This
asks it of **data**, which turns out to be the richer seam: an audit of every
field on every dataclass in `data/` found eight that nothing anywhere reads, and
several of them had docstrings *asserting* they mattered.

    starclasses.luminosity   "drives how hard the light falls on everything
                              else, which is why an M dwarf's worlds are dim
                              and an A-type's are glaring" — it drove nothing
    starclasses.halo         the corona colour, never drawn
    lineages.boredom         "what that costs in morale" — morale_tick had no
                              lineage term at all
    lineages.time_sense      "the line each one says about a long transit" — a
                              written line no player ever saw
    lessons.skip_if          a tutorial step that should skip itself, and did
                              not
    consorts.shield          1.0 screening, 0.0 flanking — never read
    mounts.axis              "losing one leaves the thrust off-axis", and it
                              did not
    commodities.cat          a category nothing grouped by

A dead field is worse than a missing one. It reads as a feature to anyone
looking at the table, it is quoted in the prose beside it, and it silently
promises behaviour the game does not have.

The allowlist below carries a **reason per entry**. That distinction matters: an
allowlist used to dodge the work is the anti-pattern this check exists to stop,
and an allowlist with a written reason is how "known, deliberate, and not a
defect" gets said out loud.
"""

from __future__ import annotations

import ast
import pathlib
import re

from .harness import Suite

#: Fields that are legitimately declared and legitimately unread, with why.
#: Anything not in here must be read somewhere, or wired up, or deleted.
ALLOWED: dict[str, str] = {
    "commodities.Commodity.cat":
        "A grouping for a market screen that lists goods in one flat table. "
        "Kept because the categories are the right ones and a grouped board is "
        "wanted; it is display metadata rather than a rule, and nothing in the "
        "sim should ever read it.",
    "mounts.Mount.axis":
        "The thrust vector of an individual mount. `sim/thrusters.py` sums "
        "thrust and `sim/attitude.py` points the hull, and neither models a "
        "hull flying lopsided because one engine of a pair is out — which is "
        "what this field is for. Task #85 holds the work; the field stays "
        "because deleting it would delete the geometry the work needs.",
    "consorts.ConsortOrder.shield":
        "How hard a consort holds station between you and the enemy, as "
        "against `draw`, which decides who gets shot at. Wired in this cycle "
        "for the flag's own damage; the *consort's* own risk from interposing "
        "is task #86.",
    "lessons.Lesson.skip_if":
        "A watcher naming a thing already true, so a tutorial step can skip "
        "itself. Task #87: the tutorial's step machinery advances on watchers "
        "firing, and skipping needs it to evaluate one at entry instead.",
}


def _fields() -> list[tuple[str, str, int]]:
    """Every field declared on a dataclass in `data/`: (path, name, line)."""
    out = []
    for path in sorted((pathlib.Path("seedfall") / "data").glob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not isinstance(item, ast.AnnAssign):
                    continue
                if not isinstance(item.target, ast.Name):
                    continue
                name = item.target.id
                if name.startswith("_"):
                    continue
                out.append((f"{path.stem}.{node.name}.{name}", name,
                            item.lineno))
    return out


class _Lum:
    """A stand-in carrying only a star brightness, for `Viewport.glare`."""

    def __init__(self, lum: float):
        self.star_lum = lum


class _Crew:
    """A stand-in officer carrying only a lineage, for `crew.tedium`."""

    def __init__(self, lineage: str):
        self.lineage = lineage


def _sources() -> str:
    """Every line of the package that is not a test, as one blob."""
    root = pathlib.Path("seedfall")
    return "\n".join(p.read_text() for p in sorted(root.rglob("*.py"))
                     if "tests" not in p.parts)


def run(suite: Suite) -> None:
    check = suite.check

    @check("nothing is declared in the tables and read by nobody")
    def _():
        # Read as `.name` anywhere in the package outside the tests. That is
        # deliberately generous — a field named the same as an unrelated
        # attribute counts as read, so this under-reports rather than crying
        # wolf. It still found eight.
        blob = _sources()
        fields = _fields()
        assert len(fields) > 300, len(fields)

        dead = []
        for full, name, line in fields:
            if len(re.findall(r"\." + re.escape(name) + r"\b", blob)) == 0:
                dead.append((full, line))

        unexplained = [(f, ln) for f, ln in dead if f not in ALLOWED]
        assert not unexplained, (
            f"{len(unexplained)} field(s) declared in the tables and read by "
            "nothing. Wire each one up, delete it, or add it to ALLOWED with "
            f"a reason: {[f for f, _ln in unexplained]}")

        # And the allowlist has to stay honest in the other direction: an
        # entry for a field that *is* now read is a stale excuse, and an entry
        # for a field that no longer exists is a lie about the tables.
        names = {full for full, _name, _ln in fields}
        stale = [f for f in ALLOWED if f not in names]
        assert not stale, (
            f"ALLOWED names fields that no longer exist: {stale}")
        revived = [f for f in ALLOWED if f not in {d for d, _ln in dead}]
        assert not revived, (
            f"ALLOWED still excuses fields that are now read — delete the "
            f"entry: {revived}")
        for full, why in ALLOWED.items():
            assert len(why) > 60, (
                f"{full} is excused with {len(why)} characters. An allowlist "
                "entry without a real reason is how this check gets defeated.")
        return (f"{len(fields)} fields declared, {len(dead)} unread and every "
                f"one of them explained ({len(ALLOWED)} entries)")

    @check("a bright star lights the picture harder than a dim one")
    def _():
        # `luminosity` said in its own docstring that it "drives how hard the
        # light falls on everything else, which is why an M dwarf's worlds are
        # dim and an A-type's are glaring". It drove nothing: every world in
        # the sector was lit identically.
        #
        # Differenced against the *same* world at the *same* range under the
        # same geometry, with only the star's brightness changed — so what is
        # measured is the light and not a different picture.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication

        from ..core.state import new_game
        from ..data.starclasses import STAR_CLASSES
        from ..sim import conn as conn_sim
        from ..sim import track as track_sim
        from ..ui.viewport import Viewport

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("glare")
        body = max(game.system.bodies, key=lambda b: b.radius_km)
        index = game.system.bodies.index(body)
        contact = next(c for c in track_sim.contacts(game, game.system)
                       if c.body_index == index)

        def brightest_tenth(lum: float) -> float:
            conn = conn_sim.start(game, contact,
                                  range_km=body.radius_km * 6.0)
            conn.star_lum = lum
            view = Viewport(conn, "fore")
            view.resize(300, 300)
            image = view.grab().toImage()
            vals = sorted(sum(image.pixelColor(x, y).getRgb()[:3])
                          for x in range(0, 300, 2) for y in range(0, 300, 2))
            top = vals[-len(vals) // 10:]
            return sum(top) / len(top)

        # Standing off the world, not on top of it: at approach range the hull
        # is inside the disc and no face lands in frame at all, which is how a
        # first attempt at this measurement read identical for every class.
        seen = [(cid, STAR_CLASSES[cid].luminosity,
                 brightest_tenth(STAR_CLASSES[cid].luminosity))
                for cid in ("M", "K", "G", "F", "A")]
        for (_a, la, ba), (_b, lb, bb) in zip(seen, seen[1:]):
            assert lb > la and bb >= ba, (
                f"a {lb}-luminosity star lights the picture to {bb:.1f} "
                f"against {ba:.1f} for a {la} one — brightness is not "
                "reaching the light")
        dim, bright = seen[0][2], seen[-1][2]
        assert bright > dim * 1.05, (
            f"an A-type lights the frame to {bright:.1f} against an M dwarf's "
            f"{dim:.1f} — the difference is not visible")

        # The conn records the brightness itself, for the system it is in.
        # Everything above sets `star_lum` by hand, so a mutation that stopped
        # `conn.start` reading it off the star passed the lot.
        for seed in range(6):
            other = new_game(f"lum-{seed}")
            spot = next(c for c in track_sim.contacts(other, other.system)
                        if c.body_index == 0)
            live = conn_sim.start(other, spot)
            want = STAR_CLASSES[other.system.star].luminosity
            assert abs(live.star_lum - want) < 1e-9, (
                f"{other.system.name} is a {other.system.star}-type with "
                f"luminosity {want} and the conn recorded {live.star_lum}")

        # And the compression is doing its job: the raw range is five hundred
        # to one and the picture must not be a white rectangle at one end or
        # black at the other.
        view = Viewport(conn_sim.start(game, contact), "fore")
        assert 0.5 <= view.glare(_Lum(0.0002)) <= 0.7, view.glare(_Lum(0.0002))
        assert 1.3 <= view.glare(_Lum(22.0)) <= 1.5, view.glare(_Lum(22.0))
        return (" · ".join(f"{cid} {b:.0f}" for cid, _l, b in seen)
                + f" — {bright / dim:.2f}x from an M dwarf to an A-type")

    @check("a star's corona is its own colour, not its disc's")
    def _():
        # Two colours per class have been in `data/starclasses.py` since it
        # was written, and the window drew the corona in the *core* colour, so
        # `halo` did nothing: every star's corona was its own disc, blurred.
        from ..core.state import new_game
        from ..data.starclasses import STAR_CLASSES
        from ..sim import sky as sky_sim

        differ = same = 0
        for cid, spec in STAR_CLASSES.items():
            assert spec.core.startswith("#") and spec.halo.startswith("#"), cid
            if spec.core.lower() != spec.halo.lower():
                differ += 1
            else:
                same += 1
        assert same == 0, (
            f"{same} of {differ + same} classes have a corona the same colour "
            "as the disc, so for those two colours do one colour's work. A "
            "first draft of this allowed one to slip through by asking for "
            "'at least eight of nine'.")

        # And the sky carries it, for every class the generator makes.
        carried = 0
        for seed in range(12):
            game = new_game(f"corona-{seed}")
            star = next(s for s in sky_sim.build(game, None)
                        if s.kind == "star")
            spec = STAR_CLASSES[game.system.star]
            assert star.halo == spec.halo, (star.halo, spec.halo)
            assert star.tint == spec.core, (star.tint, spec.core)
            carried += star.halo != star.tint
        assert carried == 12, (
            f"only {carried} of twelve skies carry a corona colour distinct "
            "from the disc")

        # And the *window* uses it. Everything above is the data path; a
        # mutation that made the corona fall back to the disc's colour passed
        # all of it, because nothing here had looked at a picture.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication

        from ..sim import conn as conn_sim
        from ..sim import track as track_sim
        from ..ui.viewport import Viewport
        app = QApplication.instance() or QApplication([])
        assert app is not None

        game = new_game("corona-seen")
        body = game.system.bodies[0]
        contact = next(c for c in track_sim.contacts(game, game.system)
                       if c.body_index == 0)
        spec = STAR_CLASSES[game.system.star]

        # `_star` alone, on a blank plate. A first draft measured the whole
        # camera frame and read (97, 64, 38) for both a red corona and a blue
        # one, because a frame at approach range is almost entirely the *world*
        # and the corona is a few dozen pixels of it. Isolating the thing under
        # test is the only way to see it.
        import dataclasses

        from PyQt6.QtGui import QColor, QImage, QPainter

        from ..ui import render3d

        conn = conn_sim.start(game, contact)
        star = next(s for s in conn.sky if s.kind == "star")
        camera = render3d.Camera(at=(0.0, 0.0, 0.0), forward=render3d.unit(star.at),
                                 up=(0.0, 0.0, 1.0), width=240, height=240,
                                 half_fov=0.55)
        view = Viewport(conn, "fore")

        def corona_hue(halo: str) -> tuple:
            plate = QImage(240, 240, QImage.Format.Format_RGB32)
            plate.fill(QColor("#000000"))
            painter = QPainter(plate)
            view._star(painter, camera, dataclasses.replace(star, halo=halo))
            painter.end()
            r = g = b = n = 0
            for x in range(0, 240, 2):
                for y in range(0, 240, 2):
                    px = plate.pixelColor(x, y)
                    if px.red() + px.green() + px.blue() > 24:
                        r += px.red(); g += px.green(); b += px.blue(); n += 1
            return (r // max(n, 1), g // max(n, 1), b // max(n, 1)), n

        warm, n_warm = corona_hue("#ff2000")
        cold, n_cold = corona_hue("#0020ff")
        assert n_warm > 40 and n_cold > 40, (
            f"the star drew {n_warm} and {n_cold} lit pixels — it is not in "
            "frame, so nothing is being measured")
        apart = sum(abs(a - b) for a, b in zip(warm, cold))
        assert apart > 40, (
            f"a red corona and a blue one paint the same star ({warm} against "
            f"{cold}) — the window is not using `halo`")
        return (f"{differ} classes with a corona of their own, carried into "
                f"{carried} of twelve skies; a red corona and a blue one "
                f"differ by {apart} in the picture")

    @check("a long crossing is harder on some crews than others")
    def _():
        # `boredom` has been declared per lineage since the tables were
        # written — 0.012 a day for a wet crew, 0.006 for a graft, nothing at
        # all for a lineage of recordings — and its docstring said it was
        # "what that costs in morale". `crew.morale_tick` had no lineage term
        # at all, so a hundred days in a hull was the same to everybody.
        from ..core.state import new_game
        from ..data import lineages
        from ..sim import crew as crew_sim
        from ..sim import transit as transit_sim

        def cross(lineage_id: str) -> float:
            # The SAME chronicle every time. Only who is aboard differs, so
            # what is measured is the lineage and not a different voyage.
            game = new_game("tedium")
            for officer in game.officers:
                officer.lineage = lineage_id
            game.ship.cargo["volatiles"] = 999
            game.credits = 500_000
            body = max(range(len(game.system.bodies)),
                       key=lambda i: game.system.bodies[i].orbit)
            begun = transit_sim.begin(game, body, "coast")
            assert begun.get("ok"), begun
            run = begun["transit"]
            for _ in range(60):
                transit_sim._spend(game, run, days=5)
                if game.dead:
                    break
            return game.ship.morale

        got = [(lid, lineages.LINEAGES_BY_ID[lid].boredom, cross(lid))
               for lid in ("wet", "grafted", "dry")]
        for (la, ba, ma), (lb, bb, mb) in zip(got, got[1:]):
            assert bb < ba, (la, lb)          # the table's own ordering
            assert mb > ma + 0.02, (
                f"a {lb} crew ends the same crossing at {mb:.3f} morale "
                f"against a {la} crew's {ma:.3f} — the lineage is not being "
                "felt")
        # And the raw rule is the one the table states.
        assert crew_sim.tedium([], 100) > 0, "an empty bridge feels nothing"
        wet = crew_sim.tedium(
            [_Crew("wet")], 100)
        assert abs(wet - lineages.LINEAGES_BY_ID["wet"].boredom * 100) < 1e-9
        return " · ".join(f"{lid} {m:.3f}" for lid, _b, m in got) + \
            " morale after the same 300-day crossing"

    @check("the crew say how a long crossing feels, and only a long one")
    def _():
        # A line per lineage, written in the tables and never once shown.
        from ..core.state import new_game
        from ..data import lineages
        from ..sim import crew as crew_sim
        from ..sim import transit as transit_sim

        game = new_game("felt")
        for officer in game.officers:
            officer.lineage = "dry"
        # Absolute days, not `TEDIUM_WORTH_SAYING - 1`. Reading the bar off
        # the constant under test is how a check passes for any value of it:
        # set the constant to zero and `how_it_feels(-1)` is still silent, so
        # the relative form could not fail. Ten days is a hop by any reading.
        short = crew_sim.how_it_feels(game, 10)
        long = crew_sim.how_it_feels(game, 90)
        assert not short, (
            f"a ten-day hop got a line about the nature of time: {short!r}")
        assert crew_sim.TEDIUM_WORTH_SAYING > 10, (
            f"the floor is {crew_sim.TEDIUM_WORTH_SAYING} days, which makes a "
            "hop philosophical")
        assert long == lineages.LINEAGES_BY_ID["dry"].time_sense, long

        # Every lineage has one, and they are not the same line.
        lines = {lid: spec.time_sense
                 for lid, spec in lineages.LINEAGES_BY_ID.items()}
        assert all(lines.values()), [k for k, v in lines.items() if not v]
        assert len(set(lines.values())) == len(lines), lines

        # And a real crossing puts it in the log where a player would see it.
        # Whichever crossing in this system is actually long enough to be
        # remarked on — the outermost body is not automatically the longest
        # trip, and a first draft picked a 29-day hop against a 30-day floor.
        game.ship.cargo["volatiles"] = 999
        from ..sim import flight as flight_sim
        best, longest = None, 0
        for index, world in enumerate(game.system.bodies):
            days = flight_sim.quote(game, world, "coast")["days"]
            if days > longest:
                best, longest = index, days
        assert longest >= crew_sim.TEDIUM_WORTH_SAYING, (
            f"the longest crossing in this system is {longest} days, under the "
            f"{crew_sim.TEDIUM_WORTH_SAYING} that gets a line")
        begun = transit_sim.begin(game, best, "coast")
        assert begun.get("ok"), begun
        said = [text for _day, text, _kind in begun["transit"].log]
        assert any(line == lines["dry"] for line in said), said
        return (f"{len(lines)} lineages, {len(set(lines.values()))} distinct "
                "lines, and the crossing log carries the right one")

    @check("the check can still see a dead field when there is one")
    def _():
        # The mutation-proofing, in the check itself: a guard that cannot fail
        # is worse than no guard, and this one is a text search over source
        # that could quietly stop matching anything at all.
        blob = _sources()
        fields = _fields()
        # A name nothing could possibly read.
        invented = "quinquireme_of_nineveh"
        assert len(re.findall(r"\." + re.escape(invented), blob)) == 0
        # And the machinery finds real fields, with real readers.
        by_name = {name for _full, name, _ln in fields}
        for known in ("radius_km", "cost", "blurb"):
            assert known in by_name, known
            assert len(re.findall(r"\." + re.escape(known) + r"\b", blob)) > 3, \
                known
        return (f"{len(by_name)} distinct field names; an invented one reads "
                "as unread and three known ones as read")
