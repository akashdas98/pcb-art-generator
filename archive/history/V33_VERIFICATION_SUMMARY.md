# V33 Verification Summary

## Direct architecture regressions

- 12/12 transactional/source-egress direct invariants pass, including atomic order invariance, causal blocker rollback, pre-egress split prohibition, source reservation reactivation, same-family HOLD, foreign-head visibility, escaped-frame clipping, cached component keepouts, and no route restart from component failure.
- V33 space-aware rebalance contract passes on seed `20260806` at 1000×1000.
- Route-first dependency probe confirms the router receives only main chips.
- Independent master-scale test passes.
- Holistic transactional routing regression passes.
- Same-seed deterministic routing regression passes.

## Hard-geometry seeds

Seed `20260806`, 1000×1000, logical samples checked individually:

- sample 0: 58/58 main lanes visible, 10 cross-chip connections, local coverage 46.76%, component residual-region service 95.64%.
- sample 1: 65/65 main lanes visible, 10 cross-chip connections, local coverage 51.64% (bounded last-ribbon overshoot), component service 96.29%.
- sample 2: 64/64 main lanes visible, 7 cross-chip connections, local coverage 42.22%, component service 97.88%.

All three checks reported zero static intersections, unmarked overlaps/stroke overlaps, compensating zigzags, tiny terminal traces, illegal mid-line/multiple connections, terminal-marker overlaps, duplicate cleanup, and intersection cleanup.

## Three-chip stress case

Seed `65`, logical sample 0, default scale:

- 3 main chips.
- 88/88 main launch lanes visible.
- 8 cross-chip connections.
- 42.81% local gap coverage.
- 90.72% connected residual-region component service.
- 23 independent local sources, 4 temporary bundle pairs.
- zero unauthorized component/pathway overlap and zero unmarked stroke overlap.

## Default runtime checks

Final-source literal/no-seed runs observed:

- 14.58 s: logical sample 0, 64/64 main lanes, 9 cross-chip connections, 53.9% local coverage, 91.0% component service, zero unauthorized overlap.
- 17.15 s: logical sample 0, 67/67 main lanes, 8 cross-chip connections, 42.7% local coverage, 93.8% component service, zero unauthorized overlap.

Captured slow seed `15486847425892096920` exposed an expensive impossible protected-routing logical sample. With the V33 one-attempt-per-logical-index batch default, it deterministically skipped logical indices 0 and 1 and emitted logical sample 2 in 25.81 s with 61/61 main lanes, 9 cross-chip connections, 47.09% local coverage, and 92.83% component service.

## Historical audit

37 pre-V33 changelog/verification files were SHA-256 compared against the released V32 package: **0 changed**.

## Scope note

The geometry-heavy aggregate unittest that launches three subprocess samples can exceed a single harness wall-clock window when run as one test; its three constituent samples were verified individually as listed above. No hard invariant was weakened to make that aggregate faster.

## Final packaged-zip verification

A fresh extraction of the packaged archive was run literally as:

```bash
python pcb_v33_renderer.py
```

with no seed, no `main_scale`, and no retry/search overrides. It completed in **15.55 s** on logical sample 0 and emitted one SVG with:

- 2 main chips;
- 63/63 main launch lanes visible;
- 4 true cross-chip connections;
- 43.26% local-gap influence coverage;
- 97.06% served residual-region component area (target can overshoot because connected regions are indivisible);
- zero unmarked line/stroke overlap;
- zero unauthorized component/pathway overlap.

The emitted SVG was rasterized and visually inspected for gross layout/collision regressions after the numeric audit.
