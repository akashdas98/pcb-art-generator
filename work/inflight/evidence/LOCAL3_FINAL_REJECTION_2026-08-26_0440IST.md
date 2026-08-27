# LOCAL-3 final candidate rejection — 2026-08-26 04:40 IST

Authoritative production renderer SHA-256: `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`.

Remaining candidate: `work/inflight/local3_two_level_static_renderer.py`, SHA-256 `d19cc74d19c04b7c4a126812a5b863bbcd56b26cb1f876d48516b531742c1b2b`.

Governing attempted fixture: `1:6 @ 0.75 / seed 0`, through `work/inflight/local_aspect_timing_probe.py`.

Recorded production control for the same proxy: ~`116.804 s` total CPU.

Final candidate attempt was allowed a 300-second execution wrapper. It did not complete, emitted no durable JSON result, and no candidate renderer process survived the timeout. Therefore it is rejected on governing whole-LOCAL performance. The earlier square screen remains only evidence that the candidate was behavior-exact/cost-neutral on the small fixture; it does not override the long failure.

Decision: **REJECT / DO NOT PROMOTE**. No successor LOCAL-3 candidate is authorized. Optimization is stopped unless explicitly reopened.
