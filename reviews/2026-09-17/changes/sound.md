# Innovation 10: Soundscape

The game had no sound. It now has 28 cues in the game's own register: soft sines and filtered noise, nothing bright, no fanfare. Every sound is synthesised on first run with the standard library, cached beside the save and keyed by a hash of its recipe. No binary asset is added to the repo.

## New files

| File | Lines | What it holds |
|---|---|---|
| `seedfall/data/sounds.py` | 234 | The cue table: 28 recipes as frozen dataclasses (`Tone`, `Noise`, `Cue`). Pure data. |
| `seedfall/ui/synth.py` | 281 | The renderer (additive sines, exponential glides, two-pole low-passed noise, envelopes, seamless loops), the WAV writer and the recipe-hashed cache. No Qt, no numpy. |
| `seedfall/ui/audio.py` | 256 | The façade, and the only module that imports QtMultimedia (lazily). It provides `play`, `loop`, `set_level`, `volume`, `status`, `wanted` and `install` (the fake-backend injection point), plus the `REQUESTED`/`PLAYED` counters. |
| `seedfall/ui/soundmap.py` | 378 | Maps game events to cues. It reads state and never writes it. Its per-window memory lives on `win.sound_ear` and is never saved. It also holds the mute chip. |
| `seedfall/tests/test_audio.py` | 295 | Suite `audio`, 5 checks: the synthesiser (including the Nyquist limit per layer and the 2 MB cache budget), the cache, the façade and the layering. |
| `seedfall/tests/test_soundmap.py` | 344 | Suite `soundmap`, 9 checks: the right cue through the game's own doors. |

## The cues

| Cue | s | Character | Trigger |
|---|---|---|---|
| click | 0.04 | a dry 4 ms tick | any `widgets.button` pressed |
| swish | 0.34 | a band of noise opening upward | `go()` to a different screen (not the first, not within 0.8 s of an act) |
| good | 0.6 | a rising fifth, E5 to B5 | log burst holding a `good` entry (1.5 s gap per kind) |
| bad | 0.8 | a low tone falling a fifth | log burst holding a `bad` entry (never stands aside) |
| warn | 0.3 | a single mid pulse, C5 | log burst holding a `warn` entry |
| burn_low/mid/high | 2.0 loop | rumble, a band higher per throttle band (<0.34, <0.75, above) | held thruster on the main drive; swaps as the throttle crosses a band |
| burn_rcs | 2.0 loop | thin cold-gas hiss | held thruster with the main drive unarmed |
| proximity | 0.16 | a soft ping, A5 | collision guard threat, once a beat; repeats every 1–8 beats as time to contact falls |
| proximity_urgent | 0.18 | a double pip, D6 | the same at level `imminent` (she cannot be stopped) |
| berth | 1.2 | two small bells a fifth apart | `Conn.landed` turns true with the outcome `alongside` or `orbit` |
| jump | 1.5 | a long whoosh over a falling hum | `map_view._jump` after `jump_to` succeeds |
| volley_kinetic | 0.45 | a thump | your shots that flew, from a weapon with ammunition, flak or seeking |
| volley_energy | 0.5 | a crackle over a falling zap | your shots that flew, from a beam |
| volley_bio | 0.42 | a wet slap | your shots that flew, from a grown weapon |
| hit | 0.65 | a blow, then the hull's ring | an enemy shot that landed on you this turn |
| breach | 1.2 | three pulses over a low floor | the count of your destroyed layers rose this turn |
| struck | 2.4 | a slow fall to rest | `battle.result == "struck"` |
| survey | 1.0 | a ping and two fading echoes | `system_view._survey` succeeds |
| dig | 0.12 | a blade tick in grit | `dig_view._work` succeeds (one per stratum) |
| despatch | 1.4 | a soft bell with bell partials | `comms.unread` rose since the last HUD refresh |
| amb_red | 6.0 loop | a warm low drone beating against itself | an M, K or T star |
| amb_bright | 6.0 loop | an open fifth with air above it | any other star |
| amb_shoals | 6.0 loop | nebula hiss, one swell per loop | `region == "shoals"` |
| amb_hollow | 6.0 loop | nearly nothing, very low | `region == "hollow"`, or an X (black hole) |
| amb_cradle | 6.0 loop | a choral shimmer, A major, each voice detuned | `region == "cradle"` |
| bloom | 6.0 loop | a low inharmonic swell that breathes | level √(known burden ÷ Sovereign threshold 23) |

## Measured

- **First-run synthesis:** 0.88–0.93 s wall and 0.90 s CPU for 28 cues. The target was under 2 s, and the suite asserts it. A second run reuses all 28 in 4 ms.
- **Cache size:** 1.56 MB (1,556,196 bytes). One-shots are 22,050 Hz and loops 11,025 Hz, all 16-bit mono.
- **Qt's decoder:** every file loads into `QSoundEffect` as `Ready`, in 0.29 s for all 28. Loop count is `Infinite` (-2).
- **Loop seams:** the last and first samples straddle zero, within 0.003 of full scale. The high-frequency energy across the seam falls between the 4th and 88th percentile of the loop's own 20 ms windows.
- **One-shots:** every one starts and ends on exactly zero, and no cue exceeds its recipe peak (max 0.6 FS).
- **Cost on the beat:** `soundmap.hud` takes 3.7 µs; `soundmap.beat` takes 26 µs with a threat present, including `collision.scan` at 0.026 ms.

