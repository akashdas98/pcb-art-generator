# MAIN-1 Long/Fine Instrumentation Audit

Status: **ACTIVE AUDIT / NO PROMOTION YET**

Production baseline is the promoted LOCAL-2 renderer at SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`.

This document preserves the MAIN-1 evidence obtained after the 2026-08-25 05:44 IST LOCAL-2 checkpoint. The scratch instrumentation/candidate tree was lost in a subsequent runtime reset, so all candidate code described below is **unpromoted and must be reconstructed from production before further qualification**.

## Objective

Explain why long/fine canvases pay materially more MAIN CPU than their increase in emitted MAIN work, without changing routing policy, density, seed ownership, line-survival semantics, or geometry admission.

The audit deliberately used a `1:6 @ 0.75` long-aspect proxy rather than routine 0.35, preserving the optimization cadence while multiplying simultaneous chip families and long-board routing extent.

## Fresh square-vs-long findings

On the same seed and current production renderer, `1:1 -> 1:6 @ 0.75` showed roughly:

- emitted MAIN segment work: **~6.13x**;
- MAIN CPU: **~7.5x** in the clean baseline;
- gesture/lookahead work per emitted segment: **~26-29% higher** on the long board.

So some long-board tax is genuine proposal/recovery work amplification rather than only lower-level infrastructure overhead.

### Spatial-query locality did not collapse

Zero-policy-change instrumentation measured the cardinality beneath gesture/exact checks. Long-vs-square normalized by gesture showed approximately:

- path-query candidate records / gesture: **~+9%**;
- exact path checks / gesture: **~+7%**;
- conflict-query neighborhood size: approximately flat;
- static-chip candidates / gesture: lower on the long board.

Therefore the spatial broad phases are not becoming globally dense enough to explain the whole MAIN tax.

### Recovery amplification

Normalized by emitted MAIN segment, the long proxy showed approximately:

- reroutes scheduled: **~+20%**;
- traceback work: **~+22%**;
- reroute exhaustion: **~+50%**.

This aligns with the increased proposal/gesture work and indicates that long boards require more recovery/proposal effort per committed segment.

## Rejected first cleanup: redundant active-head snapshot rebuild

Audit found that an ordinary round constructs an equivalent active-head spatial snapshot three times: before branching, after branching, and then again immediately afterward despite no intervening motion between the second and third construction.

A candidate removed only the third semantically redundant rebuild. It preserved exact geometry and deterministic routing work on the governing 0.75/0.5 fixtures. An ordinary timing pass looked favorable (`0.75 -> 0.5` MAIN CPU/work about `1.487x -> 1.439x`), but an adjacent fresh long-proxy comparison disproved meaningful long/fine benefit:

- production long proxy: **48.03 CPU-s**;
- candidate long proxy: **48.55 CPU-s**;
- geometry/work: identical.

Classification: **REJECT as MAIN-1 optimization target**. It is legitimate cleanup but does not solve the diagnosed long/fine tax and must not be promoted as if it did.

## Function-level profile

The square profile showed `_proposal_variants` as the dominant MAIN CPU consumer, with `_propose`, holistic `_future_options`, `_gesture_clear`, corridor construction and proposal scoring beneath it.

Connection infrastructure was smaller overall, but one subpath scaled suspiciously on the long proxy:

- `_connect_singletons()`: about **9.92 profiled s long vs 1.03 s square**;
- `_connect_forced_close_lane_heads()`: about **2.81 profiled s long vs 0.25 s square**.

## Current smallest earned candidate: O(1) materialized lane head

Inside `_connect_forced_close_lane_heads()`, the production path materializes a lane's **entire historical offset polyline** simply to read its current endpoint for broad-phase forced-close head indexing.

That endpoint is exactly determined by the final centerline segment and lane offset. Full historical materialization is unnecessary until a rare pair reaches exact join validation.

The lost scratch candidate therefore replaced only the endpoint lookup with an exact O(1) helper conceptually named `_materialized_lane_head()`:

- derive the final lane endpoint from the last centerline segment plus the same lane-offset geometry used by full materialization;
- preserve the exact coordinate;
- preserve candidate ordering, spatial indexing, join opportunity, RNG and routing policy;
- retain full lane materialization for exact pair/join validation after the broad phase.

Initial square evidence before the reset:

- geometry hash: **exactly identical** to production;
- adjacent production CPU: **5.536 s**;
- candidate CPU: **5.390 s** (~2.6% lower).

The decisive `1:6 @ 0.75 / seed 1` candidate run had been launched but its result was not recovered before the runtime reset. Therefore this candidate remains **UNQUALIFIED / UNPROMOTED**.

## Next exact step

1. Reconstruct only the O(1) lane-head helper from current production; do not resurrect the rejected snapshot-cleanup candidate.
2. Verify exact endpoint equality against full materialization across representative lane offsets/directions.
3. Run the `1:6 @ 0.75 / seed 1` adjacent production/candidate proxy first. The candidate must preserve the exact geometry/work counters and show a real long-proxy CPU reduction.
4. Only if the long proxy earns it, run the formal ordinary qualification in mandated order: 0.75 first, then 0.5.
5. Apply the established categorized + overall BEFORE/AFTER work/CPU/CPU-per-work table and complete release/stress gates before promotion.
6. Do not run 0.35 routinely; reserve it for the end of the full optimization phase.

If O(1) lane-head extraction is flat on the long proxy, reject it for MAIN-1 and continue from the function-level profile toward incremental exact-lane/connection-state reuse rather than changing MAIN routing semantics.

## 2026-08-25 11:41 IST — O(1) lane-head candidate formally rejected

The reconstructed O(1) materialized-lane-head candidate survived at SHA-256 `8ca2b04d63ffd9565c9aa788499e2f4b00973912599f2950ec1ea05282c2ba0f`. The interrupted qualification had in fact completed all 0.75/0.5 production/candidate fixtures; raw records are retained under `archive/inflight/evidence/main1_lane_head_formal_2026-08-25_1141IST/`.

All four outputs are geometry-identical with identical deterministic MAIN work. Aggregate emitted-segment work grows `1833 -> 4610` for both sources. Aggregate MAIN CPU grows `9.791664988 -> 35.865799974 s` in production and `9.859052742 -> 36.118660805 s` in the candidate, giving normalized CPU/work growth `1.456416x` production vs `1.456659x` candidate. The adjacent long proxy had shown only a small `46.08 -> 45.45 s` candidate improvement. Therefore the change is **REJECTED as a meaningful MAIN-1 scaling optimization**: it is valid cleanup but does not improve the formal ordinary curve.

Do not promote this candidate. Continue from the function-level profile toward a higher-leverage source of repeated proposal/recovery or connection-state work, preserving MAIN routing semantics.

## 2026-08-25 12:24 IST — interrupted-run instrumentation recovered

The post-11:41 interrupted run left two instrumentation-only sources under `archive/inflight/`; production is still unchanged at `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`.

- `main1_conn_count_renderer.py` (`236f3b5299d0879a2d6b0b86c9fc71d47b7dbb15bd859fc925d5646f7dd6e398`) counts forced-close and singleton scan cardinalities, candidate-pair counts, and singleton join-geometry candidate visits.
- `main1_join_reject_probe_renderer.py` (`da7265215dbe42fa23faa5c65e1a3d3aa179ec9f71a3fc4f750584dd9e234bcc`) counts where singleton head-join candidates are rejected: junction clearance, minimum-leg length, side-A/side-B special clearance, compensating zigzag, or final precise join clearance.

These are **diagnostic probes, not optimization candidates**. No surviving result file establishes their long-vs-square counts, so no causal conclusion is claimed yet. The next step is to execute these probes on `1:1 @ 0.75` and `1:6 @ 0.75` using the same seed, compare counts per emitted MAIN work, and choose the next implementation target from measured amplification rather than hotspot rank alone.

## 2026-08-25 13:30 IST — recovery topology localized; future-envelope fallback is the active candidate

Production remains unchanged at SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`.

