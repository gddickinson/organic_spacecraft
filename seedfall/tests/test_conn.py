"""Flying the ship at close quarters, and plotting against things that move.

Three new modules, and the checks that hold them. Everything below was found
by playing rather than by reading, and each fault is named where it was fixed.

**The closing rate was wrong by a factor of a thousand.** `pos` is in km and
`vel` in m/s, so `pos·vel / r` is already a velocity — the first draft divided
by another thousand "to convert". The instrument read **+0.01 m/s while the
ship flew in at twelve**, the autopilot believed it, and every approach ended
in the hull. It is the sort of fault a unit test on `closing` would have
missed, because the number looked plausible; only flying showed it.

**The autopilot managed the closing rate and ignored the rest of the
velocity.** Motion across the line of sight is the part that makes you *miss*.
With it unmanaged, `close` hung at 1.7 km circling a hull it never reached, or
went into a quay sideways at 12 m/s with its closing rate perfectly on profile.

**A body approach opened inside the planet.** Twelve kilometres from the
*centre* of a world is several thousand underground, and `mu / r²` there threw
the ship out of the system at eleven thousand kilometres a second.

**The orbit band was a percentage.** A tenth of circular is 500 m/s at a
middling world — forty main-drive burns — and wider than the whole orbit at a
rock. `orbit_band` takes whichever of the flat band and the share is tighter.

**The forecast quoted the tank before the burn paid for it.**

The claims:

- **Every approach can actually be flown**, swept over every contact in
  several systems. The general one.
- **The forecast is what the burn does**, in the pilot's own terms.
- **A prediction comes true**, checked by playing the chronicle forward.
- **An intercept costs what flying it charges** — the plot and the helm
  cannot disagree, because they are the same arithmetic.
- **A gate with no mass behind it refuses.**

The screens are held in `test_cameras.py`, and what a finished approach
costs the chronicle in `test_berthing.py`.
"""

from __future__ import annotations

import dataclasses
import inspect
import math
import re

from ..core.state import new_game
from ..sim import autopilot as pilot_sim
from ..sim import conn as conn_sim
from ..sim import preview as preview_sim
from ..sim import track as track_sim
from .harness import Suite


def _contacts(game, kinds=("body", "anchorage", "hull")):
    return [c for c in track_sim.contacts(game) if c.kind in kinds]


