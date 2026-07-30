# INTERFACE.md — SEEDFALL navigation map

The top-level map of the game. Read this before opening any source file in
`seedfall/`.

## What this is

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

**Which numbers are actually held in place.** `tests/tripwire.py` changes
every module-level tuning constant in the game — zero, double, half — and
reports the ones no check notices. A survivor is dead, tautologically checked,
or genuinely unpinned, and all three are worth knowing. The clean run: **60 of
131 unprotected**, the worst being `approaches.ODDS_PER_DAY`, which retires
the entire envoy system in silence when zeroed. `tests/test_tuning.py` pins
the worst of them, always against a figure written in the check and never
against the constant under test — the mistake this whole apparatus exists to
stop.

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

**Flying is done in days and AU; berthing is done in metres a second.** The
helm moves the ship body-to-body: pick a target, pick a burn, lose a week of
calendar, arrive. That is the right grain for a transfer and no grain at all
for the last ten kilometres, where the only question is whether you can match
velocity with something before you hit it. Nothing in the game modelled that.

Three modules, and two pop-out windows, do now.

`sim/track.py` makes everything in a system a `Contact` whose position is a
function of the day — bodies, quays, traffic, and a bare point in empty space
you simply want to be at. Because position is a function of the day, a track
runs *backwards* as well as forwards, and a burn can be solved for an arrival
**date** rather than only for "as soon as possible". `windows()` sweeps the
horizon, because a moving target is not equally dear on every day and waiting
is often cheaper than burning. Every cost comes back through `flight.route`
and `flight._leg`, so a plot cannot disagree with what flying charges; for a
body, `solve` *is* `flight.intercept`.

How much of that can be believed was measured rather than asserted. Over 735
predictions across ten chronicles, four systems and horizons out to 270 days,
**99.9% came true to the digit** — `traffic.in_system` is pure in the system
and the day, so asking it about a future day *is* the forecast. Every failure
was the Bloom crossing a threshold in `traffic` (0.15, where raiders can draw;
0.2, where a system loses a hull) and redrawing the errands. So `confidence`
is causal: it projects the growth forward and asks whether a crossing falls
before the arrival, rather than decaying with time for its own sake.

`sim/conn.py` is the close-quarters frame — kilometres, metres a second, and
a minute a tick. Reaction control for fine work, the main drive for closing
distance, `mu` taken from the body's own `radius_km` and `gravity` so a heavy
world genuinely demands a faster orbit. `sim/autopilot.py` is the computer
that flies it, split off along a real seam: `conn` says what the ship does
when you fire a thruster, `autopilot` says which thruster a competent pilot
would fire.

Four faults, all found by flying rather than reading:

- **The closing rate was wrong by a factor of a thousand.** `pos` is in km and
  `vel` in m/s, so `pos·vel / r` is already a velocity; the first draft
  divided by another thousand "to convert". The panel read **+0.01 m/s while
  the ship flew in at twelve**, the autopilot believed it, and every approach
  ended in the hull. A unit test on `closing` would have seen a plausible
  number and passed.
- **The computer managed the closing rate and ignored the rest of the
  velocity.** Motion across the line of sight does not change the range at
  all, so it reported itself perfectly on profile while sailing past — it hung
  at 1.7 km circling a hull, or went into a quay sideways at 12 m/s.
- **A body approach opened twelve kilometres from the planet's centre**, which
  is several thousand underground; `mu / r²` there threw the ship out of the
  system at eleven thousand kilometres a second.
- **The orbit band was a percentage.** A tenth of circular is 500 m/s at a
  middling world — forty burns — and wider than the whole orbit at a rock.

`ui/viewport.py` paints what a camera sees: six of them, and the target's
angular size *is* the range instrument, read the way a pilot reads a window.
The starfield is fixed at import, because a field drawn from `game.rng()`
would both shimmer between repaints and quietly advance the save's seed — the
docking instrument was bitten by exactly that. `ui/conn_window.py` is the conn
itself; `ui/plot_canvas.py` and `ui/plot3d_window.py` are the plotting board,
with zoom, pan, tilt, selection, tracking, and an arrival-date slider.

**And then it had to actually happen.** The conn shipped as a sandbox. Asked
this project's most productive question — *is everything it declares
consumed?* — the answer was nothing at all. Measured on a fresh chronicle:

    flew into Fleet Hub at 20 m/s  ->  collision, damage 50.0
    berthed alongside              ->  0.54 t of reaction mass, 0.8 h elapsed
    day 0 -> 0 · fuel 20 -> 20 · hull 336 -> 336 · where None -> None

You could wreck the ship against a station and walk away, berth alongside a
quay and not be docked, and burn a tank the hull never had — the conn invented
36.8 t of reaction mass for a ship carrying 20.

`sim/berthing.py` is where it lands. The tank is the ship's `volatiles`;
`commit` charges what was spent, advances the clock, applies the damage, and
writes `orbit_body` — which is what every other screen reads to know where the
hull is standing. It is idempotent and is called when the approach resolves,
when the captain breaks off, and when the window closes, so nothing is ever
flown for free. `can_conn` is the gate: measured, the distance from the ship
to a contact is bimodal — **0.000 AU at your body, 2.2 AU or more otherwise** —
so the threshold sits in empty space and the check holds the rule rather than
the number.

Wiring it up surfaced two more, both from playing:

- **Impact damage was linear and capped at 80**, so lithobraking into a world
  at five kilometres a second cost sixty points of three hundred and
  thirty-six. Energy goes as the square of the speed and so does the damage
  now, uncapped — 8 m/s is a scrape, 20 m/s takes half the hull, 45 m/s ends
  the chronicle.
- **A fast approach passed straight through its target.** At 45 m/s the ship
  crossed 2.7 km in one 60 s tick and went clean through a station 400 m wide
  between two contact tests — reported *adrift*, no damage. Since the curve is
  quadratic, the most dangerous approaches were precisely the ones escaping.
  `_sweep_min` tests the whole path now, not its endpoints.

**A station you could see and could not use.** Two reports from a player, and
one cause. The Fleet Hub was drawn on the helm chart, labelled, and inert:

- **"Set course" did nothing.** The button reads "Set course — 4 d, 2 t" and
  its tooltip says "Fly to Fleet Hub"; it called `course_to`, which only
  *aims* the helm — and a quay's body is very often the body already
  targeted, so it set what was already set. Clicked and measured: target 0 →
  0, orbit_body None → None, day 0 → 0, fuel 20 → 20. It flies now.
- **The Hub could not be clicked.** The painter drew its mark 11 px off the
  planet; the hit test only walked `system.bodies` with an 18 px radius, so a
  click on the station landed on the world underneath — usually already
  selected, so nothing appeared to happen. `QUAY_OFFSET` is one number now,
  read by the painter and the hit test alike, and quays are tested first.

**A conn that teleported, and one that did not notice being flown.** Two more
player reports, both about the window losing touch with the ship.

*Close and berth* ran four hundred ticks **inside the click**: the hull
arrived and the result was reported, which is exactly what a conn exists not
to do. The mode is held now and one tick is flown per beat of the same clock
the coast button already used, so a berthing takes the forty minutes it takes
— measured, 39 ticks and 39 minutes — and can be watched, corrected, or called
off half-way by pressing the button again.

And a course set at the helm moves the hull, while the conn was built around
wherever the ship stood when it opened — so it went on showing an approach on
somewhere the ship had left. It compares where the ship is against where it
was on every refresh, and reopens on whatever is alongside now.

**The broadside you ordered, and the sky you were flying in.** Two halves of
the same complaint: the game resolved things and then did not show them.

`combat._fire` resolved a shot and wrote a sentence. By the end of a turn all
that survived of a salvo of seven was seven lines of prose — no record of what
fired, from where, at what, or whether it connected, so nothing could draw it.
`sim/gunfire.py` keeps the shots: one per attempt, **including the ones that
never left the tube**, because "the lance will not train that far" is exactly
the thing worth seeing rather than reading and it is the whole argument for
coming about. `ui/battle3d.py` draws them — beams, tracers, seeking rounds on
a curve, impact flashes sized by what they did — from a camera behind and
above your own hull. The general check ties the record to the resolver:
**2,138.9 of damage recorded against 2,138.9 taken** over six chronicles.

Refusals had to be *constructed* to test. `_salvo` pre-filters to the mounts
that bear, so eight full engagements produced 285 shots and not one refusal;
the check finds the geometry by asking the sim's own predicates rather than by
placing hulls at angles guessed at.

And a player reported that taking the conn with nothing in reach showed
nothing at all. It did: the windows drew the approach target and a fixed field
of stars, so with no target there was only the field. Measured, standing off a
body at 0.40 AU, **the system's own star subtends 1.34°** — two and a half
Suns — and was not being drawn. `sim/sky.py` gives an approach the rest of its
system, placed in the approach's own frame at the size it really has, and
`conn.observe` opens the conn with nothing to approach at all, because a
captain can always look out of a window.

That exposed the one place the flight model's simplification shows. An
anchorage's position in AU *is* its body's — which is why no screen needs a
special case for flying to a quay — and asked what the sky looks like *from* a
berth it answered that the planet was at zero range and therefore 180° wide,
which is a picture of being inside it. Co-located sights are placed where they
physically are: the world below a berth reads 98° across.

**Screening that actually screens.** `ConsortOrder.shield` was one of the eight
dead fields below, and the allowlist entry I wrote for it claimed it had already
been wired. It had not — a false reason inside the field meant to prevent false
claims, and nothing checks the reasons.

The order promised "draws fire that would otherwise land on you, and takes it on
a smaller hull" and delivered only the first half: measured, the flag took 228.5
with two escorts screening against 223.6 flanking, while the screens lost 36 more
hull. A pure cost.

`consorts.interception` is the fix: a hull genuinely between wears
`shield × SHIELD_SHARE` of each blow *before* the flag's armour, landing it on
its own layers, saturating at `SHIELD_FLOOR` so six screens still leave the flag
wearing 45 of every 100. At forty seeds screening saves the flag 26% (95 against
flanking's 128) for 19 more hull off the escorts.

Two things were tried and taken back, both worth recording. The screen's station
was moved off the **midpoint** on the reasoning that a midpoint cannot be held —
measured under one method the midpoint is better (95% of alive turns against
85%), because it is *on* the line by construction, so the change was reverted and
a claimed 21%→82% improvement withdrawn as a comparison of two different
measurements. And the armour floor turned out to erase interception: flooring
against the weapon's *nominal* output means the part a screen absorbed never
reaches the comparison (at 34 armour, 26.5→21.6 flat against 26.5→15.1 scaled).

The first mutation sweep ran 7/12 and every miss was the same fault — testing a
mechanism with an aggregate something else dominates. Discarding interception's
answer entirely passed a forty-seed engagement comparison. The checks are single
blows with constructed geometry now, where 72 unscreened − 50 screened = 22 worn
balances to the tonne.

**Eight things declared and read by nobody.** `test_reachable.py` asks this of
functions; asking it of **data** is the richer seam. Every field on every
dataclass in `data/` against whether anything reads it: **eight that nothing
does**, several with docstrings asserting they mattered — `luminosity` "drives
how hard the light falls on everything else" and drove nothing; `halo` was the
corona colour and the corona was drawn in the disc's; `boredom` was "what that
costs in morale" and `morale_tick` had no lineage term at all; `time_sense` was
a written line nobody had seen. Two of the eight were mine, from the
star-catalogue cycle.

A dead field is worse than a missing one: it reads as a feature, gets quoted in
the prose beside it, and promises behaviour the game does not have.

`tests/test_declared.py` is the guard. It fails on any unread field in `data/`,
with an allowlist carrying a **reason per entry** — an allowlist used to dodge
work is the anti-pattern; one with a written reason is how "known and
deliberate" gets said. It also fails when an entry names a field that has gone,
or one that *is* now read, so excuses cannot go stale. The scan counts
`getattr(x, "name")` as a read: without that it cried wolf on `System.star` and
`Target.berth`, and a guard that cries wolf is worse than none.

Four wired, each differenced: `conn.star_lum` carries the star's brightness as
a *fact* (the way `star_dir` carries the light's direction) and `viewport.glare`
decides how many stops to show — a fourth root, since the raw range is five
hundred to one and a screen has four. Measured M 293 → A 324 on the brightest
tenth, 1.48x per lit face. Coronae now use `halo`. `crew.tedium` puts a
lineage's boredom into morale over a crossing: same voyage, wet 0.770 against
dry 0.920. And `crew.how_it_feels` says the line, above a threshold set from
354 measured crossings rather than picked (a first draft's 30 days meant it
almost never appeared).

**The bench after the tree.** The tech tree is sixty-two nodes and 28,790
points end to end, and the game carries on past every one of its ten endings. So
`research.banked` grew for ever once `researchable` came back empty — **146,040
points over the ten years after the tree closed**, on a screen that displayed
the figure and no code that could spend it. Found by asking whether every
declared thing is consumed.

`sim/programmes.py` gives it somewhere to go. A programme opens when its
*branch* is exhausted, never finishes, and completes rounds each
`ROUND_GROWTH` = 1.4 dearer than the last, so a finished tree cannot become a
fountain (eight rounds: 1,100 points to 11,595). Each round yields a **finding**
that buys standing or credits and never a better hull — an endgame bench that
improved the ship would only inflate it. Three doors, each consuming it: file
with one power, publish to all four, or sell. `PUBLISH_SHARE` = 0.45 keeps the
choice real: filing wins with the power you file with (+24.2 against
publishing's +10.9) and publishing wins on the sector total (+25.1 against
+22.2).

Two bugs, both the same fault the feature exists to fix wearing a new coat.
`research.take_spare` zeroes what it hands over — so a day's work cannot be
spent twice — and `clock` called it unconditionally, meaning a bench standing
down **destroyed** every point the tree could not use; there is a `can_take`
gate before the taking now, and 1,833 points are correctly held where the first
draft held none. And `programmes.state` attached the bench to the game as a
plain attribute, so a reload came back empty: the save codec encodes *declared
fields and nothing else*. It is a declared field on `Game` now.

**Gravity that knows which star it is, and an orbit you choose the height of.**
Two player reports, one system, and the second was the bigger fault.

`flight.period_days` was `YEAR_AT_1AU · a^1.5` — Kepler's third law with the
`sqrt(M)` left out, so **every star in the sector weighed exactly one Sun** as
far as its planets were concerned and a world at one AU took the same year
round a 0.32-solar M dwarf as round an A-type nearly six times heavier. It now
takes the star's `mu` as a *required* argument (a default is how half the call
sites end up quietly assuming the Sun), `StarClass` carries `mass_solar`, and
`starclasses.mu_of` is the single door. Measured: **645 days at one AU round an
M dwarf, 272 round an A-type, 129 round a black hole**. Black holes are new —
eight solar masses in a 23.6 km event horizon — and safe to add because a
galaxy is *stored* in the save, so an existing chronicle keeps its sector.

And there was one orbit, wherever the transfer dropped you. `sim/orbits.py`
now holds a ladder whose middle rung is `targets.approach_range` **exactly**,
so a transfer arrives at the standard orbit and low and high are each a real
piece of flying. The trade is geometry rather than invention: escape speed is
`sqrt(2mu/r)`, so `departure_factor` makes low **1.3–3.6× dearer to leave**
than high, and `look_factor` gives it correspondingly better resolution on a
survey. `heights_for` withholds rungs the hull cannot hold — a four-kilometre
comet has a 2 m/s orbit and a thruster pulse is half a metre.

**And it asks a second question now: can the tank pay for the climb.** It could
not, and nothing else did either. `climb_dv` prices a rung at
`|v_circ(from) − v_circ(to)|`, the cost of a thrust-limited spiral, and the conn
compares it against the metres a second in the tank. Flown before the gate
existed: **every high rung at every body was offered and not one was reachable**
— 25 to 264 tonnes of reaction mass against the 20 t a captain opens with — so a
captain found out by spending the whole tank to arrive at 63–76% of the height
with nothing left to leave on. The tank is volatiles in the hold, so the refused
rung is shown with its price rather than hidden: **a high orbit is a fuel
decision**, and a captain who wants one goes and buys the mass.

The control law took four attempts, and three of the failures looked perfectly
reasonable written down: a radial rate (you do not raise an orbit by thrusting
outward — 877 m/s of climb, ballistic, then aground); excess tangential speed
with a *zero* radial demand (a contradiction that cancelled the rise it had
just made); and vis-viva re-solved every tick, which is elegant and needs no
constants but only ever burns prograde at the ship's current position, so it
raised apoapsis for ever and never periapsis. What works is **round it off,
then move it**: circular speed at the current radius drives eccentricity to
nothing with no second branch, and the vis-viva transfer runs once it is round.

Two real bugs sat underneath, both fixed rather than tuned around:

- **A hull could not reverse.** `attitude.turned` sweeps the shortest great
  circle, and to a point *exactly* astern there is no shortest one — the
  perpendicular component is zero and it returned the nose unchanged. So
  `conn.apply` spent every tick slewing, the slew moved nothing, and no thrust
  was delivered. Nothing asked for a reversal until the orbit computer did.
- **`worth_turning` ordered the main drive for thruster work**, predicting 2.4
  ticks for a turn the hull measurably could not finish.

And three screens disagreed with the sim the moment `in_orbit` learned to judge
the **ellipse** rather than the instant — all the same fault, an instantaneous
question about something only true at an apse. `orbit_note` called a completed
orbit "a departure, not an orbit"; `instruments.readout` marked 9,123 m/s amber
on five of twelve approaches, the speed the ship had just got right; and
`adrift` was measured against the range the approach opened at, so climbing to
the high orbit the screen had offered read as losing the target astern.

**Adding one star class re-rolled every sector, and five checks fell over that
had been passing on seed luck** — the most useful thing this cycle turned up.
None was measuring what its name claimed: `test_politics` read "the Concord is
not always reachable" off a one-in-twenty tail (now a differenced claim,
determined 20/20 against idle 0/20); `test_bloom_arc` measured provoked growth
in a single galaxy where the effect wins in seven sectors of eight (now
aggregated over eight, tally reported); `test_officials` looped five favours at
one desk, asked the first, and claimed two — asking *spends* regard, so only one
is ever reachable per chronicle (one official per favour now, all five asked);
`test_counter` checked that a one-shot office rate expires by
comparing the board against the price posted *before* the deal, when buying
moves the board (36 to 37 on two tonnes of ore) — now measured against a
control chronicle that bought the same and never asked; and the conn preferred
a stranger's hull to the world it was orbiting.

The conn's default target rested on a premise this work removed. It ranked
`anchorage, hull, body` because "approaching what you are already orbiting is
not a manoeuvre" — which stopped being true the moment an orbit had a height
you could choose. With bodies on real orbits a passing freighter was often the
nearest thing in the system, and the conn opened on it while the hull sat in
orbit round a world it was not being shown. `default_target` now prefers
whatever is **co-located with the ship** before anything else in the system.

`sim/conn.py` went past five hundred lines and **how an approach ends** came
out into `sim/outcome.py`. The seam is real: `conn` answers what the ship does
when a thruster fires, `outcome` answers whether the approach is over. Three
of the four outcomes are about a distance; the fourth is not, and asking about
an orbit at an instant is the mistake that took four control laws and three
contradicting screens to find. The thresholds stay in `conn` and are passed
in — a constant written twice is the fault this project has hit most often.

**It went past five hundred again**, and the forecast came out into
`sim/preview.py` for the same reason and along the same seam: `conn` is the act,
`preview`, `instruments` and `outcome` are what is said *about* the act. It is
one idea — fly a throwaway twin and report what it ends up with — and it is the
part that had just been caught lying, so it earns its own file. `_rotate` became
`conn.rotate` on the way out: `autopilot` had already been importing the private
name, which is usually the tree telling you something belongs to more than one
caller.

**A sky with eight kinds of star and seven of world.** The sky then had *one*
star and *one* world, painted different colours. Eight spectral classes have
existed since the game was written — M dwarf, K, G, F, A, binary, white dwarf,
neutron star, each with its own name and tint on the chart — and every one was
drawn as the same 695,700 km ball, because `sim/sky.py` held one number for a
star's size and never asked which star. `data/starclasses.py` gives each its
real radius and luminosity: **104,355 to one**, a 12 km neutron star against
an A-type at 1.8 solar. The data already said which was which.

`data/worlds3d.py` does the same for bodies, on one idea — **latitude**.
`by_latitude(paint)` colours a sphere's bands by how far up them they sit, and
that one hook is the whole vocabulary: `capped()` gets polar caps for nothing,
`banded()` varies the bands into a gas giant, and `ring_disc()` is a flat
annulus of concentric bands. Rings are drawn in two halves — the far arc
before the world and the near arc after it — because a flat annulus
interpenetrates the sphere it circles and painter's algorithm has no answer to
that. Which giants carry rings is derived from the body's **name** in
`sky.has_rings`, so a ringed world is ringed in every chronicle from that seed
and there is nothing to save.

`tests/test_worlds.py`, `test_sky_kit.py` and `test_lighting.py` (10 checks
between them) measure all of it in pixels rather than asserting it from the
table that made it. Three lessons:

- **The first "do these look alike?" measure was measuring the background.**
  A 6×6 grid of mean colours over the whole plate, three quarters identical
  black sky — it reported seventeen pairs rendering alike. Over lit pixels
  only, plus a vertical profile (a bare mean cannot see *banding*, which is
  the whole of what makes a giant a giant), nothing collides.
- **A share test cannot catch a low-entropy key.** Ring assignment was once
  keyed on `body.id`, and there are only **seven distinct ids across 192
  giants** — so the ringed share is seven coin flips and lands on 47% by luck.
  The check that bites asks whether all thirty-one giants in the *same
  orbital slot* agree. Groups of eight or more only: the outermost slot holds
  one giant in the whole sector, and one body agreeing with itself proves
  nothing.
- **Every sphere in the game wore a faint wireframe.** Two adjacent
  antialiased polygons each cover half the pixel on their shared edge and each
  blends its half with the background, so `NoPen` ruled every solid hull with
  hairlines of empty space. `ui/render3d.py` strokes each face in its *own*
  colour: **1,194 seam pixels → 54**, on every 3D object in the game.

And then flying at one found the bug the plates could not. The **sky** drew
rings on a ringed giant; the thing being *approached* did not, because
`Target` had a `look` and no `ringed` and `viewport._model_for` returned a
bare world mesh. So a giant's rings vanished at exactly the point you got
close enough for them to be worth looking at — two doors into the same
question disagreeing, which is this project's most reliable bug shape. The
check is the general one: every body in the sector must give the same answer
to `sky.has_rings` and to `targets.target_from_body(...).ringed`, and the
picture is differenced against the identical approach with the rings taken
off (10,440 lit samples against 3,443).

**An anchor with nowhere to be.** A player reported it plainly: the gate is on
the sector chart, invisible on the helm, impossible to fly to, and nothing is
happening around it. All true. A Weave anchor was a *sector* abstraction — a
system id and a list of links — with no place inside the system it stood in.

It is an `Anchorage` now, of kind `gate`, and almost everything else fell out
of that: the helm chart already draws anchorages, `track.contacts` already
turns them into things the conn and the plotting board can aim at, and the
"where you can put in" panel already offers a course to one. `gate_body` puts
it at the **outermost** body and deliberately not the one the quay is built
over — an anchor predates every port in the Verge, it was put where there was
room and no gravity to fight, and arriving through the Weave should drop you
at the edge of a system rather than in the middle of its traffic.

The other half of the report — *shouldn't there be a lot of activity around
any gates?* — is `traffic._busyness`, which now adds two hulls for a lit
anchor. Measured: lit anchors work 3.7 hulls against a dark one's 2.1, and
waking one takes its system from 2 to 4.

*A latent bug it exposed.* `HelmView._pick` read the quay that was clicked off
`self.chart` — but `refresh()` builds a new chart every time, so it was asking
a widget that had not been clicked. It could only ever show up in a system
holding **two** berths, which no system did until anchors got a place of their
own. It reads the signal's sender now.

**Something worth looking at.** The conn's windows drew a flat coloured circle
with a radial gradient behind it. At twelve kilometres that reads as a distant
object; at six hundred metres it reads as a flat coloured circle, which is a
poor thing to be watching while berthing a hull against a shipyard.

`ui/render3d.py` is the substrate: a camera, perspective, back-face culling,
painter's-algorithm depth sorting and flat shading from a light. A few hundred
`QPainter` polygons a frame — no textures, no shaders, no dependency and no
build step for a game that is otherwise pure PyQt. `data/models3d.py` holds
the meshes, authored at radius 1 and scaled by whatever the object really is,
so one yard mesh serves a four-hundred-metre quay and a two-kilometre hub.

Three things it taught me while being built:

- **The light needs a source.** `sim/conn.py` records `star_dir` when an
  approach opens: the star sits at the system's centre and the target
  somewhere out from it, so light falls along the target's own position
  vector. One line, and a world gets its terminator on the correct side.
- **A sphere must be one colour.** Every other mesh alternates shade
  face-by-face so a flat-lit structure still reads as having parts. Do that
  to a sphere and you get a chessboard, and the chessboard eats the
  terminator — the one thing that makes a planet look like a planet.
- **The first pass was almost entirely black.** A handsome yard, correctly
  lit, and unreadable. Ambient went from 0.22 to 0.40.

**And the cameras were not looking where the ship points.** `conn.nose` is the
3D vector the main drive is aimed along; the camera basis was built from
`conn.heading`, a bare yaw angle **nothing in the game has ever written to**.
So swinging the hull round with the thrusters changed the flying and not the
view. `viewport.hull_frame` builds one set of axes from the nose, and the hull
keeps its belly toward whatever it is approaching — which is what makes the
ventral camera worth having in orbit, and which one inverted cross product had
backwards, putting the planet you are orbiting in the camera pointing at the
sky.

**Half the diplomatic board was still free.** `sim/allegiance.py` has charged
you for being seen working for somebody since it was written — relief to the
Concordat costs you with the Charter and the Freeholds — but `broker` and
`denounce` never got the same treatment. Measured at 70 standing with everyone:

    relief   (concordat)             charter -0.2, concordat +3.3, freeholds -1.3
    broker   (concordat, freeholds)  concordat +1.8, freeholds +1.8  <- nobody else
    denounce (concordat, freeholds)  charter +6, concordat +6, freeholds -14

Brokering is the most public thing a captain can do: it seats two powers at a
table, thanks you with **both**, moves their relation twenty-eight points and
decides the Concord ending — and the Charter, at -20 and -35 with the pair of
them, did not notice.

