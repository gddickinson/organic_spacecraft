# Review 2026-09-17 — SEEDFALL — gameplay, interface and engine (#9–35)

Part of the [whole-project review](README.md).

## P1 — SEEDFALL gameplay (measured with scripted play: 5 strategies × 5 seeds × 3–7 years)

9. **Lineage ending on day 21 for about 12.5k credits.** *Re-checked in
   `sim/threat.py`.*
   - **How:** lay down three empty SPOREs. The starting NAVIS counts as the
     fourth grown hull, and `licence` is a starting tech.
   - **The UI steers you to it:** the yard opens on SPORE with "Lay down"
     enabled.
   - **The licence doesn't stop it either:** a suspended licence doesn't
     block `start_build`.
   - **Fix:** count only hulls gestated after day 0; check
     `enforce.may_seed` in `start_build`. **S**

10. **Re-sweeping an already-surveyed body pays without limit.**
    - **Yield:** 1 day gives 1 survey set (about 580 cr) plus research,
      which works out to 415–586 cr/day and 447k–643k credits after 3
      years. The honest explorer made 49k–110k.
    - **Research:** the whole 62-node tree was done by about day 1,710.
    - **The UI contradicts itself:** the panel says "nothing further to say"
      while the button stays enabled.
    - **Nothing pushes the price down:** `trade.sell_survey_data` never
      calls `apply_sale`.
    - **Fix:** pay only for new findings, and route survey sales through
      `apply_sale`. **S**

11. **Standing is for sale.** *Re-checked (`sim/trade.py:125-128`).*
    - **How:** buying and reselling at the same counter grants
      `min(2, n*0.05)` standing per sale, with no cooldown.
    - **Measured:** 40 → 100 Charter standing in zero game days for about
      8k credits.
    - **Knock-on:** this plus #10 unlocks Concord (days 987–1,207) and
      Apostasy (day 201).
    - **Fix:** grant standing only on imported goods, or only on net sales
      per port per period. **S**

12. **Honest play reaches no ending, and the Bloom is back-loaded.**
    - **Three-year careers:** 20 careers (trader, explorer, fighter,
      colonist) reached nothing.
    - **Long runs:** all four long runs were overgrown on days 1,920–2,370.
      Infestation sat at 2–12 of 42 systems for about 3 years, then went
      sector-wide.
    - **Mid-game stall:** explorer income stalls once the reachable pocket
      is charted.
    - **Progress bars:** Dominion, Xenarchy and Cartel stayed near 0.
    - **Fix:** smooth the Bloom curve, and give each ending an intermediate
      tier that honest play feeds. **M**

13. **Losing a battle kills you only in the window.**
    - **Where:** `aftermath.resolve` returns `"lost"` with the captain alive,
      and only `ui/battle_view.py:403` calls `g.die`. The bridge, bots and
      `chronicle` survive defeats.
    - **Unarmed start:** 36% of encounters are lost.
    - **No combat career:** encounters come about 1.3 times a year and can't
      be sought. Bounties: 0 completed in 15 fighter-years.
    - **Fix:** move death into the sim, and add a way to seek a fight
      (patrol a lawless system, or a bounty that marks its target). **M**

14. **Envoys arrive from day 1 and block the tutorial.**
    - **Timing:** median day 12, and as early as day 1.
    - **The lock:** both "Take me there" and the envoy screen's own "Leave it
      for now" bounce off `window.py:276`.
    - **Fix:** a grace period of about 60 days, and make "Leave it" defer.
      **S**

15. **Starting positions vary enormously.** Across 40 seeds, 2 to 42
    systems are reachable at the starting drive. 10 seeds reach only
    Charter quays and 9 have a single neighbour. **Fix:** guarantee a
    minimum pocket (about 8 systems, 2 powers), and say how to get out. **M**

