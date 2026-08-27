> **RELEASE STATUS REVOKED:** premature main-chip pathway termination regression confirmed after visual inspection. See `V46_PREMATURE_MAIN_TERMINATION_AUDIT.md`. The functional/performance results below are diagnostic only and do not constitute release acceptance.

# V46 Verification Summary

**Current status: RELEASE CANDIDATE — correctness/production acceptance PASS; normalized runtime performance FAILS the intended near-linear territory scaling. V46 is not yet released.**

## Active behavioral/equivalence gate

- `python run_release_tests.py`
- **86/86 active tests passed**
- **0 failures / errors / skips / expected failures**
- Observed suite wall time: **10.718 s**

The suite includes the V46 aspect-ratio + scale API, logical-viewBox semantics, service/geometry rules, and differential/equivalence guards for optimized spatial/indexed predicates.

## Fresh V46 end-to-end production matrix

All four maintained cases use base seed `20260816`, one maintained logical sample, production generation through accepted SVG/report emission, and `--no-skip-deadlocks`.

| Case | Logical territory | Wall time | s / territory | Peak RSS | Component service | Local remainder service | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| `1:1 @ 1.0` | 1.000 | 8.55 s | 8.55 | 166.3 MiB | 59.67% | 82.26% | functional PASS |
| `1200:6248 @ 1.0` | 5.207 | 51.88 s | 9.96 | 239.0 MiB | 59.42% | 82.26% | functional PASS |
| `1:1 @ 0.35` | 8.163 | 89.23 s | 10.93 | 292.6 MiB | 59.39% | 82.16% | functional PASS |
| `1200:6248 @ 0.35` | 42.503 | **926.78 s (15:26.78)** | **21.80** | **899.9 MiB** | **59.24%** | **82.09%** | functional PASS; runtime scaling FAIL |

The critical long `0.35` case emitted an accepted **8.9 MB SVG** and report with:

- **85 main chips** versus expected 85.007; long-axis quarters `[23, 20, 20, 22]`.
- **696 prepared collections**.
- **3,556 main traces** and **401 cross-chip connections**.
- **0 stalled main-chip sides** and **0 short main-chip terminations**.
- Component service target `0.592371`; actual `0.592424`.
- Local remainder target `0.820770`; actual `0.820877`; sampled-target shortfall `0.0`.
- Zero non-octilinear segments, illegal turns, curves, static intersections, unmarked overlaps, unmarked clearance violations, forbidden intersections/touches, unauthorized component/pathway overlap, and local component-clearance violations.

## Performance verdict

Peak memory is consistent with approximately linear incremental growth after the renderer's fixed baseline. The original V45 large-N memory explosion is gone.

Wall-clock scaling is **not yet sufficiently stationary**. The first three cases cost about **8.6–10.9 seconds per logical territory**; the critical 42.5-territory case costs **21.8 seconds per territory**, roughly twice the normalized cost. That bend is too large to describe V46 as satisfying the intended "do more local work in proportion to logical territory" performance contract.

Therefore:

- **Functional/geometry/service production gate: PASS.**
- **Memory robustness gate: PASS.**
- **Normalized runtime gate: FAIL / further optimization required.**
- **V46 release status: NOT RELEASED.**

Canonical raw evidence is under `acceptance_v46/`, with the consolidated measurements in `acceptance_v46/benchmark_matrix.json`.
