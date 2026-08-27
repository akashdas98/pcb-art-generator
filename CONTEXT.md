## 2026-08-27 21:28 IST — residual-fill spatial mosaic + opportunistic cross-chip semantics promoted

- Closed three user production failures at `1:1 @ 0.35`, chip density `0.25`, run multipliers `0.25/0.5/1.0`. All were the same obsolete validator contract: `cross-chip connection invariant not realized`. Production now requires no board-level cross-chip quota; an already-legal foreign-chip encounter still wins immediately regardless of remaining journey target.
- Replaced residual territorial segregation with a shared composition mosaic. Components remain physically admitted before LOCAL for collision ownership, but both languages are distributed across the same board-scale residual field.
- Component and LOCAL ordinary cluster cardinality now has full seeded `1..12` support. Completion components form bounded seeded clusters rather than hundreds of nominal singleton spill clusters. A fixed 8x8 normalized-load mosaic disperses component-cluster anchors so individually bounded clusters cannot visually re-coalesce into a macroscopic colony.
- LOCAL large connected rooms are serviced as compact `1..12` source parcels. Component constructors, exact clearance, component 50--60% fill target, LOCAL 80--90% remaining-service target, LOCAL route grammar/recovery, and MAIN architecture remain unchanged.
- Exact sparse/fine production screens at density `0.25`, `1:1 @ 0.35`, run multipliers `0.25/0.5/1.0` all PASS with zero stalled sides, MAIN short terminations, or unaccounted launches; zero cross-chip joins is correctly accepted on the two shorter-run boards. Sparse `1:6` and `6:1 @ 0.75` screens also PASS with zero hard MAIN defects and component clusters reaching the intended 12-member upper bound.
- Final seeds-102+104 `0.75 -> 0.5` normalized screen: residual composite CPU/work **1.000x**, whole-renderer composite CPU/work **1.003x**; previous authority whole-renderer composite was **1.140x**. The visual correction does not introduce worse normalized scaling.
- Final qualification: **188/188 release tests PASS + stress 1/1 PASS**. Promoted renderer SHA-256: `b965a294b339684ccea1e95aae848c79d9cb232295a5666effd83dc844a7ca53`.

## 2026-08-27 18:03 IST — MAIN run-length control + inter-chip hit success promoted

Item 4 is complete as a workload/geometry parameterization over the existing MAIN architecture. `--main-run-length-multiplier` is bounded **0.2..3.0**, default **1.0**. The existing stochastic whole-route residency pool is scaled as one unit: `0.5` reproduces historical journey targets, default `1.0` is 2x historical, and `3.0` requests 6x historical. Per-gesture module lengths, turn grammar, clearance, proposal breadth, spatial indexing/search, reroute architecture, and LOCAL route life are unchanged. High settings only extend the existing shared route clock when the requested per-front residency would otherwise be impossible to realize.

Inter-chip connection semantics are part of this same item: a geometrically legal foreign-main-chip head connection is immediate successful completion regardless of remaining free-run target. Journey-limit completion is therefore deferred until the existing connection sweep has first refusal. Cross-chip eligibility/priority bypasses only the old probability gate after geometry/family legality is proven; there is no new global connection pass, broader radius, or relaxed clearance.

Final qualification on renderer `5d8624de9d2b5ec5b5ba7dac7fed169653074d7301751f8b1b1558e870dba98b`: **183/183 active release tests PASS**, maintained stress **1/1 PASS**, production smokes at run multipliers 0.2/1.0/3.0 clean, and a two-chip default production sample yields 7 cross-chip joins with zero hard defects. Governing 0.75->0.5 normalized composite CPU/work is **1.014x** at default and **1.046x** at the supported maximum; the preceding density authority measured 0.959x on the same isolated fixture. The favorable old sublinear point is retained rather than hidden, while static/source qualification confirms no routing/search algorithm was broadened. Evidence: `work/inflight/evidence/20260827_main_run_length_knob/qualification_summary.md`.

**Authoritative renderer SHA-256:** `5d8624de9d2b5ec5b5ba7dac7fed169653074d7301751f8b1b1558e870dba98b`. There is no active renderer candidate. The two planned post-optimization behavior knobs are now complete.

## 2026-08-27 16:44 IST — main-chip density control promoted

Main-chip source density is now a bounded workload knob: `--main-chip-density-multiplier 0.2..2.0`, default `1.0`. The new default is approximately half historical density; `2.0` restores the historical source opportunity law. The implementation changes only chip opportunity activation, uses a private deterministic substream, and retains a one-chip physical floor. MAIN routing architecture is unchanged. Final qualification: **180/180 + stress 1/1**; exact checked multiplier-2.0 compatibility produces bit-identical MAIN geometry/work. Authority: `586d8b54c8044129bea97088c542654b85a79465b37f1ff5ba8efbef96591c98`. Next active item is whole-route MAIN run length + inter-chip hit success semantics.

# Current Repository Context

Updated: 2026-08-27 14:44 IST — MAIN topology-birth / rollback-floor persistence-totality repair PROMOTED; 178/178 + stress 1/1 + exact failing seeds 3/3 clean.


## 2026-08-27 14:44 IST — MAIN topology-birth / rollback-floor persistence totality — PROMOTED

Three of five user production renders from the 12:33 authority threw `MAIN persistence horizon unresolved`. The line appearance/emerge→spread work remained visually successful; this was a separate correctness defect in young MAIN topology lifetime. Exact diagnostics showed under-four-module survival debt could be exported into fragmented siblings, young branch children could be born without atomically securing their complete survival maneuver, and—critically—a correctly born fan child could later be traced back through its own survival certificate because its rollback floor still pointed to zero.

Production now forbids recovery fragmentation while the family still carries unresolved <4-module survival debt; young branches/fans below the ordinary survival floor transactionally prove and commit their structural maneuver before topology replacement; and that maneuver becomes the child topology's recovery floor. Recovery may reroute later geometry, but cannot erase the certificate that makes the child topology valid. The ordinary line minimum remains **4 modules** and is not a straight-run rule; the separate >=8-module side-progress requirement is unchanged.

Final qualification on renderer `9541c2f62cf9afccf3388eac6b929d7dd9437c19d04acb600855e61175bd1b42`: **178/178 active release tests PASS**, maintained geometry stress **1/1 PASS**, and all three exact user-failing sample seeds PASS at the explicitly inferred `1:6 @ 0.35` MAIN-only reproduction. Seed `1638463186752876422` emits 4,109/4,109 launches visible; `13995978127231202083` emits 4,091/4,091; `3524258640260304746` emits 4,084/4,084. Every replay reports zero unresolved persistence, stalled sides, MAIN short terminations, and unaccounted launches. The raw user ZIPs did not contain invocation arguments, so only the sample seeds/failure diagnostics are exact; aspect/scale are deliberately labeled inferred. There is no active renderer candidate.

## 2026-08-27 12:33 IST — MAIN emerge→spread, connection eligibility, and live side-progress refinement — PROMOTED

A new user production error from the prior 10:55 build reopened correctness: MAIN preflight reported one stalled side at root `[88,3,"left"]` / front `355` / traces `3717..3725`, despite `4107/4107` launches visible and otherwise clean geometry. In parallel, visual review showed that root buses were behaving as if deliberately told to bend as one object, rarely spreading into independently routed cohorts, obvious head-to-head opportunities could remain separate terminal dots, and avoidable sibling traps still occurred.

The audit found concrete policy/representation causes, not merely unlucky randomness. Root fan readiness was still delayed behind the old four-module egress gate after the four-module *straight* lock had been removed, so a complete 9–24 lane bus could turn before it was allowed to split. Ordinary MAIN scoring also retained a synthetic turn reward after two straight gestures. Fan topology tried one fixed preferred outward/straight permutation first; turning alternatives were consulted mainly on failure, and the fan transaction used coarse cohort envelopes that falsely rejected physically clean 45-degree peels. Launch partitioning could produce only two giant cohorts. Same-chip fronts from distinct launch sides were excluded from several head-connection passes. Finally, side-level >=8-module progression was still too late/special-case rather than live construction debt.

