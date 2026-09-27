# Semantic SVG export contract

This document describes the machine-semantic classification now emitted in the **final SVG output**.

## Goal

Downstream tools/LLMs should be able to inspect the rendered SVG and answer questions like:
- which geometry is a main chip?
- which paths are main launch traces vs LOCAL filler traces?
- which circles are source/terminal/junction markers?
- which geometry belongs to component groups / residual clusters?
- where does a given trace start and end?

The export is meant to support secondary behavior/effect passes without re-deriving the whole scene from untyped geometry.

## Root SVG

The root `<svg>` includes:
- `data-schema="pcb-art-semantic-svg"`
- `data-schema-version="1.0"`
- `data-renderer-version="V48"`
- semantic entity/primitive counts

The existing `<metadata>` JSON report is preserved and extended with a top-level `semantic_svg` object.

## Entity groups

Every rendered `Group` is exported as an SVG `<g>` with semantic attributes.

Primary entity kinds:
- `main-chip`
- `main-pathway`
- `local-pathway`
- `component-group`

Representative exported attributes include:
- `data-entity-id`
- `data-placement-kind`
- `data-kind`
- `data-chip-id`
- `data-source-chip-id`
- `data-launch-side`
- `data-component-family`
- `data-component-families`
- `data-cluster-id`

The `class` attribute mirrors the entity type for CSS/DOM queries.

## Primitive geometry

Every primitive inside a group receives a stable SVG id plus semantic classification.

Representative primitive kinds:
- `main-trace`
- `local-trace`
- `main-trace-marker`
- `local-trace-marker`
- `main-chip-geometry`
- `component-geometry`

Representative primitive attributes include:
- `id`
- `class`
- `data-kind`
- `data-parent-entity-id`
- `data-primitive-index`
- `data-svg-type`

### Trace primitives

Polyline/line/quadratic trace primitives additionally expose:
- `data-start-x`, `data-start-y`
- `data-end-x`, `data-end-y`
- `data-point-count` (for polylines)
- `data-stroke-width`

### Marker primitives

Pathway circles additionally expose:
- `data-marker-role`

Current inferred roles:
- `source-marker`
- `terminal-marker`
- `endpoint-marker`
- `junction-marker`

## Metadata payload

`metadata.semantic_svg` contains:
- schema/version
- renderer version
- entity count / primitive count
- entity kind counts
- a machine-readable entity list
- a machine-readable primitive list

The metadata avoids duplicating full polyline point payloads because those are already present in the SVG DOM. Instead it provides classification, ownership, bounds, and lightweight summary fields.

## Example downstream use

A downstream tool can now:
1. select all `.pcb-main-trace` primitives,
2. pick one occasionally,
3. launch a glow particle from its `data-start-*` coordinates,
4. follow the trace geometry from the SVG `points` attribute,
5. detect nearby `.pcb-component-geometry` / `.pcb-local-trace` primitives,
6. decide whether to propagate the effect onward.

## Compatibility

This change does **not** change the rendered geometry itself. It is an export/annotation layer over the final output. Existing visual consumers remain valid; machine consumers gain explicit semantics.
