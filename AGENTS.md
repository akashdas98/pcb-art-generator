# PCB Art Generator — Agent Instructions

This file first routes the task into **PRODUCTION USE**, **REPOSITORY ADMINISTRATION**, or **DEVELOPMENT** mode. Do that routing before running any command. Historical files under `archive/` are evidence only and never override the active root.

## MODE ROUTING — FIRST, BEFORE ANY SAFETY GATE OR TEST

### PRODUCTION USE mode — plain render/generate requests

Enter **PRODUCTION USE** mode when the user asks to use/render/generate with the renderer and does **not** ask to modify, fix, debug, validate, test, benchmark, optimize, audit, qualify, or package the repository.

In PRODUCTION USE mode:

- Run the production entry point directly: `python generate_pcb.py ...`.
- Render exactly the requested aspect ratio / scale / count / seed and then stop.
- If the user omits the seed, **leave it omitted**. Do not substitute a maintained, reference, known-good, or "safe" seed. The renderer chooses a random seed itself.
- **DO NOT run `tools/assert_single_canonical_repo.py`.** The worktree safety gate is a DEVELOPMENT-mode repository-write guard, not a prerequisite for using the renderer.
- **DO NOT run release tests, stress tests, seed sweeps, acceptance checks, performance harnesses, qualification reports, benchmark reports, or handoff builders.**
- **DO NOT run `tools/build_handoff_bundle.py` or create a repository handoff merely because a render was requested.**
- **DO NOT create or modify a worktree/repository copy.** Use the checked-out renderer in place.
- `generate_pcb.py` writes SVG files only by default; do not create standalone report JSON unless the user explicitly asks for reports.
- Internal renderer invariants remain active. If the exact requested/generated seed fails, propagate the renderer error; never hide it by choosing another seed.

For production-use details, read only `docs/PRODUCTION_USE.md` if needed. **Do not read `docs/WORKFLOW.md` merely to generate art.**

### REPOSITORY ADMINISTRATION mode — version-control / repository housekeeping only

Enter **REPOSITORY ADMINISTRATION** mode when the user asks only to administer the already-existing repository state rather than develop or validate it. Examples include `git status`, inspecting history/diffs, staging, committing/amending, tagging, branch/remote housekeeping, fetching/pulling/rebasing/merging existing work, or pushing/syncing to a remote.

In REPOSITORY ADMINISTRATION mode:

- Perform only the requested repository/version-control administration and then stop.
- **DO NOT run `tools/assert_single_canonical_repo.py` merely because Git/repository administration was requested.** The guard is a DEVELOPMENT repository-write safety gate, not a prerequisite for committing or pushing already-existing work.
- **DO NOT run release tests, stress tests, benchmarks, qualification sweeps, or `tools/build_handoff_bundle.py` unless the user separately asks for development/validation/packaging.**
- A pure admin request does **not** trigger DEVELOPMENT handoff/recovery rules.
- Do not silently modify renderer/source/spec content while in this mode. If the task requires a content change, route that work to DEVELOPMENT mode first.
- Do not create an additional Git worktree or duplicate canonical repository as an administrative shortcut. A request specifically to create/move/delete worktrees is not exempt from the project's single-canonical-repository policy; handle it explicitly rather than invoking the DEVELOPMENT guard by default.
- If one user request combines actual code/spec changes with commit/push, the overall request is DEVELOPMENT until those changes are qualified; the final commit/push is merely the administrative tail of that DEVELOPMENT task.

For repository-administration details, read `docs/REPOSITORY_ADMINISTRATION.md` if needed. **Do not read/run the DEVELOPMENT workflow merely to commit or push.**

### DEVELOPMENT mode — content-changing / validation repository work

Enter **DEVELOPMENT** mode only when the user asks to change, fix, debug, test, validate, benchmark, optimize, audit, qualify, package, or otherwise modify renderer/repository content. Pure version-control/repository administration on an already-existing state is REPOSITORY ADMINISTRATION mode, not DEVELOPMENT. The remaining instructions in this file apply to DEVELOPMENT mode unless a section explicitly says otherwise.

## Development startup order

Before changing the renderer, read:

1. `AGENTS.md`
2. `CONTEXT.md`
3. `chip_design_language.md`
4. `docs/WORKFLOW.md`
5. `docs/POST_OPTIMIZATION_ROADMAP.md`
6. `docs/OPTIMIZATION_HISTORY.md` only when historical optimization context is needed

`chip_design_language.md` is the behavioral source of truth. `CONTEXT.md` is the current-state source of truth. `docs/WORKFLOW.md` governs DEVELOPMENT process. `CHANGELOG.md` records durable project changes.

## DEVELOPMENT: single canonical repository — hard invariant

Exactly one writable repository carrying `.pcb_repo_identity.json` may exist in a session.

- Never create or work from parallel Git worktrees, per-turn repository copies, or competing canonical roots.
- Before DEVELOPMENT repository work and before DEVELOPMENT packaging, run `python tools/assert_single_canonical_repo.py`. This command is explicitly **not** run in PRODUCTION USE or pure REPOSITORY ADMINISTRATION mode.
- `tools/assert_single_canonical_repo.py` is the hard executable anti-multi-worktree / duplicate-canonical-state gate. Do not remove, weaken, bypass, or replace it with prose.
- The handoff builder invokes that guard automatically.
- Temporary benchmark outputs may exist outside the repository, but they must not carry `.pcb_repo_identity.json`.

