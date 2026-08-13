# V38 verification summary

## Scope

V38 was checked specifically for the reported regression: long local-gap fillers being predominantly straight and
for the hard rule that a visible pathway corner may change heading only in 45-degree units.

The two maintained V37 release base seeds were rerun so the comparison uses the same logical board seeds rather than
new showcase seeds.

## Same-seed results

| Gate | V37 reference | V38 reference | V37 difficult | V38 difficult |
|---|---:|---:|---:|---:|
| Logical seed | 2065259631603175940 | 2065259631603175940 | 568060949511661325 | 568060949511661325 |
| Visible local traces | 73 | 81 | 72 | 71 |
| Pure straight visible local traces | 43 | 2 | 33 | 11 |
| Straight visible local fraction | 58.90% | **2.47%** | 45.83% | **15.49%** |
| Mean turns per visible local trace | 0.630 | **1.358** | 0.861 | **1.225** |
| Maximum single rendered vertex turn | 45° | **45°** | 45° | **45°** |
| Illegal pathway turn count | 0 | **0** | 0 | **0** |

The V37 straight/turn counts above were measured from the final rendered SVG polylines using the same heading-delta
classification as the V38 report diagnostics. V38 records those metrics directly in its report.

## Service and geometry gates

### Reference release seed

Base seed: `20260806`  
Logical seed: `2065259631603175940`

- component service target: 57.22%
- component service actual: 58.08%
- local remaining-service target: 87.59%
- local remaining-service actual: 87.66%
- local absolute service: 36.75% of original post-main residual service field
- visible local traces: 81
- pure straight visible local traces: 2 (2.47%)
- mean visible turns/local trace: 1.358
- maximum rendered single-vertex turn: 45°
- normal mop-up traces: 47
- bent normal mop-up traces: 46
- straight narrow-pocket mop-up traces: 1
- bent residual-rescue traces: 0
- component residual cleanup: 23 compound / 1 singleton / 0 micro tokens
- final clearance violations: 0
- main↔local clearance violations: 0
- component↔local clearance violations: 0
- pathway illegal-turn count: 0

Observed production runtime: approximately 25.20 s in the release test environment.

### Difficult release seed

Base seed: `15186978462388109083`  
Logical seed: `568060949511661325`

- component service target: 56.35%
- component service actual: 58.16%
- local remaining-service target: 83.28%
- local remaining-service actual: 83.56%
- local absolute service: 34.96% of original post-main residual service field
- visible local traces: 71
- pure straight visible local traces: 11 (15.49%)
- mean visible turns/local trace: 1.225
- maximum rendered single-vertex turn: 45°
- normal mop-up traces: 29
- bent normal mop-up traces: 27
- straight narrow-pocket mop-up traces: 2
- bent residual-rescue traces: 0
- component residual cleanup: 20 compound / 3 singletons / 0 micro tokens
- final clearance violations: 0
- main↔local clearance violations: 0
- component↔local clearance violations: 0
- pathway illegal-turn count: 0

Observed production runtime: approximately 24.76 s in the release test environment.

## Automated regression checks

Focused V38 unit gates completed successfully:

```text
python -m unittest \
  test_pcb_v38_renderer.V38RendererTests.test_v38_commit_rejects_direct_90_degree_turn \
  test_pcb_v38_renderer.V38RendererTests.test_v38_reference_local_fill_is_bent_dominant_and_45_degree_only

Ran 2 tests in 24.466s
OK
```

The first test deliberately attempts a direct 90-degree commit and requires a hard failure. The second performs a
full reference render and requires all of the following simultaneously:

- normalized local service ≥80%;
- visible straight-local fraction ≤20%;
- bent mop-up traces present and ≥85% of the mop-up population;
- maximum rendered single-vertex turn exactly 45°;
- zero local illegal turns;
- zero overall pathway illegal turns.

`python -m py_compile pcb_v38_renderer.py` also passes.

## Release conclusion

V38 fixes the straight-line dominance without changing the residual phase ordering or weakening service/clearance
rules. The reference board changes from majority-straight local fill to overwhelmingly articulated local fill; the
harder board also remains bent-dominant. Both maintained boards still satisfy their sampled 80–90% local service
obligations and contain no rendered turn larger than 45°.
