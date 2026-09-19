"""The one door to the speaker: `play`, `loop`, `set_level`, `volume`.

The only module in the game that imports QtMultimedia, and it does so
lazily — the first time a cue would actually sound. `ui/soundmap.py` decides
*what* is heard, from state it reads; this decides whether anything is heard
at all, and at what level.

**It does nothing, quietly, when:**

- the platform is `offscreen` or `minimal` — every check in the suite;
- QtMultimedia cannot be imported;
- there is no audio output device;
- the player has sound off, or the cue's group (effects, ambience) off;
- the device failed once. It is not asked again this session: a speaker that
  raised on one call will raise on the next sixty.

**It never raises into a slot.** What a sound device is expected to do
wrong — a C++ object deleted under it (`RuntimeError`), a cache file that
cannot be written or opened (`OSError`) — is caught by name and turns the
sound off for the session with the reason kept (`status`). Anything else is
a bug here, and goes to `core.guard.swallowed`: loud under test, one line in
play, and silence after it.

**Counted.** `REQUESTED` is every cue the game asked for and `PLAYED` every
one that reached a backend. That is how the options check proves each sound
switch does something with no speaker in the room: turn one off and the
second count stops following the first.

**A backend** is anything with `play(cue, volume)` and `loop(cue, volume)`,
where a loop at volume 0 is stopped. `install` puts a fake one in, which is
how a check hears exactly which cues fired, at what level.
"""

from __future__ import annotations

import os

from ..data.sounds import CUES_BY_ID

#: Cue id -> times the game asked for it, and times a backend was told.
REQUESTED: dict = {}
PLAYED: dict = {}

#: The master level as the player set it (0..1, and 0 with sound off), and
#: the two group switches (0 or 1).
_MIX = {"master": 0.7, "effects": 1.0, "ambience": 1.0}

#: Loops asked for and the level each was asked at. Kept while muted, so
#: turning sound back on resumes what ought to be sounding.
_WANT: dict = {}

#: What each loop's backend was last told, so a level re-asserted on every
#: refresh is a dict lookup and not a call into Qt.
_TOLD: dict = {}

_STATE = {"backend": None, "tried": False, "silent": "not asked yet"}

#: The platforms Qt renders with no display, and so with no speaker either.
HEADLESS = ("offscreen", "minimal")


class _Speaker:
    """One `QSoundEffect` per cue, made once from the synthesised cache,
    every one on the same output device."""

    def __init__(self, files: dict, device):
        from PyQt6.QtCore import QUrl
        from PyQt6.QtMultimedia import QSoundEffect
        self.effects = {}
        for cue_id, path in files.items():
            effect = QSoundEffect(device)
            effect.setSource(QUrl.fromLocalFile(str(path)))
            if CUES_BY_ID[cue_id].loop:
                effect.setLoopCount(QSoundEffect.Loop.Infinite.value)
            self.effects[cue_id] = effect

    def play(self, cue: str, volume: float) -> None:
        effect = self.effects[cue]
        effect.setVolume(volume)
        effect.play()

    def loop(self, cue: str, volume: float) -> None:
        effect = self.effects[cue]
        if volume <= 0.0:
            effect.stop()
            return
        effect.setVolume(volume)
        if not effect.isPlaying():
            effect.play()


def _output():
    """The default audio output; or, when there is none, why not, in words;
    or None when it is too soon to say (no application yet — asked again).

    **The default output only, asked once, and handed to every effect.**
    Listing every output made Qt 6.4's CoreAudio layer print two warnings a
    device on a Mac with a multichannel monitor attached, and a
    `QSoundEffect` built without a device asks again for itself — measured,
    four more lines per effect, 112 for 28. Asked this way it is 12, once.
    """
    if os.environ.get("QT_QPA_PLATFORM", "") in HEADLESS:
        return f"the {os.environ['QT_QPA_PLATFORM']} platform has no speaker"
    from PyQt6.QtGui import QGuiApplication
    if QGuiApplication.instance() is None:
        return None
    platform = QGuiApplication.platformName()
    if platform in HEADLESS:
        return f"the {platform} platform has no speaker"
    try:
        from PyQt6.QtMultimedia import QMediaDevices
    except ImportError:
        return "QtMultimedia is not installed"
    device = QMediaDevices.defaultAudioOutput()
    return "no audio output device" if device.isNull() else device


