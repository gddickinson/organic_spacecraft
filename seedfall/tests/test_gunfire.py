"""What passed between two hulls, and whether the picture shows it.

`combat._fire` resolved a shot and wrote a sentence. By the time a turn was
over, all that survived of a salvo of seven was seven lines of prose — there
was no record of what fired, from where, at what, or whether it connected, so
nothing could draw it. The tactical plot showed the geometry you *decide* on;
nothing showed what the decision produced.

`sim/gunfire.py` keeps the shots. One record per attempt, **including the ones
that never left the tube** — a mount that will not train that far is exactly
the thing a captain needs to see rather than read, and it is the whole
argument for having come about.

The claims:

- **Every point of damage came from a recorded shot.** The general one, and
  it ties the record to the resolver rather than to a second model that could
  drift: 2,138.9 recorded against 2,138.9 taken over six chronicles.
- **A mount that would not bear is recorded, not merely logged.**
- **The record is of this exchange**, cleared each turn.
- **How a weapon looks is read off the weapon**, not off a second table.
- **The picture draws the shots**, and an empty exchange draws none.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.armaments import ARMAMENTS
from ..sim import combat, encounters, gunfire
from ..sim import tactical as tac
from ..sim.ship import build_layers, make_ship, stats
from . import captain_ai
from .harness import Suite

#: A hull with enough different mounts that every `look` appears.
LOADOUT = ["railgun", "missile_rack", "particle_beam", "slug_battery",
           "reaction_organ", "opsin_eyes", "chemo_gut"]


def _fight(seed: str, difficulty: float = 1.5, faction: str = "concordat"):
    game = new_game(seed)
    ship = make_ship("navis", LOADOUT)
    build_layers(ship, game.bonuses)
    ship.cargo = {"alloy": 400, "ore": 400, "biomass": 200}
    rng = RNG(seed)
    battle = combat.start(ship, stats(ship),
                          encounters.make_enemy(rng, faction, difficulty),
                          rng=rng, game=game)
    return game, battle, rng


def run(suite: Suite) -> None:
    check = suite.check

    @check("every point of damage came from a recorded shot")
    def _():
        # The general one. It ties the record to the resolver: if `_fire`
        # ever grows a path that deals damage without noting it, the two
        # totals part company and this says so.
        recorded = taken = 0.0
        turns = shots = 0
        for seed in range(6):
            _game, battle, rng = _fight(f"agree-{seed}")
            for _turn in range(30):
                if battle.over:
                    break
                combat.take_turn(battle, captain_ai.orders(battle), rng)
                recorded += sum(s.damage for s in battle.shots)
                shots += len(battle.shots)
                turns += 1
            taken += battle.player.taken + battle.enemy.taken
        assert turns > 40 and shots > 60, (turns, shots)
        assert abs(recorded - taken) < 0.5, (
            f"{recorded:,.1f} of damage was recorded against {taken:,.1f} "
            "actually taken — something is shooting without saying so")
        return (f"{shots} shots over {turns} turns: {recorded:,.1f} recorded, "
                f"{taken:,.1f} taken")

    @check("a mount that would not bear is recorded, not merely logged")
    def _():
        # The reason refusals are in the record at all. "The lance will not
        # train that far" is the thing worth *seeing*, and it is the whole
        # argument for coming about.
        #
        # They have to be constructed. `_salvo` pre-filters to the mounts that
        # bear, so ordinary play never reaches these branches — eight full
        # engagements produced 285 shots and not one refusal. The geometry is
        # found by asking the sim's own predicates rather than by placing
        # hulls at angles I have guessed at.
        from ..sim import firing
        from ..sim import stations as st_mod
        from ..sim.ship import part

        _game, battle, rng = _fight("refuse")
        me, them = battle.player, battle.enemy

        def aim(bearing_deg: float, distance: float) -> None:
            """Put the enemy at a bearing off our nose, at a distance."""
            import math
            angle = math.radians(me.body.heading + bearing_deg)
            them.body.x = me.body.x + math.sin(angle) * distance
            them.body.y = me.body.y + math.cos(angle) * distance

        found: dict = {}

        # Out of arc: sweep the bearing until the sim says the mount will not
        # train that far, at a distance where the band is fine.
        for weapon_id in ("slug_battery", "railgun", "particle_beam"):
            spec = part(weapon_id)
            if spec is None or spec.wpn is None:
                continue
            for bearing in range(0, 360, 15):
                aim(bearing, 200.0)
                band = tac.band_for(tac.separation(me.body, them.body))
                if spec.wpn.bears_at(band) > firing.CAN_FIRE:
                    continue
                if st_mod.bears_on(me, them, spec)[0]:
                    continue
                gunfire.clear(battle)
                combat._fire(battle, me, them, weapon_id, rng)
                if battle.shots and battle.shots[0].outcome == gunfire.NO_ARC:
                    found[gunfire.NO_ARC] = (weapon_id, bearing)
                break
            if gunfire.NO_ARC in found:
                break

        # Out of band: a mount whose penalty at this range is beyond firing,
        # with the arc satisfied.
        for weapon_id in ("lixiviant", "slug_battery", "railgun"):
            spec = part(weapon_id)
            if spec is None or spec.wpn is None:
                continue
            for band in range(tac.MAX_BAND + 1):
                if spec.wpn.bears_at(band) <= firing.CAN_FIRE:
                    continue
                for bearing in range(0, 360, 15):
                    aim(bearing, (band + 0.5) * tac.BAND_UNITS)
                    if tac.band_for(tac.separation(me.body, them.body)) != band:
                        continue
                    if not st_mod.bears_on(me, them, spec)[0]:
                        continue
                    gunfire.clear(battle)
                    combat._fire(battle, me, them, weapon_id, rng)
                    if battle.shots and battle.shots[0].outcome == gunfire.NO_BEAR:
                        found[gunfire.NO_BEAR] = (weapon_id, band)
                    break
                if gunfire.NO_BEAR in found:
                    break
            if gunfire.NO_BEAR in found:
                break

        # Dry: a magazine weapon that bears, with the hold emptied.
        spec = part("railgun")
        for bearing in range(0, 360, 15):
            aim(bearing, 200.0)
            band = tac.band_for(tac.separation(me.body, them.body))
            if spec.wpn.bears_at(band) > firing.CAN_FIRE:
                continue
            if not st_mod.bears_on(me, them, spec)[0]:
                continue
            me.ship.cargo["alloy"] = 0
            gunfire.clear(battle)
            combat._fire(battle, me, them, "railgun", rng)
            if battle.shots and battle.shots[0].outcome == gunfire.DRY:
                found[gunfire.DRY] = ("railgun", bearing)
            break

        missing = [k for k in (gunfire.NO_ARC, gunfire.NO_BEAR, gunfire.DRY)
                   if k not in found]
        assert not missing, (
            f"these refusals are logged and never recorded: {missing}")
        # And a refusal is not quietly counted as a shot that flew.
        for outcome in (gunfire.NO_ARC, gunfire.NO_BEAR, gunfire.DRY):
            probe = gunfire.Shot("a", "b", "w", gunfire.BEAM, outcome)
            assert not probe.flew and not probe.landed, outcome
        return " · ".join(f"{k}: {v[0]}" for k, v in sorted(found.items()))

    @check("the record is of this exchange and no other")
    def _():
        # A muzzle flash from four turns ago is not news, and drawing it
        # would make the picture a lie about the present.
        _game, battle, rng = _fight("fresh")
        history = []
        for _turn in range(8):
            if battle.over:
                break
            before = list(battle.shots)
            combat.take_turn(battle, captain_ai.orders(battle), rng)
            history.append(len(battle.shots))
            # Nothing from the previous turn survived into this one.
            assert not any(old is new for old in before
                           for new in battle.shots), (
                "a shot from last turn is still in the record")
        assert len(history) >= 4 and max(history) > 0, history
        gunfire.clear(battle)
        assert battle.shots == [], battle.shots
        assert gunfire.summary(battle)["fired"] == 0
        return f"{len(history)} turns, each holding only its own: {history}"

    @check("how a weapon looks is read off the weapon")
    def _():
        # Not off a second table. This project has watched a second table
        # drift out of step with the first more than once — the contract
        # whitelist written three times, the docking forecast quoting the
        # truth behind the blur.
        looks: dict = {}
        for part in ARMAMENTS:
            if part.wpn is None:
                continue
            look = gunfire.look_of(part.wpn)
            looks.setdefault(look, []).append(part.id)
            traits = part.wpn.traits or ()
            if "flak" in traits:
                assert look == gunfire.FLAK, part.id
            elif "seeking" in traits:
                assert look == gunfire.SEEKING, part.id
            elif part.wpn.ammo:
                assert look == gunfire.ROUND, part.id
            else:
                assert look == gunfire.BEAM, part.id
        assert len(looks) >= 3, (
            f"every weapon in the game looks the same: {list(looks)}")
        for kind in (gunfire.BEAM, gunfire.ROUND, gunfire.SEEKING):
            assert looks.get(kind), f"nothing reads as a {kind}"
        return " · ".join(f"{k}: {len(v)}" for k, v in sorted(looks.items()))

    @check("the picture draws the exchange")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
        from ..ui.battle3d import Battle3D

        app = QApplication.instance() or QApplication([])
        assert app is not None
        _game, battle, rng = _fight("draw", 1.6)

        def lit(view) -> int:
            image = view.grab().toImage()
            total = 0
            for x in range(0, 880, 3):
                for y in range(0, 600, 3):
                    px = image.pixelColor(x, y)
                    if px.red() + px.green() + px.blue() > 220:
                        total += 1
            return total

        view = Battle3D(battle)
        view.resize(900, 620)

        said = {}
        for _turn in range(12):
            if battle.over:
                break
            combat.take_turn(battle, captain_ai.orders(battle), rng)
            said = gunfire.summary(battle)
            if said["hits"] >= 2:
                break
        assert said.get("hits", 0) >= 2, f"never got a busy turn: {said}"

        # Differenced against the *same* state with the shots taken out, so
        # what is being measured is the drawing and nothing else. The first
        # draft compared an early frame against a later one and was really
        # measuring two hulls that had moved in between.
        loud = lit(view)
        keep = list(battle.shots)
        gunfire.clear(battle)
        quiet = lit(view)
        battle.shots = keep

        assert loud > quiet + 60, (
            f"an exchange of {said['fired']} shots and {said['hits']} strikes "
            f"lit {loud} samples against {quiet} for the identical frame with "
            "the shots removed — the picture is not drawing them")

        # And the camera keeps both hulls in frame.
        camera = view._camera(900, 620)
        for side in (battle.player, battle.enemy):
            at = camera.project((side.body.x, side.body.y, 0.0))
            assert at is not None, "a hull is behind the camera"
            point, _ahead = at
            assert -200 < point.x() < 1100 and -200 < point.y() < 820, (
                f"a hull is projected to {point.x():.0f},{point.y():.0f} — "
                "off the picture entirely")
        span = tac.separation(battle.player.body, battle.enemy.body)
        return (f"{said['fired']} fired, {said['hits']} struck: {loud} lit "
                f"samples against {quiet} with the same frame emptied of "
                f"shots; both hulls framed at {span:,.0f}")
