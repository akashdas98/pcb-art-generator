# Legacy Changelogs — V4 through V33

This file preserves the historical changelog records that predate the source-snapshot release archive. Entries are concatenated from the former `archive/history/CHANGELOG_*` files; no renderer authority is defined here.

---

## CHANGELOG_V4_VARIANCE_DRIVEN.md

# v4 variance-driven refactor

This revision removes artificial numeric option menus while preserving genuinely categorical visual operations.

## Replaced with procedural variance

- main-chip short-side size bins -> continuous center-biased interval
- main-chip aspect bins -> continuous high-side-biased interval
- motif-count preset table -> continuous latent motif complexity -> integer projection
- M1 border-count menu -> conditional probabilistic growth
- M2 row/column tables -> safe-rectangle-derived bounded dimensions
- M3 band/mark count tables -> fit-derived bounded dimensions
- M7 row/column tables -> safe-rectangle-derived bounded dimensions
- M8 long/short span modes -> one continuous high-span-biased distribution
- M8 tight/moderate packing modes -> one continuous tight-biased gap distribution
- collection complexity tiers/quotas -> continuous latent richness -> family count
- ordinary entity-count table -> continuous center-biased population projection
- ordinary grid row presets -> count + anisotropy-derived dimensions
- ordinary dot standard/accent modes -> one continuous heavy-low-tail radius distribution
- mini-IC aspect bins -> one continuous aspect distribution
- mini-IC terminal central/tail modes -> one continuous center-biased terminal-length distribution
- IC single/separate/array mode menu -> singleton condition + connectivity probability + procedural dimensions
- IC rows×columns table -> continuous extent/anisotropy dimension generator
- dense rows×columns table -> continuous extent/anisotropy dimension generator

## Still categorical because the operation itself differs

Examples retained intentionally:

- motif identity M1–M8
- horizontal vs vertical body orientation
- square vs rounded corners
- filled vs hollow vs mixed state
- ordinary lattice operation (strip / orthogonal / diagonal / staggered)
- M2 topology (filled / perimeter / compact)
- terminal-side topology
- orthogonal vs row-shifted vs column-shifted dense lattice

These are visual operations, not numeric preset shapes.

## Additional execution corrections

- connected IC arrays remain exact terminal-tip contact arrays
- dense diamond grids use half-step row/column staggering rather than a 45-degree square-grid rotation
- M5 corner curves retain the shifted near-corner stand-off and expanded curvature range
- special family quotas remain exact (`IC=0.625N`, `dense=0.845N`, border=`0.700N`)
- collection packing now uses directional AABB support instead of circumcircle radii, preserving clearance while reducing unnecessary empty space
- deterministic hierarchical deadlock fallback skips pathological logical sample indices without resetting the shared batch uniqueness domain

---

## CHANGELOG_V6_CAPACITOR.md

# V6 Capacitor Entity Update

- Replaced the former collection-only `ring_circle` treatment with a distinct `capacitor_circle` entity.
- Increased continuous radius range to 4.2U–10.0U before collection scaling.
- Rendering states: filled 0.32, hollow 0.28, concentric-ring 0.40.
- Concentric inner-ring count is derived from a continuous driver; no ring-count lookup table.
- Collection-family sampling weight raised to 1.30 so the entity is visibly represented in the mix.
- Added independent isolated occurrence path: 0.72 probability per sample; count 1–3 derived from a continuous intensity driver.
- Isolated capacitors use the same secondary spread-biased placement logic and the same 18U/12U pair clearances.
- Reports now expose isolated capacitor count/states/radii plus collection capacitor group/entity counts.
- Regression suite expanded to 10 tests.

---

## CHANGELOG_V7_CAPACITOR_SINGLETON.md

# v7 — Capacitor singleton correction

- `capacitor_circle` no longer uses ordinary entity-count or lattice generation.
- One capacitor-family occurrence inside a collection now produces exactly one capacitor entity.
- Capacitors are forbidden from strip, chain, orthogonal-grid, diagonal-grid, and staggered-grid generation.
- Multiple isolated capacitors remain allowed, but each is placed independently with full secondary-component clearance.
- Added regression coverage for singleton collection capacitors and non-overlapping multiple isolated capacitors.
- Five-sample smoke audit confirmed collection capacitor entity count equals collection capacitor group count and zero reported clearance violations.

---

## CHANGELOG_V8_PATHWAYS.md

# CHANGELOG V8 PATHWAYS

- Added variance-driven pathway generation.
- Pathways originate from main chips as tightly packed bundles.
- Routing is quantized to 8 directions with 45-degree incremental turns.
- Bundles can split into sub-bundles, connect to other pathways, or terminate with filled/hollow circular endpoints.
- Pathways are generated after board placement so they are occupancy-aware.
- Pathways are rendered beneath the other entities in SVG export.

---

## CHANGELOG_V9_PATHWAY_NETWORK.md

# CHANGELOG V9 — PATHWAY NETWORK

