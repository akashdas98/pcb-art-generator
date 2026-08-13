# V21 — Termination markers, bundle persistence, and main-chip routing moat

V21 is a targeted refinement of the V20 synchronous / holistic pathway planner.  It does not
replace the routing architecture or introduce global route search.

## Termination markers

- Termination-dot radius is **2.0× V20**.
- Hollow termination-marker stroke is **2.70U**.
- Launch pitch now reserves enough room for the **outer edge of two adjacent hollow V21 dots**
  plus a **1U minimum marker gap**, while retaining the existing 70–90% chip-body-side occupancy
  objective.  The ordinary line-to-line 1.5×-mean-thickness edge-gap rule remains a lower bound.
- A hollow endpoint no longer has a trace drawn through its empty centre.  The rendered trace is
  clipped back to the **outer marker border** (`radius + stroke/2`) while the marker stays centred
  on the logical terminal point.

## Bundle-stage termination

- Normal branch depth is extended from 3 to **5** so mature small cohorts have more chances to
  peel apart before ending.
- Voluntary / hard-stop bundle termination is now suppressed by about **97%** (up from ~90%).
- Recovery fragmentation uses narrow singleton lane fronts because they route through congestion
  more effectively, but those children receive an **isolation lock**: they may not immediately
  terminate while still visually embedded in their parent bus.
- A singleton that lies between continuing same-root lanes on both lateral sides is forbidden to
  terminate.  It receives fresh reroute budget, an escape objective, and continued repair.
- Persistent bundles receive a **12-round persistence tail** after the normal board horizon.
- If all ordinary routing, branching, traceback, connection, and escape attempts are exhausted,
  unresolved persistence lanes are finalized as coordinated terminal cohorts rather than silently
  disappearing from the SVG or producing one isolated middle-of-bundle dot.

## Traceback / recovery detail

- Before a fully exhausted bundle fragments, the parent receives one last deep rollback (within
  existing recovery floors / connection locks) so the narrower children do not inherit the exact
  same dead pocket.
- Recovery-fragment children may legally leave their parent's final coarse corridor on their first
  gesture.  This exemption applies only to that inherited final segment and does not relax
  unrelated-route collision rules.

## Main-chip routing moat

- Secondary-component spawn moat remains **170U**.
- Ordinary foreign-static pathway keepout remains **8U**.
- Main-chip pathway keepout is now **24U** — exactly 3× the ordinary 8U routing keepout.
  The source chip is exempt only for the initial launch gesture; after emergence, it is also
  protected by the 24U routing moat.

## Preserved V20 hard invariants

- no mid-line trace connections;
- at most one connection per trace;
- close compatible free heads receive deterministic head-to-head connection priority;
- no unmarked centreline intersections;
- no unmarked thick-stroke touching / overlap;
- no collapsed / doubled traces;
- no rendered involuntary tiny post-emergence stubs;
- no compensating zig-zag connection repair.