The post-12:24 diagnostic run progressed beyond the connection probes before the prior response ended. The exact scratch tree from that run was not packaged, so the active candidate source in this handoff was **reconstructed from the surviving implementation description against the authoritative production renderer**. Its source is `archive/inflight/main1_future_envelope_fallback_renderer.py`, SHA-256 `d2dfd5749bfec421bd88bc2c2670eb33e945a10663c4d6e1e5b5fbfa092100ba`. It is unpromoted.

### Connection scans were not the main amplifier

The long `1:6 @ 0.75` diagnostic was too slow on the current host to complete inside the command boundary, so MAIN-only aspect-ladder work was used instead. On `1:1 -> 1:3 @ 0.75`, MAIN CPU and gesture checks both grew about **3.59x**, nearly lockstep. Connection scan counts did not explain the excess. This shifted the target upstream from per-gesture connection cost to extra proposal/recovery work generation.

### Recovery topology is the upstream amplifier

On the same `1:1 -> 1:3` ladder, launch count grew only about **2.71x**, while:

- holistic-front rounds grew about **3.65x**;
- tracebacks grew about **3.38x**;
- rollback segments grew about **3.45x**.

Conflict arbitration amplified still more: unsolved atomic conflict groups grew **106 -> 408** (~3.85x), triggering roughly **272 -> 999** traceback repairs.

A proposal/future certificate-bank probe also showed thousands of revisited head states (`~2,792` proposal-cache revisits and `~2,479` future-cache revisits on the `1:3` probe), but the first representation retained retired path-record geometry and violated the intended lifetime/compaction architecture. A compact representation reduced exact gesture checks but worsened the normalized CPU curve. Both certificate-bank directions are **REJECTED**.

### Rejected exhausted-conflict policies

Two conflict-policy experiments were screened and rejected:

1. **Exhausted partial-HOLD / maximum compatible subset** — after reroute repair was exhausted, move a compatible subset and HOLD the rest. The first aspect proxy looked promising, but the governing 0.75 -> 0.5 qualification regressed normalized MAIN CPU/work from about **1.180x production to 1.442x candidate** because the changed topology accumulated extra rollback work. Rejected.
2. **Extra atomic variants before another round** — reuse the already-generated proposal pool to search additional full assignments. This solved only **3/35** exhausted groups on the square probe and **9/170** on the `1:3` probe while spending thousands of extra lookahead draws and worsening CPU. Rejected.

Neither experiment is production authority and neither should be resurrected without new evidence.

### Strong causal result: heuristic future envelopes dominate exhausted conflicts

A surgical probe separated conflict caused by committed/current proposal corridors from conflict caused only by `future_geom`, the heuristic one-step lookahead envelope.

Among exhausted conflict attempts:

- `1:1 @ 0.75`: **100 / 123 (81.3%)** already had a complete all-front assignment whose **current corridors** were mutually legal;
- `1:3 @ 0.75`: **569 / 620 (91.8%)** already had such a complete current-corridor assignment.

In other words, most exhausted groups were not blocked by geometry that would be committed this round. They were being rejected because hypothetical best-next-step envelopes overlapped, which then triggered traceback/rollback and another round of proposal/lookahead work.

### Active candidate: future-aware first, exact-current full-assignment fallback

The earned candidate preserves the existing future-aware solver as the primary arbitration rule. **Only if that solver has no complete solution**, it retries the same full atomic group using exact current proposal-corridor compatibility, with these hard limits:

- every front in the group must still move; there is no partial winner set;
- there is no sequential commit-order ownership;
- current exact proposal clearance is unchanged;
- a proposal is eligible for the fallback only when its holistic lookahead found at least one individually legal future option (`future_option_count > 0`);
- `future_geom` remains a ranking/planning heuristic; it simply cannot force rollback by itself after the future-aware full assignment is exhausted when a complete exact-current assignment exists.

The reconstructed source implements exactly that bounded fallback and adds only diagnostic counters for fallback groups/fronts.

### Surviving first proxy evidence from the prior run

The prior unbundled run reported the following MAIN-only seed-1 `0.75` proxy:

| Metric | Production `1:1` | Production `1:3` | Candidate `1:1` | Candidate `1:3` |
|---|---:|---:|---:|---:|
| MAIN CPU | ~5.83 s | ~20.74 s | ~6.51 s | ~19.84 s |
| gesture checks | 22,104 | 79,364 | 26,023 | 75,684 |
| lookaheads | 17,209 | 61,794 | 20,932 | 59,563 |

This is **promising but not qualifying evidence**. The candidate pays fixed overhead on the square fixture but flattens aspect growth and reduces the long-side proposal/lookahead burden. Observed hard MAIN geometry invariants were clean in that proxy.

The earlier response also noted that the first formal 0.75 gate looked encouraging, but no complete durable 0.75/0.5 governing record was packaged. Therefore **no formal ACCEPT/PROMOTE claim exists**.

### Next exact step

1. Treat `archive/inflight/main1_future_envelope_fallback_renderer.py` as the sole active MAIN-1 candidate; production remains authoritative.
2. Re-run the mandated formal ordinary qualification from fresh processes in order: **0.75 first** for seeds 102+104, record categorized + overall BEFORE/AFTER; then **0.5** for seeds 102+104.
3. Reject immediately if the 0.75 -> 0.5 CPU/work curve regresses, if rollback/recovery work merely moves elsewhere, or if any hard geometry/seed-totality/line-survival invariant fails.
4. If it passes, run the complete active release/stress gates and explicitly ACCEPT/PROMOTE before changing production.
5. Keep 0.35 reserved for end-of-phase qualification; do not use it routinely during this candidate gate.

## 2026-08-25 14:28 IST — interrupted gate recovered; joint-future branch assessed

The preceding response was interrupted while the user-visible status still said `0.5 / seed 102` production was active. The durable files show that fixture and its candidate counterpart both finished before the process chain ended. No renderer process survived into recovery.

### Original future-envelope current-corridor fallback: REJECTED

`archive/inflight/main1_future_envelope_fallback_renderer.py` remains unpromoted and is now rejected as the MAIN-1 scaling candidate. The durable `0.5 / seed 102` records show:

- production MAIN CPU: `39.771783501 s`;
- candidate MAIN CPU: `40.721836496 s` (+2.39%);
- rollback segments: `2797 -> 2882`;
- gesture checks: `71956 -> 73270`;
- lookaheads: `57550 -> 60031`.

The fallback therefore moved recovery work rather than removing it at the governing fine-scale fixture. Do not promote it.

### Stronger joint-future fallback

The interrupted run then built a stricter approach: after the production solver and existing HOLD arbitration fail, a full atomic move is allowed only if every selected current proposal is mutually compatible **and** there exists a mutually compatible assignment of already-computed legal one-step future corridors for the whole group. This is materially stronger than merely requiring `future_option_count > 0` independently.