## Authority and candidate discipline

- Production authority is `pcb_v48_renderer.py` / `V48Renderer` unless `CONTEXT.md` explicitly records a promoted replacement.
- Unproven code must not overwrite production authority.
- Keep at most one coherent **active inflight workset** under `work/inflight/`. That workset may contain the primary candidate plus a compact reconstructive patch/test delta when needed to preserve interrupted work, but do not accumulate variant forests. When the workset is promoted or rejected, remove obsolete code after its useful findings are summarized in the durable docs.
- Raw profiler dumps, benchmark JSON streams, acceptance output trees, copied renderer variants, generated logs, and forensic scratch directories are **not canonical repository state**. Keep them outside the repo while working; summarize durable conclusions in Markdown.

## Anti-line-murder construction rule — hard invariant

- Anti-line-murder is a **proactive MAIN construction requirement**, not a late acceptance policy.
- MAIN must use local-space awareness, sibling progression, and future route viability while choosing early/ordinary gestures so a lane does not commonly emerge, take one turn, and immediately box itself into having no legal continuation.
- Reject/replan a bad **local proposal** before committing a doomed state; preserve unrelated valid board work.
- A late embedded/short/dead-end detector is only a regression/assertion guard proving proactive construction failed. It must not legalize the murder after retries, reject the whole board, skip the seed, or trigger a different-seed wheel spin.
- Seed totality and anti-line-murder are complementary: smarter constructive routing prevents the defect; any residual construction bug is repaired at its causal local phase rather than via sample acceptance.

## Renderer-change discipline

- Diagnose the causal design-language violation before implementing a fix.
- Preserve determinism, octilinearity, clearance rules, phase order, and all established behavior unless the user explicitly changes them.
- Do not weaken validation, raise retry budgets, skip failures, or add scale/aspect special cases merely to make a sample pass.
- Renderer behavior changes must update `chip_design_language.md`, `CONTEXT.md`, and the relevant changelog/history entry in the same promoted change.
- Documentation/tooling-only changes must not edit the behavior specification just to create churn.

## DEVELOPMENT: verification

- `python run_release_tests.py` is the mandatory active correctness gate: every test in `tests/ACTIVE_TEST_MANIFEST.json` must be discovered and pass with zero failures, errors, skips, or expected failures.
- `python run_stress_tests.py` is the maintained stress entry point.
- Performance work uses the small harness set in `tools/`; benchmark outputs belong outside the canonical repo.
- See `docs/TESTING.md` for the distinction between the finite active regression gate and the stronger production seed-totality invariant. Never describe a green finite suite or seed sweep as proof that all seeds are valid; any production construction `RuntimeError` reopens correctness.

## DEVELOPMENT: optimization objective

The optimization objective is to make expensive phases scale as close to linearly as reasonably possible with their **relevant generated/useful work**, not merely to reduce one fixed runtime. A constant-factor speedup that leaves or worsens superlinear CPU-per-work scaling is not an optimization success.

During ordinary candidate qualification, test 0.75 then 0.5. Reserve 0.35 for end-of-phase qualification unless a current diagnostic specifically requires it. Any new semantic workload knob must use the already-local/bounded architecture and be judged by CPU growth normalized by the work that knob actually generates.

## DEVELOPMENT: handoffs

Every **DEVELOPMENT-mode** project response must leave a fresh replacement-ready repository bundle. Plain PRODUCTION USE/render requests and pure REPOSITORY ADMINISTRATION requests do not invoke this workflow. Run:

`python tools/build_handoff_bundle.py`

The builder runs the single-canonical-repo guard, packages the current repository, reopens the ZIP, checks integrity and required files, and prints the bundle path and SHA-256. Do not serve an older ZIP as the current state.

### HARD recovery rule after a missed handoff

If any **DEVELOPMENT-mode** run/response ends without successfully producing a fresh complete handoff bundle, then **the first substantive action of the next DEVELOPMENT run is mandatory and fixed**: preserve and package the exact surviving current working state into a fresh complete handoff bundle **before any further implementation, investigation, testing, optimization, renderer change, or other project work**.

- Do not resume the technical task first, even if the previous run ended mid-fix and the next step is obvious.
- The recovery bundle must capture the working tree exactly as it survived, including coherent unpromoted/inflight code.
- The docs in that bundle must clearly distinguish promoted/authoritative state from unpromoted/inflight work and record the latest findings, failures, diagnostics, status, and next step known at that point.
- A previous execution/tool/window limitation that prevented packaging is **not** permission to continue work first in the next run.
- Only after the recovery bundle has been successfully built and verified may technical work resume.

This is a **hard process invariant**, not a best-effort preference. It takes precedence over resuming implementation or NIGHTLY/NORMAL continuation.

The detailed NORMAL/NIGHTLY stopping and checkpoint rules are in `docs/WORKFLOW.md`.
