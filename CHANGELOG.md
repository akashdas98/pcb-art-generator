# Changelog

## 2026-09-30 - complete restoration of referenced clean renderer

- At the user's explicit request, restore `pcb_v48_renderer.py` and its design language exactly from `E:/Downloads/pcb-art-generator_V48_CLEAN_2026-09-04_0719IST/pcb_v48_repo`. Renderer SHA-256: `7FA8219870E537DC45F3238A83D43779F4D8F5032717BDDB1447B99AF96E8FCB`.
- This restores the original seeded legacy-total density scaling and all original component/LOCAL construction, superseding later clustering, scoring and physical-area changes. Production entry point and requirements already match the reference.
- Preserve the preceding renderer, specification, documentation and superseded renderer tests in `archive/releases/v48_before_complete_reference_restore_2026-09-30`. Retain current project governance and unrelated work. Qualification results are recorded in `CONTEXT.md`.

## 2026-09-30 - restore region-service density with dispersed components

- Restore the connected-region size/quantity component score as the density control after the user confirmed the archived composition looks filled. Keep `local_density` literal and split its service score by `component_density`; do not restore the archive's seeded 0.91-style total multiplier.
- Freeze components after their regional score reaches its share, then run one LOCAL campaign in their actual remaining space and select whole routed families toward the LOCAL share. Preserve existing dispersed-cluster scheduling, cluster caps, component grammar, MAIN, physical clearances, and indexed work bounds.
- Label service scores separately from physical area. SVG reports retain independent component enclosure/cluster-interior area and LOCAL line-and-gap area; a 65% service share is not claimed as 65% physical component area.
- Preserve the preceding unqualified physical-density renderer in `archive/releases/v48_physical_density_before_region_score_2026-09-30`. Qualification and visual findings are recorded in `CONTEXT.md`.
- Exact three-seed `.5/.75/2/.9/.65` batch scores about `.901` total with `.650` component service share, while independently measured physical component area is only `.194-.203`; reports keep these meanings separate. Component clusters stay within 12 members, and review found no macroscopic colony. Neighboring `.75` density and `.25` component-share renders respond in the intended direction. Final release 234/234 and maintained stress 1/1 pass; `.75->.5` elapsed time grows 2.67x for 2.25x territory on the measured seed.

## 2026-09-29 - actual LOCAL interline gaps and independent allocation targets

- User authorized counting actual designed space between nearby LOCAL lines while leaving isolated empty areas unfilled. Metric v5 retains base half-gap ribbons and adds bounded gaps supported by at least two emitted traces, using the existing independent-source spacing as the locality bound.
- Track gap support incrementally when provisional route families are retired or selected; final emitted recount uses the same metric. Preserve physical clearance and component accounting.
- Remove the achieved-component-ratio cap from LOCAL targets: component shortfall no longer reduces the requested `D * (1-q)` allocation.
- Preserve the predecessor in `archive/releases/v48_before_actual_local_gaps_2026-09-29`. Full release and stress checks pass; independent SVG recount agrees exactly on the measured samples. The exact requested seed reaches only .435894 total occupancy against .9: this accounting correction is not a completed density-construction fix. Visual acceptance and full density attainment remain open in `CONTEXT.md`.

## 2026-09-29 - test restored half-gap LOCAL area credit

- At the user's request, restore the archived pre-doubling LOCAL service width: half the visible stroke plus the larger of half the required line-line gap and half the component-pathway gap on each side. Keep exact physical clearances and component-cluster interior credit unchanged.
- Preserve the preceding qualified renderer in `archive/releases/v48_before_local_gap_revert_2026-09-29`. Area-measure version advances to 4 because the same SVG receives a different LOCAL numerator.
- The purpose is a same-seed visual-share experiment. Full density fulfillment remains open; qualification and regenerated results are tracked in `CONTEXT.md`.
- Focused area tests10/10, full release228/228 and maintained stress1/1 pass. Five exact same-seed SVGs are in `E:/Desktop/pcb_v48_half_gap_same_seeds_2026-09-29`; independent recount agrees with reports and MAIN/chip SVG groups match originals. The renderer places fewer components and more LOCAL traces yet still reports~.65 achieved share; total occupied area drops from .475-.501 to .340-.388, further below requested .75. User visual acceptance remains open.

## 2026-09-29 - protected cluster interiors count toward component area

- User authorized counting the designed empty interior protected within existing component clusters as component area, alongside individual enclosures and spacing. Union on the canonical post-MAIN field once and exclude component-owned samples from LOCAL credit.
- Preserve current cluster formation, membership/extent limits and spatial distribution; no return of big clusters, no ID merging, no exterior hull buffer.
- Preserve the predecessor in `archive/releases/v48_individual_component_area_2026-09-29`. Implementation and qualification are tracked in `CONTEXT.md`; the full density-construction task is not declared complete by this accounting correction.
- Metric v3 passes 228/228 release tests and maintained geometry stress. Independent exact-seed SVG recounts agree within serialization/raster boundary error. Cluster member caps and distribution remain intact; the three samples have at most nine members per cluster, with smaller median spans. Actual total occupancy remains .4301/.4687/.3948 against .9, so the density failure remains open. CPU scaling and the fixed-atlas construction ceiling are recorded in current state; no runtime improvement is claimed.

## 2026-09-29 - actual component-cluster interiors

- Correct an extra .55-cell exterior buffer around component-cluster hulls. Protect actual cluster interiors while retaining exact rendered component-to-LOCAL clearance.
- Preserve ordinary endpoint reservation along the legal body: terminal backoff can move its dot before materialization.
- Preserve the preceding source in `archive/releases/v48_component_territory_overbuffered_2026-09-29`. This narrow correction passes full release/stress and exact-seed geometry checks. Complete hard-density fulfillment remains open in `CONTEXT.md`.
- Correct investigation acceptance criteria: special-trace percentages are seeded soft attempt probabilities, not required realized-output quotas. Component and LOCAL absolute area targets remain unchanged.

## 2026-09-28 - doubled LOCAL gap credit

- Per user direction, double the previously credited spacing around LOCAL lines for canonical occupied-area accounting. The LOCAL service ribbon now uses the full line-line or component-pathway clearance on each side, whichever is larger, plus half the visible stroke. Union overlapping ribbons and exclude component-owned samples as before. Report area-measure version 2 for this changed metric.
- Keep component enclosure accounting, visible geometry, physical clearances, and MAIN unchanged. The change applies uniformly across density controls; it is not a `.9/.6` exception.
- Preserve the preceding renderer in `archive/releases/v48_before_double_local_gap_2026-09-28`. Qualification and measured density effects are tracked in `CONTEXT.md`.
- Exact `.5/.75/2/.9/.6` sample totals rose to .366/.389/.372, still below the requested .9. This is an accounting change, not completion of the open density-construction correction.

## 2026-09-27 - common-area soft-density behavior rejected

- User rejected the preceding area-share release: requested total post-MAIN occupancy .9 and component share .6 yielded only .265-.280 total occupancy on three exact samples. A correct ratio with large blank regions does not satisfy either control's joint contract.
- Root cause in that version is a fixed, incomplete ordinary LOCAL atlas that only loses route families as components are admitted; its initial .149 LOCAL area on sample 0 bounds exact-.6 total area to .372 even before conflict retirement. Endpoint outputs do not establish a physical capacity bound.
- Preserved the exact rejected renderer in archive/releases/v48_area_share_soft_density_rejected_2026-09-27. Corrective implementation and qualification are active in CONTEXT.md; this entry does not claim a replacement is finished.

- Subsequent root-cause work found special singleton LOCAL proposal/logical checks reserving an ordinary endpoint dot that the round-cap/negative-hole renderer never draws. The in-progress correction unifies physical endpoint envelopes; ordinary/MAIN marker laws remain unchanged. It is not a completed density overhaul and remains unqualified in CONTEXT.md.

## 2026-09-27 - common component/LOCAL occupied-area allocation

- Replace sparse component region-credit versus LOCAL-ribbon ratios with a common post-MAIN area raster; component enclosures, interiors and surrounding spacing count.
- Build one complete ordinary LOCAL certificate pool after required prepared components, then admit additional components only while sufficient route capacity survives. Select complete route families toward the requested split and report physical-density shortfall.
- Apply area semantics to all parameter settings, including exact defaults; retain MAIN and geometry safeguards. Preceding source preserved in archive/releases/v48_debt_fair_selection_2026-09-27.
- Implementation and qualification status are recorded in CONTEXT.md.

## 2026-09-27 - top-heavy LOCAL debt construction correction

- Provenance on the newly rejected batch showed every deterministic minimum debt path in the top quarter; ordinary paths remained balanced. The global-floor sweep sorted equal debt by y then x.
- Decoupled coherent finite geometric capacity planning from seeded round-robin selection of the required visible packets across existing local chunks; retire all unused provisional ownership before emission.
- Added bounded indexed continuation of completed reserve packets, preserving every original visible-service bit and every exact physical/clearance gate; failed or budget-ineligible continuation retains the proven packet.
- Continuation accounting uses emitted ribbons, not logical segment ledger changes. Density controls and the ordinary router remain governing.
- Preserved the preceding technically qualified but visually rejected source in archive/releases/v48_scheduler_boundary_2026-09-27. Verification and visual status are recorded in CONTEXT.md.

## 2026-09-27 - residual scheduling boundary correction

- Diagnosed exclusive component cores/tiles and eroded LOCAL owner domains as artificial modality barriers.
- Made component parcels distribute local cluster load without clipping canonical glyphs; gave compact LOCAL source groups overlapping bounded routing envelopes.
- Preserved exact component/hull protection, MAIN, seed ownership, density floors, final visible-service accounting and packet grammar.
- Archived the visually rejected preceding renderer; added regressions for cross-seam glyph capacity and complete LOCAL opportunity with bounded overlap.
- Qualification and visual status are recorded in CONTEXT.md; reproducible comparison evidence is in docs/RESIDUAL_CLUSTER_DISTRIBUTION.md.

## 2026-09-27 - persistent Codex project-state architecture

