# V44 — Scale-Stationary Fine Detail and Bounded Performance

## Problem

V43 fixed long/wide population at `main_scale=1.0`, but the residual service resolution and several execution budgets still assumed the default feature scale. At `main_scale=0.35`, the same tall canvases could spend tens of minutes rejecting all default logical samples instead of emitting an SVG.

## Root causes

1. component/local service cells stayed canvas-sized while features shrank;
2. residual completion/work opportunity did not scale with the amount of fine design-area detail required by the unchanged service percentages;
3. fine geometry legitimately produced many more main-network fronts, exposing global singleton pairing and repeated traceback-index rebuilds;
4. a recovery-fragment child's first gesture could bypass inherited visible-lane zigzag validation because its own centerline still had one point;
5. late local completion rebuilt large target/coverage sets repeatedly as the service field grew into hundreds of thousands of cells.

## Correction

- Population territory remains V43's scale-independent `T=(W*H)/min(W,H)^2`.
- Component/local service-grid resolution follows the design unit (`1/main_scale` per axis).
- Fine-detail residual opportunity/work scales with `D=T/main_scale^2`; main exact-computation allowance follows distance resolution without multiplying global round counts.
- Connection/rollback/proposal broad phases are spatialized or same-snapshot cached only where exact decisions are unchanged.
- Inherited visible-lane grammar is enforced from a fragment child's first gesture.
- Local targetable-cell and first-touch bookkeeping is incremental and per-region; the 16-subcell service audit itself is unchanged.

## Release proof

V44 release requires full logical-sample-0 production acceptance at 1200×6248 and 1200×8046 with `main_scale=0.35`, plus the complete active test manifest with zero failures/errors/skips/xfails.

## Release-verification corrections

- During rotated 6248×1200 scale-1 regression verification, the final frozen-geometry audit found one component↔local clearance violation even though the local polyline body itself was clear. The visible source/terminal marker extent was not part of the materializer's redundant static admission gate. V44 now validates the complete visible local trace package against frozen chips/components and prunes the optional trace if any visible primitive violates the moat. The exact final audit is unchanged.
- Reconciled the active test tree so only `test_pcb_v44_renderer.py` is discoverable; V43's complete test suite remains preserved under `archive/releases/v43/`.
- Added an active marker-extent clearance regression and updated the incremental local-target fixture to initialize the authoritative untouched set rather than relying on the pre-V44 reconstructed-set implementation.


## Release-verification hardening: causal main-preflight pair repair

- Full stress verification exposed one main-network intersection cleanup on a tall scale-1 board. The two visible traces belonged to one diagnosed intersection pair and had both independently been reopened by preflight causal repair.
- The repair policy now follows the materialization diagnosis causally: `new_front` (the later offending trace) is repaired first; `old_front` is attempted only when the first side cannot be repaired. A successful repair of one side ends that pair's repair. This prevents a stale diagnosis from rerouting both peers and manufacturing a new crossing between two independently regrown tails.
- The final main-network materialization audit remains unchanged and may not delete a launched main trace to obtain a pass.
- Added an active regression test for the one-causal-side-per-pair rule. The active V44 manifest now contains 73 tests.

- Reconciled the optional stress suite with V44 population scaling: mandatory 6248/8046 full-production proofs remain active acceptance artifacts, while live stress samples additional square main-network seeds so it stays routinely executable.
