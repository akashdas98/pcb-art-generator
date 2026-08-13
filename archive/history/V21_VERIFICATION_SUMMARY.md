# V21 verification summary

Focused verification was run against the finalized V21 renderer.

## Reference seed: base seed 12345

- launched traces: **65**
- visibly retained traces: **65 / 65**
- minimum visible chip-side occupancy: **72.91%**
- cross-network physical connections: **2**
- total terminated traces: **28**
- still-logically-bundled forced termination traces: **0**
- coordinated final persistence traces: **10**
- escaped traces: **32**
- main-chip routing keepout required: **24U**
- observed minimum foreign-main-chip trace clearance: **57.47U**
- ordinary static keepout required: **8U**
- compensating zig-zags: **0**
- unmarked centreline intersections / overlaps: **0**
- unmarked thick-stroke overlaps / touches: **0**
- duplicate-trace cleanup removals: **0**
- intersection cleanup removals: **0**

The reference SVG contains **28** termination markers.  Marker-geometry audit found:

- hollow markers: **9**
- hollow markers with trace entering the hollow interior: **0**
- pairwise termination-marker outer-disc overlaps: **0**

The targeted V21 pathway regression test passes, including 24U main-chip routing moat,
2× endpoint-dot scale, hollow-dot clipping, marker non-overlap, retained 70–90% chip-side
coverage, no trace loss, no mid-line/multiple connections, no thick-stroke intersections, and
no compensating zig-zags.

## Alternate seed: base seed 54321

- launched / visibly retained traces: **64 / 64**
- minimum visible chip-side occupancy: **73.35%**
- bundled forced termination traces: **0**
- total terminated traces: **21**
- escaped traces: **43**
- minimum foreign-main-chip clearance: **92.15U**
- unmarked centreline overlaps: **0**
- unmarked thick-stroke overlaps: **0**
- compensating zig-zags: **0**

The historical full suite was not rerun in one monolithic invocation; the V21-affected pathway
regression was run directly and passed.
