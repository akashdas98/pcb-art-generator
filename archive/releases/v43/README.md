# PCB Circuit Art Renderer v43

Deterministic Python renderer for octilinear PCB-style circuit art as SVG.

V43 makes the generative population spatially stationary across arbitrary canvas aspect ratios. Extending either axis creates more physical PCB territory—not a square-sized composition inside empty space—while entity scale, route grammar, probabilities, clearances, and phase order remain the same. The cumulative specification is [`chip_design_language.md`](chip_design_language.md), and the operator guide is [`V43_RENDERER_README.md`](V43_RENDERER_README.md).

## Setup

Python 3.10 or newer is required.

```bash
python -m pip install -r requirements.txt
```

## Generate artwork

```bash
python pcb_v43_renderer.py --count 1 --out-dir output
python pcb_v43_renderer.py --seed 12345 --count 5 --out-dir output
python pcb_v43_renderer.py --width 1200 --height 6248 --count 1 --out-dir output
python pcb_v43_renderer.py --width 6248 --height 1200 --count 1 --out-dir output
python pcb_v43_renderer.py --width 1200 --height 8046 --count 1 --out-dir output
```

## Test

```bash
python run_release_tests.py
```

## Repository layout

- `pcb_v43_renderer.py` — active renderer
- `tests/active/` — mandatory active regression suite
- `tests/ACTIVE_TEST_MANIFEST.json` — exact active-test contract
- `tests/stress/` — optional, non-gating probes
- `chip_design_language.md` — authoritative, version-neutral design specification
- `examples/` — fresh V43 square and extended acceptance SVGs/reports
- `archive/releases/v42/` — complete superseded V42 snapshot
- `archive/releases/` — earlier complete release snapshots
- `archive/history/` — earlier changelogs and verification records

Historical release files are retained unchanged under `archive/`; they are not required by v43 at runtime.
