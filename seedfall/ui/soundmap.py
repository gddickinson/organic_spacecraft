"""What the game sounds like: game events to cues. It reads; it never writes.

`ui/audio.py` is the speaker and this is what decides to use it. Every hook
into the rest of the interface is one line, at a point that already exists:

- `widgets.button` — a click under every button (`click`);
- `MainWindow.go` — a swish on a screen change (`screen`);
- `log_panel.refresh` — the entries it is about to draw, one chime per kind,
  rate-limited (`logged`);
- `flight_clock` — the burn loop on a held thruster (`burn`), and once a
  beat the collision guard's ping (`beat`);
- `battle_view.build` — a turn's volleys, a hit, a breach, struck colours
  (`battle`);
- `afoot_view._act` — a shot on a deck, a hit on one of yours, one of yours
  down (`afoot`);
- the survey, dig and jump doors — `act`, after the act succeeded;
- `hud.refresh`, which runs on every act and every beat — the settings, a
  despatch arriving, a berth made fast, and the ambience (`hud`); `hud.build`
  hangs the mute chip in the menu bar's corner (`chip`).

**The sim never imports audio.** Where a thing leaves state behind — a berth
secured sets `Conn.landed`, a despatch raises `comms.unread` — this reads it
and compares with what it saw last time. Where an act leaves nothing (a jump,
a survey ping), the screen that performed it calls `act` once it succeeded.
What was seen last is kept on the window (`win.sound_ear`), never on the game:
the save codec refuses an attribute that is not a field.
"""

from __future__ import annotations

import time

from . import audio

#: The log's kinds that chime. Anything else — "", "dim", a colour — is
#: narration, and most of the log is narration: a chime per line would be a
#: metronome.
CHIMES = ("bad", "warn", "good")

#: Seconds between two chimes of one kind. One jump logs an arrival, a first
#: visit and two rumours in the same refresh; that is one burst and one chime.
CHIME_GAP = 1.5

#: For this long after a cue that says more — a berth, a jump, a survey —
#: the log's good and warn chimes and the screen swish stand aside, so an act
#: is one sound and not three. Bad news never stands aside.
QUIET_AFTER = 0.8

#: The clock the gaps are measured on. A check may put its own in.
clock = time.monotonic

#: Throttle bands for the held burn: QSoundEffect cannot bend pitch, so the
#: throttle picks one of three loops a band apart.
BANDS = ((0.34, "burn_low"), (0.75, "burn_mid"), (float("inf"), "burn_high"))

#: The proximity ping, in beats between pings: every beat when contact is a
#: couple of beats off, never slower than one in eight (two seconds at the
#: 250 ms beat). A beat is `TICK` seconds of flight times the time scale.
PING_SLOWEST = 8

#: A drone for each kind of system: by region first — `getattr`, so this
#: holds before and after the Far Reaches exist — then by the star.
REGION_DRONES = {"shoals": "amb_shoals", "hollow": "amb_hollow",
                 "cradle": "amb_cradle"}
DIM_STARS = ("M", "K", "T")         # red and orange dwarfs, T-Tauri
SILENT_STARS = ("X",)               # a black hole: the Hollow's near-silence


def _ear(win) -> dict:
    """What this window heard last, reset when the chronicle changes."""
    game = getattr(win, "game", None)
    ear = getattr(win, "sound_ear", None)
    if ear is None or ear["game"] != id(game):
        # Another chronicle in the same window: what the last one had
        # sounding stops with it.
        for cue in (ear["drone"], ear["burn"]) if ear is not None else ():
            if cue:
                audio.set_level(cue, 0.0)
        ear = {"game": id(game), "screen": None, "chimed": {}, "quiet": 0.0,
               "burn": "", "ping": 0, "unread": None, "conn": None,
               "drone": "", "bloom": None, "battle": None, "config": None}
        win.sound_ear = ear
    return ear


