# Session log, part 15 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-29 to 2026-07-29; undated entries keep their original place.

## 2026-07-29 — SEEDFALL: a hull flying lopsided

Three places in the tables had promised this since they were written, and not
one of them was true. `data/mounts.py`, on why the drive stations are spread
across the transom: "so losing one leaves the thrust off-axis".
`thrusters.offset`, computing exactly how far off: "which the flight computer has
to trim against". And `Mount.axis`, the direction each engine pushes — declared,
and read by nobody, because every drive was given the same constant and nothing
ever looked. So a hull on one of two engines flew exactly as straight as one on
two, only slower. Prose that describes a consequence which does not exist is
worse than silence, because it is believable.

`thrusters.yaw_torque` is `r × F` over the engines actually fitted — the one
place `Mount.axis` is read for what it is, since a cross product has to know
which way the force points. A balanced pair cancel. A NAVIS on one engine puts
**0.0012 rad/s² against 0.00076 of attitude authority**.

**My first model was wrong about the tick, and the checks told me so.** I let
the hull yaw, and wrote a check that the yaw scales with the throttle so easing
off is a real answer. It failed non-monotonically: 1.0 → 0.00°, 0.9 → 0.00°,
0.6 → 21.31°, 0.3 → 0.00°. Not noise — 0.0012 rad/s² across a sixty-second conn
tick is **126 degrees**, so the nose was wrapping past 360° and reading as zero.
An unopposed torque over a whole minute is not something a pilot trims against;
it is a ship spinning like a top, and no flight computer would allow it. The
honest model is the one the docstring already described: the computer *holds*
the nose, and the cost is that it will not open the drive past what it can hold.

So `holdable_throttle` is attitude authority over drive-induced yaw, floored at
0.15 because a refit that silently strands a ship is a worse fault than a
sluggish one. A **NAVIS on one of two engines holds 0.62** and pays 55% of the
extra mass share for the clusters trimming throughout: **twice the reaction mass
per m/s**, and a high orbit reached in 1.24× the time for 1.20× the mass. A
**LEVIATHAN shrugs a missing engine off entirely** — its moment of inertia beats
the torque — so the penalty lands on the hulls light enough to be turned by
their own drive, which is where it belongs. It falls out of the physics rather
than being arranged, and it is asserted, because a player who found it would
otherwise file it as a bug.

Two things came out of measuring rather than assuming:

- **Priced per seed, the lopsided hull reached a high orbit the balanced one
  missed.** Too much thrust overshoots at a small body, so the cap gentles the
  approach — task #83 showing its face from the other side. My first cost ratio
  summed each hull's own successes and so compared two different populations;
  it now prices only the climbs both hulls made.
- **A vacuous assertion of mine.** `assert mass_one > TRIM_COST_SHARE * 0` is
  true of any positive mass. Replaced with the exact arithmetic the surcharge
  predicts, which then failed at 1e-9 and turned out to be the tank's own
  four-place rounding — harmless, because the smallest spend the game can make
  is 0.018 t, 360 granules, so no pulse is ever free. Checked rather than
  assumed.

`sim/instruments.py` says it out loud, because a cap the pilot cannot see is a
bug report: **"Drive trim — 62% usable"**, beside an Engines panel that already
read "port of the centreline" and "Empty station — no engine fitted". Only when
there is something to say. I had added the row and asserted nothing about it —
the hole was mine, and the check came after. **And I marked it amber**, which
`test_conn.py`'s "the panel does not cry wolf at a good approach" then caught
warning on fourteen approaches that had *succeeded*: the exact fault that check
exists for. The trim is a fact about the hull, not a fault in the flying.

**The cap also exposed a third bug in `conn._copy`,** which is worth more than
the cap itself. A forecast flies a throwaway twin built from a hand-written
field list, so the twin thought it had both engines and quoted a burn 0.095 km
off the one the drive would make — the cap was on the act and not on the quote.
Rather than just adding the field, I asked which *others* the twin drops:
**`orbit_want_km`**, added when orbit heights arrived, meant `outcome.adrift`
measured drift against a 12 km opening instead of the 20,000 km being climbed
to; **`star_lum`** was harmless only because a forecast never renders. The
docstring already recorded this happening once before with `start_km`. Third
time, it becomes a guard: `test_conn.py` enumerates every `Conn` field and
demands it be carried or named as one a twin must not inherit, with the reason.
Sweeping it proved the guard earns its keep — dropping `hold` fails the old
forecast check, but dropping `orbit_want_km` or `star_lum` fails **only the new
one**.

