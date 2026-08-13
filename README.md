# PCB Circuit Art Renderer v39

Deterministic Python renderer for generating octilinear PCB-style circuit art as SVG.

The active release is v39. Its cumulative design specification is
[`chip_design_language_v39_variance_driven.md`](chip_design_language_v39_variance_driven.md),
and the detailed usage guide is [`V39_RENDERER_README.md`](V39_RENDERER_README.md).

## Setup

Python 3.10 or newer is required.

```bash
python -m pip install -r requirements.txt
```

## Generate artwork

```bash
python pcb_v39_renderer.py --count 1 --out-dir output
python pcb_v39_renderer.py --seed 12345 --count 5 --out-dir output
```

## Test

```bash
python -m unittest test_pcb_v39_renderer.py
```

## Repository layout

- `pcb_v39_renderer.py` — active renderer
- `test_pcb_v39_renderer.py` — active regression suite
- `chip_design_language_v39_variance_driven.md` — authoritative design specification
- `examples/` — v39 reference SVGs and reports
- `archive/releases/` — complete v34–v38 source snapshots
- `archive/history/` — earlier changelogs and verification records

Historical release files are retained unchanged under `archive/`; they are not required by v39 at runtime.
