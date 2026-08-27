# Inflight work

There is currently **no active renderer candidate**.

Latest promoted authority:
- renderer SHA-256: `5d8624de9d2b5ec5b5ba7dac7fed169653074d7301751f8b1b1558e870dba98b`
- active test manifest SHA-256: `60bf4911d9a017eda87b701ff4e7080955906a67fdbe3ce5e33ada3602f77b1e`
- release gate: **183/183 PASS**
- maintained geometry stress: **1/1 PASS**
- promotion status: **CLOSED / PROMOTED**

Latest promoted behavior change: MAIN whole-route run-length control plus inter-chip connection success semantics.
- `--main-run-length-multiplier`: inclusive **0.2..3.0**, default **1.0**.
- `0.5` restores historical MAIN journey targets; `1.0` is 2x historical; `3.0` is 6x historical.
- per-gesture grammar/clearance/search architecture is unchanged.
- legal foreign-main-chip connections win before voluntary journey-limit termination.
- normalized 0.75->0.5 composite CPU/work: default **1.014x**, maximum multiplier **1.046x**.

Qualification evidence: `work/inflight/evidence/20260827_main_run_length_knob/qualification_summary.md`.

The planned post-optimization behavior-knob phase is complete.
