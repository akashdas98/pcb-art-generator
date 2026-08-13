# V36 Verification Summary

This file records targeted release verification for V36. It does not claim that every historical legacy unittest
has been run in one aggregate harness.

## Contract/unit gates

The following V36-targeted tests passed together:

- root main launch traceback to emergence anchor;
- insertion-order-invariant joint conflict solution;
- unsolved same-round group defers instead of priority winner commit;
- root bundle cannot structurally split before physical egress;
- main routing occurs before secondary components spatially exist;
- `main_scale` is independent of canvas dimensions;
- `U = min(W,H)*main_scale/1600` and default 1200×1200 chip population is exactly two;
- V36 component-first → local-after-component space-aware causal contract.

The eight-test targeted run completed successfully in approximately 31 seconds.

## Deterministic reference seed `20260806`

A full V36 sample completed in approximately 25.6 seconds:

- chips: 2
- main lanes: 71 launched / 71 visible
- cross-chip connections: 8
- component target: 57.22%
- component actual service: **57.58%**
- component count: 47
- local target of remaining service budget: 87.59%
- local actual of remaining service budget: **87.99%**
- local absolute service against original post-main residual budget: 37.33%
- visible local traces: 86
- main↔local clearance violations: 0
- local↔component clearance violations: 0
- unauthorized component/pathway overlaps: 0
- illegal pathway turns: 0
- curved pathway primitives: 0

The rendered sample was rasterized and visually inspected.

## Difficult regression seed `15186978462388109083`

A full V36 sample completed in approximately 28.0 seconds:

- chips: 2
- main lanes: 93 / 93
- cross-chip connections: 8
- component target: 56.35%
- component actual service: **56.83%**
- component count: 44
- local target of remaining service budget: 83.28%
- local actual of remaining service budget: **84.33%**
- local absolute service: 36.40%
- visible local traces: 76
- local terminal-marker component-moat backoffs: 2
- main↔local clearance violations: 0
- local↔component clearance violations: 0
- unauthorized component/pathway overlaps: 0
- illegal pathway turns: 0
- curved pathway primitives: 0

## Historical preservation audit

The V36 working tree was compared byte-for-byte with the released V35 zip before packaging:

- all **52 non-bytecode V35 files** were byte-identical in the V36 tree;
- all **44 historical changelog / verification / execution-audit records** were byte-identical;
- generated `__pycache__/*.pyc` files are excluded from the V36 release zip and from the preservation count;
- V36 source/tests/docs/history are new files rather than edits to historical release records.

## Additional targeted recovery gates

- cached component route-keepout reuse: passed;
- component-placement failure never restarts main routing internally: passed.

An older mixed-batch hard-stop test exceeded the external harness window during a later targeted run; this summary
does not claim that test or the entire historical aggregate passed in that invocation.

## Final production hardening before package gate

A first clean-zip literal run exposed an empty-geometry spatial-hash crash in the forced head-to-head connection
path. A tiny final rendezvous leg could be wholly contained by the allowed junction envelope, producing an empty
Shapely difference with NaN bounds. V36 now handles that intentional junction-only case explicitly and rejects
all other empty/non-finite gesture geometry before broad-phase lookup. The two V36 connection-grammar unit guards
passed after this patch.

## Bounded post-component local-tail gate

After the phase inversion, V36 was tightened to three organic local waves plus bounded exact corridor mop-up. The
reference and difficult regression seeds still satisfy their normalized 80–90% remaining-service targets while
finishing in approximately 25.6s and 28.0s end-to-end. A deliberately troublesome residual topology now reaches a
hard final frozen-geometry clearance rejection in approximately 29s rather than entering an unbounded dense local
tail; default batch mode may deterministically skip such a logical sample.

## Final clean-package production gate

A clean V36 zip was extracted into a fresh directory and executed literally as:

```bash
python pcb_v36_renderer.py
```

with no seed, scale, retry, calibration, or search-budget overrides. It completed on logical sample 0 in
**26.72 seconds**. The generated report recorded:

- base seed: `2852330033450036735`;
- sample seed: `11381955249659321714`;
- chips: 2;
- main lanes: **84 launched / 84 visible**;
- cross-chip connections: 6;
- component target: 52.10%;
- component actual service: **53.31%**;
- component count: 39;
- local target of remaining service budget: 80.59%;
- local actual of remaining service budget: **81.21%**;
- local absolute service against the original post-main residual budget: 37.91%;
- visible local traces: 82;
- main↔local clearance violations: 0;
- local↔component clearance violations: 0;
- unauthorized component/pathway overlaps: 0;
- illegal pathway turns: 0;
- curved pathway primitives: 0;
- main gesture-clear checks: 26,718 / 52,000 deterministic budget;
- logical samples skipped: none.

The exact SVG from this gate was rasterized and visually inspected. It showed the intended V36 composition:
components establish the residual mass first, then local traces articulate the majority of the remaining service
budget while preserving intentional negative space and all visible clearances.

After recording this gate, only this verification document was updated before the final zip rebuild; renderer code
and tests were unchanged.