The implementation history survives as:

- `main1_joint_future_fallback_renderer.py` — first joint-future version;
- `main1_joint_future_fallback_cached_renderer.py` — exact per-group memoization of repeated current-pair and future-envelope GEOS predicates;
- `main1_joint_future_fallback_rawdist_renderer.py` — attempted raw-distance equivalence optimization; rejected below.

The cached version preserves the joint-future routing semantics while reducing search overhead. Its completed 0.75/0.5 seeds-102+104 formal MAIN-only records are under `archive/inflight/evidence/main1_joint_cached_formal_2026-08-25_1342IST/`.

Aggregate formal comparison, using final emitted MAIN segments as work:

| Metric | Production 0.75 | Production 0.5 | Cached joint 0.75 | Cached joint 0.5 |
|---|---:|---:|---:|---:|
| MAIN CPU (s) | 22.852965 | 79.038559 | 21.579168 | 76.687350 |
| final MAIN segments | 1833 | 4610 | 1830 | 4698 |
| CPU / final segment (s) | 0.012468 | 0.017145 | 0.011792 | 0.016323 |
| gesture checks | 42,845 | 149,901 | 42,026 | 142,956 |
| lookaheads | 34,873 | 121,837 | 34,389 | 117,139 |
| rollback segments | 1,705 | 5,076 | 1,708 | 5,098 |
| tracebacks | 698 | 2,275 | 678 | 2,279 |

Growth summary:

- production work growth: `2.5150x`;
- cached-joint work growth: `2.5672x`;
- production CPU growth: `3.4586x`;
- cached-joint CPU growth: `3.5538x`;
- production normalized CPU/work growth: **`1.3752x`**;
- cached-joint normalized CPU/work growth: **`1.3843x`**.

The cached joint-future version lowers absolute aggregate MAIN CPU at both scales (~5.57% at 0.75 and ~2.97% at 0.5) and lowers CPU per emitted segment at both scales, but **slightly worsens the governing normalized 0.75 -> 0.5 scaling curve**. It is therefore **NOT promotable as the MAIN-1 scaling fix in its current form**. Treat it as a useful approach prototype/evidence source, not production authority.

The per-seed asymmetry is important: at `0.5 / seed 102` the cached joint version is ~11.5% faster despite emitting 112 more final segments, while at `0.5 / seed 104` it is ~5.7% slower despite emitting 24 fewer segments. The next work should localize why the fallback search/topology is expensive specifically in that fine-scale seed-104 regime rather than broadening the policy.

### Raw-distance joint-future optimization: REJECTED

`main1_joint_future_fallback_rawdist_renderer.py` attempted to replace materialized `(current U future).buffer(r)` envelope comparisons with raw pairwise distance against `gap + 2r`. Although mathematically motivated, the actual fine-scale search cost was pathological on this implementation: `0.5 / seed 102` failed to complete even the MAIN-only harness inside a 120-second boundary, whereas the cached envelope version had completed in roughly 35 seconds on the durable formal record. No output/error was emitted before termination. Reject this implementation.

### Fallback-frequency probe

A diagnostic copy `main1_joint_future_fallback_probe_renderer.py` added exported fallback counters. On `0.75 / seed 104` it preserved the cached-joint geometry and observed:

- 266 fallback-attempt groups / 613 involved fronts;
- 79 successful groups / 173 successful fronts;
- 187 failed groups;
- 2,849 joint DFS checks;
- 486 exact current-pair evaluations;
- 1,676 exact future-pair evaluations;
- group sizes were dominated by size 2 (201 attempts) and size 3 (59 attempts).

A more detailed lifecycle counter inside that probe proved too intrusive at `0.5 / seed 104` and crossed the 90-second command boundary before emitting a record. Therefore do **not** treat that fine-scale timeout as evidence against the cached-joint renderer; treat the probe implementation as rejected instrumentation. The next probe must be lower-overhead and must not call lifecycle refresh merely to count categories.

### Current authority / next target

