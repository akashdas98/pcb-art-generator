# PCB Art Generator — Session Context

Read this file completely at the start of every session after `AGENTS.md`, then read
`chip_design_language.md` completely before doing any work.

## Authority and active files

- `chip_design_language.md` is the single authoritative specification and must accompany every repository change.
- Its filename is version-neutral; its internal metadata records the active design-language version.
- `pcb_v43_renderer.py` is the active renderer.
- `tests/active/test_pcb_v43_renderer.py` is the mandatory active regression suite.
- `tests/ACTIVE_TEST_MANIFEST.json` is the exact active-test contract.
- `V43_RENDERER_README.md` is the active operator guide.
- `examples/` contains fresh V43 square and extended portrait/landscape acceptance artifacts.
- `archive/releases/v42/` preserves the superseded complete V42 release.
- `archive/` otherwise contains immutable historical releases and history.

## Architectural contract

The active phase order is:

1. place main chips across the full normalized physical territory;
2. route and freeze the main-chip network against chips only;
3. place and freeze coherent residual components across the full physical territory;
4. route local-gap lines around the exact frozen main network and components;
5. perform exact rendered geometry, clearance, marker, distribution, and determinism audits.

The authoritative specification contains the complete numeric and algorithmic contract. This file is orientation,
not a substitute for reading it.

## Current maintenance state

- V43 has one aspect-invariant generative law: portrait, landscape, and square canvases differ only in physical territory/orientation, never in visual-mode rules.
- Entity dimensions remain tied to the short-side design basis and `main_scale`; population opportunity is tied to normalized territory `T=(W*H)/min(W,H)^2` and is independent of `main_scale`.
- Main chips, prepared component collections, isolated components, residual completion opportunities, and population-related work allowances are stationary per normalized territory.
- Both component and local service grids preserve approximately square-reference physical cell size and transpose under width/height rotation.
- Spatial broad phases and same-snapshot legality caches may remove impossible/global comparisons, but exact geometry/clearance decisions remain authoritative.
- Local planning and materialization include exact frozen rendered-main polylines, preventing miter-joint clearance blind spots.
- Component-first 50–60% service, local 80–90% of remainder, exact 0/±45-degree turns, source markers, hard clearances, and deterministic version-local output remain normative.
- The authoritative release status is determined only by `python run_release_tests.py`; its result must have no failures, errors, skips, expected failures, or manifest mismatch.

## Verification commands

```powershell
python -m py_compile pcb_v43_renderer.py tests/active/test_pcb_v43_renderer.py run_release_tests.py run_stress_tests.py
python run_release_tests.py
```

Use focused tests while iterating, then run the complete active suite and the maintained production acceptance renders.
