# V41 Renderer

V41 is a focused geometry-correctness release built on V40. It fixes a final-materialization frame-clipping bug exposed by extreme portrait canvases such as 1200×6248 and 1200×8046.

## Root cause

Escaped routes are clipped to their first visible canvas-frame crossing. When the final in-frame fragment was shorter than 0.10 routing module, V40 attempted to remove that microscopic tail. The code comment correctly said to extend the previous visible leg to the frame, but the implementation instead moved the previous vertex to the *current* leg's frame crossing. After a 45-degree leg followed by a tiny horizontal/vertical escape, that move skewed the incoming diagonal and the strict final audit correctly rejected it as non-octilinear.

V41 extends the actual previous octilinear leg along its own declared 8-way heading to its frame crossing. The hard exact-octilinear audit remains unchanged and is not weakened.

## Generate

```bash
python pcb_v41_renderer.py --width 1200 --height 1200 --count 1 --out-dir output
python pcb_v41_renderer.py --width 1200 --height 6248 --count 1 --out-dir output
```

All established arguments remain available, including `--seed`, `--main-scale`, logical-sample limits, and deadlock-skip controls.

## Authoritative release test

```bash
python run_release_tests.py
```

A release is not a pass unless that command exits 0 and the active manifest exactly matches discovery.

## Tall-canvas regression coverage

The active suite contains a bounded synthetic regression reproducing the exact malformed-tail mechanism at heights 6248 and 8046. `tests/stress/geometry_stress.py` additionally contains the real seed-1 tall main-network probe for those two heights.

V41 also ships fresh reference and difficult production snapshots under `examples/` because this is a behavioral renderer change and V40's inherited V39 snapshot is therefore not eligible for carry-forward.
