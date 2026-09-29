# Recovery checkpoint — 2026-08-25 14:20 IST

This file was created as the mandatory first substantive action after the preceding run/response was interrupted before a fresh complete handoff could be emitted.

## Authority
- `pcb_v48_renderer.py` remains the authoritative/promoted production renderer.
- The active MAIN-1 work remains under `work/inflight/`; no MAIN-1 candidate has been promoted by this checkpoint.

## Surviving in-flight state
- `work/inflight/main1_future_envelope_fallback_renderer.py` is the future-envelope fallback candidate described in `CONTEXT.md` and `docs/MAIN1_INSTRUMENTATION_AUDIT.md`.
- Durable formal evidence survives under `work/inflight/evidence/main1_future_fallback_formal_2026-08-25_1342IST/`.
- Additional post-formal diagnostic/candidate files also survive under `work/inflight/`, including `main1_future_alt_probe_renderer.py` and `main1_post_hold_current_fallback_renderer.py`; these are NOT promoted production authority.

## Last user-visible qualification status before interruption
- The formal 0.75 gate for the future-envelope fallback had been reported as surviving across seeds 102 + 104, with aggregate candidate MAIN CPU roughly 3.2% lower, rollback segments roughly 16.8% lower, and gesture checks roughly 5.2% lower, with hard counters clean.
- The next governing step was the 0.5 gate. The user-visible run state said `0.5 / seed 102` production was heavy but actively consuming CPU rather than known deadlocked/throwing.
- Raw files created after that message are preserved verbatim in this bundle, but this checkpoint intentionally makes NO new qualification/promotion claim until those records are inspected after packaging.

## Recovery rule
Inspect the preserved raw records only after this bundle exists. Do not infer ACCEPT/PROMOTE from file presence alone. Production remains authoritative unless a complete formal qualification + release/regression gate + explicit promotion is documented.

## Post-preservation findings (14:28 IST)
After the mandatory recovery bundle had been written, the surviving records were inspected. The original future-envelope fallback is rejected at `0.5 / seed 102`; the cached joint-future prototype is not promotable because normalized scaling is slightly worse despite lower absolute CPU; raw-distance is rejected for pathological fine-scale runtime. See `docs/MAIN1_INSTRUMENTATION_AUDIT.md` for the exact formal table.
