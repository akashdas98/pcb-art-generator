# MAIN-1 O(1) lane-head formal qualification recovery

Status: **REJECT as a meaningful scaling optimization; unpromoted**.

Production SHA-256: `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`.
Candidate SHA-256: `8ca2b04d63ffd9565c9aa788499e2f4b00973912599f2950ec1ea05282c2ba0f`.

The previously interrupted formal qualification actually completed all four production/candidate fixtures; the raw JSON/stdout/stderr records survived outside the repo and are copied into `work/inflight/evidence/main1_lane_head_formal_2026-08-25_1141IST/`.

All four candidate fixtures are geometry-identical to production and have identical MAIN deterministic work counters. Aggregate 0.75 -> 0.5 useful emitted-segment work is `1833 -> 4610` for both sources.

Aggregate MAIN CPU:

- production: `9.791664988 -> 35.865799974 s`
- candidate: `9.859052742 -> 36.118660805 s`

Normalized MAIN CPU/work growth:

- production: `1.4564162486x`
- candidate: `1.4566593102x`

The candidate therefore does **not** improve the formal ordinary scaling curve; it is fractionally worse within timing noise. The adjacent long `1:6 @ 0.75 / seed 1` proxy had shown only a small candidate win (`45.45 s` vs adjacent production `46.08 s`) with identical geometry/work. That small proxy gain is not enough to justify promotion when the formal ordinary gate is flat/slightly worse.

Classification: **REJECT for MAIN-1 promotion**. Keep the architectural finding (full historical lane materialization is unnecessary merely to obtain a current lane head) as a possible future cleanup/constant-factor micro-optimization, but do not promote it as the long/fine scaling fix.

Next target remains the function-level MAIN profile: identify a higher-leverage source of proposal/recovery amplification or connection-state recomputation without changing routing semantics.
