# PCB Circuit Art Renderer v40

Deterministic Python renderer for generating octilinear PCB-style circuit art as SVG.

The active release is v40. It is behavior-equivalent to v39 and promotes a reconciled, exact release-test contract.
Its cumulative design specification is
[`chip_design_language.md`](chip_design_language.md),
and the detailed usage guide is [`V40_RENDERER_README.md`](V40_RENDERER_README.md).

## Setup

Python 3.10 or newer is required.

```bash
python -m pip install -r requirements.txt
```

## Generate artwork

```bash
python pcb_v40_renderer.py --count 1 --out-dir output
python pcb_v40_renderer.py --seed 12345 --count 5 --out-dir output
```

## Test

```bash
python run_release_tests.py
```

## Repository layout

- `pcb_v40_renderer.py` — active renderer
- `tests/active/` — mandatory active regression suite
- `tests/ACTIVE_TEST_MANIFEST.json` — exact active-test contract
- `tests/stress/` — optional, non-gating current-policy probes
- `chip_design_language.md` — authoritative, version-neutral design specification
- `examples/` — inherited v39 reference SVGs and reports
- `archive/releases/` — complete v34–v39 source snapshots; V39 supplies the V40 equivalence baseline
- `archive/history/` — earlier changelogs and verification records

Historical release files are retained unchanged under `archive/`; they are not required by v40 at runtime.
