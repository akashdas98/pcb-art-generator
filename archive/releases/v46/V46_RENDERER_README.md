# V46 Renderer Operator Guide

## Inputs

The public geometry interface is:

```text
aspect ratio + scale
```

There are no user-facing width/height controls and no `main_scale` parameter.

```bash
python pcb_v46_renderer.py \
  --aspect-ratio 1200:6248 \
  --scale 0.35 \
  --seed 12345 \
  --count 2 \
  --out-dir output \
  --no-skip-deadlocks
```

`--aspect-ratio` accepts forms such as `1:1`, `16:9`, or `1200:6248`; only the ratio matters. `--scale` must be positive. Lower values expose more logical PCB territory.

## Scale semantics

V46 fixes the canonical short side at 1200 logical units at scale 1. The logical short side is `1200 / scale`. The long side follows the aspect ratio.

This is a logical camera/viewBox transform, not per-entity shrinking. A chip generated with the same entity seed has the same logical dimensions at scale 1 and scale 0.35; at scale 0.35 the SVG simply shows much more logical board around it.

## Output

Each accepted sample produces:

- `pcb_v46_NN_seed_<seed>.svg`
- `pcb_v46_NN_report.json`

The SVG root emits `viewBox` only; it has no fixed `width` or `height` attributes and may be displayed at any physical size preserving its aspect ratio.

## Phase order

1. main chips;
2. main-chip pathway network;
3. residual components filling 50–60% of post-main serviceable field;
4. local gap pathways filling 80–90% of the post-component remainder;
5. exact final audits and SVG/report emission.

Main routes are frozen before components/local fill and may not be steered by later phases.

## Performance semantics

More logical territory is allowed more population and bounded work opportunity. It is not allowed to enlarge the semantic scope of local decisions. V46 uses shared/local spatial indexes, bounded large-N calibration, owned rollback history, indexed terminal/component checks, and bounded full-board waves to keep the implementation aligned with that rule.
