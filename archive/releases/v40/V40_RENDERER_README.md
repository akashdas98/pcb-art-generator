# V40 Renderer

V40 is a verification-architecture release built on V39. The renderer algorithm is behavior-equivalent to V39; only non-behavioral authority/class/output labels differ. The purpose of V40 is to make the active test contract coherent, current, and mandatory.

## Generate

```bash
python pcb_v40_renderer.py --width 1200 --height 1200 --count 1 --out-dir v40_output
```

All normal V39 arguments remain available, including `--seed`, `--main-scale`, logical-sample limits, and deadlock-skip controls.

## Authoritative release test

```bash
python run_release_tests.py
```

A release is not a pass unless that command exits 0. It validates the exact active-test manifest and rejects failures, errors, skips, and expected failures.

## Test layout

- `tests/active/`: mandatory current contract.
- `tests/ACTIVE_TEST_MANIFEST.json`: exact active test set and intent map.
- `tests/stress/`: optional current-policy multi-seed probes, not release gating.
- `archive/releases/vNN/`: complete historical releases, including their original tests; excluded from active discovery.
- `TEST_ARCHITECTURE_V40.md`: normative maintenance/release rules.
- `TEST_MIGRATION_V39_TO_V40.md`: reconciliation of the seven V39 failures.

Because V40 is behavior-equivalent to V39, the accepted V39 reference SVG/report remain the production acceptance snapshot for this verification-only release. Any future renderer behavior change invalidates that inheritance and must ship a fresh snapshot.
