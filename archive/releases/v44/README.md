# PCB Circuit Art Renderer v44

Deterministic Python renderer for octilinear PCB-style circuit art as SVG.

V44 keeps V43's aspect-invariant population law and extends the same generative language to fine `main_scale` values. A smaller `main_scale` changes entity size and honest service resolution; it does **not** create a different aspect/scale mode or change main-chip/prepared-population opportunity. The cumulative specification is [`chip_design_language.md`](chip_design_language.md), and the operator guide is [`V44_RENDERER_README.md`](V44_RENDERER_README.md).

## Setup

Python 3.10 or newer is required.

```bash
python -m pip install -r requirements.txt
```

## Generate artwork

```bash
python pcb_v44_renderer.py --count 1 --out-dir output
python pcb_v44_renderer.py --seed 12345 --count 5 --out-dir output
python pcb_v44_renderer.py --width 1200 --height 6248 --count 1 --out-dir output
python pcb_v44_renderer.py --width 6248 --height 1200 --count 1 --out-dir output
python pcb_v44_renderer.py --width 1200 --height 6248 --main-scale 0.35 --count 1 --out-dir output
python pcb_v44_renderer.py --width 1200 --height 8046 --main-scale 0.35 --count 1 --out-dir output
```

## Test

```bash
python run_release_tests.py
```

The command above is the authoritative release gate. Its discovered active tests must exactly match `tests/ACTIVE_TEST_MANIFEST.json`; failures, errors, skips, expected failures, and manifest drift all fail the release.

## Repository layout

- `pcb_v44_renderer.py` — active renderer
- `tests/active/` — mandatory active regression suite
- `tests/ACTIVE_TEST_MANIFEST.json` — exact active-test contract
- `tests/stress/` — optional, non-gating probes
- `chip_design_language.md` — authoritative, version-neutral design specification
- `examples/` — fresh V44 square, extended scale-1, and fine-scale acceptance SVGs/reports
- `archive/releases/v43/` — complete superseded V43 snapshot
- `archive/releases/` — earlier complete release snapshots
- `archive/history/` — earlier changelogs and verification records

Historical release files are retained unchanged under `archive/`; they are not required by V44 at runtime.
