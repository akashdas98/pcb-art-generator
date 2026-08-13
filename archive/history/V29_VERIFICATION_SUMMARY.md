# V29 Verification Summary

## Reference generation

Command:

```bash
python pcb_v29_renderer.py --seed 12345 --count 1 --out-dir verify_v29 --max-sample-restarts 32
```

Observed build-environment runtime: about 24 seconds.

Reference routed sample highlights:

- all 65 planned main-chip launch traces remained visible (`65 / 65`), so no main launch lane was pruned as a tiny post-emergence stub;
- local residual-gap target: ~39.4%; realized representative local coverage after tuning: approximately 37–45% across checked seeds;
- local bundles show repeated real split events rather than same-direction bookkeeping splits;
- on the deliberately troublesome 1000×1000 seed `20260806`, visible main-chip launches improved from the pre-V29 50/58 observation to 54/58 after early recovery/young-head arbitration; the remaining infeasible young lanes are suppressed rather than rendered as tiny stubs;
- local special-thick population remains within the historical 15–30% intent on checked reference seeds;
- local exit permission is explicitly halved; checked reference seeds produced few or zero local frame escapes;
- residual component fill on checked reference seeds lands inside the new 80–90% band;
- no component is present during primary/local routing.

## Passed targeted tests

- capacitor continuous size-range test;
- independent `main_scale` test;
- route-before-secondary-components test;
- main bundle/pathway hard-geometry regression on seed 12345;
- bounded holistic connection/loop/recovery regression;
- byte-identical same-seed determinism test;
- arbitrary-seed hard-geometry check for 1000×1000 seed `20260806`, sample index 0.

The arbitrary-seed hard-geometry check confirmed zero:

- static intersections,
- unmarked centerline overlaps/crossings,
- thick-stroke overlaps,
- compensating zigzags,
- tiny terminal traces,
- mid-line connections,
- multiply-connected traces,
- rendered termination-marker overlaps,
- duplicate/intersection cleanup events.

## Environment-cap note

The existing three-sample aggregate arbitrary-seed regression and a combined long-running hard-stop regression command exceeded this environment's single-command execution cap. They are not recorded as passes. No acceptance invariant was weakened to make those commands finish.
