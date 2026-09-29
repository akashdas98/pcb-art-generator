# Long/Fine MAIN Persistence Diagnosis — 1:6 @ 0.35

Updated: 2026-08-25 03:58 IST

## Status


## 2026-08-26 recurrence after prior closure — repaired/promoted

A later production-use run from the 05:19 renderer proved that the broader seed-totality contract was still incomplete: `1:6 @ 0.35`, count 2, no explicit seed, failed after 184.684 s with `MAIN persistence horizon unresolved`. This is a correctness bug regardless of the missing random seed.

The recurrence was outside the earlier mature-relational/hard-four-soft-six subclass. Legitimate recovery could rewind a root launch below the four-module survival floor, and finalization lacked a constructive restoration operation; exhausted unmaterialized fan/fragment/branch intent could also remain hard debt despite already-valid mature visible geometry. Production now restores source egress through the launch family's continuously reserved corridor and cancels only exhausted future intent after exact settlement opportunities are exhausted. Relational residue still uses the prior progress-driven shared-snapshot settlement.

Regression evidence: 162/162 + stress 1/1 PASS; exact seeds 0–31 at 1:1 @ 1.0 complete MAIN with zero unresolved persistence debt; historical exact seed 1 at 1:6 @ 0.35 MAIN-only completes with 4,104/4,104 launches visible and zero unresolved debt. These are regression/fuzz evidence, not an enumeration proof. Any future production construction exception remains a correctness defect. Authoritative renderer SHA: `5b5eb7cd883b1f9403e41dbb9626976626008de2f724a03f7cfad94413da0df1`.

**CLOSED / PROMOTED. The diagnosed long/fine persistence-totality fix is production V48.**

The promoted source constructs the exact former `1:6 @ 0.35 / seed 1` board without reseeding, and exact seed 0 also completes under the whole-render phase harness. The ~10.5 minute / ~785 MiB workload remains a separate long/fine performance cost; it is not a seed rejection and was not introduced by this fix.

The promoted line-survival + atomic residual-structural fix remains valid for the specific first-rebase starvation and late sequential structural-commit defects it addressed. New raw production logs prove that the broader seed-totality contract is still incomplete in the long/fine `1:6 @ 0.35` regime.

This is not an argument for aspect-specific behavior. Work heft may increase CPU/RSS, but it must not change whether a valid canvas/scale/seed can be constructed.

## User-supplied raw evidence

Raw log archive SHA-256: `89ea46434efb12a61efc60644ea44f36601d104b7cf16d994c80c787504c15ad`.

The supplied archive contains:

- initial two-sample stderr: `RuntimeError: MAIN persistence horizon unresolved` from `_run_rounds()` before sample 1 emitted;
- explicit seed `1`: the same exact exception and call path;
- explicit seed `0`: empty stderr because the run was manually terminated after prolonged runtime/high RSS; this is an operational/scaling symptom, not proof of the same exception.

The failure is inside MAIN construction. `render_batch()` does not skip/reseed; the exact requested seed propagates the construction invariant failure as intended. The bug is therefore unresolved MAIN totality, not an acceptance-layer retry bug.

## Exact seed-1 diagnostic reproduction

A diagnostics-only source copy added state dumping at the existing final `MAIN persistence horizon unresolved` assertion. Routing decisions were not changed.

Fixture:

- aspect ratio: `1:6`
- main scale: `0.35`
- base seed: `1`
- derived logical seed: `7179163421162001120`
- chips: `98`
- effective canonical territory multiplier: `48.9795918367347`
- MAIN CPU: `317.1993 s`
- MAIN wall: `317.2474 s`
- max RSS: `440,592 KiB`
- result: `FAIL — RuntimeError: MAIN persistence horizon unresolved`

Diagnostic JSON SHA-256: `5ff007a4bcaecd286f5ae7e7d852dec7a566d1f80141e2cfbe622e8d64106379`.

Only **5 fronts / 7 traces** remained unresolved at the final assertion.

