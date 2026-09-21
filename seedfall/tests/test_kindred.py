"""What a crew may be made of, and who will have it aboard.

Five claims:

- **Eight substrates can stand a watch**, and every one of them is complete:
  a lifespan, an upkeep bill, a category anybody at a gate sorts them into,
  and a face that is drawn as what it is rather than as a person with
  unusual skin.
- **A creed is an attitude.** The powers have said what they think since the
  first commit and none of it reached a gate. It does now: the Charter's
  *one biology* refuses aliens, the Freeholds' *whatever flies* welcomes
  everybody, and the Dry Choir's *substrate is an implementation detail*
  treats all eight alike — including the reading of their papers.
- **A government tightens and only the law shuts a gate.** A bureaucracy
  makes a thing harder; it does not make it impossible. Without that rule
  an ordinary Charter capital refused six substrates of eight outright.
- **A hull decides who turns up.** A fabricated hull draws frames and minds
  to its board and a grown one does not, and a board never holds somebody
  the port would refuse at the gate.
- **A mixed crew costs something, and only sometimes.** Nothing at all
  without somebody aboard who minds, and nothing at all on a bridge of one
  kind — and real money in goodwill when both are true.
"""

from __future__ import annotations

from collections import Counter

from ..core.rng import RNG
from ..core.state import new_game
from ..data import kindred as table
from ..data import lineages as lineage_table
from ..sim import crew as crew_sim
from ..sim import kindred as kindred_sim
from ..sim import lifespan as lifespan_sim
from ..sim import places as places_sim
from .harness import Suite


def _ports(game) -> list:
    out = []
    for system in game.galaxy.systems:
        out.extend(p for p in places_sim.in_system(game, system)
                   if p.kind == "port")
    return out


