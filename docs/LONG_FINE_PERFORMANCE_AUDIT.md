# Long/Fine Performance Audit

Updated: 2026-08-25 04:34 IST

## Purpose

This audit treats the current exact `1:6 @ 0.35` runtime as a scaling problem rather than normalizing it away because the renderer eventually succeeds.

The governing standard is:

> More logical territory and more emitted geometry may require proportionally more work, but aspect ratio / work heft must not make the cost per unit of useful work grow substantially. Correctness and seed totality remain invariant.

No renderer behavior was changed during this audit. Production remains the promoted V48 source at SHA-256 `e8d1874d652e7aa6a7af763ac20b2a97d1367082dc748f61771833be49d16054`.

## Executive conclusion

The current long/fine slowdown is **real**, but it is not primarily caused by the renderer generating wildly superlinear amounts of board geometry.

At the same base seed and `main_scale=0.35`, increasing territory from `1:1` to `1:6` produces roughly the expected ~6x amounts of chips, MAIN launches, LOCAL traces, components, gesture checks, and lookaheads. Whole-render CPU, however, grows about **8.09x**.

The excess beyond perfect 6x territory-linear scaling is about **158.7 CPU-s / 2.65 minutes** on the measured seed-0 pair. Approximately:

- **58.2% of that scaling tax is LOCAL gap routing**;
- **37.1% is MAIN routing**;
- **3.4% is component placement**;
- preparation/audit/validation phases are not scaling concerns.

Therefore the optimization order should be:

1. **LOCAL direct-mopup dead-family polling** — highest-confidence first target;
2. **LOCAL hard-floor rescue/debt-completion cascade** — second target;
3. **MAIN per-operation / global-round infrastructure** — instrument first, then optimize the proven source;
4. LOCAL front/history lifetime and absolute-memory compaction;
5. component placement only after the dominant phases are corrected.

The audit led to a promoted first optimization stage, LOCAL-1, documented below. There is currently no active renderer candidate after that promotion.

---

## 1. Same-seed whole-render scaling: `1:1` -> `1:6` at 0.35

Current promoted V48, base seed 0.

| Metric | `1:1 @ 0.35` | `1:6 @ 0.35` | Growth | Growth / 6x territory |
|---|---:|---:|---:|---:|
| logical territory | 1x reference | 6x | **6.000x** | 1.000x |
| chips | 17 | 98 | 5.765x | 0.961x |
| MAIN launch traces | 711 | 4,124 | 5.800x | 0.967x |
| LOCAL traces | 1,295 | 7,869 | 6.076x | 1.013x |
| residual components | 340 | 2,047 | 6.021x | 1.003x |
| gesture-clear checks | 163,055 | 981,312 | 6.018x | 1.003x |
| lookahead evaluations | 131,687 | 801,235 | 6.084x | 1.014x |
| **MAIN CPU** | 46.598 s | 338.407 s | **7.262x** | **1.210x** |
| **LOCAL CPU** | 20.547 s | 215.606 s | **10.493x** | **1.749x** |
| **component-place CPU** | 5.582 s | 38.871 s | **6.964x** | **1.161x** |
| **whole-render CPU** | 75.957 s | 614.485 s | **8.090x** | **1.348x** |
| peak RSS | 234,584 KiB | 804,192 KiB | 3.428x | 0.571x |

### Scaling-tax decomposition

Perfect territory-linear extrapolation from the square board predicts:

- `75.957 * 6 = 455.743 CPU-s` = **7.60 minutes**.

Actual long-board cost:

- **614.485 CPU-s = 10.24 minutes**.

Excess above territory-linear cost:

- **158.741 CPU-s = 2.646 minutes**.

Phase attribution of that excess:

| Phase | Linear expectation | Actual | Excess | Share of total scaling tax |
|---|---:|---:|---:|---:|
| MAIN | 279.590 s | 338.407 s | **+58.816 s** | **37.1%** |
| LOCAL | 123.283 s | 215.606 s | **+92.323 s** | **58.2%** |
| components | 33.491 s | 38.871 s | +5.380 s | 3.4% |

Important distinction: eliminating the scaling tax alone would move this measured sample from about **10.24 min to ~7.60 min**. Getting materially below ~7.5 minutes therefore requires a second stage of **constant-cost-per-work optimization** after the superlinear scaling defects are removed.

RSS is high in absolute terms but scales sublinearly with territory in this pair, so memory growth is not the primary scaling defect. Absolute memory reduction remains worthwhile later.

---

## 2. MAIN audit: work generation is near-linear; cost per operation is not

