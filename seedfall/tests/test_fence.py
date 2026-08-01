"""Where stolen cargo comes out, and why it cannot come out where it was taken.

`sim/piracy` said where raiders are. This is the other half — somewhere for
what they take — and the shape of it is decided by a measurement that killed
the obvious design.

**Raiders and markets are disjoint by construction.** `piracy.lawlessness`
counts a dock as law, so a system with a port is never lawless enough for
raiders; and a market *is* a port. Measured across six sectors: 28 systems
carry raiders and not one of them has a port, so "raider presence feeds the
local black market" describes something that can never happen. The local
signal is flat as well — every market in the game sits at lawlessness 0.00 to
0.06.

What is not flat is the *distance* from a market to where hulls are actually
being taken: 5.3 to 44.6 across three sectors, median 16.9. Stolen cargo
travels, and `piracy.fence_pull` is how much of it reaches a given wharf.

The claims:

- **The quiet word is not one price everywhere.** It used to pay identically
  at a Charter capital and a Charter outpost, because nothing in it knew where
  you were standing.
- **Near the raiding you are paid less and can shift far more.** Measured:

      pull 0.00   pays 7,800   absorbs 15.0   117,000 a visit
      pull 0.47   pays 6,509   absorbs 32.5   211,542 a visit

  Seventeen per cent off the tonne, twice the tonnage, and the visit is worth
  1.8 times as much — so a full hold goes in one call instead of four.
- **Out on the safe lanes nothing has changed at all**, which is what keeps
  this a property of a few places rather than a discount everywhere.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..sim import customs
from ..sim import piracy
from ..sim import traffic
from .harness import Suite

SEEDS = "abcdef"


def _fenceable(game):
    """(system, faction, good) for every market that trades something banned."""
    out = []
    for system in game.galaxy.systems:
        port = getattr(system, "port", None)
        if port is None or system.market is None:
            continue
        reg = customs.regime(port.faction)
        if not reg or not reg.outlaws:
            continue
        out.append((system, port.faction, sorted(reg.outlaws)[0]))
    return out


def _at(game, system):
    game.location_id = system.id
    return system


def run(suite: Suite) -> None:
    check = suite.check

    @check("a fence cannot be where the raiding is")
    def _():
        # The measurement that decided the design. If this ever stops being
        # true, `fence_pull` should be a local reading and not a distance.
        raided = ported = 0
        laws = []
        for seed in SEEDS:
            game = new_game(seed)
            for system in game.galaxy.systems:
                if traffic.hostiles(game, system):
                    raided += 1
                    ported += getattr(system, "port", None) is not None
                if system.market is not None:
                    laws.append(piracy.lawlessness(game, system))
        assert raided, "no raiders anywhere in six sectors"
        assert ported == 0, (
            f"{ported} of {raided} raided systems have a port — a market "
            "could be supplied where it stands, and this should be local")
        assert max(laws) < 0.7, (
            f"a market sits at lawlessness {max(laws):.2f}; the local signal "
            "is no longer flat")
        return (f"{raided} raided systems, none with a port · markets run "
                f"lawlessness {min(laws):.2f}–{max(laws):.2f}")

    @check("the quiet word is not one price everywhere")
    def _():
        # It used to be: `premium` read the regime and the heat and nothing
        # about where the ship was standing.
        for seed in SEEDS:
            game = new_game(seed)
            seen = {}
            for system, faction, good in _fenceable(game):
                _at(game, system)
                seen.setdefault((faction, good), set()).add(
                    customs.premium(game, faction, good))
            spread = [v for v in seen.values() if len(v) > 1]
            if spread:
                widest = max(spread, key=lambda v: max(v) - min(v))
                assert max(widest) > min(widest), widest
                return (f"one power, one good, {len(widest)} different prices "
                        f"across its own berths: {min(widest):,}–{max(widest):,}")
        raise AssertionError("no power trades a banned good at two berths")

    @check("near the raiding you are paid less and can shift more")
    def _():
        game = new_game("fence")
        rows = []
        for system, faction, good in _fenceable(game):
            _at(game, system)
            rows.append((piracy.fence_pull(game, system), system.id, faction,
                         good, system.name))
        rows.sort(key=lambda r: r[0])
        assert rows[-1][0] > 0.2, (
            f"the most fenced market in the sector pulls {rows[-1][0]:.2f}")

        def trade(row):
            _at(game, next(s for s in game.galaxy.systems if s.id == row[1]))
            return (customs.premium(game, row[2], row[3]),
                    customs.absorbs(game, row[2]))

        far_price, far_take = trade(rows[0])
        near_price, near_take = trade(rows[-1])
        assert near_take > far_take * 1.5, (
            f"a fenced market moves {near_take} against {far_take} — that is "
            "not a channel")
        # The price falls, per tonne, once the power's own zeal is held still:
        # compare a market with the same regime rather than across powers.
        same = [r for r in rows if r[2] == rows[-1][2]]
        if len(same) > 1:
            low, high = trade(same[0]), trade(same[-1])
            assert high[0] < low[0], (
                f"{same[-1][4]} is nearer the raiding and pays {high[0]:,} "
                f"against {low[0]:,} at {same[0][4]}")
        return (f"{rows[0][4]} pull {rows[0][0]:.2f}: {far_price:,} x "
                f"{far_take} = {far_price * far_take:,.0f} · {rows[-1][4]} "
                f"pull {rows[-1][0]:.2f}: {near_price:,} x {near_take} = "
                f"{near_price * near_take:,.0f}")

    @check("out on the safe lanes nothing has changed")
    def _():
        # A market with no raiding within reach must price exactly as it did
        # before there was a fence at all.
        game = new_game("fence")
        quiet = None
        for system, faction, good in _fenceable(game):
            _at(game, system)
            if piracy.fence_pull(game, system) == 0.0:
                quiet = (system, faction, good)
                break
        assert quiet is not None, "every market in the sector is fenced"
        system, faction, good = quiet
        _at(game, system)
        from ..data.commodities import BY_ID
        reg = customs.regime(faction)
        nerve = max(0.55, 1.0 - customs.heat(game, faction) * 0.45)
        was = max(1, round(BY_ID[good].base * (1.15 + reg.zeal * 0.7) * nerve))
        assert customs.premium(game, faction, good) == was, (
            f"{system.name} pulls nothing and still prices differently")
        return f"{system.name}: {was:,} with a fence and without one"

    @check("the reach is a real distance, not a switch")
    def _():
        # `fence_pull` has to grade, or it is a second yes/no gate wearing a
        # float's clothes — the mistake `piracy` itself made and had to undo.
        pulls = []
        for seed in SEEDS:
            game = new_game(seed)
            for system, _f, _g in _fenceable(game):
                pulls.append(piracy.fence_pull(game, system))
        graded = sorted(p for p in pulls if 0.0 < p < 1.0)
        assert len(graded) >= 5, (
            f"only {len(graded)} of {len(pulls)} markets sit between nothing "
            "and everything")
        assert max(pulls) - min(pulls) > 0.3, (
            f"the whole sector spans {min(pulls):.2f}–{max(pulls):.2f}")
        return (f"{len(pulls)} markets, {len(graded)} part-fenced, "
                f"{min(pulls):.2f}–{max(pulls):.2f} across six sectors")
