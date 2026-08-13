# v17 Verification Summary

## Automated regression suite

Final command:

```text
python -m unittest -v test_pcb_v27_renderer.py
```

Result: **17 / 17 tests passed**.

The suite includes new checks for:

- the reduced 2/3 main-chip distribution,
- the main-chip-to-secondary-component breathing zone,
- deferred hard-stop scheduling and later-round rerouting,
- deterministic identical-seed output,
- arbitrary-seed hard geometry,
- zero collapsed pathways,
- zero unmarked crossings,
- zero compensating zig-zags.

## Fresh five-board visual/regression batch

Fresh batch base seed: `1684222116375752765`

All five generated boards had 2 main chips. Across this batch:

- rendered pathway traces: **67–91** per board,
- board-scale trace fraction: **0.121–0.222**,
- hard stops encountered internally: **63–95**,
- reroutes scheduled: **48–72**,
- actual rollback tracebacks: **0–9**,
- successful recovery events: **2–20**,
- branch-preflight rejections: **20–28**,
- abandoned short recovery branches pruned: **13–19 bundles** / **59–92 traces** per board.

The large abandoned-trace counts are useful diagnostic evidence: these are precisely the short boxed-in branches that previously remained visible as stubs. v17 attempts recovery first and then omits short involuntary failures that still cannot become meaningful routes.

### Hard-geometry audit for all five boards

Every fresh board reported:

- `pathway_static_intersection_count = 0`
- `pathway_unmarked_overlap_count = 0`
- `pathway_compensating_zigzag_count = 0`

The general test suite additionally verifies collapsed-trace cleanliness.

## Visual review

The post-recovery five-board montage shows substantially more open launch space around main chips and removes the dense comb of tiny involuntary dead-end stubs seen before this revision. Routes can still legitimately terminate, leave the frame, or fail after exhausting recovery; v17 does not force requested outcome percentages when geometry makes them impossible.

Cross-chip connection count happened to be zero in this particular five-board random batch. Connection remains probabilistic rather than an acceptance quota; the deterministic regression seed still exercises a successful connection path.
