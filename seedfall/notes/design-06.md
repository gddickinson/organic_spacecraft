# What this is — the design, pass by pass (6 of 8)

Moved out of `seedfall/INTERFACE.md`, which is now only the map. Text unchanged.

### The beat that ate the button under your finger

**The player: "the lag between pressing a button and any response. When the
clock is running the buttons do not act immediately, and often don't respond at
all."**

`PilotView.tick` ended in `self.refresh()`, and `View.refresh` takes every
widget out of the column and reparents it to `None`. At `BEAT_MS` 250 that is
the whole screen — viewport, six cameras, six axes, throttle, clock, both
boards, the fly-at buttons, the guns — **built again four times a second.**
Measured: **0 of 25 buttons survived one beat.**

A `QPushButton` emits `clicked` only if the release reaches the object that
took the press, and a click is held down 80-150 ms. So a beat landing inside
that window swallowed the press whole. Measured through the buttons: press
"Ahead", one beat, let go over "Ahead" — **the burn did not happen**; with no
beat in between, it did.

**The first reading of this was wrong, and the measurement said so.** The guess
was that ~60-90 styled widgets plus a fresh `Viewport` four times a second was
simply too much work. It is not: a whole beat cost **13.4 ms against a 250 ms
budget** — 12.4 of it the rebuild, 0.6 the flying, a 5% duty cycle. The screen
was never failing to keep up. It was throwing away the control the pilot was
aiming at. The fix had to be about *identity*, not speed.

**The other screen already had the answer.** `ConnWindow.refresh` keeps its
title, its viewports and its console — `self.controls.sync(conn)` — and rebuilds
only the label panel, so its clock has never eaten a press.

So the bridge does the same. `PilotView.refresh` asks `PilotView.shape` whether
the *situation* changed, as against the readings:

    return (self.conn is None, self.stood_down, self.mark, self.auto,
            self.marked() is not None,
            tuple(c.name for _km, c in rows[:4]),
            fire_panel.shape(self.game, rows))

Same shape → `sync`, which updates the viewport, three button labels and the
three readout panels in place. Different shape → the full rebuild, because a
contact leaving the list or a hull coming into reach really is a different set
of controls.

| | before | after |
|---|---|---|
| buttons surviving a beat | 0 of 25 | 25 of 25 |
| a click held across a beat | swallowed | fires |
| `view.refresh()` | 12.4 ms | 4.1 ms |
| a whole beat | 13.4 ms | 4.6 ms |

**Two doors closed on the way.** Every label that changes while the clock runs
— `panels.main_label`, `throttle_label`, `clock_label` — is formatted in one
place that `build` and `sync` both call, because #137 already caught the version
of this where two places formatted the throttle and the button read 50% above a
panel reading 100%. And `fire_panel.ARMED` now backs `buttons`, `marks` and the
new `fire_panel.shape`, so the screen asking "did the fire control change?"
cannot get a different list from the one it drew.

**`View.park` came out of `View.refresh`** so a screen can retire a single
readout under the same rule the whole column obeys: the outgoing widget is held
on the view and released on the next turn of the event loop, because a signal
handler must not destroy the widget that emitted it. That rule had killed the
process three times — a `Card`, a `QLineEdit` mid-keystroke, a `QComboBox` still
delivering the click that dismissed it — and **had no check of its own** until
now: the mutation that makes `park` drop the widget immediately survived the
whole suite. It does not any more.

### The other window had the same complaint

`ui/sights.py` answers one question — **which contacts get a name in a window,
and the bearing to each** — because two windows ask it.

The player's original report was that the Pilot screen showed nothing of what
was out there while the Conn drew its target properly. `viewport_mark.draw_sights`
fixed the Pilot half. Measured afterwards on the Conn, standing 130.3 km off the
Fleet Hub with Ashkeep Gate I at the same range and a hull 4,726 km out:
`screen.sights` was `()` and `screen.mark` was `None`. Rendered, that is a
starfield, the system star and an unnamed crosshair — **the same complaint, in
the other window.** It now names five.

The choosing lives in `ui/sights` and the drawing in `ui/viewport_mark`, so a
screen that wants names asks for them rather than working out its own rules,
which is how the two came to disagree in the first place. `ui/pilot_panels.aim_feed`
and `ConnWindow.refresh` both call `sights.out_there`, and a check reads that
from the source rather than from a picture.

**Nothing the window already names is named again.** The first draft printed
"Fleet Hub" as a sight directly on top of `Viewport._target`'s reticle, which
reads "Fleet Hub · 130.3 km" (viewport.py:427) — one thing wearing its name
twice, a pixel apart. `out_there` drops the conn's target itself, and takes a
`skip` for whatever else the caller draws: today the contact a course is laid
on, which `viewport_mark.draw` already rings with its name.

**A false alarm worth keeping.** With the sights wired, the Conn's *fore* camera
still drew nothing and looked broken. Measured rather than assumed: the Fleet
Hub was at `ahead = -130.3` — behind the lens, forty forward burns having taken
her past it — and Quiet Increment was ahead but outside the 62° field of view.
`viewport_math.project` returns `None` for anything at or behind the lens, which
is correct. Point a camera at the thing before calling the drawing wrong.

The thumbnail feeds are left bare on purpose: they are 120 px wide and a name on
one is not readable. That is asserted, so a later hand does not "fix" it.