- Replaced sparse 2–6-line pathway launches with chip-side-span-derived dense launch bundles.
- Launch bundles now occupy a large fraction of the source chip side when feasible.
- Replaced independent line-segment turns with continuous polyline traces.
- Enforced visible turn delta of only 0° or ±45° between consecutive segments.
- Added recursive multiplicity-driven bundle splitting, including repeated splits down to small bundles and occasional singleton traces.
- Added intentional branch-junction allowance so valid children are not rejected for sharing the parent branch point.
- Blocked wide bundles now split before termination rather than producing source-adjacent stubs.
- Increased minimum pathway journey length and board-scale traversal.
- Added cross-chip launch goals and natural encounter logic for frequent pathway-to-pathway connections.
- Kept pathway-to-collection connection as a rarer event.
- Kept true termination markers as hollow/filled circles and intersection markers for rare overlaps.
- Rebalanced path collision broad phase with a spatial hash and conservative bundle envelopes for tractable dense routing.

---

## CHANGELOG_V10_PATHWAY_ROUTING_FIXES.md

# CHANGELOG V10 PATHWAY ROUTING FIXES

- Pathways now always emerge perpendicular to the chip side they launch from.
- Every chip now emits on all four sides.
- Launch bundles use chip outer bounds so emitted traces do not overlap the main chip group geometry.
- Path-path and path-object accidental overlaps were tightened out of the router.
- Split children now inherit branch direction according to their lateral order within the parent bundle, reducing sibling self-intersection.
- Connection behavior to earlier-chip pathways was strengthened, and collection connections remain rarer.
- Added regression coverage for four-side emission, perpendicular launch direction, continuous 45-degree turns, and no pathway/object intersections.

---

## CHANGELOG_V11_PATHWAY_DENSITY_AND_TRAVEL.md

# CHANGELOG V11 PATHWAY DENSITY AND TRAVEL

- Increased chip-emission bus width target to roughly **80–90%** of the emitting side length.
- Loosened pathway packing density by about **50%** via wider member spacing.
- Increased emitted pathway count accordingly so the wider bus still feels substantially populated.
- Reduced eagerness to terminate and pushed bundles toward longer exploratory travel before ending.
- Added distant exploration goals so bundles are more likely to venture across the plane before termination.
- Updated regression checks to cover launch coverage ratio and the wider bundle spacing band.

---

## CHANGELOG_V12_1_ESCAPE_GUARD.md

# CHANGELOG V12.1 ESCAPE GUARD

- Fixed a control-flow bug in pathway escape handling where `gkind` could be read before assignment when `goal` was `None`.
- The fix adds only the missing `goal is not None` guard.
- No generation probabilities, geometry rules, seed derivation, or pathway behavior were otherwise changed.

---

## CHANGELOG_V12_PATHWAY_COVERAGE_AND_CONNECTIONS.md

# CHANGELOG V12 PATHWAY COVERAGE AND CONNECTIONS

- Increased pathway coverage by pushing branches to travel longer before termination.
- Increased turn frequency so pathways explore the board more actively.
- Added stronger **parallel emergence / early exploration** behavior: freshly emerging bundles are not immediately blocked by existing pathway occupancy during their early travel phase.
- Strengthened pathway-to-pathway near-connection behavior, including denser anchor sampling and a larger near-connection envelope.
- Added `escape` behavior so a substantial fraction of pathway descendants continue toward an off-canvas exit instead of terminating on-board.
- Reduced split eagerness so individual traces can run farther before subdividing again.
- Increased maximum route length and reduced direct termination bias.

---

## CHANGELOG_V16_BUNDLE_GESTURES.md

# V16 — synchronous bundle gestures

V16 replaces only the pathway subsystem on top of the trusted v12.1 static-board baseline.
The rejected v15 holistic/A* implementation was not used as a source.

## Removed

- individual-trace A* and fine-grid destination routing;
- pathway candidate-seed retries and accepted-seed searching;
- hard realized-output quotas for connections, exits, coverage, or turns;
- synthetic rendezvous nodes and proximity reported as connectivity;
- micro-step rescue paths, compensating zigzags, and permissive lane collapse.

## Added

- one seeded, coherent pathway profile per board;
- `31U–39U` canvas-relative movement modules;
- synchronous rounds over all active bundle fronts;
- broad side buses followed by contiguous `4–7` trace cohorts;
- explicit structural branch trees with stable lateral order;
- long conditional gestures toward open/underused regions, edges, components, and foreign routes;
- analytic late expansion of bundle corridors into parallel trace lanes;
- physical trace-to-trace cross-chip terminal joins;
- a corridor-only visual debug stage;
- exact audits for static intersections, accidental crossings, collapsed centerlines,
  illegal turns, micro-zigzags, and segment length;
- direct arbitrary-seed and byte-identical same-seed regressions.

## Behavioral contract

Intent probabilities control what a bundle attempts. The generated static geometry controls what
can actually happen. Missing connections, escapes, branches, or long traversals are legitimate
best-effort outcomes and never cause a pathway retry or board regeneration.

## Build verification

- 14 tests pass.
- The fresh five-board 1000×1000 deliverable set completed in 10.9 seconds in one invocation.
- Ten additional boards from two unrelated base seeds completed in 21.3 seconds total.
- In that five-board probe, every pathway retry/search counter, static intersection count,
  unmarked crossing count, and collapsed overlap count is zero.

---

## CHANGELOG_V17_TRACEBACK_REROUTE.md

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

---

## CHANGELOG_V18_HOLISTIC_CONNECTIONS_AND_REPAIR.md

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

