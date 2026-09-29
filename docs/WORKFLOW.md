# Project workflow

## State and resumption

[CONTEXT.md](../CONTEXT.md) is the single current-state source, including the active task, queued tasks, user decisions, implementation status, verification, and next step. Read it and the [routing index](CONTEXT_ROUTING.md) at session startup. Checkpoint after every meaningful change; record incomplete work before ending or switching tasks. Do not duplicate live task status in history/evidence documents.

On resumption inspect surviving relevant files, Git diff/status and any task processes, then reconcile them with the checkpoint. An interrupted command is not a test result. Resume the authorized task from the surviving state. No packaging or missed-response recovery transaction exists.

## Workspace ownership and version history

Use Git for baselines, diffs and provenance. Isolated branches/worktrees are allowed when useful. Identify each worker's target checkout, owned files and integration owner; avoid concurrent edits to the same files and never silently discard user changes. A worktree's existence is not competing production authority.

Before replacing qualified renderer behavior, preserve the preceding version in the existing source-oriented archive/releases pattern with a short history record identifying the revision or exact artifact and reason. Keep earlier archives. Ordinary scoped Git changes are allowed; mark incomplete renderer changes unqualified in current state until verified. Separate experimental candidates may use work/inflight, with their path and baseline recorded only in current state.

Move completed/rejected experiments worth retaining into archive, summarize their findings in durable history, and keep work/inflight for actual unfinished work. Archived instructions and checkpoints are historical evidence only.

## Scope and verification

Finish against the user's requested outcome. Questions, audits, documentation changes and renderer optimizations have different acceptance criteria. There are no NORMAL/NIGHTLY modes, mandatory promotion-per-response rules or exports.

Generation and pure Git administration do not imply testing or source changes. For documentation verify routes and consistency; for tooling/tests verify the affected behavior. Run the complete `python run_release_tests.py` gate for renderer changes and changes to active test infrastructure; discovery must match the manifest with no failures, errors, skips or expected failures. Use `python run_stress_tests.py` for affected geometry/construction boundaries. See [testing](TESTING.md).

For visual work inspect rendered output against the actual requested composition, including neighboring relevant variants. Record technical verification and visual acceptance separately; neither substitutes for the other. Unverified or user-rejected visual work remains open even if correctness tests pass.

Renderer behavior changes synchronize the affected design-language sections and changelog/history. Documentation/tooling changes do not rewrite behavior requirements.

## Optimization and evidence

Optimization must improve scaling toward linear CPU growth with relevant generated/useful work, not merely one fixed runtime. Diagnose the work mechanism, implement a coherent local/bounded correction, preserve routing/RNG/clearance semantics, and compare work growth, CPU growth and CPU/work before qualification. Do not introduce global scans, quadratic dependencies, unbounded retries or whole-sample restarts for local failures.

For ordinary optimization qualification use 0.75 then 0.5; reserve 0.35 for end-of-phase qualification unless a diagnostic requires it. This cadence does not apply to unrelated documentation work. Keep whole-render and phase measurements distinct. Release rebuildable cache state when its phase ends without changing semantics.

Use ignored .scratch/ (or an external task directory) for logs, renders, profiler dumps and benchmark streams. Do not commit generated debris. Preserve reproducible parameters and durable conclusions in history; link evidence needed to resume unfinished work. Git revisions identify source state; use artifact hashes only where exact forensic identity matters. Report actual runner results instead of repeating a manually maintained current test count.
