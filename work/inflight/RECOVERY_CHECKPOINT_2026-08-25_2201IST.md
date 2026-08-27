# Recovery checkpoint — 2026-08-25 22:01 IST

- Authoritative production: `pcb_v48_renderer.py`.
- Production SHA-256: `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`.
- No active/promotable MAIN-1 renderer candidate.
- This checkpoint closes the handoff gap from the preceding response by preserving the method-level timing evidence obtained after the 21:52 bundle.
- Stable proxy: `1:2 @ 0.75 / seed 104`, MAIN-only, about `15.09 s` total MAIN CPU on that pass.
- Dominant inclusive methods: `_proposal_variants` 11.07 s; `_lookahead_adjust` 5.50 s; `_propose` 5.09 s; `_gesture_clear` 4.95 s; `_future_options` 4.94 s.
- Smaller conflict machinery: `_future_conflict` 0.93 s; `_conflict_groups` 0.88 s; `_solve_conflict_group` 0.26 s; conflict-repair scheduling ~0.004 s.
- Prior recurrence evidence remains authoritative: 510/640 exhausted no-repair groups recur with the same front set on the immediately following round.
- Earned next approach: behavior-preserving proposal/lookahead subproof reuse guarded by an exact relevant-local-event/version condition. Reuse must not alter RNG, legality, routing decisions, or seed ownership.
- Qualification rule remains 0.75 then 0.5 on seeds 102+104 with categorized + overall normalized work/CPU and full gate before promotion. Routine 0.35 remains prohibited until phase end.
