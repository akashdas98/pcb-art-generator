# V41 — Tall-Canvas Octilinear Escape-Clipping Fix

## Problem

Extreme portrait canvases such as 1200×6248 through 1200×8046 could be rejected during strict pathway materialization with one `pathway_non_octilinear_segment_count` even though the routed centerline itself obeyed the 0/45-degree grammar.

## Root cause

When an escaped trace crossed the frame through a final fragment shorter than 0.10 routing module, `_clip_escaped_polyline_to_frame()` removed that microscopic tail by replacing the previous vertex with the *current fragment's* frame crossing. If the previous leg was diagonal and the tiny escape leg was horizontal/vertical, the replacement moved only one coordinate of the diagonal endpoint and manufactured a non-octilinear visible segment.

A reproduced 1200×6248 seed-1 trace contained the legal tail:

- diagonal to `(1198.022..., 2243.559...)`;
- tiny horizontal continuation beyond the right frame.

V40 replaced that point with `(1200, 2243.559...)`, skewing the preceding 45-degree segment. The final audit correctly rejected the result.

## Fix

For a microscopic final escape fragment, V41 now:

1. reads the exact heading of the previous visible leg;
2. extends that leg along the same octilinear heading to its own first frame crossing;
3. uses that frame point as the visible endpoint;
4. leaves the exact-octilinear and <=45-degree audits unchanged.

No routing probability, component rule, fill target, clearance, or audit threshold was relaxed.

## Tests and acceptance

- Added active regression `test_tall_canvas_micro_escape_cleanup_preserves_octilinear_previous_leg` for heights 6248 and 8046.
- Replaced V40's source-equivalence test with fresh V41 acceptance-snapshot coverage because renderer behavior changed.
- Added optional real tall-main-network stress coverage for 1200×6248 and 1200×8046, seed 1.
- Fresh V41 reference and difficult samples both report zero non-octilinear segments, illegal turns/junctions, and rendered clearance violations.
