"""A rival's fight: the hull they bring, the opening, and what the ending does.

Split from `sim/nemeses.py`, which holds who they are and where they go. This
is the half that touches an engagement, and it touches it only at the three
doors the fight already has:

- **Before** — `meet` is asked first by `encounters.roll_encounter`, and
  `encounter` builds the enemy from the rival's own persistent `Ship` rather
  than from `make_enemy`, so the holes you left are the holes you meet.
- **At the start** — `opening` gives somebody the first volley and brings a
  grateful rival in as a consort.
- **After** — `settle` is called by `aftermath.resolve`, the one door every
  engagement ends through. **It invents no result id.** Every ending in
  `battle_state.ENDINGS` is mapped explicitly (`data/nemeses.ENDINGS`), and a
  fight with nobody's rival in it passes through untouched except for the
  rises that ordinary fights cause.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data.nemeses import ENDINGS, OBJECT, TRAITS_BY_ID
from ..world.galaxy import distance
from . import nemeses as nem_sim
from .ship import add_cargo, build_layers, stats

#: What each level adds to the threat a rival was built to. The design's
#: figure: a level-five rival is two whole difficulty steps past the one that
#: first rose.
PER_LEVEL = 0.4

#: Trait effects, measured against the win rates `test_nemeses` holds (a
#: warfitted NAVIS on day 540, rivals risen at level one and refitted up).
#: The first draft had a relentless rival at 2.5× nerve, two escorts a fifth
#: of a hull each and a level-five last stand at 2×: level one won 70% and
#: level five **3%**, 87 fights in 200 running to the forty-turn stalemate.
#: At these, level one wins 70% and level five 36%.
SHIELD_HULL = 0.25        # a quarter more hull under the armour
ESCORT_HULL = 0.12        # each escort screens an eighth of a hull
ESCORT_NERVE = 8.0        # … and steadies the crew
DUEL_EYE = 0.08           # a duellist's accuracy
COWARD_NERVE = 0.6        # two fifths less nerve
RELENTLESS_NERVE = 1.4    # once beaten, fights the next one further
#: Nerve is the crew's, not the yard's. The level's 0.4 goes into the hull
#: and the fit, as the design says; charged to nerve at the encounter rate
#: too (27 a threat point) it added 43 to a level-five crew, the warfit broke
#: first in 94 fights of 200, and level five won 27%. Five a level and a
#: tenth of the grudge is a crew that wants it more each time, and 36%.
LEVEL_NERVE = 5.0
GRUDGE_NERVE = 0.1

#: What a winning rival takes out of your hold: a quarter of every good but
#: the reaction mass that gets you home. They want you poorer, not stranded.
PLUNDER_SHARE = 0.25

#: Standing with whoever posted the price, when you collect it.
BOUNTY_STANDING = 6.0

#: How far an ally will come to stand beside you, in light years.
ALLY_REACH = 10.0

#: How much each meeting moves the grudge, and which way.
GRUDGE_STEP = 20.0


def difficulty(nem) -> float:
    """The threat their hull is built to: what they rose at, their kind's
    edge (`data/nemeses.Archetype.edge`) and what each return added."""
    return (nem.threat + nem_sim.archetype(nem).edge
            + PER_LEVEL * nem.level)


def escorts(nem) -> int:
    if "swarm" not in nem.traits or nem.level < 4:
        return 0
    return 1 if nem.level < 5 else 2


def called(nem) -> str:
    """What the battle screen and the log call them."""
    if nem.archetype == "husk":
        return f"the husk «{nem.name}»"
    hull = nem.ship.name if nem.ship is not None else "?"
    return f"{nem.name}'s «{hull}»"


def say(nem, text: str) -> str:
    """A line with {they}/{them} filled in for this rival."""
    line = text.format(they=nem.pronoun, them=OBJECT.get(nem.pronoun, "them"))
    return line[:1].upper() + line[1:]


# ── the hull ───────────────────────────────────────────────────────────────

def refit(game, nem, rng) -> None:
    """Build their hull at their level — a new one at a rise, the same one
    re-armed on a return, which is what "a new fitting" means."""
    from . import encounters
    arch = nem_sim.archetype(nem)
    d = difficulty(nem)
    if nem.ship is None:
        made = encounters.make_enemy(rng, arch.yard, d)
        nem.ship = made["ship"]
        if nem.archetype == "husk":
            nem.ship.name = nem.name
    else:
        # **The same hull, re-armed** — and never worse armed. Re-rolling the
        # whole fit at the new level made the first return *weaker* one time
        # in three (measured: 385 hull to 376, the Whipple screen rolled
        # away), which is not what "back a level up" means. The frame keeps
        # its defences and takes the new battery only if it throws more.
        from ..data.parts import part
        chassis = nem.ship.chassis_def
        tier = encounters._tier_for(rng, d)
        fresh = encounters._outfit(rng, chassis, tier, d)
        guns = [p for p in nem.ship.fitted if part(p) and part(p).wpn]
        new_guns = [p for p in fresh if part(p) and part(p).wpn]
        if _throw(new_guns) >= _throw(guns):
            guns = new_guns
        nem.ship.fitted = [p for p in nem.ship.fitted
                           if not (part(p) and part(p).wpn)] + guns
        nem.ship.disabled.clear()
    extra = (SHIELD_HULL if "shielded" in nem.traits else 0.0) \
        + ESCORT_HULL * escorts(nem)
    build_layers(nem.ship, {"hull": 0.1 * d + extra})
    nem.ship.heat = 0.0
    _rearm(nem.ship)


def _throw(guns) -> float:
    from ..data.parts import part
    return sum(part(p).wpn.dmg for p in guns)


def _rearm(ship) -> None:
    """Top the magazine up between meetings: a rival has a home port."""
    from .encounters import ROUNDS_MAX
    for mount in stats(ship, {}).weapons:
        if mount.wpn.ammo:
            cid, per = mount.wpn.ammo
            want = per * ROUNDS_MAX
            if ship.cargo.get(cid, 0) < want:
                add_cargo(ship, cid, want - ship.cargo.get(cid, 0))


def preferred_band(ship) -> int:
    """Where their guns want to be — the band an ambush is sprung at."""
    mounts = stats(ship, {}).weapons
    if not mounts:
        return 3
    return round(sum((w.wpn.bands[0] + w.wpn.bands[1]) / 2 for w in mounts)
                 / len(mounts))


# ── before ─────────────────────────────────────────────────────────────────

def aggression(nem) -> float:
    """Odds they come for a lit hull arriving where they are."""
    theirs = float(nem.grudge.get("theirs", 0.0))
    return min(0.95, nem_sim.archetype(nem).aggression + theirs / 400.0)


def meet(game, system):
    """A rival in the arrival system rolls before anything else does.

    `encounters.roll_encounter` asks this first. Its luck is its own key, so
    a sector with no rival here draws nothing from the arrival's stream.
    """
    from . import running_dark
    for nem in sorted(nem_sim.roster(game), key=lambda n: n.id):
        if nem.location_id != system.id or nem.ship is None:
            continue
        rng = RNG(f"{game.seed}:meet:{nem.id}:{game.day}")
        if nem.status == "allied" and not nem.loyal:
            return _betray(game, nem)
        if nem.status != "active":
            continue
        if rng.chance(aggression(nem) * running_dark.exposure(game)):
            return encounter(game, nem)
    return None


def _betray(game, nem) -> dict:
    nem.status = "active"
    nem.grudge["theirs"] = min(100.0, nem.grudge.get("theirs", 0) + GRUDGE_STEP)
    nem_sim.taunt(game, nem, "betray")
    return encounter(game, nem, first="enemy",
                     intro=f"{called(nem)} comes alongside as a friend would, "
                           "and opens fire at the last moment.")


def encounter(game, nem, *, found: bool = False, band: int | None = None,
              first: str | None = None, intro: str | None = None) -> dict:
    """The engagement dict `combat.start` takes, built from their own hull.

    `found` is a hunt that found them: you pick the band, and if you ran dark
    you shoot first. Otherwise an ambusher does.
    """
    from . import encounters, running_dark
    arch = nem_sim.archetype(nem)
    ship = nem.ship
    _rearm(ship)
    d = difficulty(nem)
    st = stats(ship, {})
    resolve = (encounters.RESOLVE_BASE
               + (d - PER_LEVEL * (nem.level - 1)) * encounters.RESOLVE_PER_SCALE
               + LEVEL_NERVE * (nem.level - 1) + ESCORT_NERVE * escorts(nem)
               + GRUDGE_NERVE * float(nem.grudge.get("theirs", 0.0)))
    style = arch.personality
    if "duellist" in nem.traits:
        st.accuracy += DUEL_EYE
    if "coward" in nem.traits:
        resolve *= COWARD_NERVE
        style = "cautious"
    if "relentless" in nem.traits and nem.retreats >= 1:
        resolve *= RELENTLESS_NERVE
        style = "feral"
    if nem.level >= nem_sim.LEVEL_MAX:
        style = "feral"               # at level five they do not turn and run
    if first is None:
        if found and running_dark.dark(game):
            first = "player"
        elif not found and "ambusher" in nem.traits:
            first = "enemy"
    if band is None and first == "enemy":
        band = preferred_band(ship)
    enemy = {"ship": ship, "stats": st, "name": called(nem),
             "faction": nem.faction, "personality": style, "resolve": resolve,
             "loot": {"credits": round(1300 * (1 + d * 0.6)),
                      "research": round(13 * (1 + d * 0.4))}}
    return {"enemy": enemy, "no_parley": not arch.parley, "nemesis": nem.id,
            "band": band, "first_volley": first,
            "intro": intro or _intro(game, nem, found)}


def _intro(game, nem, found: bool) -> str:
    met = len(nem.history)
    if found:
        return f"You have found {called(nem)}. The engagement is yours to open."
    if not met:
        return (f"{called(nem)} comes out of the dark with your registry "
                "number on the board.")
    # The history is the battle screen's heading (`header`); said twice, the
    # first thing a captain read was the same sentence twice.
    return f"{called(nem)} again, and closing."


def header(game, nid) -> str:
    """"Third meeting. You drove her off at Pale Fall." — for the battle
    screen's heading, and the intro."""
    nem = nem_sim.by_id(game, nid)
    if nem is None:
        return ""
    count = len(nem.history) + 1
    ordinal = ("First", "Second", "Third", "Fourth", "Fifth", "Sixth")
    text = f"{ordinal[count - 1] if count <= 6 else f'Meeting {count}'} meeting."
    if nem.history:
        day, where, result, _words = nem.history[-1]
        place = game.galaxy.systems[int(where)].name
        text += f" {say(nem, ENDINGS[result][1])} at {place}."
    traits = ", ".join(TRAITS_BY_ID[t].name for t in nem.traits)
    return (f"{text} Level {nem.level} "
            f"{nem_sim.archetype(nem).name.lower()} · {traits}.")


