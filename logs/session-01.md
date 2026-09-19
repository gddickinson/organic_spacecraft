# Session log, part 01 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-08-02 to 2026-08-02; undated entries keep their original place.

## 2026-08-02 — SEEDFALL: the harness was not lying, the screen was

#145 item 3 said `scratchpad/flygui.py` "lies about three buttons" and asked for
the harness to be fixed. **The premise does not survive measurement**, twice
over, and both corrections are worth more than the task was.

**First: the harness is not part of the project.** `git ls-files` has never had
it; there is no `scratchpad/` in the repo. It is a throwaway probe from an
earlier cycle in this session. Fixing it ships nothing, and its one substantive
claim — that a press which only swings the hull is not a dead button — is
already guarded, and better, by `tests/test_pilot_screen`'s "a press that only
swings the hull says so, instead of looking dead", which asserts `view.last`
and the rendered panel text rather than a position delta.

**Second, and this is the real find: the screen has duplicate labels.** Sweeping
all six thrust buttons, Port and Starboard appeared to do nothing at all — no
burn, no turn, no velocity, no mass — in both drive modes, reproducible with a
fresh fixture per button. **I wrote that up as two dead controls, and it was
wrong.** Every sim-level gate measured identical for left, right and up
(`can_burn` True, `pointed_at` False, `thrust_axis` returning a proper
`[-1,0,0]`), which is what said the fault could not be where I was looking.

The bridge has 27 controls and `{'Port': 2, 'Starboard': 2}` duplicate labels:
`conn.VIEWS` names a camera "Port" and `conn.AXES` names a thruster "Port". My
probe — and `flygui.py` before it — was clicking the camera. Addressed
unambiguously the thruster burns: `burned=True`, dv 0.451 m/s.

So: item 3 is closed as wrongly premised, and the defect underneath it is task
#153, with the measurement and both halves of the fix written down. The
generalisable lesson is on #145's checking list — **a check that finds a control
by its visible text is one duplicate label away from testing the wrong widget**,
and it fails silently and confidently.

No code changed this cycle. The finding did.

## 2026-08-02 — SEEDFALL: what was below the fold was the guns

#145 item 2. The figure predated the two-column bridge and the beat rewrite, so
it was re-measured first rather than trusted.

**Still 199 px, and the measurement named the culprit.** Shown at 1360x880:
968 px of content in a 782 px view, and the two controls under the fold were
`Open fire on Patient Ledger` and `Mark Patient Ledger hostile`. A pilot in a
fight had to scroll to shoot.

**The cause, per column**: left 173 px of controls, right 777. Side by side, the
taller sets the height alone; the left was mostly stretched viewport. So this
was never "the screen is tall", it was "everything is in one column".

`ui/pilot_panels` already said the left column is the view and the hands that
fly her and the right is the boards. A trigger is a hand.

  seed 'fold'   968 px -> 785 px content, fold 186 -> 3 px,  23/25 -> 25/25 on screen
  seed 'look'          -> 812 px content, fold 199 -> 30 px, 23/27 -> 27/27 on screen

Width unchanged at 891 in 891 — nothing clipped sideways to pay for it.

**Two defects I introduced, both found by flying it rather than reading it.**

1. `KeyError: 'fire'` on the first beat. The fire control is built into the left
   column, which happens before the right — and `self._boards = {...}` further
   down threw the entry away. `_boards` is emptied once, up front, before either
   column fills it.
2. **A mutant survived**: `_swap` remembering one column instead of asking the
   widget. It only bites *after* a beat — `indexOf` returns -1 on the wrong
   layout and `insertWidget(-1, ...)` appends, walking the fire control across —
   and my fold check ran on a freshly built screen. The claim moved to the beat
   check, which captures the fire control's column, ticks five times and asserts
   it has not moved. Three mutants, three bites after that.

Rendered the bridge flying with a course laid and looked at it: fire control
under the flight controls, both "Open fire" buttons and both "Mark ... hostile"
buttons on screen.

`tests/test_bridge.py` took five separate trims to land back at 499.

## 2026-08-02 — SEEDFALL: a label is kept clear by its own width, not a fixed box

#145 item 4, the collision filmed last cycle.

**Measured against the real font**, and the single 46 px box was wrong both ways:

  how tall a label is            46 px  ->  9 px measured (ascent 7)
  how far one reaches from a dot 46 px  ->  up to 85 px ("Second Signature" 77)