Production now makes the first perpendicular emergence gesture the point at which the root fan may be solved transactionally. The child fan maneuver itself proves the unchanged ordinary **four-module per-line survival floor**. Launches are partitioned into several balanced contiguous cohorts; legal fan alternatives are seeded and open-space scored, with lane-level physical legality rather than coarse-envelope rejection. Ordinary MAIN no longer receives a synthetic "time to bend" reward; turns still arise from seeded variation, open-space capacity, target/connection geometry, and actual obstacles. The last live outcome of an unsatisfied side carries live >=8-module side-progress debt. Distinct launch sides of one chip are connection-compatible after source egress; same-side siblings remain one family and cannot silently merge.

Maintained stress then exposed one additional stale exemption on base seed `2026080602` / sample seed `1909786089031391816`: a fan child blocked during its first rebase could later take its first turn across a sibling's committed corridor while inheriting an exemption intended only for parallel straight fan rebasing. `_gesture_clear()` now grants that sibling exemption only when the **candidate itself remains straight**. The permanent regression uses a sibling corridor long enough to physically intersect the diagonal candidate; the illegal turn is rejected.

Final qualification on the promoted source: **175/175 active release tests PASS**, maintained geometry stress **1/1 PASS**, and three fresh plain-production `1:1 @ 1.0` renders from base seed `20260827` all emitted with 82/82, 84/84, and 84/84 launch traces visible, zero stalled sides, zero MAIN short terminations, and zero unaccounted launches. Those samples accumulated 44, 37, and 31 viable fan alternatives and 8, 11, and 10 MAIN connections respectively. Visual inspection confirms multi-cohort emergence and divergent continuation rather than one mandatory whole-bus bend. A small same-request runtime screen showed `20.54 s` on the previous 10:55 renderer vs `20.23 s` on the promoted renderer for three square samples; this is only a no-obvious-regression screen, not a broad optimization claim.

**Authoritative renderer SHA-256:** `4c87378867645aa90727b77ea94e98eb59c6a6f4f993a45cbbf786b5239afc8e`. There is no active renderer candidate. The raw user error, source delta, complete release/stress logs, and fresh sample SVGs are retained under `work/inflight/evidence/20260827_emerge_spread_qualification/`. Any future valid-seed construction exception reopens correctness immediately under seed totality.


## 2026-08-27 10:54 IST — wide MAIN fragment side-progress totality repair — PROMOTED

The exact `1:6 @ 0.35` production board that previously failed is now clean from a completely fresh reconstruction: base seed `8528317405406420078` deterministically produced sample seed `9409060408987575905`, completed in `934.710 s`, and emitted the full SVG/report with no whole-board restart or alternate seed. Final hard metrics include `pathway_main_stalled_side_count=0`, `pathway_main_unaccounted_launch_trace_count=0`, `pathway_main_short_termination_trace_count=0`, `pathway_persistence_horizon_unresolved_trace_count=0`, zero illegal MAIN turns/intersections/overlaps/clearance violations, and all `4,131/4,131` launch traces visible.

Causal diagnosis: the two stalled sides were 13-lane MAIN buses fragmented at the hard persistence horizon. Recovery fragmentation already proved a bounded short future for cohorts of four lanes or fewer, but wide cohorts bypassed that proof. The resulting singleton siblings could consume one another's escape room and terminate as a family near the ordinary four-module maturity floor before any lane established the separate eight-module side-progress requirement. The downstream prefix-regrow repair was operating on child ownership while the shared visible prefix remained ancestor-owned, so it could not reliably reconstruct this case after the damage.

Production now closes that birth-time hole proactively. Before a wide MAIN recovery fragmentation (`>4` lanes) below eight visible modules mutates topology, the planner must prove and commit one bounded ordinary-clearance future for one physical child lane. That trace carries a trace-id side-progress certificate through later rebases/branches, and render-time source/terminal clipping may not amputate the certified lane below eight visible modules. This is bounded `O(lanes)` local work with fixed beam/horizon; it is not a board search, seed retry, or relaxed validator. The ordinary hard MAIN maturity floor remains **four modules** and early legal turning remains allowed.

Qualification after reconstructing the two lost regressions as new reviewable tests: **168/168 active release tests PASS + stress 1/1 PASS**. The exact formerly failing frozen-state replay also showed the two repaired leaders at `8.154822` and `8.000000` visible modules with zero hard geometry defects before the full from-scratch replay was run.

**Authoritative renderer SHA-256:** `03e25cbf3ac46f86dced3822cbfa29e526b576499adacb0cf30684e329cf297d`. There is no active renderer candidate. Correctness is CLOSED for this reproduced defect; any future valid-seed construction exception reopens it immediately under seed totality. Long/fine runtime remains a separate optimization target: this exact full-board pass required ~15m35s.

## 2026-08-26 22:45 IST — exact-board preflight snapshot attempt interrupted; no new code change

Current unpromoted candidate remains renderer SHA `c80480724343f4a09286d2fde861ce60b6f8c73a77a59e49aba32f01e1e34d75`; packaged production authority remains the 16:31 renderer until a candidate actually passes the exact production board and is promoted. Correctness remains OPEN.

The exact logged board (`sample_seed=9409060408987575905`, base seed `8528317405406420078`, `1:6 @ 0.35`, MAIN-only) completed on the current prefix-aware candidate and still failed preflight with `pathway_main_stalled_side_count=2`. The source-egress exception no longer recurred; the remaining issue is stalled-side materialization/repair identity for roots `[74,1,"left"]` and `[81,2,"bottom"]`. Candidate gate before this exact-board failure was 166/166 + stress 1/1, but that finite gate does not override the production-seed failure.

To stop paying the full ~10-minute route cost on every preflight experiment, the next diagnostic strategy was validated on a small fixture: a fully routed `BundleGesturePlanner` can be pickled/restored with fronts, path records, spatial indexes, and materialization state intact. One exact-board route-to-preflight snapshot build was then started, but the process did not survive the runtime boundary and emitted no durable snapshot. This is an interrupted diagnostic attempt, not a renderer failure and not a completed artifact.

**Next action:** build the exact failing board once to immediately before preflight, persist the planner snapshot successfully, then iterate only on the two stalled-side repair/identity paths from that frozen state. Do not add another recovery heuristic before inspecting the exact owners selected by `_repair_main_stalled_side_progress()`. No reseeding, validator weakening, or whole-board acceptance loop.

## 2026-08-26 18:40 IST — source-egress + stalled-side correctness recurrence — OPEN

The 16:31 early-turn renderer failed in production at `1:6 @ 0.35` with `final source-egress reserved corridor blocked (sample_seed=9409060408987575905, front=21)`. This is a seed-totality bug, not a bad seed. Early turning exposed a stale assumption in final source-egress restoration: the fallback corridor remained a straight ray even after a root had legally satisfied its four-module cumulative survival floor through a bend. The interrupted fix changed the intended certificate to the actual bent four-module survival prefix, while retaining the original straight reservation only for a root that never matured.

The exact failing seed then advanced further and exposed a second bug: `main-network preflight materialization invariant violated` with `pathway_main_stalled_side_count=2`. The current stalled-side repair only tries to extend from an already-dead head. The next repair must transactionally rollback one candidate trace to a viable checkpoint and regrow it legally to the existing 8-module visible-side progression requirement. No seed shopping, no validator weakening, no whole-board retry.

This recovery checkout is based on the last authoritative packaged 16:31 renderer because the interrupted candidate source did not survive the runtime reset. Evidence is retained under `work/inflight/evidence/`.

## 2026-08-26 16:30 IST — early MAIN turning under the hard four-module floor — PROMOTED

The four-module MAIN launch contract remains a hard cumulative visible-survival requirement. The previous implementation incorrectly encoded that contract as a four-module **straight-run lock**: root launches carried `forced_straight_modules=4`, `_direction_candidates()` forced `initial_dir` throughout source-egress debt, and `_module_counts()` attempted to consume the remaining survival distance as one straight gesture.

Production now separates these concepts. Gesture zero still emerges perpendicular to the chip through the ordinary grammar. After that first gesture, a root may use the existing legal straight / +/-45-degree direction grammar even while cumulative materialized lane length is still below four modules. No new first-turn preference, scoring heuristic, local-space planner, or termination policy is introduced here.

The hard rules are unchanged: structural splitting/fragmentation remains blocked while source egress is pending; the source-egress reservation remains active; `<4 modules` remains physically protected hard persistence debt; deep traceback reactivates the reservation; final source-egress totality can still reconstruct a rewound launch through its reserved corridor. The change only removes the false equivalence `survive >=4 modules == remain collinear for first 4 modules`.

