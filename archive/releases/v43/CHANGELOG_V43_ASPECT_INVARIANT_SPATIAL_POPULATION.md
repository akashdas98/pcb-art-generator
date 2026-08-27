# V43 — Aspect-Invariant Spatial Population

## Problem

V42 made local residual cells physically local on long canvases, but left main-chip and component population tied to square-board global counts. A 1200×6248 or 1200×8046 board could therefore contain only 2–3 main chips and a component ecology concentrated near one end while still reporting high residual-service percentages.

## Root cause

The renderer conflated two independent concepts:

1. **entity scale**, correctly derived from the short side / `main_scale`; and
2. **population extent**, incorrectly kept at square-reference global counts and, for components, a fixed 56×56 service grid.

Several routing/search execution caps were likewise square-reference globals.

## V43 correction

- Defines normalized physical territory `T=(W*H)/min(W,H)^2`.
- Main-chip opportunity is stationary per territory: two chips per complete territory plus two independent fractional-territory Bernoulli opportunities.
- Prepared 15–18 collection population repeats per complete territory with fractional thinning.
- Isolated component and residual completion opportunities scale with territory.
- Component and local service grids both keep approximately square-reference physical cell size and transpose under rotation.
- Main/local population work caps scale with territory without changing per-entity probabilities or geometry.
- Main-router bounded searches use spatial indices rather than global all-to-all scans where decision-equivalent.
- Same-snapshot proposal legality is cached only inside one immutable transactional round; stochastic score draws remain independent.
- Planner/render broad-phase clearance reach now includes the largest possible pair-specific moat, preventing thin traces from failing to query nearby thick traces.
- Local planning and render admission include exact frozen rendered-main polylines in addition to per-segment obstacles, closing 45-degree miter-joint clearance blind spots.
- The hard 80% local remainder floor may use a territory-scaled reserve of the ordinary local router if an execution cap ends first; no geometry or service rule is weakened.
- Removed aspect-ratio semantic branches from local target selection; very large candidate sets are bounded by workload size only.
- Corrected a reconstructed double-scaling error so local exact-check allowance is `22000*T`, not `22000*T^2`.

## Test architecture

Four V42 tests whose premises were intentionally superseded were rewritten to the V43 contracts rather than deleted. Additional bounded V43 tests cover population stationarity, rotation invariance, physical grid transposition, per-territory work/cap scaling, long-axis chip spread, workload-only shortlist behavior, single (not quadratic) local-budget scaling, fragmented-region queue ordering, territory-scaled local-region source ceilings, hard-floor reserve semantics, and area-aligned partial-service retargeting.

The authoritative active suite is 63 tests. Release requires the complete suite plus fresh square and extended portrait/landscape acceptance artifacts.

- Final full-production acceptance exposed and fixed a late fragmented-pocket queue tie between integer region IDs and `None`; the queue now uses an explicit numeric priority key and the 59th active regression test covers it.

## Final production acceptance

- 1200×6248: 10 chips `[2,3,3,2]`; 200 component groups `[50,44,50,56]`; component 54.0955%; local remainder 80.1533%; all hard geometry counters zero.
- 6248×1200: 10 chips `[3,2,2,3]`; 204 component groups `[54,50,50,50]`; component 54.1830%; local remainder 80.2944%; all hard geometry counters zero.
- 1200×8046: 13 chips `[3,3,4,3]`; 270 component groups `[72,70,66,62]`; component 54.0034%; local remainder 80.2779%; all hard geometry counters zero. Logical sample 0 passes directly.