- Retired ZIP/export delivery, missed-handoff recovery, repository identity and recursive worktree/copy guards, and NORMAL/NIGHTLY stopping modes by explicit user instruction.
- Centralized live state, queued tasks and user decisions in CONTEXT.md, checkpointed after meaningful changes; added focused session-start context routing and one process source.
- Allowed scoped Git worktrees, ordinary reviewed changes and ignored local scratch while preserving previous renderer versions and source-oriented archive/history.
- Preserved former process/state in archive/project_state/2026-09-27 and moved inactive experiments intact to archive/inflight; removed duplicated live inflight status.
- Replaced workflow prose locks with route/state architecture checks; current suite counts come from runners/manifest. Renderer and behavior specification unchanged. Verification result is recorded in CONTEXT.md.

## 2026-09-27 - residual clustering visual outcome rejected

User reports the installed last fix made components and tiny LOCAL lines MORE clustered/compartmentalised. Visual completion was withdrawn despite prior technical qualification. Corrective work is deferred in CONTEXT.md until the user returns to it; no renderer rollback or new diagnosis was implemented.

## 2026-09-27 ? shared residual cluster distribution ? PROMOTED

- Coordinate component and LOCAL opportunity through shared physical composition parcels; preserve distinct seeded cluster sizes and allow larger physically bounded LOCAL groups.
- Separate component center cores from complete canonical glyph footprints, removing the fine-scale seven-population cost.
- Measure LOCAL service from final visible strokes on the unchanged canonical denominator; construct indexed early capacity only for higher requested LOCAL allocations and preserve ordinary default language.
- Correct minimum-length roundoff, certified filled-terminal settlement and polygon-versus-exact logical circle admission.
- Retain hard default/reduced-density floors; full-density all-LOCAL best-effort 80% reaches80 in all five qualified fixtures. MAIN remains unchanged on paired comparisons.
- Candidate 204/204 and complete affected fixtures pass. Native release 204/204 and stress 1/1 pass with exit code zero, zero failures/errors/skips/xfails. Source SHA-256 `244661c4f9560322ba90cfb5dd93c3ced2ebc42c37b28e5668fa86777758ba85`; evidence and performance limits in docs/RESIDUAL_CLUSTER_DISTRIBUTION.md.

## 2026-09-04 07:xx IST — residual density knobs — PROMOTED

User requested two controls on the uploaded pre-second-cluster-fix renderer:

- `local_density` in `[0,1]`: scales the total post-MAIN residual-fill budget. `1.0` means the historical residual-fill amount; `0.0` leaves post-MAIN gaps unfilled by both residual components and LOCAL lines.
- `component_density` in `[0,1]`: splits that residual-fill budget between components and LOCAL lines. `0.0` requests all LOCAL, `1.0` requests all components.

The current nominal default component share is **0.5898123324 (~0.59)**. It is derived from the historical midpoint convention: components target 55% of residual capacity, LOCAL targets 85% of the remainder, so `0.55 / (0.55 + 0.85*0.45) = 0.5898123324`. Exact default settings preserve the historical per-seed 50–60% component and 80–90% LOCAL draws through a legacy fast path rather than replacing those stochastic targets with fixed midpoint numbers.

Current implementation status:

- API/CLI wiring for both knobs is in place.
- Exact default geometry has been compared against the uploaded original renderer and is **byte-for-byte identical after stripping only the new report metadata**.
- `local_density=0` is a literal endpoint: no residual components and no LOCAL lines are emitted; MAIN is untouched.
- Non-default density requests use a shared post-MAIN residual-service budget; `local_density` scales the total requested budget and `component_density` divides it between the two residual modalities.
- Extreme all-LOCAL/all-component requests are best-effort density requests constrained by existing geometry/clearance grammar; they do not create new 90%+ hard construction invariants. Reports expose requested and realized combined residual density and realized component share.
- Targeted knob-contract tests pass.
- Full canonical release gate completed **193/193 PASS**, zero failures/errors/skips/xfails.
- Maintained geometry stress gate completed **1/1 PASS**.
- Exact-seed endpoint smokes at `1:1 @ 1.0`, seed `101`, confirm the requested semantics: `local_density=0` emits zero residual components and zero LOCAL traces; `component_density=0` emits zero components and LOCAL-only residual service; `component_density=1` emits components only and zero LOCAL traces. A `local_density=0.5` mixed smoke realized total residual service `0.4751` against target `0.4705`.
- Endpoint requests remain geometry-constrained best-effort density targets rather than new hard coverage floors: the all-LOCAL smoke realized `0.8008` of the `0.9410` requested total without weakening clearance or LOCAL routing grammar.

This change is **promoted**. Exact defaults preserve historical per-seed geometry, while non-default settings expose the new shared residual-fill controls without changing MAIN architecture, route grammar, or clearance rules. **Authoritative renderer SHA-256:** `7fa8219870e537dc45f3238a83d43779f4d8f5032717bddb1447b99af96e8fcb`.

## 2026-08-28 19:35 IST — repository-administration workflow separated from DEVELOPMENT

- Added a third top-level task mode: **REPOSITORY ADMINISTRATION**, distinct from both PRODUCTION USE and DEVELOPMENT.
- Pure repository/version-control administration on an already-existing state—status/diff/history, stage/commit/amend, tags/branches/remotes, fetch/pull/rebase/merge, push/sync—no longer routes through DEVELOPMENT merely because it writes Git metadata.
- In pure REPOSITORY ADMINISTRATION mode, agents explicitly **must not run `tools/assert_single_canonical_repo.py`**, release/stress tests, benchmarks, qualification suites, handoff builders, or DEVELOPMENT missed-handoff recovery just because commit/push/repository housekeeping was requested.
- Mixed requests remain safe: “fix/change X, then commit/push” is DEVELOPMENT while content changes are made/qualified; commit/push is only the administrative tail. Creating an additional worktree is not treated as ordinary exempt administration and remains constrained by the single-canonical-state policy.
- Added `docs/REPOSITORY_ADMINISTRATION.md`, updated `AGENTS.md`, `docs/WORKFLOW.md`, and `README.md`, and added a permanent routing regression. Renderer geometry/export source is unchanged: renderer SHA-256 remains `e06fb338cae6a81ef1249336608ee0dacefafb96e4e5ace4380bb2e01bc3ebd3`.
- Qualification: **191/191 active release tests PASS** with zero failures/errors/skips/xfails. Maintained geometry stress: **1/1 PASS**. Renderer source remains unchanged.

## 2026-08-28 23:40 IST — semantic SVG geometry classification export promoted

- Implemented a **machine-semantic SVG export layer** on the final renderer output. The exported SVG now carries root-level schema/version attributes plus a `semantic_svg` metadata payload alongside the existing report payload, so downstream tools can inspect geometry classes without re-deriving the full scene from raw shapes alone.
- Final SVG groups are now classified at entity level: `main-chip`, `main-pathway`, `local-pathway`, and `component-group`. Pathway groups preserve source-chip / launch-side semantics, and component groups preserve family / cluster semantics when present.
- Final SVG primitives are now classified with stable IDs and `class` / `data-*` attributes. Main-chip traces export as `main-trace`; LOCAL traces export as `local-trace`; pathway circles export as trace markers with inferred roles such as `source-marker`, `terminal-marker`, `endpoint-marker`, or `junction-marker`; component primitives export as `component-geometry`.
- Trace primitives now expose directly usable endpoint/state metadata in the SVG DOM itself (`data-start-*`, `data-end-*`, `data-point-count`, `data-stroke-width`, parent entity id, marker role, etc.). This is intended specifically to support downstream effects/behavior passes such as animated glow particles traveling along main traces and optionally coupling into nearby components or LOCAL traces.
- Added a focused semantic-export contract doc: `docs/SEMANTIC_SVG_EXPORT.md`.
- Qualification: **190/190 active tests PASS** (run in deterministic batches to avoid tool execution-window cutoffs) + maintained geometry stress **1/1 PASS** + direct semantic SVG smoke render/inspection PASS. Promoted renderer SHA-256: `e06fb338cae6a81ef1249336608ee0dacefafb96e4e5ace4380bb2e01bc3ebd3`. Active test manifest SHA-256: `a0182681abee07517cbf66ca477f772fc4abae5203a114128d056dab7a9f6555`.

## 2026-08-27 21:28 IST — residual-fill spatial mosaic + opportunistic cross-chip semantics promoted

- Closed three user production failures at `1:1 @ 0.35`, chip density `0.25`, run multipliers `0.25/0.5/1.0`. All were the same obsolete validator contract: `cross-chip connection invariant not realized`. Production now requires no board-level cross-chip quota; an already-legal foreign-chip encounter still wins immediately regardless of remaining journey target.
- Replaced residual territorial segregation with a shared composition mosaic. Components remain physically admitted before LOCAL for collision ownership, but both languages are distributed across the same board-scale residual field.
- Component and LOCAL ordinary cluster cardinality now has full seeded `1..12` support. Completion components form bounded seeded clusters rather than hundreds of nominal singleton spill clusters. A fixed 8x8 normalized-load mosaic disperses component-cluster anchors so individually bounded clusters cannot visually re-coalesce into a macroscopic colony.
- LOCAL large connected rooms are serviced as compact `1..12` source parcels. Component constructors, exact clearance, component 50--60% fill target, LOCAL 80--90% remaining-service target, LOCAL route grammar/recovery, and MAIN architecture remain unchanged.
- Exact sparse/fine production screens at density `0.25`, `1:1 @ 0.35`, run multipliers `0.25/0.5/1.0` all PASS with zero stalled sides, MAIN short terminations, or unaccounted launches; zero cross-chip joins is correctly accepted on the two shorter-run boards. Sparse `1:6` and `6:1 @ 0.75` screens also PASS with zero hard MAIN defects and component clusters reaching the intended 12-member upper bound.
- Final seeds-102+104 `0.75 -> 0.5` normalized screen: residual composite CPU/work **1.000x**, whole-renderer composite CPU/work **1.003x**; previous authority whole-renderer composite was **1.140x**. The visual correction does not introduce worse normalized scaling.
- Final qualification: **188/188 release tests PASS + stress 1/1 PASS**. Promoted renderer SHA-256: `b965a294b339684ccea1e95aae848c79d9cb232295a5666effd83dc844a7ca53`.

## 2026-08-27 18:03 IST — MAIN run-length workload knob + inter-chip success semantics promoted

