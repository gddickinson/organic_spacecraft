"""Every sound in the game, made from nothing on first run, and kept.

`data/sounds.py` holds the recipes; this renders them into 16-bit mono WAV
with the standard library alone — `math`, `random`, `itertools`, `array`,
`wave` — and caches the files beside the save. No Qt: `ui/audio.py` is the
only module that knows a speaker exists. No numpy either, which is not a
game dependency; everything here is a list comprehension or an
`itertools.accumulate`, the two things CPython does quickly without it.

**The cache is keyed by the recipe.** Each file is named for its cue and a
hash of that cue's recipe and `SYNTH_VERSION`, so an edited number in
`data/sounds.py` regenerates that one cue, a renderer change (bump the
version) regenerates all of them, and a stale file is deleted rather than
left to accumulate. **Beside the save** — `save_path().parent / "sounds"` —
so a test run, which redirects the save, never writes into the player's
home.

**Seamless loops.** Tones in a loop are snapped to a whole number of cycles;
noise is rendered long and its tail crossfaded into its head at equal power;
the finished loop is then rotated to begin at an upward zero crossing, so
the last sample and the first straddle zero and the seam is one ordinary
step. The noise is seeded from the cue's id, so a recipe always renders to
the same bytes.
"""

from __future__ import annotations

import array
import hashlib
import math
import operator
import os
import random
import re
import sys
import time
import wave
from itertools import accumulate, repeat
from pathlib import Path

from ..data.sounds import CUES, Noise

#: Bump when the renderer changes what a recipe sounds like. Part of every
#: cue's hash, so every cached file is remade.
SYNTH_VERSION = 1

TAU = 2.0 * math.pi

#: A loop's noise is rendered this much longer and crossfaded back into its
#: head. A quarter of the loop: long enough that no seam is audible in the
#: hiss, short enough that the crossfaded span does not dominate the loop.
CROSSFADE = 0.25

#: Every one-shot fades in over 1 ms and out over 5 ms, so it starts and ends
#: on zero — a cue cut off mid-wave clicks, and a click is a cue of its own.
FADE_IN, FADE_OUT = 0.001, 0.005

#: What the last `ensure` did, for the checks and for anyone asking why the
#: first run took a second: files made, files reused, seconds spent.
LAST: dict = {}


# ── rendering ───────────────────────────────────────────────────────────────

def _snap(hz: float, seconds: float) -> float:
    """The nearest frequency that completes whole cycles in `seconds`."""
    return max(1, round(hz * seconds)) / seconds


def _tone(cue, t, m: int) -> list:
    """A tone's `m` samples: its partials summed, before any envelope."""
    rate, nyquist = cue.rate, cue.rate / 2.0
    sin = math.sin
    out = [0.0] * m
    if t.to and not cue.loop:
        # An exponential glide: each sample's phase step is the last one's
        # times a constant, so the pitch falls (or rises) evenly in cents.
        k = (t.to / t.hz) ** (1.0 / max(1, m))
        steps = accumulate(repeat(k, m - 1), operator.mul,
                           initial=TAU * t.hz / rate)
        phase = list(accumulate(steps, initial=0.0))[:m]
        for ratio, amp in t.partials:
            if max(t.hz, t.to) * ratio < nyquist:
                out = [o + amp * sin(ratio * p) for o, p in zip(out, phase)]
        return out
    for ratio, amp in t.partials:
        hz = t.hz * ratio
        if cue.loop:
            hz = _snap(hz, cue.seconds)
        if hz >= nyquist:
            continue                  # above what the file can hold: aliasing
        w = TAU * hz / rate
        out = [o + amp * sin(w * i) for i, o in enumerate(out)]
    return out


def _lowpass(x: list, hz: float, to: float, rate: int) -> list:
    """Two one-pole low-passes in series: 12 dB an octave, darker than one.

    A single pole leaves white noise only 6 dB down an octave above the
    corner, so a "140 Hz rumble" still hissed at a kilohertz.
    """
    if to:
        k = (to / hz) ** (1.0 / max(1, len(x)))
        corners = accumulate(repeat(k, len(x) - 1), operator.mul, initial=hz)
        coeff = [1.0 - math.exp(-TAU * f / rate) for f in corners]
        for _ in range(2):
            x = list(accumulate(zip(coeff, x),
                                lambda y, ax: y + ax[0] * (ax[1] - y),
                                initial=0.0))[1:]
        return x
    a = 1.0 - math.exp(-TAU * hz / rate)
    for _ in range(2):
        x = list(accumulate(x, lambda y, v: y + a * (v - y), initial=0.0))[1:]
    return x


def _noise(cue, nz, m: int, rng) -> list:
    """`m` samples of filtered noise — or of sparse grains, for a crackle."""
    uniform, chance = rng.uniform, rng.random
    if nz.grains:
        p = nz.grains / cue.rate
        x = [uniform(-1.0, 1.0) if chance() < p else 0.0 for _ in range(m)]
    else:
        x = [uniform(-1.0, 1.0) for _ in range(m)]
    y = _lowpass(x, nz.lp, nz.lp_to, cue.rate)
    if nz.hp:
        y = [a - b for a, b in zip(y, _lowpass(y, nz.hp, 0.0, cue.rate))]
    return y


#: A layer's release: the last eighth of it, never under 4 ms. A fixed 4 ms
#: cut off anything still ringing — measured, the struck-colours tone ended
#: 15 dB below its peak and was audibly chopped rather than finished.
RELEASE, RELEASE_MIN = 0.125, 0.004


