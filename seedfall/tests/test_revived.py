"""What the revived fields actually do, now that something reads them.

`test_declared.py` next door asks the general question — is anything declared in
the tables and read by nobody? — and has now been asked of `data/`, `sim/`,
`world/` and `core/`. This holds the specific claims for the fields it found and
that were then wired up, because a guard that says "somebody reads it" is not the
same as a check that says "and this is what it does".

Split out when the two together went past five hundred lines. The seam is the
real one: above, a sweep; here, the behaviour.
"""

from __future__ import annotations

from .harness import Suite


class _Lum:
    """A stand-in carrying only a star brightness, for `Viewport.glare`."""

    def __init__(self, lum: float):
        self.star_lum = lum


class _Crew:
    """A stand-in officer carrying only a lineage, for `crew.tedium`."""

    def __init__(self, lineage: str):
        self.lineage = lineage


def run(suite: Suite) -> None:
    check = suite.check

    @check("every officer trait moves the stat it claims to")
    def _():
        # Seven traits, each declaring an effect key and a magnitude in
        # `crew.TRAITS`, and **not one of them was ever applied.**
        # `Officer.trait_id` was written when a candidate was generated and read
        # by nobody: `trait_name` and `trait_note` reached the crew screen, so a
        # Bloom veteran said "Was at Kessel's Reach and came back" and fought
        # exactly like anybody else. `make_officer` charges 25 a month for one.
        #
        # Differenced on the same hull and the same bridge with only the trait
        # changed, so what is measured is the trait.
        from ..core.state import new_game
        from ..sim import crew as crew_sim
        from ..sim.ship import stats

        #: Which stat each effect key is supposed to move.
        WATCH = {"diplomacy": "diplomacy", "repair": "regen", "trade": "trade",
                 "tactical": "accuracy", "accuracy": "accuracy",
                 "scan": "scan", "evade": "evade"}

        game = new_game("traits")
        assert game.officers, "no bridge to put a trait on"
        moved = {}
        for tid, _name, _note, key, mag in crew_sim.TRAITS:
            assert key in WATCH, (
                f"{tid} declares an effect {key!r} that names no stat — either "
                "it moves something or it should not be in the table")
            for officer in game.officers:
                officer.trait_id = None
            without = getattr(stats(game.ship, game.bonuses, game.officers),
                              WATCH[key])
            game.officers[0].trait_id = tid
            with_it = getattr(stats(game.ship, game.bonuses, game.officers),
                              WATCH[key])
            gap = with_it - without
            assert gap > 0, (
                f"the {tid} trait declares {mag} of {key} and moved "
                f"{WATCH[key]} by {gap:+.4f} — it is still decoration")
            # Roughly its declared magnitude, allowing for the multipliers some
            # stats carry (evade is scaled by brownout and loading).
            assert gap <= mag * 1.35 + 1e-9, (
                f"the {tid} trait declares {mag} and moved {WATCH[key]} by "
                f"{gap:+.4f} — more than it says it does")
            moved[tid] = gap
        for officer in game.officers:
            officer.trait_id = None

        # And the bridge sums: two of the same trait beat one.
        game.officers[0].trait_id = "quiet"
        one = stats(game.ship, game.bonuses, game.officers).scan
        game.officers[1].trait_id = "quiet"
        two = stats(game.ship, game.bonuses, game.officers).scan
        assert two > one, (
            f"two quiet officers scan {two:.4f} against {one:.4f} for one — a "
            "bridge is a sum, not a set")

        # A retired officer takes their trait with them.
        game.officers[1].retired = True
        assert stats(game.ship, game.bonuses, game.officers).scan == one, (
            "a retired officer is still lending the ship their trait")
        return " · ".join(f"{t} {g:+.3f}" for t, g in moved.items())

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

