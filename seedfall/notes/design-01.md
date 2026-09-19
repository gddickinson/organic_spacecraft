# What this is — the design, pass by pass (1 of 8)

Moved out of `seedfall/INTERFACE.md`, which is now only the map. Text unchanged.


**SEEDFALL** is a native PyQt6 space exploration / trading / combat RPG built on
the GESTALT design programme in this repository — a modern Starflight with a
Civilization layer. You command a grown starship in the Verge, survey and trade,
fight or refuse to, research a fifty-eight-node tech tree, design hulls out of
grown organs and fabricated machinery, plant colonies, and deal with the Bloom.

The GESTALT documents supply one of the five technologies and all of the
physics: the grown hull classes from the Fleet Class Reference, the six-layer
hull from the Design Dossier, the phosphorus bottleneck and 9:1 ore ratio from
Metabolism, the wet/dry cyborg control stack from Nervous System, the cell types
from the Cell Atlas, and the reproduction-licence containment regime from the
Fleet Registry. The other four technologies exist so that the grown fleet has
something to be measured against.

**Combat is positional.** Ships carry a heading and a speed on a real plane.
The five range bands still exist — weapons are specified in them — but the band
is *derived* from an actual separation rather than stored, so closing is a
manoeuvre rather than a menu pick. Every mount has a firing arc (fore, broadside,
turret) and will refuse to fire outside it, which makes turning to bring a gun to
bear a real decision.

**And you can only sit in one seat.** Each turn you take one station personally —
Helm, Gunnery or Engineering — and your officers hold the other two at their own
level, which is competent and worse than you. Directed gunnery shoots markedly
better than automatic; engineering routes power, patches the outermost breach or
dumps heat; the helm decides what will bear next turn.

**The Bloom is an antagonist, not a timer.** Five named stages advanced by the
sector-wide burden: past Motile it keeps roaming instars in the field that prefer
your colonies to empty ground; past Adaptive it builds resistance (up to 55%) to
whatever weapon family you keep using, and forgets what you stop using. At
Kessel's Reach, found by surveying the origin system, is the First Instar — the
original husk with a Charter serial still on it. Containment requires the sector
clean *and* that husk dead, which takes about twenty burn passes from a
battleship.

**Diplomacy has two axes.** Your standing with each power, and how the powers
regard *each other* — a relations matrix that starts hostile in most pairs.
Tribute, intelligence and relief move the first; only brokering moves the second,
and brokering requires both parties to think well of you already. Concord needs
all four at Kin **and** all six pairs at peace, so it is a diplomatic achievement
rather than four grinds.

**Getting anywhere is a decision.** A jump drops you at the system edge, not
alongside anything. Bodies sit on real orbits that keep moving while you fly, so
the range to a target depends on when you leave. Four burn profiles trade
reaction mass against days — and *coasting is always free*, which is what stops
an empty tank from becoming a deadlock. Local work (survey, extract, dig, land)
flies the ship alongside first, so a player who never opens the helm still gets a
coherent transit; the helm is where you choose a better one.

**A hull is only opened where there is a yard to open it.** A player asked why
they could refit anywhere. They could: `apply_refit` validated the design and
the cost and *nothing else*, so the rule lived in the button rather than the
simulation and any other caller — the remote bridge included — could strip a
hull in deep space. The button's own version was wrong twice besides: it
tested "this system contains a port", which since anchorages is not the same
as being alongside one, and it accepted any quay rather than one with a yard.
`shipyard.can_refit_here` is the rule now, expressed through
`anchorage.docked_at` and `offering(game, "shipyard")`, and the screen reads
it instead of holding its own.

**And nothing had ever counted a line.** The five-hundred-line rule has been
standing instruction since the start, and no check anywhere enforced it — which
is why files drifted over one commit at a time until there were fourteen at
once, 758 lines of debt between them. `tests/test_length.py` is the ratchet: a
file not on the debt list must be under the limit, a file on it must not grow,
and a debt that has been paid must be struck off — a stale row makes the
remaining work look bigger than it is and sends the next reader to split
something already split. Raising the limit does not get past it, because then
every debt reads as paid and the stale-row check refuses the lot.

