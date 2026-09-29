# LOCAL filling architecture review ? 2026-09-29

This is a dated design review, not a change to governing renderer behavior. Current task, approvals and qualification remain in [CONTEXT.md](../CONTEXT.md). The [workflow](WORKFLOW.md) and design language remain authoritative.

## Diagnosis

The current constructor builds an ordinary LOCAL atlas before completion components. Component admission retires complete colliding families. The area-support ledger accurately accounts for those losses, including designed interline gaps, but the atlas has no operation creating replacement capacity. Its proportional admission threshold conserves a shrinking supply: it cannot establish either requested absolute allocation. Merely removing that threshold moves the shortage to LOCAL.

On the exact latest sample, current v5 output is C=.283329 and L=.152565 for D=.9/q=.65. Changing D to .75 produces .444312 total rather than .435894: the generation decisions depend on the requested target, so the knob can change the construction outcome adversely. Independent SVG recounts agree; this is not a reporting discrepancy. Component-first and full-atlas trials also miss the joint target. Finite constructor failure does not prove physical impossibility.

The ordinary scheduler seeks untouched cells and rewards distance from existing paths, whereas actual designed-gap credit also depends on nearby trace support. This objective mismatch is a hypothesis worth diagnosing, not evidence that changing one score will fix packing. Earlier isolated targeting/population changes failed or worsened geometry.

## Proposed alternative

Test a monotone campaign of complete mixed proposals. A proposal must co-design a bounded component cluster and complete LOCAL families against the same actual free geometry. It includes independent births, bends, branches, tails, final markers, component hull protection and the exact incremental C/L union. Alternatives remain provisional. Commit only a fully legal combination, register it incrementally, and preserve already committed geometry.

The new operation must create positive joint capacity. Replacing one component cluster while losing fewer LOCAL bits is insufficient. A bank of independently generated components and independently generated routes is also insufficient: previous exact finite catalogs showed almost all routes crossing the chosen components. Templates confined to fixed rectangles and fixed inherited ports have already failed in MAIN-fragmented spaces. Do not repeat them without a new causal hypothesis.

For density response, investigate a target-independent full-capacity mixed plan at fixed q, followed by spatially fair whole-proposal selection for D. A monotone selection can prevent D inversion, but cannot repair an under-capacity plan; both absolute targets still need independent proof. Selection must count inter-proposal gap dependencies from emitted geometry, not assume additive packet areas. No such plan or sufficient capacity witness currently exists.

## Preserve the optimized work model

Existing global planner calls cannot be invoked per proposal:

- `_launch_local_gap_fronts` reconstructs counts, available candidates and nearest-geometry STRtrees.
- `_residual_gap_regions` scans and relabels the full field.
- `_run_local_gap_fast_rounds` finalizes all remaining LOCAL fronts on return.
- `_plan_residual_local_atlas` constructs complete dependency families after global materialization.

A prototype needs local query inputs, separate advancement/finalization, stable ownership, incrementally maintained geometry/support indexes, and an owned queue entry per candidate. No repeated global campaign, per-cluster full render, whole-board rescore or lazy accumulation of unlimited stale queue entries is acceptable.

Let N be canonical cells, P candidate anchors, K allowed alternatives per anchor, W bounded local construction work and I actual indexed geometry/support incidences. The intended cost is O(N + P*K*W + I), optionally O(P log P) for scheduling. This expression is not a proof until K/W and repeated-incidence counts are bounded. Record field scans, candidates, gesture checks, exact pair checks, touched area bits, queue updates and discarded work. Measure CPU and CPU/useful-work across .75 then .5, including failed candidates. Near-linear performance and adequate density are separate acceptance requirements.

## Constraints and approval boundary

Keep frozen MAIN, deterministic seed ownership, component-first final collision ownership/emission, the canonical C=D*q/L=D*(1-q) measure, every exact clearance, octilinear articulated LOCAL grammar, seeded singleton/bundling/branching behavior, bounded distributed component clusters, and existing work/retry ceilings. Current ?19.2.1 already allows joint prospective construction and causal local capacity addition; this does not need a new permission request.

Design-language ?29.26.2 also fixes LOCAL group envelopes to two six-cell chunks per axis plus a four-module border. That is an explicit specification, even though it is a scheduling mechanism rather than physical clearance. A potential alternative follows connected free-space shape while capping cells/visits/work per group. This could address irregular domains but is unproved; the user authorized a bounded experimental replacement on 2026-09-29. Production promotion and other constraint changes are not authorized by that experimental approval. No unbounded-envelope change is justified by this review.