**Still crooked, and measured**: sight labels can collide. On the Conn's aft
camera "Held Breath II" is drawn at x=315 and the reticle at x=391 — dx=76
clears `draw_sights`'s fixed `CLEAR` box of 46 px, but the label is about 68 px
wide, so they touch. Two rules are wrong at once: the overlap test compares
centre-to-centre against a fixed box rather than the label's real extent, and
sights know nothing about the reticle at all. Left for its own cycle; see #145,
which records why.

### A label is kept clear by its own width

`viewport_mark.draw_sights` used to decide whether two names would collide by
comparing their dots **centre to centre against one fixed 46-pixel box**.
Measured against the font it actually draws with — the mono face at 6 pt — that
number was wrong in both directions at once:

| | the box said | measured |
|---|---|---|
| how tall a label is | 46 px | **9 px** (ascent 7) |
| how far one reaches from its dot | 46 px | **up to 85 px** — 8 + 77 for "Second Signature" |

So vertically it over-rejected by five times, throwing away names that would
have read perfectly twenty pixels apart; and horizontally it under-rejected by
up to thirty-nine, which is how "Held Breath II" at x=315 came to be drawn
across the target reticle at x=391 on the Conn's aft camera.

`_label_box` now returns **every pixel a sight will use** — its dot and its
name, at the place the name will actually be drawn — and `_overlaps` is a plain
rectangle test. It returns `left` as well, so the label is painted exactly where
it was measured; working that out twice is how a label comes to be tested in one
spot and drawn in another.

**And the reticle is not a place a sight may go.** `Viewport._target` draws a
dashed bracket labelled "Fleet Hub · 130.3 km" (viewport.py:427) and now hands
back the box it used; `Viewport.draw` passes it to `draw_sights` as `taken`.
Sights are dropped rather than shifted, which is the rule that was already
there: nothing is drawn on top of anything, and nothing is lost because the "In
view" board lists every contact with its range.

**The checking stub was the reason this could not have been caught.**
`tests/test_sights._Blind.fontMetrics` returned **40 for every string** — a font
where every name is the same width cannot fail a rule that is only wrong for
long ones. It models the measured face now: 5 px a character against a real 4.8,
height 9, ascent 7. That had to be fixed before the rule could be.

### The guns go with the hands

The bridge's fold came down from 662 px to 199 when it became two columns, and
there it stopped. Measured on a shown window at 1360x880, what was still under
the fold was not a bit of everything — it was **exactly the fire control**:
`Open fire on Patient Ledger` and `Mark Patient Ledger hostile`, the two things
a pilot in a fight reaches for.

The cause was not that the screen was tall. Measured column by column:

| | content |
|---|---|
| left — the view and what flies her | **173 px** |
| right — the boards | **777 px** |

The two columns are laid out side by side, so the taller one sets the height on
its own, and the left was mostly stretched `Viewport`. The right column was
carrying the ship board (316), the in-view board (208), the fly-at buttons, the
autopilot row, and the whole fire control (166) on top.

`ui/pilot_panels`'s own docstring already had the rule: the left column is **the
view and the hands that fly her**, the right is **the boards that tell you what
is out there**. A trigger is a hand. Moving the fire board and its buttons to
the left settles both halves at once —

| seed | content | fold | controls on screen |
|---|---|---|---|
| `fold` | 968 → **785 px** | 186 → **3 px** | 23/25 → **25/25** |
| `look` | — → **812 px** | 199 → **30 px** | 23/27 → **27/27** |

— and the width is unchanged at 891 px in an 891 px viewport, so nothing is
clipped sideways to buy it.

**A board no longer knows which column it is in, and must not think it does.**
`PilotView._swap` replaces a readout in place on every beat; it now asks the
outgoing widget for its own layout (`old.parentWidget().layout()`) rather than
holding `self._right`. A remembered column walks the fire control across to the
boards on the first tick — `indexOf` returns -1 on the wrong layout and
`insertWidget(-1, ...)` appends. That is checked by capturing the fire control's
column, beating five times and asserting it has not moved, because the mutation
survives a check that only looks at a freshly built screen.

### One name, one control

**Two buttons on the bridge say "Port" and two say "Starboard".** Measured on
seed "dup": 27 controls, and the labels that appear more than once are exactly
`{'Port': 2, 'Starboard': 2}` —

    camera labels  (conn.VIEWS): Fore, Aft, Port, Starboard, Dorsal, Ventral
    thruster labels (conn.AXES): Port, Ahead, Starboard, Down, Astern, Up

so "Port" is both *look to port* and *thrust to port*, a few pixels apart in the
same column. The Conn window carries the same pair.

**This is why every probe that finds a button by its text has been lying.**
`scratchpad/flygui.py` reported "pressing 'Port' moved the ship nowhere", and a
fresh re-measurement — one new fixture per button, to rule out ordering —
reproduced it and added "Starboard" and made it look like two dead thrusters.
Both were clicking the *camera*. Addressed properly, the thruster burns:
`burned=True`, 0.451 m/s. Nothing was ever wrong with the thrusters.

The lesson generalises past this screen: **a check that finds a control by its
visible text is one duplicate label away from testing the wrong widget**, and it
fails silently and confidently. Recorded as task #153 with both halves — the
player-facing naming, and object names so a probe can address exactly one
control.

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