`allegiance.defenders_of` is the mirror of `offended_by`: who minds you
*attacking* a power rather than serving one. Deliberately symmetric — offence
starts below Cold, devotion above Correct — which means it costs **nothing at
dawn**, because the Verge opens with no friendships in it. Denouncing gets
dearer exactly as you pacify the sector, which is a better property than any
number I could have tuned: measured, nothing owed in a hostile sector and
-6.1 once the Freeholds have a friend.

And brokering is priced on what it **moves**, not on the thanks. `courtship`
has already shrunk the thanks to under two points at any standing where
brokering is permitted at all, so pricing the offence against the thanks made
the loudest act on the board cost a third power six tenths of a point.
`BROKER_WEIGHT` is to a settlement what `TREATY_WEIGHT` is to a treaty; the
Charter now pays -4.1 for a peace between the two powers it likes least.

*And a bug it surfaced in the board.* Brokering charges a third party twice
over — once as an enemy of each principal — and `preview` quoted that as two
separate lines, so the screen promised the Freeholds -3.30 and then again
-4.90 while the act moved them -8.20. Both halves were true and neither was
the number. `preview` merges to one line per power now, because the board is
read by a person.

*What it does to the game.* Over twenty determined chronicles, a captain who
only brokers reaches the Concord **6 times in 20**; one who brokers and keeps
everyone sweet, **19 in 20**. The ending is not harder — it asks to be paid
for. `test_politics`'s determined-broker bot was updated to court as well as
broker, because brokering alone was a complete strategy only while it was
free, and it clears the same bar far better than before.

**The Weave.** A hull's jump range is ten light years. The sector is
sixty-eight across with a median pair distance of twenty-nine, so a fresh
captain reaches **three systems of forty-one** and the rest of the Verge is
scenery. The interstellar model was never the problem — `data/crossings.py`
has four profiles with real time dilation and a documented three-cornered
trade between reaction mass, the crew's remaining years and all the work they
would otherwise have done. The problem was *reach*.

`sim/weave.py` derives nine ancient anchors from the galaxy's own seed by
farthest-point sampling — take the system nearest the middle, then repeatedly
take whichever is furthest from everything chosen so far — so they are
landmarks, identical in every process, and need no save migration. They are
paired in a ring with chords across it: the ring makes the network legible and
the chords are what make holding one system worth anything. Three burn at
dawn, lit as a connected *chain*, because a link burns only when both ends do
and three scattered singletons would have been a Weave with one working link
in it.

`sim/gates.py` is what a captain can do about it:

- **Transit is instant** — the only act in the game that does not spend the
  calendar — and pays a toll to whoever holds the far end, priced on the light
  years saved. Standing halves it or closes the ring entirely, which makes the
  Weave a political object rather than a convenience.
- **Waking a dark anchor** needs `weavecraft`, which requires Xenolith
  Metallurgy *and* the Foldrunner Coil. Learn only one and you have a very
  expensive ring you cannot switch on — the ancient-and-modern mixture the
  whole system is built on.
- **Laying your own** costs more again, and only ever onto a ring already lit.

Measured, across five sectors: a drive alone reaches 2–35 systems of 42; a
fully-lit Weave adds **8 destinations, never fewer than 2 of them beyond any
amount of hopping**.

And the price. **The Bloom travels the Weave.** A lit ring hands a share of an
infested system's growth to the far end regardless of the light years, scaled
by the same stage and provocation as everything else it does. Differenced
against the same chronicle with the carry disabled, the far end of one ring
went from clean to **0.70 infested in 180 days against 0.00**. One link is
survivable; a fully-woken Weave with something bad on it is how a sector dies.
That is the decision the system exists to pose, and it is why waking an anchor
is not simply an upgrade.

**Only rings the captain lit carry.** The three anchors burning at dawn have
been burning for four centuries; whatever they were going to spread, they
spread long ago, and the sector's present state is the equilibrium that
already includes them. This is not a dodge — it is where the decision belongs,
and it fell out of a real regression.

The first draft's carry was flat, which made it a growth channel that did not
care what the Bloom had been through, and it swamped the check that provoking
the Bloom makes it grow faster (31.8 against 33.4, when the provoked run
should be larger). Scaling it by `stage` and `provoked` fixed that and made it
a firehose instead: the sector's burden crossed several stage thresholds
inside a single tick, so the escalation check saw three stages where it wanted
four — it was *jumping* them. Three long-chronicle suites went with it, all
for the same reason: `clock.advance_days` returns early once `victory` is set,
so a sector that drowns freezes the calendar and nothing ages, escalates or
flies again.

Tuning the constant against four checks at once is fitting to tests, not
designing. Charging the world afresh every tick for rings the powers have run
for centuries was the actual mistake. With the carry restricted to what the
captain wakes, the baseline is untouched, every long-running check is valid
again, and the consequence lands exactly where the choice is made.

**Engines with places, a hull that has to point them.** A player asked three
questions the game could not answer: is there a braking burn as well as an
accelerating one, does the ship turn to aim its engines, and where are the
engines on the hull. The honest answers were no, no, and nowhere — drive slots
were a *count*, `Conn.heading` was written by nothing at all, and `flight._leg`
handed back one lump with the braking burn living only in a comment.

`data/mounts.py` gives thrust somewhere to come from: main drives mount aft on
the transom and push along the nose, without exception, because that is what a
main drive *is*; a hull with two slots and one engine pushes 0.34 off the
centreline. Attitude clusters are not fitted — every hull is built with six of
them, because a ship that could not rotate could not be flown and there is no
loadout in which that is an interesting choice.

`sim/thrusters.py` asks what that means for a particular ship. Mass comes from
the chassis `hull` rating plus every part and every tonne in the hold, so the
loadout stops being a stat line: the same Fusion Torch pulls **2.06 m/s² on a
SPORE and 0.108 on a LEVIATHAN**, and the LEVIATHAN takes 493 seconds to swing
end for end against the SPORE's 50.

`sim/attitude.py` is the consequence. The main drive pushes along the nose, so
a burn in a new direction is a *turn* first — three ticks to swing a NAVIS 90°
— and the turn spends reaction mass out of the same tank.

**Worlds are painted now, not built** — `ui/spheres.py`, and it is the fix the
previous cycle filed rather than started.

A sphere does not need geometry. It projects to a circle, and a Lambertian
sphere's brightness across that circle *is* a radial gradient whose centre is the
sub-stellar point: so the light is one gradient, exact rather than interpolated,
with no faces to show at any size. The latitude structure goes on as nested
ellipse caps, because a circle of latitude projects to an ellipse — which is what
makes the bands curve round the limb and read as a ball instead of a striped coin
— and a thin bright limb carries the atmosphere seen edge-on. The mesh path stays
for hulls, stations and gates, which are not spheres, and for ring systems, which
want geometry because they interpenetrate the world they circle.

Measured: **11 ms against 88.8 ms** for the same world close up, the worst
brightness step across the surface down to 10 levels — which is quantisation, not
a facet — and the phase ordering right all the way round, from the star behind the
camera through half-lit to eclipsed.

The level-of-detail from the previous cycle went with the meshes it served: there
is one mesh resolution again, kept only for the catalogue checks that compare one
kind of world against another under a fixed light.

**Four things had to be got wrong first, and each one is a lesson about where the
bugs live in a renderer.**

- **Ninety degrees out.** A first draft built each latitude cap by rotating a box
  with `QTransform`, and put the pole on the local *x* axis while the ellipse and
  the skirt both ran along *y*. Every world came out as a vertical split with the
  polar colour flooding the rest. Rebuilt from explicit vectors, which cannot be
  ninety degrees out because there is no frame to confuse.
- **Sign-guessing the light.** The first lighting worked the star's screen
  direction out from the light vector and came out evenly lit, because two
  conventions — "the direction light travels *from*" and "which way is up on the
  picture" — both had to be right at once. Now the *sub-stellar point itself* is
  projected: `render3d.draw` lights a face by `dot(normal, -light)`, so the
  brightest point on the sphere is the one whose normal is `-light`, and asking
  the camera where that lands asks exactly the question the mesh asks.
- **An eclipsed world lit like noon.** Using the projected distance to place the
  gradient failed when the sub-stellar point was on the *far* hemisphere, where it
  still projects inside the disc. The offset comes from the phase now — the disc
  centre's own brightness — which puts the bright pole at the centre at full day,
  on the limb at half, and clear of the disc when the star is behind the world.
  And when the star is exactly behind either the camera or the world there is no
  direction at all and the disc is *uniform*, which needed saying separately: a
  gradient centred on the disc drew an eclipse with a bright middle.
- **Two lighting laws.** The first version invented its own brightness constants
  and drew every world darker than the mesh it replaced. It reads
  `render3d.AMBIENT` and `DIFFUSE` now and samples the same law at known angles —
  `AMBIENT + DIFFUSE·cos θ` at `sin θ` of the radius — so there is one lighting
  law with two ways of evaluating it rather than two laws.

- **A multiply of white is a no-op, so half the lighting law was missing.** The
  light went on as one `CompositionMode_Multiply` gradient — and a multiply can
  only darken. `AMBIENT + DIFFUSE` is **1.45** at the sub-stellar point, every
  level above 1.0 clipped to the same white, and so a grey-154 world that should
  have run **223 → 62** across its face ran **154 → 62**: the entire lit half
  flat, and the terminator a cliff **6% of the face** wide. It survived a cycle
  because the check compared the two *ends* of the profile, which were right. The
  multiply carries everything at or below unity now and a `Plus` pass carries the
  excess above it (`OVER_BRIGHT`), which brightens toward white rather than toward
  the surface's own colour — an approximation, said out loud in the code, because
  `Plus` cannot know what is underneath it. Measured after: **223 → 62 over 18%
  of the face**.

And two about the checks. Measuring "no facets" by walking a scanline reported 121
levels, which was the *silhouette* — the atmosphere ring against empty space,
which is meant to be an edge. It samples inside the limb now. And **the defect
above was found by a mutation that survived**: flattening the falloff to no
terminator at all changed nothing on the picture, because every stop was already
clipped to the same white. A surviving mutant is not always a missing check — this
one was pointing at the code.

**Worlds were faceted, and four attempts to smooth the shading failed.** Graphics
picked because it was asked for. At 22 rings by 30 segments — 660 faces, already a
fine mesh — a world filling the window read as the polyhedron it is: flat shading
gives each face one colour, so you could count the quads across the terminator.

The obvious answer is Gouraud, and `QPainter` has no per-vertex colour, so I tried
to reach it with a `QLinearGradient` per face. **It cannot be done, and it took
four goes to see why.** A linear gradient is constant perpendicular to its own
axis, where real Gouraud varies — and that error alternates with a quad's
orientation, so every version put a *checkerboard* on the sphere:

1. Corner to corner, from the darkest-lit vertex to the brightest. Two vertices of
   a quad often sit at nearly the same brightness, so which counted as darkest
   flipped face to face.
2. The same, with the gradient's *axis* taken from the projected light instead.
   No change: the colour ends were still chosen by brightness.
3. Ends chosen geometrically along that axis. A quad whose per-vertex colours run
   (low, high, high, low) still had them swapped whenever the extreme pair changed
   edge.
4. Ends ordered by *latitude*, so the colour can never reverse. Still checkered,
   for the structural reason above.

It was not the rim term either — forcing that to zero left the pattern exactly as
it was, which is how the colour pairing was identified as the cause. All of it was
reverted.

**Geometry is what worked.** Rendered side by side, 22x30 is plainly faceted and a
mesh four times finer is smooth, and the cost is in *faces* rather than pixels —
6.7 ms against 20 ms for the same world at any size on screen. So worlds are built
at two resolutions and `ui/viewport.py` spends the fine one only above
`FINE_ABOVE` pixels of radius: a body nine pixels across in a camera thumbnail
looks identical either way and must not cost four times as much. Measured, the
whole conn window repaints in 102 ms against a 700 ms timer — 15% of a frame — and
a distant world still costs 8 ms.

**Where the faces go matters as much as how many.** At about 2,550 faces either
way, 44x58 still bands horizontally, because the colour runs with latitude and
rings are what sample it; 70x36 and 96x26 kill that banding and stripe the limb
instead, because segments are what round the silhouette. 60x44 is the pair that
reads smooth in both, and that is what `FINE` is.

**It is better rather than beautiful, and worth saying so.** The residual banding
is inherent to flat-shaded polygons with one colour a face, and the real fix is to
stop treating a sphere as geometry at all: project it to a disc and shade it
analytically with an offset radial gradient, which is exact for a Lambertian
sphere and cheaper than either mesh. That is its own piece of work — task #97.

**The price register sorted on the sticker price and never said what the flight
cost.** Trading picked for breadth. The market itself turned out sound — measured
across all thirteen goods there is a 20% spread and no same-counter money pump,
and the depth is real: buying 280 t of ore drove the price 36 → 43 and drained the
stock to nothing, which then relaxed back over a year. The fault was in the
*information*.

`best_markets` returned a price, an age and a confidence, and the panel drew a
straight-line light-year count beside it. No hops, no days, no notion of whether
the ship could get there. Measured over six sectors and six commodities:

- **32% of the recommendations were to systems the ship cannot reach at all** —
  not far, not dear, unreachable, and nothing said so.
- **44% of the lists put a worse port first.** The worst case ranked a port worth
  0.5 a day above one on the same list worth 3.9 — seven times better, listed
  below it.

`reach.route_to` has existed since the contract board needed it, and its docstring
names this very lesson: the board "named a reward and a deadline and never once
said where the work *was*". The rows carry `hops` and `days` now and selling ranks
on **revenue a day**; buying ranks on price with the days breaking ties, because
there what you want is the low number. The unreachable are kept and marked rather
than dropped — a jump drive is a thing a captain can go and buy — but they rank
last. On one board that means Lumen Mouth, paying the *highest* price for ore at
₡31, sits at the bottom reading "beyond your jump · nothing you can reach", while
the port that can actually be flown to shows "1 hop, 7 days · 4 a day".

`reach.routes_from` is the walk, once, for the whole list: `route_to` used to run
its own breadth-first search per call, and the register asks about four ports for
each of thirteen commodities on every repaint.

**Two more faults fell out of the reordering, both latent:**

- **`freight.runs` said "a price you wrote down beats a price somebody described
  to you" and did not do it.** It kept whichever run had the higher `worth`, and
  the register happened to win often enough that the check on it passed. Measured,
  **18 of 44 runs known both ways have the desk quoting the better number**, so a
  rumour was replacing your own notes four times in ten. It implements the rule
  now.
- **`from_register` inherited a display limit.** It generates candidate runs and
  called `best_markets` with its default `limit=4`, so what work existed at a desk
  depended on how many rows a panel draws. 549 register-known runs are offered
  where the top four used to be, and 54 commodity-and-port sets are larger than
  four.

**One asteroid gave up 8,427 tonnes instead of 140.** Mining picked for breadth,
and found the largest arithmetic hole in the game so far.

`raise_rate` lifts material with four rigs — `mine` for ore, `phos` for
phosphate, `drink` for volatiles, `graze` for biomass. `actions.extract` wore the
body down with **two of them**: `st.mine + st.drink`. So a phosphate rig and a
harvest tendril raised material and depleted nothing. Fit a token mining root
beside them, and one body gave up **8,427 t over 283 spells against an ordinary
hull's 140 t over 8** — sixty times its worth. Not infinite, because `extract`
refuses a hull with no mining root and no harvest tendril at all, which is what a
first draft of the check claimed and had to withdraw. Sixty times is enough.

`mining.RIGS` is the one table now — the pairs `raise_rate` walks — and
`mining.rig_of` sums it, so a rig that lifts material is a rig that wears the body
down by construction rather than by two lists agreeing. Measured after: 159 t
against 128 t, which is a hull's fittings mattering rather than a fountain.

**And the forecast was biased by the option it was comparing.** `prospect`
estimated the average rate at the midpoint of what was left and multiplied by days
and a `WORKING_LOSS` fudge. Against actually working the body out it was 2% low on
a bioleach and **45% low on a bore** — the error tracking how fast the method
depletes, because the faster it goes the fewer steps the average is taken over.
The days figure was separately a fifth too long, because `prospect` used
`max(mine, drink)` where `extract` used the sum.

It is a **dry run** now: it walks the body down in five-day steps through
`raise_rate` and the same depletion arithmetic, and adds up what comes off. It
cannot disagree with the act because it *is* the act with the ship left at home —
the same reason `sim/preview.py` flies a throwaway twin instead of predicting a
burn. Checked with events silenced, the error across all four methods is −0.0%,
+0.0%, +0.2% and +0.1%; with events live it varies ±6% either way, which is a
windfall and an accident behaving like noise rather than bias.

What that buys is a legible decision. On one ice body the screen now reads: a cut
and a bore both recover about 98 t, but the bore does it in 64 days against 135;
a bioleach recovers **254 t** and takes 386. Speed against total, and both figures
true.

**A hang, and the lesson from it.** The dry run's `while` loop exited only when
the depletion arithmetic advanced, so a mutation that removed the advance spun for
ever and took the whole sweep with it — I had to kill it, and killing it left the
mutation in the tree, which is its own hazard. There is a hard step bound beside
the depletion test now: a loop whose termination depends on arithmetic is a hang
waiting for someone to break the arithmetic, and a check that hangs is worse than
one that fails because it costs everything and tells you nothing.

**"Grievances are counted" was true in three places and false in the code.**
`approach.preview` tells a captain refusing a levy that "they will file it as a
grievance, and grievances are counted"; the levy's own `costs` line in
`data/approaches.py` says "they collect grievances". What actually happened was

    dip.ensure(game).grievances = getattr(dip.ensure(game), "grievances", 0) + 1

— a counter on a field `DiplomaticState` **does not declare.** Nothing read it,
and because it was undeclared the save's decoder dropped it: set it to seven,
save, reload, and it comes back as nothing at all.

**An existing check covered it and passed anyway.** `test_envoy` asserted the
counter went up, reading it through `getattr(state, "grievances", 0)` — which is
how an undeclared attribute passes for a field — and never saved. The number
moved, the check was satisfied, the feature was missing.

The deeper fault was an asymmetry. An overture is remembered
(`diplomacy._remember`), and so is an answer to a demand for ground —
`territory.answer` notes all three of pay, cede and refuse, and
`grudge.because` puts them on the diplomacy screen. **An envoy's answer was the
one dealing with a power that left no trace**, so a captain who had refused four
levies faced a power that priced him badly and a screen that could not say why.

`data/approaches.AS_ANSWERED` is the table and `approach._remember` is the door,
mirroring the one diplomacy already had. A grievance is a *memory* now, which is
the machinery that already turns dated things into a price bias and into whether
a power will deal with you — and which persists. Measured: refusing levies takes
the Charter from **0.0 to −28.6** feeling and its prices from x1.000 to
**x1.051**, and the screen reads "Their feeling −34 · Their prices to you +6% on
what you buy · Y1 D001 · you left our levy unpaid (−14)". Accepting a
requisition is deliberately *not* remembered: a power that recorded every barrel
of ore would have a ledger nobody could read.

Three fields went with it, all read by nobody: `Envoy.choice`,
`territory.Demand.choice` — both redundant now the memory carries the answer —
and `DiplomaticState.favours`, whose story is the guard's.

**The guard's accessor hatch was cut too wide.** It credited any dict subscript
or `.get("literal")` as reading a field, and that hid
`DiplomaticState.favours` for a whole cycle: the field is read nowhere, and
`sim/officials.py` keeps a *different* per-official favours dict which it reaches
as `store["favours"]`. A field excused by an unrelated dict that happens to share
its name is a guard doing nothing. What counts now is a **named accessor reaching
a field by string** — `getattr`/`hasattr`/`setattr`, and a two-argument
`get`/`set_to` with the subject first and the key second, which is the shape of
`options.get(game, "hints")` whose body is a `getattr`. The credited-name set
fell from **538 to 153**, and the swept total from 8 unread to 6.

**And a mirage worth recording.** I came to this by measuring whether the four
powers ever move among themselves, saw the relations matrix freeze after year six
and the venture count stop dead at 36, and spent a good while building the case
that the powers stall. They do not. `advance_days` returns early on
`game.victory`, the unattended chronicle had reached the **"ruin" ending**, and
the clock was correctly waiting for the player to take it or carry on into the
epoch. There is no venture bug. The lesson is about the measurement: a headless
probe that advances years without driving the ending is measuring a stopped
clock, and `tests/chronicle.py` already knew that — it guards its loop on
`game.dead and not game.victory` and asserts it got twenty rounds in.

**The declared-field guard went past `data/`, and found seven traits that did
nothing.** Task #88 pointed `test_declared.py` at `sim/`, `world/` and `core/` as
well — 1,167 fields — and the richest find was in the crew.

`crew.TRAITS` has declared seven officer traits since it was written, each with
an effect key and a magnitude: Charter-raised +0.04 diplomacy, Yards-trained
+0.05 repair, Freehold-born +0.05 trade, Bloom veteran +0.05 tactical, Wet-wired
+0.03 accuracy, Quiet +0.04 scan, Reckless +0.04 evade. **Not one was ever
applied.** `Officer.trait_id` was written when a candidate was generated and read
by nobody: `trait_name` and `trait_note` went to the crew screen, so a Bloom
veteran said "Was at Kessel's Reach and came back" and fought exactly like
anybody else. It was not free either — `make_officer` charges 25 a month for a
trait, so a captain had been paying for seven effects that did not exist.

`crew.trait_effects` sums them by key and `ship.stats` adds each into the stat it
names. Six of the keys name a stat computed there; the seventh, `tactical`, names
the *skill* the combat numbers derive from, and a first draft converted it into
levels — which measuring showed to be nonsense, moving accuracy by 0.0026 where
every other trait moved its stat by 0.03 to 0.05. A magnitude declared in stat
units is a stat, so it adds to accuracy and evade directly.

Two more of the findings landed on the gunner's board, which is the one screen
whose job they were:

- **`firing.Shot.band_shift`** — "bands to close (negative) or open (positive) to
  reach its envelope" — read by nobody, so a mount out of range said "range" and
  left the captain to work out which way. It says **"open 3"** now, which is an
  order for the helm rather than a complaint.
- **`gunfire.Shot.frm`, `.to` and `.weapon`** recorded who fired, at whom, with
  what, and nothing read any of them: which gun did what existed only as prose in
  the log, while a gunner pulling the trigger saw a heat number change and
  nothing else. The board carries a **Last exchange** list now, both directions.

Two were deleted rather than wired. `anchorage.Anchorage.extras` was a dict built
in three places carrying a redundant copy of the port's level, a gate's lit flag
and a colony id, all reachable from the objects themselves; and
`territory.Demand.holdings` was a count of what was at stake beside a live
`holdings_in()` — a stored copy that can disagree with the truth the moment a
colony is lost, which is the two-doors fault this project has hit more than any
other. The six that remain are allowlisted against tasks #92, #93 and #94.

**And two lessons about the guard itself.** A regex for `.name` counted
`self.x = 1` as *reading* `x`; it walks the AST for a `Load` now, because a field
only ever assigned is exactly as dead as one nobody mentions, and three findings
were of that shape. The other is that a field only the *suite* reads is still
dead: `extras` was read by `test_anchorage` and by nothing in the game, which is
why the sweep excludes the tests. Constructor keywords stay invisible to it —
`Demand(holdings=…)` and `Anchorage(extras=…)` were both real writes it did not
see — which is right for the verdict, since a write is not a read, but it means
the count of writes it could report would be wrong.

**The gunner had no middle.** `combat` offered one named mount or `_salvo` —
"everything that can bear, fired together" — and `_salvo`'s own docstring says
the cost is heat and ammunition, "which is why a single aimed shot stays a real
option". That reads like a trade until it is measured.

**A HAMMERFALL with five mounts puts 69 points of heat into itself in one salvo,
against a fault line of 40 and a vent of 6 a turn.** It faults on turn one and
never comes back: across ten turns its resolve bled from 92.9 to −34 on its own
radiators, in a fight it was winning on damage. The alternative on offer was one
mount out of five. So **buying armament made the salvo button worse**, which is
the question this project asks of every good thing, and here the answer was yes.

`sim/gunnery.py` is the missing control: fire *some* of them. `quote` says what a
chosen set does to the hull before the trigger — heat in, clamp, vent, then the
fault test, in that order, because a volley that lands a point over and vents six
is not a fault and quoting it as one would be crying wolf. `advise` picks the
most damage of any set that will not fault, found exhaustively, since no chassis
carries more than five mounts and 32 subsets is nothing.

Played over twelve engagements at two difficulties with the guns supplied, on the
hot hull the advised volley won **6/12 and 4/12 against 1/12 and 2/12** for firing
everything, and never faulted once against 53% and 57% of turns. On a cooler
LONGSHOT the three options are level inside a twelve-seed sample, and firing
everything still overheats on nearly half its turns.

**`advise` was wrong twice and playing it is what showed both.** It first ordered
by damage *per point of heat* — heat is the constraint, so economise heat — which
favours the small guns: a PDC is four damage a point, a Fusion Lance barely two.
It picked the pea-shooters, left the main armament cold and won 3 of 12, while
firing one Fusion Lance every turn won 6 despite faulting a fifth of the time.
Economising heat is not the job. Then it could advise firing *nothing*: on a warm
hull no mount fitted under the line, so the answer was to sit still, and played
out it said fire, hold, fire, hold — shooting half as often as the enemy.
`ship.py` records the same lesson beside `HEAT_CEILING` from the last time it
happened, that they "lost to their own radiators, in a fight they never shot in".
The floor is now the heaviest gun that bears: faulting is a cost, being harmless
is a loss.

Three more things the work turned up:

- **The fault line is `heat_cap`, not `heat_cap * HEAT_CEILING`.** The ceiling is
  the physical clamp on how much heat a hull can hold; the line `_end_of_turn`
  tests is half that. I read them the wrong way round and built a board on it,
  which would have called every faulting volley safe. `gunnery.fault_line` is one
  function and `_end_of_turn` now asks it too.
- **`Shot.mount_id` is a part id, so it is not unique.** Five mounts came back
  under three names, because three Fusion Lances are all `fusion_lance`. They are
  genuinely interchangeable — one hold rather than per-mount magazines, identical
  parts in identical arcs — so a selection is a **multiset** and the count has to
  be capped at what the hull carries. The window keys its holds by slot for the
  same reason.
- **Five of the eighteen weapons draw `alloy` and a new captain carries none.**
  Not a bug — you supply your own guns — but it wrecked two rounds of my own
  measurements, which compared gunnery modes on a ship where nothing could fire.

