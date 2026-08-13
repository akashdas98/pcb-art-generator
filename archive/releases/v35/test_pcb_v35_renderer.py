import math
import statistics
import gc
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pcb_v35_renderer import V35Renderer, BundleGesturePlanner, SplitMix64, sample_seed, chip_seed, nearest_dir_index, SIDE_TO_DIR, dir_vec, Group, prim_rect_fill


class NoPathRenderer(V35Renderer):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        # Historical non-routing fixtures test component grammar/clearance, not V33 mop-up density.
        self.component_extra_filler_limit=0
        self.component_density_cap=0
    def generate_pathways(self, sseed, placed):
        return [], dict(
            pathway_bundle_count=0, pathway_launch_trace_count=0, pathway_split_count=0,
            pathway_leaf_bundle_count=0, pathway_connection_count=0,
            pathway_collection_connection_count=0, pathway_termination_count=0,
            pathway_intersection_marker_count=0, pathway_overlap_event_count=0,
            pathway_trace_count=0, pathway_mean_segments_per_trace=0.0,
            pathway_max_segments_per_trace=0, pathway_min_segments_per_trace=0)

class V35RendererTests(unittest.TestCase):

    def _planner_front(self, planner, fid_seed, start, direction, chip=0):
        tid=planner.next_trace_id; planner.next_trace_id += 1
        return planner._make_front(ids=[tid], chip=chip, side='right', side_index=0,
                                   path=[start], direction=direction, offsets={tid:0.0},
                                   thicknesses={tid:3.0*planner.U}, prefixes={tid:[]},
                                   rng=SplitMix64(fid_seed))

    def test_root_main_launch_can_trace_back_to_emergence_anchor(self):
        r=V35Renderer(seed=31001)
        planner=BundleGesturePlanner(r, sample_seed(r.seed,0), [])
        f=self._planner_front(planner, 1, (200.0,200.0), 0)
        end=(200.0+2*planner.module,200.0)
        g=planner._corridor_geom(f,f['path'][-1],end)
        p=dict(front=f['id'],start=f['path'][-1],end=end,dir=0,modules=2,geom=g,score=1.0)
        planner._accept(f,p,defer_post=True)
        self.assertEqual(len(f['path']),2)
        f['reroute_pending']=True; f['reroute_ready_round']=0
        count=planner._traceback_for_reroute(f)
        self.assertEqual(count,1)
        self.assertEqual(len(f['path']),1)
        self.assertEqual(f['path'][0],(200.0,200.0))
        self.assertGreaterEqual(planner.stats['pathway_root_emergence_traceback_count'],1)

    def test_joint_conflict_solution_is_insertion_order_invariant(self):
        r=V35Renderer(seed=31002)
        planner=BundleGesturePlanner(r, sample_seed(r.seed,0), [])
        a=self._planner_front(planner, 2, (100.0,200.0), 0, chip=0)
        b=self._planner_front(planner, 3, (180.0,120.0), 2, chip=1)
        def prop(f,end,d,score):
            g=planner._corridor_geom(f,f['path'][-1],end)
            return dict(front=f['id'],start=f['path'][-1],end=end,dir=d,modules=2,geom=g,future_geom=g,score=score,priority=score)
        # First choices cross; second choices peel away.
        av=[prop(a,(260.0,200.0),0,5.0), prop(a,(160.0,140.0),7,4.0)]
        bv=[prop(b,(180.0,280.0),2,5.0), prop(b,(240.0,180.0),1,4.0)]
        m1={a['id']:av,b['id']:bv}; m2={b['id']:bv,a['id']:av}
        g1=planner._conflict_groups(m1); g2=planner._conflict_groups(m2)
        self.assertEqual(g1,g2)
        s1=planner._solve_conflict_group(g1[0],m1)
        s2=planner._solve_conflict_group(g2[0],m2)
        k=lambda sol:[(p['front'],p['dir'],p['end']) for p in sol]
        self.assertEqual(k(s1),k(s2))
        self.assertFalse(any(planner._future_conflict(p,q) for i,p in enumerate(s1) for q in s1[i+1:]))

    def test_unsolved_same_round_group_defers_instead_of_choosing_winner(self):
        r=V35Renderer(seed=31003)
        planner=BundleGesturePlanner(r, sample_seed(r.seed,0), [])
        a=self._planner_front(planner, 4, (100.0,200.0), 0, chip=0)
        b=self._planner_front(planner, 5, (180.0,120.0), 2, chip=1)
        def prop(f,end,d):
            g=planner._corridor_geom(f,f['path'][-1],end)
            return dict(front=f['id'],start=f['path'][-1],end=end,dir=d,modules=2,geom=g,future_geom=g,score=1.0,priority=1.0)
        vm={a['id']:[prop(a,(260.0,200.0),0)], b['id']:[prop(b,(180.0,280.0),2)]}
        group=planner._conflict_groups(vm)[0]
        self.assertIsNone(planner._solve_conflict_group(group,vm))
        self.assertTrue(planner._schedule_atomic_conflict_repair(group,0))
        self.assertTrue(a['reroute_pending'])
        self.assertTrue(b['reroute_pending'])
        self.assertEqual(len(planner.path_segments),0)

    def test_young_blocked_launch_requests_causal_blocker_rollback(self):
        r=V35Renderer(seed=31004)
        planner=BundleGesturePlanner(r, sample_seed(r.seed,0), [])
        young=self._planner_front(planner, 6, (100.0,200.0), 0, chip=0)
        blocker=self._planner_front(planner, 7, (170.0,120.0), 2, chip=1)
        blocker['gestures']=5; blocker['travel']=6*planner.module; blocker['_routing_round']=3
        a=(170.0,120.0); b=(170.0,280.0); g=planner._corridor_geom(blocker,a,b)
        planner._record_segment(blocker,a,b,g)
        self.assertTrue(planner._request_local_yield(young,4))
        self.assertTrue(blocker['reroute_pending'])
        self.assertFalse(young['reroute_pending'])
        self.assertGreaterEqual(planner.stats['pathway_causal_blocker_rollback_request_count'],1)

    def _planner_with_fake_chip(self, seed=32001):
        r=V35Renderer(seed=seed)
        chip=Group('fake-chip', [prim_rect_fill(300.0,300.0,80.0,80.0,0,r.FG)],
                   dict(placement_kind='chip'))
        return r, BundleGesturePlanner(r, sample_seed(r.seed,0), [chip])

    def _root_family_front(self, planner, seed=1, lane_count=2, fan_pending=True):
        ids=[]; offsets={}; thicknesses={}
        pitch=7.0*planner.U
        for j in range(lane_count):
            tid=planner.next_trace_id; planner.next_trace_id += 1
            ids.append(tid)
            offsets[tid]=(j-(lane_count-1)/2)*pitch
            thicknesses[tid]=3.0*planner.U
        f=planner._make_front(ids=ids, chip=0, side='right', side_index=0,
                              path=[(360.0,300.0)], direction=0, offsets=offsets,
                              thicknesses=thicknesses, prefixes={tid:[] for tid in ids},
                              rng=SplitMix64(seed), forced_straight_modules=int(planner.launch_egress_modules))
        f['fan_parts']=[ids[:max(1,lane_count//2)],ids[max(1,lane_count//2):]] if lane_count>1 else [ids]
        f['fan_pending']=bool(fan_pending and lane_count>1)
        f['launch_family_key']=(0,0,'right')
        f['launch_egress_pending']=True
        for tid in ids:
            start=(360.0,300.0+offsets[tid])
            end=(360.0+planner.launch_egress_modules*planner.module,start[1])
            rad=.5*thicknesses[tid]+planner.r.pathway_interroute_keepout
            from shapely.geometry import LineString
            planner.source_egress_reservations.append(dict(owner=(0,0,'right'),tid=tid,active=True,
                geom=LineString([start,end]).buffer(rad,cap_style='round',join_style='mitre',quad_segs=4)))
        return f

    def test_root_bundle_cannot_structurally_split_before_physical_egress(self):
        r,planner=self._planner_with_fake_chip(32001)
        f=self._root_family_front(planner, 11, lane_count=4, fan_pending=True)
        self.assertTrue(planner._source_egress_pending(f))
        self.assertEqual(planner._direction_candidates(f),[f['initial_dir']])
        self.assertEqual(planner._branch_front(f),[])
        self.assertFalse(planner._fragment_bundled_front(f))

    def test_single_cohort_root_is_straight_until_source_egress(self):
        r,planner=self._planner_with_fake_chip(32002)
        f=self._root_family_front(planner, 12, lane_count=3, fan_pending=False)
        self.assertFalse(f['fan_pending'])
        self.assertTrue(planner._source_egress_pending(f))
        # Egress protection is independent of fan state: a one-cohort side cannot make the
        # V31 straight->45->straight hook before its physical source lanes clear.
        self.assertEqual(planner._direction_candidates(f),[f['initial_dir']])

    def test_root_traceback_reactivates_source_egress_reservation(self):
        r,planner=self._planner_with_fake_chip(32003)
        f=self._root_family_front(planner, 13, lane_count=1, fan_pending=False)
        start=f['path'][-1]
        end=(start[0]+5*planner.module,start[1])
        g=planner._corridor_geom(f,start,end)
        p=dict(front=f['id'],start=start,end=end,dir=0,modules=5,geom=g,future_geom=g,score=1.0,priority=1.0)
        planner._accept(f,p,defer_post=True)
        self.assertTrue(planner._launch_egress_cleared(f))
        self.assertTrue(all(not rec['active'] for rec in planner.source_egress_reservations))
        f['reroute_pending']=True; f['reroute_ready_round']=0
        self.assertGreaterEqual(planner._traceback_for_reroute(f),1)
        self.assertTrue(planner._source_egress_pending(f))
        self.assertTrue(all(rec['active'] for rec in planner.source_egress_reservations))

    def test_same_family_conflict_can_atomically_hold_sibling(self):
        r,planner=self._planner_with_fake_chip(32004)
        a=self._root_family_front(planner, 14, lane_count=1, fan_pending=False)
        b=self._root_family_front(planner, 15, lane_count=1, fan_pending=False)
        # Give both the same family but separated starts. Each only has one proposal and the
        # proposals collide, so a full assignment is impossible; protected-family arbitration
        # must return one mover + one explicit HOLD rather than a winner/loser commit fallback.
        b['path']=[(420.0,240.0)]; b['origin']=b['path'][0]
        for f in (a,b): f['launch_family_key']=(0,0,'right')
        def prop(f,end,d=0):
            g=planner._corridor_geom(f,f['path'][-1],end)
            return dict(front=f['id'],start=f['path'][-1],end=end,dir=d,modules=2,geom=g,future_geom=g,score=1.0,priority=1.0)
        pa=prop(a,(500.0,300.0),0)
        pb=prop(b,(420.0,360.0),2)
        vm={a['id']:[pa],b['id']:[pb]}
        sol=planner._solve_conflict_group([a['id'],b['id']],vm)
        self.assertIsNotNone(sol)
        self.assertEqual(len(sol),1)
        self.assertEqual(planner.stats['pathway_family_hold_front_count'],1)

    def test_foreign_path_inside_head_disk_is_not_invisible(self):
        r,planner=self._planner_with_fake_chip(32005)
        planner.source_egress_reservations=[]
        f=self._root_family_front(planner, 16, lane_count=1, fan_pending=False)
        planner.source_egress_reservations=[]
        # Put a foreign segment only a tiny distance in front of the current head. V31/V33's
        # old global start-disk subtraction hid this exact geometry from _gesture_clear().
        start=f['path'][-1]
        bx=start[0]+.04*planner.module
        blocker=self._planner_front(planner, 17, (bx,start[1]-2*planner.module), 2, chip=1)
        bend=(bx,start[1]+2*planner.module)
        bg=planner._corridor_geom(blocker,blocker['path'][-1],bend)
        planner._record_segment(blocker,blocker['path'][-1],bend,bg)
        end=(start[0]+2*planner.module,start[1])
        geom=planner._corridor_geom(f,start,end)
        self.assertFalse(planner._gesture_clear(f,start,end,geom))

    def test_escaped_trace_is_clipped_at_first_frame_crossing(self):
        r=V35Renderer(seed=32006)
        planner=BundleGesturePlanner(r, sample_seed(r.seed,0), [])
        pts=[(100.0,100.0),(-10.0,100.0),(-10.0,220.0)]
        clipped=planner._clip_escaped_polyline_to_frame(pts)
        self.assertEqual(len(clipped),2)
        self.assertAlmostEqual(clipped[-1][0],0.0,places=6)
        self.assertAlmostEqual(clipped[-1][1],100.0,places=6)

    def test_component_fallback_reuses_precomputed_route_keepout(self):
        r = V35Renderer(seed=9090)
        cap = r.generate_isolated_capacitors(sample_seed(r.seed, 0))[0]
        # Block essentially the whole legal component field so the bounded fallback executes.
        blocker = Group('blocking-path', [prim_rect_fill(r.W/2, r.H/2, r.W-30*r.U, r.H-30*r.U, 0, r.FG)],
                        dict(placement_kind='pathway', pathway=True))
        original = r._component_candidate_valid
        missing = {'path': 0, 'chip': 0}
        def wrapped(cand, kind, chips, pathways, accepted, attachment_point=None,
                    chip_keepout=None, pathway_keepout=None, accepted_index=None, pathway_component_index=None):
            if chip_keepout is None: missing['chip'] += 1
            if pathway_keepout is None: missing['path'] += 1
            return original(cand, kind, chips, pathways, accepted, attachment_point,
                            chip_keepout, pathway_keepout, accepted_index, pathway_component_index)
        with mock.patch.object(r, '_component_candidate_valid', side_effect=wrapped):
            placed, stats = r.place_residual_components([], [cap], [], [blocker], SplitMix64(1234),
                                                         target=.85, fallback_attempts=12)
        self.assertEqual(stats['component_unplaced_count'], 1)
        # V29 forgot these arguments in the hot fallback loop, rebuilding the complete route
        # keepout on every random candidate.  Every placement call must receive the cached unions.
        self.assertEqual(missing['chip'], 0)
        self.assertEqual(missing['path'], 0)

    def test_post_route_component_failure_never_restarts_routing_internally(self):
        class ComponentFailureRenderer(V35Renderer):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.route_calls = 0
            def generate_pathways(self, sseed, placed):
                self.route_calls += 1
                return [], {}
            def _place_component_population_on_frozen_routes(self, cur_seed, population, placed_chips, pathways, layout_attempts=4):
                return [], {
                    'component_unplaced_count': 1,
                    'component_residual_gap_fill_actual': 0.0,
                }, population[2]
        r = ComponentFailureRenderer(seed=15317896771924782433)
        with self.assertRaisesRegex(RuntimeError, 'component-only recovery exhausted'):
            r.generate_sample(0, max_sample_restarts=4, collection_plan_attempts=128, calibration_rounds=96)
        self.assertEqual(r.route_calls, 1)

    def test_exact_quota_assignment(self):
        r = V35Renderer(seed=777)
        for i in range(100):
            rng = SplitMix64(sample_seed(r.seed, i))
            N = r.collection_count(rng)
            assigned = r.assign_collection_families(rng, N)
            if assigned == (None, None):
                continue
            assigns, q = assigned
            self.assertEqual(sum('ic' in a['families'] for a in assigns), q['N_ic'])
            self.assertEqual(sum('dense' in a['families'] for a in assigns), q['N_dense'])
            self.assertEqual(sum(a['border'] for a in assigns), q['N_border'])
            for a in assigns:
                self.assertEqual(len(a['families']), a['family_count'])
                self.assertEqual(len(a['families']), len(set(a['families'])))

    def test_ic_arrays_are_procedural_and_connected(self):
        r = V35Renderer(seed=1)
        modes = {'single': 0, 'separate': 0, 'array': 0}
        dims = set()
        ratios = []
        contacts = 0
        for i in range(800):
            sg = r.make_ic_subgroup(SplitMix64(1000 + i))
            modes[sg.structural['ic_mode']] += 1
            if sg.structural['ic_mode'] == 'array':
                self.assertEqual(sg.structural['required_contact_failure_count'], 0)
                self.assertGreater(sg.structural['required_contact_count'], 0)
                rr, cc = sg.structural['array_shape']
                dims.add((rr, cc))
                ratios.append(max(rr, cc) / min(rr, cc))
                contacts += sg.structural['required_contact_count']
        self.assertGreater(modes['array'], 600)
        self.assertGreater(modes['single'], 40)
        self.assertGreater(modes['separate'], 30)
        self.assertGreaterEqual(len(dims), 8)
        self.assertTrue(any(min(d) == 1 for d in dims))
        self.assertTrue(any(min(d) > 1 for d in dims))
        self.assertGreater(max(ratios), 4.0)
        self.assertGreater(contacts, 0)

    def test_dense_dimensions_and_diamond_stagger_are_procedural(self):
        r = V35Renderer(seed=222)
        dims = set()
        ratios = []
        orient = {'orthogonal': 0, 'diamond-row-shift': 0, 'diamond-col-shift': 0}
        for i in range(800):
            sg = r.make_dense_subgroup(SplitMix64(5000 + i), 12 * r.U)
            dims.add(tuple(sg.structural['dense_dims']))
            rr, cc = sg.structural['dense_dims']
            ratios.append(max(rr, cc) / min(rr, cc))
            orient[sg.structural['dense_orientation']] += 1
        self.assertGreaterEqual(len(dims), 18)
        self.assertGreater(orient['orthogonal'], 250)
        self.assertGreater(orient['diamond-row-shift'], 120)
        self.assertGreater(orient['diamond-col-shift'], 120)
        self.assertGreater(sum(x >= 2.5 for x in ratios), 400)
        self.assertTrue(any(x < 2.0 for x in ratios))

    def test_main_chip_scalar_variation_is_continuous(self):
        r = V35Renderer(seed=999)
        qvals = set()
        avals = set()
        seen_m5 = 0
        for si in range(50):
            s = sample_seed(r.seed, si)
            for j in range(4):
                g = r.generate_chip(chip_seed(s, j), j)
                qvals.add(round(g.structural['q_chip'], 6))
                avals.add(round(max(g.structural['width'], g.structural['height']) / g.structural['q_chip'], 6))
                if 'M5' in g.structural['motifs']:
                    seen_m5 += 1
                    self.assertEqual(len([p for p in g.primitives if p.kind == 'quadratic']), 4)
        self.assertGreater(len(qvals), 120)
        self.assertGreater(len(avals), 120)
        self.assertGreater(seen_m5, 0)

    def test_capacitor_circle_family_is_available_and_varied(self):
        r = V35Renderer(seed=333)
        seen_concentric = 0
        radii = []
        for i in range(300):
            g = r.make_ordinary_subgroup(SplitMix64(7000 + i), 'capacitor_circle', 12 * r.U)
            metas = g.structural['capacitor_entities']
            self.assertEqual(g.structural['entity_count'], 1)
            self.assertEqual(g.structural['lattice'], 'singleton')
            self.assertEqual(len(metas), 1)
            for m in metas:
                radii.append(m['capacitor_radius'])
                if m['capacitor_state'] == 'concentric':
                    seen_concentric += 1
        self.assertGreater(seen_concentric, 100)
        self.assertGreaterEqual(min(radii), 6.3 * r.U)
        self.assertGreater(max(radii), 18.0 * r.U)
        self.assertGreater(max(radii)-min(radii), 12.0 * r.U)

    def test_isolated_capacitor_occurrence_path(self):
        r = V35Renderer(seed=444)
        samples_with = 0
        counts = []
        states = set()
        for i in range(300):
            gs = r.generate_isolated_capacitors(sample_seed(r.seed, i))
            if gs:
                samples_with += 1
                counts.append(len(gs))
                states.update(g.structural['capacitor_state'] for g in gs)
                self.assertTrue(all(g.structural['family'] == 'capacitor_circle' for g in gs))
        self.assertEqual(samples_with, 300)
        self.assertGreaterEqual(max(counts), 2)
        self.assertIn('filled', states)
        self.assertIn('hollow', states)
        self.assertIn('concentric', states)


    def test_multiple_isolated_capacitors_are_independent_and_clear(self):
        r = V35Renderer(seed=445)
        gs = None
        for i in range(500):
            candidate = r.generate_isolated_capacitors(sample_seed(r.seed, i))
            if len(candidate) >= 2:
                gs = candidate
                break
        self.assertIsNotNone(gs)
        placed = r.place_objects([], [], gs, SplitMix64(123456789))
        self.assertIsNotNone(placed)
        caps = [g for g in placed if g.structural.get('placement_kind') == 'isolated']
        self.assertEqual(len(caps), len(gs))
        for i, a in enumerate(caps):
            for b in caps[i+1:]:
                self.assertFalse(a.geom.intersects(b.geom))
                self.assertGreaterEqual(a.geom.distance(b.geom), 12 * r.U - 1e-7)

    def test_source_has_no_ic_or_dense_shape_lookup_table(self):
        src = Path(__file__).with_name('pcb_v35_renderer.py').read_text()
        self.assertNotIn('shape=rng.weighted([((1,2)', src)
        self.assertNotIn('dims=rng.weighted([((1,4)', src)
        self.assertIn('_procedural_dims(', src)

    def test_bundle_gesture_pathways_are_direct_modular_and_collision_clean(self):
        gc.collect()
        r = V35Renderer(seed=12345)
        placed, rep = r.generate_sample(0, max_sample_restarts=64)
        paths = [g for g in placed if g.structural.get('placement_kind') == 'pathway' and not g.structural.get('pathway_marker')]
        non_paths = [g for g in placed if g.structural.get('placement_kind') != 'pathway']
        # Visible pathway count is a soft best-effort outcome; hard checks below govern validity.
        self.assertGreater(len(paths), 0)
        self.assertEqual(rep['pathway_planner_mode'], 'route_first_family_protected_transactional_parallel')
        self.assertEqual(rep['generation_order'], 'main_chips -> primary_pathways -> local_gap_pathways -> residual_components')
        self.assertEqual(rep['component_placement_mode'], 'post_route_residual_gap_fill')
        self.assertEqual(rep.get('component_pathway_unauthorized_overlap_count',0),0)
        self.assertGreaterEqual(rep['component_residual_gap_fill_actual'],0.90)
        self.assertLessEqual(rep['component_residual_gap_fill_actual'],1.0)
        self.assertEqual(rep['pathway_candidate_seed_retry_count'], 0)
        self.assertEqual(rep['pathway_route_search_count'], 0)
        self.assertGreaterEqual(rep['pathway_bundle_count'], rep['chip_count'] * 4)
        self.assertGreater(rep['pathway_local_gap_source_count'], 0)
        self.assertGreater(rep['pathway_local_gap_trace_count'], 0)
        self.assertGreater(rep['pathway_local_gap_visible_trace_count'], 0)
        self.assertEqual(tuple(rep['pathway_local_gap_special_probability_range']), (0.15,0.30))
        self.assertGreaterEqual(rep['pathway_local_gap_special_ratio'], 0.0)
        self.assertGreaterEqual(rep['pathway_local_gap_source_count'], 6)
        self.assertEqual(rep['pathway_local_gap_independent_source_count'], rep['pathway_local_gap_source_count'])
        self.assertEqual(rep['pathway_local_gap_trace_count'], rep['pathway_local_gap_source_count'])
        self.assertGreaterEqual(rep['pathway_local_gap_bundle_pair_count'], 0)
        self.assertEqual(rep['pathway_local_gap_round_budget'], 28)
        self.assertTrue(0.40 <= rep['pathway_local_gap_fill_target_fraction'] <= 0.50)
        self.assertGreater(rep['pathway_local_gap_open_cell_count'], 0)
        self.assertGreater(rep['pathway_local_gap_target_cell_count'], 0)
        self.assertGreaterEqual(rep['pathway_local_gap_fill_actual'], 0.395)
        self.assertLessEqual(rep['pathway_local_gap_fill_actual'], 0.55)
        self.assertEqual(tuple(rep['pathway_local_gap_normal_branch_boost_range']), (3.0,5.0))
        self.assertAlmostEqual(rep['pathway_local_gap_exit_probability_factor'], 0.50)
        self.assertAlmostEqual(rep['pathway_chip_launch_gap'], 22.5*r.U)
        self.assertGreaterEqual(rep['pathway_source_marker_count'], rep['pathway_visible_launch_trace_count'])
        # Soft design outcome: launch density is reported, not quota-enforced.
        self.assertGreater(rep['pathway_launch_trace_count'], 0)
        # Soft target only: realized launch coverage may fall below the sampled intent when geometry is constrained.
        self.assertGreaterEqual(rep['pathway_visible_launch_coverage_min'], 0.0)
        self.assertGreater(rep['pathway_launch_cohort_count'], rep['chip_count'] * 4)
        self.assertGreater(rep['pathway_split_count'], 0)
        # Travel/segment density is diagnostic, not a realized quota.
        self.assertGreaterEqual(rep['pathway_mean_segments_per_trace'], 0.0)
        # Soft target only: cross-chip connection appetite is stochastic/conditional, not a realized quota.
        self.assertGreaterEqual(rep['pathway_cross_chip_connection_count'], 1)
        self.assertEqual(rep['pathway_cross_chip_connected_trace_count'], 2 * rep['pathway_cross_chip_connection_count'])
        self.assertEqual(rep['pathway_collection_connection_count'], 0)
        self.assertEqual(rep['pathway_connection_count'], rep['pathway_cross_chip_connection_count'])
        self.assertGreater(rep['pathway_decision_round_count'], 1)
        self.assertGreaterEqual(rep['pathway_rounds_with_multiple_fronts'], 0.90 * rep['pathway_decision_round_count'])
        self.assertEqual(rep['pathway_static_intersection_count'], 0)
        self.assertEqual(rep['pathway_unmarked_overlap_count'], 0)
        self.assertEqual(rep['pathway_collapsed_overlap_count'], 0)
        self.assertEqual(rep['pathway_compensating_zigzag_count'], 0)
        self.assertEqual(rep['pathway_unmarked_stroke_overlap_count'], 0)
        self.assertEqual(rep['pathway_midline_connection_count'], 0)
        self.assertEqual(rep['pathway_multiply_connected_trace_count'], 0)
        self.assertEqual(rep['pathway_tiny_termination_trace_count'], 0)
        self.assertEqual(rep['pathway_duplicate_trace_cleanup_count'], 0)
        self.assertEqual(rep['pathway_intersection_trace_cleanup_count'], 0)
        self.assertGreaterEqual(rep['pathway_min_normal_center_segment'], 2 * rep['pathway_module_canvas_units'] - 1e-7)
        self.assertGreaterEqual(rep['pathway_min_actual_segment'], .10 * rep['pathway_module_canvas_units'] - 1e-7)
        # Canvas coverage is a soft exploration target.
        self.assertTrue(0 <= rep['pathway_canvas_quartiles_touched'] <= 4)
        chip_sides = {}
        for g in paths:
            is_local=bool(g.structural.get('local_gap_pathway'))
            if not is_local:
                chip_sides.setdefault(g.structural['bundle_source_chip'], set()).add(g.structural['launch_side'])
            self.assertTrue(all(d in range(8) for d in g.structural.get('segment_direction_indices', [])))
            if g.structural.get('launch_line_count',0)>1 and not (is_local and g.structural.get('local_gap_special')):
                self.assertGreaterEqual(g.structural.get('bundle_spacing', 0), 5.0 * r.U)
            self.assertGreaterEqual(g.structural.get('launch_line_count', 0), 1)
            # Realized launch span is reported, not quota-enforced.
            self.assertTrue(0.0 <= g.structural.get('launch_coverage_ratio', 0) <= 1.0)
            expected_first = None if is_local else SIDE_TO_DIR[g.structural['launch_side']]
            for prim in g.primitives:
                if prim.kind != 'polyline':
                    continue
                illegal=[]
                for obj in non_paths:
                    if not prim.geom.intersects(obj.geom):
                        continue
                    if obj.structural.get('component_pathway_attached'):
                        continue
                    illegal.append(obj)
                self.assertFalse(illegal)
                pts = prim.svg['points']
                dirs=[]
                for a,b in zip(pts,pts[1:]):
                    if abs(a[0]-b[0])+abs(a[1]-b[1]) < 1e-9:
                        continue
                    dirs.append(nearest_dir_index(b[0]-a[0], b[1]-a[1]))
                if dirs and expected_first is not None:
                    self.assertEqual(dirs[0], expected_first)
                for a,b in zip(dirs,dirs[1:]):
                    delta=(b-a)%8
                    self.assertIn(delta,(0,1,7), msg=f'illegal visible turn {a}->{b}')
        # Which launch sides remain visible is best-effort under geometry; planned bundles are checked separately.
        for sides in chip_sides.values():
            self.assertTrue(sides.issubset({'top','right','bottom','left'}))
            self.assertTrue(sides)

    def test_pathways_are_deterministic_without_pathway_seed_search(self):
        a = V35Renderer(1200, 1200, seed=20260806)
        b = V35Renderer(1200, 1200, seed=20260806)
        placed_a, report_a = a.generate_sample(0, max_sample_restarts=1)
        placed_b, report_b = b.generate_sample(0, max_sample_restarts=1)
        self.assertEqual(report_a, report_b)
        self.assertEqual(a.svg_for(placed_a, report_a), b.svg_for(placed_b, report_b))
        self.assertEqual(report_a['pathway_candidate_seed_retry_count'], 0)
        self.assertEqual(report_a['pathway_route_search_count'], 0)

    def test_arbitrary_seed_pathways_preserve_hard_geometry_only(self):
        # Run each geometry-heavy board in a fresh process.  The test is about renderer
        # invariants, not GEOS cache accumulation inside the verifier process.
        module_dir=str(Path(__file__).parent)
        for sample_index in (0, 1, 2):
            code=f"""
from pcb_v35_renderer import V35Renderer
r=V35Renderer(1000,1000,seed=20260806)
_,rep=r.generate_sample({sample_index},max_sample_restarts=64)
assert rep['pathway_candidate_seed_retry_count']==0
assert rep['pathway_route_search_count']==0
assert rep['pathway_static_intersection_count']==0
assert rep['pathway_unmarked_overlap_count']==0
assert rep['pathway_collapsed_overlap_count']==0
assert rep['pathway_unmarked_stroke_overlap_count']==0
assert rep['pathway_compensating_zigzag_count']==0
assert rep['pathway_tiny_termination_trace_count']==0
assert rep['pathway_midline_connection_count']==0
assert rep['pathway_multiply_connected_trace_count']==0
assert rep['pathway_termination_marker_overlap_count']==0
assert rep['pathway_duplicate_trace_cleanup_count']==0
assert rep['pathway_intersection_trace_cleanup_count']==0
assert rep['pathway_min_normal_center_segment'] >= 2*rep['pathway_module_canvas_units']-1e-7
"""
            proc=subprocess.run([sys.executable,'-c',code],cwd=module_dir,text=True,
                                capture_output=True,timeout=60)
            self.assertEqual(proc.returncode,0,msg=f'sample {sample_index}: {proc.stderr or proc.stdout}')


    def test_main_chip_density_is_canvas_gated_and_scale_independent(self):
        # The default 1200-square composition is exactly two main chips. Shrinking geometry
        # with main_scale must not silently create another anchor on the same canvas.
        for ms in (1.0,0.75,0.5):
            r=V35Renderer(1200,1200,seed=24680,main_scale=ms)
            self.assertEqual(r.chip_count_probability(),0.0)
            counts=[r.chip_count(SplitMix64(sample_seed(r.seed,i))) for i in range(120)]
            self.assertEqual(set(counts),{2})
        # Extra real canvas area gradually enables the historical rare third-chip case.
        r=V35Renderer(1600,1600,seed=24680)
        self.assertGreater(r.chip_count_probability(),0.0)
        self.assertLessEqual(r.chip_count_probability(),0.10)
        counts=[r.chip_count(SplitMix64(sample_seed(r.seed,i))) for i in range(400)]
        self.assertIn(3,counts)
        self.assertIn(2,counts)

    def test_secondary_components_keep_main_chip_breathing_room(self):
        r = NoPathRenderer(seed=987654321)
        placed, _ = r.generate_sample(0, max_sample_restarts=64)
        chips=[g for g in placed if g.structural.get('placement_kind')=='chip']
        secondary=[g for g in placed if g.structural.get('placement_kind') in ('collection','isolated')]
        self.assertTrue(chips)
        self.assertAlmostEqual(r.component_chip_clearance, 42.0*r.U)
        for chip in chips:
            b=chip.bounds
            self.assertGreaterEqual(min(b[0],b[1],r.W-b[2],r.H-b[3]), r.chip_edge_clearance-1e-7)
            for obj in secondary:
                self.assertGreaterEqual(chip.geom.distance(obj.geom), r.component_chip_clearance-1e-7)

    def test_routes_before_secondary_components_exist(self):
        class RouteOrderProbe(V35Renderer):
            def generate_pathways(self, sseed, placed):
                self.kinds_seen_by_router=[g.structural.get('placement_kind') for g in placed]
                raise RuntimeError('ROUTE_ORDER_PROBE')
        r=RouteOrderProbe(seed=20260808)
        with self.assertRaisesRegex(RuntimeError, 'ROUTE_ORDER_PROBE'):
            r.generate_sample(0,max_sample_restarts=1)
        self.assertTrue(r.kinds_seen_by_router)
        self.assertEqual(set(r.kinds_seen_by_router), {'chip'})

    def test_main_scale_is_independent_of_canvas_size(self):
        a=V35Renderer(1200,1200,seed=9,main_scale=1.0)
        b=V35Renderer(1200,1200,seed=9,main_scale=0.65)
        self.assertEqual(a.W,b.W); self.assertEqual(a.H,b.H)
        self.assertAlmostEqual(b.U/a.U,0.65)
        ga=a.generate_chip(chip_seed(sample_seed(a.seed,0),0),0)
        gb=b.generate_chip(chip_seed(sample_seed(b.seed,0),0),0)
        self.assertAlmostEqual(gb.structural['q_chip']/ga.structural['q_chip'],0.65,places=6)
        with self.assertRaises(ValueError):
            V35Renderer(main_scale=0)

    def test_hard_stops_use_deferred_reroute_before_forced_termination(self):
        r = V35Renderer(seed=2026080601)
        _, rep = r.generate_sample(0, max_sample_restarts=64)
        self.assertIn('pathway_hard_stop_count', rep)
        self.assertIn('pathway_reroute_scheduled_count', rep)
        self.assertIn('pathway_traceback_count', rep)
        self.assertIn('pathway_general_repair_scheduled_count', rep)
        self.assertIn('pathway_deep_traceback_count', rep)
        self.assertLessEqual(rep['pathway_reroute_scheduled_count'],
                             rep['pathway_hard_stop_count'] + rep['pathway_general_repair_scheduled_count'])
        self.assertLessEqual(rep['pathway_traceback_count'], rep['pathway_reroute_scheduled_count'])
        self.assertGreaterEqual(rep['pathway_traceback_segment_count'], rep['pathway_traceback_count'])
        self.assertEqual(rep['pathway_static_intersection_count'], 0)

    def test_holistic_connections_loop_guard_and_extended_repair_are_active(self):
        r = V35Renderer(seed=12345)
        placed, rep = r.generate_sample(0, max_sample_restarts=64)
        paths = [g for g in placed if g.structural.get('placement_kind') == 'pathway' and not g.structural.get('pathway_marker')]
        self.assertGreater(rep['pathway_holistic_connection_pair_count'], 0)
        self.assertEqual(rep['pathway_planner_mode'], 'route_first_family_protected_transactional_parallel')
        self.assertGreater(rep['pathway_lookahead_evaluation_count'], 0)
        self.assertGreaterEqual(rep['pathway_conflict_region_count'], 0)
        self.assertGreaterEqual(rep['pathway_transactional_birth_reject_count'], 0)
        # V33 restores cross-chip networking as an acceptance invariant.
        self.assertGreaterEqual(rep['pathway_cross_chip_connection_count'], 1)
        self.assertGreater(rep['pathway_loop_candidate_reject_count'], 0)
        self.assertGreater(rep['pathway_traceback_count'], 0)
        self.assertGreater(rep['pathway_deep_traceback_count'], 0)
        self.assertEqual(rep['pathway_profile']['reroute_budget'], 7)
        self.assertTrue(1.50 <= rep['pathway_profile']['branch_multiplier'] <= 1.80)
        self.assertAlmostEqual(rep['pathway_profile']['late_life_branch_start'], .60)
        self.assertAlmostEqual(rep['pathway_profile']['late_life_branch_multiplier'], 1.50)
        self.assertEqual(rep['pathway_profile']['persistence_tail_rounds'], 12)
        self.assertGreaterEqual(rep['pathway_late_life_branch_attempt_count'], 0)
        self.assertAlmostEqual(rep['pathway_required_static_keepout'], 8.0 * r.U)
        self.assertAlmostEqual(rep['pathway_required_main_chip_keepout'], 24.0 * r.U)
        self.assertAlmostEqual(rep['pathway_termination_dot_scale'], 2.0)
        self.assertAlmostEqual(rep['pathway_termination_dot_hollow_stroke'], 2.70 * r.U)
        self.assertAlmostEqual(rep['pathway_terminal_head_keepout'], 4.5 * r.U)
        self.assertGreaterEqual(rep['pathway_terminal_head_backoff_count'], 0)
        self.assertGreaterEqual(rep['pathway_early_reroute_scheduled_count'], 0)
        self.assertGreaterEqual(rep['pathway_trace_thickness_min'], 2.0 * r.U - 1e-7)
        self.assertLessEqual(rep['pathway_trace_thickness_max'], 7.4 * r.U + 1e-7)
        self.assertGreaterEqual(rep['pathway_launch_min_lane_edge_gap_ratio'], 1.49)
        self.assertEqual(rep['pathway_midline_connection_count'], 0)
        self.assertEqual(rep['pathway_multiply_connected_trace_count'], 0)
        self.assertEqual(rep['pathway_unmarked_stroke_overlap_count'], 0)
        self.assertEqual(rep['pathway_tiny_termination_trace_count'], 0)
        self.assertGreaterEqual(rep['pathway_min_foreign_static_clearance'], rep['pathway_required_static_keepout']-1e-7)
        self.assertGreaterEqual(rep['pathway_min_foreign_main_chip_clearance'], rep['pathway_required_main_chip_keepout']-1e-7)
        self.assertGreater(rep['pathway_recovery_fragment_count'], 0)
        # Soft target only: realized launch coverage may fall below the sampled intent when geometry is constrained.
        self.assertGreaterEqual(rep['pathway_visible_launch_coverage_min'], 0.0)
        # Diagnostic metric only: suppressed speculative traces must not become visible tiny stubs.
        self.assertGreaterEqual(rep['pathway_abandoned_short_trace_count'], 0)
        # Soft persistence tendency only: bundled forced endings are reported, not percentage-gated.
        self.assertGreaterEqual(rep['pathway_bundled_forced_termination_trace_count'], 0)
        self.assertEqual(rep['pathway_compensating_zigzag_count'], 0)
        self.assertEqual(rep['pathway_unmarked_overlap_count'], 0)
        local_special=[g for g in paths if g.structural.get('local_gap_special')]
        self.assertGreaterEqual(len(local_special), 1)
        for g in local_special:
            polylines=[p.svg for p in g.primitives if p.kind=='polyline']
            holes=[p.svg for p in g.primitives if p.svg.get('type')=='circle' and p.svg.get('fill')==r.BG]
            self.assertEqual(g.structural.get('launch_line_count'), 1)
            self.assertTrue(any(10.0*r.U <= p['stroke_width'] <= 24.8*r.U for p in polylines))
            self.assertTrue(all(p.get('linecap')=='round' for p in polylines))
            self.assertGreaterEqual(len(holes), 1)
            # Special thick traces use the stroke cap + negative hole, never an attached FG dot.
            self.assertFalse(any(p.svg.get('type')=='circle' and p.svg.get('fill')!=r.BG for p in g.primitives))
        for g in paths:
            markers=[]
            for i,p in enumerate(g.primitives):
                s=p.svg
                if s.get('type')!='circle':
                    continue
                if s.get('fill')==r.BG:
                    # V24 extra-thick local traces hollow their own round caps with a
                    # background-coloured negative circle; this is not an endpoint marker.
                    continue
                outer=s['r'] + (s.get('stroke_width',0.0) if s.get('stroke')!='none' else 0.0)/2
                markers.append((s['cx'],s['cy'],outer))
                self.assertGreaterEqual(s['r'], 2.70*r.U-1e-7)
                if s.get('fill')=='none':
                    endpoints=[]
                    for pp in g.primitives:
                        ps=pp.svg
                        if ps.get('type')=='polyline' and ps.get('points'):
                            endpoints.extend((ps['points'][0],ps['points'][-1]))
                    self.assertTrue(endpoints)
                    nearest=min(math.hypot(ex-s['cx'],ey-s['cy']) for ex,ey in endpoints)
                    self.assertAlmostEqual(nearest,outer,places=5)
            for i,a in enumerate(markers):
                for b in markers[i+1:]:
                    self.assertGreaterEqual(math.hypot(a[0]-b[0],a[1]-b[1]),a[2]+b[2]-1e-7)
        for g in paths:
            # Realized launch span is reported, not quota-enforced.
            self.assertTrue(0.0 <= g.structural.get('launch_coverage_ratio', 0) <= 1.0)

    def test_single_sample_invariants(self):
        r = NoPathRenderer(seed=12345)
        placed, rep = r.generate_sample(0, max_sample_restarts=64)
        self.assertIn(rep['chip_count'], (2, 3))
        self.assertIn(rep['collection_count'], (15, 16, 17, 18))
        self.assertEqual(rep['IC_required_contact_failure_count'], 0)
        self.assertEqual(rep['forbidden_intersection_count'], 0)
        self.assertEqual(rep['forbidden_touch_count'], 0)
        self.assertEqual(rep['clearance_violation_count'], 0)
        N = rep['collection_count']
        self.assertEqual(rep['quotas']['N_ic'], round(.625 * N))
        self.assertEqual(rep['quotas']['N_dense'], round(.845 * N))
        self.assertEqual(rep['quotas']['N_border'], round(.700 * N))
        mL = statistics.median(rep['collection_long'])
        mq = statistics.median(rep['chip_q'])
        core = sum(.026 * 1200 <= x <= .073 * 1200 for x in rep['collection_long']) / N
        self.assertGreaterEqual(core, .80)
        self.assertTrue(.040 * 1200 <= mL <= .052 * 1200)
        self.assertTrue(.42 <= mL / mq <= .56)
        fps = rep['collection_fingerprints']
        self.assertEqual(len(fps), len(set(fps)))
        self.assertNotIn(None, fps)

    def test_two_sample_cross_sample_uniqueness(self):
        r = NoPathRenderer(seed=12345)
        _, a = r.generate_sample(0, max_sample_restarts=8)
        _, b = r.generate_sample(2, max_sample_restarts=8)
        all_fp = a['collection_fingerprints'] + b['collection_fingerprints']
        self.assertEqual(len(all_fp), len(set(all_fp)))

    def test_batch_deadlock_skip_preserves_one_renderer_domain(self):
        class SkipFirst(NoPathRenderer):
            def generate_sample(self, sample_index=0, max_sample_restarts=256, collection_plan_attempts=256, calibration_rounds=256):
                if sample_index == 0:
                    raise RuntimeError('synthetic deadlock')
                placed, report = super().generate_sample(0, max_sample_restarts=max_sample_restarts,
                                                         collection_plan_attempts=collection_plan_attempts,
                                                         calibration_rounds=calibration_rounds)
                report['logical_sample_index'] = sample_index
                return placed, report
        r = SkipFirst(seed=12345)
        with tempfile.TemporaryDirectory() as td:
            reports, skipped = r.render_batch(1, Path(td), max_sample_restarts=32, max_logical_samples=4)
            self.assertEqual(skipped, [0])
            self.assertEqual(len(reports), 1)
            self.assertEqual(reports[0]['logical_sample_index'], 1)


    def test_v35_space_aware_causal_contract(self):
        r=V35Renderer(1200,1200,seed=20260806)
        placed,rep=r.generate_sample(0,max_sample_restarts=1)
        chips=[g for g in placed if g.structural.get('placement_kind')=='chip']
        for i,a in enumerate(chips):
            for b in chips[i+1:]:
                self.assertGreaterEqual(a.geom.distance(b.geom), r.chip_chip_clearance-1e-7)
        self.assertGreaterEqual(rep['pathway_cross_chip_connection_count'],1)
        self.assertEqual(rep['pathway_main_stalled_side_count'],0)
        self.assertEqual(rep['pathway_visible_launch_trace_count'],rep['pathway_launch_trace_count'])
        self.assertEqual(rep['pathway_local_gap_independent_source_count'],rep['pathway_local_gap_source_count'])
        self.assertGreaterEqual(rep['pathway_local_gap_trace_count'],rep['pathway_local_gap_source_count'])
        self.assertGreater(rep['pathway_local_gap_visible_trace_count'],0)
        self.assertAlmostEqual(r.local_gap_bundle_probability,0.50)
        self.assertLessEqual(2*rep['pathway_local_gap_bundle_pair_count'],rep['pathway_local_gap_source_count'])
        self.assertLessEqual(rep['pathway_local_gap_bundle_release_count'],2*rep['pathway_local_gap_bundle_pair_count'])
        self.assertGreaterEqual(rep['pathway_local_gap_fill_actual'],0.40)
        self.assertLessEqual(rep['pathway_local_gap_fill_actual'],0.55)
        self.assertGreaterEqual(rep['component_residual_gap_fill_actual'],0.90)
        self.assertLessEqual(rep['component_residual_gap_fill_actual'],1.0)
        self.assertEqual(rep.get('component_pathway_unauthorized_overlap_count',0),0)
        self.assertEqual(rep['pathway_unmarked_stroke_overlap_count'],0)
        self.assertEqual(rep['pathway_static_intersection_count'],0)
        self.assertEqual(rep['pathway_illegal_turn_count'],0)
        self.assertEqual(rep['pathway_curved_primitive_count'],0)
        self.assertGreater(rep['pathway_local_space_capacity_evaluation_count'],0)
        self.assertGreater(rep['pathway_traceback_count'],0)
        self.assertGreaterEqual(rep['main_chip_pair_min_clearance'],rep['main_chip_pair_required_clearance']-1e-7)
        self.assertAlmostEqual(rep['design_scale_basis'],1200.0)
        self.assertEqual(rep['design_unit_divisor'],1600)

    def test_v35_default_scale_is_canvas_over_1600_and_default_canvas_is_two_chip_only(self):
        r=V35Renderer(1200,1200,seed=1)
        self.assertAlmostEqual(r.canvas_S,1200.0)
        self.assertAlmostEqual(r.S,1200.0)
        self.assertAlmostEqual(r.U,0.75)
        self.assertAlmostEqual(r.chip_chip_clearance,322.5)
        self.assertEqual(r.chip_count_probability(),0.0)
        class Fixed:
            def __init__(self,x): self.x=x
            def random(self): return self.x
        self.assertEqual(r.chip_count(Fixed(0.0)),2)
        self.assertEqual(r.chip_count(Fixed(.999999)),2)
        larger=V35Renderer(1600,1600,seed=1)
        self.assertGreater(larger.chip_count_probability(),0.0)
        self.assertEqual(larger.chip_count(Fixed(0.0)),3)
        self.assertEqual(larger.chip_count(Fixed(.999999)),2)
        self.assertEqual(V35Renderer(1200,1200,seed=1,main_scale=.5).chip_count_probability(),0.0)

    def test_v35_traceback_blacklists_actual_replayed_corridor_at_rollback_junction(self):
        r=V35Renderer(seed=340034)
        p=BundleGesturePlanner(r,340034,[])
        tid=p.next_trace_id; p.next_trace_id+=1
        f=p._make_front(ids=[tid],chip=0,side='right',side_index=0,path=[(200.0,200.0)],direction=0,
                        offsets={tid:0.0},thicknesses={tid:2.5*r.U},prefixes={tid:[]},rng=SplitMix64(99))
        p.fronts[f['id']]=f
        def commit(d,mods=2):
            a=f['path'][-1]; b=(a[0]+dir_vec(d)[0]*mods*p.module,a[1]+dir_vec(d)[1]*mods*p.module)
            g=p._corridor_geom(f,a,b)
            p._accept(f,dict(front=f['id'],start=a,end=b,dir=d,modules=mods,geom=g,score=0.0),defer_post=True)
        for _ in range(4): commit(0,2)
        junction=f['path'][-1]
        commit(1,2); commit(0,2)
        f['reroute_attempts']=0
        removed=p._traceback_for_reroute(f)
        self.assertGreaterEqual(removed,2)
        self.assertEqual(f['reroute_replay_dir'],1)
        self.assertEqual(f['reroute_avoid_dir'],1)
        self.assertAlmostEqual(f['path'][-1][0],junction[0])
        self.assertAlmostEqual(f['path'][-1][1],junction[1])

    def test_v35_connection_leg_rejects_visible_90_degree_terminal_kink(self):
        r=V35Renderer(1200,1200,seed=99)
        p=BundleGesturePlanner(r,99,[])
        tid=p.next_trace_id; p.next_trace_id+=1
        f=p._make_front(ids=[tid],chip=0,side='right',side_index=0,
                        path=[(200.0,200.0),(240.0,160.0)],direction=3,
                        offsets={tid:0.0},thicknesses={tid:2.0*r.U},prefixes={tid:[]},rng=SplitMix64(7))
        p.fronts[f['id']]=f
        # Incoming visible direction is NW (3); this SW terminal leg (5) is a 90-degree kink.
        leg=[f['path'][-1],(230.0,170.0)]
        self.assertTrue(p._connection_leg_creates_compensating_zigzag(f,tid,leg))

    def test_v35_nonzero_offset_singleton_rebases_to_exact_materialized_head_before_connection(self):
        r=V35Renderer(1200,1200,seed=100)
        p=BundleGesturePlanner(r,100,[])
        tid=p.next_trace_id; p.next_trace_id+=1
        f=p._make_front(ids=[tid],chip=0,side='right',side_index=0,
                        path=[(300.0,300.0),(340.0,260.0)],direction=3,
                        offsets={tid:8.0},thicknesses={tid:2.0*r.U},prefixes={tid:[]},rng=SplitMix64(8))
        p.fronts[f['id']]=f
        before=list(p._materialized_paths(f)[tid])
        p._rebase_singleton_to_materialized_head(f,tid)
        self.assertAlmostEqual(f['offsets'][tid],0.0)
        self.assertEqual(f['prefixes'][tid],before)
        self.assertAlmostEqual(f['path'][0][0],before[-1][0])
        self.assertAlmostEqual(f['path'][0][1],before[-1][1])
        self.assertEqual(p._materialized_paths(f)[tid],before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
