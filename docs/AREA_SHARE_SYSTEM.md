# Residual density scoring and occupied-area history

Current production is restored exactly to the referenced 2026-09-04 clean renderer, including its seeded legacy-total scaling and original construction. Later physical-area accounting, literal-service targets and clustering changes below are superseded historical evidence. Live status is in [CONTEXT.md](../CONTEXT.md).

## Superseded investigation and partial restoration

# Residual density scoring and occupied-area history

On 2026-09-30 the user restored connected-region component service scoring because
the 2026-09-04 renderer visibly distributed components and LOCAL lines well. The
current renderer uses literal `D` and `q` allocations in service-score units:
components earn region-weighted size/quantity credit, while LOCAL earns final
emitted line-and-designed-gap credit. Components freeze before one LOCAL routing
campaign; complete dependency families are selected toward the LOCAL share. The
current dispersed component-cluster constructor and exact geometry limits remain.
The former common physical-area measure is still independently reported as a
diagnostic, never under the component service-score label. Earlier results below
describe the superseded physical-area control and remain historical evidence.
Live status and qualification are in [CONTEXT.md](../CONTEXT.md).

The latest user clarification authorizes actual designed gaps between nearby LOCAL lines.
Metric v5 retains the restored half-spacing base ribbons, then credits bounded interline
spaces supported by at least two emitted traces. The locality bound is the existing 2.20-module
independent-source spacing; an isolated trace does not gain an enlarged halo. The shared
canonical MAIN-free field clips all credit and component-owned samples remain excluded.
Component enclosure/cluster-interior accounting and physical clearance are unchanged.
Historical measurements below use earlier metrics and are not current density receipts.
Live implementation and qualification status is in [CONTEXT.md](../CONTEXT.md).

## User rejection of the soft-density implementation

The 2026-09-27 implementation described below passed finite technical gates but did not meet
the density contract. At requested total occupancy .9 and component share .6 it produced only
.265/.280/.271 total occupancy on the three exact samples. An almost exact .6 ratio does not
compensate for those blank areas. The fixed ordinary LOCAL atlas began at only about .149 area
on sample 0 and could only lose complete route families after component admission. Even before
those losses, that atlas bounds exact-.6 total occupancy to about .372; it cannot fund the
requested .36 LOCAL allocation after filling components. The component gate and final LOCAL cap
then suppress both modalities. This is an algorithmic bound of that implementation, not a proof
of a physical packing limit. Its source is [preserved](../archive/releases/v48_area_share_soft_density_rejected_2026-09-27/README.md).

The governing contract now requires the requested total area and split together. The correction
is active in [CONTEXT.md](../CONTEXT.md); the old qualification data below is historical evidence
only and must not be interpreted as acceptance of the soft-density behavior.

Further exact-sample-0 probes isolated two independent construction defects. Replanning LOCAL
after the current mixed component placement reaches .339 LOCAL area toward the requested .36,
versus .106 from the fixed-atlas selector, but component area remains only .159 toward .54.
The current component-only constructor reaches .461 component area; fresh LOCAL routing around
that placement reaches only .052. Its 323 protected cluster territories leave .307 area outside
component enclosures. After conservatively allowing the widest legal LOCAL ribbon to reach into
those territories, .1098 of the field still cannot be occupied by either modality, proving that
**that particular placement** cannot reach .9 total. This is not a global geometry limit.
Scratch-only exact-legal contact placement raises component area to .503, still below .54 and
without a joint LOCAL witness. The root correction must combine compact component-cluster
packing with causal LOCAL reflow; none of these isolated probes is a qualified replacement.

## Why the prior share did not describe composition

The component metric credited connected room area in proportion to component size/quantity
quotas. Sparse assemblies could service large rooms. LOCAL measured coverage ribbons instead.
Their ratio was reported as a shared-budget fraction despite incompatible numerators.

Read-only measurement of the three user samples (scale .5, chip multiplier .75, run multiplier 2,
local density .9, component share .6; batch base 14864835225619827578, indices 0/1/2) establishes:

| Sample | Old reported component share | Component enclosure/half-gap area | LOCAL half-gap area | Common physical component share |
|---|---:|---:|---:|---:|
| 0 | .60073 | .12712 | .19274 | .39742 |
| 1 | .62072 | .13182 | .18799 | .41218 |
| 2 | .60170 | .13570 | .18900 | .41793 |

Areas use a frozen post-MAIN raster, including whole component-group bounding rectangles and
half the required surrounding component spacing; LOCAL uses stroke plus allocated half-gap
ribbons and excludes component-owned samples. Overlap is unioned rather than counted twice.
Continuous Shapely enclosure/line areas give similar results, with expected raster differences.
No arbitrary connected-room credit or painted-pixel-only definition is used.

## Authorized replacement

Design language section 19.2.1 governs literal physical occupied-area targets and all defaults.
D=local_density requests total area and q=component_density requests component share.
Nominal allocations are D*q and D*(1-q), measured on one subcell field independently tested
against frozen MAIN keepouts and edges. Construction targets actual component enclosure gain.
Finite construction opportunity can limit achievable density; this is not proof of globally
maximum packing. After the required prepared component population freezes, one complete ordinary LOCAL atlas is planned against that baseline and frozen MAIN. Additional component admission must preserve
enough surviving complete route-family certificates for its paired share, including prospective
cluster hulls and exact clearance. Final spatial selection spends only required certificates.
This proactively preserves route opportunity rather than relying on a late LOCAL cap after
components have consumed the field. Reports expose actual area/share,
allocation caps and shortfalls rather than claiming success from the old quota score.

MAIN, coherent component grammar, clearances, octilinearity, seed ownership and fair LOCAL debt
remain governing. The preceding renderer is [preserved](../archive/releases/v48_debt_fair_selection_2026-09-27/README.md).
Live implementation/qualification state belongs exclusively to [CONTEXT.md](../CONTEXT.md).
Rebuildable independent analysis is `.scratch/common_area_independent.py`; baseline receipts
are `.scratch/component_footprint/common_before_0/1/2.json`.

## Rejected component-first physical-area probe

The first prototype did target physical component area: representative sample 0 grew from .127
component area to .465, with 897 groups and unchanged MAIN. But LOCAL could realize only .050,
producing .902 component share instead of .6. Exact physical keepouts and component-cluster hulls
removed most future route opportunity. Changing numerators alone did not solve construction order.
The paired future-capacity admission above addresses that causal failure; this prototype is retained
as diagnostic evidence, not an accepted result (`.scratch/common_area/independent_0.json`; its provisional SVG was superseded).

## Final qualification and limits

The final installed design uses the fixed prepared component population as the baseline before
planning one complete ordinary LOCAL atlas. Component proposals preserve ordinary future route
capacity, and final selection emits unchanged complete dependency families. The early prototype
that reserved routes before mandatory prepared components achieved .6 share only by reducing
component area to .08; it was rejected. Ranking first-fit proposals alone also failed because that
atlas was incomplete and spent most future capacity on unavoidable prepared placements.

Final full release passes 219/219 (142.423s), zero failures/errors/skips/xfails; stress passes
1/1 (3.825s). All 21 final fixtures pass exact geometry reports with one component population.
Three exact user-seed replays retain byte-identical MAIN groups and produce:

| Sample | Old component area | New component area | New LOCAL area | New component share | New total area |
|---|---:|---:|---:|---:|---:|
| 0 | .12712 | .15911 | .10608 | .59999 | .26519 |
| 1 | .13182 | .16776 | .11184 | .60000 | .27960 |
| 2 | .13570 | .16269 | .10846 | .60000 | .27115 |

An independent emitted-SVG raster gives matching area within one bit; continuous geometric
intersection is close. Chromium review compared all three old/new exact samples and neighboring
square, fine, wide/tall and modality endpoint outputs. User visual acceptance is separate.

Literal `local_density=.9` does not achieve 90% physical occupancy in these layouts. Actual
total area is .265/.280/.271, and the report records the resulting .635/.620/.629 shortfalls.
At a representative default-share seed, density requests .1/.2/.3/.4/.9 realize
.102/.200/.260/.286/.287: the knob follows requests at low levels then saturates under legal
construction capacity. These finite outcomes establish no universal packing limit. Neither the
old region-credit ratio nor a new target/cap is presented as achieved physical area without
measuring the emitted SVG. All previous SVGs remain preserved; new same-seed review SVGs are
`pcb_v48_area_share_00/01/02_seed_...svg` on E:/Desktop.


