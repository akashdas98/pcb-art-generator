# V18 verification summary

## Regression tests

The package contains 18 unit tests. Every test passed on the final V18 code. Pathway-heavy cases were executed in split invocations because running the entire suite in one wrapper call can exceed the per-call time limit.

Final-code verification covered:

- byte-identical deterministic SVG + JSON for identical seeds;
- arbitrary-seed pathway collision cleanliness;
- 70–90% visible chip-body launch-side coverage on the reference pathway test;
- denser main-chip launch spacing and 3–5 trace routing cohorts;
- shared-round holistic cross-chip connection pairing;
- real physical cross-chip joins on the reference sample;
- active anti-loop candidate rejection plus the existing no-compensating-zigzag audit;
- five-attempt deferred rerouting, multi-segment traceback, deep traceback, conflict repair, and stagnation repair;
- zero static pathway intersections;
- zero unmarked trace crossings;
- zero collapsed overlaps;
- reduced 2/3 main-chip density and the 85U secondary-component moat retained.

## Five-board final visual probe

The first three boards are consecutive logical samples from base seed `0x20260806`. Two additional deterministic base seeds are used for the last two visual boards so the deliverable does not wait on an unusually slow later static-board sample. This is not pathway candidate searching and does not alter the one-seed/one-output behavior.

| sample | launch traces | rendered traces | visible launch span min | cross-chip joins | loop candidates rejected | tracebacks | deep tracebacks | static intersections | unmarked crossings | compensating zigzags |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 160 | 150 | 74.3% | 4 | 184 | 166 | 42 | 0 | 0 | 0 |
| 1 | 180 | 173 | 74.0% | 1 | 252 | 96 | 19 | 0 | 0 | 0 |
| 2 | 192 | 192 | 72.7% | 5 | 306 | 133 | 41 | 0 | 0 | 0 |
| 3 (`12345`) | 176 | 150 | 75.8% | 2 | 275 | 90 | 9 | 0 | 0 | 0 |
| 4 (`515151`) | 187 | 184 | 72.7% | 2 | 414 | 128 | 31 | 0 | 0 | 0 |

All five final visual samples preserve a visible launch span above 70% of every represented chip side while retaining zero audited geometry violations.