`ui/gunner_window.py` is the seat: a boresight per mount, the tactical plot, a
board of every mount with what stops it and what it costs, and the trigger with
the heat quoted before it is pulled. `ui/mount_sight.py` draws the sights — and
**`firing.arc_span` returns half-angles**, which its docstring says and my first
draft ignored, putting a fore arc entirely to starboard. `ui/tactical_plot.py`
had already been fixed for exactly that and left the reason behind it: "drawing
only one of them is a lie about the ship." It looked plausible on screen because
the target happened to be near dead ahead when I looked.

`MainWindow.battle_act` is now the one door for resolving a turn, because there
are two seats on the same engagement and the second copy is where the
`b.player.st = ship_stats` line gets left out.

**The pilot could not throttle.** `sim/conn.apply` has taken a `throttle` since
the drive learned to throttle and a `ticks` since it was written, and the conn
could reach neither: it fired `apply(conn, axis, main=use_main)` and nothing
else, so the human's main drive was a switch — full power, one minute — while
the flight computer beside it throttled freely. `apply` still carries the note
saying why the *computer* needed it: "one tick of a fusion torch on a SPORE is
124 m/s, so the computer lit it to trim ten, overshot, corrected the overshoot,
and never converged."

Flown by hand, that is not a rough edge, it is a hull that cannot be berthed. A
SPORE under a Fusion Torch moves **41.9 m/s a press**, so a pilot with ten metres
a second of way on has no move that improves matters: every press overshoots
further than the error. Measured, a full-power-only pilot stays **stuck at 10.00
m/s**, outside the 1.5 m/s berthing limit, for ever.

`sim/pilot.py` is the console's side of it: `THROTTLE_STEPS` of a tenth, a
quarter, a half and everything, and `COAST_MINUTES` of 1, 5 and 15. With the
ladder that same pilot gets to **0.48 m/s** and berths. Two controls rather than
one, because `apply` does two things — it fires *once* and then steps time
`ticks` times, so the second is a **coast** and not a burn length; calling it a
burn length would be a lie about the button, and the button's name is all a pilot
has to go on.

`pilot.quote` is the only door the console speaks through, so a tooltip cannot
promise what the burn will not do; the old tooltip was computed at full power for
one minute whatever the console said. `pilot.burn_cost` is the only door the
*cost* comes through, and that fixed a real fault: **`can_burn` demanded a whole
`MAIN_COST` whatever the throttle**, so a hull holding 0.119 t was told "No
reaction mass for the drive" for a burn costing 0.012. That is the gate refusing
an act it could well afford — the fault this project has swept every other gate
for, and it existed here only because the throttle was unreachable, so nobody had
thought to ask. `apply` has its own gate call, and a sweep caught *that* one
separately: asking it at full power left `can_burn` correct and the burn still
refused, with nothing to show it.

`ui/conn_controls.py` is the console itself, split out of `ui/conn_window.py`
when that went past five hundred lines along a seam already there — the window
owns the cameras, the panel and the clock. The panel names the settings in m/s,
because "10%" of a number the pilot cannot see is not information.

**And losing one engine of a pair now costs something.** Three separate places
in the tables had promised this for as long as they had existed and not one of
them was true. `data/mounts.py`, on why the stations are spread across the
transom: "so losing one leaves the thrust off-axis". `thrusters.offset`,
computing exactly how far off: "which the flight computer has to trim against".
And `Mount.axis`, the direction each engine pushes — declared, and read by
nobody, because every drive was given the same constant. So a hull on one of two
engines flew exactly as straight as one on two, only slower.

`thrusters.yaw_torque` is `r × F` over the engines actually fitted, which is the
one place `Mount.axis` is read for what it is: a cross product has to know
which way the force points. **My first draft let the hull yaw and was wrong
about the tick.** An unopposed 0.0012 rad/s² across a sixty-second conn tick is
126 degrees — not a ship needing trim, a ship spinning like a top — and it made
my own measurements nonsense, because the nose wrapped past 360° and read as
zero. No flight computer would permit it. It holds attitude and opens the drive
only as far as it can hold, which is `holdable_throttle`: attitude authority
over drive-induced yaw, floored so no refit can strand a ship.

The result is a real trade rather than a number going down. A **NAVIS on one of
two engines holds 0.62** of the engine it has left and pays 55% of the extra
mass share for the clusters trimming throughout, which comes to **twice the
reaction mass per m/s** and a high orbit reached in 1.24× the time for 1.20× the
mass. And it is still flyable: berthing is unaffected (6/6 either way), and every
high orbit the balanced hull reached, the lopsided one reached too.

**A correction to the first telling of this.** It said a LEVIATHAN shrugs a
missing engine off entirely because its moment of inertia beats the torque, and
that was measured on one engine and generalised too far. A LEVIATHAN holds 1.00
under a **Reaction-Mass Organ** and **0.20 under a Fusion Torch** — seven and a
half times the thrust, and the clusters lose. What decides the cap is off-axis
thrust against attitude authority; mass helps at equal thrust, but thrust is the
term that varies most. A NAVIS with one Fusion Torch sits on the floor at 0.15.
So the shape of the trade is that **a big engine on a hull with few stations is
the liability**, which is a more interesting rule than the one I first wrote.

One thing fell out sideways. Priced per-seed, the lopsided hull reached a high
orbit on a seed the *balanced* hull missed: too much thrust overshoots at a
small body, so the cap gentles the approach. That is task #83 showing its face
from the other direction, and it is why the cost check compares only the climbs
both hulls made — a ratio over two different populations would have read as a
lopsided hull being better.

`sim/instruments.py` says it out loud, because a cap the pilot cannot see is a
bug report: **"Drive trim — 62% usable"**, and only when there is something to
say. A row reading 100% forever is a row the pilot learns to skip. My first
draft marked it *amber*, and `test_conn.py`'s "the panel does not cry wolf at a
good approach" caught it warning on fourteen approaches that had **succeeded** —
which is exactly the fault that check was written for. The trim is a fact about
the hull, not a fault in the flying, so it reads plain.

**And the cap found a third bug in `_copy`.** `conn.forecast` flies a throwaway
twin, and the twin is built by a hand-written field list. Adding `hold` left it
thinking it had both engines, so the quote was 0.095 km off the burn: the cap
was on the act and not on the forecast. Asking the general question — *which*
fields does the twin drop? — turned up two more, both silent. `orbit_want_km`,
added when orbit heights arrived, meant `outcome.adrift` measured drift against
a 12 km opening rather than the 20,000 km the ship was climbing to. `star_lum`
was harmless, since a forecast never renders, but it was dropped for the same
reason. Its own docstring already recorded this happening once before with
`start_km`; the third time it became a guard. `test_conn.py` now enumerates
`Conn`'s fields and requires every one to be carried, or named as a field a twin
must *not* inherit with the reason — `landed`, `log`, `outcome` and `damage` are
the four. The mutation sweep is the proof it was worth it: dropping `hold` fails
the old forecast check, but dropping `orbit_want_km` or `star_lum` fails **only
the new guard**.

Three faults came out of building it, all found by flying:

- **A bigger engine made every hull worse.** One tick of a fusion torch on a
  SPORE is 124 m/s, so the computer lit it to trim ten, overshot, corrected
  the overshoot, and never converged. The worst drift a hull could recover
  from ran 60, then 2, then 140 m/s across three drives of *increasing*
  thrust. Engines throttle now.
- **The control law was a ladder of branches**, each with its own threshold.
  It held at the flat delta-v the conn used to assume and fell apart across a
  160-fold range of real acceleration. It is one law now: `target_velocity`
  says what the velocity should be, and the burn cancels the difference.
- **Thrust comes in six directions**, so the nearest axis to a correction is
  up to 45° off it — burning the *whole* error along it overshoots and creates
  error elsewhere. A NAVIS was measured hunting between left, back, down,
  right and up at 650 m, never berthing. Only the component that axis can
  cancel is burned.

`sim/burnplan.py` is the third gap, and the place I had to correct myself. The
first draft derived a cruise speed from the quote and reported the burns to
reach it: four and a half thousand kilometres a second, and every hull in the
game declared inadequate. The arithmetic was right — a NAVIS crossing 6.5 AU
in five days *is* doing 0.75% of light speed — and the conclusion was wrong,
because the game does not fly interplanetary legs on Newton. It has a `jump`
rating, a Foldrunner Coil, a relativistic profile, and a `dilation` argument on
the clock. So the plan describes the crossing in the game's own terms: half the
reaction mass is the braking burn, the turns take the time this hull's clusters
need, and the coast is nearly all of it. `flight` remains the authority on days
and mass; the plan is that quote, explained.

**A window that captured the game instead of reading it.** Three more player
reports, one cause:

- **Moored to the Fleet Hub, the conn opened on the planet.** `track.contacts`
  lists bodies before anchorages and the window took the first row in reach —
  but you are already in orbit of the body, so approaching it is not a
  manoeuvre. `default_target` prefers anchorage, then hull, then body.
- **`ConnWindow.contacts` was built in `__init__`**, so after a jump it went
  on offering the traffic of a system the ship had left.
- **`PlotCanvas.system` was too.** After a jump the canvas drew the old system
  while the contact list beside it — which asks the game every refresh —
  listed the new one. One window, two systems, neither of them labelled.

The same report asked whether positions are linked across the game. They are,
and it is now checked rather than asserted: every screen bottoms out in
`flight.position(body, day)`, and the helm chart and the plotting board — two
different projections — place the same body within **9e-16 AU** of each other
on the same day. What the report was actually seeing is physics: the orbital
periods are properly Keplerian (0.40 AU → 92 days, 9 AU → 27 years), so over a
four-day crossing the outer worlds move 0.5 px and the inner one 2.2 px on a
chart where an AU is about twenty pixels. The traffic, on a 46-day leg, moves
11–18 px in the same time.

**A berth is a place.** A player asked why the helm shows only the star and
the planets, and how they would ever navigate back to a shipyard. They could
not: a `Port` hung off a `System` with **no position at all** — no body, no
orbit, no coordinates. The quay you were standing on was nowhere in space, and
docking was a screen you switched to from the chart, so the one view you fly
from could not show you the one place you most need to fly back to.

`sim/anchorage.py` gives each one somewhere to be, anchored to a body — which
means it inherits a real orbit that moves with the clock, and every intercept,
burn profile and transfer quote works on it unchanged, because flying to a
quay *is* flying to the body it orbits. Anchorages are **derived, never
stored**, like `ship.stats()`: one source of truth, no migration, and no way
for a saved quay to disagree with the port it belongs to. The price of that
choice is that derivation must not depend on the clock or the RNG, which is
what `test_anchorage` pins.

The helm now draws quays (▣), capitals (◈) and your own holdings (⬡) with
labels, says in words where the hull is standing, and lists everything you can
put in at with a course and a fuel bill. `offering(game, "shipyard")` answers
the original question directly. Known *hulls* are still not plotted — nothing
in the game gives another ship a persistent position, so that is honestly a
separate piece of work rather than a marker.

**The hands get older too.** A player asked why they did not. Because
`ship.crew` was an integer — a headcount with nothing to hang an age on — so
"your crew ages on a long crossing" was true of the three named officers and
of nobody else aboard. A twenty-year chronicle retired the bridge and left the
lower decks untouched, and sleeping the hands saved something no number
recorded, which is exactly why a dormancy bug hid there for a cycle.

They are still a mass, deliberately: two numbers on the `Ship`, a mean and a
spread, aged by proper time at the lineage's rate and slowed by whatever share
of them is under. The spread is what makes ageing-out a slope — as it carries
part of the mess deck past the lineage's span they start leaving, a few a
year, rather than the hull emptying on one tick.

And they can finally be **replaced**. `ship.crew` moved in exactly one
direction before — down, through fighting, hunger, and sleeps somebody did not
come up from — with no way to sign anybody on at all. `lifespan.sign_on` takes
hands within the berths that exist, for a fee, and a young intake pulls the
average down: an old deck at 80 comes back to 49.

**And you can sleep through it.** Dilation was the only answer to a long
crossing: fly harder and pay in reaction mass — an engineering answer to a
biological problem. `sim/dormancy.py` is the other one. `trehalose` has sat in
the commodity tables since the beginning described as *"vitrified sugar with
CAHS proteins; replaces the water in a cell and holds it, unbreathing"* — the
sugar real tardigrades use — and nothing ever consumed a gram of it.

Three methods and a null: **cold sleep** (a third of the ageing, a third of
the rations, 0.6% a head per hundred days), **trehalose vitrification** (4% of
the ageing and 5% of the rations, at 2.4% a head and a real bill in sugar),
and **low-power idle**, which only a Dry Choir lineage can do because it is
not sleep at all. Measured over a 600-day crossing: a sleeper ages 0.07 years
against the watch's 1.64, and eats 13 tonnes against 61.

The design turns on three rules. **Somebody stays awake** — `MIN_WATCH`, and
the watch pays full price in years and rations. **The saving is on proper
time**, folded into `lifespan` and `upkeep` rather than special-cased, so what
the screen promises and what the clock applies cannot drift. And **it does not
stack free with dilation**: both cost the ship's own work, so doing both costs
it twice — measured, a year banks 712 research awake at rest, 154 asleep, 123
at dilation 4, and 30 doing both.

**Time is relative, and there are two clocks.** `Game.day` is the Verge's:
every deadline, market, colony, faction and hull-in-a-yard runs on it.
`Game.ship_day` is proper time — what the hull and the people in it actually
live through. They agree until you fly a crossing hard, and `advance_days(n,
dilation)` is the only place either is written.

The split is a design statement, not bookkeeping. **Sector time**: markets,
ventures, diplomacy, colonies, contracts, the Bloom. **Ship time**: research,
repair, cooling, refining, ageing, upkeep, morale, wages. So a hard burn buys
your crew their remaining years back and costs you everything you would have
got done in the years you skipped — a `data/crossings.py` choice between a
long coast, a steady transit, a hard burn and a relativistic run, at 1× to 11×
dilation and 0.45× to 5× the reaction mass.

**Who is aboard, and what time does to them.** Everyone used to be the same
thing: immortal, breathing, eating nothing — while the opening screen sold a
**Dry Choir** lineage on "no air to run out of" and the daily tick asphyxiated
your recordings on exactly the same schedule as a wet crew. A lineage
(`data/lineages.py`) is a substrate, and it decides three things:

| Lineage | Prime / span | Ages at | Eats per head per day | Breathes |
|---|---|---|---|---|
| Wet | 52 / 96 y | 1.00× | biomass (a tonne a head a year) | yes |
| Grafted | 88 / 164 y | 0.58× | biomass + magnetite | yes |
| Dry Choir | 240 / 620 y | 0.14× | silicon + magnetite, 16× the power | **no** |
| Xenoform | 380 / 900 y | 0.07× | volatiles + a trace of xenolith | no |

Upkeep is drawn from commodities the economy already trades, deliberately: a
bill payable in a currency nobody sells is a tax, not a decision. A hull is
provisioned on day one with 220 days of *its own* crew's consumption, so a
Choir captain is not punished for a choice made on the character screen.
Going short is slow — six days of grace, then it costs people or levels
depending on what ran out.

**How you look at a body decides what you find.** Surveying used to be one
button: three days, no cost, no risk, the same kind of answer for a comet as for
an ocean world — while thirteen sensor fittings and a drone technology existed
only to nudge a single `scan` float. There are now four methods, and they are
deliberately *not* a ladder:

| Method | Flies there | Sees | Blind to | Wants |
|---|---|---|---|---|
| Long-range sweep | no | resources | life, anomalies, anything buried | to be inside your sensor reach |
| Close pass | yes | resources, life, anomalies | anything buried | reaction mass for the trip |
| Probe swarm | no | resources, life, anomalies | anything buried | `dronework`, 3 t silicon + 2 t alloy |
| Deep survey | yes | everything, including buried sites | — | scan ≥ 0.55, 4 t of charges, nine days |

Each method names what it `finds`, and `world/planets.survey_body` is filtered
by that list, so a method that says it cannot see lifeforms genuinely cannot.
The panel states the whole bill before you commit — days, stores, **and the
reaction mass for getting there** — plus what the method will be blind to, which
is the part that makes choosing one a decision rather than a formality.

Sensor reach is what gates the free method, and it is the reason a **listening
post is worth planting**: three colony classes advertise sensor reach, and
`colony.effects` has tallied it per system since they were written — but nothing
ever read the tally, so a CHORUS node extended your array by exactly nothing.
`sim/survey.reach()` reads it now. It stays per-system rather than folded into
`ship_stats`, because a dish spread across one system should not help you three
jumps away.

**Two mini-games.** The **docking approach** is the control loop from the
nervous-system study — sense, compute, act, hold homeostasis — with three drifting
axes, one correction per pass, and readings blurred by how good your sensors are.
A clean approach earns standing; a botched one buys a tug. The **decoding bench**
takes a recording of something that was not speaking to you: four positions, a
hidden pattern, and feedback that tells you how many glyphs are exactly right and
how many are merely present, never which. Solving one is worth alien
understanding, and costs nothing but attempts.

**There is a game on the ground.** Landing a party opens a 7×7 zone map revealed
one tile at a time. Moving costs days of supply (known ground is cheap to
re-cross, which is what makes coming home survivable); terrain springs hazards
that officers' skills mitigate; site features offer choices resolved against a
named stat. Nothing is banked until the party is back on the lander, and running
out of supply in the field costs most of the haul. How much biomass you commit at
launch buys how long they can stay.

**Contracts are optional work with deadlines.** Six kinds, posted per port and
scaled by distance. They are checked on the clock and complete the moment their
terms are met rather than when you remember to hand them in. Nothing in the game
requires taking one — the five endings are open from turn one.

**Alien technology is a separate progression from research.** Four cultures —
the Abyssals, the Ossuary, the Weft and the Tessellate — left twelve
technologies scattered across the sector as buried sites. None can be reasoned
out. Understanding accumulates in study points from four sources: excavating a
site, taking relics apart in a laboratory, buying somebody's field notes at a
port, and seizing them off a hull you destroy. At full understanding the
technology is *incorporated* — its id is appended to `research.unlocked`, so the
shipyard and codex treat it like anything else you know, and it never appears in
the research tree because you could not have derived it.

**Thirty-five hulls and nineteen stations across five families:**

| Family | Hulls | Character |
|---|--:|---|
| Grown | 12 | Gestated from a seed. Heals; eats phosphate; takes months. |
| Fabricated | 13 | Concordat of Yards. Welded in weeks, dear, and never mends. |
| Hybrid | 4 | Freehold grafts. Both bills, both gifts. |
| Synthetic | 4 | Dry Choir. Crewless, superb instruments, no self-repair. |
| Xeno | 2 | Not ours. It mends, and nobody has explained how. |

Which parts graft to which frame is `ACCEPTS` in `data/hull_types.py`: a grown
hull refuses a fusion lance, a Yards hull refuses an intima, a hybrid takes
either, and a synthetic frame takes fabricated and Dry Choir work but nothing
alive.

## Running

```
python -m seedfall                  # title screen
python -m seedfall --new            # straight into a new chronicle
python -m seedfall --seed verge-7   # a specific sector
python -m seedfall.tests            # simulation + interface suites
python -m seedfall.tests sim        # one suite
```

Requires **PyQt6** (`pip install PyQt6`). Nothing else — no network, no server,
no browser. Saves live in `~/.seedfall/save.json`.

## Layout

