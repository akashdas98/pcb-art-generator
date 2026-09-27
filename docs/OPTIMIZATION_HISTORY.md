# V47 Optimization History — Compact Authoritative Record

This document replaces the previous forest of dated status files, raw benchmark summaries, candidate notes, and profiler dumps. It preserves the decisions and measurements needed to understand why the current architecture exists without keeping every experiment artifact in the repository.

## 1. Objective and baseline problem

The optimization pass was governed by one principle: expensive renderer phases should scale as close to linearly as reasonably possible with their **relevant logical/useful/generated work**. Static speedups alone did not count if CPU-per-work scaling stayed equally superlinear or worsened.

The V45/V46 transition made scale/aspect behavior physically meaningful but exposed severe work amplification at fine scales and large logical territories. A correctness-focused persistence repair in early V47 restored natural MAIN routing behavior but greatly increased expensive recovery/search work. The subsequent pass therefore had to preserve behavior while eliminating global/repeated work.

## 2. Program map — Items 1–26

| # | Target | Final status / outcome |
|---|---|---|
| 1 | canonical component/LOCAL physical service model | DONE |
| 2 | LOCAL live residual-debt retirement | DONE |
| 3 | LOCAL fragment candidate-work budget | DONE |
| 4 | LOCAL partial-debt rescue work budget | DONE |
| 5 | LOCAL direct-mop-up work/service sampling | DONE |
| 6 | LOCAL exact-failure polling certificates | DONE |
| 7 | LOCAL bounded direct run-family stochastic retry | DONE |
| 8 | LOCAL emergency cleanup targets hard floor | DONE |
| 9 | LOCAL two-stage spread + physical-debt rescue | DONE |
| 10 | LOCAL record-specific committed-path AABB broad phase | DONE |
| 11 | LOCAL debt-family retirement / run cache / pre-geometry certificates | DONE |
| 12 | LOCAL normalized acceptance | DONE / near-linear |
| 13 | MAIN 0.5-vs-0.35 work isolation | DONE |
| 14 | MAIN immutable frame/chip capacity rescoring cache | DONE |
| 15 | MAIN 0.75->0.5 regime-transition audit | DONE |
| 16 | MAIN 0.5->0.35 continuation/amplification audit | DONE |
| 17 | historical MAIN scheduler approach decision | DONE / RETAIN |
| 18 | reject flat-speed-only structural replay | DONE / rejected |
| 19 | MAIN duplicate whole-board repair/preflight audit | DONE |
| 20 | MAIN hard-stop rollback + exact-lane geometry reuse / immutable STRtree | DONE / promoted |
| 21 | MAIN proposal/future-option residual | DONE / four structural subtargets promoted, residual exhausted |
| 22 | MAIN end-of-phase acceptance | DONE / near-linear-practically-exhausted on qualified fixture |
| 23 | component gap-first/residual scaling | DONE |
| 24 | localize post-MAIN component retry scope | DONE |
| 25 | chip placement/uniqueness/global-population residual | DONE / exhausted |
| 26 | final whole-render 1:1 three-scale acceptance | DONE |

## 2A. Per-target normalized scaling ledger

The numbered program mixed **promotions** with audits, isolation stages, RETAIN decisions, rejections, and final acceptance gates. Therefore a standalone BEFORE -> AFTER CPU/work number does **not** exist for every item. `N/A` below means the item did not itself promote a code change with a valid paired useful-work denominator; the row records the quantitative evidence that closed the target instead of inventing an A/B number. Different rows sometimes use different phase-native denominators, so do not chain them as one continuous benchmark series.

