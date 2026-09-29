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
- `--local-density 0..1` (default `1.0`): requests combined post-MAIN visual-service score. Component service is based on distribution and size/quantity quotas across connected free-space regions; LOCAL service is based on emitted line-and-designed-gap coverage. `0` emits neither modality.
- `--component-density 0..1` (default `0.5898123324396783`, about `0.59`): allocates that service score between components and LOCAL lines. It is a share of the service score, not a claim that components physically enclose that percentage of the surface.

These are geometry/workload controls only; they do not select alternate routing algorithms or qualification modes. The renderer must report both the combined service result and any component or LOCAL service shortfall.

Reports also give separate physical enclosure/line coverage on the frozen post-MAIN field. Those physical percentages can differ substantially from the visual-service score; neither is to be relabeled as the other. A reported service shortfall means the requested score was not met. Exact geometry and clearance remain required.

If `--seed` is omitted, leave it omitted. The renderer chooses a random base seed. **Do not replace
an omitted seed with a reference, maintained, known-good, or "safe" seed.** Seeds are inputs, not
acceptance lottery tickets; every valid seed is owned by the renderer's construction contract.

## USE-mode contract

For a plain generation request, do exactly the requested render and stop.

Do not run release/stress tests, performance harnesses, seed sweeps, qualification, source edits or report generation unless separately requested. Generate exactly the requested batch in the selected checkout. There is no export or repository-identity prerequisite.

`generate_pcb.py` writes the requested SVG files only. Renderer metadata remains embedded inside the
SVG itself, but no standalone report JSON is emitted by this production entry point.

Construction and final invariants inside `V48Renderer` remain active. If an invariant fails, that
failure belongs to the exact requested/generated seed and must propagate; USE mode must not hide it
by choosing another seed.

## Other work

For changes or analysis load only the relevant routes from [context routing](CONTEXT_ROUTING.md). Current tasks and user decisions are in [CONTEXT.md](../CONTEXT.md); [workflow](WORKFLOW.md) governs changes.