def _envelope(m: int, rate: int, attack: float, decay: float) -> list:
    """Raised-cosine attack, exponential decay, and a release to zero."""
    k = math.exp(-1.0 / (decay * rate)) if decay > 0 else 1.0
    env = list(accumulate(repeat(k, m - 1), operator.mul, initial=1.0))
    rise = min(m, max(1, int(attack * rate)))
    for i in range(rise):
        env[i] *= 0.5 - 0.5 * math.cos(math.pi * i / rise)
    tail = min(m, max(int(RELEASE_MIN * rate), int(RELEASE * m), 1))
    for j in range(tail):
        env[m - 1 - j] *= 0.5 - 0.5 * math.cos(math.pi * j / tail)
    return env


def _scaled(wave_: list, amp: float) -> list:
    """A layer brought to peak `amp`, so the recipe's amps are its balance."""
    top = max((abs(v) for v in wave_), default=0.0)
    if top <= 0.0:
        return wave_
    g = amp / top
    return [v * g for v in wave_]


def _one_shot(cue, rng) -> list:
    n = int(round(cue.seconds * cue.rate))
    mix = [0.0] * n
    for layer in cue.layers:
        start = min(n, int(round(layer.at * cue.rate)))
        span = layer.length or (cue.seconds - layer.at)
        m = min(n - start, int(round(span * cue.rate)))
        if m <= 1:
            continue
        raw = (_noise(cue, layer, m, rng) if isinstance(layer, Noise)
               else _tone(cue, layer, m))
        env = _envelope(m, cue.rate, layer.attack, layer.decay)
        shaped = _scaled([r * e for r, e in zip(raw, env)], layer.amp)
        mix[start:start + m] = [a + b for a, b in
                                zip(mix[start:start + m], shaped)]
    return mix


def _loop(cue, rng) -> list:
    n = int(round(cue.seconds * cue.rate))
    fade = int(n * CROSSFADE)
    mix = [0.0] * n
    for layer in cue.layers:
        if isinstance(layer, Noise):
            y = _noise(cue, layer, n + fade, rng)
            # Equal power, because the two ends are uncorrelated noise: a
            # linear crossfade dips 3 dB in the middle, audible as a sag
            # once a loop.
            head = [y[i] * math.sin(0.5 * math.pi * i / fade)
                    + y[n + i] * math.cos(0.5 * math.pi * i / fade)
                    for i in range(fade)]
            y = head + y[fade:n]
        else:
            y = _tone(cue, layer, n)       # whole cycles: already seamless
        mix = [a + b for a, b in zip(mix, _scaled(y, layer.amp))]
    return mix


def render(cue) -> list:
    """The cue as floats in -1..1, normalised to its peak."""
    rng = random.Random(f"seedfall:sound:{cue.id}")
    mix = _loop(cue, rng) if cue.loop else _one_shot(cue, rng)
    n = len(mix)
    if cue.swell:
        cycles, depth = cue.swell
        mix = [v * (1.0 - depth * (0.5 - 0.5 * math.cos(TAU * cycles * i / n)))
               for i, v in enumerate(mix)]
    mix = _scaled(mix, cue.peak)
    if cue.loop:
        # The upward crossing with the smallest step across it, so the two
        # samples either side of the seam are as near zero as the loop has.
        ups = [i for i in range(1, n) if mix[i - 1] < 0.0 <= mix[i]]
        cut = min(ups, key=lambda i: mix[i] - mix[i - 1], default=0)
        return mix[cut:] + mix[:cut]
    rise, fall = int(FADE_IN * cue.rate), int(FADE_OUT * cue.rate)
    for i in range(rise):
        mix[i] *= i / rise
    for j in range(fall):
        mix[n - 1 - j] *= j / fall
    return mix


def write(path: Path, samples: list, rate: int) -> None:
    """16-bit mono PCM, written aside and renamed so a crash leaves nothing
    half-made where the cache would trust it."""
    pcm = array.array("h", [int(v * 32767.0) for v in samples])
    if sys.byteorder == "big":
        pcm.byteswap()                 # WAV is little-endian
    staged = path.with_suffix(".part")
    with wave.open(str(staged), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(pcm.tobytes())
    os.replace(staged, path)


# ── the cache ───────────────────────────────────────────────────────────────

def stamp(cue) -> str:
    """A hash of everything that decides how this cue sounds."""
    text = f"{SYNTH_VERSION}|{cue!r}"
    return hashlib.sha1(text.encode()).hexdigest()[:10]


def filename(cue) -> str:
    return f"{cue.id}-{stamp(cue)}.wav"


def cache_dir() -> Path:
    """Beside the save, wherever the save has been sent."""
    from ..core import save as save_mod
    return save_mod.save_path().parent / "sounds"


def ensure(folder: Path | None = None, cues=CUES) -> dict:
    """Every cue's file, made if it is missing or stale. `{id: Path}`.

    A file is trusted when its name carries the recipe's current hash and it
    is longer than a WAV header; anything else under a cue's name is an old
    recipe and is removed.
    """
    started = time.perf_counter()
    folder = Path(folder) if folder is not None else cache_dir()
    folder.mkdir(parents=True, exist_ok=True)
    made, kept, files = 0, 0, {}
    for cue in cues:
        path = folder / filename(cue)
        if path.is_file() and path.stat().st_size > 44:
            kept += 1
        else:
            write(path, render(cue), cue.rate)
            made += 1
        files[cue.id] = path
        mine = re.compile(rf"{re.escape(cue.id)}-[0-9a-f]{{10}}\.(wav|part)")
        for other in folder.iterdir():
            if other != path and mine.fullmatch(other.name):
                other.unlink(missing_ok=True)
    LAST.update(made=made, kept=kept, folder=str(folder),
                seconds=round(time.perf_counter() - started, 3),
                bytes=sum(p.stat().st_size for p in files.values()))
    return files
