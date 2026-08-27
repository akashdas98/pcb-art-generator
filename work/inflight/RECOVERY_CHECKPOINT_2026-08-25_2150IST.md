# Recovery checkpoint — 2026-08-25 21:50 IST

- Authoritative production: `pcb_v48_renderer.py`
- SHA-256: `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`
- No active/promoted MAIN-1 candidate.
- Post-21:28 experiments are preserved in `work/inflight/` and documented in `docs/MAIN1_INSTRUMENTATION_AUDIT.md`.
- Connection lifecycle policy changes are rejected.
- Strongest surviving causal evidence: 510/640 no-repair conflict groups recur unchanged next round; existing exact legality/failure caches are already heavily active.
- Cross-round `_future_conflict` memoization approaches are rejected/unqualified; exact round-local cache is behavior-preserving but insufficient.
- Next work: exact event/version-driven reuse or wakeup suppression for unchanged exhausted transactions, with no routing/RNG/legality semantic change.
- Required qualification remains 0.75 then 0.5, seeds 102+104, normalized work/CPU plus full gate; routine 0.35 is forbidden until phase end.
