# V35 Verification Summary

## Scope

This release verification targets the V35 changes requested after V34: correct `/1600` scale semantics without a second 0.75 multiplier, canvas-gated anchor population, genuine main-route recovery, honest visible local-line service with real perimeter, substantial-region component capacity, gap-aware component size/quantity, and hard no-90°/no-curved-path/no-overlap invariants.

This document does **not** claim that the complete legacy unittest aggregate was run to completion. The targeted current-release gates below were completed individually or in bounded groups.

## Source/reference run — seed 20260806

Command:

```bash
python pcb_v35_renderer.py --seed 20260806 --count 1 --out-dir /mnt/data/v35_release_ref
```

Observed wall time after final connection/preflight hardening: **34.57 s**.

Key report values:

- canvas: 1200×1200
- main chips: **2**
- `chip_count_probability_3`: **0.0**
- design scale basis: **1200**
- design unit divisor: **1600** (`U=0.75`)
- required chip-chip clearance: **322.5**
- measured chip-chip clearance: **377.9983**
- main launch traces: **71**
- visible main launch traces: **71/71**
- cross-chip connections: **8**
- causal tracebacks: **158**, removing **236** committed segments
- visible local gap traces: **103**
- local target: **41.3305%**
- honest visible local stroke+perimeter service: **41.3788%**
- direct 90° pathway turns: **0**
- curved pathway primitives: **0**
- unmarked pathway overlaps: **0**
- static pathway intersections: **0**
- substantial component regions: **55**
- optional thin/sliver residual regions: **105**
- component target: **92.8891%**
- substantial-region component service: **94.5746%**
- total components after gap fill: **87**
- gap-size component counts: large **18**, medium **32**, small **15**, micro **2** (remaining components are established/pre-generated component population)
- mean spans for gap-sized classes: large **39.71**, medium **24.68**, small **16.68**, micro **3.67** canvas units
- unauthorized component/pathway overlaps: **0**
- component unplaced count: **0**

The exact SVG from this run was rasterized and visually inspected. It shows two separated main chips, a substantially denser distributed local-line field, components of visibly varied scale in residual rooms, and intentional negative space in some awkward pockets. No gross 90°/curved-route/overlap regression was observed.

## Difficult routing/fill regression — base seed 15186978462388109083

Direct `generate_sample(0, max_sample_restarts=1)` after final connection/preflight hardening completed in **39.32 s**.

- main chips: **2**
- main launch survival: **93/93**
- cross-chip connections: **8**
- causal tracebacks: **209**, removing **438** committed segments
- visible local filler traces: **120**
- local target: **41.1139%**
- honest local service: **41.1492%**
- direct 90° turns: **0**
- curved pathway primitives: **0**
- unmarked pathway overlaps: **0**
- static pathway intersections: **0**
- substantial component regions: **61**
- optional residual sliver regions: **126**
- component target: **92.5398%**
- component service: **93.4462%**
- components: **81**
- unauthorized component/pathway overlaps: **0**

This validates that thin/fragmented residual pockets no longer make the 90% component target pathological while substantial rooms remain size×quantity constrained.

## Targeted tests completed

Fast architecture/regression group:

```text
5 tests — scale/population, replay-corridor traceback, cached component keepouts,
component failure never reroutes — PASS (0.790 s)
```

Transactional/source-egress group:

```text
10 tests — root emergence traceback, insertion-order invariant joint conflicts,
no sequential winner fallback, causal blocker rollback, protected source egress,
root traceback reactivation, same-family atomic HOLD, foreign-head visibility,
frame clipping — PASS (0.008 s)
```

Additional gates:

- `test_routes_before_secondary_components_exist` — PASS
- `test_main_scale_is_independent_of_canvas_size` — PASS
- `test_hard_stops_use_deferred_reroute_before_forced_termination` — PASS (27.503 s)
- `test_v35_space_aware_causal_contract` — PASS (27.665 s)