def run(suite: Suite) -> None:
    check = suite.check

    @check("eight substrates can stand a watch, and every one is complete")
    def _():
        for lineage in lineage_table.LINEAGES:
            assert lineage.id in table.CLASS_OF, lineage.id
            assert table.CLASS_OF[lineage.id] in table.CLASS_NAME
            assert lineage.prime > 0 and lineage.span > lineage.prime
            assert lineage.ageing >= 0 and lineage.decline >= 0
            assert lineage.what and lineage.ending
            # An upkeep bill payable in a currency nobody sells is not a
            # decision, which is this file's oldest rule.
            from ..data.commodities import BY_ID
            for good in lineage.upkeep:
                assert good in BY_ID, (lineage.id, good)
        assert len(lineage_table.LINEAGES) >= 8
        for faction, view in table.FACTION_VIEW.items():
            for kind, band in view.items():
                assert kind in table.CLASS_NAME, (faction, kind)
                assert band in table.BANDS, (faction, band)
        for family, weights in table.HULL_DRAW.items():
            for lineage_id in weights:
                assert lineage_id in lineage_table.LINEAGES_BY_ID, lineage_id
        return (f"{len(lineage_table.LINEAGES)} substrates over "
                f"{len(table.CLASSES)} categories, every table complete")

    @check("a creed is an attitude, and a gate finally reads it")
    def _():
        game = new_game("kin-creed")
        seen = {}
        for place in _ports(game):
            if place.faction and place.faction not in seen:
                seen[place.faction] = place
        assert len(seen) >= 3, sorted(seen)
        # The Charter's one biology: flesh yes, not-from-here no.
        assert table.view_of("charter", "born") == "welcome"
        assert table.view_of("charter", "alien") == "refused"
        # The Freeholds take anything that flies.
        assert table.view_of("freeholds", "machine") == "welcome"
        # And the Choir means what it says about substrate.
        for _cid, _name, _note in table.CLASSES:
            assert table.view_of("sanhedrin", _cid) == "welcome", _cid
        # Asked of a real gate, the bands come out different per power.
        bands = {}
        for faction, place in seen.items():
            bands[faction] = kindred_sim.standing(game, place, "frame")["band"]
        assert len(set(bands.values())) >= 2, bands
        return "; ".join(f"{f}: a frame is {b}" for f, b in
                         sorted(bands.items()))

    @check("a government tightens, and only the law shuts a gate")
    def _():
        game = new_game("kin-gov")
        refused = Counter()
        seen, shut = 0, []
        for place in _ports(game):
            for lineage in lineage_table.LINEAGES:
                got = kindred_sim.standing(game, place, lineage.id)
                seen += 1
                assert got["band"] in table.BANDS, got
                if got["refused"]:
                    refused[lineage.id] += 1
                    # A refusal is either the power's own view or the law
                    # closing it. A bureaucracy alone may not do it.
                    own = table.view_of(place.faction,
                                        table.class_of(lineage.id))
                    assert own == "refused" or place.law >= table.LAW_CLOSES, (
                        f"{place.name} ({place.faction}, law {place.law}) "
                        f"refuses {lineage.id} and neither its creed nor its "
                        "law says so")
                    shut.append(place.name)
        assert seen >= 100, seen
        assert refused, "nowhere in the sector refuses anybody"
        # And not everywhere: a sector that refused everything would be the
        # same defect the other way round.
        assert sum(refused.values()) < seen * 0.4, dict(refused)
        return (f"{seen} gates asked; {sum(refused.values())} refusals, "
                f"worst {refused.most_common(1)[0][0]}")

    @check("your own deck answers to nobody")
    def _():
        game = new_game("kin-own")
        aboard = places_sim.ship(game)
        assert aboard is not None
        for lineage in lineage_table.LINEAGES:
            got = kindred_sim.standing(game, aboard, lineage.id)
            assert got["band"] == "welcome", (lineage.id, got)
            assert not got["refused"]
        assert not kindred_sim.kept_aboard(game, aboard)
        return f"all {len(lineage_table.LINEAGES)} substrates welcome aboard"

    @check("a hull decides who turns up, and a gate decides who is offered")
    def _():
        game = new_game("kin-draw")
        game.credits = 400_000
        drawn = {}
        for chassis, family in (("navis", "grown"),
                                ("drayhorse", "fabricated")):
            game.ship.chassis = chassis
            weights = kindred_sim.draw_for(game)
            assert weights == table.HULL_DRAW[family], (chassis, weights)
            seen = Counter()
            for place in _ports(game)[:20]:
                for officer in crew_sim.pool_here(game, place):
                    seen[officer.lineage] += 1
                    # Nobody on a board is somebody the gate would refuse.
                    ok, why = kindred_sim.may_sign(game, place,
                                                   officer.lineage)
                    assert ok, (place.name, officer.lineage, why)
            drawn[chassis] = seen
        assert drawn["drayhorse"].get("frame", 0) > 0, (
            "a fabricated hull draws no frames at all")
        assert drawn["navis"].get("frame", 0) == 0, (
            "a grown hull is drawing frames")
        assert sum(drawn["navis"].values()) > 0
        return (f"grown: {dict(drawn['navis'])}; "
                f"fabricated: {dict(drawn['drayhorse'])}")

    @check("a mixed crew costs something, and only when somebody minds")
    def _():
        game = new_game("kin-rub")
        for n, officer in enumerate(game.officers):
            officer.lineage = ("wet", "frame", "dry")[n % 3]
            officer.conviction = "purse"
        quiet = kindred_sim.friction(game)
        assert quiet["per_day"] == 0.0, quiet
        assert kindred_sim.complement(game)["kinds"] >= 2
        # Give one of them the view, and it starts costing.
        game.officers[0].conviction = kindred_sim.PURIST
        rub = kindred_sim.friction(game)
        assert rub["per_day"] > 0, rub
        assert rub["minders"] and rub["minders"][0] is game.officers[0]
        # A bridge of one kind costs nothing, whoever is aboard.
        for officer in game.officers:
            officer.lineage = "wet"
        assert kindred_sim.friction(game)["per_day"] == 0.0
        # And the tick actually moves loyalty when it does cost.
        for n, officer in enumerate(game.officers):
            officer.lineage = ("wet", "frame", "dry")[n % 3]
        was = game.officers[0].loyalty
        game.advance_days(30)
        assert game.officers[0].loyalty < was, (was,
                                                game.officers[0].loyalty)
        return (f"{rub['kinds']} kinds aboard costs {rub['per_day']:.2f} "
                "loyalty a day to the one who minds, and nothing to "
                "anybody else")

    @check("everybody has a face, and a frame is not drawn as a person")
    def _():
        from ..ui import portrait
        game = new_game("kin-face")
        officer = game.officers[0]
        flesh = None
        built = 0
        for lineage in lineage_table.LINEAGES:
            officer.lineage = lineage.id
            officer.age = None
            face = portrait.of(game, officer)
            assert face.kind == table.class_of(lineage.id), lineage.id
            assert face.note and lineage_table.LINEAGES_BY_ID[lineage.id]
            if face.built:
                built += 1
                assert face.bald >= 1.0, (
                    f"a {lineage.id} was drawn with hair")
            elif flesh is None:
                flesh = face
        assert built >= 3, built
        assert flesh is not None and not flesh.built
        # And the same substrate twice is the same face.
        officer.lineage = "frame"
        officer.age = None
        assert portrait.of(game, officer).skin == \
            portrait.of(game, officer).skin
        return (f"{len(lineage_table.LINEAGES)} substrates drawn, {built} of "
                "them built rather than born")

    @check("the screens say what the crew is made of and who is kept aboard")
    def _():
        from PyQt6.QtWidgets import QLabel
        from .qtkit import app as _app
        from .qtkit import main_window
        keep = _app()
        game = new_game("kin-ui")
        hard = None
        for place in _ports(game):
            if kindred_sim.standing(game, place, "frame")["refused"]:
                hard = place
                break
        game.officers[0].lineage = "frame"
        game.officers[0].conviction = kindred_sim.PURIST
        if hard is not None:
            game.location_id = hard.system_id
            game.orbit_body = hard.body_id
        win = main_window(game, (1440, 900))
        win.go("crew")
        view = win.views["crew"]
        view.tab = "watches"
        view.refresh()
        for _ in range(4):
            keep.processEvents()
        said = " ".join(lab.text() for lab in view.findChildren(QLabel)
                        if lab.text())
        assert "Frame" in said, "the crew screen never says what they are"
        win.go("concourse")
        conc = win.views["concourse"]
        conc.tab = "rule"
        conc.refresh()
        for _ in range(4):
            keep.processEvents()
        gate = " ".join(lab.text() for lab in conc.findChildren(QLabel)
                        if lab.text())
        assert "crew" in gate.lower(), gate[:120]
        win.close()
        keep.processEvents()
        return ("the Watches tab names the substrates; the gate says what it "
                "makes of them")
