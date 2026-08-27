#!/usr/bin/env python3
"""Production-use entry point for PCB Art Generator V48.

This command renders exactly the requested samples and stops. It intentionally does not run
repository safety gates, release tests, stress tests, performance harnesses, handoff builders,
or seed qualification. When --seed is omitted, V48Renderer chooses one random base seed; that
seed is then rendered normally under the seed-totality contract.

By default this command writes SVG files only. The renderer report remains embedded in each SVG
metadata because it is part of the rendered artifact, but no standalone report JSON is written.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from pcb_v48_renderer import V48Renderer


def render_requested(
    *,
    aspect_ratio: str = "1:1",
    scale: float = 1.0,
    seed: Optional[int] = None,
    count: int = 1,
    out_dir: Path | str = Path("v48_output"),
    main_chip_density_multiplier: float = 1.0,
    main_run_length_multiplier: float = 1.0,
) -> list[Path]:
    """Render exactly ``count`` logical samples and return their SVG paths.

    No validation workflow, stress suite, repository guard, report-file generation, or alternate
    seed selection is performed here. Construction-time/final invariants inside the renderer
    remain active; if one fails, the exception propagates for that exact logical seed.
    """
    if count < 1:
        raise ValueError("count must be >= 1")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    renderer = V48Renderer(
        aspect_ratio, scale, seed,
        main_chip_density_multiplier=main_chip_density_multiplier,
        main_run_length_multiplier=main_run_length_multiplier,
    )
    paths: list[Path] = []

    for logical_index in range(count):
        placed, report = renderer.generate_sample(logical_index)
        svg = renderer.svg_for(placed, report)
        path = out_dir / f"pcb_v48_{logical_index:02d}_seed_{report['seed']}.svg"
        path.write_text(svg, encoding="utf-8")
        paths.append(path)

    return paths


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Render PCB SVGs only. No repository/test/stress/handoff workflow is run."
    )
    ap.add_argument("--aspect-ratio", default="1:1", help="output shape as W:H")
    ap.add_argument("--scale", type=float, default=1.0, help="design zoom; lower exposes more territory")
    ap.add_argument(
        "--seed",
        type=lambda x: int(x, 0),
        default=None,
        help="optional base seed; omit to let the renderer choose a random seed",
    )
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--out-dir", type=Path, default=Path("v48_output"))
    ap.add_argument("--main-chip-density-multiplier", type=float, default=1.0, metavar="0.2..2.0")
    ap.add_argument("--main-run-length-multiplier", type=float, default=1.0, metavar="0.2..3.0")
    args = ap.parse_args()

    for path in render_requested(
        aspect_ratio=args.aspect_ratio,
        scale=args.scale,
        seed=args.seed,
        count=args.count,
        out_dir=args.out_dir,
        main_chip_density_multiplier=args.main_chip_density_multiplier,
        main_run_length_multiplier=args.main_run_length_multiplier,
    ):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
