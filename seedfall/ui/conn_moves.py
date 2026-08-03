"""The acts that swap the conn's flight for another one.

Split out of `ui/conn_window.py` when the window went past five hundred lines,
along the seam these four share and nothing else does: each replaces
`game.conn` — with a fresh approach, a hand-over, a free flight, or nothing —
and each must first bill the flight it is replacing. `_leave_flight` is that
rule; the other three are the doors that come through it.

They are `ConnWindow` methods in module clothing — each takes the window as
`self` and is bound in the class body — so the buttons, the checks and the
window itself all drive exactly one implementation.
"""

from __future__ import annotations

from ..sim import berthing as berth_sim
from ..sim import conn as conn_sim
from .conn_targets import default_target


def _leave_flight(self) -> None:
    """Bill a live flight before anything replaces it.

    **Every door that swaps `game.conn` for a fresh one comes through here.**
    `_settle` returns early for an approach that is not over — so retargeting,
    reopening after a jump and "Fly free" all used to build the new `Conn`
    from the undebited tank: measured, four burns of mass came straight back
    when the target was changed. Nothing is flown for free means *nothing*.
    """
    conn = self.conn
    if conn is None or conn.landed:
        return
    if not conn.over:
        conn.outcome = "broken off"
        conn.log.append("Approach broken off.")
    berth_sim.commit(self.game, conn)


def _reopen(self) -> None:
    """Rebuild the approach after the ship has been flown somewhere."""
    self._leave_flight()
    self.win.set_conn_clock(False)
    contact = default_target(self.game)
    self.contact = contact
    if contact is None:
        self.conn, self.refused = conn_sim.observe(self.game), ""
    else:
        self.conn, self.refused = berth_sim.begin(self.game, contact)
        if self.conn is None:
            self.conn = conn_sim.observe(self.game)
    for feed in self.feeds.values():
        feed.conn = self.conn
    self.screen.conn = self.conn


def _pick_target(self) -> None:
    """Only what the ship is actually alongside. Everything else is a burn.

    The list used to offer every contact in the system, so a captain could
    open the conn on a hull eight AU away and fly the last ten kilometres of
    a journey they had not made.
    """
    near = [c for c in self.contacts if berth_sim.can_conn(self.game, c)[0]]
    # **Flying for its own sake is one of the choices.** With nothing in
    # reach this used to be a dead end — "plot a transfer first" — which is
    # true about *berthing* and was being said about *flying*. A captain may
    # take the conn whenever they like; there is nobody to ask permission of
    # to move your own ship.
    rows = [f"{c.name} — {c.detail}" for c in near[:12]]
    picked = self.win.dialog(
        "Approach which?",
        (["The conn is the last few kilometres. These are what the ship "
          "is already alongside."] if near else
         ["Nothing is within reach of the thrusters — but the ship is "
          "yours to fly."]) + rows,
        [(c.name, index) for index, c in enumerate(near[:6])]
        + [("Fly free — no destination", "free"), ("Cancel", None)])
    if picked is None:
        return
    if picked == "free":
        self._free_flight()
        return
    contact = near[picked]
    live = self.conn
    was_on = self.running
    from ..sim import freeflight as free_sim
    handed = (live is not None and not live.landed
              and free_sim.is_free(live))
    if handed:
        # A free flight is *handed over*, keeping the way she has on — the
        # same door opening the window on a contact uses. The old flight is
        # absorbed, meters and all, so it is not broken off.
        fresh, why = free_sim.hand_over(self.game, live, contact)
    else:
        # Bill what the live approach has burned *before* the fresh one
        # reads the tank — `begin` records the hold as its opening mass, and
        # an unbilled spend would open the new approach on tonnes the old
        # one already burned.
        if live is not None and not live.landed:
            berth_sim.charge_flown(self.game, live)
        fresh, why = berth_sim.begin(self.game, contact)
    if fresh is None:
        # **A refusal does not stop the ship.** This used to write the
        # `None` straight onto `game.conn`, destroying a live flight because
        # a quay said no — and file the reason in a field nothing read. The
        # flight keeps flying; the refusal is said out loud.
        self.refused = why
        self.win.toast(why or "Refused.", "warn")
        self.refresh()
        return
    if not handed:
        self._leave_flight()
    self.contact = contact
    self.conn, self.refused = fresh, ""
    for feed in self.feeds.values():
        feed.conn = self.conn
    self.screen.conn = self.conn
    # The clock survives a retarget: it is the flight's, and the flight goes
    # on under its new target.
    self.win.set_conn_clock(was_on)
    self.refresh()


def _free_flight(self) -> None:
    """Take the conn on open space: fly the ship because you want to.

    The same pad, the same cameras, the same tank — with no target and
    nothing to arrive at. It ends when the pilot secures.
    """
    from ..sim import freeflight as free_sim
    was_on = self.running
    self._leave_flight()
    conn, why = free_sim.begin(self.game)
    if conn is None:
        self.win.toast(why, "warn")
        return
    self.contact = None
    self.conn, self.refused = conn, ""
    self.win.set_conn_clock(was_on)
    # The window watches for the ship being moved out from under it; a free
    # flight *is* the ship being moved, so what it opened at has to be
    # brought up to date or the next refresh throws the flight away.
    self.opened_at = (self.game.location_id,
                      getattr(self.game, "orbit_body", None))
    for feed in self.feeds.values():
        feed.conn = self.conn
    self.screen.conn = self.conn
    self.win.toast("The conn is yours. No destination set.")
    self.refresh()