## Hunks in shared and other-owned files

- `sim/options.py`: 4 defaulted fields appended to `Options` (`sound`, `sound_volume` 70, `sound_effects`, `sound_ambience`) and 4 rows appended to `FIELDS`. The volume uses a new kind, `percent`.
- `ui/options_view.py`: `QSlider` import; `audio, soundmap` import; a Sound panel with a Speaker status row; `_set` plays a sample chime after a `sound*` change; a `percent` → `_slider` dispatch; a new `_slider` method (no tracking, so a drag does not rebuild the page under the hand).
- `tests/suites.py`: two rows appended, `audio` and `soundmap`.
- `tests/test_options.py`: a docstring bullet; `percent` added to the allowed kinds; one appended check, "each sound setting silences what it says".
- `data/help.py`: one topic appended, `sound` ("What you hear").
- `tests/tripwire_kin.py`: one row appended, `"sounds": ("audio",)`. The harness guard requires every module with a tuning constant to have a fast path. `data/sounds.LOW` is guarded: 0, ×2 and ÷2 each turn `audio` red. At ÷2 a loop asks for more than its file's Nyquist limit; at ×2 the cache passes its 2 MB budget. This was checked on a scratch copy of the package.
- `ui/window.py`: `from . import soundmap` on its own line; `soundmap.screen(self)` as the last line of `go()`; `soundmap.configure(self)` at the end of `apply_options()`.
- `ui/widgets.py`: `from . import soundmap`; `b.clicked.connect(soundmap.click)` in `button()`.
- `ui/log_panel.py`: `from . import soundmap` on its own line; `soundmap.logged(win, fresh)` after `_since`.
- `ui/flight_clock.py`: `from . import soundmap` on its own line; `soundmap.beat(win)` before `beat_refresh()` in `fly_beat`; `soundmap.burn(win)` in `start_burn` and in `end_burn`.
- `ui/hud.py`: `from . import soundmap` on its own line; the chip placed in the menu bar corner in `build` (with a 2-line comment); `soundmap.hud(win, waiting)` in `refresh`.
- `ui/battle_view.py`: `from . import soundmap` on its own line; `soundmap.battle(self.win, b)` at the top of `build`.
- `ui/map_view.py`, `ui/system_view.py`, `ui/dig_view.py`: `from . import soundmap` on its own line; one `soundmap.act(...)` after the act's `ok` check.

## Deviations from the spec

1. **The cue table lives in `data/sounds.py`,** a fourth file. Recipes are pure data. The renderer, cache and 28 recipes together would have passed 500 lines in `ui/synth.py`.
2. **Pitch follows throttle in three bands, not continuously.** `QSoundEffect` has no pitch control. The loop swaps at throttle 0.34 and 0.75, and a fourth loop covers the attitude jets.
3. **The Bloom follows `threat.known_bloom`, not the sector-wide `bloom_burden`.** Otherwise the speaker would give away what the fog hides from the chart, which is the leak `known_bloom` was written to close.
4. **The berth is read from state (`Conn.landed` plus the outcome) in the HUD hook,** not hooked into each of the three `commit` doors.
5. **The mute chip sits in the menu bar's right corner, not on the HUD row.** On the HUD it took 10 px from each name at 1,040 px and "Thule's Rise" elided. The menu bar is in-window on every platform (`setNativeMenuBar(False)`).
6. **The layer check is in `test_audio`, not `test_layers`,** to avoid editing another stream's file. The options efficacy check is in `test_options`, where "every setting does something" lives.
7. **Synthesis is synchronous on the first cue that would sound.** That happens once per install, takes about 0.9 s, and never happens with sound off.
8. **After a specific cue** (berth, jump, survey, dig, struck), the log's good and warn chimes and the swish stand aside for 0.8 s, so one act makes one sound. Bad news never stands aside.

## For the maps (not edited here)

- **INTERFACE.md, Layout:**
  - `data/sounds.py`: every sound as a recipe; the renderer lives in ui/synth.
  - `ui/synth.py`: the recipes rendered to WAV with the stdlib, cached beside the save by recipe hash.
  - `ui/audio.py`: the one door to the speaker; a no-op offscreen, without a device or with sound off; `install` takes a fake.
  - `ui/soundmap.py`: game events to cues, read from state; the mute chip.
  - Tests: `test_audio.py` (5 checks) and `test_soundmap.py` (9 checks).
- **IMPROVEMENTS.md:** close "No sound. Not one byte."
- **Known noise:** on a Mac with a multichannel output attached, Qt 6.4's CoreAudio backend prints "audio device has unrecognized channel" while it enumerates devices. The façade asks for the default output once and hands that device to all 28 effects, so the warning appears 12 times, once, when the speaker is first opened. Built without a device, each `QSoundEffect` re-enumerated, and it came to 124 lines.

## Full suite

`python3 -m seedfall.tests -j 4`: **219 suites · 1602 checks · 0 failed checks · 0 skipped · wall 282 s**, all green.
