# V29 — Gap Coverage, Early Recovery, Terminal Clearance, Capacitor Scale

V29 keeps V28's route-first generation order:

1. main chips,
2. primary pathways,
3. local gap pathways,
4. residual components.

No secondary component geometry is restored to the router.

## Routing changes

- Launching fronts now enter bounded reroute/recovery after the first failed movement instead of waiting through repeated early hard blocks.
- Launching fronts evaluate three bounded proposal variants and receive six recovery-mode rounds. The global reroute budget remains bounded at 7.
- Head-to-head connection eligibility begins after one accepted gesture. Close, facing young heads from different chips receive deterministic exact-checked connection priority out to 5 routing modules, so two newly emerged networks can join instead of spending recovery budget blocking each other.
- Terminal survival checks use the shortest actually materialized lane rather than bundle-centre travel, preventing an inside turn lane from being treated as a valid long terminal when it is still physically short.
- Local-gap recovery is deliberately cheaper than main recovery: at most 4 reroute attempts and at most 2 traceback gestures per attempt.

## Local-gap composition

- The local phase now measures representative residual open cells after the primary network freezes.
- A seeded soft target of `Uniform(0.38, 0.42)` of those residual cells is used as the local-line coverage objective.
- Up to three bounded adaptive waves may be launched. Later waves are sized from the measured remaining coverage deficit rather than a fixed source-count quota.
- Ordinary local roots contain 3–4 traces.
- Local bundles receive a seeded `3.0–5.0×` branch-probability multiplier relative to normal branch behavior.
- Local branch children attempt visible `±45°` peel directions toward uncovered cells in their current gap; straight continuation is only a bounded fallback when the preferred peel is not legal.
- Local frame-exit permission is multiplied by `0.50`. Near-frame interior pivots and residual-gap targets are preferred, and the persistence tail does not forcibly convert local bundles to exit intent.
- The existing 15–30% special-thick local trace population intent remains active cumulatively across adaptive waves.

## Terminal-head clearance

- Free terminal heads receive an additional `4.5U` visual clearance target from foreign pathway geometry.
- This is solved after topology is frozen by backing the terminal polyline up along its already-valid path before placing the endpoint marker.
- Backoff is not a route search and does not reopen routing contention.
- Candidate backoff positions preserve the existing visible minimum-segment invariant and prioritize zero terminal-marker overlap.

## Component fill

- Residual component gap-site fill target changes from 75–90% to 80–90% after local routing is frozen.
- Component placement still never causes pathway rerouting.

## Capacitor size

The complete active capacitor radius expression is shifted upward by 50%:

- V28: `r = (4.2 + 8.7*R^0.90)U`
- V29: `r = (6.3 + 13.05*R^0.90)U`

This is exactly `1.5×` the V28 radius for every sampled driver value `R`.

## Version naming

V29 continues the single active version-number scheme. Historical changelogs and verification files retain their original names and content.