Production remains SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`. There is currently **no promotable MAIN-1 renderer candidate**.

The next earned target is narrow: instrument the cached joint-future fallback with O(1) counters only (attempt/success/failure/group-size/DFS-check/cache-miss counts, no lifecycle refresh), especially on `0.5 / seed 104`, and determine whether the fine-scale regression comes from fallback-search CPU itself or from the changed downstream recovery topology. Only then modify eligibility/search. Do not resurrect the broad current-corridor fallback or the raw-distance implementation.

### 2026-08-25 14:35 IST — light fallback-cost probe / host slowdown

A lower-overhead probe (`main1_joint_future_fallback_lightprobe_renderer.py`) was created from the cached joint-future prototype. It adds only O(1) attempt/success/failure/group-size/cache-miss counters plus `process_time()` around the fallback search; it does not call lifecycle refresh or construct geometry solely for instrumentation.

At `0.75 / seed 104` it preserved the cached-joint geometry SHA and work counters and measured:

- MAIN CPU: `8.9832 s`;
- joint-future fallback CPU: `0.2810 s` (~3.1% of MAIN CPU);
- 266 fallback-attempt groups / 613 involved fronts;
- 79 successful groups / 173 successful fronts;
- 187 failed groups;
- 2,849 DFS checks;
- 486 exact current-pair cache misses/evaluations;
- 1,676 exact future-pair cache misses/evaluations.

This rules out the fallback DFS bookkeeping as a dominant cost at 0.75.

The same light probe at `0.5 / seed 104` exceeded a 90-second command boundary. Crucially, the **unchanged cached joint-future control** also exceeded the same 90-second boundary in the current host state. A separate 30-second bounded control consumed `29.95 s` user CPU + `0.47 s` system CPU at ~101% CPU and emitted no record before the deliberate timeout. Therefore the current inability to finish the fine-scale fixture is a host-speed/runtime-window issue, not evidence that the light probe changed renderer complexity. The durable earlier formal records (35–41 s range for these fine-scale fixtures) remain the valid like-for-like comparison set.

Do not promote/reject any renderer based on the new 90-second timeouts. Resume the light probe on `0.5 / seed 104` only when the execution environment can complete the unchanged cached control in a comparable window, or use a sufficiently large foreground execution boundary and compare adjacent control/probe processes on the same host state.


## 2026-08-25 21:28 IST — recovery of post-16:29 proxy findings (no source candidate survived)

The preceding continuation produced additional **diagnostic/proxy evidence after the 16:29 bundle**, but the turn ended before those scratch sources/results were packaged. The exact surviving authoritative repository therefore still has no active renderer candidate and production remains SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`. The findings below are recovered from the conversation log and must be treated as evidence/next-direction only until reconstructed from production.

### Smaller recovery-topology proxy and discarded-proof diagnosis

Because the current host could no longer complete the governing `0.5 / seed 104` MAIN-only control within a practical foreground boundary, MAIN-1 iteration moved to a deterministic `0.75` smaller-aspect proxy. Proxy results are **not qualifying evidence** and cannot replace the required 0.75/0.5 seeds-102+104 gate.

A recurrence probe on a `1:2 @ 0.75 / seed 104` proxy found that a joint-future fallback success frequently recurred immediately: 635 successful front-moves were observed and 600 front appearances re-entered another exhausted fallback conflict on the very next round. This showed that a jointly compatible one-step continuation was normally discarded after the current commit.

Two attempts to preserve/use that continuation were rejected:

- carrying the proved next step as an additional next-round proposal created extra holistic work and exceeded the proxy command boundary;
- replacing the stale `future_geom` with the jointly selected compatible future envelope in the defensive second pass also exceeded the stable adjacent-control proxy boundary, implying that simply allowing every jointly-future-compatible transaction through creates materially worse downstream topology.

### Lifecycle localization: structural/connection-pending, not mature steady-state

A lifecycle probe showed the successful exhausted-conflict fallback was almost entirely associated with `STRUCTURAL_TRANSITION` and/or `CONNECTION_PENDING` fronts. Only 4/1047 exhausted groups contained any `NORMAL` front and there were zero all-normal successful fallback groups. This invalidated the idea that the problem was mainly mature steady-state fronts forgetting a safe continuation.

The audit then identified a structural modeling inconsistency: `_future_options()` predicts the next step from a shallow endpoint-updated copy, while `_accept()` changes local front state such as branch stage, cooldown, reroute state, travel and direction grammar. Several production-based post-commit-state lookahead candidates were tested on proxies:

- combined structural/post-commit model initially improved `1:1 -> 1:2` normalized MAIN CPU/launch growth for seed 104 from about `1.414x -> 1.339x` and reduced lookahead/recovery work;
- a stricter structural-only version improved that seed-104 aspect proxy further (~`1.302x`) but gave only a weak 0.75->0.65 scale improvement;
- cooldown-only was behaviorally clean and reduced absolute work, but worsened the 0.75->0.65 normalized scale curve (~`1.46x` vs production ~`1.37x`);
- seed 102 then disproved the combined model as a general scaling fix: aggregate executable 0.75->0.65 normalized CPU/launch growth was worse than production.

All post-commit-state variants are therefore **REJECTED as MAIN-1 scaling fixes**. No source from these scratch variants survived the interrupted turn and none should be reconstructed unless new evidence requires it.

### Connection-pending wedge

The remaining dominant lifecycle class is `CONNECTION_PENDING`: 570/1047 exhausted conflict groups in the proxy involved it. A narrow reciprocal-peer future-envelope exemption was tested and rejected because it increased actual connections but also increased long-proxy rollback (`1545 -> 1908`) and worsened normalized aspect growth.

The next architectural inconsistency is earlier in the lifecycle: hard reciprocal connection transactions are declared at substantially longer range than the actual singleton join executor can act. A recovered distribution probe observed **2,988 reciprocal pair commitments** on the proxy, while only about **43.5% were within 5 modules**; the actual singleton join executor only considers pairs within **10 modules**. Long-range attraction can remain soft without forcing two fronts into a hard atomic `CONNECTION_PENDING` transaction.

