# V16 verification summary

## Architecture assertions

- Active planner: `synchronous_bundle_gestures`
- Pathway candidate-seed retries: `0`
- Fine route searches / A*: `0`
- Static placement changes made for pathways: `0`
- Behavioral outcome acceptance gates: none
- Same seed and parameters: byte-identical JSON report and SVG

## Automated suite

Fourteen tests cover the inherited static-board rules plus the new pathway architecture,
determinism, modular movement, physical joins, arbitrary-seed geometry, and exact collision audit.

## Fresh five-board visual set

The deliverable set was generated once with a fresh cryptographic base seed
`9709108145809082148`. Logical samples `0–4` all emitted directly; every static baseline
`restart_index` was also `0`. No sample was rejected or replaced based on its pathways.

| Measurement | Range across five boards |
|---|---:|
| Runtime, one five-board invocation | 10.9 seconds |
| Cross-chip physical joins | 0–6 |
| Traces in those joins | 0–12 |
| Off-canvas trace escapes | 67–90 |
| Board-scale trace fraction | 5.1–12.1% |
| Mean segments per rendered trace | 2.29–3.23 |
| 12×12 coverage fraction | 51.4–66.0% |
| Static-object intersections | 0 |
| Unmarked trace intersections | 0 |
| Collapsed centerline overlaps | 0 |
| Compensating zigzags | 0 |
| Pathway seed retries / route searches | 0 / 0 |

One board realized no cross-chip join. It remains in the set because connections are best-effort
probabilistic behavior, not a hidden acceptance quota.

## Additional arbitrary-seed probe

Ten more boards were generated from unrelated base seeds `17` and `99887766` after the planner
was complete. Across those boards:

- cross-chip physical joins ranged from `0–8`;
- off-canvas trace escapes ranged from `57–107`;
- coarse coverage ranged from `35.4–70.1%`;
- every retry/search, static-intersection, unmarked-intersection, collapse, and compensating-
  zigzag counter remained zero.

These probes validate hard geometry and direct execution. They do not establish aesthetic output
quotas, and the renderer does not use them to select future seeds.
