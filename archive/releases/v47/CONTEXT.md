# Current Repository Context

Updated: 2026-08-23 clean promotion of the independent seed-totality tranche + paused line-murder workset preservation.

## Production authority

- **Promoted production renderer:** `pcb_v47_renderer.py`, SHA-256 `648a53399955fa1c521d718308ea296b6d2c1bc5fb60fd83abe1b027c7f20e7b`.
- This is the clean 23:19 seed-totality tranche: batch seed skipping removed, whole-board reseeding removed, collection-family construction made total, MAIN preflight repair made defect-local, and component hard-floor completion made monotonic/local.
- Fresh promotion qualification completed: **137/137 active release tests PASS + 1/1 maintained stress PASS**.
- Later termination/embedded-lane experiments are **not** in production authority. Their latest reconstructive renderer/test deltas are preserved under `work/inflight/line_murder_terminal_followup_*.diff`, alongside the paused V3 candidate, because their failure mode is now governed by the proactive anti-line-murder task.
- Repository cleanup itself did not alter renderer behavior.
- The completed scaling program covers Items 1–26 on its qualified fixtures. See `docs/OPTIMIZATION_HISTORY.md`.

## Hard handoff-recovery process rule

If any run ends without a successfully verified fresh complete handoff bundle, the **first substantive action of the next run must be recovery packaging of the exact surviving working state before any further project work**. No implementation, investigation, test run, optimization, or renderer change may happen first. The recovery bundle must preserve inflight/unpromoted work and clearly document authority versus inflight state plus the latest findings/failures/next step. Previous inability to package is the trigger for this rule, not an exception to it. See `AGENTS.md` and `docs/WORKFLOW.md` for the normative wording.

## Repository normalization

The optimization run had accumulated thousands of raw work products in the canonical repository: benchmark JSONs, profiler dumps, copied renderer candidates, acceptance trees, logs, forensic directories, generated SVGs, and dozens of redundant status/handoff documents. They were not product source and made each handoff hundreds of megabytes.

The canonical repository is now intentionally small:

- current renderer + behavior specification;
- active tests and two small performance harnesses;
- the hard single-canonical-repo guard and handoff builder;
- compact current/process/history documentation;
- source-oriented historical release snapshots;
- a very small current example set;
- one compact paused line-murder inflight workset (V3 plus reconstructive follow-up deltas), not a variant forest.

Raw optimization evidence is no longer canonical repo content. Its durable conclusions are consolidated into `docs/OPTIMIZATION_HISTORY.md`, `CHANGELOG.md`, and this file.

## Paused Task 1 — premature MAIN-line murders

The user asked to set this aside while repository cleanup and rejected-sample discussion happen.

Production authority is the promoted seed-totality renderer above. The primary retained unpromoted line-murder candidate is:

`work/inflight/line_murder_space_replan_v3.py`

Candidate SHA-256:

`b033e0c0e7423cfc9be2e09f0c9399c2bdb6925140ed7a4f8bf124949dda2329`

Additional compact reconstructive evidence from the later termination-totality continuation is preserved as:

- `work/inflight/line_murder_terminal_followup_renderer.diff`
- `work/inflight/line_murder_terminal_followup_tests.diff`

Those deltas are **not active production code**. They preserve the latest late-terminal experiments and regressions so their findings can be reused when the line-murder task resumes without contaminating authority.

Causal diagnosis: a final-horizon `space_available_replan` termination deferral can correctly prove that local continuation space exists after the shared main-routing clock has effectively ended. The front then may receive no ordinary movement opportunity before coordinated final termination. V3 gives only those exact horizon-deferral fronts a bounded three-round atomic movement settlement using the existing proposal/conflict/collision/connection machinery; it does not begin a new late recovery campaign.

Governing seed `16875795162674203288` evidence:

| scale | authority centerline | V3 centerline | terminal traces | bundled forced terminals |
|---|---:|---:|---:|---:|
| 0.75 | 67,820.03 | 69,361.74 (+2.27%) | 56 -> 52 | 14 -> 12 |
| 0.5 | 138,727.61 | 143,936.74 (+3.75%) | 145 -> 145 | authority baseline retained / V3 36 |