- Added `--main-run-length-multiplier` in the hard range **0.2..3.0**, default **1.0**. It scales the existing stochastic whole-route MAIN residency pool only: `0.5` restores historical residency, `1.0` is **2x historical**, and `3.0` is **6x historical**. Per-gesture segment grammar, turn rules, clearance, proposal breadth, spatial search, reroute architecture, and LOCAL route life are unchanged.
- Valid foreign-main-chip head connections now win immediately when geometrically legal. The journey target governs only voluntary free termination; reaching it sets termination pending until the existing connection arbitration has first refusal. No new connection search radius/global pass was introduced.
- High multipliers extend only the existing shared MAIN clock capacity enough to make the requested residency physically reachable; historical RNG draw order and ordinary clock values are preserved when already sufficient.
- Governing 0.75->0.5 normalized screen, seeds 102+104: BEFORE authority composite work 60,429->134,330 = 2.223x, CPU 7.492->15.976 s = 2.133x, CPU/work 0.959x; AFTER default work 59,724->136,088 = 2.279x, CPU 7.283->16.822 s = 2.310x, CPU/work **1.014x**; maximum multiplier 3.0 work 81,588->173,263 = 2.124x, CPU 9.333->20.724 s = 2.221x, CPU/work **1.046x**. The favorable BEFORE sublinear point remains recorded; the renderer diff does not alter the underlying lookahead/local-space/clearance/search algorithms.
- Final qualification: **183/183 release tests PASS + stress 1/1 PASS**; lower/default/upper production smokes pass with zero stalled/short/unaccounted MAIN traces; two-chip default smoke records 7 cross-chip joins / 14 connected traces.
- Promoted renderer SHA-256: `5d8624de9d2b5ec5b5ba7dac7fed169653074d7301751f8b1b1558e870dba98b`.

## 2026-08-27 16:44 IST — main-chip density workload knob promoted

- Added `--main-chip-density-multiplier` in the hard range **0.2..2.0**, default **1.0**. Default density is approximately half the historical source population; `2.0` restores the historical two-opportunity-per-territory law exactly.
- Density selection uses a private deterministic substream, preserving downstream population RNG. A hard one-main-chip physical floor prevents low-density small boards from exporting a zero-source topology into unrelated phases.
- This is a workload/geometry parameterization only. No MAIN routing, placement, collision, persistence, or search algorithm was changed. Multiplier `2.0` produces bit-identical checked MAIN geometry and identical routing-work counters to the preceding authority.
- Governing 0.75->0.5 default-density screen (seeds 102+104): work 47,510->106,742 = 2.247x; MAIN CPU 10.093->22.823 s = 2.261x; CPU/work growth 1.006x. The historical 0.874x comparison point is not attributed to chip-count quantization after checking the exact counts; same-geometry compatibility controls are the authority for algorithmic-efficiency preservation.
- Final qualification: **180/180 release tests PASS + stress 1/1 PASS**, plus real `1:1 @ 1.0`, multiplier `0.2` production smoke with one chip and clean MAIN hard counters.
- Promoted renderer SHA-256: `586d8b54c8044129bea97088c542654b85a79465b37f1ff5ba8efbef96591c98`.

## 2026-08-27 14:44 IST — MAIN topology-birth / rollback-floor persistence-totality repair promoted

- Reopened correctness after 3/5 user production runs from the 12:33 authority threw `MAIN persistence horizon unresolved` on three distinct sample seeds. All three are treated as construction defects under seed totality, not as rejectable seeds.
- Closed two topology-birth holes: recovery fragmentation can no longer export unresolved <4-module survival debt into singleton siblings, and an ordinary young MAIN branch must transactionally commit/prove every child's structural maneuver through the unchanged four-module survival floor before replacing the parent topology.
- Exact run-5 diagnosis found a later recovery hole: a fan child could be born valid above four modules but retain `recovery_floor_segments=0`, allowing ordinary traceback to erase its own survival maneuver and recreate a ~1-module `branch_stage=0` child. The transactional structural maneuver is now the child's rollback floor.
- The ordinary MAIN minimum remains **4 modules**, not four straight modules. The separate >=8-module side-progress certificate remains one outcome per launch side. No clearance relaxation, safe-seed selection, whole-board restart, or validator acceptance filter was added.
- Persistence errors now include sample seed + aspect ratio + scale; the three supplied raw logs predate this, so their `1:6 @ 0.35` replay geometry is explicitly recorded as inferred rather than logged fact.
- Qualification on one byte-identical final source: **178/178 release tests PASS + stress 1/1 PASS**. All three exact user-failing sample seeds PASS under the inferred long/fine MAIN-only reproduction: `1638463186752876422` => 4,109/4,109 visible; `13995978127231202083` => 4,091/4,091; `3524258640260304746` => 4,084/4,084; all with zero unresolved persistence, stalled sides, short terminations, or unaccounted launches.
- Promoted renderer SHA-256: `9541c2f62cf9afccf3388eac6b929d7dd9437c19d04acb600855e61175bd1b42`. No active renderer candidate remains.

## 2026-08-27 12:33 IST — MAIN emerge→spread / connection / live side-progress refinement promoted

- Reopened correctness from user production error `main-network preflight materialization invariant violated`: stalled root `[88,3,left]`, front 355, traces 3717–3725, with 4107/4107 launch traces otherwise visible and clean geometry.
- Fixed the structural cause of the visual whole-bus bend: fan readiness no longer waits for four modules of unsplit root ownership. After the real perpendicular emergence gesture, a transactional child fan may commit if every child maneuver proves the unchanged four-module per-line survival floor.
- Removed the synthetic ordinary-MAIN +/-45 turn reward that fired after two straight gestures. MAIN bends now come from seeded variance, target/connection geometry, open-space capacity, or obstacles rather than a fixed cadence.
- Replaced fixed-first fan topology with seeded, space-scored viable alternatives; corrected false fan rejection by validating actual rendered lanes instead of overlapping coarse cohort envelopes; changed 9–24 line launch partitioning to several balanced cohorts.
- Promoted side-level >=8-module visible progression into live construction debt for the last unsatisfied outcome rather than relying on late materialization repair/special fragment paths. The ordinary line minimum remains four modules.
- Distinct launch sides of one chip are now legitimate MAIN connection families after source egress; same-side siblings remain non-connectable. Final head-to-head arbitration uses the same family rule.
- Maintained stress base seed `2026080602` / sample seed `1909786089031391816` exposed one stale fan-rebase sibling exemption. It now applies only when the candidate itself continues straight; a first turn can never inherit the parallel-rebase exemption and cross a sibling corridor. Permanent regression physically reproduces that crossing.
- Qualification: **175/175 release tests PASS + stress 1/1 PASS**. Three fresh `1:1 @ 1.0` samples from base seed `20260827` emitted with zero stalled sides/MAIN short terminations/unaccounted launches and showed multiple viable fan alternatives (44/37/31) plus 8/11/10 MAIN connections.
- Small same-request runtime screen: previous 10:55 renderer 20.54 s vs this renderer 20.23 s for three square samples; no material slowdown is visible in this screen, but this is not a broad performance qualification.
- Promoted renderer SHA-256: `4c87378867645aa90727b77ea94e98eb59c6a6f4f993a45cbbf786b5239afc8e`. No active renderer candidate remains.

## 2026-08-27 10:54 IST — wide MAIN fragment side-progress totality repair promoted

- Closed the exact production correctness recurrence on base seed `8528317405406420078` / sample seed `9409060408987575905`, `1:6 @ 0.35`. Fresh from-scratch generation now emits the complete SVG/report in `934.710 s` with no reseed or whole-board restart.
- Root cause: 13-lane recovery fragments bypassed the existing <=4-lane bounded future proof, allowing all newborn singleton siblings to crowd/terminalize near the four-module maturity floor before any lane established the separate eight-module side-progress audit. The late prefix-regrow path could not reliably repair this because the common visible prefix remained ancestor-owned.
- Wide MAIN fragmentation below eight modules now transactionally proves/commits one bounded ordinary-clearance side-progress leader before topology mutation. The certificate is trace-id based so it survives later ownership changes; terminal/source marker clipping preserves that trace at >=8 visible modules.
- The hard ordinary MAIN maturity floor remains **4 modules**. No four-module straight lock was restored, no clearance was relaxed, and no validator/seed acceptance loop was added.
- Exact completed report: `4,131/4,131` launches visible; `pathway_main_stalled_side_count=0`; `pathway_main_unaccounted_launch_trace_count=0`; `pathway_main_short_termination_trace_count=0`; `pathway_persistence_horizon_unresolved_trace_count=0`; zero illegal turn/intersection/overlap/clearance failures.
- Recreated two permanent regressions for wide-fragment leader birth and >=8-module rendered leader preservation. Qualification: **168/168 release tests PASS + stress 1/1 PASS**.
- Promoted renderer SHA-256: `03e25cbf3ac46f86dced3822cbfa29e526b576499adacb0cf30684e329cf297d`. Long/fine runtime remains an optimization issue; this correctness pass does not claim the 0.35 long-strip workload is fast.

## 2026-08-26 16:30 IST — MAIN launch survival decoupled from four-module straight lock

- Narrow anti-line-murder correction: the hard **four-module MAIN survival floor remains unchanged**, but it is now cumulative materialized route length rather than a requirement that the first four modules be collinear.
- Root gesture zero still emerges perpendicular to the chip. After that first gesture, a root still below four modules may use the ordinary legal straight / +/-45-degree direction grammar; no new turn preference or local-space heuristic was added in this change.
- Root launch creation no longer sets `forced_straight_modules=4`, and source-egress mode no longer overrides segment lengths to consume the entire remaining four-module floor as one straight gesture.
- Structural splitting and bundle fragmentation remain forbidden until source-egress survival clears; `<4 modules` remains hard protected persistence debt, source-egress reservations remain active, and final source-egress totality/reconstruction is unchanged.
- Active regression now explicitly proves: first gesture is perpendicular, an early +/-45 turn becomes legal while cumulative route length is still below four modules, and the launch remains physically protected below the floor.
- DEVELOPMENT qualification: **162/162 release tests PASS + stress 1/1 PASS**. Authoritative renderer SHA-256: `f3b3179921db023fa8160885275244779190836015fdd4676e9cafe690bd7f90`.