Current promoted V48, base seed 1, MAIN-specific same-seed comparison at 0.35.

| Metric | `1:1` | `1:6` | Growth |
|---|---:|---:|---:|
| territory | reference | 6x | **6.000x** |
| chips | 17 | 98 | 5.765x |
| launch traces | 691 | 4,104 | 5.939x |
| approximate emitted segment work | ~4,505 | ~27,546 | **6.115x** |
| gesture-clear checks | 141,115 | 887,062 | **6.286x** |
| lookaheads | 115,727 | 719,722 | **6.219x** |
| local-space evaluations | 44,336 | 287,559 | **6.486x** |
| MAIN CPU | 37.405 s | 320.487 s | **8.568x** |

Normalized implications:

- CPU / emitted segment worsens about **1.401x** (+40%);
- gesture checks / emitted segment worsen only about **1.028x**;
- lookaheads / emitted segment worsen about **1.017x**;
- local-space evaluations / emitted segment worsen about **1.061x**;
- CPU / gesture-clear check worsens about **1.363x**.

### MAIN diagnosis

This argues **against** redesigning MAIN routing policy merely because proposal construction is hot. High-level routing work already scales close to actual territory/geometry.

The missing CPU is likely in the machinery underneath or around those local operations. Static inspection identifies several candidates that should be discriminated with low-overhead counters before any MAIN architecture change:

1. `_run_rounds()` repeatedly rebuilds and sorts active-front populations.
2. `_assign_round_connection_targets(...)` rebuilds an active-head spatial hash, sorts eligible active fronts, constructs cross-chip pair candidates, and globally sorts them. Ordinary rounds can perform this more than once around branching/movement.
3. `_conflict_groups(...)` constructs a fresh spatial hash for the proposal pool each arbitration round.
4. `_gesture_clear(...)` performs spatial record queries plus exact geometry checks; successful primary-MAIN proof reuse also constructs signature/state objects. If spatial candidate cardinality rises with long-strip active population, each nominal “gesture check” becomes more expensive even though the count is linear.

### Required MAIN discriminator before implementation

Add near-zero-overhead diagnostic counters, not timing wrappers, for:

- static-index records returned per gesture-clear query;
- path-index records returned per gesture-clear query;
- exact geometry pair checks after AABB filtering;
- AABB rejections;
- path-clear proof hit/miss counts;
- active-head snapshot rebuild calls and total active heads inserted;
- connection-target pair candidates generated/sorted;
- conflict-group proposal count / conflict-edge count.

Compare same-seed square vs long aspect. Only then choose between:

- reducing repeated all-active snapshot / matchmaking rebuilds, or
- reducing per-local-query exact geometry cost.

Do **not** alter line-survival, connection semantics, branch probabilities, or geometry admission merely to make this faster.

---

## 3. LOCAL audit: dominant scaling defect

LOCAL is the clearest current target. On seed 0 its emitted LOCAL trace count grows **6.08x**, but LOCAL CPU grows **10.49x**. The same-seed seed-1 detailed counters reveal two concrete sources of amplification.

### 3.1 Smoking gun: quarantined direct-run families are repeatedly polled

Seed 1 detailed comparison:

| Counter | `1:1` | `1:6` | Growth | Growth / 6x territory |
|---|---:|---:|---:|---:|
| LOCAL traces | 1,534 | 10,939 | 7.131x | 1.189x |
| visible LOCAL traces | 797 | 4,935 | 6.192x | 1.032x |
| spawn attempts | 51,770 | 370,511 | 7.157x | 1.193x |
| target calls | 7,956 | 56,439 | 7.094x | 1.182x |
| target-cell evaluations | 186,705 | 1,339,882 | 7.176x | 1.196x |
| target-chunk evaluations | 38,707 | 250,345 | 6.468x | 1.078x |
| direct-run family attempts | 5,813 | 33,744 | 5.805x | 0.967x |
| unique direct families attempted | 2,208 | 12,738 | 5.769x | 0.962x |
| families quarantined | 1,722 | 10,015 | 5.816x | 0.969x |
| **quarantine skip checks** | **167,952** | **5,538,055** | **32.974x** | **5.496x** |
| direct-failure certificate hits | 2,432 | 14,459 | 5.945x | 0.991x |

Only ~5.8x as many families become quarantined, which is appropriate for 6x territory. But the long board performs **5.54 million skip checks**—about **33x** the square count.

Static inspection of `_local_gap_direct_mopup` explains why: after a family becomes known-dead/quarantined, later successful iterations still revisit region caches and encounter that same family again, incrementing the skip counter and continuing. Dead choices remain in the live search surface.