| # | Target | Normalized CPU/work BEFORE -> AFTER | Closure evidence / note |
|---|---|---|---|
| 1 | canonical component/LOCAL physical service model | **N/A** | Architectural accounting correction. Micro-proof: with an 8x larger coverage map, historical service-read CPU grew ~8x while the incremental read stayed ~1x; no adjacent-scale phase CPU/work A/B was claimed. |
| 2 | LOCAL live residual-debt retirement | **N/A** | No accepted dense 0.5 paired scaling A/B at this checkpoint. 1.0 LOCAL CPU fell ~16%; 0.75 was behavior-identical/inert. |
| 3 | LOCAL fragment candidate-work budget | **1.802x -> 1.602x** | 0.75->0.5 LOCAL CPU per canonical service cell; fragment candidate work/territory also bent 3.482x -> 2.007x. |
| 4 | LOCAL partial-debt rescue work budget | **N/A** | The rescue phase is absent at 0.75, so a phase-native adjacent CPU/work ratio is undefined. At 0.5 candidate work fell 8,774 -> 4,800 (-45.3%) and LOCAL CPU 13.556s -> 13.298s. |
| 5 | LOCAL direct-mop-up work/service sampling | **N/A formal useful-work A/B** | Territory proxy improved 1.659x -> 1.523x CPU/territory; spawn-work/territory 1.376x -> 1.095x. This row is intentionally not mislabeled as phase-native CPU/work. |
| 6 | LOCAL exact-failure polling certificates | **1.461x -> 1.407x** | 0.75->0.5 LOCAL CPU per actual serviced residual area. |
| 7 | LOCAL bounded direct run-family stochastic retry | **1.390x -> 1.259x** | 0.75->0.5 LOCAL CPU per actual serviced residual area; run-family attempts/territory 2.668x -> 1.523x. |
| 8 | LOCAL emergency cleanup targets hard floor | **1.219x -> 1.158x** | 0.75->0.5 LOCAL CPU per actual serviced area. |
| 9 | LOCAL two-stage spread + physical-debt rescue | **1.187x -> 1.183x** | CPU/service timing barely moved, but deterministic spawn-attempt work/territory improved **1.075x -> 1.002x**, which was the causal scaling objective of this item. |
| 10 | LOCAL record-specific committed-path AABB broad phase | **1.028x -> 1.019x** | Paired 0.75->0.5 CPU per serviced grid-cell-equivalent; used for delta only because absolute timing level differed from prior checkpoints. |
| 11 | LOCAL debt-family retirement / run cache / pre-geometry certificates | **~1.249x -> ~1.145x** directly; **~1.107x** after the remaining item-11 cleanup | 0.5->0.35 CPU per emitted LOCAL centerline. The debt-family promotion alone gave ~1.145x; subsequent bounded/cache/certificate cleanup brought the fine-scale closure to ~1.107x. |
| 12 | LOCAL normalized acceptance | **phase closure, not a new A/B** | Final accepted LOCAL: ~0.997x over 0.75->0.5 and ~1.107x over 0.5->0.35. Historical ordinary baseline was roughly ~1.65-1.80x depending the contemporaneous useful-work denominator. |
| 13 | MAIN 0.5-vs-0.35 work isolation | **N/A — audit** | Isolated the fine-scale MAIN amplification and earned the next causal work; no renderer promotion. |
| 14 | MAIN immutable frame/chip capacity rescoring cache | **1.244209x -> 1.196405x** | 0.5->0.35 MAIN CPU per emitted centerline, behavior-identical. |
| 15 | MAIN 0.75->0.5 regime-transition audit | **N/A — audit** | Closed the approach/regime question; no standalone promoted A/B. |
| 16 | MAIN 0.5->0.35 continuation/amplification audit | **N/A — audit** | Causal continuation audit; no standalone promoted A/B. |
| 17 | historical MAIN scheduler approach decision | **N/A — RETAIN decision** | Existing scheduler retained after approach audit; no code change. |
| 18 | reject flat-speed-only structural replay | **N/A — rejected** | Candidate did not satisfy the scaling objective; authority/curve unchanged. |
| 19 | MAIN duplicate whole-board repair/preflight audit | **N/A formal CPU/work A/B** | Promoted removal of one redundant whole-board materialization in repair regimes; exact geometry unchanged. The report intentionally used pass-count/cost evidence rather than claiming a paired normalized overall curve. |
| 20 | MAIN hard-stop rollback + exact-lane geometry reuse / immutable STRtree | **hard-stop fine: 1.249420x -> 1.228269x**; **lane/STRtree fine overall: 1.214459x -> 1.136864x** | Separate controlled paired harnesses. Lane/STRtree ordinary overall also improved 1.370625x -> 1.354483x. |
| 21 | MAIN proposal/future-option residual | **four promoted subtargets** | Exact replay overall ~1.3425x -> ~1.2803x; future-certificate overall 1.252816x -> 1.240565x; regional-success overall 1.255274x -> 1.236641x; grammar-preflight overall 1.255688x -> 1.214384x. Category-native wins were stronger. |
| 22 | MAIN end-of-phase acceptance | **phase closure, not a new A/B** | Final accepted MAIN CPU/useful-work: **1.022314x** over 0.75->0.5 and **1.165588x** over 0.5->0.35. Pre-dedicated ordinary MAIN baseline was ~1.255x. |
| 23 | component gap-first/residual scaling | **multi-step:** 1.492711x -> 1.411904x -> 1.233736x; later ~1.362x -> ~1.275x and ~1.295x -> ~1.258x subtargets | All are component-native paired subtargets on their then-current authority. Final 0.5->0.35 component CPU/work acceptance was **~0.949x**. |
| 24 | localize post-MAIN component retry scope | **N/A — containment/correctness architecture** | Valid MAIN is no longer discarded for ordinary component retry failure; target was failure-scope locality, not a scaling A/B. |
| 25 | chip placement/uniqueness/global-population residual | **N/A — exhausted/rejected** | Two measured candidates rejected; ordinary governing fixtures had zero global uniqueness retries. Current behavior retained. |
| 26 | final whole-render 1:1 three-scale acceptance | **0.75->0.5: 1.210989x -> 1.195375x; 0.5->0.35: 1.179953x -> 1.147276x** | Whole-render CPU normalized by total-primitive proxy, BEFORE vs final AFTER. This was the final aggregate closure metric, not a replacement for phase-native denominators. |

