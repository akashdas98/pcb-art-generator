# Long/fine v2 qualification evidence recovered from interrupted continuation

Status: evidence-only recovery after runtime reset; candidate remains UNPROMOTED.

- Candidate SHA-256: `e8d1874d652e7aa6a7af763ac20b2a97d1367082dc748f61771833be49d16054`
- Production SHA-256: `ac53e1d1fae493beb55ab8dc05c0ba7d3053add19a1c6b71cb52ce926738fb79`
- Ordinary 0.75 -> 0.5 normalized MAIN CPU/visible-work growth: production ~`1.592x`, v2 ~`1.409x`.
- Deterministic normalized work: gesture `1.4271x -> 1.4277x`; lookahead `1.4293x -> 1.4257x`; local-space `1.4578x -> 1.4536x`.
- Visible terminated-route <=8/<=14: 0.75/102 `3/11 -> 3/11`; 0.75/104 `2/7 -> 2/7`; 0.5/102 `18/58 -> 16/57`; 0.5/104 `18/64 -> 18/61`.
- Scratch candidate contract after replacing obsolete under-six-hard-debt assertion: 151/151 PASS; maintained stress 1/1 PASS.
- Mandatory 0.5 -> 0.35 normalized MAIN CPU/work: production ~`1.055x`, v2 ~`1.366x` => FAIL / MODIFY.
- Ordinary routing-work counters did not explain the 0.35 CPU delta. Next profiling target: `_settle_final_relational_persistence_progress()` and direct support work.

The scratch test edits/profiler outputs did not survive the runtime reset and are not represented as canonical files here.