## 2026-09-29 restriction audit and narrowed correction

Reassessment found an extra construction exclusion: LOCAL cluster territory and prospective component admission buffered actual component-cluster convex hulls by 0.55 LOCAL grid cell. The active design protects cluster interiors and independently requires exact component-to-pathway clearance; it does not prescribe this additional exterior halo. The correction uses the same bare actual hull in both phases. It preserves component area accounting, exact physical moats, marker reservation, MAIN, packet grammar and spatially fair selection. The preceding source is preserved in `archive/releases/v48_component_territory_overbuffered_2026-09-29`.

An equal-setting ordinary reflow on a saved dense component bank isolated the effect: C=.529184 stayed fixed; L rose from .185431 to .241071. Independent bare-hull and physical checks found no violations. This diagnostic is not the production batch or proof of the requested .54/.36 construction. Evidence: `.scratch/high_c_buffered_ordinary_baseline.json` and `.scratch/bare_hull_territory_diagnostic.json`.

A separate proposed endpoint-only ordinary envelope was withdrawn after identifying final terminal backoff: an ordinary dot can move backward along its legal body, so the existing broader marker reservation remains. No weakened final gate was used to accept shifted dots.

Earlier investigation also imposed unsupported realized special-trace quotas. Section 27.1 and the special-type rule govern seeded attempt probabilities; geometry determines realizations, and realized percentages are report data. Earlier per-room special-quota MILP infeasibility is not a governing failure. Physical area deficits remain real. A q=0/D=.9 control retaining all seeded probabilities and disabling only thin-first capacity planning reached L=.744563, with zero reported physical violations; this isolates most of the earlier .51-to-.79 improvement to construction order, not forced special scheduling. That control is scratch evidence only (`.scratch/seeded_ordinary_endpoint_pilot.json`).

The narrowed production candidate passed the complete 226-test release gate and maintained stress test. Current visual, scaling and density status is recorded in CONTEXT.md; these gates do not establish full density fulfillment.


Exact post-correction samples independently recount total occupancy .367631/.394743/.348358; the third regresses. MAIN/chip serialized geometry is identical in all three before/after pairs. All three retain large blank areas on visual inspection; no density qualification is claimed. Serial .75->.5 field growth is 2.101x; CPU growth is 2.161x before and 1.440x after, with unchanged candidate attempt counts. Candidate .75 runtime worsens, so this is not a blanket performance improvement. Reproducible receipts and rendered previews are under `.scratch/territory_qualification/`.

A bounded fresh-subgroup layout pilot in the same MAIN-fragmented R=3734 room, with a fixed L=.36208 route scaffold, admitted nine 2-3-family row/column/grid assemblies and reached C=.32325 (previous fixed-bank C=.3131), total=.68532. It tested 9,216 positions, found 1,251 exact-valid nominations, and final physical/marker/singleton-hull audits were clear. This does not close the C=.54 deficit; singleton cluster IDs are not seeded cluster-progression qualification. Component layout adaptation around already frozen routes remains insufficient. Repro: `.scratch/coupled_irregular/adaptive_assembly.py` and `_audit.py` with adjacent JSON receipts.


All-LOCAL early-targeting diagnosis found 83.67% of unpaid canonical samples in previously touched coarse cells. A scratch constructor retiring a target only once its allowed samples are covered, and aiming at connected unpaid subcell patches, improves L=.744563 to .751256 with unchanged work caps; it emits1,824 rather than1,873 traces. Seeded ordinary routes gain1,344 union bits and their median length rises5.78->6.00 modules, but1,164 short deterministic-debt traces still dominate. This mechanism alone is insufficient and was not integrated. Independent saved-geometry comparison is `.scratch/area_target_geometry_comparison.json`; rendered preview `.scratch/area_target_pilot.png` shows dense repeated short bent packets and does not establish user visual acceptance. The live source remains the narrow bare-hull correction only.


