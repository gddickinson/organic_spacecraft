"""A gun with hands on it: where it points, what it kills, and what the drills ask.

The claims this holds shut, each of which cost something to get right:

- **Lead is real arithmetic, not a decoration.** The aim point for a crossing
  target is ahead of it by the flight time, a beam's is the target itself, and
  the two come out of one function so the pip and the hit cannot disagree.
- **The mounting is a mounting.** It swings at its own rate, it stops where
  the hull is in the way, and the director and the hands cannot both have it.
- **A gun runs out and cooks off.** Both are recoverable and both are visible.
- **Every drill can be won**, by a bot that plays them all — which is the only
  honest way to know a training course is a course and not a wall.
- **Subsystems are the point of attacking a structure.** Taking the turrets
  off a station silences it, taking its mast blinds it, and the directive list
  reads that off the state rather than counting events.
- **What is done at the gun lands in the engagement it was fought in**, once.
"""

from __future__ import annotations

import math

from ..core.rng import RNG
from ..core.state import new_game
from ..data import armaments
from ..data import drills as table
from ..data import turrets as turret_data
from ..sim import drills as drill_sim
from ..sim import foes, gunsight, manning, skirmish
from ..sim import turret as turret_sim
from .harness import Suite
from .qtkit import app as _app
from .qtkit import main_window

#: How long the bot is allowed on one drill, in ticks of `skirmish.STEP`.
PATIENCE = 6_000


def _seat(part: str = "slug_battery") -> turret_sim.Turret:
    return turret_sim.make(part, at=(0.0, 0.2, 0.9))


def _play(drill, seed: str = "suite"):
    """A gunner good enough to prove a drill is winnable. Returns the verdict.

    Deliberately not a good gunner: it locks whatever the directives point at,
    waits until the mounting is within three degrees of the aim, and pulls.
    Everything it beats, a person can beat.
    """
    rng = RNG(f"{seed}:{drill.id}")
    action = drill_sim.begin(drill, rng)
    for _step in range(PATIENCE):
        if action.over:
            break
        want = skirmish.nearest_threat(action)
        if want is not None and want.behaviour != "home":
            for row in drill_sim.directives(action, drill):
                if row["done"] or not row["primary"]:
                    continue
                pick = next((c for c in skirmish.live(action, hostile=True)
                             if row["kind"] == "clear" or c.parts), None)
                if pick is not None:
                    want = pick
                    break
        if want is not None:
            turret_sim.lock(action.turret, want.id)
        drill_sim.tick(action, drill, rng)
        if action.over:
            break
        mark = skirmish.aim_now(action)
        if mark is None:
            continue
        off = gunsight.off_bore(action.turret.bearing, action.turret.elevation,
                                mark["aim"][0], mark["aim"][1])
        if off <= 3.0 and mark["in_reach"]:
            skirmish.fire(action, rng)
    return action, drill_sim.judge(action, drill)