## 3. LOCAL architecture changes

The original expensive LOCAL behavior tied work too closely to repeated success/output attempts and broad rescans. The accepted architecture moved service to physical residual debt and bounded local work:

- canonical physical service cells and live residual-debt accounting;
- candidate-work budgets proportional to normalized territory rather than successful outputs;
- partial-debt rescue budgets and direct mop-up based on physical service opportunity;
- exact failure certificates to avoid repeatedly proving the same impossible local action;
- bounded direct run-family retry rather than open-ended retries;
- emergency cleanup aimed at the hard floor, not repeatedly sampled preference;
- two-stage spread followed by physical-debt rescue;
- record-specific committed-path AABB broad phase and local target/capture state;
- retirement/release of finished local debt families and rebuildable transient state.

Final accepted normalized LOCAL CPU/visible-work growth was approximately:

- 0.75 -> 0.5: **~0.997x** CPU per visible centerline growth;
- 0.5 -> 0.35: **~1.107x**.

Historically the ordinary transition had been roughly ~1.65–1.80x depending on the contemporaneous exact useful-work denominator.

## 4. MAIN architecture changes

Important accepted MAIN changes included:

### Item 20 — incremental rollback + exact-lane geometry reuse / immutable spatial snapshot

The repair regime stopped repeatedly rebuilding broad geometric state for work whose dependency set was unchanged. Exact lane geometry and immutable STRtree snapshots were reused while mutable route state remained correctly incremental. This removed large repeated repair/preflight work without weakening clearance semantics.

### Item 21 promoted residual subtargets

1. **Exact multi-draw proposal replay** — repeated stochastic draws inside one immutable proposal context reuse the same legality/corridor/loop-risk traversal while preserving RNG/output semantics. Proposal-category CPU/work growth improved approximately `1.3751x -> 1.3070x`; same-harness overall MAIN `1.3425x -> 1.2803x`.
2. **Future-certificate-first lazy corridor materialization** — consult a live exact future-failure certificate before constructing geometry for an already-proven blocked future. Future corridor constructions dropped from 14,143 -> 11,375 at 0.75 and 33,401 -> 25,454 at 0.5; future-corridor CPU/work improved `1.171741x -> 1.113387x`.
3. **Regional successful path-clear proof reuse** — reuse successful path-collision subproofs only when the exact local path-record dependency membership and spatial generation remain unchanged; all static/source/endpoint/grammar checks stay live. `_gesture_clear` CPU/work improved about `1.229607x -> 1.212888x`.
4. **Local grammar/preflight structural work** — retained exact behavior while removing repeated proposal/grammar work that had already been proven within the same immutable context.