### Residue A — mature lanes with legal continuation

Three singleton fronts from chip 32/right side remain classified `between_siblings`, but each still has at least one exact-clear ordinary straight/±45 continuation from the final committed board:

| front | traces | visible/materialized length | legal continuation evidence |
|---:|---:|---:|---|
| 5567 | 1 | ~20.833 modules | 1-module legal moves in dirs 2 and 3 |
| 5717 | 1 | 13.000 modules | 1-module legal move in dir 0 |
| 5872 | 1 | ~16.167 modules | 1-module legal moves in dirs 1 and 0 |

These lanes are not geometrically exhausted. The fixed persistence horizon is ending construction while valid local continuation still exists. More total board work increases the chance of encountering such a residue, but must not convert it into a seed rejection.

### Residue B — preferred-length debt incorrectly acting as hard validity debt

Two additional fronts are exactly **5.000 modules** long and have no exact-clear straight/±45 continuation in the diagnostic probe:

- front 1218: bundled 3 traces;
- front 7014: singleton 1 trace.

Both have cleared source egress, have no pending fan/fragment birth, no unfinished branch stage, and are not relationally embedded. Their only remaining reason for being protected/unresolved is the current six-module persistence requirement.

This exposes a contract mismatch in production source:

- `main_launch_maturity_modules = 4.0` is the hard survival floor;
- `main_launch_preferred_terminal_modules = 6.0` is documented in `_terminate_front()` as a **soft visual preference, not a reason to reject an otherwise valid board**;
- `_persistence_hard_debt()` currently marks every MAIN front shorter than the 6-module preferred value as hard debt;
- the final young-survival pass sets `protected_launch_unresolved=True` if the route still cannot reach 6 modules, causing the whole seed to throw even when the route is already above the 4-module hard floor.

Therefore a soft quality target is currently being promoted into a construction-validity assertion.

## Relationship to the earlier long/fine evidence

This result strongly corroborates the previously preserved V47 long/fine diagnosis. The historical `1200:6248 @ 0.35` fixture exposed 54 mature residual MAIN lanes, overwhelmingly `between_siblings`, and the recorded next discriminator was exactly whether those lanes still had legal continuation.

The new 1:6/seed-1 diagnostic completes that discriminator for a current promoted V48 repro: several mature residual lanes **do** still have legal continuation. At least part of the long/fine rejection class is therefore a premature fixed-horizon termination of valid construction work.

The promoted V48 atomic structural helper is not itself implicated by these five final residues: all five have `branch_stage=None`. The first-rebase/late-structural-commit line-murder fix remains a real fix for its traced mechanism; it simply did not totalize this separate late terminal/persistence family.

## Correct architectural direction

Do **not** add aspect-ratio exceptions, seed retries, larger global restart budgets, or a bigger fixed persistence tick constant.

The correction should separate **work scheduling** from **validity**:

1. Six-module preferred journey may continue to receive bounded/priority routing opportunities, but failure to reach 6 may not by itself invalidate a route that is already at or above the true 4-module maturity floor and has exhausted legal local continuation.
2. A mature relational-debt lane that still has a legal ordinary continuation may not be rejected merely because a fixed global persistence clock expired. Residual settlement must be progress/debt driven: continue exact local construction while legal progress exists, with atomic conflict handling, until the debt is discharged or local legal continuation is genuinely exhausted.
3. If a mature relational lane has **no** legal continuation, that is a separate deterministic local-resolution case. It must be resolved without whole-seed rejection, while preserving the proactive anti-line-murder rule; do not legalize systematic bad terminals merely because an arbitrary retry counter expired.
4. Runtime/memory must then be qualified independently. More territory may cost proportionally more work; it may not change correctness.

## Seed 0

The supplied seed-0 stderr was empty because that attempt was manually terminated. The same exact workload has now been reproduced to completion under both production and v2 with the whole-render phase harness. It is **very expensive but finite**, and it is not a v2-introduced correctness failure. Detailed side-by-side evidence is recorded in the 2026-08-25 02:00 IST update below.

