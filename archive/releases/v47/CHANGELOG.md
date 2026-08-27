# Changelog

This is the compact current-era changelog. Complete historical source snapshots live under `archive/releases/`; older V4–V33 changelogs are consolidated in `archive/LEGACY_CHANGELOGS_V4_V33.md`.

## Promoted — independent seed-totality repair tranche — 2026-08-23

- Promoted the clean 23:19 seed-totality renderer as production authority: SHA-256 `648a53399955fa1c521d718308ea296b6d2c1bc5fb60fd83abe1b027c7f20e7b`.
- Promotion includes removal of batch logical-seed skipping and whole-board reseeding, total local collection-family construction, defect-scaled MAIN preflight repair, and monotonic/local component hard-floor completion.
- This promotion deliberately excludes the later terminal/embedded-lane experiments. Their exact renderer/test deltas are preserved compactly under `work/inflight/line_murder_terminal_followup_*.diff`.
- The proactive anti-line-murder rule is now attached directly to the paused line-murder task: prevent doomed early paths during construction; late detection is assertion-only and may never reject the board, spin another seed, or legalize murder after exhaustion.
- Promotion qualification completed: **137/137 active release tests PASS + 1/1 maintained stress PASS**.

## Unreleased — anti-line-murder architectural clarification — 2026-08-23

- Made the governing anti-line-murder rule explicit: prevention belongs in proactive MAIN route construction, especially emergence/early-gesture proposal selection with local-space, sibling-progression, and future-maneuvering awareness.
- Local candidate proposals may be rejected/replanned before committing a doomed state; unrelated valid work must be preserved.
- Late short/embedded/dead-end detection is an assertion/regression guard only. It may not legalize a murder after exhaustion, reject the board, skip the seed, or trigger whole-sample reseeding.
- Seed totality and anti-line-murder are complementary. Systematic late trapped lanes must be traced back to the causal MAIN planning/proposal failure rather than "fixed" by a broad terminal-rescue or acceptance subsystem.
- No renderer code was promoted by this clarification; the separate line-murder V3 candidate remains paused/unpromoted.

## Unreleased — handoff recovery hardening — 2026-08-23

- Added a non-negotiable missed-handoff recovery invariant to `AGENTS.md`, `docs/WORKFLOW.md`, and `CONTEXT.md`: if a run ends without a fresh verified complete handoff bundle, the **first substantive action of the next run must be to preserve/package the exact surviving working state before any implementation, investigation, testing, optimization, renderer edit, or other project work**.
- The recovery bundle must retain coherent unpromoted/inflight work and clearly distinguish it from promoted authority while recording the latest findings, failures, diagnostics, status, and next step.
- Previous tool/execution/window inability to package is the trigger for this recovery mode, never an exception to it; the rule takes precedence over NORMAL/NIGHTLY continuation.
- Applied the rule immediately on 2026-08-23: a recovery bundle of the surviving unpromoted termination-tail working tree was built before these documentation edits.

## Unreleased — repository normalization — 2026-08-22

- Reorganized the canonical repository around source, active tests, executable guardrails, compact agent documentation, release history, and a tiny example set.
- Removed canonical copies of transient optimization debris: profiler/forensic trees, benchmark JSON streams, acceptance output directories, logs, copied renderer-variant forests, redundant dated status/handoff/manifests, and generated experiment outputs.
- Consolidated durable V47 optimization conclusions into `docs/OPTIMIZATION_HISTORY.md`.
- Preserved `tools/assert_single_canonical_repo.py` unchanged as the hard anti-multi-worktree / duplicate-canonical-state gate.
- Preserved the current unpromoted line-murder V3 candidate exactly at `work/inflight/line_murder_space_replan_v3.py`.
- Moved the single V44 reference-report dependency used by active tests into `tests/fixtures/` and updated the stress probe to import the active V47 renderer instead of relying on a root-level V45 copy.
- Added V45 and V46 source-oriented snapshots to `archive/releases/` and pruned generated example payloads from archived V40–V44 snapshots.
- Replaced repository-mutating handoff metadata/checksum generation with a lean bundle builder that packages/verifies the repository without generating artifact clutter inside it.
- Production renderer bytes unchanged: `8a43f6c2421e67b66f3d83a5f40dc269074a237d63eac2f183a60bad29b3b744`.

## Unreleased — seed-totality repair — 2026-08-22