This is unnecessary polling, not generated geometry.

### Optimization target LOCAL-1

**Retire quarantined direct-run families from live search state exactly once.**

A safe design should preserve the existing candidate order/score and failure certificates. Viable structures include a per-region ordered live-family cursor/list or a lazy heap/version scheme where a quarantined family is removed/invalidated once rather than inspected in every later scan.

Hard requirements:

- preserve exact geometry and clearance admission;
- preserve global LOCAL service semantics;
- do not add an aspect-specific path;
- no smaller cap / skipped work masquerading as optimization;
- quarantine skip work should become approximately O(unique quarantined families), not O(quarantined families * later successful iterations).

This is the **highest-confidence first implementation target**.

### 3.2 Rescue-wave cliff: whole-field candidate budgets repeat after hard-floor shortfall

Seed 1:

| Counter | `1:1` | `1:6` | Growth |
|---|---:|---:|---:|
| fragment candidate tokens | 8,164 | 48,980 | ~6.000x |
| partial-service rescue waves | 1 | 3 | 3.000x |
| **partial-service candidate tokens** | **4,898** | **88,164** | **18.000x** |
| deterministic debt-completion candidates | not invoked | **136,597** | regime transition |
| deterministic completion traces emitted | not invoked | **214** | — |

The per-wave candidate budget itself scales with territory, which is fine. The long board, however, exhausts all three whole-field partial-service waves and then enters deterministic debt completion. That creates a **budget x wave-count** scaling cliff: 6x territory * 3 rescue waves = 18x candidate tokens before the deterministic tail even starts.

### Optimization target LOCAL-2

Replace repeated whole-field hard-floor rescue sweeps with a **monotonic debt-driven scheduler** over unpaid service regions/cells.

The global 80–90% service contract remains global. Region/cell debt is a scheduling mechanism only; it must not become a new per-region quota or behavior rule.

Desired property:

- each successful service action monotonically retires explicit remaining debt;
- exhausted/certified regions leave the live rescue queue;
- work scales with actual unpaid service debt and legal candidate opportunities, not `whole-board candidate cap * number of rescue waves`;
- deterministic completion becomes exceptional rather than a routine long-strip tail.

Qualification should explicitly track partial-service candidate tokens per useful LOCAL output and whether deterministic completion is entered.

### 3.3 Secondary LOCAL lifetime / memory opportunity

LOCAL repeatedly filters/scans `self.fronts.values()` for active local fronts while terminated/abandoned front/history objects remain resident. Long boards create many more total sources than final visible traces. Maintaining a compact active-local-ID set and/or freezing completed fronts into minimal materialization records may reduce Python scanning/cache pressure and absolute RSS.

This is **not** the first scaling target because RSS itself is sublinear by territory and the dead-family/rescue-wave mechanisms have stronger direct evidence.

---

## 4. Component placement: real but distant third

On same-seed seed 0:

- residual component count grows **6.021x**;
- component-placement CPU grows **6.964x**;
- CPU per component therefore worsens roughly **16%**.

This is a measurable scaling tax, but component placement is only ~6% of the long render and contributes ~3.4% of the total excess-over-linear CPU. Do not interrupt LOCAL/MAIN work for it.

The seed-1 detailed report also shows residual component-region count growing ~7.6x, suggesting fragmentation/bookkeeping may be responsible for the per-component penalty. Revisit after LOCAL and MAIN.

---

## 5. Recommended optimization sequence

### Stage A — LOCAL-1: dead-family retirement

Question: can direct mopup preserve identical behavior while removing repeated polling of already-quarantined families?

Required evidence before promotion:

- ordinary candidate qualification at **0.75 then 0.5**;
- categorized + overall BEFORE/AFTER work/CPU/work-growth table;
- authoritative LOCAL service/geometry counters unchanged or improved;
- long-aspect proxy after ordinary qualification to prove quarantine-skip scaling collapses;
- final 0.35 qualification only at the end of the phase.

Success indicator: 5.54M long-board quarantine skips collapse toward the number of actual unique dead families rather than merely falling because work was skipped.

### Stage B — LOCAL-2: debt-driven hard-floor rescue

Question: can remaining service debt be paid monotonically without repeated whole-field rescue waves and the deterministic-completion cliff?

Success indicators:

- partial-service candidate tokens scale close to actual territory/debt rather than 18x for 6x territory;
- deterministic debt completion disappears from normal long/fine fixtures or becomes genuinely exceptional;
- target/spawn evaluations per visible LOCAL trace approach square behavior;
- global service target and geometry remain unchanged.

