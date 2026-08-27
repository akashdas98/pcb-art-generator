# PCB Circuit Art Renderer v42

Deterministic Python renderer for generating octilinear PCB-style circuit art as SVG.

The active release is v42. It preserves the established visual/geometry rules while making local residual-fill bookkeeping and search scale correctly on extreme aspect ratios such as 1200×6248 and 1200×8046. The cumulative specification is [`chip_design_language.md`](chip_design_language.md), and the operator guide is [`V42_RENDERER_README.md`](V42_RENDERER_README.md).

## Setup

Python 3.10 or newer is required.

```bash
python -m pip install -r requirements.txt
```

## Generate artwork

```bash
python pcb_v42_renderer.py --count 1 --out-dir output
python pcb_v42_renderer.py --seed 12345 --count 5 --out-dir output
python pcb_v42_renderer.py --width 1200 --height 6248 --count 1 --out-dir output
python pcb_v42_renderer.py --width 1200 --height 8046 --count 1 --out-dir output
```

## Test

```bash
python run_release_tests.py
```

## Repository layout

- `pcb_v42_renderer.py` — active renderer
- `tests/active/` — mandatory active regression suite
- `tests/ACTIVE_TEST_MANIFEST.json` — exact active-test contract
- `tests/stress/` — optional, non-gating current-policy probes
- `chip_design_language.md` — authoritative, version-neutral design specification
- `examples/` — fresh v42 reference, difficult, and tall acceptance SVGs/reports
- `archive/releases/v41/` — complete superseded V41 snapshot
- `archive/releases/` — earlier complete release snapshots
- `archive/history/` — earlier changelogs and verification records

Historical release files are retained unchanged under `archive/`; they are not required by v42 at runtime.
