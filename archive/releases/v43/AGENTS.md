# PCB Art Generator — Repository Instructions

These instructions apply to every file in this repository. Historical release directories may contain older
documents, but they do not override this file for work on the active renderer.

## Mandatory session startup

Before analyzing, editing, generating, or testing any repository change, read these files completely in this order:

1. `AGENTS.md`
2. `CONTEXT.md`
3. `chip_design_language.md`

Do not skim or rely on memory from an earlier session. The third file is the single source of truth for how the
renderer works. If any implementation, test, README, changelog, or request conflicts with it, stop and resolve the
conflict from the source of truth before changing code.

## Change discipline

- Diagnose the root cause and identify the violated design-language invariant before implementing a fix.
- Preserve all established hard invariants, phase ordering, deterministic behavior, and required functionality.
- Never weaken an audit, silently suppress required output, add an unauthorized special case, or change a numeric
  rule merely to make a failing sample pass.
- Follow the specification's established format: numbered normative sections, explicit numeric rules, manifest
  entries where applicable, and versioned historical refinements. Do not replace it with informal summaries.
- Every repository change must update `chip_design_language.md` in the same change. Record the reason, affected
  invariant, and normative behavior in the appropriate section and in its active change record. Documentation-only,
  test-only, tooling, and governance changes are not exempt.
- Update `CONTEXT.md` whenever paths, architecture, verification status, known failures, or active work change.
- Keep the active renderer and release documents at the repository root. The active release-gating tests live in
  `tests/active/` and are governed by `tests/ACTIVE_TEST_MANIFEST.json`. Complete superseded releases, including their
  original tests, live in `archive/releases/vNN/`; the active runner must discover only `tests/active/`. Treat archived
  snapshots as immutable historical evidence unless the user explicitly requests an archival correction.
- Verify the complete affected system, neighboring variants, and maintained regression behavior after meaningful
  changes. Report any remaining failures accurately.

## General work — root cause first

- Gather evidence, identify the violated invariant or failing boundary, and explain why the proposed change
  addresses the underlying failure before implementing it.
- Prefer one coherent architectural correction over symptom-specific patches and accumulating special cases.
- When evidence contradicts the current diagnosis, stop extending that approach and reassess from first principles.
- Do not remove functionality, reduce scope, or change interaction semantics to make a defect disappear.
- Treat workarounds as a last resort. Document the root limitation, risks, narrow scope, and removal condition.
- Treat local or emulated verification as evidence, not proof, when the reported failure occurs in another runtime,
  browser engine, device, or environment.

## HTML, CSS, and frontend work

- Prefer standards-based responsive behavior: viewport metadata, CSS media/container queries, and `matchMedia`
  when JavaScript must choose one mounted composition. Avoid device, user-agent, touch, or screen heuristics unless
  standards-based breakpoints are demonstrably insufficient.
- Before adding responsive or browser-specific branches, inspect the rendered DOM, stylesheet delivery, cascade,
  computed styles, layout viewport, hydration, bounds, clipping, stacking, and paint order.
- Treat real-device and real-browser-engine results as authoritative for engine-specific defects.
- Do not mount duplicate responsive trees and hide one with CSS when SVG, `foreignObject`, hydration, accessibility,
  paint behavior, or duplicate semantics can expose the hidden tree. Prefer one mounted composition.
- When mixing SVG and HTML, minimize `foreignObject`, preserve stable native-SVG paint order, and give essential SVG
  paint properties explicit presentation attributes when inheritance is unreliable.
- Keep server and client output deterministic. Avoid hydration-time replacement, device detection, or pre-hydration
  DOM mutation when semantic HTML and normal breakpoints can solve the requirement.
- Diagnose generated-asset and tooling-state mismatches before changing UI code. Verify the tested client received
  matching HTML, CSS, and JavaScript.
- Preserve progressive enhancement: canonical content remains accessible without JavaScript, and initialization
  delays or failures must not leave it hidden, translucent, duplicated, or structurally incomplete.

## Source-of-truth identity

- Canonical specification path: `chip_design_language.md`
- The filename is intentionally version-neutral.
- The active design-language version is stored inside that document, not in its filename.
