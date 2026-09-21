"""People with lives, things to own, and somewhere to spend money.

Four claims:

- **A crew is people, not stations.** Everybody aboard has a homeworld, an
  upbringing, an ambition, berths before this one, relationships that lean
  for or against them, and possessions — all derived, so nothing is saved and
  an officer from an old chronicle has a family today.
- **What is on a shelf is where you are standing.** The chandler stocks the
  world's tech level and the customs desk enforces its law level, both read
  off the one profile, so a railgun is ordinary at law 2 and contraband at
  law 9 *from the same table*.
- **The counter keeps its spread, and the bank makes nothing.** Selling back
  always pays less than buying; a deposit moves credits and never mints them.
  A round trip through either must not leave a captain richer.
- **A night ashore costs money and buys something that is not money** —
  morale, loyalty, standing, and sometimes a rumour that points at a real
  world.
"""

from __future__ import annotations

from collections import Counter

from ..core.rng import RNG
from ..core.state import new_game
from ..data import backgrounds as bg
from ..data import careers as career_table
from ..data import kit as kit_table
from ..data import venues as venue_table
from ..sim import person as person_sim
from ..sim import profile as profile_sim
from ..sim import shore
from .harness import Suite

CROWD = ("shore-a", "shore-b", "shore-c", "shore-d")


def _port(game):
    """A system with a port, made current."""
    system = next(s for s in game.galaxy.systems if s.port and s.market)
    game.location_id = system.id
    return system