`sim/control.py` was the second: 602 lines, with the tug — its own banner at
line 490, four functions, five constants, and nothing above the banner calling
anything below it — moved to `sim/tug.py`, leaving 487. Here the constants
*came with it*, which is the opposite of the conn split and for the same
reason: searched untruncated, `TUG_FROM` and its four siblings are read by
nothing outside the tug, so `sim/tug` is their one door.

`sim/conn.py` was the first paid off: 612 lines, with the tick integrator —
`_substeps`, `_sweep_min`, `_step`, `_touch`, `_resolve`, one contiguous block
with exactly one caller — moved to `sim/conn_step.py`, leaving 489. The
constants stayed in `sim/conn` because eleven other modules read them;
`ALONGSIDE_RATE` alone is read by `autopilot`, `moorings`, `clearance`,
`instruments` and the flight window, and re-exporting them to tidy the new file
would have been a second door.

**Which numbers are actually held in place.** `tests/tripwire.py` changes
every module-level tuning constant in the game — zero, double, half — and
reports the ones no check notices. A survivor is dead, tautologically checked,
or genuinely unpinned, and all three are worth knowing. The clean run: **60 of
131 unprotected**, the worst being `approaches.ODDS_PER_DAY`, which retires
the entire envoy system in silence when zeroed. `tests/test_tuning.py` pins
the worst of them, always against a figure written in the check and never
against the constant under test — the mistake this whole apparatus exists to
stop.

**Two of the survivors are now pinned, and finding out why they had survived
mattered as much as fixing them.** `approaches.QUIET_DAYS` had *two* apparent
guards and neither could fail: `test_approach` built its fixture with
`game.day += QUIET_DAYS - 5`, so the fixture moved with the constant, and
`test_tuning` stated in a comment that it pinned it while asserting only that
three to sixty envoys arrive a decade — a wide enough door to walk a spacing
rule through sideways. `bloom.RESIST_DECAY` had none at all.

Both are pinned on what they govern, measured through the sim and never read
from the table. The quiet spell: two chronicles played a day at a time for
eleven years each, 78 repeat approaches, shortest gap **120 days** and longest
608, asserted at 110..140. The forgetting: a family at full 0.55 resistance
falls to **0.515** after 100 days, **0.200** after 1,000 and is gone by 1,600
(4.4 years) — with the invariant that a thousand days told one at a time
equals a thousand told at once, because the clock steps daily in play and
jumps in a transfer. Halved, doubled and zeroed, all six mutations go red.

**One door for what is too long, and one for the fast paths — the hard way.**
`tests/test_harness_guard.py` has checked both since long before the recent
work, and two more checkers grew beside it anyway: `tests/test_length.py` with
a second debt list, and `tests/test_tripwire.py` with a weaker copy of the
fast-path check under a docstring claiming nothing had ever checked the tool.
Within two cycles the two debt lists disagreed — harness_guard still carried
`sim/conn.py` at 612 and `sim/control.py` at 602 after both were split, and the
pair differed on `ui/viewport.py`, 535 against 533. A stale ceiling is silent,
because a 612 cap over a 489-line file passes; only the list that *refuses*
stale rows would ever have said so.

`test_length` is the one debt list now. `test_harness_guard` keeps the
fast-path check, being strictly stronger — it also catches a module named
twice, which matters because a dict literal keeps the last value for a repeated
key in silence. One assertion from the deleted pair was **not** a duplicate and
only mutation found it: a ghost `KIN` entry, a row naming a module that does
not exist, survived the deletion. It is folded into harness_guard's check now.

**Fast paths are ordered cheapest-first, and the order is checked.** Timed:
`politics` 145.4 s against `exchequer` 3.5, `industry` 7.5, `armada` 0.1.
Measured constant by constant, seven of `exchequer`'s thirteen are held by
`exchequer` and two more by `industry`, so its entry reads
`("exchequer", "industry", "politics")` and the dear suite is reached only by
what the cheap ones miss. Putting `politics` first fails a check, not merely
the clock.