## Next implementation gate

Build the smallest unpromoted candidate that:

- distinguishes hard 4-module launch-survival debt from the soft 6-module preferred journey;
- replaces fixed-horizon rejection of mature legally-continuable relational residue with monotonic/progress-driven local settlement using the existing exact gesture/conflict rules;
- adds targeted regressions for both seed-1 residue types;
- first qualifies ordinary 0.75 and 0.5 behavior/scaling, then re-runs the explicit `1:6 @ 0.35` bug fixture because the defect itself lives there;
- promotes only after the complete release/stress gate and exact requested-seed full-board emission succeed.

## 2026-08-24 23:36 IST recovery note

A subsequent continuation began an unpromoted totality candidate based on this diagnosis. The runtime container reset during the first expensive `1:6 @ 0.35 / seed 1` qualification, destroying the scratch candidate and scratch benchmark files before they were packaged. Production V48 therefore remains unchanged and authoritative in this repository.

The following evidence from that interrupted continuation is preserved here so it is not lost:

- Candidate architecture (UNPROMOTED): split late persistence into **soft work debt** vs **hard validity debt**. The soft work scheduler continues to prefer six visible modules; hard validity uses the true four-module launch-survival floor plus source/fan/fragment/branch/relational obligations.
- Candidate architecture (UNPROMOTED): add progress-driven residual relational settlement for mature singleton sibling-embedding debt. It proposes from one shared snapshot, commits a deterministic conflict-clean subset atomically with HOLD/fairness, and repeats while real movement is committed. There is no correctness-affecting tick/retry cap. Zero legal proposals is recorded as geometric exhaustion for final cohort arbitration.
- Targeted scratch tests passed before the reset:
  - a five-module mature main lane was soft work debt but **not** hard validity debt;
  - a synthetic relational residue requiring five successive legal moves completed all five rather than stopping at a fixed horizon;
  - a mature relational residue with zero legal proposals was classified as geometric exhaustion, not `protected_launch_unresolved`.
- Ordinary MAIN-only screening completed before the reset. Governing seeds 102+104, 1:1:
  - production aggregate 0.75: CPU `10.2545 s`, visible work `4339.302`, gesture checks `42,842`, lookaheads `34,873`, local-space evals `14,805`;
  - candidate aggregate 0.75: CPU `11.1645 s`, visible work `4340.349`, gesture checks `43,396`, lookaheads `35,394`, local-space evals `14,814`;
  - production aggregate 0.5: CPU `38.5336 s`, visible work `10580.413`, gesture checks `149,075`, lookaheads `121,531`, local-space evals `52,623`;
  - candidate aggregate 0.5: CPU `40.7978 s`, visible work `10699.591`, gesture checks `151,853`, lookaheads `122,958`, local-space evals `52,772`.
- From those same scratch records, normalized 0.75 -> 0.5 CPU/work growth was approximately **1.541x production vs 1.482x candidate**. Deterministic normalized growth also improved slightly for gesture checks (`1.427x -> 1.419x`), lookaheads (`1.429x -> 1.409x`), and local-space evaluations (`1.458x -> 1.445x`). These are screening results only because the scratch files were lost in the reset; they must be regenerated before promotion.
- Behavior remained clean on those ordinary fixtures: zero unaccounted launches, zero short-main invariant failures, zero stalled sides, zero octilinear/turn/clearance violations. Seed 104 @ 0.75 remained geometry-identical to production; other candidate fixtures changed only late geometry and therefore require normal behavior qualification.

**Recovery rule:** reconstruct this candidate only after a fresh verified handoff has been created from the surviving production authority. Then regenerate the ordinary 0.75 and 0.5 screening evidence before re-running the expensive `1:6 @ 0.35 / seed 1` repro. Do not infer a pass/fail from the interrupted long/fine attempt; it produced no renderer result.

## 2026-08-25 00:39 IST — corrected v2 placement evidence recovered from interrupted continuation

