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


def alive(widget, p: QPainter) -> bool:
    """Whether this painter began. **The guard for a widget that is not a
    `Painted`**, and there are thirteen of them.

    `Painted` was written for this and only the widgets that inherit it were
    protected; the rest construct `QPainter(self)` and draw. Measured, that
    is not academic: late in a long run `QPainter::begin` failed on the
    approach view, every later call on the dead painter raised inside
    `paintEvent`, and **Qt took the whole process down** — exit 134, after
    170 suites had passed, with the failure printed as an argument-overload
    error a hundred lines from the cause.

    Two lines at the top of a raw `paintEvent` retire that: the miss is
    recorded where the others are, and the frame is simply skipped.
    """
    if p.isActive():
        return True
    MISSES.append((type(widget).__name__, widget.width(), widget.height(),
                   "the painter never began"))
    return False


def safe_paint(fn):
    """Wrap a raw `paintEvent` so a frame that dies is recorded, not fatal.

    The other half of what `Painted` does, for the thirteen widgets that
    build their own `QPainter`. `alive` above catches the painter that never
    began; this catches the one that **dies mid-frame** — measured, the
    approach view's painter was live at the top of the frame and invalid by
    the time it drew a label, and the `TypeError` PyQt raises for a dead
    receiver escaped `paintEvent` and **took the process down**: exit 134
    with every one of 171 suites passing and nothing failing.

    A miss is a picture that did not happen. It belongs in `MISSES`, where
    the checks that care can read it, and nowhere near the process exit.
    """
    def wrapper(self, event):
        try:
            return fn(self, event)
        except (RuntimeError, TypeError) as err:
            MISSES.append((type(self).__name__, self.width(), self.height(),
                           repr(err)[:120]))
    wrapper.__name__ = getattr(fn, "__name__", "paintEvent")
    wrapper.__doc__ = fn.__doc__
    return wrapper


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