At both measured scales V3 recorded zero short terminations, stalled sides, unaccounted launches, non-octilinear segments, illegal turns, unmarked clearance/overlap violations, or static intersections. **V3 is still INFLIGHT / UNPROMOTED**; broader behavior qualification, normalized scaling interpretation, and the complete release gate remain outstanding. Do not promote it merely from these two measurements.

## Governing clarification — anti-line-murder is proactive construction

Anti-line-murder does **not** mean "detect a bad terminal late, then reject the board or spin another seed." Its governing intent is that MAIN routes are smarter and more proactive about their path choices: especially at emergence and the first few gestures, they must account for local space, sibling progression, and plausible future maneuvering room so they do not commonly create a one-turn/early dead-end that later has nowhere legal to go.

Local candidate gestures/routes may be rejected and replanned before committing such a doomed state. A late embedded/short/dead-end detector is only an assertion/regression guard that proactive construction failed. It must not become a production acceptance filter, a whole-board rejection trigger, an exhaustion-based permission to murder the line, or a different-seed retry mechanism.

Therefore the current seed-totality work must not drift into inventing a broad late terminal-rescue subsystem as a substitute for good MAIN construction. If a final detector fires, trace the causal routing/planning failure backward and fix the proposal/selection behavior that created the doomed state while preserving unrelated valid work. The separate V3 line-murder candidate remains paused/unpromoted.

## Active architectural issue — seed totality / no production sample acceptance

Hard production rule: **a valid canvas/scale/seed must deterministically construct one valid board.** Whole-sample acceptance/rejection, skipping to another logical seed, or treating seeds as lottery tickets is not an acceptable production mechanism. Local proposal rejection remains normal. Final sample validation is an assertion that construction preserved the hard invariants; if it fires, that is a renderer defect to fix at the causal phase.

Do not solve this by raising whole-sample retry budgets, advancing to a different logical sample, weakening geometry/behavior invariants, or converting failures into a softer final quality filter. Recovery must be local/bounded and preserve unrelated valid upstream work.

### Promoted independent seed-totality repair tranche

1. **Batch acceptance/skip removed.** `render_batch()` renders exactly logical indices `0..count-1`; `RuntimeError` is no longer swallowed and replaced with a different seed. The old CLI retry/skip controls were removed.
2. **Whole-board reseeding removed.** `generate_sample()` no longer loops over whole-sample restart seeds. Early construction exhaustion now identifies the causal phase instead of silently rebuilding the board.
3. **Collection-family coverage made total locally.** Missing ordinary-family coverage can consume surplus capacitor-family slots, surplus ordinary slots, or locally promote a lower-complexity collection. It no longer returns “bad sample” for a cosmetic family draw. N=15..18 was spot-checked across 20,000 deterministic seeds per N with zero assignment failures.
4. **MAIN preflight repair budget made defect-local.** The former fixed 12-transaction ceiling for the entire board was replaced by a bounded budget proportional to observed suppressed/missing launch defects. Intersection, clearance, and duplicate cleanup causal pairs are included. A real 13-independent-defect integration regression restores all 13 launches.
5. **Component hard-floor completion no longer stops at an arbitrary global filler count.** Residual completion is finite because every failed local cell is retired and every successful filler claims/retires at least one service cell. A forced `component_extra_filler_limit=0` regression still reached 51.2% service; the old architecture stopped near 0.2% and would later reject the sample.

Promotion gate for these changes: **137/137 PASS + 1/1 maintained stress PASS**. The paused line-murder V3 file remains byte-identical and unpromoted.

### Long/fine evidence and remaining totality work

User-reported local/Codex production run at approximately **1:6 @ 0.35** attempted eight logical samples, discarded all eight, emitted zero SVGs, and spent about 52 minutes. That behavior is not acceptable and the skip/reseed machinery that enabled it is now gone.

The final optimization qualification itself was only 1:1 at 0.75 -> 0.5 -> 0.35. A 1:6 @ 0.35 board is about 48.98 canonical territories, six times the 1:1 @ 0.35 territory, so the old 134-test/1:1 closure never proved long/fine seed totality.

Historical V47 evidence shows `1200:6248 @ 0.35` (~42.5 territories) could produce a full sample with 85 chips / 696 collections. A fresh exact probe also generated **1:6 @ 0.35**, base seed `202608182200`, logical index 0, derived seed `505888913089298392`, with **98 chips / 810 collections** and no whole-board retry, in about **849.9 s**. Thus the regime is constructible and failures are path/seed dependent rather than universally impossible.

