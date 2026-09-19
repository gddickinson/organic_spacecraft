# Session log, part 29 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span undated to undated; undated entries keep their original place.

## Repair spends days, not calls (#119)

The last place #116's claim was not enforced. `ship.repair_tick` worked the
layer stack innermost-first and `break` fired only when a layer was left
*unfilled* — so a call standing for thirty days filled the innermost layer and
walked on to the next one **still carrying all thirty of them**, while thirty
calls of one day filled nothing and stopped each time. On a hull at 50% with
feedstock to spare, the same thirty days:

    one call of 30 days     1.0000 hull
    two calls of 15         1.0000
    five calls of 6         0.9677
    ten calls of 3          0.8561
    thirty calls of 1       0.8384

**The task had the direction backwards** — its title says the honest clock made
repair "30x faster". It made it *slower*: the old code's cascade needed a long
call to happen at all, and `MAX_STEP = 1` took that away.

Days are the resource now, spent innermost-first: a layer takes the days its own
rate needs and the remainder goes to the next one out. Measured across every
chopping from one call to sixty, in all three feedstock regimes:

    feedstock to spare   0.829259   spread 3.3e-16
    feedstock short      0.678571   spread 2.2e-16
    no feedstock         0.500000   spread 0

The cadence the docstring promises is unchanged — nothing outer is touched while
something inner is still open. What changed is the total: a month of mending now
heals 67.19 points where it healed 136, so the drive rate caps the larder at
3.36 t rather than 20.5 t.

### Wrong turns worth keeping

- **My first mutation did not restore the defect it claimed to.** Setting
  `left -= 0.0` left the chop-independence check *green* at 1.0000, because I
  had also removed the old `break`-on-unfilled — and undiminished days without
  that break is still additive. The original defect was the two together. The
  mutation was redone by restoring the original loop verbatim, which reddens
  three checks.
- **A mutation proved one of my own new lines dead.** The draft opened the loop
  with `if left <= 0: break`; deleting it changed no verdict, because once the
  days are gone `rate * left` is zero, `want` is zero, and the existing
  `heal <= 0` already breaks. Removed — an unreachable branch is the same
  defect as a field that is declared and never read.
- **Two existing checks encoded the old cadence and had to be re-derived, not
  just re-baselined.** "What it eats is what it is limited by" tested 2/5/20.5/
  500 t and now caps at 3.36 t, so its levels moved to 1/2/5/500 to keep both
  the feedstock-bound and rate-bound regions walked. "With a full larder it
  heals exactly what it always did" recomputed the *old* formula as its
  expectation; it now models day-spending independently and additionally
  asserts all sixty days were consumed, so it cannot pass by both sides being
  wrong the same way.

## The suite was overwriting the player's saved game (#122)

Filed as a scheduling problem — the suite takes ~25 minutes against a cron that
fires every 10, so overlapping runs are the normal case. Measuring it found a
worse defect underneath.

`core/save` spent `SAVE_PATH` as a **default argument** on `write`, `read`,
`exists` and `clear`. A default binds when the function is defined, so the path
could not be redirected by a test, by a second process, or by assigning to the
constant afterwards. Fourteen check files call `save_mod.write({"game": game})`
with no path.

Measured, not supposed. After a full run, `~/.seedfall/save.json` held **192,514
bytes of a game seeded `lab8`** — a fixture invented three cycles earlier for
the orrery checks — at day 0 with 18,000 credits. Whatever chronicle the player
had was already gone before this cycle began.

Now `save.save_path()` is one door, resolved at call time, honouring
`SEEDFALL_SAVE`. `tests/__init__.py` sets it to `seedfall-test-<pid>.json` in
the temp directory on import — there rather than in `__main__` because a check
module is often imported on its own, and an `atexit` hook takes the file and its
`.tmp` away again.

Measured after the fix:

    four concurrent runs      4 x 3 checks, all green, no interference
    player's save             a68363554e0ec50a, 52 bytes, before and after
    full 25-minute suite      player's save byte-identical afterwards
    temp files left behind    0

**The cycle prompt's rule that the suite must be run alone is now obsolete.**
It was a workaround for this defect.