def run(suite: Suite) -> None:
    check = suite.check

    @check("a barely turning orbit is committed to one sense, not flipped")
    def _():
        # `ACROSS_FLOOR` is why: the sense of the tangent used to come from the
        # sign of a dot product, and near a small body the tangential velocity is
        # a couple of metres a second, so the sign flipped between ticks. The
        # computer demanded prograde, then retrograde, then prograde, and pumped
        # energy into the orbit instead of shaping it — measured, a comet's 6.8
        # m/s orbit driven from 335 km out to 1,340 and adrift.
        #
        # `tests/tripwire.py` reported the constant as protected only by a suite
        # that does not name it, so nothing said where the line is. Against
        # **0.7 m/s and 1.5 m/s written here**, chosen to *bracket* it: a first
        # draft probed at 0.4 and 6, and the sweep still reported it unpinned,
        # because the floor is the larger of the constant and a thruster pulse
        # (0.45 on this hull) — so zeroing or halving it left 0.4 below the line
        # and 6 above it, and the check could not tell. A probe has to fall
        # between the values a mutation would put the line at.
        game = new_game("across")
        contact = next(iter(_contacts(game, ("body",))))
        conn = conn_sim.start(game, contact)
        conn.pos = [100.0, 0.0, 0.0]

        # Below the floor: whichever way it is creeping, the answer is the same.
        senses = set()
        for creep in (0.7, -0.7, 0.05, -0.05):
            conn.vel = [0.0, creep, 0.0]
            side = pilot_sim._across(conn)
            senses.add((side[0] > 0) - (side[0] < 0))
            senses.add((side[1] > 0) - (side[1] < 0))
        assert len(senses) <= 2, (
            f"the tangent's sense flips with a drift of 0.7 m/s: {senses}")
        one_way = pilot_sim._across(conn)

        # Above it: the answer follows the way the ship is actually going, and
        # the two directions of travel give opposite tangents.
        conn.vel = [0.0, 1.5, 0.0]
        going = pilot_sim._across(conn)
        conn.vel = [0.0, -1.5, 0.0]
        coming = pilot_sim._across(conn)
        assert going != coming, (
            "at a metre and a half a second the sense is still committed rather "
            "than read off the motion, so a ship in a real orbit can be told to "
            "reverse it")
        assert going == one_way or coming == one_way, (
            "the committed sense is neither of the two real ones")
        return ("at 0.7 m/s the tangent is committed to one sense; at 1.5 it "
                "follows the way the hull is travelling, both ways")

    @check("every approach can be flown to a berth or an orbit")
    def _():
        # The general one, and the one that found the closing-rate fault:
        # hand every contact in several systems to the flight computer and
        # see whether it arrives. Before the fix, none of them did.
        outcomes: dict = {}
        failures = []
        for seed in range(5):
            game = new_game(f"conn-fly-{seed}")
            for contact in _contacts(game):
                mode = "orbit" if contact.kind == "body" else "close"
                conn = conn_sim.start(game, contact)
                pilot_sim.fly(conn, mode, 1500)
                outcomes[conn.outcome or "unresolved"] = (
                    outcomes.get(conn.outcome or "unresolved", 0) + 1)
                if conn.outcome not in ("orbit", "alongside"):
                    failures.append(
                        f"{contact.name} ({contact.kind}) on {mode}: "
                        f"{conn.outcome or 'never resolved'} at "
                        f"{conn.range_km:,.2f} km, {conn.speed:,.1f} m/s")
        assert not failures, (
            f"{len(failures)} approach(es) the computer could not fly: "
            f"{failures[:4]}")
        assert sum(outcomes.values()) >= 30, outcomes
        return " · ".join(f"{n} {name}" for name, n in sorted(outcomes.items()))

    @check("the closing rate is a real speed, not a thousandth of one")
    def _():
        # The fault itself, asked directly: fly straight at the target and
        # the instrument must agree with how fast the range is actually
        # shrinking. Derived from the range, never from the formula.
        game = new_game("closing")
        contact = next(c for c in _contacts(game) if c.kind == "hull")
        conn = conn_sim.start(game, contact)
        for _ in range(6):
            conn_sim.apply(conn, "forward")
        worst = 0.0
        for _ in range(8):
            before = conn.range_km
            said = conn.closing
            conn_sim.apply(conn, None)          # coast exactly one tick
            fell = (before - conn.range_km) * 1000.0 / conn_sim.TICK
            worst = max(worst, abs(said - fell) / max(1.0, abs(fell)))
        assert worst < 0.05, (
            f"the instrument reads a closing rate {worst:.0%} away from the "
            "rate the range is actually falling at")
        assert conn.closing > 1.0, (
            f"six burns ahead and the panel still reads {conn.closing:.3f} m/s")
        return (f"instrument within {worst:.1%} of the measured rate over "
                "eight coasting minutes")

    @check("the computer recovers from a drift across the approach")
    def _():
        # A gap the sweep above cannot see: `start` puts the ship dead ahead
        # of the target with its velocity along the line of sight, so the
        # branch that kills motion *across* it never fires there. Disabling
        # that branch entirely passed every other check in this suite.
        #
        # A pilot who has burned sideways, or been shoved, is the real case.
        # Velocity across the line of sight does not change the range at all,
        # so a computer watching only the closing rate reports itself
        # perfectly on profile while sailing past.
        game = new_game("sideways")
        contact = next(c for c in _contacts(game, ("anchorage", "hull")))
        failures, flown = [], 0
        for drift in (2.0, 6.0, 15.0, 30.0):
            for sign in (1.0, -1.0):
                conn = conn_sim.start(game, contact)
                conn.vel = [drift * sign, 1.0, drift * sign * 0.4]
                across = math.dist(pilot_sim.lateral(conn), (0.0, 0.0, 0.0))
                assert across > drift * 0.8, (across, drift)
                pilot_sim.fly(conn, "close", 2000)
                flown += 1
                if conn.outcome != "alongside":
                    failures.append(
                        f"{drift:g} m/s of drift {'+' if sign > 0 else '-'}: "
                        f"{conn.outcome or 'never resolved'} at "
                        f"{conn.range_km:,.2f} km")
        assert not failures, (
            f"{len(failures)} of {flown} off-axis approaches never berthed: "
            f"{failures}")
        return (f"{flown} approaches begun with up to 30 m/s across the line "
                "of sight, every one berthed")

    @check("the forecast is what the burn does")
    def _():
        # Every axis, both drives, every kind of target — and including the
        # tank, which the first draft quoted before the burn had paid for it.
        game = new_game("conn-fc")
        worst: dict = {}
        counted = 0
        for contact in _contacts(game):
            for main in (False, True):
                for axis_id, _label, _vec in conn_sim.AXES:
                    conn = conn_sim.start(game, contact)
                    for _ in range(4):
                        if conn.over:
                            break
                        said = preview_sim.forecast(conn, axis_id, main=main)
                        conn_sim.apply(conn, axis_id, main=main)
                        for field, got in (("range_km", conn.range_km),
                                           ("closing", conn.closing),
                                           ("speed", conn.speed),
                                           ("rcs", conn.rcs)):
                            gap = abs(said[field] - got)
                            worst[field] = max(worst.get(field, 0.0), gap)
                            counted += 1
        assert counted > 500, counted
        for field, gap in worst.items():
            assert gap < 1e-6, (
                f"the forecast's {field} is {gap:g} away from what the burn "
                "actually left")
        return (f"{counted} comparisons over {len(conn_sim.AXES)} axes and "
                "both drives, every field exact")

    @check("a forecast's twin carries every field that changes the flying")
    def _():
        # `_copy` is a hand-written field list, and it has now been caught
        # short three times: `start_km` when it was written, then
        # `orbit_want_km` and `hold`. The failure mode is always the same and
        # always quiet — the twin takes the dataclass default, flies a slightly
        # different ship, and the forecast lies by a little. The check above
        # catches it only when the dropped field happens to change one of the
        # four numbers it compares, and only on the approaches it flies.
        #
        # So guard the list itself. Every field is either carried or named here
        # as one a twin must *not* inherit, with the reason.
        fresh = {
            "landed": "a twin flies from here; it has not landed",
            "log": "the twin's own log is thrown away with the twin",
            "outcome": "an approach that has ended cannot be forecast",
            "damage": "damage taken is the real ship's, not the trial's",
            "struck_damage": "what the other body took, and a trial run may "
                             "not bill a station for a collision that has "
                             "not happened",
            "struck_dv": "the shove the other body took, likewise the real "
                         "approach's and not the trial's",
            "company": "your own other hull, placed live each beat by "
                       "`sky.company` — a forecast is not a beat and a twin "
                       "has nobody keeping station on it",
            "fired_axis": "what the *ship* fired, which a trial run has not",
            "fired_main": "likewise — a twin's burn is not the ship's",
            "fired_share": "likewise",
            "fired_turning": "likewise",
            "towed": "how far the boats have walked the *ship* in. A trial "
                     "run may not credit a station with a tow it has not "
                     "made, for the same reason it may not bill one for a "
                     "collision that has not happened",
            "charged": "seconds billed — a ledger fact, not a flying one",
            "sheered": "how far the structure has worked itself away from "
                       "the *ship*. A trial run may not bill a station for "
                       "standing off, for the same reason it may not bill it "
                       "for a collision that has not happened",
            "charged_rcs": "`charged`'s mass twin — a trial run bills nobody",
            "avoiding": "the hazard already announced — a record of what was "
                        "*said*, not state the flying reads",
            "clock_on": "the screens' beat — a twin is flown by its forecast",
        }
        body = inspect.getsource(preview_sim._copy)
        carried = set(re.findall(r"(\w+)=(?:conn\.|list\(conn\.)", body))
        missing = []
        for field in dataclasses.fields(conn_sim.Conn):
            if field.name in carried or field.name in fresh:
                continue
            missing.append(field.name)
        assert not missing, (
            f"`_copy` drops {missing} — a forecast would fly a twin holding "
            "the dataclass default instead of what this ship actually has. "
            "Carry it, or name it in `fresh` with the reason it must not be.")
        # And the allowlist has to stay honest: a name in it that is no longer
        # a field is a reason nobody will ever read again.
        names = {f.name for f in dataclasses.fields(conn_sim.Conn)}
        stale = sorted(set(fresh) - names)
        assert not stale, f"`fresh` names {stale}, which are not fields"
        return (f"{len(carried)} of {len(names)} fields carried, "
                f"{len(fresh)} deliberately left fresh")
