# Long/fine totality v2 evidence

These are retained historical qualification/reproduction records for the long/fine totality source that was subsequently **promoted byte-for-byte** into production `pcb_v48_renderer.py`.

Candidate SHA-256: `e8d1874d652e7aa6a7af763ac20b2a97d1367082dc748f61771833be49d16054`
Current production authority is `pcb_v48_renderer.py` SHA-256
`e8d1874d652e7aa6a7af763ac20b2a97d1367082dc748f61771833be49d16054`.

Important records:

- `longfine_seed1_main_only.json` — exact `1:6 @ 0.35`, base seed 1, MAIN-only PASS.
- `longfine_seed1_full_report.json` — full emitted-board report for the exact same requested seed;
  `restart_index=0`, all 4,104 MAIN launches visible, no skipped/reseeded logical sample.
- `prod_*.json` / `cand_*.json` — ordinary 1:1 screening at 0.75 then 0.5 for governing
  seeds 102 and 104.
- `longfine_seed0_production_phase.json` — exact `1:6 @ 0.35`, base seed 0, production whole-render phase PASS (`630.862 s` CPU, `805,176 KiB` peak RSS).
- `longfine_seed0_v2_phase.json` — same fixture on v2 PASS (`614.485 s` CPU, `804,192 KiB` peak RSS).
- `longfine_seed0_*_phase.time.txt` — `/usr/bin/time -v` process records for those two runs.

The generated SVG itself is deliberately not retained in the lean repository. The emitted SVG was
10,476,942 bytes with SHA-256
`b1922ef443581627cb87a1695893cd1baa4a789a230669ea07ab7a7d47297e28`.
The retained full report SHA-256 is
`0e6d17fbc0fe87ac112843a8c3cd41400cd4c556cb492a74d14ab38e1285086f`.

- `0341_user_raw_logs/` — user-supplied post-promotion `1:6 @ 0.35` CLI logs; no exceptions, externally terminated before sample completion; evidence for performance/observability classification, not seed rejection.
