# V35 — Honest Gap Service, Canvas-Gated Population, and Residual-Pocket Correction

## Scale and anchor population

- Removed V34's extra `0.75` design-scale multiplier.
- Active scale is now `S=min(W,H)*main_scale`, `U=S/1600`.
- Main-chip count is gated by actual canvas area, not `main_scale`.
- Default 1200×1200 always produces exactly two main chips.
- Rare third-chip probability becomes eligible only as actual canvas area grows, capped at 10%.
- Strengthened routing moat to `max(430U, 0.265*S_canvas)`; default 1200 square requires 322.5 canvas units between chip footprints.

## Main routing

- Retained V34 local-space-aware transactional routing and real causal multi-gesture traceback.
- Retained rollback-junction replay-corridor suppression: recovery remembers the historical direction that left the rollback point rather than merely the dead-head direction.
- Retained local-space termination deferral and foreign-blocker causal recovery.
- Fixed an intact main-side family failure where clearing the protected egress horizon could be misinterpreted as completion after a cohort fan failed. Reaching the egress threshold now ends protection only; the family must continue/settle rather than terminate en masse.
- Added/retained physical offset-lane grammar checks and main-only fail-fast materialization before local/component work.
- Fixed a failed-preflight repair state leak: an exhausted rollback/regrow attempt can no longer leave the offending main child active with mutated history.
- After genuine causal reroute is exhausted, a shared-prefix child whose inherited physical lane is already long and grammar-clean may terminate at that last valid prefix checkpoint instead of deleting the lane or discarding the entire logical sample.
- Fixed connection-junction double-offset geometry: singleton lanes retaining a non-zero bundle offset are rebased to their exact materialized head before a physical connection leg is committed.
- Connection legs now obey the same visible 0/±45° turn grammar as ordinary routing; a junction may not manufacture a tiny terminal 90° kink.

## Hard geometry

- Direct 90° pathway turns are proposal/materialization rejection conditions for main and local pathways.
- Pathway bodies remain straight-segment polylines only; curved/Bézier pathway bodies are forbidden.
- Unauthorized intersections, unmarked overlaps, and missing visible main launches remain hard failures.

## Honest local-gap service

- Increased connected residual analysis to 56×56.
- Replaced inflated local coverage halo with visible stroke + legitimate allocated spacing/perimeter only.
- Replaced expensive polygon-union coverage accounting with deterministic 4×4 subcell raster occupancy; service width is unchanged.
- Abandoned/pruned local routes are removed from both service accounting and collision occupancy.
- Fixed allocation that allowed a few large rooms to monopolize nearly all local sources; substantial regions receive distributed opportunity before extra sources are area-weighted.
- Added region-specific minimum useful lengths so small/medium pockets can retain appropriately short visible fillers instead of being generated and discarded.
- Made singleton local branching effective while preserving independent births, temporary 50% encounter bundling, and the existing local branching/exit tendencies.
- Added a dedicated lightweight synchronous local-growth loop so decorative fillers do not pay full cross-chip causal-search/permutation cost.
- Added bounded grid-run mop-up for long still-unserved straight/diagonal runs in substantial rooms.
- Local target is now a board-level `40–43%`; it deliberately does not require every residual cavity to contain a line.
- Local-to-local spacing is thickness-aware and components preserve the same pathway keepout around local traces as main traces.

## Gap-aware components

- Increased component residual field to 56×56.
- Removed the old inflated component service halo and one-object-serves-whole-room accounting.
- Added substantial/mandatory versus optional thin/sliver residual regions.
- Optional tiny/thin pockets may remain empty; feasible ones may receive micro fillers without clearance exemptions.
- Component acceptance now uses the minimum of substantial-region area representation and area-weighted size×quantity capacity.
- Large regions require multiple capacity units; large/medium/small/micro component sizes are selected from actual gap scale and local clearance.
- Added bounded per-instance gap adaptation (90%→80%→75%) for an oversized generated collection that otherwise cannot fit its assigned usable room.
- Component failure remains component-only and never restarts routing.
- Historical collection scale/quota validation remains a pre-route template-language invariant. Bounded per-gap instance shrinkage is not reinterpreted as a late failure of the source collection scale distribution.

## Collision/runtime fixes

- Added accepted-component spatial broad-phase indexing.
- Removed an accidental global all-to-all distance scan from dense filler ranking.
- Replaced pathological topology-union use for large multi-primitive component collections with collision geometry collections / primitive-set checks.
- Replaced full-board pathway keepout intersection in the component hot loop with a spatial index of individually buffered nearby pathway groups.
- Tightened terminal attachment validation so permission to contact one terminal cannot mask contact with another nearby pathway.
- Final unauthorized component/pathway overlap and component-component clearance audits use spatial broad-phase plus exact local checks.

## Semantics preserved

- Main chips route before secondary components exist.
- Local gap paths route before components.
- Components never steer or reroute pathways.
- Same seed/settings remain deterministic by design; no time-dependent visual degradation or global A* was introduced.
- Historical release records remain unchanged.
