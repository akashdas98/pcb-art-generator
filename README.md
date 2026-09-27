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
- `--local-density`: `0..1`, default `1.0`. This scales the **combined post-MAIN residual-fill budget** (components + LOCAL lines). `0` leaves post-MAIN residual gaps empty; `1` requests the renderer's historical total residual-fill amount for that seed.
- `--component-density`: `0..1`, nominal default `0.5898123324396783` (about `0.59`). It splits that combined residual budget between components and LOCAL lines: `0` allocates it all to LOCAL, `1` all to components. The default is the midpoint-convention component share `0.55 / (0.55 + 0.45*0.85)`. At the exact two defaults the renderer takes a legacy fast path, preserving the historical seeded `50–60%` component target followed by `80–90%` LOCAL of the remainder.

Shared residual composition distributes varied component pockets and LOCAL groups across the post-MAIN field. Default mixed LOCAL retains its hard 80% remainder floor. Reduced density floors scale with `local_density`; only full-density all-LOCAL uses best-effort 80% with true shortfall reporting. See [distribution qualification](docs/RESIDUAL_CLUSTER_DISTRIBUTION.md).

Density knobs are target/budget controls, not clearance overrides. At extreme mixes the existing component/LOCAL grammar can under-realize a requested target; metadata reports both the requested residual budget and the actual realized total/share.

If `--seed` is omitted, **do not choose a "safe" or reference seed**. Leave it omitted; the
renderer chooses a random base seed. Seeds are inputs, not lottery tickets.

A plain generation request does **not** require or authorize:

- the worktree/canonical-repository safety gate;
- release tests or stress tests;
- seed sweeps or acceptance/qualification runs;
- performance harnesses;
- report generation;
- handoff bundle generation.

`generate_pcb.py` writes the requested SVG files only by default. It does not emit standalone
report JSON. Internal renderer invariants still run; an invariant failure propagates for that
exact seed and must not be hidden by reseeding.

See `docs/PRODUCTION_USE.md` for the concise production-use contract.

## Repository administration vs development

Pure version-control/repository housekeeping on an already-existing state—status/diff/history, staging, commit/amend, tags/branches/remotes, fetch/pull/rebase/merge, push/sync—is **REPOSITORY ADMINISTRATION** mode. It does not invoke the DEVELOPMENT worktree guard, tests, stress, benchmarks, or handoff builder merely because Git administration was requested. See `docs/REPOSITORY_ADMINISTRATION.md`.

Only when the task is to change, fix, debug, validate, test, benchmark, optimize, audit, qualify, package, or otherwise modify repository content should an agent enter DEVELOPMENT mode and follow `AGENTS.md` plus `docs/WORKFLOW.md`.

Development verification commands are:

```bash
python tools/assert_single_canonical_repo.py
python run_release_tests.py
python run_stress_tests.py
```

These commands are **not prerequisites for production rendering**.

## Repository map

- `generate_pcb.py` — canonical production-use entry point: render requested SVGs and stop.
- `pcb_v48_renderer.py` — production renderer implementation / `V48Renderer` authority.
- `docs/PRODUCTION_USE.md` — production-use contract; no tests/gates/handoffs.
- `docs/REPOSITORY_ADMINISTRATION.md` — pure Git/repository housekeeping contract; no automatic DEVELOPMENT guard/tests/handoff.
- `chip_design_language.md` — behavioral source of truth.
- `AGENTS.md` — PRODUCTION USE / REPOSITORY ADMINISTRATION / DEVELOPMENT mode router plus DEVELOPMENT instructions.
- `CONTEXT.md` — current authority and durable project state.
- `CHANGELOG.md` — consolidated current-era project changes.
- `docs/WORKFLOW.md` — DEVELOPMENT-only NORMAL/NIGHTLY, qualification, evidence, and handoffs.
- `docs/TESTING.md` — DEVELOPMENT test architecture.
- `docs/OPTIMIZATION_HISTORY.md` — compact durable optimization history.
- `docs/LONG_FINE_PERFORMANCE_AUDIT.md` — long/fine scaling diagnosis/history.
- `tools/assert_single_canonical_repo.py` — DEVELOPMENT anti-multi-worktree / duplicate-canonical-state guard; not a pure repository-administration prerequisite.
- `tools/build_handoff_bundle.py` — DEVELOPMENT replacement-ready ZIP builder.
- `tests/active/` — mandatory DEVELOPMENT release regressions.
- `tests/stress/` — maintained DEVELOPMENT stress test.
- `work/inflight/` — DEVELOPMENT-only unpromoted work area.
- `examples/` — deliberately small reference set.
- `archive/releases/` — historical source-oriented releases.

## Current production status

V48 production authority is `pcb_v48_renderer.py`. The seed-total construction contract forbids
whole-sample skipping/reseeding. The historical `pair_chip_isolated` component↔chip clearance bug
has been fixed by conservative construction-time clearance certificates plus an exact phase-local
audit. The current authoritative renderer SHA and full qualification history are in `CONTEXT.md`.