The fix pushed `sim/conn.py` to 525 lines, so the forecast came out into
`sim/preview.py` — the same seam `instruments.py` and `outcome.py` left along,
and the right one: `conn` is the act, these are what is said about it. `conn.py`
is 465 now, `preview.py` 77. `_rotate` became `conn.rotate` on the way, because
`autopilot` had been importing the private name all along.

`seedfall/tests/test_lopsided.py`, 9 checks. Nine mutations, **nine caught,
none missed** — the floor turned into a ceiling, the ratio inverted, the cap
computed and not applied, the conn told every hull is balanced, the surcharge
dropped, the torque returned as zero, and the panel condition broken in *both*
directions: silenced, and made to speak when there is nothing to say. Four more
against `_copy` and the trim row's severity: **four caught, none missed**.

## 2026-07-29 — SEEDFALL: screening that actually screens

`ConsortOrder.shield` — 1.0 for "screen me", 0.25 for concentrating, 0.0 for
flanking — was one of the eight dead fields the guard found yesterday, and the
allowlist entry I wrote for it said it had already been wired for the flag's
damage. **It had not.** A false reason inside the very field meant to prevent
false claims, and nothing checks the reasons: they are only as honest as whoever
writes them. Worth leaving on the record rather than quietly correcting.

So the order's own promise — "draws fire that would otherwise land on you, and
takes it on a smaller hull" — was half true. `draw` sent shots at the escort;
nothing at all came off the blows that still arrived. Measured before: over six
engagements the flag took **228.5 with two escorts screening against 223.6 with
the same two flanking**, while the screens lost 36 more hull for the privilege.
Screening was a pure cost. You paid and got nothing.

**I also changed the screen's station, and had to take it back.** The order aims
an escort at the *midpoint* between the enemy and the flag, and the argument
against that seemed strong: the midpoint moves whenever either ship moves, so no
hull can hold it. I moved the station to hug the flag on the threat side and
reported it as an improvement from 21% interposed to 82%.

**That comparison was worthless.** The two figures were different measurements —
21% counted blows across *whole engagements*, including every turn after the
escorts were dead; 82% counted turns while alive over a short window. Measured
properly, under one method, the midpoint is *better*: 95% of alive turns against
85%, because the midpoint is **on** the line between the two hulls by
construction. Reverted, and the engagement figures improved with it, flag 111 →
95. The mutation sweep is what caught it: "a screen goes back to chasing the
midpoint" would not fail, and the reason it would not fail is that there was
nothing wrong with the midpoint.

`consorts.interception` is the arithmetic, and it is the part that was real. A hull that is genuinely between wears
`shield × SHIELD_SHARE` of each blow, before the flag's own armour, and the part
it wears lands on its layers. It saturates: `SHIELD_FLOOR` means six screens
still leave the flag wearing 45 of every 100, because "does more of a good thing
make it worse" is a question worth answering with "it stops helping".

**And the whole thing nearly went in tuned against noise.** At eight and ten
seeds the engagement totals moved *non-monotonically* with the shield share —
+7.8, −5.2, +3.8, −20.8, −19.6 — which is what noise looks like when mistaken for
signal, and a constant fitted to that would have been fitted to nothing. Forty
seeds, and the ordering is stable:

    screen        flag  95.0   escorts lost 76.0   diverted onto screens
    flank         flag 128.0   escorts lost 57.0   diverted           nothing

Screening saves the flag 26% and costs the escorts 19 more hull. Concentrating
protects the flag best of all by ending the fight soonest, which is exactly what
*its* blurb claims, so the check asserts the trade against **flanking** — the
order that explicitly screens nobody — rather than asserting an ordering across
all three that the game does not have.