16. **Smaller rule bugs.**
    - `colony.can_found` ignores the licence that `found` enforces, so the
      dialog offers "Plant it" and then refuses.
    - Survey commissions count bodies surveyed before acceptance (2 of 18
      paid out within a day).
    - Freight quotes taken during a market shock aren't marked, so one
      "0.94 confidence" run lost 12k credits.
    - The research bench logs "short of hardware" every 1–5 days.
    - **Effort:** S each.

17. **The tutorial and goal text contradict the game.**
    - **Tutorial:** lesson 9 says to sell survey data two lessons before the
      first survey; it says "fifty-eight nodes" (the game has 62) and "six
      powers" (there are four); and real-time flying lessons come before any
      money.
    - **Goals:** Apostasy says "Kin" but checks ≥75 (Kin starts at 70), and
      Concord's text omits "all six pairs at peace".
    - **Fix:** compute counts from data. **S**

18. **"Take command" breaks game rules from inside the UI.**
    - **Where:** `yard_view.py:427-438` (*re-checked*).
    - **Effect:** it moves all cargo with no capacity check, so 148 t went
      into a 12 t SPORE (HUD: "Hold · 141/12 t").
    - **Fix:** a `consorts.take_command` rule with a refusal reason. **S**

19. **Opening a screen changes the future.**
    - **Where:** `contracts.board_for:208` and `ui/berths_panel.py:27` draw
      from the game RNG lazily.
    - **Effect:** a game where the board was opened on day 0 has different
      markets by day 200.
    - **Fix:** seed each draw from its own key. **S**

20. **Six copies of the "stores" helpers spend in opposite orders.**
    `colony` and `shipyard` spend from the depot first; `works` and `gates`
    spend from the hold first, and biomass is crew food. **Fix:** one
    `sim/stores.py`. **S**

---

## P1 — SEEDFALL interface

21. **Content clips at the enforced minimum and at 1280×720, and
    horizontal scroll is off.**
    - **Where:** `widgets.py:361`.
    - **At 1040×680:** 11 of 15 screens overflow, and **all 13 Port "Sell"
      buttons are off-screen**.
    - **The Yard** needs 938 px, which is the root cause of the known
      "After refit" clipping.
    - **Fix:** `ScrollBarAsNeeded`, a collapsible log, and wrapping rows.
      **M**

22. **In battle, every action is below the fold.** All 20 action buttons
    sit under the viewport even at 1560×1000, and the read text is cut off.
    **Fix:** pin the orders in a left column. **M**

23. **Every click rebuilds the whole screen and the log.**
    - **The log:** 63 ms per refresh even when nothing changed
      (`window._refresh_log`).
    - **Per click:** Port Buy takes 145 ms; a Tech tab takes 294–363 ms.
    - **Fix:** an incremental log, and update Tech cards in place as Pilot
      already does. **S / M**

24. **The Conn window re-simulates the flight inside `paintEvent`.**
    - **Where:** `viewport_hud.py:44-80` calls `preview.track` 7 times a
      beat.
    - **Cost:** 93 ms per 250 ms beat. Memoising per beat measured 44 ms.
    - **Fix:** compute once in `fly_beat`. **S**

25. **Much of the game can't be played by keyboard.**
    - `Card` is unfocusable, and it drives bodies, research, hulls and the
      new-game choices.
    - The star chart is mouse-only.
    - Focus jumps to the HUD after every action.
    - There are no accessible names, and there are 0 tooltips on the Port
      and Tech buttons.
    - **Fix:** focusable cards, a destination list beside the chart, and
      restoring focus by object name. **M**

26. **Visual fixes.**
    - **Flat buttons look disabled:** they use the same colours as disabled
      buttons (`theme.py:104-106`), and 88 buttons are flat, including
      Disengage and Brace.
    - **The HUD is too wide:** it needs at least 1,411 px against the 1,360
      px default, so captions overprint.
    - **Dark bands** show behind every label in a panel (`theme.py:70`
      paints `QWidget` with GROUND).
    - **Colour-only encodings:** under deuteranopia, log good vs bad falls to
      ΔE 12. Ground-map features share 6 colours with no legend.
    - **The Sector Chart:** its Fly buttons sit about 1,100 px below the
      chart.
    - **Effort:** S–M each.

