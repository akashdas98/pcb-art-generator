#!/bin/bash
set -euo pipefail
ROOT=/mnt/data/v48_current_work/pcb_v48_repo
cd "$ROOT"
PROBE=work/inflight/evidence/20260827_residual_mosaic/perf/residual_probe.py
SRC=pcb_v48_renderer.py
BASE=work/inflight/evidence/20260827_residual_mosaic_second_pass/final_qualification/perf_final
for SCALE in 0.75 0.5; do
  for SEED in 102 104; do
    OUT="$BASE/candidate_s${SCALE}_seed${SEED}.json"
    python "$PROBE" "$SRC" "$SCALE" "$SEED" "$OUT" > "$BASE/candidate_s${SCALE}_seed${SEED}.log" 2>&1
  done
done
echo 0 > "$BASE/rc.txt"
