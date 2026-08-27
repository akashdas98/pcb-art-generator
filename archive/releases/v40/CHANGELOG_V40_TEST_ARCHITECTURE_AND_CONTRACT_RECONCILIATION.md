# V40 — Test Architecture and Contract Reconciliation

V40 changes **verification architecture only**. `pcb_v40_renderer.py` is mechanically behavior-equivalent to archived V39 apart from non-behavioral authority/class/output labels; the active suite asserts this equivalence.

## Why V40 exists

V39 shipped seven active-looking tests whose fixtures/methodology no longer matched the current renderer, while the behaviors they intended to protect were still relevant. Earlier verification summaries had adopted targeted release gates, which allowed stale tests to accumulate without being reconciled.

## V40 corrections

- Rebuilt the seven failing tests around current architecture rather than deleting their intent.
- Removed `NoPathRenderer` from the active suite.
- Removed old fixed-seed / 64-restart whole-board grinding from the active release suite.
- Preserved historical implementations in complete `archive/releases/vNN/` snapshots; the release runner discovers only `tests/active/` and cannot treat archived tests as current.
- Added `tests/stress/` for optional multi-seed probing using current one-attempt + skip semantics.
- Added exact `tests/ACTIVE_TEST_MANIFEST.json`.
- Added authoritative `run_release_tests.py`; release fails on any failure/error/skip/expected-failure or manifest mismatch.
- Added `TEST_ARCHITECTURE_V40.md` and `TEST_MIGRATION_V39_TO_V40.md`.
- Added V40 normative design-language rules requiring tests to co-evolve with every code/design change.

## Migrated V39 failures

All seven live intents remain covered: batch skip/domain preservation; bundle/network hard geometry; hard-stop deferred reroute/deep traceback; holistic connections/loop guard/repair; 42U component-chip breathing room; current component-template invariants; and cross-sample fingerprint uniqueness.