### Wrong turns worth keeping

- **The first version of the guard destroyed the thing it guarded.** It wrote
  with no path and *then* compared the player's save before and after — so
  proving it bites, by reverting `save_path` and running it, put a 52-byte
  marker over `~/.seedfall/save.json`. It now asserts `save_path() != theirs`
  **before** writing anything; re-run against the reverted code it fails three
  checks and leaves the file's hash untouched.
- **A mutation that only reddens one check is not proof the whole fix is
  pinned.** Three were needed, each landing on a different check: reverting
  `save_path` to the home path (all three red), stopping the harness setting
  the variable (two red), and dropping the pid from the filename so concurrent
  runs would collide again (one red — and only that one).

## Wars, and the quay that strikes its colours (#115)

`sim/war.py` — derived, never stored, like `anchorage`, `fleets` and `piracy`.
`at_war(game, a, b)` is `relation <= WAR_AT`, so a war needs no start event, no
peace treaty and no save field, and a chronicle loaded from disk agrees with the
one that wrote it.

**What was measured first, and it is the whole reason this task existed.** Over
1,800 days across three sectors, with 15 to 18 ventures running to resolution:

    system.faction changed hands            0, 2, 2 systems
    of those, taken from another power      0, 0, 0
    port.faction changed hands              0, 0, 0

`_claimable` asked for `s.faction is None`, so annexation could only take
*unclaimed* ground. The sector's map filled in and never changed hands, and the
task's central image — a quay that cleared you last month now flying another
flag — could not occur at all.

`WAR_AT = -60` is set against what the matrix actually reaches, not picked
round. Worst relation any pair reached in 1,800 days over eight sectors: -57,
-69, -67, -81, -60, -95, -63, -78, median -68.

    threshold -40   war in 8 of 8 sectors        -60   war in 6 of 8
    threshold -50   war in 8 of 8                -70   war in 3 of 8
                                                 -80   war in 2 of 8

At -50 every sector is permanently at war somewhere and the state carries no
information; at -70 most chronicles never see one. And wars start partway in —
one measured sector sat at -45 for seven steps of 150 days before dropping to
-57.

The register and the berth stay two facts, deliberately: `system.faction` is
who has it on their books, `port.faction` is who runs the quay, and
`exchequer.holdings` reads the second and says why. They already disagree on 2
of 63 ported systems at generation. Annexing empty ground still moves only the
register; taking a system off somebody you are fighting moves both, because
that is what taking it means.

After: **12 wars over 10 sectors x 3,600 days, 5 quays changed hands, in 4 of
10 sectors.**

### Wrong turns worth keeping

- **My first measurement said 4-6 ports changed flag. It was my own bug.** The
  probe built its "before" map over *all* systems, scoring portless ones as
  `None` — so a port being founded read as a flag change. Corrected to compare
  only systems that had a port at day 0, the answer was 0, and it stayed 0
  across every later probe.
- **Making the spoils claimable was not enough, and the flight said so.** Wars
  started in 6 of 8 sectors and still no quay moved. Instrumenting the
  resolutions: of 49 annexations over ten sectors, **46 targeted a system with
  no port at all** and 3 an enemy quay, because open ground outnumbers spoils
  about three to one and `rng.pick` was uniform. A power at war now goes for
  its enemy's quays; expansion into empty space is what it does the rest of the
  time.
- **One of my own checks passed without checking anything.** "Annexing empty
  ground still leaves the berth where it was" searched the sector for an
  unclaimed *ported* system, found none, and returned a green tick reading "no
  unclaimed system carries a port in this sector". It constructs the case now.
- **Two candidate defects were investigated and both were correct as they
  stood**, so nothing was changed: `system.faction` vs `port.faction` is a
  deliberate two-fact distinction documented in `exchequer.holdings`, not a
  duplicated door; and `ventures.live()` has no lazy side effect — the same
  chronicle observed and unobserved produced identical results on three seeds.

## Hulls can meet: force projection, and keeper_of stops lying (#129)