The historical recorded failing fixture `1200:6248 @ 0.35`, base seed `20260816`, previously died at MAIN preflight with 5 suppressed launch traces (`3549` launch traces vs `3544` visible). The current per-defect preflight repair directly addresses that failure class, but a current MAIN-only reproduction did **not** complete within a 20-minute execution boundary. It neither re-threw the old invariant nor proved success. Treat that as an unresolved **termination/performance-totality** signal; do not mark the historical seed fixed yet.

Remaining ordinary sample-killing classes still to totalize/qualify include MAIN persistence-horizon exhaustion, component preparation/placement service exhaustion beyond the global-cap fix, LOCAL 80% hard-floor exhaustion, and any final validator failure caused by a recoverable construction path. True impossible-state/programmer assertions (for example non-octilinear commit corruption or deterministic RNG replay divergence) remain loud defects rather than recovery/acceptance mechanisms.

Release criterion remains **seed totality**, not an acceptance percentage.

## Preserved line-murder-adjacent termination evidence after the promoted 23:19 checkpoint

This later experimental state is preserved as reconstructive diffs even though it is not promoted. The termination-totality continuation removed the old fallback that eventually treated an embedded mature singleton ending as legal merely because repair attempts were exhausted. That fallback was acceptance-by-exhaustion and could reintroduce the very premature/embedded terminal behavior the renderer is supposed to prevent.

The preserved experimental patch added transactional final-lane repair: failed forward separation restores the lane exactly, and bounded tail replan rewinds only that lane's owned tail while leaving sibling geometry untouched. Targeted regressions established that exhaustion does not legalize an embedded ending, failed repair rolls back exactly, and sibling routes are not mutated. The full active gate for this unpromoted tree previously reached **139/139 PASS + 1/1 stress PASS**.

However, the exact historical fixture `1200:6248 @ 0.35`, base seed `20260816`, still failed in production MAIN after about **278.6 s** with `RuntimeError: V47 persistence horizon unresolved`. Post-patch diagnostics showed that the old exhaustion loophole had been masking a systematic residue: **54 mature unresolved MAIN lanes**, broken down as **50 `between_siblings` only, 2 fragment-embedded only, and 2 fragment-embedded + between-siblings**. They had no under-six-module, source-egress, pending-fan, pending-fragment-birth, or unfinished-branch debt; many were already roughly 8–18+ modules long.

Therefore deeper blind rollback is not yet justified. The next causal discriminator, which was started but not completed, is to test each final mature embedded lane for an ordinary legal straight/±45 continuation after normal routing:

- if a legal continuation exists, the fixed persistence horizon is the bug and that lane should continue locally;
- if no legal continuation exists, the renderer needs a deterministic local physical terminal-resolution rule for that genuinely exhausted lane;
- neither outcome may reject the whole seed.

Do not promote these late-terminal experiments as a seed-totality shortcut. Under the governing proactive anti-line-murder rule, systematic embedded-lane residue is evidence that MAIN routing/planning must prevent the doomed state earlier; late detectors remain assertions, not acceptance or board-rejection machinery.

## Post-optimization roadmap

The ordered behavior/CLI work remains:

1. premature MAIN-line murders — paused with V3 retained;
2. diagnose and eliminate whole-sample rejection at large long/fine territory before claiming production robustness;
3. chip-spawn multiplier + approximately 50% lower default population;
4. MAIN run-length multiplier + approximately doubled underlying default run target while preserving variance;
5. explicit inter-chip connection-is-success semantics.

See `docs/POST_OPTIMIZATION_ROADMAP.md` for details.

## Preserved later inflight evidence — 2026-08-23

A later unpromoted continuation reached 144/144 active tests + 1/1 stress on a terminal-settlement experiment and made several cheap 1200x1200 @ 0.75 repro seeds construct, while the long/fine 1200x6248 @ 0.35 historical fixture remained unqualified because the execution host became severely inconsistent. A separate repeated-render slowdown was also observed in one long-lived Python process.

None of that code is production authority. The exact delta from the promoted renderer/tests is preserved compactly under `work/inflight/line_murder_terminal_followup_*.diff`. Its useful lesson is folded into the paused line-murder task: late settlement may expose symptoms, but anti-line-murder must be achieved proactively during MAIN construction rather than by acceptance, exhaustion-based murder, or whole-board rejection.
