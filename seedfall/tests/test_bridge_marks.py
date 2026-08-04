"""What the window says about the thing you are flying at.

Split out of `tests/test_bridge.py` when it passed five hundred lines. The
seam is a real one: the other file is about the *screen* — that it paints,
fits, counts its rebuilds and keeps a button under the pilot's finger. This
one is about the **mark**: naming what is out there, ringing the thing a
course is laid on, and saying in words what the computer is doing about it.

All three grew teeth when orbits gained a tilt (`sim/elements`). A contact
tens of degrees out of the plane is ringed in none of the six cameras unless
the window points off its own edge at it, and the computer closing on one
burns down whichever axes the correction wants rather than politely ahead.

**Everything here is measured on a window that has been `show()`n.** An
offscreen widget that was never shown reports a scroll range of zero and
answers every layout question "fine".
"""

from __future__ import annotations

from ..sim import conn as conn_sim
from ..sim import engage as engage_sim
from .harness import Suite
from .test_pilot_screen import _bridge
from .test_sights import _Blind


def run(suite: Suite) -> bool:
    try:
        import PyQt6  # noqa: F401
    except ImportError as err:
        print(f"── bridge marks ───\n  skipped: PyQt6 not available ({err})\n")
        return False

    check = suite.check

    @check("the quays and hulls out there are named, as the conn names its own")
    def _():
        # **A player reported this**: standing off the Fleet Hub, the conn
        # draws it inside a dashed reticle reading "Fleet Hub · 12.0 km", and
        # the Pilot window showed nothing at all. The sky data was never
        # missing — measured, a free flight's `sky` holds *more* than an
        # approach's, ten entries against nine, including the anchorages the
        # approach leaves out. `Viewport._target` gives a target its real size
        # and a free flight has no target, so the Hub was one 1.6-pixel speck
        # among the stars.
        from PyQt6.QtWidgets import QApplication
        from ..sim import track as track_sim
        game, win, view = _bridge("cmp")
        app = QApplication.instance()

        # **Moored, a quay used to be at *exactly* the ship's position**, and
        # this check said so — "there is no bearing to it and nothing to
        # draw, that is right, not a gap". It was not right. A quay sat at
        # its body's coordinates, which is the middle of the planet, and a
        # player found what that costs: the range to it read zero, so the
        # flight computer concluded it had arrived and would not move, and a
        # target at zero range subtends 180° and fills every camera at once.
        # `anchorage.berth_orbit` gives it a place of its own, so even from
        # the mooring there is a bearing and something to draw.
        view.refresh()
        hub = next(c for c in view.in_view() if c.kind == "anchorage")
        assert any(n == hub.name for _v, n, _near in view.feed.sights), (
            "the window was not told about the quay at all")
        moored_km = engage_sim.range_km(game, view.conn, hub)
        assert moored_km > 1.0, (
            f"{hub.name} is {moored_km:,.3f} km off — a quay standing at the "
            "centre of its own world again")

        # Fly out, and it must become something you can find.
        view.use_main = True
        for _ in range(90):
            view.burn("forward")
        view.refresh()
        for _ in range(3):
            app.processEvents()
        km = engage_sim.range_km(game, view.conn, hub)
        assert km > 100.0, f"the fixture never left: {km:,.0f} km"

        named = {n for _v, n, _near in view.feed.sights}
        assert hub.name in named, named
        assert any(c.kind == "hull" and c.name in named
                   for c in track_sim.contacts(game)), (
            f"no hull is named out of the window: {named}")
        # Worlds are not named: `_sky` draws those as lit discs and nobody
        # loses a planet.
        worlds = {c.name for c in track_sim.contacts(game) if c.kind == "body"}
        assert not (named & worlds), f"worlds are being labelled too: {named & worlds}"

        # **And the window actually paints them.** Comparing two grabs of the
        # same widget — one with sights, one without — proved nothing: the
        # images differed either way, so the check passed with the drawing
        # deleted. Ask the drawing itself instead, through the same `project`
        # and camera the window uses.
        from ..ui import viewport_mark
        from ..ui.viewport import basis
        from ..ui.viewport_math import project

        drew = 0
        for _vid, _label, vec in conn_sim.VIEWS:
            cam = basis(vec, view.conn)
            drew += viewport_mark.draw_sights(
                _Blind(), view.feed.sights, project, cam, 460, 260)
        assert drew, (
            "the window is told what is out there and paints none of it, in "
            "any of the six cameras")

        # **And the window calls it.** Asking the drawing directly proved only
        # that the drawing works — deleting the call from `Viewport.draw` left
        # this check green, because it was never testing the wiring.
        # Read the wiring rather than paint it: `Painted` declines to draw at
        # all when the platform refuses a backing store, and a check that
        # depends on a successful paint goes red on correct code.
        import inspect
        body = inspect.getsource(view.feed.draw)
        assert "viewport_mark.draw_sights(" in body, (
            "Viewport.draw never asks for the sights to be drawn")
        assert "self.sights" in body, (
            "it asks for sights to be drawn without handing them over")
        return (f"{len(named)} named at {km:,.0f} km off the quay, "
                f"{drew} of them landing in one of the six cameras")

    @check("the computer says what it is doing, and it changes as it does it")
    def _():
        # **It used to say six words the whole way in** — "running for Held
        # Breath" while the computer torched, braked and coasted in turn, so
        # a pilot could not tell accelerating from braking from arriving.
        from ..sim import freeflight as free_sim
        from ..ui import pilot_panels as panels
        game, _win, view = _bridge("auto")
        # **The furthest in the band, not the first.** This took whichever
        # hull came to hand, and once orbits gained a tilt that was often a
        # hop short enough for the thrusters — so the computer swung, nudged
        # and arrived without ever opening the main drive, and a check about
        # torching and braking had no torch in it. The claim needs a run long
        # enough to need one.
        reach = {c: engage_sim.range_km(game, view.conn, c)
                 for c in view.in_view() if c.kind == "hull"}
        target = max((c for c, km in reach.items() if 100 < km < 200_000),
                     key=lambda c: reach[c])
        assert panels._computer_says(view) == "off — she flies as you fly her"

        view.fly_at(target)
        view.set_auto("run")
        # **Sampled all the way down, not at four moments.** This took four
        # snapshots and asserted the first said "ahead" and a later one
        # "astern" — which held while the sector was one plane, because a
        # contact was then almost always somewhere near the nose. It is not a
        # fact about three dimensions: a mark tens of degrees out of the plane
        # is closed on down whichever axes the correction wants, and measured
        # on one run the computer opened the torch 340 times on *down*, *left*
        # and *back* and never once on ahead. The words were right and the
        # claim was wrong.
        #
        # What must hold is that the narration is the *record* — it names the
        # burn that happened — and that it moves as the flying does.
        said, matched = [], 0
        for _ in range(1400):
            view.tick()
            phrase = panels._computer_says(view)
            said.append(phrase)
            conn = view.conn
            # Only while it is still *running*: the beat she arrives on, the
            # mode hands back to "null" and the words become the holding
            # words, while `fired_axis` still carries the burn that got her
            # there. Both are right; they are answering different questions.
            if (view.auto == "run" and conn.fired_axis is not None
                    and not conn.fired_turning):
                which = conn_sim.AXES_BY_ID[conn.fired_axis][1].lower()
                assert which in phrase, (
                    f"it burned {which} and said {phrase!r}")
                assert ("the torch" in phrase) == bool(conn.fired_main), (
                    f"main={conn.fired_main} and it said {phrase!r}")
                matched += 1
            if view.auto == "null":
                break

        assert len(set(said)) > 2, (
            f"the computer said the same thing the whole way in: {set(said)}")
        assert matched > 20, f"only {matched} beats named a burn at all"
        # It really opens the main drive on a run of this length, and it
        # really coasts and swings as well — three different things to say.
        assert any("the torch" in t for t in said), (
            "it crossed seven thousand kilometres without the torch")
        assert any("thrusters" in t for t in said), said[:3]
        assert any("coming about" in t for t in said), said[:3]
        for phrase in said[:-1]:
            assert "running her in" in phrase, phrase
        # Arrived: it hands back — the flight's one name for holding, "null".
        assert view.auto == "null", view.auto
        assert "holding station" in said[-1], said[-1]

        # Holding station is not a course, and says its own thing.
        view.break_off()
        assert "holding station" in panels._computer_says(view)
        view.set_auto("hold")
        assert panels._computer_says(view).startswith("off"), (
            panels._computer_says(view))
        # The run in order, with each phrase said once: a thousand beats of
        # "coasting → astern on thrusters → coasting" is the same news three
        # hundred times, and a check's line has to be readable.
        seen, order = set(), []
        for phrase in (t.split(" — ")[-1] for t in said):
            if phrase not in seen:
                seen.add(phrase)
                order.append(phrase)
        return (f"{len(said)} beats, {matched} of them naming the burn on "
                f"record: " + " → ".join(order))

    @check("the thing you are flying at is ringed out of the window")
    def _():
        # **Measured before this existed: the picture did not change at all.**
        # A free flight has no `conn.target`, so `Viewport._target` returns at
        # once — "station keeping: there is no target, only sky" — and laying
        # a course rendered byte-identical. Out there everything is a point of
        # light and they all look alike, so "fly at that one" was a row of
        # text to cross-reference against a starfield.
        from PyQt6.QtWidgets import QApplication
        game, win, view = _bridge("mark")
        app = QApplication.instance()
        win.show()
        for _ in range(8):
            app.processEvents()
        try:
            target = next(c for c in view.in_view() if c.kind == "hull"
                          and 100 < engage_sim.range_km(game, view.conn, c)
                          < 200_000)
            # **Not by comparing two grabs.** Twice this cycle an image diff
            # of the same widget proved nothing — it differed with the
            # drawing deleted, and it matched with the drawing present when
            # other checks had run first. What the window is *told*, and
            # whether it *asks* for the ring, are both exact.
            from ..ui import viewport_mark
            assert view.feed.mark is None, "a ring before any course was laid"

            view.fly_at(target)
            view.refresh()
            for _ in range(4):
                app.processEvents()
            assert view.feed.mark is not None, "the window was told nothing"
            # "wears the name": the mark may carry the engagement band.
            assert view.feed.mark[1].startswith(target.name), \
                view.feed.mark[1]

            # **And the window asks for it.** Not by painting: `Painted`
            # returns early when the platform refuses a backing store, so a
            # grab-based check goes red on correct code late in a long run —
            # it did, once. The wiring is in the source and can be read.
            import inspect
            body = inspect.getsource(view.feed.draw)
            assert "viewport_mark.draw(" in body, (
                "Viewport.draw never asks for the ring to be drawn")
            assert "self.mark" in body, (
                "Viewport.draw asks for a ring without handing it the mark")

            # And it lands somewhere in the picture, in some camera.
            from ..ui.viewport import basis
            from ..ui.viewport_math import project
            drawn = sum(1 for _v, _l, vec in conn_sim.VIEWS
                        if viewport_mark.draw(_Blind(), view.feed.mark,
                                              project, basis(vec, view.conn),
                                              460, 260))
            assert drawn, f"{target.name} is ringed in none of the six cameras"

            # Breaking off takes the ring away again.
            view.break_off()
            view.refresh()
            for _ in range(4):
                app.processEvents()
            assert view.feed.mark is None, "the ring outlived the course"
        finally:
            win.hide()
        return f"{target.name} ringed, and the ring goes when the course does"

    return True