Focused regressions plus the canonical DEVELOPMENT gate pass **162/162 + stress 1/1**. Authoritative renderer SHA-256: `f3b3179921db023fa8160885275244779190836015fdd4676e9cafe690bd7f90`. There is no active renderer candidate.


## 2026-08-26 15:34 IST — MAIN persistence-totality recurrence repair — PROMOTED

A user production invocation from the 05:19 renderer (`1:6 @ 0.35`, count 2, no explicit seed) failed after 184.684 s with `RuntimeError: MAIN persistence horizon unresolved`. The missing random seed never weakened the correctness claim: every valid renderer-generated or explicit seed is owned by construction, and any production construction `RuntimeError` is a seed-totality bug.

The previous long/fine persistence closure covered mature relational residue and the hard-four/soft-six distinction but left two broader final hard-debt classes only partially constructive: (1) legitimate deep MAIN traceback can rewind a root launch below the true four-module source-egress floor, and (2) exhausted *unmaterialized* fan/fragment/branch scheduler intentions could remain classified as hard validity debt after the visible route was already mature.

Production now performs constructive true-final settlement before the final persistence assertion: a root below the four-module floor is rebuilt deterministically through its continuously reserved source-egress corridor; exhausted unmaterialized structural intent is cancelled without deleting or bending any visible geometry; mature relational debt continues through the existing progress-driven shared-snapshot settlement. No seed retry, whole-board restart, collision relaxation, or safe-seed substitution is introduced. The assertion remains as an unreachable regression guard and now reports the sample seed and debt classes if it ever fires.

Qualification evidence is deliberately finite regression evidence, not a proof by enumeration: **162/162 active tests PASS + stress 1/1 PASS**, exact MAIN seeds 0–31 at 1:1 @ 1.0 completed with zero unresolved persistence debt, and the historically important exact **seed 1 at 1:6 @ 0.35 MAIN-only** completed in 385.94 CPU-s with **4,104/4,104 launches visible and zero unresolved/source-egress/structural debt**. Any future valid-seed construction exception reopens correctness immediately.

Authoritative renderer SHA-256: `5b5eb7cd883b1f9403e41dbb9626976626008de2f724a03f7cfad94413da0df1`. There is no active renderer candidate.

## Production-use vs development-mode contract — 2026-08-26

A plain request to **use/render/generate** with V48 is now explicitly **PRODUCTION USE mode**, not repository work. The canonical command is `python generate_pcb.py ...`. In that mode an agent must render exactly what was requested and stop: no worktree/canonical-repository guard, no release/stress tests, no seed sweep/qualification, no performance harness, no handoff builder, and no standalone report JSON unless explicitly requested. If the seed is omitted, it stays omitted; `V48Renderer` chooses its random base seed itself. Maintained/reference/known-good/"safe" seed substitution is forbidden.

`AGENTS.md` routes this mode **before** DEVELOPMENT instructions, and `docs/PRODUCTION_USE.md` is the concise use contract. `docs/WORKFLOW.md`, repository safety gates, tests, stress, qualification, and handoff rules apply only when the user asks to change/fix/debug/test/validate/benchmark/optimize/audit/qualify/package the repository.

The production-use interface remains unchanged. Production renderer behavior is now authoritative at SHA-256 `9541c2f62cf9afccf3388eac6b929d7dd9437c19d04acb600855e61175bd1b42`. The active DEVELOPMENT release gate is now **178/178**; maintained geometry stress remains **1/1**.

## Production authority

- **Active release:** V48.
- **Renderer:** `pcb_v48_renderer.py` / `V48Renderer`.
- **Renderer SHA-256:** `586d8b54c8044129bea97088c542654b85a79465b37f1ff5ba8efbef96591c98`.
- **Mandatory DEVELOPMENT release gate:** **180/180 PASS**, zero failures/errors/skips/xfails.
- **Maintained geometry stress:** **1/1 PASS**.
- **DEVELOPMENT single-canonical-repository guard:** `tools/assert_single_canonical_repo.py`; never remove or weaken it. It is not run for plain PRODUCTION USE rendering.
- **Historical V47 authority:** archived under `archive/releases/v47/`.

## Seed totality — hard production contract

For every valid canvas / scale / seed, construction owns that exact deterministic board. Whole-sample acceptance/rejection, whole-board reseeding, or silently advancing to another logical seed is not production recovery.

V48 retains the deterministic constructive completion architecture for chip generation/placement, collection planning/calibration, component residual service, and LOCAL hard-floor debt completion. Randomized budgets are fast paths, not existence proofs. The 50–60% component-service and 80–90% LOCAL-service requirements remain construction requirements, not optional acceptance thresholds.

The MAIN line-survival family that had previously been deferred from ordinary V48 seed-totality work is now promoted as part of production rather than left as a known rejection family.

Historical exact repros that previously failed only in MAIN now complete as the requested seed:

- 1:1 @ 1.0, base seed **103** — full board emitted, `restart_index=0`, no skipped seed, zero unresolved persistence / unaccounted launches / stalled sides / geometry violations;
- 1:1 @ 0.75, base seed **103** — full board emitted with the same hard counters clean;
- 1:1 @ 0.75, base seed **105** — full board emitted with the same hard counters clean.

These are regression evidence for the previously known rejection family; they are not a claim that finite testing enumerates every possible seed. The production contract itself remains seed totality.

### Long/fine persistence totality — promoted closure

The user-supplied `1:6 @ 0.35` production logs exposed a distinct late MAIN persistence-totality defect after the earlier line-murder promotion. Exact diagnostics isolated two policy bugs: (1) mature sibling-embedded lanes with legal continuation could still be rejected when a fixed persistence clock expired; and (2) the 6-module preferred visible journey was incorrectly acting as hard validity debt even though the true launch-survival floor is 4 modules.

Production now separates **work debt** from **validity debt**: routes between 4 and 6 modules still receive preferred late routing opportunities, but missing six cannot by itself reject a valid seed. After all historical bounded final cleanup, true mature relational residue is settled by shared-snapshot, conflict-clean **progress-driven** local motion until the debt clears or no exact ordinary proposal exists; a fixed tick count cannot decide validity. Genuine zero-proposal residue is handled as local geometric exhaustion for coordinated terminal arbitration rather than as a clock failure.

Exact `1:6 @ 0.35` evidence on the promoted byte-identical source:

- base seed **1**: full board emitted with `restart_index=0`, `skipped_logical_indices=[]`, all **4,104/4,104** MAIN launch traces visible, zero hard MAIN/geometry failures, and `component_unplaced_count=0`;
- base seed **0**: full board/phase harness completes finitely. The long/fine regime is expensive (~10.5 minutes / ~785 MiB in the measured environment), but that cost already existed in the pre-fix production source; the promoted source was slightly faster in the paired run and does not introduce the high-RSS regime.

General seed totality remains a production invariant rather than an acceptance-rate claim. Any future `MAIN persistence horizon unresolved` recurrence is a construction defect to diagnose, not permission to skip/reseed. Detailed causal history is retained in `docs/LONG_FINE_PERSISTENCE_DIAGNOSIS.md`.

## Long/fine performance scaling — AUDIT COMPLETE / IMPLEMENTATION OPEN

Exact `1:6 @ 0.35` boards are now valid, but the current runtime is **not** accepted as the desired scaling behavior. Same-seed current-production audit shows ~6x territory produces roughly ~6x chips/traces/components/high-level routing checks while whole-render CPU grows ~8.09x. On seed 0, perfect territory-linear extrapolation from the current square board predicts ~455.7 CPU-s (~7.60 min) versus the measured ~614.5 CPU-s (~10.24 min): a ~158.7 s / 2.65 min scaling tax.

Phase attribution of that excess is approximately **58% LOCAL gap routing, 37% MAIN, 3% component placement**. LOCAL is the first optimization target. Detailed seed-1 counters expose two concrete amplifiers: (1) only ~10,015 long-board direct-run families are quarantined but they are re-polled **5,538,055** times; and (2) partial-service rescue candidate work grows **18x** for 6x territory because the long board enters all three whole-field rescue waves and then a 136,597-candidate deterministic debt-completion tail.

MAIN high-level work generation is much closer to linear (about 6.11x emitted segment work, 6.29x gesture checks, 6.22x lookaheads for 6x territory) while MAIN CPU grows ~8.57x on the seed-1 comparison. Instrument lower-level spatial/global-round cost before changing routing policy.