Final accepted MAIN CPU/useful-work growth:

- 0.75 -> 0.5: **1.022314x**;
- 0.5 -> 0.35: **1.165588x**.

The fine-scale tail was accepted as behavior-bearing lifecycle/proposal work after causal residual audits found no justified remaining population-coupled inner kernel on the qualified fixture.

## 5. Important rejected MAIN approach families

These were not forgotten; they were rejected because they worsened normalized scaling, behavior, or complexity relative to benefit:

- broad role-specific/generic foresight removal and target-aware connection horizons;
- causal waiter/dependency graph for blocked-state proof — exact but pathological bookkeeping at density;
- decision-junction traceback — passed correctness but reduced useful work / became pathological at 0.5;
- generic exhausted atomic HOLD / soft-future fallbacks — shifted conflict pressure into hard-stop/traceback debt;
- on-demand/full legal-universe conflict expansion — expensive combinatorial work or behavior degradation;
- planner-only/unified singleton connection settlement — changed connection population / did not win the governing scaling curve;
- service-wide `distance < gap` rewrite replacing `intersects` + `distance` — lost the cheap dense true-collision short circuit;
- suffix-replay/localized materialization infrastructure — reusable fraction too small for dependency complexity;
- persistent loop-risk cache / reuse of round-legality proof — exact but bookkeeping overhead worsened affected scaling;
- `_front_half_width()` epoch/container cache — lower absolute CPU but CPU/work scaling worsened (~1.189x -> ~1.333x), so rejected under the scaling objective;
- immutable score-static-clearance cache — exact but no affected normalized curve improvement.

## 6. Components

The component phase moved away from global/cross-product style residual work toward gap-first/local service:

- gap-aware component-first residual fill;
- static-clearance certificates for repeated immutable rejection cases;
- attachment-opportunity-first ordering, avoiding unnecessary full candidate validation before proving an attachment opportunity exists;
- local source-first/residual-region discovery instead of broad repeated global ranking;
- ordinary post-MAIN component retries localized inside the component phase so valid MAIN routing is not discarded for recoverable component placement failure.

A key attachment-opportunity promotion kept governing output exact and reduced 0.5 `_component_candidate_valid()` calls from 335 to 190. Two-run CPU/work growth improved from roughly `1.409492x` to `1.233736x` relative to the immediately preceding authority. Final component-native 0.5 -> 0.35 CPU/work was approximately **0.949x**, and no new fine-scale component regime was found.

The old global component collection cross-sample exact/near-duplicate aesthetic history/dedupe system was later removed as unnecessary.

## 7. Retry scope and failure containment

A major architectural rule from the optimization pass is that a recoverable downstream phase failure should not discard expensive valid upstream work. Post-MAIN ordinary component recovery was localized so valid MAIN routing is retained while component attempts progress. This principle must be preserved when diagnosing the newly observed long/fine whole-sample rejection behavior.

## 8. Memory/lifetime work

Earlier fine/long renderer states reached roughly the ~900 MB class. The pass introduced phase-local caches/spatial structures and explicit release of rebuildable state once a phase is done. Final guarded 1:1 @ 0.35 acceptance recorded approximately **235,376 KiB** peak RSS (~230 MiB). Memory work is considered complete unless new evidence shows a lifetime regression.

## 9. Final qualified whole-render acceptance

Final Item-26 fixture:

- aspect 1:1;
- base seed `202608182200`;
- logical sample index 1 / derived seed `16875795162674203288`;
- scale sequence 0.75 -> 0.5 -> 0.35;
- all three completed with `restart_index=0` and no geometry/clearance/octilinear violations.

AFTER whole-render results:

| scale | whole CPU | MAIN CPU | LOCAL CPU | component placement CPU | total primitives | max RSS KiB |
|---|---:|---:|---:|---:|---:|---:|
| 0.75 | 11.0578 s | 6.4209 s | 3.4854 s | 0.8339 s | 2,792 | 171,768 |
| 0.5 | 30.7021 s | 16.7095 s | 10.6339 s | 2.4200 s | 6,485 | 170,608 |
| 0.35 | 76.4005 s | 43.0312 s | 26.0253 s | 5.1663 s | 14,066 | 235,376 |

Whole-render total-primitive proxy **late-checkpoint BEFORE vs final AFTER**:

> **Important:** this `BEFORE` is the preserved Aug-19 pre-dedicated-scaling authority (`65dfff...`), **not the beginning of the full optimization run**. These numbers measure the final tranche only and must not be quoted as the start-to-finish renderer-wide gain.

| interval | late-checkpoint BEFORE CPU/work | final AFTER CPU/work |
|---|---:|---:|
| 0.75 -> 0.5 | 1.210989x | **1.195375x** |
| 0.5 -> 0.35 | 1.179953x | **1.147276x** |

A same-runtime reconstruction using the earlier Aug-18 authority `63e045...` and final optimization authority `8a43f6...` on seed `20260816`, sample 0, gives a clean start-era whole-render comparison for the 1.0 -> 0.75 interval:

| state | scale 1.0 CPU | scale 0.75 CPU | primitive growth | CPU growth | CPU/primitive growth |
|---|---:|---:|---:|---:|---:|
| early optimization authority `63e045...` | 4.6997 s | 10.5232 s | 2.0465x | 2.2392x | **1.0942x** |
| final optimization authority `8a43f6...` | 4.9527 s | 8.5484 s | 1.9326x | 1.7259x | **0.8930x** |

This reconstructible interval therefore moved from about **+9.4% superlinear CPU per emitted primitive to ~10.7% sublinear**. It is evidence of a substantial full-run scaling improvement, but it is only one adjacent interval; the compact repository does not currently contain an equally clean same-runtime start-era 0.5/0.35 whole-render reconstruction. Do not extrapolate a full three-scale percentage from the late-checkpoint Item-26 table.

Optimization-closure correctness gate was **134/134 PASS**; the current seed-totality branch has since expanded the active gate to **137/137**.

## 10. Critical qualification caveat discovered after closure

The scaling numbers above are valid for what they measured, but Item 26 used **1:1 only**. A 1:1 @ 0.35 fixture covers about 8.16 canonical territories. A 1:6 @ 0.35 board covers about 48.98 territories — six times more actual logical territory and roughly ~98 chip opportunities under the current law.

The user later observed a local/Codex run in that long/fine regime where 8/8 logical samples were rejected after ~52 minutes and no SVG was emitted. The current batch skip path loses the exact `RuntimeError` reason, so the failing invariant is not yet known.

This does not automatically falsify the near-linear per-attempt/phase CPU-work measurements; repeated expensive rejected attempts can make expected time-to-valid-output terrible even when each attempt scales acceptably. It does mean the optimization program's final production qualification was too narrow to certify long/fine acceptance robustness.

Historical V47 evidence contains a successful `1200:6248 @ 0.35` (~42.5 territories) sample with 85 chips and 696 collections, so large full generation was possible earlier. The current rejection behavior is therefore a real operational regression or uncovered regime and must be diagnosed separately.

Future qualification must require predetermined-seed totality, record exact failing phase/reason for any assertion, and measure wasted CPU/termination behavior — not merely CPU per useful work on successful fixtures. “Acceptance rate” is not a production target.

## 11. Current post-optimization behavior issue

Premature MAIN-line termination is being handled separately from the completed scaling pass. The current V3 candidate is preserved under `work/inflight/` but remains unpromoted and paused. Exact status and metrics are in `CONTEXT.md`.

## 11. Seed-totality reframing (2026-08-22)

Whole-sample "acceptance probability" is no longer a production metric or design goal. The required contract is seed totality: valid canvas/scale/seed -> one deterministic valid board. Local proposal rejection remains legitimate; whole logical samples must not be discarded in favor of another seed. Final validation is an assertion of construction correctness.

