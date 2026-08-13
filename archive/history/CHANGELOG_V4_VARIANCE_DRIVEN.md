# v4 variance-driven refactor

This revision removes artificial numeric option menus while preserving genuinely categorical visual operations.

## Replaced with procedural variance

- main-chip short-side size bins -> continuous center-biased interval
- main-chip aspect bins -> continuous high-side-biased interval
- motif-count preset table -> continuous latent motif complexity -> integer projection
- M1 border-count menu -> conditional probabilistic growth
- M2 row/column tables -> safe-rectangle-derived bounded dimensions
- M3 band/mark count tables -> fit-derived bounded dimensions
- M7 row/column tables -> safe-rectangle-derived bounded dimensions
- M8 long/short span modes -> one continuous high-span-biased distribution
- M8 tight/moderate packing modes -> one continuous tight-biased gap distribution
- collection complexity tiers/quotas -> continuous latent richness -> family count
- ordinary entity-count table -> continuous center-biased population projection
- ordinary grid row presets -> count + anisotropy-derived dimensions
- ordinary dot standard/accent modes -> one continuous heavy-low-tail radius distribution
- mini-IC aspect bins -> one continuous aspect distribution
- mini-IC terminal central/tail modes -> one continuous center-biased terminal-length distribution
- IC single/separate/array mode menu -> singleton condition + connectivity probability + procedural dimensions
- IC rows×columns table -> continuous extent/anisotropy dimension generator
- dense rows×columns table -> continuous extent/anisotropy dimension generator

## Still categorical because the operation itself differs

Examples retained intentionally:

- motif identity M1–M8
- horizontal vs vertical body orientation
- square vs rounded corners
- filled vs hollow vs mixed state
- ordinary lattice operation (strip / orthogonal / diagonal / staggered)
- M2 topology (filled / perimeter / compact)
- terminal-side topology
- orthogonal vs row-shifted vs column-shifted dense lattice

These are visual operations, not numeric preset shapes.

## Additional execution corrections

- connected IC arrays remain exact terminal-tip contact arrays
- dense diamond grids use half-step row/column staggering rather than a 45-degree square-grid rotation
- M5 corner curves retain the shifted near-corner stand-off and expanded curvature range
- special family quotas remain exact (`IC=0.625N`, `dense=0.845N`, border=`0.700N`)
- collection packing now uses directional AABB support instead of circumcircle radii, preserving clearance while reducing unnecessary empty space
- deterministic hierarchical deadlock fallback skips pathological logical sample indices without resetting the shared batch uniqueness domain
