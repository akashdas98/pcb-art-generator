# PCB Art Generator V48

Procedural PCB-style SVG generator with octilinear routing, main chips, component assemblies,
residual component fill, and local gap pathways.

## Use the renderer

If the task is simply to generate PCB art, use the production entry point and stop there:

```bash
pip install -r requirements.txt
python generate_pcb.py --aspect-ratio 1:1 --scale 1.0 --count 1 --out-dir output
```

Optional exact seed:

```bash
python generate_pcb.py --aspect-ratio 1:6 --scale 0.35 --seed 123 --count 1 --out-dir output
```

Optional workload/geometry controls:

```bash
python generate_pcb.py --main-chip-density-multiplier 1.0 --main-run-length-multiplier 1.0 \
  --local-density 1.0 --component-density 0.5898123324396783
```

- `--main-chip-density-multiplier`: `0.2..2.0`, default `1.0` (approximately half historical source density; `2.0` restores historical density).
- `--main-run-length-multiplier`: `0.2..3.0`, default `1.0` (2x historical whole-route MAIN residency; `0.5` restores historical residency). Legal foreign-main-chip connections still complete immediately.
- `--local-density`: `0..1`, default `1.0`. This requests combined post-MAIN visual-service score. `0` leaves the residual field empty.
- `--component-density`: `0..1`, default `0.5898123324396783` (about `0.59`). This allocates the requested post-MAIN service score between component distribution/size and LOCAL line coverage. It is not a physical component-area fraction; SVG metadata also reports actual enclosure and LOCAL areas separately.

The density score combines connected-region component service with measured LOCAL line-and-gap service. These are not both physical area percentages; the separate physical-area fields in SVG metadata make that distinction explicit. A shortfall in either requested service allocation is reported. Exact geometry and clearance remain required. Current qualification status is in [CONTEXT.md](CONTEXT.md).

If `--seed` is omitted, **do not choose a "safe" or reference seed**. Leave it omitted; the
renderer chooses a random base seed. Seeds are inputs, not lottery tickets.

A plain generation request does **not** require or authorize:

- release tests or stress tests;
- seed sweeps or acceptance/qualification runs;
- performance harnesses;
- report generation;
- unrelated source changes.

`generate_pcb.py` writes the requested SVG files only by default. It does not emit standalone
report JSON. Internal renderer invariants still run; an invariant failure propagates for that
exact seed and must not be hidden by reseeding.

See `docs/PRODUCTION_USE.md` for the concise production-use contract.

## Working in the repository

At session startup read [current state and task queue](CONTEXT.md) and [context routing](docs/CONTEXT_ROUTING.md). Load only relevant detail. [AGENTS.md](AGENTS.md) supplies concise agent instructions; [workflow](docs/WORKFLOW.md) covers checkpoints, Git ownership, archive preservation and verification. No ZIP/export or repository-identity guard is required.

Use Git for version history and reviewable changes. Isolated worktrees are allowed with explicit ownership and integration. Preserve previous renderer versions under archive/releases before replacing qualified behavior. Store temporary renders/logs in ignored .scratch/ or an external task directory.

For renderer or active-test-infrastructure changes:

```bash
python run_release_tests.py
```

Use `python run_stress_tests.py` for affected geometry/construction boundaries. Neither command is a generation prerequisite. [Testing](docs/TESTING.md) explains finite regression coverage versus seed totality.

## Repository map

- generate_pcb.py: SVG generation entry point.
- pcb_v48_renderer.py / V48Renderer: installed renderer.
- chip_design_language.md: behavior specification; read relevant sections on demand.
- CONTEXT.md: sole current status, decisions, verification and task queue.
- docs/CONTEXT_ROUTING.md: task-specific context index.
- docs/WORKFLOW.md: sole process source.
- CHANGELOG.md and docs/* history/evidence: dated durable findings, not live queues.
- tests/active and tests/ACTIVE_TEST_MANIFEST.json: active correctness gate.
- tests/stress: maintained geometry stress checks.
- work/inflight: actual unfinished experiments; status lives in CONTEXT.md.
- archive/releases: previous source-oriented renderer versions.
- archive/inflight: inactive experimental sources/evidence.
- archive/project_state: historical context/process snapshots.

Renderer code was not changed by the Codex workflow migration. Current visual issues and retained user decisions are in CONTEXT.md.
