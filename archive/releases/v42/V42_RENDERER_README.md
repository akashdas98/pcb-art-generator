# V42 Renderer

V42 is a tall-canvas scaling/performance release built on V41. It keeps the established PCB design language intact while removing square-canvas assumptions and superlinear searches from the local residual-fill phase.

## What changed

### Local service cells remain physically local

V41 used a fixed 56×56 local residual grid. On a 1200×8046 canvas that stretched each cell to roughly 21×144 units, so the local-service estimator no longer represented a local neighborhood.

V42 keeps the short axis at 56 cells and scales the long-axis cell count with aspect ratio. Examples:

- 1200×1200 → 56×56
- 1200×6248 → 56×292
- 1200×8046 → 56×375

This applies to local residual bookkeeping/routing only. The component grid remains 56×56 so aspect ratio does not create a new component-density policy.

### Search work is localized

Where V41 repeatedly scanned distant geometry that could not affect a capped local score, V42 uses the existing spatial index / nearest-neighbor broad phase to identify only potentially relevant geometry before running the same exact Shapely checks.

The component residual candidate selector also avoids repeatedly sorting the entire field when only the best small candidate set is needed.

### Tall late-stage completion remains the same design language

The target is still 80–90% of the post-component remainder. V42 does not lower that target and does not permit illegal lines to reach it. Tall boards receive bounded additional local work; once the efficient articulated cleanup reaches diminishing returns, any remaining deficit is returned to the ordinary local router for additional waves.

All local line turns remain 0/±45 degrees, all exact rendered clearance checks remain in force, and component-first service remains 50–60%.

## Usage

```bash
python pcb_v42_renderer.py --width 1200 --height 1200 --count 1 --out-dir output
python pcb_v42_renderer.py --width 1200 --height 6248 --count 1 --out-dir output
python pcb_v42_renderer.py --width 1200 --height 8046 --count 1 --out-dir output
```

## Verification

```bash
python run_release_tests.py
```

The active V42 gate contains 47 tests. Optional additional probes are under `tests/stress/` and are not release gates.