## 2026-08-26 14:20 IST — production-use entry point separated from DEVELOPMENT workflow

- Added `generate_pcb.py` as the canonical plain-use entry point: render the requested aspect/scale/count/seed and stop. It writes SVGs only by default and does not emit standalone report JSON.
- `AGENTS.md` now routes task intent **before any command**. Plain use/render/generate requests are PRODUCTION USE mode; the anti-worktree guard, release/stress suites, seed sweeps, performance qualification, handoff builder, and DEVELOPMENT workflow are explicitly forbidden unless repository work was requested.
- Omitted seeds must remain omitted; agents must not substitute maintained/reference/known-good/"safe" seeds. `V48Renderer` chooses the random base seed itself under the seed-totality contract.
- Added `docs/PRODUCTION_USE.md`; marked `docs/WORKFLOW.md` and `docs/TESTING.md` DEVELOPMENT-only; rewrote README so the first canonical action is generation rather than verification.
- Added two active regressions enforcing the production-use contract. Real smoke run through `generate_pcb.py` produced exactly one SVG, zero standalone JSON reports, and used a renderer-generated random seed.
- Renderer implementation is byte-unchanged at `d7ac1d9af0286dda86d994a638504fe8ab63521847d9050633fc4d49d0f21745`. DEVELOPMENT gate is now **160/160 + stress 1/1** after this tooling/documentation change.

## 2026-08-25 04:34 IST — long/fine performance scaling audit complete

- Audited current promoted V48 specifically against the requirement that aspect/work heft may increase total work but should not materially increase CPU per actual generated/useful work. No renderer code changed.
- Same-seed seed-0 `1:1 -> 1:6 @ 0.35`: territory is 6.00x; chips/MAIN traces/LOCAL traces/components/gesture/lookahead work are approximately 5.8–6.1x, while total CPU is 8.09x. Current square linear extrapolation predicts ~455.7 s (~7.60 min) versus 614.5 s (~10.24 min), a ~158.7 s / 2.65 min scaling tax.
- Excess-over-linear phase attribution: LOCAL +92.3 s (~58.2% of tax), MAIN +58.8 s (~37.1%), component placement +5.4 s (~3.4%). LOCAL is therefore the first target.
- Detailed seed-1 LOCAL counters expose the strongest concrete amplifier: 10,015 quarantined direct-run families generate 5,538,055 repeated quarantine-skip polls (32.97x square for only 6x territory). Partial-service candidate tokens also grow 18x because the long board uses all three rescue waves and then a 136,597-candidate deterministic debt-completion tail.
- MAIN emitted segment work grows ~6.11x while MAIN CPU grows ~8.57x on the seed-1 comparison; high-level proposal/check counts are near territory-linear, so lower-level spatial/global-round cost must be instrumented before changing routing policy.
- New durable audit: `docs/LONG_FINE_PERFORMANCE_AUDIT.md`. Recommended order: LOCAL dead-family retirement -> debt-driven hard-floor rescue -> measured MAIN infrastructure optimization -> later constant-factor/memory/component work.

## 2026-08-25 04:13 IST — 0341 long/fine raw logs classified as execution cutoff

- User-supplied `1:6 @ 0.35` raw logs from the promoted 0341 bundle contain no renderer exception: stderr is empty for count-2, seed-0, seed-1, and foreground seed-1 attempts.
- No SVG/report or JSON summary was emitted before external termination because the CLI writes each SVG/report only after the whole logical sample returns and prints its batch JSON only after the requested batch completes.
- This is consistent with the already-qualified expensive-but-finite long/fine regime (~10.5 min / ~785 MiB class on exact seed 0; ~320.5 s MAIN alone on exact seed 1), and is **not evidence that the promoted persistence-totality fix regressed**.
- Seed-totality remains promoted/closed. Long/fine runtime/RSS remains an open optimization target; CLI progress observability is a separate tooling opportunity.
- Raw logs retained at `archive/inflight/evidence/0341_user_raw_logs/`. Production renderer code is unchanged.

## 2026-08-25 01:23 IST — long/fine totality v2 seed-1 full-board PASS (UNPROMOTED)

- Production V48 remains unchanged at `ac53e1d1fae493beb55ab8dc05c0ba7d3053add19a1c6b71cb52ce926738fb79`.
- Recovered surviving v2 candidate: `archive/inflight/v48_longfine_totality_v2_renderer.py`, SHA-256 `e8d1874d652e7aa6a7af763ac20b2a97d1367082dc748f61771833be49d16054`.
- Exact `1:6 @ 0.35`, base seed 1 MAIN-only repro now PASSes: 4,104/4,104 launch traces visible, zero hard MAIN/geometry failures, ~320.49 MAIN CPU-s, ~497 MiB RSS.
- Stronger exact-seed full-board run also PASSes: SVG/report emitted with `restart_index=0`, no skipped logical index, 98 chips, 824 collections, zero unplaced components, no route restart, and clean hard MAIN/geometry counters.
- Four routes remain under the soft six-module preferred visible target; v2 intentionally retains that quality diagnostic without treating it as hard rejection because they satisfy the four-module survival floor.
- Seed 0 remains a separate performance/RSS investigation; no exception existed in the supplied seed-0 log.
- No promotion earned yet; complete release/stress plus final scaling/behavior qualification remain mandatory.

# Changelog

## 2026-08-24 23:18 IST — long/fine MAIN seed-totality defect reproduced

- User-supplied `1:6 @ 0.35` logs reproduce `RuntimeError: MAIN persistence horizon unresolved` inside `_run_rounds()` for explicit seed 1; seed 0 was manually terminated after prolonged high-RSS execution and has no exception in the supplied stderr.
- A diagnostics-only seed-1 MAIN reproduction fails after ~317.2 CPU-s / 440,592 KiB max RSS with only 5 unresolved fronts / 7 traces.
- Three mature `between_siblings` singleton lanes (13.0–20.83 modules) still have exact-clear straight/±45 continuation at the final assertion, proving the fixed persistence horizon can stop valid construction prematurely.
- Two other fronts (4 traces) are exactly 5.0 modules, have no legal continuation, and are rejected solely because the 6-module **preferred** journey is currently represented as hard persistence debt despite the documented 4-module hard maturity floor.
- General long/fine MAIN seed totality is therefore reopened. The promoted first-rebase fairness + atomic structural-settlement fix remains production authority for the mechanisms it actually fixed; renderer code is unchanged in this diagnostic checkpoint.
- Added `docs/LONG_FINE_PERSISTENCE_DIAGNOSIS.md` with raw-log hashes, exact residue classification, architecture constraints, and the next implementation gate.

## 2026-08-24 22:22 IST — proactive MAIN line-survival promoted

- Promoted the exact fairness + atomic-horizon candidate into `pcb_v48_renderer.py`; production SHA is `ac53e1d1fae493beb55ab8dc05c0ba7d3053add19a1c6b71cb52ce926738fb79`.
- Newborn structural children with a real future option may HOLD after losing their first rebase; after one prior HOLD, one-round anti-starvation fairness prevents repeated same-round starvation. Fairness resets on first-rebase commit and never relaxes geometry.
- Replaced the old sequential residual structural-persistence commit path with bounded shared-snapshot atomic settlement/HOLD, eliminating the exact late incompatible-sibling defect traced through 162/515 and 163/516.
- Corrected behavior qualification to use rendered visible route length consistently. Governing short terminated traces improve from `6/18 -> 3/11` (0.75/102), `2/11 -> 2/7` (0.75/104), `29/75 -> 18/58` (0.5/102), and `26/74 -> 18/64` (0.5/104), measured as <=8/<=14 modules.
- Governing 0.75->0.5 aggregate MAIN CPU/work improves **1.333x -> 1.204x** using emitted visible MAIN centerline modules. Promoted 0.5->0.35 final CPU/work growth is **1.030x**.
- Added two active regressions for one-HOLD anti-starvation fairness and shared-snapshot atomic residual settlement. Candidate and promoted canonical gates both pass **148/148**; maintained stress passes **1/1**.
- Historical deferred MAIN rejection repros 1.0/103, 0.75/103, and 0.75/105 now each emit one full board with `restart_index=0`, no skipped logical seed, and clean persistence/launch/geometry counters.
- Retired the obsolete line-murder experiment forest after summarizing its useful evidence in `docs/LINE_MURDER_PROMOTION_HISTORY.md`.

## 2026-08-24 16:57 IST — missed-handoff recovery + conflict-solver localization

- Production V48 remains byte-unchanged and authoritative.
- Corrected the prior response's handoff failure: additional investigation had been performed after the preserved ZIP was made, but that stale ZIP was returned instead of the latest state.
- Atomic shared-snapshot horizon removes seed-102 @0.5's 2 late preflight defects/repairs (`28.058 s` fairness MAIN -> `18.990 s` atomic MAIN in trusted fresh-process probes).
- Preserved and rejected a narrower reservation-only horizon as preferred direction; it leaves seed-104 bundled forced terminations at `29` versus fairness `26`.
- Identified multi-renderer/single-process timing contamination; fresh process per renderer is now the trusted qualification timing method.
- Localized remaining scaling regression to fairness conflict arbitration: paired seed-102+104 conflict combinations grow `3.57x` in V48 vs `6.31x` in atomic; `_solve_conflict_group` CPU grows ~`2.89x` vs ~`4.81x`. Traceback CPU is negligible.
- Preserved behavior-identical HOLD-solver instrumentation: seed-102 @0.5 runs 65 fairness HOLD solves, checks 2357 combinations, max group size 9, max 999 states in one solve.
- Next: retain successful fairness + atomic semantics, remove needless HOLD-solver combinatorial search, then rerun mandatory 0.75 -> 0.5 normalized qualification before promotion.

This is the compact current-era changelog. Complete historical source snapshots live under `archive/releases/`; older V4–V33 changelogs are consolidated in `archive/LEGACY_CHANGELOGS_V4_V33.md`.

## Unreleased — structural first-rebase anti-starvation candidate — 2026-08-24