**LOCAL-1 direct-mopup dead-family retirement is now promoted.** Quarantined immutable direct-run families leave each region's cached live-run list before the next scan instead of being re-polled indefinitely. Governing 1:1 fixtures at 0.75 and 0.5 are bit-for-bit geometry-identical to the pre-change renderer. Aggregate quarantine skip work drops 10,235 -> 873 at 0.75 and 52,848 -> 2,107 at 0.5; normalized LOCAL CPU/visible-work growth improves **1.304x -> 1.226x**. Whole-render CPU/visible-routing-work growth is effectively flat/slightly better (**1.3983x -> 1.3977x**). Production SHA is `325e2ec0c79d2ec7a051c9c08b2abba73c6fab5c5561a665a2c4d16dec85acf2`; active gate **152/152 PASS**, stress **1/1 PASS**. No 0.35 run was used for this ordinary stage, per cadence.

Next target is **LOCAL-2 debt-driven hard-floor rescue scheduling**, then evidence-led MAIN infrastructure optimization. See `docs/LONG_FINE_PERFORMANCE_AUDIT.md`. There is currently no active renderer candidate.

## Promoted proactive anti-line-murder architecture

The former paused line-murder task is **closed and promoted**.

### Root cause 1 — first-rebase arbitration starvation

Exact traces showed that a viable newborn non-local structural child could have a legal mandatory first rebase and real future maneuvering room, yet repeatedly lose that move during same-round conflict arbitration. Recovery then cycled around the same young junction and produced short 6–14-module corpses.

Production now treats that state proactively:

- a viable newborn `STRUCTURAL_TRANSITION` child at `branch_stage == 0` may HOLD rather than being rolled back merely because its first rebase lost a same-round conflict;
- the first conflict gives no special priority;
- after one prior HOLD, the child's next first-rebase proposal receives a one-round anti-starvation fairness term;
- fairness state resets as soon as that first rebase commits;
- eligibility requires an exact future option; no clearance, geometry, octilinear, or persistence rule is relaxed.

### Root cause 2 — sequential late structural commits

The old residual structural-persistence helper could advance mature sibling fronts sequentially after ordinary shared-snapshot arbitration had already shown their proposed moves were mutually incompatible. On the critical fairness 0.5/seed-102 trace this created two late same-family crossings (trace/front 162/515 and 163/516 against sibling 161/509), which final preflight then had to shorten away.

Production now settles residual structural persistence in bounded **shared-snapshot atomic ticks**:

- all residual structural fronts propose from the same committed snapshot;
- conflict groups choose a maximum compatible subset;
- incompatible siblings HOLD and re-propose against the next snapshot;
- mature unresolved decorative turn intent may be cancelled only without changing the already-valid visible prefix;
- the old front-by-front sequential residual commit path is not used.

This removes the specific fairness-era late repair pathology: on 1:1 @ 0.5 / seed 102 the promoted architecture reaches final preflight with **0 local defects and 0 causal repairs**.

## Authoritative line-survival behavior evidence

Rendered visible route length in `pathway_main_outcome_by_trace` is the authoritative short-route observable. Logical travel is not authoritative after marker clipping/backoff and final preflight.

Visible terminated-trace histogram (<=8 / <=14 modules), production BEFORE vs promoted AFTER:

| Scale / seed | BEFORE V48 | AFTER promoted |
|---|---:|---:|
| 0.75 / 102 | `6 / 18` | **`3 / 11`** |
| 0.75 / 104 | `2 / 11` | **`2 / 7`** |
| 0.5 / 102 | `29 / 75` | **`18 / 58`** |
| 0.5 / 104 | `26 / 74` | **`18 / 64`** |

The goal is not to forbid every naturally short terminal. The promoted change removes the systematic first-rebase starvation / illegal late-sibling-commit mechanisms while preserving valid short outcomes when geometry genuinely warrants them.

## Scaling qualification — BEFORE vs AFTER

Formal 1:1 qualification used governing seeds 102+104, fresh one-renderer-per-process runs, with emitted visible MAIN centerline modules as useful work.

### Overall MAIN

| State | 0.75 work | 0.5 work | Work Growth | 0.75 CPU | 0.5 CPU | CPU Growth | CPU / Work Growth |
|---|---:|---:|---:|---:|---:|---:|---:|
| BEFORE V48 | 4,333.518 modules | 10,496.776 | 2.422x | 12.304 s | 39.742 s | 3.230x | **1.333x** |
| AFTER promoted | 4,339.302 modules | 10,580.413 | 2.438x | 12.993 s | 38.148 s | 2.936x | **1.204x** |

The candidate therefore does not buy survival by worsening the overall normalized curve; it improves the governing 0.75 -> 0.5 CPU/work growth materially.

### Deterministic category work growth

The conflict-state counter is intentionally not treated as a proxy for total runtime: direct profiling showed the fairness HOLD solver is tiny (~0.026 CPU-s on profiled 0.5/102), while proposal construction dominates MAIN CPU. The relevant deterministic category scaling is:

| Category | BEFORE work/visible-work growth | AFTER work/visible-work growth | Result |
|---|---:|---:|---|
| proposal variants | ~1.355x | ~1.357x | essentially unchanged |
| lookahead evaluations | ~1.412x | ~1.429x | ~1.2% worse |
| gesture-clear checks | ~1.395x | ~1.427x | ~2.3% worse |
| local-space capacity evaluations | ~1.556x | **~1.458x** | improved |
| conflict combinations | ~1.474x | ~2.590x | worse counter, but tiny CPU category |
| traceback segments | ~1.115x | ~1.221x | worse counter, cheap bookkeeping |

Lightweight inclusive category timing was retained as diagnostic evidence but is host-frequency/profiler sensitive and is not used to override the clean overall CPU qualification. The promotion decision is based on the actual overall CPU/work curve plus deterministic category work and behavior/correctness gates.

## End-of-phase 0.35 qualification

0.35 was held until the end of the phase as required. Promoted 1:1 seeds 102 and 104 both PASS MAIN with zero unresolved/unaccounted/unmaterialized launch state, zero stalled sides, zero preflight repairs, and zero clearance/octilinear/turn violations.

Aggregated promoted 0.5 -> 0.35:

- useful visible MAIN work: `10,580.413 -> 22,071.951` = **2.086x**;
- MAIN CPU: `38.148 -> 81.946 s` = **2.148x**;
- CPU/work growth: **1.030x**.

This is close to linear for the final fine-scale interval on the governing pair.

## Qualification status

Promotion gates completed:

- candidate active release gate: **148/148 PASS**;
- candidate maintained stress: **1/1 PASS**;
- promoted canonical active release gate: **148/148 PASS**;
- promoted canonical maintained stress: **1/1 PASS**;
- final 0.35 governing MAIN canaries: **2/2 PASS**;
- historical deferred MAIN rejection repros 1.0/103, 0.75/103, 0.75/105: **3/3 full-board PASS**, no seed skipping and `restart_index=0`.

## Rejected / superseded line-murder experiments

Durable conclusions from the investigation are summarized in `docs/LINE_MURDER_PROMOTION_HISTORY.md`. The obsolete inflight renderer variants/diffs are retired after promotion; they are not production authority.

Important rejected directions include broad zero-future bans, generic two-step lookahead, short-rebase rescue, broad atomic branch birth, unconditional newborn priority, greedy HOLD, depth-1-only fairness, post-rebase grace, fragile-only thresholds, fairness B&B/compatibility-bound micro-optimizations, four-tick residual horizons, keeping unresolved intent, ordinary-motion fallback after cancellation, and reservation-only late settlement.

## Optimization status

The V47 scaling optimization program Items 1–26 remains closed. The subsequent V48 seed-totality + proactive line-survival repair described above is also now promoted and closed on its maintained qualification set. Do not reopen hotspot work without new causal evidence or explicit user direction.

The historical long/fine 1:6 @ 0.35 operational qualification remains a separate expensive production-regime check; do not confuse that broader canvas qualification with the now-fixed known MAIN seed-rejection mechanisms above.

## Hard handoff-recovery process rule

If any response/run ends without a successfully verified fresh complete handoff bundle, the **first substantive action of the next run must package the exact surviving working state before any further implementation, investigation, testing, optimization, or renderer changes**. A prior execution/tool/window boundary is the trigger for recovery packaging, not an exception.

