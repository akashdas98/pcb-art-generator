# V45 — True Zoom / Logical-Area Population

V45 supersedes V44's scale-stationary-population assumption.

## Corrected scale semantics

- Added `canvas_territory_scale()` for the raw aspect-ratio territory visible at scale 1.
- Redefined `population_area_scale()` as `canvas_territory_scale() / main_scale²`.
- Main-chip opportunities, prepared collection population, isolated capacitors, population/service caps, and design-detail capacity now share this logical-area basis.
- `design_detail_area_scale()` no longer applies a second inverse-square factor; it equals logical population area.

## Spatial corrections

- Removed the `0.265 * raw_canvas_short_side` floor from chip-to-chip clearance. Chip clearance now scales with design geometry (`430U`), so newly exposed logical territory can actually be occupied.
- Main congestion/coverage grid resolution now follows design-local scale, matching residual service grids.
- Main gesture-check allowance scales once with logical area, rather than multiplying logical area by another inverse-distance factor.

## Router scalability hardening

True zoom exposes many more simultaneous primary fronts. V45 therefore removes several scale-1-hidden costs without weakening exact legality:

- static ranking probes use spatial hashes and conservative AABB distance;
- proposal conflict geometry is cached;
- same-round conflict checks reject impossible AABB pairs before GEOS operations;
- proposal-pool conflict grouping uses a spatial index instead of bucket-wide all-pairs expansion;
- look-ahead ranks its six tiny future options cheaply, exact-checking the strongest shortlist with a fallback if those are blocked;
- route intent/exit targets use design-local journey horizons instead of forcing fine-scale traces to chase scale-1-global destinations;
- chip placement queries the full scaled `430U` chip-to-chip moat before exact geometry admission;
- the synchronized recovery horizon is 24–28 rounds, while per-front route grammar/journey budgets are unchanged;
- post-horizon expensive beam search is reserved for immature/protected launches; mature legal routes end locally instead of all being forced toward the physical SVG frame;
- intact source-family settlement is bounded to two ticks per pass.

Final route collision, clearance, exact-octilinear, source-egress, and frozen-geometry gates remain exact.

## Tests

The old tests that asserted population must be independent of `main_scale` were replaced by tests that lock the corrected contract:

- inverse-square logical population area;
- rotation invariance at equal scale;
- increased chip and prepared-component opportunity at fine scale;
- design-local main and service grids;
- one logical-area work multiplier, not double scaling.

`python run_release_tests.py` passes 73/73 active tests with zero failures/errors/skips/xfails.

Fresh true-zoom evidence:

- 1200×1200, `main_scale=0.35`, seed 45035: 16 primary chips and 131 prepared collections.
- 1200×6248, `main_scale=0.35`, seed 45036: 86 primary chips, distributed `[22, 22, 18, 24]` across long-axis quarters.
- Real 1200×1200/0.35 main-network production run, seed 45035: 682 visible launch traces, 79 cross-chip connections, 25 decision rounds, 67,634 exact gesture checks, and zero hard overlap/clearance/octilinear/static-intersection violations.


## 2026-08-15 forensic status correction

The prior V45 release-PASS designation is revoked. A real long `main_scale=0.35` production attempt exposed performance/algorithmic scaling failures not exercised by the active 73-test gate. No renderer behavior is changed by this status correction. See `V45_SCALE035_FORENSIC_AUDIT.md`.
