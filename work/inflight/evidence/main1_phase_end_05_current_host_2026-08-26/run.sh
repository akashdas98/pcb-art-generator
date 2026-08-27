#!/usr/bin/env bash
set -u
run_one(){
  label="$1"; src="$2"; seed="$3"
  /usr/bin/time -f 'wall=%e cpu_user=%U cpu_sys=%S rss_kib=%M' -o "$D/$label.time.txt" \
    timeout 300s python tools/perf_harness.py "$src" --aspect-ratio 1:1 --scale 0.5 --seed "$seed" --out "$D/$label.json" >/dev/null
  echo $? > "$D/$label.rc"
}
run_one s05_102_before work/inflight/main1_before_proof_reuse_renderer.py 102
run_one s05_102_after pcb_v48_renderer.py 102
run_one s05_104_before work/inflight/main1_before_proof_reuse_renderer.py 104
run_one s05_104_after pcb_v48_renderer.py 104
echo done > "$D/batch.done"