An isolated ordinary-population audit found cumulative births including abandoned nonemitted fronts charged against the live1024 ceiling. Correcting only that ledger within unchanged work budgets admitted246 additional ordinary sources in the existing partial wave and increased ordinary union service by3,613 bits. It nevertheless reduced final coverage by176 bits, shortened seeded routes, and introduced one final termination-marker overlap. The scratch candidate is invalid and was not integrated (`.scratch/live_local_population_pilot.json`, `_geometry.json`). More ordinary births into fragmented late space are not sufficient; a numeric ledger correction must not be promoted as the density fix.


Current-source component-only D=.9/q=1, scale.75/chip.75/run2/sample0 reaches C=.490187. A bounded shadow check proves scalar maximum-span/nearest-clearance fitting rejects some native generated candidates that pass unchanged exact geometry at the same center (9/161 sampled rejects). A scratch native-shape-first correction admits108 such native compounds but reaches only C=.508937, with420 rather than429 groups and zero reported geometry/grammar violations. It roughly doubles preliminary phase cost and remains far below .9; not integrated. Repros `.scratch/q1_scalar_span_shadow.py/.json` and `.scratch/q1_native_span_candidate.py/.json/.pkl` include exact controls and candidate provenance.

The single full-cluster transfer/re-rooting prototype also remains uncommitted. Existing rollback reopened two initial entry ports, but the complete candidate could not preserve all five exterior tails and a retained branch family under its bounded closure. Three independent visible packages changed retained terminal/tail geometry; the actual materializer still encountered an unrepaired source. This is a failed local constructor, not a proof of geometric impossibility. Executable and explicit checks are `.scratch/joint_room_alternatives_transfer_reroot.py/.json/.pkl`; original scaffold is preserved.


## 2026-09-29 user clarification: protected interior is component area

The user explicitly authorized counting designed protected space inside existing component clusters and explicitly prohibited bringing back big clusters. The revised measure unions individual enclosure-and-spacing masks with the actual bare protected hulls of those existing clusters on the same canonical field. It adds no exterior hull halo, merges no IDs and does not change component/LOCAL physical clearance. Component-owned samples are excluded from LOCAL. Existing cluster-size, member-count, placement and distribution rules remain governing; output cluster extents and visual distribution require verification.

Independent remeasurement of the unchanged exact sample0 SVG adds14,183 component bits: individual-only C=.220576 becomes C=.314467, L=.146982, total=.461449. This demonstrates previously uncredited protected area without changing a single primitive. It is an accounting diagnostic, not a regenerated requested-share result or proof of .9 occupancy. Repro `.scratch/cluster_area_independent.py`, `.scratch/cluster_area_before05_independent.json`.

Implemented metric v3 uses the same hull union for prospective admission, incremental placement accounting, final reporting and LOCAL exclusion. Exact regenerated samples independently total .430090/.468673/.394827 at the requested .6 component share (raster tolerance), with unchanged MAIN/chip SVG geometry and zero reported hard geometry violations. Full release228/228 and maintained stress1/1 pass. Cluster counts85/86/71 become74/81/58; maximum members12/10/10 become9/9/9; median spans192.1/197.1/210.4U become175.2/189.5/189.7U. Maximum spans rise slightly to460.6/452.0/432.7U without rule changes. Rendered review finds no renewed macroscopic component colonies or top-only tiny-line piles; blank regions and density failure remain. Evidence `.scratch/territory_qualification/cluster*`, `.scratch/cluster_area_after*_independent.json` and `_visual.json`.

The corrected metric exposes the frozen-atlas ceiling independently of accounting: scale.75 initial LOCAL atlas pays only .275020 against .36 requested, before residual components. Commit can only remove whole route families;45 of132 retire and all87 surviving families are selected at L=.181561. Initial balanced total is therefore bounded above by .275020/.4=.687550 for that finite atlas, before further losses. This is a limitation of the current constructor, not proof of geometric impossibility or permission to weaken any parameter. A resumable joint component/ordinary-family transaction is a proposed correction to that commit boundary, not yet implemented or validated.
