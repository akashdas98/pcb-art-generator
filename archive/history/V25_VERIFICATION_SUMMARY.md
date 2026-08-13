# V25 Verification Summary

## Build checks

- Python source compiles successfully.
- Existing static collection/quota invariants pass under the new generation order.
- New route-first unit test confirms the pathway generator receives only `placement_kind == "chip"`.
- New scale test confirms changing `main_scale` changes S/U-derived geometry while leaving W/H unchanged.
- New post-route component test confirms the residual-fill mode and zero unplaced components on the test seed.

## Full routed smoke sample

Reference smoke run:

```text
base seed: 12345
canvas: 1200 × 1200
main_scale: 1.0
chip_count: 2
collection_count: 17
visible pathway traces: 79
planner: route_first_bounded_local_holistic_v25
component mode: post_route_residual_gap_fill_v25
sampled gap-fill target: 0.8412039069
realized representative gap-site fill: 0.8260869565
representative gap sites: 23
unplaced components: 0
pathway static intersections: 0
unmarked pathway overlaps: 0
collapsed pathway overlaps: 0
unmarked thick-stroke overlaps: 0
```

Observed wall time in the build environment was approximately 34 seconds for this routed sample.

## Independent main-scale smoke check

Using the same 1200×1200 canvas and seed with the no-path test harness:

```text
main_scale  U      representative first-chip short dimension
0.65        0.65   78.39
1.00        1.00   120.61
1.25        1.25   150.76
```

The chip dimension ratio follows the supplied master scale while canvas dimensions remain unchanged.

## Interpretation

V25 removes secondary-component obstruction from the routing problem. It does not remove pathway-vs-
pathway collision, branching, persistence, connection, anti-zig-zag, or marker constraints. Final
component filling is intentionally bounded and gap-seeking rather than a global packing optimizer.

## Additional regression verification

- Main pathway invariant regression (`seed=12345`) passes after classifying one-module local
  structural rebases as explicit non-normal exceptions and suppressing empty cleaned-up roots.
- Holistic connection / recovery regression (`seed=12345`) passes unchanged.
- Arbitrary-seed hard-geometry samples for base seed `20260806`, logical indices `0`, `1`, and `2`
  each report zero static intersections, unmarked overlaps, collapsed overlaps, unmarked stroke
  overlaps, compensating zigzags, tiny terminations, midline connections, multiply-connected traces,
  marker overlaps, duplicate cleanup, and intersection cleanup.
- The visible no-tiny-death audit now runs after source/terminal marker clipping for all terminated
  traces, so clipping cannot reduce a legal centreline into a rendered sub-2.75-module stub.
- Same-seed determinism was verified with two fresh `1000×1000` renderers at seed `515151`; both
  produced the same combined SVG+report SHA-256:

```text
705630a18901322839ec9086683116e733b54c5f862f7f8559fc84f86a2f9b49
```
