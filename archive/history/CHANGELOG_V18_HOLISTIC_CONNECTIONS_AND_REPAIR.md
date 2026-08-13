# V18 — holistic connections, launch restoration, loop guard, extended repair

V18 builds directly on v17 traceback/reroute. Static-object generation and the deterministic seed model are unchanged.

## Launch restoration

- Main-chip launch occupancy is now sampled against the **actual main chip body** rather than the larger decorated group bounds.
- Each side targets **70–90%** body-side occupancy.
- Lane spacing is restored to a denser `4.35U–6.10U` band so chips do not look under-connected.
- Routing fan cohorts are reduced to **3–5 contiguous traces** rather than the wider v16/v17 cohorts, so denser launch buses do not immediately become oversized routing corridors.
- Launch fan-out can occur immediately when a very wide common trunk would be blocked.
- Fan-out is viability-gated: the bus is not committed to a split whose cohorts cannot perform their first lane-preserving rebase.
- A specific coarse-envelope exemption allows adjacent siblings from the same fan to make their first parallel rebase. This does **not** relax collision rules between unrelated pathways.

## Parallel / holistic connection planning

- Movement remains synchronous: all active fronts are evaluated from a shared round snapshot before accepted geometry is committed.
- Cross-chip connection opportunities are now also computed from that same snapshot.
- Compatible fronts receive a shared meeting objective for the round, so both sides can steer and branch toward the same opportunity instead of one reacting to geometry the other already committed.
- Actual joins remain physical trace-to-trace junctions; proximity alone is never counted as a connection.
- Active foreign lanes can receive a T-junction. Their accepted geometry is then recovery-locked so later traceback cannot erase a segment another trace has joined.
- Expensive lane materialisation is limited to paired / nearest candidate fronts rather than sweeping every trace every round.

## Anti-loop behavior

Before accepting a normal gesture, V18 rejects candidates that would:

- return too close to an older local route point;
- make substantial radial regression back toward the route origin after meaningful outward travel;
- begin a short-window sequence of repeated same-sense turns that would curl into a spiral / roundabout.

This is in addition to the existing self-crossing, illegal-turn, and compensating-zigzag prevention.

## Extended traceback / reroute

- Repair budget increased from **3 to 5** attempts.
- Traceback depth grows with repeated failed repairs and can rewind **up to 4** accepted local gestures.
- Recovery mode lasts up to 3 subsequent routing decisions and may use a one-module full PCB step where a 2–3 module move cannot escape clutter.
- Recovery is no longer hard-stop-only. Repeated same-round conflicts and route stagnation may also schedule deferred repair.
- Existing physical connections establish a recovery floor so traceback never invalidates a completed network join.
- Short terminal alignment legs below `0.45 × module` are rejected rather than used as cosmetic connection fixes.

## Preserved invariants

- deterministic same-seed output;
- no A* or per-path destination search;
- no pathway seed retries / accepted-output searching;
- probabilistic / variance-driven intents remain best-effort rather than quotas;
- no static intersections;
- no unmarked trace crossings;
- no collapsed centerline sharing;
- no compensating zigzags.
