"""Opening checks — the commission you pick has to be the one you get.

Two things are pinned here.

The first is the invariant that makes the rest of the suite mean anything: a
`new_game()` with no choices must be *exactly* the game as it shipped. Three
hundred and seventy-odd checks are written against that opening. If choosing
nothing quietly changed it, every one of them would go on passing while
measuring a different game, which is worse than any of them failing.

The second is the project's usual rule, applied to the one screen that had
never had to obey it: what an opening says it will give you is what it gives.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.beginnings import ORIGINS, POSTINGS, STOCKS
from ..data.chassis import CHASSIS_BY_ID
from ..data.factions import FACTIONS_BY_ID
from ..data.hull_types import ACCEPTS
from ..data.parts import PARTS_BY_ID
from ..data.tech import STARTING_TECH
from ..sim import beginning as beginning_sim
from ..sim import shipyard as shipyard_sim
from .harness import Suite


def _dock_at_a_yard(game) -> bool:
    """Put the hull alongside something that can open it up.

    `apply_refit` used to work anywhere — the rule lived in the button, not
    the sim, so a hull could be stripped in deep space. It does not any more,
    and a check that refits has to say where it is standing. Not every system
    has a yard, so this moves the hull to one that does.
    """
    from ..sim import anchorage
    for candidate in [game.system] + list(game.galaxy.systems):
        for berth in anchorage.in_system(game, candidate):
            if berth.offers("shipyard"):
                game.location_id = candidate.id
                game.orbit_body = berth.body_id
                return True
    return False

def run(suite: Suite) -> None:
    check = suite.check

    @check("choosing nothing opens exactly the game that shipped")
    def _():
        for seed in ("keel", "verge-7", "identical"):
            plain = new_game(seed)
            chosen = new_game(seed, choices=beginning_sim.default())
            assert plain.ship.chassis == chosen.ship.chassis == "navis"
            assert plain.ship.fitted == chosen.ship.fitted
            assert plain.ship.name == chosen.ship.name == "Patient Increment"
            assert plain.ship.crew == chosen.ship.crew == 34
            assert plain.ship.cargo == chosen.ship.cargo
            assert plain.credits == chosen.credits == 18000
            assert plain.rep == chosen.rep
            assert plain.location_id == chosen.location_id
            assert sorted(plain.research.unlocked) == sorted(STARTING_TECH)
            assert [o.stat for o in plain.officers] == \
                   [o.stat for o in chosen.officers]
            assert plain.flags == chosen.flags == {}
        return "3 seeds: hull, outfit, purse, standing, crew and start identical"

    @check("every stock and origin together opens a game you can fly")
    def _():
        opened = 0
        for stock in STOCKS:
            for origin in beginning_sim.origins_for(stock.id):
                hulls = beginning_sim.hulls_for(stock.id, origin.id)
                assert hulls, f"{stock.id}/{origin.id} can fly nothing"
                choices = beginning_sim.Choices(
                    stock=stock.id, origin=origin.id, hull=hulls[0].id,
                    posting="charter")
                game = new_game(f"open-{stock.id}-{origin.id}", choices=choices)
                assert not game.dead
                assert game.ship_stats.jump > 0, "a hull that cannot jump"
                assert game.ship_stats.power >= 0
                assert game.system.port, "opened somewhere with no quay"
                assert game.credits >= 0, f"{origin.id} opens in debt"
                opened += 1
        return f"{opened} stock/origin openings, every one flyable"

    @check("the opening screen's forecast is the game you get")
    def _():
        checked = 0
        for stock in STOCKS:
            for origin in beginning_sim.origins_for(stock.id):
                hulls = beginning_sim.hulls_for(stock.id, origin.id)
                choices = beginning_sim.Choices(
                    stock=stock.id, origin=origin.id, hull=hulls[0].id,
                    posting="charter")
                said = beginning_sim.preview(choices)
                got = new_game(f"fore-{stock.id}-{origin.id}", choices=choices)

                assert got.credits == said["credits"], (
                    f"{origin.id}: said {said['credits']:,}, opened with "
                    f"{got.credits:,}")
                assert got.ship.chassis == said["chassis"].id
                assert sorted(got.research.unlocked) == said["tech"], (
                    f"{origin.id}: technologies differ")
                for fid, value in said["standing"].items():
                    assert abs(got.rep.get(fid, 0) - value) < 0.01, (
                        f"{origin.id}: said {fid} {value:+.0f}, opened at "
                        f"{got.rep.get(fid, 0):+.0f}")
                for cid, tonnes in said["cargo"].items():
                    assert abs(got.ship.cargo.get(cid, 0) - tonnes) < 0.01, (
                        f"{origin.id}: said {tonnes:g} t of {cid}, opened with "
                        f"{got.ship.cargo.get(cid, 0):g}")
                checked += 1
        return f"{checked} openings, every figure on the screen matching"

    @check("the bridge on the card is the bridge that sails")
    def _():
        # `preview` reported `crew_slots(stock)` — two for a dry stack — and
        # `apply` only touched the officers when the player had picked some,
        # which no screen let them do. So every chronicle opened with the
        # same three whoever you were, and the card said two for 30 of 90
        # stock/origin/posting openings.
        from ..data.beginnings import CREW_SLOTS

        assert len(set(CREW_SLOTS.values())) > 1, (
            "every lineage sails the same bridge, so this proves nothing")
        wrong, checked = [], 0
        for stock in STOCKS:
            for origin in ORIGINS:
                for posting in POSTINGS:
                    choices = beginning_sim.Choices(
                        stock=stock.id, origin=origin.id, posting=posting.id)
                    said = beginning_sim.preview(choices)
                    game = new_game("bridge", choices=choices)
                    checked += 1
                    if len(game.officers) != said["crew"]:
                        wrong.append(f"{stock.id}/{origin.id}: card says "
                                     f"{said['crew']}, sails with "
                                     f"{len(game.officers)}")
        assert not wrong, (
            f"{len(wrong)} opening(s) seat a bridge the card did not promise: "
            f"{wrong[:4]}")
        assert checked >= 45, checked
        return (f"{checked} openings, every bridge the size its card promised "
                f"({dict(CREW_SLOTS)})")

    @check("the stations you pick are the stations you get")
    def _():
        # `Choices.crew` was honoured by `apply` from the day it was written
        # and no screen ever set it — so the ids in `CREW_CHOICES` were never
        # exercised, and two of them were stat names. `make_officer` answered
        # a station it did not know by picking one at random, so choosing the
        # engineer would have seated somebody else.
        from ..data.beginnings import CREW_CHOICES
        from ..core.rng import RNG
        from ..sim.crew import CREW_ROLES, make_officer

        ids = {r[0] for r in CREW_ROLES}
        stray = [s for s in CREW_CHOICES if s not in ids]
        assert not stray, (
            f"{stray} are offered as stations and match no role — "
            f"`make_officer` would seat somebody at random")

        for stock in STOCKS:
            room = beginning_sim.crew_slots(stock.id)
            want = tuple(CREW_CHOICES[-room:])       # the unusual end
            choices = beginning_sim.Choices(stock=stock.id, crew=want)
            game = new_game("picked", choices=choices)
            got = tuple(o.role for o in game.officers)
            assert got == want, (
                f"{stock.id}: asked for {want} and got {got}")

        # And an id nobody knows is refused rather than answered at random.
        try:
            make_officer(RNG("unknown"), "engineering")
        except ValueError:
            pass
        else:
            raise AssertionError(
                "make_officer answered an unknown station instead of saying so")
        return (f"{len(CREW_CHOICES)} stations, every one seating the officer "
                "asked for; an unknown one refused")

    @check("an origin that claims a cost actually charges it")
    def _():
        # A card that says "the Charter files you as a licence risk" and moves
        # nothing is the exact defect this project keeps finding: a screen
        # making a claim the sim does not honour.
        base = new_game("cost-base")
        silent = []
        for origin in ORIGINS:
            if origin.id == "surveyor":
                continue          # the canonical opening, and it says so
            choices = beginning_sim.Choices(
                stock=origin.stocks[0], origin=origin.id,
                hull=beginning_sim.hulls_for(origin.stocks[0], origin.id)[0].id)
            game = new_game("cost-base", choices=choices)
            moved = (game.credits != base.credits
                     or game.rep != base.rep
                     or sorted(game.research.unlocked) != sorted(base.research.unlocked)
                     or game.ship.cargo != base.ship.cargo
                     or game.flags != base.flags)
            if not moved:
                silent.append(origin.id)
            assert origin.gives and origin.costs, f"{origin.id} says nothing"
            if any(delta < 0 for delta in origin.rep.values()):
                worse = [f for f, d in origin.rep.items() if d < 0]
                for fid in worse:
                    assert game.rep[fid] < base.rep[fid], (
                        f"{origin.id} claims to anger {fid} and does not")
        assert not silent, f"origins that change nothing: {silent}"
        return f"{len(ORIGINS) - 1} origins, all of them moving something real"

    @check("you can refit every part your own hull launched with")
    def _():
        # A live soft-lock, found by the opening checks. The shipped NAVIS
        # carried a Reaction-Mass Organ, a Radiator Bloom and a Mining Root
        # whose technologies were not in STARTING_TECH — and the Refit tab
        # offers a Remove button for every fitted part. Pull the drive on day
        # one and `parts_available("drive", ...)` returned an empty list, so
        # the slot could never be filled again.
        from ..data.parts import parts_available
        game = new_game("refit-back")
        chassis = CHASSIS_BY_ID[game.ship.chassis]
        for pid in game.ship.fitted:
            part = PARTS_BY_ID[pid]
            offered = parts_available(part.slot, chassis, game.research.unlocked)
            assert any(p.id == pid for p in offered), (
                f"{part.name} is fitted to the opening hull and cannot be "
                f"refitted once removed — {part.slot} offers "
                f"{[p.id for p in offered]}")

        # And prove the round trip: strip the drive, put it back.
        without = [p for p in game.ship.fitted if p != "reaction_organ"]
        _dock_at_a_yard(game)
        assert shipyard_sim.apply_refit(game, game.ship, without)[0]
        game.recompute()
        game.credits += 50_000
        for key in ("biomass", "ore", "phosphate", "silicon", "alloy"):
            game.stores[key] = 200
        back = list(game.ship.fitted) + ["reaction_organ"]
        ok, why = shipyard_sim.apply_refit(game, game.ship, back)
        assert ok, f"could not put the drive back: {why}"
        game.recompute()
        assert game.ship_stats.jump > 9, game.ship_stats.jump

        # And every other opening, read off the ship that actually opens:
        # whatever is bolted on, the captain holds the technology for it, so
        # every fitting is one the yard will sell back.
        outfits = 0
        for stock in STOCKS:
            for origin in beginning_sim.origins_for(stock.id):
                hull = beginning_sim.hulls_for(stock.id, origin.id)[0]
                opened = new_game(f"outfit-{stock.id}-{origin.id}",
                                  choices=beginning_sim.Choices(
                                      stock=stock.id, origin=origin.id,
                                      hull=hull.id))
                frame = CHASSIS_BY_ID[opened.ship.chassis]
                for pid in opened.ship.fitted:
                    part = PARTS_BY_ID[pid]
                    offered = parts_available(part.slot, frame,
                                              opened.research.unlocked)
                    assert any(p.id == pid for p in offered), (
                        f"{stock.id}/{origin.id} opens with {pid} fitted and "
                        f"the yard will not sell it back — {part.slot} offers "
                        f"{[p.id for p in offered]}")
                outfits += 1
        return (f"{len(game.ship.fitted)} fitted parts all refittable, drive "
                f"stripped and restored to {game.ship_stats.jump:.1f} ly; "
                f"{outfits} other openings hold their own outfits' technology")

    @check("a hull you are offered comes fitted with something that works")
    def _():
        # An opening hull with an empty drive slot is not a choice, it is a bug
        # the player discovers in the shipyard on day one.
        seen = 0
        for stock in STOCKS:
            for origin in beginning_sim.origins_for(stock.id):
                for chassis in beginning_sim.hulls_for(stock.id, origin.id):
                    fitted = beginning_sim.fit_for(chassis)
                    ok, errs, _brown = shipyard_sim.validate(chassis, fitted)
                    assert ok, f"{chassis.id}: {errs[:2]}"
                    for pid in fitted:
                        part = PARTS_BY_ID[pid]
                        assert part.family in ACCEPTS[chassis.family], (
                            f"{chassis.id} was fitted a {part.family} part")
                    if chassis.slots.get("drive"):
                        assert any(PARTS_BY_ID[p].slot == "drive"
                                   for p in fitted), (
                            f"{chassis.id} opens with no drive")
                    seen += 1
        return f"{seen} offered hulls, each with a legal working outfit"

    @check("every posting opens somewhere with a quay")
    def _():
        missing = []
        for index in range(6):
            for posting in POSTINGS:
                choices = beginning_sim.Choices(posting=posting.id,
                                                stock="grafted",
                                                origin="grafter", hull="graft")
                game = new_game(f"post-{index}", choices=choices)
                if not game.system.port:
                    missing.append(f"{posting.id}@{index}")
                elif posting.faction:
                    assert game.system.faction == posting.faction, (
                        f"{posting.id} opened in {game.system.faction} space")
        assert not missing, f"postings that open with no port: {missing}"
        return f"{len(POSTINGS)} postings across 6 sectors, all at a quay"

    @check("a stock only flies what it says it will")
    def _():
        for stock in STOCKS:
            for origin in beginning_sim.origins_for(stock.id):
                for chassis in beginning_sim.hulls_for(stock.id, origin.id):
                    assert chassis.family in stock.families, (
                        f"{stock.id} offered a {chassis.family} hull")
            for faction_id in ():
                pass
        # And the reverse: a dry captain must not be handed a grown hull.
        dry = beginning_sim.hulls_for("dry", "cantor")
        assert dry and all(c.family in ("synthetic", "fabricated") for c in dry)
        assert not any(c.family == "grown" for c in dry), (
            "the Dry Choir was offered something alive to fly")
        return (f"{len(STOCKS)} stocks, each held to its own families; "
                f"dry may fly {sorted({c.family for c in dry})}")

    @check("the opening survives a save and reload")
    def _():
        import os
        import tempfile
        os.environ["HOME"] = tempfile.mkdtemp()
        from ..core import save as save_mod
        from ..core.state import load_game

        choices = beginning_sim.Choices(stock="dry", origin="cantor",
                                        hull="cantor", posting="sanhedrin",
                                        name="Fifth Recension")
        game = new_game("reload", choices=choices)
        game.advance_days(3)
        save_mod.write({"game": game})
        back = load_game()
        assert back is not None
        assert back.ship.chassis == "cantor"
        assert back.ship.name == "Fifth Recension"
        assert back.rep == game.rep
        assert back.flags.get("canon_holder") is True
        assert sorted(back.research.unlocked) == sorted(game.research.unlocked)
        return f"{back.ship.name}, a {back.ship.chassis}, reloaded intact"