`fleets.keeper_of` said in its own docstring that "a power can be out-shipped
over its own holding, and that is worth being able to see". Measured across six
sectors, it agreed with `system.port.faction` in **99 of 99** non-empty cases
and differed in **0** — a `max()` over a dict that could never hold two
entries, because `_weights` put hulls only on `exchequer.holdings`.

#115 did not fix it. Wars move *holdings*, not hulls: measured after a decade
with **nine live wars**, powers-with-hulls-per-system was still `{1: 195,
0: 141}`. Never two, by construction.

`_weights` now also stations hulls on what `war.spoils` says a power is trying
to take. `FRONT_WEIGHT` is 0.6, chosen against a sweep over eight sectors flown
a decade each:

    0.0   contested  0    holder out-shipped  0    holdings left bare 1
    0.3   contested 65    holder out-shipped  6    holdings left bare 1
    0.6   contested 77    holder out-shipped  9    holdings left bare 1
    1.0   contested 77    holder out-shipped 34    holdings left bare 4
    1.6   contested 76    holder out-shipped 48    holdings left bare 7

Below 1.0 on purpose: a power defends its own ground harder than it presses
somebody else's, so the attacker is usually the smaller squadron and taking a
system off its holder is an achievement. At 1.0 the holder is out-shipped in
44% of contests, which reads as a sector with no home ground at all.

The change is **inert in peacetime** — at day 0 nobody is at war, `spoils` is
empty, and placement is exactly what it was.

**This unblocks #114.** Two powers' squadrons can now be in one system, which
is where a fleet action has to happen.

### Wrong turns worth keeping

- **An existing check asserted something this makes false, and it stayed green
  by luck.** "Hulls sit where the holdings are" asserts `set(spread) <= held`,
  which is true only at peace; it passed because its fixture is a fresh sector
  where nobody is fighting. Renamed to say "in peacetime" and given an explicit
  `assert not war.wars(game)`, so it fails loudly if that fixture ever starts
  at war rather than quietly testing a different claim.
- **Mutating the front to nothing reddens the two new checks but not the old
  one**, which is the right shape: the old check is about peacetime and must
  not care. Mutating the *holdings* out instead reddens four, including the
  peacetime one — the two halves are separately pinned.

## A fleet action, at the scale the economy pays for (#114)

`sim/armada.py` — derived, stores nothing, resolves nothing. `combat` remains
the only thing that constructs a `Battle`; this answers who is contesting a
system, how the weight of metal falls, and what that does to the annexation
being fought over.

**The title's scale does not exist and was not built.** #114 asked for "a
battle of two hundred hulls". Measured: the economy sustains a mean of **23
hulls in the entire sector** (25, 26, 23, 24, 20, 22 over six), because
`fleets.UPKEEP` is 45/day against the margins `exchequer` produces. And a
contested system, over eight sectors flown a decade each:

    contested systems per sector   10, 11, 13, 0, 8, 0, 0, 13   (mean 6.9)
    hulls in one                   min 2, median 3, max 4

Three of those eight sectors never went to war. So a fleet action here is a
handful of hulls over a quay — roughly **fifty times** smaller than the title —
which is also precisely why one hull can tip one.

**The claim the task set, measured.** `ventures.odds` weighed the sponsor's
levies, its standing with everybody else and whether the player had leant on
it, and not one term asked who had hulls over the place. `armada.balance` now
feeds it at `BALANCE_SWAY = 0.25`. On a 2-against-1 at Ferron Hollow, with the
**stance held fixed** so this measures the hull and not the opinion:

    backed    away 0.717   present 0.800    the hull alone is worth +0.083
    opposed   away 0.117   present 0.075    the hull alone is worth -0.042

The player's hull counts when they are *there* **and** have taken a side —
`Venture.stance`, which they already set from the ventures panel and which
`odds` already read, so taking a side in a fleet action needed no new state and
no new screen.

### Wrong turns worth keeping

- **My first measurement of the claim was +0.383, and it was mostly not the
  hull.** It compared "away and neutral" against "present and backing", so it
  counted `ventures.SWAY` — the player's opinion, which already counted before
  any of this existed. Holding the stance fixed and moving only the ship gives
  +0.083, which is the honest number and the one the check asserts.
