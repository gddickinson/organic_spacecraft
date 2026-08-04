"""The traffic: who is calling, when it gets here, and what you say back.

**Nothing in the Verge ever spoke to the captain.** Things happened — a war
opened, a port woke, a power's regard crossed from cool to warm, a harbour
assigned a mast — and the only record was a line in the player's own log, in
the player's own voice, as though they had noticed it themselves. Traffic
control granted clearance without a word passing either way.

A `Signal` is somebody addressing you, and it has three parts the log never
had: **a sender**, **a delay**, and sometimes **a question**.

**The delay is the interesting one, and a gate does not help the way you
would expect.** A ring moves *mass*; it does not carry radio. Nothing is
broadcast through the Weave. So a despatch crosses it the only way anything
crosses it — **aboard something** — and what actually happens is a courier
boat waiting for a slot, transiting, and rebroadcasting on the far side.

That gives three regimes:

* **Inside a system**, a signal is a radio call and arrives the same day.
* **Across the lit Weave**, it is carried: per hop, the wait for the next
  despatch boat plus whatever queue that gate is working. A Charter gate
  reserves a third of twenty-two slots a day for despatches, so news moves
  through it in hours; an ancient ring cycles six times a day and takes its
  time. A busy anchor is slow news as well as a slow crossing, which is the
  honest consequence of carrying rather than broadcasting.
* **Off the network**, there is nothing to carry it and it goes at the speed
  of light: one year per light year. A system with no lit anchor is not
  merely awkward to reach — it is years out of date, and so are you while you
  sit in it, reading news that was true when you left.

That makes lighting an anchor a decision about *hearing* as well as
travelling, and it is why `weave.network` and `sim/gatetraffic` are asked
rather than a distance.

**What is stored is what was said.** Signals live on the chronicle because a
message you have not answered is state; nothing else here is stored. Who
would send what is derived from the world each day by comparing a handful of
watched facts against what has already been reported, so the traffic cannot
drift from the sector it describes and cannot repeat itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data import signals as sig_data


@register
@dataclass
class Signal:
    """One thing somebody said to you, and when it gets here."""

    id: str
    frm: str
    name: str
    channel: str
    subject: str
    body: str
    sent_day: float
    due_day: float
    #: Where it was sent from, for the delay and for the board to say.
    system_id: int = -1
    read: bool = False
    #: The answers offered, as `(key, words)`. Empty for traffic that is
    #: telling you rather than asking.
    replies: tuple = ()
    answered: str = ""

    @property
    def asks(self) -> bool:
        return bool(self.replies) and not self.answered

    def arrived(self, day: float) -> bool:
        return day >= self.due_day

    @property
    def stale_days(self) -> float:
        """How old this was by the time it reached you.

        The whole point of carrying a signal rather than broadcasting it: a
        despatch relayed across two lit anchors is hours old, and one that
        crawled out of an unlit system left before you were flying.
        """
        return max(0.0, self.due_day - self.sent_day)

    @property
    def note(self) -> str:
        """One phrase for a board about how far behind the news is."""
        old = self.stale_days
        if old < 0.04:
            return "live"
        if old < 1.0:
            return f"{old * 24:,.0f} h old"
        if old < 400.0:
            return f"{old:,.0f} d old"
        return f"{old / 365.0:,.1f} years old"


def _all(game) -> list:
    got = getattr(game, "signals", None)
    if got is None:
        got = []
        game.signals = got
    return got


def _marks(game) -> dict:
    got = getattr(game, "signal_marks", None)
    if got is None:
        got = {}
        game.signal_marks = got
    return got


# ── how long anything takes to arrive ──────────────────────────────────────

def hops(game, frm: int, to: int) -> int | None:
    """Lit-Weave hops between two systems, or None if there is no path.

    Both ends have to be burning for a link to work — `weave.network` says so
    — which is the whole reason an unlit anchor is worth lighting.
    """
    if frm == to:
        return 0
    from . import weave as weave_sim
    net = weave_sim.network(game)
    if frm not in net or to not in net:
        return None
    seen, edge, step = {frm}, [frm], 0
    while edge and step < 64:
        step += 1
        nxt = []
        for sid in edge:
            for other in net.get(sid, ()):
                if other == to:
                    return step
                if other not in seen:
                    seen.add(other)
                    nxt.append(other)
        edge = nxt
    return None


def carried_days(game, system_id: int) -> float:
    """What one hop out of this system costs a despatch, in days.

    The wait for the next courier plus whatever queue its gate is working.
    A ring that reserves a third of twenty-two slots a day passes despatches
    in hours; one that cycles six times a day does not.
    """
    from . import gatetraffic
    from . import weave as weave_sim
    gate = weave_sim.gate_at(game, system_id)
    if gate is None:
        return sig_data.DAYS_PER_LY          # nothing here to carry anything
    ring = gatetraffic.ring_of(gate)
    per_day = max(1e-6, ring.slots_per_day * ring.courier_share)
    headway = 1.0 / per_day
    return headway + gatetraffic.wait_days(game, gate, courier=True)


def path_days(game, frm: int, to: int) -> float | None:
    """Days for a despatch carried along the lit Weave, or None if unreachable.

    Walked hop by hop rather than counted, because the cost of a hop is a
    property of the *gate it leaves by* — a chain through a busy ancient ring
    is not the same as one through three brisk Charter gates.
    """
    if frm == to:
        return sig_data.SAME_SYSTEM_DAYS
    from . import weave as weave_sim
    net = weave_sim.network(game)
    if frm not in net or to not in net:
        return None
    best = {frm: 0.0}
    edge = [frm]
    for _round in range(64):
        nxt = []
        for sid in edge:
            leg = best[sid] + carried_days(game, sid)
            for other in net.get(sid, ()):
                if other not in best or leg < best[other] - 1e-9:
                    best[other] = leg
                    nxt.append(other)
        if not nxt:
            break
        edge = nxt
    return best.get(to)


def lag_days(game, frm: int, to: int) -> float:
    """How long a signal takes to get from one system to another.

    Three regimes, and the gap between them is the point: the same system is
    a radio call, the lit Weave is *carried* by couriers through rings that
    queue, and everything else is light.
    """
    if frm == to or frm < 0 or to < 0:
        return sig_data.SAME_SYSTEM_DAYS
    carried = path_days(game, frm, to)
    if carried is not None:
        return carried
    from ..world.galaxy import distance
    here = {s.id: s for s in game.galaxy.systems}
    a, b = here.get(frm), here.get(to)
    if a is None or b is None:
        return sig_data.DAYS_PER_LY
    apart = distance(a, b)
    # Off the Weave, word still travels — aboard whatever is crossing on its
    # own drive. Slow, but not light-slow. Only somewhere no hull can reach
    # at all is genuinely cut off.
    from . import reach as reach_sim
    try:
        shipped = to in reach_sim.component(game, start=frm)
    except Exception:                                          # noqa: BLE001
        shipped = True
    if shipped:
        return apart * sig_data.DAYS_PER_LY_SHIPPED
    return apart * sig_data.DAYS_PER_LY


# ── sending, reading, answering ────────────────────────────────────────────

def send(game, frm: str, name: str, channel: str, subject: str, body: str,
         system_id: int | None = None, replies=()) -> Signal:
    """Put something on the wire. It arrives when the distance says it does."""
    where = game.system.id if system_id is None else int(system_id)
    lag = lag_days(game, where, game.system.id)
    sig = Signal(id=f"sig-{len(_all(game))}-{int(game.day)}-{frm}",
                 frm=frm, name=name, channel=channel, subject=subject,
                 body=body, sent_day=float(game.day),
                 due_day=float(game.day) + lag, system_id=where,
                 replies=tuple(replies))
    _all(game).append(sig)
    return sig


def inbox(game, channel: str = "") -> list:
    """Everything that has arrived, newest first."""
    day = float(game.day)
    out = [s for s in _all(game)
           if s.arrived(day) and (not channel or s.channel == channel)]
    return sorted(out, key=lambda s: -s.due_day)


def unread(game) -> int:
    return sum(1 for s in inbox(game) if not s.read)


def asking(game) -> list:
    """Arrived, unanswered, and waiting on the captain."""
    return [s for s in inbox(game) if s.asks]


def read(game, signal_id: str) -> Signal | None:
    for sig in _all(game):
        if sig.id == signal_id:
            sig.read = True
            return sig
    return None


def answer(game, signal_id: str, key: str) -> bool:
    """Say one of the things offered. Returns whether it took."""
    for sig in _all(game):
        if sig.id != signal_id or sig.answered:
            continue
        if key not in {k for k, _words in sig.replies}:
            return False
        sig.answered = key
        sig.read = True
        return True
    return False


# ── who calls, and why ─────────────────────────────────────────────────────

def tick(game, days: float = 1.0) -> int:
    """Let the sector speak. Returns how many signals were sent.

    **Derived from watched facts, never rolled.** Each day a handful of
    things about the world are compared with what has already been reported;
    a signal goes out when one of them *changes*, and the new value is
    written down. That is why the traffic cannot drift from the sector it
    describes, cannot repeat itself, and cannot spam a captain who is sitting
    still — and why none of it needs the chronicle's luck, which belongs to
    the world rather than to the post.
    """
    from ..data.factions import FACTIONS_BY_ID
    from . import diplomacy as dip
    marks = _marks(game)
    sent = 0
    for power in dip.POWERS:
        standing = float(getattr(game, "rep", {}).get(power, 0.0))
        band, _blurb = dip.relation_band(standing)
        key = f"regard:{power}"
        was = marks.get(key)
        # **The number, not the name.** Whether a move is warmer is a
        # comparison of standings; keeping a private ordering of the band
        # *names* here was a second copy of `data/diplomacy`'s table, and it
        # was wrong from the first day — the keys were lower case and the
        # bands are not, so every lookup missed and every change, up or down,
        # told the captain their doors had got heavier.
        marks[key] = [band, standing]
        if not isinstance(was, list) or was[0] == band:
            continue
        warmer = standing > float(was[1])
        who = FACTIONS_BY_ID.get(power)
        name = getattr(who, "name", power.title())
        send(game, power, name, "power",
             f"Your standing: {band}",
             f"{name} has moved you from {was[0]} to {band}. "
             + ("They will say so where it counts."
                if warmer else "You will find doors heavier than they were."),
             replies=(("noted", "Acknowledge"),))
        sent += 1
    return sent


def sweep(game, keep: int = 120) -> int:
    """Drop the oldest read-and-answered traffic so the store cannot grow."""
    got = _all(game)
    if len(got) <= keep:
        return 0
    stale = [s for s in got if s.read and not s.asks]
    drop = len(got) - keep
    for sig in sorted(stale, key=lambda s: s.due_day)[:drop]:
        got.remove(sig)
    return min(drop, len(stale))