```
seedfall/
├── __main__.py         entry point: python -m seedfall
├── core/               engine primitives — no game rules, no Qt
│   ├── rng.py          seeded mulberry32 + pick/weighted/gauss/shuffle helpers
│   ├── util.py         formatting (credits, mass, stardate, duration) and clamp
│   ├── save.py         generic dataclass ⇄ JSON codec, @register, atomic write
│   ├── solid.py        a tiny 3D kit: primitives, projection, key/fill/rim
│   │                   lighting, specular and a depth term
│   ├── surface.py     a cap on a sphere projected as an ellipse, from its
│   │                   own axes rather than from an orthographic guess
│   ├── llm.py          optional language model, off by default, hard timeout
│   └── state.py        the Game object, advance_days(), new_game(), load_game()
├── data/               static content tables — pure data, no logic
│   ├── commodities.py  14 tradeable goods
│   ├── beginnings.py   stocks, origins and postings — who you are before day one
│   ├── personas.py     voices: register, tics, and offline sentence frames
│   ├── screens.py      the rail and the key for each screen — read by both layers
│   ├── help.py         the manual: prose, and which facts each topic generates
│   ├── lessons.py      the tutorial's eight steps, and what each one watches for
│   ├── epochs.py       what the Verge becomes after each of the ten endings
│   ├── scenarios.py    40 situations an epoch puts in front of you
│   ├── chassis.py      the hull registry — assembles and re-exports the rest
│   ├── hull_types.py   layer stacks, the Chassis record, family rules (ACCEPTS)
│   ├── hulls_grown.py  the 12 GESTALT classes
│   ├── hulls_built.py  13 fabricated · 4 hybrid · 4 synthetic · 2 xeno
│   ├── part_types.py   Part / Weapon / Ability shapes, slots, range bands
│   ├── modules.py      drives, power, sensors, compute, utility organs
│   ├── armaments.py    weapons and defences
│   ├── parts.py        merged registry over modules + armaments
│   ├── tech.py         61-node research tree, 10 branches, 5 tiers
│   ├── colonies.py     19 colony and station classes, and `EFFECT_TEXT`:
│   │                   what each grant means, in words
│   ├── factions.py     6 powers + reputation bands
│   ├── exchequer.py    what a port yields, what it costs, what building costs
│   ├── wharfage.py     what a quay takes off the cargo crossing it, and
│   │                   what a treaty's berthing clause takes off that
│   ├── settlements.py  what the ground gives, and what settling it costs
│   ├── industry.py     processes: which technology makes which good, and
│   │                   what a licence to run it is worth
│   ├── lifeforms.py    xenobiology generation tables + anomalies
│   ├── strata.py       the four layers of a dig, 3 methods, finds and spoils
│   ├── contraband.py   who outlaws what, how hard they look, what they say
│   ├── territory.py    what a power says when its claim lands on your ground
│   ├── charts.py       what each power pays for a survey, and what for
│   ├── surveys.py      the four ways of looking, and what each cannot see
│   ├── approaches.py   the powers coming to you: what each wants, and why
│   ├── officials.py    harbourmasters: tempers, levers and favours
│   ├── dormancy.py     ways of sleeping a crossing, and what each risks
│   ├── lineages.py     what a crew member is made of: span, upkeep, ageing
│   ├── crossings.py    how hard to fly a jump, and which clock pays for it
│   ├── fieldnotes.py   the eight things the ground can tell you
│   ├── mounts.py       where an engine sits on a hull, and which way it pushes
│   ├── gates.py        the Weave's ancient anchors: tolls, rings and chords
│   ├── models3d.py     meshes at radius 1: shipyard, hull, anchor, asteroid
│   ├── starclasses.py  8 spectral classes with real radii and luminosities —
│   │                   a 12 km neutron star to an A-type at 1.8 solar
│   ├── worlds3d.py     worlds by latitude: caps, bands, and concentric rings
│   ├── surfaces.py     and by longitude: named features, and a lattice of
│   │                   ground texture sized to whatever the frame holds
│   │                   (starclasses also carries each class's mass, which is
│   │                   what decides how fast its worlds go round)
│   └── lore.py         intro, victories, endings, name pools, glossary
├── world/              generated content
│   ├── galaxy.py       sector generation, lane relaxation, distance/transit
│   ├── planets.py      bodies, biomes, resource grades, survey resolution
│   └── economy.py      per-port supply/demand, prices, market drift
├── sim/                game rules — never import Qt
│   ├── ship.py         Ship model, stats(), layer stack, cargo, repair
│   ├── shipyard.py     design validation, costing, build queue, refit
│   ├── combat.py       turn resolution, firing, damage, endings;
│   │                   `_run_seats` runs helm and engineering either way;
│   │                   `cook()` holds heat under `HEAT_CEILING`
│   ├── battle_state.py the Side and Battle shapes, shared by resolver/AI/UI
│   ├── tactical.py     the plane: positions, headings, firing arcs, bands
│   ├── stations.py     helm / gunnery / engineering: the seats and their acts
│   ├── turnplan.py     and the forecast of a turn that contains one — the
│   │                   seats you are not in included, since they run
│   │                   themselves, and the helm flown on a copy of the hull
│   ├── enemy_ai.py     how the other side fights — same geometry, no cheating
│   ├── abilities.py    defensive abilities, returning their own log lines
│   ├── colony.py       founding, daily yields, aggregate colony effects
│   ├── research.py     project selection and point accrual
│   ├── crew.py         officers, recruitment, experience, morale
│   ├── encounters.py   NPC generation and transit events
│   ├── threat.py       Bloom growth and spread, cleansing, victory checks
│   ├── xeno.py         study points, incorporation, alien passive bonuses
│   ├── biology.py      what your own biology explains on the ground
│   ├── bloom.py        stages, roaming instars, resistance, the First Instar
│   ├── contracts.py    generation, acceptance, progress, expiry
│   ├── diplomacy.py    standing, the relations matrix, treaties, brokering;
│   │                   every gift priced through `allegiance`
│   ├── expedition.py   the ground game: zone map, movement, attempts, hauls
│   │                   — `step_cost` is the one door for what a step spends
│   ├── reach.py        what you can get to at all, and what a drive would open
│   ├── plans.py        the ship as solids: hull, fittings, hold, berths;
│   │                   `scar()` marks the blight a hurt hull shows
│   ├── beginning.py    turning an opening choice into a chronicle
│   ├── legacy.py       life after an ending: epochs, pressure, situations
│   ├── telemetry.py    what the instrument windows read, band by band
│   ├── memory.py       minds: what everyone remembers about you
│   ├── grudge.py       what a power's memory costs you, and why
│   ├── voice.py        speech, written by the game or by a model
│   ├── manual.py       resolves the manual's facts from the tables themselves
│   ├── options.py      player settings, every one of which does something
│   ├── tutorial.py     watches the game until the thing has actually been done
│   ├── fieldwork.py    everything done off the ship — digs, analysis, landings
│   ├── assessment.py   reading an engagement: who wins, why, what to do
│   ├── chains.py       commissions: work that escalates and closes doors
│   ├── inquiry.py      evidence, approaches, setbacks and breakthroughs
│   ├── intel.py        how well a system is known, and what a chart is worth
│   ├── loading.py      fitted mass against what the hull is rated to shift
│   ├── orders.py       which standing orders apply — the discoverability index
│   ├── wayhome.py      the cheapest known walk back to the lander, in days of
│   │                   supply, and whether the party can afford it
│   ├── parley.py       breaking off and talking your way out: the odds, what
│   │                   each part of them is worth, the turn a refusal costs
│   ├── transit.py      standing the watches of a crossing
│   ├── programmes.py   what the bench runs once a branch is exhausted, and
│   │                   what a finding buys: standing, money, or nothing
│   ├── conn.py         the last ten kilometres: a local frame, thrusters and
│   │                   the main drive, and what a contact costs
│   ├── outcome.py      whether an approach is over — alongside, in orbit,
│   │                   aground or adrift. An orbit is a shape rather than a
│   │                   distance, which is why it is not decided in conn.py
│   ├── orbits.py       what counts as an orbit, its size and roundness, and
│   │                   the ladder of heights you can ask to hold
│   ├── autopilot.py    the flight computer: one control law, three modes
│   ├── attitude.py     pointing the hull, and what the swing costs
│   ├── thrusters.py    mass, thrust and slew rate from what is actually fitted
│   ├── burnplan.py     a transfer as a sequence of burns
│   ├── berthing.py     what an approach charges the chronicle when it ends
│   ├── instruments.py  the conn's panel, judged against what it is trying to do
│   ├── preview.py      what a burn will do before you make it: a throwaway
│   │                   twin of the ship, flown and reported on
│   ├── pilot.py        what the console is set to — the throttle ladder, the
│   │                   coast, and the one door a burn's cost comes through
│   ├── gunnery.py      which mounts speak this turn: the volley, what it costs
│   │                   the hull in heat, and the best set that will not fault
│   ├── targets.py      a body or a quay as something with a mu and a radius
│   ├── weave.py        the ancient anchors, their rings, and lighting a chain
│   ├── gates.py        transit through the Weave, and what the toll is
│   ├── dig.py          working a site stratum by stratum, banking as you go
│   ├── customs.py      the contraband run: the unposted price and the search
│   ├── allegiance.py   what serving a power costs you with its enemies
│   ├── territory.py    claims against holdings: trespass, levy, defiance
│   ├── charts.py       pricing a survey by what is actually in the system
│   ├── aftermath.py    what an engagement leaves behind: salvage and standing
│   ├── notes.py        field notes: filed, looked up again, and worth something
│   ├── trade.py        buying and selling over a counter, and survey data
│   ├── services.py     repairs, a paid word, and a fortnight of bench time
│   ├── freight.py      the freight desk: what is worth loading, and where
│   ├── responses.py    provocation, the Bloom's answers, and studying a mass
│   ├── market.py       supply shocks, and the prices you wrote down
│   ├── ventures.py     what the powers do on their own account
│   ├── exchequer.py    the public purse: income, upkeep, building,
│   │                   retrenchment, and the stake a venture costs
│   ├── wharfage.py     the due on the captain's own trade, and whose purse
│   │                   it lands in — one door for the rate and for the act
│   ├── accord.py       what a signed treaty is worth: mutual berthing off
│   │                   the wharfage at their quays, and their charts of
│   │                   their own space — quoted before you sign, and the
│   │                   same instrument through either door into signing
│   ├── settlement.py   the powers put people on the ground, and the local
│   │                   market starts hearing about it
│   ├── industry.py     licensing a process to a power: their treasury pays,
│   │                   their berths start making the thing, its price falls
│   ├── weather.py      the front overhead during a landing
│   ├── mining.py       seams, depth, and how hard you work a body
│   ├── rumours.py      leads that point somewhere before you have been,
│   │                   and what the place you heard one is worth
│   ├── consorts.py     escorts: ordering one out of its berth, standing
│   │                   orders, screening, who draws fire, what they eat
│   ├── loyalty.py      what the bridge thinks of how you run the ship
│   ├── works.py        colony development: what a settlement becomes
│   ├── flight.py       the helm: orbits, intercepts, routing, transfer burns
│   ├── survey.py       what a way of looking costs, finds, and is blind to
│   ├── approach.py     a power's envoy: caused, costed, and answerable;
│   │                   a treaty signed here costs what one you propose costs
│   ├── officials.py    who runs the quay, what they think, what you know
│   ├── anchorage.py    quays, hubs and holdings — places you can put in
│   ├── traffic.py      other hulls: where they are, what they are doing,
│   │                   and which systems the picket mesh reports from
│   ├── doctrine.py     the battle computer: what unattended seats decide
│   ├── firing.py       which mounts bear, and what would fix the rest
│   ├── damage.py       a hit: which layer takes it, what breaches, the words
│   ├── dormancy.py     who is under, what it saves, and who wakes up
│   ├── lifespan.py     ageing, decline, and the end of a career
│   ├── upkeep.py       what each lineage eats, and what going short costs
│   ├── minigames.py    the docking control loop and the decoding bench
│   └── actions.py      player actions spanning modules (jump/survey/mine/dive)
├── ui/                 PyQt6 presentation — never mutates state directly
│   ├── theme.py        palette, fonts, the global stylesheet
│   ├── widgets.py      Panel, Card, Bar, Pill, TabBar and the View base class
│   ├── window.py       MainWindow: hud, nav rail, view stack, log, dialogs
│   ├── title.py        title screen and the opening briefing
│   ├── app.py          QApplication bootstrap
│   ├── map_view.py     custom-painted sector chart and jump control
│   ├── system_view.py  bodies, survey, extraction, diving, colonising
│   ├── survey_panel.py the four methods as cards, each stating its blind spot
│   ├── crossing_panel.py  the four ways to fly it, costed on both clocks
│   ├── anchorage_panel.py where you can put in, and how to get back to it
│   ├── traffic_panel.py   who else is out here, and which of them runs dark
│   ├── life_panel.py      the life catalogue, grouped by biochemistry
│   ├── mesh_panel.py      what the picket mesh hears in systems you are
│   │                   not in, and what the chart marks because of it
│   ├── doctrine_panel.py  what the seats you are not in intend this turn
│   ├── firing_panel.py    mount by mount: ready, or exactly what is stopping it
│   ├── approach_plot.py   the docking approach, drawn instead of counted
│   ├── envoy_view.py      a power's proposition, with all three answers costed
│   ├── official_panel.py  the desk: who is there, and both ways of asking
│   ├── dormancy_panel.py  the long sleep, costed in years, tonnes and lives
│   ├── tactical_plot.py   the engagement from above, arcs included
│   ├── port_view.py    market, services, recruitment
│   ├── board_panel.py  the contract board, split out of port_view
│   ├── ship_view.py    layer stack, fittings, crew, hold
│   ├── plans_panel.py  the ship drawn: materials, rim light, blight
│   ├── yard_view.py    hull designer, build queue, fleet management
│   ├── tech_view.py    research tree
│   ├── empire_view.py  colonies, depot, victory progress, waiting
│   ├── codex_view.py   class reference, powers, glossary, about
│   ├── xeno_view.py    the xenology desk (hosted as a Research tab)
│   ├── expedition_view.py  the landing zone: fogged map, party, field log
│   ├── diplomacy_view.py   relations matrix and the overture desk
│   ├── helm_view.py    orbit chart and burn planner
│   ├── minigame_view.py    docking approach and decoding bench
│   ├── dig_view.py     the trench: the stratum you are on and how to take it
│   ├── blackmarket_panel.py  the quiet word on the quay, and the tip-off
│   ├── freight_panel.py  what is worth loading here, and what it clears
│   ├── demand_view.py  answering a power that has annexed ground you hold
│   └── battle_view.py  combat screen and post-engagement resolution
└── tests/              python -m seedfall.tests
    ├── harness.py      a tiny check runner (no pytest dependency)
    ├── test_sim.py     27 simulation checks
    ├── test_xeno.py    5 alien-technology checks
    ├── test_play.py    14 playability checks — can the game be won and lost
    ├── test_combat.py  5 tactical checks — arcs, stations, consorts
    ├── captain_ai.py   a competent test pilot: steers until its arcs bear
    ├── test_empire.py  6 colony checks — works, effects, costs, persistence
    ├── test_crew.py    7 crew checks — convictions, loyalty, consequences
    ├── test_missions.py 7 commission checks — escalation, blocking, lapsing
    ├── test_settlement.py 8 checks — people on the ground, and the local
    │                   price of what they dig
    ├── test_biology.py 7 checks — what you can make sense of on the ground
    ├── test_mesh.py    5 checks — what a CHORUS Node lets you see
    ├── test_options.py 8 checks — every setting does something
    ├── test_provenance.py 9 checks — a rumour's source, and whether
    │                   the buyer of a chart knows yours
    ├── test_explore.py 8 exploration checks — the intel ladder, rumours
    ├── test_mining.py  7 mining checks — seams, methods, wear, exhaustion
    ├── test_research.py 8 research checks — evidence, approaches, setbacks
    ├── test_trade.py   8 trade checks — shocks, the register, staleness
    ├── test_ground.py  7 ground checks — weather, sight, being pinned
    ├── test_politics.py 8 politics checks — ventures, sides, the Concord
    ├── test_design.py  6 design checks — loading, overloading, stranding
    ├── test_orders.py  8 orders checks — reachability, urgency, unread state
    ├── test_assessment.py 6 read checks — honesty, arcs, robustness
    ├── test_balance.py 8 balance checks — measured by playing the fights
    ├── test_bloom_arc.py 7 Bloom checks — provocation, answers, study
    ├── test_transit.py 6 crossing checks — watches, aborting, tension
    ├── test_watches.py 5 checks — every option a real trade, every risk priced
    ├── test_courtship.py 7 checks — diminishing returns on goodwill
    ├── test_routing.py 5 checks — power routing lands the turn it is ordered
    ├── test_magazine.py 6 checks — the other side can actually fight
    ├── test_stranded.py 6 checks — the way out of a dead end is real
    ├── test_geography.py 5 checks — a port stays the kind of port it is
    ├── test_grants.py  8 checks — every colony effect is read, and does something
    ├── test_prospect.py 5 checks — a ground option's prize is the officer's prize
    ├── test_gates.py   4 checks — every "may I?" agrees with the act it guards
    ├── test_beginnings.py 11 checks — the opening card is the chronicle you get
    ├── test_docking.py 5 checks — the approach instrument can be believed
    ├── test_fog.py     6 checks — the chart shows only what you can see
    ├── test_customs.py 9 contraband checks — the premium, the search, heat
    ├── test_allegiance.py 8 checks — taking sides, and brokering out of it
    ├── test_territory.py 8 checks — annexation, levy, defiance, seizure
    ├── test_charts.py  9 chart checks — contents, buyers, staleness, rate
    ├── test_aftermath.py 7 checks — salvage, standing, and who is glad
    ├── test_notes.py   8 field-note checks — filed, counted, kept, reachable
    ├── test_layers.py  5 layer checks — no Qt below, no ledger above
    ├── test_cargo.py   6 cargo-contract checks — the board offers no traps
    ├── test_freight.py 9 freight checks — the desk, its floor, its stock,
    │                   and a career
    ├── test_workings.py 7 mining checks — the rig stops when the hold is full
    ├── test_burns.py   7 burn checks — heat, cooking, and a real profile choice
    ├── test_bench.py   5 bench checks — the draw matches what the screen says
    ├── test_works.py   5 works checks — nothing gated behind a phantom tech
    ├── test_overtures.py 5 checks — the preview is what the overture does
    ├── test_seats.py   6 seat checks — what taking a station is worth
    ├── test_founding.py 5 checks — the seed dialog says what will grow
    ├── test_attempts.py 6 checks — the odds shown are the odds rolled
    ├── test_reach.py   6 reach checks — the chart's wall is a real wall
    ├── test_plans.py   8 plan checks — the model is the ship, and it is solid
    ├── test_picture.py 8 checks — the picture shows the ship's condition
    ├── test_courting.py 8 checks — a gift is seen by the recipient's enemies
    ├── test_thermal.py 12 checks — guns and helm both bounded
    ├── test_helm.py    5 checks — every number on the burn board is accounted
    ├── test_grants.py  5 checks — every colony grant is read, and explained
    ├── test_postings.py 5 checks — the board only offers work you can reach
    ├── test_counter.py 6 checks — the board's price is the counter's
    │                   price, on the screen as well as in the helper
    ├── test_landing.py 6 checks — walking home beats stranding
    ├── test_charting.py 5 checks — a chart is dated, and goes off
    ├── test_conviction.py 6 checks — every event an officer cares about fires
    ├── test_bench_kinds.py 5 checks — evidence names are real, tech is reachable
    ├── test_envoy.py   7 checks — the preview is the answer, both doors alike
    ├── test_seatwork.py 5 checks — the crew hold their seats either way
    ├── test_thermal_doors.py 5 checks — every heat door goes through one gate
    ├── test_ventures.py 6 checks — both sides of a venture are costed
    ├── test_exchequer.py 10 checks — the powers' purses: income,
    │                   upkeep, building, retrenchment, the venture stake
    ├── test_climbs.py  5 checks — the conn sells no climb the tank cannot
    │                   make, and prices the ones it refuses
    ├── test_company.py 6 checks — who may be ordered to sail in company,
    │                   and what feeding them costs
    ├── test_parley.py  6 checks — the odds on talking your way out, stated
    │                   and then measured by hailing four hundred times
    ├── test_wayhome.py 8 checks — the walk back to the lander, priced against
    │                   what walking it spends
    ├── test_abilities.py 6 checks — every bridge ability fires, is bounded,
    │                   and says what it will do
    ├── test_levy.py    5 checks — the levy on a holding: taken, received,
    │                   and said out loud
    ├── test_fog.py     10 checks — what the chart shows about a star nobody
    │                   of yours has looked at, the body count included
    ├── test_wharfage.py 10 checks — the due on your own trade: conserved,
    │                   named on the board, waived at a free port, priced by
    │                   standing and by the size of the berth
    ├── test_accord.py  10 checks — a treaty's two clauses are real: the
    │                   relief lands at their quays and nobody else's, the
    │                   charts are priced at what a broker would take, the
    │                   desk quotes both before signing, and proposing one
    │                   and accepting one deliver the same instrument
    ├── test_industry.py 10 checks — a licensed process changes a market
    ├── test_orderplan.py 6 checks — every order says what it will do
    ├── test_turnplan.py 8 checks — and says it about the *turn*: the figure
    │                   on the button is where the hull ends up, played over
    │                   2,000 turns, with the gunner you left behind named
    ├── ground_ai.py    a party leader good enough to measure the ground with
    ├── suites.py       the suite table `__main__` dispatches from
    ├── test_beginnings.py 9 checks — the commission you pick is the one you get
    ├── test_legacy.py  7 aftermath checks — an ending is a turn, not a stop
    ├── test_instruments.py 5 checks — a gauge agrees with the ship and itself
    ├── test_lopsided.py 9 checks — what one missing engine of a pair costs
    ├── test_pilot.py   9 checks — a throttle and a coast the pilot can reach
    ├── test_volley.py  7 checks — the gunner's middle: fire some of them
    ├── test_gunboard.py 3 checks — the board, pressed and read off screen
    ├── test_revived.py 5 checks — what the revived dead fields now do
    ├── test_voices.py  8 checks — the game speaks with no model reachable
    ├── test_grudges.py 9 checks — memory reaches the price and the board
    ├── test_gunnery.py 5 checks — what a weapon delivers is what the bridge said
    ├── test_controls.py 4 checks — every control that is not a button
    ├── interact.py     plays by pressing what is on the screen, not by calling sim
    ├── test_bridge.py  6 checks — the protocol answers, always, and stays local
    ├── test_manual.py  13 checks — the manual cannot go stale, options cannot lie
    ├── test_tutorial.py 12 checks — it will not take your word for it
    ├── chronicle.py    one captain, one save, a decade of doing everything
    ├── test_chronicle.py 3 checks — that decade, through every screen
    ├── capture.py      renders every screen offscreen, for the README
    ├── captain_bot.py  the long-game captain the playability checks fly
    ├── probes.py       the newer efficacy probes, split out of levers.py
    ├── test_dig.py     7 dig checks — strata, methods, banking, backfilling
    ├── test_resume.py  5 resume checks — anything half-done survives a save
    ├── efficacy.py     the harness: neutralise a feature, measure the world
    ├── levers.py       one entry per claim the game makes about a number
    ├── test_efficacy.py 31 checks — every feature has to move something
    ├── test_reachable.py 4 reachability checks — nothing written and uncalled
    ├── test_verbs.py   10 verb checks — every control in the game, clicked
    ├── test_flight.py  5 helm checks — determinism, intercepts, routing
    └── test_ui.py      24 interface checks, rendered on Qt's offscreen platform
```

## How the layers connect

The dependency rule is one-directional and worth preserving:

```
data/  ──►  world/  ──►  sim/  ──►  ui/  ──►  __main__
                    core/ is available to everything
```

- **`core/state.Game` owns time.** `advance_days(n)` is the only clock: it ticks
  research, colonies, build slips, hull regrowth, every market, payroll, air,
  morale and the Bloom, then checks for victory. Nothing else advances a day.
- **`sim/` never imports Qt.** It takes a `game` and returns plain data. That is
  why the simulation suite can run headless and why the whole rules layer is
  testable without a display.
- **`ui/` never mutates state directly** — a view calls a `sim/` function, then
  `win.refresh()`, which recomputes derived values and redraws.
- **`ship.stats()` is the single source of derived numbers.** Chassis base +
  fitted parts + research bonuses + officer skills, with a power-brownout
  multiplier. Anything asking "how far can this ship jump" asks `stats()`.
- **Views subclass `ui.widgets.View`** and implement `build()`; the base class
  clears and rebuilds the column on every refresh. Simple and fast enough — a
  full screen is a few hundred widgets.

## The parts that will bite you

- **`MainWindow.__init__` refreshes before it is fully built.** The tutorial bar
  is constructed forty lines into `__init__` and refreshes itself on
  construction, and it asks `win.current` — which was assigned *after* it. So
  opening a chronicle that already had a tutorial running raised
  `'MainWindow' object has no attribute 'current'`, which is the reload case: a
  save made mid-lesson. Every check built the window first and started the
  tutorial after, so none of them went through that door. `current` and `views`
  are initialised at the top now; anything a child widget asks about during
  construction has to exist before the child does.
- **Two true-sounding claims can contradict each other, and the answer is
  usually scale.** "A tutorial step that is already true should skip itself" and
  "a captain who did it already is not advanced for free" are irreconcilable
  from state alone — one incidental survey and two years of them are the same
  fact at different sizes. `tutorial.SETTLED_IN_DAYS` is the distinction: inside
  the first month everything is taught, after it what the chronicle can show you
  have done is stepped over. Both checks pass unchanged.
- **Price is not value, and the exchequer chose by price.** `_invest` took the
  cheapest work it could afford — and the equilibrium the upkeep curve is built on
  means the cheap works are the ones that never pay: promoting an outpost to a
  station adds 90 a day of yield and 90 a day of upkeep, *net nothing*, and
  promoting a station to a hub is 60 a day worse than not bothering. Founding a
  berth clears 60 a day; settling ground clears 32. So "take the cheapest" bought
  the two works with no return before either with one, and the powers planted
  **six settlements in year one and none in the seven years after**. It sorts by
  payback now, with never-pays last by cost — which is exactly what a Fleet Hub
  should be: what you buy with money you have nothing better to do with.
- **`Body.id` is the body's index within its system.** 155 bodies in a sector
  share **six** distinct ids, so anything keyed on `body_id` alone matches a body
  in every system at once. `Colony` has keyed on the `(system_id, body_id)` pair
  since it was written; `sim/settlement.py`'s first draft did not, and six
  settlements masked the whole sector — `sites_for` went from twenty-odd
  candidates per power to zero inside a year and nothing was settled again.
- **A quoted payback has to count the years the thing loses money.** A settlement
  manages 25% of its output on day one, which is 11.5 a day against 14 of upkeep:
  **−2.5**. Two fresh ones moved a power's income *down*, 724 a day to 720.
  Dividing cost by the mature rate reads 1,000 days where integrating the ramp
  gives **1,485**, and the difference decides whether settling looks better or
  worse than founding a berth. `settlement.payback_days` is the one door and
  `exchequer.payback` asks it.
- **A layer that cannot ask who is looking should not price what it finds.**
  `world/planets.survey_body` used to add `lf.value * 0.25` of research for every
  organism it catalogued — inside `world/`, which by the layer rule cannot see the
  `Game` and therefore cannot know whether anybody aboard can read a radiotroph.
  The grant moved to `sim/biology.harvest`, so the same body pays two captains
  differently: **116 points of research unread against 149 read** on the same
  catch. The constant went with it (`SPECIMEN_SHARE`), out of the middle of the
  survey arithmetic.
- **Grouping by a key is how you find out the key was lying.** `FORMS` is a pool
  of body plans — "jointed swimmer", "plated crawler" — and one entry was
  `"chemotrophic reef"`. The generator picks the form and the metabolism
  independently, so it cheerfully filed a chemotrophic reef as a photoautotroph,
  and nobody could see it until the catalogue put the two beside each other. There
  is a check now that no body plan contains a biochemistry stem.
- **Two guards can excuse each other, and one pair did for a whole feature.**
  `test_grants` asks whether every colony effect is read *by name* somewhere;
  `test_declared` asks whether every declared field is read. The `drift` effect
  passed the first because `sim/ship.py` mentioned `"drift"` — to set
  `Stats.has_drift` — and `has_drift` passed the second because it was on the
  allowed list as a flag waiting for a mechanic. So the colony effect was
  "consumed" by a dead ship stat and the stat was excused by a promise, and
  between them **a 21,000-credit module and an 18,000-credit colony did nothing
  at all**, with both descriptions promising it plainly. When you excuse a field,
  check that nothing else is leaning on the mention.
- **Traffic was always derivable anywhere and only ever asked about here.**
  `traffic.in_system` is a pure function of the sector and the day, so the hulls
  working *any* system have always been computable — and every caller passed the
  system the ship was in. `traffic.plotted` and `mesh_reaches` are the gate now:
  you see where you are, where a CHORUS Node aboard plus a visit lets the mesh
  report, and any system holding a Node colony of yours (`colony.drifting`,
  written beside `colony.watching` rather than as another published key nothing
  opens). The chart marks systems reporting hulls nobody claims, and
  `ui/mesh_panel` says which and what.
- **"Inline hints" turned off under four per cent of the hints.** `sim/options.py`
  opens with the rule that *an option that changes nothing is a lie*, and the
  setting was gated in exactly one place — `View.hint`, called **10** times
  against `widgets.note`'s **270**. The options page describes it as "the short
  explanations under panel headings", which is what `note` draws. Measured on the
  port screen: **89 labels with hints on, 89 with them off.** `note` reads
  `widgets.HINTS` now, pushed in by `MainWindow.apply_options` — the function
  whose docstring already said it exists to push settings into the parts of the
  window that hold their own, and the same arrangement `core/llm.py` uses for the
  speech settings. Two things to know if you touch it: a withheld note is a
  **hidden label, not `None`**, because fifteen places add one straight to a
  layout with `addWidget` and Qt answers `None` with "cannot add a null widget"
  (a hidden widget is excluded from its layout and takes no space); and
  `widgets.HINTS` is module state for the life of the process, so a check that
  turns hints off **must restore them in a `finally`** or every suite after it
  renders without explanations.
- **`conn.apply` takes `ticks` and `throttle` by keyword only, and that is a bug
  fix.** They used to be positional, and four checks called
  `apply(conn, axis, main, throttle)` — putting the throttle into `ticks`, where
  `max(1, ticks)` quietly rounded it to one, and leaving the throttle at its
  default. So every flight those checks flew had **the main drive wide open**,
  which is the one thing `pilot.usable_throttle` exists to prevent: an
  unthrottled drive made a bigger engine *worse*, because one tick of a fusion
  torch is 124 m/s and the computer would light it to trim ten. The checks were
  verifying a ship the game does not fly, and one of them —
  "a lopsided hull still makes orbit, slower and dearer" — was passing for that
  reason. Re-measured at a body where the drive does the work, one engine takes
  **2.32× the time and 1.91× the mass**; at a small body, where an orbit climb is
  thruster work, the same comparison comes out 0.79× and the cap has nothing to
  bite on. If you add a call to `apply`, the signature will not let you make
  this mistake.
- **An approach with nothing left to burn is over.** Every orbit check flew with
  `conn.rcs = 99999`, and `orbits.heights_for` offered a rung on `holdable` alone
  — whether the thrusters are *fine* enough — and never asked whether the
  tank was *big* enough (it does now: `test_climbs` flies the offer on the tank
  `conn.start` found, and the unlimited tank is what hid this for as long as the
  ladder has existed). Flown with the twenty tonnes a hull carries, the high
  rung of a 153 km asteroid spent the lot in about two thousand ticks and then
  ordered a burn every tick for another eighteen thousand, refused each time by
  `can_burn`: nothing moved, nothing was said, the approach never ended.
  `outcome.resolve` now ends it — as `orbit` if the hull is in a sound one, which
  it reports along with the height it actually reached, and as `dry` if it is not
  in orbit and no longer closing. Still closing is left alone: a dry hull can
  arrive on momentum, and taking the approach away from it would be wrong.
- **Two fields were being written and read by nobody for as long as their
  features have existed.** `Rumour.heard_at` recorded the port you were told
  something at, and truth was a per-kind coin flip — so a story about the far
  side of the sector told at a lonely outpost was exactly as good as one about
  the next star over told at a Fleet Hub. `Mind.met` and `Mind.first_met` counted
  how often somebody had dealt with you and since when, while every decision in
  the game came from standing — what you have *done* — and nothing from
  acquaintance — who you *are* to them. Both are read now
  (`rumours.provenance`, `memory.acquaintance`), and the lesson for anything
  similar is that the field being present in the save is not evidence anybody
  consults it. `test_declared` catches a field nothing reads by *name*, which is
  why these two survived: `.met` and `.true` are read all over the codebase on
  other objects.
- **A distance constant has to be measured against the sector, not chosen.**
  Provenance grades a story by how far it has travelled, and the first draft used
  11 and 55 light-years for "local" and "far". Measured over 4,264
  port-to-system distances: median 27, 80th percentile 40, longest 69 — so 55 was
  the 96th percentile and **three per cent of stories ever reached the far end of
  the scale**. At 11 and 42 the bands come out 30/27/44%, and stories run from
  77% true down to 45%.