---

## CHANGELOG_V19_SPACING_BRANCHING_AND_PERSISTENCE.md

# V19 — inward chips, doubled chip moat, component keepout, stronger branching and bundle persistence

V19 builds directly on V18. The synchronous shared-round / holistic connection architecture remains active; no A* search, pathway seed retry, or accepted-output search is introduced.

## 1. Main-chip placement moved inward

- Main-chip final geometry must stay at least **120U** from every canvas edge.
- The existing 2/3 chip-count distribution is retained.

## 2. Main-chip exclusion moat doubled

- Secondary collections and isolated capacitors now require **170U edge-to-edge clearance** from every main chip (2× the V17/V18 85U breathing zone).
- Fixed a placement bug where the spatial query only searched 60U around a candidate even when the configured chip-secondary clearance was larger. The query now expands to the full moat before pair checks are evaluated.
- A direct three-chip / 18-secondary stress case succeeds with the corrected lookup while preserving the full moat.

## 3. Thicker no-touch perimeter around components

- Bundle corridor geometry must remain at least **4U** from every foreign static component.
- The corridor already contains the full trace/bundle stroke envelope, so this 4U is additional visible air beyond the line thickness.
- The source chip is exempt only for its own launch gesture; traces still begin outside the complete chip geometry.

## 4. Branching is 50–80% more likely

- The V18 base board-level branch appetite remains seeded at `0.34–0.54`.
- V19 multiplies the effective branch probability by a seeded **1.50–1.80** factor, capped below certainty.
- Ordinary structural branch rules, contiguous lane partitioning, lateral-order preservation and branch preflight remain unchanged.
- In recovery conditions, a branch may use a one-module lane-preserving rebase so a wide trapped cohort can split rather than repeatedly fail as one envelope.

## 5. Bundled termination strongly suppressed

- When a multi-trace front reaches its ordinary journey limit, it has only about **10%** of the former willingness to terminate.
- In the other ~90% case it attempts a useful branch and otherwise receives additional journey budget.
- A hard-stopped bundle first receives the normal extended repair budget. If that budget is exhausted, only about **10%** terminate while still bundled; the preferred outcome is recovery fragmentation into independent singleton fronts at their true materialized lane endpoints.
- Singleton traces are allowed to terminate normally. Component approaches, explicit physical connections and off-frame exits remain legitimate terminals.

## 6. Traceback / reroute extended

- Reroute budget: **5 → 7** attempts.
- Maximum progressive traceback depth: **4 → 6** accepted gestures.
- Recovery-mode duration: **3 → 4** decisions.
- Stagnation repair triggers earlier, and repeated same-sense turn drift may also schedule a repair.
- Existing connection recovery floors, loop rejection, collision rules and no-compensating-zigzag rules remain intact.

## Preserved hard invariants

- deterministic supplied-seed behavior;
- synchronous round planning and deterministic conflict resolution;
- no pathway candidate-seed retries;
- no A* / destination route search;
- no static intersections;
- no unmarked trace crossings;
- no collapsed centerlines;
- no compensating micro-zigzags;
- launch-side occupancy remains targeted at 70–90% of main-chip body width/height.

---

## CHANGELOG_V20_THICK_TRACES_HEAD_CONNECTIONS_AND_NO_INTERSECTIONS.md

# V20 — late-life branching, doubled trace gauge, head-only joins, and strict no-intersection routing

V20 builds directly on V19. The synchronous / holistic shared-round planner remains the routing architecture; no A*, pathway seed search, or realized-output quota search is introduced.

## 1. Late-life branch boost

- V19's seeded board-level branch appetite and `1.50–1.80×` general branch multiplier remain active.
- A route is considered in its **later life after ~60% of its originally planned gesture budget, with at least five accepted gestures**.
- In that later phase the branch probability receives an additional **1.50× multiplier** (capped below certainty).
- The 60% threshold is intentionally a first tuning guess and is reported as `late_life_branch_start=0.60`.

## 2. Trace gauge doubled and lane gap tied to stroke width

