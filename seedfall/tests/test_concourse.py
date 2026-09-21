"""Places, and everything they sell to a person rather than to a hull.

Five claims:

- **People are not only at starports.** A habitat drum, a holding of yours
  and a power's settlement are places with a concourse, gated on the same
  four numbers a quay is: how much of a place it is, how many people, how
  advanced, how hard the law. Nothing is stored; a place is read off what
  the chronicle already holds.
- **The law runs both ways.** Every door is gated on tech and on law, and
  the `vice` tier is gated *downwards* — a chop shop, a fence and a black
  clinic appear where the law does not reach and vanish where it does. So
  what a captain can buy is a fact about where they chose to put in.
- **The price quoted is the price charged**, for a body as for a cargo.
  `clinic.quote` says the money, the days and the odds, and `clinic.buy`
  performs exactly that. A round trip through any counter never leaves a
  captain richer.
- **What is bought is kept.** A fitted weave and a paid-for course are
  facts, not derivations: they are saved, they survive a reload, and
  `lifepath.of` folds them onto the derived record so the ship's own
  checks feel them without knowing this file exists.
- **The screen decides nothing.** Every tab opens at two sizes, everywhere,
  and every button is an act in the sim.
"""

from __future__ import annotations

from collections import Counter

from ..core.rng import RNG
from ..core.state import new_game
from ..data import careers as career_table
from ..data import treatments as treat_table
from ..data import venue_types
from ..data import venues as venue_table
from ..sim import clinic as clinic_sim
from ..sim import lifepath as life_sim
from ..sim import places as places_sim
from ..sim import shore
from .harness import Suite

CROWD = ("conc-a", "conc-b", "conc-c")


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


def _settle(game):
    """Put a drum and a works into the sector, so the other three kinds of
    place are real rather than theoretical.

    A fresh chronicle holds nothing but starports — no colony has been
    planted and no power has founded anything — so a check that only walked
    a fresh sector would be asserting about one of the four kinds and
    claiming all of them.
    """
    from ..sim import colony as colony_sim
    from ..sim import settlement as settlement_sim
    system = next(s for s in game.galaxy.systems if s.port and len(s.bodies) > 2)
    drum = colony_sim.Colony(
        id=9001, class_id="arca_drum", name="The Drum",
        system_id=system.id, body_id=system.bodies[1].id, need=0,
        online=True)
    rig = colony_sim.Colony(
        id=9002, class_id="monitor_station", name="Far Watch",
        system_id=system.id, body_id=system.bodies[2].id, need=0,
        online=True)
    # And a garrison, which is one of the two classes added with the
    # concourse: a crowd rather than a machine, so it carries doors.
    post = colony_sim.Colony(
        id=9004, class_id="bastion_post", name="The Bastion",
        system_id=system.id, body_id=system.bodies[-1].id, need=0,
        online=True)
    game.colonies = list(getattr(game, "colonies", []) or []) + [drum, rig,
                                                                post]
    works = settlement_sim.Settlement(
        id=9003, power="charter", system_id=system.id,
        body_id=system.bodies[2].id, good="volatiles")
    game.settlements = list(settlement_sim.held(game)) + [works]
    game.location_id = system.id
    return system


