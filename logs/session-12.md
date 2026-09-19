# Session log, part 12 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-30 to 2026-07-30; undated entries keep their original place.

## 2026-07-30 — SEEDFALL: the quay takes its cut, and a third door onto a price (#100)

The purse cycle wired the powers to the sector's own trade and deliberately left
the captain's out. A captain could make a fortune over the counter at a Fleet Hub
the Charter built, maintains and pays upkeep on, and **not one credit reached the
Charter.** So: wharfage, the oldest charge in shipping — a share of the value
crossing the quay, taken by whoever holds it, in and out.

Three things move it, and each one is a decision the player already makes.
**The size of the berth**: an outpost takes 2%, a station 2.5%, a Fleet Hub 3%,
so "where do I trade" stops being "wherever the spread is widest". **What they
think of you**: full relief arrives with the Kin band at 70 regard, and the
Kin-to-Hunted spread is **a factor of four** — standing has always bought a
better price, and it buys a smaller cut now as well. **Whose quay it is**: a free
port is free. Nobody takes anything at an independent freehold or at a Free Port
of your own, which is `exchequer.holdings`' existing rule read from the other
side, and it gives the sector's seven independents a reason to exist on a trade
route.

Nothing crosses the quay in three cases and none of them pays: contraband sold
off the books (the smuggler's edge, in money, for the first time), survey sets —
task #66 records that surveying is already break-even and this would have tipped
it — and services, which are bought *from* a port rather than shipped through it.

**Measured before it was tuned, because "a small rate" is not the same as "a
small change".** A decade of one chronicle: 272 deals, **799,533 across the
counter, 18,359 in dues**, and by the end **41% of everything the Charter held
had come off the captain**. Then the number that actually matters — over the runs
the freight desk itself recommends, the two quays take **11% of what a run
clears**, 10% loading at an outpost against 12% at a station. Felt, and not
punitive.

**A third door onto a price, in a screen a suite exists to guard.** `test_counter`
was written for exactly this defect and its docstring says so: *"a screen that
quotes one number and charges another is the defect this project keeps finding."*
It sweeps `market.quote_buy` against the till. But the market grid on the port
screen was asking neither — it called `world.economy.buy_price` directly, so it
carried neither the grudge bias nor the office rate, **while the comment forty
lines above it claimed "now it is in the quote, and the board says so"**. Measured
with a quiet price in hand: the grid printed 36 and 29 while the counter charged
32 and paid 33. A check that reads the helper can never see this, so the new one
reads the labels out of the rendered grid — and it fails the moment the old call
is put back.

**And the desk was quoting voyages nobody could load.** `freight.voyage` sized a
run by the hold and by the purse and never by the stock on the quay: **12 of 15
recommended runs forecast more tonnage than the port held, the worst by 2.7× — a
287-tonne voyage out of a berth holding 59.** Wrong twice over, because
`worth_flying` ranks by `net` and `net` scales with tonnage, so the ordering was
decided by cargo that did not exist. `trade.buy` has always capped at all three.

**Two more forecasts owned up on their own**, both caught by checks that were
already there, which is the best kind of afternoon:

- The freight desk's card quoted the spread and the fuel and would have left the
  wharfage out — so `voyage` asks `wharfage.due_on` about *both* quays, the far
  one about the port the run actually points at, and the card reads
  "₡54,230 out, ₡140 of mass, ₡3,121 in dues at both quays".
- A cargo contract's card under-quoted sourcing by 542 on 16,640 (`test_cargo`,
  3.3% against its 2% tolerance). `cargo_cost` already split neutral generation
  from the player's quote — a fee cannot depend on who reads the board — and the
  due depends on standing, so it goes on the same side of that split.

`trade.buy` sizes the purchase against price *plus* due now. A hold filled to the
last credit of the posted price and then unable to pay the charge is the same
defect as an approach ordering burns it has no mass for, and there is a check
that holds a purse containing exactly twenty tonnes and watches it buy nineteen.

Nine deliberate breakages, nine caught by the check that should catch each one:
the rate zeroed, the due credited to nobody, the board's sentence deleted, your
own Free Port charged like anyone's, the desk forgetting the far quay, the
purchase sized on the posted price again, the stock cap removed, relief switched
off, the port ladder flattened.

Twelve new checks, 948 across the suite, all green.

## 2026-07-30 — SEEDFALL: two true claims that contradicted each other (#87)

`Lesson.skip_if` — "a watcher that means this is already true" — has been declared
since lessons were written. It was read by nothing, and it was also **set on no
lesson at all**: eight lessons, eight empty strings. Doubly dead.

