# Session log, part 30 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span undated to undated; undated entries keep their original place.

## Two more of the seven, and they were two different defects (#132)

`gates.TOLL_REFUSED_BELOW` (-40) decides whether a ring opens for you at all.
`approach.LOSING` (-30) decides when a power is beaten badly enough by a rival
to want it said out loud. Both swept green at double and half; the reasons were
not the same.

**The toll was tautologically checked**, like the two before it:

    test_weave.py:208   game.rep[far.faction] = TOLL_REFUSED_BELOW - 5

Double the bar to -80 and the standing became -85: still under, still refused,
still green.

**`LOSING` was held by nothing at all.** No check in the suite referenced it —
the third of the three states `tripwire.py` names, and the one it was written
for: real, load-bearing, and unpinned.

Measured through the doors before writing either. `gates.toll` opens at -40.0
and is shut at -40.5, a strict `<`. `approach.reasons` offers nothing at
relation -29 and a denunciation at -30, so that gate is `<=` — the boundary is
*inside* the losing side, and a bracket written to the wrong side of it would
have passed while testing nothing.

Both bracketed with absolute values a point either side, and both now go red at
double, half **and a 1.5-point nudge**:

    TOLL_REFUSED_BELOW   ring open at -39, shut at -41
    LOSING               silent at -29, denouncing at -30, and it names who

Four of seven done. Three remain: `industry.ILLICIT_COST`, `robots3d.DRIVE_Z`,
`voice.COLD_AT`.

### Wrong turn worth keeping

- **The two constants looked identical from the sweep and were not.** Both
  reported "green at double and half", which reads as one finding with one
  fix. The toll needed an existing check de-tautologised; `LOSING` needed a
  check that did not exist. Treating the sweep's verdict as a diagnosis rather
  than a symptom would have produced one edit and left the second constant
  exactly as unprotected as before.

## Two more, and the worst of the four defect shapes so far (#132)

`industry.ILLICIT_COST` (-18) is what teaching somebody an unlicensed process
costs you with everybody else. `voice.COLD_AT` (-18) decides the mood a speaker
answers you in. Both swept green at double and half, and again for different
reasons.

**`COLD_AT` was held by nothing** — no check referenced it or `WARM_AT`.
Measured through `voice.mood_for`, both gates are inclusive: greet at -17, cold
at exactly -18, warm at exactly +18. Bracketed absolutely, in `test_voices`.

**`ILLICIT_COST` was worse than tautological: its check never ran.** The
assertion was

    if got is not None:
        ...
        assert all(h <= RIVAL_COST + ILLICIT_COST + 1e-9 for h in hit)

and `best_buyer` returns `None` here, because the seed licence is the dearest
in the tree — measured, all four powers answer *"cannot raise 23,645–31,280,
the treasury will not stand it"*. So the branch was skipped every run, **and
the check still returned a summary reading "an illicit licence -18 on top"**.
It narrated a measurement it had not made.

Funded the purses (500,000 each) so the case is reached, asserted the buyer
exists rather than hoping, and replaced the derived bound with the absolute
figures the flight actually produces:

    licensee            +14
    each rival, licit    -6
    each rival, illicit -24     (the -18 is the difference)

Both now go red at double, half and a 1.5-point nudge.

**Six of seven done.** `robots3d.DRIVE_Z` remains and is the genuine odd one
out: it positions a drone's thruster ring in `data/robots3d.py` and nothing
outside the mesh reads it. Measured: 3 of 20 machine looks carry a ring —
`lamplighter`, `rigger`, `verger` — the other 17 get legs. It needs a picture
check, not an arithmetic one.

### Wrong turns worth keeping

- **I wrote a vacuous assertion while removing one.** The first draft of the
  industry fix ended with `assert all(...) is False or True`, which is `True`
  whatever the generator says — the exact defect the cycle was for. Caught on
  re-reading before running.
- **A skipped branch that still reports is worse than a tautology**, and it is
  invisible in a green run: the tautology at least executes. Any `if x is not
  None:` wrapping the substance of a check deserves an `assert x is not None`
  above it.

## The last of the seven: a constant only a picture could pin (#132 closed)