### Exact next experiment

Reconstruct from authoritative production a narrow candidate that preserves all existing long-range connection attraction/scoring, but **does not promote a reciprocal pair into hard `CONNECTION_PENDING` state until the pair is within the executor's own 10-module reach**. Do not exempt intended peers from exact current-corridor geometry, do not change join legality, do not add fallback rescue, and do not change seed/RNG ownership.

First screen it on the deterministic 0.75 recovery-topology proxy against an adjacent production control. If it removes connection-pending exhausted groups/rollback without shifting work elsewhere, then test both governing seeds at executable ordinary scales and eventually the mandatory 0.75 -> 0.5 gate on a host that can complete the unchanged control. No routine 0.35 during this ordinary candidate stage.

## 2026-08-25 21:50 IST — connection lifecycle and repeated conflict-predicate audit

Production remains unchanged at SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`. All sources in this section are diagnostic/unpromoted unless explicitly stated otherwise. The `1:2 @ 0.75 / seed 104` MAIN-only fixture is an iteration proxy only; it is not qualifying evidence and cannot replace the mandatory 0.75 -> 0.5 seeds-102+104 gate.

### Connection-lifecycle candidates: rejected

`main1_connection_pending_10module_renderer.py` capped hard reciprocal pair assignment at the existing singleton join executor's 10-module reach while preserving the existing candidate-selection machinery. On the proxy, rollback segments improved `1545 -> 1420`, but MAIN CPU regressed `14.8911 -> 16.6678 s`, gesture checks rose `62899 -> 65866`, lookaheads `53385 -> 56259`, and reroute-exhausted events `2806 -> 3176`; connections remained 41. Reject: long-range hard coordination is doing useful recovery work even before the final join is executable.

`main1_connection_softguide_10module_renderer.py` retained the long-range meeting target but withheld reciprocal hard-peer status beyond 10 modules. It failed to complete inside the same enlarged proxy boundary after an adjacent production control. Reject as a policy direction; later host behavior showed that second-process timing can be noisy, but there is no positive evidence and the candidate removes coordination that the first experiment already showed to be useful.

`main1_connection_recovery_exclusion_renderer.py` prevented already-recovering fronts from entering a new hard connection transaction. It likewise failed to complete inside the enlarged adjacent proxy boundary. Reject: pairing is materially participating in recovery rather than being separable from it.

### Pair churn is a symptom of recovery coupling

Instrumentation-only `main1_connection_pair_churn_probe_renderer.py` preserved production geometry and counted 3558 hard pair assignments. Distance bins were <=5 modules: 1605; 5-10: 1293; 10-13: 275; >13: 385. For fronts paired on consecutive rounds there were 1327 same-peer continuations and 1270 immediate partner switches; after a gap there were 3618 same-peer and 621 switched-peer appearances.

The state split localizes most immediate churn to repair: same-peer next-round = 165 clean / 1157 repair / 5 structural; switched-peer next-round = 259 clean / 993 repair / 18 structural. Therefore partner churn is not a clean standalone optimization target: connection arbitration and recovery are deliberately entangled in the current topology.

### Exhausted atomic conflicts recur almost immediately

Instrumentation-only `main1_no_repair_recurrence_probe_renderer.py` found 364 atomic conflict groups that successfully scheduled repair and 640 groups for which no further repair could be scheduled. Of those no-repair groups, 510 (~79.7%) recurred with the same exact front set on the immediately following round; another 54 recurred after a gap. Lifecycle involvement among the no-repair groups: structural transition 486, connection pending 317, recovering 155, normal 1. This is strong evidence that exhausted groups repeatedly regenerate proposal/lookahead/conflict work even when the current recovery mechanism has no new action to take.

However, existing exact legality/failure caches are already heavily active on this proxy: primary path-clear proof hits 12248; proposal failure-certificate hits/stores 11529/10192; future failure-certificate hits/stores 5749/7628; future-local-visible certificate hits/stores 667/1209. The remaining amplification is therefore not explained by a missing ordinary path-blockage cache.

### `_future_conflict()` reuse: high, but cross-round exact memoization remains unresolved

`main1_future_conflict_reuse_probe_renderer.py` observed 25633 `_future_conflict()` calls and about 9006 unique approximate proposal-pair geometry states, i.e. roughly 65% repeated calls. This motivated several behavior-preserving memoization attempts.

- `main1_future_conflict_cache_renderer.py`: exact nested semantic key constructed at every call. On the proxy it preserved complete geometry/work but was slightly slower (`16.0561 -> 16.6581 s` MAIN in the adjacent record). Reject implementation: key construction consumed the GEOS savings, but this validates that a sufficiently complete call-time semantic key can preserve behavior.
- `main1_future_conflict_token_cache_renderer.py`: tokenized cross-round key, first canonicalized then corrected to ordered direction because the same-fan fast path is directional. Proposal-creation-time freezing is semantically suspect because repair/branch state may change before the actual conflict call; no positive qualifying evidence survived. Reject.
- `main1_future_conflict_lazy_token_cache_renderer.py`: token frozen on first conflict use rather than proposal creation. It did not yield positive evidence in the available execution window; keep rejected/unqualified rather than treating timeout as a renderer proof.
- `main1_future_conflict_round_cache_renderer.py`: exact round-local directional cache stored on the proposal object. A standalone run completed with production-identical geometry/work; one measured run was ~15.37 s MAIN and a second ~14.74 s. It recorded 5122 hits / 20511 misses (~20% within-round reuse). This is semantically safe on the observed proxy but provides insufficient leverage and no robust speedup. Reject for MAIN-1.

Host note: back-to-back long proxy commands sometimes make the second process miss an outer wall boundary even when the same candidate finishes normally when run alone. Do not infer candidate pathology solely from second-process timeout; use fresh standalone processes for performance screening.

### Current MAIN-1 status / next direction

No renderer candidate is promotable. Connection distance/lifecycle suppression has been rejected. The strongest remaining causal fact is the 510/640 immediate recurrence of no-repair atomic conflict groups, combined with the fact that ordinary geometry legality caches already hit heavily. The next optimization should reduce repeated work for an unchanged exhausted conflict state **without changing routing decisions, RNG semantics, horizon semantics, or legality**. Prefer an event/version-driven or transaction-local reuse mechanism keyed to exact immutable state; do not simply sleep fronts, suppress connection pairing, or reintroduce broad future-envelope rescue policies.

## 2026-08-25 21:58 IST — method-level cost split after recurrence audit

Production remains unchanged at SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`; there is still no promotable MAIN-1 candidate.