A second reconstruction attempt after the 23:37 recovery checkpoint identified and rejected one placement error, then produced a narrower **v2** design before another runtime reset removed the scratch tree. Production remained unchanged throughout.

### Rejected v1 placement

The first reconstruction placed progress-driven relational settlement **too early**, before the renderer's existing final escape / survival / stalled-family cleanup. Instrumentation on `1:6 @ 0.35 / seed 1` showed that this point still contains **hundreds of temporarily `between_siblings` fronts**. The helper therefore attempted to totalize a large transient population rather than the true final persistence residue. That placement is rejected.

### Corrected v2 placement

The progress-driven relational settlement belongs only at the **true final residue point**, after all existing bounded final cleanup and immediately before final coordinated terminal/rejection handling. It therefore acts only on genuinely unresolved mature relational residue. The soft-six / hard-four debt split remains unchanged:

- six visible modules remains a preferred routing/work target;
- four visible modules is the hard launch-survival validity floor;
- a route at or above four modules may not reject the seed solely for failing to reach six after genuine local exhaustion.

### Surviving v2 screening evidence

The scratch files were lost, so these numbers are evidence to regenerate, not promotion authority. They were observed before the reset:

- targeted soft-vs-hard debt regression: PASS;
- targeted progress-driven settlement beyond a fixed tick horizon: PASS;
- targeted zero-proposal geometric-exhaustion classification: PASS;
- 1:1 @ 0.75 / seed 102: PASS and **geometry-identical to production**; only three additional gesture-clear checks were observed;
- 1:1 @ 0.75 / seed 104: PASS, **geometry-identical to production**, and deterministic work was identical on the measured counters;
- 1:1 @ 0.5 / seed 102: PASS with zero unaccounted launches, zero short-MAIN invariant failures, zero stalled sides, and clean geometry counters. Production measured `71,706` gesture-clear checks / `57,466` lookaheads; v2 measured `71,988` / `57,544`. One raw CPU pair was roughly `22.7 s -> 24.0 s`, but host-frequency noise makes that pair non-decisive.
- 1:1 @ 0.5 / seed 104 was **not completed** before the execution boundary.
- corrected-v2 `1:6 @ 0.35 / seed 1` was **not run to completion**, so the historical failure is still OPEN.

### Recovery / next gate

There is no surviving v2 source after the reset. Reconstruct v2 only from this recorded architecture, then regenerate the targeted tests and ordinary 0.75 -> 0.5 qualification. Only after those agree may the explicit `1:6 @ 0.35 / seed 1` no-reseed repro be run. Do not infer correctness from the interrupted attempt.


## 2026-08-25 01:23 IST — v2 survives and exact seed-1 full board emits

The corrected v2 source now survives in `archive/inflight/v48_longfine_totality_v2_renderer.py` (SHA-256 `e8d1874d652e7aa6a7af763ac20b2a97d1367082dc748f61771833be49d16054`). Production remains unchanged and authoritative.

Regenerated ordinary screening is retained under `archive/inflight/evidence/`: governing 1:1 seeds 102/104 pass at 0.75 and 0.5 with hard MAIN invariants clean. The decisive explicit long/fine repro also now passes at two levels:

1. **MAIN-only, exact `1:6 @ 0.35`, base seed 1:** PASS in `320.487 s` MAIN CPU (`323.074 s` total harness CPU), peak RSS `509,292 KiB`; logical seed `7179163421162001120`; all `4,104 / 4,104` launch traces visible; zero short-MAIN, stalled-side, unaccounted-launch, illegal-turn, non-octilinear, clearance, or intersection failures.
2. **Full board, same requested base seed 1:** PASS. A `10,476,942`-byte SVG and report were emitted with `restart_index=0`, `skipped_logical_indices=[]`, 98 chips, 824 collections, `component_unplaced_count=0`, `route_restarted_for_component_failure=false`, zero hard MAIN/geometry failures, and all `4,104 / 4,104` launch traces visible. The emitted SVG SHA-256 was `b1922ef443581627cb87a1695893cd1baa4a789a230669ea07ab7a7d47297e28`. The retained full report is `archive/inflight/evidence/longfine_seed1_full_report.json`.