## Repository shape

Canonical state contains current source/spec/docs, active tests, maintained harnesses, executable guards, a tiny curated example set, and historical release snapshots. Raw profiler/benchmark/output trees remain outside the repository.

### 2026-08-25 recovery update — long/fine v2 remains unpromoted

A corrected v2 design was screened after the prior checkpoint but its scratch tree was subsequently lost in a runtime reset. The key correction is placement: progress-driven relational settlement must run only at the **true final persistence residue point after all existing bounded cleanup**, not earlier when hundreds of transient sibling-embedded fronts still exist. The soft-six / hard-four debt split remains the intended validity model. Surviving v2 screening evidence is recorded in `docs/LONG_FINE_PERSISTENCE_DIAGNOSIS.md`; 0.5/104 and the decisive `1:6 @ 0.35 / seed 1` repro remain incomplete. Production is unchanged and general long/fine seed totality remains OPEN.

### 2026-08-25 01:23 IST — current long/fine v2 state

The corrected v2 source now survives under `work/inflight/v48_longfine_totality_v2_renderer.py` at SHA-256 `e8d1874d652e7aa6a7af763ac20b2a97d1367082dc748f61771833be49d16054`; it is **unpromoted** and production remains SHA-256 `ac53e1d1fae493beb55ab8dc05c0ba7d3053add19a1c6b71cb52ce926738fb79`.

The explicit historical `1:6 @ 0.35 / base seed 1` repro now passes MAIN and emits a complete board from the exact requested seed: logical seed `7179163421162001120`, `restart_index=0`, no skipped logical index, 4,104/4,104 MAIN launch traces visible, zero hard MAIN/geometry violations, and zero unplaced components. Evidence is retained under `work/inflight/evidence/`. The original seed-1 rejection is therefore fixed **in the candidate**, not yet in production.

Seed 0 remains open as a separate long/fine performance/RSS problem because the user-supplied attempt had no exception and was manually terminated after prolonged CPU/RSS growth. Next work must diagnose seed 0 without changing seed ownership or conflating cost with correctness. Promotion still requires the complete release/stress and scaling/behavior gates.

### 2026-08-25 02:00 IST — long/fine seed-0 cost localized; v2 remains unpromoted

Exact `1:6 @ 0.35 / base seed 0` now completes under the whole-render phase harness in both production and v2. Production takes `630.862 s` CPU with `805,176 KiB` peak RSS; v2 takes `614.485 s` CPU with `804,192 KiB` peak RSS. The user-observed ~9 minute / ~745 MB behavior was therefore a faithful observation of a **pre-existing expensive but finite long/fine workload**, not evidence that v2 introduced a runaway or seed rejection. Production MAIN alone is `352.985 s`; v2 MAIN is `338.407 s`. LOCAL-gap routing is also very expensive (`220.395 s` production, `215.606 s` v2).

The correctness status is now: exact seed 1 full board PASS in v2 with no reseeding; exact seed 0 whole-render phase PASS in v2; production remains unchanged. v2 is still **UNPROMOTED** until the complete active release/stress and final promotion/scaling gates pass. Retained evidence lives under `work/inflight/evidence/` and the detailed diagnosis is in `docs/LONG_FINE_PERSISTENCE_DIAGNOSIS.md`.

### 2026-08-25 03:12 IST — long/fine v2 promotion blocker narrowed to 0.35 helper scaling

The unpromoted v2 remains the surviving candidate at SHA-256 `e8d1874d652e7aa6a7af763ac20b2a97d1367082dc748f61771833be49d16054`; production remains unchanged at `ac53e1d1fae493beb55ab8dc05c0ba7d3053add19a1c6b71cb52ce926738fb79`.

A later scratch qualification (lost in a runtime reset after evidence was observed) established: 0.75 -> 0.5 normalized MAIN CPU/work improves (~`1.592x -> 1.409x`); authoritative short-route behavior is equal/better; reconstructed candidate contract tests passed 151/151 and stress 1/1. However the mandatory final 0.5 -> 0.35 qualification failed scaling: production ~`1.055x`, v2 ~`1.366x` normalized MAIN CPU/work. Ordinary gesture/lookahead/local-space work does not account for the delta, so the remaining target is overhead inside `_settle_final_relational_persistence_progress()` or its direct support work. Classification: **MODIFY, not promote**. Full details and the recovery limitation are in `docs/LONG_FINE_PERSISTENCE_DIAGNOSIS.md`.

### 2026-08-25 03:58 IST — long/fine v2 promoted

The surviving v2 source has been promoted byte-for-byte into `pcb_v48_renderer.py` at SHA-256 `e8d1874d652e7aa6a7af763ac20b2a97d1367082dc748f61771833be49d16054`. The reconstructed active contract is **151/151 PASS** and maintained stress is **1/1 PASS** on the promoted file. The earlier apparent 0.5 -> 0.35 scaling blocker was timing contamination: a fresh same-host paired recheck gives production-before CPU/work growth **0.994x** versus promoted **0.989x**, with useful visible MAIN work growth ~2.086x vs ~2.081x. Promotion is therefore accepted; there is no active renderer candidate.

### 2026-08-25 04:13 IST — promoted 0341 raw-log follow-up: timeout, not rejection

User-supplied raw logs from `V48_0341_1x6_s035_raw_logs(1).zip` contain **no Python exception** for the exact CLI attempts `--aspect-ratio 1:6 --scale 0.35` (count 2, explicit seed 0, explicit seed 1, and the earlier foreground seed-1 attempt). All captured stderr files are empty; no renderer JSON summary or SVG/report was emitted before those processes were externally terminated / hit the execution boundary.

This does **not** reproduce the former MAIN persistence-totality bug. The promoted CLI is synchronous: `render_batch()` completes `generate_sample()` for a logical sample before writing that sample's SVG/report, and `main()` prints the JSON batch summary only after `render_batch()` returns. Long/fine generation is already measured as an expensive but finite production regime: exact seed 0 completes in ~630.9 CPU-s with ~805,176 KiB peak RSS on pre-fix production and ~614.5 CPU-s / ~804,192 KiB on the promoted byte-identical source; exact seed 1 MAIN alone takes ~320.5 CPU-s and the promoted source has previously emitted the full exact-seed board with `restart_index=0`. Therefore an execution window shorter than full sample completion naturally produces empty stderr/stdout and zero SVGs even when the renderer is valid.

Current status: **seed-totality fix remains closed/promoted; long/fine performance remains open.** Do not classify an externally killed, exception-free long/fine run as a seed rejection. Future work should optimize the expensive `1:6 @ 0.35` workload (MAIN plus LOCAL gap routing) and may separately improve CLI progress/checkpoint observability, without reintroducing reseeding or weakening validity invariants. Raw logs are retained under `work/inflight/evidence/0341_user_raw_logs/`.

### 2026-08-25 05:34 IST — LOCAL-2 active candidate checkpoint

LOCAL-1 remains production at SHA-256 `325e2ec0c79d2ec7a051c9c08b2abba73c6fab5c5561a665a2c4d16dec85acf2`. LOCAL-2 is now represented by one coherent inflight candidate at `work/inflight/v48_local2_candidate.py`, SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`; it is **not promoted**.

The current candidate combines a single stochastic hard-floor debt campaign with an exact first-leg legality cache for deterministic debt completion. The ordinary 0.75 -> 0.5 screen improves normalized LOCAL CPU/work growth from ~`1.105x` to ~`1.042x` and whole-render CPU/work growth from ~`1.292x` to ~`1.271x`. Partial-rescue candidate tokens fall from `3,201 -> 9,600` across production 0.75 -> 0.5 to `1,067 -> 4,800` in the candidate; 0.5 deterministic completion attempts fall `35,759 -> 22,886`.

The completed long `1:6 @ 0.75` proxy proves the diagnosed work cliff is removed (`3 -> 1` rescue waves, `19,200 -> 6,400` partial tokens), but it also changes LOCAL population: service `0.806398 -> 0.800341`, total LOCAL traces `2,392 -> 2,096`, visible traces `1,085 -> 1,061`, with 27 deterministic-completion traces. This candidate therefore remains **RETAIN / qualification incomplete**. The next question is behavioral: whether the lower total trace population is a legitimate elimination of redundant stochastic rescue or an unacceptable thinning of the design language. No release/stress gate or promotion is earned until that is resolved. See `work/inflight/evidence/LOCAL2_CANDIDATE_STATUS_2026-08-25_0534IST.md`.

### 2026-08-25 05:41 IST — LOCAL-2 promoted; MAIN instrumentation next

LOCAL-2 is now production at SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`. Candidate and promoted canonical gates pass **154/154**, maintained stress **1/1**. The partial-service reserve now opens one stochastic debt campaign rather than repeatedly rescoring the same whole unpaid field; deterministic exact-legal completion reuses an identical first-leg legality proof only across second-leg variants that share that exact leg.