A fresh exact 1:6 @ 0.35 probe using base seed `202608182200`, logical index 0 (derived seed `505888913089298392`) succeeded with 98 chips and 810 collections in ~849.9 s without a whole-sample retry. Combined with the user-observed separate 0/8 discarded-sample run, this establishes a seed/path-dependent totality defect rather than universal impossibility of the regime.

## 12. Seed-totality repair after optimization closure

The post-closure long/fine failure exposed a correctness contract that the scaling pass had not qualified: a valid deterministic seed must not be discarded. The current repair branch removes whole-sample skip/reseed behavior and moves ordinary recovery to causal phases. Completed architectural corrections include total collection-family quota construction, defect-scaled MAIN preflight repair, and component hard-floor completion bounded by monotonic residual-cell retirement rather than an arbitrary global filler count.

Current regression gate: **137/137 PASS + 1/1 maintained stress PASS**. Long/fine totality is still open; in particular, the historical `1200:6248 @ 0.35`, seed `20260816`, did not finish a current MAIN-only reproduction within a 20-minute execution boundary and therefore is not yet qualified.

## 13. Unpromoted termination-tail continuation and embedded-lane residue

After the 23:19 seed-totality checkpoint, an unpromoted MAIN termination repair made failed terminal-separation work transactional and added bounded affected-lane-only tail replan. The old fallback that legalized an embedded mature lane solely because attempts were exhausted was removed. The working tree passed **139/139 active tests + 1/1 maintained stress**, but this did not qualify the change for promotion.

The governing historical `1200:6248 @ 0.35`, base seed `20260816`, still failed after about **278.6 s** with `V47 persistence horizon unresolved`. A post-patch debt inspection exposed **54 mature residual MAIN lanes**: 50 `between_siblings` only, 2 fragment-embedded only, and 2 fragment-embedded plus `between_siblings`; there was no short-length/source-egress/fan/fragment-birth/unfinished-branch debt. This showed the former exhaustion fallback had hidden a systematic terminal-completion problem.

The next earned diagnostic is continuation feasibility on those exact mature residual lanes. Legal straight/±45 continuation means the shared/fixed persistence horizon is prematurely ending construction; zero legal continuation means the lane requires a deterministic local physical terminal resolution. Whole-seed rejection is invalid in either case. This work remains **INFLIGHT / UNPROMOTED**.

## 14. Proactive line-survival scaling qualification — 2026-08-24

The post-V48 line-murder repair was promoted only after the behavior fix cleared the same scaling objective used by the optimization pass. On 1:1 seeds 102+104, emitted visible MAIN centerline modules were the useful-work denominator.

| state | 0.75 work | 0.5 work | work growth | 0.75 CPU | 0.5 CPU | CPU growth | CPU/work growth |
|---|---:|---:|---:|---:|---:|---:|---:|
| pre-promotion V48 | 4,333.518 | 10,496.776 | 2.422x | 12.304 s | 39.742 s | 3.230x | **1.333x** |
| promoted line-survival | 4,339.302 | 10,580.413 | 2.438x | 12.993 s | 38.148 s | 2.936x | **1.204x** |

Final promoted 0.5 -> 0.35 on the same pair: work `10,580.413 -> 22,071.951` = 2.086x; CPU `38.148 -> 81.946 s` = 2.148x; CPU/work = **1.030x**.

The investigation also demonstrated why counters cannot substitute for category CPU: fairness conflict combinations scale worse, but the HOLD solver measured as a tiny CPU category; proposal construction dominates MAIN. Deterministic proposal-call/work scaling stayed essentially unchanged (~1.355x -> ~1.357x), while the clean overall normalized CPU curve improved materially. Full causal/rejected-approach history is in `docs/LINE_MURDER_PROMOTION_HISTORY.md`.

## 2026-08-25 — long/fine performance scaling audit

After long/fine seed totality was promoted, current V48 was audited for the remaining `1:6 @ 0.35` runtime/RSS problem without changing renderer behavior.

