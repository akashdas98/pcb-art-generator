# Main-chip density knob qualification — 2026-08-27

Final renderer SHA-256: `586d8b54c8044129bea97088c542654b85a79465b37f1ff5ba8efbef96591c98`
Active test manifest SHA-256: `b27627af237325111658de3ac828a0408ecec837ccb607e0c56206d6a0c73a1d`

## Contract
- `--main-chip-density-multiplier`: inclusive 0.2..2.0, default 1.0.
- Default 1.0 is the new approximately-half historical density; 2.0 restores the historical two-opportunity-per-territory law exactly.
- Physical floor: at least one main chip per valid board.
- Geometry/workload control only; no placement/routing architecture change.

## Qualification
- Release gate: **180/180 PASS** on the final one-chip-floor source.
- Maintained geometry stress: **1/1 PASS**.
- Production low-end smoke: `1:1 @ 1.0`, base seed `20260827`, multiplier `0.2`: SVG emitted, exactly 1 main chip, 39 MAIN launch traces, zero unresolved persistence and zero MAIN short terminations.
- Historical compatibility control at multiplier 2.0: old authority and candidate produce bit-identical MAIN geometry and identical routing-work counters on the checked 0.75/0.5 fixtures. Renderer diff contains no MAIN routing-code changes.

## Governing 0.75 -> 0.5 scaling screen (seeds 102 + 104)

| regime | chips 0.75 -> 0.5 | launches 0.75 -> 0.5 | work 0.75 -> 0.5 | work growth | MAIN CPU 0.75 -> 0.5 | CPU growth | CPU/work growth |
|---|---:|---:|---:|---:|---:|---:|---:|
| historical density | 7 -> 16 | 284 -> 676 | 81,240 -> 211,151 | 2.599x | 17.231 -> 39.154 s | 2.272x | 0.874x |
| new default density | 4 -> 8 | 161 -> 329 | 47,510 -> 106,742 | 2.247x | 10.093 -> 22.823 s | 2.261x | 1.006x |

Count quantization is real generally, but it does **not** explain this specific 0.874x -> 1.006x change: historical 0.5 has exactly 8 chips in each governing seed (the exact continuous expectation at T=4), while historical 0.75 realizes 4 and 3 chips against expectation 3.556. The renderer candidate changes routing workload composition by changing source population, while the routing implementation itself is unchanged. Same-geometry multiplier-2.0 controls confirm identical routing geometry/work; raw CPU timings for byte-identical work are noisy in this shared environment and are not treated as evidence of an algorithmic efficiency regression.

## Decision
**ACCEPT / PROMOTE.** The knob changes source population/workload only and preserves the routing architecture and historical workload exactly at multiplier 2.0.
