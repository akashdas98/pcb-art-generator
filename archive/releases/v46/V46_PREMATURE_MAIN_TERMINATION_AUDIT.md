# V46 Premature Main-Termination Regression Audit

Status: **V46 release candidate invalid / behavior regression confirmed**.

## Finding

The long `1200:6248 @ scale 0.35` production sample exposes a main-route persistence regression. The regression was introduced in V45's true-zoom performance work and inherited unchanged by V46.

V44 main routing profile:
- `max_rounds = 48..56`
- `persistence_tail_rounds = 12`

V45/V46 main routing profile:
- `max_rounds = 24..28`
- `persistence_tail_rounds = 0`

The V45 change was intended to reduce fine-scale runtime, but it is not behavior-neutral. At the global horizon, mature active main fronts are allowed to terminate locally; remaining same-root/fragment cohorts may be assigned `termination_reason='coordinated_persistence_limit'` rather than receiving the former persistence tail.

This violates the project's no-functionality-loss optimization requirement when it changes the visible frequency of short chip-emergent pathways.

## Evidence from the final V46 long scale-0.35 sample

Report: `acceptance_v46/long_s035/output/pcb_v46_00_report.json`

- main launch traces: `3556`
- termination traces: `2398`
- coordinated-persistence-limit terminal traces: `2094`
- short traces (<3 rendered segments): `516` (`14.51%`)
- hard main-short-terminal counter: `0`
- stalled-side counter: `0`

The latter two counters do **not** protect the intended visual behavior:
- `pathway_main_short_termination_trace_count` only rejects terminated main traces **below** the 4-module hard survival floor; a trace ending at exactly 4 modules is legal to that test.
- `pathway_main_stalled_side_count` is side-level: it only requires at least one lane on a fully terminated chip side to reach 8 modules. It does not prevent several sibling lanes on that side from ending at/near the 4-module floor.

Direct SVG measurement of the same accepted sample found 31 non-frame-ending main-chip polylines at essentially exactly 4 routing modules. This matches the user's visual observation of chip-emergent lines being killed very early.

## Test-suite coverage defect

The active V46 test `test_holistic_connections_loop_guard_and_extended_repair_are_active` checks `persistence_tail_rounds == 12`, but obtains that value from `examples/V44_REFERENCE_REPORT.json` through `_reference_report()`. It does not assert the live V46 planner profile. Therefore the suite can pass while V46 actually runs with `persistence_tail_rounds == 0`.

This contradicts the active manifest's stated rule that historical V44/V45 reports may not satisfy a V46 release gate.

## Required correction

Do not weaken the 4-module hard survival floor or the 8-module side-progress rule. Instead restore the intended persistence/exploration behavior without reintroducing global superlinear work:

1. Remove the V45 24..28/zero-tail shortcut as an acceptance-preserving performance mechanism.
2. Re-express persistence as local/family-local work so larger logical territory creates more independent persistence work rather than a board-global tail transaction.
3. Preserve the documented parallel launch / joint arbitration behavior.
4. Add live V46 tests for the actual planner profile and, more importantly, distributional/production guards against a renewed mass of 4-module main terminals.
5. Re-run full behavior, equivalence, and long scale-0.35 production/performance acceptance before release.

No renderer behavior has been modified by this audit document; it records the confirmed failing state for the next correction pass.
