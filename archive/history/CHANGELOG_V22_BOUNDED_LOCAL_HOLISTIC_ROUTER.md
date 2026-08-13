# V22 — Bounded Local Holistic Router

V22 replaces the increasingly repair-heavy V21 decision layer with a bounded local holistic scheduler while preserving the existing V21 geometry/materialization rules, trace styling, static placement, seed determinism, and hard collision invariants.

## Design-policy clarification

V22 makes the renderer's governing distinction explicit:

- **Hard invariants** are never traded away: no static intersections, no unmarked centerline or thick-stroke contacts, no doubled/collapsed traces, no mid-line joins, no multiply-connected trace, no compensating zig-zags, no overlapping termination markers, no tiny visible involuntary post-emergence stubs, and all configured chip/component keepouts remain authoritative.
- **Soft tendencies** are best-effort only: launch coverage, connection frequency, branching frequency, travel/coverage, frame exits, and bundled-termination suppression are intentions and diagnostics, not realized-output quotas.
- A constrained board is allowed to realize less of a soft tendency. The renderer must never retain bad geometry, regenerate the static board, or search indefinitely merely to hit a percentage.

This also removes the old final-materialization behavior that could keep a tiny failed trace visible solely to preserve >=70% realized launch span.

## Routing architecture

- Planner mode: `bounded_local_holistic_v22`.
- Open-space movement retains the cheap seeded V21 stochastic fast path.
- A **40×40 congestion field** provides inexpensive board-wide awareness.
- Explicit front lifecycle labels are maintained: `LAUNCHING`, `NORMAL`, `STRUCTURAL_TRANSITION`, `CONNECTION_PENDING`, `RECOVERING`, `TERMINAL`.
- Bounded foresight activates only for young, structural, recovering, connection-pending, failed, or congested fronts.
- Local future conflicts are grouped through a spatial broad phase. At most four fronts are jointly considered; each contributes only a tiny shortlist of candidates.
- The local scheduler prefers compatible futures rather than allowing one greedy move to consume another front's only near-term corridor.
- Active-front blocker yielding remains bounded and local; it is not a global board re-route.

## Transactional topology

- Launch fans and ordinary branches are preflighted before topology commits.
- V22 fan birth uses a tiny bounded permutation of non-crossing child maneuvers instead of insisting on one decorative left/right peel when geometry makes that exact fan impossible.
- A structural child is not intentionally born into an immediately blocked continuation.
- Connection detachment may peel only an **outer lane** of a live cohort. Interior lanes must first become exposed through a real contiguous branch.
- Detached prefixes remain recovery-locked so later traceback cannot erase geometry already inherited by a connected child.

## Connections

- Trace-to-trace joins remain **head-to-head only**.
- A trace may participate in at most one trace connection.
- Close compatible heads receive deterministic priority when a legal physical join exists.
- Same-chip-side ancestry no longer blocks an otherwise legitimate close free-head join.
- Final marker arbitration may perform bounded local blocker negotiation: an unrelated terminal singleton can rewind only its own local tail, allow an obvious head pair to connect, then attempt a bounded escape around the new join.
- No mid-line/T attachment is reintroduced.

## Recovery and termination

- Deferred reroute/traceback remains available, but V22 uses prevention and bounded foresight before escalating recovery.
- Young bundles prefer legitimate transactional branching before recovery fragmentation.
- Proactive persistence fragmentation is withheld until a cohort has made meaningful travel.
- Tiny involuntary terminated leaves below 2.75 modules are never retained merely to protect a launch-percentage target; they are suppressed as failed speculative routing.
- Escape-beam and final-exit checks now inspect the complete inherited visible history of recovery singletons, preventing a local child from creating a hidden prefix-boundary A→B→A zig-zag.

## Preserved V21/V20 geometry rules

- 2× termination dots; hollow stroke 2.70U; hollow traces stop at the marker border.
- Ordinary trace widths 2.00–3.10U with rare emphasis traces.
- Lane edge gaps target roughly 1.5× adjacent mean line thickness and also accommodate enlarged endpoint dots.
- 8U foreign secondary/static routing keepout.
- 24U foreign/main-chip routing keepout with source-chip monotonic outward egress semantics.
- 170U chip-to-secondary static-placement moat and 120U chip-to-frame placement inset.
- Late-life branching begins around 60% of sampled lifespan and receives a further 1.50× tendency multiplier.
- Same seed and parameters remain deterministic; no pathway seed search, A*, or pathway-driven static-board restart is used.