`robots3d.DRIVE_Z = -0.42` places a drone's thruster ring, and nothing outside
the mesh reads it — an arithmetic assertion would only restate it.

**It reaches the picture, and that was measured rather than assumed.** Doubling
it to -0.84 and re-rendering each machine's silhouette:

    lamplighter   50.0% of its silhouette survives
    verger        61.0%
    rigger        80.5%
    loader       100.0%  — it walks, and is untouched

So the offset is visible, and exactly on the machines that carry a ring.

The check asserts the geometry with **absolute** numbers: all three flyers have
12 vertices at -0.47 and 12 at -0.37 (the tube, 0.1 deep, centred on the
offset), nothing below -0.60, the lowest geometry between -0.60 and -0.50 so
the ring's own boxes are the bottom of the machine, and the head above it — a
ring on top would satisfy a check that only asked whether one existed. No
walker has either plane. Measured across all 20 looks: 3 fly, 17 walk.

Red at -0.84, at -0.21, at a 0.05 nudge to -0.47, and at +0.42 (flipped above
the machine).

### Seven constants, four defect shapes

All seven reported identically as "green at double and half". The causes were
not the same, and treating the sweep's verdict as a diagnosis would have fixed
one and left the rest:

- **Tautologically checked** (4) — the check read the constant under test.
- **Held by nothing** (2) — `approach.LOSING`, `voice.COLD_AT`: no reference.
- **Never executed** (1) — `industry.ILLICIT_COST` sat under `if got is not
  None:` where `best_buyer` always returned None, and the check still returned
  a summary quoting the constant.
- **Cosmetic-looking but visible** (1) — `DRIVE_Z`, which needed a rendered
  measurement to know it mattered at all.

## The first honest full sweep since #116, and what it found

With the task list empty, the well-founded work was the sweep itself: #131 made
`tripwire` stop counting a timeout as proof, so its verdicts mean something
again — and nobody had run it over the whole set since.

**Rate, measured: 9 survivors in the first 18 constants — 50%.** Alphabetical,
so `approaches`, `bloom`, `charts`, `diplomacy`:

    approaches.QUIET_DAYS  approaches.ODDS_PER_DAY  bloom.MAX_RESIST
    bloom.RESIST_PER_HIT   bloom.RESIST_DECAY       bloom.HEART_HP
    charts.KNOWN_WORTH     diplomacy.COURTSHIP_KNEE diplomacy.COURTSHIP_FLOOR

The sweep also costs about **42 seconds a constant** now, so a full pass is
roughly five hours. Both facts are filed as #133 — the honest reading is that
these were never caught by their own module's suite but by the *broad* stage,
which cost 36 seconds when written and takes about 25 minutes since
`MAX_STEP` became 1. **#116 destroyed the diffuse coverage and #131 made it
visible.** Writing ~200 checks is not the answer; narrowing the broad stage to
the suites that could plausibly be affected is the fix worth designing.

### One landed: the length of the game's climax

`data/bloom.HEART_HP = 2600` is the Bloom Heart's hit points — the thing a
captain has to destroy to win. It *was* checked, by `test_play`, which the
sweep cannot reach because `play` is in `SLOW`. But the assertion was
`strikes > 1` inside a `while strikes < 40` loop, and measured with a
battleship:

    HEART_HP 1300 ->  9 passes      2600 -> 19 passes      5200 -> 37 passes

so halving and doubling both sailed through, and doubling cleared the loop's
own cap by three. Bracketed at 14..26 against the measured 19. Red at half and
at double; green at 3,000, which is deliberate — this is a pacing number and
"several visits, not one and not forty" is the design intent, unlike the
threshold constants in #132 where a single point matters.

### Wrong turns worth keeping

- **My first hand-verification was worthless and looked fine.** Checking
  whether `HEART_HP` was really unpinned, I rewrote `sim/bloom.py` — the
  constant lives in `data/bloom.py`. The mutation never applied, the suite
  passed, and that would have read as "the sweep is wrong, nothing to do here".
  The `assert n != s` in the mutation script is what caught it.
