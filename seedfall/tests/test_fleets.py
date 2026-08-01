"""What a power can put in space, and what it costs it.

Measured before `sim/fleets.py` existed. The powers have real purses — income,
outlay and a margin, and they found and promote ports with them. The sector has
eighty-four hulls, twenty-one of them on patrol, each flying somebody's flag.
**The two had nothing to do with each other:**

    traffic._busyness = 1 + port.level (+1 capital, +2 lit anchor, −1 bloom)

A power's presence was a reading of its infrastructure and never of its
treasury, so a bankrupt power had exactly as many hulls on station as a
thriving one. Nothing in the game answered "what can this power field", and
`control.means` read port levels because there was nothing better to read.

The claims:

- **A fleet is what the margin sustains**, derived every time it is asked, so
  it cannot drift and a save cannot carry a stale one.
- **The fleet follows the margin down as well as up.** The claim this file
  started with was "ports are paid for in hulls", and the measurement said no:
  founding costs the purse nothing and pays 60 a day at once, so six foundings
  took the freeholds from 7 hulls to 15 with the purse unmoved at 30,000, and
  promoting moves margin by exactly zero. There is no choice a power can make
  that costs it margin — task #117. What *does* cost it is losing holdings,
  which is what annexation already does.
- **Hulls are where the holdings are**, weighted by port level, and the shares
  sum to the strength with no draw involved.
- **The top rung of `control.LADDER` needs something that can come out after
  you.** A capital with no squadron still shoots from its own batteries and
  cannot drive anybody off.

A wrong turn worth keeping, because it invalidated a whole round of numbers.
The first measurement of "how often does a power lose its squadron" advanced
900 days in a single `advance_days` call and reported **12 of 24 capitals**
losing theirs. Stepped ten days at a time over the same span it is **1 of 24**.
`core/clock.advance_days` runs each subsystem's tick once with `n` as an
argument, so a per-day *decision* fires once for the whole jump and the economy
lands somewhere the game would never actually reach. See task #116. Everything
here advances in steps.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import control
from ..sim import diplomacy as dip
from ..sim import exchequer as ex
from ..sim import fleets
from ..sim import war
from .harness import Suite

SEEDS = "abcdef"


def _played(seed, days=600, step=10):
    """A sector played forward in steps, which is the only honest way.

    One `advance_days(900)` and ninety `advance_days(10)` produce different
    economies — see the module docstring and task #116 — so a check that jumps
    is measuring a game that does not exist.
    """
    game = new_game(seed)
    for _ in range(max(1, days // step)):
        game.advance_days(step)
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("a fleet is what the margin sustains")
    def _():
        game = new_game("fleet")
        said = []
        for power in dip.POWERS:
            margin = fleets.sustains(game, power)
            assert abs(margin - ex.margin(game, power)) < 1e-9, (
                "the fleet is reading a margin of its own rather than the "
                "exchequer's")
            assert fleets.strength(game, power) == max(
                0, int(margin // fleets.UPKEEP))
            said.append(f"{power[:4]} {margin:.0f}→{fleets.strength(game, power)}")
        # And the sector as a whole is the size of the traffic already in it:
        # twenty-one patrol hulls exist, so a fleet of two or of two hundred
        # would both be wrong.
        totals = []
        for seed in SEEDS:
            played = _played(seed)
            totals.append(sum(fleets.strength(played, p) for p in dip.POWERS))
        assert all(12 <= t <= 44 for t in totals), (
            f"sector fleets across six sectors: {totals} — against the "
            "twenty-one patrol hulls the sector already carries")
        return (" · ".join(said) + f" · played out: {sorted(totals)}")

    @check("lose the holdings and the fleet goes with them")
    def _():
        # **This check claimed the opposite first, and the measurement said
        # no.** "Ports are paid for in hulls" is the trade an order of battle
        # wants to make, and it is not in this economy: founding costs the
        # purse nothing and pays 60 a day immediately, so six foundings took
        # the freeholds from 7 hulls to 15 with the purse unmoved at 30,000.
        # Promoting moves margin by exactly zero. See task #117 — there is no
        # choice a power can make that costs it margin.
        #
        # So this claims only what is true: the fleet is a *reading* of the
        # margin and follows it down as well as up. Holdings change hands in
        # this game — that is what annexation is — and a power that loses them
        # loses the income, the margin and the hulls, in that order.
        game = new_game("losses")
        power = max(dip.POWERS, key=lambda p: fleets.strength(game, p))
        before, margin = fleets.strength(game, power), fleets.sustains(game, power)
        assert before > 0, f"{power} fields nothing to lose"
        taken = 0
        for system in ex.holdings(game, power):
            if system.port.capital:
                continue
            system.port.faction = "sanhedrin" if power != "sanhedrin" else "charter"
            taken += 1
        after = fleets.strength(game, power)
        assert taken, f"{power} holds nothing but a capital"
        assert after < before, (
            f"{power} lost {taken} holdings and still fields {after} hulls "
            f"against {before}")
        return (f"{power} lost {taken} holdings: margin "
                f"{margin:.0f}→{fleets.sustains(game, power):.0f}, fleet "
                f"{before}→{after}")

    @check("in peacetime hulls sit where the holdings are, by port level")
    def _():
        # "In peacetime" is not decoration. A power at war keeps hulls off what
        # it is trying to take as well — see the two checks below — so `spread`
        # is a subset of the holdings only while nobody is fighting, which is
        # the case at day 0 of a fresh sector.
        game = new_game("where")
        assert not war.wars(game), "this sector starts at war; pick another"
        for power in dip.POWERS:
            spread = fleets.stations(game, power)
            assert sum(spread.values()) == fleets.strength(game, power), (
                f"{power} keeps {sum(spread.values())} hulls against a "
                f"strength of {fleets.strength(game, power)}")
            held = {s.id for s in ex.holdings(game, power)}
            assert set(spread) <= held, (
                f"{power} has hulls somewhere it holds nothing, at peace")
        # And the share follows the **port level**, which is what makes a
        # capital hold more than an outpost.
        #
        # This check has been wrong three times, and the third time is the
        # instructive one. It compared a capital with any smaller holding
        # using `>=` (a tie satisfies that, so flattening the weighting left
        # it green). Then it demanded two more hulls at a capital than at an
        # ordinary holding *of the same level* — and there is no such thing:
        # every capital in the game is level 3 and no ordinary port ever is,
        # which is why `CAPITAL_WEIGHT` was deleted rather than pinned. Then
        # it demanded a gap of two by level, and measured across six sectors
        # **exactly one power** produces one: with fleets of four to eight
        # spread over three to six holdings, largest-remainder rounding is
        # bigger than the weighting.
        #
        # So the claim is the one the numbers actually support: the ordering
        # never inverts. A developed holding is never given fewer hulls than
        # an outpost, in any power, in any sector.
        strict = 0
        pairs = 0
        for seed in SEEDS:
            other = new_game(seed)
            for power in dip.POWERS:
                spread = fleets.stations(other, power)
                held = ex.holdings(other, power)
                if fleets.strength(other, power) < 2 or len(held) < 2:
                    continue
                top = max(held, key=lambda s: s.port.level)
                low = min(held, key=lambda s: s.port.level)
                if top.port.level == low.port.level:
                    continue
                pairs += 1
                high, small = spread.get(top.id, 0), spread.get(low.id, 0)
                assert high >= small, (
                    f"{seed}/{power}: a level {top.port.level} holding keeps "
                    f"{high} hulls and a level {low.port.level} one keeps "
                    f"{small} — the weighting is upside down")
                strict += high > small
        assert pairs >= 12, f"only {pairs} comparable pairs in six sectors"
        assert strict >= pairs * 0.6, (
            f"the level decided only {strict} of {pairs} pairs — rounding is "
            "doing the work")
        shown = [f"{strict} of {pairs} pairs across six sectors put more at "
                 "the developed holding, and none put fewer"]
        return " · ".join(shown)

    @check("a power at war keeps hulls off what it is trying to take")
    def _():
        # The change that makes a contested system possible at all. Before it,
        # hulls only ever sat on holdings, so two powers could not be in one
        # system: measured over eight sectors flown a decade each with nine
        # live wars, powers-with-hulls-per-system came out {1: 195, 0: 141}.
        game = new_game("front")
        dip.ensure(game)
        dip.shift_relation(game, "charter", "freeholds", -200)
        assert war.at_war(game, "charter", "freeholds")
        spoils = {s.id for s in war.spoils(game, "charter")}
        assert spoils, "at war and nothing of theirs is takeable"
        spread = fleets.stations(game, "charter")
        forward = spoils & set(spread)
        assert forward, (
            "charter is at war and keeps every hull at home; nothing can "
            "ever be contested")
        held = {s.id for s in ex.holdings(game, "charter")}
        assert set(spread) & held, "the whole fleet went forward and left home bare"
        assert sum(spread.values()) == fleets.strength(game, "charter"), (
            "hulls were created or lost by going to the front")
        # And a system at the front now carries two flags.
        contested = [s for s in game.galaxy.systems
                     if len(fleets.squadron_at(game, s)) > 1]
        assert contested, "two powers at war and not one system carries two flags"
        return (f"{len(forward)} of charter's stations are enemy ground; "
                f"{len(contested)} systems carry two flags")

    @check("a holder can be out-shipped over its own holding")
    def _():
        # `keeper_of` said this in its docstring and it was false: measured
        # across six sectors it agreed with `system.port.faction` in 99 of 99
        # non-empty cases and differed in 0, because `squadron_at` could never
        # return two powers.
        seen = out = 0
        for i in range(6):
            game = new_game(f"keep{i}")
            dip.ensure(game)
            for a, b in (("charter", "freeholds"), ("concordat", "sanhedrin")):
                dip.shift_relation(game, a, b, -200)
            for system in game.galaxy.systems:
                here = fleets.squadron_at(game, system)
                if len(here) < 2:
                    continue
                seen += 1
                if fleets.keeper_of(game, system) != system.port.faction:
                    out += 1
        assert seen, "no contested system anywhere, so nothing was tested"
        assert out, (
            f"{seen} contested systems and the holder kept every one of them; "
            "`keeper_of` still cannot differ from the port's own faction")
        return f"{out} of {seen} contested systems are held by somebody else's fleet"

    @check("the answer is derived, so it never drifts")
    def _():
        # The discipline `sim/anchorage` uses for a quay's whole existence.
        game = new_game("derived")
        power = dip.POWERS[0]
        first = fleets.stations(game, power)
        for _ in range(5):
            game.rng("shuffle").int(0, 99)
            assert fleets.stations(game, power) == first, (
                "luck moved a squadron")
        twin = new_game("derived")
        assert fleets.stations(twin, power) == first, (
            "a fresh sector from the same seed fields a different fleet")
        return (f"{sum(first.values())} hulls, unmoved by five draws and a "
                "rebuilt sector")

    @check("the top rung needs something that can come out after you")
    def _():
        # `repelled` is not a heavier gun, it is being driven off. Measured
        # through `control.means`, the one door the ladder reads.
        # The home system, and it must be the home system: `control.means`
        # reads `game.system` rather than the contact's own, which is true
        # enough in play — contacts come off the system you are in — but a
        # check that hands it a capital from across the sector is asking
        # about one port and being answered about another.
        game = new_game("a")
        system = game.system
        port = getattr(system, "port", None)
        assert port is not None and port.capital, (
            f"{system.name} is not a capital — this check needs the home "
            "system to be one, and seed 'a' is chosen for that")
        contact = _quay_contact(game, system)
        assert fleets.guard_at(game, system, port.faction) > 0
        assert control.means(game, contact) == 4, (
            "a guarded capital cannot reach the top of the ladder")

        # Now make that power insolvent. Taking its other holdings away is
        # not enough — a capital earns for itself, so it keeps a picket while
        # it is solvent, and in this economy a power with one holding still
        # clears the upkeep of a hull. That is the correct behaviour and it is
        # why this rule will bite far more once #117 gives the powers real
        # costs.
        #
        # `port.independent` is a field the sector already carries and
        # `exchequer.holdings` already excludes: a port that has declared for
        # itself still flies the flag and stops paying in. A power whose
        # holdings have all gone independent is exactly the case the rule is
        # about — grand berths, no revenue, nothing that can come out.
        gone = 0
        for held in ex.holdings(game, port.faction):
            held.port.independent = True
            gone += 1
        assert fleets.sustains(game, port.faction) < fleets.UPKEEP, (
            f"{port.faction} still clears {fleets.sustains(game, port.faction):.0f} "
            "a day with every holding gone independent")
        assert fleets.guard_at(game, system, port.faction) == 0, (
            f"{port.faction} keeps a squadron on no revenue")
        assert control.means(game, contact) == 3, (
            f"a capital with no squadron still reaches "
            f"{control.LADDER[control.means(game, contact)]}")
        return (f"{system.name}: repelled while guarded · warded once "
                f"{gone} holdings went independent and left "
                f"{port.faction} on {fleets.sustains(game, port.faction):.0f} "
                "a day")

    @check("a screen can say what is on station")
    def _():
        game = new_game("board")
        told = fleets.note(game, game.system)
        assert told, "nothing said about a system with a fleet in it"
        here = fleets.squadron_at(game, game.system)
        if here:
            assert "On station" in told, told
            assert fleets.keeper_of(game, game.system) in here
        empty = next((s for s in game.galaxy.systems
                      if not fleets.squadron_at(game, s)), None)
        assert empty is not None, "every system in the sector is garrisoned"
        assert "Nothing on station" in fleets.note(game, empty)
        assert fleets.keeper_of(game, empty) == ""
        return f"{game.system.name}: {told}"


def _quay_contact(game, system):
    """The anchorage contact for this system's port."""
    from ..sim import track as track_sim
    for contact in track_sim.contacts(game, system):
        if contact.kind == "anchorage":
            return contact
    raise AssertionError(f"no anchorage in {system.name}")