- **A stock can be genuinely untraded, and the drift must leave it that way.**
  `tick_market` adopted a baseline of 1.0 for any stock that had none, and the
  supply floor lifted a zero supply to 0.02 so that the shim then adopted *that*.
  Between them, a good `make_market` deliberately left out of a port was on sale
  there one day into the chronicle: unlicensed seed is stocked at **9 ports in
  21** and **all 21 sold it after a single day**, which is most of the point of
  contraband gone. A stock with no baseline *and* no supply is skipped now. It is
  the only way a market says "not here", so anything that writes supply or
  baseline has to preserve it — `sim.industry.industrialise` is the one thing
  allowed to open one, and it does so deliberately.
- **Technology reaches markets through `Stock.works`, not through prices.**
  A licensed process multiplies the *baseline* of one good at every berth its
  holder owns, so the daily drift settles onto it and the change is permanent —
  where a shock multiplies the price and lifts cleanly. Keeping the two apart is
  what lets a check tell an industry from a strike, and the first draft of that
  check could not: it read a 6% fall where four of five berths had fallen 11%,
  because the fifth had a strike on and its price had gone *up*.
- **A forecast quotes what the captain would be charged.** `industry.forecast`
  prices a copy of the stock through `buy_price` with the captain's standing and
  haggling in it. A check comparing it against a raw `buy_price(market, cid, 0)`
  read every berth as 40–50% out in the same direction — the signature of a
  scale factor, which here was a trade bonus of 0.48.
- **A port is not scenery any more, and things that cached one will break.**
  The powers keep treasuries (`sim/exchequer.py`): each berth pays its holder
  `level × 90` a day and costs `30 × level²`, so an outpost and a station both
  clear about sixty and a Fleet Hub very nearly pays for itself and no more. A
  surplus founds or promotes one up `world.galaxy.PORT_KINDS`; a deficit takes
  the cheapest one down a step, and an outpost that goes down a step **closes,
  taking its market with it**. Two things fell over the first time one did:
  `test_geography` crashed on `system.market.stock` for a berth it had listed
  eight years earlier, and the register cheerfully offered a two-year-old price
  at a port that no longer existed. Anything that holds a system, a port or a
  market across a passage of time must re-check that it is still there.
  `promote`, `found` and `demote` are the only writers of a port's level, and
  `demote` will not close the berth the player's own hull is sitting in.
- **`tick_market` needs to be told how big the port is.** `make_market` scales
  the opening stock by the berth's level and the daily drift then pulled every
  commodity at every port toward the same `supply × 60` regardless — so within
  about a month a Fleet Hub held exactly as much cargo as an outpost, and the
  level was decorating the opening inventory and nothing else. It takes a
  `level` argument now and `core/clock.py` passes the port's own. Measured a
  year in: outpost 1,300 t, station 1,779 t, hub 2,832 t, holding steady
  instead of converging.

- **`HULL_SCALE` in `sim/ship.py`** converts the descriptive `hull` figures in
  `data/chassis.py` into combat hit points. Chassis numbers are written to read
  sensibly against each other; this constant tunes fight length. Change it and
  every engagement in the game changes.
- **`MAX_LANE` in `world/galaxy.py`** guarantees no star sits further from its
  nearest neighbour than a starting hull can jump. Without the relaxation pass
  that enforces it, some seeds strand the player on turn one. It does *not*
  guarantee the sector is traversable: flood-filling from the start at starting
  jump range reaches between 2 and all 42 systems depending on the seed, median
  13, with a quarter of sectors under eight. Opening the rest means a better
  drive. `sim/reach.py` computes that component, and `reach.plan()` costs the
  way out: the technologies still needed and their research points, the
  credits, and each material with the reachable ports that stock it. **A pocket
  is a long project and not a trap** — measured across 24 walled sectors, the
  smallest of them two systems, every one could supply its own way out. A check
  keeps asking rather than trusting that measurement.
- **One helper feeds the quote and the till.** `market.quote_buy` /
  `quote_sell` apply the grudge bias, and `note_prices`, `trade.buy/sell` and
  `contracts.cargo_cost` all read them. Pricing a contract's cargo with the raw
  `buy_price` while the counter charged the adjusted one put the board's quote
  nearly nine hundred credits out, which `test_cargo` caught the day grudges
  landed. If you add a place that shows a price, use the helper.
- **The tutorial never diverts navigation.** Everything else you can be
  part-way through — a battle, a trench, an aftermath question — is guarded in
  `window.go()`. The tutorial deliberately is not: a tutorial that stops you
  doing the thing it is describing is worse than none, in a game whose premise
  is that there is no track. A check walks all twelve screens with a lesson
  open and fails if any of them diverts.
- **Nothing may touch a widget after emitting a signal that could delete it.**
  Almost every card handler rebuilds its own screen, and `View.refresh`
  unparents the old widgets — which frees the C++ object immediately. `Card`
  emitted inline and then called `super().mousePressEvent(ev)` on a corpse,
  which aborted the process: clicking a body or a technology killed the game.
  `Card` defers the emit by one turn of the event loop. If you add a widget
  whose click rebuilds anything, do the same.
- **Clicking is not the same as pressing a button.** `test_verbs` drives every
  `QPushButton` on every screen, and Qt emits those safely after the press
  completes — so the crash above lived behind what read as full coverage.
  Auditing the rest found 14 line edits, 13 spin boxes and 5 combo boxes that
  nothing had ever touched, and the first one driven **segfaulted the
  process**: the manual's search field rebuilt its own view on `textChanged`,
  which fires mid-keystroke. `test_controls.py` drives every other kind of
  control there is — cards, combos, spinners, typing a character at a time,
  and the ship plan's drag and wheel.
- **`ui/widgets.defer()` is where the rule lives.** Anything wired to a signal
  whose handler rebuilds the emitting widget goes through it. A rebuild that
  replaces a field the player is typing into must also restore focus and the
  cursor, or the field silently accepts one character and no more.
- **`game.day` is a whole number, and `advance_days` is what keeps it one.**
  Callers pass fractions — a short transit, a burn quoted to a tenth of a day —
  and the clock used to take them, drifting `day` to a float. Everything
  downstream assumes an integer: `day % 365`, contract deadlines, chart dates,
  the day a memory formed. The heading bar crashed outright on the first
  fractional day. The fraction is carried rather than dropped, with an epsilon,
  because a hundred tenth-days sum to 9.999999999999998 and would lose a day
  every ten.
- **A driven session must not open behind a modal dialog.** The briefing and
  the tutorial offer both block on `exec()`, so a watcher saw a pop-up while
  the bridge quietly played the game underneath it. `--bridge` skips them, and
  `blocked`/`dismiss` let a caller see and clear anything modal.
- **Anything that blocks needs neutralising before a session can drive it.**
  `QDialog.exec` is the obvious one; `QInputDialog.getText` is *static* and
  does not go through it — the shipyard asks a new hull's name that way, and a
  session that pressed *Lay down* waited ten minutes for an answer nobody was
  going to give.
- **`--bridge` serves the window you are looking at.** `bridge/attached.py`
  puts the protocol in front of a live `MainWindow` and marshals every command
  onto the Qt thread before it touches the game — the socket runs on another
  thread and the interface reads the `Game` from the main one, so anything else
  is a data race. Loopback and token-gated like the headless bridge.
- **`credits` is a builtin.** So is `id`, `type`, `input` and `format`. Calling
  one by mistake does not raise `NameError` — `credits(x)` calls the
  interpreter's easter-egg `_Printer` and fails two suites away as
  "`_Printer.__call__()` takes 1 positional argument but 2 were given". If you
  import `core.util.credits`, import it under its own name.
- **A screen's keys come from `data/screens.py`, not from its position.** The
  rail used to derive them as "1–9, then 0 for the rest", so the moment an
  eleventh screen was added the Codex and the Aftermath both bound `0` and one
  of them had no key at all. The table is read by the window *and* by
  `sim/manual.py`, which is on the other side of the layer rule, so the Keys
  page cannot drift from the rail.
- **The language model is off unless it is switched on, and nothing depends on
  it.** `SEEDFALL_LLM` gates it, `llm.complete()` returns `None` whenever there
  is nothing there, and every speaking path already had to work offline so
  `None` is the ordinary case rather than an error. Speech reads state and
  never writes it, which is what makes the whole feature removable. If you add
  a voice, the written path is the one that has to be good.
- **You hold the technology for everything bolted to your hull.**
  `parts_available` filters the shipyard by what you have unlocked, so a fitted
  part whose technology you lack can be removed and never put back. The shipped
  NAVIS carried three: a Reaction-Mass Organ, a Radiator Bloom and a Mining
  Root. Pulling the drive on day one emptied the slot permanently and left the
  drive dropdown offering nothing at all. `beginning.tech_of()` enforces the
  rule structurally — whatever `new_game` fits, it also grants — so no future
  hull or opening can reintroduce it, and `STARTING_TECH` names the three
  outright so the constant is honest about what a captain knows.
- **An index into `game.system.bodies` is not a location.** `Dig` used to hold
  only `body_index`, resolved against whatever system the ship was in *now*, so
  a trench worked from anywhere else read a different body's fatigue — or
  raised `IndexError` against a shorter body list. Digs are saved, so the wrong
  body outlived the session. `Dig.system_id` pins it and `dig.site_of()` /
  `dig.at_site()` are the only correct ways to reach the ground it is in.
  Anything else that stores a body index needs the same treatment.
- **`GRIND_TURN` / `MAX_TURNS` in `sim/combat.py`** stop two well-armoured hulls
  grinding forever. Armour is also floored at 15% damage leak-through for the
  same reason.
- **`sim/ship.py` owns the thermal rule; `combat` and `flight` both defer.**
  `HEAT_CEILING` and `cook()` live next to `cool()`, because the hull owns its
  own physics and both the guns and the helm put heat into it. `combat`
  re-exports them. Two copies of this rule existed briefly and drifted
  immediately — the guns were bounded and the helm was not, and a captain
  fresh off ten hard burns routed on turn three at 51% hull *holding fire the
  whole way*.

  **Put heat in with `ship.add_heat`, which clamps on the way in.** This used
  to say "call `cook()` wherever heat is added; there are exactly two such
  places" — and there were six. A crossing watch, a flight incident, an
  action's own effects and taking a hit in combat all added heat raw, so a
  fault alone took a hull sitting at the ceiling to 2.36x its cap. Asking
  callers to remember is what four of six did not do.
  `tests/test_thermal_doors.py` fails on any `\.heat +=` outside `ship.py`.
  (`sim/customs.py` has its own unrelated `add_heat` — scrutiny from the
  revenue, not thermal load.)
- **Heat is bounded by `HEAT_CEILING`, and that is load-bearing.** It used to
  be unbounded, and because the overheat penalty scales with how far over the
  cap you are, it compounded: a Bastion firing the five heavy mounts it has
  slots for went 68 → 132 → 187 → 243 → 279 and routed itself on turn five at
  93% hull. `cook()` is called from `_fire`, which is the only thing in the
  game that adds heat, so one clamp at the source covers every hull. An
  end-of-turn clamp was tried too and measured to change nothing at all, so it
  was removed rather than left in looking useful.
- **Every tuning constant is pinned, and that is measured rather than
  assumed.** All 153 module-level numeric constants across `data/`, `sim/` and
  `core/` were swept: doubled, halved and zeroed, and every one is noticed by
  a check. The sweep also reports *where* the protection comes from — a
  constant caught only by the wide set is held up by a suite that happened to
  walk past, which is a thinner thread than a check written for it.
  `consorts.WITHDRAW_AT` was the only one in that state and now has its own.
  Re-run with `python3 -m seedfall.tests.tripwire`; about seventy minutes, and
  never alongside the suite, because it rewrites source while it works.
- **A forecast has to clamp what the hull clamps.** `order_preview` quotes
  what the heat *becomes*, not the raw sum: a salvo worth 74 on a hull at 30
  with a 50 cap stops at the ceiling, so the line reads "heat 30 → 100 of 50 —
  pinned at the ceiling" and not "→ 104". My first draft quoted the sum, which
  is the same defect the function exists to fix, one layer up.
- **A screen with two buttons has to price both of them.** The ventures panel
  showed the odds as they stood, priced *backing*, and left "Work against it"
  bare — no standing cost, and no hint that either button moves the odds by
  `SWAY`: measured, a 51% venture becomes 81% backed and 21% opposed. It never
  mentioned that being right afterwards pays again either. `RIGHT_BACKED` and
  `RIGHT_OPPOSED` were bare numbers inside `_resolve`; they are in
  `data/ventures.py` now and `ventures.preview` reads the same ones.
- **`tripwire.KIN` is hand-written, and a stale entry fails silently.** The
  tool runs a constant against its own neighbourhood first and only pays for
  the wide sweep if that passes. An entry naming a suite that no longer
  exists makes `python -m seedfall.tests <name>` run nothing and exit zero, so
  the fast stage "passes" every time and every constant quietly costs the full
  run — measured, `ship` swept in 17s with a fast path and 240s without. An
  entry naming a `SLOW` suite is worse: the verdict then depends on whether a
  module has an entry at all. `test_harness_guard` holds both, and requires
  every module with constants either to have a fast path or to be named as
  having no suite that covers it. It caught its first live case in
  `SETTLED_IN_DAYS`: `tutorial` was on the `SLOW` list **for building a
  window**, which cost the constant its only witness. That list means "too
  expensive to run once per constant" — and the tutorial suite sets the
  offscreen platform itself and runs in two seconds. Needing a window is not a
  reason to exclude a suite; costing thirty is.
- **Every action that spends a turn must run the seats.** `take_turn` takes
  two shapes: `{"type": "station", "order": ...}`, which runs the crew-station
  system, and the older `{"type": "fire", "weapon_id": ...}` family, which the
  battle screen still uses for the firing picture's per-mount buttons and the
  ability buttons. The older shape never called `_run_stations`, so picking a
  mount meant nobody flew the ship and nobody stood in engineering that turn —
  measured, heat 30 ended at 24.0 through the old door and 19.44 through the
  new, with `helm_order` still `None`. Only `move` had ever been migrated.
  `_run_seats` is now called from both. Note the helm runs *before* the guns
  on both paths, so a mount that bears when you press the button may not bear
  when the shot goes.
- **`TREATY_WEIGHT` is read by both doors into signing one.**
  `diplomacy.perform` charges the signatory's enemies through
  `sim/allegiance.py`; `approach.answer` did not, so the same instrument with
  the same signatory cost −6 with each of three powers when you proposed it
  and **nothing** when you accepted their offer. Waiting to be asked was how
  you signed a treaty for free. Both read the one constant now, and
  `preview` states the price.
- **`preview["credits"]` is money moving; `preview["offer"]` is the price on
  the table.** They were one field, and the envoy screen rendered a haggle as
  "Treasury: +794" — a captain reading that row believed they had been paid
  for asking. Nothing is paid until the offer is accepted.
- **A fixture that names something the game does not know is invisible.**
  `inquiry.add` returns 0.0 for an unrecognised kind — silently, which is
  right for a sim that must survive an old save. `test_provisional` typed six
  evidence kinds by hand; three (`field`, `relic`, `trade`) do not exist and
  one that does (`reading`) was missing. Six of the ten branch mixes want
  `reading`, cognition 35% of it, so the suite that decides whether any
  research approach dominates measured those branches 20–30% slow. Derive
  from `EVIDENCE`, as `test_bench` always did. `tests/test_bench_kinds.py`
  checks the call sites **and** any hand-written `*KINDS` list, because the
  call site passed a variable and no search of call sites could have seen it.
- **A returned value nobody reads is a feature nobody gets.** `crew.grant_xp`
  hands back the officers it has just promoted — that is what the return is
  *for* — and all eight call sites dropped it, so `promoted` (+5 to everyone
  aboard, it is in `UNIVERSAL`) never once fired and a promotion was not even
  logged. Pass `game=` and it reports itself: the ship feels the event, the
  officer gets `PROMOTION_OWN` on top, and it goes in the log.
- **An event whose name is composed cannot be found by searching for it.**
  `loyalty.served` builds `f"{conviction.id}_served"`, so the audit in
  `tests/test_conviction.py` keeps an explicit `COMPOSED` allowance and proves
  those separately by behaviour. Anything else must appear literally in
  `sim/`, `core/`, `ui/`, `world/` or `bridge/`.
- **Two doors into the same event will drift, and the drivers use the working
  one.** Surveying a body can be reached through `actions.survey` — which the
  remote bridge and every test driver call — and through `survey.perform`,
  which the screen calls. Only the first dated the finished chart, so
  `charts.freshness` returned 1.0 for every chart a player ever made:
  `FRESH_DAYS` and `STALE_FLOOR` decided nothing, and the survey office's
  "Age of the survey" row sat behind `if fresh < 0.95` and could not fire.
  Nothing caught it because every driver in the suite went through the door
  that worked. `tests/test_charting.py` asserts both doors leave the same
  state.
- **Order the penalties after the limits, not instead of them.**
  `haul_kept` applied the carrying limit on the way home and skipped it
  entirely when the party stranded, so stranding returned 40% of an *uncapped*
  pile: 500 t collected came home as 200 t stranded against 60 t returned. The
  penalty was a reward by a factor of twenty-three, and the way to play the
  ground was to strand the party deliberately. Cap first, charge second.
- **`tests/ground_ai.py` is to the ground what `captain_ai` is to combat.**
  Walking a party at random and grabbing whatever is underfoot measures
  nothing, because it never returns to the lander, so every policy strands and
  scores the same. `margin` — supply held back for the walk home — is the one
  decision the ground poses, and sweeping it should show a peak in the middle:
  measured 29 t at margin 0, 35 t at 4, 23 t at 14.
- **Establishing state by hand can make a check unreachable.**
  `test_officials` proved the office rate worked by writing it into the dated
  `favours` dict directly. It does not get there that way: a quiet price is
  granted "this once", carries `lasts=0`, and `ask()` recorded favours under
  `if favour.lasts:` — so a zero-day favour fell straight through and the
  price code could never fire in a real game. The check exercised a state the
  game could not produce and read as coverage. Grant through the same call the
  player uses.
- **One helper for the price, and nothing applied at the till.** The office
  rate was applied inside `trade.buy`/`trade.sell`, so the board showed 36/t
  while the counter charged 31.68. `market.quote_buy`/`quote_sell` are the
  price — office rate, grudge bias and all — and `tests/test_counter.py`
  sweeps the two against each other.
  **And there was a third door nobody had swept.** The market grid on
  `ui/port_view.py` called `world.economy.buy_price` directly, so it carried
  neither the office rate nor the grudge bias, while the comment forty lines
  above it said "now it is in the quote, and the board says so". Measured with a
  quiet price in hand: the grid printed 36 and 29 while the counter charged 32
  and paid 33. A check that reads the helper can never see this — the new one
  reads the labels out of the rendered grid.
- **Wharfage is charged on top of the price, not folded into it.**
  `sim/wharfage.py` takes a share of every deal for whoever holds the quay, and
  the money moves in `collect`, which debits the captain and credits the purse in
  one function so the two cannot disagree. It is deliberately *not* inside
  `quote_buy`/`quote_sell`: a price the board can print stays a price, and the
  charge is named separately — on the board, in the ship's log, and on the
  freight desk's forecast of a run. So `res["paid"]` is the goods and
  `res["due"]` is the quay, and anything measuring what a trade cost has to add
  them.
- **A forecast of an act is not a forecast of the turn that contains it.**
  `stations.order_preview` costed each order against its own act, and
  `test_orderplan` checked it that way — by calling `run_engineering` directly.
  Both agreed, and both were answering a question the captain never asks. On a
  Bastion at 45 of a 50 cap, sitting down at engineering and ordering *vent*,
  the panel said `heat 45 → 20` and the turn ended at **74**: the gunner left at
  the guns fires everything that bears, always, whatever the heat. That is
  deliberate — it is what a battle computer is bought to fix — but quoting it
  at nobody was not, and it left the one order whose purpose is cooling
  advertised with the wrong sign while *hold fire*, which cools by 10, read as
  the order that does nothing. The forecast now steps the turn the way
  `combat.take_turn` steps it and is exact to the hundredth over 2,095 played
  turns. **The general form: ask what the player is actually choosing between,
  and forecast that.**
- **A dry run beats a better formula.** The residual error after folding in the
  other seats was the geometry moving under the forecast — worst at *present
  the broadside*, whose own blurb says everything on the flanks bears, and which
  was therefore quoted as *cooling* on eight turns in a thousand. Our guns fire
  after our own helm has moved us and before the enemy moves at all, so flying
  the order on a copy of the body is not an approximation of the answer, it is
  the answer. Copying two dataclasses retired the whole error class.
- **The ceiling belongs to the one function that adds heat.** `ship.add_heat`
  clamps; shedding is a plain `max(0, heat - x)` and never consults the ceiling.
  Reproducing that in a forecast, I clamped on every step *and on a step of
  zero* — which cooled a hull sitting above a ceiling lowered by radiator damage
  by five points a turn it never lost. `delta >= 0` and `delta > 0` are
  different programs when the hull is already over.
- **A mutation that changes nothing is not a coverage gap.** Replacing the
  salvo's arc-and-band test with arc alone failed to break any check, and the
  reason was that the two never differ at any range these hulls fight at:
  0 turns in 89. The real gap was next door — the count check ran only with full
  magazines, where "what trains" and "what burns" are the same list. Both
  mutations bit once it ran with an empty one.
- **A promise in the sales text is a claim the game has to meet.** A treaty was
  sold as "mutual berthing, shared charts, and a clause about the Bloom that
  nobody expects to be honoured" for 30,000 credits. The third is a joke; the
  other two were as well. Signing appended a faction id to a list read by
  `treaty_bonus` (+3% on the trade stat, on no screen) and by the matrix's
  "treaty" pill. Measured at Vesper Bight: wharfage 1.714% before and 1.552%
  after — and *all* of that fall was the standing the treaty granted, which
  tribute at a third of the price buys as well. Charts known: 0 before, 0
  after. `sim/accord.py` is the two clauses, and the lesson generalises past
  this one instrument: **read what a thing tells the player it does, then go and
  measure each promise separately.** A benefit that is real but invisible
  (`treaty_bonus`) and a benefit that is named but absent (berthing, charts)
  fail the same way at the desk.
- **Isolate the lever you claim to be measuring.** The first pass at checking
  the berthing clause let `perform` grant its standing, and standing is *also*
  an input to `wharfage.rate` — so the check would have passed on a treaty that
  did nothing but flatter you. `tests/test_accord.py::_sign` restores `game.rep`
  after signing for exactly this reason, and the two-doors check restores it on
  the envoy path too, where `accept_rep` lands instead.
- **Count both doors into the same act.** `treaty` can be proposed at the
  diplomacy desk or accepted from an envoy, and `data/diplomacy.py` already
  records what happened when they disagreed about `TREATY_WEIGHT` — waiting to
  be asked was the way to sign for free. Adding the charts clause to the
  proposing door alone would have been that bug in reverse; `accord.hand_over`
  is the one delivery both call.
- **A posting has to name somewhere the hull can get to.** `_pick_target` was
  documented as choosing a system "reachable in principle" and tested only
  `bloom < 0.4`; reachability is transitive and nothing checked it, so **65%
  of targeted postings named a system outside the reachable component** (15 of
  42 systems fly at the opening drive). Ask `reach.component`, which is the
  same answer the chart gives. `reach.route_to` costs the flight, and the card
  states it.
- **A coverage check pinned to one seed is a check you are getting away with.**
  `test_chronicle`'s "does everything it claims" ran on a fixed seed by
  design, but only **1 seed in 24** ever planted a colony — so it was pinned
  to the one that worked and any change anywhere would break it. The cause was
  a driver bug, not luck: `chronicle._refit_here` still tested "the system has
  a port" after `shipyard.can_refit_here` tightened to "alongside a yard", so
  `apply_refit` returned "you are not alongside a yard" and the driver dropped
  it. Putting in at a yard first took planting to 6 seeds in 48.
- **A vocabulary whitelist is not coverage.** Two suites listed
  `megastructure` in a `KNOWN_EFFECTS` set, which asserts only that nobody
  declares an *unknown* key — never that a declared one is consumed. It read
  like coverage for a flag no line of the game consulted: the ARCA Habitat
  cost 400,000 credits, 2,600 tonnes of ore and 900 days, and its one
  distinguishing property did nothing. `test_grants.py` asks the general
  question instead — *is every declared effect read by something* — and found
  a second dead key (`drydock`) on its first run.
- **A quoted burn's risk is the profile plus three surcharges** — distance,
  the star at either end of the leg, and the heat already in the hull — and
  `path_note` must account for all of them. Two were silent, and the third was
  found only because a check asked the *general* question ("does anything cost
  more than its profile without the screen saying why") rather than testing
  the two known cases. That check verifies each component separately: an
  earlier version asked only whether *some* note existed, and a surviving note
  masked a deleted one.
- **Never `git checkout <path>` to undo a scratch mutation.** Mutation testing
  wants the file back exactly as it was, and `git checkout` restores it from
  the *index* — which silently throws away the uncommitted work the cycle is
  about. It cost this file its whole change once. Read the bytes into memory
  first and write them back in a `finally:`; `tests/` mutation harnesses do.
- **Driving a fight with one repeated order measures nothing.** Combat is
  positional: a hull whose mounts are all on the beam never fires while it
  steers straight at the enemy, so a test that only ever says "salvo" reports
  zero damage and looks like a balance problem. Use `tests/captain_ai.py`,
  which picks the helm order that suits the arcs the ship actually carries.
- **The ground's one piece of arithmetic is `sim/wayhome.py`.** A step spends a
  day on ground already crossed and up to three on fresh, times the weather;
  reach the pad and the haul comes up capped at what four people can lift; run
  out first and 40% of it comes home. The screen showed "Supply · 7 days" and
  **never said how far away the lander was**, so 60% of a hold rode on a
  subtraction nobody was shown. `expedition.step_cost` is the one door for what a
  step costs and `wayhome` adds it up over the cheapest *known* route, so the
  quote and the walk cannot drift.
  Two things it must keep doing: count the days a party is **pinned** (a
  katabatic gale stops all movement, and the first version quoted "4 days home, 3
  to spare" to a party that could not take a step — a trap, found by the check
  that walks the quoted route and was refused at the first one); and refuse to
  plan over tiles nobody has seen, which needs a *tempting* unseen shortcut to
  test, since avoiding dear unseen ground costs nothing either way.
- **The long chronicle never brought a party home.** Measured over ten years: 50
  landings stranded, 32 aborted, **0 returned** — so `lift_off`, `can_lift` and
  the whole banked-haul path were never driven by a played game. It walks back on
  a costed two days' spare now: 31 returned, 14 stranded. And knowing the price
  is worth something — at the same margin, a leader reading the costed walk
  returned 15 parties of 24 and stranded 5, where one counting tiles returned 9
  and stranded 11.
- **A levy reaches the power that claimed the ground, and the captain hears about
  it.** `territory.collect_tithe` skimmed thirty per cent off a holding's output
  and `colony.tick` **threw its return away**: measured on a RADIX Mine turning out
  2.6 t of ore a day, thirty days produced 78 t, the captain received 54.6, and the
  Charter's purse moved by **nothing**. No log line, nobody the richer. It credits
  `Purse.levies` now and the clock writes "Charter took the levy off RADIX Mine —
  35.1 t ore, 1.5 t phosphate, worth about 1,089". Both halves are rules the game
  applies elsewhere: `wharfage.collect` moves both sides in one function, and #100
  exists so a deduction is never silent.
  The demand screen has always quoted "a levy would cost X a year" off a bare 0.55
  inside `yearly_worth` — with nothing receiving the levy there was no act for that
  forecast to be wrong against. `territory.value_of` is the one door now and the
  quote is exact: **8,829 a year against a year that took 8,829**.
- **A commission's reward has to exist, and there are two tech namespaces.**
  `chains.Chain.reward_tech` promised the Reliquary's captain `xenolinguistics`,
  which is in **neither** the research tree nor `data/xenotech.py`, and
  `chains._finish` appended the string to `research.unlocked` regardless — a
  reward granting no bonus and opening no node, on the one commission in four
  that hands over a whole node of a fifty-eight-node tree, advertised on no
  screen. Task #38's shape exactly. It grants `firstcontact` (First Contact
  Protocol, tier 4, 1,100 points — which is what the Reliquary is *about*),
  `chains.reward_tech_of` is the door the desk reads, and the desk says "1,100
  points of research you do not have to do".
  **The guard has to know about both namespaces.** A first sweep checked the tree
  alone and reported thirty-seven phantoms — twelve xeno parts naming ids that
  live in `data/xenotech.py` and are perfectly real, gated behind studied alien
  work rather than the bench. A check that cried wolf about those would have been
  deleted inside a month. It also refuses a *xenotech* id as a commission reward,
  because `_finish` grants by appending to `research.unlocked` and only a tree
  node can go there — caught by mutation, since `vent_symbiosis` exists.
