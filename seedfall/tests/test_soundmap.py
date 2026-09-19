"""The right cue at the right moment, heard through the game's own doors.

`test_audio` pins the synthesiser and the façade; this plays the game with a
fake speaker (`test_audio.Recorder`, put in with `audio.install`) and asserts
what was heard. Every act goes through the door a player's press goes
through — the log refresh, `flight_clock`, `battle_act`, the map's jump, the
system screen's survey, the one clock's beat — so a hook that came unwired
fails here rather than going quiet in play.

The chime gaps are measured on `soundmap.clock`, which each check replaces
with one it can wind on by hand: a rate limit tested with `sleep` is a slow
check that fails under load.
"""

from __future__ import annotations

import contextlib
from types import SimpleNamespace

from ..core.rng import RNG
from ..core.state import new_game
from ..ui import audio, soundmap
from .harness import Suite
from .test_audio import Recorder

#: Held for the life of the process: see `qtkit`.
_ALIVE: list = []


class _Clock:
    """A clock that moves only when told."""

    def __init__(self):
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


@contextlib.contextmanager
def _listening(seed: str):
    """A window over a fresh chronicle, with a fake speaker in before the
    window exists, so what it plays on opening is heard too."""
    from . import qtkit
    ear, tick, real = Recorder(), _Clock(), soundmap.clock
    audio.install(ear)
    soundmap.clock = tick
    try:
        game = new_game(seed)
        win = qtkit.main_window(game)
        _ALIVE.append(win)
        yield game, win, ear, tick
    finally:
        soundmap.clock = real
        audio.install(None)


def _threat_conn(game):
    """An approach to the first quay, for putting her on a collision course."""
    from ..sim import berthing as berth_sim
    from ..sim import track as track_sim
    quay = next(c for c in track_sim.contacts(game) if c.kind == "anchorage"
                and berth_sim.can_conn(game, c)[0])
    return berth_sim.begin(game, quay)[0]