The long `1:6 @ 0.75` behavior check shows the apparent total-source reduction is overwhelmingly non-visible work elimination: 296 fewer total LOCAL source traces but only 24 fewer visible traces (92% of removed sources non-visible), service `0.806398 -> 0.800341`, mean turns `1.2341 -> 1.2422`, and comparable direct raster texture. This is accepted as behavior-preserving removal of redundant emergency rescue work rather than density thinning.

There is no active renderer candidate after this promotion. The next optimization target is MAIN-1 instrumentation of per-operation amplification. Per cadence, do not run 0.35 until the full current optimization phase reaches its final qualification boundary.

### 2026-08-25 10:49 IST — MAIN-1 recovery checkpoint after runtime reset

The MAIN-1 instrumentation/profiling scratch tree from the prior run was lost in a runtime reset before a fresh handoff could be built. Production remains the promoted LOCAL-2 renderer at SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`; **no MAIN candidate is promoted**.

Preserved evidence is now durable in `docs/MAIN1_INSTRUMENTATION_AUDIT.md`. The long-aspect 0.75 proxy shows both proposal/recovery work amplification (~26–29% more gesture/lookahead work per emitted segment) and a smaller per-check locality tax, but not a collapse of the spatial broad phases. A redundant third active-head snapshot rebuild was tested and rejected as a meaningful long/fine optimization after an adjacent proxy comparison (`48.03 s` production vs `48.55 s` candidate, exact same geometry/work).

The current smallest earned but lost/unpromoted experiment is exact O(1) extraction of a forced-close lane's current materialized head instead of rematerializing its entire historical offset polyline merely for broad-phase indexing. Initial square evidence preserved exact geometry and measured `5.536 -> 5.390 CPU-s`; the decisive long-proxy result was not recovered. The first implementation action after this checkpoint is to reconstruct only that candidate and qualify it; do not touch production first.

### 2026-08-25 11:41 IST — MAIN-1 lane-head candidate rejected after recovered formal gate

The O(1) forced-close lane-head candidate survives at `work/inflight/main1_lane_head_renderer.py`, SHA-256 `8ca2b04d63ffd9565c9aa788499e2f4b00973912599f2950ec1ea05282c2ba0f`, but is **REJECTED / UNPROMOTED**. All four formal 0.75/0.5 production/candidate records survived and are now retained in the handoff. Geometry and deterministic work are identical on every fixture. Aggregate normalized MAIN CPU/work growth is `1.456416x` production vs `1.456659x` candidate, so the formal curve is flat/slightly worse despite a small adjacent long-proxy speedup (`46.08 -> 45.45 s`). Production remains SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`. Next work should target a higher-leverage source from the MAIN-1 profile rather than promote this cleanup.

### 2026-08-25 12:24 IST — missed-handoff recovery / MAIN-1 probe state preserved

Authoritative production remains the promoted LOCAL-2 renderer at SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`; there is no unpromoted renderer behavior candidate eligible for promotion. The O(1) lane-head cleanup remains formally rejected.

Two later surviving files are **instrumentation-only** probes: `work/inflight/main1_conn_count_renderer.py` (`236f3b52...6e398`) and `work/inflight/main1_join_reject_probe_renderer.py` (`da726521...34bcc`). They add counters only and have no surviving benchmark conclusion. After this recovery bundle, MAIN-1 resumes by measuring square-vs-long `0.75` connection/join amplification with these probes, then choosing the next evidence-backed optimization mechanism. Do not promote either probe as renderer behavior.

### 2026-08-25 13:30 IST — MAIN-1 active future-envelope fallback candidate

Authoritative production remains SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`; no production renderer change has been promoted.

The active MAIN-1 causal finding is that exhausted same-round atomic conflicts are predominantly **heuristic future-envelope conflicts rather than committed current-corridor conflicts**. On the surviving seed-1 0.75 aspect probe, 100/123 exhausted `1:1` conflict attempts and 569/620 exhausted `1:3` attempts already admitted a complete all-front exact-current-corridor assignment. Repeated future-envelope rejection was therefore amplifying rollback, traceback, proposal, lookahead and gesture work with aspect.

Rejected experiments on the way to this finding include proposal/future certificate banks, exhausted partial-HOLD subset movement, and extra proposal-variant search. See `docs/MAIN1_INSTRUMENTATION_AUDIT.md` for the evidence and reasons.

The current unpromoted candidate is `work/inflight/main1_future_envelope_fallback_renderer.py` at SHA-256 `d2dfd5749bfec421bd88bc2c2670eb33e945a10663c4d6e1e5b5fbfa092100ba`. The prior scratch source was not bundled, so this candidate was reconstructed against authoritative production from the surviving implementation description. It keeps the existing future-aware full atomic solver primary and only, after that solver is exhausted, permits a **full** exact-current-corridor assignment when every selected proposal still has at least one individually legal future option. It never chooses a partial winner set, never commits sequentially, and does not relax current geometry clearance.

Surviving first-proxy evidence is promising but non-qualifying: production `1:1 -> 1:3 @ 0.75` MAIN CPU was about `5.83 -> 20.74 s`; candidate about `6.51 -> 19.84 s`; long-side gesture checks fell `79,364 -> 75,684` and lookaheads `61,794 -> 59,563`. Observed hard MAIN invariants were clean. Formal governing 0.75/0.5 qualification is incomplete; the candidate is **UNQUALIFIED / UNPROMOTED**.

Next exact action: fresh 0.75 seeds 102+104 production-vs-candidate qualification, then 0.5 seeds 102+104, with the mandatory categorized + overall BEFORE/AFTER Work Growth / CPU Growth / CPU-per-Work table and complete active release/stress gates before any ACCEPT/PROMOTE decision. Keep 0.35 reserved for end-of-phase qualification.

## 2026-08-25 14:28 IST — MAIN-1 recovery status

The interrupted future-envelope qualification has been recovered from durable files. Production is still unchanged at `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`.

- The original `main1_future_envelope_fallback_renderer.py` is **REJECTED**: at `0.5 / seed 102`, MAIN CPU regressed `39.77 -> 40.72 s`, rollback segments `2797 -> 2882`, and lookaheads `57550 -> 60031`.
- The stricter cached joint-future approach (`main1_joint_future_fallback_cached_renderer.py`, SHA `deaf7348a15467aba7f8b4571d6bd2b7b17e457f9da6aa8618c3e123f049fe4b`) lowers absolute CPU at both governing scales but slightly worsens normalized 0.75 -> 0.5 CPU/work growth: production `1.3752x` vs candidate `1.3843x`. It is therefore **UNPROMOTED / NOT ACCEPTED as MAIN-1 scaling fix**.
- The raw-distance optimization of that branch is **REJECTED** after `0.5 / seed 102` exceeded 120 s in the MAIN-only harness without output.
- A fallback-count probe showed 266 attempted joint-future fallback groups and 79 successes at `0.75 / seed 104`, but a lifecycle-heavy version of the probe was itself too intrusive at fine scale and is not evidence about renderer correctness/performance.

There is currently **no active promotable renderer candidate**. The next exact step is a low-overhead O(1)-counter audit of the cached joint-future fallback at the regressing `0.5 / seed 104` fixture, separating direct fallback-search cost from downstream recovery/topology cost. Preserve the cached joint branch as evidence only; production remains authority. Do not run 0.35 during ordinary MAIN-1 candidate work.

### 14:35 IST host/runtime note
A low-overhead joint-future fallback-cost probe is now preserved as `work/inflight/main1_joint_future_fallback_lightprobe_renderer.py`. On `0.75 / seed 104`, direct fallback search cost was only `0.281 CPU-s` of `8.983 s` MAIN (~3.1%), with 266 attempts and 79 successful fallback groups. Fine-scale `0.5 / seed 104` could not be remeasured because both the probe **and unchanged cached control** exceeded the current 90-second command boundary. A 30-second control consumed a full CPU core (~101%), so this is not scheduler starvation. Do not interpret these current timeouts as candidate regressions; use the earlier durable formal records for current conclusions.

