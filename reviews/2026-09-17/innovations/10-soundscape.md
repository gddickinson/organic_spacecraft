# Innovation 10 — Soundscape (presentation)

## Why

"No sound. Not one byte." That has been open on the backlog since the flight
deck campaign. The backlog itself notes that four cues would carry more than
any HUD addition:
- a thruster loop on the held burn;
- a proximity tone from the collision guard;
- a chime when a berth is secured;
- a distinct bad-news alert.

QtMultimedia is available in the environment (PyQt6 6.4.2).

## What the player gets

A quiet, organic soundscape in the game's register: dark-field microscopy
rendered as sound. Soft sine and filtered-noise tones, no fanfare.

- **Interface:** a subtle click on buttons and a soft swish on screen changes.
- **The log:** one chime per kind. Good is a rising two-note, bad a low
  falling tone, warn a single mid pulse. Each is rate-limited so a burst of
  entries plays once.
- **Flying:**
  - a burn loop while a burn is held (`flight_clock.start_burn`/`end_burn`),
    with pitch following throttle;
  - a proximity tone from the collision guard, whose repetition rate rises as
    time-to-contact falls;
  - a chime when a berth is secured;
  - a jump whoosh.
- **Combat:** a volley (per weapon family: a thump for kinetic, a crackle for
  energy, a wet slap for biological), a hit, a breach alarm, and a struck
  colours tone.
- **Work:** a survey ping; a dig tick per stratum; a despatch arriving (a soft
  bell).
- **Ambience:**
  - one drone per system type: dim red star, bright star, nebula hiss for the
    Shoals, near-silence for the Hollow, choral shimmer for the Cradle. It is
    keyed off `System.star` and `getattr(system, "region", "verge")`, so it
    works before and after the Far Reaches merge.
  - **The Bloom:** a low organic swell whose level follows the sector burden.
    You can *hear* things getting worse.

## Design

### Synthesis

All sound is generated procedurally at first run, with the standard library
only (`wave`, `math`, `array`, `struct`; numpy is not a game dependency).
- Use additive sines, simple envelopes (attack/decay), filtered noise (a
  one-pole low-pass on white noise), and seamless loops (a whole number of
  cycles, crossfaded).
- Output goes to a cache dir beside the save (`save_path().parent /
  "sounds"`, so tests stay redirected), versioned by a hash of the synth
  parameters so an edit regenerates.
- **No binary assets in the repo.**

### The façade

`ui/audio.py`, the only module that imports QtMultimedia:
- `play(cue)`, `loop(cue, on: bool)`, `set_level(ambience_key, 0..1)`,
  `volume(master, sfx, ambience)`.
- It **does nothing** when:
  - QtMultimedia can't import;
  - the platform is `offscreen`/`minimal`;
  - `options.sound` is off;
  - no audio device exists.
- It never raises into a slot. Every call is wrapped.

### Cue mapping

`ui/soundmap.py` maps game events to cues. It **reads state; the sim never
imports audio.**

The window already has the hooks:
- `_refresh_log` sees new log entries with their kind; stream B makes it
  incremental with a "new entries" hook, so play the chime there;
- `go()` is a screen change;
- `flight_clock` is burns and the collision guard;
- `battle_view` sees volleys and hits through the battle's log;
- `berthing` securing sets state on the flight.

Where an act leaves no state, reuse the `tutorial_watch.deed` pattern: a
transient per-game list of recent deeds the UI drains. Add it only if needed.

### Options

`data`/`sim/options.Options` gains `sound: bool = True`,
`sound_volume: int = 70`, `sound_ambience: bool = True`, and
`sound_effects: bool = True`. The options suite demands that "every setting
does something": give each an efficacy check through the façade's counters
(cues requested vs played).

### Cost

Synthesis at first run in under 2 s for about 25 cues. Playback has no work
on the flight beat beyond a dict lookup. Loops use `setLoopCount(Infinite)`.

## UI

Options gains a Sound section (master volume slider, effects and ambience
toggles). The HUD may show a small speaker chip that mutes on click.

## Tests (new suite `test_audio`)

- The synthesiser writes valid WAV files (header, sample rate, duration within
  ±5% of spec, no clipping above full scale, loops that start and end at zero
  crossings).
- The cache is reused, and regenerated when the parameters change.
- The façade is a no-op offscreen and never raises. With a fake backend
  injected, the right cues fire for:
  - a log burst of good, bad and warn entries (rate-limited to one each);
  - a held burn (the loop starts and stops);
  - a screen change;
  - a combat volley and hit;
  - a despatch.
- The Bloom ambience level rises with the burden.
- Options toggles mute their categories (efficacy).
- No module outside `ui/` imports audio (the layer suite).
