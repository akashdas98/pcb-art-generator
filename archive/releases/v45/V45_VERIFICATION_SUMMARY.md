# V45 Verification Summary

**Release gate status: REVOKED / NOT PRODUCTION-READY.**

The 73-test active suite still passes, but the suite does not exercise the complete long-canvas `main_scale=0.35` production path through routing, residual filling, final acceptance, and SVG emission. A real `1200×6248 @ 0.35` render exposed algorithmic scaling failures that invalidate the previous PASS designation.

## What remains verified

- `logical_area = canvas_territory / main_scale²` population semantics;
- rotation-invariant logical-area math;
- fine-scale primary chip and prepared-component population growth;
- chip spacing proportional to scaled design geometry rather than a raw-canvas moat;
- deterministic seeds and exact 0/±45-degree pathway grammar in covered fixtures;
- the real `1200×1200 @ 0.35` main-network case used for the prior square evidence.

## What is not verified and currently fails production viability

- complete `1200×6248 @ 0.35` accepted SVG emission;
- complete `1200×8046 @ 0.35` accepted SVG emission;
- normalized wall-clock and peak-memory performance for full fine-scale long boards;
- scale-linear behavior of component calibration/uniqueness, main-router global bookkeeping, terminal cleanup, and residual placement.

The first real long fine-scale render exposed a combinatorial prepared-collection calibration DP whose source still assumes `N<=18`; true zoom produces about 699 collections on the inspected 1200×6248 case. After bypassing that defect diagnostically, whole-population uniqueness retry and superlinear main-router/terminal bookkeeping remained.

See [`V45_SCALE035_FORENSIC_AUDIT.md`](V45_SCALE035_FORENSIC_AUDIT.md) for measured evidence and the complete hotspot inventory.

## Active test result (informational only)

```bash
python run_release_tests.py
```

Result remains **73/73 active tests passed; 0 failures/errors/skips/xfails**, but this is **not sufficient for release** until the missing full-production performance/acceptance gates are added and pass.

Historical V44 remains under `archive/releases/v44/`.