def run(suite: Suite) -> bool:
    """True: it ran. An optional suite returning nothing reads as skipped."""
    check = suite.check

    @check("a burst of news chimes once per kind, and a second burst waits")
    def _():
        with _listening("snd-log") as (game, win, ear, tick):
            mark = len(ear.heard)
            for i in range(5):
                game.add_log(f"good {i}", "good")
            for i in range(3):
                game.add_log(f"bad {i}", "bad")
            game.add_log("uneasy", "warn")
            game.add_log("narration", "")
            win.refresh()
            burst = ear.played(mark)
            assert sorted(burst) == ["bad", "good", "warn"], burst

            mark = len(ear.heard)
            game.add_log("more", "good")
            game.add_log("worse", "bad")
            win.refresh()
            assert ear.played(mark) == [], ear.played(mark)
            tick.t += soundmap.CHIME_GAP
            game.add_log("later", "good")
            win.refresh()
            assert ear.played(mark) == ["good"], ear.played(mark)
        return ("ten entries: bad, warn, good once each; a burst inside "
                f"{soundmap.CHIME_GAP} s is silent, one after it chimes")

    @check("a screen change swishes, a button clicks, the first screen is "
           "quiet")
    def _():
        with _listening("snd-screen") as (_game, win, ear, _tick):
            assert "swish" not in ear.played(), ear.played()
            mark = len(ear.heard)
            win.go("ship")
            win.go("ship")
            assert ear.played(mark) == ["swish"], ear.played(mark)
            mark = len(ear.heard)
            win.nav_buttons["port"].click()
            assert ear.played(mark) == ["click", "swish"], ear.played(mark)
        return "one swish for two goes to one screen; click before swish"

    @check("a held burn is a loop: on at the press, following the throttle, "
           "off at the release")
    def _():
        from ..sim import freeflight as free_sim
        from ..ui import flight_clock
        with _listening("snd-burn") as (game, win, ear, _tick):
            conn, why = free_sim.begin(game)
            assert conn is not None, why
            win.conn = conn
            win.go("pilot")
            conn.arm_main, conn.throttle = True, 1.0
            mark = len(ear.heard)
            flight_clock.start_burn(win, "forward")
            assert ear.loops(mark) == [("burn_high", True)], ear.loops(mark)
            mark = len(ear.heard)
            win.set_conn_clock(True)
            conn.throttle = 0.2
            win.fly_beat()
            assert ear.loops(mark) == [("burn_high", False),
                                       ("burn_low", True)], ear.loops(mark)
            mark = len(ear.heard)
            flight_clock.end_burn(win)
            assert ear.loops(mark) == [("burn_low", False)], ear.loops(mark)
            # The attitude jets hiss; and a key held while the captain walks
            # off the deck stops with the order it belonged to.
            conn.arm_main = False
            mark = len(ear.heard)
            flight_clock.start_burn(win, "left")
            win.go("helm")
            assert ear.loops(mark) == [("burn_rcs", True),
                                       ("burn_rcs", False)], ear.loops(mark)
            win.set_conn_clock(False)
            assert not any(c.startswith("burn") for c in audio.wanted())
        return "high → low with the throttle, off on release and on leaving"

    @check("the collision guard pings faster as contact nears")
    def _():
        with _listening("snd-prox") as (game, win, ear, _tick):
            conn = _threat_conn(game)
            win.conn = conn
            counts = {}
            for km, speed in ((60, 60), (300, 200), (300, 400), (300, 800),
                              (12, 200)):
                conn.pos, conn.vel = [0.0, -km, 0.0], [0.0, speed, 0.0]
                win.sound_ear["ping"] = 0
                mark = len(ear.heard)
                for _ in range(24):          # six seconds of 250 ms beats
                    soundmap.beat(win)
                counts[(km, speed)] = ear.played(mark)
            rates = [len(v) for v in counts.values()]
            assert rates == sorted(rates) and rates[0] < rates[-1] == 24, rates
            assert set(counts[(60, 60)]) == {"proximity"}, counts[(60, 60)]
            assert set(counts[(12, 200)]) == {"proximity_urgent"}
            conn.vel = [0.0, -5.0, 0.0]          # opening: nothing to say
            mark = len(ear.heard)
            soundmap.beat(win)
            assert not ear.played(mark)
            # And through the one clock, not only the hook. Close in: an
            # approach flown from 60 km out is given up as adrift.
            conn.pos, conn.vel = [0.0, -12.0, 0.0], [0.0, 30.0, 0.0]
            win.sound_ear["ping"] = 0
            mark = len(ear.heard)
            win.set_conn_clock(True)
            win.fly_beat()
            win.set_conn_clock(False)
            beat = [c for c in ear.played(mark) if c.startswith("proximity")]
            assert len(beat) == 1, ear.played(mark)
        return "pings in 24 beats as contact nears: " + ", ".join(
            f"{km} km at {v} m/s {len(n)}" for (km, v), n in counts.items())

    @check("a berth made fast rings the bells, from the flight's own state")
    def _():
        from ..sim import autopilot as pilot_sim
        with _listening("snd-berth") as (game, win, ear, _tick):
            game.orbit_body = game.system.bodies[0].id
            conn = _threat_conn(game)
            win.conn = conn
            win.refresh()        # the bar sees her under way, as a beat would
            pilot_sim.fly(conn, "close", 1200)
            assert conn.outcome == "alongside", conn.outcome
            mark = len(ear.heard)
            win.fly_beat()                   # the one clock settles it
            heard = ear.played(mark)
            assert heard.count("berth") == 1, heard
            assert "good" not in heard, (
                f"the log's chime did not stand aside for the berth: {heard}")
            mark = len(ear.heard)
            win.refresh()
            assert "berth" not in ear.played(mark), "rang twice for one berth"
        return f"heard {heard}"

    @check("a turn of combat is heard once: your volleys by family, a hit "
           "on you")
    def _():
        from ..sim import encounters
        with _listening("sound-drive") as (_game, win, ear, _tick):
            enemy = encounters.make_enemy(RNG("sound-drive"), "freeholds", 2)
            win.begin_combat({"enemy": enemy, "intro": "test"}, "system")
            view, b = win.views["battle"], win.battle
            volleys = hits = 0
            for _ in range(10):
                if b.over:
                    break
                mark = len(ear.heard)
                view._act({"type": "station", "order": "salvo"})
                want = set()
                for shot in b.shots:
                    part = next((w for w in b.player.st.weapons
                                 if w.name == shot.weapon), None)
                    if shot.mine and shot.flew and part is not None:
                        want.add("volley_bio" if part.family == "grown" else
                                 "volley_energy" if not (
                                     part.wpn.ammo or {"flak", "seeking"}
                                     & set(part.wpn.traits))
                                 else "volley_kinetic")
                    if (not shot.mine and shot.landed
                            and shot.to == b.player.ship.name):
                        want.add("hit")
                got = {c for c in ear.played(mark)
                       if c.startswith("volley") or c == "hit"}
                assert got == want, (b.turn, got, want)
                volleys += any(c.startswith("volley") for c in got)
                hits += "hit" in got
                mark = len(ear.heard)
                view.refresh()
                assert not ear.played(mark), "a redraw replayed the turn"
            assert volleys and hits, (volleys, hits)
            win.battle = None
        return f"{volleys} turns with a volley, {hits} with a hit"

    @check("a despatch arriving rings once; the jump and the survey are "
           "heard at their doors")
    def _():
        from ..sim import comms as comms_sim
        from ..sim.actions import jump_quote
        with _listening("sound-drive") as (game, win, ear, tick):
            comms_sim.send(game, "news", "Sector bulletin", "news", "A test",
                           "Body.")
            game.advance_days(30)
            mark = len(ear.heard)
            win.refresh()
            win.refresh()
            assert ear.played(mark).count("despatch") == 1, ear.played(mark)

            game.ship.cargo["volatiles"] = 200
            target = next(s for s in game.galaxy.systems
                          if s.id != game.location_id
                          and jump_quote(game, s, "steady")["in_range"])
            before = win.sound_ear["drone"]
            tick.t += 10
            mark = len(ear.heard)
            win.views["map"].selected = target.id
            win.views["map"]._jump("steady")
            heard = ear.played(mark)
            assert heard[0] == "jump" and "swish" not in heard, heard
            assert win.sound_ear["drone"] == soundmap.drone_for(target)
            if before != win.sound_ear["drone"]:
                assert (before, False) in ear.loops(mark), ear.loops(mark)

            tick.t += 10
            mark = len(ear.heard)
            view = win.views["system"]
            view.selected = 0
            view._survey("pass")
            assert ear.played(mark)[:1] == ["survey"], ear.played(mark)
        return f"despatch once; {heard}; survey pinged"

    @check("a stratum dug is a tick, one a stratum")
    def _():
        from ..data.xenotech import XENOTECH
        from ..sim import dig as dig_sim
        with _listening("snd-dig") as (game, win, ear, tick):
            body = game.system.bodies[0]
            body.relic = body.relic or XENOTECH[0].id
            body.relic_found = True
            started = dig_sim.begin(game, 0)
            assert started["ok"], started.get("why")
            win.dig = started["dig"]
            win.go("dig")
            ticks = 0
            for _ in range(4):
                if win.dig.over:
                    break
                tick.t += 10
                mark = len(ear.heard)
                win.views["dig"]._work("careful")
                assert ear.played(mark)[:1] == ["dig"], ear.played(mark)
                ticks += 1
            win.dig = None
        return f"{ticks} strata, {ticks} ticks"

    @check("each kind of system has its drone, and the Bloom's swell rises "
           "with what the captain has seen")
    def _():
        drone = soundmap.drone_for
        cases = {("verge", "M"): "amb_red", ("verge", "K"): "amb_red",
                 ("verge", "G"): "amb_bright", ("verge", "A"): "amb_bright",
                 ("verge", "X"): "amb_hollow", ("shoals", "F"): "amb_shoals",
                 ("hollow", "M"): "amb_hollow", ("cradle", "B"): "amb_cradle",
                 ("elsewhere", "M"): "amb_red"}
        for (region, star), want in cases.items():
            assert drone(SimpleNamespace(region=region, star=star)) == want
        assert drone(SimpleNamespace(star="M")) == "amb_red", "pre-regions"

        from ..sim import intel as intel_sim
        with _listening("snd-bloom") as (game, win, ear, _tick):
            for s in game.galaxy.systems:
                s.bloom = 0.0
            for s in game.galaxy.systems[:10]:
                s.visited = True           # ten systems the captain has seen
            seen = [s for s in game.galaxy.systems
                    if intel_sim.sees_bloom(game, s)]
            unseen = [s for s in game.galaxy.systems if s not in seen]
            levels, told = [], []
            for burden in (0.0, 0.5, 2.0, 4.0, 9.0):
                for s in seen:
                    s.bloom = burden / len(seen)
                levels.append(soundmap.bloom_level(game))
                win.sound_ear["bloom"] = None      # as a new day would
                mark = len(ear.heard)
                win.refresh()
                told += [v for _verb, c, v in ear.heard[mark:]
                         if c == "bloom" and v > 0]
            assert levels[0] == 0.0 and levels == sorted(set(levels)), levels
            assert told == sorted(told) and len(told) == 4, told
            for s in unseen:
                s.bloom = 0.9
            assert soundmap.bloom_level(game) == levels[-1], (
                "growth nobody has seen was put through the speaker")
        return (f"{len(cases)} systems, and the swell at "
                + ", ".join(f"{v:.2f}" for v in levels)
                + f" for burdens 0 to 9 across {len(seen)} seen systems")

    return True
