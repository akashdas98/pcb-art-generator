# V25 — Route-First Residual Fill + Independent Main Scale

V25 changes generation dependency order rather than adding more routing search.

## Architectural change

The active generation order is now:

1. main chips are generated and placed;
2. primary chip-emitted pathways are routed against main chips only;
3. local residual-gap pathways are routed against the frozen main network;
4. all pathway geometry is frozen;
5. collections and isolated capacitors are generated and placed into the residual free field.

Secondary components no longer exist spatially while the router is running. They cannot block a
candidate gesture, force a split, cause traceback, terminate a lane, or otherwise steer the pathway
network.

The existing V24 main/local bundle grammar, branching behavior, thick local accents, source markers,
anti-collapse rules, head-only connection rules, and hard geometry audits remain active.

## Router-side component intent removed

The V24 `component` routing intent is removed from the active planner. V25 routing intentions are
pathway-native: connect, exit, and explore.

Rare pathway-to-small-component relationships are reversed. After routing, an isolated capacitor may
be placed on an eligible free pathway terminal. The component adapts to the route; the route never
searches for a not-yet-existing component.

## Residual component fill

The final component pass samples a soft target in `[0.75, 0.90]` and constructs a bounded seeded set of
representative residual gap sites from the routed board. Larger collections are placed first and small
isolated capacitors fill later pockets.

The active post-route clearances are:

- main chip ↔ secondary component: `42U`
- pathway ↔ non-attached secondary component: `10U`
- secondary component ↔ secondary component: `12U`
- secondary component ↔ frame: `20U`

The historical `170U` pre-route chip-secondary moat is no longer the active final-placement rule; its
routing-reservation purpose is obsolete once components are placed after pathways.

The 75–90% value is gap-site coverage, not literal raw canvas-area packing. Exact transformed geometry
still has final authority. If a pathological component population cannot fit, the sample may restart,
but the frozen route network is never rerouted around components.

## Independent main scale

`V27Renderer(..., main_scale=1.0)` and CLI `--main-scale` now expose an explicit positive master geometry
scale independent of canvas width/height.

Internally:

```text
S_canvas = min(W,H)
S = S_canvas * main_scale
U = S / 1200
```

Thus a 1200×1200 canvas at `main_scale=0.65` remains 1200×1200 while all S/U-derived chips, components,
strokes, clearances, and pathway modules become 65% of default physical size.

The renderer never mutates `main_scale` automatically to solve fit or routing problems.

## Determinism

No new non-deterministic stream is introduced. Post-route component filling uses a seed derived from the
sample seed. Same seed + same canvas + same `main_scale` produces the same result.
