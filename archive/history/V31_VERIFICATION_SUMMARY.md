# V31 Verification Summary

## New transactional-parallel invariants

Direct unit regressions pass for:

1. a root main-chip launch can rewind its first accepted gesture completely back to its emergence anchor;
2. local joint conflict solving returns the same compatible assignment when the proposal-map insertion
   order is reversed;
3. an unsolved same-round conflict group schedules repair for the group and commits no winner geometry;
4. a young blocked launch requests rollback from the causal active foreign blocker rather than immediately
   scheduling itself as the loser.

## Existing renderer regressions

The following existing checks were run successfully after the V31 core change:

- bundle-gesture pathway geometry/collision regression (`seed=12345`);
- deferred hard-stop/traceback recovery regression;
- bounded holistic connection/loop/repair regression;
- three individual arbitrary-seed hard-geometry samples for base seed `20260806` at 1000×1000;
- component fallback uses cached route keepout unions;
- component failure cannot internally restart routing;
- route-before-secondary-components dependency;
- independent `main_scale` behavior;
- quota/IC/dense/capacitor/static component regressions;
- single-sample and cross-sample uniqueness/deadlock-domain checks.

The test harness's combined all-in-one heavy command can exceed the execution wrapper window, so the
geometry-heavy arbitrary-seed cases were also executed separately. Each completed cleanly.

## Known-problem seed comparison

For base seed `20260806` at the default 1200×1200 scale:

- V30 visible main launch traces: `53 / 58`;
- V31 visible main launch traces: `56 / 58`;
- V31 unmarked thick-stroke overlap count: `0`;
- V31 tiny termination trace count: `0`;
- V31 local-gap coverage report: `0.45` on the checked sample.

This is not a hard 100% launch-survival quota; physical feasibility and hard geometry still govern. The
important V31 invariant is that same-round processing order cannot create a winner whose proposal then
becomes an obstacle to its peer, and young launches can force causal rollback consideration.

## Untouched default execution

A literal no-argument invocation of the final working renderer completed successfully:

```text
python pcb_v31_renderer.py
```

Observed wall time in this environment: approximately `11.8 s` for one completed SVG. The generated
report identified `pathway_planner_mode = route_first_transactional_parallel` and reported zero unmarked
stroke overlaps and zero tiny termination traces.

Wall-clock time is not used to alter seeded geometry.