### Stage C — MAIN-1: instrument per-operation amplification

Question: which lower-level MAIN mechanism causes ~6.1x emitted segment work to consume ~8.6x CPU?

Instrument first. Then optimize only the proven source: global snapshot/matchmaking rebuilds, conflict infrastructure, or spatial/exact-geometry candidate cardinality.

### Stage D — constant-factor pass after scaling is near-linear

Even perfect six-territory scaling from the current square baseline is ~7.6 minutes. If the product target is materially faster than that, a separate constant-factor pass will still be required after the scaling tax is removed.

Candidate areas after A–C:

- active/front/history compaction;
- reuse/incrementalization of spatial structures where semantics permit;
- exact-geometry query/proof allocation reduction;
- component fragmentation bookkeeping.

---

## 6. Non-targets / anti-solutions

Do not “fix” long/fine speed by:

- lowering density/population specifically for long aspect ratios;
- giving `1:6` different routing behavior;
- reducing correctness/service budgets until work disappears;
- rejecting/skipping heavy seeds;
- weakening the 50–60% component or 80–90% LOCAL construction requirements;
- reducing line survival or connection opportunities;
- replacing evidence-driven work with a larger timeout.

The target is the same board grammar and same validity contract at lower **CPU per actual work**.

---

## 7. Audit decision

**RETAIN** the promoted renderer behavior and totality architecture.

**OPEN optimization phase:** long/fine performance scaling.

**First implementation target:** LOCAL direct-mopup quarantine retirement.

The evidence is strong enough to answer the audit question; do not over-investigate before trying the smallest semantics-preserving LOCAL-1 change and qualifying it through the normal stage gates.


---

## 8. Stage A result — LOCAL-1 dead-family retirement PROMOTED (2026-08-25)

Production now retires an immutable direct-run family from the owning region's cached live search list once that family reaches the existing invariant retry cap. The region is marked dirty and its ordered list is compacted once before its next scan; region-version rebuilds also filter already-retired identities. Candidate score/order, retry cap, RNG sequence for surviving candidates, exact geometry admission, and the global LOCAL service contract are unchanged.

Governing ordinary qualification used 1:1 seeds 102 and 104, **0.75 first and then 0.5**. All four complete output geometry hashes are byte-identical BEFORE vs AFTER.

| Category | BEFORE Work Growth | BEFORE CPU Growth | BEFORE CPU/Work Growth | AFTER Work Growth | AFTER CPU Growth | AFTER CPU/Work Growth |
|---|---:|---:|---:|---:|---:|---:|
| LOCAL visible traces | 2.1046x | 2.7449x | **1.3042x** | 2.1046x | 2.5800x | **1.2259x** |
| Whole render / visible routing traces | 2.2151x | 3.0975x | **1.3983x** | 2.2151x | 3.0961x | **1.3977x** |

Deterministic dead-family polling collapses without changing useful work:

| Counter | BEFORE 0.75 | BEFORE 0.5 | AFTER 0.75 | AFTER 0.5 |
|---|---:|---:|---:|---:|
| quarantined families | 539 | 1,318 | 539 | 1,318 |
| quarantine skip encounters | **10,235** | **52,848** | **873** | **2,107** |

The first list-copy prototype and the O(1) insertion-ordered-map prototype were both rejected/modified because they preserved geometry but added unnecessary constant Python overhead. The promoted design keeps fast production list iteration and compacts only dirty regions once before the next scan.

Qualification: **152/152 active release tests PASS**, maintained stress **1/1 PASS**. Production renderer SHA-256: `325e2ec0c79d2ec7a051c9c08b2abba73c6fab5c5561a665a2c4d16dec85acf2`. This ordinary stage intentionally did **not** run 0.35; the project cadence reserves 0.35 for the end of the full optimization phase.

**Next stage:** LOCAL-2 — replace repeated whole-field hard-floor rescue waves / deterministic tail search with monotonic debt-driven scheduling while preserving the same global 80–90% service contract and exact geometry rules.

## LOCAL-2 implementation checkpoint — 2026-08-25 05:34 IST

LOCAL-1 is already promoted. LOCAL-2 currently has one unpromoted candidate: one hard-floor stochastic debt campaign plus exact first-leg legality caching in deterministic debt completion.

The candidate clears the ordinary 0.75 -> 0.5 scaling question: normalized LOCAL CPU/work improves from ~`1.105x` to ~`1.042x`, and whole-render CPU/work from ~`1.292x` to ~`1.271x`. The long `1:6 @ 0.75` proxy confirms the targeted repeated-wave amplification is removed: waves `3 -> 1`, partial tokens `19,200 -> 6,400`.

