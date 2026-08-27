# Recovery checkpoint — 2026-08-25 23:52 IST

This checkpoint reconstructs and preserves the exact authoritative MAIN-1 promoted renderer after the previous execution window ended before a fresh handoff could be packaged.

## Authority

- `pcb_v48_renderer.py` SHA-256: `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`.
- The renderer was reconstructed from the exact promotion diff recovered from durable execution history and verified byte-for-byte against the known promoted SHA.
- MAIN-1 exact-local proof reuse is **PROMOTED**. There is no active renderer behavior candidate.
- Active release contract after promotion: **156/156 PASS** in the completed promotion run; maintained geometry stress **1/1 PASS**.

## MAIN-1 promotion result

The promoted change reuses two exact local proofs across held/revisited MAIN fronts while preserving RNG, proposal scoring, topology and output geometry:

1. first-draw proposal legality membership when the full front proposal state and exact local committed-path/source-egress dependency signature are unchanged;
2. successful future-leg legality proofs under the same exact local dependency contract.

Any relevant nearby committed route or source-egress state change invalidates reuse immediately.

Formal 1:1 seeds 102+104, ordinary `0.75 -> 0.5` qualification:

- final emitted MAIN segment work: `1833 -> 4610` for both BEFORE and AFTER = `2.515003x`;
- BEFORE CPU: `10.638228 -> 59.275867 s` = `5.571968x`; normalized CPU/work = **`2.215492x`**;
- AFTER CPU: `11.274694 -> 40.621074 s` = `3.602854x`; normalized CPU/work = **`1.432545x`**;
- aggregate 0.5 MAIN CPU: `59.275867 -> 40.621074 s` (~31.5% lower);
- 0.5 gesture-clear checks: `149,901 -> 130,062`;
- all governing fixture geometry hashes, lookahead counts, rollback segments and traceback counts are unchanged BEFORE vs AFTER.

An adjacent 0.75 recheck removed the apparent light-board overhead: seed 102 `8.6326 -> 7.9443 s`, seed 104 `4.6302 -> 4.7670 s`, aggregate ~4.8% faster, with identical geometry.

## Phase-end 0.35 status

MAIN-1 promotion closes the ordinary long/fine scaling stages and therefore triggered the reserved phase-end 0.35 qualification. The first pre-MAIN-1 `1:1 @ 0.35 / seed 102` attempt exceeded the 180-second execution boundary with no emitted JSON record. It is **not** classified as a renderer failure. No 0.35 comparison was completed before the prior window ended.

Next exact action after this recovery bundle: resume the phase-end 0.35 qualification using the preserved pre-MAIN-1 source (`d58ee1bf...9c9b0`) versus promoted production (`3100503d...03ebb`), seeds 102 then 104, without changing renderer behavior. The historical full `1:6 @ 0.35` operational benchmark remains separate and should follow the normalized phase-end gate, not replace it.
