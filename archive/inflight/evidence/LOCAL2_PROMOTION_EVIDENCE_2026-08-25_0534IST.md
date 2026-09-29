# LOCAL-2 candidate status — 2026-08-25 05:34 IST

## Authority

Production remains LOCAL-1 at SHA-256 `325e2ec0c79d2ec7a051c9c08b2abba73c6fab5c5561a665a2c4d16dec85acf2`.
The sole inflight candidate is `work/inflight/v48_local2_candidate.py`, SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`.

## Rejected LOCAL-2 approaches

1. Debt-proportional per-wave candidate cap: REJECT. Governing debt still consumed the full cap; no work reduction.
2. Monotonic cell frontier across the existing three waves: REJECT. Nearly every admitted debt cell legitimately changed state and re-entered; candidate tokens stayed at 19,200 on the long proxy.
3. One campaign without deterministic-tail optimization: MODIFY. It removed the three-wave cliff but exposed expensive exact deterministic completion at 0.5, worsening normalized LOCAL CPU/work growth.

## Current candidate

Current candidate combines:

- one stochastic debt-rescue campaign instead of reopening the whole debt field for three complete waves;
- exact caching of the deterministic debt-completion first-leg legality result while varying only the second leg.

The cache does not alter candidate order, geometry admission, legality, service targets, or seed ownership.

## Ordinary 0.75 -> 0.5 qualification

Across governing seeds 102 + 104:

| Metric | Production | Candidate |
|---|---:|---:|
| LOCAL useful-work growth (`pathway_local_gap_trace_count`) | 2.2458x | 2.3208x |
| LOCAL CPU growth | 2.4824x | 2.4177x |
| **LOCAL CPU/work growth** | **1.1054x** | **1.0418x** |
| whole-render CPU growth | 2.9022x | 2.9491x |
| **whole-render CPU/work growth** | **1.2923x** | **1.2707x** |
| partial-rescue tokens, 0.75 | 3,201 | **1,067** |
| partial-rescue tokens, 0.5 | 9,600 | **4,800** |
| deterministic completion candidates, 0.5 | 35,759 | **22,886** |
| first-leg cache hits, 0.5/102 | 0 | **5,287** |

All ordinary fixtures remain above the 0.80 LOCAL service hard floor and have clean hard correctness counters. Geometry can differ in the rescue tail because the rescue scheduling policy itself is the optimization target.

## Long 1:6 @ 0.75 proxy — completed after prior response

Production vs current candidate, same seed/harness:

| Metric | Production | Candidate |
|---|---:|---:|
| partial rescue waves | 3 | **1** |
| partial candidate tokens | 19,200 | **6,400** |
| deterministic completion candidates | 0 | **15,565** |
| deterministic completion traces | 0 | 27 |
| first-leg cache hits | 0 | **5,706** |
| LOCAL service fraction | 0.806398 | **0.800341** |
| LOCAL traces | 2,392 | **2,096** |
| visible LOCAL traces | 1,085 | **1,061** |
| LOCAL CPU (single host run; diagnostic only) | 50.706 s | 46.971 s |
| total CPU (single host run; diagnostic only) | 110.687 s | 101.149 s |
| peak RSS | 291,052 KiB | 287,888 KiB |

The candidate removes the diagnosed three-wave work cliff, but the long proxy ends very near the hard 0.80 service floor and has ~12.4% fewer total LOCAL traces. This is a **behavioral qualification question**, not an automatic promotion win. Next substantive step is to compare the actual LOCAL output/population distribution and determine whether this is legitimate debt-efficient completion or unacceptable thinning of the design language. Do not run release/stress or promote until that question is answered.

## Scale cadence

No routine 0.35 run is permitted during this ordinary LOCAL-2 stage. 0.35 remains reserved for the end of the full optimization phase.