**And the first sweep ran 7/12, with all five misses the same mistake: testing a
specific mechanism with an aggregate something else dominates.** Discarding
interception's answer *entirely* — so the flag took the whole blow and the screens
wore their share as well — passed a forty-seed "screening protects the flag"
comparison untouched, because that difference comes mostly from `draw`. The fix
was single blows with constructed geometry, where the books balance exactly: 72
on an unscreened flag, 50 screened, 22 worn by the hull in front.

Two real bugs surfaced only that way:

- **The flag's own hull saturated the measurement.** Thirty shots destroy it
  either way and `taken` caps at 336.0 in both runs, which reads exactly like a
  mechanism that does nothing.
- **The armour floor erased interception.** `max(nominal · 0.15, dmg − armour)`
  floors against the weapon's *nominal* output, so the part a screen absorbed
  never reached the comparison. At 34 armour a flat floor lets a screen cut
  26.5 → 21.6; scaled by what actually arrived, 26.5 → 15.1. A rule that stops
  armour negating a weapon must not also negate the hull in front of it. I first
  attributed the 336 figure to this floor, which was wrong — right conclusion,
  wrong evidence, corrected in the comment.

The station that was kept is load-bearing, and that had to be shown rather than
assumed: send the screen at the enemy, or astern of the flag away from the guns,
and the checks fail. A mutation that does not fail is usually a weak check; this
cycle it meant a wrong fix, and the difference is only visible if you go and look.

`tests/test_screening.py`, 8 checks.

## 2026-07-29 — SEEDFALL: eight things declared and read by nobody

`test_reachable.py` has asked "is every function reachable?" for a long time and
caught two of my own orphans this session. Asking the same of **data** turned out
to be the richer seam. An audit of every field on every dataclass in `data/`
found **eight that nothing anywhere reads** — and several had docstrings
*asserting* they mattered:

    starclasses.luminosity   "drives how hard the light falls on everything
                              else, which is why an M dwarf's worlds are dim
                              and an A-type's are glaring" — it drove nothing
    starclasses.halo         the corona colour, drawn in the disc's colour
    lineages.boredom         "what that costs in morale" — morale_tick had no
                              lineage term at all
    lineages.time_sense      a written line no player had ever seen
    lessons.skip_if          a tutorial step that should skip itself, and did not
    consorts.shield          1.0 screening, 0.0 flanking — never read
    mounts.axis              "losing one leaves the thrust off-axis" — it did not
    commodities.cat          a category nothing grouped by

A dead field is worse than a missing one: it reads as a feature to anyone
looking at the table, it gets quoted in the prose beside it, and it silently
promises behaviour the game does not have. Two of these eight were **mine**,
from the star-catalogue cycle two days ago.

**The deliverable is the guard.** `tests/test_declared.py` fails on any field in
`data/` that nothing reads, with an allowlist carrying a **written reason per
entry** — because an allowlist used to dodge the work is the anti-pattern, and
one with a reason is how "known and deliberate" gets said. It also fails if an
allowlist entry names a field that no longer exists, or one that *is* now read,
so the excuses cannot go stale. The scan counts `getattr(x, "name")` as a read:
a first version missed that and would have cried wolf on `System.star` and
`Target.berth`, and a guard that cries wolf is worse than none.

Four wired this cycle, each with a differenced check:

- **Luminosity now lights the picture.** `conn.star_lum` carries the fact the
  way `star_dir` already carried the light's direction, and the window decides
  how many stops of it to show — a fourth root, because the raw range is five
  hundred to one and a display has about four. Measured over the same world at
  the same range with only the star changed: M 293 · K 303 · G 312 · F 323 ·
  A 324 on the brightest tenth of the frame, and 1.48x per lit face.
- **A corona is its own colour.** Nine classes have a halo distinct from their
  disc; the window drew the disc's colour blurred.
- **A crossing is harder on some crews.** Measured on the *same* voyage with
  only the lineage changed: wet 0.770, grafted 0.845, dry 0.920 morale after
  300 days.
- **And the crew say how it feels.** `TEDIUM_WORTH_SAYING` was 30 days in a
  first draft and the line then almost never appeared — the longest crossing in
  the system I tried was 29. Measured across 354 crossings in eight sectors the
  median is nine days and the ninetieth percentile twenty-three, so it is 20.

**Mutation sweep 15/15 on source, and it took two passes.** The first ran 11/17
and the six misses split cleanly:

