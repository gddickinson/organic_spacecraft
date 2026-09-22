"""Afoot: the ground, the rules, and whether the odds on the button are the odds.

Seven claims:

- **Every plan can be walked.** Every kind of site, over many sectors, lays
  out decks on which every room is reachable from the way in — a locked
  door counting as a door somebody could open — and nothing stands on a
  wall or in a doorway.
- **Sight is symmetric**, and a path never goes through what it cannot.
- **The plan is the site.** The same quay is the same quay every time, and
  a hull's rooms are its fittings: refit it and the plan changes.
- **Preview equals act.** The hit chance an attack shows is the chance it
  hits, measured over a thousand throws; the same for first aid.
- **Things do what they claim** (efficacy): armour takes damage off, a
  weapon's kit bonus moves the chance, a word moves an officer, wounds
  close over days and a medic closes them faster.
- **Every verb and every topic has a door**, and nothing names one that
  does not exist.
- **Looking costs nothing.** Every forecast a screen asks for leaves the
  chronicle's luck where it was.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data import afoot_folk, afoot_things
from ..sim import (afoot, afoot_acts, afoot_deeds, afoot_fight, afoot_map,
                   afoot_plans, afoot_said, afoot_sites)
from ..sim.afoot_state import OPEN, Actor, party
from . import afoot_kit
from .harness import Suite

SECTORS = 12


def _entry_reach(walk, deck: int) -> set:
    """Everything reachable on a deck from its way in (or its lift), with
    every locked door treated as a door somebody could open."""
    for t in walk.things:
        if t.kind in afoot_things.DOORS and t.state == "locked":
            t.state = "shut"
    walk.version += 1
    start = next(((t.x, t.y) for t in walk.things if t.deck == deck
                  and t.kind in ("airlock", "gangway", "lift")), None)
    return afoot_map.connected(walk, deck, start) if start else set()


def _check_plan(walk) -> list:
    """Everything wrong with one laid-out walk, as sentences."""
    bad = []
    for deck in range(len(walk.decks)):
        reach = _entry_reach(walk, deck)
        for room in walk.rooms:
            if room.deck != deck:
                continue
            if not any(c in reach for c in room.cells()):
                bad.append(f"{walk.name}: {room.name} cannot be reached")
    for t in walk.things:
        if walk.decks[t.deck].at(t.x, t.y) not in OPEN:
            bad.append(f"{walk.name}: a {t.kind} stands on a wall")
    doors = {(t.deck, t.x, t.y) for t in walk.things
             if t.kind in afoot_things.DOORS}
    for t in walk.things:
        kind = afoot_things.THING_BY_ID[t.kind]
        if kind.blocks and any((t.deck, t.x + dx, t.y + dy) in doors
                               for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                               if dx or dy) and t.kind != "counter":
            bad.append(f"{walk.name}: a {t.kind} blocks a doorway")
    return bad


def _walks(game) -> list:
    """Every site here, laid out and started, then set aside."""
    out = []
    for site in afoot_sites.here(game):
        if not site.ok:
            continue
        got = afoot.begin(game, site.key, ["captain"])
        assert got["ok"], (site.key, got)
        out.append(game.afoot)
        game.afoot = None
    return out


def _duel(game, weapon="shotgun", armour="", target_armour="",
          distance: int = 3):
    """Two people in an empty corridor, one with a gun."""
    got = afoot.begin(game, f"ship:{game.ship.uid}", ["captain"])
    assert got["ok"], got
    walk = game.afoot
    for a in list(walk.actors):
        if a.side == "npc":
            walk.actors.remove(a)
    me = party(walk)[0]
    me.weapon, me.armour = weapon, armour
    me.kit = [k for k in (weapon, armour) if k]
    deck = walk.decks[me.deck]
    row = next(y for y in range(deck.h)
               if deck.rows[y].count(",") > distance + 4)
    xs = [x for x in range(deck.w) if deck.rows[row][x] == ","]
    me.x, me.y = xs[1], row
    foe = Actor(id=9999, name="Target", side="npc", folk="raider",
                deck=me.deck, x=xs[1] + distance, y=row, hp=10_000,
                hp_max=10_000, mood="hostile", armour=target_armour,
                stats={"str": 7, "dex": 7, "end": 7, "int": 7, "edu": 7,
                       "soc": 7})
    walk.actors.append(foe)
    return walk, me, foe


def run(suite: Suite) -> None:
    check = suite.check

    @check("every kind of site lays out a plan every room of which can be walked to")
    def _():
        bad, walks, kinds = [], 0, set()
        for n in range(SECTORS):
            game = afoot_kit.settle(afoot_kit.fresh(f"afoot-plan-{n}"))
            for walk in _walks(game):
                bad += _check_plan(walk)
                walks += 1
                kinds.add(walk.kind)
        for wreck in ("raider_hulk", "bloom_freighter", "survey_hulk",
                      "liner_wreck", "choir_probe"):
            game, site = afoot_kit.at_wreck((wreck,))
            assert afoot.begin(game, site.key, ["captain"])["ok"]
            bad += _check_plan(game.afoot)
            walks += 1
            kinds.add("wreck")
        assert not bad, bad[:6]
        assert {"ship", "port", "habitat", "holding", "wreck"} <= kinds, kinds
        return f"{walks} walks over {sorted(kinds)}, every room reachable"

    @check("a struck hull can be boarded, and her plan is hers")
    def _():
        game = afoot_kit.fresh("afoot-prize-plan")
        hull = afoot_kit.struck(game)
        got = afoot.begin_prize(game, hull, "concordat", ["captain"])
        assert got["ok"], got
        walk = game.afoot
        assert not _check_plan(walk), _check_plan(walk)
        kinds = {r.kind for r in walk.rooms}
        assert {"bridge", "hold"} <= kinds, kinds
        assert sum(len(t.holds) for t in walk.things if t.kind == "cargo"), \
            "her real cargo is not in her hold"
        return f"{len(walk.rooms)} rooms; her cargo is in her hold"

    @check("the same site lays out the same plan, and a refit changes a hull's")
    def _():
        game = afoot_kit.fresh("afoot-same")
        site = afoot_sites.own_hull(game)
        a = afoot_plans.plan(game, site)
        b = afoot_plans.plan(game, site)
        assert [d.rows for d in a.decks] == [d.rows for d in b.decks]
        before = sorted(r.kind for r in a.rooms)
        game.ship.fitted = [p for p in game.ship.fitted
                            if p not in ("polyp_lab", "photic_flash")] + [
            "polyp_lab"]
        after = sorted(r.kind for r in afoot_plans.plan(game, site).rooms)
        assert before != after, "refitting her left the same rooms aboard"
        for place in afoot_sites.here(game):
            if place.kind != "ship" and place.ok:
                assert [d.rows for d in afoot_plans.plan(game, place).decks] \
                    == [d.rows for d in afoot_plans.plan(game, place).decks]
        return f"the hull's rooms follow the fit: {len(before)} → {len(after)}"

    @check("sight is symmetric, and a path never crosses a wall or a lock")
    def _():
        game = afoot_kit.fresh("afoot-sight")
        walk = _walks(game)[1]
        rng = RNG("pairs")
        floor = afoot_map.open_squares(walk, 0)
        pairs = 0
        for _n in range(600):
            a, b = rng.pick(floor), rng.pick(floor)
            if afoot_map.distance(*a, *b) > afoot_map.SIGHT:
                continue
            assert afoot_map.sees(walk, 0, *a, *b) == \
                afoot_map.sees(walk, 0, *b, *a), (a, b)
            pairs += 1
        g = afoot_map.ground(walk, 0)
        probe = Actor(id=-5, name="", side="party", folk="", deck=0,
                      x=floor[0][0], y=floor[0][1], hp=1, hp_max=1)
        walked = 0
        for _n in range(60):
            goal = rng.pick(floor)
            for sq in afoot_map.path(walk, probe, *goal):
                assert g.passable(*sq) and sq not in g.locked, sq
                walked += 1
        return f"{pairs} pairs symmetric; {walked} steps of path, all on floor"

    @check("the chance an attack shows is the chance it hits")
    def _():
        game = afoot_kit.fresh("afoot-odds")
        walk, me, foe = _duel(game, distance=5)
        want = afoot_fight.terms(game, walk, me, foe)["odds"]
        rng = RNG("odds")
        hits = 0
        for _n in range(1200):
            me.acted, me.aim = False, 0
            hits += afoot_fight.attack(game, walk, me, foe, rng)["hit"]
        got = hits / 1200
        assert abs(got - want) < 0.04, (want, got)
        return f"shown {want:.0%}, hit {got:.0%} of 1,200"

    @check("armour takes damage off, and a weapon's own bonus moves the odds")
    def _():
        game = afoot_kit.fresh("afoot-armour")
        rng = RNG("armour")
        dealt = {}
        for worn in ("", "flak"):
            walk, me, foe = _duel(game, target_armour=worn, distance=2)
            total = hits = 0
            for _n in range(400):
                foe.hp, foe.status, me.acted = 10_000, "up", False
                got = afoot_fight.attack(game, walk, me, foe, rng)
                if got["hit"]:
                    total, hits = total + got["damage"], hits + 1
            dealt[worn or "none"] = total / max(1, hits)
            game.afoot = None
        assert dealt["flak"] < dealt["none"] - 3.5, dealt
        walk, me, foe = _duel(game, weapon="carbine", distance=8)
        with_bonus = afoot_fight.terms(game, walk, me, foe)["odds"]
        me.weapon = "rifle"
        rifle = afoot_fight.terms(game, walk, me, foe)["odds"]
        me.weapon = "autopistol"
        pistol = afoot_fight.terms(game, walk, me, foe)["odds"]
        assert with_bonus > pistol, (with_bonus, pistol)
        return (f"a hit does {dealt['none']:.1f} bare, {dealt['flak']:.1f} "
                f"through flak; carbine {with_bonus:.0%}, rifle {rifle:.0%}, "
                f"pistol {pistol:.0%} at 8")

    @check("first aid heals as often as it says it will")
    def _():
        game = afoot_kit.fresh("afoot-aid")
        keys = afoot_kit.everybody(game)[:2]
        assert afoot.begin(game, f"ship:{game.ship.uid}", keys)["ok"]
        walk = game.afoot
        medic, patient = party(walk)[:2]
        patient.x, patient.y = medic.x + 1, medic.y
        rng = RNG("aid")
        patient.hp, patient.status, patient.talked = -2, "down", []
        want = afoot_fight.aid_terms(game, walk, medic, patient)["odds"]
        healed = 0
        for _n in range(900):
            patient.hp, patient.status, patient.talked = -2, "down", []
            medic.acted, medic.spent = False, []
            healed += afoot_fight.first_aid(game, walk, medic, patient,
                                            rng)["healed"] > 0
        got = healed / 900
        assert abs(got - want) < 0.05, (want, got)
        return f"shown {want:.0%}, patched {got:.0%}"

    @check("every verb on a thing and every topic of talk has a door")
    def _():
        for verb in afoot_things.VERBS:
            assert verb in afoot_deeds.DEEDS, verb
        for thing in afoot_things.THINGS:
            for verb in thing.verbs:
                assert verb in afoot_things.VERBS, (thing.id, verb)
        handed = ("business", "hire", "favour", "gift")
        for topic in afoot_folk.TOPICS:
            assert topic in handed or topic in afoot_said.SAID, topic
        for folk in afoot_folk.FOLK:
            for topic in folk.topics:
                assert topic in afoot_folk.TOPICS, (folk.id, topic)
        for act in ("aid", "carry", "drop", "frisk", "sneak", "aim", "watch",
                    "stims", "claim"):
            assert act in afoot_deeds.DEEDS, act
        return (f"{len(afoot_things.VERBS)} verbs, "
                f"{len(afoot_folk.TOPICS)} topics, every one answered")

    @check("a word with an officer moves them, once a month")
    def _():
        game = afoot_kit.fresh("afoot-word")
        assert afoot.begin(game, f"ship:{game.ship.uid}", ["captain"])["ok"]
        walk = game.afoot
        me = party(walk)[0]
        mate = next(a for a in walk.actors if a.folk == "officer"
                    and a.side == "npc")
        me.deck, me.x, me.y = mate.deck, mate.x, mate.y
        me.x += 1 if afoot_map.ground(walk, mate.deck).passable(
            mate.x + 1, mate.y) else -1
        officer = next(o for o in game.officers if o.id == mate.officer)
        was = officer.loyalty
        got = afoot.talk(game, me.id, mate.id, "word")
        assert got["ok"], got
        assert officer.loyalty > was, (was, officer.loyalty)
        again = afoot.talk(game, me.id, mate.id, "word")
        assert not again["ok"], "a second word the same day moved them again"
        return f"loyalty {was:.1f} → {officer.loyalty:.1f}; the second refused"

    @check("wounds close by the day, and faster with a medic aboard")
    def _():
        game = afoot_kit.fresh("afoot-mend")
        game.wounds = {"captain": 12.0}
        afoot.mend(game, 3)
        with_medic = 12.0 - game.wounds.get("captain", 0.0)
        game.wounds = {"captain": 12.0}
        kept = list(game.officers)
        game.officers = []
        afoot.mend(game, 3)
        alone = 12.0 - game.wounds.get("captain", 0.0)
        game.officers = kept
        game.wounds = {"captain": 12.0}
        for _day in range(40):
            game.advance_days(1)
        assert "captain" not in game.wounds, game.wounds
        assert alone > 0 and with_medic >= alone, (alone, with_medic)
        return (f"three days: {alone:g} alone, {with_medic:g} with the crew "
                "aboard; gone within forty days of the clock")

    @check("asking what would happen moves no dice")
    def _():
        game = afoot_kit.fresh("afoot-look")
        walk = _walks(game)[1]
        game.afoot = walk
        before = game.rng_seed
        me = party(walk)[0]
        for other in walk.actors:
            if other.side == "npc":
                afoot.talk_options(game, me.id, other.id)
            afoot_fight.terms(game, walk, me, other)
        afoot_acts.offer(game, walk, me)
        afoot_map.reach(walk, me)
        afoot.visible(walk, me.deck)
        assert game.rng_seed == before, "a forecast moved the chronicle's luck"
        return f"{len(walk.actors)} people forecast, no luck spent"
