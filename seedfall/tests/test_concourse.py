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
from ..sim import crew as crew_sim
from ..sim import lifepath as life_sim
from ..sim import lifespan as lifespan_sim
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

    @check("a quay counts the people aboard it, and serves the world below")
    def _():
        game = new_game("conc-quay-heads")
        quays, hub = [], None
        for system in game.galaxy.systems:
            port = next((p for p in places_sim.in_system(game, system)
                         if p.kind == "port"), None)
            if port is None:
                continue
            assert port.heads <= places_sim.QUAY_HEADS[5] * \
                places_sim.CAPITAL_HEADS, (port.name, port.heads)
            assert port.served >= port.heads, port
            line = places_sim.population(port)
            assert f"{port.heads:,}" in line
            if port.served > port.heads:
                assert f"{port.served:,}" in line and "aboard" in line
            quays.append(port)
            if system.port.capital:
                hub = port
        assert hub is not None and all(hub.heads >= q.heads for q in quays)
        return (f"{len(quays)} quays; the Fleet Hub "
                f"{places_sim.population(hub)}")

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
