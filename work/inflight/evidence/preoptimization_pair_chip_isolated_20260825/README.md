# Pre-optimization raw error correction — 2026-08-25

Source: user-supplied `pcb_v48_renderer_raw_error_logs_20260825.zip`.

The contained `renderer_error.log` is from `pcb-art-generator_V48_CLEAN_2026-08-25_0341IST` and records a completed failing renderer process:

- elapsed: `435.3526184 s` (`00:07:15.3526184`)
- exit code: `1`
- exception: `RuntimeError: post-route validation failed: pair_chip_isolated`

This is direct evidence that the pre-optimization 0341 long/fine regime was not uniformly "valid but slow". At least one run spent more than seven minutes and then failed final validity.

The log does **not** include the command line, base seed, logical seed, or sample index. Therefore this exact historical failure cannot currently be replayed from this artifact alone, and it must not be claimed that the current renderer has specifically closed this exact fixture unless the missing invocation is recovered.

Previously supplied 0341 raw-log sets containing empty stderr remain valid evidence only for those particular externally terminated attempts. They do not justify a universal claim about all 0341 runs.
