# v17 — Pathway Traceback / Reroute Recovery

This revision targets pathways that become boxed in shortly after launch or later in their journey. It keeps the v16 deterministic, probabilistic, variance-driven, conditional and permutational generation model; the new behavior is recovery logic, not realized-output quota enforcement.

## 1. Lower main-chip density

- A normal board now generates **2 main chips 90% of the time** and **3 main chips 10% of the time**.
- This replaces the previous 3/4-chip distribution and leaves more traversable board area for pathway networks.
- The outcome remains seed-driven and deterministic.

## 2. Main-chip breathing room for secondary components

- Collections and isolated secondary components now keep an **85U clearance moat** from main chips.
- Chip-to-chip clearance remains governed by its existing rule.
- Secondary-to-secondary clearance remains governed by its existing rule.
- The goal is to preserve usable launch/corridor space around each chip rather than allowing small objects to immediately choke every exit.

## 3. Deferred hard-stop recovery

A front is no longer immediately killed merely because its current proposals fail.

- A hard-stopped front is marked for recovery and reconsidered on a **later synchronous routing round**.
- Each front receives up to **3 reroute attempts**.
- When sufficient accepted route history exists, recovery rolls back one or more recent accepted segments, rebuilds the path spatial index/coverage state, and asks the front to choose another legal continuation.
- The failed heading is de-prioritized during the reroute round.
- Recovery still obeys the existing hard geometry constraints: no static-object intersections, no accidental route crossings, no collapsed lanes, and no compensating zig-zag rescue paths.
- Deliberate journey-limit termination, connection and off-frame exit remain terminal decisions; they are not treated as failures to be rerouted.

## Junction and launch safeguards

Two additional safeguards were needed so the reroute system would not merely create new tiny branches:

- **Branch preflight:** a proposed split is committed only if every child has a viable mandatory emergence/rebase corridor at that moment. Otherwise the parent remains active and may reconsider branching later.
- **Straight recovery rebase:** when a child loses its ordinary two-module rebase corridor to another simultaneously advancing bundle, recovery may use a one-module *straight-only* escape rebase before any turn. This is restricted to recovery and cannot be used as a general micro-segment mechanism.

## Abandoned recovery-branch cleanup

After the recovery budget is exhausted, a very short involuntary dead-end is treated as an abandoned search branch rather than a deliberate visible trace termination.

- Short `hard_stop_exhausted` / `round_limit` leaves below 4 modules are pruned from the final materialized pathway tree.
- Deliberate `journey_limit` terminations are retained.
- At least one visible leaf is preserved per chip-side launch root.

This cleanup is intentionally downstream of the routing attempts: the system first tries to save the pathway through later-round rerouting, then removes only short failed recovery artifacts that never became meaningful routes.

## Determinism

Same seed -> same SVG/report output remains a required invariant. No hidden pathway seed search or post-hoc replacement seed is introduced.
