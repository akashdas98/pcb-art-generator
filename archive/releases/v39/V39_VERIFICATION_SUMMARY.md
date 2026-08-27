# V39 verification summary

V39 was regression-tested on the same two release base seeds used for V38.

## Root-cause reproduction from released V38 SVGs

On both maintained V38 release boards, 3 of 8 inspected intentional cross-chip head-to-head joins formed 90-degree
through-junctions even though each individual trace passed the per-polyline turn audit. This demonstrated that the
remaining 90-degree corners were a network-junction audit gap, not merely visual aliasing.

The V38 reference report also had 71 visible main launch traces but zero main source markers because source-marker
creation incorrectly depended on the final leaf having no parent.

## V39 reference seed

- base seed: `20260806`
- logical sample seed: `2065259631603175940`
- cross-chip connections: 7
- non-octilinear pathway segments: 0
- illegal in-trace turns: 0
- illegal connection-junction turns: 0
- rendered line-clearance violations: 0
- component/local clearance violations: 0
- visible main launch traces: 71
- main emergence/source markers: 71
- normalized local residual fill: 86.48%
- straight visible local trace fraction: 7.04%

## V39 difficult seed

- base seed: `15186978462388109083`
- logical sample seed: `568060949511661325`
- cross-chip connections: 6
- non-octilinear pathway segments: 0
- illegal in-trace turns: 0
- illegal connection-junction turns: 0
- rendered line-clearance violations: 0
- component/local clearance violations: 0
- visible main launch traces: 93
- main emergence/source markers: 93
- normalized local residual fill: 80.33%
- straight visible local trace fraction: 12.66%

The difficult seed deliberately retains the legal 80.33% result rather than accepting an optional filler whose
rendered thick round cap would violate a component moat.

## Automated gates

Targeted structural tests cover exact octilinear classification, rejection of a 90-degree connection junction,
acceptance of a legal 45-degree junction, and rejection of a direct 90-degree in-trace commit. The maintained full
reference regression additionally requires zero non-octilinear segments, zero illegal connection-junction turns, zero
rendered line-clearance violations, one main source marker per visible main launch, local fill >=80%, and a
bent-dominant local population.