- **The fog covers the body count, and a chart's price no longer gives it away.**
  `intel.LEVELS[0]` calls a registry entry "a body count the registry will not
  stand behind" and `LEVELS[1]`, which is what a chart buys, promises "the bodies
  are real" — and the map panel printed `len(sys.bodies)` at every rank, sized the
  marker by it, **and priced the chart at `900 + 260 a body`**. Measured across a
  sector: forty-one unknown systems, thirteen distinct prices, the count inverting
  exactly (1,160 → one body, 1,420 → two, 1,680 → three). The one fact a chart
  exists to sell was written on its tag. `intel.body_count` is the door; the price
  is `CHART_BASE + CHART_PER_LY × distance` — the trip somebody made, which is
  what a broker can honestly charge for — and its correlation with the body count
  is **0.02 against the old formula's 1.00**. `map_view.marker_radius` is a
  function rather than an expression because a mutation putting the old radius
  back left every check green.
- **`abilities.preview` is the door, and `seal` is bounded.** Six abilities are
  granted by seven fitted parts, and a played decade of seventy engagements fired
  **none of them**, so nothing had driven the module end to end. Reading it for
  that reason found `seal` doing `st.armour += 4` on a four-turn cooldown with no
  other rule: **2 armour to 34 over eight firings**, 43 over a long engagement,
  unbounded — on a part the opening NAVIS carries. Its own sentence says it "gives
  up the breached compartment", which presupposes a breach and is finite, so it
  now needs a holed layer, spends it, and never touches the pressure vessel: five
  compartments of six for +20 and then nothing. `use_ability` asks `preview` and
  **only spends the cooldown if it fires** — it used to set the cooldown before
  deciding anything, so an ability that could do nothing still went out of action
  for four turns and returned quietly.
- **A consort is a `Side`.** `sim/consorts.py` subclasses it, so `_fire`,
  `_apply_to_layers` and the arc checks work on one without changes. What that
  buys is also the constraint: anything that assumes a battle has exactly two
  sides — `_who()` did — has to learn otherwise.
- **Ordering a hull to sail in company is `consorts.sail`, not a screen.** It was
  a screen: `yard_view._set_escort` wrote `ship.escort` and `ship.docked_at`
  itself, so the rule about which hulls may be ordered out lived in whether the
  button had been drawn, and the first headless caller ordered out a hull that
  was not in the fleet. `can_sail` is the rule — yours, not the flag, not a wreck,
  somebody aboard, berthed *here*, not already out — and `data/orders.py`'s escort
  card reads the same function, having previously nagged about hulls six systems
  away.
- **A hull in company eats out of your hold.** `upkeep.complement(game,
  company=True)` counts its crew; `demand` asks with them and `draw`/`breathers`
  ask without, because stores come out of the shared hold while air and power are
  per hull. Before this a fleet was free to keep — measured, a thirty-crew escort
  moved the day's demand, the power draw and the wage bill by exactly nothing.
  `consorts.keep` is what the yard quotes, unrounded, so the figure on the panel
  is the figure `upkeep.tick` takes.
- **Counting which mechanics a played decade ever reaches is worth doing
  directly.** Wrapping the doors and playing ten years found that **seventy
  engagements deployed a consort in none of them** — `escorts_of` was empty every
  time because a chronicle never lays down a second hull, so orders, screening and
  interception had never been driven end to end by a game. `test_company` now
  drives them: four engagements, four consorts deployed, 73 turns with one
  interposed between the flag and the enemy.
- **Save identity**: `game.ship` must be the same object as its entry in
  `game.fleet`. `load_game()` re-links them after decoding; damage would
  otherwise apply to a copy.
- **Transient fields**: anything on a dataclass marked
  `metadata={"transient": True}` is skipped by the save codec. `Game.ship_stats`
  holds references to the content tables and must never be written to a save.
- **Qt mnemonics**: an `&` in a button label becomes an accelerator underscore.
  Write "and".
- **Never derive anything persistent from `hash()`.** Python randomises string
  hashing per process, so a value derived from it changes on every launch.
  Orbital phases did exactly this, and a saved game reloaded with every planet
  somewhere new. Use `core.rng.hash_seed`.
- **`View._sync_scroll()` is why screens paint correctly on the first frame.**
  Rebuilding a view's column does not tell its `QScrollArea` that the contents
  changed size, and the layout's true minimum is not known until the new
  widgets are polished — so it measures once immediately and once more after
  the event loop settles. Qt recovered on its own by the second turn, which
  made the fault invisible in play and very visible in a screenshot.
- **Adding a hull family** means touching six places: `LAYER_SETS`, `ACCEPTS`,
  `FAMILY_LABEL`/`FAMILY_TINT`/`FAMILY_NOTE`, `BASE_POWER`, `BUILD_NEED`, and
  `NO_REGEN` if it cannot heal — all of them in `data/hull_types.py`. The test
  suite checks every family for all six, and that its layer weights sum to one.
- **Xenotech ids live in `research.unlocked` alongside real technologies.**
  Anything walking that list must tolerate ids that are not in `TECH_BY_ID` —
  `tech.bonuses()` already skips them, and the gate check in `test_sim.py`
  accepts either vocabulary. Alien passive bonuses are folded in separately by
  `Game.recompute()`.
- **Study banked past a prerequisite is kept, not lost.** You can dig up the
  Phase Loom before you understand the Null Seam; `xeno.settle()` runs on the
  clock and incorporates anything whose moment has arrived.
- **A colony's numbers come from `sim/works.py`, not its class.** `yields_of`,
  `upkeep_of`, `effects_of` and `pop_ceiling` combine the class definition with
  whatever the settlement has since built. Read `col.definition.yields`
  directly and you will report what the colony produced the day it was planted.
- **Anything a work grants that needs an action, not just a number, has to be
  triggered where the work completes.** Opening a harbour was read only at
  maturation, so a colony that built one afterwards had the `port` effect and
  no market.
- **A conviction that reacts to an event nothing raises is dead flavour.**
  `data/convictions.py` names events; something in `sim/` or `ui/` has to call
  `loyalty.record()` with that exact string or the belief never fires. A check
  in `test_crew.py` greps the tree and fails on any event that is never raised
  — it caught ten of them on the day the system was written, including every
  belief the xenologist held.
- **Loyalty bands and loyalty mechanics share their edges.** `BANDS` in
  `data/convictions.py` turns on `WALKOUT` and `RESTLESS`, the same constants
  `effective_level()` uses, so the pill on the roster is a statement about what
  the officer will actually do. Move one and move the other.
- **A commission stage is an ordinary contract.** `sim/chains.py` builds one
  through `contracts.shape()`, the same function the board uses, so deadlines,
  cargo, bounties and expeditions all work untouched. What makes it a chain is
  `Contract.chain` and what happens in `chains.on_contract_done()`.
- **`contracts.active()` is board work only.** Commission stages are excluded
  from it and from the `MAX_ACTIVE` cap, because they are not work you chose to
  juggle. Use `contracts.all_open()` when you genuinely mean everything live.
- **`shape()` takes its scale before it writes the title.** A stage that asked
  for half the usual tonnage used to be titled with the full figure and
  complete at the halved one — a posting nobody could plan a hold around.
- **`rumours.circulating()` must stay pure.** It runs every time the port desk
  is drawn. Deciding truth used to plant what the story claimed, which seeded
  bloom and buried relics across the sector merely because somebody looked at a
  noticeboard. Truth is now a dice roll at circulation; `plant()` runs in
  `take()`, when you have actually committed to the lead.
- **Intel levels are derived, never stored.** `intel.level()` reads
  `body.surveyed`, `system.visited` and the bought-chart list, so nothing has
  to be kept in step. Add a way to learn about a system and it belongs in that
  function.
- **Volatiles are never buried below an open cut, and neither is whatever a
  body is advertised as.** `mining._depth_of()` enforces both. Fuel at depth
  two strands a captain with no bore and no reaction mass — the same deadlock
  the mining root's `drink` was added to prevent — and a rock listed as
  ore-bearing that needs a shaft is a survey that lied.
- **Seams are derived from `body.resources`, never stored.** Depth comes from
  `hash_seed` of the body and resource, so every existing save has seams
  without a migration and the same rock always hides the same thing in the same
  place. Never use `hash()` here; see the note above about orbits.
- **`STARVED_FLOOR` is why a new captain is not stuck.** A programme runs at
  that fraction with nothing on the bench; evidence buys the rest. Set it to
  zero and a captain who picks a project on turn one and flies makes no
  progress at all, which reads as a broken game rather than a hungry one.
- **A programme's evidence mix comes from its branch**, in
  `data/inquiry.BRANCH_MIX`, not from each of the sixty-one technologies. A new
  technology needs no work there; a new *branch* does, and `test_research.py`
  fails if one is missing.
- **An evidence kind nothing grants is an empty locker.** The same greping
  check as the convictions: every kind in `EVIDENCE` must appear as a literal
  in a `sim/` or `ui/` call to `inquiry.add`.
- **`Stock.shock` is kept apart from `Stock.supply` on purpose.** The daily
  drift pulls supply toward equilibrium; if a blight were folded into supply
  the drift would quietly erase it, and expiring it could never restore the
  original price. `market.apply_to_markets()` recomputes every row from the
  live shocks wholesale rather than adjusting, so an expired shock lifts
  cleanly and two overlapping ones cannot drift out of step.
- **The register is memory, not observation.** `market.note_prices()` writes
  down what a port pays only while you are standing in it, and
  `market.confidence()` decays what you wrote. Nothing should ever read a
  distant market directly — that is the whole mechanic.
- **A weather condition gated on a biome that does not exist is unreachable.**
  `data/weather.py` gates whiteouts and downpours on biome ids, and those must
  be real ones from `world/planets` — the first draft invented "ice" and
  "ocean" and silently lost two of its seven conditions. `test_ground.py`
  checks every gate against a real galaxy.
- **Anything that stops the party moving must leave something it can do.**
  A katabatic gale refuses movement, so `expedition.shelter()` is always
  available and always costs a day of supply. Without it a pinned party can
  neither progress nor die and the expedition simply stops.
- **`diplomacy.drift()` is what stops the sector ratcheting shut.** Every
  blockade and censure is a debit; with nothing pulling the other way a decade
  of background politics drove every pair far below `CONCORD_RELATION` and left
  an ending unreachable through no fault of the player. Grievances fade toward
  `INITIAL_RELATIONS`. Any new faction behaviour that moves relations needs to
  be weighed against it.
- **Ventures never annex a system you hold a colony in.** `_claimable()`
  excludes them. Losing a settlement to a registry filing would be good drama
  and would also silently break the colony that is still pointing at it.
- **Never size anything against `chassis.mass_t`.** Structural mass runs from a
  sixty-tonne SPORE to a twelve-billion-tonne LEVIATHAN, so any threshold built
  on it is meaningless for most of the range. `sim/loading.py` sizes capacity
  from slot count and hold rating, which are on the same scale as the parts and
  cargo that fill them.
- **Loading affects jump range at 45% strength, deliberately.** A full hold
  costing speed is a trade; a full hold leaving a captain unable to reach the
  nearest system is the stranding deadlock this project has hit twice.
  `test_design.py` checks the laden jump against the nearest neighbour.
- **A new system is not finished until `data/orders.py` can point at it.**
  Fifteen cycles each added something perfectly discoverable to whoever had
  just built it; a new captain saw a chart, one log line, and no sign any of it
  existed. Every entry there needs a predicate of the same id in
  `sim/orders.py`, and `test_orders.py` fails on either half being missing.
- **Anything persistent on `Game` needs a reader.** `test_orders.py` walks the
  dataclass fields and fails on any that nothing loads — it caught a levy
  counter that incremented and changed nothing, and a death reason the game
  recorded and never showed.
- **Never compare combatants by raw hull and raw damage.** Enemy hull is a
  chassis lottery that does not track difficulty at all — `make_enemy` picks
  from a faction pool and scales hull only 10% per difficulty point — while
  armament and armour both track it cleanly. `assessment.weight()` compares
  turns-to-break after armour, and its thresholds are calibrated against 320
  measured fights rather than guessed.
- **Most fights end when somebody's nerve goes, not their hull.** Any model of
  who is winning that ignores resolve reads far bleaker than the game plays,
  which is why the thresholds sit where they do rather than at the obvious 1.0.
- **Build a fresh hull for every fight in a balance measurement.** Reusing one
  ship across a run silently starts every fight after the first with a wreck.
  It reads as "encounters are brutally hard" and sent an entire afternoon's
  tuning the wrong way before the artefact was spotted.
- **Nerve is driven by the fight, not the clock.** `_end_of_turn` once drained
  resolve purely on the turn counter, and the enemy lost it twice as fast as
  the player, so an unarmed hull drove off a battleship three times in four by
  waiting. It now turns on damage taken, being behind on damage, and futility —
  that last term is what keeps endurance a real strategy for a hull built to be
  hit.
- **Every low-tier weapon in the game is grown-family.** A fabricated hull at
  tier one can mount none of them, which is why faction warships used to arrive
  unarmed. `encounters._weapon_pool` raises the tier until something fits.
- **Qt swallows exceptions raised inside a slot.** It prints a traceback to
  stderr and carries on, so `button.click()` returns perfectly happily and a
  test that only clicks sees nothing wrong. This is why fleeing and hailing
  could be broken for a whole cycle while `test_ui.py` rendered every screen
  and passed. `test_verbs.py` installs a `sys.excepthook` to catch them; if
  that trap ever stops working every verb check goes quietly green, so there is
  a check for the trap itself.
- **Rendering a screen does not press its buttons.** `test_ui.py` proves the
  screens draw; `test_verbs.py` proves the verbs run. They are different
  claims and a refactor can break the second without touching the first.
- **`responses.growth_multiplier()` is read in `threat.tick`, and that is the
  only thing making provocation matter.** It was computed and read by nothing
  at all on the first pass — the same shape as the levy counter that
  incremented and changed nothing. If a new Bloom response adds an effect, find
  the place that consumes it before believing it works.
- **Studying a mass and burning it are exclusive on the same mass.** Study
  yields xenolith and readings scaled by how much growth is present and feeds
  it a little; burning removes the thing you would have studied. That conflict
  is the setting's central tension and `STUDY_FLOOR` is what keeps a burnt-out
  system from paying twice.
- **A public function nobody calls is a feature that does not exist.**
  `test_reachable.py` walks the tree and fails on any public module-level
  function called from nowhere at all. Be clear about its limit: it will not
  catch one that is called only from a readout or only by the suite. The
  Bloom's growth multiplier was consumed by `summary()` from the day it was
  written while contributing nothing to the simulation, and this check would
  have passed on it. Reachability is a floor, not a guarantee.
- **`return None` is not a result.** Counting it made the analysis flag every
  early-exit function; the self-check caught that on its first run, which is
  the argument for the self-check existing.
- **A feature is not finished until a lever in `tests/levers.py` proves it
  moves the world.** Reachability only shows a function is called;
  `test_efficacy.py` switches each claimed effect off and demands the same
  seeded scenario come out different. Disconnect the Bloom growth multiplier
  and reachability still reports "every one reachable" while efficacy fails.
- **Levers patch a module attribute, not an imported name.** The codebase calls
  across modules as `module.function(...)`, so the lookup happens at call time
  and every caller sees the substitution. A lever aimed at something imported
  by name would silently do nothing, so the suite checks each substitution
  actually changes its measurement before trusting the comparison.
- **Watch for a probe that saturates or starts already satisfied.** The first
  Bloom lever ran long enough for every system to pin at its 1.0 ceiling, so a
  Bloom growing half again as fast reached exactly the same total; the first
  research lever stocked the bench full in *both* runs. Both read as inert
  features when the features were fine.
- **A crossing charges as it goes, not up front.** `transit.begin()` takes
  nothing; each watch spends its share. That is what makes cutting the burn a
  real decision — you keep what you have not yet spent and lose what you have.
- **`intel.sees_bloom` is the one door for what the chart may show about a
  star's infestation.** The sector chart has a careful knowledge system —
  `intel.level` ranks 0..3 and the marker and port ring both respect it — and
  the Bloom was exempt from all of it: a red halo sized by `system.bloom` on
  every star however unknown, and a side panel printing "Bloom mass: 77%" one
  line above "Knowledge: name only". It also quietly undid the picket, whose
  `watch` effect exists to report what happens where you are not. You see a
  system's Bloom if you have been there, can see it from where you stand,
  watch it, or hold a colony in it. **A registry entry is not eyes.**
- **The aggregate stays public.** Holdings still reports how many systems
  carry growth and what share of the sector by mass, so scouting is a cost
  rather than a wall: how bad is published, where is earned.
- **`Docking.shown` is the instrument; `d.error` is the truth, and screens
  never touch it.** The readout was rolled fresh inside `reading()` on every
  call, and the panel called it from `game.rng("readout")` — which advances
  the save's seed — so an untouched axis read −44, −49, −42, −47, −49 in five
  consecutive paints. The panel then took its *colour* from `d.error` while
  printing the blur, and every button's forecast quoted `d.error` outright.
  The reading is taken once per pass now and the panel, the colours and
  `forecast` all use it. **If you add a docking readout, read `shown`.**
- **`NOISE_CEILING` must stay above `TOLERANCE` or the sensor rating is
  inert.** It was 5 against a tolerance of 6, so nulling the reading put you
  inside tolerance whatever your instruments: flying on the instrument alone,
  every noise from 0 to 5 docked 100% of the time in 3.2–3.5 passes. At 9 a
  bare hull (sensor 2) reads ±7 and pays about a pass; a well-found one reads
  ±3 and does not.
- **`CREW_CHOICES` holds station ids, and `make_officer` refuses one it does
  not know.** Two of the six used to be *stat* names — "engineering" and
  "medicine" against the roles "engineer" and "medic" — and `make_officer`
  answered an unrecognised id by picking a role at random. Nothing exercised
  it, because no screen ever set `Choices.crew`; the moment the opening grew
  a bridge picker, choosing the engineer would have seated somebody else.
  `role_id=None` still means "anybody"; a name is now either known or an
  error.
- **`CREW_SLOTS` is the opening complement, not a ceiling.** The berths board
  is explicit that in play "you may keep as many as you can pay", and six
  roles exist to be filled — so `can_hire` deliberately does not consult it.
  `beginning.apply` trims to it, which is what makes a dry stack sail with
  two, as its card has always said.
- **Every gate must agree with the act it guards, and the act should call the
  gate.** The sim has seventeen `can_*`/`is_*` functions; a screen asks the
  gate whether to offer a button and the act asks its own conditions when the
  button is pressed. Two real bugs came from that gap before it was asked on
  purpose (`is_stranded` against `extract`, `quote` against `check`), and
  `test_gates` found a third: `crew.hire` refused a station that was already
  crewed and the berths board did not know — **49% of candidates over sixty
  ports could not be signed**, every one under a live button.
- **An agreement check cannot guard a shared gate, and must not pretend to.**
  Once `hire` calls `can_hire` and `start_build` calls `can_build_here`,
  changing the gate moves both answers together and they agree all the way
  down — which is the architecture you want. The *rule* then needs a separate
  check measured by outcome. Making `can_build_here` answer yes everywhere
  passed every check in the project until one was written for it.
- **`contracts.CARGO_KINDS` is the one list of kinds completed by carrying
  something.** It was written out three times — in `quote`, in `shape`, and
  again in `test_cargo` — and all three said `("deliver", "prospect")` while
  `check` completed a `relic` in the *same branch* as a prospect. So relic was
  the one cargo contract neither priced on the board nor floored against what
  its goods cost: measured over 271 of them, median net **−402** and **62%
  losing money**, against 0% for the two that were covered. A check that
  shares the code's whitelist can only confirm what the code already assumed —
  `test_cargo` derives the set by playing now, handing each kind its
  completion state with an empty hold and then a full one.
- **A ground option's prize depends on who you send, and the card must say
  so.** `attempt` multiplies a success by `1 + margin * MARGIN_BONUS`, but
  `odds_for` quoted the bare `REWARD_SCALE` band — so the card read the same
  at every officer level while the payout did not. Measured on "Cut a sample",
  800 attempts a level: quoted 8–26 ore throughout, paid up to 32.2 green and
  47.8 at level five, with 28 of 42 option-and-level pairs over their ceiling.
  Skill moved the odds on screen and the prize in secret. The quote is
  conditioned on the officer now — the smallest and largest margin they can
  roll on a success, carried through — so a seam reads 8–32 green and 9–45 at
  level four. **The tuning constants live in `data/expedition.py`**; a bare
  0.12 inside `attempt` is what made the forecast unable to quote it.
- **A dead aggregate is where a dead effect hides.** `test_grants` asks the
  general question — is every effect a colony grants read by something? — and
  two slipped past it anyway. `colony.effects()` copied `watch` into a
  `watch_systems` set and `fabricate` into a `has_fabricator` flag that **no
  other line in the game ever opened**, and the check counted those copies as
  consumers. A mention inside a function whose own output nobody reads is not
  a consumer. The check excludes the aggregator's body now, and follows one
  hop through it (`vault` reaches `state.py` via `has_vault`, and must still
  pass). A second check holds the aggregate itself to publishing only keys
  something opens — it was carrying six dead ones, including a `research`
  that was always 0.0 while two callers added it to the bench rate.
- **`colony.watching()` and `colony.fabricating()` are direct queries**, not
  aggregate lookups. A picket gates whether you hear about unlicensed growth
  in a system you are not in — the sector used to report every infestation
  anywhere, which is exactly why the effect bought nothing. A fabricator takes
  `FABRICATED_OFF` off the *credits* of fabricated fittings built or refitted
  in its system; the metal is charged either way, and grown fittings are
  untouched. `cost_of` and `refit_cost` both take the flag, and `yard_view`
  passes it so the screen quotes what the yard charges.
- **A port reverts to `Stock.base`, not to 1.0.** `make_market` builds real
  economic geography — an ore-rich system's port gets up to 1.75x supply, a
  faction's exports 1.55x, what it is short of 0.62x — and `tick_market` used
  to drag every commodity at every port toward
  `1 + volatility * trend * 12`, a number with nothing to do with the port.
  The geography was gone inside a year: the spread in ore supply across ports
  fell 0.431 → 0.117, and from year one **the best arbitrage in the entire
  sector was zero or negative on every commodity, for ever**. The module
  docstring had always said "its own equilibrium"; the arithmetic said 1.0.
  `base` defaults to 0 and is adopted from current supply on first tick, so
  saves written before it keep their character instead of being flattened.
- **A 4-sample threshold is not a check.** `test_politics`' Concord broker ran
  four seeds and demanded three. Measured over seventy-two games the true rate
  is 56–68%, so that assertion had about an even chance of failing on any
  given day and had been passing on luck. It went red for an economy change
  that a fixed-length control proved had no political effect at all — same 322
  ventures, standing and relations within noise — and the apparent
  53%-against-75% gap vanished (21/36 against 22/36) on a fresh range of
  seeds. Twenty games and a floor at 35% now. **When a check on a stochastic
  outcome fails, measure the rate on a fresh seed range before believing it.**
- **`is_stranded` must ask whoever grants each way out, not guess.** It is
  the gate on `distress_call`, the game's only answer to being out of fuel and
  money at once, and it carried two guesses. The ice test read
  `resources["volatiles"] > 0.05` — how *rich* a body is — while whether a rig
  will go on it is `mining.worked_out`, which reads how much has been *taken*.
  Different quantities, so a rich body worked to exhaustion counted as fuel
  for ever: a captain at Amber Anchorage, a one-body system, with 0 credits
  and 2.3 tonnes, was refused a tow with "you can still move". The port test
  fell back to `or 40` when `buy_price` returned None, which is exactly what
  it returns when the shelf is empty. **If you add a fourth way out, ask its
  owner.**
- **A fresh sector is not the state the bug lives in.** No port in 417 is out
  of reaction mass at generation, which is why the empty-shelf branch went
  unseen for so long. Played sectors get there. Construct the state.
- **`captain_bot` is the deadlock check and it has to reach the end.** Its own
  docstring says a stall means a hole a player would fall into, and nothing
  was asserting it ran its full five years — two of six stopped short, one on
  day 1406 of 1825, while the solvency check beside it passed on the *mean*
  treasury of all six.
