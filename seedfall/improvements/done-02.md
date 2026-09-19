# SEEDFALL backlog — done, part 02 of 03

Moved out of `seedfall/IMPROVEMENTS.md`, which keeps only what is open. Order and wording are unchanged.

## Done — the eleventh pass (2026-08-04): the sector answers back

The top of the reassessed list, in order. Every one carries a played claim.

- **A wait stands down on news worth a hand** (`core/clock.wait_days`,
  `Game.wait_days`). Found by playing: a year alongside a Fleet Hub starved
  three crew one at a time, with credits in the purse and biomass on sale a
  berth away, while the log said "it is starting to tell" five times and
  nothing paused. `advance_days` stays exact — work that bills its own days
  bills all of them — and *waiting* is the different verb. Stops on `bad`
  **and `warn`** (`STAND_DOWN_KINDS`: the starving crew is warned three
  times and only `bad` once everyone is dead, so stopping on `bad` alone
  stops exactly too late), always for a question the window would lock on,
  and reports a digest — days, treasury, what was said — with "wait the
  remaining N days" on the dialog. Measured on a provisioned captain:
  9–90-day stretches, so waiting is still waiting.
- **The Bloom is felt in the treasuries that fund everything**
  (`exchequer.BLOOM_YIELD_LOSS`). Nothing holding money read `system.bloom`
  before: a fully overgrown sector now takes a power from 724 to 109 credits
  a day, which shrinks its fleets, its ventures and its promotions through
  machinery that already existed.
- **The powers fight it** (`containment`, `data/ventures.py` +
  `ventures._apply`). Six venture kinds and none was about the thing eating
  the sector; nothing in the game but the captain had ever reduced
  `system.bloom`. A flotilla is fitted out for the worst system anybody can
  see, cuts 0.22 off it, and provokes the Bloom the way a captain's burn
  does. Backing or opposing it runs through the existing preview pipeline.
- **Ruin is outlived, not waited out** (`threat._stood_through_it`), and
  **the loss can be reached** (`threat.harbours_left`). Ruin asked only for
  a drowned sector and a live hull, which passivity satisfies ~180 days
  before the loss could fire — and victory is checked first, so a living
  captain could not lose to the Bloom at all. Ruin now wants something of
  yours still standing or a record of having fought; the loss fires when
  every *harbour* is drowned, which happens sooner and can be watched
  closing.
- **An empire is not free to administer** (`works.admin_total`,
  `data/works.ADMIN_STEP`). Each holding past the first makes every holding
  dearer: the marginal worth of one more falls from +359/day at five to
  +65 at thirty, so colony spam has a ceiling, and the credit line goes
  negative at scale — a large empire must *trade* to pay its bill, which is
  the late-game sink the game lacked. The seed card quotes it before you
  commit.
- Found while doing it: the bridge's `extract` verb advertised "tonnes" and
  its parameter was *days* of rig time — asking for 30 t ran a 30-day
  working that raised 99 t.
