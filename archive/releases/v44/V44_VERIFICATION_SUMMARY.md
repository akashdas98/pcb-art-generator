# V44 Verification Summary

## Release status

**PASS.** V44 is the verified scale-stationary fine-detail baseline.

Authoritative active gate:

```bash
python run_release_tests.py
```

Result: **73/73 active tests passed** with **0 failures, 0 errors, 0 skips, 0 expected failures, and 0 manifest drift**.

Optional additional-seed main-network stress:

```bash
python run_stress_tests.py
```

Result: **PASS** on three additional deterministic square main-network seeds, with all hard routing/geometry/cleanup counters zero.

## Production acceptance set

All committed acceptance artifacts are logical sample 0 and are stored under `examples/`.

- `V44_REFERENCE_*` — 1200×1200, `main_scale=1.0`.
- `V44_DIFFICULT_*` — maintained difficult 1200×1200, `main_scale=1.0`.
- `V44_EXTENDED_PORTRAIT_6248_*` — 1200×6248, `main_scale=1.0`.
- `V44_EXTENDED_LANDSCAPE_6248_*` — 6248×1200, `main_scale=1.0`.
- `V44_EXTENDED_PORTRAIT_8046_*` — 1200×8046, `main_scale=1.0`.
- `V44_SCALE035_PORTRAIT_6248_*` — 1200×6248, `main_scale=0.35`.
- `V44_SCALE035_PORTRAIT_8046_*` — 1200×8046, `main_scale=0.35`.

### Fine-scale extended proof: 1200×6248 @ 0.35

- main chips: **10**
- prepared collections: **86**
- chip long-axis quarters: **2 / 2 / 4 / 2**
- component long-axis quarters: **582 / 443 / 486 / 519**
- component residual service: **54.005%**
- local service of post-component remainder: **80.145%**
- visible main launches: **427 / 427**
- non-octilinear / illegal-turn / illegal-junction counters: **0**
- intersection / duplicate / zigzag materialization cleanup counters: **0**
- component↔pathway / local↔component / main↔local clearance violations: **0**

### Fine-scale upper proof: 1200×8046 @ 0.35

- logical sample: **0 directly; no batch skip/retry used**
- main chips: **13**
- prepared collections: **113**
- chip long-axis quarters: **3 / 3 / 4 / 3**
- component long-axis quarters: **617 / 762 / 567 / 692**
- service grid: **160 × 1073**
- component residual service: **54.004%**
- local service of post-component remainder: **80.083%**
- visible main launches: **541 / 541**
- non-octilinear / illegal-turn / illegal-junction counters: **0**
- intersection / duplicate / zigzag materialization cleanup counters: **0**
- component↔pathway / local↔component / main↔local clearance violations: **0**
- measured end-to-end acceptance runtime in this verification environment: **1933.652 s**
  - main routing: 142.625 s
  - component phase: 460.304 s
  - local phase: 1315.913 s

The runtime is substantial because `main_scale=0.35` intentionally emits far more real SVG detail; release support is defined by deterministic completion and the unchanged hard contracts, not by silently reducing population/service density.

## V44 corrections verified

- Service grids follow the actual design unit, so smaller `main_scale` gets finer honest service resolution.
- Main-chip/prepared-population opportunity remains governed by normalized canvas territory and is independent of `main_scale`.
- Residual detail capacity/work scales with design detail area instead of relying on scale-1 execution caps.
- Fine-scale main routing removes global singleton pairing, repeated same-round traceback index rebuilds, and repeated immutable proposal geometry work.
- Recovery-fragment inherited visible grammar is enforced from the child's first gesture.
- Incremental local target bookkeeping preserves the exact untouched/partial-service semantics without whole-field reconstruction per trace.
- Final local admission validates stroke plus source/terminal marker extent against frozen geometry.
- Main preflight intersection repair is causal per diagnosed pair: repair `new_front` first; only if it cannot repair may `old_front` be tried. One successful side ends the stale pair diagnosis.
- Acceptance tests explicitly require zero materialization intersection, duplicate, and zigzag cleanup—not merely zero final audit counters.

## Package gate

The release ZIP must contain the complete current repository, not a delta. After packaging, it is extracted into a clean directory and the authoritative active gate plus optional stress runner are executed again from that extracted package before handoff.
