# V32 — Source-Egress Family Protection and Materialization Consistency

V32 is a routing-correctness release. It preserves V31 transactional parallel rounds and V30 route-first runtime architecture while closing the remaining premature-main-line death paths.

## Active changes

- Main-chip source buses remain straight and structurally indivisible until the shortest physical lane clears 4 routing modules from the chip. This applies even to single-cohort sides.
- Source maturity is derived from current physical lane length. Traceback below the boundary reactivates launch protection and per-lane egress reservations.
- Temporary per-lane egress reservations prevent mature/foreign routes and local fillers from stealing a still-emerging lane's corridor; young-vs-young main families remain transactional peers.
- Protected same-family conflict transactions may atomically HOLD some siblings for a round. Local-only conflict transactions may also HOLD, preventing all-or-nothing gesture-zero deadlocks.
- The bundle proposal corridor uses a flat leading edge; turn/miter clearance remains conservative.
- The gesture-start ownership disk no longer hides foreign committed geometry near the current head. Self/ancestor continuation alone receives that exemption.
- Main routes below 4 physical modules cannot be terminalized/pruned. Routes that just clear source egress receive one bounded soft persistence attempt toward 6 modules without creating a hard runtime quota.
- Escaped polylines are rendered only to their first frame crossing. Invisible off-canvas continuation cannot cause final collision cleanup to suppress an otherwise valid visible trace.
- Terminal backoff/hollow-marker clipping cannot manufacture a sub-0.10-module visible final segment; a filled marker is used when hollow clipping would do so.
- Legal connection-junction overlap radius is thickness-aware in both exact connection validation and final render audit, including extra-thick local traces.
- Main-launch survival and main-short-terminal metrics are explicitly reported, and unequal launched/visible main counts now reject the routing result instead of silently shipping cleanup loss.

## Local-gap consequence

The stricter main geometry changed residual topology and exposed an all-or-nothing deadlock in local waves. V32 permits atomic HOLD in local-only conflict groups. This restores the existing ~38–42% target without increasing global search or simply multiplying source count.

## Non-changes

- No A* or global route search.
- No secondary components during routing.
- No change to the V29 capacitor-size rule, local branch multiplier, local exit factor, component-fill target, or independent `main_scale` argument.
- Historical changelogs and verification records are not rewritten.
