# Residual-fill mosaic + opportunistic cross-chip qualification — 2026-08-27

## Promotion decision

**ACCEPT / PROMOTE** renderer `b965a294b339684ccea1e95aae848c79d9cb232295a5666effd83dc844a7ca53` after the final documentation-complete release/stress gate.
This change closes the three user-supplied low-density `cross-chip connection invariant not realized` errors and replaces
macroscopic component-vs-LOCAL territorial segregation with a shared residual spatial mosaic.

## Error repair

The three user logs are retained beside this file. All three were generated from the 18:05 authority at `1:1 @ 0.35`,
main-chip density `0.25`, with MAIN run-length `0.25`, `0.5`, and `1.0`. They all fail at the obsolete board-level assertion
`cross-chip connection invariant not realized`. The production rule is now the narrower intended contract: if an already-
legal foreign-main-chip connection is encountered it wins immediately; a board is not required to manufacture one.

## Residual design-language repair

- Components and LOCAL lines share the same board-scale residual territory even though components are admitted first for
  collision ownership.
- Component and LOCAL cluster cardinality has full seeded support from 1 through 12; singulars are normal and 10--12 is a
  minority large-cluster outcome.
- Prepared component clusters and completion component clusters are separate bounded composition units.
- Completion fillers no longer appear as hundreds of nominal singleton spill clusters.
- A fixed 8x8 normalized-load composition mosaic disperses *cluster anchors* before connected-region quota chooses exact
  service cells, preventing adjacent bounded clusters from recombining visually into a megacluster.
- LOCAL large residual rooms are partitioned into compact 1--12-source parcels; ordinary source allocation services those
  parcels instead of treating one connected room as one line cluster.
- Component constructors, exact clearance, fill percentages, LOCAL gesture generation/routing/recovery, and MAIN routing
  architecture are unchanged.

## Correctness / regression gates

- Active release gate: **188/188 PASS**, zero failures/errors/skips/xfails.
- Maintained geometry stress: **1/1 PASS**.
- Permanent regressions cover opportunistic zero-cross-chip acceptance, component 1--12 support, component population
  partitioning, macroscopic completion-cluster dispersion, and LOCAL first-wave parcel dispersion.

## Exact sparse/fine production screens

Base seed `20260827184756`, `1:1 @ 0.35`, density `0.25`:

| MAIN run multiplier | Result | Stalled sides | MAIN short | Unaccounted | Cross-chip joins | Component clusters / max | LOCAL sources |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.25 | PASS | 0 | 0 | 0 | 0 | 120 / 9 | 930 |
| 0.5 | PASS | 0 | 0 | 0 | 0 | 133 / 11 | 974 |
| 1.0 | PASS | 0 | 0 | 0 | 1 | 127 / 12 | 1007 |

The `0.25` board contains 77 completion clusters, 30 singleton component clusters, and LOCAL clusters reaching the intended
12-source upper bound. Visual PNG/SVG evidence is retained under `sparse_035_detached/`.

## Sparse aspect-ratio screens

Same base seed, density `0.25`, run multiplier `0.25`, `scale=0.75`:

| Aspect | Result | Stalled / short / unaccounted | Component clusters / max | LOCAL sources |
| --- | --- | --- | ---: | ---: |
| 1:6 | PASS | 0 / 0 / 0 | 153 / 12 | 1336 |
| 6:1 | PASS | 0 / 0 / 0 | 177 / 12 | 1347 |

Visual evidence is retained under `strips_sparse_075/` and shows component clusters distributed along the full strip with
LOCAL pathways occupying the same broad territory rather than separate macroscopic zones.

## Normalized efficiency — seeds 102 + 104, 0.75 -> 0.5

Territory growth reference: `2.25x`.

| Category | BEFORE CPU growth | BEFORE work growth | BEFORE CPU/work | AFTER CPU growth | AFTER work growth | AFTER CPU/work |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Components / placed component | 2.708x | 2.373x | 1.141x | 1.982x | 2.285x | **0.867x** |
| LOCAL / independent source | 2.487x | 2.205x | 1.128x | 2.506x | 2.389x | **1.049x** |
| Residual composite explicit work | 2.531x | 2.218x | 1.141x | 2.397x | 2.397x | **1.000x** |
| Whole-renderer composite work | 2.551x | 2.238x | 1.140x | 2.375x | 2.367x | **1.003x** |

The final mosaic changes legitimate spatial service workload but does not worsen normalized scaling. No new scale-dependent
all-pairs/global search term was introduced; the macroscopic anchor scheduler is a fixed 64-tile composition pass.

## Authority

- Previous authority: `5d8624de9d2b5ec5b5ba7dac7fed169653074d7301751f8b1b1558e870dba98b`.
- Promoted renderer: `b965a294b339684ccea1e95aae848c79d9cb232295a5666effd83dc844a7ca53`.
- Active test manifest SHA-256: `395db697f601540a28a28f2d67073081746f204ef9e491c462bb5996b41060a0`.
- Raw source delta: `authority_1805_to_residual_mosaic.diff`.
- Raw user error ZIPs are retained in this evidence directory.