Vertically it over-rejected five times over and dropped names that would read
fine 21 px apart; horizontally it under-rejected by up to 39 px, which is
"Held Breath II" at x=315 drawn across the reticle at x=391.

**The fix**: `_label_box` returns every pixel a sight uses — dot and name, at
the place the name is actually drawn — and `_overlaps` is a rectangle test. It
hands back `left` too, so the label is painted where it was measured.
`Viewport._target` reports the box its bracket and label took and `Viewport.draw`
passes it as `taken`, so a sight is never drawn across the reticle.

**The stub was the blocker, exactly as recorded.** `_Blind.fontMetrics` returned
40 for every string — structurally unable to fail a rule that is only wrong for
long names. It models the measured face now (5 px a character against a real
4.8, height 9, ascent 7). Fixing the checker had to come first.

**Two wrong turns.**

1. My "far enough apart" fixture used a bearing that put the second sight *off
   the frame*: at this focal length 160 lands it at x=578 in a 464 px window, so
   `_screen` dropped it and the check passed for the wrong reason. Recomputed —
   40 lands it at x=319 — it passes for the right one.
2. **A mutant survived.** I had asserted `"taken" in src`, which stays true when
   the argument is dropped from the *call* and the local is left behind. The
   check now parses `Viewport.draw` with `ast` and asserts `draw_sights` is
   called with seven arguments. Five mutants, five bites after that.

Rendered the aft camera again to look: the reticle reads clean.

`ui/viewport.py` 521 -> 531 against its recorded cap of 533.

## 2026-08-02 — SEEDFALL: the Conn window had the player's complaint too

#145 item 1, unblocked by #146.

**Measured first.** 130.3 km off the Fleet Hub, Ashkeep Gate I at the same
range, a hull 4,726 km out: the Conn's main screen had `sights == ()` and
`mark is None`. Rendered it — a starfield, the system star, an unnamed
crosshair. The player's report about the Pilot screen, wearing the other
window's hat. Now five contacts named.

**One door.** `ui/sights.out_there(game, conn, rows, skip=())`, called by both
`pilot_panels.aim_feed` and `ConnWindow.refresh`; a check reads that from the
source with `inspect.getsource` rather than from a picture.

**Two things only the rendering caught.**

1. **A false alarm I nearly filed as a bug.** After wiring, the *fore* camera
   still drew no names. Measured: Fleet Hub at `ahead = -130.3` (behind the
   lens after 40 forward burns), Quiet Increment ahead but outside the 62° FOV.
   `project` returns None for both, correctly. The aft camera showed the labels.
2. **A real one.** The target was named twice — `Viewport._target` already draws
   "Fleet Hub · 130.3 km" and the sight printed "Fleet Hub" a pixel away.
   `out_there` now drops whatever the window names for itself, and the Pilot
   screen hands over its laid mark the same way.

**Also fixed, and it was mine**: #147 put the `conn` property above
`ConnWindow`'s docstring, which demoted the docstring to a no-op string
expression — the class had none at all. `ConnWindow.__doc__` reads again.

**Five mutants, five bites**, under `-B`: the Conn sets no sights again · sights
name the target the reticle already names · the laid mark is named twice again ·
the Pilot screen chooses its own sights again · the thumbnails get labels they
have no room for.

**Lengths**: `ui/conn_window.py` went 498 → 508 with the change and was trimmed
back to 499, paying for itself out of its own prose.

**Not fixed, deliberately, with the evidence recorded on #145**: sight labels
still collide — "Held Breath II" at x=315 against the reticle at x=391, dx=76
clearing a 46 px box for a 68 px label. Fixing it means replacing `CLEAR` with
extent-based constants, which touches the machinery #134 sweeps, and
`_Blind.fontMetrics` returns a fixed 40 for every string, so it cannot model a
width-aware rule until that stub is fixed first.

## 2026-08-02 — SEEDFALL: the beat was eating the button under your finger

Player report: "the lag between pressing a button and any response. When the
clock is running the buttons do not act immediately, and often don't respond at
all."

**Measured, and the first explanation was wrong.** The guess was cost: ~60-90
styled widgets and a fresh `Viewport` rebuilt four times a second. Timed, a
whole beat is **13.4 ms against a 250 ms budget** — a 5% duty cycle. Not slow.

