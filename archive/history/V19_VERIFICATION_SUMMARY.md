# V19 verification summary

V19 changes placement clearances, static-path keepouts, branching tendency, bundled termination behavior, and repair depth while retaining V18's synchronous/holistic architecture.

## Targeted regression checks on finalized code

The directly affected regression tests pass after the final 170U spatial-query fix:

- `test_secondary_components_keep_main_chip_breathing_room`
- `test_bundle_gesture_pathways_are_direct_modular_and_collision_clean`
- `test_holistic_connections_loop_guard_and_extended_repair_are_active`

These checks cover the new chip edge/moat rules, 70–90% launch-side occupancy, 1.50–1.80 branch multiplier, seven-attempt repair profile, minimum foreign-static keepout, real cross-chip joins, anti-loop behavior, no collapsed traces, no unmarked crossings, and no compensating zigzags.

A monolithic invocation of the complete historical suite is substantially slower under the stronger static placement and repair settings; the path-heavy aggregate arbitrary-seed test exceeded the execution wrapper timeout. No assertion failure was observed in the targeted final-code regressions above.

## Reference V19 visual probe

Base seed `0x20260806`, logical sample 0:

- chips: 2
- collections: 17
- visible launch coverage minimum: **72.39%**
- cross-chip joins: **7**
- pathway splits: **85**
- recovery fragmentations: **13**
- effective branch multiplier: **1.5368×**
- minimum foreign-static trace clearance: **4.817U** (required: 4U)
- static intersections: **0**
- unmarked crossings: **0**
- collapsed overlaps: **0**
- compensating zigzags: **0**

## Three-chip / maximum-secondary stress case

Base seed `12345`, logical sample 18, restart 0:

- chips: **3**
- collections: **18**
- minimum final chip-to-frame gap: **199.89U** (required: 120U)
- minimum chip-to-secondary gap: **172.59U** (required: 170U)
- visible launch coverage minimum: **72.86%**
- cross-chip joins: **9**
- pathway splits: **120**
- recovery fragmentations: **35**
- minimum foreign-static trace clearance: **4.956U** (required: 4U)
- static intersections: **0**
- unmarked crossings: **0**
- collapsed overlaps: **0**
- compensating zigzags: **0**

This stress case specifically verifies that the doubled 170U moat plus inward chip placement remains geometrically feasible even at 3 chips / 18 secondary collections.

## Important placement bug fixed

Before V19's final patch, the pair rule could request an 85U/170U chip-secondary clearance while the placement spatial lookup queried only a 60U neighborhood. Pairs outside that query window were not prospectively tested and could survive until final validation. V19 expands the lookup to `max(60U, chip_secondary_clearance)`, so the configured moat is enforced during placement itself rather than only discovered after the board has already been laid out.
