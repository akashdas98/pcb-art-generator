# V39 changelog — exact octilinear junctions, rendered clearances, and source dots

## Why

V38 greatly improved local-line articulation, but two visual legality leaks remained: rare line-line clearance
violations and apparent 90-degree corners. Main-chip emergence dots had also disappeared.

The 90-degree cases were real network-level connection corners: each participating polyline was individually legal,
but a head-to-head connection could combine their terminal headings into an L. V38's final turn audit was
per-polyline and therefore could not detect that through-junction angle. V38 also used nearest-octant quantization as
part of its turn diagnostic, which was insufficient as a structural legality proof.

The remaining clearance cases were render-time differences between flat-ended planning corridors and visible thick
round caps.

## Changes

1. Added exact octilinear segment classification. Non-octilinear pathway segments are illegal.
2. Enforced 0/±45-degree turn grammar at proposal, commit, recorded-path, materialization, and final audit stages.
3. Added head-to-head connection-junction grammar: traversing a connection may turn only 0/±45 degrees.
4. Added final rendered stroke-to-stroke clearance auditing outside bounded legitimate junction envelopes.
5. Added actual rendered primitive admission against frozen chips/components and previously admitted traces so thick
   round caps cannot intrude into required moats. Optional local fillers are discarded on failure.
6. Restored source dots to every visible main physical launch by tying them to the launch trace's original emergence
   point rather than final leaf parentage.
7. Expanded bent-only fragmented residual rescue across legal octilinear approach headings to recover coverage after
   rejecting formerly easy illegal junctions.
8. Kept seeded 80–90% local service as the target; hard acceptance requires at least 80% of post-component remaining
   service when exact geometry exhausts the sampled target.

No V37 coherent-component behavior or V38 articulation policy was intentionally weakened.