The real number: `View.refresh` unparents every widget, `PilotView.tick` called
it every beat, and **0 of 25 buttons survived one**. A `QPushButton` emits
`clicked` only when the release reaches the object that took the press, and a
click is held 80-150 ms — so a beat in the middle ate it.

**Reproduced through the buttons**: press "Ahead", one beat, release over
"Ahead" — no burn. Without the beat — burn.

**A wrong turn worth recording.** The first probe reported "handler fired?
True" and nearly had me calling the report unreproducible. It drove Qt by
object reference: `QTest.mousePress(btn)` … `QTest.mouseRelease(btn)` with the
same Python `btn`. `park` only *unparents* the old widgets — they stay alive on
`view._doomed` — so the release found the very object that took the press. A
player aims at a place, not an object. Re-finding the button by its label
turned the same probe red.

**The fix**: controls built once and kept; `PilotView.sync` updates readings in
place; `PilotView.shape` decides when the situation (not the reading) changed
and a real rebuild is owed.

  buttons surviving a beat   0 of 25  ->  25 of 25
  click held across a beat   swallowed -> fires
  view.refresh()             12.4 ms  ->  4.1 ms
  whole beat                 13.4 ms  ->  4.6 ms

Readings still move (asserted), and laying a course still grows "Run for …"
and "Break off the course" (asserted). Rendered the bridge after 20 beats and
looked at it: 50.4 km flown, 32 min elapsed, course laid, "opening at 32 m/s"
agreeing with the nose 180° off.

**Six mutants, six bites**, all under `-B`: the beat rebuilds everything again ·
shape never notices a new situation · the beat stops moving the readings · the
throttle button stops following the throttle · park drops the widget · park
never releases what it holds.

**The fifth survived at first.** Nothing had ever checked `View.park`'s
guarantee — the defence against the segfault that killed the process three
times. Pre-existing gap, inherited by extracting `park` out of `refresh`;
closed rather than left.

**Ratchet**: `ui/widgets.py` came 517 → 516 and the debt row moved with it.
`tests/test_bridge.py` needed three separate trims to land at 499.

**One red run that was not a regression.** The first full run of this work
came back **EXIT=139 — SIGSEGV** after 38 suites, on "QPaintDevice: Cannot
destroy paint device that is being painted". It was not this change: `moorings`,
the suite that was running, passes alone; the same first 42 suites in the same
order re-ran green; and `bridge`, `pilotscreen` and `ui` are none of them in the
first 42, so none of this had executed. The same Qt message appears in green
runs. The re-run went 180 suites, EXIT=0. Filed as **#152** — and it means a
single red full run is not on its own evidence of a regression here.

**Filed rather than folded in: #151.** A `Game.__setattr__` spy caught
`PilotView.ensure_conn` replacing a live 2,700 s approach with a fresh flight at
0 s — called from `build()`, so taking command of the ship is a side effect of
drawing the bridge. Harmless when each screen owned its own conn; harmful since
#147 made them one.

## 2026-08-02 — SEEDFALL: one conn, because the bridge and the Conn window flew different ships

The player's report, and it was architectural rather than cosmetic.

**Measured first.** Flew the Pilot screen 290.9 km over 60 minutes on the main
drive, 20.00 t of reaction mass down to 14.57. Opened the Conn window: 12.0 km,
0 minutes, 20.00 t. Two `Conn` objects. `ConnWindow` built one and kept it on
the window, `PilotView` built another and kept it on the view, `MainWindow` had
no `conn` at all.

**The join.** `Game.conn` (transient), `MainWindow.conn = _on_game("conn")`,
and both screens as properties onto it. "pilot conn is the game's: True".

**Four wrong turns, all found by flying rather than reasoning.**

1. Putting a plain `conn` field on `Game` **broke saving**. A `Conn` holds a
   `Target`, which `core/save.register` has never heard of: the save was written
   and would not read back — "save refers to unknown type 'Target'",
   `load_game()` → `None`. Marked transient; `saved: True | loaded: True | conn
   after load: None, day 0 credits 18,000`.
2. `freeflight.hand_over` set `vel`, `nose`, `rcs` and `elapsed` and never set
   `pos`, though its docstring promised it — so the hull **teleported 302.9 km**
   (290.9 → 12.0) the moment you opened the Conn on something. Fixed from
   `track.at`; after: 290.9 km → 290.9 km, **0.0 km moved in the world**.
