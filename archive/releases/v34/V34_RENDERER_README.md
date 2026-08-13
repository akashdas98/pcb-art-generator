# V34 deterministic renderer

## Authority

`chip_design_language_v34_variance_driven.md` is the single cumulative active design specification.
Historical changelog and verification files remain records of their original releases and are not rewritten.

## V34 architecture

Generation remains hierarchical:

1. place main chips;
2. route the complete main network against chips only;
3. route independent, region-aware local gap fillers against the frozen main network;
4. freeze all pathways;
5. place region-aware components into the remaining field.

Secondary components never exist spatially during pathway routing and can never cause a reroute.

### Whole-design default scale

V34 changes the default physical scale from the old canvas/1200 basis to canvas/1600 while preserving the chip-count distribution.

```text
S_canvas = min(width, height)
S_design = S_canvas * main_scale * 0.75
U        = S_canvas * main_scale / 1600
```

Thus on a 1200×1200 canvas with `--main-scale 1.0`, `S_design=900` and `U=0.75`.
The chip-count rule remains exactly 90% two chips / 10% three chips.

### Main-chip spacing

Main-chip pair clearance is `max(360U, 0.205*S_canvas)`. At the default 1200 square this is 270 canvas units. This routing moat deliberately does not shrink with the smaller design scale.

### Local-space-aware causal routing

V34 retains transactional-parallel rounds. It additionally ranks bounded candidate corridors using a maintained local congestion/free-space field, while exact geometry remains the final legality test.

Deadlock recovery is causal: recent committed gestures may be removed, the direction that actually left the rollback junction into the failed corridor is recorded as the replay direction, and recovery considers different legal ±45° corridors before replay. Foreign causal blockers have a separate bounded yield allowance. If usable local space exists, hard-stop/journey/round-limit termination may be deferred for a local replan.

A fail-fast main-only materialization preflight runs before local/component filling. If a physical offset lane would later be suppressed for a zigzag/intersection, its owning leaf is reopened, rolled back and locally regrown. If the bounded causal repair fails, the logical sample is rejected before filler work.

### Hard pathway grammar

Pathway bodies are SVG polylines made only from straight segments. Consecutive headings may change by 0 or ±45 degrees. Direct 90-degree bends and quadratic/Bézier pathway primitives are hard failures. Miter joins are used for route bends; round caps are terminal styling only.

### Local-gap lines

The post-main residual field is analyzed as connected regions on a 28×28 grid. Ordinary local fillers are born independently as singleton lines. Region size, unmet area, local orientation and capacity determine source allocation, line lifetime and target selection. The internal seeded target is 42–50%, with accepted visible local influence coverage required to remain about 40% or higher.

Compatible local lines in the same region have a deterministic 50% chance to align temporarily for 2–4 atomic rounds, at most once per line, then separate and resume independent gap seeking. The 3–5× local branching boost and 50% local frame-exit factor remain active.

### Components

After all pathways freeze, components use a separate connected 28×28 residual-region analysis. Established collections are fitted into suitably large rooms first; bounded gap-sized capacitors/dots/dashes/squares/circles serve smaller unfilled pockets. Accepted visual-service coverage is at least 90%, with a seeded 90–94% target. Unauthorized component/pathway contact is a hard failure except the explicit terminal attachment.

## Generate

```bash
python pcb_v34_renderer.py --count 1 --out-dir output
python pcb_v34_renderer.py --seed 12345 --count 5 --out-dir output
python pcb_v34_renderer.py --seed 12345 --main-scale 0.80 --out-dir output_small
```

`--seed` is optional; when omitted a fresh 64-bit cryptographic seed is generated.

Useful runtime/debug flags remain:

```bash
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

Normal rendering should leave `--no-skip-deadlocks` off. Default batch behavior gives a logical sample one full-board attempt, then deterministically skips a pathological topology rather than multiplying expensive full reroutes.

## Requirements

- Python 3.10+
- Shapely 2.x (`pip install shapely>=2.1`)

## Tests

```bash
python -m unittest test_pcb_v34_renderer.py
```

The verification summary records the targeted V34 regression gates used for release.
