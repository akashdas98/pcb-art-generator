# v27 execution audit

Purpose: identify places where an exact program cannot be derived from v27 without either resolving a contradiction or making an implementation choice.

## Resolved contradiction: exact special-family quotas vs filler sampling

v27 says:
- `N_ic = round(0.625*N)` is exact,
- `N_dense = round(0.650*N)` is exact,
- later acceptance requires those exact quotas,
- but the family filler table also allowed IC/dense to be sampled into collections outside the preselected quota index sets.

Literal execution therefore increased IC/dense counts above the exact quotas and caused the final validator to reject almost every sample.

Resolution in the renderer-consistent sheet:
- quota index sets are exclusive membership sets,
- remaining slots are filled from square/circle/dot/dash only,
- infeasible tier/family-count states restart rather than exceeding a quota.

This follows the document's own rule that numeric hard constraints win conflicts.

## Existing under-specification 1: M2 `compact matrix`

v27 provides:
- probability,
- radius,
- rows,
- columns,
- x/y pitch,
- fit reduction order,

but does not provide a geometric rule that makes `compact matrix` distinct from `filled grid` after those same row/column/pitch values are sampled.

Current renderer behavior:
- both use the authorized sampled lattice;
- perimeter mode alone omits interior points;
- no new matrix-specific geometry is invented.

Consequence: `compact matrix` currently has no distinct topology from `filled grid`. A distinct numeric construction requires an explicit future design-language rule.

## Existing under-specification 2: M7 short-line orientation

v27 specifies short-line probability, rows, columns, pitch, line length, and stroke, but no orientation distribution for those M7 lines.

Current renderer behavior:
- M7 short lines are horizontal.

This is isolated in the implementation and should be replaced if/when an explicit M7 line-orientation rule is added to the sheet.

## Existing under-specification 3: separate-multiple IC relative arrangement

v27 specifies:
- 2 or 3 separate ICs,
- each may vary individually,
- visible full-terminal edge gap `4U–8U`,
- they must not touch,

but does not specify the topology/orientation of those separate placements inside the IC subgroup.

Current renderer behavior:
- a 1-D separated arrangement is used,
- horizontal/vertical is 50/50,
- the required full-terminal visible gap is preserved.

The 50/50 arrangement is an implementation choice, not a rule claimed to come from v27. A fully source-locked renderer needs an explicit rule here.

## Implementation fidelity notes

### Collection packing
The renderer centers subgroup AABBs exactly as §14 specifies. Candidate clearance is not approximated: the implementation observes that the specified `d = r_C + r_G + Uniform(3U,8U)` uses radii of circles enclosing each complete AABB, so every candidate is already guaranteed at least 3U geometric separation. It therefore avoids constructing temporary Shapely geometry for 64 rejected/scored candidates.

### Collision
Full accepted objects use stroke-expanded Shapely collision regions. Global placement uses a spatial-hash broad phase followed by exact intersection/distance checks.

### Scale
No hidden scale correction is used. Collections are regenerated/selected from retry streams until the batch footprint constraints pass.

### IC arrays
Array cells are exact duplicates and center pitch is computed from body dimension plus twice normal terminal length. Required matching terminal tips are algebraically verified; failures reject validation.

### Uniqueness
Completed collection fingerprints are computed before global placement and registered across all samples from one renderer instance. Near-duplicate RMS filtering is applied only against structurally matching buckets.

### V16 pathway interpretation

V15 is not an input to this package. Its A* searches, accepted-candidate seed stream, realized
connectivity quota, planarization patches, and synthetic rendezvous nodes were discarded.

The active pathway pass interprets the behavioral percentages as attempt probabilities. It does
not move static objects, reject a board, or advance to another pathway seed when the static layout
prevents a preferred outcome. The report fields
`pathway_candidate_seed_retry_count` and `pathway_route_search_count` are therefore hard-coded
architecture assertions and must remain zero.

The planner's coarse perception consists of static Shapely occupancy plus a 12×12 underused-region
map. It scores only straight and adjacent 45-degree bundle gestures; this map is not a fine route
grid. Exact stroke-expanded geometry remains authoritative for acceptance.

`pathway_cross_chip_connection_count` records only explicit trace-to-trace contact points stored
in the connection graph. Proximity is an opportunity to split or approach, not a successful join.
Sub-module geometry is permitted only for an audited terminal connection alignment. All ordinary
center-corridor gestures remain at least two sampled modules long, apart from the one-module
crowded launch fallback.

## V19 execution note

V19 fixes the placement broad-phase radius so pairwise chip-secondary clearance checks are queried over the full configured 170U moat. Main-chip frame inset is 120U. Pathway foreign-static keepout is 4U beyond the full corridor stroke envelope. Branching uses a seeded 1.50–1.80 multiplier over the V18 base appetite. Repair budget is seven attempts with progressive traceback up to six gestures; exhausted bundles preferentially fragment into singleton lane fronts rather than terminating together.