3. Securing from the bridge left the flight live: `secure` → `win.refresh()` →
   `ensure_conn` → a fresh conn on the same breath. 30 minutes became a
   different object at 0 minutes. `stood_down` + a "Take the conn" button.
4. `ConnWindow.closeEvent` wrote `outcome = "broken off"` and settled, ending an
   approach under a pilot still flying it from the bridge. Removed — `_break_off`
   is the one door onto giving up.

**Two harness mistakes worth writing down.** I edited `ui/conn_window.py` while
the mutation harness had it checked out, and separately let a detached run stay
alive while starting a second — between them the restore raced my edit and left
a mutation *in the file*, and one mutant reported `SKIP: pattern not found`
against a pattern that was plainly there. A skip is not a survival, but it is
not a proof either: re-run alone in the foreground, it BITES. **The rule about
never running two suites at once applies to mutation runs too**, and to editing
any file a harness is holding.

**Ten mutants, ten bites**, each run with `-B`:
`conn window: builds its own flight again` · `pilot view: keeps its own flight
again` · `hand_over: teleports to the arrival range again` · `hand_over: forgets
the hours flown` · `state: the conn is saved after all` · `secure: the bridge
hands her straight back again` · `secure: no way to take the conn back` ·
`take_conn: does not clear the stand-down` · `close: breaks off the flight on
the way out again` · `commit: stops charging for the mass burned`.

**Filed rather than folded in:** #148 (securing refunds up to 0.005 t — the
ledger rounds to 2 dp, the burn tracks 4; measured 2.715 t spent billed as 2.71)
and #149 (a flight nobody ever ends is never charged for its mass, unlike the
hours, which `charge_flown` bills as they pass).

## 2026-08-02 — SEEDFALL: the ship had two positions, depending who asked

#146, which was blocking #145's last big item. `freeflight.where` returns
`flight.ship_position(game) + conn.pos`, and `conn.pos` is an offset from the
frame's **origin** — which is where she let go in a free flight and the
*target* in an approach. `flight.ship_position` is not written again until
`berthing.commit`, so in an approach the answer was simply wrong.

Constructed so the two origins could not coincide — stand off, secure, then
take the conn:

                   where -> target      the conn's own range_km
    anchorage        10,152.4 km               12.0 km
    hull                                       12.0 km
    body                                    6,135.8 km

and afterwards all three agree to the decimal: 12.0, 12.0, 6,135.8.

It read correct on a fresh game only because the ship is moored *at* the
quay's body, so `ship_position` and the target's position are the same point.
That is why nothing had caught it, and why the first measurement of it last
cycle looked fine until I forced the ship away first.

**The fix is that a target can now say where it is.** `sim/track.at` is the
one door for "where is anything", and it reads `kind`, `at_xy`, `body_index`
and `hull_id` off whatever it is handed. A `Target` carried all but the last
two — and `target_from_contact` **dropped `hull_id` entirely** for a hull, so
a hull target could not be found again even in principle. It carries both now,
and `where` asks `track.at` when the conn has a target and keeps the cheap
`ship_position` path when it does not.

**A regression I did not cause, and checked before claiming otherwise.** The
Pilot screen's press cost read 14.0 ms and 11 traffic rebuilds against 12.3 ms
and 6 recorded earlier, which looked like my doing. Stashed and measured HEAD:
**11 rebuilds there too**. The increase came from last cycle's sights, which
call `freeflight.toward` per contact; this change is free, because a free
flight still takes the branch that never touches traffic.

Four mutations red, including the two halves of the branch swapped — an
approach measuring from the ship, and a free flight measuring from the target.

## 2026-08-02 — SEEDFALL: four names on one pixel, and labels drawn off the edge

#145 continued. Rendering the newly-named sights and counting them found two
faults that the eye had only hinted at.

**Four hulls projected to exactly the same pixel.** Measured across the six
cameras: Second Signature, Margin Call, Long Consent and Quiet Increment came
out at `dx=0, dy=0` in the fore view — they are hundreds of millions of
kilometres away in almost the same bearing, so four names printed on one spot.
Nothing is lost by dropping three of them: the "In view" board lists every
contact with its range. `sights` arrives nearest first, so the one kept is
always the nearer.

