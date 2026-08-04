"""A ring has a throat and a clock, and a busy one makes you wait.

`sim/gates` said transit was instant and cost money, standing and the Bloom.
That was true and incomplete: a gate is a machine with a size and a cycle
rate, and a system working one hard has a queue at it. Both matter more once
despatches travel this way, because nothing is broadcast through a ring —
a signal crosses aboard a courier competing for the same slots.

The claims:

* a **bore is a size, not a toll** — no fee or standing gets a hull through
  a throat it does not fit;
* the three kinds differ in throat and cycle **in the order the table says**;
* a busy system **queues** and a quiet one does not;
* a **courier gets through what a freighter waits in**, which is the whole
  point of a reserved share;
* and the wait is **bounded** — a ring keeps working, so a queue is a cost
  and never a wall.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data import gate_traffic as rings
from ..sim import gatetraffic
from ..sim import weave as weave_sim
from .harness import Suite


def _a_gate(game):
    """Any lit anchor in this chronicle, with its system."""
    for gate in weave_sim.gates(game):
        if gate.lit:
            return gate
    return None


def run(suite: Suite) -> None:
    check = suite.check

    @check("a bore is a size, and no fee argues with it")
    def _():
        game = new_game("bore")
        gate = _a_gate(game)
        assert gate is not None, "no lit anchor in this chronicle"
        ring = gatetraffic.ring_of(gate)
        ok, _why = gatetraffic.may_pass(game, gate, ring.bore_t * 0.5)
        assert ok, "a hull well inside the throat was refused"
        # Rich, well-regarded, and still too big.
        game.credits = 10_000_000
        for faction in list(game.rep):
            game.rep[faction] = 100
        refused, why = gatetraffic.may_pass(game, gate, ring.bore_t * 1.5)
        assert not refused, "a hull half again the bore went through"
        assert "bore" in why or "throat" in why, why
        return (f"{ring.name}: {ring.bore_t:,.0f} t through, "
                f"{ring.bore_t * 1.5:,.0f} t refused — {why.split('—')[-1].strip()}")

    @check("the three kinds are different machines, in the order stated")
    def _():
        assert (rings.ANCIENT.bore_t > rings.CHARTER.bore_t
                > rings.YOURS.bore_t), "the throats are not in the stated order"
        assert (rings.CHARTER.slots_per_day > rings.ANCIENT.slots_per_day
                > rings.YOURS.slots_per_day), (
            "a Charter gate is built for throughput and an ancient ring is "
            "not; the cycle rates do not say so")
        return " · ".join(
            f"{r.name} {r.bore_t:,.0f} t at {r.slots_per_day:g}/day"
            for r in (rings.ANCIENT, rings.CHARTER, rings.YOURS))

    @check("a busy system queues and a quiet one does not")
    def _():
        game = new_game("queue")
        gate = _a_gate(game)
        assert gate is not None
        ring = gatetraffic.ring_of(gate)
        # Read off the sector as it stands, then against a system working the
        # ring far harder than it can clear.
        quiet = gatetraffic.wait_days(game, gate)
        real = gatetraffic.demand(game, gate.system_id)
        was = gatetraffic.demand
        try:
            gatetraffic.demand = lambda *_a, **_k: ring.slots_per_day * 3.0
            busy = gatetraffic.wait_days(game, gate)
        finally:
            gatetraffic.demand = was
        assert busy > quiet, (
            f"a ring worked at three times its cycle waits {busy:.2f} d "
            f"against {quiet:.2f} when it is not")
        assert busy <= rings.MAX_WAIT_DAYS + 1e-9, (
            f"a queue of {busy:.1f} days is a wall, not a cost")
        return (f"{real:.1f} transits a day wanted of {ring.slots_per_day:g}: "
                f"{quiet * 24:,.1f} h; at three times the cycle, {busy:.2f} d")

    @check("a courier gets through what a freighter waits in")
    def _():
        game = new_game("courier")
        gate = _a_gate(game)
        assert gate is not None
        ring = gatetraffic.ring_of(gate)
        was = gatetraffic.demand
        try:
            gatetraffic.demand = lambda *_a, **_k: ring.slots_per_day * 2.0
            hull = gatetraffic.wait_days(game, gate)
            post = gatetraffic.wait_days(game, gate, courier=True)
        finally:
            gatetraffic.demand = was
        assert post < hull, (
            f"a despatch waits {post:.2f} d against a hull's {hull:.2f} — the "
            "reserved share is doing nothing")
        assert post > 0.0, "a despatch is handled instantly, which is too good"
        return (f"at twice the cycle: a hull waits {hull:.2f} d, a despatch "
                f"{post:.2f} d")

    @check("a ring says what it is doing, in words")
    def _():
        game = new_game("gateword")
        gate = _a_gate(game)
        said = gatetraffic.note(game, gate)
        assert "bore" in said and any(
            w in said for w in ("clear", "working", "busy", "backed up")), said
        assert gatetraffic.note(game, None) == "No anchor here."
        return said
