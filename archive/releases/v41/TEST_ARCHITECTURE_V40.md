# V40 Test Architecture — Normative Release Contract

V40 repairs the test-maintenance debt discovered in V39. Tests are part of the renderer contract, not an append-only historical archive.

## Suite layout

- `tests/active/` — current, bounded, release-gating tests. Every discovered test is mandatory.
- `tests/ACTIVE_TEST_MANIFEST.json` — exact list of active tests and the behavior each protects. Discovery and manifest must match exactly.
- `tests/stress/` — optional multi-seed probes (files are deliberately not named `test_*.py`). They may be slower, but they must use current production execution semantics; they are not substitutes for active contract tests.
- `archive/releases/vNN/` — complete immutable historical release snapshots, including their original test implementations. The release runner discovers only `tests/active/`, so archived `test_...` files cannot be mistaken for current contracts.
- `run_release_tests.py` — the authoritative release command.

## Hard rules for every future renderer version

1. **Tests change with behavior.** Any renderer/code/design-language change that alters a behavior, parameter, invariant, phase order, fixture assumption, or execution policy must reconcile the tests covering that behavior in the same version.
2. **No stale carry-forward.** A test whose fixture or assertion no longer represents the current architecture may not remain in `tests/active/` merely because it used to pass. Its still-valid intent must be migrated first; only genuinely superseded intent may be retired.
3. **No silent deletion.** Removing or materially weakening an active test requires a migration-ledger entry stating whether its intent was superseded or where it is re-covered.
4. **Full active suite is the release gate.** A renderer may not be called a pass, successful build, verified release, or new baseline unless `python run_release_tests.py` exits 0.
5. **Zero exceptions inside active.** Active release tests allow no failures, errors, skips, expected failures/xfails, or ignored test methods.
6. **Targeted tests are additive, not a substitute.** Version-specific new tests may be run during development, but they do not replace the complete active release suite.
7. **Historical/stress suites are explicit.** Historical tests are non-discoverable archives. Stress tests are separately named and cannot be cited as proof that the active suite passed.
8. **Production-policy fidelity.** Active fixtures must use current execution semantics. Old retry/search behavior may not be resurrected just to make a test pass.
9. **Behavior-only snapshot inheritance is exceptional.** A prior accepted production snapshot may be inherited only when the new renderer is mechanically proven behavior-equivalent to the prior renderer. V40 does this with `test_v40_renderer_is_behavior_equivalent_to_v39`. Any future behavioral code change invalidates that inheritance and requires a fresh production acceptance snapshot.
10. **Manifest exactness.** Adding/renaming/removing an active test without updating `tests/ACTIVE_TEST_MANIFEST.json` fails the release runner before tests execute.

## V40 migration outcome

The seven V39 failures were not discarded. Their live intents were migrated to current bounded fixtures:

- batch deadlock skip / one renderer domain → synthetic `render_batch` fixture;
- bundle routing / collision-clean geometry → maintained acceptance contract + current hard-geometry counters;
- hard stop / deferred reroute / deep repair → controlled live planner history;
- holistic connections / loop guard / extended repair → maintained contract + bounded pairing/loop checks;
- component-chip breathing room → direct current candidate-clearance gate;
- single-sample component invariants → current Phase-A/template fixture;
- cross-sample uniqueness → current batch fingerprint domain at template stage.

The old 64-restart arbitrary-seed probe was also removed from the active suite and replaced by a production-policy stress probe in `tests/stress/`.

## V41 application of the snapshot rule

V41 changes renderer behavior in escaped-trace materialization, so the V40 `test_v40_renderer_is_behavior_equivalent_to_v39` gate is no longer an active test and V39 acceptance artifacts are not inherited. V41 ships fresh reference/difficult snapshots, and the active suite points to the fresh V41 reference report. The removed V40 equivalence test remains preserved in `archive/releases/v40/` as historical evidence; its intent is superseded by the explicit fresh-snapshot branch of rule 9 rather than silently deleted.