**And the count was lying.** After that fix the fore camera reported *one*
sight drawn and the picture showed none. `project` returns a point for
anything with a positive component along the view axis, so a contact eighty
degrees off the nose comes back at x=2,000 in a 464-pixel window — drawn past
the edge of the pixmap and counted as drawn. `_screen` bounds it to the frame
now, and the honest total is **3 of 6 sights landing in any camera**, with the
aft view reading "Fleet Hub" and "Patient Ledger" side by side.

**A bigger defect turned up and was deliberately not fixed.** Wiring the same
sights into the Conn window needs a bearing that is right in an approach
frame, and `freeflight.where` is not. Constructed: stand off 10,164 km from a
quay, secure, take the conn on it —

    conn.range_km       12.0 km      ← the conn's own answer
    freeflight.where    10,152.4 km  ← what `engage.range_km` would use

`conn.pos` is an offset from the frame's origin, and the origin is where she
let go only in a free flight; in an approach it is the target. It reads
correct on a fresh game only because the ship is moored *at* the quay's body.
I began the fix, found that `conn.target` is a `Target` and not a `Contact` so
`track.at` will not take it, and that doing it properly needs a position for
every target kind on a hot path — reverted, and filed as #146 with the
measurement. Half a one-door fix is worse than a clear boundary.

Four mutations red. Two checks moved to `tests/test_sights.py` when
`test_bridge` hit 529 lines, along a real seam: the bridge is the screen, the
sights are the drawing rules, and the rules need no window shown at all.

## 2026-08-02 — SEEDFALL: two player reports, one real and one not

Both measured before touching anything, and they came out differently.

**"The engine is on full thrust and the velocity stays the same."** It does
not. Pressed through the screen's own button with the main drive lit:

    press 1  2.7 m/s   press 2  5.3   press 3  8.0
    press 4 10.6       press 5 13.3   press 6 15.9

and `conn.speed` is exactly `|vel|` — 172.30 against 172.30 at forty presses.
Thrust accumulates and the row is honest. What can make it *look* flat is
already on the screen now: with the drive **off** a press is 0.45 m/s rather
than 2.65; an off-axis press with the torch lit spends its whole tick swinging
the hull and says so in the Drive row; and the autopilot brakes, which the
Autopilot row now spells out. I could not reproduce a case where it genuinely
stalls.

**"The Pilot view doesn't show the Fleet Hub or other ships and stations."**
Entirely right, and the cause was not the data. Rendered side by side at the
same quay:

    the conn  — "Fleet Hub · 12.0 km" inside a dashed reticle
    the pilot — nothing at all

`Viewport._target` gives a target its true angular size, and a free flight has
no target, so the Hub fell through to `_sky` as a **1.6-pixel speck**.
Measured: the free flight's sky holds *more* than the approach's — ten entries
against nine, **including the anchorages the approach leaves out**. The
drawing was the only thing missing.

`viewport_mark.draw_sights` names the quays and hulls out there, brighter
inside `engage.reach_km`. Worlds are left alone: `_sky` draws those as lit
discs and nobody loses a planet. Flown 651 km off the quay, the aft camera
reads "Fleet Hub" and "Patient Ledger".

**And moored, a quay is at exactly the ship's position** — the bearing is
literally `(0, 0, 0)`, there is no direction to draw, and the zero guard
returns None. That is right rather than a gap, and the check says so.

**Three checks of mine proved nothing, and the same lesson each time: do not
compare two grabs of a widget.** The first compared the view with sights and
without; the images differed either way, so deleting the drawing left it
green. The second asked `draw_sights` directly — which tests the drawing and
not the wiring, so deleting the *call* left it green too. The third was the
mark check written last cycle: standalone it passed, and inside the full run,
after other checks had shown windows of their own, the same two grabs came out
identical and it went **red on correct code**. Stubbing the drawing and asserting the window *asked* was better and still
not right: `painting.Painted` declines to draw at all when the platform
refuses a backing store — the very flakiness that module was written for — so
a check that depends on a successful paint went red on correct code in the
full run and green on its own. The wiring is read out of the source now:
`Viewport.draw` must name `viewport_mark.draw` and hand it `self.mark`.
Exact, order-independent, needs no paint device, and every deletion still goes
red.

**Two checks of mine proved nothing and a mutation said so, twice.** The first
compared two grabs of the same widget, with sights and without; the images
differed either way, so deleting the drawing left it green. The second asked
`draw_sights` directly — which tests the drawing and not the wiring, so
deleting the *call* from `Viewport.draw` left it green too. It now stubs
`draw_sights` and asserts the window asks for it, with something in hand.
