# PCB Art Generator — Session Context

Read this file completely at the start of every session after `AGENTS.md`, then read
`chip_design_language.md` completely before doing any work.

## Authority and active files

- `chip_design_language.md` is the single authoritative specification and must accompany every repository change.
- Its filename is version-neutral; its internal metadata records the active design-language version.
- `pcb_v41_renderer.py` is the active renderer.
- `tests/active/test_pcb_v41_renderer.py` is the mandatory active regression suite.
- `tests/ACTIVE_TEST_MANIFEST.json` is the exact active-test contract.
- `V41_RENDERER_README.md` is the active operator guide.
- `examples/` contains fresh V41 reference and difficult acceptance artifacts.
- `archive/releases/v40/` preserves the superseded V40 renderer/test-contract release and its inherited V39 examples.
- `archive/` otherwise contains immutable historical releases and history.

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

- V41 fixes the V40 microscopic escaped-tail frame-clipping defect without changing routing probabilities, phase order, density targets, component language, or the 45-degree pathway grammar.
- The defect occurred only during final materialization: a tiny final escape leg could move the preceding vertex to the wrong segment's frame crossing and skew an otherwise legal 45-degree leg.
- V41 extends the previous visible octilinear leg to its own frame crossing instead, preserving both first-frame termination and exact pathway grammar without creating a sub-0.10-module visible tail.
- Active regression coverage includes the exact microscopic-tail case on heights 6248 and 8046.
- Optional stress coverage reproduces the real `1200×6248` and `1200×8046`, seed-1 main networks.
- Because V41 changes renderer behavior, V40's inherited V39 acceptance snapshot is not reused. `examples/` contains fresh V41 reference and difficult samples/reports.
- The authoritative release status is determined only by `python run_release_tests.py`; its result must have no failures, errors, skips, expected failures, or manifest mismatch.

## Verification commands

```powershell
python -m py_compile pcb_v41_renderer.py tests/active/test_pcb_v41_renderer.py run_release_tests.py run_stress_tests.py
python run_release_tests.py
```

Use focused tests while iterating, then run the complete affected suite with sufficient timeout.
