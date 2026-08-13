# V37 Verification Summary

V37 is the anti-confetti component-language correction on top of V36. It preserves the V36 phase order and routing invariants while restoring coherent multi-entity component assemblies as the dominant residual component language.

## Targeted regression gates

Passed:

- medium/large residual rooms generate compound assemblies, not standalone dot/dash filler;
- micro tokens are restricted to genuine micro regions and the sample-wide cap is 8;
- cached component-route keepout reuse remains intact;
- root main bundles cannot split before physical source egress;
- full reference-seed compound-dominance gate;
- full V37 space-aware causal contract.

The focused four-test structural run completed in ~0.06s. The full reference compound-dominance test completed in ~24.1s. The full space-aware causal contract completed in ~24.1s.

## Reference seed `20260806`

- elapsed: **23.99s**
- chips: 2
- main lanes: 71 launched / 71 visible
- cross-chip connections: 8
- component target: 57.22%
- component actual service: **58.08%**
- total accepted component groups: 44
- residual cleanup groups: 24
- compound residual assemblies: **23**
- singleton residual components: 1
- micro token fillers: **0** / cap 8
- compound share of residual cleanup: **95.8%**
- local actual of remaining service budget: **88.38%**
- local absolute service: 37.05%
- terminal/component marker backoffs: 2
- component↔local clearance violations: 0
- unauthorized component/pathway overlaps: 0
- main↔local clearance violations: 0
- illegal turns: 0
- curved pathway primitives: 0

## Difficult regression seed `15186978462388109083`

- elapsed: **23.54s**
- chips: 2
- main lanes: 93 launched / 93 visible
- cross-chip connections: 8
- component target: 56.35%
- component actual service: **58.16%**
- total accepted component groups: 42
- residual cleanup groups: 23
- compound residual assemblies: **20**
- singleton residual components: 3
- micro token fillers: **0** / cap 8
- compound share of residual cleanup: **87.0%**
- local actual of remaining service budget: **83.89%**
- local absolute service: 35.10%
- terminal/component marker backoffs: 3
- component↔local clearance violations: 0
- unauthorized component/pathway overlaps: 0
- main↔local clearance violations: 0
- illegal turns: 0
- curved pathway primitives: 0

## Visual regression result

The same reference seed was rasterized before and after the V37 correction. V36 visibly contained broad fields/rows of orphan dots, tiny squares and dashes. V37 replaces those open-room cleanup fields with bordered multi-family modules while retaining a small-component path for genuinely small pockets. Both V37 production samples were rasterized and visually inspected.

## Root-cause confirmation

On V36 reference seed `20260806`, 27 of 47 accepted component groups were generic residual mop-up fillers. The cleanup class therefore numerically dominated the prepared proper collection population. In V37 the same seed uses 24 residual cleanup groups, 23 of which are compound assemblies and none of which are micro tokens.

## Release status

The V37 renderer, cumulative authoritative specification, changelog, README, tests, and this verification record are packaged together. Historical V36 files remain preserved alongside the new V37 release files.
