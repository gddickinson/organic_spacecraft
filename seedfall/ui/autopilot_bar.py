"""The autopilot, reachable from every screen a hand can fly from.

The player's report: "it isn't easy to turn the auto-pilot on from every
flight-related screen." Measured, they were being kind — the bridge offered
two of the five modes, the helm only a docking shortcut, and the approach
window none at all, each with its own arming logic. This is the one bar:
every mode the computer flies, one Manual button, the same labels and the
same toggle on every screen, all through `flight_clock.arm_mode`.

The buttons read the flight (`Conn.auto`, `flightdeck.can_arm`), so a bar on
the helm and a bar on the approach window cannot disagree — they are the
same facts worn twice. A mode the computer would refuse is greyed with the
reason on it; the lit mode wears `▶` and pressing it lets go; **Manual**
always works and reads lit when nothing is armed, so "is the computer
flying" has one obvious answer and one obvious exit.
"""

from __future__ import annotations

from ..sim import flightdeck as deck_sim
from ..sim import instruments as panel_sim
from . import flight_clock
from .widgets import button, light


#: The modes, in the order a pilot reaches for them. "Run for" appears only
#: when a course is laid — it needs the mark.
MODES = (("null", "Hold station"), ("brake", "Brake to zero"),
         ("close", "Close and berth"), ("orbit", "Make orbit"),
         ("depart", "Move away"))


def dockable(game):
    """The quay the computer could take her into from here, if any."""
    from ..sim import berthing as berth_sim
    from ..sim import track as track_sim
    for c in track_sim.contacts(game):
        if c.kind == "anchorage" and berth_sim.can_conn(game, c)[0]:
            return c
    return None


def dock(win, contact) -> None:
    """One button, one system: the conn on the quay, `close` armed.

    The same act from the helm, the system screen or anywhere else — the
    docking mini-game remains as the *hand-flown* alternative for standing;
    this is the computer doing the same job through the same conn.
    """
    from .conn_window import open_conn
    window = open_conn(win, contact)
    window._auto("close")


def buttons(win) -> list:
    """The bar's buttons for the live flight, ready to lay out.

    Empty when nothing is being flown — a screen with no flight has nothing
    to arm. Rebuilt by the host screen's own refresh, which every flying
    screen already does on a beat.
    """
    conn = win.conn
    if conn is None or conn.landed:
        return []
    armed = conn.auto or ""
    out = []
    rows = list(MODES)
    if getattr(conn, "mark", ""):
        rows.append(("run", f"Run for {conn.mark}"))
    for mode, text in rows:
        btn = button(f"▶ {text}" if armed == mode else text,
                     lambda _=False, m=mode: flight_clock.arm_mode(win, m),
                     kind="flat")
        btn.setObjectName(f"auto_{mode}")
        btn.setProperty("base", text)
        ok, why = deck_sim.can_arm(win.game, conn, mode)
        btn.setEnabled(ok or armed == mode)
        btn.setToolTip(why if not ok else "")
        light(btn, armed == mode)
        out.append(btn)
    off = button("Manual", lambda: flight_clock.arm_mode(win, None),
                 kind="flat",
                 tip="The computer lets go; the pad and the keys are yours. "
                     "A held thruster always outranks the computer anyway.")
    off.setObjectName("auto_off")
    light(off, not armed, "warn")
    out.append(off)
    return out


def sync(win, btns) -> None:
    """Relight an already-built bar from the flight — for a screen that
    updates on the beat without rebuilding (the helm, the approach view)."""
    conn = win.conn
    if conn is None or not btns:
        return
    armed = conn.auto or ""
    for btn in btns:
        mode = btn.objectName()[5:]
        if mode == "off":
            light(btn, not armed, "warn")
            continue
        base = btn.property("base") or btn.text()
        btn.setText(f"▶ {base}" if armed == mode else base)
        light(btn, armed == mode)


def said(win) -> str:
    """One line for a host screen's note: what the computer is doing now."""
    conn = win.conn
    if conn is None or conn.landed:
        return ""
    return "Computer: " + panel_sim.computer_note(conn)
