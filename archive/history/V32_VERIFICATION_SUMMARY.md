# V32 Verification Summary

V32 was verified against the specific premature-line failure modes that survived V31 and against the existing routing/geometry/runtime invariants. Final materialization now hard-rejects any routing result whose visible main-lane count differs from its launched main-lane count or whose main terminal falls below the protected floor.

## Direct routing semantics

14 targeted architecture tests passed, including:

- transactional insertion-order invariance;
- no sequential winner for an unsolved same-round conflict;
- root traceback to the emergence anchor;
- causal blocker rollback;
- no fan/branch/recovery fragmentation before physical source egress;
- single-cohort source buses remain straight before egress;
- traceback reactivates source protection/reservations;
- protected same-family atomic HOLD;
- foreign geometry inside the old head-start disk is not hidden;
- escaped geometry is clipped at its first frame crossing;
- routes still precede all secondary components;
- cached component keepouts remain reused;
- component failure cannot internally restart routing;
- same-seed pathway determinism remains active.

## Known failure seeds

Current V32 results:

- seed `6826100834675585483`: 59 launched / 59 visible main lanes; zero main-short terminals; zero intersection cleanup; zero zigzag cleanup.
- seed `15186978462388109083`: 67 / 67; zero main-short terminals; zero intersection cleanup; zero zigzag cleanup.
- seed `20260806`, 1000×1000 samples 0/1/2: 58/58, 65/65, 64/64 visible main lanes; zero static intersections, unmarked/collapsed/stroke overlaps, compensating zigzags, tiny terminations, midline/multiple connections, marker overlaps, duplicate cleanup, and intersection cleanup. Local-gap coverage was 41.1%, 39.0%, and 45.8% respectively.

## Local-gap target

Seed `12345` produces ~51.6% representative local-gap coverage (within the existing 30–55% hard regression envelope around the 38–42% soft target), with 23 visible local traces after the local-only HOLD correction. The previous intermediate V32 state produced only 17.2% because local peers could deadlock at gesture zero.

## Untouched default invocations

Three final-source clean `python pcb_v32_renderer.py` runs with no seed, scale, retry, search, or calibration overrides completed in approximately:

- 8.77 s — 56/56 main lanes visible; 42.9% local-gap coverage; 86.4% residual component fill.
- 7.61 s — 59/59; 41.7%; 83.3%.
- 9.45 s — 56/56; 48.1%; 87.5%.

All three completed on logical sample 0 with restart index 0 and reported zero main-short terminals, intersection cleanup, zigzag cleanup, and unresolved protected launches.

## Notes

The aggregate three-seed unittest wrapper can exceed the surrounding command harness window due to subprocess overhead/GEOS process handling. Each of its three constituent geometry-heavy samples was run independently and completed in about 7.5–8.0 seconds with all assertions satisfied.
