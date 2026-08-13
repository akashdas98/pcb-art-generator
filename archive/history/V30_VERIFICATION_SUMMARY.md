# V30 Verification Summary

## Default-mode runtime regression

The reported V29 failure was reproduced as a release-blocking class of bug: an untouched default run could
spend excessive work in residual component fallback/retry. V30 was then exercised with **literal no-argument
CLI invocations** from clean directories:

```bash
python pcb_v30_renderer.py
```

No seed, `main-scale`, output directory, benchmark/test seed, search budget, retry budget, calibration budget,
or deadlock flag was supplied. Three final isolated release-tree runs completed and emitted one SVG each in:

- 11.55 s — base seed `5263602788798090720`, restart index 0, no skipped logical sample;
- 9.41 s — base seed `17266022421911298604`, restart index 0, no skipped logical sample;
- 10.05 s — base seed `17260622200694415783`, restart index 2, no skipped logical sample.

The third run is useful evidence that cheap pre-routing rejection/retry can occur without recreating the V29
minutes-long failure mode. All three completed component placement in one layout attempt and reported
`route_restarted_for_component_failure=false`. Their representative local-gap covered/open-cell fractions were
approximately 0.426, 0.378, and 0.378 respectively, and residual component gap-site fill was approximately
0.864, 0.833, and 0.889. Exact geometry remains authoritative, so the 38–42% local target is soft.

Wall time is diagnostic only; seeded output never branches on time.

## Test suite

All **22** test cases in `test_pcb_v30_renderer.py` were exercised successfully across split runs so the
geometry-heavy subprocess cases stayed within the execution harness limit.

Passed coverage includes:

- cached component fallback keepout regression: every candidate receives precomputed chip/pathway
  keepouts; the V29 omission cannot recur silently;
- post-route component failure regression: component-only recovery exhaustion does not internally invoke
  another routing pass;
- exact quota assignment;
- route-before-secondary-components invariant;
- independent `main_scale` invariant;
- V29/V30 capacitor continuous 1.5× radius range;
- primary bundle-gesture hard-geometry/pathway invariant test;
- byte-identical pathway determinism without pathway-seed search;
- three arbitrary 1000×1000 seeded hard-geometry subprocess checks, including zero compensating
  zigzags after the materialization-only leaf cleanup;
- deferred hard-stop reroute regression;
- bounded holistic connection/loop/repair regression;
- single-sample, two-sample uniqueness, and batch deadlock-skip regressions.

## Reproduced wasted-work case

A deterministic base seed that previously completed after skipping/retrying late was used to verify
pre-route rejection. Before the V30 preflight correction the run took about 19 s and discarded a logical
sample after a post-route `coverage_dash` validation failure. V30 detects that family-coverage failure
before routing; the same base seed completes logical sample 0 after a cheap pre-route retry in about 13 s,
with only one expensive route pass.

## Structural audit

- Residual-fill fallback passes `chip_keepout` and `pathway_keepout` into `_component_candidate_valid()`.
- Component template generation/calibration occurs before `generate_pathways()` but templates have no
  canvas position and are not passed into the planner.
- Final component placement and alternate-population recovery reuse the frozen route network.
- Successful report metadata exposes the pre-route-template and no-component-reroute facts.
- V29 visual routing rules remain active; V30 is a runtime/dependency correction, not a density or route-
  behavior rollback.
