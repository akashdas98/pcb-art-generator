# PCB Art Generator V47

Deterministic/probabilistic procedural PCB-style SVG generator with octilinear routing, main chips, component assemblies, residual component fill, and local gap pathways.

## Run

Install:

```bash
pip install -r requirements.txt
```

Generate one sample:

```bash
python pcb_v47_renderer.py --aspect-ratio 1:1 --scale 1.0 --count 1 --out-dir output
```

Whole-sample retry/skip CLI controls have been removed. A requested logical seed is rendered exactly once; construction failures propagate for that exact seed and must be repaired at their causal phase.

## Verify

```bash
python tools/assert_single_canonical_repo.py
python run_release_tests.py
python run_stress_tests.py
```

The active suite is governed by `tests/ACTIVE_TEST_MANIFEST.json`. The current production renderer SHA and open issues are in `CONTEXT.md`.

## Repository map

- `pcb_v47_renderer.py` — production authority.
- `chip_design_language.md` — behavioral source of truth.
- `AGENTS.md` — agent entry point and hard working rules.
- `CONTEXT.md` — current authority, in-flight work, and open issues.
- `CHANGELOG.md` — consolidated current-era project changes.
- `docs/WORKFLOW.md` — NORMAL/NIGHTLY, qualification, evidence-retention, and handoff rules.
- `docs/TESTING.md` — active test architecture and production-acceptance distinction.
- `docs/OPTIMIZATION_HISTORY.md` — compact durable record of the V47 scaling pass and important rejected approaches.
- `docs/POST_OPTIMIZATION_ROADMAP.md` — ordered behavior/CLI work after the scaling pass.
- `tools/assert_single_canonical_repo.py` — **hard anti-multi-worktree / duplicate-canonical-state guard; do not remove or weaken.**
- `tools/build_handoff_bundle.py` — fresh replacement-ready ZIP builder.
- `tools/v47_perf_harness.py` — cheap MAIN routing differential/performance harness.
- `tools/v47_exact_sample_phase_perf_harness.py` — exact logical-sample phase timing harness.
- `tests/active/` — mandatory release tests.
- `tests/stress/` — maintained stress test.
- `work/inflight/` — at most the current coherent unpromoted candidate; currently the paused line-murder V3.
- `examples/` — deliberately tiny current reference set.
- `archive/releases/` — historical source-oriented release snapshots V34–V46.
- `archive/LEGACY_CHANGELOGS_V4_V33.md` — older changelogs consolidated into one file.

## Repository hygiene

Do not commit transient benchmark/forensic output. Raw `bench_results`, `forensics`, `experiments`, acceptance directories, profiler dumps, logs, stdout/time captures, and copied candidate forests belong outside the canonical repo. Preserve durable conclusions in the Markdown history instead.

## Current status

V47 renderer authority is `648a533...`. The 1:1 three-scale optimization qualification remains complete and the active gate is **137/137 + 1/1 stress PASS**. Seed-totality repair is in progress: batch seed skipping and whole-board reseeding are gone; collection-family coverage and component hard-floor completion now recover constructively/local-first. Long/fine totality remains open, and the premature-line-termination V3 candidate remains paused/unpromoted. See `CONTEXT.md`.