- **Fifteen failures the pipe had been hiding, all traced before fixing.**
  Four were real regressions of mine: the heart-fallback that fixed the
  no-op responses had let the *routine* top-up reach the origin, making it
  a permanent re-infestation engine that put Containment out of reach
  (`_spawn_instar(from_heart=...)` — a wave is an event, the top-up is a
  standing condition); and a competent enemy proved worth about a
  difficulty step, so a light patrol beat an armed hull three times in ten
  until enemy nerve was re-pitched (`encounters.RESOLVE_BASE`, measured
  82/33/15 across the scale against 71/33/15). Six were checks encoding
  rules deliberately changed — Ruin's new gate, hold-only delivery,
  `abilities.armour_of`, the moved ledger, and two fixtures that assumed a
  port can never close (a power poor enough to retrench now gives one up,
  which is the Bloom's economic bite working). **Five were checks measuring
  badly**, and would have failed on any later change: the provoked-growth
  check ran three years into saturation where both arms pin at the ceiling
  and read equal to the decimal — below it the effect is ×2.20 and ahead in
  20 sectors of 20, against the ×1.085 and 15-of-20 it used to report; the
  warfit and smuggling checks judged 32- and 12-sample statistics against
  thresholds finer than their noise, and smuggling used a *mean* where one
  seizure swamps the distribution (median: bare +33k, kitted +292k); and
  the `offer_gain` one-door check counted a *comment* as a reading.
- **Four length violations, and the measurement that hid them.** The tenth
  pass was reported green on a run whose exit code was read through a pipe
  (`... | tail; echo $?` is *tail's* status, always 0), so `tests/test_ui.py`
  at 530 lines rode into commit `0c98798` over the ceiling. Paid off along
  real seams: `tests/test_window.py` (the window as an application —
  navigation refusal, save on quit, dismissed dialogs, the unstubbed
  briefing), `ui/seed_dialog.py` (offering, pricing and planting a colony),
  and `sim/exchequer_ledger.py` (the screen queries), which took
  `sim/exchequer.py` under the limit and **off the debt list** — ten files
  and 517 lines of debt now, down from eleven and 525. `tests/test_play.py`
  went the same way afterwards, along the seam its own docstring names:
  `tests/test_endgame.py` holds the Bloom's escalation, its adaptation and
  the climax at Kessel's Reach.
- **A check whose control was somebody else's ports.**
  `test_industry`'s "cheaper than other powers' berths" inverted by one
  credit (156 against 155) the moment infestation began moving power
  economies — the same shape as the 1.15 ratio that check already records
  recalibrating once. Replaced with the like-for-like control (the same
  berths, the same year, without the licence), which no tuning of the
  sector's economy can shift. **A control that is not the thing you changed
  is not a control.**

## Done — the twelfth pass (2026-08-04): played again, five things found

A fresh play-through of the committed tree, over the bridge and on screen.
Everything here was found by playing rather than by reading.

- **The ship's log became an unreadable smear.** By day 226 the sidebar —
  the game's only notification channel — was a column of two-pixel slivers.
  The same fault `widgets.View._sync_scroll` exists for, in the one panel
  that fix never reached: rebuilding a column of wrapping labels inside a
  scroll area does not tell the inner widget its contents grew, so sixty
  entries were flattened into one screenful instead of scrolling. Now
  2,062 px of log in a scroller, and the good/bad tints from the tenth pass
  finally do their job.
- **A recurring warning turned a long wait into a wall.** Standing down on
  every bad line meant a hold short of biomass stopped the wait eight times
  in fourteen days with the same sentence. `wait_days(..., ignoring=)` and
  a digest that hands back what it showed: **"carry on" now means "I have
  read that"**, and only genuinely new news stops the next spell. Measured:
  three stand-downs for three distinct developments, then a full 120-day
  spell.
- **A driven session deadlocked on an envoy.** An envoy or a territorial
  demand stops the clock and locks the window, and the protocol could
  neither see nor answer one — so every wait returned nought days for ever.
  `waiting` and `reply` verbs (`bridge/protocol.py`).
- **The containment bar said "nearly won" to a captain who had done
  nothing.** It measured systems-not-yet-infested, so an untouched sector
  on day 227 read 38 of 42. The husk is half the condition and is now half
  the measure: 46% untouched, 50% with the sector clean, 100% only with the
  origin dead.
- **"Five of them"** over ten endings, counted now rather than stated; and
  `HEART_HP` read from `data/bloom` in both views instead of a hardcoded
  2600 in each.

## Done — the thirteenth pass (2026-08-05): the flight deck, photographed

A deep play-test driven through the real interface — a hull flown to a quay
by hand and then by computer, every flying window opened, every instrument
photographed and *looked at*. Five defects, none of which stopped anything
working, which is why pressing every control had never found them.

- **Opening the conn threw away a finished approach.** Berthed at Fleet Hub,
  moored, `anchorage.docked_at` naming the berth — and opening the Conn
  window began a fresh approach at the arrival range, so the instruments
  read 12,000 m from a quay the ship was tied to. Securing sets `landed`,
  and the window read that as "no live flight". Exactly the fault that
  window's own note says it exists to prevent: one flight, whichever window
  you look through. Taking the conn again is a control the pilot presses.
- **Two controls in one grid cell.** The conn console put "Cut in" and the
  100% throttle in the same place — four throttle steps running into a
  button at column 3 — drawn over each other into an unreadable smear, both
  clickable. The throttle and coast runs have a row of their own now and
  their columns are derived, so neither collides if either list grows.
- **An instrument value cut off mid-word.** "Computer — off — she flies as
  you fly her" was drawn unwrapped in a fixed-width column: the pilot read
  "she flies as you f". Values wrap now.
- **A ladder of overlapping labels.** Every tick on the predicted course
  carried its time, and on a slow approach the whole hour landed inside
  forty pixels — "6m120m…560m" in one smear. One label per `LABEL_GAP`.
- **Four names in one place on the plotting board.** At the default zoom the
  inner system is a few pixels across, so the star, its worlds, the quay and
  the ship all wrote their names on the same spot. Names give way to each
  other (`NAME_GAP`); marks never do, and a chosen mark is always named.

`tests/test_flightpix.py` holds the four claims — a suite that asks whether
the flying windows can be *read*, beside `test_flightops`, which asks
whether their controls work.

## Done — the fourteenth pass (2026-08-05): the fog, and two stolen flights

The Holdings fog leak, then a forty-six shot sweep of every screen with a
flight photographed at five stages, an orbit, a free flight and all six
cameras.

- **The Holdings panel counted the whole sector.** `intel.sees_bloom` covers
  the chart and this went round it: every infested system counted and the
  sector-wide burden printed, above a picket whose `watch` is sold on
  telling you what happens where you are not. `threat.known_bloom` is the
  one door — the census is what is *known*, and it says how many systems
  nothing of yours has looked at rather than folding them in silently.
  `victory_progress(seen_only=True)` fogs the containment bar for display;
  **the achieved flag is never fogged**, or a captain could take Containment
  by keeping their eyes shut.
- **Opening the conn stole a live orbit.** Established at 299 km under the
  computer, opening the Conn window switched the target to a quay and began
  a fresh approach — photographed as "Conn — Fleet Hub, approach begun,
  12.0 km" over a hull circling a world. Two causes, both now fixed: the
  window asked `default_target` instead of the flight it already had, and
  **a `Target`'s id is not a `Contact`'s id** — a quay is `quay:port-14` on
  both sides but a body is `body:0` as a contact and `0` as a target, so
  "am I already flying to this?" answered *no* for every world in the game.
  `conn_targets.same_place` asks the question through
  `targets.target_from_contact`, so both sides are the same kind of thing.
- The same fix retired the `landed` half of the test: `landed` means
  *arrived* — secured at a quay, established in an orbit, set down on a
  surface — and all three are still flights whose target the window should
  be showing.

- **A ship in orbit is no longer at the planet's core.**
  `flight.ship_position` returned the body's exact position when alongside
  one, so the Pilot screen listed a world 6,772 km in radius at `0 km` and
  every range to the thing you were standing at came out nought. This is
  the third defect of that shape the project has fixed, after
  `anchorage.berth_orbit` for a quay at its planet's centre and
  `traffic.STATION_KM` for a hull sharing a body — and it is fixed the same
  way, by giving the thing a place of its own.
  `flight.ship_orbit_offset` holds the radius the flight actually flies
  (`Game.orbit_alt_km`, or the standard rung when nobody has chosen), on an
  orbit derived from the body's identity and the calendar and never stored,
  so an old chronicle gains the place without a migration. Measured: the
  world that read 0 km now reads 7,449 km, which is its standard orbit
  radius, and the conn's altitude and this agree because both ask
  `orbits.height_km`. Two position claims that asserted the hull sat at the
  body's exact centre now assert the stronger thing — that it rides *with*
  the body without being buried in it — and a new sweep holds that nothing
  a captain is standing at ever reads zero (61 ranges, 6 chronicles).

## Done — the fifteenth pass (2026-08-05): one way in to everything

**Reported by a player: "I can fly up to a Weave anchor, but how do I use
it?"** They were right to be stuck. An anchor is a place in the system with
no services, the panel that rides a ring lives on the sector chart, and the
anchorage card's fall-through for anything that is not a quay offered *Open
holdings*. So the game invited them to fly to a thing and then said nothing
at it.

- **The anchor explains itself, at the anchor.** Standing at one now says
  what a Weave anchor is, whether it is lit, what it is joined to, and — if
  dark — exactly what waking it wants, which is the Weavecraft technology
  before anything else. With a button to the chart where the ring is ridden.
- **A manual topic**, "The Weave, and how to ride one", with a generated
  fact that reads *this* chronicle: how many anchors are burning, what the
  one here is doing, and what a step from where you stand would cost.
- **`sim/hail.py` and `ui/comms_window.py` — the general fix.** One door
  that opens on anything `sim/track` can put a cursor on: who they are,
  what they say in their own voice (`sim/voice`), and a menu of what can be
  done, every entry either available or greyed *with the reason*. A quay
  lists its services and its harbourmaster; a gate lists its transits or
  what it needs; a world lists survey, rig and landing; a hull lists hail,
  mark and the guns. Reachable from the Pilot screen's contact rows and
  from every place on the helm's put-in list.
  It decides nothing — every option is a door that already existed
  (`berthing`, `gates`, `hostiles`, the port screen), which is what stops a
  menu promising what the game would refuse. `tests/test_hail.py` holds
  that: what the menu offers is what `berthing.can_conn` answers, and every
  refusal names a reason.

## Done — the sixteenth pass (2026-08-05): played long, and losing exists

Fifty-odd chronicles driven headlessly across the economy, four long games
pressed through the real GUI to day 2,280–2,666, and the option-space behind
every dialog (colonies, research, the ground, digs, the shipyard) driven
directly. The GUI play found nothing; the long economy runs found eight
things, and two of them were load-bearing.

- **The game had no loss by neglect.** Three modules agreed a chronicle ends
  when the crew is gone, no officer is active and no machine keeps watch —
  and the test sat inside the branch `upkeep.tick` only reaches when
  something the crew *needs* is missing. Nothing is missing once nobody is
  aboard to need it, so the branch was unreachable: five do-nothing
  chronicles all emptied (seed `dn-a` at day 1516) and not one ended.
  `upkeep.unmanned` is asked every tick now; doing nothing ends it at 1517.
- **Idling out-researched playing by about forty per cent.** `research.tick`
  poured `banked` in raw while the day's own points were throttled by what
  the bench is supplied with, so *not choosing* beat choosing and a saved
  lump cascaded through node after node. Banked points go through the same
  gate now: always-on 12 techs against bank-then-dump 13, was 16–17.
- **Standing was purchasable at about 350 credits a point.** Survey data is
  an ordinary stocked commodity, so the sets could be bought over the very
  counter they were handed back to, and the hand-in granted `min(6, n*0.4)`
  with no cooldown — nought to the +100 cap in 19 to 26 hand-ins.
  `SURVEY_REP_CAP` puts it at the same rate as any other sale, and the
  hand-in finally goes through `wharfage.collect`, which its own docstring
  calls "the only place money moves" — 50 sets moved 20,650 credits with the
  quay seeing none of its 519.
- **A prospect is gated on the voyage, not on a tally.** The `bought_here`
  count added in the twelfth pass never came down, so a captain who
  *refuelled* at the issuing port — volatiles and biomass are both wanted
  goods — had an honest mined cargo refused for tonnes long since burned.
  `Contract.travelled` is the thing the rule was always reaching for, and a
  purchase cannot poison it.
- **A starving holding said so every day for ever** — 770 lines in 800 days,
  which wiped the 300-line log inside four months and stood a long wait down
  daily. Once when it starts, once a year after that, and once when it is
  fed again.
- **A hold worth selling is a way out.** `is_stranded` priced escape against
  the purse alone, so a captain at a market with 15,000 credits of silicon
  aboard was called stranded — and the tow charged them standing to be
  dragged away from the counter that would have fixed it.
- Two smaller ones: a discarded docstring in `colony.bloom_attack` (two
  string literals, the informative one a no-op), and the harness captain in
  `tests/captain_bot.py`, which bought fuel and never food and then had no
  income once the bodies in reach ran out. **Three times now this file has
  recorded the same lesson: that is not the game dead-ending, it is the
  probe failing to take the move in front of it.**

## Done — the seventeenth pass (2026-08-05): one ship, one place, one drive

Three things reported from play, all of them the same shape — a fact with
more than one door.

- **The ship's position did not follow a flight.** `flight.ship_position`
  returned the *recorded* place, and the recorded place is not written again
  until `berthing.commit` — so the helm's system map, the plotting board and
  the tactical list all held the hull at the quay it left while the conn
  beside them counted the range down. Reported as four windows disagreeing
  with a fifth; it was one window telling the truth. `base_position` is the
  recorded place now (what `freeflight.where` flies from) and
  `ship_position` adds `Conn.flown_km` on top, so every screen that already
  asked the one door follows the flight without being told there was one.
  - The subtlety that cost a rewrite: **`conn.pos` is not an offset from the
    ship.** An approach's frame is anchored on its *target* and
    `conn_open.start` opens it at a canned arrival range, so `conn.pos` is
    already kilometres the instant a conn is taken — adding it teleported
    the hull every time a window opened. `Conn.start_pos` and the
    `flown_km` it feeds are zero at that instant and exactly the kilometres
    flown after it, which is true in an approach frame and a free one alike.
  - The sector chart is at light-year scale and a flight inside a system
    does not change which system you are in. There is nothing there to
    follow, and the check says so, so a later cycle does not "fix" it.
- **The engine button said "off" while the computer was burning.** Three
  windows formatted that label themselves and only the flight panel had
  learned to say FIRING. `instruments.drive_note` is the one door;
  `conn_controls`, `flight_window` and `pilot_panels` all ask it.
- **Speed was there under two names.** `instruments.readout` called it
  "Speed" in a free flight and "Relative" when orbiting and when coming
  alongside. One quantity, three windows, two words — which reads as a
  missing instrument, and was reported as one. It is "Speed" everywhere; the
  orbit panel keeps "Circular here" beside it, because that is a different
  number.

**And one thing the new fixes caught in an old check.** Giving the game loss
by neglect (16th pass) silently shortened every long headless fixture: a
do-nothing chronicle now ends at about day 1,360, and `advance_days`
early-returns after that — so `test_war`'s "3,600 days" loop was really
running about 1,400 and measuring the sector a third of the way through its
decade. It reported 1 war over six sectors and no quay changing hands, against
6 and 2 when the calendar actually elapses. The fixture provisions the hull
now (food and wages, the only things `upkeep.demand` asks for — not a
suppressed death, so a regression in the rule itself would still show), and
the check reports the span each sector actually got so the truncation cannot
go quiet again. Surveyed the rest: `test_geography._fed` already had the
pattern and its docstring says why; every other long fixture stops under
1,400 days. **Any new fixture that means to run past ~1,400 days must
provision, or it is measuring less calendar than it asks for.**

Played rather than argued: `test_window` opens the real `OrbitChart` and
`PlotCanvas`, flies the hull 19,539 km from the flight deck and asks each
widget where it is drawing her; `test_position` holds the recorded place
still mid-flight and checks securing does not count the flight twice;
`test_instruments` drives all four target kinds for the speed row and walks
the drive label through off → armed → FIRING with the pad switched *off*,
which is the reported case.
