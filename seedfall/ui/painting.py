"""One door for painting on a widget, and for surviving not being able to.

**Every painted widget in this project had the same latent crash.** A
`paintEvent` opens `QPainter(self)` and starts drawing. When Qt cannot hand out
a paint device — a zero-sized widget, or a backing store the platform refuses
late in a long process — `QPainter::begin` fails with "Paint device returned
engine == 0", and every call on that painter comes back from PyQt as *"first
argument of unbound method must have type 'QPainter'"*.

That exception is raised **inside** `paintEvent`, where Qt cannot propagate it.
It does not fail anything. It ends the process, wherever it happens to be. It
killed a 174-suite run four times, in three different suites, from two
different files — `ui/gauges.py` first and `ui/viewport.py` after that one was
guarded, which is what made it clear this is a class of fault rather than a
site.

**Asking first is not enough, measured.** A run with an `isActive()` check in
place still died *inside* the paint, three calls after the painter had said it
was active — so the device can go away mid-frame and no question asked
beforehand covers it. What works is owning the whole span: begin, check, draw,
catch, end.

A widget mixes in `Painted` and implements `draw`. It never touches the
painter's lifetime, and it cannot take the process down by failing to draw.
"""

from __future__ import annotations

from PyQt6.QtGui import QPainter

#: Every paint that did not happen: `(class, width, height, why)`.
#:
#: Kept rather than swallowed. A guard that catches everything is exactly the
#: shape of thing that turns a real regression green, so the checks read this
#: from both sides: a healthy widget with room to draw must record nothing, and
#: a draw that raises must appear here rather than reaching Qt.
MISSES: list = []


class Painted:
    """Mix in before the QWidget base. Implement `draw(p)`, not `paintEvent`."""

    def draw(self, p: QPainter) -> None:                 # pragma: no cover
        """What this widget paints. The painter is live for the whole call."""

    def began(self, p: QPainter) -> bool:
        """Whether there is anywhere to paint at all."""
        if p.isActive():
            return True
        MISSES.append((type(self).__name__, self.width(), self.height(),
                       "the painter never began"))
        return False

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        if not self.began(p):
            return
        try:
            self.draw(p)
        except (RuntimeError, TypeError) as err:
            MISSES.append((type(self).__name__, self.width(), self.height(),
                           repr(err)[:120]))
        finally:
            if p.isActive():
                p.end()
