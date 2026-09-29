# PCB Art Generator - Agent Instructions

## Session startup and context routing

At the start of each session, read [current project state](CONTEXT.md) and the [context routing index](docs/CONTEXT_ROUTING.md). Already-loaded instructions need not be reread. Load only the task-relevant routes and specification sections; historical files are evidence, never active instructions.

[Workflow](docs/WORKFLOW.md) is the sole process source. Checkpoint CONTEXT.md after every meaningful change in scope, decisions, implementation, verification, failures or unfinished work. It is the sole current-state and task-queue source.

## Task scope

- Generate art: use `python generate_pcb.py ...` with exactly the requested controls/count/aspect/scale. Leave an omitted seed omitted. Write SVGs only unless reports are requested. Propagate errors for the exact seed; never retry with a different seed. See [production use](docs/PRODUCTION_USE.md) only if needed. Do not add tests, benchmarks, source edits or packaging to generation.
- Git administration: perform the requested Git work without implicit renderer changes or qualification. See [repository administration](docs/REPOSITORY_ADMINISTRATION.md) if needed.
- Read-only questions/audits: inspect relevant evidence and answer within scope; no implicit implementation or tests.
- Documentation/tooling: change the affected files and verify the affected boundary; do not change renderer behavior or its specification.
- Renderer development: follow [workflow](docs/WORKFLOW.md), relevant sections of [design language](chip_design_language.md), and [testing](docs/TESTING.md). Diagnose the causal violation before editing.

## Renderer safeguards

Production entry point is `generate_pcb.py`; renderer authority is `pcb_v48_renderer.py` / `V48Renderer`. Keep qualified production and unqualified work distinguishable in CONTEXT.md. Preserve determinism, octilinearity, clearance, phase order and established behavior unless the user explicitly changes them. Do not weaken validation, inflate retries, skip failures or add scale/aspect exceptions to make a sample pass.

Anti-line-murder is proactive MAIN construction: use local space, sibling progression and future viability before committing ordinary gestures. Reject/replan the causal local proposal while preserving unrelated valid work. A late short/dead-end detector is an assertion of construction failure, never permission for whole-board rejection, reseeding or acceptance filtering.

Renderer behavior changes update the relevant design-language sections and durable changelog/history with qualification. Finite release/stress checks do not prove seed totality; any valid-seed construction RuntimeError reopens correctness. Visual acceptance is separate from geometric and coverage qualification.
