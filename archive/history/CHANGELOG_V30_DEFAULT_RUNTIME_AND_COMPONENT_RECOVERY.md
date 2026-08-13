# V30 — Default Runtime and Component-Recovery Correction

## Trigger

An untouched V29 default invocation (`count=1`, no seed, no `main-scale`, no benchmark/test seed,
no search-budget or retry/calibration overrides) was observed to produce no SVG within a five-minute
execution window. This is a release-blocking runtime regression; default generation must not rely on a
lucky seed.

## Root causes found

1. **Residual-fill hot-loop regression.** `place_residual_components()` correctly precomputed buffered
   chip/pathway unions for its normal site-placement path, but the 720-candidate whole-field fallback
   called `_component_candidate_valid()` without passing those cached unions. Every fallback candidate
   could therefore rebuild the complete buffered routed-network union. V29's ~40% local network and
   1.5× capacitor size made fallback more likely and made that accidental recomputation much more costly.
2. **Late component-only rejection.** Component template generation/calibration, ordinary-family
   coverage, scale checks, dense balance, IC-contact checks, and uniqueness were still allowed to fail
   after routing. Those failures caused an expensive routed board to be discarded even though the
   failure had no dependency on route geometry.
3. **Post-route layout failure could multiply routing work.** A failed final component layout used the
   complete-sample retry path instead of first exhausting component-only alternatives on the already
   frozen pathway network.
4. **Ordinary-family assignment could leave a known-invalid coverage result.** The bounded swap repair
   could stop without achieving the minimum two occurrences of each required ordinary family and defer
   discovery until later validation.

## V30 corrections

- The whole-field component fallback always receives and reuses the precomputed chip and pathway
  keepout unions. Rebuilding the complete routed-network union inside a fallback candidate is forbidden.
- Non-spatial component templates are generated/calibrated before routing. They have no canvas position,
  are not added to routing occupancy, and cannot influence pathway decisions.
- Template-only validation now happens before `generate_pathways()`: collection scale calibration,
  special-family quotas, ordinary-family coverage, dense-shape balance, IC required contacts, and
  collection uniqueness.
- If the ordinary-family assignment repair cannot achieve required coverage, the assignment is rejected
  immediately before any geometry/routing work.
- Final component placement runs on the frozen main+local pathway network and receives bounded
  deterministic layout retries.
- If needed, bounded alternate component populations are regenerated/calibrated and placed against the
  same frozen routes. This does not invoke pathway traceback or rerouting.
- Successful reports explicitly record:
  - `component_templates_prepared_before_routing = true`
  - `route_restarted_for_component_failure = false`
- No elapsed-time value influences generation; fixes are deterministic dependency/work corrections.
- Final arbitrary-seed verification exposed one pre-existing materialization-only short `A→B→A`
  terminal twitch. V30 suppresses such free terminal/escaped leaves at materialization rather than
  rendering the hard zigzag violation or invoking route search. Connected traces remain governed by
  the existing connection-leg zigzag guard.

## What did not change

- Main chips remain the only static objects present spatially during primary routing.
- Main routing, ~38–42% local-gap routing, 3–5× local branch tendency, half-rate local frame exits,
  terminal-head backoff, 1.5× capacitor radius range, and 80–90% residual component gap-site target are
  unchanged from V29.
- No A*, global route search, route-seed search, or component-driven route search was added.
- `main_scale` behavior is unchanged.
- Historical changelog/verification files are retained as history and are not rewritten.
