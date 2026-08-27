# V45 Renderer Guide — True Zoom / Logical-Area Population

V45 corrects the meaning of `main_scale`.

## What `main_scale` means

`main_scale` is a zoom control over one continuous generative board, not an object-size-only multiplier. If the SVG dimensions stay fixed and `main_scale` becomes smaller, the renderer is viewing more logical board territory.

For width `W`, height `H`, and scale `m`:

```text
canvas_territory = (W*H) / min(W,H)^2
logical_area     = canvas_territory / m^2
```

Every complete logical territory contributes the same stationary population opportunities and the same local routing/component language. This is not tiling and there is no special portrait/landscape/fine-scale mode.

At `m=0.35`, a fixed canvas exposes approximately `8.163×` as much logical board area as at `m=1.0`.

## Consequences

- Main-chip count opportunity scales with logical area.
- Prepared component collections and isolated capacitors scale with logical area.
- Chip-to-chip clearance scales with the chip geometry; there is no raw-canvas moat floor that blocks fine-scale population.
- Main-router congestion/coverage grids and residual-service grids both refine in design-local units.
- Main routing retains the same deterministic/probabilistic, parallel transactional grammar and the same exact octilinear/clearance gates.
- Residual component fill remains a reaction to actual remaining gaps; it is no longer asked to compensate for missing primary population at fine scale.

## CLI

```bash
python pcb_v45_renderer.py --width 1200 --height 1200 --main-scale 0.35 --count 1 --out-dir v45_output
```

Useful options remain `--seed`, `--max-sample-restarts`, `--max-logical-samples`, `--collection-plan-attempts`, `--calibration-rounds`, `--pathway-debug-stage`, and `--no-skip-deadlocks`.

Same seed + same inputs remain deterministic.

## Validation

Run:

```bash
python run_release_tests.py
```

The release gate must pass all 73 active tests with zero failures/errors/skips/xfails.
