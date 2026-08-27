# V41 Verification Summary

## Status

**PASS — complete active release contract.**

V41 fixes the microscopic escaped-tail frame-clipping defect that could manufacture one non-octilinear visible segment on extreme portrait canvases. The exact-octilinear and <=45-degree audits remain unchanged.

## Reproduced failure

Before the fix, deterministic `1200×6248`, base seed `1`, logical sample `0` reached main-network preflight with:

- `pathway_non_octilinear_segment_count = 1`
- `pathway_illegal_turn_count = 0`

The malformed visible tail was created only after frame clipping. Its pre-clipped materialized points were exact octilinear geometry.

## Root-cause verification

The failing legal tail ended with a 45-degree leg followed by a microscopic horizontal escape. V40 moved the diagonal endpoint to the horizontal segment's frame crossing. V41 instead extends the previous diagonal along its own exact DIR8 heading to its own frame crossing.

The bounded active regression covers the same mechanism on heights `6248` and `8046` and requires:

- zero malformed visible segments;
- exact 0/45-degree path grammar after clipping;
- a real frame crossing;
- no sub-0.10-module visible tail.

## Authoritative release command

```bash
python run_release_tests.py
```

Final result on 2026-08-14:

- active tests discovered: **44**
- passed: **44**
- failures: **0**
- errors: **0**
- skips: **0**
- expected failures / xfails: **0**
- manifest mismatch: **0**
- observed runtime: **6.73 s**

## Real tall-canvas main-network probes

The real deterministic main-network path that previously failed was rerun separately at both reported extremes:

- `1200×6248`, base seed `1`: **PASS**, `pathway_non_octilinear_segment_count=0`, `pathway_illegal_turn_count=0`.
- `1200×8046`, base seed `1`: **PASS**, `pathway_non_octilinear_segment_count=0`, `pathway_illegal_turn_count=0`.

These probes exercise actual chip placement and main routing, not only the synthetic clipping helper.

## Fresh V41 production snapshots

Because this is a behavioral renderer change, V40's V39-equivalent snapshot inheritance is not used.

Fresh standard reference (`base_seed=20260806`, sample seed `2065259631603175940`):

- non-octilinear segments: **0**
- illegal turns: **0**
- illegal connection-junction turns: **0**
- rendered clearance violations: **0**
- component residual service: **58.91%**
- local residual service: **86.48%**
- main source markers: **71/71**

Fresh difficult reference (`base_seed=15186978462388109083`, sample seed `568060949511661325`):

- non-octilinear segments: **0**
- illegal turns: **0**
- illegal connection-junction turns: **0**
- rendered clearance violations: **0**
- component residual service: **56.99%**
- local residual service: **80.33%**
- main source markers: **93/93**

## Scope

No routing probability, main/component population rule, phase order, fill target, chip/component clearance, connection grammar, or audit tolerance was weakened or changed. V41 changes only the microscopic escaped-tail materialization behavior and the tests/snapshots/docs required by that behavioral fix.
