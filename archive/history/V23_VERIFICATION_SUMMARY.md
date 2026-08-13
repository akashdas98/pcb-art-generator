# V23 verification summary

## Focused regression results

The following focused tests pass on the frozen V23 code:

- exact collection quota assignment;
- capacitor singleton-family generation and widened radius distribution;
- 100% isolated-capacitor occurrence path with retained independent 1–3 count variation;
- isolated capacitor placement/clearance;
- secondary-component/main-chip moat;
- core bundle-gesture pathway geometry and local-gap integration;
- bounded-local-holistic connection/recovery behavior;
- source/terminal hollow-marker clipping;
- special local singleton thickness audit.

## Fixed-seed hard-geometry probes

Three `20260806` arbitrary sample-index probes were run separately. Each reported:

- `pathway_static_intersection_count = 0`
- `pathway_unmarked_overlap_count = 0`
- `pathway_collapsed_overlap_count = 0`
- `pathway_unmarked_stroke_overlap_count = 0`
- `pathway_compensating_zigzag_count = 0`
- `pathway_tiny_termination_trace_count = 0`
- `pathway_midline_connection_count = 0`
- `pathway_multiply_connected_trace_count = 0`
- `pathway_termination_marker_overlap_count = 0`
- `pathway_duplicate_trace_cleanup_count = 0`
- `pathway_intersection_trace_cleanup_count = 0`

Observed local special shares on those probes were **6.25%**, **7.14%**, and **8.33%**. These are measurements of the seeded best-effort outcome, not acceptance quotas.

## Reference visual probes

Three frozen-code visual samples are included with the release. They demonstrate:

- source dots at main-chip emergence points;
- sparse interior local-gap bundles;
- extra-thick singleton local traces;
- increased capacitor prevalence;
- visibly broader capacitor size range.

## Runtime note

On the 1200×1200 reference probe used during V23 development, the complete sample including the second local-gap phase completed in about **12–13 seconds** in this environment. The local phase uses a shorter bounded horizon and does not run a second full-board search.

A full duplicate-render determinism regression was not completed in the execution wrapper because some historical static seeds plus two full route passes exceed the wrapper timeout. V23 introduces no nondeterministic routing source: local-gap source selection, source-marker styles, and special-line selection all use deterministic SplitMix64 streams derived from the sample seed.