**A fast path that misses its guard makes the sweep lie, not merely dawdle.**
Measured: 19 constants swept, four on the shortlist, **all four already
guarded** — `charts.KNOWN_WORTH` by `provenance` (0.3 s), the whole COURTSHIP_*
family by `courtship` (1.4 s), and neither suite named by the entry. `charts`
and `diplomacy` name them now, cheapest first. `test_tripwire.MEASURED` records
nine such pairs; it used to demand the guard be in `SLOW`, and that rule would
have barred the four rows that matter, so it is gone.

**`sweepkit.put` replaces a file atomically**, because the alternative cost a
real one: a SIGKILL timeout caught a sweep inside `write_text` — which
truncates before it writes — and left `data/diplomacy.py` 168 lines shorter,
with the SIGTERM restore handler never getting to run. A temp file and
`os.replace` cannot leave a half.

**The sweep has two stages that differ by two orders of magnitude, and they
are now two commands.** Measured: `piracy`'s ten constants swept in 20 seconds;
`exchequer`'s thirteen were still going after thirty minutes. The difference is
not the constants but the suites their entries name — `exchequer` answers in
3.6 s, `politics` in 145.4, and handing both to one run cost 148 s a variant.
Stage one asks one suite at a time and stops at the first objection, which
changes no verdict and took `piracy` to 9.2 s; `--fast` skips stage two
entirely, producing a **shortlist** rather than a verdict, and says so in those
words, because "unprotected" is a conclusion the fast stage cannot reach.

**`tests/sweepkit.py` is how to find a constant and how to change one**, split
out of `tripwire.py` at exactly five hundred lines. It is a leaf — it reads
nothing from the sweep and knows nothing about suites — so a one-off tool
hunting a single constant's guard can use it instead of reimplementing
`rewrite` by hand, which is one transcription error away from a mutation that
never restores.

**The sweep itself was dead at HEAD and nobody knew**, because `main` had no
check: a local `noticed = False` shadowed the module-level `noticed()` for the
whole function including its closure, so the first constant tried called
`False(suites)`. #134 had been waiting on a tool that could not start. It runs
now — `tripwire tug` reports 5 constants, 0 unprotected — and `main` is
exercised by a check with the suites stubbed out, so the loop and the restore
are held even though running the real thing takes ten hours.

**And the sweep restores from its own snapshot, not from `rewrite`'s word.**
Found by breaking `rewrite` on purpose to prove a check bit: the undo came from
the same call, so breaking the rewriter broke the undo, and `data/gates.py` was
left on disk holding `TOLL_REFUSED_BELOW = 0`.

**What `tests/test_tripwire.py` is actually for.** Not the table's shape —
harness_guard owns that — but the *measured* half: which suite has been watched
to go red when a given constant moves. A wrong fast path does not fail; it
makes the tool answer confidently. Measured,
`bloom.HEART_HP` halved and doubled ran `bloom` green, `tuning` green — the one
suite that imports the module — and `play` **red**. It had been reported a
survivor while a check sat there holding it.

**The entries cannot be got right by reading, which is the whole difficulty.**
An imports-derived table was tried and was wrong in both directions:
`test_play` imports nothing from `bloom` and guards its heart; `test_tuning`
imports it and guards nothing. So every entry is earned by mutation.
`test_tripwire.MEASURED` records the ones that have been, and a fast path can
no longer quietly stop naming the only suite protecting a constant — a row
whose guard is not in `SLOW` is rejected too, since such a row would prove
nothing. It also found an entry for `declared`, a module that does not exist.