The mandated y/x minimum-certificate sweep and chunk round-robin completion in ?29.27 remain in force unless explicitly superseded. A new prospective ordinary mixed constructor can initially coexist with them; do not silently remove the fallback or its anti-pileup guarantees. Precise visual probabilities should not be relaxed merely for convenient templates. Older LOCAL-before-components and 80?90% service-floor wording is superseded by ??19.2.1/29.28.

## Evidence gate before rewriting production

Use frozen MAIN and prepared components from the failing exact seed. Examine an open room, a narrow corridor and a fragmented pocket with existing candidate/work limits. Require fully materialized positive C/L proposals, exact geometry/marker/hull checks, independent v5 area accounting, and explicit local work counts. If an authorized shape-adaptive envelope is tested, use the same inputs and work ceilings as the fixed-envelope control and charge field construction once.

A local witness only justifies a one-pass board-wide scratch trial; it is not a density fix. Production integration needs a complete mixed-area witness, neighboring D/q checks including endpoints, no density inversion, visual review for cluster/short-line concentration, independent emitted recount, geometry audits, full release/stress and scaling qualification. Failures should disprove the candidate hypothesis rather than cause retry inflation or successive special cases.

## Authorized fixed-envelope sensitivity result

The bounded experiment is complete on the exact frozen component-first state (3 chips, 12 MAIN groups, 819 components; C=.585449). The control and candidate use the same current renderer and exact collision/marker guards. The candidate partitions existing physical route cells once by four-neighbor growth: at most 144 owned cells and 24 cells per axis, followed by the existing four-module halo. New ownership also drives region/target nomination; changing only polygon guards would not test the intended hypothesis.

| Measurement | Fixed boxes | Adaptive neighborhoods |
|---|---:|---:|
| Canonical LOCAL fraction | .192831 | .197540 |
| LOCAL target | .315000 | .315000 |
| Region count | 613 | 465 |
| Visible LOCAL traces | 613 | 606 |
| Short-trace diagnostic count | 491 | 482 |
| Deterministic debt traces | 292 | 322 |
| CPU seconds | 31.047 | 33.828 |
| Reported geometry violations | 0 | 0 |

The new partition assigns all 3,043 eligible cells once, checks exactly 12,172 neighbors (4 per cell), and builds 3,043 cell boxes. The largest actual group has 83 owned cells. Sorting adds O(N log N); connected growth and bounded geometry construction add no per-group whole-field scan. These structural bounds do not qualify whole-render CPU scaling: only one fixed-state comparison was run, and no scaling claim is made.

Independent serialized-SVG recount gives LOCAL .192799 versus .197489; differences from in-memory reports are 5 and 8 canonical bits at serialized geometry boundaries. Component recount differs by 4 bits in both variants. The candidate PNG was inspected: the layout remains fragmented and many short fillers remain. It does not establish visual acceptance or the density contract.

Conclusion: removing fixed-box fragmentation gains only .004709 of post-MAIN area (0.47 percentage points), with about 9% more CPU and more deterministic debt traces. This does not justify production integration or a larger rewrite centered on envelope shape. The underlying need to co-design actual component and LOCAL capacity remains. No production/specification edit follows from this sensitivity test. Source hash before/after is B4290529D44529730631C046BE84DACCDA87339E5F869509C8C19000D89C897C.

The completed experiment source and small receipts are preserved in [the experiment archive](../archive/experiments/2026-09-29-adaptive-local-envelopes/README.md). Independent emitted-group recount exactly matches both in-memory totals; 102 adaptive groups containing1,909 cells cross former parcel seams, confirming the sensitivity changed actual nomination reach.

## Prospective mixed packet probe

The user subsequently authorized implementing the small prototype. The [completed diagnostic source and receipts](../archive/experiments/2026-09-29-prospective-mixed-packets/README.md) are insufficient for promotion. On the exact prepared failing sample, room and fragmented cases admit small compatible component/LOCAL proposals with independently verified ?C/?L of132/115 and117/295 bits. The corridor admits no component. Each successful case realizes only1 of its seeded3-member cluster; neither demonstrates useful target-level filling. All use the same sample LOCAL profile and current v5 accounting, actual cluster hull exclusion and exact geometry gates. The two positive proposal SVGs were independently recounted exactly and their cropped renders inspected; they are separate alternatives, not a combined board.

The harness exposes both remaining defects directly: its routes are fixed before component fitting (atomic acceptance alone is not shape co-design), and existing setup rescans12,544 cells/rebuilds global scoring inputs per case. That setup must never be wrapped in a per-cluster production loop. Thus this prototype does not satisfy the proposed evidence gate and does not justify a production rewrite or scaling qualification. Any further constructor must establish the component cluster footprint and articulated route opportunity together before either becomes fixed, with scoped indexed construction inputs. No actual implementation of that sufficient constructor exists yet.
