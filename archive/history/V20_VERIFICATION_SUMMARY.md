# V20 verification summary

The expensive full static-board historical suite was not rerun end-to-end in this editing pass because V19 full sample generation exceeds the execution wrapper on this environment. Routing was instead exercised against the finalized V19 reference static board using two deterministic pathway seeds, plus Python syntax compilation of renderer/tests.

## Reference pathway seed

- launched / visible traces: **119 / 119**
- visible minimum chip-side launch coverage: **0.7374**
- ordinary trace thickness range observed: **2.007–3.075U**
- minimum launch edge-gap / adjacent mean-thickness ratio: **1.520**
- late-life branch evaluations: **8**
- physical cross-chip joins: **2**, both mandatory close-head joins
- minimum foreign-static trace clearance: **9.051U** against required **8U**
- tiny termination traces (<2.75 modules): **0**
- unmarked centerline intersections: **0**
- collapsed/doubled centerlines: **0**
- unmarked thick-stroke overlaps/touches: **0**
- mid-line connections: **0**
- multiply-connected traces: **0**
- final intersection cleanup suppressions: **0**
- final duplicate cleanup suppressions: **0**

## Alternate pathway seed on the same static board

- physical cross-chip joins: **1** mandatory close-head join
- visible minimum chip-side launch coverage: **0.7231**
- minimum launch edge-gap ratio: **1.509**
- minimum foreign-static clearance: **9.132U**
- all crossing/overlap/duplicate/mid-line/multiple-connection/tiny-termination audits: **0**

The routing-only probe is deliberately not presented as a substitute for the complete historical regression suite; it validates the V20 changes and the new hard rendered-geometry invariants directly.