- Ordinary trace width is now **2.00–3.10U** (2× V19's 1.00–1.55U).
- Rare emphasis traces are also doubled to **5.0–7.4U**.
- Launch pitch is chosen so the **edge-to-edge gap is at least about 1.5× the adjacent pair's mean trace thickness**.
- Chip-side occupancy remains targeted at **72–90%** of the actual chip-body side.

## 3. Small-component routing perimeter doubled

- The foreign-static routing keepout is **8U**, doubled from V19's 4U.
- This 8U is extra air outside the complete routed stroke/bundle envelope; it is not merely a centerline distance.

## 4. Trace-to-trace connections are head-to-head only

- The former singleton-to-middle-of-foreign-lane attachment path is disabled.
- A trace already present in a physical connection cannot connect again.
- Connections terminate at the **free heads of both participating traces**; mid-line T-junctions are forbidden.
- Very close compatible cross-chip lane heads (within **1.90 routing modules**) are deterministic connection opportunities rather than probability rolls.
- Close heads may peel one lane out of a still-bundled cohort **only after** the complete terminal connection is proven collision-clean. Sibling lanes continue routing normally.
- The junction envelope is checked against third-party routes, so the two participating heads are the only geometry allowed in the connection overlap region.

## 5. Detached-prefix recovery lock

- When a lane peels out of a bundle for a connection, the remaining parent cohort's current route becomes a traceback floor.
- This prevents later recovery from rewinding shared geometry that the detached child still visibly owns, eliminating a subtle source of stale-prefix crossings.

## 6. No tiny emergence stubs

- Involuntary terminal routes shorter than **2.75 routing modules** are classified as abandoned recovery attempts and are not rendered as deliberate-looking stubs.
- Ordinary isolated termination remains allowed once the route has travelled meaningfully; component approaches, physical joins, and off-frame exits remain legitimate terminals.

## 7. Strict intersection / duplicate safeguards

- Ordinary proposal collision checks remain active at the bundle-corridor level.
- Head connections additionally receive an **exact materialized-lane stroke check** against every currently owned trace.
- Final materialization audits both centerlines and full thick-stroke geometry.
- Unmarked centerline crossings, collapsed/duplicated centerlines, thick-stroke overlaps/touches, multiply-connected traces, and non-head connections are all reported explicitly.
- A final deterministic safety filter suppresses any trace that would violate those hard rendered-geometry invariants; the V20 verification probes required **zero** such suppressions.

## Preserved rules

- deterministic same-seed behavior;
- shared synchronous planning rounds with deterministic commit conflict resolution;
- no pathway candidate-seed retry or A* search;
- anti-circle / anti-turn-drift behavior;
- extended V19 traceback/reroute and bundle-persistence behavior;
- 120U main-chip edge inset and 170U main-chip/secondary placement moat;
- 70–90% chip-side emergence target.

---

## CHANGELOG_V21_TERMINATION_MARKERS_BUNDLE_PERSISTENCE_AND_CHIP_KEEPOUT.md

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

---

## CHANGELOG_V22_BOUNDED_LOCAL_HOLISTIC_ROUTER.md

# V22 — Bounded Local Holistic Router

V22 replaces the increasingly repair-heavy V21 decision layer with a bounded local holistic scheduler while preserving the existing V21 geometry/materialization rules, trace styling, static placement, seed determinism, and hard collision invariants.

## Design-policy clarification

V22 makes the renderer's governing distinction explicit:

- **Hard invariants** are never traded away: no static intersections, no unmarked centerline or thick-stroke contacts, no doubled/collapsed traces, no mid-line joins, no multiply-connected trace, no compensating zig-zags, no overlapping termination markers, no tiny visible involuntary post-emergence stubs, and all configured chip/component keepouts remain authoritative.
- **Soft tendencies** are best-effort only: launch coverage, connection frequency, branching frequency, travel/coverage, frame exits, and bundled-termination suppression are intentions and diagnostics, not realized-output quotas.
- A constrained board is allowed to realize less of a soft tendency. The renderer must never retain bad geometry, regenerate the static board, or search indefinitely merely to hit a percentage.

This also removes the old final-materialization behavior that could keep a tiny failed trace visible solely to preserve >=70% realized launch span.

## Routing architecture

- Planner mode: `bounded_local_holistic_v22`.
- Open-space movement retains the cheap seeded V21 stochastic fast path.
- A **40×40 congestion field** provides inexpensive board-wide awareness.
- Explicit front lifecycle labels are maintained: `LAUNCHING`, `NORMAL`, `STRUCTURAL_TRANSITION`, `CONNECTION_PENDING`, `RECOVERING`, `TERMINAL`.
- Bounded foresight activates only for young, structural, recovering, connection-pending, failed, or congested fronts.
- Local future conflicts are grouped through a spatial broad phase. At most four fronts are jointly considered; each contributes only a tiny shortlist of candidates.
- The local scheduler prefers compatible futures rather than allowing one greedy move to consume another front's only near-term corridor.
- Active-front blocker yielding remains bounded and local; it is not a global board re-route.

## Transactional topology

- Launch fans and ordinary branches are preflighted before topology commits.
- V22 fan birth uses a tiny bounded permutation of non-crossing child maneuvers instead of insisting on one decorative left/right peel when geometry makes that exact fan impossible.
- A structural child is not intentionally born into an immediately blocked continuation.
- Connection detachment may peel only an **outer lane** of a live cohort. Interior lanes must first become exposed through a real contiguous branch.
- Detached prefixes remain recovery-locked so later traceback cannot erase geometry already inherited by a connected child.

## Connections

- Trace-to-trace joins remain **head-to-head only**.
- A trace may participate in at most one trace connection.
- Close compatible heads receive deterministic priority when a legal physical join exists.
- Same-chip-side ancestry no longer blocks an otherwise legitimate close free-head join.
- Final marker arbitration may perform bounded local blocker negotiation: an unrelated terminal singleton can rewind only its own local tail, allow an obvious head pair to connect, then attempt a bounded escape around the new join.
- No mid-line/T attachment is reintroduced.

## Recovery and termination

- Deferred reroute/traceback remains available, but V22 uses prevention and bounded foresight before escalating recovery.
- Young bundles prefer legitimate transactional branching before recovery fragmentation.
- Proactive persistence fragmentation is withheld until a cohort has made meaningful travel.
- Tiny involuntary terminated leaves below 2.75 modules are never retained merely to protect a launch-percentage target; they are suppressed as failed speculative routing.
- Escape-beam and final-exit checks now inspect the complete inherited visible history of recovery singletons, preventing a local child from creating a hidden prefix-boundary A→B→A zig-zag.

## Preserved V21/V20 geometry rules

- 2× termination dots; hollow stroke 2.70U; hollow traces stop at the marker border.
- Ordinary trace widths 2.00–3.10U with rare emphasis traces.
- Lane edge gaps target roughly 1.5× adjacent mean line thickness and also accommodate enlarged endpoint dots.
- 8U foreign secondary/static routing keepout.
- 24U foreign/main-chip routing keepout with source-chip monotonic outward egress semantics.
- 170U chip-to-secondary static-placement moat and 120U chip-to-frame placement inset.
- Late-life branching begins around 60% of sampled lifespan and receives a further 1.50× tendency multiplier.
- Same seed and parameters remain deterministic; no pathway seed search, A*, or pathway-driven static-board restart is used.

---

## CHANGELOG_V23_LOCAL_GAP_PATHWAYS_AND_CAPACITORS.md

# V23 — Local-gap pathways, source markers, and capacitor tuning

V23 is built on the frozen V22 bounded-local-holistic router. It does **not** replace or relax the V22 hard routing invariants.

## 1. Source markers

- Every visible pathway trace now has a filled or hollow circular marker at its source/emergence point.
- Source markers use the same marker radius/stroke language as terminal markers.
- Hollow source markers clip the trace at the marker's **outer stroke boundary**, so the line is never visible passing through the hollow center.
- The marker draw choice uses a dedicated deterministic per-trace RNG and therefore does not perturb route decisions.

## 2. Capacitor occurrence

- Collection-family sampling weight for `capacitor_circle` increases from **1.30 → 3.90** (exactly 3×).
- The independent isolated-capacitor occurrence path was already 0.72; multiplying by 3 saturates at probability **1.00**.
- The existing independent isolated count rule remains 1–3 and is still continuously derived rather than selected from a count menu.

## 3. Capacitor size variance

- Continuous radius formula changes from:
  - `(4.2 + 5.8 * R^0.90)U`
  - to `(4.2 + 8.7 * R^0.90)U`
- The additive size span is therefore **50% wider**.
- Resulting continuous radius range is **4.2U–12.9U**.

## 4. Sparse local-gap pathway phase

Main-chip pathways route first. Only after that network is frozen does V23 search residual free space for local pathway sources.

- Candidate sources come from a small jittered residual-space grid.
- Candidate scoring prefers high static/path clearance and low local congestion.
- The phase intentionally samples only a few useful gaps; it does **not** try to fill every empty region.
- A failed local source/path is simply omitted. Local-gap realization is a soft best-effort outcome, never a board-acceptance quota.
- Ordinary local roots contain **2–5 traces**.
- Local roots use the same V22 direction grammar, branch logic, connection logic, collision rules, keepouts, anti-loop checks, traceback/reroute, endpoint handling, and thick-stroke audits.
- Because these routes are explicitly local accents, their second-pass horizon is bounded to **20 normal rounds + up to 6 persistence rounds** rather than another full board-spanning horizon.

## 5. Extra-thick local singleton traces

- The target share is **5–10% of the planned local trace population**.
- Special traces always spawn as **single-member roots**, never as bundles.
- Their width is sampled as **5–8× a freshly sampled ordinary trace width**.
- They retain the same collision/keepout/connection/termination grammar as other local traces.

## 6. Hard-rule preservation

V23 keeps the V22 hard-vs-soft contract:

Hard invariants remain hard, including no static intersection, no unmarked thick-stroke contact, no doubled/collapsed traces, no compensating zigzags, no mid-line connection, no multiply-connected trace, no visible tiny involuntary death, and no overlapping terminal markers.

The local-gap system is never allowed to violate those rules merely to realize more filler.

---

## CHANGELOG_V24_DENSER_LOCAL_GAPS_AND_HOLLOW_THICK_CAPS.md

# V24 — Denser local gaps, branching local cohorts, hollow thick caps, and launch spacing

V24 is built on V23 and preserves the V22/V23 hard-routing contract. The changes are local-gap and rendering refinements; main holistic routing rules are not weakened.

## 1. Verification runtime policy

Wall-clock verification timeouts scale with the number of generated samples: each geometry-heavy sample receives its own per-sample allowance, so an N-sample verification batch is budgeted approximately N times the single-sample allowance. This is a verifier/runtime policy, not a reason to multiply routing search depth by trace count.

## 2. Denser local-gap population

- Residual-space candidate grid increases from 9×9 to 12×12.
- V24 normally attempts 6–7 ordinary local bundle roots instead of V23's 3–4.
- Ordinary local roots now begin with 3–4 traces.
- Source spacing is reduced enough to use separate residual holes while the exact collision/keepout checks remain authoritative.
- Local roots receive 10–15 gesture life budgets and the local second pass uses 24 normal rounds + up to 6 persistence rounds.
- Failed local routes remain best-effort omissions; gap coverage is never a quota.

## 3. Local bundle breakup bias

V23 local children could lose their local identity after a branch. V24 propagates `local_gap`, `local_gap_special`, and the local branch profile through topology/recovery changes.

- Local-gap branch appetite receives a 1.90× multiplier.
- Local branching can begin after one local gesture.
- The local late-life threshold begins around 35% of planned life and adds another 1.35× boost.
- Mature local bundles receive strong minimum branch tendencies (about 0.90 for 3+ traces, 0.80 for 2 traces when geometry allows).
- Local normal branches first split into narrower contiguous parallel cohorts with a one-module rebase; the children then make independent normal routing decisions. This is more feasible inside constrained gaps than insisting on a wide immediate decorative fan.

All branch births remain transactional and collision checked.

## 4. Special thick local traces

- V23's 5–10% special probability is tripled to a seeded soft target of 15–30%.
- Special roots remain singleton-only.
- Thickness remains 5–8× a freshly sampled ordinary line width.
- They no longer receive separate source/termination-dot primitives.
- Their actual polyline uses round caps. A background-coloured negative circle is placed inside the visible source cap, and inside a free terminal cap when the trace terminates. Connected/component ends remain solid so the connection is not visually broken.

## 5. Main-chip emission gap

The visible source point of each main-chip trace is moved three times farther from the chip than V23:

- V23: 7.5U
- V24: 22.5U

This affects the chip-to-emitting-line gap only; the existing 24U foreign/main-chip routing keepout remains unchanged.

## 6. Capacitors

V23's capacitor tuning remains active unchanged:

- collection capacitor weight = 3.90 (3× the pre-V23 value);
- isolated capacitor occurrence saturates at 1.00;
- continuous radius range = 4.2U–12.9U (+50% size span).

---

## CHANGELOG_V25_ROUTE_FIRST_RESIDUAL_FILL_AND_MAIN_SCALE.md

# V25 — Route-First Residual Fill + Independent Main Scale

V25 changes generation dependency order rather than adding more routing search.

## Architectural change

The active generation order is now:

1. main chips are generated and placed;
2. primary chip-emitted pathways are routed against main chips only;
3. local residual-gap pathways are routed against the frozen main network;
4. all pathway geometry is frozen;
5. collections and isolated capacitors are generated and placed into the residual free field.

Secondary components no longer exist spatially while the router is running. They cannot block a
candidate gesture, force a split, cause traceback, terminate a lane, or otherwise steer the pathway
network.

The existing V24 main/local bundle grammar, branching behavior, thick local accents, source markers,
anti-collapse rules, head-only connection rules, and hard geometry audits remain active.

## Router-side component intent removed

The V24 `component` routing intent is removed from the active planner. V25 routing intentions are
pathway-native: connect, exit, and explore.

Rare pathway-to-small-component relationships are reversed. After routing, an isolated capacitor may
be placed on an eligible free pathway terminal. The component adapts to the route; the route never
searches for a not-yet-existing component.

## Residual component fill

The final component pass samples a soft target in `[0.75, 0.90]` and constructs a bounded seeded set of
representative residual gap sites from the routed board. Larger collections are placed first and small
isolated capacitors fill later pockets.

The active post-route clearances are:

- main chip ↔ secondary component: `42U`
- pathway ↔ non-attached secondary component: `10U`
- secondary component ↔ secondary component: `12U`
- secondary component ↔ frame: `20U`

The historical `170U` pre-route chip-secondary moat is no longer the active final-placement rule; its
routing-reservation purpose is obsolete once components are placed after pathways.

The 75–90% value is gap-site coverage, not literal raw canvas-area packing. Exact transformed geometry
still has final authority. If a pathological component population cannot fit, the sample may restart,
but the frozen route network is never rerouted around components.

## Independent main scale

`V27Renderer(..., main_scale=1.0)` and CLI `--main-scale` now expose an explicit positive master geometry
scale independent of canvas width/height.

Internally:

```text
S_canvas = min(W,H)
S = S_canvas * main_scale
U = S / 1200
```

Thus a 1200×1200 canvas at `main_scale=0.65` remains 1200×1200 while all S/U-derived chips, components,
strokes, clearances, and pathway modules become 65% of default physical size.

The renderer never mutates `main_scale` automatically to solve fit or routing problems.

## Determinism

No new non-deterministic stream is introduced. Post-route component filling uses a seed derived from the
sample seed. Same seed + same canvas + same `main_scale` produces the same result.

---

## CHANGELOG_V29_GAP_COVERAGE_EARLY_RECOVERY_AND_CAPACITOR_SCALE.md

# V29 — Gap Coverage, Early Recovery, Terminal Clearance, Capacitor Scale

V29 keeps V28's route-first generation order:

1. main chips,
2. primary pathways,
3. local gap pathways,
4. residual components.

No secondary component geometry is restored to the router.

## Routing changes

- Launching fronts now enter bounded reroute/recovery after the first failed movement instead of waiting through repeated early hard blocks.
- Launching fronts evaluate three bounded proposal variants and receive six recovery-mode rounds. The global reroute budget remains bounded at 7.
- Head-to-head connection eligibility begins after one accepted gesture. Close, facing young heads from different chips receive deterministic exact-checked connection priority out to 5 routing modules, so two newly emerged networks can join instead of spending recovery budget blocking each other.
- Terminal survival checks use the shortest actually materialized lane rather than bundle-centre travel, preventing an inside turn lane from being treated as a valid long terminal when it is still physically short.
- Local-gap recovery is deliberately cheaper than main recovery: at most 4 reroute attempts and at most 2 traceback gestures per attempt.

## Local-gap composition

- The local phase now measures representative residual open cells after the primary network freezes.
- A seeded soft target of `Uniform(0.38, 0.42)` of those residual cells is used as the local-line coverage objective.
- Up to three bounded adaptive waves may be launched. Later waves are sized from the measured remaining coverage deficit rather than a fixed source-count quota.
- Ordinary local roots contain 3–4 traces.
- Local bundles receive a seeded `3.0–5.0×` branch-probability multiplier relative to normal branch behavior.
- Local branch children attempt visible `±45°` peel directions toward uncovered cells in their current gap; straight continuation is only a bounded fallback when the preferred peel is not legal.
- Local frame-exit permission is multiplied by `0.50`. Near-frame interior pivots and residual-gap targets are preferred, and the persistence tail does not forcibly convert local bundles to exit intent.
- The existing 15–30% special-thick local trace population intent remains active cumulatively across adaptive waves.

## Terminal-head clearance

- Free terminal heads receive an additional `4.5U` visual clearance target from foreign pathway geometry.
- This is solved after topology is frozen by backing the terminal polyline up along its already-valid path before placing the endpoint marker.
- Backoff is not a route search and does not reopen routing contention.
- Candidate backoff positions preserve the existing visible minimum-segment invariant and prioritize zero terminal-marker overlap.

## Component fill

- Residual component gap-site fill target changes from 75–90% to 80–90% after local routing is frozen.
- Component placement still never causes pathway rerouting.

## Capacitor size

The complete active capacitor radius expression is shifted upward by 50%:

- V28: `r = (4.2 + 8.7*R^0.90)U`
- V29: `r = (6.3 + 13.05*R^0.90)U`

This is exactly `1.5×` the V28 radius for every sampled driver value `R`.

## Version naming

V29 continues the single active version-number scheme. Historical changelogs and verification files retain their original names and content.

---

## CHANGELOG_V30_DEFAULT_RUNTIME_AND_COMPONENT_RECOVERY.md

# V30 — Default Runtime and Component-Recovery Correction

## Trigger

An untouched V29 default invocation (`count=1`, no seed, no `main-scale`, no benchmark/test seed,
no search-budget or retry/calibration overrides) was observed to produce no SVG within a five-minute
execution window. This is a release-blocking runtime regression; default generation must not rely on a
lucky seed.

## Root causes found

1. **Residual-fill hot-loop regression.** `place_residual_components()` correctly precomputed buffered
   chip/pathway unions for its normal site-placement path, but the 720-candidate whole-field fallback
   called `_component_candidate_valid()` without passing those cached unions. Every fallback candidate
   could therefore rebuild the complete buffered routed-network union. V29's ~40% local network and
   1.5× capacitor size made fallback more likely and made that accidental recomputation much more costly.
2. **Late component-only rejection.** Component template generation/calibration, ordinary-family
   coverage, scale checks, dense balance, IC-contact checks, and uniqueness were still allowed to fail
   after routing. Those failures caused an expensive routed board to be discarded even though the
   failure had no dependency on route geometry.
3. **Post-route layout failure could multiply routing work.** A failed final component layout used the
   complete-sample retry path instead of first exhausting component-only alternatives on the already
   frozen pathway network.
4. **Ordinary-family assignment could leave a known-invalid coverage result.** The bounded swap repair
   could stop without achieving the minimum two occurrences of each required ordinary family and defer
   discovery until later validation.

## V30 corrections

- The whole-field component fallback always receives and reuses the precomputed chip and pathway
  keepout unions. Rebuilding the complete routed-network union inside a fallback candidate is forbidden.
- Non-spatial component templates are generated/calibrated before routing. They have no canvas position,
  are not added to routing occupancy, and cannot influence pathway decisions.
- Template-only validation now happens before `generate_pathways()`: collection scale calibration,
  special-family quotas, ordinary-family coverage, dense-shape balance, IC required contacts, and
  collection uniqueness.
- If the ordinary-family assignment repair cannot achieve required coverage, the assignment is rejected
  immediately before any geometry/routing work.
- Final component placement runs on the frozen main+local pathway network and receives bounded
  deterministic layout retries.
- If needed, bounded alternate component populations are regenerated/calibrated and placed against the
  same frozen routes. This does not invoke pathway traceback or rerouting.
- Successful reports explicitly record:
  - `component_templates_prepared_before_routing = true`
  - `route_restarted_for_component_failure = false`
- No elapsed-time value influences generation; fixes are deterministic dependency/work corrections.
- Final arbitrary-seed verification exposed one pre-existing materialization-only short `A→B→A`
  terminal twitch. V30 suppresses such free terminal/escaped leaves at materialization rather than
  rendering the hard zigzag violation or invoking route search. Connected traces remain governed by
  the existing connection-leg zigzag guard.

## What did not change

- Main chips remain the only static objects present spatially during primary routing.
- Main routing, ~38–42% local-gap routing, 3–5× local branch tendency, half-rate local frame exits,
  terminal-head backoff, 1.5× capacitor radius range, and 80–90% residual component gap-site target are
  unchanged from V29.
- No A*, global route search, route-seed search, or component-driven route search was added.
- `main_scale` behavior is unchanged.
- Historical changelog/verification files are retained as history and are not rewritten.

---

## CHANGELOG_V31_TRANSACTIONAL_PARALLEL_ROUTING.md

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

---

## CHANGELOG_V32_SOURCE_EGRESS_FAMILY_PROTECTION.md

# V32 — Source-Egress Family Protection and Materialization Consistency

V32 is a routing-correctness release. It preserves V31 transactional parallel rounds and V30 route-first runtime architecture while closing the remaining premature-main-line death paths.

## Active changes

- Main-chip source buses remain straight and structurally indivisible until the shortest physical lane clears 4 routing modules from the chip. This applies even to single-cohort sides.
- Source maturity is derived from current physical lane length. Traceback below the boundary reactivates launch protection and per-lane egress reservations.
- Temporary per-lane egress reservations prevent mature/foreign routes and local fillers from stealing a still-emerging lane's corridor; young-vs-young main families remain transactional peers.
- Protected same-family conflict transactions may atomically HOLD some siblings for a round. Local-only conflict transactions may also HOLD, preventing all-or-nothing gesture-zero deadlocks.
- The bundle proposal corridor uses a flat leading edge; turn/miter clearance remains conservative.
- The gesture-start ownership disk no longer hides foreign committed geometry near the current head. Self/ancestor continuation alone receives that exemption.
- Main routes below 4 physical modules cannot be terminalized/pruned. Routes that just clear source egress receive one bounded soft persistence attempt toward 6 modules without creating a hard runtime quota.
- Escaped polylines are rendered only to their first frame crossing. Invisible off-canvas continuation cannot cause final collision cleanup to suppress an otherwise valid visible trace.
- Terminal backoff/hollow-marker clipping cannot manufacture a sub-0.10-module visible final segment; a filled marker is used when hollow clipping would do so.
- Legal connection-junction overlap radius is thickness-aware in both exact connection validation and final render audit, including extra-thick local traces.
- Main-launch survival and main-short-terminal metrics are explicitly reported, and unequal launched/visible main counts now reject the routing result instead of silently shipping cleanup loss.

## Local-gap consequence

The stricter main geometry changed residual topology and exposed an all-or-nothing deadlock in local waves. V32 permits atomic HOLD in local-only conflict groups. This restores the existing ~38–42% target without increasing global search or simply multiplying source count.

## Non-changes

- No A* or global route search.
- No secondary components during routing.
- No change to the V29 capacitor-size rule, local branch multiplier, local exit factor, component-fill target, or independent `main_scale` argument.
- Historical changelogs and verification records are not rewritten.

---

## CHANGELOG_V33_SPACE_AWARE_GAP_FILL_AND_CONNECTION_REBALANCE.md

# V33 — Space-Aware Gap Fill and Connection Rebalance

V33 retains the V31 transactional-parallel routing core, V32 source-egress/family protection, route-first dependency order, and independent `main_scale`. It fixes the compositional regressions visible after V32 without restoring component obstacles or global route search.

## Main chips and main network

- Main-chip pair clearance target increased to **210U** and chip placement strongly prefers spread-out solutions.
- Cross-chip networking appetite is restored; accepted multi-chip routing must produce at least one true cross-chip connection.
- Added a bounded post-main terminal connection sweep using exact geometry.
- All launched main lanes must remain visible and a whole emitted side may not be accepted as only short terminated traces (`pathway_main_stalled_side_count == 0`).
- Unauthorized line/stroke overlaps remain hard failures; final cleanup may not silently remove a main lane.

## Local gap network

- Replaced the coarse global gap heuristic with a connected **24×24 residual-region field**.
- Regions carry area, spans, center, size class, and principal orientation.
- Local gap target is now **40–50%** of residual gap influence area (bounded final-line overshoot may reach roughly 55%).
- Ordinary local fillers are born as **independent singleton lines**, not pre-bundled roots.
- Small regions receive fewer/shorter/thinner fillers; large regions receive proportionally more/longer activity.
- Per-region source capacity and unmet-area weighting stop one large room from monopolizing filler sources.
- Compatible independent local lines in the same region have a deterministic **50%** chance to travel as a temporary parallel pair for **2–4 atomic rounds**, then release and resume independent gap seeking. Each line may bundle at most once.
- Existing local 3–5× branching boost and 50% frame-exit factor are retained.

## Components

- Replaced representative point-site coverage as the governing metric with connected **28×28 residual-region analysis**.
- Component service target is **90–94% of remaining connected residual-region area**.
- Large established collections are fitted first; bounded gap-sized capacitors/dots/dashes/squares/circles mop up unserved pockets according to local region size/capacity.
- Density target scales with residual cells, capped at 46 accepted component placement sets; mop-up adds at most 28 extra fillers.
- Unauthorized component/pathway overlap is a hard failure. Only an explicitly designated terminal attachment may contact a path.
- Component recovery remains component-only against frozen routes; it never triggers rerouting.

## Runtime

- Batch default is one full sample attempt per logical index before deterministic skip. This prevents one impossible protected-routing topology from multiplying full reroutes. `--max-sample-restarts` still permits explicit overrides.

## Historical policy

All V4–V32 changelog and verification files remain historical records and are not rewritten by V33.

