"""Bodies, berths and faces: what a concourse does to the people on it.

Split from `test_concourse.py` at five hundred lines, along the seam that was
already there: that file is about *places* — what is open, who runs them,
who lived what life — and this is about what a place does to a person.

Five claims:

- **The price quoted is the price charged**, for a body as for a cargo, and
  what is bought is *kept*: a fitted weave and a paid-for course survive a
  save and reach every check the ship makes.
- **A hull is a place.** A LAZARET is a hospital with a drive, and what is
  open aboard is open *only* aboard — a grand hotel does not follow a cutter.
- **Anagathics are an arrangement, not a purchase.** Years come off on the
  day and the clinic bills every month after it; miss one and it stops.
- **A hiring board is wherever somebody stands under one**, not only at a
  quay, and the pool and the door that carries it always agree.
- **Everybody has a face**, it is the same face twice, and what a clinic has
  fitted into somebody is visible on it and placed on a body.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data import careers as career_table
from ..data import treatments as treat_table
from ..data import venues as venue_table
from ..sim import clinic as clinic_sim
from ..sim import crew as crew_sim
from ..sim import lifepath as life_sim
from ..sim import lifespan as lifespan_sim
from ..sim import places as places_sim
from ..sim import shore
from .harness import Suite


def _richest(game, kind: str = ""):
    """The place in this sector with the most on offer."""
    best = None
    for system in game.galaxy.systems:
        for place in places_sim.in_system(game, system):
            score = len(clinic_sim.offered(game, place, kind)) if kind \
                else len(shore.open_here(game, place))
            if best is None or score > best[0]:
                best = (score, system, place)
    return best


def run(suite: Suite) -> None:
    check = suite.check

    @check("every treatment is real, and the catalogue is consistent")
    def _():
        ids = [t.id for t in treat_table.TREATMENTS]
        assert len(ids) == len(set(ids)), "two treatments share an id"
        offers = {o for o, _n in venue_table.OFFERS}
        for got in treat_table.TREATMENTS:
            assert got.kind in offers, (got.id, got.kind)
            assert got.tl >= 0 and got.cr >= 0 and got.days >= 1
            assert got.days <= treat_table.LONGEST, got.id
            for cid in got.gives:
                assert cid in treat_table.SCORES, (got.id, cid)
            assert not got.skill or got.skill in career_table.SKILLS, got.id
            # A risk with no mishap is a threat nobody carries out.
            assert bool(got.risk) == bool(got.mishap), got.id
            # Somebody must actually sell this sort of work somewhere.
            assert venue_table.BY_OFFER.get(got.kind), got.kind
        cheap = treat_table.price_at(treat_table.TREATMENT_BY_ID["hand_deck"],
                                     15)
        dear = treat_table.price_at(treat_table.TREATMENT_BY_ID["hand_deck"], 9)
        assert cheap < dear, (cheap, dear)
        return (f"{len(treat_table.TREATMENTS)} treatments over "
                f"{len(treat_table.BY_KIND)} kinds; a palm deck is "
                f"{cheap:,} at TL 15 and {dear:,} at TL 9")

    @check("the clinic quotes what it charges, and what it does is kept")
    def _():
        game = new_game("conc-body")
        _n, system, place = _richest(game, "cyber")
        game.location_id = system.id
        game.orbit_body = place.body_id
        game.ashore = place.id          # across (`sim/crossing`)
        game.credits = 900_000
        rows = clinic_sim.offered(game, place, "cyber")
        assert rows, "nowhere in the sector fits anything to anybody"
        officer = game.officers[0]
        before = life_sim.of(game, officer)
        was_scores = dict(before.characteristics)
        got = rows[0]["treatment"]
        said = clinic_sim.quote(game, place, officer, got.id)
        assert said["ok"], said
        purse, day = game.credits, game.day
        out = clinic_sim.buy(game, place, officer, got.id, rng=RNG("ok"))
        assert out["ok"], out
        # The quote is the charge. Credits also move for the days the work
        # takes — wages and stores are charged by the clock, not by the
        # clinic — so the claim is about the *bill*, and that the purse never
        # comes out ahead of it.
        assert out["cr"] == said["cr"], (out["cr"], said["cr"])
        assert game.credits <= purse - said["cr"], (purse, game.credits)
        assert game.day >= day + got.days, (day, game.day)
        if out["went"]:
            after = life_sim.of(game, officer)
            for cid, delta in got.gives.items():
                assert after.characteristics[cid] >= was_scores[cid] + delta \
                    or after.characteristics[cid] == treat_table.SCORE_CAP, (
                        cid, was_scores[cid], after.characteristics[cid])
            assert got.id in game.fitted[str(officer.id)]
            # And it survives a reload: this is saved, not derived. A save
            # is JSON, which has no integer keys — a dict keyed by the
            # officer's id came back keyed by a string, which is why the
            # store is keyed by a string on the way in.
            from ..core.save import decode, encode
            again = decode(encode(game))
            assert got.id in (again.fitted or {}).get(str(officer.id), []), (
                "what was fitted did not survive a save")
        # Teaching is kept the same way and reaches the ship's own checks.
        tr = clinic_sim.offered(game, place, "train")
        if tr:
            game.credits = 900_000
            taught = clinic_sim.buy(game, place, officer,
                                    tr[-1]["treatment"].id, skill="broker",
                                    rng=RNG("teach"))
            assert taught["ok"], taught
            if taught["went"]:
                assert life_sim.of(game, officer).skill("broker") >= 0
        return (f"{got.name} at {place.name}: {said['cr']:,} credits, "
                f"{got.days} days, {said['odds']:.0%} — charged to the "
                "credit and kept through a save")

    @check("a cold berth takes somebody off the bridge and gives them back")
    def _():
        game = new_game("conc-ice")
        best = None
        for system in game.galaxy.systems:
            for place in places_sim.in_system(game, system):
                rows = clinic_sim.offered(game, place, "ice")
                if rows and (best is None or len(rows) > len(best[2])):
                    best = (system, place, rows)
        assert best, "nowhere in the sector racks a person"
        system, place, rows = best
        game.location_id = system.id
        game.orbit_body = place.body_id
        game.ashore = place.id          # across (`sim/crossing`)
        game.credits = 400_000
        officer = game.officers[0]
        aboard = len(game.officers)
        got = clinic_sim.freeze(game, place, officer, rows[-1]["treatment"].id)
        assert got["ok"], got
        assert len(game.officers) == aboard - 1
        assert clinic_sim.on_ice(game), "nobody in the rack"
        assert clinic_sim.ice_bill(game) == 0.0, "billed on the day they went in"
        game.advance_days(730)
        owed = clinic_sim.ice_bill(game)
        assert owed > 0, "two years in a rack and nothing owed"
        purse = game.credits
        back = clinic_sim.thaw(game, place, officer.id)
        assert back["ok"], back
        assert len(game.officers) == aboard
        assert game.credits == purse - owed, (purse, game.credits, owed)
        assert not clinic_sim.on_ice(game)
        return (f"{officer.name} racked at {place.name}, two years at "
                f"{owed:,.0f} credits, and up again")

    @check("a hull is a place, and a hospital ship is a hospital")
    def _():
        game = new_game("conc-ship")
        aboard = places_sim.ship(game)
        assert aboard is not None and aboard.kind == "ship", aboard
        small = len(shore.open_here(game, aboard))
        assert small >= 1, "nothing at all is open on a working hull"
        # Every door aboard is a door *only* aboard, and none of the ashore
        # ones follow you: a grand hotel in a cutter is the failure mode.
        for venue in shore.open_here(game, aboard):
            assert venue.aboard, venue.id
        port = next(p for p in places_sim.in_system(game)
                    if p.kind != "ship")
        for venue in shore.open_here(game, port):
            assert not venue.aboard, venue.id
        # A LAZARET is a hospital with a drive, and it can now act like one.
        game.ship.chassis = "lazaret"
        game.ship.crew = 120
        big = places_sim.ship(game)
        assert big.amenity > aboard.amenity, (aboard.amenity, big.amenity)
        doors = shore.open_here(game, big)
        assert len(doors) > small, (small, len(doors))
        care = clinic_sim.offered(game, big)
        assert care, "a hospital ship that cannot treat anybody"
        assert clinic_sim.offered(game, aboard) != care
        # And the hull's own tech rises with the tree, which is what puts a
        # vat deck on it.
        assert big.tech >= places_sim.SHIP_TECH_BASE
        return (f"a NAVIS carries {small} doors; a LAZARET carries "
                f"{len(doors)} and {len(care)} sorts of work")

    @check("anagathics are an arrangement, and the clinic goes on billing")
    def _():
        game = new_game("conc-course")
        best = None
        for system in game.galaxy.systems:
            for place in places_sim.in_system(game, system):
                rows = clinic_sim.offered(game, place, "years")
                if rows and (best is None or len(rows) > len(best[2])):
                    best = (system, place, rows)
        assert best, "nowhere in the sector sells a year"
        system, place, rows = best
        game.location_id = system.id
        game.orbit_body = place.body_id
        game.ashore = place.id          # across (`sim/crossing`)
        game.credits = 3_000_000
        officer = game.officers[0]
        was = lifespan_sim.age_of(officer, game)
        got = clinic_sim.buy(game, place, officer, rows[0]["treatment"].id,
                             rng=RNG("years"))
        assert got["ok"], got
        if not got["went"]:
            return "the course failed its throw; the arrangement is unproven"
        assert lifespan_sim.age_of(officer, game) < was, "no years came off"
        assert clinic_sim.course_of(game, officer) is not None
        month = clinic_sim.month_cost(game)
        assert month > 0, "a standing course that costs nothing"
        assert clinic_sim.slows(game, officer) == clinic_sim.COURSE_SLOW
        # A year passes: the clinic is paid, and they age more slowly for it.
        purse, aged = game.credits, lifespan_sim.age_of(officer, game)
        game.advance_days(365)
        assert game.credits < purse, "a year on a course and nothing charged"
        lived = lifespan_sim.age_of(officer, game) - aged
        assert 0.0 < lived < 0.9, f"a year on anagathics aged them {lived:.2f}"
        # And it stops when the money does, rather than running for free.
        game.credits = 0
        game.advance_days(120)
        assert not clinic_sim.courses(game), "an unpaid course is still running"
        assert clinic_sim.slows(game, officer) == 1.0
        return (f"{was:.0f} → {lifespan_sim.age_of(officer, game):.0f} years, "
                f"{month:,.0f} a month, and it stops when the money does")

    @check("a hiring board is wherever somebody is standing under one")
    def _():
        game = new_game("conc-hire")
        boards, biggest = 0, None
        for system in game.galaxy.systems:
            for place in places_sim.in_system(game, system):
                rows = crew_sim.pool_here(game, place)
                if not rows:
                    # No pool means no door offering one. The two must agree.
                    assert not shore.selling(game, place, "hire") or \
                        place.heads == 0, place.name
                    continue
                boards += 1
                assert shore.selling(game, place, "hire"), place.name
                if biggest is None or len(rows) > len(biggest[1]):
                    biggest = (place, rows)
        assert boards >= 3, boards
        place, rows = biggest
        # The same board twice, and nobody aboard is standing on it.
        again = crew_sim.pool_here(game, place)
        assert [o.name for o in again] == [o.name for o in rows]
        aboard = {o.name for o in game.officers}
        assert not aboard & {o.name for o in rows}
        # And signing one on works, through the same door the quay uses.
        game.credits = 200_000
        taker = next((o for o in rows if crew_sim.can_hire(game, o)[0]), None)
        if taker is not None:
            got = crew_sim.hire(game, taker)
            assert got["ok"], got
            assert taker in game.officers
        return (f"{boards} boards in the sector; {place.name} has "
                f"{len(rows)} under it")

    @check("everybody has a face, and what was fitted to them shows on it")
    def _():
        from ..ui import body_plan, portrait
        game = new_game("conc-face")
        seen = 0
        for officer in game.officers:
            face = portrait.of(game, officer)
            again = portrait.of(game, officer)
            assert face.skin == again.skin and face.hair == again.hair, (
                "a face is not the same face twice")
            assert 0.0 <= face.age <= 1.0 and face.collar
            assert face.note, officer.name
            assert not face.marks, "nothing has been fitted to anybody yet"
            seen += 1
        assert seen >= 1
        # Fit something visible, and it is visible.
        officer = game.officers[0]
        game.fitted = {str(officer.id): ["optic_suite", "cortex_link",
                                         "muscle_weave"]}
        face = portrait.of(game, officer)
        assert "eye" in face.marks and "temples" in face.marks, face.marks
        assert face.strain > 0 and portrait.worst_mark(face)
        assert portrait.named(portrait.worst_mark(face))
        assert portrait.treatments_showing(game, officer)
        # And the body plan puts each of them somewhere on a body.
        sites = body_plan.sites_for(game, officer)
        assert len(sites) == 3, sites
        for row in sites:
            assert -1.0 <= row["x"] <= 1.0 and 0.0 <= row["y"] <= 1.0
            assert row["where"], row
        assert len(body_plan.says(game, officer)) >= 4
        # Every treatment that goes *into* somebody has a place on the plate.
        for got in treat_table.TREATMENTS:
            if got.kind in ("care", "years", "ice", "train"):
                continue
            assert got.id in body_plan.SITES, (
                f"{got.id} is fitted to a person and has nowhere to be")
        return (f"{seen} faces, stable; three fittings on one of them, all "
                "of them somewhere on the plate")
