# V22 Verification Summary

## Acceptance policy

Verification is split into two categories.

### Hard pass/fail invariants

A board fails verification for any of the following:

- static-object intersection;
- unmarked centerline intersection/overlap;
- unmarked thick-stroke touch/overlap;
- collapsed/doubled trace;
- compensating zig-zag;
- visible involuntary terminal trace shorter than 2.75 routing modules;
- mid-line trace connection;
- multiply-connected trace;
- overlapping termination markers;
- duplicate/intersection cleanup required by the final SVG safety net;
- configured static/main-chip pathway-clearance violation.

### Soft reported outcomes

These are measured and compared, but do **not** invalidate a physically legal board:

- realized launch-span percentage;
- visible/attempted launch-trace count;
- cross-chip join count;
- branch realization;
- travel/canvas coverage;
- short-but-not-tiny legal endings;
- abandoned speculative routes;
- bundled forced-ending frequency.

The sampled launch intent remains approximately 72–90% of a chip-body side, but realized output is never forced to remain in that range.

## Regression execution

The following test methods completed successfully in the build environment after the V22 freeze:

- `test_bundle_gesture_pathways_are_direct_modular_and_collision_clean`
- `test_pathways_are_deterministic_without_pathway_seed_search`
- `test_hard_stops_use_deferred_reroute_before_forced_termination`
- `test_holistic_connections_loop_guard_and_extended_repair_are_active`
- 11 static/component/quota/placement tests in one batch
- 2 uniqueness/deadlock tests in one batch

The geometry-heavy arbitrary-seed test contains three complete renders and exceeds this environment's combined execution wrapper when run as one method. Its three boards were therefore verified separately with the same hard assertions.

## Fixed benchmark observations

These figures are diagnostic outcomes, not quotas.

### Reference — 1200×1200, seed 12345, sample 0

- launch traces: 65
- visible traces: 65
- minimum realized launch span: 0.7291
- cross-chip joins: 3
- same-chip close-head joins: 1
- tiny visible terminations: 0
- bundled forced termination traces: 0
- static intersections: 0
- unmarked thick-stroke overlaps/touches: 0
- compensating zig-zags: 0
- duplicate cleanup: 0
- intersection cleanup: 0
- termination-marker overlaps: 0
- mid-line joins: 0
- multiply-connected traces: 0

### Stress 0 — 1000×1000, seed 20260806, sample 0

- attempted launch traces: 60
- visible traces: 58
- minimum realized launch span: 0.7377
- cross-chip joins: 4
- tiny visible terminations: 0
- bundled forced termination traces: 0
- abandoned speculative traces: 2
- all hard geometry/connection/marker violation counts: 0

### Stress 1 — 1000×1000, seed 20260806, sample 1

- attempted launch traces: 65
- visible traces: 60
- minimum realized launch span: 0.3882
- cross-chip joins: 4
- tiny visible terminations: 0
- bundled forced termination traces: 0
- abandoned speculative traces: 5
- compensating zig-zags: 0
- all intersection/overlap/connection/marker violation counts: 0

This is the benchmark that demonstrates the soft-target policy most clearly: V22 suppresses invalid tiny routes even though doing so leaves one constrained chip side far below the nominal launch-span intent.

### Stress 2 — 1000×1000, seed 20260806, sample 2

- attempted launch traces: 65
- visible traces: 64
- minimum realized launch span: 0.7245
- cross-chip joins: 3
- tiny visible terminations: 0
- bundled forced termination traces: 0
- abandoned speculative traces: 1
- all hard geometry/connection/marker violation counts: 0

## Runtime character

Observed full-board routing times in this build environment are roughly in the low-to-mid tens of seconds for these benchmark boards. V22 remains strictly bounded: no unrestricted route search or full-board routing-permutation search is part of normal generation.
