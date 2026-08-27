# MAIN run-length knob qualification — 2026-08-27

Final renderer SHA-256: `5d8624de9d2b5ec5b5ba7dac7fed169653074d7301751f8b1b1558e870dba98b`

## Contract

- `--main-run-length-multiplier`: inclusive **0.2..3.0**, default **1.0**.
- Default `1.0` scales the existing sampled whole-route MAIN residency pool to **2x historical**; `0.5` reproduces historical residency; `3.0` requests **6x historical** residency.
- Per-gesture module lengths, turn grammar, clearance, proposal breadth, spatial search, reroute architecture, and LOCAL route life are unchanged.
- A geometrically legal foreign-main-chip head connection is successful immediately; voluntary journey termination waits until the existing connection arbitration has had first refusal.
- This is a geometry/workload control. No new global connection pass or broader search algorithm was added.

## Correctness / behavior qualification

- **183/183** active release tests PASS.
- Maintained geometry stress: **1/1 PASS**.
- Permanent regressions cover whole-route scaling/local invariance, high-knob shared-clock capacity, and cross-chip connection before voluntary journey termination.
- Production smokes at multipliers `0.2`, `1.0`, and `3.0` all pass with zero stalled sides, short MAIN terminations, or unaccounted launches.
- Two-chip production smoke (`1:1 @ 0.75`, seed 102, default run multiplier) passes with **7 cross-chip connections / 14 connected traces**, zero hard defects.

## Normalized 0.75 -> 0.5 scaling

Governing seeds: `102 + 104`; aspect `1:1`; chip density multiplier `1.0`. CPU is MAIN process CPU. Composite work tokens = gesture-clear checks + lookahead evaluations + local-space capacity evaluations + holistic connection-pair work. The categories are retained separately below; the composite is a stable workload denominator, not a claim that every token has identical unit cost.

### BEFORE — density authority / historical run residency

| Category | 0.75 work | 0.5 work | Work growth | CPU/work growth |
|---|---:|---:|---:|---:|
| Gesture legality checks | 24,570 | 57,518 | 2.341x | 0.911x |
| Lookahead evaluations | 22,940 | 49,224 | 2.146x | 0.994x |
| Local-space capacity evals | 11,495 | 24,194 | 2.105x | 1.013x |
| Connection-pair work | 1,424 | 3,394 | 2.383x | 0.895x |
| **Composite routing work** | **60,429** | **134,330** | **2.223x** | **0.959x** |

MAIN CPU: `7.492s -> 15.976s` = **2.133x**.

### AFTER — run multiplier 1.0 / 2x historical residency

| Category | 0.75 work | 0.5 work | Work growth | CPU/work growth |
|---|---:|---:|---:|---:|
| Gesture legality checks | 24,697 | 58,672 | 2.376x | 0.972x |
| Lookahead evaluations | 22,929 | 50,366 | 2.197x | 1.051x |
| Local-space capacity evals | 10,389 | 23,081 | 2.222x | 1.040x |
| Connection-pair work | 1,709 | 3,969 | 2.322x | 0.995x |
| **Composite routing work** | **59,724** | **136,088** | **2.279x** | **1.014x** |

MAIN CPU: `7.283s -> 16.822s` = **2.310x**.

### HIGH — run multiplier 3.0 / 6x historical residency

| Category | 0.75 work | 0.5 work | Work growth | CPU/work growth |
|---|---:|---:|---:|---:|
| Gesture legality checks | 32,845 | 73,832 | 2.248x | 0.988x |
| Lookahead evaluations | 31,969 | 64,362 | 2.013x | 1.103x |
| Local-space capacity evals | 14,461 | 30,037 | 2.077x | 1.069x |
| Connection-pair work | 2,313 | 5,032 | 2.176x | 1.021x |
| **Composite routing work** | **81,588** | **173,263** | **2.124x** | **1.046x** |

MAIN CPU: `9.333s -> 20.724s` = **2.221x**.

## Decision

**ACCEPT / PROMOTE.** Default normalized CPU/work is `1.014x`; the maximum supported run multiplier is `1.046x`. Both remain close to linear. The preceding authority measured `0.959x` in this isolated fixture; that favorable sublinear point is retained in the record rather than hidden. The renderer diff does not change the lookahead, local-space, clearance, proposal, spatial-index, or reroute algorithms, so the small shift is attributable to the changed geometry/work mix and measurement noise rather than a broader algorithmic implementation. High multiplier does not introduce a new asymptotic path.

Production authority may therefore move to the final renderer hash above.