The V35 contract checks, among other things: default scale semantics, two-chip default population, main-chip spacing, cross-chip connectivity, zero stalled sides, complete main launch survival, independent local birth, 50% temporary local bundling parameter, ≥40% honest local service, ≥90% component service, and zero illegal turns/curves/pathway overlaps/component-path overlaps.

## Determinism check

The reference seed `20260806` was rendered in two fresh processes. The report JSON and SVG were byte-identical:

```text
report SHA-256: 20b0cbf9d4c687979aa5fd9458bbc51897d08ff7b7f25a27a338f6ae7211c1cd
SVG SHA-256:    12c6d9e6b54d2ab86f3d3dde542794aa33c71c088c3423987d7f4aec38b216d3
```

## Historical-file audit

All **42** pre-V35 changelog / verification-summary / execution-audit files present in the released V34 package were compared against the V35 release tree and are byte-identical. No historical release record was rewritten.

## Late long-tail hardening before final package gate

A random default-package run exposed a >180 s logical-sample skip chain. Reproducible seed sweeps isolated three late rejection seams that were fixed before final packaging:

- base seed `8418061797062126226`: one otherwise-valid main child produced a shared-prefix compensating tail. V35 now performs real rollback/regrowth first, restores state if that fails, and may terminate at the already-long grammar-clean inherited prefix checkpoint. The seed now completes with **87/87** main launches, **41.31%** honest local service, **93.71%** component service, and zero zigzag cleanup.
- base seed `3869344152219641869`: an escaped shared-prefix child hit the same failed-repair state leak. After the state-safe prefix-checkpoint fallback it completes instead of discarding the board.
- base seed `166046635469616812`: a connected singleton retained a non-zero cohort offset; the junction leg was planned in physical coordinates but appended to the offset centreline, creating a tiny final 90-degree kink after materialization. V35 now rebases such a singleton to its exact materialized head before connection. This seed completes in **33.83 s** with zero illegal turns and **93.14%** component service.

The same seed also exposed that final `collection_core_fraction` validation was re-evaluating bounded 90/82/75% gap-fit instance scaling as though it changed the source collection language. Source collection scale/quota validation is now authoritative pre-route; explicit per-gap adaptation no longer causes a late whole-board rejection.

A default skip-path regression using base seed `8310590520830183946` skipped cheap-invalid logical sample 0 and emitted logical sample 1 in **28.31 s**.

Additional fast tests added and passed:

- terminal connection leg rejects a visible 90-degree continuation;
- non-zero-offset singleton rebases to the exact materialized head without changing its visible prefix;
- default `/1600` scale and canvas-gated two-chip rule;
- rollback-junction replay-direction blacklist.

## Final packaged no-argument gate

The rebuilt V35 zip was extracted into a clean directory and invoked literally with no arguments:

```bash
python pcb_v35_renderer.py
```

Observed wall time: **30.86 s**. The run completed on logical sample **0** with no skip chain.

Key report values:

- random base seed: `10238859494160258328`
- emitted seed: `4205329766497871209`
- main chips: **2**
- main launch survival: **84/84**
- cross-chip connections: **6**
- causal tracebacks: **218**
- visible local filler traces: **96**
- honest local stroke+perimeter service: **40.2067%**
- substantial-region component service: **91.6097%**
- direct 90° pathway turns: **0**
- curved pathway primitives: **0**
- unmarked pathway overlaps: **0**
- static pathway intersections: **0**
- unauthorized component/pathway overlaps: **0**

The exact SVG from this gate was rasterized and visually inspected. It shows two main chips, distributed local fillers across the board, visibly varied component scales/quantities in residual rooms, and intentional negative space in awkward pockets; no gross 90°/curved-route/overlap regression was observed.

After recording this gate, only this verification Markdown file was changed before the archive was rebuilt; renderer/test/authority code remained byte-identical to the gated source.