- **An NPC's magazine is sized to its own mounts, not to salvage.**
  `make_enemy` gave every hull a flat 4–20 t of ore, alloy and biomass —
  stores meant for the wreck — and those were quietly doubling as ammunition
  nobody had sized against a fight. Measured: a mean of 12 rounds against a
  31-turn fight, dry on turn 11, **unarmed for 63% of every engagement**, and
  the player taking no damage at all in 13 of 20 fights. `ROUNDS_MIN/MAX`
  stock each ammo-hungry mount separately now.
- **A warship needs a gun that can hurt you, not just a gun.**
  `_weapon_pool` raised the tier until *some* weapon existed, and for a
  fabricated hull the first to appear is the point-defence cannon — so **40%
  of NPC hulls arrived armed with nothing but flak**, Concordat warships at
  difficulty two included. `MAIN_GUN_DAMAGE` (12, against a median mount of
  30) is the bar. Specialists are still fitted alongside a battery, which is
  what they are for.
- **The difficulty curve was a cliff, and `_rack` is what gave it a bottom.**
  Scales 0.5, 1 and 2 all came out at 8–16 points of throw because every one
  of them carried flak, and scale 3 jumped to 85. Requiring a main gun fixed
  the flat bottom and created a new fault in its place: a fabricated hull's
  first main gun is tier three, and tier three holds the breach torpedo, so a
  light patrol drew from a battleship's rack. `_rack` widens the pool with
  difficulty. Now 27 · 28 · 45 · 88.
- **The seats run engineering first, then the helm, then the guns.** That
  order is load-bearing, not incidental. Engineering is what sets
  `side.route`, and its two consumers sit either side of it: the guns read it
  when they fire (after both seats) and the helm reads it while steering. With
  the helm running first, `route_guns` landed on the turn it was given and
  `route_engines` landed a turn late — ordering "power to the drive" left the
  ship at a dead stop, and it leapt to 74.9 on the following turn, the turn
  the captain had ordered *hold station*. If you add a seat, put whatever
  allocates a resource before whatever spends it.
- **The best seat depends on the hull, and that is working as intended.**
  Measured over 40 engagements apiece: a beam-armed navis leaves the enemy at
  46% hull with the captain at the helm and 92% with the captain at the guns;
  a heavy bastion reverses it, 66% at the helm against 30% at the guns.
  Taking the gunnery seat costs you the helm, which repeats its last order at
  seven-tenths turn rate — for a ship that has to keep its beam on, that costs
  more than the accuracy is worth. Do not "fix" this.
- **`offer_gain` is the only thing that decides what an overture buys.**
  `preview` and `perform` each carried their own copy of
  `action.gain * (1 + diplomacy)`, which is the arrangement that produced a
  free treaty, an ungranted favour and a phantom haggle payment in this same
  file. One function now, and `test_courtship` greps the source to keep it
  that way — `.gain` may appear exactly once in `sim/diplomacy.py`.
- **Goodwill is cheapest from people who barely know you.** `courtship()`
  tapers an overture's worth above 25 standing, squared, to a floor of 0.30.
  Without it nothing in diplomacy had a diminishing return at all: the same
  forty tonnes moved a power at 95 exactly as far as one at 0, and the
  Concord — the sector's whole political condition — arrived on day 855 for a
  captain who never left port. It is 3.2 years now, and the powers finish
  sitting *at* Kin (70–73) rather than pinned at 100.
  **The floor must not go below about 0.30.** Standing erodes on its own — the
  churn takes a power at 90 down to 83 inside two years — so an ally has to
  stay worth courting. At 0.08 and 0.15 the determined broker in
  `test_politics` reached the Concord in only two games of four: an ending
  made unreachable is a worse fault than one made too cheap.
- **A penalty is a share of the gain, never a flat amount.**
  `allegiance.price` had `max(1.0, ...)` under it — invisible while every act
  was worth five or more, and a trap the moment `courtship` made a gift worth
  0.88: the floored penalty of 1.0 with each of two rivals turned relief at
  high standing into a button that cost forty tonnes to leave you 1.12 worse
  off. The floor also flattened the severity ramp this module exists to
  create. Keep costs strictly proportional to `weight`.
- **A movement of "−0" is a rounding artefact, not a number.** Courtship made
  the small end of the standing range real, and a penalty of a tenth of a
  point formatted as "−0 standing" — which reads as nothing and looks like a
  bug. `diplomacy_view.standing_figure` decides it; note that
  `abs(delta) < 0.5` is *not* the right test, because Python rounds a half to
  even and exactly −0.5 formats as "−0" too. Ask what it rounds to.
- **The hull regrows and the calendar does not.** About 2.3 a day when badly
  hurt, and faster near full. So *hull damage is a cheap cost and days are an
  expensive one*, and an option that charges both can cancel itself out:
  `contact/hold` was first retuned to ten off the hull plus two days, and the
  two days healed the ten exactly. Never price a watch option — or judge one —
  on declared damage alone; `test_watches.py` measures what is still missing
  after the option's own days have passed.
- **Every watch option must be a trade nobody can dismiss.** `data/watches.py`
  states the rule in its own docstring — "there is no option that is simply
  best" — and four options broke it. The check is *domination*: does any
  option cost no more on every axis and pay at least as much? That single
  question found all four, across two watches, and it catches four of the five
  regressions in the mutation sweep. Testing the options that worked would
  have found none of them.
- **A declared risk has to cost something when it fires.** `contact/hold`
  carried the largest risk in the table, 45%, and `risk_damage=0`: it printed
  "They were not nobody." and nothing happened. `risk_days` exists because a
  risk could previously only cost hull, and being stopped and searched costs
  time — without it the option could not be priced at all.
- **The price register holds price quotes and nothing else.** Chart completion
  dates used to be stashed in `game.register` beside them, and
  `market.best_markets` walks every value in it and reads `.sell` — so charting
  anything and then opening a port raised `AttributeError` inside a Qt slot,
  where Qt swallows it and the panel simply fails to draw. Chart dates live in
  `game.charts_made` now, with a migration for old saves. Found by rendering
  the screens for the README, which is a kind of play the suite was not doing.
- **A watch option states what going wrong costs, not just its odds.** The
  panel rendered "Might go wrong: 30%" and stopped, so holding through debris
  (30% of thirty off the hull) and running a bad slug (35% of twenty-four)
  read as the same gamble. `risk_text` and `risk_damage` existed in the data
  and were read by `sim/transit.py` alone — the screen referenced neither.
- **A ground option states its odds, its prize and its risk.** The screen
  listed "(science, difficulty 3)" and nothing else. Resolution is
  `1d6 + officer level >= difficulty + 2`, so that same string is a
  one-in-three with a green officer and five-in-six with a level-three one; the
  reward was unpacked into a discarded variable; and a failure springs a hazard
  40% of the time, unstated. `expedition.odds_for()` gives all four, and the
  ground game is nothing but a sequence of these choices.
- **The seed dialog says what will grow.** It showed each class's cost and
  gestation and never its yield — the one thing that separates them. Measured
  on one rocky body: fourteen classes from 2.6 t of ore a day (RADIX Mine,
  12,000) to 260 credits a day (Free Port, 74,000) to 4.2 research a day
  (Reactivated Array, 96,000), and three that yield nothing and buy effects
  instead. `colony.forecast()` gives yield, upkeep, effects and a rough
  payback, and the card shows them.
- **A colony forecast prices at a flat table, not at a market.** A payback that
  swings with whichever port you are standing in is not something a player can
  compare classes with.
- **A seat says what taking it is worth, not just who is holding it.** The
  orders panel printed each station's officer level and never the consequence.
  Measured from the sim: gunnery is +0.22 to hit with a green officer and +0.10
  with a veteran; an unattended helm repeats its last order at 0.7 + 0.06 a nav
  level of the turn rate; an unattended engineering section sheds a fraction of
  its vent and can do nothing else. `stations.seat_value()` states each, so who
  you have decides where you should be sitting.
- **An overture says what it buys, not only what it costs.** The diplomacy
  screen listed a name, a blurb and a price and never a benefit: tribute at
  12,000 credits for +9 standing read the same as relief at 40 t of biomass
  for +11, which is about six times better per credit. `dip.preview()` is a
  pure function returning what will move — the target, third parties, and the
  relations matrix — and the screen draws it.
- **A treaty's cost with the signatory's enemies is now stated.** It charges
  standing through `allegiance` and said so nowhere: you signed, and two other
  powers thought less of you for a reason the game never mentioned. In a sector
  at war that is six points with each of the other three.
- **Nothing is gated behind a technology that does not exist.** "Build a
  xenology annex" — 100 days, 11,000 credits, +0.5 research a day and +0.04
  diplomacy — was gated on `tech="xenolinguistics"`, which is in neither the
  research tree nor the xenotechnologies. It was buildable by 0 of 19 colony
  classes with everything in the game unlocked. One entry in the whole content
  set was wrong; `test_works.py` now checks all 131 gated entries across works,
  colonies, parts and chassis, plus every tech prerequisite.
- **A test fixture was part of why it hid.** `test_verbs` appended the phantom
  id to `research.unlocked`, so the sweep that clicks every control saw a work
  no real chronicle could reach. A fixture that invents content is a fixture
  that stops the suite noticing content is missing.
- **What the bench says a programme will eat is what it eats.** `needs()` is
  documented as the end-to-end total and the screen prints it as "26 wanted";
  `draw()` then spent `total / 60` a day while a careful programme runs about
  128 days, so the bench ate 2.1x the advertised figure on every track. The
  sixty was a duration nobody had checked. The draw is paced over
  `span_of()` — the programme's real expected length at the current rate — so
  the two agree.
- **A quote is priced for the approach in hand.** Running parallel tracks costs
  "three benches' worth of material" by its own blurb, and the readout quoted
  the careful number. `needs()` takes the `Research` and applies the approach's
  draw, so the shelves are read against what this programme will actually take.
- **The four burn profiles are a decision because a hard burn arrives hot.**
  Measured: a system flown end to end took 55 days coasting and 10 on hard
  burns, and the hard burn cost about three hundred credits of reaction mass
  and 1.2% of a hull that heals itself. Nobody would ever have coasted — and
  its own blurb promised the radiators would complain. A burn now leaves heat
  in the hull (62% of cap on a hard burn), a hot hull is riskier to burn again
  in, and over the cap the radiators stop keeping up and the hull cooks. One
  hard burn from cold is free; a habit of them costs 11% of the hull.
- **Heat is no longer a one-way ratchet.** Nothing outside combat added it and
  nothing shed it, so a ship sat at thirty for twelve hundred days with vents
  rated at twenty-four a turn. `ship.cool()` runs on the clock. `REST_VENT` is
  not a physical ratio — it is the rate that makes heat a state you fly in
  rather than one that has gone by the time you arrive.
- **A rig stops when the hold is full.** `extract()` used to compute the whole
  spell's haul, take `min(raised, cargo_free)` and deplete the body for the
  full duration anyway. Measured: sixty days with an empty hold took 106.2 t
  and worked the body out by 0.384; with the hold 97% full it took 10.2 t and
  worked it out by the *identical* 0.384. Ninety-six tonnes raised and thrown
  away, a third of the body spent, and nothing said so. The working now ends
  when there is nowhere to put what it raises, and time and depletion both
  follow what was actually lifted.
- **A full hold must not be a stranding.** Refusing to work a body with
  nowhere to put the ore is right, and on its own it deadlocks: no room to mine
  ice for reaction mass, no mass to jump on, and the only way to dump anything
  was the contraband panel, which appears solely when carrying contraband at a
  hostile port. `trade.jettison()` is general now and the hold has a vent
  control. The project already holds that an empty tank must not be a deadlock;
  this is the same rule from the other side.
- **Everything that can refuse a working is checked before the ship flies out
  to it.** `flight.ensure_at()` came first, so a refusal cost twelve days of
  flying and gave nothing back. The regression check caught that, not me.
- **The panel forecasts the spell.** It quoted tonnes a day and offered "Work
  it — 30 days" with no notion of what that came to; now it says "25 t in 14
  days — the hold fills first".
- **The freight desk is an information tool with a floor under it.** Within a
  starting jump only 5% of lane/goods pairs show a positive spread, and the
  runs that do exist are invisible — finding one means visiting every
  neighbour first. The desk draws on two honest sources: your own register
  (real prices, going stale) and the harbourmaster, who names his own power's
  ports and what they are short of but will not quote their board.
- **A spread thinner than the drift is not a trade.** `tick_market` moves
  supply about 1.8% a day plus a random walk, so a thin margin is gone by the
  time the hull arrives. Flown and banded by spread, every band below a fifth
  loses money on average, so `MIN_SPREAD` is 0.20 and the desk will not
  recommend anything under it. Measured over two-year careers: 981 credits on
  your own notes, 33,069 following the desk.
- **What a run clears is the voyage, not the spread.** Ranking by margin per
  tonne is how a captain flies a four-credit spread nine light-years and pays
  for the reaction mass themselves.
- **Short-range legal arbitrage is thin by design and that is fine.** Ports of
  one power want the same things, so trading means crossing into somebody
  else's space. The contract board is the early game — every one of twelve
  openings has affordable work — and the desk comes into its own with range and
  a register.
- **A cargo contract is priced against what its cargo costs.** The reward was
  `amount * (base * 0.55 + rate * 0.4)`, and `base * 0.55` is the *floor* — what
  a market holding none of a good pays for it. Nobody sells at the floor, so the
  board priced its own work against a number that does not exist: 44% of cargo
  contracts paid less than sourcing their cargo, worst case fifty thousand
  credits down. `cargo_cost()` prices it properly and the board shows the
  arithmetic, because a fee on its own made a trap look like a living.
- **Distance pays haulage on cargo, not a share of the goods.** The old
  multiplicative premium turned an eighty-tonne silicon run into 130,000 clear.
  Freight is priced by mass and distance — a tonne is a tonne in the hold.
- **A quote prices for the captain reading it; generation prices neutrally.** A
  contract's fee cannot depend on the standing of whoever happens to see the
  board, but what *you* will be charged does. Getting that backwards made the
  quote wrong by two per cent, which the check caught.
- **A field note is kept, not printed once.** Recovered lore lived in
  `expedition.lore`, was shown in the report dialog, and went out with the
  expedition object — never on the `Game`, never in the codex, and worth
  nothing, since `REWARD_SCALE["lore"]` was (0, 0). Three feature options
  existed to display a sentence and take it away. Notes now have identity
  (`data/fieldnotes.py`), are filed with the body, system and day they came
  from, and are evidence on an inquiry track, so going down and reading the
  room is worth doing.
- **A note is not cargo.** Stranding costs 60% of the haul; it does not cost
  what somebody already read and remembered. `test_notes.py` pins that.
- **No screen writes the ledger.** Seventeen sites across four view modules
  spent credits and moved standing directly — buying, selling, hiring, paying a
  bonus, repairing, buying a lead, commissioning bench time, scrapping a hull,
  tying up at a quay, and moving contraband off the books. Every one was a rule
  only a mouse could perform. They live in `sim/trade.py`, `sim/services.py`,
  `sim/crew.py`, `sim/shipyard.py`, `sim/customs.py` and `sim/minigames.py` now.
- **`test_layers.py` enforces the one-directional rule instead of stating it.**
  It matches ledger writes structurally — assignment to `.credits`, augmented
  assignment, `game.rep[…] = …`, any call to `adjust_rep` — and carries a
  self-check that plants all three shapes and fails if the matcher misses any,
  because a structural matcher that silently matches nothing would have passed
  on the day the defect was at its worst.
- **What a fight leaves behind belongs to the rules, not the screen.** Salvage,
  loot, cargo off the wreck, bounty progress, seized xenology, instar kills,
  consorts lost, loyalty and every standing change used to live in
  `ui/battle_view.py._finish()`; `sim/combat.py` held a loot dict and nothing
  else. Nothing headless could resolve an engagement, so every balance run that
  fought a battle collected no loot, no standing and no bounty credit. It is
  `sim/aftermath.resolve()` now, and the view reads what it returns.
- **`Battle.settled` makes the payout idempotent.** Both the screen and a
  headless driver can reach the end of a fight; neither may collect the salvage
  twice.
- **A kill is noted by everyone who dislikes the victim.** Destroying a hull
  moved its owner and nobody else, in a sector whose whole politics is a
  relations matrix. It now pays the owner's rivals a share scaled by the same
  severity ramp `sim/allegiance.py` uses, so a cordial sector gloats not at all
  and one at war gloats loudly. A Bloom kill pleases all four powers rather
  than the Charter alone, which is what it did — hardcoded, in a screen.
- **A chart is priced on what it says, not on how many bodies it has.**
  `survey_value()` was `460 + 210 * len(bodies)`, so a system with a buried
  Abyssal site and ore worth crossing the sector for fetched what five bare
  rocks fetched. Measured: charting the home system took 53 days and paid
  1,510 — 28 credits a day, against roughly 1,600 for smuggling. The whole
  42-system sector came to 55,014, about one contraband run.
- **The price list is scaled against the rest of the economy, not chosen.** The
  best contract in the game pays about 27,000 and the dearest hull 900,000. A
  first pass put a remarkable system's chart at 92,000 — over three times the
  best contract — which fixed exploration being worthless by making it the
  best-paying thing in the sector. The numbers in `data/charts.py` land a
  median chart near 26,000 and charting near 750 credits a day.
- **Who buys is a decision, because the powers want different things.** The Dry
  Choir pays over the odds for life and anomalies, the Yards for ore and sites,
  the Charter for anything alive or old or growing. Best and worst buyer differ
  by 1.6x on average and the best buyer varies by system, so a chart is
  something you carry to the right quay.
- **Charts go stale.** A survey is dated when it is finished and decays to 45%
  over two years, which makes a survey circuit a living rather than a one-off
  sweep of the sector.
- **Claims and holdings have to be able to collide.** `ventures._claimable()`
  used to exclude any system the player held a colony in, and `can_found()`
  never looked at `system.faction` — so the powers declined to contest your
  ground and you could squat on theirs, and territory was never once disputed.
  Both directions are live now, through `sim/territory.py`.
- **A demand is something you are in the middle of**, so `Demand` is a field on
  the `Game` with an `.over` flag and `window.go()` diverts to it. `test_resume`
  picked it up as the sixth guarded activity with no prompting — which is the
  whole point of writing that check as a rule rather than a list.
- **Every answer to a demand costs something different.** Paying the levy keeps
  the holding and gives up 30% of what it makes; ceding loses it and reads
  best with them; refusing keeps it, costs standing, and means somebody comes
  for it — measured at 12 of 12 defiant holdings seized within eight years. A
  claim that lapses cancels the standoff rather than leaving it hanging.
- **Work for a power is a position, not an errand.** Completing a contract
  charges you standing with everyone that power is at odds with, scaled by how
  bad the rift is (`sim/allegiance.py`). `contracts.py` did not import
  `diplomacy` at all, so you could be the Charter's courier, the Concordat's
  bounty hunter and the Freeholds' prospector in the same week while all three
  were at war, and every one of them thought better of you for it.
- **The penalty is not the point; the escape is.** Severity ramps from zero at
  −15 to full at −70, so brokering a rift *part* of the way down is worth doing.
  Measured: the same 28 jobs return 108 total standing in a hostile sector and
  170 in a brokered one. That is what finally gives the relations matrix a job
  in ordinary play rather than only at the Concord ending.
- **Contraband needs both halves or it is not a trade.** A good that is
  outlawed somewhere has no posted price there and therefore a much better
  unposted one (`customs.premium`), and the same power opens your hold at the
  dock (`customs.inspect`). Shipping only the search would be a tax nobody
  would choose to pay; shipping only the premium is what the game already had,
  and measurement said it beat honest trade outright.
- **Scrutiny is the brake.** Selling into a black market and being cleared both
  raise a per-faction heat that thins what they will pay, thickens the search,
  and decays on the clock. Without it one dock is an unlimited money printer.
  `COOLING` was tuned by playing careers, not chosen: at the first value a run
  put on more heat than a month shed, so every career ended down.
- **Mitigations multiply, they do not subtract.** Standing, a clean approach and
  a concealed hold each take a share off the odds. Subtracting them let a
  fitted-out hull with good standing drive the risk under the floor and stop
  being a smuggler at all.
- **A part that is kit for a trade is marked `civilian`** and NPC loadouts skip
  it. Adding two smuggling parts put them straight into the enemy outfit pool
  and broke the combat-assessment check — a feature about trade silently
  re-tuning every encounter in the game.
- **A dig banks per layer, not at the end.** `dig.work()` credits understanding
  as each stratum comes out, so a trench abandoned after the casing is worth the
  casing. That is the whole reason backfilling is a choice rather than a way of
  throwing the dig away, and it is what `test_dig.py` pins: restoring
  bank-at-the-end passes every other dig check and fails that one alone.
- **Anything you can be in the middle of belongs on the `Game`.** The window
  exposes `transit`, `docking`, `decoding`, `dig` and `decoding_tech` as properties
  over game fields; holding them on the window loses them over a save, which
  docking and decoding did unnoticed for many cycles. `test_resume.py` reads
  the guard in `window.go()`, takes every activity with an `.over` flag, and
  fails on any that is not a field on the `Game`.
- **A `Battle` stays on the window on purpose**, recorded in `battle_state` and
  in `TRANSIENT` in `test_resume.py`: combat resolves in one sitting and no
  clock runs during it. Anything else added to that allowlist needs its reason
  written down beside it.
- **Colony effects are a closed vocabulary.** `test_sim.py` asserts that every
  key in a `ColonyClass.effects` is one the game actually reads, so a typo in a
  station definition fails the suite instead of silently doing nothing.

## Tests

`python -m seedfall.tests` — no dependencies beyond PyQt6 itself.

- **`test_sim.py`** drives the rules headlessly: sector generation and
  determinism, every chassis and part, tech-tree reachability, trade, colonies,
  building, combat outcome distributions, Bloom pacing, save round-trip.
- **`test_combat.py`** covers arcs and crew stations, and holds the consorts to
  the bargain their orders describe: screening must measurably pull fire off
  the flag, and flankers must shoot markedly more than screens do.
- **`test_empire.py`** plants a colony, matures it and develops it: that a
  finished work changes production, that its effects reach ward, build sites
  and sensors, that material is charged up front, and that works survive a
  save.
- **`test_crew.py`** checks that the same act pulls a bridge apart rather than
  together, that loyalty is felt at the crew stations and not only on a roster,
  and that a year of missed payroll actually costs you officers.
- **`test_missions.py`** runs a commission to its end, and checks the three
  things that make one different from a posting: that stages escalate, that
  taking one is refused at its rival's own port, and that a missed deadline
  withdraws it permanently.
- **`test_explore.py`** climbs the intel ladder rung by rung, checks a chart
  cannot be bought twice or a survey sold twice, and — the important one —
  proves that thirty passes over the rumour desk leave the galaxy byte for byte
  unchanged.
- **`test_mining.py`** measures the four methods against each other over
  twenty runs apiece and asserts they are actually different bargains — a bore
  must out-yield an open cut by a third and cost more hull and more of the body
  doing it — then works a body out and checks it stops paying.
- **`test_research.py`** measures a captain who surveys against one who does
  not — the second must reach the first technology in well under three quarters
  the time, or the evidence model is decoration — and checks that a captain who
  picks a project on turn one and does nothing else still gets there.
- **`test_trade.py`** puts a shock on a market, checks the price moves, then
  expires it and checks the price comes back — the failure mode being a sector
  that accumulates permanent distortions over a long game. It also formats
  every shock's text to catch an unfilled field, which would otherwise crash a
  port screen months into somebody's game.
- **`test_ground.py`** pins a party under a gale and shelters until the
  expedition ends, which is the check that a stuck state cannot exist. It also
  measures tiles crossed with and without weather, so a condition that costs
  nothing fails.
- **`test_politics.py`** checks that a determined broker can still reach the
  Concord against twenty-five years of background churn, and — because the
  emergent numbers plateau against the -100 floor either way and make a weak
  signal — tests the fading mechanism directly by pushing a relation down and
  watching it come back.
- **`test_design.py`** builds every chassis at a sensible fit and fails if any
  is penalised for it, then maxes one out and fails if it is not. It also
  checks that a fully laden starting hull can still reach its nearest
  neighbour.
- **`test_orders.py`** builds ten game states and demands every standing order
  fire in at least one of them, calls every predicate unguarded so a broken one
  cannot hide behind the panel's exception guard, and checks that acting on an
  order makes it go quiet.
- **`test_assessment.py`** plays out forty fights across two hulls and four
  difficulties and fails if a worse-sounding verdict wins more often than a
  better-sounding one — the read is worth nothing if it is not honest. It fails
  against the raw-hull comparison the first draft used.
- **`test_balance.py`** plays out every assertion it makes. It checks no
  faction fields an unarmed warship, that heavier threats arrive in heavier
  hulls, that the win rate falls with difficulty and rises with a better ship,
  that waiting is not a way to beat a battleship, and that fleeing and hailing
  both actually run — the last because splitting them into `parley.py` left
  them calling names that no longer existed and nothing drove either path.
- **`test_parley.py`** checks a *probabilistic* forecast the only honest way:
  state the chance the panel shows, then hail four hundred times and count. 22%
  said / 19% run, 45/45, 60/64 — inside three sigma at each standing. The odds
  were nowhere before this: "Hail them" was a hidden one-shot whose losing side
  is the enemy taking a free turn, on the same panel where
  `stations.order_preview` prints a line per helm order. **And the hail never
  asked what the power remembered** — `b.rep` is the standing on the books,
  `grudge.feeling` is the memory behind it, which the game already spends on
  prices, favours and whether work is posted. A Charter that remembers a
  destroyed hull sits at -88, which takes a hail from 22% to 4%; one that
  remembers a rescue lifts it to 28%. `parley.odds`/`escape_odds` are the one
  door and return the named terms, so the panel reads "42% they stand down —
  your standing with them +17 · you have the upper hand +13 · what they remember
  of you -7. Refused, they fire anyway."
- **`test_verbs.py`** clicks every enabled control in the game — 210 of them
  across the standing screens, an engagement, an expedition, all four port
  tabs and both mini-games — each on a fresh game, and again with a wrecked
  hull that has no money, no crew and no air. It fails against last cycle's
  parley regression, which is what it was written for.
- **`test_bloom_arc.py`** provokes the Bloom until every response has fired,
  checks they fire in order and never twice, and — the one that matters —
  measures actual spread with and without them, because a multiplier nothing
  reads looks exactly like one that works.
- **`test_reachable.py`** found the three things this cycle fixed: treaties
  that bought no trade advantage, instars that could not be killed, and
  officers whose convictions never felt your standing move. It carries a
  self-check, because an analysis that cannot fail is worse than none.
- **`test_efficacy.py`** carries two checks on itself: that a deliberately
  decorative feature fails, and that every lever's substitution bites. A
  harness that cannot fail is worse than none.
