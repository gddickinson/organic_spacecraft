# Innovation 8 — Officer arcs: what changed

Spec: `reviews/2026-09-17/innovations/08-officer-arcs.md`. This note stands in
for the edits to `seedfall/INTERFACE.md`, `IMPROVEMENTS.md`, `README.md` and
`SESSION_LOG.md`, none of which were touched.

## New modules

| File | Lines | What it holds |
|---|---|---|
| `data/arc_types.py` | ~100 | `Choice`, `Beat`, `Signature`, `Arc`; `TRIGGERS` (date, place, loyalty, event), `EVENTS` (fight, burn, colony), `PLACES` (the place rules the prose may name); `choice()` |
| `data/arcs.py` | ~430 | The calendar (`QUIET_DAYS` 45, `GAP_MIN/MAX` 50–120, `ANSWER_DAYS` 60, `PLACE_DAYS` 300, `EVENT_DAYS` 365, `LOYALTY_DAYS` 240, `LOYAL_AT` 75, `LAPSE_FIRST/SECOND/LAST` 4/6/14, `RACE_DAYS` 45, `QUIET_CHAPTER`), each signature's number, `SIGNATURES` (12, each naming where it is read), the first six arcs, `ARCS`, `ARCS_BY_ID` |
| `data/arcs_late.py` | ~230 | The other six arcs (split at the length rule; imports only the shapes) |
| `sim/arcs.py` | ~475 | The door: `planned` (pure), `assign`, `tick` (one line in sector time), the beat state machine (scheduled → armed → open), lapses, `preview`, `answered` (called by `comms.answer`), `witness`, `signature_effects`, `comprehension`, `status`, `record`, **`progress`** |
| `sim/arc_beats.py` | ~210 | A beat's words in the officer's register (`data/personas`: officer, or the Choir's plural for a `dry` lineage), its slots (place, hull, a rival, the Assembly's seat, the Cradle's song, the previous answer), and `preview`/`perform` of a choice — the same numbers, clamps included |
| `sim/arc_places.py` | ~200 | Place rules resolved when a beat arms: nearest reachable Bloom-held system (or the reachable edge of Bloom country), Freehold capital/port, Choir port, Charter capital, Yards port, a moon, a wreck (a portless system), a race finish 1.2–2.6 jumps out; the deep anchors; region entries (a marker while unopened). `beyond`, `waiting_for`, a memo of reachability |
| `ui/arc_panel.py` | ~130 | The Ship screen's **Crew** tab, a beat's costed answers on the Despatches board, and the Codex's **The crew** page |
| `tests/test_arcs.py` | ~330 | Suite `arcs` (15 checks with `arcs_screens`) |
| `tests/arcs_screens.py` | ~220 | Cross-process save, old save, and four Qt checks, run by `test_arcs` |
| `tests/arc_captain.py` | ~190 | The scripted captain that engages every beat (flies there, fights, burns, plants, buys a round, opens a rim, answers) |
| `tests/arc_probes.py` | ~210 | One efficacy probe per signature (`PROBES`; a signature without one fails at import) |

## Saved state

- `Officer.arc: str | None = None`, `arc_beat: int = 0`, `arc_state: dict = {}`, `signature: str | None = None` — appended at the end of `sim/crew.Officer`, under a comment.
- `Game.flags["arcs"]`: `{fights, record, answered, lapsed, opened}` — what outlives an officer (the Codex's record, the renown counters). **No `Game` field was added**; `core/state.py` is untouched.
- Old saves load: the four fields default, and the first tick deals each officer the arc `arcs.planned` shows (their own key, `{seed}:arc:{officer.id}`), so the crew tab shows it even before that tick.

## The arcs

| Arc | Beat 1 | Beat 2 | Beat 3 | Signature (read at) |
|---|---|---|---|---|
| The last signal | date | place: Bloom | event: burn | Kessel-steady — burn cut ×1.20 (`threat.cleanse`) |
| Old debts | date | place: Freehold capital | date | Paid in full — Freeholds ≥ 15 (`arcs.tick`) |
| The defector | date | place: Choir port | loyalty | Second mind — +1 decoding try (`minigames.begin_decoding`), scan +0.08 (`ship.stats`) |
| The disgraced scientist | date | place: Charter capital | date | Peer reviewed — confirm days ÷1.3 (`inquiry.confirm_cost`) |
| The deserter | date | place: Yards port | event: fight | Drill — unattended helm ×1.10 (`stations.helm_share`) |
| The grower | date | place: a moon | event: colony | Green thumb — holding yields ×1.08 (`works.crewed_yields`) |
| The cartographer | date | place: Hollow anchor | place: in the Hollow | Dead reckoning — jump +0.5 ly (`ship.stats`), the Hollow charted free |
| The pilgrim | date | place: Cradle anchor | place: in the Cradle | Light-tongued — diplomacy +0.08 (`ship.stats`), Kith +25% (`arcs.comprehension`) |
| The widow | date | place: a wreck | loyalty | Remembered — morale ≥ 0.45 (`arcs.tick`) |
| The gambler | date | place: Freehold port | place: a race (45 days) | Lucky — 25% reroll of a failed ground attempt (`expedition.attempt`/`odds_for`) |
| The heretic | date | place: Bloom | place: Charter capital | Unafraid — study ×1.30 (`responses.study_value`) |
| The heir | date | place: Freehold port | date | Landed — ₡250/month from the Freeholds' purse (`arcs.tick`), or given away: Freeholds +20 once |

Every choice's credits, standing, cargo and loyalty are in the table; a gain
is paid out of a named power's purse (nothing conjured). The rival (`sim/nemeses`),
the Assembly's seat (`sim/assembly`) and the Kith (`getattr(game, "kith")`)
are read defensively.

## For other innovations

- **Renown (9):** `arcs.progress(game) -> {assigned, beats_done, finished, signatures}`.
- **Kith (2):** multiply comprehension by `1 + arcs.comprehension(game)` (0.25 with Light-tongued aboard and `game.kith` set; 0 otherwise). The pilgrim's last beat says the Kith are singing when `game.kith` is not None.

## Suite `arcs` (15 checks)

1. every arc seen through from each of the 3 opening officers (36 runs) by the scripted captain, with its signature; the Hollow charted by Dead reckoning;
2. each trigger kind fires (date, place, loyalty, fight, burn, colony) and none before its condition;
3. every one of the 82 answers does what its preview said (credits, standing, goods, the officer's loyalty, the purse, the signature); an unaffordable one is refused and changes nothing;
4. lapses cost 4/6/14 exactly, on day `until + 1` not `until`; a lapsed last beat takes a restless officer below the line and `loyalty.tick` walks them out (arcs removes nobody);
5. every signature moves its number (14 probes), with the Lucky odds rolled against the quote;
6. dealing is the officer's key; looking (`status`, `planned`, `preview`, …) changes nothing;
7. nothing arms before day 45 or during the tutorial's first chapters;
8. a beat past an unopened rim waits 600 days without lapsing, says what opens it, and opens once there;
9. ignoring every story for three years costs some loyalty and nobody walks out;
10. a save mid-story answered through `answer_signal` in a fresh process equals this process;
11. an officer from a pre-arcs save is dealt the same story twice;
12–15. Qt: the Crew tab at 1040×680 and 1360×880 (and opening it changes nothing), all 36 beats on the Despatches board answered by their own buttons, an unaffordable answer greyed with its reason, the Codex's crew page.

## Shared and other-owned files touched (one line per hunk)

- `sim/crew.py`: four defaulted `Officer` fields appended, under a comment.
- `core/sectortime.py`: import; `arcs_sim.tick(game, n, r)` after `nemeses_sim.tick` in `reckoning` (draws nothing from `r`).
- `sim/comms.py`: `answer` asks `arcs.answered` for an `arc:` sender before marking it answered.
- `sim/aftermath.py`: import; `arcs.witness(game, "fight")` after `rival_ends.settle`.
- `sim/ship.py`: signature effects merged into `tr` after `trait_effects`; `+ tr.get("jump", 0.0)` in the jump line.
- `sim/threat.py`: `cleanse` multiplies the cut by `1 + burn` after the draw.
- `sim/minigames.py`: `begin_decoding` adds the `decode` tries.
- `sim/inquiry.py`: `confirm_cost(res, tech_id, officers=())` divides by `1 + confirm`; `begin_confirming` passes `game.officers`.
- `sim/stations.py`: new `helm_share(officers, nav)`; `run_helm` and `seat_value` call it.
- `sim/works.py`: `crewed_yields` multiplies by `1 + yield`.
- `sim/responses.py`: `study_value` multiplies xenolith and readings by `1 + study`.
- `sim/expedition.py`: `odds_for` quotes the reroll; new `_luck`; `attempt` rerolls a failure (drawn only when owed).
- `ui/despatch_view.py`: import; an `arc:` despatch is drawn by `arc_panel.beat`.
- `ui/ship_view.py`: import; a "Crew" tab hosting `arc_panel.crew`.
- `ui/codex_view.py`: import; a "The crew" tab hosting `arc_panel.codex`.
- `ui/inquiry_panel.py`: `confirm_cost` passed `game.officers`.
- `data/help_more.py`: topic `arcs` appended.
- `tests/suites.py`: row `arcs` appended. `tests/tripwire_kin.py`: rows `arcs`, `arc_places`.

## Deviations

- **Places are chosen when a beat arms, not when the arc is dealt**, from the galaxy as it then is (the nearest Bloom mass on day one is often gone by beat 2). Deterministic all the same.
- **A place out of the drive's reach waits without lapsing** (as the spec asks for the Reaches), and says a longer jump would open the way; the Bloom rule prefers the reachable edge of Bloom country when every mass is walled off.
- **Light-tongued's comms bonus is always on**: `ship.stats` has no game to ask whether the Kith exist. The Kith lift is 0 without them.
- **Paid in full and Remembered are daily floors** (`arcs.tick`), like the Assembly's Choir floor, not clamps inside `adjust_rep`/`morale_tick`; they take hold the day after the signature, so an answer does exactly what its preview said.
- **Arc bookkeeping lives in `game.flags["arcs"]`**, not a new `Game` field.
- `LOYAL_AT` is 75, not just under "Willing": a bridge paid on time settles in the high eighties.

## Measurements

- **Scripted captain** (`tests/arc_captain.py`, engages every beat): 36 of 36 (12 arcs × 3 opening officers) finished with their signature; the longest ended on day 306.
- **Strategy bots, 3 years × seeds verge-7, s5, alpha-1** (trader, explorer, fighter, colonist; scratch `scratch-arcs/campaign/arcrun.py`, modes off / ignored / engaged):
  - *Ignored:* 4.75 beats opened per run and 7.2 lapsed (a place or event beat that never came lapses too); 0 answered.
  - *Loyalty, ignored vs off:* −2.4 mean over the 11 runs that ended the same way (−4.3 to +3.3). Starting officers who walked out: the same in 12 of 12 pairs.
  - *Engaged* (answers every beat, flies to reachable places, seeks a fight, buys a round): of 21 officers who stayed, 8 got a signature, 8 reached the end without one (their event beat — a burn, a fight, a holding — never came for that bot), and 5 were waiting on a place beyond the drive (mostly the Hollow's gate). So 16 of 21 reached the end of the story. The explorer, the one strategy with a healthy economy in every mode: 3 signatures, 4 ended without, 2 waiting.
- **Cost:** 0.92 ms a day with arcs against 0.90 without (two idle years); reachability is memoised.
- **Signature probes** (off → on): burn cut 0.529 → 0.634; Freeholds held at −40 → 15; decoding tries 8 → 10 (the scan lift crosses the sensor bonus too); scan 0.53 → 0.61; days to confirm 352 → 271; unattended helm 0.70 → 0.77; holding yield 2.71 → 2.93; jump 8.88 → 9.41 ly; diplomacy 0.04 → 0.12; Kith 0 → 0.25; morale floor 0.20 → 0.45; ground odds 0.667 → 0.722 (rolled 0.669 / 0.714); study xenolith 2.26 → 2.94; Landed ₡0 → ₡250 a month, out of the Freeholds' purse.
