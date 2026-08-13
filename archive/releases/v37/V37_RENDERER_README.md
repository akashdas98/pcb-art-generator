# V37 deterministic renderer

## Authority

`chip_design_language_v37_variance_driven.md` is the single cumulative active design specification.
Historical changelog and verification files remain immutable release records.

## Generation order

V37 uses a main-route-first, component-first residual architecture:

1. place main chips;
2. route and freeze the complete main-chip network against chips only;
3. place gap-aware components into the post-main residual field to a seeded **50–60%** service target;
4. freeze components;
5. route local gap fillers through the actual post-component free field to **80–90% of the remaining service budget**;
6. run final exact geometry/clearance audits.

Components never influence main-chip routing. They intentionally influence the later local-gap phase because they
are already physical board objects by then. Local failure never reroutes main pathways or moves components.

## Scale and chip population

```text
S_canvas = min(width, height)
S        = S_canvas * main_scale
U        = S / 1600
```

There is no extra 0.75 multiplier. At 1200×1200 and `--main-scale 1.0`, `U=0.75`.

Main-chip population remains based on actual canvas area, not `main_scale`:

```text
p(3 chips) = 0.10 * clamp((W*H)/(1200*1200) - 1, 0, 1)
```

Therefore the default 1200×1200 canvas always has exactly two main chips.

## Main routing

V37 preserves V35's transactional-parallel, local-space-aware main router and genuine causal traceback/re-route.
Main lanes preflight their real materialized geometry before either residual phase. Deadlock recovery may rewind
committed history, suppress the failed replay corridor, and regrow through a materially different local corridor.
Full main-lane survival, side progress, cross-chip connection, and source-egress invariants remain hard.

## Hard pathway grammar

Visible pathway bodies are straight-segment polylines only. Consecutive headings may change only by 0 or ±45°.
Direct 90° turns, curved pathway bodies, unauthorized intersections/overlaps, or missing visible main lanes reject
the logical sample.

## First residual phase: components 50–60%

After the main network freezes, V37 runs the V35 connected residual-region component allocator with a seeded
`Uniform(0.50, 0.60)` service target.

The allocator remains local-gap-aware:
- small usable gaps prefer small components;
- medium gaps prefer medium components;
- large rooms require larger components and/or multiple capacity units;
- optional thin/sliver pockets may receive micro components when exact clearance fits, or remain negative space;
- one tiny component cannot satisfy a huge room.

Exact chip/main-path/component/component/edge clearances remain authoritative. Accepted components are frozen
before local routing starts.


## Coherent residual-component language

V37 keeps the 50–60% component target but changes how residual completion is realized. Prepared full collections remain first. If more component capacity is required, medium/large connected rooms receive compound assemblies built from the same IC/dense/ordinary/capacitor collection grammar, usually with an outer border. Standalone dot/dash/square/circle tokens are restricted to genuinely micro connected pockets and capped at eight per sample. A locally narrow candidate point may reject a compound assembly, but may not crush it below 72% of its generated residual-instance scale.

This prevents residual-service accounting from turning open rooms into fields of disconnected glyphs. Small rooms may still receive appropriately small coherent entities such as capacitors.

## Second residual phase: local lines 80–90% of remaining

Let `C` be the actual component service fraction. V37 samples `L` from `Uniform(0.80,0.90)` and sets:

```text
remaining_service = 1 - C
absolute_local_target = remaining_service * L
reported_local_fraction = actual_absolute_local_service / remaining_service
```

This keeps the accounting consistent with the component capacity metric while the geometry remains literal: local
lines route only through actual post-component free space and see both frozen main traces and components as obstacles.

Local behavior is otherwise preserved from V35: independent births, deterministic 50% temporary compatible-line
bundling, later release, elevated branching, region-aware source count/length, reduced frame exit, and honest visible
stroke + legitimate spacing-perimeter service. V37 uses three organic synchronous waves, then the existing bounded
space-aware straight/diagonal mop-up to finish the remaining measured obligation without dense peer-simulation tails.

Local lines preserve their normal line-to-line/main-line moat and the full component-pathway moat. If a terminal
dot would intrude into a component moat, the terminal can back off anywhere along its already legal path while
preserving the minimum visible trace length. If no legal marker position exists, that optional local filler is pruned;
the route body is never bent into an illegal corner and component clearance is never weakened.

The unfilled 10–20% of the remaining service budget—and awkward geometric slivers—may remain intentional negative space.

## Runtime architecture

Main routing and local routing are separate planner phases. The local planner preloads the frozen main network and
uses a spatial broad phase for component obstacles, so candidate gestures exact-check only nearby components.
Component placement likewise uses spatial indexing. These are performance optimizations only; exact geometry is
still the final legality gate.

## Generate

```bash
python pcb_v37_renderer.py --count 1 --out-dir output
python pcb_v37_renderer.py --seed 12345 --count 5 --out-dir output
python pcb_v37_renderer.py --seed 12345 --main-scale 0.80 --out-dir output_small
```

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
python -m unittest test_pcb_v37_renderer.py
```

`V37_VERIFICATION_SUMMARY.md` records the targeted release gates actually completed.
