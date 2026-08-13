# CHANGELOG V10 PATHWAY ROUTING FIXES

- Pathways now always emerge perpendicular to the chip side they launch from.
- Every chip now emits on all four sides.
- Launch bundles use chip outer bounds so emitted traces do not overlap the main chip group geometry.
- Path-path and path-object accidental overlaps were tightened out of the router.
- Split children now inherit branch direction according to their lateral order within the parent bundle, reducing sibling self-intersection.
- Connection behavior to earlier-chip pathways was strengthened, and collection connections remain rarer.
- Added regression coverage for four-side emission, perpendicular launch direction, continuous 45-degree turns, and no pathway/object intersections.