A zero-policy-change method timing probe was run on the stable `1:2 @ 0.75 / seed 104` MAIN-only recovery proxy after the 21:50 recurrence/conflict audit. Inclusive CPU attribution was:

| Operation | Inclusive CPU |
|---|---:|
| `_proposal_variants` | **11.07 s** |
| `_lookahead_adjust` | **5.50 s** |
| `_propose` | **5.09 s** |
| `_gesture_clear` | **4.95 s** |
| `_future_options` | **4.94 s** |
| `_score_candidate` | 1.14 s |
| `_future_conflict` | **0.93 s** |
| `_conflict_groups` | 0.88 s |
| `_solve_conflict_group` | **0.26 s** |
| connection-target assignment | 0.17 s |
| conflict-repair scheduling itself | ~0.004 s |

Total MAIN routing CPU for the proxy was about `15.09 s`; the table is inclusive and therefore intentionally overlaps parent/child time.

This materially changes MAIN-1 priority. The recurrence evidence (`510/640` no-repair exhausted atomic groups recur with the same front set on the immediately following round) is expensive because the next round regenerates proposal and holistic lookahead work. Pure conflict-solver work is too small to be the main wedge: `_future_conflict` plus group/solver overhead is a minor fraction compared with `_proposal_variants`, `_propose`, `_gesture_clear`, and `_future_options`.

### Earned next target

Do **not** pursue more conflict-DFS micro-optimization or connection-policy changes without new evidence. The next experiment must be behavior-preserving reuse of already-paid proposal/lookahead subproofs across an unchanged exhausted transaction, guarded by an exact local event/version condition so that any nearby geometry/state change invalidates reuse.

Hard constraints:

- no sleeping/skipping a front merely because it failed last round;
- no RNG resequencing or seed substitution;
- no legality weakening;
- no stale geometric certificate surviving a relevant local mutation;
- reuse should target proposal/lookahead construction/evaluation, not routing policy;
- a proxy win is not promotion: governing qualification remains 0.75 then 0.5, seeds 102+104, with normalized work/CPU and full release/stress gates; 0.35 remains phase-end only.

## 2026-08-25 22:15 IST — MAIN-1 exact-local proof reuse PROMOTED

The final MAIN-1 approach preserves routing decisions and removes repeated proposal/lookahead legality work for fronts held across unchanged local board state.

### Promoted mechanism

- Cross-round proposal-pool reuse replays only the already-proved **legality membership** of the first proposal draw. All seeded module-list shuffles, score/noise computation, candidate weighting and RNG draws still execute in the historical order.
- The replay is eligible only when `_proposal_reuse_front_state(f)` is identical and the exact dynamic dependency signature over the reuse bounds is unchanged.
- Dynamic dependencies are the queried committed MAIN path-record identities plus path-index generation and the queried source-egress reservation/protected-owner state. Static chips/components are immutable during MAIN and need no versioning.
- Successful `_future_options()` gesture proofs are similarly reused only while the exact candidate geometry's local dynamic dependency signature remains unchanged.
- A relevant nearby committed route or source-egress state mutation invalidates the proof immediately; stale geometry is never grandfathered.

The promoted renderer SHA-256 is `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`.

### Governing ordinary qualification — seeds 102+104

