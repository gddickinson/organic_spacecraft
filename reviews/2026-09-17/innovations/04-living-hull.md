# Innovation 4 — The living hull (ship progression)

## Why

SEEDFALL's premise is a ship that was **grown rather than built**, but after
launch a grown hull changes only by refit, exactly like a welded one. The
GESTALT documents describe tissues that respond to load and environment:
- bone remodelling (Wolff's law);
- melanised, radiotrophic fungal rind;
- heat-shock proteins;
- the mineral gut that eats rock.

The game uses almost none of that after day 0. Ship progression today is
research plus refit; this adds a third axis that **only the grown families
have**, and it is a real reason to choose them over the Concordat's hulls.

## What the player gets

Grown, hybrid and xeno hulls **remember what you do with them**, and at
thresholds they **sprout an adaptation**: a small, permanent, biologically
grounded change with a benefit and a cost. You decide whether to let it set
in.

### Stress channels

Each channel is recorded on the Ship where the act happens:

| Channel | Recorded by | Unit |
|---|---|---|
| `impact` | damage taken, per layer (`sim/damage.py`) | hp absorbed |
| `heat` | cooking over the cap (`ship.cool` result in `core/clock`) | heat-days |
| `crossing` | light-years jumped (`actions.jump_to`) | ly |
| `dark` | days at a dim star (`system.heat` < 0.25) or a sunless body | days |
| `glare` | days at a hot star (`system.heat` ≥ 0.9; the Cradle later) | days |
| `gut` | tonnes mined or extracted | t |
| `eyes` | survey acts | count |
| `depth` | atmosphere or ocean dives | count |
| `burn` | hard-burn crossings | count |

### Adaptations

About 16, in `data/adaptations.py`. Each has:
- a trigger channel and threshold;
- `fx`, as Stats keys the ship pipeline already reads;
- a cost, which is also `fx` (e.g. mass up, speed down, conceal down);
- a GESTALT-grounded paragraph;
- the families it can occur in.

Examples:
- **Callused rind** (impact): armour +8%, speed −3%.
- **Scar lattice** (impact, high): regen +25%, evade −4%.
- **Radiator fronds** (heat): vent +20%, conceal −0.1 ("they glow").
- **Heat-shock chaperones** (heat, high): heat_cap +15%.
- **Long-haul metabolism** (crossing): jump +0.4 ly, morale −0.02.
- **Melanised rind** (dark): o2_days +30%, and a radiation-dose multiplier ×0.8 for the Cradle later.
- **Night-adapted eyes** (dark): sensor +12% in dim systems.
- **Mineral gut hypertrophy** (gut): mine +15%, phos +10%, cargo −3%.
- **Acute opsins** (eyes): scan +0.05.
- **Pressure bone** (depth): dive safety up, armour +3%, mass +2%.
- **Motile trim** (burn): speed +5%, heat_cap −5%.
- **Glare mantle** (glare): shields crew dose ×0.75.

### Encourage or suppress

When a channel crosses a threshold, an adaptation **emerges**, shown on the
Ship screen with both paths costed:
- **Encourage.** It sets in over about 20 days and costs growth material
  (phosphate and biomass, drawn through the one `sim/stores` door once stream
  A's `sim/stores.py` exists; until then the existing spend helper). "The
  body is grown by eating the rock."
- **Suppress.** It fades, and the channel is drawn down so it doesn't
  immediately re-emerge.
- **Ignored**, it sets in by itself after 60 days. The organism doesn't wait
  for permission, and that is the point.

### Genome budget and pruning

- **Budget.** A hull keeps at most N adaptations, from its class size: SPORE
  1, NAVIS 3, large classes 4, LEVIATHAN 5. Hybrids adapt at half rate with
  budget N−1. Xeno hulls adapt at 1.5× rate but draw their adaptation at
  random from the eligible set.
- **Pruning.** At a Fleet Hub (the `gestation` service), a surgeon can
  **prune** an established adaptation for credits plus days.
- **Fabricated and synthetic hulls never adapt.** Say so on their Ship
  screen, as a trait of the family.

## Design

- **State:** `Ship.stress: dict = {}`, `Ship.adaptations: list = []` (ids),
  and `Ship.emerging: dict | None = None` (`id`, `since_day`). All are
  defaulted fields, so old saves load.
- **Content:** `data/adaptations.py` holds the table and thresholds.
- **Rules:** `sim/adaptation.py` holds `record(ship, channel, amount)`,
  `tick(game, n)` (emergence, setting in, auto-set after 60 days),
  `encourage/suppress/prune` with previews, and `fx(ship)`.
- **Stats:** `sim/ship.stats()` adds `adaptation.fx(ship)` the same way it
  adds part `fx`. Keep the arithmetic in one place; a percentage fx multiplies
  the computed stat, an absolute fx adds.
- **Recording sites:** add one line at each place in the table above. Use a
  helper so a missing ship is harmless (enemy hulls may record too; that is
  fine, it's their body).
- **Clock:** `adaptation.tick(game, ship_n)` in **ship time**, because
  biology runs on the crew's clock. It returns log tuples.
- **Fleet:** consort hulls accumulate stress too. Keep it simple: only hulls
  that actually do the act record it.

## UI

A new "Body" panel on the Ship screen (`ui/ship_view.py`, or a new
`ui/body_panel.py` hosted there):
- the channels as bars toward their next threshold;
- the emerging adaptation with Encourage and Suppress, costs stated;
- established adaptations with their fx and a Prune button (enabled only at a
  Fleet Hub, with the cost stated).

The ship picture (`plans_panel` / `ui/plans`) can tint or mark adapted
layers; optional, and only if cheap. Add a Codex/Help topic on adaptation.

## Balance targets

- A normal career sees its first emergence between day 60 and day 250, and
  3–6 over five years.
- No single adaptation is worth more than about a tier-2 fitting.
- Effects are small and their costs real, so a player who suppresses
  everything is not badly behind.

## Tests (new suite `test_adaptation`)

- Each channel accumulates from its real act (drive the act, not the
  recorder).
- Crossing a threshold makes an emergence.
- Encourage costs exactly what the preview said and sets in on the stated
  day.
- Every adaptation's fx reaches `ship_stats`: efficacy, switched off, the
  number moves.
- Fabricated and synthetic hulls never emerge anything.
- The budget caps the count, and pruning equals its preview.
- Auto-setting after 60 days.
- Cross-process save.
- The pieces of ship progression (research, refit, adaptation) stack without
  overflow; clamp where a stat has a hard range.
