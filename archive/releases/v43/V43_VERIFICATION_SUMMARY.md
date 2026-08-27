# V43 Verification Summary

## Release status

V43 is a verified release under the repository's authoritative active-test architecture.

Authoritative command:

```bash
python run_release_tests.py
```

Result: **63/63 active tests passed; 0 failures; 0 errors; 0 skips; 0 expected failures; 0 manifest mismatches.**

## What V43 verifies

V43 replaces V42's square-board-sized population on extended canvases with one rotation-invariant stationary law over normalized physical territory `T=(W*H)/min(W,H)^2`. Entity scale remains short-side / `main_scale` based; population extent does not.

The release gate retains every live inherited geometry/routing/component contract and adds direct coverage for territory-stationary population, transposed physical service grids, per-territory work/source ceilings, long-axis distribution, workload-only optimization branches, hard-floor reserve behavior, partial-service area targeting, and committed extended acceptance artifacts.

## Fresh square acceptance

### Standard reference — 1200×1200

- chips: 2
- prepared collections: 18
- component residual service: 58.8350%
- local remainder service: 87.7706%
- pure-straight local trace fraction: 5.95%
- main source markers: 71/71 launch traces
- non-octilinear segments: 0
- illegal in-trace turns: 0
- illegal connection-junction turns: 0
- rendered clearance violations: 0
- main/local clearance violations: 0
- local/component clearance violations: 0
- unauthorized component/pathway overlaps: 0

### Difficult reference — 1200×1200

- chips: 2
- prepared collections: 17
- component residual service: 57.3238%
- local remainder service: 83.5079%
- pure-straight local trace fraction: 12.99%
- main source markers: 93/93 launch traces
- all geometry/clearance violation counters: 0

## Final extended production acceptance

All three cases use base seed `7179163421162001120` and **logical sample 0 succeeds directly**.

### 1200×6248 portrait

- normalized territory: 5.2067
- main chips: 10; long-axis quarters `[2,3,3,2]`; span 89.31%
- prepared collections: 86
- total component groups: 200; long-axis quarters `[50,44,50,56]`; span 98.97%
- component grid: 56×292
- component residual service: 54.0955%
- local remainder service: 80.1533%
- main source markers: 427/427 launch traces
- all exact turn/octilinear/clearance counters: 0

### 6248×1200 landscape

- normalized territory: 5.2067
- main chips: 10; long-axis quarters `[3,2,2,3]`; span 92.21%
- prepared collections: 86
- total component groups: 204; long-axis quarters `[54,50,50,50]`; span 98.88%
- component grid: 292×56
- component residual service: 54.1830%
- local remainder service: 80.2944%
- main source markers: 427/427 launch traces
- all exact turn/octilinear/clearance counters: 0

### 1200×8046 portrait upper maintained case

- normalized territory: 6.7050
- main chips: 13; long-axis quarters `[3,3,4,3]`; span 90.33%
- prepared collections: 113
- total component groups: 270; long-axis quarters `[72,70,66,62]`; span 99.20%
- component grid: 56×375
- component residual service: 54.0034%
- local remainder service: 80.2779%
- absolute local service: 36.9251% of the original post-main service field
- hard-floor absolute requirement: 36.7973%
- ordinary hard-floor rescue: 7/7 territory-scaled waves
- partial-service ordinary rescue: 2/7 bounded waves
- main source markers: 541/541 launch traces
- all exact turn/octilinear/clearance counters: 0

## Integration regressions discovered during release proof

The full production acceptance exposed and fixed four issues that bounded unit tests alone did not reveal:

1. mixed integer/`None` residual-region IDs could crash a tied fragmented-pocket priority sort;
2. a square-era per-region local-source ceiling remained globally fixed at 34 instead of scaling per normalized territory;
3. one zero-gain ordinary rescue wave prematurely cancelled the remaining bounded hard-floor reserve;
4. binary "touched-cell" source targeting could disagree with the 16-subcell area service audit near the hard floor, so the final reserve may retarget partially serviced cells while using the same ordinary router and exact geometry rules.

All four now have active regression coverage.