Why it matters is the option page's own sentence: the tutorial *"can also be
started from the Help screen at any time."* Every watcher compares against a
`mark` taken when its step opens, so a captain two years in who starts the
tutorial is told to "survey one of the bodies here" with thirty surveys behind
them — and has to go and survey another. Every step demanded a fresh action for
something long since learned.

**And then the fix ran straight into a check that says the opposite.** *"A captain
who did it already is not advanced for free"* has been in the suite since the
tutorial shipped: it surveys two bodies, starts the tutorial, and asserts step one
is still to be done. Both claims are right, and from state alone they are the same
fact at two sizes — one incidental survey five minutes ago against two years of
them. So the distinction is the size: `SETTLED_IN_DAYS`. Inside the first month
everything is taught; after it, what the chronicle can show you have done is
stepped over. Both checks pass unchanged, which is how I know the reconciliation is
real rather than a preference.

**Four of the eight lessons carry a skip, and the other four cannot.** The
chronicle keeps *state* — this body is surveyed, this port's prices are in the
register, these systems have been visited, this contract is accepted — and the
remaining questions are *history*: was cargo ever sold, were volatiles bought
rather than mined, was the Ship screen ever opened. It keeps no record of those,
and inventing a counter to feed a tutorial would be the tail wagging the dog. Those
four ask again, which for a step that takes one click is a fair price.

Played: a fresh captain opens at step 1 of 8 with nothing skipped. A captain at day
700 who has surveyed, noted a market and been to another system opens at **step 3
of 8, "2 you had already done"** on the bar, is taught sell, fuel, work, ship and
powers, and has 3 stepped over in all — `helm` goes when its turn comes, because
the skip is re-evaluated after every step and not only at the start.

**A crash found by taking the screenshot.** `MainWindow.__init__` builds the
tutorial bar forty lines in; the bar refreshes on construction and asks
`win.current`, which was assigned *after* it. So opening a chronicle with a
tutorial already running died with `'MainWindow' object has no attribute
'current'` — which is the reload case, a save made mid-lesson. Every check in the
tutorial suite built the window first and started the tutorial after, so not one of
them ever went through that door. `current` and `views` are set at the top of
`__init__` now, and there is a check that builds a window around a running
tutorial.

**And the reconciliation's own number was unguarded, which the harness caught.**
A month is a tuning constant, and `SETTLED_IN_DAYS` went in without a fast path,
so the tripwire's guard failed the run: the only suite that could speak for it —
`tutorial` — was on the excluded list *for building a window*. That exclusion is
supposed to mean "too expensive to run per constant", and this suite sets the
offscreen platform itself and takes **two seconds**. Off the list, and its
verdict measured rather than assumed: zeroed and halved are both caught by the
check above, and **doubled was caught by nothing** — the veteran stands at day
700, so two months would have passed while a captain a season in was still being
sent to survey another body. So the month is bracketed from both sides now, by
one captain at two days apart: a week in, nothing is assumed; six weeks in, the
survey counts. Whatever the number is, it lies between them, and all three
degenerate values fail.

That leaves **one entry on the dead-field allowlist**: `commodities.Commodity.cat`,
which is display metadata for a grouped market board and is deliberately not read
by the sim. Every other field in `data/`, `sim/`, `world/` and `core/` — 1,192 of
them — is consumed by something.

Four new checks, 936 across the suite, all green.

## 2026-07-30 — SEEDFALL: somebody on the ground at last (#99)

Measured at turn zero, and it has been true since the sector was written: **161
bodies across 42 systems and 0 settlements.** The player could plant a colony and
no power ever had, so every trade in the Verge happened at an orbital berth and a
world rich in phosphate was a number on a survey screen. The economy had one half.

The powers settle now, out of the treasuries the exchequer cycle gave them, on
bodies in systems they hold whose grades are worth working. A settlement is
deliberately **not** a player colony — `data/colonies.py` is player-shaped, with
build costs in the captain's materials and works to commission, and reusing it
would have an NPC power paying biomass out of a hold it does not have. A
settlement is four facts: whose it is, which body, what the ground gives, and how
long it has been growing.

Played, five years: **4 → 13 → 23 → 40 → 59 settlements** across 21 systems, all
four workable goods, purses still bounded, berths still going up. And the market
knows, which was the point:

    ore        32 where it is worked   against  43 where it is not
    volatiles  32                               38
    biomass    57                               64
    phosphate  310                              362

