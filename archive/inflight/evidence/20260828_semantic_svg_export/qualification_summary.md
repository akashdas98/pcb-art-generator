# 2026-08-28 semantic SVG export qualification summary

## Change summary

Implemented semantic classification in the final SVG export.

The exported SVG now includes:
- root schema/version attributes,
- `semantic_svg` metadata inside `<metadata>`,
- semantic entity grouping for main chips, main pathways, local pathways, and component groups,
- stable primitive ids plus `class` / `data-*` classification attributes,
- trace endpoint and marker-role metadata intended for downstream behavior/effect passes.

This was an export-layer change only; geometry generation itself was not intentionally changed.

## Qualification performed

### Static / compile
- `python -m py_compile pcb_v48_renderer.py` — PASS
- `python tools/assert_single_canonical_repo.py` — PASS

### Active release gate
The active suite contains 190 tests after adding the semantic SVG regression tests.
Because a single monolithic invocation hit the execution boundary in this environment, the suite was executed deterministically in 10 batches (`batch_01` .. `batch_10`).

Aggregate result:
- **190/190 active tests PASS**

Focused semantic / production subset:
- `ProductionUseContractTests` + `SemanticSvgExportTests` — **4/4 PASS**

Focused behavioral subset:
- `test_batch_seed_totality_never_skips_failed_logical_seed`
- `test_pathways_are_deterministic_without_pathway_seed_search`
- `test_bundle_gesture_pathways_are_direct_modular_and_collision_clean`
- `test_component_hard_floor_completion_is_not_stopped_by_legacy_global_filler_cap`

Result:
- **4/4 PASS**

### Maintained stress
- `python -m unittest tests.stress.geometry_stress` — **1/1 PASS**

### Direct smoke / inspection
- Rendered one direct square sample and inspected the produced SVG.
- Verified presence of:
  - `data-schema="pcb-art-semantic-svg"`
  - entity-level semantic `<g>` attributes
  - primitive-level ids/classes/data attributes
  - `semantic_svg` metadata payload

Result:
- PASS