**Swept again after seven cycles of new work**, module by module: wharfage,
parley, abilities, territory, orbits, consorts, autopilot, wayhome. Nothing came
back *unprotected* — but five constants came back "protected only by a suite that
does not name their subject", which is the sweep's other verdict and the more
interesting one. Two of the five were **tautologies I had written myself**:
`parley.WAVERING_AT` was probed at `WAVERING_AT ± 5`, and `abilities.SHED_SHARE`
was compared against a figure computed from `SHED_SHARE`. Three had no check at
all: the seizure rate on a defiant holding, the height tolerance the whole climb
quote stops at, and `autopilot.ACROSS_FLOOR`.
All five are pinned against figures written in the checks now. **And the probes
have to bracket the mutation, not merely straddle the truth**: my first pin on
`ACROSS_FLOOR` used 0.4 and 6 m/s and the sweep still called it unpinned, because
the floor is the larger of that constant and a thruster pulse (0.45), so zeroing
or halving it left both probes on the same sides of the line. 0.7 and 1.5 catch it.

(The tool's own first run reported sixteen and was wrong: it rewrote source
between suite runs while Python served `.pyc` files compiled from the mutated
text, so restores did not reliably take. It runs with bytecode disabled now.
A tool that audits the tests has to be audited too.)

**A screen cannot free the widget that is talking to it.** The rule has cost
three segfaults — a `Card`, a `QLineEdit` mid-keystroke, and a `QComboBox`
whose popup was still delivering the click that dismissed it. Each was fixed
at its call site with `widgets.defer`, one at a time, as players found them.

`View.refresh` closes the class instead. The outgoing widgets are parked on
the view and released on the *next* turn of the event loop, so whatever
emitted is guaranteed to outlive the event it emitted during — whether or not
the call site remembered to defer. (They still do; it is belt and braces now
rather than the only thing standing between a drop-down and a crash.)

And the suite can now catch a signal instead of dying from one.
`tests/popup_probe.py` sends **real mouse events to a popup's viewport** —
the actual path the crash lives on, which `setCurrentIndex` and
`activated.emit` never touch — and runs as its own process, so a segfault is a
failed check with an exit code rather than a dead test run. Verified: backing
the fix out makes it report `exit -11`.

**There is somebody behind the counter.** A quay was a bag of services.
`sim/memory.py` has carried a `port` mind kind since it was written and a
fresh chronicle's store was empty and stayed empty — nothing ever put a person
where you dock fifty times.

`sim/officials.py` splits them in two, deliberately. **Who they are is
derived**: name, temperament and which lever could exist against them, seeded
from the port id, stable for the chronicle, no migration — the rule
`anchorage` and `traffic` obey. **What passed between you is stored**, on the
mind that already persists: regard, memories, levers found, favours running.

The politics is in the ceiling. Trading squarely makes somebody *helpful* and
stops — `DEALING_CAP` is a wall patience cannot climb. Past it you need either
something they want or something they would rather you did not say. Leaning on
a lever works whatever they think of you, costs **more** regard than asking as
a friend (`LEAN_MULTIPLIER`), spends the lever, and drops the ceiling honest
dealing can ever reach again (`CAP_PER_LEAN`) — you can trade your way back
into being useful, never back into being liked. Five favours, each read
somewhere real: a search that does not happen, a wider and richer contract
board, goods at the office rate, a berth regardless, a word before a claim.

**The powers come to you now.** Diplomacy ran one way: six actions, all
player→faction, and the powers themselves did exactly one thing — `drift`,
pulling their grievances back toward a baseline. So the four of them were a
vending machine. You put standing in and took tariffs out, and a captain could
ignore the board for twenty years without anyone knocking.

`sim/approach.py` is the other direction, and its rule is that **every
approach has to be caused**. A power asks for silicon because its own quays
are short of silicon — read off `Market.stock` and restricted to what is in
your hold, because "somebody has looked at what you are carrying" has to be
true. It asks you to denounce the Freeholds because it is losing to the
Freeholds. It warns you off a rival because you have been carrying that
rival's cargo. It offers terms because your standing has passed 62. It levies
your holdings because they are inside its declared space. Nothing fires
because a die came up; the die only decides *when*, among reasons that already
exist. No reason, no envoy — pinned by a check that plays four hundred months
with every trigger dead.

