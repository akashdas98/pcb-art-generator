# V19 — inward chips, doubled chip moat, component keepout, stronger branching and bundle persistence

V19 builds directly on V18. The synchronous shared-round / holistic connection architecture remains active; no A* search, pathway seed retry, or accepted-output search is introduced.

## 1. Main-chip placement moved inward

- Main-chip final geometry must stay at least **120U** from every canvas edge.
- The existing 2/3 chip-count distribution is retained.

## 2. Main-chip exclusion moat doubled

- Secondary collections and isolated capacitors now require **170U edge-to-edge clearance** from every main chip (2× the V17/V18 85U breathing zone).
- Fixed a placement bug where the spatial query only searched 60U around a candidate even when the configured chip-secondary clearance was larger. The query now expands to the full moat before pair checks are evaluated.
- A direct three-chip / 18-secondary stress case succeeds with the corrected lookup while preserving the full moat.

## 3. Thicker no-touch perimeter around components

- Bundle corridor geometry must remain at least **4U** from every foreign static component.
- The corridor already contains the full trace/bundle stroke envelope, so this 4U is additional visible air beyond the line thickness.
- The source chip is exempt only for its own launch gesture; traces still begin outside the complete chip geometry.

## 4. Branching is 50–80% more likely

- The V18 base board-level branch appetite remains seeded at `0.34–0.54`.
- V19 multiplies the effective branch probability by a seeded **1.50–1.80** factor, capped below certainty.
- Ordinary structural branch rules, contiguous lane partitioning, lateral-order preservation and branch preflight remain unchanged.
- In recovery conditions, a branch may use a one-module lane-preserving rebase so a wide trapped cohort can split rather than repeatedly fail as one envelope.

## 5. Bundled termination strongly suppressed

- When a multi-trace front reaches its ordinary journey limit, it has only about **10%** of the former willingness to terminate.
- In the other ~90% case it attempts a useful branch and otherwise receives additional journey budget.
- A hard-stopped bundle first receives the normal extended repair budget. If that budget is exhausted, only about **10%** terminate while still bundled; the preferred outcome is recovery fragmentation into independent singleton fronts at their true materialized lane endpoints.
- Singleton traces are allowed to terminate normally. Component approaches, explicit physical connections and off-frame exits remain legitimate terminals.

## 6. Traceback / reroute extended

- Reroute budget: **5 → 7** attempts.
- Maximum progressive traceback depth: **4 → 6** accepted gestures.
- Recovery-mode duration: **3 → 4** decisions.
- Stagnation repair triggers earlier, and repeated same-sense turn drift may also schedule a repair.
- Existing connection recovery floors, loop rejection, collision rules and no-compensating-zigzag rules remain intact.

## Preserved hard invariants

- deterministic supplied-seed behavior;
- synchronous round planning and deterministic conflict resolution;
- no pathway candidate-seed retries;
- no A* / destination route search;
- no static intersections;
- no unmarked trace crossings;
- no collapsed centerlines;
- no compensating micro-zigzags;
- launch-side occupancy remains targeted at 70–90% of main-chip body width/height.