However, the long proxy also changes output population: LOCAL service `0.806398 -> 0.800341`, total LOCAL traces `2,392 -> 2,096`, visible traces `1,085 -> 1,061`. Before promotion, compare the actual emitted LOCAL distribution/coverage and determine whether this is harmless removal of redundant rescue output or unacceptable design-language thinning. Classification remains **RETAIN / qualification incomplete**. Do not move to release/stress or LOCAL-3/MAIN work until this question is answered.

## 9. Stage B result — LOCAL-2 debt campaign + exact first-leg reuse PROMOTED (2026-08-25)

LOCAL-2 replaces repeated whole-field partial-service reserve campaigns with one monotonic debt campaign and removes repeated exact first-leg clearance work in the deterministic debt tail. The hard 80% service floor, sampled 80–90% normal preference, total source opportunity, exact second-leg legality, routing grammar, and seed ownership remain unchanged.

Governing ordinary qualification used seeds 102 + 104, **0.75 first and then 0.5**:

| Category | BEFORE Work Growth | BEFORE CPU Growth | BEFORE CPU/Work Growth | AFTER Work Growth | AFTER CPU Growth | AFTER CPU/Work Growth |
|---|---:|---:|---:|---:|---:|---:|
| LOCAL traces | 2.2458x | 2.4824x | **1.1054x** | 2.3208x | 2.4177x | **1.0418x** |
| Whole render / LOCAL traces | 2.2458x | 2.9022x | **1.2923x** | 2.3208x | 2.9491x | **1.2707x** |

Work elimination:

- partial-rescue tokens: production `3,201 -> 9,600` across 0.75 -> 0.5 versus promoted `1,067 -> 4,800`;
- 0.5 deterministic debt-completion candidates: `35,759 -> 22,886`;
- exact first-leg cache hits: `5,287` on 0.5/102.

Long `1:6 @ 0.75` proxy:

- rescue waves `3 -> 1`;
- stochastic candidate tokens `19,200 -> 6,400`;
- visible LOCAL traces `1,085 -> 1,061` (-2.2%);
- physical LOCAL service `0.806398 -> 0.800341` (still above the hard floor);
- mean turns per visible trace `1.2341 -> 1.2422`;
- special ratio `0.1497 -> 0.1445`;
- straight-visible fraction `0.1217 -> 0.1112`;
- 92% of the removed total source traces were non-visible; direct raster comparison retains comparable texture, articulation and negative-space balance.

Qualification: **154/154 active release tests PASS**, maintained stress **1/1 PASS** on candidate and promoted canonical source. Production SHA-256: `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`.

Per the ordinary optimization cadence, LOCAL-2 does **not** run 0.35. The next stage is **MAIN-1 instrumentation**: localize the remaining per-operation CPU amplification before changing MAIN routing semantics.


## 10. Stage C result — MAIN-1 exact-local proof reuse PROMOTED + final 0.35 gate CLOSED (2026-08-26 00:08 IST)

MAIN-1 reuses exact proposal-membership and successful future-leg legality proofs only while their precise local committed-path/source-egress dependencies remain unchanged. It does not alter proposal RNG, scoring, route topology, geometry admission, rollback policy, or seed ownership.

Ordinary seeds-102+104 0.75 -> 0.5 qualification improved normalized MAIN CPU/useful-work growth from **2.215492x -> 1.432545x** with byte-identical geometry/topology and aggregate 0.5 gesture checks `149,901 -> 130,062`. Canonical promotion gate: **156/156 PASS**, maintained stress **1/1 PASS**.

The reserved final fine-scale gate was then completed. A provisional cross-host calculation was rejected as invalid evidence; fresh adjacent 0.5 timings were collected on the same host as the 0.35 pair.

| Category / overall phase | BEFORE Work Growth | BEFORE CPU Growth | BEFORE CPU/Work Growth | AFTER Work Growth | AFTER CPU Growth | AFTER CPU/Work Growth |
|---|---:|---:|---:|---:|---:|---:|
| MAIN emitted segments / MAIN phase overall, 0.5 -> 0.35 | 2.063991x | 2.141140x | **1.037378x** | 2.063991x | 2.074347x | **1.005017x** |

Aggregate useful MAIN segments are `4,610 -> 9,515`. Same-host aggregate MAIN CPU is `50.811738 -> 108.795035 s` BEFORE and `51.261908 -> 106.334978 s` AFTER. At 0.35, gesture-clear checks fall `296,105 -> 266,481`; all deterministic output hashes and routing-topology counters match BEFORE/AFTER.