def run(suite: Suite) -> None:
    check = suite.check

    @check("everybody aboard is a person, not a station")
    def _():
        homes, wants, ties, kit, berths, seen = (Counter(), Counter(),
                                                 Counter(), Counter(), 0, 0)
        for seed in CROWD:
            game = new_game(seed)
            for officer in game.officers:
                who = person_sim.of(game, officer)
                seen += 1
                assert who.home is not None and who.raised is not None
                assert who.wants is not None, who.ambition
                assert who.ties, f"{who.name} knows nobody at all"
                assert who.kit, f"{who.name} owns nothing at all"
                homes[who.homeworld] += 1
                wants[who.ambition] += 1
                ties[len(who.ties)] += 1
                berths += len(who.berths)
                for item in who.kit:
                    assert item in kit_table.ITEM_BY_ID, item
                    kit[item] += 1
                for tie in who.ties:
                    assert tie.kind in bg.TIE_BY_ID, tie.kind
                    assert tie.who and tie.where, tie
                assert bg.TIES_LEAST <= len(who.ties) <= bg.TIES_MOST
        # A crew where everybody is from the same place is not a crew.
        assert len(homes) >= 5, dict(homes)
        assert len(wants) >= 5, dict(wants)
        assert len(kit) >= 12, len(kit)
        return (f"{seen} people: {len(homes)} homeworlds, {len(wants)} "
                f"ambitions, {sum(ties.elements()) if False else berths} "
                f"berths between them, {len(kit)} kinds of possession")

    @check("a person is derived: the same every time, and stored nowhere")
    def _():
        game = new_game("shore-same")
        officer = game.officers[0]
        was = game.rng_seed
        first = person_sim.of(game, officer)
        again = person_sim.of(game, officer)
        assert game.rng_seed == was, "reading a person moved the chronicle"
        assert person_sim.says(first) == person_sim.says(again)
        assert [t.who for t in first.ties] == [t.who for t in again.ties]
        twin = new_game("shore-same")
        other = next(o for o in twin.officers if o.id == officer.id)
        assert person_sim.of(twin, other).kit == first.kit
        assert not any(f.startswith("person") or f.startswith("tie")
                       for f in vars(officer)), sorted(vars(officer))
        return (f"{first.name}: {len(first.ties)} people, "
                f"{len(first.kit)} possessions, read three times the same")

    @check("every table the people are dealt from is real and complete")
    def _():
        for home in bg.HOMEWORLDS:
            for name in home.skills:
                assert name in career_table.SKILLS, (home.id, name)
        for raised in bg.UPBRINGINGS:
            for name in raised.skills:
                assert name in career_table.SKILLS, (raised.id, name)
        for tie in bg.TIE_KINDS:
            assert "{who}" in tie.line, tie.id
        for career, kinds in bg.CAREER_TIES.items():
            assert career in career_table.CAREER_BY_ID, career
            for kind in kinds:
                assert kind in bg.TIE_BY_ID, (career, kind)
        # The catalogue: every id unique, every skill real, every price sane.
        ids = [i.id for i in kit_table.ITEMS]
        assert len(ids) == len(set(ids)), "two items share an id"
        for item in kit_table.ITEMS:
            assert item.category in kit_table.CATEGORY_NAME, item.id
            assert not item.gives or item.gives in career_table.SKILLS, item.id
            assert 0 <= item.law <= 10, item.id
            assert item.tl >= 0 and item.mass >= 0, item.id
        for cid, _n, _note in kit_table.CATEGORIES:
            assert kit_table.BY_CATEGORY[cid], f"{cid} is an empty shelf"
        for venue in venue_table.VENUES:
            assert venue.kind in venue_table.KIND_NAME, venue.id
            assert not venue.favours or venue.favours in career_table.SKILLS
        return (f"{len(kit_table.ITEMS)} items over "
                f"{len(kit_table.CATEGORIES)} categories, "
                f"{len(venue_table.VENUES)} venues, "
                f"{len(career_table.SKILLS)} skills, all consistent")

    @check("the shelf is the tech level and the desk is the law level")
    def _():
        game = new_game("shore-shelf")
        widest, tightest, seen = None, None, 0
        for system in game.galaxy.systems:
            world = profile_sim.port_world(system)
            if not system.port or world is None:
                # A port whose system is nothing but gas giants and comets
                # has no world to stand on, and `shore` already answers with
                # an empty concourse rather than a crash.
                assert not shore.shelves(game, system)
                continue
            got = profile_sim.profile(game, system, world)
            rows = shore.shelves(game, system)
            seen += 1
            for row in rows:
                assert kit_table.stocked_at(row["item"], got.tech), (
                    f"{system.port.name} at TL {got.tech} stocks "
                    f"{row['item'].name} (TL {row['item'].tl})")
                assert row["legal"] == kit_table.legal_at(row["item"], got.law)
            if widest is None or len(rows) > widest[0]:
                widest = (len(rows), system.port.name, got.tech)
            if tightest is None or len(rows) < tightest[0]:
                tightest = (len(rows), system.port.name, got.tech)
        assert seen and widest and tightest
        assert widest[0] > tightest[0], (widest, tightest)
        # One item, two worlds: the law decides, and the same table says both.
        rail = kit_table.ITEM_BY_ID["gauss_rifle"]
        assert kit_table.legal_at(rail, 2) and not kit_table.legal_at(rail, 9)
        return (f"{seen} ports; widest {widest[1]} at TL {widest[2]} with "
                f"{widest[0]} lines, tightest {tightest[1]} with "
                f"{tightest[0]}")

    @check("the chandler keeps its spread and the bank mints nothing")
    def _():
        game = new_game("shore-money")
        system = _port(game)
        game.credits = 400_000
        rows = [r for r in shore.shelves(game, system) if r["cr"] > 300]
        assert rows, "nothing here costs anything"
        worst = 0
        for row in rows[:20]:
            before = game.credits
            got = shore.buy(game, system, row["item"].id)
            assert got["ok"], got
            back = shore.sell(game, system, row["item"].id)
            assert back["ok"], back
            assert back["cr"] < got["cr"], (row["item"].id, got, back)
            worst = max(worst, game.credits - before)
        assert worst <= 0, f"a round trip through the chandler made {worst}"
        # The bank moves money and never makes it.
        held = game.credits
        shore.deposit(game, system, 50_000)
        assert game.credits == held - 50_000, game.credits
        assert game.deposited == 50_000, game.deposited
        shore.withdraw(game, system, 50_000)
        assert game.credits == held and game.deposited == 0.0, (
            game.credits, game.deposited)
        # And it refuses what is not there.
        assert not shore.withdraw(game, system, 10)["ok"]
        return (f"20 round trips through the chandler, best {worst:+,.0f}; "
                "50,000 banked and drawn, to the credit")

    @check("a night ashore costs money and buys something that is not money")
    def _():
        game = new_game("shore-night")
        system = _port(game)
        game.credits = 200_000
        game.ship.morale = 0.5
        rows = shore.open_here(game, system, "entertainment")
        assert rows, "nowhere to go on a class-A concourse"
        venue = next(v for v in rows if v.morale > 0)
        said = shore.ashore_note(game, system, venue)
        assert "credits" in said and "morale" in said, said
        before = (game.credits, game.ship.morale)
        got = shore.ashore(game, system, venue.id, RNG("night"))
        assert got["ok"], got
        assert game.credits == before[0] - got["cr"], game.credits
        assert game.ship.morale > before[1], game.ship.morale
        assert got["cr"] == shore.ashore_cost(game, venue), (
            "the screen quoted one price and the till charged another")
        one_night = game.ship.morale
        # Broke, and it says so rather than going anyway.
        game.credits = 1
        assert not shore.ashore(game, system, venue.id, RNG("n"))["ok"]
        # A rumour points at a world that exists.
        heard = ""
        for step in range(40):
            game.credits = 200_000
            out = shore.ashore(game, system, venue.id, RNG(f"r{step}"))
            if out.get("heard"):
                heard = out["heard"]
                break
        if heard:
            assert any(s.name in heard for s in game.galaxy.systems) \
                or "Nothing worth" in heard, heard
        return (f"{venue.name}: {got['cr']:,} credits, morale "
                f"{before[1]:.0%} → {one_night:.0%} on one night"
                + (f'; heard "{heard[:44]}…"' if heard else ""))

    @check("what a port offers is what the world can support")
    def _():
        game = new_game("shore-ports")
        rich = poor = None
        for system in game.galaxy.systems:
            world = profile_sim.port_world(system)
            if not system.port or world is None:
                continue
            got = profile_sim.profile(game, system, world)
            here = shore.open_here(game, system)
            for venue in here:
                assert got.starport >= venue.port, (system.port.name, venue.id)
                assert got.population >= venue.people, (system.port.name,
                                                        venue.id)
            if rich is None or len(here) > len(rich[1]):
                rich = (system, here)
            if poor is None or len(here) < len(poor[1]):
                poor = (system, here)
        assert rich and poor and len(rich[1]) > len(poor[1]), (rich, poor)
        return (f"{rich[0].port.name} carries {len(rich[1])} venues; "
                f"{poor[0].port.name} carries {len(poor[1])}")

    @check("the Concourse tab opens, and a purchase shows up on it")
    def _():
        from PyQt6.QtWidgets import QLabel
        from .qtkit import app as _app
        from .qtkit import main_window
        keep = _app()
        game = new_game("shore-ui")
        system = _port(game)
        game.credits = 300_000
        win = main_window(game, (1360, 880))
        win.go("port")
        view = win.views["port"]
        view.tab = "concourse"
        view.refresh()
        for _ in range(4):
            keep.processEvents()
        said = " ".join(lab.text() for lab in view.findChildren(QLabel)
                        if lab.text())
        assert "chandler" in said.lower(), "no chandler on the concourse"
        assert "credits" in said, "the purse is not shown"
        row = shore.shelves(game, system)[0]
        shore.buy(game, system, row["item"].id)
        view.refresh()
        for _ in range(4):
            keep.processEvents()
        again = " ".join(lab.text() for lab in view.findChildren(QLabel)
                         if lab.text())
        assert "1 possession" in again, "what was bought is not on the screen"
        win.close()
        keep.processEvents()
        return f"the concourse opens and {row['item'].name} lands in the purse"