Both directions, too: a settled system is **hungrier** for everything its people
do not make, so it is somewhere to carry cargo *to* as well as from. The effect
goes through `industry.industrialise`, the single writer of `Stock.works` — that
field began as "what the holder of this berth was licensed to make" and means
"what is made here" now, whoever is making it, so a licence and a settlement in
one system compose instead of overwriting each other.

**Three defects, and the first two are in work I wrote in earlier cycles.**

- **Price is not value, and the exchequer chose by price.** `_invest` took the
  cheapest affordable work — and the equilibrium the upkeep curve is built on
  means the cheap works never pay: promoting an outpost to a station adds 90 a
  day of yield and 90 of upkeep, *net nothing*, and a hub is 60 a day worse than
  not bothering. Founding a berth clears 60; settling clears 32. So the rule
  bought both no-return works before either paying one, and the powers planted
  **six settlements in year one and none in the seven years after**. It sorts by
  payback now, never-pays last by cost — which is what a Fleet Hub actually is:
  the thing you buy with money you have nothing better to do with.
- **`Body.id` is the body's index within its system.** 155 bodies share **six**
  distinct ids. My first `on_body` keyed on `body_id` alone, so six settlements
  masked the entire sector and `sites_for` went from twenty-odd candidates per
  power to zero. `Colony` has keyed on the pair since it was written — the
  precedent was there to read.
- **A quoted payback has to count the years the thing loses money.** A settlement
  manages 25% of its output on day one: 11.5 a day against 14 of upkeep, so
  **−2.5**. Two fresh ones moved a power's income *down*, 724 to 720 — which is
  the opposite of what my check asserted, and the check was wrong rather than the
  code. Cost over the mature rate reads 1,000 days; integrating the ramp gives
  **1,485**, and that difference decides whether settling beats founding a berth.
  `settlement.payback_days` is the one door and the exchequer asks it.

The system view says who lives on a body — *"Charter · works ore · established, 2
years in"* — the powers' ledger carries settlements and what they pay, and the
ship's log fills up with *"Dry Choir: people are on the ground at Thule Crossing
II, working phosphate."*

**And one more, in a check rather than the code.** Settling moved a berth's
supply mid-flight and the industry forecast check went 26% out, so I excluded
systems that gained a settlement during the measurement — and it was still 27%
out at one berth. The cause was not settlements at all: a `dumping` shock (×1.9
supply) had been live when the forecast was taken and had lifted by the time the
price was read. The comment I wrote on that check last cycle says the measurement
is taken "over the berths where alloy is not under a shock **at either end**", and
the code only ever checked one end. Both ends now, and the worst forecast is back
to 5% across 13 berths.

Eight new checks, 932 across the suite, all green.

## 2026-07-30 — SEEDFALL: what you can make sense of on the ground (#94, finished)

`Lifeform.metabolism` was the identity key behind the two strings the survey
screens print, and **nothing read the key itself**. A radiotroph and a
photoautotroph were the same row with different words; the catalogue could not
group by anything; and nothing asked whether the captain had any business
understanding what they were looking at. `test_declared` had carried it for
cycles with the reason *"a catalogue that groups by metabolism is wanted and the
tech tree has a branch of that name to match against."*

The pairing is not invented — each of the eight biochemistries goes to the node
that *is* that biochemistry, and the tree's own names give it away:

    photo    photoautotroph   ← Photosynthetic Intima      0 pts
    thermo   thermophile      ← Radiator Bloom           140
    halo     halophile        ← Water Refinery           160
    chemo    chemolithotroph  ← Mineral Gut              320
    crypto   cryptobiont      ← Trehalose Cryptobiosis   500
    methano  methanogen       ← Sabatier Loop            500
    radio    radiotroph       ← Deinococcus Repair       540
    piezo    piezophile       ← Piezolyte Physiology     880

Four are exact: the Sabatier Loop makes methane, trehalose vitrification *is*
cryptobiosis, piezolyte physiology is what a piezophile has, Deinococcus is the
radiation organism. **Two of the eight are legible on day one** — the mechanic is
neither off nor already won at the start, and the exotic ones are worth saving up
for.

**A specimen is worth more to somebody who can read it.** Catalogue a piezophile
with no piezolyte physiology and you have a jar of tissue: it counts, it goes in
the register, and it yields 60% of what it would to a bench that can say what it
is doing. Measured on the same body: **18 points unread, 30 read**; on the same
whole catch, **116 against 149**. Which closes a loop that was already half built
— `data/inquiry.py` has the metabolism branch of research running on 60% specimen
evidence, so the specimens fund the branch that explains the specimens.