- **`test_transit.py`** flies the same crossings under a hurried policy and a
  careful one and fails unless hurrying genuinely saves days and genuinely
  costs hull. An option that is best on every axis is not a decision.
- **`test_notes.py`** drives a party into a wreck, works it for notes, brings
  them home, and fails unless the shelf, the provenance and the evidence all
  survive — including across a save. It also checks every note is reachable and
  that the draw prefers ones you lack, so no written discovery is unfindable.
- **`test_attempts.py`** rolls each option six hundred times and fails unless
  the empirical success rate matches the quoted chance — the resolution lives
  in `attempt` and the quote in `odds_for`, and the point is that they cannot
  drift. Dropping the `+2` from the quote makes it report "said 67% rolled
  32%".
- **`test_tutorial.py`** exists because the failure mode of a tutorial is
  silent: a step that advances when Next is pressed teaches nobody anything and
  will march a confused player through eight screens of congratulation. Every
  lesson names a watcher, every watcher is a function of game state compared
  against a mark taken when the lesson opened, and the checks walk the whole
  thing by *doing* each action — then separately prove that three hundred days
  of doing nothing leaves it on lesson one. Replacing the watcher with "trust
  the player" fails three of them.
- **`test_manual.py`** enforces two things that screens usually escape. A
  manual that says "thirty-five hulls" is wrong the day somebody adds one and
  nothing would notice, so every countable claim is generated from the table it
  describes and a check fails if a topic names a fact nothing can resolve. And
  an option that changes nothing is a lie: every setting the screen offers must
  appear somewhere in the package outside `options.py`, so a setting that stops
  being read fails here rather than sitting on screen doing nothing. It also
  found the key collision below.
- **`test_bridge.py`** drives the whole protocol in-process, because verbs are
  plain functions over a `Game` and a socket is a detail. One check does open a
  real loopback connection, because the thing that broke only breaks over one:
  `survey` returns a `Lifeform` among its results, the reply was merged into
  the envelope, and `json.dumps` raised *inside the connection thread* — the
  socket died silently and the caller was left reading an empty line. A
  boundary has to be total; a caller on a pipe can catch neither a traceback
  nor a hang-up.
- **`test_gunnery.py`** exists because combat had one outcome. `_fire` floors
  damage at `max(dmg * 0.15, dmg - armour)` so that something always gets
  through, and `_apply_to_layers` then discarded anything at or below half a
  point — which swallowed the floor whole for the only weapon a new captain
  owns. Measured: 360 engagements, 100% driven-off, both hulls at 100%. The
  read panel had been reporting the correct 0.45 a turn the whole time, which
  is how one rule with two implementations hides.
- **`test_reach.py`'s "a pocket is a long project and not a trap"** is the
  check carrying a design decision. Generation was *not* changed to close the
  gaps, because playing a two-system pocket showed evidence still accumulates,
  both its markets sell magnetite, and it earned 71,000 of the 78,000 credits
  in under seven years. The wall is a gate, not a lock — so the fix was making
  the gate legible rather than removing it. If a future change makes a pocket
  genuinely unsupplyable, that check fails and the decision gets revisited.
- **`test_grudges.py`** holds memory to *changing behaviour* rather than
  colouring speech: a quay prices you by what it remembers, a power that holds
  enough against you stops posting work, and feeling travels between powers
  close on the relations matrix. The rule underneath is that `because()` must
  name the memories responsible for whatever `feeling()` returns — nothing in
  this game may dislike you for a reason it cannot state. Making the price bias
  and the cold shoulder inert fails two checks here and one efficacy lever.
- **`test_voices.py`** exists to prove the language model is optional in the
  way it claims to be. `llm.complete` is replaced with something that raises,
  so a check that reaches for a model fails loudly, and what is measured is the
  written fallback: eight personas across seven moods, all distinct, none
  leaking a frame slot. The suite stays hermetic and the game stays whole with
  nothing installed.
- **`test_legacy.py`** covers the ten endings and the epoch each one opens.
  Its sharpest check performs all 120 answers across the forty situations and
  compares each against the effect its card printed — the card and
  `legacy.apply` read the same dict, and this is what keeps them one dict. It
  caught the Cartel ending being unreachable by construction: the threshold
  asked for prices from 25 systems and a sector has only 17 to 24 markets.
- **`test_beginnings.py`** pins the invariant the whole suite rests on: a
  `new_game()` with no choices must be *exactly* the game as it shipped, because
  three hundred and eighty checks are written against that opening and a default
  that quietly differed would leave all of them passing while measuring a
  different game. It also found a live soft-lock — see below.
- **`test_plans.py`** holds the ship model to being built out of the actual
  ship, and holds the renderer to the one thing a software rasteriser gets
  wrong silently. A face wound the wrong way is culled when it should be drawn,
  and the symptom is not a crash or a blank screen: the ship renders as a
  handsome x-ray of its own far wall with the cargo floating in front of the
  hull, and roughly half the faces cull either way so the count says nothing.
  Two checks cover it — one on the normals of every primitive, one that puts a
  box inside a sphere and insists the sphere occludes it.
- **`test_courting.py`** holds diplomacy to being a choice. Measured before
  anything was touched, a captain with money sat at 92/100/100/100 with all
  four powers *while two of them were at −67 with each other*: the three gift
  overtures added standing with their target and cost nothing anywhere else,
  so the relations matrix was scenery and `broker` — the one action that moves
  it — bought nothing you could not get by ignoring it. Gifts run through
  `sim/allegiance.py` now, which contracts, treaties and territory already
  used. Measured after: courting one side of an implacable feud reaches 100
  and −100; courting both reaches 69 and 63, neither at Kin. Brokering the
  rift first drops what courting costs elsewhere from 7.8 to 1.0, which is the
  purpose `broker` never had.

  Playing it then found the trap it created. Below −60 standing every overture
  was refused and the only move left was `denounce`, which makes it worse — a
  captain at −100 with unlimited credits courted a power for 120 sessions and
  moved them **not one point**. `tribute` reaches to −100 now, so there is
  always a door and it is the expensive, undignified one: 555 days of steady
  tribute to climb back from the floor.

- **`test_picture.py`** holds the picture of the ship to showing the ship. A
  hull at 25% used to render pixel-for-pixel identically to one fresh out of
  the yard: every reading of the damage was a percentage in a side panel,
  while the model — the one thing always on the screen — said nothing. Damage
  is drawn now as blight spreading over the hull, following the *outermost*
  layer, because that is the one damage lands on first and the one you could
  actually see. The checks measure it end to end rather than by field: two
  renders that differ by pixel count, the same ship twice that does not, and
  neighbour agreement to hold the blight to contiguous patches — the first
  version asked whether a marked face had a marked neighbour, which with half
  the hull marked is true by chance, and scored per-face static at 99%.
  `speckle()` scatters from a stable hash rather than `game.rng()`, because
  drawing happens many times a second and must never advance the save; one
  check exists solely to keep it that way.

- **`test_reach.py`** walks the reachable component with `jump_quote` rather
  than re-deriving it, so the chart and the Set course button cannot drift, and
  fits each drive the chart offers before believing what it claims to open.
- **`test_chronicle.py`** is the one suite that does not build a fresh, narrow
  game. `chronicle.py` flies a single captain for ten years — surveying whole
  systems, refitting, hiring, trading off the freight desk, mining, digging,
  landing parties, planting colonies, running works and moving the relations
  matrix — and the suite repaints every screen and every tab against that save
  as it accumulates, with `sys.excepthook` armed because Qt swallows what a
  slot raises. It exists because the README screenshots found a shipped crash
  in minutes that forty-three suites had missed: the crash needed a *charted*
  sector and a *port screen* in the same save, and nothing put accumulated
  state in front of the screens that read it. The driver carries its own
  history in comments — each measured failure that made it cover less than it
  claimed — and the third check fails if any of those counters reads zero
  again. Tabs are read off the live `TabBar` rather than a hardcoded list, and
  clicked rather than assigned, so a tab added tomorrow is covered tomorrow and
  the refresh runs where the exception would really be swallowed.
- **`test_founding.py`** plants all fourteen classes a body will take, matures
  each, and fails unless the yield, upkeep, effects and gestation are what the
  dialog forecast. Its fixture stocks every commodity rather than a guessed
  list — the first version missed spidroin and died on a class it was not
  testing.
- **`test_seats.py`** drives the claims through `run_helm` and
  `run_engineering` rather than re-deriving their formulas, so changing one and
  not the quoted figure is caught. Its fixture creates a tactical officer
  before setting one's level: the opening crew is a scientist, a navigator and
  an engineer, so promoting "the tactical officer" silently did nothing and the
  check compared a green bridge with itself.
- **`test_overtures.py`** performs every overture and fails unless the standing
  and the matrix move exactly as previewed, and unless previewing moves nothing
  at all. Hiding the treaty's rivals again makes it report "said {charter:
  14}, did {charter: 14, concordat: -1, freeholds: -2.2}".
- **`test_works.py`** builds every work on every colony class that will take
  it and fails unless each changes what its table says it changes, unless every
  work is buildable by somebody, and unless every gate names a real technology.
- **`test_bench.py`** runs programmes to completion on every approach and
  fails unless what was quoted is what came off the shelves. Restoring the
  hardcoded sixty makes it report "the bench takes 2.06x what it advertises".
- **`test_burns.py`** flies a whole system on each profile and fails unless
  burning hard is both faster and materially worse for the hull, and unless a
  single burn from cold costs nothing. It also pins what the helm quotes
  against what the hull actually arrives at.
- **`test_workings.py`** works the same body with an empty hold and a full one
  and fails unless the second costs proportionally less ground. Its
  proportionality check measures the room to leave from the haul the spell
  would actually raise: the first version picked a fill fraction blind and
  passed on a seed where no capping happened at all, which is the vacuous-check
  failure this project has shipped before.
- **`test_freight.py`** flies eight two-year careers with the desk and eight
  without, and fails unless the desk wins and unless the desk-following career
  is profitable at all. It also pins the threshold that made the desk honest
  and the one that nearly made it useless: `COLD` was -8, the floor of Neutral,
  and the Dry Choir *starts* at -10, so a new captain on a Dry Choir quay was
  locked out on day one. Its newest check buys what the desk quotes:
  `voyage` sized a load by hold and purse and never by the stock on the quay, so
  **12 of 15 recommended runs forecast more tonnage than the port held, the worst
  by 2.7×** — a 287-tonne voyage out of a berth holding 59. That was wrong twice,
  because `worth_flying` ranks by `net` and `net` scales with tonnage, so the
  ordering was decided by cargo that did not exist.
- **`test_wharfage.py`** trades at nine quays and checks both sides of every
  deal: what leaves the captain's account arrives in the holder's purse to the
  credit. The rate it charges is read *off the rendered board* and applied to a
  real purchase, because reading `wharfage.rate` would only prove the module
  agrees with itself. It measures what the charge is worth in play — over the
  runs the desk actually recommends the two quays take **11% of what a run
  clears**, 10% loading at an outpost against 12% at a station — and what
  standing is worth: **a factor of four between Kin and Hunted**. A decade of one
  chronicle: 272 deals, 799,533 across the counter, 18,359 in dues, and **41% of
  what the Charter holds by the end came off the captain**.
- **`test_cargo.py`** buys the cargo, flies the delivery and banks the fee,
  and fails unless what the board quoted is what the treasury did. Its haulage
  check measures *net*, not a ratio to cargo value: the first version asserted
  reward/cost < 4 and failed at 11.7x on ore hauled a long way, which is not a
  fault — freight is priced by mass and distance, so the ratio to a cheap
  good's value says nothing.
- **`test_layers.py`** holds both halves of the layer rule: that no module
  under `sim/`, `data/`, `world/` or `core/` imports Qt, and that no module
  under `ui/` writes the ledger. Neither breach the project actually suffered
  was an import going the wrong way — both were rules written upward, which is
  why the Qt check alone was never enough.
- **`test_aftermath.py`** plays
  the same engagement twice — once through `sim/aftermath.resolve()` and once
  through the view's `_finish()` — and fails unless credits, standing and
  research come out identical, so the extraction has to stay faithful and not
  merely tidy. Paying a 250-credit bonus from the screen fails it by name.
- **`test_charts.py`** pins the number that made the cycle worth doing: it
  measures charting in credits per day across six sectors and fails both if it
  drops back toward the 28 it was and if it climbs past 1,500, which would make
  surveying the best-paying thing in the game rather than a living. Restoring
  the flat rate fails four of its eight checks, the last one reporting "35
  credits a day".
- **`test_territory.py`** fails unless the powers will actually annex ground
  you hold, unless all three answers diverge, and unless a levy takes the share
  it says it does. Its helper asserts the holding is still *in* `game.colonies`
  and not merely `online`: a colony can mature and be overgrown inside the same
  `advance_days` call, which handed the first version of these checks a holding
  that had already been eaten.
- **`test_allegiance.py`** holds the order of play in place: serving one power
  exclusively must make you its partisan and nobody else's friend, and a broker
  who makes peace first must still be able to work all four to Kin. It also
  pins the card to the ledger — what the board quotes a job will cost and what
  standing actually moves have to be the same number.
- **`test_customs.py`** flies whole smuggling careers and fails unless the run
  pays, unless committing to it (a concealed hold, standing, a clean approach)
  pays markedly better than a bare hull, and unless hammering one dock stops
  paying. It also pins the shape of the risk: every mitigation stacked must
  still leave you catchable.
- **`test_dig.py`** works sites to the bottom under all three methods and fails
  unless the choice is genuine: care must yield most in total, cutting must be
  fastest and cost hull, and working briskly must beat care *per day* — an
  option nobody would ever pick is not an option. It also names the floor it
  found: `test_reachable.py` matches bare names, so `dig.summary` — written this
  cycle and called by nothing — was masked by other modules' `summary`.
- **`test_resume.py`** saves mid-approach, mid-exchange and mid-crossing and
  demands all three come back identical — including the decoding secret, since
  a code regenerated on load would let a player save, guess, reload and guess
  again.
- **`test_flight.py`** holds the helm to its promises: that a seed grows one
  fixed set of orbits *in every process*, that a transfer aims where a body
  will be rather than where it is, that the intercept solve converges, and that
  no course is plotted through a star.
- **`test_conn.py`** flies every contact in five chronicles to a berth or an
  orbit, and is the check that found the closing-rate fault: before it, none
  of them arrived. It compares the conn's forecast against the burn over 2,272
  cases, plays the chronicle forward to see whether the plot's predictions
  come true, and holds the board and the helm to the same arithmetic. Two
  checks earn their place by what they caught in a mutation sweep: disabling
  the branch that kills velocity *across* the approach passed everything else,
  because `start` always puts the ship dead ahead — so there is now a check
  that arrives off-axis on purpose, and it failed on the first run.
- **`test_public.py`** holds the rule that every public act pays for being
  public. Its general check derives who *ought* to mind from the relations
  matrix rather than from `offended_by` — sharing the code's own list would
  prove nothing. Its first sweep missed three, all holes in the checks: the
  preview-versus-act agreement had been measured at 3,456 comparisons while
  the fix was built and never written down, nothing held the two principals
  exempt from each other, and the Bloom-partisan check was asked of a Bloom
  with no relation to anybody, so it scored zero devotion and dropped out on
  its own. Sweep: 8/8.
- **`test_weave.py`** holds the gate network. Its first sweep missed three
  mutations and all three were the same defect in the *checks*: the standing
  block sat behind `if far.faction:` and silently ran nothing where the far
  end had no owner, and the helper that builds a rich captain always granted
  Weavecraft, so removing the requirement broke nothing. The far end is given
  an owner now, and a separate check asks a captain who has not done the
  reading. Sweep: 11/11.
- **`test_thrusters.py`** holds the propulsion model, and its general claim
  is the one that caught all three faults above: **more thrust is never
  worse.** Each time a hull flew *worse* for a better engine, that check
  named it. A second — "a full hold is felt on the helm" — exists because the
  mutation sweep found nothing holding *mass* as opposed to size: fixing the
  moment of inertia to a constant, and dropping cargo from the reckoning
  entirely, both passed everything else. Sweep: 12/12.
- **`test_berthing.py`** holds what an approach costs: that the tank is the
  ship's, that committing spends it, that the clock hears about it, that a
  berth writes `orbit_body` and a lost approach does not, and that an impact
  is paid for in proportion to the speed. Its mutation sweep is 13/13 — with
  one deliberate exception recorded in `test_helm.py`: changing `QUAY_OFFSET`
  is *not* caught, because the painter and the hit test both read it and move
  together, which is the whole point of having one number. The rule that is
  held is that a world and its quay each select themselves.
- **`test_cameras.py`** holds the screens rather than the flying, and measures
  them in pixels: the nose camera must be full of a target the tail cannot see
  at all, and five repaints of a still ship must give one picture. Asking
  `viewport.project` whether the aft camera can see something in front would
  be asking the code to confirm itself.
- **`test_gunfire.py`** ties the picture of an exchange to the resolver that
  produced it: every point of damage must come from a recorded shot (2,138.9
  recorded against 2,138.9 taken over six chronicles), refusals are recorded
  rather than merely logged, and the plot is differenced against the identical
  frame with the shots removed.
- **`test_connwindow.py`** holds the window against the ship: that "close and
  berth" flies the last kilometres rather than running four hundred ticks
  inside the click, and that a conn notices the hull being flown from the helm
  instead of showing an approach on somewhere it has left.
- **`test_screening.py`** holds the screening trade: that a blow meant for the
  flag is worn by whatever is standing in front, that a screen keeps a station
  it can actually hold, that screening protects the flag *and* costs the
  escorts, that it saturates rather than stacking to invulnerability, and that
  every point diverted is a point some hull took.
- **`test_declared.py`** is the standing guard that nothing in `data/` is
  declared and read by nobody, plus the four revivals it forced. Its allowlist
  carries a reason per entry and fails on stale excuses in both directions.
  Mutation sweep 15/15 on source, after a first pass at 11/17 whose four real
  misses were all the same fault — measuring near the thing rather than the
  thing. Notably the corona was checked in the tables and never in a picture,
  and the tedium floor was checked as `THRESHOLD - 1`, which cannot fail for any
  value of the threshold.
- **`test_programmes.py`** holds the endgame bench: that nothing accrues on a
  finished tree that cannot be spent, that every round costs more than the last,
  that all three doors are live and none dominated, that every point of standing
  and every credit traces to a *consumed* finding, that a programme opens only
  when its branch is done, that the screen says which situation it is in, and
  that findings survive a save.
- **`test_orbits.py`** (9 checks, mutation sweep 17/17) holds the gravity model
  and the orbit ladder: that a
  world's year is its *star's* (645 days at one AU round an M dwarf against 272
  round an A-type), that every height the conn offers can be flown to and the
  ones withheld genuinely cannot, that the height is a trade in both
  directions, that the fuel the helm quotes for leaving an orbit is the fuel
  the transfer spends, and that the panel and the sim never disagree about
  whether this is an orbit. Two checks were added when `apply`'s signature was
  fixed: **every offered height resolves on the tank a hull actually carries**
  (32 approaches, all inside 6,000 ticks, 31 in orbit and one run dry — where one
  used to run 60,000 ticks and never resolve), and **a dry hull is told what it
  has** rather than left ordering refused burns.
- **`test_climbs.py`** flies the *offer* rather than the ladder, on the tank
  `conn.start` finds rather than the unlimited one, and fails unless every rung
  the conn sells can be reached and no climb costs more than its price. It also
  reads the console: a refused rung has to be **visible, priced and dead**, and
  hiding one is a mutation the check catches. Its two constants are measured
  rather than chosen — `QUOTABLE` from the gap between the worst rung whose spend
  ran away (25.7 pulses of authority, nine times its quote) and the best one that
  did not (100.7, 1.4×), and `CLIMB_MARGIN` from the worst real climb in seven
  sectors (2.03× the ideal, at Quill Rise II). Both first drafts were caught by
  this suite: 25 let through a rung that ate a tank, and 1.4 promised a price it
  could not keep.
- **The orbit law's two dead ends are recorded in `sim/autopilot.py`** rather
  than in a task, because both were measured and both are counter-intuitive: a
  purely tangential demand asks for zero radial velocity and so spends its whole
  authority *braking* an orbit's natural breathing, which removes energy and
  drove a hull aground; and demanding circular speed at the current radius pumps
  energy into an eccentric orbit, because the ship lingers near apoapsis where
  that demand says go faster. An apsidal law fixes both and flew an asteroid for
  3.1 t against the shipped law's 1,205 — **and is still not shipped, because on
  a 20 t tank it is no better and it goes aground where the shipped law
  survives.** Task #101's plane change does not exist: `hz/|h|` is 1.000 and the
  plane-change Δv is 0.0 m/s at every arrival.
- **`test_tutorial.py`** gained three: a veteran restarting it from the Help
  screen opens at **step 3 of 8 with 2 already done** and is still taught the
  five the chronicle cannot vouch for, only those four lessons carry a
  `skip_if` (the chronicle keeps *state*, and "was cargo ever sold" is
  *history*), and a window can be built around a tutorial that is already
  running — which used to raise
  A fourth brackets the settling-in month from both sides — a captain a week in
  is assumed nothing, one six weeks in has their survey counted — because zeroing
  and halving `SETTLED_IN_DAYS` were caught and **doubling was caught by
  nothing**: the veteran check stands at day 700, so a two-month gate passed
  while a captain a season in was still sent to survey another body.
- **`test_settlement.py`** runs a sector for five years and watches it fill:
  **4 → 13 → 23 → 40 → 59 settlements** across 21 systems and all four workable
  goods, the ground deciding what each one works, the worked good cheaper where it
  is worked than where it is not (ore 32 against 43, phosphate 310 against 362), a
  settled system hungrier for everything it does not make, `Stock.works` composing
  a licence on top of a settlement rather than overwriting it, and a settlement
  costing its founder before it pays.
- **`test_biology.py`** measures the metabolism pairing by surveying rather than
  by reading the table: every biochemistry has its own explaining node and no node
  explains two, a specimen is worth 18 points unread and 30 read, two of eight
  biochemistries are legible on day one and the dearest costs 880 points, the
  catalogue groups only what you actually catalogued and deepest-first, the line
  naming a technology spells it the way `data/tech.py` does — and no body plan
  claims a biochemistry.
- **`test_mesh.py`** holds the picket mesh to what its descriptions promise:
  without a node only the system you are in is plotted *while the traffic
  elsewhere really is there*, a node aboard plots the systems you have stood in
  and no others, a Node planted somewhere plots that system and stops when it
  goes offline, what the mesh shows is what standing there shows (same hulls, same
  names, one derivation), and the chart's warning is true — every hostile count it
  reported was what was actually waiting on arrival.
- **`test_options.py`** is the guard `sim/options.py` had been claiming since it
  was written — its docstring said "`test_options` fails if one stops being
  [read]" and there was no such suite, which is the module's own rule broken one
  level up. Each of the eight settings is **turned on and off and something a
  player would notice has to differ**: the window stops asking, the explanations
  disappear, an open instrument's timer moves from 400 ms to 1,500, the chronicle
  is written at once at zero days and not until day 21 at twenty, the three
  speech settings each push to `core/llm` and the other five do not, and the
  tutorial is offered only with its switch on. Plus the structural pair — every
  field is on the screen and every screen row is a field — and the bounds, which
  are enforced in `set_to` so a second UI cannot disagree with them.
- **`test_provenance.py`** measures both revived fields over samples big enough
  to see a rate in: 2,214 stories from six sectors come true 77% of the time from
  a local source and 45% from the far side, the trust figure the desk prints
  tracks the rate it observes to within 2%, moving `heard_at` alone changes the
  answer, a hub's word beats an outpost's by exactly `QUAY_TRUST` a level, the
  price the panel quotes is the price the counter takes, and a buyer who knows
  the captain pays 30% more for a survey — with both halves of knowing counted,
  so twenty-four dealings inside a month is worth less than the same business
  spread over years.
- **`test_industry.py`** licenses processes and then goes and looks at the
  prices: the buyer's treasury pays to the credit, the gate agrees with the act
  across all 48 process/power pairs, the industry comes up and alloy falls from
  134 to 118 at the licensee's berths against 187 elsewhere, the forecast lands
  within 8% of where the market settles a year later across 21 berths, it costs
  the captain 157 a tonne at that counter against 168 quoted, a berth founded
  afterwards comes up with the industry already running, licensing twice is
  refused and bringing an industry up three times changes nothing, every rival
  notices, and a good a port does not trade stays untraded.
- **`test_exchequer.py`** measures the public purse by running a sector for
  eight years rather than by calling `promote` and observing that it promotes: a
  day moves each purse by exactly what the ledger says, a surplus builds, a
  deficit gives a step up and *recovers the upkeep*, a power that cannot find
  the stake starts no ventures, a blockade costs its target income through the
  same `yield_of` the screen reads, a founded berth quotes prices the player can
  trade at, a closed berth is marked in the register, nobody pulls a berth down
  with the player's hull alongside, and a Free Port of the player's pays them a
  harbour due. The last check is the tripwire set: every constant in
  `data/exchequer.py` is pinned by a consequence — an outpost and a station
  clearing about the same, a promotion being a season of surplus away — rather
  than by repeating its own value.
- **`test_worlds.py`**, **`test_sky_kit.py`** and **`test_lighting.py`** hold the
  astronomical catalogue, and measure it in pixels rather than asserting it from
  the tables that made it. `test_worlds.py`: no two kinds of world render alike, a
  gas giant is banded and nothing else is, and faces meet with no seams between
  them. `test_sky_kit.py`: a star's size is its class's, rings are concentric *in
  the mesh* and belong to the world rather than to its number in the system, a
  ringed giant keeps them when you fly at it, and every kind the galaxy makes has
  a mesh. `test_lighting.py`: a painted world is smooth and its phase follows the
  star, the terminator is where the star puts it — moving with it, monotone into
  the shadow, **brighter than the surface's own colour at full day**, and a
  falloff with width rather than a cliff — and the paint covers the disc at every
  tilt. The three were one file until it passed 500 lines; each of the three
  claims in `test_lighting.py` exists because a mutation of `ui/spheres.py`
  survived without it.
- **`test_ui.py`** builds the real `MainWindow` on Qt's `offscreen` platform and
  paints every screen and every tab, including a live engagement. It stubs
  `win.dialog` because `QDialog.exec()` would block. One check builds its own
  window: grabbing a widget forces a layout pass, so a check for first-frame
  layout cannot reuse one every earlier check has already painted.
