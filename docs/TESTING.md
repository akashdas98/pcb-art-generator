# Testing and Production Qualification

> **DEVELOPMENT MODE ONLY.** Do not run release/stress tests for a plain request to use or generate with the renderer. Production use is `python generate_pcb.py ...` and stops after rendering.

## Active release gate

`python run_release_tests.py`

- Discovers only `tests/active/`.
- Discovered test names must exactly equal `tests/ACTIVE_TEST_MANIFEST.json`.
- Zero failures, errors, skips, expected failures, or xfails.

`python run_stress_tests.py` runs the maintained geometry stress entry point.

Historical tests under `archive/releases/` never participate in the active gate. The manifest and discovered suite determine the current test count; documentation does not pin a count.

Focused workflow regressions check that active context links resolve inside the project, current-state routers point to `CONTEXT.md`, and retired workflow artifacts are absent. These checks constrain repository architecture rather than exact instruction wording. Renderer generation contracts remain independent of those routing checks.

## Performance harnesses

- `tools/perf_harness.py` — cheap MAIN differential/performance screening.
- `tools/exact_sample_phase_perf_harness.py` — exact logical-sample phase timing.

Raw output belongs in ignored .scratch/ or an external task directory; durable conclusions go into Markdown history.

## Seed-totality regression coverage

The production contract is not an acceptance percentage: **every valid requested seed is its own board**. Local candidate proposals may be rejected/replanned; whole logical samples may not be discarded in favor of another seed.

V48 adds forced regressions that deliberately exhaust former stochastic budgets and require constructive recovery for chip generation, chip placement, collection planning/calibration, component placement, gesture-budget accounting, and LOCAL hard-floor debt completion.

A green active release gate proves only that the checked-in finite regression contract passes. It does **not** prove that every possible seed has been enumerated or that production seed totality may be inferred from a pass percentage. Deterministic seed probes and maintained stress runs are additional regression/fuzz evidence, not a substitute for the production invariant.

The production rule is stronger than the suite: **any construction `RuntimeError` for any valid requested or renderer-generated seed is a correctness defect and automatically reopens seed-totality work.** It must be diagnosed and repaired at its causal construction phase; it may not be hidden by reseeding, safe-seed substitution, sample rejection, or an acceptance-rate claim.