27. **Pop-out windows are never freed.** None sets `WA_DeleteOnClose`, and
    each open leaks 12–88 widgets. **S**

28. **Game rules live in `ui/`.**
    - Rumour truth-seeding (`rumours_panel.py:24`).
    - Shore leave `advance_days(7)` and officer dismissal (`berths_panel`).
    - Research state writes (`tech_view`).
    - About 25 `add_log` calls for sim acts.
    - **Fix:** move each into `sim/`, returning `{ok, why, text}`. **M**

29. **The same thing is labelled differently on different screens.**
    - Three thrust pads with three layouts.
    - Reaction mass shown three ways ("48.0", "48.00 t", "48 t").
    - Identical "Computer" and "Autopilot" rows on the Pilot board.
    - "Kill relative motion" bypasses the one-clock door.
    - **Effort:** S–M.

---

## P2 — SEEDFALL engine code health

30. **Bridge input validation.**
    - **NaN:** `buy`/`sell` with NaN poisons credits and the save
      (`trade.py:63`, `protocol.py:222`).
    - **Negative indices** wrap to the last body or system.
    - **After death:** verbs still act.
    - **`jump`** drops its encounter.
    - **`remember text=null`** permanently breaks that person's `speak`.
    - **`shot`** writes to any path it is given (`attached.py:148`).
    - **Fix:** reject non-finite and out-of-range values at the protocol
      boundary. **S**

31. **The optional LLM path blocks the UI thread.** A dead endpoint freezes
    it for 12 s per call, with no backoff, and `complete()` raises on
    `{"response": null}`. **Fix:** catch everything, add a circuit breaker,
    and call it off the UI thread. **S–M**

32. **Imports and dead code.**
    - **Cycle:** `core/state.py` and `core/clock.py` import 29 sim modules,
      so core and sim import each other. 19 of those imports are otherwise
      dead but are what half-fills the save registry (#1), which is
      fragile.
    - **Re-entrancy:** add a guard in `advance_days` itself.
    - **`sim/xeno.py:136`:** its `__all__` names a missing `known`.
    - **pyflakes:** 284 findings (236 unused imports).
    - **Real test bugs:** `test_works3d.py:151/156` has a duplicate dict
      key, so one expectation is never checked, and `test_lighting.py:152`
      has an undefined name.
    - **Effort:** S.

33. **Broad `except` blocks.** Found in `sky.py:113,164,226`, `targets.py`,
    `clearance.py`, `control.py`, `comms.py`, `gatetraffic.py`, `orders.py`,
    `parley.py` and `lifespan.py`. None fired in play; today they only hide
    future bugs. Narrow them or log the first hit. **S**

34. **Performance is fine, with two cheap wins.** `tick_market` is 47% of
    tick time, and `exchequer.income` is recomputed 8 times a day (memoise
    it per day). The save is 180 KB at day 0 and 267 KB at year 7, with
    load and save ≤13 ms.

35. **Files at or over the 500-line limit.**
    - **Over:** `data/works3d.py` 635, `ui/viewport.py` 533, `map_view.py`
      526, `widgets.py` 512.
    - **At exactly 500:** `sim/expedition.py`, `sim/contracts.py` and
      `ui/window.py`. The rule says *under* 500, but `test_length` allows
      500.
    - **Long functions:** `clock._one_step` is 260 lines; split it into ship
      time and sector time.
    - **Seams, one line each:**
      - `works3d` → move `_keel.._gantry` to `works3d_parts`.
      - `viewport` → move the target and boom code out.
      - `map_view` → `StarChart` to `star_chart.py`.
      - `widgets` → `View` to `view_base.py`.
      - `window.go` → a nav table.
    - **Effort:** M total.
