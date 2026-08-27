# PCB Circuit Art Renderer v41

Deterministic Python renderer for generating octilinear PCB-style circuit art as SVG.

The active release is v41. It fixes a frame-clipping defect that could manufacture a non-octilinear visible segment when a legal escaped trace reached the canvas edge through a microscopic final leg, most visibly on unusually tall canvases.
The cumulative specification is [`chip_design_language.md`](chip_design_language.md), and the operator guide is [`V41_RENDERER_README.md`](V41_RENDERER_README.md).

## Setup

Python 3.10 or newer is required.

```bash
python -m pip install -r requirements.txt
```

## Generate artwork

```bash
python pcb_v41_renderer.py --count 1 --out-dir output
python pcb_v41_renderer.py --seed 12345 --count 5 --out-dir output
python pcb_v41_renderer.py --width 1200 --height 6248 --count 1 --out-dir output
```

## Test

```bash
python run_release_tests.py
```

## Repository layout

- `pcb_v41_renderer.py` — active renderer
- `tests/active/` — mandatory active regression suite
- `tests/ACTIVE_TEST_MANIFEST.json` — exact active-test contract
- `tests/stress/` — optional, non-gating current-policy probes, including tall-canvas main-network checks
- `chip_design_language.md` — authoritative, version-neutral design specification
- `examples/` — fresh v41 reference SVGs and reports
- `archive/releases/` — complete superseded release snapshots through v40
- `archive/history/` — earlier changelogs and verification records

Historical release files are retained unchanged under `archive/`; they are not required by v41 at runtime.