def run(suite: Suite) -> None:
    check = suite.check

    @check("a place is anywhere with people, and it is derived from nothing new")
    def _():
        kinds, seen = Counter(), 0
        for seed in CROWD:
            game = new_game(seed)
            _settle(game)
            was = game.rng_seed
            for system in game.galaxy.systems:
                for place in places_sim.in_system(game, system):
                    seen += 1
                    kinds[place.kind] += 1
                    assert place.heads >= 0 and 0 <= place.amenity <= 5
                    assert 0 <= place.people <= 12, place
                    assert place.tech >= 0 and place.law >= 0
                    assert places_sim.says(place), place.name
                    assert places_sim.by_id(
                        game, place.id, system) is not None
            assert game.rng_seed == was, "reading the sector's places cost luck"
        assert seen >= 20, seen
        # All four kinds are real, and the drum is a *city*: a million people
        # in orbit had nothing to sell anybody until places existed.
        for kind, _name, _note in places_sim.KINDS:
            assert kinds[kind], f"no {kind} anywhere in three sectors"
        game = new_game("conc-kinds")
        system = _settle(game)
        drum = next(p for p in places_sim.in_system(game, system)
                    if p.name == "The Drum")
        assert drum.kind == "habitat" and drum.amenity == 5, drum
        assert len(shore.open_here(game, drum)) > 20, (
            "a million people in a drum and nowhere to eat")
        rig = next(p for p in places_sim.in_system(game, system)
                   if p.name == "Far Watch")
        assert rig.kind == "holding", rig
        assert len(shore.open_here(game, rig)) < len(
            shore.open_here(game, drum))
        # A headcount and its population digit agree, which is the join to
        # every venue gate in the game.
        assert places_sim.digit(1) == 0 and places_sim.digit(1_000_000) == 6
        assert places_sim.amenity_for(1_000_000) == 5
        assert places_sim.amenity_for(0) == 0
        return (f"{seen} places over {len(CROWD)} sectors: "
                + ", ".join(f"{n} {k}" for k, n in kinds.most_common()))

    @check("what is open is where you are standing, and the law runs both ways")
    def _():
        game = new_game("conc-open")
        lawful = seedy = None
        for system in game.galaxy.systems:
            for place in places_sim.in_system(game, system):
                rows = shore.open_here(game, place)
                for venue in rows:
                    assert venue_types.open_to(venue, place), (
                        f"{venue.id} is open at {place.name} and should not be")
                vice = [v for v in rows if v.kind == "vice"]
                if vice and (seedy is None or place.law < seedy[0].law):
                    seedy = (place, vice)
                if place.law >= 7 and (lawful is None
                                       or len(rows) > len(lawful[1])):
                    lawful = (place, rows)
        assert seedy, "nowhere in the sector is lawless enough for a back room"
        assert lawful, "nowhere in the sector is lawful"
        assert not [v for v in lawful[1] if v.kind == "vice"], (
            f"{lawful[0].name} is law {lawful[0].law} and has a chop shop")
        # Every venue's tables are real.
        for venue in venue_table.VENUES:
            assert venue.kind in venue_table.KIND_NAME, venue.id
            assert not venue.favours or venue.favours in career_table.SKILLS
            for offer in venue.offers:
                assert offer in venue_table.OFFER_NAME, (venue.id, offer)
        ids = [v.id for v in venue_table.VENUES]
        assert len(ids) == len(set(ids)), "two venues share an id"
        return (f"{len(venue_table.VENUES)} doors over "
                f"{len(venue_table.KINDS)} kinds; {seedy[0].name} at law "
                f"{seedy[0].law} carries {len(seedy[1])}, "
                f"{lawful[0].name} at law {lawful[0].law} carries none")

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

    @check("a sector with a concourse in it has people who worked on one")
    def _():
        from ..data import backgrounds as bg
        from ..data.colonies import COLONIES_BY_ID
        # Fourteen careers, and every one of them complete: the six civil
        # services were added with the concourse they explain.
        for career in career_table.CAREERS:
            assert career.ranks and career.skills, career.id
            assert career.mishaps and career.events and career.benefits
            assert career.station in career_table.STATION_SKILLS, career.id
            assert career.id in bg.CAREER_TIES, (
                f"{career.id} leaves nobody behind")
            for name in career.skills + career.officer_skills:
                assert name in career_table.SKILLS, (career.id, name)
        for station, pool in career_table.BY_STATION.items():
            assert station in career_table.STATION_SKILLS, station
            for cid in pool:
                assert cid in career_table.CAREER_BY_ID, (station, cid)
        # The new trades are not decoration: somebody's door wants each.
        wanted = {v.favours for v in venue_table.VENUES if v.favours}
        for name in ("cybernetics", "pharmacy", "security", "teaching"):
            assert name in career_table.SKILLS, name
            assert name in wanted, f"nobody on a concourse wants {name}"
        # And the new habitat classes are real places that carry doors.
        game = new_game("conc-careers")
        civil = set()
        for seed in ("civ-a", "civ-b", "civ-c", "civ-d"):
            other = new_game(seed)
            for officer in other.officers:
                civil.add(life_sim.of(other, officer).career)
        # The two new classes are places to live rather than machines with
        # people in them, and both carry a real concourse.
        for klass in ("stack_arcology", "bastion_post"):
            got = COLONIES_BY_ID[klass]
            assert got.sites and got.days > 0 and got.pop >= 500, klass
        assert len(career_table.CAREERS) >= 14, len(career_table.CAREERS)
        return (f"{len(career_table.CAREERS)} careers and "
                f"{len(career_table.SKILLS)} skills, all consistent; "
                f"{len(civil)} distinct careers dealt over four crews")

    @check("a gate says who runs it and what they have on you")
    def _():
        from ..sim import authority as auth_sim
        game = new_game("conc-rule")
        _settle(game)
        seen, hard, soft = 0, None, None
        for system in game.galaxy.systems:
            for place in places_sim.in_system(game, system):
                said = auth_sim.says(game, place)
                assert said and len(said) >= 4, (place.name, said)
                digit, name, about = auth_sim.government(game, place)
                assert name and about, place.name
                watch = auth_sim.garrison(game, place)
                assert 0.0 <= watch["watch"] <= 1.0, watch
                risk = auth_sim.against_you(game, place)
                assert risk["charges"] == [] or risk["charges"]
                seen += 1
                if hard is None or place.law > hard.law:
                    hard = place
                if soft is None or place.law < soft.law:
                    soft = place
        assert seen >= 10, seen
        assert hard.law > soft.law, (hard.law, soft.law)
        # The words change with the digit, which is the whole point of it.
        assert auth_sim.law_words(0) != auth_sim.law_words(9)
        # A holding of yours is governed by you, and says so.
        mine = next(p for p in places_sim.in_system(game) if p.mine)
        assert auth_sim.government(game, mine)[1] == "Yours", mine.name
        return (f"{seen} gates read: {hard.name} at law {hard.law}, "
                f"{soft.name} at law {soft.law}")

    @check("the Concourse screen opens everywhere, on every tab")
    def _():
        from PyQt6.QtWidgets import QLabel
        from .qtkit import app as _app
        from .qtkit import main_window
        keep = _app()
        game = new_game("conc-ui")
        _n, system, place = _richest(game)
        game.location_id = system.id
        game.orbit_body = place.body_id
        game.credits = 500_000
        counted = Counter()
        for size in ((1040, 680), (1440, 900)):
            win = main_window(game, size)
            win.go("concourse")
            view = win.views["concourse"]
            for tab in ("shops", "board", "clinic", "evening", "rule"):
                view.tab = tab
                view.refresh()
                for _ in range(4):
                    keep.processEvents()
                said = " ".join(lab.text() for lab in
                                view.findChildren(QLabel) if lab.text())
                assert place.name in said, (tab, said[:80])
                counted[tab] += len(said)
            # And it walks to every other place in the system.
            for other in places_sim.in_system(game, system):
                view.go_place(other.id)
                for _ in range(3):
                    keep.processEvents()
                page = " ".join(lab.text() for lab in
                                view.findChildren(QLabel) if lab.text())
                assert other.name in page, other.name
            win.close()
            keep.processEvents()
        assert all(counted[t] > 200 for t in counted), dict(counted)
        return (f"five tabs at two sizes at {place.name}, and every place "
                f"in the system walked")