### 2026-08-25 16:28 IST — interrupted-run recovery / governing fine fixture unusable on current host

The post-14:35 continuation retried the unchanged cached joint-future control and low-overhead light probe adjacently on `0.5 / seed 104` with a larger foreground execution boundary. The unchanged cached control again failed to emit a record before the boundary. No PCB renderer process survives the interruption, no renderer source was changed/promoted, and production remains SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`.

This is treated as a **host/tool execution limitation**, not new renderer-performance evidence, because the same deterministic cached control previously completed and has durable formal records, while recent same-host reruns have become >90 s and now exceed the expanded foreground boundary as well. Preserve the earlier formal evidence.

MAIN-1 remains unresolved. The next practical diagnostic is a deterministic smaller MAIN-only proxy that reproduces the same recovery/conflict topology and can complete on this host. Use the proxy only to choose/iterate on an architectural candidate. Promotion still requires the mandated governing ordinary qualification (`0.75` then `0.5`, seeds 102+104), categorized + overall BEFORE/AFTER scaling table, and full release/stress gate on a usable execution host. `0.35` remains reserved for the end of the full optimization phase.


### 2026-08-25 21:28 IST — MAIN-1 post-16:29 recovery checkpoint

The interrupted continuation after the 16:29 bundle produced proxy-only MAIN-1 evidence but no surviving promotable source. Production remains SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`. Post-commit-state lookahead variants and reciprocal-peer future-envelope exemption were rejected. The current earned wedge is connection lifecycle: long-range attraction is soft, but hard `CONNECTION_PENDING` pairing appears to begin before the actual singleton join executor can act. Next experiment delays hard pairing until the existing 10-module executor reach while preserving all join legality/geometry/RNG semantics. Full evidence is in `docs/MAIN1_INSTRUMENTATION_AUDIT.md`.

### MAIN-1 continuation checkpoint — 2026-08-25 21:50 IST

Production is still SHA-256 `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`; MAIN-1 remains active with no promotable candidate. New proxy work rejected 10-module connection-pending caps, soft-only long-range pair guidance, and recovery exclusion. Pair-churn instrumentation showed most immediate partner switching occurs during repair, so connection churn is a symptom of recovery coupling rather than a standalone target.

The strongest new causal finding is that 510/640 exhausted atomic conflict groups with no schedulable repair recur with the same front set on the very next round. Existing path/proposal/future failure caches already have high hit counts, so ordinary blocked-geometry recomputation is not the missing optimization. `_future_conflict()` itself has high cross-round reuse (~65% approximate repeated pair states), but exact cross-round memoization attempts were either too expensive or semantically fragile; an exact round-local proposal-object cache was behavior-preserving but only ~20% hits and no robust speedup.

Next target: event/version-driven or exact immutable-state reuse of unchanged exhausted conflict transactions, preserving RNG, legality, horizon behavior and routing decisions. Proxy work remains non-qualifying; any earned candidate must still pass the mandated 0.75 -> 0.5 seeds-102+104 normalized work/CPU gate and full release/stress gate before promotion.

### 2026-08-25 21:58 IST — MAIN-1 recurrence cost localized to proposal/lookahead regeneration

Production remains unchanged at `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`; no MAIN-1 candidate is active/promotable. A method-level timing probe on the stable `1:2 @ 0.75 / seed 104` recovery proxy shows dominant inclusive cost in `_proposal_variants` (~11.07 s), `_lookahead_adjust` (~5.50 s), `_propose` (~5.09 s), `_gesture_clear` (~4.95 s), and `_future_options` (~4.94 s), while `_future_conflict` (~0.93 s), `_conflict_groups` (~0.88 s), and `_solve_conflict_group` (~0.26 s) are much smaller. Combined with the prior finding that 510/640 exhausted no-repair groups recur unchanged on the next round, the next MAIN-1 target is exact event/version-guarded reuse of proposal/lookahead subproofs for an unchanged transaction. Do not alter routing/RNG/legality semantics; formal 0.75 -> 0.5 qualification remains required and routine 0.35 remains forbidden until phase end.

### 2026-08-25 22:15 IST — MAIN-1 promoted; phase-end 0.35 active

MAIN-1 exact-local proof reuse is now production at SHA-256 `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`. It preserves routing decisions and final geometry while reusing already-paid proposal-membership and successful future-leg legality proofs only when the exact front state and exact local committed-path/source-egress dependencies are unchanged. Relevant local mutation invalidates reuse immediately.

Formal seeds 102+104, 0.75 -> 0.5: final MAIN segment work growth is identical at `2.515003x`; normalized MAIN CPU/work growth improves **`2.215492x -> 1.432545x`**; aggregate 0.5 MAIN CPU falls `59.275867 -> 40.621074 s`; gesture-clear checks fall `149,901 -> 130,062`; geometry hashes/lookahead/rollback/traceback topology are identical. Canonical release gate is **156/156 PASS**, geometry stress **1/1 PASS**. There is no active renderer candidate.

The ordinary long/fine scaling stages are therefore closed and the reserved phase-end 0.35 qualification is active. The first pre-MAIN-1 `1:1 @ 0.35 / seed 102` attempt exceeded a 180-second wrapper boundary without emitting a record; this is incomplete measurement, not renderer failure. Next action after the mandatory recovery bundle is to run the phase-end 0.35 BEFORE/AFTER comparison for seeds 102 then 104, then update the final categorized + overall scaling closure. The historical full `1:6 @ 0.35` production-runtime benchmark remains a separate operational check.


## 2026-08-26 00:08 IST — long/fine scaling phase closed

MAIN-1 final same-host 0.5 -> 0.35 qualification passes with identical geometry/topology: useful MAIN work grows `2.063991x`; normalized MAIN CPU/work improves `1.037378x -> 1.005017x`. The earlier provisional `1.268x` AFTER figure is superseded because it mixed 0.5 and 0.35 timings from different host-performance epochs. Production remains SHA `3100503d...03ebb`; canonical gate remains 156/156 + stress 1/1. LOCAL-1, LOCAL-2 and MAIN-1 are all closed/promoted. Next: separate full `1:6 @ 0.35` operational benchmark of current production and whole-render comparison against the pre-optimization audit.

### 2026-08-26 00:46 IST — interrupted full long/fine operational benchmark recovery

After the 00:09 phase-closure checkpoint, the authoritative promoted renderer (`3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`) began the separate full `1:6 @ 0.35 / base seed 0` whole-render operational benchmark. The prior execution turn ended before the harness emitted its JSON record. No renderer process or durable benchmark output survived into the resumed runtime. The last live observation before interruption was approximately **5:05 CPU time / ~494 MiB RSS**, with one healthy renderer process, no Python exception, and no completed sample yet. This is an **interrupted observation only**, not a runtime result or failure classification. The exact fixture must be rerun to completion before updating the operational BEFORE/AFTER table.

### 2026-08-26 — full `1:6 @ 0.35` operational check reopens long/fine scaling

Authoritative production SHA remains `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`; correctness remains closed and no promoted optimization is reverted. Exact seed-0 same-host phase-harness runs now exist for both `1:1 @ 0.35` and `1:6 @ 0.35` under `work/inflight/evidence/operational_post_main1/`.

Current same-host results: total CPU `96.822 -> 729.786 s` (7.537x) while visible routing work (MAIN launches + LOCAL traces) grows `2,006 -> 11,993` (5.979x), giving **1.261x whole-render CPU/work growth**. MAIN CPU/launch grows **1.256x**, LOCAL CPU/trace **1.375x**, component-place CPU/component **1.164x**. Peak RSS `235,092 -> 802,392 KiB` is sublinear versus work. Six-times-square extrapolation leaves `148.855 s` excess, approximately `+75.37 s` MAIN and `+67.30 s` LOCAL.

Therefore the actual long board overrides the earlier provisional phase-closure wording: **long/fine performance scaling is reopened**. LOCAL-1, LOCAL-2 and MAIN-1 remain valid promoted sub-optimizations, but additional aspect-driven MAIN/LOCAL work is required. The absolute 729.8 s cannot be compared directly with the historical 614.5 s because host speed changed; same-host ratios are authoritative for this decision.