**Long/fine scaling optimization phase decision: CLOSED.** LOCAL-1, LOCAL-2, and MAIN-1 are promoted. The remaining task is the separate full `1:6 @ 0.35` operational benchmark to quantify end-to-end production runtime/RSS after these scaling changes; it is not an open correctness or MAIN-scaling candidate stage.

---

## 11. Full long-board operational recheck after LOCAL-1/LOCAL-2/MAIN-1 — PHASE REOPENED (2026-08-26)

The post-optimization full-board check was run on the authoritative renderer SHA `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`, exact base seed 0, scale 0.35, using the same phase harness for `1:1` and `1:6` sequentially on the same host. This is the governing long-board scaling check; the earlier ordinary square-scale gates remain valid evidence for their wedges but are not sufficient to close the long-board phase.

| Metric | `1:1 @ 0.35` | `1:6 @ 0.35` | Growth | Growth / relevant work |
|---|---:|---:|---:|---:|
| chips | 17 | 98 | 5.765x | — |
| MAIN launch traces | 711 | 4,124 | 5.800x | — |
| LOCAL traces | 1,295 | 7,869 | 6.076x | — |
| residual components | 340 | 2,047 | 6.021x | — |
| gesture-clear checks | 149,654 | 873,543 | 5.837x | — |
| lookaheads | 131,687 | 801,235 | 6.084x | — |
| MAIN CPU | 58.667 s | 427.371 s | 7.285x | **1.256x / MAIN launch** |
| LOCAL CPU | 28.556 s | 238.630 s | 8.357x | **1.375x / LOCAL trace** |
| component-place CPU | 7.308 s | 51.230 s | 7.010x | **1.164x / component** |
| whole-render CPU | 96.822 s | 729.786 s | 7.537x | **1.261x / visible routing work** |
| peak RSS | 235,092 KiB | 802,392 KiB | 3.413x | sublinear vs work |

Visible routing work here is MAIN launch traces + LOCAL traces: `2,006 -> 11,993`, growth `5.9786x`. Whole-render CPU/work therefore grows **1.2607x**. Relative to plain 6x territory the normalized whole-render CPU growth is similarly **1.2562x**; the conclusion does not depend on using board area as the normalizer.

A six-times-square CPU extrapolation on this same host is `580.931 s`; actual long-board CPU is `729.786 s`, leaving `148.855 s` of same-host excess. Phase excess over the same six-times-square extrapolation is approximately MAIN `+75.37 s`, LOCAL `+67.30 s`, component placement `+7.38 s`, with other measured phases near linear. Thus the remaining tax is overwhelmingly MAIN + LOCAL.

**Decision: the long/fine scaling phase is REOPENED.** The ordinary 0.75->0.5 and phase-end 0.5->0.35 square-scale qualifications correctly established that the promoted wedges do not introduce fine-scale amplification, but they did not eliminate aspect-driven amplification on the actual `1:6` board. The full operational fixture gets the final word. There is no correctness regression and no production rollback: the promoted optimizations are retained because they remove real work and pass all gates, but additional long-aspect MAIN/LOCAL optimization is required before the phase can be called complete.

The absolute `729.786 s` result must not be compared directly to the historical `614.485 s` as a speed regression because the current execution host is materially slower; the same-host square control is `96.822 s` versus the historical `75.957 s`. Use same-host growth ratios for the scaling decision.


## 12. Reopened phase — LOCAL aspect-amplification localization (2026-08-26 01:23 IST)

No production renderer change. Authoritative SHA remains `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`. The full same-host `1:1 -> 1:6 @ 0.35` operational result reopened the phase because whole-render CPU/useful-routing-work grows `1.2607x`; LOCAL is the steepest remaining phase at `1.375x CPU / emitted LOCAL trace`, ahead of MAIN `1.256x / launch` and components `1.164x / component`.

A zero-policy timing probe on seed 0 at scale 0.75 localized the remaining LOCAL aspect tax without changing renderer behavior:

| LOCAL quantity / subphase | `1:1` | `1:6` | Growth |
|---|---:|---:|---:|
| visible LOCAL traces | 166 | 1,000 | 6.024x |
| total LOCAL traces | 272 | 1,510 | 5.551x |
| residual open cells | 2,741 | 16,098 | 5.873x |
| residual regions | 47 | 344 | **7.319x** |
| total LOCAL CPU (probe harness) | 15.085 s | 118.509 s | **7.856x** |
| `_launch_local_gap_fronts()` | 1.158 s | 9.138 s | **7.894x** |
| `_gesture_clear()` | 1.578 s | 9.531 s | 6.038x |
| `_run_local_gap_fast_rounds()` | 1.712 s | 10.673 s | 6.236x |
| direct mop-up | 0.880 s | 5.290 s | 6.009x |
| fragment mop-up | 1.077 s | 5.414 s | 5.026x |
| `_local_gap_target()` | 0.135 s | 0.650 s | 4.828x |