- **A mutation deleting the `at_war` filter in `sides()` left every check
  green**, because in play hulls only reach a foreign system *through*
  `war.spoils`, so the filter is unreachable by flying. Rather than delete a
  guard that states what makes the module mean "contested" rather than
  "crowded", the check now constructs the case — a non-belligerent squadron
  parked over somebody's quay — and asserts it is not an action.
- **The harness caught the new module before I did**, refusing it for having a
  tuning constant and no tripwire fast path. Registering `armada` was the fix;
  the investigation behind it found something worse and is filed as **#130**:
  `tripwire.constants()` matches `ast.Constant`, and `-60.0` parses as
  `UnaryOp(USub, Constant(60.0))`, so **14 negative constants across the
  codebase have never been swept at all** — including `clearance.WELCOME_AT`,
  `grudge.COLD_SHOULDER`, `allegiance.IMPLACABLE` and `war.WAR_AT`. 422 are
  swept; those 14 are invisible. Task #60's "none unprotected" was true only of
  the constants the scanner could see.

## The tripwire could not see a negative constant (#130)

`tripwire.constants()` walked each module's AST and kept assignments whose value
was an `ast.Constant`. **A negative literal is not one** — `-60.0` parses as
`UnaryOp(op=USub, operand=Constant(60.0))` — so every negative module-level
constant was skipped in silence.

    swept before the fix    422
    invisible               14
    swept after             436

The fourteen are not incidental numbers. `clearance.WELCOME_AT` decides whether
a quay opens a hatch to you; `grudge.COLD_SHOULDER` and
`allegiance.IMPLACABLE` decide whether a power will deal with you at all;
`gates.TOLL_REFUSED_BELOW` decides whether a gate lets you through;
`war.WAR_AT` decides whether two powers are fighting. Task #60 is titled "all
153 tuning constants measured, none unprotected" — true only of the constants
the scanner could see.

**Swept, and the result is the good one: 14 of 14 are noticed, 0 survive.**
They were protected all along; nothing could see that they were. No new checks
were needed, which is the outcome worth having and not the one to assume.

`sim/war` also had no fast path — it was added last cycle carrying only
`WAR_AT`, which was invisible, so `test_harness_guard` had nothing to complain
about. Registered as `("war", "armada")`.

### Wrong turns worth keeping

- **My sweep left a constant mutated in the working tree.** The refinement pass
  was killed by an outer 10-minute timeout, so its `finally` never ran and
  `data/territory.py` was left holding `UNWELCOME = -12.5` against a real value
  of -25.0. `tripwire.main` guards against exactly this and says so in its
  docstring — "a tool that edits source has to put it back on the way out, not
  only on the happy path" — and my ad-hoc probe reimplemented the trap it
  warns about. Caught by diffing the constants against their expected values
  before committing; a `git status` alone would have shown a modified file with
  no hint of what was wrong with it.
- **The distinction between "bites" and "hangs" was left unmeasured.** Of the
  fourteen, six were caught by a check going red and eight by the run timing
  out with the constant at zero. `suite_passes` counts a hang as noticed and
  documents that, so the sweep's verdict stands — but a hang is weaker evidence
  than a red check, and the pass that would have separated them (trying the
  doubled and halved variants for those eight) ran past ten minutes and was
  abandoned rather than left half-reported.

## The sweep has been voting with a stopwatch since #116 (#131)

`tripwire.suite_passes` runs a constant's own suites, then the broad set. Both
stages read a `subprocess.TimeoutExpired` as proof — *"a hang is a very loud
notice"*. Measured this cycle, and the premise under that is gone:

    the broad set          155 suites
    LIMIT                  60 seconds
    time it actually takes ~25 minutes, since `core/clock.MAX_STEP` became 1

The note beside `KIN` still says "the broad set costs thirty-six seconds",
which was true before the honest clock landed. **It now times out unmutated**,
so every constant its own fast path failed to catch has been handed a pass mark
earned by a stopwatch, for as long as #116 has been in.

Fixed: `completes(suites)` calibrates once, per set, whether a run finishes
inside `LIMIT` with nothing mutated; a timeout counts as evidence only where it
does; and a stage that cannot finish clean abstains rather than convicting.

