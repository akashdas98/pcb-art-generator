# V39 → V40 Test Migration Ledger

V40 is a verification/test-architecture release. The renderer algorithm is behavior-equivalent to V39; only non-behavioral authority/class/output labels differ. The active suite contains the current contract. V39 and earlier test files remain in their complete snapshots under `archive/releases/vNN/`.

| V39 failing test | V40 treatment | Intent preserved? |
|---|---|---|
| `test_batch_deadlock_skip_preserves_one_renderer_domain` | Rewritten with a synthetic current-policy `render_batch` fixture; no routing/residual-fill dependency. | Yes |
| `test_bundle_gesture_pathways_are_direct_modular_and_collision_clean` | Reconciled to current hard report invariants and bounded router contracts; ancient seed/64-restart dependency removed. | Yes |
| `test_hard_stops_use_deferred_reroute_before_forced_termination` | Rewritten against controlled real route history; proves scheduling, multi-segment traceback/deep repair, and budget exhaustion ordering. | Yes |
| `test_holistic_connections_loop_guard_and_extended_repair_are_active` | Reconciled to maintained network metrics plus direct deterministic connection-pair and loop-risk fixtures. | Yes |
| `test_secondary_components_keep_main_chip_breathing_room` | Rewritten against the current 42U post-main component candidate gate. | Yes |
| `test_single_sample_invariants` | Rewritten against Phase-A/template preparation, where quotas/scale/fingerprints actually belong; no obsolete `NoPathRenderer`. | Yes |
| `test_two_sample_cross_sample_uniqueness` | Rewritten at the batch fingerprint/template layer with first population registered before second preparation. | Yes |

Additional cleanup: the old active arbitrary-seed test used `max_sample_restarts=64`, which no longer matches production. It was moved to `tests/stress/` and now uses one-attempt + logical-sample skip semantics.
