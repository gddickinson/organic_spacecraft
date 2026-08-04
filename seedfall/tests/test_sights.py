"""The rules for drawing what is out there: one name per spot, inside the frame.

Split out of `tests/test_bridge.py`, which is about the screen. This is about
`ui/viewport_mark`: given a bearing and a camera, is anything drawn, where, and
what is dropped.

Pure geometry — no window is shown and no paint device is needed, which
matters: `ui/painting.Painted` declines to draw at all when the platform
refuses a backing store, and a check that depends on a successful paint goes
red on correct code late in a long run. That happened once already.
"""

from __future__ import annotations

from .harness import Suite

class _Blind:
    """A painter that records nothing: what is under test is the count."""

    def setPen(self, *a): pass
    def setBrush(self, *a): pass
    def setFont(self, *a): pass
    def drawEllipse(self, *a): pass
    def drawLine(self, *a): pass
    def drawText(self, *a): pass

    def fontMetrics(self):
        return _Metrics()


class _Metrics:
    """The mono font at 6 pt, close enough to reason about.

    **The old stub returned 40 for every string**, which made it structurally
    incapable of showing the bug it was guarding: a rule that is wrong only
    for long names cannot fail against a font where every name is the same
    width. Measured on the real font — "A" 5 px, "Fleet Hub" 43, "Held Breath
    II" 67, "Second Signature" 77, height 9, ascent 7 — that is about 4.8 px a
    character, so 5 is honest and errs wide.
    """

    PER_CHAR = 5

    def horizontalAdvance(self, text): return len(text) * self.PER_CHAR
    def height(self): return 9
    def ascent(self): return 7