- Established the production contract `valid canvas + scale + seed -> one deterministic valid board`; final validation is an assertion, not an acceptance filter.
- Removed batch-level logical-seed skipping: `render_batch()` now renders exactly the requested logical indices and propagates a construction defect for that exact seed.
- Removed `generate_sample()`'s outer whole-board restart/reseed loop. Compatibility parameters remain inert at API level while downstream callers migrate.
- Made collection-family quota coverage constructive instead of allowing a cosmetic family-mix draw to invalidate the sample; exhaustive spot coverage over N=15..18 found no assignment failures across 20,000 seeds per N.
- Changed MAIN preflight repair from a fixed 12-transaction whole-board ceiling to a bounded per-observed-defect local budget, and included intersection/clearance/duplicate suppression causes. A real 13-defect regression repairs all 13 locally.
- Removed the arbitrary board-wide component residual filler count as a hard-floor stop. Completion is now bounded by monotonic residual-service-cell retirement, so legal remaining capacity can continue to be serviced without rejecting the seed because a global filler counter expired. A forced zero-cap regression reaches 51.2% rather than stopping near 0.2%.
- Current mandatory gate after these repairs: **137/137 PASS**; maintained geometry stress: **1/1 PASS**.
- Exact historical `1200:6248 @ 0.35`, seed `20260816`, remains unqualified on the current authority: a MAIN-only probe was still running when a 20-minute execution boundary was reached. This is recorded as an unresolved termination/performance-totality issue, not treated as a rejected seed or a success.
- Renderer SHA-256 at this checkpoint: `648a53399955fa1c521d718308ea296b6d2c1bc5fb60fd83abe1b027c7f20e7b`.

## V47 — reconstruction, persistence restoration, locality/scaling optimization — 2026-08-17 through 2026-08-22

- Restored behavior lost/regressed across the V45/V46 transition, including persistent MAIN routing semantics and long/fine population behavior.
- Reworked LOCAL service around physical residual debt, bounded candidate work, certificates, direct-run families, emergency hard-floor cleanup, and spatial locality.
- Reworked MAIN expensive services around incremental rollback, exact-lane geometry reuse, immutable spatial snapshots, proposal replay, failure certificates, and local successful-clearance proof reuse.
- Reworked component placement to gap-first/opportunity-first local service and localized ordinary post-MAIN component retries so valid MAIN routing is not discarded for normal component placement recovery.
- Added phase-lifetime cleanup/rebuildable-state release and bounded/local spatial indexing, reducing peak memory from the earlier ~900 MB class; final 1:1 @ 0.35 canary peak was about 235 MiB.
- Final qualified phase-native CPU/useful-work growth: MAIN ~1.022x (0.75->0.5) / 1.166x (0.5->0.35); LOCAL ~0.997x / ~1.107x; components ~0.949x on the final 0.5->0.35 component-native acceptance.
- Final guarded 1:1 whole-render primitive-normalized CPU/work growth improved from 1.211x to 1.195x over 0.75->0.5 and from 1.180x to 1.147x over 0.5->0.35.
- Final active release gate at optimization closure: 134/134 PASS (the current seed-totality branch has since expanded the active gate).
- Operational caveat discovered after closure: full long/fine production acceptance was not qualified; user later observed 0/8 valid samples at roughly 1:6 @ 0.35. This remains open and is tracked in `CONTEXT.md`.

## V46 — logical viewBox / aspect- and zoom-consistent territory

- Introduced logical-viewBox scaling so aspect extension and zoom share one logical-territory law rather than ad-hoc canvas-specific behavior.
- Expanded fine-scale primary population/detail capacity with normalized territory and made service grids design-unit based.
- Established rotation/aspect invariance tests and long-canvas coverage.
- A persistence/line-termination behavior regression became a major input to V47 reconstruction. See `archive/releases/v46/`.

## V45 — true zoom / logical-area population

- Converted scale from a mostly cosmetic/detail setting into logical-area exposure and population growth.
- Added fine-scale primary population behavior and long/tall canvas validation work.
- See `archive/releases/v45/`.

## V44 and earlier

Source snapshots V34–V44 are under `archive/releases/`. V4–V33 changelog records are in `archive/LEGACY_CHANGELOGS_V4_V33.md`.

### 2026-08-23 — seed-totality termination repair (INFLIGHT, not promoted)
- Replaced remaining mature MAIN persistence rejection for locally exhausted `between_siblings` singletons with local deterministic settlement after transactional repair; no whole-board retry/skip was added.
- Fixed transactional stale-object bug: failed tail repair can restore a new canonical front object; fallback settlement now reacquires that canonical object before mutating status.
- Added final post-topology relational settlement and final commit of debt-free active MAIN fronts, preventing valid launch geometry from disappearing merely because planner state remained `active` after the last topology change.
- Known former rejection repros 1200x1200 @ 0.75 seeds 1/3/7 now construct; release gate 144/144 and stress 1/1 pass.
- Long/fine 1200x6248 @ 0.35 seed 20260816 remains a required uncompleted qualification because the current execution host exhibits severe slowdown even on the unchanged recovery baseline.

- Documentation correction: Item-26 whole-render `BEFORE` is explicitly identified as the Aug-19 late checkpoint, not the start of the optimization run. A same-runtime Aug-18 early-authority vs final-authority 1.0->0.75 reconstruction is recorded in `docs/OPTIMIZATION_HISTORY.md`; do not quote the Item-26 1.211->1.195 / 1.180->1.147 deltas as the full-run gain.
