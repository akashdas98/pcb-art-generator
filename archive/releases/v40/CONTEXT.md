# PCB Art Generator — Session Context

Read this file completely at the start of every session after `AGENTS.md`, then read
`chip_design_language.md` completely before doing any work.

## Authority and active files

- `chip_design_language.md` is the single authoritative specification and must accompany every repository change.
- Its filename is version-neutral; its internal metadata records the active design-language version.
- `pcb_v40_renderer.py` is the active renderer.
- `archive/releases/v39/pcb_v39_renderer.py` is the mechanically compared V40 behavioral baseline.
- `tests/active/test_pcb_v40_renderer.py` is the mandatory active regression suite.
- `tests/ACTIVE_TEST_MANIFEST.json` is the exact active-test contract.
- `V40_RENDERER_README.md` is the active operator guide.
- `examples/` contains the maintained V39 reference artifacts inherited by behavior-equivalent V40.
- `archive/` contains immutable historical releases and history.

## Architectural contract

The active phase order is:

1. place main chips;
2. route and freeze the main-chip network against chips only;
3. place and freeze coherent residual components;
4. route local-gap lines around the frozen main network and components;
5. perform exact rendered geometry, clearance, marker, and determinism audits.

The authoritative specification contains the complete numeric and algorithmic contract. This file is orientation,
not a substitute for reading it.

## Current maintenance state

- V40 changes verification architecture, class/output labels, and release governance; its renderer algorithm is
  mechanically behavior-equivalent to V39.
- The seven stale V39 test implementations were reconciled to current bounded fixtures. Their prior implementation
  is preserved in the complete `archive/releases/v39/` snapshot, outside active-suite discovery.
- `tests/stress/geometry_stress.py` is optional and non-gating. Stress results cannot substitute for the release gate.
- Active specification references must use the stable `chip_design_language.md` path.
- The authoritative release status is determined only by `python run_release_tests.py`; its result must have no
  failures, errors, skips, expected failures, or manifest mismatch.
- The consolidated V40 tree passed the authoritative gate on 2026-08-14: 44/44 active tests, with zero failures,
  errors, skips, expected failures, or manifest mismatch.

## Verification commands

```powershell
python -m py_compile archive/releases/v39/pcb_v39_renderer.py pcb_v40_renderer.py tests/active/test_pcb_v40_renderer.py run_release_tests.py run_stress_tests.py
python run_release_tests.py
```

Use focused tests while iterating, then run the complete affected suite with sufficient timeout.
