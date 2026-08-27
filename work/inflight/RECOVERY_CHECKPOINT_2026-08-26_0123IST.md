# Recovery checkpoint — 2026-08-26 01:23 IST

- Production renderer unchanged: SHA-256 `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`.
- Existing promoted stages retained: LOCAL-1, LOCAL-2, MAIN-1; active suite remains 156 tests plus maintained stress from the latest canonical gate.
- Full same-host `1:1 -> 1:6 @ 0.35 / seed 0` operational benchmark reopened long-board scaling: whole CPU/work ~1.261x; LOCAL 1.375x/trace; MAIN 1.256x/launch; components 1.164x/component.
- New zero-policy LOCAL aspect probe (`0.75`, seed 0): residual regions 47 -> 344 (7.319x), `_launch_local_gap_fronts()` CPU 1.158 -> 9.138 s (7.894x), gesture-clear 6.038x, target selection 4.828x.
- Diagnostic cProfile identifies repeated launch scheduling / fragmented residual spatial work as the earned next target; `STRtree.query_nearest` is ~4.312 s on the long profile and `_residual_gap_regions()` ~4.828 s.
- No active behavior candidate. Next: decompose `_launch_local_gap_fronts()` nearest-geometry tree/query work vs whole-candidate-pool scoring/allocation; optimize the approach only if it removes fragmentation-driven work without changing service, RNG ownership, density, or geometry legality.
