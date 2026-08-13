# V38 changelog — articulated local-gap routing and 45-degree-only turn hardening

## Problem

V37 restored coherent residual component assemblies, but the final local-gap completion stage still inherited a
straight-corridor shortcut. After organic local growth, `_local_gap_direct_mopup` exact-checked long horizontal,
vertical, and diagonal uncovered runs and committed straight fillers. On the maintained V37 release boards this made
pure start-to-end straight traces visually dominant even though the organic router itself was capable of turning.

The pathway grammar already intended 0/±45° heading changes only, and the maintained V37 boards reported zero
illegal turns. V38 nevertheless makes that invariant defense-in-depth so no special constructor, repair, or mop-up
path can introduce a direct 90° corner.

## Changes

### Organic local fronts

- Reduced local target attraction so a target is a region-level attractor rather than a beeline rail.
- Every local front samples a deterministic 1–3 accepted-gesture straight-run allowance.
- Once that allowance is due, a legal ±45° proposal receives a strong soft score advantage over another straight
  continuation.
- The existing two-gesture post-turn cooldown remains, preventing the new turn preference from becoming rapid
  compensating zigzag behavior.

### Bent-first final service completion

- Replaced the normal straight-corridor mop-up with a bounded bent planner.
- A normal mop-up trace must contain a mid-body +45° or -45° pivot before commit.
- Candidate bends are cheaply ranked from residual-field geometry; only the strongest bounded candidates receive
  exact geometry/clearance checks.
- After the bend, the trace may take additional ordinary legal local gestures.
- A pure straight mop-up remains only as a genuinely narrow-pocket exception and is globally capped.
- If fragmented residual service is still below target, a second bounded rescue uses bent-only two-leg doglegs; it
  does not restore broad straight fillers.

### 45-degree-only hardening

A direct 90° heading change is now blocked at multiple independent layers:

1. proposal grammar;
2. commit-time heading delta validation;
3. actual rendered-polyline-tail validation when a segment is recorded;
4. final materialized pathway audit.

The hard legal set for consecutive pathway headings remains exactly: straight (`0°`) or one 45-degree unit left/right
(`±45°`). Curved pathway bodies remain forbidden.

### New diagnostics

Reports now expose:

- `pathway_local_gap_straight_visible_trace_count`
- `pathway_local_gap_straight_visible_trace_fraction`
- `pathway_local_gap_mean_turns_per_visible_trace`
- `pathway_local_gap_max_single_vertex_turn_degrees`
- `pathway_local_gap_mopup_bent_trace_count`
- `pathway_local_gap_mopup_straight_trace_count`
- `pathway_local_gap_mopup_bent_rescue_trace_count`

The maintained release regression boards require straight visible local traces to remain at or below 20%, while
geometry is still allowed to leave constrained negative space rather than forcing an illegal bend.

## Explicit non-changes

- Main-chip routing architecture and transactional-parallel recovery are unchanged.
- Main routes still freeze before any residual components exist.
- V37 coherent compound component assemblies are retained unchanged in intent.
- Component target remains 50–60% of post-main residual service capacity.
- Local-line target remains 80–90% of the post-component remaining service budget.
- Existing thickness-aware pathway spacing and component/pathway clearances remain hard.
- Deterministic seeded generation and canvas/main-scale rules are unchanged.
