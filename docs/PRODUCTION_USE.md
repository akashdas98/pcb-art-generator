# Production Use — Generate and Stop

This document applies when the task is to **use the renderer to generate PCB art**, not to modify,
debug, qualify, benchmark, optimize, validate, or package the repository.

## Canonical production command

```bash
python generate_pcb.py --aspect-ratio 1:1 --scale 1.0 --count 1 --out-dir output
```

Optional exact base seed:

```bash
python generate_pcb.py --aspect-ratio 1:6 --scale 0.35 --seed 123 --count 1 --out-dir output
```

Behavior controls:

- `--main-chip-density-multiplier 0.2..2.0` (default `1.0`): scales the stochastic territory-normalized main-chip population; `1.0` is the new approximately-half-density baseline and `2.0` roughly restores the previous density. The physical population has a hard floor of one main chip per valid board, so low values can saturate at one on small territory.
- `--main-run-length-multiplier 0.2..3.0` (default `1.0`): scales the stochastic whole-route MAIN free-running journey/residency target. It does not override valid inter-chip connections, which remain successful immediately when encountered.
- `--local-density 0..1` (default `1.0`): scales the total post-MAIN residual-service budget shared by components and LOCAL lines. `0` emits neither residual components nor LOCAL lines; `1` is the historical combined residual-fill amount for that seed.
- `--component-density 0..1` (default `0.5898123324396783`, about `0.59`): chooses what share of that residual budget is assigned to components. `0` assigns the budget to LOCAL lines and `1` to components. The nominal default is `0.55 / (0.55 + 0.45*0.85)`, derived from the midpoint of the historical `50–60%` component convention followed by `80–90%` LOCAL of the remainder. At exact defaults the legacy per-seed draws and geometry path are preserved.

These are geometry/workload controls only; they do not select alternate routing algorithms or qualification modes. Residual density requests remain subject to the renderer's exact geometry and clearance rules, so extreme allocations are best-effort density targets rather than permission to relax clearance. The embedded SVG report includes requested and realized combined residual density and component share.

If `--seed` is omitted, leave it omitted. The renderer chooses a random base seed. **Do not replace
an omitted seed with a reference, maintained, known-good, or "safe" seed.** Seeds are inputs, not
acceptance lottery tickets; every valid seed is owned by the renderer's construction contract.

## USE-mode contract

For a plain generation request, do exactly the requested render and stop.

Do **not** run any of the following unless the user separately asks for repository development,
validation, benchmarking, qualification, or packaging:

- `tools/assert_single_canonical_repo.py`;
- `run_release_tests.py`;
- `run_stress_tests.py`;
- performance/acceptance/seed-sweep harnesses;
- `tools/build_handoff_bundle.py`;
- test reports, stress reports, benchmark reports, or handoff reports;
- alternate-seed retries, maintained/reference/safe seeds, or seed shopping.

`generate_pcb.py` writes the requested SVG files only. Renderer metadata remains embedded inside the
SVG itself, but no standalone report JSON is emitted by this production entry point.

Construction and final invariants inside `V48Renderer` remain active. If an invariant fails, that
failure belongs to the exact requested/generated seed and must propagate; USE mode must not hide it
by choosing another seed.

## Development mode is separate

If the user asks to **change, fix, debug, test, validate, benchmark, optimize, audit, or package** the
renderer/repository, then follow `AGENTS.md` development mode and `docs/WORKFLOW.md`. The worktree
safety gate and handoff rules belong there. They are deliberately not part of production use.
