# PCB Art Generator — Session Context

Read this file completely at the start of every session after `AGENTS.md`, then read
`chip_design_language.md` completely before doing any work.

## Authority and active files

- `chip_design_language.md` is the single authoritative specification and must accompany every repository change.
- Its filename is version-neutral; its internal metadata records the active design-language version.
- `pcb_v42_renderer.py` is the active renderer.
- `tests/active/test_pcb_v42_renderer.py` is the mandatory active regression suite.
- `tests/ACTIVE_TEST_MANIFEST.json` is the exact active-test contract.
- `V42_RENDERER_README.md` is the active operator guide.
- `examples/` contains fresh V42 reference, difficult, and tall acceptance artifacts.
- `archive/releases/v41/` preserves the superseded V41 release.
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

- V42 retains V41's exact tall-canvas frame clipping fix and all V39/V40 geometry/test-contract protections.
- Local residual cells now preserve approximately the same physical size on extreme aspect ratios instead of stretching a fixed 56×56 grid over the entire canvas.
- Component population remains on the existing fixed 56×56 component grid; tall aspect ratio alone does not multiply component population.
- Bounded spatial broad phases replace global all-to-all scans only where the resulting score/clearance decision is equivalent; exact nearby geometry checks remain authoritative.
- Local computational allowances scale with canvas workload, while the actual route grammar, 50–60% component-first service, 80–90% local service target, clearances, 0/±45-degree turns, and deterministic behavior remain unchanged.
- Tall late-stage completion first uses the established bent/articulated cleanup and then returns any remaining deficit to ordinary local routing waves rather than relaxing geometry or inventing straight-line shortcuts.
- Fresh V42 square acceptance artifacts and deterministic 1200×6248 / 1200×8046 tall acceptance artifacts live under `examples/`.
- The authoritative release status is determined only by `python run_release_tests.py`; its result must have no failures, errors, skips, expected failures, or manifest mismatch.

## Verification commands

```powershell
python -m py_compile pcb_v42_renderer.py tests/active/test_pcb_v42_renderer.py run_release_tests.py run_stress_tests.py
python run_release_tests.py
```

Use focused tests while iterating, then run the complete affected suite with sufficient timeout.