## 2026-08-26 01:23 IST — reopened long-board LOCAL localization

- No production change; authoritative renderer remains `3100503d...03ebb`.
- Full `1:1 -> 1:6 @ 0.35` same-host operational scaling remains the governing reopen evidence: whole-render CPU/work `1.261x`, LOCAL CPU/trace `1.375x`, MAIN CPU/launch `1.256x`, components CPU/component `1.164x`.
- New zero-policy `0.75 / seed 0` LOCAL aspect probe: visible traces `166 -> 1000` (6.024x), open cells `2741 -> 16098` (5.873x), but residual regions `47 -> 344` (7.319x). `_launch_local_gap_fronts()` CPU grows `1.158 -> 9.138 s` (7.894x), while `_gesture_clear()` grows 6.038x and `_local_gap_target()` only 4.828x.
- Diagnostic cProfile points into repeated launch scheduling / fragmented residual geometry: `_launch_local_gap_fronts()` ~`1.696 -> 13.940 s`; long-board `STRtree.query_nearest` ~4.312 s/1012 calls; `_residual_gap_regions()` `0.653 -> 4.828 s` (~7.39x).
- No active renderer candidate. Next earned work is to separate nearest-geometry tree/query cost from whole-candidate-pool scoring/allocation in `_launch_local_gap_fronts()` and remove work proportional to fragmentation rather than accepted LOCAL service. Existing LOCAL-1/2 and MAIN-1 promotions remain retained.

### 2026-08-26 02:55 IST — LOCAL-3 nearest-query checkpoint

Long/fine scaling remains reopened; production SHA stays `3100503d...03ebb`. LOCAL-3 localization found the strongest current aspect amplifier inside `_launch_local_gap_fronts()` nearest scoring: static global `STRtree.query_nearest` grows ~13.77x for ~5.85x static geometry; path nearest grows ~10.64x for ~5.62x path geometry. Exact global-tree caching, capped vector query, per-region sort, and per-candidate Python-local nearest were rejected. Exact static score-radius tiling improves launch-scheduler aspect growth (`8.073x -> 7.350x`) with identical LOCAL counters but does not improve whole-LOCAL proxy growth (`~1.327x -> ~1.344x`), so it is MODIFY/not promotable. Next: retain production and find a lower-overhead locality representation, likely addressing both static and path nearest scoring; whole-LOCAL normalized scaling is the acceptance metric.

## 2026-08-26 04:06 IST — LOCAL-3 process/status correction

The reopened long-board optimization is not back at square one, but the latest LOCAL-3 work became too micro-iterative. Preserve all promoted LOCAL-1/LOCAL-2/MAIN-1 changes; production remains `3100503d...03ebb`.

Critical denominator correction: on the `0.75 / seed 0` `1:1 -> 1:6` LOCAL proxy, visible traces grow `6.024x`, but exact nearby path records reaching GEOS grow `6.830x` and static primitive broad-phase returns grow `7.633x`. Thus much of the apparent `1.375x CPU/trace` tax reflects genuinely denser collision work on the long board, not algorithmic overhead. Judge future LOCAL scaling against relevant collision work as well as emitted traces.

Rejected after 02:56: finer path-hash cells, LOCAL first-leg proof-cache extension, LOCAL future-success proof-cache extension. Current unpromoted candidate: `work/inflight/local3_two_level_static_renderer.py`, exact two-level static group->primitive broad phase. Square screen is behavior-identical and effectively cost-neutral; long result is still unqualified.

Process rule for next work: qualify this candidate once. If it lacks a material whole-LOCAL normalized win, reject it and stop broad-phase micro-variant cycling. Recompute residual LOCAL CPU-per-relevant-work; continue LOCAL only if a substantial algorithmic amplifier remains, otherwise move to MAIN aspect scaling.


## 2026-08-26 04:40 IST — OPTIMIZATION STOPPED

Optimization is no longer an active task. The sole remaining candidate, `work/inflight/local3_two_level_static_renderer.py`, is **REJECTED / UNPROMOTED** after failing to finish the governing `1:6 @ 0.75 / seed 0` proxy inside 300 s (production reference ~116.804 s). There are **no active renderer candidates**.

Retain production SHA `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb` and all promoted LOCAL-1/LOCAL-2/MAIN-1/seed-totality/anti-line-murder work. Final canonical validation: 156/156 active tests + stress 1/1 PASS.

Known residual aspect scaling is accepted/deferred, not an active optimization target. Same-host full `1:1 -> 1:6 @ 0.35` remains whole 1.261x CPU/visible-routing-work, MAIN 1.256x CPU/launch, LOCAL 1.375x CPU/visible-trace, components 1.164x CPU/component. LOCAL's trace-normalized figure overstates pure algorithmic growth: on the diagnostic proxy, exact path-GEOS collision work grows 6.830x and static primitive interaction work 7.633x versus 6.024x visible traces and 7.856x LOCAL CPU. Do not resume optimization unless explicitly requested; proceed to non-optimization roadmap work instead.

## 2026-08-26 — historical baseline correction: 0341 was not merely slow

New user-supplied primary evidence, retained under `work/inflight/evidence/preoptimization_pair_chip_isolated_20260825/`, corrects the earlier historical characterization of the pre-optimization `2026-08-25_0341IST` renderer.

`renderer_error.log` shows that one 0341 process ran for `435.3526184 s` (`7:15.35`) and then exited with code 1 at final validation:

`RuntimeError: post-route validation failed: pair_chip_isolated`

Therefore the pre-optimization long/fine regime must **not** be described globally as "stable/valid but slow" or merely "expensive but finite". Some measured seeds/attempts did complete successfully and some previously supplied attempts were externally terminated with empty stderr, but at least one 0341 run demonstrably reached post-route validation and failed correctness after substantial CPU time. The old baseline was seed/path-dependent in both validity and runtime.

The new raw log contains no CLI invocation or seed. Consequently it cannot serve as an exact replay fixture, and this repository does not claim that current production specifically reproduces/repairs `pair_chip_isolated` for that unknown historical seed. Current production's already-established tested validity evidence (exact long/fine seeds 0/1 plus the canonical active suite) remains valid, but the historical baseline narrative is corrected.

## 2026-08-26 — `pair_chip_isolated` seed-totality defect FIXED / PROMOTED

The historical raw log's missing seed is **not** a limitation on classifying the failure. Seeds are renderer inputs, not lottery tickets: any valid seed that reaches a final validity error is a production correctness defect. Exact replay of that one historical random seed would have been useful forensic convenience only, not a prerequisite for fixing the bug.

`pair_chip_isolated` means a pair-clearance failure between a main chip and a component whose `placement_kind` is `isolated` (an isolated capacitor/residual filler). It does **not** mean that a chip failed to connect.

The causal defect was reproduced deterministically from geometry. Construction admitted chip clearance using a nominal-radius finite Shapely round buffer (`quad_segs=8`), while final validation used exact primitive Euclidean distance. The finite buffer is an inscribed chord approximation, so a thin region near rounded offset corners lies outside the polygonized buffer while remaining at true distance `< component_chip_clearance`. A component in that region was therefore accepted during construction and rejected only at final validation as `pair_chip_isolated`.

Production now uses a conservative finite-buffer radius `gap / cos(pi/(4*q)) + epsilon` for the fast chip keepout and residual static-clearance certificates. This makes the polygonized keepout a superset of the true required Euclidean neighbourhood: it may reject a razor-close valid proposal but cannot admit an invalid one. An exact phase-local `_component_chip_clearance_violation_count()` audit is also required to be zero before the component phase is accepted; it never triggers a whole-board/seed retry and MAIN remains frozen.

Permanent regression coverage includes the explicit old false-safe annulus, direct assertion that final validation names it `pair_chip_isolated`, conservative residual-clearance certificates, 4,680 adversarial near-boundary geometry cases with zero false accepts, and end-to-end seed checks. Canonical gate is **158/158 + stress 1/1 PASS**.

Authoritative renderer SHA is now `d7ac1d9af0286dda86d994a638504fe8ab63521847d9050633fc4d49d0f21745`.

The old wording that "the exact failure cannot be claimed closed because the seed is missing" is superseded. The historical invocation is still unavailable for byte-for-byte replay, but the **causal bug class is reproduced and closed** independently of seed identity.