def _backend():
    if _STATE["backend"] is not None or _STATE["tried"]:
        return _STATE["backend"]
    device = _output()
    if device is None:
        return None
    _STATE["tried"] = True
    if isinstance(device, str):
        _STATE["silent"] = device
        return None
    from . import synth
    _STATE["backend"] = _Speaker(synth.ensure(), device)
    _STATE["silent"] = ""
    return _STATE["backend"]


def _fail(where: str, err: BaseException) -> None:
    """The device let us down: silence for the rest of the session."""
    _STATE.update(backend=None, tried=True,
                  silent=f"{where} failed: {type(err).__name__}: {err}")
    _TOLD.clear()


def _gain(cue: str, level: float = 1.0) -> float:
    """Linear gain for a cue. The master is on a square law — half-way is a
    quarter of the power, about where the ear hears half as loud; a linear
    slider spends its whole top half on differences nobody can hear."""
    group = CUES_BY_ID[cue].group
    return _MIX["master"] ** 2 * _MIX[group] * max(0.0, min(1.0, level))


def _tell(cue: str) -> None:
    """Bring one loop's backend in line with what is wanted of it."""
    volume = _gain(cue, _WANT.get(cue, 0.0))
    if _TOLD.get(cue, 0.0) == volume:
        return
    speaker = _backend() if volume > 0.0 else _STATE["backend"]
    if speaker is None:
        return
    speaker.loop(cue, volume)
    _TOLD[cue] = volume
    if volume > 0.0:
        PLAYED[cue] = PLAYED.get(cue, 0) + 1


def play(cue: str) -> bool:
    """Play a one-shot cue. True if it reached a speaker."""
    REQUESTED[cue] = REQUESTED.get(cue, 0) + 1
    try:
        volume = _gain(cue)
        speaker = _backend() if volume > 0.0 else None
        if speaker is None:
            return False
        speaker.play(cue, volume)
    except (RuntimeError, OSError) as err:
        _fail("play", err)
        return False
    except Exception as err:            # noqa: BLE001 — see the module note
        _fail("play", err)
        from ..core.guard import swallowed
        swallowed("audio.play", err)
        return False
    PLAYED[cue] = PLAYED.get(cue, 0) + 1
    return True


def set_level(cue: str, level: float) -> None:
    """Run a loop at `level` (0..1) of its full volume; 0 stops it.

    The ambience's one control: a drone is set to a level when its system
    is entered and to 0 when it is left, and the Bloom's swell is set to
    wherever the burden has got to.
    """
    level = max(0.0, min(1.0, float(level)))
    if _WANT.get(cue, 0.0) == level and cue in _WANT:
        return
    if level > 0.0:
        REQUESTED[cue] = REQUESTED.get(cue, 0) + 1
    _WANT[cue] = level
    try:
        _tell(cue)
    except (RuntimeError, OSError) as err:
        _fail("set_level", err)
    except Exception as err:            # noqa: BLE001 — see the module note
        _fail("set_level", err)
        from ..core.guard import swallowed
        swallowed("audio.set_level", err)


def loop(cue: str, on: bool) -> None:
    """Start or stop a loop at its full level — a held burn."""
    set_level(cue, 1.0 if on else 0.0)


def volume(master: float, effects: float, ambience: float) -> None:
    """The mix: master 0..1 (0 with sound off) and the two group switches.

    Running loops follow at once — a drone muted from the options page stops
    now, not when the next system is entered.
    """
    _MIX.update(master=max(0.0, min(1.0, float(master))),
                effects=1.0 if effects else 0.0,
                ambience=1.0 if ambience else 0.0)
    try:
        for cue in list(_WANT):
            _tell(cue)
    except (RuntimeError, OSError) as err:
        _fail("volume", err)
    except Exception as err:            # noqa: BLE001 — see the module note
        _fail("volume", err)
        from ..core.guard import swallowed
        swallowed("audio.volume", err)


def wanted() -> dict:
    """The loops that ought to be sounding now, and at what level."""
    return {cue: level for cue, level in _WANT.items() if level > 0.0}


def status() -> str:
    """What the speaker is doing, in words, for the options page."""
    if _STATE["backend"] is not None:
        return "playing"
    return _STATE["silent"] or "not asked yet"


def install(backend):
    """Put a backend in — a check's fake, usually — and hand back the last.

    Clears the counters and every loop, so what is heard afterwards is only
    what happened afterwards. `install(None)` goes back to looking for a real
    speaker the next time a cue is played.
    """
    was = _STATE["backend"]
    _STATE.update(backend=backend, tried=backend is not None,
                  silent="" if backend is not None else "not asked yet")
    for kept in (REQUESTED, PLAYED, _WANT, _TOLD):
        kept.clear()
    return was