def run(suite: Suite) -> bool:
    try:
        import PyQt6  # noqa: F401
    except ImportError as err:
        print(f"── sights ───\n  skipped: PyQt6 not available ({err})\n")
        return False

    check = suite.check

    @check("the Conn window names what is out there, and names it once")
    def _():
        # **The player's report, in the other window.** `ui/viewport_mark`
        # gave the Pilot screen its names; measured afterwards on the Conn,
        # 130.3 km off the Fleet Hub with a gate at the same range and a hull
        # 4,726 km out, `screen.sights` was `()` — a starfield, the system
        # star and an unnamed crosshair.
        from ..ui.conn_window import open_conn
        from .test_pilot_screen import _bridge

        _game, win, view = _bridge("connsights")
        view.use_main = True
        for _ in range(40):
            view.burn("forward")
        window = open_conn(win)
        try:
            named = [n for _v, n, _near in window.screen.sights]
            assert named, "the Conn's main screen names nothing at all"

            # **And the target is not named twice.** `Viewport._target` draws
            # its own reticle reading "Fleet Hub · 130.3 km"; the first draft
            # printed "Fleet Hub" as a sight on top of it, a pixel apart.
            aim = window.conn.target.name
            assert aim not in named, (
                f"{aim} is named by the reticle and again as a sight: {named}")

            # The compact feeds are 120 px wide. A name on one is not
            # readable, so they are left bare on purpose.
            assert all(f.sights == () for f in window.feeds.values()), (
                "the thumbnail feeds were given labels they have no room for")
        finally:
            window.close()
        return f"the Conn names {len(named)} contacts, none of them its target"

    @check("both windows ask one door what gets a name")
    def _():
        # Read from the source, not from a picture: the two screens disagreeing
        # about the same scene is what started all of this, and a re-implemented
        # rule in one of them is how it would come back.
        import inspect
        from ..ui import conn_window, pilot_panels, sights as sights_mod

        for where in (inspect.getsource(pilot_panels.aim_feed),
                      inspect.getsource(conn_window.ConnWindow.refresh)):
            assert "out_there" in where, (
                "a screen is choosing its own sights instead of asking "
                "ui/sights")
        # And the mark is handed over as already-named, so a laid course does
        # not wear its name twice either.
        assert "skip=" in inspect.getsource(pilot_panels.aim_feed), (
            "the Pilot screen does not tell ui/sights what it already names")

        # The rule itself: what the window draws for itself is dropped.
        from .test_pilot_screen import _bridge
        game, _win, view = _bridge("skipmark")
        view.fly_at(view.in_view()[0])
        rows, aim = view.ranged(), view.marked()
        out = sights_mod.out_there(game, view.conn, rows, skip=(aim,))
        assert aim is not None and aim.name not in [n for _v, n, _k in out], (
            f"the laid course is drawn as a ring and named again: {aim}")
        return "one door, and what a window draws itself it does not repeat"

    @check("a label is kept clear by its own width, not by a fixed box")
    def _():
        # **The rule used to be one 46-pixel box compared centre to centre**,
        # and measured against the real font it was wrong both ways. A label
        # is 9 px tall, so vertically it over-rejected by five times; and a
        # label reaches `8 + width` from its dot — 85 px for "Second
        # Signature" at 77 — so horizontally it under-rejected by up to 39.
        # Rendered, "Held Breath II" ran into the target reticle.
        from ..ui import viewport_mark
        from ..ui.viewport_math import project

        cam = ((0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        # 50 px apart on screen: comfortably outside the old 46 px box, so the
        # old rule drew both whatever they were called.
        far = ((23.1, 100.0, 0.0), "B", False)
        short = [((0.0, 100.0, 0.0), "A", True), far]
        long_ = [((0.0, 100.0, 0.0), "Second Signature", True), far]
        assert viewport_mark.draw_sights(
            _Blind(), short, project, cam, 464, 260) == 2, (
            "two short names 50 px apart do not touch and must both be drawn")
        assert viewport_mark.draw_sights(
            _Blind(), long_, project, cam, 464, 260) == 1, (
            "a 16-character name reaches 88 px and must not be drawn over "
            "the sight 50 px to its right")

        # And the other way: 21.6 px apart vertically is clear for a 9 px
        # label, and the old box threw one of them away.
        stacked = [((0.0, 100.0, 0.0), "A", True),
                   ((0.0, 100.0, 10.0), "B", False)]
        assert viewport_mark.draw_sights(
            _Blind(), stacked, project, cam, 464, 260) == 2, (
            "two names a clear 21 px apart vertically were merged")
        return ("50 px apart: two short names drawn, one long one; 21 px "
                "apart vertically both drawn")

    @check("a sight is not drawn on the reticle that already names the target")
    def _():
        # Rendered on the Conn's aft camera at 130.3 km: `Viewport._target`
        # draws a dashed bracket labelled "Fleet Hub · 130.3 km", and a sight
        # label landed across it. `_target` hands back the box it used and
        # `draw_sights` keeps off it.
        import inspect
        from ..ui import viewport, viewport_mark
        from ..ui.viewport_math import project

        cam = ((0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        one = [((0.0, 100.0, 0.0), "Held Breath II", True)]
        assert viewport_mark.draw_sights(
            _Blind(), one, project, cam, 464, 260) == 1, "nothing drawn at all"
        # The same sight, with the reticle sitting where it would land.
        assert viewport_mark.draw_sights(
            _Blind(), one, project, cam, 464, 260,
            [(200.0, 100.0, 320.0, 160.0)]) == 0, (
            "a sight was drawn across the target's own bracket")

        # **And the window really does hand the box over.** Read the call
        # itself, not the word: the first draft asserted `"taken" in src`,
        # which stays true when the argument is dropped from the call and the
        # local left behind. That mutation survived.
        import ast as _ast
        import textwrap
        tree = _ast.parse(textwrap.dedent(
            inspect.getsource(viewport.Viewport.draw)))
        calls = [n for n in _ast.walk(tree) if isinstance(n, _ast.Call)
                 and getattr(n.func, "attr", "") == "draw_sights"]
        assert calls, "the viewport never draws sights at all"
        assert len(calls[0].args) == 7, (
            f"draw_sights is called with {len(calls[0].args)} arguments — the "
            f"reticle's box is not among them")
        assert "return (sx - box" in inspect.getsource(viewport.Viewport._target), (
            "_target does not report the pixels its reticle took")
        return "a sight that would land on the reticle is dropped"

    @check("two things on the same bearing do not print over each other")
    def _():
        # **Measured on one scene**: four hulls — Second Signature, Margin
        # Call, Long Consent and Quiet Increment — projected to *exactly the
        # same pixel*, dx=0 dy=0, because they are hundreds of millions of
        # kilometres off in almost the same direction. Four names stacked on
        # one spot is worse than three of them missing, and nothing is lost:
        # the "In view" board lists every one with its range.
        from ..ui import viewport_mark
        from ..ui.viewport_math import project

        cam = ((0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        same = [((0.0, 100.0, 0.0), "Alpha", True),
                ((0.0, 200.0, 0.0), "Beta", False),
                ((0.0, 300.0, 0.0), "Gamma", False)]
        drew = viewport_mark.draw_sights(_Blind(), same, project, cam, 464, 260)
        assert drew == 1, (
            f"three contacts on one bearing drew {drew} labels on one pixel")

        # Far enough apart and both are drawn. (160 puts the second one off
        # the frame entirely at this focal length — `_screen` drops it and the
        # check passes for the wrong reason. 40 lands it at x=319 of 464.)
        apart = [((0.0, 100.0, 0.0), "Alpha", True),
                 ((40.0, 100.0, 0.0), "Beta", False)]
        assert viewport_mark.draw_sights(
            _Blind(), apart, project, cam, 464, 260) == 2, (
            "two contacts well apart were merged into one")

        # And nearest wins, because `sights` arrives nearest first.
        seen = []

        class Naming(_Blind):
            def drawText(self, _at, name):
                seen.append(name)

        viewport_mark.draw_sights(Naming(), same, project, cam, 464, 260)
        assert seen == ["Alpha"], f"the further one won: {seen}"
        return "three on one bearing draw one name, the nearest"

    @check("a sight outside the frame is not drawn off the edge of it")
    def _():
        # `project` returns a point for anything with a positive component
        # along the view axis, so a contact eighty degrees off the nose comes
        # back at x=2,000 in a 464-pixel window. Measured before this: the
        # fore camera reported one sight drawn and showed none.
        from ..ui import viewport_mark
        from ..ui.viewport_math import project

        cam = ((0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        ahead = [((0.0, 100.0, 0.0), "Ahead", True)]
        assert viewport_mark.draw_sights(
            _Blind(), ahead, project, cam, 464, 260) == 1

        # Ahead of the lens, and a long way off to the side.
        wide = [((900.0, 100.0, 0.0), "Wide", True)]
        assert viewport_mark.draw_sights(
            _Blind(), wide, project, cam, 464, 260) == 0, (
            "a contact far outside the frame was drawn past the edge of it")
        # **The ring is allowed one thing a sight is not**, and this is the
        # line between them. A mark just past the edge gets a chevron on the
        # frame pointing the way to turn, because six cameras leave blind
        # cones between them and a course laid on something in one of those
        # was ringed nowhere at all. A mark *this* far out — eighty degrees
        # off the nose, thousands of pixels beyond a 464-pixel window — is
        # beside you rather than ahead, and gets nothing, exactly as a sight
        # does. See `viewport_mark.POINTER_REACH`.
        assert viewport_mark.draw(_Blind(), ((900.0, 100.0, 0.0), "Wide"),
                                  project, cam, 464, 260) is False
        near = ((0.6, 1.0, 0.55), "Just off")
        assert viewport_mark.draw(_Blind(), near, project, cam, 464, 260), (
            "a mark just past the edge got no pointer, so a course laid in "
            "the gap between two cameras is shown nowhere")
        return ("ahead is drawn; just off the edge is pointed at; eighty "
                "degrees off the nose is not")

    @check("a mark behind the camera is not drawn in front of it")
    def _():
        # `project` returns None for anything at or behind the lens, and the
        # ring must respect that or a contact astern would be painted over
        # the stars ahead. Asked directly, because a picture cannot easily
        # prove the *absence* of a ring in the right place.
        from ..ui import viewport_mark
        from ..ui.viewport_math import project

        cam = ((0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        drawn = []

        class Fake:
            def setPen(self, *a): pass
            def setBrush(self, *a): pass
            def setFont(self, *a): pass
            def drawEllipse(self, *a): drawn.append("ring")
            def drawLine(self, *a): pass
            def drawText(self, *a): drawn.append("name")
            def fontMetrics(self):
                class M:
                    def horizontalAdvance(self, _t): return 60
                return M()

        assert viewport_mark.draw(Fake(), ((0.0, 5.0, 0.0), "ahead"),
                                  project, cam, 400, 300) is True
        assert "ring" in drawn and "name" in drawn, drawn
        drawn.clear()
        assert viewport_mark.draw(Fake(), ((0.0, -5.0, 0.0), "astern"),
                                  project, cam, 400, 300) is False
        assert not drawn, "a mark behind the camera was drawn anyway"
        assert viewport_mark.draw(Fake(), None, project, cam, 400, 300) is False
        assert viewport_mark.draw(Fake(), ((0.0, 0.0, 0.0), "here"),
                                  project, cam, 400, 300) is False
        return "ahead is ringed; astern, nothing, and a zero bearing are not"


    return True