An envoy is something you can be part-way through, so it lives on `Game` with
an `.over` flag and `window.go()` will not let you wander off. Three answers,
each costed in full before it is taken — and **letting the window lapse costs
exactly what refusing costs**, because an offer with a free deadline is a
button that waits forever rather than a decision.

**A body can be worked out.** It used to cap at 95% depleted and then pay a
token tonne a session **for ever** — measured still yielding at trip 199,
identically to trip 20. So a seam never ended, there was never a reason to go
and find another, and a method that works a body gently bought nothing at all:
the cap arrived whatever you did.

`mining.worked_out` ends it, and the four methods finally pull apart. From one
body: `bore` lifts 2.45 t a day and takes 202 t in total; `leach` lifts 1.01 a
day and takes 407. Rate against lifetime, and neither number is visible from
the other, so `mining.prospect` states both — how long the body has left under
this method, and how much is still in it this way. `WORKING_LOSS` calibrates
that forecast against what a body actually gives up, because the midpoint
estimate read 15% high for every method including the one with no mishap risk;
`test_seams` re-measures it so it cannot drift.

**The four ways to run a programme are finally four choices.** Measured,
`push` was simply the best: fastest mean time to unlock — 76 days against
`careful`'s 132 — with its 28%-a-season setback risk *already inside that
figure*, because a setback costs progress and progress is what "days to
unlock" counts. Four approaches on the screen, one answer.

The blurb had named the missing cost from the beginning — *"skip the
confirmations, build on results nobody has replicated"* — and nothing read it.
A pushed result is **provisional** now: the technology unlocks and contributes
`PROVISIONAL_WORTH` (55%) of its bonuses until somebody goes back over the
figures, which costs bench time and no evidence. That is a cost days-to-unlock
cannot see, which is exactly why the dominance was invisible.

Measured after: to two *sound* technologies, `parallel` wins on a full bench
and `copy` on a thin one, and `push` — still the fastest to raw capability —
is the slowest of the four to soundness. No approach is best at everything.

**A near miss on the ground is worth something.** `SPOILED` sat in
`sim/expedition.py` with a comment reading "what a spoiled attempt is worth,
as a share", set to `0.0`, and read by nothing — found by `tests/tripwire.py`,
which is what it is for: a constant already at its degenerate value is either
dead or a feature somebody switched off and forgot.

So every attempt on the ground was all-or-nothing. Missing the mark by one and
fumbling it by five were the same outcome, an officer's level was a cliff
rather than a slope, and the screen — which states everything else before you
commit — had nothing to say about failure but that it might spring a hazard.

A miss inside `NEAR_MISS` now brings back a tapering share: measured, 645
credits for missing by one against 351 for missing by two, and nothing at all
beyond the window. Across every reward type a botch keeps 12–36% of a clean
attempt. The odds line says so — *"17% of the time, about 30% of the prize
still comes back"* — because "it fails" and "it fails and you keep a third"
are different decisions.

**The approach is drawn, and can be flown for you.** The docking mini-game
modelled an error per axis, a drift per axis, a readout blurred by the sensors
and a precision set by the hull and the navigator — and all of it reached the
player as three integers and six buttons. The drift reached them not at all,
so a pilot correcting the worst reading three times running could watch the
other two walk out of tolerance and never be told why.

`ui/approach_plot.py` draws it: range and attitude as a position against the
collar with the tolerance box at the centre, roll as the hull's tilt (a roll
error is not a position and pretending it is would be a prettier lie than the
numbers were), and a ghost showing where the next correction lands — drift
included. `minigames.forecast` is the number behind the ghost, and every burn
button now says what it leaves and which axes it lets slip.

`minigames.autopilot` is the drive computer, gated on the same `doctrine` stat
as the battle computer. It picks the axis that costs most to leave, weighing
how far out it is against where its drift is taking it, and cannot fire harder
than the hull allows. **It is priced**: a computer-flown approach is graded as
a bare clean dock. Measured, it docks about as often as a careful hand — 68%
against 68% — at grade 1.00 against 2.39. Before that cap it matched a good
pilot exactly, which makes an approach a chore to automate rather than a skill
worth having.