The evidence rules out target selection and ordinary exact gesture legality as the primary residual amplifier. The strongest correlation is fragmentation of the residual field (`47 -> 344` regions) combined with repeated launch scheduling.

A follow-up cProfile is diagnostic only (not timing evidence) and points one level deeper. `_launch_local_gap_fronts()` grows from about `1.696 s -> 13.940 s` under profiling. On the long proxy, Shapely `STRtree.query_nearest` contributes `4.312 s` across 1,012 calls, while `_residual_gap_regions()` itself costs `4.828 s` versus `0.653 s` square (~7.39x). Candidate scoring/allocation and spatial queries inside launch scheduling therefore remain the earned implementation-audit target.

**Current decision:** no new renderer candidate yet. Retain all promoted LOCAL-1/LOCAL-2/MAIN-1 work. Continue the reopened LOCAL pass by decomposing `_launch_local_gap_fronts()` into nearest-geometry tree construction/query and whole-candidate-pool scoring/allocation work, then remove the work term that scales with fragmented regions rather than actual accepted LOCAL service. Do not change density, service floors, seeds, geometry admission, or board grammar.

## 13. LOCAL-3 nearest-query localization + tiled-static partial result — 2026-08-26 02:55 IST

Production remains SHA `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`; no candidate is promoted. On the `0.75 / seed 0` `1:1 -> 1:6` proxy, the launch scheduler's nearest-distance block is the steepest measured LOCAL subterm. Dedicated splitting shows static `STRtree.query_nearest` CPU grows ~`13.77x` while static geometry grows ~`5.85x`, and path `query_nearest` grows ~`10.64x` while path geometry grows ~`5.62x`; tree builds themselves are negligible on the square fixture. This localizes the residual aspect tax to global nearest-query behavior rather than tree construction, target selection, gesture legality, or global candidate sorting.

An exact static score-radius tiled implementation (`archive/inflight/local3_static_tiled_nearest_renderer.py`, SHA `a2ca7b657894f74596231382148e9aa0e774f376f1248b9acbd130a710353569`) completed after the prior interruption. It preserves all observed LOCAL counters. `_launch_local_gap_fronts()` improves from production `1.0941 -> 8.8320 s` (`8.073x`) to tiled `1.1400 -> 8.3792 s` (`7.350x`), reducing launch CPU/work growth from ~`1.340x` to ~`1.220x`. However total proxy CPU changes from production `14.6129 -> 116.8039 s` to tiled `14.8584 -> 120.2822 s`, so governing whole-LOCAL CPU/work does not improve in that measurement (~`1.327x -> 1.344x`). Decision: **MODIFY / not promotable**. The measured global-nearest pathology remains the target, but the representation must translate its scheduler win into overall LOCAL scaling.

## 13. Reopened LOCAL-3: denominator correction + two-level static broad phase (2026-08-26 04:06 IST)

Production remains SHA-256 `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`. No LOCAL-3 candidate is promoted.

The post-02:56 continuation tested several exact implementation variants and rejected them when whole-LOCAL scaling did not improve:

- finer committed-path SpatialHash cells: behavior-exact but slower at both aspects;
- extending MAIN first-leg proof reuse to LOCAL: redundant, effectively zero useful hits because LOCAL proposal-pool replay already removes that repetition;
- extending MAIN holistic future-success proof reuse to LOCAL: inapplicable because the lightweight LOCAL router does not call holistic `_future_options()`.

A more important measurement corrected the work denominator. On the stable `0.75 / seed 0`, `1:1 -> 1:6` LOCAL aspect proxy:

- visible LOCAL traces grow `6.024x`;
- nearby committed-path records actually visited by `_gesture_clear()` grow `6.862x`;
- nearby path records reaching exact GEOS collision predicates grow `6.830x`;
- static primitive records returned to `_gesture_clear()` grow `7.633x`.

Therefore a material fraction of the prior `1.375x CPU / visible trace` long-board ratio is **real geometric interaction-density growth**, not pure algorithmic overhead. Future LOCAL scaling judgments must include collision-interaction work, not normalize only by emitted traces.

