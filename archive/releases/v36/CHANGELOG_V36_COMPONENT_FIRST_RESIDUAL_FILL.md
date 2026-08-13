# CHANGELOG V36 — Component-First Residual Fill and Local Completion

V36 preserves V35 main routing, scale, chip-population gating, hard pathway grammar, honest service accounting,
and exact clearances, but reverses the two residual-fill phases.

## Generation order

1. Main chips.
2. Main-chip network against chips only; preflight/repair; freeze.
3. Gap-aware components serve 50–60% of the post-main substantial residual capacity; freeze.
4. Local gap lines route around the frozen main network and frozen components and serve 80–90% of the remaining
   service budget.
5. Final exact line/component/marker/clearance audits.

## Component-first residual phase

- `component_residual_gap_fill_target` is sampled from `Uniform(0.50,0.60)`.
- V35 substantial-region area × size/quantity capacity remains the governing metric.
- Small gaps prefer small/micro objects, medium gaps medium objects, and large gaps larger/multiple capacity units.
- Optional sliver pockets may remain negative space.
- The old V35 dense-count floor is disabled for this 50–60% phase so components do not mechanically climb back
  toward ~100% before local lines start.
- Component placement failure can only retry/regenerate component templates/placements against the same frozen
  main routes.

## Local-after-component phase

- `local_gap_fill_range = (0.80,0.90)` is interpreted as a fraction of the **remaining service budget** after
  component service.
- If `C` is component service and `L` the seeded normalized local target, the absolute local target is
  `(1-C)*L`.
- Physical routing still uses actual post-component free geometry; components are real obstacles.
- Frozen main pathway geometry is preloaded into the local path index.
- A component spatial broad phase avoids all-component exact checks for every local candidate while retaining
  exact nearby clearance tests.
- V35 local-line language remains: independent sources, temporary compatible bundling, release, boosted branching,
  region-aware scale/lifetime, honest visible stroke + legitimate spacing perimeter.

## Clearance hardening for reversed order

- Final audits explicitly check main↔local pathway clearance and component↔local pathway clearance.
- Ordinary local source/terminal markers are included in component clearance.
- If a final local terminal dot would violate a component moat, the endpoint may back off along its existing legal
  straight/45° path until the marker clears; no illegal bend is introduced.
- Unauthorized component/pathway overlap is re-audited against the combined main+local pathway population.

## Unchanged invariants

- `S = min(W,H) * main_scale`, `U = S/1600`; no extra 0.75 multiplier.
- Default 1200×1200 canvas has exactly two main chips; `main_scale` does not alter chip population.
- Main routing is transactional-parallel and uses local-space-aware causal traceback/re-route.
- Main-lane survival and side progress remain hard.
- Pathway bodies are straight segments only with 0/±45° changes; direct 90° turns and curved pathway primitives
  are hard failures.
- Residual phases never reroute the frozen main network.

## Final production hardening

- Forced head-to-head connection legs now explicitly handle the valid case where the final tiny rendezvous leg
  lies wholly inside the already-audited junction envelope. Shapely represents the outside remainder as an empty
  geometry with NaN bounds; V36 no longer sends those bounds into the spatial hash.
- Ordinary gestures reject empty/non-finite candidate geometry before broad-phase lookup. The junction-only
  exception still checks the full finite leg against static/source-egress constraints and the junction disk against
  third routed corridors.

## Bounded local-tail runtime

- Post-component local routing uses three organic synchronous waves, preserving independent birth, temporary
  bundling, branching and local-space steering, then hands the remaining service obligation to the exact
  straight/diagonal residual-corridor mop-up.
- A deterministic per-planner gesture-check budget rejects unusually expensive logical samples by work count, not
  elapsed time. Healthy release seeds remain well below the cap; seeded geometry therefore never depends on clock
  timing.
- Component obstacles are broad-phased at primitive granularity for local routing so a complex collection cannot
  trigger pathological repeated topology-distance work through one dissolved 50–70-primitive union.
