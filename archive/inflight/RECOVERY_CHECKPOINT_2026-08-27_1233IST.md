# Recovery checkpoint — 2026-08-27 12:33 IST

Status: **PROMOTED / AUTHORITATIVE; no active renderer candidate.**

- renderer: `pcb_v48_renderer.py`
- SHA-256: `4c87378867645aa90727b77ea94e98eb59c6a6f4f993a45cbbf786b5239afc8e`
- active release gate: **175/175 PASS**
- maintained geometry stress: **1/1 PASS**

This promotion closes the 2026-08-27 user-reported stalled-side recurrence plus the systematic MAIN launch behavior audit: delayed fan readiness, synthetic whole-bus turn incentive, fixed-first fan topology, coarse-envelope false fan conflicts, oversized launch cohorts, same-chip/different-side connection exclusion, late-only side-progress debt, and stale sibling fan-rebase turn exemption.

The ordinary hard MAIN line survival floor remains **4 modules**. The separate >=8-module side-progress requirement belongs to at least one physical outcome from each launch side. No safe-seed fallback, whole-board acceptance loop, relaxed clearance, or validator weakening was introduced.

Evidence:
- `work/inflight/evidence/20260827_emerge_spread_qualification/qualification_summary.md`
- `work/inflight/evidence/20260827_emerge_spread_qualification/release_gate_175of175.log`
- `work/inflight/evidence/20260827_emerge_spread_qualification/geometry_stress_1of1.log`
- `work/inflight/evidence/20260827_emerge_spread_qualification/renderer_vs_1055_promoted.diff`
- `work/inflight/evidence/20260827_emerge_spread_qualification/user_error_pcb_render_error_20260827_110209_586.zip`
- three fresh square sample SVGs in the same evidence directory.
