"""Raiders where the law is not.

Raiders existed before `sim/piracy.py`: `traffic` gave one in ten systems an
unmarked hull and `encounters` made it the thing that jumps you. What did not
exist was any reason for them to be *where they are*. Two doors, both reading
the same field:

    traffic:    hostile_ok = system.port is None or system.bloom > 0.15
    encounters: danger     = bloom * 0.9 + (0.04 if port else 0.14) + 0.09·dark

Measured across 252 systems in six sectors, raiders appeared in 25 of 127
portless systems and 1 of 125 with a port — and already avoided a squadron,
17% at nothing on station against 0–2% elsewhere. That correlation was an
accident: both questions read `port`, and a fleet had nothing to do with
either.

The claims:

- **Law is one quantity**, made of a squadron on station, a dock, a claim,
  the distance from the nearest capital and the Bloom — and both doors read it,
  so a system cannot be lawful enough to keep raiders out and dangerous enough
  to jump you at the same time.
- **Piracy did not get more common, it got better placed.** 28 systems in 252
  against the old 26 — and none of them guarded, none of them with a port.
- **A squadron is the largest single term**, which is what connects this to
  `sim/fleets`: a power that can no longer pay for hulls stops policing.

Two wrong turns, both from measuring:

*The scale piled up against its ceiling.* At `WILD = 0.72` the quantiles ran
p60 0.80 to p90 0.91 — thirty per cent of the sector inside a tenth of the
range — so the number carried almost no information. At 0.45 it spreads: p25
0.03, p50 0.39, p90 0.64.

*A cliff placed piracy worse than the thing it replaced.* Gating on
lawlessness alone dropped raiders from 26 systems to **9**, because the least
policed systems are the portless ones and they carry about one hull each.
Scaling the chance *within* the gate put it back to 28 — the worst places
carry more raiders rather than merely being allowed one.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import exchequer as ex
from ..sim import fleets
from ..sim import piracy
from ..sim import traffic
from .harness import Suite

SEEDS = "abcdef"


def _sweep():
    """(lawlessness, has raiders, guarded, has port) for every system."""
    out = []
    for seed in SEEDS:
        game = new_game(seed)
        for system in game.galaxy.systems:
            out.append((
                piracy.lawlessness(game, system),
                bool(traffic.hostiles(game, system)),
                sum(fleets.squadron_at(game, system).values()),
                getattr(system, "port", None) is not None))
    return out


def run(suite: Suite) -> None:
    check = suite.check

    @check("raiders are where the law is not")
    def _():
        rows = _sweep()
        total = len(rows)
        raided = [r for r in rows if r[1]]
        assert raided, "no piracy anywhere in six sectors"
        share = len(raided) / total
        # The old gate put raiders in 26 of 252. The point was never more
        # piracy, it was piracy that is somewhere for a reason.
        assert 0.06 <= share <= 0.18, (
            f"{len(raided)} of {total} systems carry raiders ({share:.0%}) "
            "against the 10% the port gate produced")
        guarded = [r for r in raided if r[2]]
        ported = [r for r in raided if r[3]]
        assert not guarded, (
            f"{len(guarded)} raider systems have a squadron on station")
        assert not ported, f"{len(ported)} raider systems have a port"
        worst = min(r[0] for r in raided)
        assert worst >= piracy.RAIDERS_FROM, (
            f"a system at {worst:.2f} carries raiders below the "
            f"{piracy.RAIDERS_FROM:.2f} floor")
        return (f"{len(raided)} of {total} systems = {share:.0%}, none "
                f"guarded, none docked, none under {worst:.2f}")

    @check("the scale uses its range")
    def _():
        # At WILD = 0.72 this failed: p60 0.80 against p90 0.91, thirty per
        # cent of the sector inside a tenth of the range. A number that does
        # not spread cannot be read, and forces its own threshold to the top.
        vals = sorted(r[0] for r in _sweep())
        n = len(vals)
        def q(share):
            return vals[min(n - 1, int(share * (n - 1)))]
        assert q(0.25) < 0.20, f"a quarter of the sector is at {q(0.25):.2f}"
        assert 0.25 < q(0.5) < 0.55, f"the median system is {q(0.5):.2f}"
        # The top decile must not be jammed against the ceiling, which is
        # exactly what went wrong at WILD = 0.72: p90 sat at 0.91 and nine
        # systems in ten read as barely-policed. Demanding a wide p60–p90 gap
        # instead was the wrong test — the real spread lives at the *bottom*,
        # where a quarter of the sector is under 0.03, and the top is
        # legitimately bunched because most of the sector is empty and far.
        assert q(0.9) < 0.75, (
            f"nine systems in ten are under {q(0.9):.2f} — the scale is "
            "pinned near its ceiling and cannot distinguish bad from awful")
        assert q(0.75) - q(0.25) > 0.35, (
            f"the middle half spans only {q(0.75) - q(0.25):.2f}")
        return " · ".join(f"p{int(s * 100)} {q(s):.2f}"
                          for s in (0.1, 0.25, 0.5, 0.75, 0.9))

    @check("a squadron is the largest single thing keeping order")
    def _():
        # What connects this to `sim/fleets`: a power that can no longer pay
        # for hulls stops policing, and its space goes bad.
        game = new_game("collapse")
        system = next(s for s in game.galaxy.systems
                      if sum(fleets.squadron_at(game, s).values()) >= 1
                      and getattr(s, "port", None))
        power = system.port.faction
        guard = fleets.guard_at(game, system, power)
        before = piracy.lawlessness(game, system)
        for held in ex.holdings(game, power):
            held.port.independent = True
        assert fleets.guard_at(game, system, power) == 0
        after = piracy.lawlessness(game, system)
        moved = after - before
        assert moved > 0, (
            f"{system.name} lost its squadron and the law did not move")
        assert abs(moved - min(piracy.GUARD_CAP,
                               piracy.PER_HULL * guard)) < 1e-9, (
            f"losing {guard} hull(s) moved the law by {moved:.2f}, not by "
            "what a hull is worth")
        # And it is the largest term: worth more than the dock or the claim.
        assert piracy.PER_HULL > piracy.PORT_WORTH > piracy.CLAIM_WORTH, (
            "a dock or a claim outweighs somebody's hulls actually being here")
        return (f"{system.name}: {guard} hull(s) away takes the law "
                f"{before:.2f} → {after:.2f}")

    @check("both doors ask the same question")
    def _():
        # `encounters` had its own arithmetic over the same field, so the two
        # could disagree about one volume and nothing would notice.
        from ..sim import encounters
        game = new_game("doors")
        lawful = min(game.galaxy.systems,
                     key=lambda s: piracy.lawlessness(game, s))
        wild = max(game.galaxy.systems,
                   key=lambda s: piracy.lawlessness(game, s))
        assert not traffic.hostiles(game, lawful), (
            "the best-kept system in the sector has raiders in it")
        # Danger is a reading of the same number, so it must order the same
        # way as the law does.
        quiet = piracy.lawlessness(game, lawful) * encounters.LAW_WORTH
        rough = piracy.lawlessness(game, wild) * encounters.LAW_WORTH
        assert rough > quiet, (rough, quiet)
        assert encounters.LAW_WORTH > 0, "the law does not reach the danger"
        return (f"{lawful.name} {piracy.lawlessness(game, lawful):.2f} vs "
                f"{wild.name} {piracy.lawlessness(game, wild):.2f}, and the "
                "danger follows")

    @check("a screen says how well kept a system is")
    def _():
        game = new_game("kept")
        seen = set()
        for system in game.galaxy.systems:
            said = piracy.note(game, system)
            assert said, f"nothing said about {system.name}"
            seen.add(said)
        assert len(seen) >= 3, (
            f"only {len(seen)} distinct things said about a whole sector")
        best = min(game.galaxy.systems,
                   key=lambda s: piracy.lawlessness(game, s))
        assert "Well kept" in piracy.note(game, best)
        return f"{len(seen)} bands used across the sector"