- Traced the dominant young-line corpse mechanism to same-round conflict starvation: viable branch-stage-0 structural children can repeatedly lose their mandatory first rebase, then cycle through rollback/recovery until they become 6–14-module corpses.
- Current best unpromoted candidate lets such a viable newborn HOLD on a first-rebase conflict and grants one-round anti-starvation fairness only after it has already been held once; fairness resets immediately after the first rebase commits. At the time the exact candidate delta was preserved under `archive/inflight/`; that experiment artifact was retired after promotion. Durable findings are in `docs/LINE_MURDER_PROMOTION_HISTORY.md`.
- Behavior evidence: at 0.75, <=8-module corpses fall `13->5` (seed101), `3->2` (seed102), `2->0` (seed104); at 0.5 they fall `21->11` (seed102) and `17->9` (seed104), with corresponding reductions in <=14 corpses and mostly better completion metrics.
- Candidate is not promotable: clean paired normalized 0.75->0.5 CPU/work growth worsens about `1.373x -> 1.469x` despite lower absolute CPU at both scales. Fine-scale traceback segments rise (`2323->2797` seed102; `1865->2279` seed104) and conflict-combination work can rise.
- Rejected broad zero-future bans, two-step lookahead, short-rebase rescue, broad atomic birth, unconditional newborn priority, greedy HOLD, depth-1-only variants, post-rebase grace, fragile-only thresholds, and pairwise-conflict memoization. The completed decision ledger is now summarized in `docs/LINE_MURDER_PROMOTION_HISTORY.md`.
- Production V48 remains unchanged. The next task is behavior-preserving profile-driven removal of the fairness candidate's fine-scale traceback/arbitration cost; do not promote a worse scaling curve.

## Unreleased — resumed proactive line-murder diagnosis — 2026-08-23

- Rejected a broad young-MAIN `future_option_count == 0` prohibition: it over-constrained healthy routing, increased persistence debt/work, and is not production authority.
- Rejected generic two-step lookahead and a short-rebase-only structural recovery candidate; the latter could move a doomed child from one dead rebase to another because generic future-option counting does not fully encode the structural state machine.
- Isolated the recurring upstream corpse pattern to very young structural children/recovery rebases, commonly around ~6 modules, that can be created from a healthy parent and then committed into a structural step with no genuine maneuvering room.
- Identified branch-birth preflight as the next causal target: current V48 proves the newborn child's first rebase but not a bounded post-rebase maneuver set. The next candidate must make early split creation transactional and defer a split when any child lacks an exact-legal lane-order-preserving continuation after rebase.
- No code from these rejected/diagnostic candidates is promoted. V48 production authority remains unchanged.

## V48 — seed-total construction outside the paused MAIN line-murder family — 2026-08-23

- Promoted the reconstructed V48 renderer as the ordinary/non-line-murder seed-totality release. Production authority is `pcb_v48_renderer.py` / `V48Renderer`; V47 is archived under `archive/releases/v47/`.
- Whole-sample seed skipping/reseeding remains forbidden. Stochastic fast paths may exhaust locally, but ordinary exhaustion must fall through to deterministic constructive completion rather than declaring the requested seed unacceptable.
- Main-chip generation gains a deterministic in-language fallback; main-chip uniqueness is based on exact generated geometry rather than the former coarse motif/aspect signature; stochastic placement exhaustion falls through to deterministic legal lattice placement, including a whole-Phase-A population placement fallback before MAIN exists.
- Collection generation/planning/calibration gains deterministic grammar-preserving completion, and component residual placement walks finite residual-service candidates with exact clearance rather than allowing a random recovery budget to decide whether the board exists.
- LOCAL hard-floor recovery gains a deterministic exact-legal residual-debt sweep. The seeded component 50–60% and LOCAL 80–90% service targets remain hard construction requirements; V48 does **not** turn a missed floor into an accepted board merely to avoid rejection.
- The global pathway gesture-check budget is diagnostic/work telemetry only; finite underlying construction loops, exact validity, and causal assertions govern behavior instead of a board-wide luck ceiling.
- Added forced regressions that set old stochastic budgets to zero/tiny values and require constructive completion. The active V48 release suite contains 146 mandatory tests.
- Deterministic downstream probes at 1.0 and 0.75 found no chip/component/LOCAL seed failure after MAIN completed; one 0.75 case required seven deterministic LOCAL debt-completion traces and still reached ~80.13% service. Challenged failures that remain are exclusively the separately paused MAIN persistence/materialization/line-survival family. They remain loud and are never rerolled.
- At this 2026-08-23 checkpoint the proactive anti-line-murder task was still paused; it was subsequently promoted on 2026-08-24 as recorded at the top of this changelog.
- Final V48 qualification after release rename/polish: **146/146 active tests PASS + 1/1 maintained stress PASS + single-canonical-repository guard PASS**. Renderer SHA-256: `83c1fbc45c3b0d9c37a699b1fcf6961cf35b9737c87df523843f8fa215650614`.
- The executable anti-multi-worktree / duplicate-canonical-state gate remains byte-identical at `1034099fe44ac60c7f968ac976d468a270b5f4e63caf93b49fca12f975650b4d`; the paused line-murder V3 candidate remains byte-identical at `b033e0c0e7423cfc9be2e09f0c9399c2bdb6925140ed7a4f8bf124949dda2329`.


## Promoted — independent seed-totality repair tranche — 2026-08-23

- Promoted the clean 23:19 seed-totality renderer as production authority: SHA-256 `648a53399955fa1c521d718308ea296b6d2c1bc5fb60fd83abe1b027c7f20e7b`.
- Promotion includes removal of batch logical-seed skipping and whole-board reseeding, total local collection-family construction, defect-scaled MAIN preflight repair, and monotonic/local component hard-floor completion.
- This promotion deliberately excludes the later terminal/embedded-lane experiments. Their exact deltas were preserved during investigation and later retired after promotion; their durable conclusions are summarized in `docs/LINE_MURDER_PROMOTION_HISTORY.md`.
- The proactive anti-line-murder rule is now attached directly to the paused line-murder task: prevent doomed early paths during construction; late detection is assertion-only and may never reject the board, spin another seed, or legalize murder after exhaustion.
- Promotion qualification completed: **137/137 active release tests PASS + 1/1 maintained stress PASS**.

## Unreleased — anti-line-murder architectural clarification — 2026-08-23

- Made the governing anti-line-murder rule explicit: prevention belongs in proactive MAIN route construction, especially emergence/early-gesture proposal selection with local-space, sibling-progression, and future-maneuvering awareness.
- Local candidate proposals may be rejected/replanned before committing a doomed state; unrelated valid work must be preserved.
- Late short/embedded/dead-end detection is an assertion/regression guard only. It may not legalize a murder after exhaustion, reject the board, skip the seed, or trigger whole-sample reseeding.
- Seed totality and anti-line-murder are complementary. Systematic late trapped lanes must be traced back to the causal MAIN planning/proposal failure rather than "fixed" by a broad terminal-rescue or acceptance subsystem.
- No renderer code was promoted by this clarification; the separate line-murder V3 candidate remains paused/unpromoted.

## Unreleased — handoff recovery hardening — 2026-08-23

- Added a non-negotiable missed-handoff recovery invariant to `AGENTS.md`, `docs/WORKFLOW.md`, and `CONTEXT.md`: if a run ends without a fresh verified complete handoff bundle, the **first substantive action of the next run must be to preserve/package the exact surviving working state before any implementation, investigation, testing, optimization, renderer edit, or other project work**.
- The recovery bundle must retain coherent unpromoted/inflight work and clearly distinguish it from promoted authority while recording the latest findings, failures, diagnostics, status, and next step.
- Previous tool/execution/window inability to package is the trigger for this recovery mode, never an exception to it; the rule takes precedence over NORMAL/NIGHTLY continuation.
- Applied the rule immediately on 2026-08-23: a recovery bundle of the surviving unpromoted termination-tail working tree was built before these documentation edits.

## Unreleased — repository normalization — 2026-08-22

- Reorganized the canonical repository around source, active tests, executable guardrails, compact agent documentation, release history, and a tiny example set.
- Removed canonical copies of transient optimization debris: profiler/forensic trees, benchmark JSON streams, acceptance output directories, logs, copied renderer-variant forests, redundant dated status/handoff/manifests, and generated experiment outputs.
- Consolidated durable V47 optimization conclusions into `docs/OPTIMIZATION_HISTORY.md`.
- Preserved `tools/assert_single_canonical_repo.py` unchanged as the hard anti-multi-worktree / duplicate-canonical-state gate.
- At this checkpoint the unpromoted line-murder V3 source was preserved under `archive/inflight/`; it was later superseded and retired after the 2026-08-24 promotion.
- Moved the single V44 reference-report dependency used by active tests into `tests/fixtures/` and updated the stress probe to import the active V47 renderer instead of relying on a root-level V45 copy.
- Added V45 and V46 source-oriented snapshots to `archive/releases/` and pruned generated example payloads from archived V40–V44 snapshots.
- Replaced repository-mutating handoff metadata/checksum generation with a lean bundle builder that packages/verifies the repository without generating artifact clutter inside it.
- Production renderer bytes unchanged: `8a43f6c2421e67b66f3d83a5f40dc269074a237d63eac2f183a60bad29b3b744`.

## Unreleased — seed-totality repair — 2026-08-22

- Established the production contract `valid canvas + scale + seed -> one deterministic valid board`; final validation is an assertion, not an acceptance filter.
- Removed batch-level logical-seed skipping: `render_batch()` now renders exactly the requested logical indices and propagates a construction defect for that exact seed.
- Removed `generate_sample()`'s outer whole-board restart/reseed loop. Compatibility parameters remain inert at API level while downstream callers migrate.
- Made collection-family quota coverage constructive instead of allowing a cosmetic family-mix draw to invalidate the sample; exhaustive spot coverage over N=15..18 found no assignment failures across 20,000 seeds per N.
- Changed MAIN preflight repair from a fixed 12-transaction whole-board ceiling to a bounded per-observed-defect local budget, and included intersection/clearance/duplicate suppression causes. A real 13-defect regression repairs all 13 locally.
- Removed the arbitrary board-wide component residual filler count as a hard-floor stop. Completion is now bounded by monotonic residual-service-cell retirement, so legal remaining capacity can continue to be serviced without rejecting the seed because a global filler counter expired. A forced zero-cap regression reaches 51.2% rather than stopping near 0.2%.
- Current mandatory gate after these repairs: **137/137 PASS**; maintained geometry stress: **1/1 PASS**.
- Exact historical `1200:6248 @ 0.35`, seed `20260816`, remains unqualified on the current authority: a MAIN-only probe was still running when a 20-minute execution boundary was reached. This is recorded as an unresolved termination/performance-totality issue, not treated as a rejected seed or a success.
- Renderer SHA-256 at this checkpoint: `648a53399955fa1c521d718308ea296b6d2c1bc5fb60fd83abe1b027c7f20e7b`.

