# V44 Renderer

V44 is the scale-stationary fine-detail release. It extends V43's aspect-invariant population law so the same renderer remains usable when `main_scale` is substantially below 1.0, including the reported 1200×6248 and 1200×8046 canvases at `main_scale=0.35`.

## One population law, finer spatial resolution

`main_scale` still changes entity dimensions, not main-chip/prepared-population opportunities. Normalized population territory remains:

`T = (W × H) / min(W,H)^2`

Residual service/detail resolution follows the actual design unit. At scale `s`, component/local service-grid resolution increases by `1/s` per axis, and legitimate residual detail/work capacity scales with `D = T/s^2`.

Examples:

- 1200×1200 @ 1.0 → 56×56 service grid
- 1200×1200 @ 0.35 → 160×160
- 1200×6248 @ 1.0 → 56×292
- 1200×6248 @ 0.35 → 160×833
- 1200×8046 @ 0.35 → 160×1073

The main router's coarse congestion/coverage grids remain aspect-aware but scale-independent. Exact geometry, not those heuristic cells, determines legality.

## Performance corrections

V44 removes several costs that become pathological only when fine geometry creates hundreds of simultaneously legal route fronts and thousands of residual details:

- spatial singleton/forced-close connection pairing instead of all-pairs round scans;
- one global pathway-index rebuild after a batch of ready tracebacks rather than after every traceback;
- immutable-snapshot proposal/corridor caching where deterministic inputs are identical;
- incremental local untouched/retarget bookkeeping instead of reconstructing the whole fine service field per target;
- region-run caching and direct first-touch capture in late local completion instead of repeated whole-board set copies.
- final local visible-primitive admission checks stroke and source/terminal marker extent against the frozen static moat, closing marker-only clearance violations.
- main-network preflight intersection repair is causal per pair: repair the later offending trace first and never reroute both peers after one side has already succeeded.

These are execution optimizations only. Exact octilinear geometry, 0/±45-degree turns, clearances, component-first phase order, service targets, branching probabilities, and deterministic seeded generation remain normative.

## Fine-scale inherited-prefix correction

A recovery-fragment child owns visible geometry before its centerline contains two points. V43's early-return shortcut could therefore let its first gesture complete a forbidden repeated A→B→A→B weave in the inherited prefix. V44 validates the visible inherited lane from the child's first gesture onward; the final zigzag audit is unchanged.

## Runtime scaling

Fine scale intentionally creates much more real SVG detail: at `main_scale=0.35`, the design-area completion capacity is about 8.16× the scale-1 reference per normalized territory. V44 removes superlinear/global search defects, but full generation time still grows with the number of chips, component assemblies, and local traces actually emitted. Production acceptance therefore requires logical sample 0 to complete successfully; the renderer may not rely on cycling through rejected samples to appear supported.

## Usage

```bash
python pcb_v44_renderer.py --width 1200 --height 1200 --count 1 --out-dir output
python pcb_v44_renderer.py --width 1200 --height 6248 --main-scale 0.35 --count 1 --out-dir output
python pcb_v44_renderer.py --width 1200 --height 8046 --main-scale 0.35 --count 1 --out-dir output
```

## Verification

```bash
python run_release_tests.py
```

The authoritative active suite and committed acceptance reports are the release gate. Optional probes under `tests/stress/` are non-gating.
