# Workflow and Optimization Governance

> **DEVELOPMENT MODE ONLY.** This workflow applies only when the user asks to change, fix, debug, test, validate, benchmark, optimize, audit, qualify, or package the repository. A plain request to **use/render/generate** with the renderer is PRODUCTION USE mode: run `python generate_pcb.py ...` and do **not** run this workflow, the worktree guard, tests/stress, seed sweeps, reports, or the handoff builder. A request only to inspect, commit, or push an already-existing working tree is REPOSITORY ADMINISTRATION mode and likewise does not invoke this workflow, the guard, tests, or handoff builder. See `AGENTS.md` for routing and `docs/PRODUCTION_USE.md` for rendering.

## 1. One canonical writable repository

The project uses exactly one canonical writable repository per session. The repository identity is stored in `.pcb_repo_identity.json`.

Run `python tools/assert_single_canonical_repo.py` before DEVELOPMENT repository work and before DEVELOPMENT handoff. Do not run it for PRODUCTION USE rendering or REPOSITORY ADMINISTRATION of an already-existing working tree. The guard fails if Git reports parallel worktrees or if another directory under `/mnt/data` carries the same durable repository identity. This is deliberately executable because accidental parallel state previously caused authority contamination. **Do not remove or weaken this guard for DEVELOPMENT work.**

Temporary benchmark/output directories must live outside the canonical repo and must not copy the repository identity file.

## 2. Evidence-retention policy

Canonical repo state is for durable source and durable knowledge, not every intermediate artifact.

Keep in the repository:

- production source/spec;
- active tests and a very small number of maintained harnesses;
- hard guardrails whose correctness cannot safely rely on prose;
- current state/process/history Markdown;
- historical release source snapshots;
- very few useful reference examples;
- at most the coherent current unpromoted candidate.

Do not keep in the repository:

- profiler dumps;
- raw benchmark/acceptance JSON forests;
- stdout/time/log captures;
- dozens of renderer copies;
- per-turn status/handoff/manifests;
- generated SVG batches used only for one experiment;
- forensic scratch trees.

When an experiment ends, copy its meaningful measurements, decision, and rationale into the appropriate durable Markdown and delete the transient work products from canonical state.

## 3. NORMAL mode

NORMAL is default.

- Work through the current causal stage until one meaningful candidate has completed required adjacent-scale/behavior validation, normalized BEFORE/AFTER scaling reporting, complete active release gate, and explicit ACCEPT/PROMOTE.
- A rejected candidate, failed profiler, timeout, or merely identified next step is not a meaningful stop boundary if another evidence-backed path remains.
- After one meaningful validated promotion, synchronize `chip_design_language.md` when behavior changed, `CONTEXT.md`, `CHANGELOG.md`/history as appropriate, build the fresh handoff ZIP, and report.
- If the current stage is genuinely exhausted with no defensible next causal target, record that conclusion and stop without inventing more work.

## 4. NIGHTLY mode

NIGHTLY is active only when the user explicitly requests NIGHTLY/overnight/continue-as-much-as-possible execution for that run.

- Do not stop after the first promotion; continue through earned targets while the whole active phase remains unfinished.
- Internally retain stage discipline: once a stage has enough evidence to answer its question, move immediately to the next earned stage rather than over-investigating.
- Checkpoint durable current state after every promotion and after costly coherent unpromoted states that would be expensive to reconstruct, but checkpointing does not itself authorize stopping.
- Candidate rejection, command timeout, profiler failure, execution-window boundary, or one exhausted subtarget is not a voluntary NIGHTLY stop condition.
- NIGHTLY self-stops only when the entire active optimization phase is demonstrably complete or the user interrupts.

## 5. Optimization method

Primary objective: fix scaling, bringing expensive phases close to linear CPU growth with **relevant useful/generated work** while preserving behavior.

For each target:

1. identify the actual work-generation mechanism or duplicated/global dependency;
2. decide RETAIN / MODIFY / REPLACE / REMOVE at the approach level;
3. implement the smallest causal change earned by evidence;
4. validate behavior/correctness first;
5. compare normalized work growth, CPU growth, and CPU-per-work growth;
6. reject constant-factor wins that leave the scaling curve unchanged or worse when scaling is the target;
7. run the full active release gate before promotion.

Do not hotspot-chase merely because a function is expensive. Do not over-design future architecture before the current stage has answered its question.

## 6. Scale cadence

Ordinary candidate work:

1. 0.75 — run and record;
2. 0.5 — run and record;
3. do not routinely run 0.35.

At the end of a full optimization phase, qualify separately and sequentially at 0.75, 0.5, then 0.35. A current diagnostic can explicitly justify a different fixture when the bug itself lives outside that cadence.

Every meaningful scaling report should distinguish:

- relevant Work Growth;
- CPU Growth;
- CPU / Work Growth;
- behavior/correctness deltas;
- whole-render/aggregate data versus phase-native metrics.

## 7. Memory/lifetime rule

Release rebuildable spatial/cache state when a phase no longer needs it and rebuild later only when required. Do not keep entire-board transient structures resident merely for convenience. Memory optimization must not alter geometry or generation semantics.

## 8. Semantic knobs

Future chip-count/run-length controls are workload controls, not permission to undo the optimized architecture.

- More requested work may legitimately take more total time.
- They must not reintroduce board-wide scans, quadratic cross-products, unbounded retry expansion, or whole-sample restarts for local recoverable failures.
- Judge scaling by CPU per relevant generated work at representative knob extremes.

## 9. Packaging transaction

Every user-facing **DEVELOPMENT-mode** project response must ship a fresh replacement-ready bundle. Plain PRODUCTION USE rendering does not create a handoff:

`python tools/build_handoff_bundle.py`

The builder invokes the single-canonical-repo guard and verifies the ZIP after writing it. No stale ZIP may be served as the current handoff.

### 9.1 HARD missed-handoff recovery invariant

If a run/response ends without successfully producing that fresh complete bundle, the next run enters **handoff-recovery mode before all other project activity**.

The mandatory order is:

1. **Do not resume implementation, investigation, profiling, testing, optimization, renderer edits, or other technical work.**
2. Preserve the exact surviving current working state, including coherent unpromoted/inflight changes.
3. Ensure current-state documentation distinguishes authoritative/promoted code from unpromoted/inflight code and records all latest findings, failures, diagnostics, status, and next steps known from the interrupted run.
4. Run the single-canonical-repository guard.
5. Build and verify a fresh complete handoff bundle from that exact state.
6. Only after the recovery bundle exists and verifies successfully may project work continue.

This rule is **non-negotiable and higher priority than NORMAL/NIGHTLY continuation**. A prior tool timeout, execution-window cutoff, packaging failure, or other inability to create the bundle does not waive the rule; it is precisely what triggers it. The next run must not accumulate additional uncheckpointed work before recovery packaging.