## V47 — reconstruction, persistence restoration, locality/scaling optimization — 2026-08-17 through 2026-08-22

- Restored behavior lost/regressed across the V45/V46 transition, including persistent MAIN routing semantics and long/fine population behavior.
- Reworked LOCAL service around physical residual debt, bounded candidate work, certificates, direct-run families, emergency hard-floor cleanup, and spatial locality.
- Reworked MAIN expensive services around incremental rollback, exact-lane geometry reuse, immutable spatial snapshots, proposal replay, failure certificates, and local successful-clearance proof reuse.
- Reworked component placement to gap-first/opportunity-first local service and localized ordinary post-MAIN component retries so valid MAIN routing is not discarded for normal component placement recovery.
- Added phase-lifetime cleanup/rebuildable-state release and bounded/local spatial indexing, reducing peak memory from the earlier ~900 MB class; final 1:1 @ 0.35 canary peak was about 235 MiB.
- Final qualified phase-native CPU/useful-work growth: MAIN ~1.022x (0.75->0.5) / 1.166x (0.5->0.35); LOCAL ~0.997x / ~1.107x; components ~0.949x on the final 0.5->0.35 component-native acceptance.
- Final guarded 1:1 whole-render primitive-normalized CPU/work growth improved from 1.211x to 1.195x over 0.75->0.5 and from 1.180x to 1.147x over 0.5->0.35.
- Final active release gate at optimization closure: 134/134 PASS (the current seed-totality branch has since expanded the active gate).
- Operational caveat discovered after closure: full long/fine production acceptance was not qualified; user later observed 0/8 valid samples at roughly 1:6 @ 0.35. This remains open and is tracked in `CONTEXT.md`.

## V46 — logical viewBox / aspect- and zoom-consistent territory

- Introduced logical-viewBox scaling so aspect extension and zoom share one logical-territory law rather than ad-hoc canvas-specific behavior.
- Expanded fine-scale primary population/detail capacity with normalized territory and made service grids design-unit based.
- Established rotation/aspect invariance tests and long-canvas coverage.
- A persistence/line-termination behavior regression became a major input to V47 reconstruction. See `archive/releases/v46/`.

## V45 — true zoom / logical-area population

- Converted scale from a mostly cosmetic/detail setting into logical-area exposure and population growth.
- Added fine-scale primary population behavior and long/tall canvas validation work.
- See `archive/releases/v45/`.

## V44 and earlier

Source snapshots V34–V44 are under `archive/releases/`. V4–V33 changelog records are in `archive/LEGACY_CHANGELOGS_V4_V33.md`.

### 2026-08-23 — seed-totality termination repair (INFLIGHT, not promoted)
- Replaced remaining mature MAIN persistence rejection for locally exhausted `between_siblings` singletons with local deterministic settlement after transactional repair; no whole-board retry/skip was added.
- Fixed transactional stale-object bug: failed tail repair can restore a new canonical front object; fallback settlement now reacquires that canonical object before mutating status.
- Added final post-topology relational settlement and final commit of debt-free active MAIN fronts, preventing valid launch geometry from disappearing merely because planner state remained `active` after the last topology change.
- Known former rejection repros 1200x1200 @ 0.75 seeds 1/3/7 now construct; release gate 144/144 and stress 1/1 pass.
- Long/fine 1200x6248 @ 0.35 seed 20260816 remains a required uncompleted qualification because the current execution host exhibits severe slowdown even on the unchanged recovery baseline.

- Documentation correction: Item-26 whole-render `BEFORE` is explicitly identified as the Aug-19 late checkpoint, not the start of the optimization run. A same-runtime Aug-18 early-authority vs final-authority 1.0->0.75 reconstruction is recorded in `docs/OPTIMIZATION_HISTORY.md`; do not quote the Item-26 1.211->1.195 / 1.180->1.147 deltas as the full-run gain.

## 2026-08-24 01:43 IST — line-murder fairness profiling checkpoint

- Kept production V48 unchanged.
- Preserved the structural first-rebase anti-starvation fairness candidate as inflight only.
- Confirmed traceback bookkeeping is not the fine-scale CPU sink; higher traceback is a downstream state symptom.
- Preserved two compact behavior-preserving experiments: first-rebase fairness lifecycle reset and duplicate singleton-connection corridor-geometry reuse. Neither is sufficient for promotion.
- Localized a major 0.5 seed-102 penalty to late preflight: V48 performs 2 materializations / 0 local repairs; fairness performs 6 materializations / 2 transactional launch repairs.
- Next causal task: trace those two repaired launch identities upstream and prevent the construction defect during routing.

## 2026-08-24 02:21 IST — line-murder atomic-horizon checkpoint

- Production V48 remains unchanged.
- Traced fairness seed-102 / scale-0.5 late preflight repairs to trace/front `162/515` and `163/516`, depth-3 siblings of parent 510, both crossing sibling trace/front `161/509`.
- Root cause: residual `_try_complete_structural_persistence_debt()` committed fronts sequentially after ordinary shared-snapshot arbitration had already found their moves incompatible; this could manufacture rendered same-family crossings which preflight later shortened away.
- Rejected per-front materialized-lane guards as over-conservative on seed 104.
- Preserved at the time the combined fairness + atomic-horizon candidate; that exact logic was later promoted and the transient diff retired.
- On 0.5 seed 102 the combined candidate removes the two late preflight repairs (`6 -> 2` materializations, `2 -> 0` local repairs) while retaining the fairness-era routing outcome; measured MAIN CPU in the direct phase-timing experiment falls to ~16.8-17.0 s from ~19.6 s on the repair-heavy fairness path.
- No promotion yet. Required next step is the normal 0.75 + 0.5 categorized/overall normalized CPU/work qualification, then the complete gate if scaling is acceptable. 0.35 remains end-of-phase only.


## 2026-08-24 19:57 IST — line-murder HOLD-solver continuation (INFLIGHT, not promoted)

- Production V48 renderer remains byte-unchanged.
- Found and corrected an experimental branch-and-bound budget-accounting bug that could accidentally expand the original 2048-state HOLD search budget.
- Preserved at the time the corrected-budget and compatibility-aware exact-bound experiments; both were rejected and their transient diffs retired after promotion.
- Corrected B&B preserves atomic geometry and improves aggregate 0.75->0.5 conflict-work growth `6.314x -> 4.821x`, but still misses V48's `3.571x`; classification **MODIFY**.
- Compatibility-aware exact bounding improves the same deterministic growth to `4.095x` while preserving atomic geometry, but remains insufficient and adds compatibility-probe work.
- Localized remaining work to repeated small conflict groups: seed 104 @ 0.5 invokes the fairness HOLD solver 156 times, mostly for groups of 2-6 fronts.
- Next step is exact small-group arbitration optimization preserving lexicographic selection and bounded-search semantics, followed by the mandated 0.75-then-0.5 scaling gate. No release gate or 0.35 run is earned yet.

## 2026-08-24 23:36 IST — recovery checkpoint after runtime reset

- No production renderer change.
- Preserved the open `1:6 @ 0.35` persistence-totality diagnosis.
- Recorded the exact architecture and surviving ordinary-scale evidence of an unpromoted totality candidate that was lost when the runtime reset during the expensive seed-1 repro.
- Reasserted that the interrupted long/fine attempt produced no valid pass/fail result and must be rerun after candidate reconstruction.

## Unreleased — long/fine persistence-totality v2 reconstruction evidence — 2026-08-25

- Rejected the first progress-driven residual-settlement placement because it ran before existing final cleanup and therefore saw hundreds of transient `between_siblings` fronts on `1:6 @ 0.35 / seed 1`.
- Corrected architecture places progress-driven relational settlement only at the true final residue point, after existing bounded final cleanup and immediately before final coordinated terminal/rejection handling.
- Preserved the soft-six / hard-four validity split: six modules is preferred work, four modules is the hard launch-survival validity floor.
- Targeted v2 tests passed before scratch loss. Ordinary 0.75 seeds 102/104 were geometry-identical to production; 0.5/102 remained invariant-clean with only small deterministic-work deltas (`71,706 -> 71,988` gesture checks; `57,466 -> 57,544` lookaheads).
- 0.5/104 and the decisive corrected-v2 `1:6 @ 0.35 / seed 1` repro were not completed before the runtime boundary. No v2 code was promoted; production remains unchanged.

## Unreleased — long/fine seed-0 phase comparison — 2026-08-25 02:00 IST

- Production renderer remains unchanged; v2 remains unpromoted.
- Exact `1:6 @ 0.35 / seed 0` completed successfully under the same whole-render phase harness on both production and v2.
- Production: `630.862 s` CPU / `630.978 s` wall / `805,176 KiB` peak RSS.
- v2: `614.485 s` CPU / `614.630 s` wall / `804,192 KiB` peak RSS.
- Production MAIN/LOCAL-gap CPU: `352.985 / 220.395 s`; v2: `338.407 / 215.606 s`.
- Conclusion: the reported ~9+ minute / ~745 MB seed-0 behavior is a real **pre-existing long/fine performance cost**, but the exact seed is finite and valid; v2 does not cause the high-RSS regime and is slightly faster in this paired run.
- Evidence retained under `archive/inflight/evidence/longfine_seed0_*`. Promotion still requires the full active release/stress and final qualification gates.

## Unreleased — long/fine v2 fine-scale scaling blocker — 2026-08-25 03:12 IST