- **The sweep script restores atomically now**, keeping the original in a
  sibling temp file and putting it back with `os.replace`. Killing this run
  mid-sweep left the tree clean, where the `write_text` approach two cycles ago
  truncated `data/industry.py` to nothing — it truncates before it writes, and
  a signal in that window loses the file.

## The sweep's broad stage can finish again, so it votes again (#133)

The task proposed narrowing the broad stage to the suites that could plausibly
be affected, computed from the import graph. **Measured, that does not work:**
median fan-in is **163 of 172** test modules, because `core/state` is a hub
every test reaches, so transitive reachability is nearly universal. It would
have bought 163 suites instead of 155.

What does work came from timing every suite individually:

    155 suites, 761 s in total, and wildly lopsided
    politics 145 s (19% of everything)   byhand 52   provisional 34   orders 29

    keep <= 1.0 s   55 suites,  27 s        keep <= 2.0 s   81 suites,  65 s
    keep <= 1.5 s   71 suites,  47 s        keep <= 3.0 s  101 suites, 114 s

`SLOW` — the exclusion list — was hand-kept and calibrated before
`core/clock.MAX_STEP` became 1. None of `politics`, `byhand`, `provisional` or
`orders` was in it, and all four had grown past half a minute. Set from the
measurement at a 1.5 s cut: **71 suites, 29 s of wall clock, inside `LIMIT`**.

Proved it recovers coverage on three constants that survived last cycle's
sweep — `bloom.MAX_RESIST`, `charts.KNOWN_WORTH`, `diplomacy.COURTSHIP_KNEE`
are all **CAUGHT** now.

Also closed a hazard the change created: `_run` inherited `SEEDFALL_SAVE`, so a
sweep child would have written over the save of the run that spawned it. It
gets its own now.

### Wrong turns worth keeping

- **I wrote the same string bug twice.** Emitting a set literal as
  `" ".join(repr(n) ...)` and wrapping it with `textwrap.fill` produced
  `'bloombridge'` — adjacent string literals concatenate in Python. It landed
  in `SLOW` first and then, unbelievably, in the guard's own table. Caught both
  times by reconciling counts against the measurement rather than by reading
  the file; the second version asserts the parsed literal equals the measured
  set.
- **The obvious check was not viable and measuring it said so.** Asserting
  `completes(SUITES)` inside a suite run means launching 71 child suites on an
  already-loaded machine, and it exceeded `LIMIT` — it would have been timing
  the hardware, not the design. The check is static instead: every suite
  measured over budget is named, and must be excluded.
- **The change broke an existing guard, and the guard was the thing that was
  wrong.** "A fast path may not name a suite in `SLOW`" was right while `SLOW`
  held seventeen mostly-window-needing suites. With the two stages doing
  different jobs it is not: the fast path is *the suite that knows this
  module*, and running one expensive suite for the one constant it speaks for
  is exactly its purpose. 118 fast paths now name an excluded suite and every
  one is the right suite for its module.

## Opening fire from the pilot's seat (#135)

