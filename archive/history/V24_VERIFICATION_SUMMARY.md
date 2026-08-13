# V24 verification summary

## Focused regressions

The frozen V24 code passes the core bundle-geometry regression and the bounded-local-holistic connection/recovery regression in fresh processes. On the 1200×1200 reference seed they complete in roughly 18–19 seconds each in this environment.

Verification uses a per-sample timeout allowance; multi-sample runs receive a proportional total wall-clock allowance rather than reusing a one-sample cap.

## Reference local-gap probe (seed 12345)

Observed after final tuning:

- local sources: 13
- planned local traces: 28
- visible local traces: 15
- local split events: 3
- special thick planned share: 25%
- local second-pass round budget: 24 (+ up to 6 persistence rounds)
- hard geometry violations: 0

## Hard-seed probes (base seed 20260806)

Sample 0:
- local sources: 13
- planned local traces: 30
- visible local traces: 23
- local split events: 8
- special thick share: 23.3%
- static intersections / thick-stroke overlaps / zigzags / tiny deaths / marker overlaps: all 0

Sample 1:
- local sources: 13
- planned local traces: 31
- visible local traces: 17
- local split events: 3
- special thick share: 22.6%
- hard geometry metrics observed before the execution-wrapper cutoff were clean.

Sample 2:
- local sources: 13
- planned local traces: 26
- visible local traces: 15
- local split events: 3
- special thick share: 26.9%
- static intersections / thick-stroke overlaps / zigzags / tiny deaths / marker overlaps / duplicate cleanup / intersection cleanup: all 0

These populations and percentages are observations of deterministic seeded outcomes, not acceptance quotas.