Static broad-phase duplication remains a legitimate removable term. Across LOCAL gesture queries, roughly `8.6-8.8` static primitive records correspond to each actually-nearby component/group. The renderer already owns lazy per-Group primitive indexes, so an unpromoted candidate at `archive/inflight/local3_two_level_static_renderer.py` replaces global primitive fan-out with a two-level exact broad phase: global group lookup followed by exact per-group primitive lookup. The square screen is behavior-exact and near cost-neutral: total CPU `14.613 -> 14.619 s`, `_gesture_clear()` `1.499 -> 1.442 s`, all LOCAL counters identical, zero clearance/overlap violations. The decisive long `1:6 @ 0.75 / seed 0` result was not collected before the execution window ended, so this candidate is **ACTIVE / UNQUALIFIED**, not accepted or rejected.

### Process correction

The recent LOCAL-3 sequence became too micro-iterative. Do not continue indefinitely trying nearby broad-phase variants. The next continuation should:

1. qualify the existing two-level-static candidate once on the long proxy;
2. if it does not produce a material whole-LOCAL normalized gain (not just a subroutine win), reject it and stop LOCAL-3 micro-optimization;
3. recompute LOCAL normalized scaling using a work denominator that includes exact collision interactions / nearby static groups, so genuine density is not mislabeled superlinearity;
4. only reopen another LOCAL architectural wedge if a meaningful residual CPU-per-relevant-work amplifier remains;
5. otherwise move to the remaining MAIN aspect tax, using the same corrected relevant-work methodology.

The objective remains near-linear CPU in the scale of relevant geometric work; the renderer is not required to make a physically denser interaction field cost the same CPU per emitted trace.


## 14. Optimization stop / final LOCAL-3 disposition — 2026-08-26 04:40 IST

**Optimization is STOPPED by explicit project decision.** No new optimization branch should be started from this checkpoint unless the user explicitly reopens optimization later. All previously promoted production work is retained; authoritative renderer SHA-256 remains `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`.

### Final remaining candidate disposition

The only remaining unqualified renderer candidate was `archive/inflight/local3_two_level_static_renderer.py` (two-level static group -> primitive collision broad phase). Its square screen was behavior-exact and near cost-neutral, but the decisive `1:6 @ 0.75 / seed 0` qualification attempt did **not** complete inside a 300-second wrapper and emitted no durable result; the corresponding production long proxy is recorded at ~`116.804 s`. No candidate process survived the wrapper. This is a decisive whole-LOCAL performance rejection: **REJECT / DO NOT PROMOTE**. Do not iterate nearby broad-phase variants as a continuation of LOCAL-3.

### Corrected interpretation of residual LOCAL scaling

The operational long-board result still shows `1.375x CPU / visible LOCAL trace` when trace count alone is used as the denominator. That number is not pure algorithmic superlinearity. On the stable `0.75 / seed 0`, `1:1 -> 1:6` LOCAL proxy:

- visible LOCAL traces grow `6.024x`;
- path records reaching exact GEOS collision predicates grow `6.830x`;
- static primitive records returned to LOCAL gesture collision checks grow `7.633x`;
- measured LOCAL CPU grows `7.856x`.

Thus CPU growth relative to measured collision-interaction growth is roughly `1.15x` versus exact path-GEOS work and `1.03x` versus static primitive interaction work. There is no single scalar denominator that perfectly combines these heterogeneous interactions, but the evidence is sufficient to reject the earlier interpretation that LOCAL is doing ~37.5% extra algorithmic work for an otherwise identical physical task. A substantial part of the trace-normalized rise is genuine local interaction-density growth on the elongated board.

### Final known residuals accepted/deferred

The completed same-host full `1:1 -> 1:6 @ 0.35 / seed 0` operational comparison remains valid evidence of residual aspect cost:

- whole render: `5.979x` visible routing work, `7.537x` CPU => `1.261x CPU / visible-routing-work`;
- MAIN: `5.800x` launches, `7.285x` CPU => `1.256x CPU / launch`;
- LOCAL: `6.076x` visible traces, `8.357x` CPU => `1.375x CPU / visible trace`, with the collision-work denominator correction above;
- components: `6.021x` component work, `7.010x` CPU => `1.164x CPU / component`.

These residuals are **known and accepted/deferred**, not open optimization tasks. In particular, MAIN aspect scaling was not reopened after the LOCAL-3 stop decision. Future work should proceed to product/behavior roadmap items unless optimization is explicitly reopened.

### Final validation

Canonical production was revalidated after rejecting the last candidate: **156/156 active release tests PASS** and maintained geometry stress **1/1 PASS**. No production renderer source change occurred during LOCAL-3 closure.
