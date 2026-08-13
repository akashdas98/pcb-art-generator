# V34 Verification Summary

## Release scope

V34 verifies the user-requested correction set: whole-design canvas/1600 default scale, unchanged chip-count distribution, stronger chip routing separation, bounded local-space-aware forward routing, causal multi-gesture traceback with failed-corridor replay suppression, no direct 90° pathway turns, no curved pathway bodies, independent/space-aware local-gap filling, >=90% residual component service, and zero unauthorized overlap.

## Direct architectural regressions

The following transactional/source-egress tests pass:

- root main launch can traceback to the emergence anchor;
- joint conflict solution is insertion-order invariant;
- unsolved same-round conflict commits no winner and schedules joint repair;
- a young blocked launch can request causal rollback from the blocker;
- no root structural split before physical egress;
- single-cohort root remains straight through physical egress;
- traceback reactivates source-egress reservation;
- same-family conflict can atomically HOLD a sibling;
- V34 default scale is canvas/1600 for the complete design while chip-count rule remains 90% two / 10% three;
- traceback blacklists the historical corridor leaving the rollback junction.

All 10 direct tests passed.

Route-before-components and independent `main_scale` tests also pass.

## Full V34 contract regression

`test_v34_space_aware_causal_contract` passes on a full 1200×1200 routed board. It asserts:

- chip pair clearance >= the V34 routing moat;
- at least one true cross-chip connection;
- every launched main lane remains visible;
- no stalled emitted main side;
- local fillers are independent singleton births;
- local gap fill >=40%;
- residual component service >=90%;
- zero unauthorized line/stroke, static, and component/pathway overlap;
- zero illegal pathway turns;
- zero curved pathway primitives;
- local-space-capacity evaluation is active;
- actual traceback is active;
- default `design_scale_basis=900` and `design_unit_divisor=1600` on a 1200 square.

## Determinism

Two fresh V34 renderer instances using seed `20260806`, identical 1200×1200 canvas and default scale produce identical reports and byte-identical SVG output. The deterministic full-sample regression passes with one logical-sample attempt; pathway candidate seed search and global route search remain zero.

## Representative seeded runs

### Seed 20260806 — 1200×1200 default V34 scale

- elapsed: ~17.6 s
- design basis: 900; U=0.75
- main launches: 58 / 58 visible
- cross-chip connections: 17
- local-gap line coverage: 41.22%
- visible local traces: 45
- independent local sources: 49
- residual component visual service: 93.32%
- illegal pathway turns: 0
- curved pathway primitives: 0
- unmarked pathway/stroke overlap: 0
- unauthorized component/pathway overlap: 0

### Seed 15186978462388109083 — 1200×1200 default V34 scale

- elapsed: ~23.0 s
- main launches: 67 / 67 visible
- cross-chip connections: 18
- traceback operations: 307
- committed segments removed by traceback: 708
- local-space available replan deferrals: 27
- local-gap line coverage: 48.22%
- visible local traces: 49
- independent local sources: 58
- residual component visual service: 92.57%
- illegal pathway turns: 0
- curved pathway primitives: 0
- unmarked pathway/stroke overlap: 0
- unauthorized component/pathway overlap: 0

This seed is important because substantial free-space-aware traceback/re-route is actually exercised rather than the board succeeding only due to spacing.

### Three-chip seed 59 — 1200×1200 default V34 scale

- elapsed: ~20.8 s
- chips: 3
- main launches: 97 / 97 visible
- cross-chip connections: 22
- local-gap line coverage: 43.51%
- visible local traces: 30
- residual component visual service: 92.91%
- illegal pathway turns: 0
- curved pathway primitives: 0
- unmarked pathway/stroke overlap: 0
- unauthorized component/pathway overlap: 0

This confirms the stronger routing moat does not eliminate the 3-chip branch of the unchanged chip-count distribution.

## Untouched default-mode probe

A literal no-argument V34 working-tree invocation completed on logical sample 0 in ~19.25 s:

- chips: 2
- chip pair geometry clearance: ~682.8 canvas units; required V34 moat: 270
- main launches: 66 / 66 visible
- cross-chip connections: 14
- traceback operations: 296
- local-gap line coverage: 48.91%
- visible local traces: 41
- residual component visual service: 92.34%
- illegal turns / curved pathway primitives / unauthorized overlaps: all 0

A second random default probe skipped its first pathological logical sample and emitted a valid logical sample 1 with 63/63 main lanes, 13 cross-chip connections, 47.14% local coverage and 90.55% component service. This confirms default skip semantics remain active instead of multiplying full-board retries.

## Runtime-sensitive fixes

- Local free-space awareness uses the maintained congestion grid for ranking and exact geometry only for final legality; the discarded version that performed many Shapely distance probes per candidate was not shipped.
- Physical offset-lane grammar is exact-checked only for risky compensating reversal/structural cases, not every ordinary candidate.
- Component service-grid accounting is incremental; adding a mop-up filler does not rebuild/buffer the entire accepted component union.
- Component distribution ranking uses cheap centre-distance heuristics while exact geometry remains authoritative for collision acceptance.
- Component-only retries operate on frozen routes and cannot invoke routing.

## Historical integrity

All 40 prior `CHANGELOG_V*.md`, `V*_VERIFICATION_SUMMARY.md`, and `V27_EXECUTION_AUDIT.md` records found in the released V33 package were SHA-256 compared against the V34 working tree and are byte-identical. V34 adds new records rather than rewriting history.

## Final packaged no-argument gate

The final clean zip was extracted to a fresh directory and run literally as `python pcb_v34_renderer.py` with no arguments. It completed in **12.83 s** on logical sample 0 with:

- main launches: 63 / 63 visible;
- cross-chip connections: 22;
- traceback operations: 173; committed segments removed: 331;
- local-space termination/replan deferrals: 9;
- local-gap line coverage: 44.14%; visible local traces: 41; independent local sources: 57;
- residual component visual service: 91.65%;
- main-chip pair geometry clearance: ~843.18 canvas units vs required 270;
- illegal pathway turns: 0;
- curved pathway primitives: 0;
- unmarked pathway/stroke overlap: 0;
- unauthorized component/pathway overlap: 0;
- `design_scale_basis=900`, `design_unit_divisor=1600`.