The full report still records four `pathway_main_free_terminal_under_preferred_visible_trace_count` traces. Under v2 this is deliberately **not a hard validity failure**: those routes cleared the four-module survival floor but did not satisfy the soft six-module preference. This is direct evidence that the soft-vs-hard debt split is operating as intended rather than silently deleting the quality diagnostic.

### Status after seed-1 emission

The original explicit seed-1 persistence rejection is fixed **in v2**, with no reseeding or whole-sample skip. This does not yet justify promotion. The supplied seed-0 run had no exception but was manually terminated after >9 minutes / ~745 MB RSS, so seed 0 remains a separate performance/RSS investigation. Correctness and cost must remain separate: more territory may increase work but may not make validity probabilistic.

Next: reproduce exact seed 0 on v2 with phase/work/RSS instrumentation, identify whether its cost is ordinary proportional long/fine work or a pathological amplification, then complete the full active release/stress and promotion qualification only if scaling remains acceptable.

## 2026-08-25 02:00 IST — seed-0 phase comparison completed

Exact fixture: `1:6 @ 0.35`, base seed `0`, sample index `0`, one ordinary `generate_sample` call. The harness does not seed-shop or loop over whole-board restarts; both sources completed successfully.

Retained evidence:

- `archive/inflight/evidence/longfine_seed0_production_phase.json` — SHA-256 `302a51a571c6484bda79bf94efa1fddf8cdfe6f3e9f079306547c09e1835bce0`;
- `archive/inflight/evidence/longfine_seed0_v2_phase.json` — SHA-256 `82bdc3c12da5caff338aafdf1cd89d70805ab9c348e8182b9ecd2d1829b189f4`;
- matching `/usr/bin/time -v` records are retained beside them.

| Metric | Production V48 | v2 candidate | v2 vs prod |
|---|---:|---:|---:|
| status | PASS | PASS | — |
| total CPU | 630.862 s | **614.485 s** | **-2.60%** |
| total wall | 630.978 s | **614.630 s** | **-2.59%** |
| peak RSS | 805,176 KiB | **804,192 KiB** | **-0.12%** |
| MAIN CPU | 352.985 s | **338.407 s** | **-4.13%** |
| LOCAL-gap CPU | 220.395 s | **215.606 s** | **-2.17%** |
| component-place CPU | 47.794 s | **38.871 s** | **-18.67%** |
| MAIN launch traces | 4,124 | 4,124 | identical count |
| visible MAIN launches | 4,124 | 4,124 | identical count |
| gesture-clear checks | 971,076 | 981,312 | +1.05% |
| lookahead evaluations | 799,087 | 801,235 | +0.27% |

The two geometry hashes differ, as expected for a candidate that changes final persistence settlement, so phase-level clock differences are not interpreted as a pure microbenchmark. The important qualification conclusion is narrower and robust: **v2 does not create the observed high-runtime/high-RSS regime. Production itself takes ~10.5 minutes and ~786 MiB peak RSS on the same exact seed, while v2 is slightly faster with effectively identical peak RSS.**

Therefore seed 0 is no longer classified as an unresolved runaway/rejection. It is a confirmed **long/fine performance cost** shared by production and v2. That cost remains a legitimate future optimization target, but it is separate from the persistence-totality correctness fix.

Production remains unchanged. v2 remains **UNPROMOTED** pending the full active release gate, maintained stress gate, and final required promotion/scaling qualification.

## 2026-08-25 03:12 IST — recovery of lost promotion-qualification evidence

A later continuation completed additional **UNPROMOTED** v2 qualification, but the runtime reset before those scratch test edits/profiler outputs could be packaged. The surviving v2 source remains the candidate at SHA-256 `e8d1874d652e7aa6a7af763ac20b2a97d1367082dc748f61771833be49d16054`; production remains unchanged at `ac53e1d1fae493beb55ab8dc05c0ba7d3053add19a1c6b71cb52ce926738fb79`.