def configure(win) -> None:
    """Push the four sound settings into the façade. Nothing if unchanged.

    From `apply_options`, and from every HUD refresh — which is how a
    reloaded chronicle's settings take hold before anyone opens the page.
    """
    from ..sim import options as options_sim
    game = win.game
    wanted = (bool(options_sim.get(game, "sound")),
              int(options_sim.get(game, "sound_volume") or 0),
              bool(options_sim.get(game, "sound_effects")),
              bool(options_sim.get(game, "sound_ambience")))
    ear = _ear(win)
    if ear["config"] == wanted:
        return
    ear["config"] = wanted
    on, percent, effects, ambience = wanted
    audio.volume(percent / 100.0 if on else 0.0, effects, ambience)


def click(*_signal) -> None:
    """A button pressed. The quietest thing the game plays."""
    audio.play("click")


def screen(win) -> None:
    """A screen change, heard as a swish — not the window's first screen,
    and not a `go` to where it already is."""
    ear = _ear(win)
    here = getattr(win, "current", None)
    was, ear["screen"] = ear["screen"], here
    if was is not None and was != here and clock() >= ear["quiet"]:
        audio.play("swish")


def logged(win, fresh) -> None:
    """The log's new entries: one chime per kind in the burst, each kind no
    more than once every `CHIME_GAP`. None is a first draw, not news."""
    if not fresh:
        return
    ear = _ear(win)
    now = clock()
    kinds = {entry[2] for entry in fresh}
    for kind in CHIMES:
        if kind not in kinds:
            continue
        if kind != "bad" and now < ear["quiet"]:
            continue
        if now - ear["chimed"].get(kind, -CHIME_GAP) < CHIME_GAP:
            continue
        ear["chimed"][kind] = now
        audio.play(kind)


def act(win, cue: str) -> None:
    """An act that leaves nothing to read afterwards — a jump, a survey, a
    stratum dug — told by the screen that performed it, once it worked."""
    _ear(win)["quiet"] = clock() + QUIET_AFTER
    audio.play(cue)


def sample(win) -> None:
    """A chime at the level just set, from the options page."""
    configure(win)
    audio.play("good")


# ── flying ──────────────────────────────────────────────────────────────────

def _burn_cue(win) -> str:
    conn = getattr(win, "conn", None)
    if (not getattr(win, "burn_order", None) or conn is None
            or conn.over or conn.landed):
        return ""
    if not conn.arm_main:
        return "burn_rcs"
    throttle = float(conn.throttle or 0.0)
    return next(cue for top, cue in BANDS if throttle < top)


def burn(win) -> None:
    """Keep the burn loop in step with the hand on the stick: on while a
    thruster is held, the band following the throttle, off when released."""
    ear = _ear(win)
    want = _burn_cue(win)
    if want == ear["burn"]:
        return
    if ear["burn"]:
        audio.loop(ear["burn"], False)
    if want:
        audio.loop(want, True)
    ear["burn"] = want


#: What each kind of contact sounds like. A berthing already had a cue and
#: nothing else on the flight deck did — a hull struck at fifty metres a
#: second made no sound at all, which is the same hole the pictures had.
#: **Alongside and orbit ring through `hud` instead**, not here. They are
#: the two `_berthed` already watches for, and ringing them twice is what
#: the check that berth is heard *once* caught the moment this was wired in.
STRUCK_CUE = {
    "collision": "impact", "aground": "impact", "ditched": "impact",
    "scrape": "graze", "cut": "graze", "ward": "hit",
    "down": "berth", "captured": "berth",
    "alongside": "", "orbit": "",
    # An engagement rings its own bells through `battle` — the volleys by
    # family, the hit, the breach. A second cue here would double every one.
    "gunfire": "",
}


def struck(win, fresh) -> None:
    """A contact, heard. Takes the effects `ui/effects.watch` has just made.

    One sound for one moment, however many things happened in the tick: a
    cut that pulses and a ward that bites in the same minute is one event to
    an ear, and playing both makes a mess of the one that mattered.
    """
    configure(win)
    loudest = max(fresh, key=lambda e: e.power, default=None)
    if loudest is None:
        return
    cue = STRUCK_CUE.get(loudest.shock.kind, "")
    if not cue:
        return
    _ear(win)["quiet"] = clock() + QUIET_AFTER
    audio.play(cue)