**The plot shows what bears.** Everything needed to answer "can this mount
shoot right now" was modelled — `tactical` knows the arc and the bearing,
`Weapon.bears_at` knows the range band, `combat._fire` knows if the magazine
is dry — and none of it was ever shown. It reached the player *after* the turn
was spent, as a log line explaining that the shot had not happened. So a
captain choosing between *come about* and *present the broadside* chose blind
and was told afterwards which had been right.

`sim/firing.py` answers per mount, before the turn: does it bear, is the range
right, is there ammunition, and if not exactly how far the bow must come round
or how many bands to close. The plot draws one wedge per arc, lit when
something in it bears, and the enemy's arcs faintly — sitting in a forward arc
is a decision. `closing_rate` is the other half of a static picture: a range
with no sign of which way it is going. It is the *instantaneous* rate, what
happens if neither hull turns, and is documented as such rather than dressed
up as a forecast the simulation would not honour.

Building it found the game holding **three** opinions on whether a gun can
fire — `_fire` refuses above 0.6, every selector picks only 0.5, and
`assessment` called anything above 0.5 unusable. In practice the gap is empty
(`bears_at` steps 0.22 a band, so penalties are 0, 0.22, 0.44, 0.66), so this
was a landmine rather than a live defect. `CAN_FIRE` and `WORTH_FIRING` name
both, `assessment` delegates, and a check holds the gap shut so widening a
weapon's bands has to be a decision.

**The seats you leave now think.** You are one person on a bridge with three
stations: you take one each turn and the officers hold the other two. What
"hold" meant was literal — `order_id = side.helm_order or "hold"` — so an
unattended helm repeated your last order until you came back to it. Order
*close* on turn one and walk to gunnery, and the helm flew you down the
enemy's throat for the rest of the engagement while a competent navigator sat
there doing exactly what they were told. That is not a hard choice about where
to spend attention; it is a punishment for looking away.

`sim/doctrine.py` is the battle computer. It reads the plane — band, aspect,
heat, hull, what bears — and picks an order for each empty seat, and the
battle screen states which and why **before** the turn resolves.

It is neither free nor better than you. `doctrine` is a stat off the compute
fitting: 0.15 for the wet-stack core you launch with, up to 1.00 for a Cold
Ledger. Below `MINIMUM = 0.30` there is no computer and the old
repeat-forever behaviour stands, which is what every other check in the suite
was written against. Above it the shortlist widens with the rating. And a seat
run by the machine works at the *officer's* rate, not yours — measured, the
computer vents 90% of what you vent sitting there — so choosing a station
still matters. Measured effect: 12.1% of the enemy's hull removed over 24
fights with no computer, 16.9% with an excellent one.

**The Verge is not empty.** Nothing gave another hull a *position*: encounters
were rolled the instant you arrived and thrown away, consorts followed you
implicitly, and faction ventures were a number in a ledger. So the sector
looked deserted in the one view that should look busiest, and "a Concordat
patrol jumped me at Loam Span" arrived with no warning it could have given.

`sim/traffic.py` derives a handful of hulls per system — traders, patrols,
prospectors, couriers, and the occasional unmarked hull — each with a name, a
faction, an errand and a position that moves with the clock along its leg.
**Derived, not stored**, like anchorages: persistent identity with no
migration, at the price that derivation must never touch `game.rng()`, which
advances with the save and would reshuffle the sector on every reload.

The payoff is that the chart *predicts*. `roll_encounter` weighs who is
actually present, so the hull that turns onto you is one you could have
plotted first — by name — and a system with something running dark is
measurably more dangerous to arrive in (18% of arrivals contested against 6%,
same system, same day). Busyness follows the port: a capital works five hulls,
unclaimed space one, and a system the Bloom has eaten fewer than either,
because the traffic left.