- Production remains unchanged; long/fine v2 remains UNPROMOTED.
- Repeated ordinary 0.75 -> 0.5 qualification favored v2 (~1.592x production vs ~1.409x v2 normalized MAIN CPU/visible-work growth) with equal/better visible short-route behavior.
- Scratch contract update corrected the obsolete "under six is hard debt" test and added focused final-residue regressions; scratch candidate gate reached 151/151 PASS and stress 1/1 PASS.
- Mandatory final 0.5 -> 0.35 qualification found a real blocker: ~1.055x production vs ~1.366x v2 normalized MAIN CPU/work growth.
- Normal routing-work counters were essentially unchanged, localizing the next profiling target to the new final relational-persistence helper/support work.
- Runtime reset destroyed the scratch 151-test edits and profiler attempt; the observed evidence is preserved in `docs/LONG_FINE_PERSISTENCE_DIAGNOSIS.md`, but canonical active tests remain unchanged until reconstructed and rerun.

## 2026-08-25 03:58 IST — long/fine MAIN persistence totality PROMOTED

- Promoted the exact long/fine v2 source into production V48 at SHA-256 `e8d1874d652e7aa6a7af763ac20b2a97d1367082dc748f61771833be49d16054`.
- Split late MAIN **work debt** from **hard validity debt**: 6 visible modules remains the preferred journey, while the true hard launch-survival floor remains 4 modules plus source/fan/fragment/branch/relational obligations.
- Added true-final progress-driven relational settlement after all historical bounded cleanup. Mature sibling-embedded residue proposes from shared snapshots and commits conflict-clean compatible motion until debt clears or exact ordinary continuation is genuinely exhausted; a fixed persistence clock no longer decides validity.
- Replaced the obsolete active test that treated every under-six route as hard debt and added three focused regressions for the hard-four/soft-six contract, progress beyond fixed tick counts, geometric exhaustion, and preferred-length diagnostics. Active production gate is now **151/151 PASS**; maintained stress is **1/1 PASS**.
- Exact `1:6 @ 0.35 / seed 1` emits a complete board from the requested seed with `restart_index=0`, no skipped logical seed, 4,104/4,104 MAIN launches visible, zero hard MAIN/geometry failures, and zero unplaced components.
- Exact `1:6 @ 0.35 / seed 0` is finite in both pre-promotion production and the promoted source. The measured ~10.5 minute / ~785 MiB workload is a pre-existing long/fine performance cost, not a rejection or promotion regression.
- Corrected the earlier apparent 0.35 scaling rejection after fresh same-host remeasurement. Aggregate 1:1 seeds 102+104, 0.5 -> 0.35: BEFORE useful work `7,935.310 -> 16,553.963` modules (2.086x), CPU `39.026 -> 80.938 s` (2.074x), CPU/work growth **0.994x**; AFTER useful work `7,975.116 -> 16,599.416` (2.081x), CPU `40.881 -> 84.143 s` (2.058x), CPU/work growth **0.989x**. The former `1.366x` candidate value was host-timing contamination and is superseded.
- Ordinary 0.75 -> 0.5 repeated qualification remained acceptable (~1.592x BEFORE vs ~1.409x AFTER normalized MAIN CPU/visible-work growth), with authoritative short-route behavior equal or improved.
- Retired the duplicate inflight renderer; there is no active renderer candidate after this checkpoint.


## 2026-08-25 04:55 IST — LOCAL-1 dead-family retirement PROMOTED

- Promoted behavior-preserving LOCAL direct-mopup dead-family retirement at renderer SHA-256 `325e2ec0c79d2ec7a051c9c08b2abba73c6fab5c5561a665a2c4d16dec85acf2`.
- Once an immutable direct-run family reaches the existing 3-attempt cap, its owning region is marked dirty and the ordered cached live-family list is compacted once before the next scan. Region-version rebuilds filter already-retired identities. No scoring, retry, RNG, geometry-admission, or service-policy rule changed.
- Governing 1:1 qualification was run in mandated order 0.75 -> 0.5 on seeds 102/104; complete geometry hashes are identical BEFORE/AFTER on all four fixtures.
- Aggregate quarantine skip encounters fall `10,235 -> 873` at 0.75 and `52,848 -> 2,107` at 0.5. LOCAL visible-work growth is unchanged at `2.1046x`; LOCAL CPU growth improves `2.7449x -> 2.5800x`, so LOCAL CPU/work growth improves **`1.3042x -> 1.2259x`**. Whole-render CPU/visible-routing-work growth is effectively flat/slightly better (`1.3983x -> 1.3977x`).
- Rejected/modified two earlier implementation forms: per-quarantine list copying and insertion-ordered mapping. Both preserved geometry but carried unnecessary ordinary constant overhead.
- Added active regression `test_v48_quarantined_direct_run_families_retire_from_live_region_scan`; promoted gate is **152/152 PASS**, stress **1/1 PASS**.
- Per scale cadence, no 0.35 qualification was run for this ordinary stage. Next target is LOCAL-2 debt-driven hard-floor rescue scheduling.

## 2026-08-25 05:34 IST — LOCAL-2 inflight checkpoint (unpromoted)

- Preserved the current LOCAL-2 candidate (`d58ee1bf...9c9b0`) in `archive/inflight/`.
- Rejected debt-proportional cap and monotonic-cell-frontier variants because they did not remove the repeated-wave work mechanism.
- Retained a one-campaign rescue scheduler plus deterministic exact first-leg legality cache.
- Ordinary 0.75 -> 0.5 normalized LOCAL CPU/work improves ~`1.105x -> 1.042x`; whole-render CPU/work improves ~`1.292x -> 1.271x`.
- Long `1:6 @ 0.75` proxy completes with rescue waves `3 -> 1` and candidate tokens `19,200 -> 6,400`, but service moves `0.806398 -> 0.800341` and LOCAL traces `2,392 -> 2,096`; behavior qualification remains open.
- Production is unchanged; no release/stress gate or promotion yet.

## 2026-08-25 05:41 IST — LOCAL-2 debt-campaign rescue promoted

- Promoted the one-campaign LOCAL partial-service reserve plus deterministic exact first-leg legality cache into `pcb_v48_renderer.py`; production SHA is `d58ee1bf5073dd479e954b922a5fbdec56ef879de10394bf804094752af9c9b0`.
- Rejected debt-proportional cap and monotonic-cell-frontier approaches because they failed to remove the repeated-wave work mechanism.
- Governing 0.75 -> 0.5 normalized LOCAL CPU/work improves ~`1.105x -> 1.042x`; whole-render CPU/work improves ~`1.292x -> 1.271x`.
- Long `1:6 @ 0.75` partial rescue changes `3 waves / 19,200 tokens -> 1 wave / 6,400 tokens`; visible LOCAL traces change only `1,085 -> 1,061` and service remains valid at `0.800341`.
- Added two active regressions for one-campaign scheduling and exact first-leg reuse. Candidate and promoted canonical gates pass **154/154**; maintained stress passes **1/1**.
- LOCAL-2 is closed. MAIN per-operation amplification is the next optimization target. No routine 0.35 was run at this ordinary stage.

## 2026-08-25 — MAIN-1 instrumentation recovery (no production change)

- Added `docs/MAIN1_INSTRUMENTATION_AUDIT.md` preserving the lost scratch audit after runtime reset.
- Long-aspect `1:6 @ 0.75` instrumentation localizes MAIN amplification to increased proposal/recovery work plus selected connection-state overhead; broad-phase spatial locality itself remains mostly local.
- Rejected removal of a redundant third active-head snapshot rebuild as a meaningful MAIN-1 optimization: adjacent long-proxy CPU was flat/slightly worse despite exact geometry/work preservation.
- Recorded the next unpromoted experiment: exact O(1) current-lane-head extraction for `_connect_forced_close_lane_heads()` instead of full historical offset-polyline materialization during broad-phase indexing. Scratch source/result was lost; production remains unchanged.


## Unreleased — 2026-08-25 21:28 IST MAIN-1 interrupted proxy recovery

- No production renderer change; production remains `d58ee1bf...9c9b0`.
- Recovered post-16:29 proxy evidence: immediate recurrence after joint-future fallback, lifecycle localization to structural/connection-pending fronts, rejected post-commit-state variants, and rejected reciprocal-peer future-envelope exemption.
- Narrowed the next architectural experiment to delaying hard reciprocal `CONNECTION_PENDING` promotion until the pair is within the existing singleton join executor's 10-module reach while preserving long-range attraction and exact join legality.
- No scratch source for the post-16:29 experiments survived; repository clearly distinguishes recovered evidence from authoritative code.

## Unreleased — 2026-08-25 21:50 IST MAIN-1 recovery/conflict audit

- Production unchanged at `d58ee1bf...9c9b0`; no candidate promoted.
- Rejected three connection-lifecycle policy variants: hard pairing capped to the 10-module join reach, soft long-range target with delayed hard peer status, and exclusion of recovering fronts from pairing.
- Pair-churn probe found 3558 hard assignments; immediate partner switching is dominated by repair state (993 repair vs 259 clean), showing churn is coupled to recovery.
- No-repair recurrence probe found 510/640 exhausted atomic conflict groups recur with the same front set on the next round.
- Existing path/proposal/future failure caches already show heavy reuse; ordinary blocked-geometry caching is not the missing wedge.
- `_future_conflict()` reuse probe found ~65% repeated approximate proposal-pair states. Exact call-time memoization preserved behavior but was slower; tokenized cross-round variants were rejected/unqualified; exact round-local memoization preserved behavior but yielded only ~20% hits and no robust speedup.
- MAIN-1 next target is behavior-preserving reuse/wakeup control for unchanged exhausted conflict transactions. Formal 0.75 -> 0.5 qualification remains pending and 0.35 remains reserved for phase-end qualification.

## Unreleased — 2026-08-25 21:58 IST MAIN-1 method timing localization

- Production unchanged at `d58ee1bf...9c9b0`; no candidate promoted.
- Zero-policy-change `1:2 @ 0.75 / seed 104` proxy timing localizes MAIN cost primarily to proposal/lookahead regeneration: `_proposal_variants` ~11.07 s inclusive, `_lookahead_adjust` ~5.50 s, `_propose` ~5.09 s, `_gesture_clear` ~4.95 s, `_future_options` ~4.94 s.
- Conflict machinery is much smaller (`_future_conflict` ~0.93 s, `_conflict_groups` ~0.88 s, `_solve_conflict_group` ~0.26 s), so conflict-DFS/cache micro-optimization is not the earned MAIN-1 wedge.
- Combined with 510/640 immediately recurring no-repair exhausted groups, next target is exact local-event/version-guarded reuse of proposal/lookahead subproofs with routing/RNG/legality semantics preserved.