def beat(win) -> None:
    """One beat of the flight: the collision guard's ping, repeating faster
    as contact nears, and a double pip once she cannot be stopped."""
    from ..sim import collision
    from ..sim.conn import TICK
    ear = _ear(win)
    threat = collision.scan(None, win.conn)
    if threat is None:
        ear["ping"] = 0
        return
    ear["ping"] -= 1
    if ear["ping"] > 0:
        return
    scale = max(1, int(getattr(win, "time_scale", 1)))
    beats = threat.seconds / (TICK * scale)
    ear["ping"] = max(1, min(PING_SLOWEST, int(beats / 2)))
    audio.play("proximity_urgent" if threat.level == "imminent"
               else "proximity")


# ── combat ──────────────────────────────────────────────────────────────────

def _family(b, shot) -> str:
    """kinetic, energy or bio: what a volley sounds like, from the weapon."""
    from ..sim import gunfire
    part = next((w for w in b.player.st.weapons if w.name == shot.weapon),
                None)
    if part is not None and part.family == "grown":
        return "bio"
    return "energy" if shot.look == gunfire.BEAM else "kinetic"


def battle(win, b) -> None:
    """A turn of an engagement, heard once however often it is redrawn:
    your volleys by weapon family, a hit on you, a layer lost, colours
    struck."""
    if b is None:
        return
    ear = _ear(win)
    key = (id(b), b.turn, len(b.log))
    seen = ear["battle"]
    if seen is not None and seen[0] == key:
        return
    fresh = seen is None or seen[0][0] != id(b)
    down = sum(1 for layer in b.player.ship.layers if layer.hp <= 0)
    struck = b.result == "struck"
    ear["battle"] = (key, down, struck)
    shots = list(getattr(b, "shots", ()))
    for family in sorted({_family(b, s) for s in shots
                          if s.mine and s.flew}):
        audio.play(f"volley_{family}")
    if any(s.landed and s.to == b.player.ship.name for s in shots
           if not s.mine):
        audio.play("hit")
    if not fresh and down > seen[1]:
        audio.play("breach")
    if struck and (fresh or not seen[2]):
        act(win, "struck")


def afoot(win, got: dict, walk) -> None:
    """A press on a deck, heard once: the party's own shot by what it was
    fired with, a hit on one of yours, one of yours going down."""
    if walk is None:
        return
    from ..data import afoot_arms
    mine = {a.id for a in walk.actors if a.side == "party"}
    if got.get("check") is not None and "hit" in got:
        who = next((a for a in walk.actors if a.id == walk.selected), None)
        laser = who is not None and afoot_arms.arm(who.weapon).laser
        audio.play("volley_energy" if laser else "volley_kinetic")
    events = list(got.get("events", []) or [])
    if any(e.get("kind") == "attack" and e.get("hit") and e.get("at") in mine
           for e in events):
        audio.play("hit")
    if any(e.get("kind") == "down" and e.get("who") in mine for e in events):
        audio.play("breach")


# ── the bar every screen shows ──────────────────────────────────────────────

def drone_for(system) -> str:
    """The ambience a system gets."""
    region = getattr(system, "region", "verge")
    if region in REGION_DRONES:
        return REGION_DRONES[region]
    star = getattr(system, "star", "G") or "G"
    if star in SILENT_STARS:
        return "amb_hollow"
    return "amb_red" if star in DIM_STARS else "amb_bright"


def bloom_level(game) -> float:
    """How loud the Bloom's swell is, 0..1. You can hear it getting worse.

    **What the captain has seen of it**, `threat.known_bloom` — not the
    sector's true burden, which would put through the speaker exactly what
    the fog keeps off the chart. Against the burden at which it turns
    Sovereign, on a square root, so the first stages are already audible:
    measured, Vegetative (4) sounds at 0.42 and Motile (9) at 0.63.
    """
    from ..data.bloom import STAGES
    from ..sim import threat
    seen = threat.known_bloom(game)["burden"]
    return min(1.0, max(0.0, seen / STAGES[-1].threshold)) ** 0.5


