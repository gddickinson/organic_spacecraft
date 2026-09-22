"""Fire that is not one aimed shot: bursts, suppression, grenades and smoke.

- **a burst** adds the gun's Auto to the damage, and a gun that fires one at
  a time refuses it — spending no luck to say so;
- **suppressing fire** pins the target and whoever stands beside them — not
  a sentry, which has no nerves to shake — and a pinned shot is the worse
  for it, until a round passes;
- **a grenade** reaches everybody in its burst, friend or not; a stun one
  puts them on the floor and kills nobody; each is spent once thrown, and
  one not carried cannot be thrown at all;
- **smoke** hangs where it lands, nobody sees through it, and it clears in
  `SMOKE_ROUNDS`.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data import afoot_arms as arms
from ..sim import afoot, afoot_fight, afoot_fire, afoot_map, checks
from ..sim.afoot_state import Actor, party
from . import afoot_kit
from .harness import Suite


def _out(seed: str):
    game = afoot_kit.fresh(seed)
    site = next(s for s in afoot.sites(game) if s.kind == "port" and s.ok)
    assert afoot.begin(game, site.key, ["captain"])["ok"]
    walk = game.afoot
    me = party(walk)[0]
    walk.decks[me.deck].g = 1.0            # braced, so the dice are the gun's
    walk.version += 1
    return game, walk, me


def _free(walk, deck: int, near, far: int, sees_from=None):
    """A free floor square `far` squares from `near`, in sight of
    `sees_from` if given, with a free square beside it."""
    g = afoot_map.ground(walk, deck)
    used = {(a.x, a.y) for a in walk.actors if a.deck == deck}
    d = walk.decks[deck]
    for y in range(d.h):
        for x in range(d.w):
            if (x, y) in used or not g.passable(x, y) or afoot_map.distance(
                    near[0], near[1], x, y) != far:
                continue
            if sees_from and not afoot_map.sees(walk, deck, *sees_from, x, y):
                continue
            if any(g.passable(x + dx, y + dy) and (x + dx, y + dy) not in used
                   for dx, dy in afoot_map.STEPS):
                return x, y
    raise AssertionError(f"no free square {far} from {near}")


def _foe(walk, deck: int, spot, folk="raider", **kw) -> Actor:
    who = Actor(id=9000 + len(walk.actors), name=kw.pop("name", folk.title()),
                side="npc", folk=folk, deck=deck, x=spot[0], y=spot[1],
                hp=kw.pop("hp", 60), hp_max=60, mood=kw.pop("mood", "hostile"),
                weapon=kw.pop("weapon", "carbine"),
                stats={"str": 7, "dex": 7, "end": 7, "int": 7, "edu": 7,
                       "soc": 7}, **kw)
    walk.actors.append(who)
    return who


def _beside(walk, who, folk="raider", **kw) -> Actor:
    return _foe(walk, who.deck, _free(walk, who.deck, (who.x, who.y), 1),
                folk, **kw)


def _landing(game, walk, me, target, grenade: str) -> RNG:
    """Dice under which this throw lands dead on: the throw's first draw is
    its check, so a seed that passes the check alone passes it thrown."""
    got = afoot_fire.terms(game, walk, me, target, grenade)
    assert got["ok"], got["why"]
    for n in range(400):
        if checks.roll(RNG(f"throw:{n}"), got["skill"], got["score"],
                       "average", got["extra"]).ok:
            return RNG(f"throw:{n}")
    raise AssertionError("no throw ever landed")


def run(suite: Suite) -> None:
    check = suite.check

    @check("a burst adds the gun's Auto; a single-shot gun refuses, and spends no luck")
    def _():
        game, walk, me = _out("fire-burst")
        foe = _foe(walk, me.deck, _free(walk, me.deck, (me.x, me.y), 2,
                                        (me.x, me.y)), hp=200)
        me.weapon = "autopistol"
        for n in range(200):
            me.acted = False
            single = afoot_fight.attack(game, walk, me, foe, RNG(f"b:{n}"))
            me.acted = False
            burst = afoot_fight.attack(game, walk, me, foe, RNG(f"b:{n}"),
                                       burst=True)
            if single["hit"] and single["damage"] > 0:
                break
        assert burst["damage"] - single["damage"] == arms.arm("autopistol").auto
        me.weapon, me.acted = "snub_pistol", False
        luck = game.rng_seed
        got = afoot.attack(game, me.id, foe.id, burst=True)
        assert not got["ok"] and "one at a time" in got["why"], got
        foe.deck = (me.deck + 1) % len(walk.decks)
        got = afoot.attack(game, me.id, foe.id)
        assert not got["ok"] and game.rng_seed == luck, "a refusal rolled"
        return (f"{single['damage']} a shot, {burst['damage']} a burst; a "
                "snub pistol says no without a die")

    @check("suppressing fire pins the target and whoever is beside them — not a sentry")
    def _():
        game, walk, me = _out("fire-suppress")
        foe = _foe(walk, me.deck, _free(walk, me.deck, (me.x, me.y), 3,
                                        (me.x, me.y)))
        mate = _beside(walk, foe, name="His mate")
        sentry = _beside(walk, foe, "sentry", name="A sentry")
        me.weapon = "rifle"
        got = afoot.suppress(game, me.id, foe.id)
        assert not got["ok"] and "cannot lay down fire" in got["why"], got
        me.weapon = "carbine"
        steady = afoot_fight.terms(game, walk, foe, me)["extra"]
        got = afoot.suppress(game, me.id, foe.id)
        assert got["ok"] and set(got["pinned"]) == {foe.name, mate.name}, got
        assert sentry.pinned == 0 and me.acted
        shaken = afoot_fight.terms(game, walk, foe, me)["extra"]
        assert shaken - steady == arms.PINNED, (steady, shaken)
        afoot_fire.settle(walk)
        assert foe.pinned == mate.pinned == 0
        assert afoot_fight.terms(game, walk, foe, me)["extra"] == steady
        return (f"{', '.join(got['pinned'])} pinned at {arms.PINNED:+d}; the "
                "sentry never flinched; a round later, steady again")

    @check("a grenade reaches everybody in its burst; a stun one kills nobody; each is spent")
    def _():
        game, walk, me = _out("fire-grenade")
        foe = _foe(walk, me.deck, _free(walk, me.deck, (me.x, me.y), 3,
                                        (me.x, me.y)))
        bystander = _beside(walk, foe, "patron", name="A bystander",
                            mood="neutral")
        me.kit = [k for k in me.kit if k not in arms.GRENADE_BY_ID]
        luck = game.rng_seed
        got = afoot.throw(game, me.id, foe.id, "frag_grenade")
        assert not got["ok"] and game.rng_seed == luck, got
        me.kit += ["frag_grenade", "stun_grenade"]
        assert afoot_fire.grenades(me) == ["frag_grenade", "stun_grenade"]
        # Reach is asked before anything else, so the square need not be
        # floor: somebody eight squares off is past any arm.
        far = _foe(walk, me.deck, (me.x + arms.GRENADE_BY_ID["frag_grenade"]
                                   .reach + 2, me.y))
        assert not afoot_fire.terms(game, walk, me, far, "frag_grenade")["ok"]
        before = (foe.hp, bystander.hp)
        got = afoot_fire.throw(game, walk, me, foe, "frag_grenade",
                               _landing(game, walk, me, foe, "frag_grenade"))
        assert got["ok"] and got["check"].ok, got
        assert foe.hp < before[0] and bystander.hp < before[1], "it spared"
        hurt = (before[0] - foe.hp, before[1] - bystander.hp)
        assert afoot_fire.grenades(me) == ["stun_grenade"]
        foe.hp = bystander.hp = 1
        foe.status = bystander.status = "up"
        me.acted = False
        got = afoot_fire.throw(game, walk, me, foe, "stun_grenade",
                               _landing(game, walk, me, foe, "stun_grenade"))
        assert got["ok"] and foe.status != "dead" != bystander.status
        assert foe.numb > 0 and afoot_fire.grenades(me) == []
        return (f"frag: {hurt[0]} to the target, {hurt[1]} to the bystander;"
                " stun: both floored, neither dead; two thrown, two spent")

    @check("smoke hangs where it lands, nobody sees through it, and it clears")
    def _():
        game, walk, me = _out("fire-smoke")
        foe = _foe(walk, me.deck, _free(walk, me.deck, (me.x, me.y), 4,
                                        (me.x, me.y)))
        me.kit += ["smoke_grenade"]
        me.weapon = "carbine"
        assert afoot_fight.terms(game, walk, me, foe)["ok"]
        got = afoot_fire.throw(game, walk, me, foe, "smoke_grenade",
                               _landing(game, walk, me, foe, "smoke_grenade"))
        assert got["ok"]
        cloud = [t for t in walk.things if t.kind == "smoke"]
        assert cloud and not afoot_map.sees(walk, me.deck, me.x, me.y,
                                            foe.x, foe.y)
        blind = afoot_fight.terms(game, walk, me, foe)
        assert not blind["ok"] and "No line" in blind["why"], blind
        for _n in range(arms.SMOKE_ROUNDS):
            afoot_fire.settle(walk)
        assert not any(t.kind == "smoke" for t in walk.things)
        assert afoot_fight.terms(game, walk, me, foe)["ok"]
        return (f"{len(cloud)} squares of smoke; no line through it; clear "
                f"after {arms.SMOKE_ROUNDS} rounds")
