# V16 — synchronous bundle gestures

V16 replaces only the pathway subsystem on top of the trusted v12.1 static-board baseline.
The rejected v15 holistic/A* implementation was not used as a source.

## Removed

- individual-trace A* and fine-grid destination routing;
- pathway candidate-seed retries and accepted-seed searching;
- hard realized-output quotas for connections, exits, coverage, or turns;
- synthetic rendezvous nodes and proximity reported as connectivity;
- micro-step rescue paths, compensating zigzags, and permissive lane collapse.

## Added

- one seeded, coherent pathway profile per board;
- `31U–39U` canvas-relative movement modules;
- synchronous rounds over all active bundle fronts;
- broad side buses followed by contiguous `4–7` trace cohorts;
- explicit structural branch trees with stable lateral order;
- long conditional gestures toward open/underused regions, edges, components, and foreign routes;
- analytic late expansion of bundle corridors into parallel trace lanes;
- physical trace-to-trace cross-chip terminal joins;
- a corridor-only visual debug stage;
- exact audits for static intersections, accidental crossings, collapsed centerlines,
  illegal turns, micro-zigzags, and segment length;
- direct arbitrary-seed and byte-identical same-seed regressions.

## Behavioral contract

Intent probabilities control what a bundle attempts. The generated static geometry controls what
can actually happen. Missing connections, escapes, branches, or long traversals are legitimate
best-effort outcomes and never cause a pathway retry or board regeneration.

## Build verification

- 14 tests pass.
- The fresh five-board 1000×1000 deliverable set completed in 10.9 seconds in one invocation.
- Ten additional boards from two unrelated base seeds completed in 21.3 seconds total.
- In that five-board probe, every pathway retry/search counter, static intersection count,
  unmarked crossing count, and collapsed overlap count is zero.
