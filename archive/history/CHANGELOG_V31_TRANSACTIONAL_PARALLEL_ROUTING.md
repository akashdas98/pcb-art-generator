# V31 — Transactional Parallel Routing

V31 is a routing-core correction. It does not change the V29 visual-density/component agenda or the
V30 component/runtime dependency order. Its purpose is to make the long-standing "parallel growth"
requirement true at the commit and recovery levels, not only at proposal generation.

## Problem corrected

V30 generated movement proposals from a shared round state but then ultimately accepted selected
proposals through a priority-sorted sequential loop. A same-round loser could therefore be forced to
reroute after the winner had already become committed geometry. In addition, pending traceback was
executed inside the per-front proposal loop, so fronts could even propose against different effective
snapshots depending on front id. Root main-chip launches also retained a one-segment recovery floor,
preventing a one-gesture newborn from rewinding to its emergence anchor.

That combination allowed exactly the failure V31 is intended to remove: a very young route could be
nipped in the bud by geometry whose apparent ownership was partly an artifact of internal processing
order.

## Active changes

- All ready traceback/rollback executes before the movement snapshot is taken.
- Every active movement front proposes against the same committed snapshot.
- Conflict grouping now applies to every interacting proposal pool, not only fronts already tagged for
  the bounded-holistic layer.
- A local conflict component is solved as a deterministic bounded complete assignment: every participant
  must receive a mutually compatible proposal.
- If no complete assignment exists, the component commits no movement that round. There is no
  priority-sorted winner/loser fallback.
- Unsolved mixed groups containing a young root main-chip launch preferentially schedule rollback on the
  non-young participants. All-young or all-normal groups are repaired symmetrically.
- Root main-chip launches now have a post-emergence recovery floor of zero until a real shared-prefix or
  physical-connection lock raises that floor. A one-gesture launch can therefore trace all the way back
  to its emergence anchor.
- A young blocked launch can identify the foreign route whose committed corridor is actually blocking its
  forward neighborhood and request that blocker to yield/rewind.
- A recently terminated, unconnected leaf may be reopened for bounded causal repair when its recent tail
  is the blocker. Connected/shared topology is not reopened by this rule.
- Accepted movement geometry is written as an atomic batch before post-move proximity/branch/terminal
  reactions are evaluated.
- New report diagnostics expose atomic-round commits, deferred conflict groups, repair-front counts,
  causal blocker rollback requests, causal terminal reopens, and root-emergence traceback.

## Explicitly unchanged

- No A* or global route search was added.
- No candidate-seed pathway search was added.
- Secondary components still do not exist spatially during routing.
- V29 local-gap target/branching/exit behavior is unchanged.
- V29 capacitor scale and V30 post-route component recovery are unchanged.
- `main_scale` semantics are unchanged.
- Historical V4–V30 changelogs and verification records are not rewritten.
