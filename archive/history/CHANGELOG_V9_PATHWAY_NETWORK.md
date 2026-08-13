# CHANGELOG V9 — PATHWAY NETWORK

- Replaced sparse 2–6-line pathway launches with chip-side-span-derived dense launch bundles.
- Launch bundles now occupy a large fraction of the source chip side when feasible.
- Replaced independent line-segment turns with continuous polyline traces.
- Enforced visible turn delta of only 0° or ±45° between consecutive segments.
- Added recursive multiplicity-driven bundle splitting, including repeated splits down to small bundles and occasional singleton traces.
- Added intentional branch-junction allowance so valid children are not rejected for sharing the parent branch point.
- Blocked wide bundles now split before termination rather than producing source-adjacent stubs.
- Increased minimum pathway journey length and board-scale traversal.
- Added cross-chip launch goals and natural encounter logic for frequent pathway-to-pathway connections.
- Kept pathway-to-collection connection as a rarer event.
- Kept true termination markers as hollow/filled circles and intersection markers for rare overlaps.
- Rebalanced path collision broad phase with a spatial hash and conservative bundle envelopes for tractable dense routing.
