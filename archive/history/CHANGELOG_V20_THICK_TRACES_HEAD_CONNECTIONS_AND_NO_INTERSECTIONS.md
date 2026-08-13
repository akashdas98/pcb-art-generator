# V20 — late-life branching, doubled trace gauge, head-only joins, and strict no-intersection routing

V20 builds directly on V19. The synchronous / holistic shared-round planner remains the routing architecture; no A*, pathway seed search, or realized-output quota search is introduced.

## 1. Late-life branch boost

- V19's seeded board-level branch appetite and `1.50–1.80×` general branch multiplier remain active.
- A route is considered in its **later life after ~60% of its originally planned gesture budget, with at least five accepted gestures**.
- In that later phase the branch probability receives an additional **1.50× multiplier** (capped below certainty).
- The 60% threshold is intentionally a first tuning guess and is reported as `late_life_branch_start=0.60`.

## 2. Trace gauge doubled and lane gap tied to stroke width

- Ordinary trace width is now **2.00–3.10U** (2× V19's 1.00–1.55U).
- Rare emphasis traces are also doubled to **5.0–7.4U**.
- Launch pitch is chosen so the **edge-to-edge gap is at least about 1.5× the adjacent pair's mean trace thickness**.
- Chip-side occupancy remains targeted at **72–90%** of the actual chip-body side.

## 3. Small-component routing perimeter doubled

- The foreign-static routing keepout is **8U**, doubled from V19's 4U.
- This 8U is extra air outside the complete routed stroke/bundle envelope; it is not merely a centerline distance.

## 4. Trace-to-trace connections are head-to-head only

- The former singleton-to-middle-of-foreign-lane attachment path is disabled.
- A trace already present in a physical connection cannot connect again.
- Connections terminate at the **free heads of both participating traces**; mid-line T-junctions are forbidden.
- Very close compatible cross-chip lane heads (within **1.90 routing modules**) are deterministic connection opportunities rather than probability rolls.
- Close heads may peel one lane out of a still-bundled cohort **only after** the complete terminal connection is proven collision-clean. Sibling lanes continue routing normally.
- The junction envelope is checked against third-party routes, so the two participating heads are the only geometry allowed in the connection overlap region.

## 5. Detached-prefix recovery lock

- When a lane peels out of a bundle for a connection, the remaining parent cohort's current route becomes a traceback floor.
- This prevents later recovery from rewinding shared geometry that the detached child still visibly owns, eliminating a subtle source of stale-prefix crossings.

## 6. No tiny emergence stubs

- Involuntary terminal routes shorter than **2.75 routing modules** are classified as abandoned recovery attempts and are not rendered as deliberate-looking stubs.
- Ordinary isolated termination remains allowed once the route has travelled meaningfully; component approaches, physical joins, and off-frame exits remain legitimate terminals.

## 7. Strict intersection / duplicate safeguards

- Ordinary proposal collision checks remain active at the bundle-corridor level.
- Head connections additionally receive an **exact materialized-lane stroke check** against every currently owned trace.
- Final materialization audits both centerlines and full thick-stroke geometry.
- Unmarked centerline crossings, collapsed/duplicated centerlines, thick-stroke overlaps/touches, multiply-connected traces, and non-head connections are all reported explicitly.
- A final deterministic safety filter suppresses any trace that would violate those hard rendered-geometry invariants; the V20 verification probes required **zero** such suppressions.

## Preserved rules

- deterministic same-seed behavior;
- shared synchronous planning rounds with deterministic commit conflict resolution;
- no pathway candidate-seed retry or A* search;
- anti-circle / anti-turn-drift behavior;
- extended V19 traceback/reroute and bundle-persistence behavior;
- 120U main-chip edge inset and 170U main-chip/secondary placement moat;
- 70–90% chip-side emergence target.
