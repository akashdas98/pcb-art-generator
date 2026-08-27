# V42 Verification Summary

## Release status

V42 is a verified release under the repository's authoritative active-test architecture.

Authoritative command:

```bash
python run_release_tests.py
```

Result: **47/47 active tests passed; 0 failures; 0 errors; 0 skips; 0 expected failures; 0 manifest mismatches.**

## Scope

V42 addresses tall-canvas local-fill scaling/performance without weakening geometry or density semantics. The component population policy remains unchanged; only local residual bookkeeping/work allocation becomes aspect-consistent.

## Fresh square acceptance

### Standard reference

- component residual service: 58.91%
- local remainder service: 86.48%
- non-octilinear segments: 0
- illegal turns: 0
- illegal connection-junction turns: 0
- unmarked clearance violations: 0
- main source markers: 71/71 launch traces

### Difficult reference

- component residual service: 56.99%
- local remainder service: 80.33%
- non-octilinear segments: 0
- illegal turns: 0
- illegal connection-junction turns: 0
- unmarked clearance violations: 0
- main source markers: 93/93 launch traces

## Tall acceptance

Deterministic base seed `1`, logical sample `0`:

### 1200×6248

- derived sample seed: `7179163421162001120`
- component service: `0.5401509622295365`
- local service of post-component remainder: `0.8380681044488534`
- absolute local service of original post-main field: `0.3853848114169215`
- non-octilinear segments: 0
- illegal in-trace turns: 0
- illegal junction turns: 0
- unmarked clearance violations: 0
- main/local clearance violations: 0
- local/component clearance violations: 0
- component/pathway unauthorized overlaps: 0

### 1200×8046

- derived sample seed: `7179163421162001120`
- component service: `0.5526470395692655`
- local service of post-component remainder: `0.8308606206719295`
- absolute local service of original post-main field: `0.37168795836290514`
- non-octilinear segments: 0
- illegal in-trace turns: 0
- illegal junction turns: 0
- unmarked clearance violations: 0
- main/local clearance violations: 0
- local/component clearance violations: 0
- component/pathway unauthorized overlaps: 0

The tall acceptance artifacts were captured deterministically from the same production phase pipeline while profiling phases separately in the tool environment. They establish output/geometry/service behavior; they are not presented as a monolithic wall-clock benchmark.

## Active regression additions

V42 adds direct active coverage that:

- local grid cells retain approximately reference physical size on portrait and landscape extreme ratios;
- the component population grid remains fixed rather than multiplying with canvas aspect ratio;
- tall local computational allowance scales sublinearly with area and dense-tail cleanup remains bounded.

The V41 microscopic escape-tail regression remains active as well.