**A layer that cannot ask who is looking should not price what it finds.** The
research for catalogued life was added inside `world/planets.survey_body` as
`lf.value * 0.25`, in a package the layer rule forbids from seeing the `Game`. It
moved to `sim/biology.harvest`, which is the only place that arithmetic lives now,
and the bare constant went with it.

The catalogue is a new codex tab (`ui/life_panel`): every organism you have
catalogued, grouped by biochemistry, deepest column first, each saying whether the
bench reads it or what it would take — *"Piezolyte Physiology · 880 points"* — and
what a specimen of it is worth. Played it: **28 organisms across 8 of 8
biochemistries, 8 read and 20 not.** The body screen's biota lines carry the same
line, and the survey debrief says how many went into the register unread and in
which biochemistries, because a captain who knows they are leaving value on the
ground has a reason to come back.

**Two things found by looking rather than reasoning.**

- Grouping by the key is how you find out the key was lying. `FORMS` is a pool of
  body plans — "jointed swimmer", "plated crawler" — and one entry was
  **"chemotrophic reef"**. The generator picks the form and the metabolism
  independently, so it had been filing a chemotrophic reef as a photoautotroph
  since lifeforms were written, and nobody could see it until the catalogue put
  the two beside each other. Renamed, with a check that no body plan contains a
  biochemistry stem.
- The biota line read *"nobody aboard can read it — mineral gut would, at 320
  points"*. `str.capitalize()` lower-cases everything after the first character,
  so a technology's name was printed in lower case on the screen telling you to go
  and research it. There is a check that every such line spells the node exactly
  as `data/tech.py` does.

And `test_declared` fired its stale-excuse arm the moment the field started being
read — *"ALLOWED still excuses fields that are now read — delete the entry"* — for
the second cycle running. That arm has now caught three fields on their way out.

Seven new checks, 924 across the suite, all green.

## 2026-07-30 — SEEDFALL: two guards excusing each other, and the mesh that was waiting

**A 21,000-credit module and an 18,000-credit colony did nothing at all**, and the
reason is the most interesting thing this cycle found.

`test_grants` asks whether every colony effect is read *by name* somewhere.
`test_declared` asks whether every declared field is read. The CHORUS Node's
`drift` effect passed the first because `sim/ship.py` contained the string
`"drift"` — where the only thing it did was set `Stats.has_drift` — and
`has_drift` passed the second because it was on the allowed list as a flag waiting
for somebody to decide what drift *was*. So the colony effect counted as consumed
*because* a dead ship stat mentioned it, and the stat was excused *because* a task
promised to get round to it. **Each guard was satisfied by the other's hole.**

Both descriptions promise the thing plainly:

    module:  "reconciling against every other node in the mesh"
    colony:  "Reads the traffic: other hulls in this system stay plotted."

And the implementation was already there, unasked. `sim/traffic.in_system` is a
pure function of the sector and the day — it has always been able to derive the
hulls working *any* system — and every caller in the game passed the system the
ship was sitting in. So the module's own docstring complaint stood unanswered: *"a
Concordat patrol jumped me at Loam Span" arrived with no warning it could possibly
have given.*

`traffic.plotted` and `mesh_reaches` are the gate now. You see the system you are
in; a CHORUS Node aboard reports from systems you have actually stood in, because
the mesh needs something of yours to reconcile against; and a Node planted in a
system holds that system whether or not one is aboard. `colony.drifting` is written
beside the existing `colony.watching` rather than as another key published into
`effects()` — that function's own docstring warns that a published key nothing
opens is where a dead effect hides, which is exactly the trap I had half-written
before rereading it.

The payoff is on the chart. `ui/mesh_panel` lists what the mesh is hearing —
measured on one chronicle with a Node fitted and fourteen systems visited: **13
systems reporting, one hull running dark at Thule Watch**, sorted so trouble reads
first. And the sector chart marks that system in red before you commit to the jump,
with the legend entry to say what the mark means. Five checks hold it, including
the one that matters: **every hostile count the chart warned about was what was
actually waiting on arrival.**

Also this cycle: **#101 closed as a wrong diagnosis of my own.** Last cycle I filed
a task claiming the orbit law was spending thousands of metres a second flattening
inclined arrivals into the xy plane. Measured across two sectors and seven bodies:
`h = r × v` has `hz/|h| = 1.000` and the plane-change delta-v is **0.0 m/s**
everywhere. The galaxy is generated flat. Two further hypotheses went the same way
before I stopped — the hull is not stuck slewing (3–138 slew ticks against
thousands of burns), and the arrival at a small body is at 38% of circular speed,
a plunge rather than an orbit. I had reached for an explanation that fitted the
shape of a trace without measuring the quantity it named, and the honest end of
that is a closed task saying so rather than a fix for something that is not
happening.