- **Four were real holes, all the same species** — measuring near the thing
  instead of the thing. Every check set `conn.star_lum` by hand, so nothing
  asserted `conn.start` reads it off the star. The corona checks examined the
  data path and the class table and **never a picture**, so making the corona
  fall back to the disc's colour passed all of them; it is now drawn on a blank
  plate, where a red corona and a blue one differ by 137. "At least eight of
  nine" classes let one sharing slip through — all nine must now. And the
  tedium floor was checked as `TEDIUM_WORTH_SAYING - 1`, which is precisely the
  trap this project has a rule about: a bar read off the constant under test
  cannot fail for *any* value of it, and at zero `how_it_feels(-1)` is still
  silent. It is an absolute ten days now.
- **Two were bad mutations of mine.** I mutated `test_declared.py` itself —
  deleted its assertion, gutted its reason-length rule — and expected the suite
  to notice. Nothing can: a check cannot catch its own assertion being removed.
  That is a flaw in how I built the sweep, not a gap in the guard, and the
  honest response is to say so rather than invent a meta-check to paper over it.

Four allowlisted with reasons and tasks: mount axis (#85), consort interposing
risk (#86), tutorial skip (#87), commodity category (display metadata, and
nothing in the sim should ever read it). The same scan over `sim/` and `world/`
finds fifteen more — three of them mine from the gunfire cycle, and three
`Options` fields, which is the worse smell because `test_options` exists to hold
"an option that changes nothing is a lie". Task #88, deliberately not folded in
here: the guard would land red.

## 2026-07-29 — SEEDFALL: the bench after the tree

The tech tree is sixty-two nodes and 28,790 points end to end, and the game is
explicitly built to carry on past every one of its ten endings. So there is a
day when the last node lights and the bench has nothing to do. Measured on a
generous rate that day was **2,014**, after which the ship accrued **146,040
research points over ten years that bought nothing at all** — every laboratory,
every CHORUS node, the `research` bonus on eight technologies and the whole
survey economy behind them feeding a number `ui/tech_view.py` *displayed* and no
code could ever spend. Found by asking the plainest question there is: is every
declared thing consumed?

`data/programmes.py` and `sim/programmes.py` give it somewhere to go. A
programme opens when its **branch** is exhausted — so a captain who drives one
branch hard is running one long before the tree is done, and this is the same
machinery arriving late rather than a mode bolted onto the end. It never
finishes; it completes rounds, each `ROUND_GROWTH = 1.4` dearer than the last,
so a finished tree cannot become a fountain: measured, eight rounds run from
1,100 points to 11,595.

Each round yields a **finding**, and a finding buys standing or credits and
never a better hull. That is deliberate — an endgame bench that improved the
ship would only inflate it; one that pays in standing feeds the political game,
which is where the decisions are. Three doors, each consuming the finding:

    file with the Choir     sanhedrin +24.2                    (deep with one)
    publish openly          +25.1 spread over all four        (broad, shallow)
    sell                    5,566 credits                    (nothing political)

`PUBLISH_SHARE = 0.45` is what makes that a real choice rather than a dominated
one: filing wins with the power you file with (24.2 against publishing's 10.9)
and publishing wins on the sector total (25.1 against 22.2). Below a quarter,
publishing is dominated everywhere; above it, filing never makes sense.

Two bugs found by playing, both mine, and both the *same fault the feature
exists to fix* in fresh costume:

- **The clock took the spare points and threw them away.**
  `research.take_spare` zeroes what it hands over — deliberately, so a day's
  work cannot be spent twice — and `clock` called it unconditionally, so a bench
  standing down destroyed every point the tree could not use. There is now a
  `can_take` gate asked *before* the taking; measured, 1,833 points correctly
  held for a stood-down bench where the first draft held none.
- **The findings did not survive a save.** `programmes.state` attached the
  bench to the game as an attribute, and the save codec encodes *declared
  fields and nothing else*, so a reload came back with an empty bench. It is a
  declared field on `Game` now.

And the research screen was telling a captain to "pick something below" with
every technology in the sector already known and nothing below to pick. It says
where the points go instead.

`tests/test_programmes.py`, 7 checks.
