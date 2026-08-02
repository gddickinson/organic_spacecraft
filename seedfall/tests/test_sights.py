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
        class M:
            def horizontalAdvance(self, _t): return 40
        return M()


def run(suite: Suite) -> bool:
    try:
        import PyQt6  # noqa: F401
    except ImportError as err:
        print(f"── sights ───\n  skipped: PyQt6 not available ({err})\n")
        return False

    check = suite.check

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

        # Far enough apart and both are drawn. `CLEAR` is the rule.
        apart = [((0.0, 100.0, 0.0), "Alpha", True),
                 ((viewport_mark.CLEAR * 2, 100.0, 0.0), "Beta", False)]
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
        # The same for the ring.
        assert viewport_mark.draw(_Blind(), ((900.0, 100.0, 0.0), "Wide"),
                                  project, cam, 464, 260) is False
        return "ahead is drawn; eighty degrees off the nose is not"

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