| State | 0.75 work (segments) | 0.5 work | Work Growth | 0.75 MAIN CPU | 0.5 MAIN CPU | CPU Growth | CPU / Work Growth |
|---|---:|---:|---:|---:|---:|---:|---:|
| BEFORE `d58ee1bf...` | 1,833 | 4,610 | 2.515003x | 10.638228 s | 59.275867 s | 5.571968x | **2.215492x** |
| AFTER `3100503d...` | 1,833 | 4,610 | 2.515003x | 11.274694 s | 40.621074 s | 3.602854x | **1.432545x** |

Deterministic topology is identical on all four governing fixtures: same complete output geometry hashes, same emitted segment work, same lookahead evaluations, same rollback segments and same traceback counts. The work removed is exact repeated legality proof work: aggregate 0.5 gesture-clear checks fall `149,901 -> 130,062`.

The first aggregate 0.75 timing looked ~6% worse because the candidate's bookkeeping is a larger fraction on light boards. A fresh adjacent recheck gave seed 102 `8.6326 -> 7.9443 s` and seed 104 `4.6302 -> 4.7670 s`, ~4.8% faster in aggregate, still geometry-identical. Promotion therefore does not rely on accepting a known 0.75 slowdown.

### Gates

Two new active regression tests prove the exact invalidation contract for proposal-pool reuse and future-success proof reuse. Candidate and then canonical promoted production passed the complete release gate; canonical status is **156/156 PASS**, zero failures/errors/skips/xfails, plus maintained geometry stress **1/1 PASS**.

Classification: **ACCEPT / PROMOTE. MAIN-1 ordinary scaling stage closed.**

### Reserved phase-end 0.35 qualification

Per cadence, 0.35 was not used during candidate iteration. After promotion, the final phase-end 0.35 step was started. The first BEFORE `1:1 @ 0.35 / seed 102` foreground attempt exceeded the 180-second execution boundary without an emitted record. This is an incomplete measurement, not a correctness failure. Resume from a fresh process after the mandatory recovery handoff; do not modify production before the phase-end comparison is complete.


## 2026-08-26 00:08 IST — MAIN-1 phase-end 0.35 qualification CLOSED

Authoritative production remains SHA-256 `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`. No renderer behavior changed during this final measurement.

The reserved phase-end comparison used the exact pre-MAIN-1 source (`d58ee1bf...9c9b0`) and promoted MAIN-1 source on the same deterministic `1:1` fixtures, seeds 102 and 104. Fresh adjacent 0.5 timings were repeated on the same current host after an initial cross-host comparison proved misleading. All BEFORE/AFTER geometry hashes and all routing-topology counters remain identical per fixture.

### Same-host 0.5 -> 0.35 final scaling

| Category / overall phase | BEFORE Work Growth | BEFORE CPU Growth | BEFORE CPU/Work Growth | AFTER Work Growth | AFTER CPU Growth | AFTER CPU/Work Growth |
|---|---:|---:|---:|---:|---:|---:|
| MAIN emitted segments / MAIN phase overall | 2.063991x | 2.141140x | **1.037378x** | 2.063991x | 2.074347x | **1.005017x** |

Because the qualification harness isolates MAIN, the categorized MAIN row and active-phase overall row are the same quantity by construction. Useful work is final emitted MAIN segments: aggregate `4,610 -> 9,515`.

Fresh same-host aggregate CPU:

- BEFORE 0.5: `50.811738479 s`; AFTER 0.5: `51.261907538 s`.
- BEFORE 0.35: `108.795035146 s`; AFTER 0.35: `106.334977532 s`.
- At 0.35, gesture-clear checks fall `296,105 -> 266,481` while output geometry and recovery/lookahead topology remain identical.
- Absolute promoted 0.35 MAIN CPU is ~2.26% lower on this pair. More importantly, normalized fine-scale growth improves from mildly superlinear **1.037378x** to essentially linear **1.005017x**.

### Superseded cross-host comparison

Do **not** use the earlier provisional `1.268x` AFTER normalized 0.5 -> 0.35 value. It combined historical 0.5 timings from a materially faster host epoch with fresh 0.35 timings. A direct signature-volume probe then showed dependency-signature calls/record volume growing approximately with useful work rather than superlinearly (`27,717 -> 55,615` calls and `60,134 -> 122,240` nearby path records on seed 104). The fresh same-host 0.5 rerun confirmed the timing mismatch.

### Phase decision

**ACCEPT / PHASE CLOSED.** MAIN-1 retains exact behavior and removes the measured fine-scale CPU/work amplification. The ordinary 0.75 -> 0.5 gate had already improved normalized MAIN CPU/work from `2.215492x -> 1.432545x`; the reserved same-host 0.5 -> 0.35 gate now confirms the promoted implementation remains essentially territory/work-linear at the finer scale.

The next task is not another MAIN-1 candidate. It is the separate expensive production-regime check: full `1:6 @ 0.35` operational benchmarking of the fully optimized authoritative renderer, followed by a whole-render BEFORE/AFTER runtime/RSS comparison against the preserved pre-long/fine audit evidence.