# ── at the start ───────────────────────────────────────────────────────────

def opening(game, battle, encounter: dict) -> None:
    """The first volley, and a grateful rival turning up. Called once, right
    after `combat.start`, by whoever started the fight."""
    from .damage import _say
    battle.nemesis = encounter.get("nemesis")
    first = encounter.get("first_volley")
    if first in ("player", "enemy"):
        rng = RNG(f"{game.seed}:volley:{battle.nemesis}:{game.day}")
        shooter, target = ((battle.player, battle.enemy) if first == "player"
                           else (battle.enemy, battle.player))
        _bring_to_bear(shooter, target)
        _say(battle, ("You were dark until the guns spoke. First volley."
                      if first == "player" else
                      f"{battle.enemy_name} fires before you have the range."),
             "good" if first == "player" else "bad")
        from .shooting import _salvo
        _salvo(battle, shooter, target, rng)
    if battle.nemesis is None:
        ally = _ally_for(game)
        if ally is not None:
            from . import consorts
            consorts.deploy(battle, [ally.ship], None, battle.bonuses)
            _say(battle, f"{called(ally)} comes up on your quarter. "
                         "An old debt, being paid.", "good")


def _bring_to_bear(side, other) -> None:
    """They chose the moment: the hull is already turned to shoot.

    Turned for the *fixed* guns, by weight of metal — a turret bears whatever
    the heading. The first draft took the commonest arc, which on a NAVIS
    with a flash organ (turret) and a lixiviant (fore) was the turret's
    broadside: the lixiviant never bore again, and a first volley cut a
    starting hull's bounty rate from 28% to 1% over 150 fights.
    """
    from . import tactical as tac
    weight: dict = {}
    for w in side.st.weapons:
        arc = tac.arc_of(w)
        if arc != "turret":
            weight[arc] = weight.get(arc, 0.0) + w.wpn.dmg
    want = max(weight, key=weight.get) if weight else "fore"
    off = {"fore": 0.0, "broad": 90.0, "aft": 180.0}[want]
    side.body.heading = (tac.bearing_to(side.body, other.body) - off) % 360


def _ally_for(game):
    here = game.system
    fleet = {s.uid for s in game.fleet}
    for nem in nem_sim.roster(game):
        if (nem.status == "allied" and nem.loyal and nem.ship is not None
                and nem.ship.uid not in fleet
                and distance(game.galaxy.systems[nem.location_id], here)
                <= ALLY_REACH):
            return nem
    return None