The other half of #94 — a lifeform's `metabolism`, which groups nothing — is left
open with the work I did on it recorded: the eight metabolisms pair honestly with
techs the tree already has (Sabatier Loop ↔ methanogen, Trehalose Cryptobiosis ↔
cryptobiont, Piezolyte Physiology ↔ piezophile, Deinococcus Repair ↔ radiotroph,
Photosynthetic Intima ↔ photoautotroph, Mineral Gut ↔ chemolithotroph), so what
you have researched decides what you can make sense of on the ground. That is a
table, a sim door and a codex grouping, and it is a cycle rather than an
afterthought.

Five new checks, 917 across the suite, all green.

## 2026-07-30 — SEEDFALL: the guard that did not exist, and the option that was a lie

Two things this cycle. The first is a correction.

**#101 was filed on a wrong diagnosis, and is closed as one.** Last cycle I
claimed the orbit law was spending thousands of metres a second flattening
inclined arrivals into the xy plane, because `_across` returns `[-py, px, 0]`.
Measured: **every arrival in the game is already in that plane.** Across two
sectors and seven bodies, `h = r × v` has `hz/|h| = 1.000` and the plane-change
delta-v is **0.0 m/s** everywhere — the galaxy is generated flat. The fix I
proposed would have been a no-op with extra arithmetic.

How the error was made is the part worth keeping: I saw the spiral experiment
descend into the ground, saw `main=True, throttle=1.00` with the burn axis
changing every sample, and reached for the explanation that fitted the *shape* of
the trace without measuring the quantity it claimed. Two more hypotheses went the
same way before I stopped — the hull is not stuck slewing either (3 to 138 slew
ticks against thousands of burns), and the arrival at a small body is at **38% of
circular speed**, a plunge rather than an orbit, which is why circularising is
what costs. The shipped law works; I stopped rather than keep re-deriving a
control law by trace-reading, and #102 keeps the measurements.

**Then #90, which turned out to have a real defect under it.**
`sim/options.py` opens with the project's rule pointed at a screen that usually
escapes it — *an option that changes nothing is a lie* — and then says: *"Every
field below is read somewhere, and `test_options` fails if one stops being."*
**There was no `test_options`.** The module named a guard that did not exist,
which is the same untruth one level up: a claim about the code rather than about
the game.

So this is that guard, and it asks the strong form. "Is the name mentioned
somewhere" is nearly worthless — a setting can be read into a variable nothing
consumes, which is the defect this project has found more often than any other.
Each of the eight settings is turned on and off and something a player would
notice has to differ: the window stops asking, the explanations disappear, an
open instrument moves from 400 ms to 1,500, the chronicle is written at once at
zero days and not until day 21 at twenty, the three speech settings each push to
`core/llm` and the other five do not, the tutorial is offered only with its switch
on.

**Writing it found that one option very nearly was a lie.** "Inline hints" was
gated in exactly one place, `View.hint`, called **10** times against
`widgets.note`'s **270** — and the options page describes the setting as "the
short explanations under panel headings", which is precisely what `note` draws.
Measured on the port screen: **89 labels with hints on, 89 with them off.** The
switch turned off 3.6% of the hints.

`note` reads `widgets.HINTS` now, pushed in by `MainWindow.apply_options` — whose
docstring already said it exists to push settings into the parts of the window
that hold their own, the same arrangement `core/llm.py` uses. Port screen after:
**89 → 82**, and the market table untouched.

Two details that cost a draft each. A withheld note returns a **hidden label, not
`None`**: `Panel.add` skips `None` happily, and the fifteen places that add a note
straight to a layout answer it with *"cannot add a null widget"* — where a hidden
widget is excluded from its layout and takes no space, so all 280 call sites work
unchanged. And `widgets.HINTS` is module state for the life of the process, so the
check that turns hints off **restores them in a `finally`**; without that, every
suite running after it would render without explanations and some unrelated check
would fail a long way from the cause.

Three of my own errors in the checks, all found by running them: I stubbed
`win.confirm` in the fixture and then tested the stub; I asserted the voices
switch through `llm.enabled()`, which asks whether a provider is *answering* and
is False on a machine with no model however the switch is set — so the check now
watches the *push* instead; and I called `offer_tutorial(game)` when it takes the
window. Also a `QApplication` I did not hold a reference to, which took its
`MainWindow`'s C++ object with it and aborted the process on the next Qt call.

Eight new checks, 912 across the suite, all green.
