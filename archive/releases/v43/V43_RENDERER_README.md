# V43 Renderer

V43 is the aspect-invariant spatial-population release. It fixes the V42 architectural defect where extended canvases received a square-board-sized main/component population inside a much larger coordinate frame.

## One generative law for every canvas shape

V43 separates **entity scale** from **population extent**:

- chip/component/trace dimensions continue to derive from the short-side design basis and `main_scale`;
- population opportunities derive from normalized physical territory
  `T = (W × H) / min(W,H)^2`;
- swapping width and height preserves the population law and transposes the physical service grids;
- there is no tall, wide, or square visual mode.

A 1200×6248 canvas therefore contains about 5.21 square-reference territories and receives proportionally more main-chip anchors, prepared collections, isolated components, residual completion opportunities, and routing work across the full canvas. It is not tiled; all placement remains globally seeded and clearance-aware.

## Physical residual grids

Both component and local residual grids preserve approximately the square-reference cell size. Examples:

- 1200×1200 → 56×56
- 1200×6248 → 56×292
- 6248×1200 → 292×56
- 1200×8046 → 56×375

The 50–60% component service and 80–90% local service-of-remainder contracts therefore measure the full physical board rather than stretched giant cells.

## Routing and geometry are unchanged in meaning

V43 retains the existing exact octilinear grammar, 0/±45-degree turn rule, component/chip/pathway clearances, transactional-parallel main routing, component-first phase order, bent-dominant local completion, source dots, deterministic seeding, and final rendered audits.

Spatial hashes / STRtrees and same-snapshot legality caching are broad-phase performance tools only. Every potentially relevant pair still reaches the same exact geometry rule. Local routing additionally indexes the exact rendered frozen-main polylines so mitered main-trace joints cannot create a clearance blind spot.

## Usage

```bash
python pcb_v43_renderer.py --width 1200 --height 1200 --count 1 --out-dir output
python pcb_v43_renderer.py --width 1200 --height 6248 --count 1 --out-dir output
python pcb_v43_renderer.py --width 6248 --height 1200 --count 1 --out-dir output
python pcb_v43_renderer.py --width 1200 --height 8046 --count 1 --out-dir output
```

## Verification

```bash
python run_release_tests.py
```

The active V43 gate contains 63 mandatory tests. Optional probes under `tests/stress/` are non-gating.
