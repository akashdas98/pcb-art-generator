# V40 Verification Summary

## Status

**PASS — complete active release contract.**

V40 is a verification/test-architecture release. The renderer algorithm is mechanically behavior-equivalent to V39; only non-behavioral authority/class/output labels differ. The active suite contains an explicit source-equivalence test, so the accepted V39 production reference snapshot is inherited for V40. No fresh behavioral renderer change is claimed in this release.

## Authoritative command

```bash
python run_release_tests.py
```

Result on the consolidated repository tree on 2026-08-14:

- active tests discovered: **44**
- passed: **44**
- failures: **0**
- errors: **0**
- skips: **0**
- expected failures / xfails: **0**
- manifest mismatch: **0**
- observed suite runtime after repository-native V39 archival: **2.914 s**

## Reconciliation performed

The seven V39 failures were not deleted. Their still-current behavioral intents were migrated to current fixtures:

1. batch deadlock skip preserves one renderer/batch domain;
2. bundle/network routing remains modular and collision-clean;
3. hard stops schedule recovery and deep traceback before reroute-budget exhaustion;
4. holistic connection pairing, loop rejection, and extended repair remain active;
5. post-main components preserve the 42U main-chip moat;
6. current component-template quotas/scale/fingerprint invariants are tested at the Phase-A/template layer;
7. cross-sample collection fingerprints remain unique in one registered batch domain.

The obsolete `NoPathRenderer` fixture is absent from the active suite. The old 64-restart arbitrary-seed method is absent from the active suite. Historical implementations remain in complete `archive/releases/vNN/` snapshots, outside the release runner's explicit `tests/active/` discovery root.

## Future release protection

`chip_design_language.md` and `TEST_ARCHITECTURE_V40.md` now make test co-evolution normative. A future code/design behavior change must reconcile its affected tests in the same release. `tests/ACTIVE_TEST_MANIFEST.json` must exactly match discovery. A release may not be called a pass unless the complete active runner exits zero.

Optional stress probing is separate (`python run_stress_tests.py`) and is intentionally not part of the release gate; stress results cannot substitute for the active suite.