Preserved evidence from that continuation:

- repeated fresh-process 1:1 0.75 -> 0.5 qualification resolved the earlier noisy clock disagreement in v2's favor;
- normalized MAIN CPU/useful-visible-work growth (median of two fresh runs per seed) was approximately **1.592x production vs 1.409x v2**;
- deterministic normalized work was essentially unchanged: gesture `1.4271x -> 1.4277x`, lookahead `1.4293x -> 1.4257x`, local-space `1.4578x -> 1.4536x`;
- authoritative visible terminated-route behavior (<=8 / <=14 modules) remained equal or better: 0.75/102 `3/11 -> 3/11`, 0.75/104 `2/7 -> 2/7`, 0.5/102 `18/58 -> 16/57`, 0.5/104 `18/64 -> 18/61`;
- a candidate release run initially found one expected obsolete contract test: `test_v47_under_six_module_main_route_is_hard_persistence_debt`; that test encoded the diagnosed bug by treating the 6-module preference as hard validity debt;
- in scratch, that obsolete test was replaced by the correct stronger contract (5 modules remains preferred/work debt but is not hard validity debt), and focused regressions were added for progress-driven final relational settlement and genuine geometric exhaustion;
- the resulting **candidate scratch gate passed 151/151**, and maintained candidate stress passed **1/1**;
- the mandatory end-of-phase 0.35 gate then found the remaining promotion blocker: aggregate 1:1 0.5 -> 0.35 normalized MAIN CPU/work growth was approximately **1.055x production vs 1.366x v2**;
- ordinary routing-work counters did not explain that fine-scale CPU delta: normalized gesture/lookahead/local-space work was essentially unchanged or slightly improved, implicating overhead in the new final-residue persistence machinery rather than ordinary route generation;
- classification at the reset boundary was therefore **MODIFY / DO NOT PROMOTE**. Correctness, behavior, release tests, stress, and 0.75 -> 0.5 scaling passed, but 0.35 scaling did not.

Important recovery limitation: the 151-test scratch edits and the attempted helper-profiler output did not survive the runtime reset. They must be reconstructed from the preserved contract before any promotion. Do not record 151 tests as canonical active authority until those edits are recreated and rerun.

### Exact next question

Profile `_settle_final_relational_persistence_progress()` at 0.35 and determine which of its operations grows disproportionately (residual population scans, proposal construction/materialization, conflict arbitration, or repeated cohort rebuilding). Optimize only that proven overhead while preserving:

1. the hard-4 / soft-6 validity split;
2. progress-driven rather than fixed-clock final relational settlement;
3. shared-snapshot/conflict-clean commits;
4. exact-seed totality with no reseeding or aspect-ratio special case.

Then repeat the mandated qualification cadence: ordinary 0.75, ordinary 0.5, end-of-phase 0.35; only after the 0.35 CPU/work curve is acceptable may the reconstructed 151-test + stress gate earn promotion.

## 2026-08-25 03:58 IST — promotion closeout and scaling correction

The surviving v2 source was promoted byte-for-byte into production at SHA-256 `e8d1874d652e7aa6a7af763ac20b2a97d1367082dc748f61771833be49d16054`. The reconstructed production contract passes **151/151** active tests and maintained stress **1/1**.

The prior scratch conclusion that v2 failed 0.5 -> 0.35 scaling (`~1.366x`) is superseded. Direct helper instrumentation at 0.5/102 showed only ~`0.116 s` CPU inside the entire final-relational helper, already inconsistent with the claimed tens-of-seconds penalty. Fresh same-host uninstrumented remeasurement then produced:

| State | 0.5 visible work | 0.35 visible work | Work growth | 0.5 MAIN CPU | 0.35 MAIN CPU | CPU growth | CPU/work growth |
|---|---:|---:|---:|---:|---:|---:|---:|
| BEFORE production | `7,935.310` modules | `16,553.963` | `2.086x` | `39.026 s` | `80.938 s` | `2.074x` | **`0.994x`** |
| AFTER promoted | `7,975.116` modules | `16,599.416` | `2.081x` | `40.881 s` | `84.143 s` | `2.058x` | **`0.989x`** |

The candidate therefore does **not** worsen the normalized fine-scale curve; it is marginally better in this paired recheck. Deterministic normalized gesture/lookahead/local-space growth remains essentially unchanged between BEFORE and AFTER. The earlier blocker was host-frequency/timing contamination.

Authoritative behavior qualification also remained equal or better: 0.75/102 `3/11 -> 3/11`, 0.75/104 `2/7 -> 2/7`, 0.5/102 `18/58 -> 16/57`, 0.5/104 `18/64 -> 18/61` for visible terminated routes <=8/<=14 modules.

There is no active long/fine renderer candidate after promotion. Future work on the expensive ~10-minute 1:6 regime is a performance optimization problem, not unresolved seed-totality correctness.

## 2026-08-25 04:13 IST — post-promotion 0341 raw-log classification

A subsequent external attempt to render two `1:6 @ 0.35` samples from the promoted 0341 bundle produced zero SVGs before termination. The supplied raw logs contain **no Python exception and no stderr output** for count-2, explicit seed 0, explicit seed 1, or the earlier foreground seed-1 attempt. This is therefore not a reproduction of `MAIN persistence horizon unresolved`.

The CLI provides no partial sample artifact: `render_batch()` writes an SVG/report only after `generate_sample()` has completed that entire logical sample, and the final JSON summary is printed only after the complete requested batch returns. Since the same promoted source is already proven finite on exact long/fine seeds and seed 0 alone requires roughly ten minutes in the measured environment, an external execution cutoff can legitimately leave empty logs and no SVG despite correct construction. Treat this as **performance/observability**, not validity.

## 2026-08-26 correction — separate 0341 post-route validity failure

A later user-supplied raw-error archive adds evidence that was absent from the previously reviewed 0341 log set. `renderer_error.log` from the same `pcb-art-generator_V48_CLEAN_2026-08-25_0341IST` source records a real completed failure after `435.3526184 s`:

`RuntimeError: post-route validation failed: pair_chip_isolated`

This supersedes any broad wording in this document that could be read as saying the 0341 long/fine renderer was *uniformly* valid and only slow. The earlier empty-stderr logs remain evidence about those particular externally killed runs; seed-0/seed-1 successful reproductions remain evidence that the regime was not universally impossible. The correct historical conclusion is **seed/path-dependent validity plus severe performance cost**.

The error artifact does not preserve the command line or seed, so the exact `pair_chip_isolated` fixture cannot be replayed from it alone. Do not claim exact closure of this specific historical failure without recovering that invocation.

## 2026-08-26 — superseding closure of `pair_chip_isolated`

The earlier note that the missing historical seed prevented claiming closure was too restrictive. Seed totality means the seed value is irrelevant to whether the failure is a renderer defect; one valid input seed producing an invalid board is enough.

The specific construction/validation mismatch has now been reproduced deterministically and fixed. `pair_chip_isolated` is chip↔isolated-capacitor clearance. The old component admission gate intersected against a nominal-radius `quad_segs=8` round buffer, whose chord approximation under-covers the true Euclidean offset between arc vertices. Final validation used exact primitive distance. This created a thin false-safe annulus.

Production now uses conservative inflated finite buffers for fast admission/residual certificates plus an exact component-phase chip-clearance audit. Regression geometry explicitly demonstrates: old nominal buffer misses the candidate; exact final predicate reports the violation; new conservative keepout rejects it during construction. The causal failure class is therefore closed without needing to recover the historical random seed.

Canonical validation: **158/158 release + 1/1 stress PASS**. Production SHA: `d7ac1d9af0286dda86d994a638504fe8ab63521847d9050633fc4d49d0f21745`.