def _berthed(ear, game) -> bool:
    """Did a flight come alongside or make orbit since the last refresh?
    `berthing.commit` sets `Conn.landed` on the flight it settles."""
    conn = getattr(game, "conn", None)
    now = (id(conn), bool(conn.landed)) if conn is not None else None
    was, ear["conn"] = ear["conn"], now
    return (now is not None and was is not None and was[0] == now[0]
            and not was[1] and now[1]
            and conn.outcome in ("alongside", "orbit"))


def hud(win, unread: int) -> None:
    """Once a refresh and once a beat, from the bar every screen shows."""
    configure(win)
    ear = _ear(win)
    game = win.game
    if ear["unread"] is not None and unread > ear["unread"]:
        audio.play("despatch")
    ear["unread"] = unread
    if _berthed(ear, game):
        act(win, "berth")
    from . import sky_strip        # lazily: it builds widgets, which ring us
    sky_strip.sound(win, ear)      # a flare warning, the nova (innovation 7)
    burn(win)                  # a berth or a battle can end a burn unheld
    drone = drone_for(game.system)
    if drone != ear["drone"]:
        if ear["drone"]:
            audio.set_level(ear["drone"], 0.0)
        audio.set_level(drone, 1.0)
        ear["drone"] = drone
    where = (game.day, game.location_id)
    if where != ear["bloom"]:
        ear["bloom"] = where
        audio.set_level("bloom", bloom_level(game))
    _show_chip(win)


# ── the mute chip, in the menu bar's corner ─────────────────────────────────

def chip(win):
    """The speaker chip: sound on or off, the same setting as the options
    page, one press from anywhere. Kept as `win.sound_btn`; what is handed
    back is the chip in a margin, for the menu bar's corner."""
    from PyQt6.QtWidgets import QHBoxLayout, QWidget
    from . import theme
    from .widgets import button
    win.sound_btn = b = button("", lambda: mute(win), kind="flat")
    b.setAccessibleName("Sound on or off")
    b.setFixedSize(30, 20)
    # A button's own padding would leave no room for the icon at 30 x 20.
    b.setStyleSheet("QPushButton { padding: 0; border-color: %s; }"
                    % theme.LINE2)
    holder = QWidget()
    row = QHBoxLayout(holder)
    row.setContentsMargins(0, 1, 12, 1)
    row.addWidget(b)
    return holder


def mute(win) -> None:
    from ..sim import options as options_sim
    options_sim.set_to(win.game, "sound",
                       not options_sim.get(win.game, "sound"))
    configure(win)
    _show_chip(win)
    win.save()


def _speaker(on: bool):
    """A speaker, drawn: waves when it is on, a cross when it is muted.

    Drawn rather than typed — a "♪" in the bar's 10 px face was four pixels
    wide, and the muted one could not be told from it at arm's length.
    Painted at twice the size it is shown, so it stays sharp on a HiDPI
    screen.
    """
    from PyQt6.QtCore import QPointF, Qt
    from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
    from . import theme
    ink = QColor(theme.INK2 if on else theme.tint("warn"))
    art = QPixmap(36, 36)
    art.fill(Qt.GlobalColor.transparent)
    p = QPainter(art)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(ink)
    p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in (
        (5, 13), (11, 13), (19, 6), (19, 30), (11, 23), (5, 23))]))
    p.setBrush(Qt.BrushStyle.NoBrush)
    pen = QPen(ink, 2.6)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    if on:
        for r in (6, 11):
            p.drawArc(18 - r, 18 - r, 2 * r, 2 * r, -45 * 16, 90 * 16)
    else:
        p.drawLine(24, 13, 32, 23)
        p.drawLine(32, 13, 24, 23)
    p.end()
    return QIcon(art)


def _show_chip(win) -> None:
    b = getattr(win, "sound_btn", None)
    if b is None:
        return
    from ..sim import options as options_sim
    on = bool(options_sim.get(win.game, "sound"))
    if b.property("sound_on") != on:
        from PyQt6.QtCore import QSize
        b.setProperty("sound_on", on)
        b.setIcon(_speaker(on))
        b.setIconSize(QSize(15, 15))
        b.setToolTip("Sound on — press to mute" if on
                     else "Sound off — press to hear the ship again")
