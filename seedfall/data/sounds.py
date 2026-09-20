"""Every sound in the game, as a recipe. Pure data: `ui/synth.py` renders it.

The register is the rest of the game's: dark-field microscopy, rendered as
sound. Soft sines and filtered noise, nothing bright, no fanfare. A cue is a
few layers — a `Tone` (a sine and its overtones, perhaps gliding) or a
`Noise` (white noise through a low-pass, perhaps less another for a band) —
each with its own attack and exponential decay.

**No sound ships in the repository.** Every file is made from these recipes
on first run and cached beside the save, stamped with a hash of the recipe,
so editing a number here regenerates exactly that cue and nothing else.

Loops (`loop=True`) are held to two rules the renderer enforces: every tone
completes a whole number of cycles in the loop (its frequency is snapped to
a multiple of `1/seconds`), and noise is crossfaded tail-into-head. `swell`
cycles are whole numbers for the same reason. A loop with a half-cycle in it
clicks once per repeat, which over an hour of ambience is the only thing a
player would hear.

Ambience and the burn loops run at 11,025 Hz: the drones are all under
3 kHz, and halving the rate halves both the cache and the first-run time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tone:
    """A sine and its overtones. `partials` are (ratio, amplitude) pairs."""

    hz: float
    to: float = 0.0            # glides here, exponentially; 0 holds the pitch
    amp: float = 1.0
    at: float = 0.0            # seconds into the cue it starts
    length: float = 0.0        # seconds it lasts; 0 runs to the end
    attack: float = 0.004      # seconds, raised-cosine
    decay: float = 0.0         # exponential time constant, s; 0 holds
    partials: tuple = ((1.0, 1.0),)


@dataclass(frozen=True)
class Noise:
    """White noise through a low-pass, and optionally less a slower one."""

    lp: float                  # corner, Hz
    lp_to: float = 0.0         # the corner glides here; 0 holds it
    hp: float = 0.0            # subtract a low-pass at this corner: a band
    amp: float = 1.0
    at: float = 0.0
    length: float = 0.0
    attack: float = 0.002
    decay: float = 0.0
    grains: float = 0.0        # > 0: sparse impulses a second, not a hiss


@dataclass(frozen=True)
class Cue:
    id: str
    group: str                 # "effects" or "ambience": its switch
    seconds: float             # its length; a loop's period
    peak: float                # normalised peak, as a fraction of full scale
    layers: tuple
    what: str                  # its character, in words
    loop: bool = False
    rate: int = 22050
    swell: tuple = ()          # (whole cycles over the cue, depth 0..1)


#: The loop rate. See the module note.
LOW = 11025

_CHIME = ((1.0, 1.0), (2.0, 0.18), (3.0, 0.06))
_BELL = ((1.0, 1.0), (2.0, 0.25), (2.76, 0.18), (5.4, 0.06))

CUES: tuple = (
    # ── the interface ────────────────────────────────────────────────────
    Cue("click", "effects", 0.04, 0.16, (
        Noise(4000, hp=800, amp=0.6, attack=0.0005, decay=0.004),
        Tone(2100, amp=0.5, attack=0.0005, decay=0.006)),
        "a dry tick, 4 ms, a little brighter than the rest of the game"),
    Cue("swish", "effects", 0.34, 0.2, (
        Noise(500, lp_to=2600, hp=150, attack=0.12, decay=0.1),),
        "a band of noise opening upward — a slide being changed"),

    # ── the log: one per kind ────────────────────────────────────────────
    Cue("good", "effects", 0.6, 0.34, (
        Tone(659.3, length=0.25, attack=0.006, decay=0.14, partials=_CHIME),
        Tone(987.8, at=0.11, attack=0.006, decay=0.22, partials=_CHIME)),
        "a rising fifth, E to B, two soft notes"),
    Cue("bad", "effects", 0.8, 0.46, (
        Tone(233.1, to=155.6, attack=0.015, decay=0.3,
             partials=((1.0, 1.0), (2.0, 0.45), (3.0, 0.2), (4.2, 0.05))),
        Noise(300, amp=0.2, attack=0.01, decay=0.12)),
        "a low tone falling a fifth, with a breath under it"),
    Cue("warn", "effects", 0.3, 0.3, (
        Tone(523.3, attack=0.006, decay=0.08,
             partials=((1.0, 1.0), (2.0, 0.25))),),
        "a single mid pulse, C5"),

    # ── flying ───────────────────────────────────────────────────────────
    # A held burn, in three throttle bands and the cold-gas thrusters.
    # QSoundEffect cannot change pitch, so "pitch follows the throttle"
    # is three loops a band apart, swapped as the throttle crosses a band.
    Cue("burn_low", "effects", 2.0, 0.34, (
        Noise(160), Noise(900, hp=300, amp=0.25),
        Tone(44, amp=0.35, partials=((1.0, 1.0), (2.0, 0.4)))),
        "a low rumble under a third throttle", loop=True, rate=LOW,
        swell=(4, 0.12)),
    Cue("burn_mid", "effects", 2.0, 0.4, (
        Noise(280), Noise(1400, hp=400, amp=0.3),
        Tone(58, amp=0.35, partials=((1.0, 1.0), (2.0, 0.4)))),
        "the rumble at half throttle, a fourth higher", loop=True, rate=LOW,
        swell=(6, 0.12)),
    Cue("burn_high", "effects", 2.0, 0.46, (
        Noise(460), Noise(2200, hp=600, amp=0.35),
        Tone(74, amp=0.35, partials=((1.0, 1.0), (2.0, 0.4)))),
        "the drive near full, brighter and faster-breathing", loop=True,
        rate=LOW, swell=(8, 0.12)),
    Cue("burn_rcs", "effects", 2.0, 0.26, (
        Noise(3200, hp=900), Noise(400, amp=0.2)),
        "a thin hiss: the attitude jets, not the drive", loop=True,
        rate=LOW, swell=(3, 0.2)),
    Cue("proximity", "effects", 0.16, 0.3, (
        Tone(880, attack=0.004, decay=0.045,
             partials=((1.0, 1.0), (2.0, 0.15))),),
        "a soft ping, A5; it repeats faster as contact nears"),
    Cue("proximity_urgent", "effects", 0.18, 0.34, (
        Tone(1174.7, length=0.07, attack=0.003, decay=0.03),
        Tone(1174.7, at=0.08, attack=0.003, decay=0.035)),
        "a double pip, D6: she can no longer be stopped"),
    Cue("berth", "effects", 1.2, 0.36, (
        Tone(784, attack=0.01, decay=0.35, partials=_BELL[:3]),
        Tone(1174.7, at=0.14, attack=0.01, decay=0.45,
             partials=((1.0, 1.0), (2.76, 0.1)))),
        "two small bells a fifth apart: made fast"),
    # **A crash had no sound at all.** Every gun in the game rings the hull
    # and flying one into a Fleet Hub at 55 m/s did not — which is the same
    # hole the pictures had: the loudest thing that can happen on the flight
    # deck was the quietest thing in the interface.
    Cue("impact", "effects", 1.6, 0.72, (
        Noise(2600, lp_to=240, hp=40, amp=0.9, attack=0.001, decay=0.5),
        Tone(34, to=22, amp=1.0, attack=0.002, decay=0.9,
             partials=((1.0, 1.0), (2.0, 0.4), (3.3, 0.18))),
        Tone(146.8, to=104, amp=0.45, at=0.04, attack=0.004, decay=0.7,
             partials=((1.0, 1.0), (2.41, 0.35), (4.7, 0.12)))),
        "a crunch and a long structural groan under it: the frames took it"),
    Cue("graze", "effects", 0.7, 0.34, (
        Noise(4200, lp_to=1400, hp=700, amp=0.8, attack=0.004, decay=0.28,
              grains=900),
        Tone(220, to=186, amp=0.3, attack=0.01, decay=0.24)),
        "a grating scrape along the skin, and nothing worse"),
    Cue("jump", "effects", 1.5, 0.45, (
        Noise(250, lp_to=3200, hp=80, attack=0.55, decay=0.35),
        Tone(110, to=36, amp=0.5, attack=0.3, decay=0.5)),
        "a long whoosh opening upward over a falling hum"),

    # ── combat ───────────────────────────────────────────────────────────
    Cue("volley_kinetic", "effects", 0.45, 0.6, (
        Tone(62, to=38, attack=0.002, decay=0.13,
             partials=((1.0, 1.0), (2.0, 0.45), (3.0, 0.2))),
        Noise(500, amp=0.5, attack=0.001, decay=0.03)),
        "a thump: something thrown"),
    Cue("volley_energy", "effects", 0.5, 0.4, (
        Noise(6000, grains=2500, attack=0.001, decay=0.12),
        Tone(1400, to=420, amp=0.6, attack=0.002, decay=0.09)),
        "a crackle over a falling zap: energy down a line"),
    Cue("volley_bio", "effects", 0.42, 0.5, (
        Noise(1400, hp=200, attack=0.001, decay=0.05),
        Noise(700, amp=0.5, at=0.03, attack=0.004, decay=0.07),
        Tone(180, to=95, amp=0.6, attack=0.002, decay=0.08,
             partials=((1.0, 1.0), (2.3, 0.3)))),
        "a wet slap: something grown, letting go"),
    Cue("hit", "effects", 0.65, 0.6, (
        Noise(1600, hp=60, attack=0.001, decay=0.12),
        Tone(48, amp=0.8, attack=0.002, decay=0.3,
             partials=((1.0, 1.0), (2.0, 0.5), (3.0, 0.25))),
        Tone(290, to=250, amp=0.35, attack=0.002, decay=0.18,
             partials=((1.0, 1.0), (2.71, 0.4)))),
        "a blow and the hull's own ring after it"),
    Cue("breach", "effects", 1.2, 0.45, (
        Tone(392, length=0.3, attack=0.03, decay=0.14,
             partials=((1.0, 1.0), (2.0, 0.35), (3.0, 0.12))),
        Tone(392, at=0.36, length=0.3, attack=0.03, decay=0.14,
             partials=((1.0, 1.0), (2.0, 0.35), (3.0, 0.12))),
        Tone(392, at=0.72, length=0.3, attack=0.03, decay=0.14,
             partials=((1.0, 1.0), (2.0, 0.35), (3.0, 0.12))),
        Tone(196, amp=0.4, attack=0.2, decay=0.6)),
        "three pulses over a low floor: a layer has gone"),
    Cue("struck", "effects", 2.4, 0.35, (
        Tone(523.3, to=392, attack=0.08, decay=0.7,
             partials=((1.0, 1.0), (2.0, 0.2))),
        Tone(329.6, amp=0.6, at=0.25, attack=0.2, decay=0.9)),
        "a slow fall to rest: they have struck their colours"),

    # ── work ─────────────────────────────────────────────────────────────
    Cue("survey", "effects", 1.0, 0.32, (
        Tone(1318.5, attack=0.003, decay=0.22,
             partials=((1.0, 1.0), (2.0, 0.08))),
        Tone(1318.5, amp=0.28, at=0.38, attack=0.003, decay=0.2),
        Tone(1318.5, amp=0.1, at=0.7, attack=0.003, decay=0.18)),
        "a ping and two fading echoes, E6"),
    Cue("dig", "effects", 0.12, 0.34, (
        Noise(2600, hp=300, attack=0.0005, decay=0.012),
        Tone(340, amp=0.6, attack=0.001, decay=0.025,
             partials=((1.0, 1.0), (2.4, 0.3)))),
        "a tick of a blade in grit"),
    Cue("despatch", "effects", 1.4, 0.3, (
        Tone(1046.5, attack=0.004, decay=0.5, partials=_BELL),),
        "a soft bell, C6, with a bell's inharmonic overtones"),

    # ── ambience: one drone per kind of system, and the Bloom ────────────
    Cue("amb_red", "ambience", 6.0, 0.2, (
        Tone(55, partials=((1.0, 1.0), (2.0, 0.45), (3.0, 0.2),
                           (4.0, 0.1))),
        Tone(55.33, amp=0.6), Noise(140, amp=0.35)),
        "a dim red star: a warm low drone beating slowly against itself",
        loop=True, rate=LOW, swell=(1, 0.25)),
    Cue("amb_bright", "ambience", 6.0, 0.16, (
        Tone(110, amp=0.8, partials=((1.0, 1.0), (1.5, 0.5), (2.0, 0.4),
                                     (3.0, 0.2))),
        Tone(220.5, amp=0.35), Noise(3000, hp=1200, amp=0.12)),
        "a bright star: an open fifth with air over it",
        loop=True, rate=LOW, swell=(2, 0.2)),
    Cue("amb_shoals", "ambience", 6.0, 0.18, (
        Noise(2200, hp=250), Noise(500, amp=0.4), Tone(73.33, amp=0.2)),
        "the Shoals: nebula hiss, rising and falling once a loop",
        loop=True, rate=LOW, swell=(1, 0.45)),
    Cue("amb_hollow", "ambience", 6.0, 0.05, (
        Noise(70), Tone(36.67, amp=0.4, partials=((1.0, 1.0), (3.0, 0.3)))),
        "the Hollow: very nearly nothing, and very low",
        loop=True, rate=LOW, swell=(1, 0.5)),
    Cue("amb_cradle", "ambience", 6.0, 0.16, (
        Tone(220, amp=0.8, partials=((1.0, 1.0), (2.0, 0.15))),
        Tone(220.33, amp=0.5), Tone(277.2, amp=0.6),
        Tone(277.7, amp=0.4), Tone(329.6, amp=0.6), Tone(330.1, amp=0.4),
        Tone(440, amp=0.3), Noise(4000, hp=2000, amp=0.05)),
        "the Cradle: a choral shimmer, A major, every voice doubled "
        "a hair out of tune", loop=True, rate=LOW, swell=(2, 0.25)),
    Cue("bloom", "ambience", 6.0, 0.36, (
        Tone(41, partials=((1.0, 1.0), (1.618, 0.35), (2.4, 0.15),
                           (3.2, 0.25), (4.8, 0.12))),
        Tone(41.5, amp=0.7), Noise(110, amp=0.6),
        Noise(700, hp=250, amp=0.15)),
        "the Bloom: a low inharmonic swell that breathes once a loop",
        loop=True, rate=LOW, swell=(1, 0.7)),
    # ── the living sky (innovation 7, `ui/sky_strip.sound`) ─────────────
    Cue("flare", "effects", 1.1, 0.34, (
        Noise(3200, lp_to=900, hp=500, amp=0.5, attack=0.02, decay=0.35),
        Tone(620, to=880, amp=0.5, attack=0.03, decay=0.3, partials=_CHIME),
        Tone(930, to=1320, amp=0.25, at=0.18, attack=0.02, decay=0.25)),
        "a flare warning: a crackle opening upward over a rising pair"),
    Cue("nova", "effects", 3.0, 0.4, (
        Tone(55, to=41, amp=0.9, attack=0.4, decay=1.4,
             partials=((1.0, 1.0), (2.0, 0.3), (3.0, 0.15))),
        Noise(1800, lp_to=200, amp=0.5, attack=0.8, decay=1.0),
        Tone(440, amp=0.2, at=0.6, attack=0.5, decay=1.2, partials=_BELL)),
        "the nova: a slow deep swell, a wash of light, one far bell"),
)

CUES_BY_ID = {c.id: c for c in CUES}