### 2026-08-25 — MAIN-1 exact-local proposal/future proof reuse promoted

- Promoted exact cross-round proposal-membership reuse and successful future-leg proof reuse under exact local committed-path/source-egress dependency signatures.
- Preserves seeded replay, proposal scoring/RNG order, routing topology and output geometry; nearby relevant path/egress mutation invalidates reuse immediately.
- Formal seeds 102+104, 0.75 -> 0.5: normalized MAIN CPU/work growth improves **2.215492x -> 1.432545x** with identical emitted MAIN work/topology; aggregate 0.5 MAIN CPU `59.275867 -> 40.621074 s`, gesture-clear checks `149,901 -> 130,062`.
- Added two permanent cache-contract regressions. Canonical release gate **156/156 PASS**, maintained geometry stress **1/1 PASS**.
- New authoritative renderer SHA-256: `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`.
- MAIN-1 ordinary stage is closed. Reserved phase-end 0.35 qualification is active; the first BEFORE seed-102 attempt exceeded its execution boundary with no record and is not classified as a renderer failure.


### 2026-08-26 00:08 IST — MAIN-1 final fine-scale qualification closed

- No renderer code change; production remains `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`.
- Completed reserved same-host 0.5 -> 0.35 seeds-102+104 gate with byte-identical BEFORE/AFTER geometry/topology.
- MAIN useful-work growth `2.063991x`; normalized CPU/work improves `1.037378x -> 1.005017x`; aggregate 0.35 MAIN CPU `108.795035 -> 106.334978 s`; gesture checks `296,105 -> 266,481`.
- Explicitly superseded a provisional cross-host `1.268x` AFTER calculation after fresh 0.5 measurements proved host-speed contamination.
- Long/fine scaling phase (LOCAL-1 + LOCAL-2 + MAIN-1) is closed. Next task is the separate full `1:6 @ 0.35` operational runtime/RSS benchmark.

## 2026-08-26 00:46 IST — interrupted operational benchmark preserved

- No renderer change; production remains `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`.
- Preserved the only surviving observation from the interrupted full `1:6 @ 0.35 / seed 0` operational run: ~5:05 CPU / ~494 MiB RSS, healthy/no exception, but no completed harness record.
- That observation is not a completion time and must not be used in scaling arithmetic. The exact operational fixture remains to be rerun to completion.

## 2026-08-26 — full long-board operational check: scaling phase reopened

- No renderer code change; production remains `3100503d...03ebb` and still passes its promoted correctness contract.
- Exact same-host seed-0 `1:1 -> 1:6 @ 0.35` operational measurements: CPU `96.822 -> 729.786 s`, visible routing work `2,006 -> 11,993` (5.979x), normalized whole-render CPU/work **1.261x**.
- Remaining phase-normalized growth: MAIN CPU/launch **1.256x**, LOCAL CPU/trace **1.375x**, component-place CPU/component **1.164x**.
- Same-host excess above 6x square CPU is `148.855 s`, dominated by MAIN (`+75.37 s`) and LOCAL (`+67.30 s`).
- Long/fine scaling phase is therefore **REOPENED**. Existing LOCAL-1/2 and MAIN-1 promotions remain retained; next work targets remaining aspect-driven MAIN/LOCAL amplification.


## 2026-08-26 01:23 IST — reopened long-board LOCAL localization

- No production change; authoritative renderer remains `3100503d...03ebb`.
- Full `1:1 -> 1:6 @ 0.35` same-host operational scaling remains the governing reopen evidence: whole-render CPU/work `1.261x`, LOCAL CPU/trace `1.375x`, MAIN CPU/launch `1.256x`, components CPU/component `1.164x`.
- New zero-policy `0.75 / seed 0` LOCAL aspect probe: visible traces `166 -> 1000` (6.024x), open cells `2741 -> 16098` (5.873x), but residual regions `47 -> 344` (7.319x). `_launch_local_gap_fronts()` CPU grows `1.158 -> 9.138 s` (7.894x), while `_gesture_clear()` grows 6.038x and `_local_gap_target()` only 4.828x.
- Diagnostic cProfile points into repeated launch scheduling / fragmented residual geometry: `_launch_local_gap_fronts()` ~`1.696 -> 13.940 s`; long-board `STRtree.query_nearest` ~4.312 s/1012 calls; `_residual_gap_regions()` `0.653 -> 4.828 s` (~7.39x).
- No active renderer candidate. Next earned work is to separate nearest-geometry tree/query cost from whole-candidate-pool scoring/allocation in `_launch_local_gap_fronts()` and remove work proportional to fragmentation rather than accepted LOCAL service. Existing LOCAL-1/2 and MAIN-1 promotions remain retained.

### 2026-08-26 04:06 IST — status-only LOCAL-3 checkpoint
- No production change.
- Added denominator correction: long LOCAL geometry performs materially more exact collision interaction work per visible trace.
- Recorded rejected post-02:56 LOCAL cache/hash experiments.
- Preserved active unqualified two-level static group->primitive broad-phase candidate.
- Tightened continuation rule to avoid micro-optimization cycling.


## 2026-08-26 — optimization STOPPED / final candidate rejected

- Explicit stop decision: no active optimization work remains; do not start another LOCAL or MAIN optimization branch unless the user explicitly reopens optimization.
- Final unqualified LOCAL-3 two-level static group->primitive candidate rejected after its `1:6 @ 0.75 / seed 0` run failed to complete within 300 s and emitted no durable record, versus ~116.804 s production control.
- Corrected LOCAL denominator retained: exact collision-interaction work grows materially faster than visible trace count (path-GEOS 6.830x; static primitive returns 7.633x versus traces 6.024x), so much of the long-board trace-normalized CPU increase is real geometry-density work.
- Known residual long-aspect costs remain accepted/deferred rather than open tasks: whole 1.261x CPU/visible-routing-work; MAIN 1.256x CPU/launch; LOCAL 1.375x CPU/trace before collision-work correction; components 1.164x CPU/component.
- Final production SHA remains `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`; final gate 156/156 + stress 1/1 PASS.

### Historical evidence correction — 2026-08-26

- Added user-supplied pre-optimization 0341 raw error evidence showing a real late post-route validity failure after 435.35 s: `pair_chip_isolated`.
- Corrected the historical narrative: pre-optimization long/fine V48 was not uniformly "valid but slow"; validity was seed/path dependent in addition to severe runtime cost.
- No renderer code changed. Current production SHA remains `3100503d27110c2bcd4b680ab65b6f9d50b344660fd43106cedbabe62ff03ebb`.

## 2026-08-26 — seed-total component↔chip clearance correctness fix — PROMOTED

- Fixed a real seed-totality correctness defect behind the historical late `post-route validation failed: pair_chip_isolated` failure.
- `placement_kind == "isolated"` means an isolated capacitor component; the error is a chip↔isolated-component clearance violation, not an "isolated chip" condition.
- Root cause: component admission used `chip.geom.buffer(component_chip_clearance, quad_segs=8)` at the nominal radius. A finite round buffer is an inscribed polygonal approximation, leaving a thin false-safe annulus near rounded offset corners. Final validation uses exact primitive Euclidean distance, so construction and validation could disagree for rare geometries/seeds.
- Reproduced the defect deterministically without the historical seed: a capacitor in that annulus was accepted by the old construction gate while `_groups_violate_clearance(..., component_chip_clearance)` and final validation reported `pair_chip_isolated`.
- Replaced nominal-radius chip keepouts with a mathematically conservative finite-buffer radius `gap / cos(pi/(4*quad_segs)) + epsilon`. The fast buffered broad phase can now false-reject only; it cannot false-accept a true Euclidean clearance violation.
- Applied the same conservative-buffer proof to residual-gap static-clearance certificates, eliminating the second path by which a residual filler could rely on an under-covering polygonized keepout.
- Added an exact phase-local component↔chip clearance audit and made zero violations a component-phase acceptance invariant. MAIN is never regenerated for this condition.
- Added two permanent regressions: the explicit historical-style annulus/`pair_chip_isolated` fixture and conservative residual-certificate verification.
- Adversarial property sweep: 4,680 near-boundary geometries, zero false accepts. End-to-end seeds 0/1/2 at `1:1 @ 1.0` and seed 0 at `1:2 @ 0.75` complete with zero component↔chip clearance violations.
- Final canonical gate: **158/158 active tests PASS + stress 1/1 PASS**.
- Authoritative renderer SHA-256: `d7ac1d9af0286dda86d994a638504fe8ab63521847d9050633fc4d49d0f21745`.
- Optimization remains stopped. This was a correctness/seed-totality repair, not a reopened performance-optimization phase.

## 2026-08-26 — MAIN persistence-totality recurrence repair — PROMOTED

- A real production-use `1:6 @ 0.35` run from the prior renderer failed after 184.684 s with `RuntimeError: MAIN persistence horizon unresolved`; absence of an explicit seed does not reduce severity because renderer-generated seeds are ordinary production inputs.
- Closed the remaining non-relational final hard-debt holes without reseeding: deep-traceback root launches are constructively restored through their continuously reserved four-module source-egress corridor, and exhausted unmaterialized fan/fragment/branch intentions are cancelled once visible geometry is already mature.
- Preserved legitimate deep traceback/source-reservation behavior; an earlier blunt rollback-floor version was rejected when existing regressions caught it.
- Final persistence exceptions now include sample seed and debt-class diagnostics if the supposedly unreachable guard ever fires.
- Added two permanent regressions and tightened release language: a finite green suite is regression evidence, not proof that every seed has been enumerated. Any valid-seed construction `RuntimeError` automatically reopens correctness.
- Canonical gate: **162/162 release tests PASS + stress 1/1 PASS**. Exact seeds 0–31 at 1:1 @ 1.0 complete MAIN with zero unresolved persistence debt. Historical exact seed 1 at `1:6 @ 0.35` MAIN-only completes in 385.94 CPU-s with 4,104/4,104 launches visible and zero unresolved hard debt.
- Authoritative renderer SHA-256: `5b5eb7cd883b1f9403e41dbb9626976626008de2f724a03f7cfad94413da0df1`.