Asked for manual flight at any time, off the clock, with undocking, leaving
orbit, and combat in live control. **Measured first, and most of it already
existed** — `sim/freeflight` (#109):

    freeflight.begin(game)   no target, no clearance; the gate is reaction mass
    200 conn ticks           advanced game.day by 0 — it does not run on the clock
    hours charged once       on berthing.commit, as conn.elapsed / DAY_SECONDS
    hand_over(...)           becomes an approach carrying the way already on
    leaving a dock/orbit     derived from position, so flying away *is* leaving
    the conn already offers  Break off · Make orbit · Close and berth ·
                             New approach… · Secure · Run clock / Stop clock

**The gap was the guns.** Measured on `sim/conn.py`: "weapon" appeared 0 times
and "hostile" 0. No door from live flight into a fight.

`sim/engage.py` is that door and resolves nothing — `combat` still builds the
`Battle`, `firing` still says which mounts can speak, `encounters.make_enemy`
still says what a hull of a given flag carries.

**What the range means, and why it is `conn.pos`.** Asked through `sim/track`,
every contact sharing a body with the hull reads as **0 km** away and every
other body as hundreds of millions — measured on seed "engage", the nearest was
429,631,101 km. There is no local geometry for a second hull, so "fire at
whatever is out there" has no honest answer. What there is is how far the hull
has flown from where it let go, which is the range to anything left behind at
the quay. Against `freeflight.far_km()` of 10,000 and five bands, that is a
2,000 km step each:

    alongside   Contact      5,000 km   Medium      9,000 km   Extreme
    3,000 km    Close        7,000 km   Long

So the flying earns the range: 200 km opens at Contact, 120 units apart;
9,000 km opens at Extreme, 1,080 units apart. Same seed, same hull, same dice.

### Wrong turns worth keeping

- **I nearly filed a defect I had invented.** Flying 5,000 km from a quay
  leaves `ship.docked_at` set, which looked like two doors disagreeing — until
  I checked what writes it. `Ship.docked_at` holds a **system id** for fleet
  hulls laid up in a yard (`consorts`, `shipyard`, `yard_view`); the player's
  berth is `anchorage.docked_at`, which is **derived from position**. I had set
  the field to a quay id, a value the game never puts there. No defect.
- **A "the messages differ" assertion cannot tell refusals apart when each
  carries the contact's name.** Deleting the world clause from `may_engage`
  left every check green, because "Loam Fall I is not a hull" and "Fleet Hub is
  not a hull" are different strings. The check asserts the *kind* of refusal
  now — a world is refused for being a world.

## A conn engagement fought alone (#136, part)

**A defect in what shipped last cycle, found by measuring rather than reading.**
`ui/battle_view.begin` passes `fleet=consorts.escorts_of(g)` when an encounter
starts a fight. `engage.open_fire` did not. Measured with one consort aboard:

    consorts.escorts_of(game)          ['Consort']
    consorts in a conn engagement      []

So the same captain, against the same enemy, fought two-to-one when jumped and
alone when they picked the fight themselves. Who started it is not a reason to
leave your escort behind. Fixed, and checked.

### And the measurement that decides the rest of #136

Whether the pilot can aim at a *second* contact turns on whether hulls have
local geometry. Asked through **both** doors, which agree exactly:

    hull                track.at (km)     traffic.position (km)
    Held Breath                     0                         0
    Patient Ledger         39,588,118                39,588,118
    Long Consent          429,631,101               429,631,101

A hull sharing a body with the ship sits at that body's **exact** AU position —
zero kilometres off. There is no sub-body geometry to project into the conn's
frame, so "fly toward that asteroid and engage the ship beside it" cannot be
expressed today: flying toward anything increases `conn.pos`, which is what
`engage.band_for` reads, so it opens the fight *further* off.

That is a modelling change to `sim/traffic` — giving hulls positions within a
body's neighbourhood — and not a projection. Left filed rather than guessed at.

Noted while working: `ui/conn_window.py` is **508 lines** at HEAD, already past
the five-hundred rule before anything was added to it. The fire control will
need its own module rather than making that worse.

## A hull holding station has a place of its own (#136, part)

**The correction that makes flying at something mean something.** `engage`
ranged on `conn.pos` — how far the hull had come from where it let go —
because there was nothing else to range on: measured through both
`traffic.position` and `track.at`, which agree exactly, a hull sharing a body
with the ship sat at that body's position to the metre, **0 km off**, and every
other body was hundreds of millions. That was honest about something left at
the quay and exactly backwards for something flown at — closing on a contact
increased `conn.pos` and opened the fight *further away*.

`traffic.STATION_KM = 6000` gives a station-keeping hull a place in its body's
neighbourhood, **derived from its id and never rolled** — `in_system` is pure
in `(system, day, sector state)` and says why: the *Kestrel* you hailed
yesterday has to be the same *Kestrel*. A station is the same kind of fact, so
it is a reading of the identity. Measured: two hulls holding station 4,826 and
5,982 km off their bodies, identical when the chronicle is rebuilt.

`engage.range_km` now measures ship to contact, so the flying closes it:

    flown      0 km   ->  4,826 km off   Medium
    flown  2,000 km   ->  2,912 km off   Close
    flown  4,000 km   ->  1,293 km off   Contact
    flown  6,000 km   ->  1,692 km off   Contact   (flown past it)

### Wrong turns worth keeping

- **The suite went red and the guard was right.** Moving the range onto the
  contact left `engage.flown_km` called by nothing, and `test_reachable`
  refused it: "1 public function nothing ever calls. Either wire it into the
  game or delete it." Deleted. The check I would have written for that is the
  one already there.
- **A check of mine asserted the wrong thing about the right fact.** It
  measured every station-keeping hull's offset from **the ship**, and one of
  them holds station at another world half a billion kilometres away. The
  claim is about a hull and *its own body*; measured that way it passes and
  means something.

## Flying with the clock running (#137, the foundation)

The Pilot screen's hard part was never the view — it was the clock. An approach
tells the chronicle **once**, at the end: `berthing.commit` charges
`advance_days(conn.elapsed / DAY_SECONDS)`. A screen where the clock is always
running has to tell it as it goes, and the two must come to the same thing or a
live view is a way to buy or dodge time.

Measured first:

    conn.TICK = 60 s        one tick is a minute of ship time
    DAY_SECONDS = 86,400    so 1,440 ticks is exactly one game day

And the two do come to the same thing — **not approximately.** Three days
charged in one call and in 4,320 calls:

    charged once        day 3, credits 17,947.00
    charged 4,320 times day 3, credits 17,947.00     difference 0.0000

That is #116 paying off directly: `core/clock.MAX_STEP` is 1, so a jump of N
days *is* N jumps of one. A live clock is safe because the clock is honest.

`berthing.charge_flown(game, conn)` is the one door, billing only the minutes
nobody has billed yet, remembered on `Conn.charged`. `commit` goes through it
too, so a pilot who flies live and then breaks off does not pay twice for the
same hour.

### Wrong turns worth keeping

- **The suite went red twice, and both guards were right.** `test_reachable`
  refused `engage.flown_km` once the range moved onto the contact — dead code,
  deleted. Then `test_conn` refused the new `Conn.charged` field: `_copy`,
  which builds the twin a forecast flies, dropped it. That guard demands the
  field be carried **or named with the reason it must not be** — and it must
  not be: `charged` is a ledger fact, not a flying one, and a twin carrying it
  could let a forecast decide the ship had already paid for time it has not
  flown. Named, with that reason.
- Neither was a check I had to write. Both were already there, waiting.

## The five-hundred-line rule had no guard, and sixteen files were past it

#137's first move was `ui/window.py` at 519 lines. Splitting it turned up
something larger: **the rule was never checked**, and measured across the
package, sixteen files were over — `data/works3d.py` 635, `sim/robots.py` 616,
`sim/conn.py` 612, `sim/control.py` 602, `tests/test_orbits.py` 567,
`tests/test_control.py` 560, `ui/viewport.py` 535, and nine more.

`window.py` split along a seam its own comments already marked — the endings
went to `ui/endings.py` (70 lines) and `check_ending` stays as a two-line door,
because nine screens call it and every check that stubs a window relies on it
being a method. 519 → 475.

That also turned up **twelve dead imports** in `window.py` — `Bar`, `Pill`,
`ALIGN_R`, `spacer`, `hull_pct`, `cargo_used`, `CHASSIS_BY_ID` and more, left
behind when the HUD moved to `ui/hud.py` and never removed. The project's
"declared and unconsumed" guard covers functions, not imports, so nothing saw
them.

Splitting sixteen files is not one cycle's work, so the new check is a
**ratchet**: every file over five hundred is named at the length it has today.
A named file may shrink but never grow, and a file not on the list may never
cross. Proved by three mutations — a named file gaining one line, an unnamed
file crossing, and the `window.py` split being undone.

### Wrong turns worth keeping

- **I destroyed my own uncommitted work with `git checkout --`.** Restoring
  `ui/window.py` after a mutation reverted it to HEAD — the *pre-split*
  519-line version — because the split was not committed. `ui/endings.py`
  survived only by being untracked. Every mutation elsewhere this session used
  a temp copy for exactly this reason; here I reached for git and lost the
  work. Redone from the recipe.
- **A heredoc turned `\n` into a literal backslash-n** and `ast.parse` refused
  the file before it was written, which is the only reason nothing was
  corrupted. Parse before writing, always.
