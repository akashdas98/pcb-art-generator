# Recovery checkpoint — 2026-08-26 21:41 IST

## Authority

- Packaged production remains the 16:31 renderer at SHA-256 `f3b3179921db023fa8160885275244779190836015fdd4676e9cafe690bd7f90` until the candidate below finishes exact-seed qualification and is explicitly promoted.
- Current unpromoted candidate renderer SHA-256: `c80480724343f4a09286d2fde861ce60b6f8c73a77a59e49aba32f01e1e34d75`.
- Correctness is OPEN. Do not describe this candidate or packaged production as error-free yet.

## Candidate contents

The candidate preserves the 4-module cumulative MAIN survival floor while keeping early turns legal. It contains two linked correctness repairs exposed by the exact production seed `9409060408987575905`:

1. Source-egress reservation/replay follows the actual survival geometry. Once a root first reaches four physical modules through a bend, its actual bent survival prefix becomes the replayable certificate. A never-mature under-floor partial bend rewinds to emergence before the original straight fallback reservation is consumed.
2. MAIN stalled-side preflight repair keeps the existing forward extension / outer-lane peel first. If those fail, singleton repair transactionally regrows from progressively earlier checkpoints. It can now also truncate only the affected child's own inherited visible prefix when the dead geometry is entirely in `prefixes[tid]` and no owned `route_history` exists. Failed attempts restore a fresh original snapshot; sibling/parent geometry and the existing side-progress threshold are not weakened.

Permanent regressions added for:
- under-floor early-turn final settlement,
- replay of a mature bent survival prefix after deep traceback,
- dead-head owned-tail rollback/regrow,
- inherited-prefix-only child rollback/regrow.

The prior continuation reported the complete candidate gate as **166/166 release tests PASS + stress 1/1 PASS**. No older regression was weakened.

## Exact production-seed qualification in progress

- Logged internal sample seed: `9409060408987575905`.
- Recovered base seed for logical sample 0: `8528317405406420078`.
- Fixture: MAIN-only, `1:6 @ 0.35`.
- Durable process: `/mnt/data/exact_main_replay.py`.
- At checkpoint time the exact process was still RUNNING at ~8:00 CPU, one core saturated, with zero stderr/output/result bytes so far.
- Acceptance requires actual completion with `pathway_main_stalled_side_count == 0`, zero short MAIN terminations, and zero unresolved persistence debt. Merely surviving longer is not a pass.

## Next action

Do not modify the candidate while the exact replay is running. Poll the existing process to completion. If it passes, rerun the canonical 166-test release gate + stress on this exact final source, promote explicitly, update authority docs, and package. If it fails, preserve the new exact error and continue the same correctness branch without reseeding or relaxing invariants.

## Exact replay completion — FAIL

The durable exact replay completed after ~599.87 CPU-s / 600.12 wall-s and **FAILED** at MAIN preflight. The original source-egress exception did not recur, but `pathway_main_stalled_side_count` remained `2` on the exact board. Full machine-readable result is preserved at `work/inflight/evidence/20260826_exact_seed_9409060408987575905_prefixaware_FAIL.json`.

Key evidence:
- `pathway_launch_trace_count == pathway_visible_launch_trace_count == 4131`.
- no short-termination, octilinearity, static-intersection, overlap, or clearance violations.
- two stalled roots remain: `[74,1,"left"]` and `[81,2,"bottom"]`.
- their surviving candidates are child fronts with visible lengths roughly 4–6 modules.
- `preflight_prefix_checkpoints == 0`; the new inherited-prefix fallback did not engage on the real stalled-side representation.

Therefore candidate SHA `c8048072...34d75` is **UNPROMOTED / INCOMPLETE**. Next diagnosis must trace why `_repair_main_stalled_side_progress()` is not reaching the actual rendered-prefix owners for those two roots. Do not add another recovery algorithm until that representation/selection mismatch is understood.

## 22:45 IST continuation status

After the exact replay failure above, a small-fixture experiment confirmed that a routed `BundleGesturePlanner` can be serialized and restored with its live routing/materialization state. The intended next step was therefore changed from repeated full-board reruns to one exact-board **pre-preflight planner snapshot**, allowing the two stalled-side repair paths to be debugged repeatedly without rerouting the whole `1:6 @ 0.35` board.

An exact-board snapshot build was started and observed healthy for roughly three minutes CPU, but that process/output did **not** survive the subsequent runtime boundary. At 22:45 IST there is no live renderer/snapshot process and no durable planner pickle/result from that attempt. No renderer source changed during the snapshot attempt. Candidate SHA remains `c80480724343f4a09286d2fde861ce60b6f8c73a77a59e49aba32f01e1e34d75`.

Next continuation should create the durable exact preflight snapshot first, then inspect the actual stalled-front ownership/selection mismatch from that frozen state.