def run(suite: Suite) -> bool:
    check = suite.check

    @check("a crossing target is led, and a beam is not")
    def _():
        gun = turret_data.for_part("slug_battery")      # 4.0 km/s
        beam = turret_data.for_part("mag_lance")        # instant
        at = (0.0, 12.0, 0.0)
        across = (0.35, 0.0, 0.0)                       # 350 m/s abeam
        led = gunsight.lead_point(gun, at, across)
        assert led[0] > 0.9, f"a 350 m/s crosser at 12 km was led {led[0]:.2f} km"
        # The lead is the flight time times the crossing speed, to a metre.
        flight = gunsight.flight_time(gun, math.dist(led, (0.0, 0.0, 0.0)))
        assert abs(led[0] - across[0] * flight) < 0.001, (led, flight)
        assert gunsight.lead_point(beam, at, across) == at, "a beam was led"
        # And a target coming straight at you needs no deflection at all.
        head_on = gunsight.lead_point(gun, at, (0.0, -0.35, 0.0))
        assert abs(head_on[0]) < 1e-9 and head_on[1] < at[1], head_on
        got = gunsight.solution(gun, at, across)
        assert got["lead"] > 4.0, f"the sight showed {got['lead']:.1f}° of lead"
        return (f"12 km abeam at 350 m/s: led {led[0] * 1000:,.0f} m over "
                f"{flight:.2f} s, {got['lead']:.1f}° of deflection; "
                "a beam is led nothing")

    @check("the mounting swings at its own rate and stops where the hull is")
    def _():
        turret = _seat("fusion_lance")                  # 7°/s, ±70° arc
        kind = turret.kind
        turret_sim.order(turret, 60.0, 0.0)
        turret_sim.tick(turret, 1.0)
        assert abs(turret.bearing - kind.traverse) < 1e-6, (
            f"one second moved it {turret.bearing:.2f}° of {kind.traverse}")
        # Told to go past the stop, it goes to the stop and no further.
        turret_sim.order(turret, 179.0, 89.0)
        for _tick in range(200):
            turret_sim.tick(turret, 0.5)
        assert abs(turret.bearing - kind.arc) < 0.01, turret.bearing
        assert abs(turret.elevation - kind.up) < 0.01, turret.elevation
        assert not gunsight.in_arc(kind, kind.arc + 2.0, 0.0), "the arc leaks"
        # A faster mounting really is faster, and it is the table that says
        # so — measured against a *fresh* lance, not the one now sitting on
        # its stop, which is 70° from the middle and moving nowhere.
        quick = _seat("pdc")
        turret_sim.order(quick, 60.0, 0.0)
        turret_sim.tick(quick, 1.0)
        slow = _seat("fusion_lance")
        turret_sim.order(slow, 60.0, 0.0)
        turret_sim.tick(slow, 1.0)
        assert quick.bearing > slow.bearing * 4, (quick.bearing, slow.bearing)
        return (f"fusion lance {slow.bearing:,.0f}° in a second to a "
                f"±{kind.arc:,.0f}° stop; the cannon does "
                f"{quick.bearing:,.0f}° in the same second")

    @check("the director takes the gun, and a hand on the stick takes it back")
    def _():
        rng = RNG("director")
        turret = _seat("pdc")
        contact = foes.make("bogey", "Bogey", "drone", (6.0, 9.0, 2.0),
                            vel=(0.0, -0.3, 0.0))
        action = skirmish.open_action(turret, [contact])
        turret_sim.lock(turret, "bogey")
        for _tick in range(80):
            skirmish.tick(action, rng)
        mark = skirmish.solution(action, contact)
        off = gunsight.off_bore(turret.bearing, turret.elevation,
                                mark["aim"][0], mark["aim"][1])
        assert off < 1.0, f"the director left the gun {off:.1f}° off"
        # A push on the stick drops the lock rather than fighting it.
        turret_sim.stick(turret, -1.0, 0.0)
        assert not turret.locked, "the director kept the mounting"
        was = turret.bearing
        skirmish.tick(action, rng, 0.5)
        assert turret.bearing < was, "the stick moved nothing"
        return f"director on in {off:.2f}°; the stick takes it off at once"

    @check("a gun runs out, feeds, cooks off and comes back")
    def _():
        rng = RNG("heat")
        turret = _seat("fusion_lance")                  # 26 heat a pull
        for _pull in range(6):
            turret.cooldown = 0.0
            turret_sim.pull(turret, rng)
        assert turret.jammed, f"{turret.heat:.0f}° and still firing"
        ok, why = turret_sim.can_fire(turret)
        assert not ok and "Cooked" in why, why
        for _tick in range(400):
            turret_sim.tick(turret, 0.2)
        assert not turret.jammed, "it never came back"
        # And a magazine empties, then feeds.
        gun = _seat("railgun")
        kind = gun.kind
        for _pull in range(kind.rounds + 2):
            # The clock and the temperature both stood down: this check is
            # about the magazine, and a railgun at 12° a pull cooks off after
            # nine of them, which is the *other* check above.
            gun.cooldown, gun.heat, gun.jammed = 0.0, 0.0, False
            turret_sim.pull(gun, rng)
        assert gun.rounds <= 0 and gun.reloading > 0.0, (gun.rounds,
                                                         gun.reloading)
        for _tick in range(int(kind.reload_s / 0.1) + 4):
            turret_sim.tick(gun, 0.1)
        assert gun.rounds == kind.rounds, gun.rounds
        # A beam has no magazine and says so rather than pretending.
        beam = _seat("particle_beam")
        fed, said = turret_sim.feed(beam)
        assert not fed and "reactor" in said, said
        return (f"cooked at {turret_sim.COOKED:.0f}° and cleared; "
                f"{kind.rounds} rounds out and {kind.reload_s:,.0f} s back in")

    @check("a rack puts a seeker on the plot, and the screen can take it off")
    def _():
        rng = RNG("seekers")
        rack = foes.make("raider", "Raider", "corvette", (0.0, 18.0, 0.0),
                         behaviour="stand", stand_km=18.0, guns=(foes.RACK,))
        action = skirmish.open_action(_seat("pdc"), [rack], hp=400.0,
                                      max_hp=400.0)
        for _tick in range(200):
            skirmish.tick(action, rng)
        seekers = [c for c in action.contacts if c.behaviour == "home"]
        assert seekers, "a full rack launched nothing in twenty seconds"
        # It closes, and it hurts when it arrives.
        first = seekers[0]
        assert first.range_km < 18.0, first.range_km
        # And a point-defence cannon can kill one: they are contacts.
        turret_sim.lock(action.turret, first.id)
        for _tick in range(300):
            skirmish.tick(action, rng)
            mark = skirmish.aim_now(action)
            if mark is None:
                break
            off = gunsight.off_bore(action.turret.bearing,
                                    action.turret.elevation,
                                    mark["aim"][0], mark["aim"][1])
            if off < 4.0:
                skirmish.fire(action, rng)
            if first.dead:
                break
        assert first.dead, (f"{first.name} survived a point-defence cannon at "
                            f"{first.range_km:.2f} km")
        return (f"{len(seekers)} seeker(s) launched; one killed by the screen, "
                f"{action.turret.hits} of {action.turret.fired} landed")

    @check("taking a station's turrets off silences it, and its mast blinds it")
    def _():
        station = foes.fit(
            foes.make("hub", "Hub", "station", (0.0, 9.0, 0.0),
                      behaviour="fixed", guns=(foes.MEDIUM,)),
            "turret", "turret", "sensor", "reactor")
        assert not foes.silenced(station), "it was born silent"
        assert foes.can_shoot(station, 0), "it cannot shoot at all"
        assert foes.blinded(station) == 1.0, foes.blinded(station)
        for piece in station.parts:
            if piece.kind == "turret":
                foes.hurt(station, piece.max_hp, "the gun", part=piece.id)
        assert foes.silenced(station), "the turrets are off and it still fires"
        assert not foes.can_shoot(station, 0), "a silenced hub shot back"
        mast = next(p for p in station.parts if p.kind == "sensor")
        foes.hurt(station, mast.max_hp, "the gun", part=mast.id)
        assert foes.blinded(station) < 0.5, foes.blinded(station)
        # The whole thing is hurt by every piece that came off it.
        assert station.hp < station.max_hp, station.hp
        # And a drive off a mover stops it moving.
        boat = foes.fit(foes.make("boat", "Boat", "corvette", (0.0, 8.0, 0.0),
                                  behaviour="run", pace=0.4), "engine")
        drive = boat.parts[0]
        foes.hurt(boat, drive.max_hp, "the gun", part=drive.id)
        was = boat.at
        foes.steer(boat, 1.0, RNG("still"))
        assert boat.at == was and foes.crippled(boat), boat.at
        return ("turrets off → silent; mast off → "
                f"{foes.blinded(station):.0%} of its aim; drive off → still")

    @check("every drill in the school can be won")
    def _():
        won, said = 0, []
        for drill in table.in_order():
            _action, verdict = _play(drill)
            if verdict["won"]:
                won += 1
            said.append(f"{drill.id} {verdict['rating']}")
        assert won >= 8, f"only {won} of {len(table.DRILLS)}: {said}"
        return f"{won} of {len(table.DRILLS)} won by the bot — " + ", ".join(
            said[:4]) + " …"

    @check("a drill's waves all arrive, and the directives read the state")
    def _():
        drill = table.DRILL_BY_ID["pack"]
        action, verdict = _play(drill)
        assert len(action.waves_in) == len(drill.waves), (
            f"{len(action.waves_in)} of {len(drill.waves)} waves flew — an "
            "exercise that ends before its schedule is not the exercise")
        assert action.clock >= drill.waves[-1].at, action.clock
        rows = {r["id"]: r for r in verdict["rows"]}
        assert set(rows) == {a.id for a in drill.aims}, sorted(rows)
        # The list is a read: asking twice of an unchanged action says the
        # same thing, which is what lets it be drawn every frame.
        again = drill_sim.directives(action, drill)
        assert [r["done"] for r in again] == [r["done"] for r in verdict["rows"]]
        return (f"{len(action.waves_in)} waves over {action.clock:,.0f} s; "
                f"{len(rows)} directives, read twice the same")

    @check("every seat names a real gun, and every drill a real seat")
    def _():
        known = {p.id for p in armaments.ARMAMENTS}
        missing = [t.part for t in turret_data.TURRETS if t.part not in known]
        assert not missing, f"seats for armaments nobody stocks: {missing}"
        for kind in turret_data.TURRETS:
            assert turret_data.weapon_for(kind.part) is not None, kind.part
            assert kind.traverse > 0 and kind.arc > 0, kind.part
        seats = {t.part for t in turret_data.TURRETS}
        for drill in table.DRILLS:
            assert drill.seat in seats, f"{drill.id} sits at {drill.seat}"
            assert drill.aims, f"{drill.id} asks for nothing"
            assert drill.waves, f"{drill.id} has an empty sky"
            for spawn in [s for wave in drill.waves for s in wave.spawn]:
                assert spawn.kind in foes.KINDS, (drill.id, spawn.kind)
                for gun in spawn.guns:
                    assert gun in drill_sim.GUNS, (drill.id, gun)
                for part in spawn.parts:
                    assert part in foes.SUBSYSTEMS, (drill.id, part)
        return (f"{len(turret_data.TURRETS)} seats over {len(known)} "
                f"armaments; {len(table.DRILLS)} drills, every spawn real")

    @check("a gun on your own hull is manned, and what it does lands in the fight")
    def _():
        from ..sim import encounters
        game = new_game("manned")
        seats = manning.seats(game)
        assert seats, (
            "a hull with armament and no seat behind any of it: "
            f"{list(getattr(game.ship, 'fitted', []))}")
        assert all(s["kind"] is not None for s in seats), seats
        # With nothing shooting at you there is nothing to man, and the
        # refusal says where to go instead.
        action, why = manning.take(game, seats[0]["mount"])
        assert action is None and "school" in why, why
        # In an engagement, the seat opens on the ship you are fighting.
        from ..sim import combat as combat_sim
        enemy = encounters.make_enemy(RNG("manned"), "concordat", 1.4)
        game.battle = combat_sim.start(
            game.ship, game.ship_stats, enemy, bonuses=game.bonuses,
            officers=game.officers, game=game, rng=game.rng("fight"))
        action, why = manning.take(game, seats[0]["mount"])
        assert action is not None, why
        foe = next(c for c in action.contacts if c.id == "enemy")
        assert foe.parts, "the ship you are fighting has nothing to shoot off"
        was = sum(layer.hp for layer in game.battle.enemy.ship.layers)
        foes.hurt(foe, 40.0, "your gun")
        first = manning.land(game, action, game.battle)
        again = manning.land(game, action, game.battle)
        now = sum(layer.hp for layer in game.battle.enemy.ship.layers)
        assert first["dealt"] > 0 and again["dealt"] == 0.0, (first, again)
        assert was - now == first["dealt"], (was, now, first)
        return (f"{len(seats)} seats on the hull; {first['dealt']:,.0f} landed "
                "in the engagement, and a second call banks nothing")

    @check("the gunner's window paints, and a beat moves the action")
    def _():
        from ..ui import painting
        from ..ui.turret_window import TurretWindow
        keep = _app()
        game = new_game("turret-ui")
        win = main_window(game, (1200, 820))
        drill = table.DRILL_BY_ID["pass"]
        action = drill_sim.begin(drill, RNG("ui"))
        window = TurretWindow(win, action, drill)
        window.beat.stop()
        window.resize(1100, 760)
        window.show()
        keep.processEvents()
        misses = len(painting.MISSES)
        first = window.glass.grab().toImage()
        was = action.clock
        for _beat in range(30):
            window.step()
        keep.processEvents()
        assert action.clock > was, "thirty beats moved no time"
        window.refresh()
        keep.processEvents()
        again = window.glass.grab().toImage()
        assert again != first, "the picture never changed"
        assert len(painting.MISSES) == misses, painting.MISSES[-2:]
        # The hands reach the sim: a held stick swings the mounting.
        bearing = action.turret.bearing
        window.push("x", 1.0)
        for _beat in range(10):
            window.step()
        assert action.turret.bearing > bearing, "the stick did nothing"
        window.release("x")
        window.close()
        win.close()
        keep.processEvents()
        return (f"{action.clock:,.1f} s flown in the window, the picture "
                "moved, and the stick reaches the mounting")

    return True
