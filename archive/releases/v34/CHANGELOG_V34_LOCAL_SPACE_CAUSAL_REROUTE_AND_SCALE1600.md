# V34 — Local-Space Causal Reroute, Scale /1600, and Fill Enforcement

## Scale and chip placement

- Reduced the complete default design scale by 25%: `U = S_canvas * main_scale / 1600`; S-derived chips/collections shrink consistently with U-derived routing/component geometry.
- Kept chip-count probability unchanged at 90% two chips / 10% three chips.
- Increased chip routing separation to `max(360U, 0.205*S_canvas)`; default 1200×1200 separation is 270 canvas units.

## Main routing

- Added bounded local free-space/corridor-capacity ranking from the maintained occupancy/congestion field.
- Made deadlock traceback deeper and causal: rollback records the historical direction leaving the rollback junction and suppresses replay of that failed corridor during recovery.
- Recovery considers both legal ±45° alternatives without permitting a direct 90° pivot.
- Added separate bounded causal-yield allowance for foreign blockers of young launches.
- Added local-space termination deferral when a materially viable alternate corridor exists.
- Added fail-fast main-only materialization audit before local/component work.
- Added bounded causal rollback/regrowth for a physical lane that would otherwise be removed by late zigzag/intersection cleanup.
- Added physical offset-lane tail grammar checking for risky compensating reversal turns, including inherited fan/branch prefixes.

## Geometry invariants

- Pathway heading changes are limited to 0/±45°; any direct 90° turn is a hard failure.
- Pathway route bodies are straight-segment polylines only; quadratic/Bézier pathway primitives are a hard failure.
- Unauthorized pathway overlap/intersection and component/pathway overlap remain hard failures.

## Local-gap network

- Connected residual-region grid is 28×28.
- Ordinary local lines remain independent singleton births with one-time 50% temporary bundling on compatible encounters.
- Increased region-capacity-driven source allowance after the smaller default scale created more residual territory; no artificial coverage-halo widening was used for this correction.
- Internal target is 42–50% with a hard accepted visual floor of approximately 40%; component fill cannot compensate for local-line underfill.

## Components

- Retained connected-region, size-aware residual placement and 90–94% visual-service target.
- Made >=90% component service a hard accepted-sample invariant.
- Reworked service accounting incrementally so adding a filler does not rebuild/buffer the full accepted component union each iteration.
- Reduced random fallback work and replaced expensive exact geometry-distance ranking in the mop-up distribution heuristic with centre-distance ranking; exact collision geometry remains authoritative.

## Dependency/runtime

- Main-network materialization validity is checked before local/component phases so a bad main network fails fast.
- Component-only placement/repopulation still operates on frozen routes and can never trigger routing.
- No global A*, route permutation search, or time-dependent visual degradation was introduced.