Same-seed seed-0 `1:1 -> 1:6` scaling shows ~6x high-level generated work but **8.09x** whole-render CPU. Linear extrapolation from the current square board predicts ~455.7 CPU-s versus 614.5 CPU-s actual, a ~158.7 s scaling tax. LOCAL contributes ~58% of that excess, MAIN ~37%, component placement ~3%.

The strongest LOCAL mechanism is repeated polling of already-quarantined direct-run families: 10,015 long-board quarantined families generate **5,538,055** quarantine-skip checks. A second cliff comes from three whole-field partial-service rescue waves (18x candidate tokens for 6x territory) followed by a 136,597-candidate deterministic debt-completion tail.

MAIN high-level work is near territory-linear (~6.11x emitted segment work, ~6.29x gesture checks, ~6.22x lookaheads for 6x territory) while CPU grows ~8.57x on the seed-1 comparison, so MAIN needs lower-level spatial/global-round instrumentation before any routing-policy change.

The ordered plan is retained in `docs/LONG_FINE_PERFORMANCE_AUDIT.md`: LOCAL dead-family retirement first; debt-driven rescue second; measured MAIN infrastructure optimization third; constant-factor/memory/component work later. Production remained unchanged by the audit.

## 2026-08-25 — Long/fine LOCAL scaling: LOCAL-1 and LOCAL-2 promoted

- LOCAL-1 removed repeated polling of already-quarantined direct-run families by compacting only dirty region lists before their next scan. Exact governing geometry was preserved; normalized LOCAL CPU/work scaling improved materially.
- LOCAL-2 rejected two non-solutions first: debt-proportional caps did not reduce work, and a monotonic-cell frontier still reopened essentially every changed cell. The retained architecture uses one stochastic debt campaign plus deterministic exact-first-leg proof reuse.
- LOCAL-2 governing 0.75 -> 0.5 normalized LOCAL CPU/work improves ~`1.105x -> 1.042x`; long `1:6 @ 0.75` rescue waves fall `3 -> 1` and partial tokens `19,200 -> 6,400` while visible LOCAL population changes only ~2.2% and remains within the same design language.
- LOCAL-2 production SHA: `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`; active gate 154/154 + stress 1/1 PASS.
- Next: instrument MAIN per-operation amplification. No MAIN routing-policy change is justified until the lower-level source of the long/fine CPU/work tax is measured.


## 2026-08-26 — optimization stopped after final LOCAL-3 rejection

- The remaining two-level static group->primitive LOCAL broad-phase candidate was **REJECTED**: its decisive `1:6 @ 0.75 / seed 0` run failed to complete inside 300 s with no durable record, versus the recorded production control at ~116.804 s.
- No further LOCAL broad-phase variants or MAIN aspect optimization will be pursued unless optimization is explicitly reopened.
- Final denominator correction: long-board LOCAL visible traces grow 6.024x on the diagnostic proxy, while exact path-GEOS interactions grow 6.830x and static primitive interactions 7.633x; measured LOCAL CPU grows 7.856x. Much of the earlier trace-normalized 1.375x ratio therefore reflects genuinely denser interaction work.
- Known same-host full-board residuals are retained as accepted/deferred evidence: whole renderer 1.261x CPU/visible-work, MAIN 1.256x CPU/launch, LOCAL 1.375x CPU/visible-trace before interaction-denominator correction, components 1.164x CPU/component.
- Production remains SHA `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`; final canonical gate 156/156 + stress 1/1 PASS.

## 2026-09-27 residual composition preservation

Shared cluster distribution retains local spatial indexes, chunk heaps, incremental service masks and exact first-leg reuse. Fine-scale component center-core/glyph-footprint conflation caused seven populations and 28.453 component CPU s; full selected-tile containment restores one population at every qualified scale. Mixed LOCAL .75->.5 CPU/source growth 1.1105x (previous production 1.2452x); .5->.351.0840x. Absolute LOCAL CPU rises with true visible coverage and added output. MAIN paired SVG geometry is unchanged. See RESIDUAL_CLUSTER_DISTRIBUTION.md for workload counts, raw-to-durable evidence, endpoint checks and limitations. Native release 204/204 and stress 1/1 pass with exit code zero. This correction is promoted.
