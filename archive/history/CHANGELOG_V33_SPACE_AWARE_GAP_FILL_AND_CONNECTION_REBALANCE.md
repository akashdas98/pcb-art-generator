# V33 — Space-Aware Gap Fill and Connection Rebalance

V33 retains the V31 transactional-parallel routing core, V32 source-egress/family protection, route-first dependency order, and independent `main_scale`. It fixes the compositional regressions visible after V32 without restoring component obstacles or global route search.

## Main chips and main network

- Main-chip pair clearance target increased to **210U** and chip placement strongly prefers spread-out solutions.
- Cross-chip networking appetite is restored; accepted multi-chip routing must produce at least one true cross-chip connection.
- Added a bounded post-main terminal connection sweep using exact geometry.
- All launched main lanes must remain visible and a whole emitted side may not be accepted as only short terminated traces (`pathway_main_stalled_side_count == 0`).
- Unauthorized line/stroke overlaps remain hard failures; final cleanup may not silently remove a main lane.

## Local gap network

- Replaced the coarse global gap heuristic with a connected **24×24 residual-region field**.
- Regions carry area, spans, center, size class, and principal orientation.
- Local gap target is now **40–50%** of residual gap influence area (bounded final-line overshoot may reach roughly 55%).
- Ordinary local fillers are born as **independent singleton lines**, not pre-bundled roots.
- Small regions receive fewer/shorter/thinner fillers; large regions receive proportionally more/longer activity.
- Per-region source capacity and unmet-area weighting stop one large room from monopolizing filler sources.
- Compatible independent local lines in the same region have a deterministic **50%** chance to travel as a temporary parallel pair for **2–4 atomic rounds**, then release and resume independent gap seeking. Each line may bundle at most once.
- Existing local 3–5× branching boost and 50% frame-exit factor are retained.

## Components

- Replaced representative point-site coverage as the governing metric with connected **28×28 residual-region analysis**.
- Component service target is **90–94% of remaining connected residual-region area**.
- Large established collections are fitted first; bounded gap-sized capacitors/dots/dashes/squares/circles mop up unserved pockets according to local region size/capacity.
- Density target scales with residual cells, capped at 46 accepted component placement sets; mop-up adds at most 28 extra fillers.
- Unauthorized component/pathway overlap is a hard failure. Only an explicitly designated terminal attachment may contact a path.
- Component recovery remains component-only against frozen routes; it never triggers rerouting.

## Runtime

- Batch default is one full sample attempt per logical index before deterministic skip. This prevents one impossible protected-routing topology from multiplying full reroutes. `--max-sample-restarts` still permits explicit overrides.

## Historical policy

All V4–V32 changelog and verification files remain historical records and are not rewritten by V33.
