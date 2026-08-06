"""Law checks — being seen, being charged, and being made to pay.

The governance layer's premise is that a power's law is only as long as its
arm, so these check the *reach* before anything else: an act nobody could have
witnessed is not an offence, an act at somebody's quay is on a file before the
hold is closed, and the difference is playable.

Everything here performs the thing. No check asserts that a constant has a
value; they carry contraband through a quay, refuse a levy, let a judgment go
unanswered, and then look at what the powers did about it.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.offences import LAWFUL, OFFENCES, OFFENCES_BY_ID
from ..sim import debts as debts_sim
from ..sim import dockets
from ..sim import governance as gov_sim
from ..sim import law as law_sim
from ..sim import tribunal as tribunal_sim
from ..sim import warrants as warrants_sim
from .harness import Suite


def _under(seed: str, power: str):
    """A chronicle standing at a quay this power holds and watches."""
    game = new_game(seed)
    game.credits = 250_000
    game.system.port.faction = power
    game.system.faction = power
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("every offence is charged by somebody and reachable from play")
    def _():
        # The table is the whole design: which powers recognise what. An
        # offence nobody charges is dead weight, and one every power charges
        # makes the four of them interchangeable, which is the thing this
        # layer exists not to be.
        for offence in OFFENCES:
            assert offence.powers, f"{offence.id} is nobody's crime"
            assert set(offence.powers) <= set(LAWFUL), offence.id
            assert 0 < offence.gravity <= 1.0, offence.id
            assert offence.writ and offence.did, offence.id
        universal = [o.id for o in OFFENCES if set(o.powers) == set(LAWFUL)]
        only_one = [o.id for o in OFFENCES if len(o.powers) == 1]
        assert only_one, ("no offence belongs to a single power — the four "
                          "legal cultures are then interchangeable")
        assert len(universal) < len(OFFENCES), "every power charges everything"
        return (f"{len(OFFENCES)} offences; {len(universal)} universal, "
                f"{len(only_one)} peculiar to one power "
                f"({', '.join(only_one)})")

    @check("being seen is not being charged, and reach is what decides")
    def _():
        # The load-bearing claim. The same act, in two places, with two
        # different answers — and the difference is what a power actually has
        # in the system rather than a die roll.
        watched = _under("reach-watched", "charter")
        far = new_game("reach-far")
        far.credits = 250_000
        # Somewhere the Charter holds nothing at all.
        elsewhere = next((s for s in far.galaxy.systems
                          if getattr(s, "faction", None) != "charter"
                          and (s.port is None
                               or s.port.faction != "charter")), None)
        assert elsewhere is not None, "no unwatched system in the sector"
        far.location_id = elsewhere.id

        seen = dockets.witness(watched, "charter", watched.system)
        blind = dockets.witness(far, "charter", elsewhere)
        assert seen > 0.5, f"a power at its own quay saw nothing: {seen}"
        assert blind < dockets.FILE_FLOOR, (
            f"a power with nothing in the system still saw it: {blind}")

        here = dockets.allege(watched, "charter", "trafficking",
                              "you sold off the books", 1.0, watched.system)
        there = dockets.allege(far, "charter", "trafficking",
                               "you sold off the books", 1.0, elsewhere)
        assert here is not None, "the quay did not notice"
        assert there is None, "a power with no eyes there charged you anyway"
        return (f"witness {seen:.2f} at their own quay against {blind:.2f} "
                f"where they hold nothing — charged in one, not the other")

    @check("a power will not charge what its own table does not call a crime")
    def _():
        # The Freeholds are the market where an unlicensed seed has a posted
        # price. They cannot prosecute the thing they sell, and the table —
        # not a special case in the sim — is what says so.
        game = _under("freehold-seed", "freeholds")
        made = dockets.report(game, "contraband", "wildseed in the hold",
                              1.0, game.system)
        powers = {c.power for c in made}
        assert "freeholds" not in powers, (
            "the Freeholds charged a captain for carrying the thing they "
            "post a price for")
        assert OFFENCES_BY_ID["unlicensed"].powers == ("charter",), (
            "germination without a licence is not the Charter's alone")
        return (f"contraband at a Freehold quay charged by {sorted(powers) or 'nobody'}; "
                "the licence is the Charter's own affair")

    @check("an act nobody files on ages out, and two things never do")
    def _():
        game = _under("prescribe", "concordat")
        rng = RNG("prescribe")
        light = dockets.allege(game, "concordat", "evasion",
                               "you ran a picket", 0.35, game.system, seen=0.4)
        grave = dockets.allege(game, "concordat", "killing",
                               "you destroyed a hull", 1.0, game.system,
                               seen=1.0)
        assert light is not None and grave is not None
        # Stand well off and let the years pass without ever being filed on.
        light.weight = 0.05                       # too slight to bother with
        game.day += OFFENCES_BY_ID["evasion"].prescribes + 60
        game.law.swept.clear()
        dockets.sweep(game, 1, rng)
        assert light.outcome == "spent", (
            f"a slight matter never aged out: {light.state}/{light.outcome}")
        assert grave.state != "closed" or grave.outcome != "spent", (
            "destroying a hull prescribed, and it must not")
        return (f"an unfiled evasion is spent after "
                f"{OFFENCES_BY_ID['evasion'].prescribes:.0f} days; a killing "
                "is still live")

    @check("a judgment is a debt that grows, and ignoring it is its own charge")
    def _():
        game = _under("arrears", "concordat")
        rng = RNG("arrears")
        debt = debts_sim.owe(game, "concordat", 12_000, note="a judgment")
        assert debt is not None
        opening = debts_sim.balance(game, debt)
        game.day += 400
        grown = debts_sim.balance(game, debt)
        assert grown > opening, f"a judgment did not grow: {opening} → {grown}"

        lines = debts_sim.tick(game, 1, rng)
        assert any("arrears" in t.lower() or "file" in t.lower()
                   for _k, t in lines), lines
        charged = [c for c in law_sim.open_charges(game, "concordat")
                   if c.offence == "arrears"]
        assert charged, "an unpaid judgment never became a charge"
        # And exactly once, however long it stands.
        before = len(charged)
        game.day += 400
        debts_sim.tick(game, 1, rng)
        after = len([c for c in law_sim.open_charges(game, "concordat")
                     if c.offence == "arrears"])
        assert after == before, (
            f"one unpaid judgment generated {after} arrears charges — the "
            "docket fills with the same fact")
        return (f"₡{opening:,.0f} became ₡{grown:,.0f} over 400 days, and "
                "went on the file once")

    @check("a creditor takes its share at the till, and says so first")
    def _():
        # Distraint is the answer to a fine you can decline to pay by never
        # opening the screen. It has to happen where the money is.
        from ..sim import wharfage
        game = _under("distraint", "concordat")
        power = wharfage.holder(game, game.system)
        assert power, "the fixture has no counter"
        debts_sim.owe(game, power, 20_000, note="a judgment", distrain=True)
        warned = debts_sim.distraint_note(game, game.system)
        assert warned and "%" in warned, (
            f"the board did not warn before the counter took its cut: {warned!r}")

        owed_before = debts_sim.total_owed(game, power)
        purse = game.credits
        wharfage.collect(game, game.system, 30_000)
        owed_after = debts_sim.total_owed(game, power)
        assert owed_after < owed_before, (
            f"selling at their counter paid them nothing: {owed_before} → "
            f"{owed_after}")
        assert game.credits < purse, "the captain was not charged for it"
        return (f"₡{owed_before - owed_after:,.0f} taken out of a ₡30,000 "
                "sale, and the board said so before the sale")

    @check("the record survives a save and a reload")
    def _():
        import json

        from ..core.save import decode, encode
        game = _under("law-persist", "charter")
        rng = RNG("persist")
        dockets.allege(game, "charter", "contraband", "nine tonnes", 1.4,
                       game.system, seen=1.0)
        game.day += 40
        dockets.sweep(game, 40, rng)
        debts_sim.owe(game, "charter", 5_000, note="a judgment")
        warrants_sim.issue(game, "charter", "refuse", "because", "holdings")

        back = decode(json.loads(json.dumps(encode(game))))
        state = law_sim.ensure(back)
        assert len(state.charges) == len(game.law.charges), "charges lost"
        assert len(state.debts) == len(game.law.debts), "debts lost"
        assert len(state.warrants) == len(game.law.warrants), "warrants lost"
        assert state.charges[0].offence == "contraband", state.charges[0]
        assert warrants_sim.in_force(back), "the instrument did not survive"
        assert debts_sim.total_owed(back) > 0, "the debt did not survive"
        return (f"{len(state.charges)} charge(s), {len(state.debts)} debt(s) "
                f"and {len(state.warrants)} instrument(s) came back")

    @check("a captain who does nothing wrong is never charged with anything")
    def _():
        # The most important negative claim in the file. A governance layer
        # that accretes charges from ordinary play would be a tax on existing,
        # and the first thing a player would say is that the game is picking
        # on them.
        worst = 0.0
        for seed in ("clean-a", "clean-b", "clean-c"):
            game = new_game(seed)
            game.credits = 200_000
            for _ in range(16):
                game.ship.cargo["biomass"] = max(
                    game.ship.cargo.get("biomass", 0), 300)
                game.credits = max(game.credits, 200_000)
                game.advance_days(150)
                if game.dead:
                    break
            trouble = gov_sim.trouble(game)
            worst = max(worst, trouble)
            assert not law_sim.ensure(game).charges, (
                f"{seed}: a captain who never acted was charged with "
                f"{[c.offence for c in law_sim.ensure(game).charges]}")
            assert not warrants_sim.in_force(game), f"{seed}: instruments"
        return (f"three chronicles to day ~2,400 doing nothing illegal: "
                f"worst exposure {worst:.2f}")

    @check("the whole layer runs off one door, and the clock turns it")
    def _():
        game = _under("gov-tick", "charter")
        rng = RNG("gov")
        dockets.allege(game, "charter", "contraband", "eleven tonnes", 1.5,
                       game.system, seen=1.0)
        seen = []
        for _ in range(14):
            game.day += 30
            seen.extend(gov_sim.tick(game, 30, rng))
        assert seen, "the law never did anything over 420 days"
        closed = [c for c in law_sim.ensure(game).charges
                  if c.state == "closed"]
        assert closed, "a filed charge was never decided"
        assert gov_sim.note(game), "nothing to say on the status line"
        return (f"{len(seen)} thing(s) happened over 420 days; "
                f"{len(closed)} matter(s) decided — “{gov_sim.note(game)}”")

    @check("a captain who ignores everything does not drown the save file")
    def _():
        # **Measured, before the guard existed: 61,820 charges and ₡498
        # million owed inside eight years, from one contraband bust.** A
        # default charge decided in absence generated a default charge; its
        # debt went unpaid and generated arrears; that was decided in absence
        # too. The layer was generating its own work, geometrically, and a
        # save file of that shape does not load.
        from ..sim import customs
        game = _under("no-spiral", "charter")
        rng = RNG("no-spiral")
        game.scrutiny["charter"] = 1.0
        game.ship.cargo["wildseed"] = 9.0
        out = customs.inspect(game, rng)
        tries = 0
        while not out.get("caught") and tries < 40:
            game.ship.cargo["wildseed"] = 9.0
            out = customs.inspect(game, rng)
            tries += 1
        assert out.get("caught"), "could not get boarded to set the fixture up"

        for _ in range(40):                       # ten years of not caring
            game.advance_days(90)
        charges = law_sim.ensure(game).charges
        procedural = [c for c in charges
                      if OFFENCES_BY_ID[c.offence].procedural]
        assert len(charges) < 20, (
            f"ten years of ignoring one bust made {len(charges)} charges")
        per_power = {}
        for charge in procedural:
            key = (charge.power, charge.offence)
            per_power[key] = per_power.get(key, 0) + 1
        assert max(per_power.values(), default=0) <= 3, (
            f"a power raised the same procedural complaint repeatedly: "
            f"{per_power}")
        owed = debts_sim.total_owed(game)
        assert owed < 400_000, (
            f"ignoring one bust for a decade came to {owed:,.0f}")
        return (f"one bust ignored for ten years: {len(charges)} charges "
                f"(was 61,820) and {owed:,.0f} owed (was 498 million)")

    @check("exposure and the summons list agree with the record")
    def _():
        game = _under("expose", "sanhedrin")
        rng = RNG("expose")
        dockets.allege(game, "sanhedrin", "trespass", "their ground", 1.0,
                       game.system, seen=1.0)
        assert dockets.exposure(game, "sanhedrin") > 0
        assert dockets.exposure(game, "charter") == 0, "wrong power charged"
        game.day += 40
        dockets.sweep(game, 40, rng)
        waiting = tribunal_sim.summons(game)
        assert len(waiting) == 1 and waiting[0].power == "sanhedrin", waiting
        state = gov_sim.standing_with(game, "sanhedrin")
        assert state["filed"] == 1 and state["forum"], state
        return (f"exposure {dockets.exposure(game, 'sanhedrin'):.2f} with the "
                f"Dry Choir, none with anybody else; “{state['note']}”")
