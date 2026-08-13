# V35 deterministic renderer

## Authority

`chip_design_language_v35_variance_driven.md` is the single cumulative active design specification.
Historical changelog and verification files remain immutable release records.

## Generation order

V35 preserves route-first generation:

1. place main chips;
2. route the complete main-chip network against chips only;
3. route independent local gap fillers against the frozen main network;
4. freeze all pathways;
5. place components into the remaining residual field.

Secondary components never participate in main/local routing and component failure can never trigger a pathway reroute.

## Scale and chip population

The V35 default has no extra scale multiplier:

```text
S_canvas = min(width, height)
S        = S_canvas * main_scale
U        = S / 1600
```

At 1200×1200 and `--main-scale 1.0`, `S=1200` and `U=0.75`.

Main-chip population is determined by **actual canvas area**, not `main_scale`:

```text
p(3 chips) = 0.10 * clamp((W*H)/(1200*1200) - 1, 0, 1)
```

Therefore a default 1200×1200 board always has exactly **two** main chips. Making the design smaller on that same canvas does not create another chip.

Main-chip pair clearance is `max(430U, 0.265*S_canvas)`; on the default square this is 322.5 canvas units.

## Main routing and causal recovery

V35 retains V34's transactional-parallel, local-space-aware main router. Candidate gestures are ranked by bounded local free-space/corridor capacity while exact geometry is the final legality gate.

Deadlock recovery can rewind multiple committed gestures. The failed corridor recorded at rollback is the historical direction that actually left the rollback junction, not merely the direction at the dead head. That replay corridor is suppressed while alternate legal 0/±45° corridors are reconsidered. If useful local space exists, hard-stop termination is deferred for bounded recovery.

Main-lane materialization is preflighted before local/component fill. A physical offset lane that would otherwise be suppressed for an illegal zigzag/intersection is causally reopened and regrown. If a shared-prefix child has no legal alternate local tail after genuine rollback/regrowth, but its inherited physical prefix is already long and grammar-clean, V35 may terminate that lane at the last valid prefix checkpoint instead of deleting the lane or discarding the entire board. Failed repair attempts restore their original state exactly.

Head-to-head connections use the same visible 0/±45° grammar. A singleton that still carries a non-zero bundle offset is first rebased to its exact rendered head before the connection leg is committed, preventing double-offset terminal kinks.

## Hard pathway grammar

All visible pathway bodies are straight-segment polylines. Consecutive segment headings may change only by 0 or ±45°.

Hard failures include:
- direct 90° pathway turns;
- quadratic/Bézier/curved pathway bodies;
- unauthorized pathway intersections or unmarked overlaps;
- missing visible main launch lanes.

Round terminal styling remains allowed and does not make the pathway body curved.

## Honest local gap fill

The residual routing field uses a 56×56 connected-space analysis. Local fillers are born independently; compatible fillers can still temporarily bundle with the existing deterministic 50% encounter probability and later separate again.

The board-level local target is `Uniform(0.40, 0.43)`. This is **not** a requirement to touch every pocket.

Coverage is counted only from geometry that will actually render:
- visible local trace stroke;
- plus its legitimate allocated line-spacing/exclusion perimeter;
- unioned with a deterministic 4×4 subcell occupancy mask per residual cell.

Abandoned/pruned lines contribute neither coverage nor collision occupancy. The old inflated invisible service halo is gone.

Local-to-local spacing is thickness-aware, with an edge gap of approximately 1.5× adjacent mean trace thickness and never below the ordinary inter-route keepout. Components later preserve `component_pathway_clearance` from local lines exactly as they do from main lines.

Organic synchronous local waves handle the authored/branching/bundling behavior. A bounded exact mop-up then targets long still-unserved straight/diagonal runs in substantial residual rooms. Thin, triangular, isolated or otherwise awkward pockets may remain negative space.

## Residual components

After routes freeze, components analyze a separate 56×56 connected residual field.

V35 distinguishes:
- **substantial/mandatory regions**, which are plausibly fillable by ordinary component geometry;
- **optional thin/sliver regions**, which may remain empty or receive micro fillers when exact clearance permits.

The seeded component target remains `Uniform(0.90, 0.94)`, but it applies to meaningful residual capacity rather than literal sliver packing. Acceptance uses the minimum of:
1. substantial-region area representation; and
2. area-weighted size×quantity capacity satisfaction.

Large rooms therefore require more component-capacity units than small rooms. Larger components contribute more capacity, but one token object cannot satisfy an arbitrarily large room. Component families include large, medium, small and optional micro gap fillers. Oversized collection instances may receive a bounded deterministic 90%→80%→75% gap-adaptation scale-down before exact rechecking. Source collection scale/quota language is validated before routing; this explicit per-gap adaptation is therefore not allowed to trigger an expensive late collection-scale rejection after a board has already been routed.

Exact chip/path/component clearances remain authoritative. Optional micro components get no spacing exemption.

## Runtime architecture

Dense component placement uses spatial broad-phase indexing for accepted components and for individually buffered nearby pathway groups. Exact collision checks are still performed, but V35 avoids topology-unioning the entire dense board for every candidate.

Local service accounting uses deterministic raster occupancy instead of repeatedly building large polygon unions. These are performance changes only; they do not widen service/clearance definitions.

## Generate

```bash
python pcb_v35_renderer.py --count 1 --out-dir output
python pcb_v35_renderer.py --seed 12345 --count 5 --out-dir output
python pcb_v35_renderer.py --seed 12345 --main-scale 0.80 --out-dir output_small
```

`--seed` is optional; without it a fresh 64-bit seed is generated.

Runtime/debug flags remain:

```text
--width
--height
--seed
--count
--main-scale
--out-dir
--max-sample-restarts
--max-logical-samples
--collection-plan-attempts
--calibration-rounds
--pathway-debug-stage corridors
--no-skip-deadlocks
```

Normal rendering should leave `--no-skip-deadlocks` off.

## Requirements

- Python 3.10+
- Shapely 2.x (`pip install shapely>=2.1`)

## Tests

```bash
python -m unittest test_pcb_v35_renderer.py
```

The V35 verification summary records the targeted release gates actually completed for this release; it does not claim the entire legacy aggregate if that aggregate was not run to completion.
