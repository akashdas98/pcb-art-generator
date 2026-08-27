# Recovery checkpoint — 2026-08-26 02:55 IST

Authoritative production renderer is unchanged:

- `pcb_v48_renderer.py` SHA-256 `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`
- no LOCAL-3 renderer candidate is promoted.
- long/fine phase remains reopened by the same-host `1:1 -> 1:6 @ 0.35` operational result.

This checkpoint recovers all post-01:25 LOCAL-3 aspect diagnostics and candidate sources that survived the interrupted turn.

## Measured LOCAL-3 mechanism

At `0.75 / seed 0`, production visible LOCAL traces grow `166 -> 1000` (`6.024x`). Internal launch-scheduler timing shows the nearest-distance block is the steepest measured subterm. The dedicated query split found:

- static geometry population growth ~`5.85x`, but static `STRtree.query_nearest` CPU growth ~`13.77x`;
- committed-path geometry population growth ~`5.62x`, but path `STRtree.query_nearest` CPU growth ~`10.64x`;
- STRtree construction itself is negligible on the square fixture compared with query time.

Thus the current LOCAL-3 target is aspect-sensitive nearest-neighbor scoring inside `_launch_local_gap_fronts()`, not LOCAL target selection, exact gesture legality, or global candidate sorting.

## Rejected / modified experiments

All experiments below preserved the observed LOCAL population/counters on the screening fixtures; none changed production.

- `local3_local_nearest_renderer.py`: exact per-candidate local spatial-hash distance loops; rejected because Python-local distance work was much slower even on the square board.
- `local3_vector_capped_nearest_renderer.py`: exact vectorized capped/dwithin nearest calculation; rejected because long launch scheduling worsened.
- `local3_per_region_sort_renderer.py`: removed useless cross-region global ordering; behavior-exact but long scheduler slightly slower; rejected as a performance fix.
- `local3_static_score_tree_cache_renderer.py`: reused immutable global static STRtree; behavior-exact but long launch scheduling worsened; proves tree construction is not the main tax.

## Tiled-static nearest experiment — completed after interruption

`work/inflight/local3_static_tiled_nearest_renderer.py` SHA-256 `a2ca7b657894f74596231382148e9aa0e774f376f1248b9acbd130a710353569` partitions the immutable static score field into exact score-radius tiles, with every obstacle capable of influencing the existing 5-module capped score present in the relevant local tree. It changes scoring implementation only; no scoring cap/grammar/service rule is relaxed.

Observed `0.75 / seed 0` results:

| metric | production 1:1 | production 1:6 | tiled 1:1 | tiled 1:6 |
|---|---:|---:|---:|---:|
| visible LOCAL traces | 166 | 1000 | 166 | 1000 |
| `_launch_local_gap_fronts()` CPU | 1.0941 s | 8.8320 s | 1.1400 s | 8.3792 s |
| total probe CPU | 14.6129 s | 116.8039 s | 14.8584 s | 120.2822 s |

The targeted launch-scheduler growth improves materially (`8.073x -> 7.350x`; normalized by visible LOCAL work ~`1.340x -> 1.220x`), but the whole LOCAL proxy growth does not improve (`~1.327x -> ~1.344x` normalized by visible traces) in this single adjacent measurement. Therefore this implementation is **not promotable**. Treat the approach as `MODIFY`: the measured global-nearest pathology is real, but this representation does not yet improve the governing whole-LOCAL scaling metric.

Durable evidence is copied under `work/inflight/evidence/local3_aspect_audit_2026-08-26_0255IST/`.

## Next earned action

Do not promote or swap production. Continue from the measured nearest-query term. Before another architecture change, identify why the tiled implementation's scheduler win does not translate into whole-LOCAL CPU: measure candidate-vs-production internal nearest/prelude/fast-round timing or find a representation that attacks both static and committed-path nearest queries with lower setup/dispatch overhead. Any candidate must improve normalized whole-LOCAL aspect scaling, then pass the ordinary `0.75 -> 0.5` gate, release/stress suite, and final full long-board recheck before promotion.