Re-measured the eight constants that had only ever "bitten" by hanging, at
double and half (skipping zero, the value already known to hang):

    industry.RIVAL_COST      -12.0 RED     pinned
    gates.TOLL_REFUSED_BELOW  both green   NOT pinned
    industry.ILLICIT_COST     both green   NOT pinned
    robots3d.DRIVE_Z          both green   NOT pinned
    territory.UNWELCOME       both green   NOT pinned
    approach.LOSING           both green   NOT pinned
    clearance.WELCOME_AT      both green   NOT pinned
    voice.COLD_AT             both green   NOT pinned

**Seven of eight are pinned by nothing.** Filed as #132; writing seven checks
in one cycle is how a check gets written to pass rather than to bite.

### Wrong turns worth keeping

- **My probe emptied a source file, and my verification said it was clean.**
  Killing the background sweep sent SIGTERM into `path.write_text`, which
  truncates before it writes — `seedfall/data/industry.py` was left at **0
  bytes**. The check I ran afterwards compared each constant against its
  expected value and reported "no mutated leftovers", because a file with no
  constants in it has nothing that compares unequal. `git diff` is the only
  verification that catches a deletion; a value check cannot. Restored from
  git before anything was committed.
- **The most important half of the fix was unreachable by any check.**
  `try_value` is a closure inside `main()` and carried its own copy of the
  try/except, so a mutation restoring "a hang is proof" there left the whole
  suite green. Both now go through one `noticed(suites)`, which is also the
  one door for "did anything object" — there were two.
- **The first diagnosis was wrong and cheap to disprove.** The obvious reading
  was that zeroing these constants sent the sim into an unbounded loop.
  Patching `clearance.WELCOME_AT = 0.0` in-process and running its suite
  finished normally, all five checks passing — so the hang was never the
  constant, and the tool was the thing at fault.

## Two of the seven unpinned constants, and the shape of why (#132)

`clearance.WELCOME_AT` (-40) decides whether a quay opens a hatch to you at
all; `territory.UNWELCOME` (-25) decides whether a claimant will let you plant
on their register. Both swept green at double and half. Neither was dead, and
neither was unread — both were **tautologically checked**, the second of the
three states `tests/tripwire.py` opens by naming:

    test_clearance.py:80   game.rep[quay.faction] = clearance_sim.WELCOME_AT - 40.0
    test_territory.py:170  game.rep["charter"]    = UNWELCOME - 10

The check read the same constant the code read, so the two moved together.
Double the bar to -80 and the standing became -120: still under, still refused,
still green. The assertion could not fail.

Both now bracket the bar with **absolute** standings, a point either side, so
moving it in either direction puts one of them on the wrong side:

    WELCOME_AT   granted at -39, refused at -41 with "standing -41" in the words
    UNWELCOME    refused at -26, and welcome at -24

Measured through the game's own doors first, to find where the bar really is —
`clearance.request` flips between -40.0 and -40.5, `territory.welcome` between
-25 and -26, both strict `<`.

Proved by hand-sweeping each constant to double, half, **and a 1.5-point
nudge**: all three go red now, and all three were green before.

Five remain, filed in #132: `gates.TOLL_REFUSED_BELOW`,
`industry.ILLICIT_COST`, `robots3d.DRIVE_Z`, `approach.LOSING`,
`voice.COLD_AT`.

### Wrong turns worth keeping

- **The first probe could not have shown the granted side.** It took the first
  anchorage with a faction and swept the standing down, and every value came
  back refused — including 0 — because that berth answers "no berth to offer"
  regardless. A check written on that fixture would have asserted "refused at
  -41" against a quay that refuses everybody, which is a green tick for
  nothing. The suite's own `_here()` fixture grants at 0, and that is what both
  checks use.
- **Each check now asserts the bar is where it thinks it is** — `assert
  WELCOME_AT == -40.0` — and says why in the message: absolute brackets have to
  be re-bracketed by hand if the constant is retuned. That is deliberate. A
  bracket that follows the constant is the defect being fixed here.
