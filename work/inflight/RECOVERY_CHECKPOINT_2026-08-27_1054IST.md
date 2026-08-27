# V48 promotion checkpoint — 2026-08-27 10:54 IST

## Authority

- **PROMOTED / AUTHORITATIVE:** `pcb_v48_renderer.py`
- SHA-256: `03e25cbf3ac46f86dced3822cbfa29e526b576499adacb0cf30684e329cf297d`
- Active release gate: **168/168 PASS**
- Maintained geometry stress: **1/1 PASS**
- Active renderer candidate: **none**

## Exact production recurrence closure

- aspect/scale: `1:6 @ 0.35`
- base seed: `8528317405406420078`
- logical index: `0`
- sample seed: `9409060408987575905`
- fresh from-scratch elapsed: `934.709886597 s`
- result: **PASS; full SVG/report emitted**

Hard final counters:

- visible launches: `4131 / 4131`
- `pathway_main_stalled_side_count = 0`
- `pathway_main_unaccounted_launch_trace_count = 0`
- `pathway_main_short_termination_trace_count = 0`
- `pathway_persistence_horizon_unresolved_trace_count = 0`
- illegal MAIN turn/intersection/overlap/clearance counts = `0`

Evidence:

- `work/inflight/evidence/20260827_exact_seed_replay/run_metadata.json`
- `work/inflight/evidence/20260827_exact_seed_replay/exact_report.json`
- `work/inflight/evidence/20260827_exact_seed_replay/exact_seed_9409060408987575905.svg`
- `work/inflight/evidence/20260827_candidate_qualification/release_gate_168.log`
- `work/inflight/evidence/20260827_candidate_qualification/geometry_stress.log`
- earlier frozen-state proof: `work/inflight/evidence/exact_seed_9409060408987575905_wide_fragment_candidate_check.json`

## Architectural result

The fix is proactive at wide-fragment birth: one physical child lane must establish a bounded ordinary-clearance side-progress future before a >4-lane MAIN recovery cohort below eight modules is allowed to fragment. The trace-level certificate survives later front ownership changes and cannot be visually clipped below eight modules. The general hard MAIN maturity floor remains **four modules**.

## Remaining work

Correctness is closed for this reproduced defect. The ~15m35s long/fine full-board runtime confirms performance optimization remains open and should resume under the existing complexity-led scaling process without weakening seed totality or geometry.
