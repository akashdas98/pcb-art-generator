# V48 before reverting doubled LOCAL gap credit

`pcb_v48_renderer.py` is the qualified production source before the user's
2026-09-29 request to test the earlier half-gap LOCAL service rule. SHA-256:
`f0d0d435b96364fe626bf27647fa20d2601e4c3b351033da8e393d78c7d339cf`.

The preserved source counted the full line-line or component-pathway gap on
each side of each LOCAL stroke. The requested experiment restores half of
each term, without changing physical clearance or component-cluster credit.
The hard total-density shortfall remained open in this predecessor.
