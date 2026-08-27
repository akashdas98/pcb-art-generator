# V42 — Tall-Canvas Local-Fill Scaling and Performance

## Problem

After V41 fixed the tall-canvas octilinear clipping defect, complete 1200×6248 and 1200×8046 boards exposed a second issue: local residual fill retained several square-board assumptions. A fixed 56×56 service grid became physically stretched on portrait canvases, global scans grew with all accumulated geometry, and fixed square-board work caps could stop the local phase before the existing 80–90% service rule was realizable.

## Changes

- Made the **local** residual grid aspect-aware while preserving approximately square physical service cells.
- Kept the **component** gap/population grid fixed at 56×56; tall aspect ratio alone does not multiply component population.
- Replaced an all-to-all local-source distance scan with bounded spatial-hash neighbor lookup followed by the same exact distance calculation.
- Replaced global-union distance work in component residual scoring with spatial nearest-neighbor broad-phase queries.
- Replaced whole-field sort-for-top-48 component filler selection with bounded top-k selection using the same scoring tuple.
- Updated residual-region capacity bookkeeping incrementally rather than recomputing unaffected accepted component capacities.
- Scaled the local exact-gesture computational allowance with the square root of the tall area multiplier instead of retaining the square-board cap.
- Added a bounded articulated fragmented-pocket cleanup for tall boards and then returns any remaining deficit to the ordinary local router for bounded late waves.
- Preserved the existing 0/±45-degree turn grammar, exact rendered clearances, component-first 50–60% service, local 80–90% remainder-service target, deterministic seeding, and source-marker behavior.

## Acceptance evidence

Deterministic base seed 1:

- 1200×6248: component service 54.02%; local remainder service 83.81%; all exact octilinear/turn/clearance counters zero.
- 1200×8046: component service 55.26%; local remainder service 83.09%; all exact octilinear/turn/clearance counters zero.

Fresh standard and difficult V42 acceptance samples also retain zero geometry violations.
