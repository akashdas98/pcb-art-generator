import math
import json
import statistics
import gc
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pcb_v40_renderer import V40Renderer, BundleGesturePlanner, SplitMix64, sample_seed, chip_seed, placement_seed, retry_seed, nearest_dir_index, exact_dir8_index, SIDE_TO_DIR, dir_vec, Group, prim_rect_fill

class V40RendererTests(unittest.TestCase):
    @classmethod
    def _reference_report(cls):
        """Accepted V39 production snapshot, valid for V40 only because V40 is behavior-equivalent."""
        root=Path(__file__).resolve().parents[2]
        return json.loads((root/'examples'/'V39_REFERENCE_REPORT.json').read_text())

    def _prepare_component_templates(self,r,sample_index):
        """Prepare the current non-spatial component population without routing.

        This is the correct fixture for component grammar, scale and fingerprint contracts.
        It follows the same Phase-A/template code used by generate_sample, but deliberately
        stops before main routing and residual-fill acceptance.
        """
        sseed=sample_seed(r.seed,sample_index); srng=SplitMix64(sseed)
        nc=r.chip_count(srng); N=r.collection_count(srng)
        assigns,quotas=r.assign_collection_families(srng,N)
        if assigns is None:
            return None
        chips=[]; sigs=set()
        for j in range(nc):
            base=chip_seed(sseed,j); found=None
            for rr in range(128):
                try:
                    g=r.generate_chip(retry_seed(base,rr) if rr else base,j)
                except RuntimeError:
                    continue
                sig=(g.structural.get('orientation'),g.structural.get('aspect_bin'),g.structural.get('motifs'),
                     g.structural.get('inner_border_count'),g.structural.get('exterior_side_set_configuration'))
                if sig not in sigs:
                    found=g; sigs.add(sig); break
            if found is None:
                return None
            chips.append(found)
        placed_chips=r.place_objects(chips,[],[],SplitMix64(placement_seed(sseed)))
        if placed_chips is None:
            return None
        population=None
        for pa in range(3):
            population=r._prepare_component_population_once(sseed,placed_chips,assigns,quotas,128,96,pa)
            if population is not None:
                break
        if population is None:
            return None
        return dict(sseed=sseed,nc=nc,N=N,assigns=assigns,quotas=quotas,chips=placed_chips,population=population)

    def _planner_front(self, planner, fid_seed, start, direction, chip=0):
        tid=planner.next_trace_id; planner.next_trace_id += 1
        return planner._make_front(ids=[tid], chip=chip, side='right', side_index=0,
                                   path=[start], direction=direction, offsets={tid:0.0},
                                   thicknesses={tid:3.0*planner.U}, prefixes={tid:[]},
                                   rng=SplitMix64(fid_seed))

    def test_root_main_launch_can_trace_back_to_emergence_anchor(self):
        r=V40Renderer(seed=31001)
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
        r=V40Renderer(seed=31002)
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
        r=V40Renderer(seed=31003)
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
        r=V40Renderer(seed=31004)
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
        r=V40Renderer(seed=seed)
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
        r=V40Renderer(seed=32006)
        planner=BundleGesturePlanner(r, sample_seed(r.seed,0), [])
        pts=[(100.0,100.0),(-10.0,100.0),(-10.0,220.0)]
        clipped=planner._clip_escaped_polyline_to_frame(pts)
        self.assertEqual(len(clipped),2)
        self.assertAlmostEqual(clipped[-1][0],0.0,places=6)
        self.assertAlmostEqual(clipped[-1][1],100.0,places=6)

    def test_component_fallback_reuses_precomputed_route_keepout(self):
        r = V40Renderer(seed=9090)
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
        class ComponentFailureRenderer(V40Renderer):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.route_calls = 0
            def generate_main_pathways(self, sseed, placed):
                self.route_calls += 1
                return [], {'pathway_planner_mode':'route_first_family_protected_transactional_parallel'}
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
        r = V40Renderer(seed=777)
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
        r = V40Renderer(seed=1)
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
        r = V40Renderer(seed=222)
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
        r = V40Renderer(seed=999)
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
        r = V40Renderer(seed=333)
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
        r = V40Renderer(seed=444)
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
        r = V40Renderer(seed=445)
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
        src = (Path(__file__).resolve().parents[2] / 'pcb_v40_renderer.py').read_text()
        self.assertNotIn('shape=rng.weighted([((1,2)', src)
        self.assertNotIn('dims=rng.weighted([((1,4)', src)
        self.assertIn('_procedural_dims(', src)

    def test_bundle_gesture_pathways_are_direct_modular_and_collision_clean(self):
        rep=self._reference_report(); r=V40Renderer(1200,1200,seed=rep['base_seed'])
        self.assertEqual(rep['pathway_planner_mode'],'route_first_family_protected_transactional_parallel')
        self.assertEqual(rep['generation_order'],'main_chips -> primary_pathways -> residual_components_50_60 -> local_gap_pathways_80_90_of_remaining')
        self.assertEqual(rep['component_placement_mode'],'post_main_pre_local_residual_gap_fill')
        self.assertGreaterEqual(rep['pathway_bundle_count'],rep['chip_count']*4)
        self.assertGreater(rep['pathway_launch_trace_count'],0)
        self.assertGreater(rep['pathway_split_count'],0)
        self.assertGreaterEqual(rep['pathway_cross_chip_connection_count'],1)
        self.assertEqual(rep['pathway_cross_chip_connected_trace_count'],2*rep['pathway_cross_chip_connection_count'])
        self.assertEqual(rep['pathway_connection_count'],rep['pathway_cross_chip_connection_count'])
        self.assertGreater(rep['pathway_decision_round_count'],1)
        self.assertGreaterEqual(rep['pathway_rounds_with_multiple_fronts'],.90*rep['pathway_decision_round_count'])
        self.assertEqual(rep['pathway_static_intersection_count'],0)
        self.assertEqual(rep['pathway_unmarked_overlap_count'],0)
        self.assertEqual(rep['pathway_collapsed_overlap_count'],0)
        self.assertEqual(rep['pathway_unmarked_stroke_overlap_count'],0)
        self.assertEqual(rep['pathway_compensating_zigzag_count'],0)
        self.assertEqual(rep['pathway_tiny_termination_trace_count'],0)
        self.assertEqual(rep['pathway_midline_connection_count'],0)
        self.assertEqual(rep['pathway_multiply_connected_trace_count'],0)
        self.assertGreaterEqual(rep['pathway_min_normal_center_segment'],2*rep['pathway_module_canvas_units']-1e-7)
        self.assertGreaterEqual(rep['pathway_min_actual_segment'],.10*rep['pathway_module_canvas_units']-1e-7)
        self.assertAlmostEqual(rep['pathway_chip_launch_gap'],22.5*r.U)
        self.assertGreaterEqual(rep['pathway_source_marker_count'],rep['pathway_visible_launch_trace_count'])
        self.assertEqual(rep['pathway_illegal_turn_count'],0)
        self.assertEqual(rep['pathway_non_octilinear_segment_count'],0)
        self.assertEqual(rep['pathway_illegal_connection_junction_turn_count'],0)
        self.assertEqual(rep['pathway_unmarked_clearance_violation_count'],0)

    def test_pathways_are_deterministic_without_pathway_seed_search(self):
        a=V40Renderer(1200,1200,seed=20260806); b=V40Renderer(1200,1200,seed=20260806)
        sa=sample_seed(a.seed,0); sb=sample_seed(b.seed,0)
        self.assertEqual(sa,sb)
        ca=a.generate_chip(chip_seed(sa,0),0); cb=b.generate_chip(chip_seed(sb,0),0)
        self.assertEqual(ca.structural,cb.structural)
        self.assertEqual([p.svg for p in ca.primitives],[p.svg for p in cb.primitives])
        pa=BundleGesturePlanner(a,sa,[]); pb=BundleGesturePlanner(b,sb,[])
        fa=self._planner_front(pa,41001,(300.0,300.0),0,chip=0)
        fb=self._planner_front(pb,41001,(300.0,300.0),0,chip=0)
        for f in (fa,fb):
            f['launch_egress_pending']=False; f['gestures']=2; f['local_gestures']=2; f['intent']='explore'
        va=pa._propose(fa); vb=pb._propose(fb)
        key=lambda x:(x['dir'],x['modules'],tuple(round(v,8) for v in x['end']),round(x['score'],8))
        self.assertEqual(key(va),key(vb))
        self.assertEqual(pa.stats['pathway_candidate_seed_retry_count'],0)
        self.assertEqual(pa.stats['pathway_route_search_count'],0)

    def test_main_chip_density_is_canvas_gated_and_scale_independent(self):
        # The default 1200-square composition is exactly two main chips. Shrinking geometry
        # with main_scale must not silently create another anchor on the same canvas.
        for ms in (1.0,0.75,0.5):
            r=V40Renderer(1200,1200,seed=24680,main_scale=ms)
            self.assertEqual(r.chip_count_probability(),0.0)
            counts=[r.chip_count(SplitMix64(sample_seed(r.seed,i))) for i in range(120)]
            self.assertEqual(set(counts),{2})
        # Extra real canvas area gradually enables the historical rare third-chip case.
        r=V40Renderer(1600,1600,seed=24680)
        self.assertGreater(r.chip_count_probability(),0.0)
        self.assertLessEqual(r.chip_count_probability(),0.10)
        counts=[r.chip_count(SplitMix64(sample_seed(r.seed,i))) for i in range(400)]
        self.assertIn(3,counts)
        self.assertIn(2,counts)

    def test_secondary_components_keep_main_chip_breathing_room(self):
        r=V40Renderer(1200,1200,seed=40001)
        U=r.U
        chip=Group('chip-fixture',[prim_rect_fill(600,600,120*U,100*U,0,r.FG)],
                   {'placement_kind':'chip','q_chip':100*U})
        comp_template=Group('component-fixture',[prim_rect_fill(0,0,20*U,20*U,0,r.FG)],
                            {'placement_kind':'collection','families':('square',),'border':False,'subgroups':[]})
        chip_right=chip.bounds[2]
        near=comp_template.transformed(chip_right+10*U+0.50*r.component_chip_clearance,600)
        near.structural['placement_kind']='collection'
        far=comp_template.transformed(chip_right+10*U+r.component_chip_clearance+2*U,600)
        far.structural['placement_kind']='collection'
        self.assertAlmostEqual(r.component_chip_clearance,42.0*U)
        self.assertFalse(r._component_candidate_valid(near,'collection',[chip],[],[]))
        self.assertTrue(r._component_candidate_valid(far,'collection',[chip],[],[]))
        self.assertLess(chip.geom.distance(near.geom),r.component_chip_clearance)
        self.assertGreaterEqual(chip.geom.distance(far.geom),r.component_chip_clearance-1e-7)

    def test_routes_before_secondary_components_exist(self):
        class RouteOrderProbe(V40Renderer):
            def generate_main_pathways(self, sseed, placed):
                self.kinds_seen_by_router=[g.structural.get('placement_kind') for g in placed]
                raise RuntimeError('ROUTE_ORDER_PROBE')
        r=RouteOrderProbe(seed=20260808)
        with self.assertRaisesRegex(RuntimeError, 'ROUTE_ORDER_PROBE'):
            r.generate_sample(0,max_sample_restarts=1)
        self.assertTrue(r.kinds_seen_by_router)
        self.assertEqual(set(r.kinds_seen_by_router), {'chip'})

    def test_main_scale_is_independent_of_canvas_size(self):
        a=V40Renderer(1200,1200,seed=9,main_scale=1.0)
        b=V40Renderer(1200,1200,seed=9,main_scale=0.65)
        self.assertEqual(a.W,b.W); self.assertEqual(a.H,b.H)
        self.assertAlmostEqual(b.U/a.U,0.65)
        ga=a.generate_chip(chip_seed(sample_seed(a.seed,0),0),0)
        gb=b.generate_chip(chip_seed(sample_seed(b.seed,0),0),0)
        self.assertAlmostEqual(gb.structural['q_chip']/ga.structural['q_chip'],0.65,places=6)
        with self.assertRaises(ValueError):
            V40Renderer(main_scale=0)

    def test_hard_stops_use_deferred_reroute_before_forced_termination(self):
        r=V40Renderer(seed=40002)
        planner=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        f=self._planner_front(planner,40003,(220.0,220.0),0,chip=0)
        # Materialize enough real route history to exercise the current recovery policy.
        for _ in range(4):
            startp=f['path'][-1]; endp=(startp[0]+2*planner.module,startp[1])
            geom=planner._corridor_geom(f,startp,endp)
            planner._accept(f,dict(front=f['id'],start=startp,end=endp,dir=0,modules=2,geom=geom,score=1.0),defer_post=True)
        before_segments=len(f['path'])-1
        f['reroute_attempts']=1
        self.assertTrue(planner._schedule_reroute(f,round_index=10,reason='hard_stop'))
        self.assertEqual(f['status'],'active')
        self.assertTrue(f['reroute_pending'])
        self.assertEqual(planner.stats['pathway_reroute_scheduled_count'],1)
        self.assertEqual(planner.stats['pathway_termination_count'],0)
        rewound=planner._traceback_for_reroute(f)
        self.assertGreaterEqual(rewound,3)
        self.assertLess(len(f['path'])-1,before_segments)
        self.assertGreaterEqual(planner.stats['pathway_traceback_segment_count'],rewound)
        self.assertGreaterEqual(planner.stats['pathway_deep_traceback_count'],1)
        # Only an exhausted recovery budget may make the scheduler refuse another reroute.
        f['reroute_pending']=False
        f['reroute_attempts']=planner.profile['reroute_budget']
        self.assertFalse(planner._schedule_reroute(f,round_index=20,reason='hard_stop'))
        self.assertGreaterEqual(planner.stats['pathway_reroute_exhausted_count'],1)

    def test_holistic_connections_loop_guard_and_extended_repair_are_active(self):
        rep=self._reference_report(); r=V40Renderer(1200,1200,seed=rep['base_seed'])
        self.assertGreater(rep['pathway_holistic_connection_pair_count'],0)
        self.assertGreater(rep['pathway_lookahead_evaluation_count'],0)
        self.assertGreater(rep['pathway_loop_candidate_reject_count'],0)
        self.assertGreater(rep['pathway_traceback_count'],0)
        self.assertGreater(rep['pathway_deep_traceback_count'],0)
        self.assertGreater(rep['pathway_recovery_fragment_count'],0)
        self.assertEqual(rep['pathway_profile']['reroute_budget'],7)
        self.assertAlmostEqual(rep['pathway_profile']['late_life_branch_start'],.60)
        self.assertAlmostEqual(rep['pathway_profile']['late_life_branch_multiplier'],1.50)
        self.assertEqual(rep['pathway_profile']['persistence_tail_rounds'],12)
        self.assertEqual(rep['pathway_compensating_zigzag_count'],0)
        # Bounded live checks: holistic pairing and loop guard are exercised directly.
        p=BundleGesturePlanner(r,sample_seed(r.seed,99),[])
        a=self._planner_front(p,42001,(300.0,400.0),0,chip=0)
        b=self._planner_front(p,42002,(300.0+3*p.module,400.0),4,chip=1)
        for f in (a,b):
            f['gestures']=2; f['local_gestures']=2; f['launch_egress_pending']=False; f['intent']='connect'; f['travel']=5*p.module
        self.assertEqual(p._assign_round_connection_targets([a,b],1),1)
        self.assertEqual(a['round_connection_peer'],b['id'])
        a['gestures']=4; a['initial_dir']=0
        self.assertTrue(p._candidate_loop_risk(a,4,(a['path'][-1][0]-2*p.module,a['path'][-1][1])))

    def test_single_sample_invariants(self):
        r=V40Renderer(seed=20260806)
        prep=self._prepare_component_templates(r,0)
        self.assertIsNotNone(prep)
        N=prep['N']; quotas=prep['quotas']; chips=prep['chips']
        cols,_caps,pending=prep['population']
        self.assertEqual(len(cols),N)
        self.assertEqual(N,18)
        self.assertEqual(quotas['N_ic'],round(.625*N))
        self.assertEqual(quotas['N_dense'],round(.845*N))
        self.assertEqual(quotas['N_border'],round(.700*N))
        self.assertEqual(r._validate_component_templates(cols,chips,quotas),[])
        L=[max(g.bounds[2]-g.bounds[0],g.bounds[3]-g.bounds[1]) for g in cols]
        q=[g.structural['q_chip'] for g in chips]
        mL=statistics.median(L); mq=statistics.median(q)
        core=sum(.026*r.S <= x <= .073*r.S for x in L)/N
        self.assertGreaterEqual(core,.80)
        self.assertTrue(.040*r.S <= mL <= .052*r.S)
        self.assertTrue(.42 <= mL/mq <= .56)
        fps=[fp for fp,_rec,_g in pending]
        self.assertEqual(len(fps),len(set(fps)))
        self.assertNotIn(None,fps)

    def test_two_sample_cross_sample_uniqueness(self):
        r=V40Renderer(seed=20260806)
        first=self._prepare_component_templates(r,0)
        self.assertIsNotNone(first)
        first_pending=first['population'][2]
        first_fp={fp for fp,_rec,_g in first_pending}
        for fp,rec,_g in first_pending:
            r.batch_fingerprints.add(fp); r.register_record(rec)
        # sample 1 may legitimately fail cheap template preparation; sample 2 is the maintained
        # deterministic second contract population for this seed/domain.
        second=self._prepare_component_templates(r,2)
        self.assertIsNotNone(second)
        second_pending=second['population'][2]
        second_fp={fp for fp,_rec,_g in second_pending}
        self.assertEqual(len(second_fp),len(second_pending))
        self.assertTrue(first_fp.isdisjoint(second_fp))

    def test_batch_deadlock_skip_preserves_one_renderer_domain(self):
        class SkipFirst(V40Renderer):
            def __init__(self,*args,**kwargs):
                super().__init__(*args,**kwargs); self.calls=[]
            def generate_sample(self,sample_index=0,**kwargs):
                self.calls.append(sample_index)
                if sample_index==0:
                    raise RuntimeError('synthetic deadlock')
                return [],dict(seed=sample_seed(self.seed,sample_index),base_seed=self.seed,
                               logical_sample_index=sample_index,renderer_identity=id(self))
            def svg_for(self,placed,report):
                return '<svg xmlns="http://www.w3.org/2000/svg"/>'
        r=SkipFirst(seed=12345)
        with tempfile.TemporaryDirectory() as td:
            reports,skipped=r.render_batch(1,Path(td),max_sample_restarts=1,max_logical_samples=4)
            self.assertEqual(skipped,[0])
            self.assertEqual(r.calls,[0,1])
            self.assertEqual(len(reports),1)
            self.assertEqual(reports[0]['logical_sample_index'],1)
            self.assertEqual(reports[0]['base_seed'],r.seed)
            self.assertEqual(reports[0]['renderer_identity'],id(r))

    def test_v38_space_aware_causal_contract(self):
        rep=self._reference_report(); r=V40Renderer(1200,1200,seed=rep['base_seed'])
        self.assertGreaterEqual(rep['main_chip_pair_min_clearance'],rep['main_chip_pair_required_clearance']-1e-7)
        self.assertGreaterEqual(rep['pathway_cross_chip_connection_count'],1)
        self.assertEqual(rep['pathway_main_stalled_side_count'],0)
        self.assertEqual(rep['pathway_visible_launch_trace_count'],rep['pathway_launch_trace_count'])
        self.assertEqual(rep['pathway_local_gap_independent_source_count'],rep['pathway_local_gap_source_count'])
        self.assertGreaterEqual(rep['pathway_local_gap_trace_count'],rep['pathway_local_gap_source_count'])
        self.assertGreater(rep['pathway_local_gap_visible_trace_count'],0)
        self.assertAlmostEqual(r.local_gap_bundle_probability,0.50)
        self.assertLessEqual(2*rep['pathway_local_gap_bundle_pair_count'],rep['pathway_local_gap_source_count'])
        self.assertGreaterEqual(rep['pathway_local_gap_fill_actual'],0.79)
        self.assertGreaterEqual(rep['component_residual_gap_fill_actual'],0.50)
        self.assertLessEqual(rep['component_residual_gap_fill_actual'],0.62)
        self.assertEqual(rep.get('component_pathway_unauthorized_overlap_count',0),0)
        self.assertEqual(rep.get('pathway_main_local_clearance_violation_count',0),0)
        self.assertEqual(rep.get('local_component_clearance_violation_count',0),0)

    def test_v38_default_scale_is_canvas_over_1600_and_default_canvas_is_two_chip_only(self):
        r=V40Renderer(1200,1200,seed=1)
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
        larger=V40Renderer(1600,1600,seed=1)
        self.assertGreater(larger.chip_count_probability(),0.0)
        self.assertEqual(larger.chip_count(Fixed(0.0)),3)
        self.assertEqual(larger.chip_count(Fixed(.999999)),2)
        self.assertEqual(V40Renderer(1200,1200,seed=1,main_scale=.5).chip_count_probability(),0.0)

    def test_v38_traceback_blacklists_actual_replayed_corridor_at_rollback_junction(self):
        r=V40Renderer(seed=340034)
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

    def test_v38_connection_leg_rejects_visible_90_degree_terminal_kink(self):
        r=V40Renderer(1200,1200,seed=99)
        p=BundleGesturePlanner(r,99,[])
        tid=p.next_trace_id; p.next_trace_id+=1
        f=p._make_front(ids=[tid],chip=0,side='right',side_index=0,
                        path=[(200.0,200.0),(240.0,160.0)],direction=3,
                        offsets={tid:0.0},thicknesses={tid:2.0*r.U},prefixes={tid:[]},rng=SplitMix64(7))
        p.fronts[f['id']]=f
        # Incoming visible direction is NW (3); this SW terminal leg (5) is a 90-degree kink.
        leg=[f['path'][-1],(230.0,170.0)]
        self.assertTrue(p._connection_leg_creates_compensating_zigzag(f,tid,leg))

    def test_v38_nonzero_offset_singleton_rebases_to_exact_materialized_head_before_connection(self):
        r=V40Renderer(1200,1200,seed=100)
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


    def test_residual_filler_uses_compound_assemblies_outside_micro_rooms(self):
        r=V40Renderer(seed=37001)
        rng=SplitMix64(37002)
        medium=dict(short_span=90*r.U,cell_count=18)
        large=dict(short_span=180*r.U,cell_count=60)
        for i,reg in enumerate((medium,large)):
            g=r._make_residual_filler_component(rng,i,reg)
            self.assertTrue(g.structural.get('residual_compound'))
            self.assertFalse(g.structural.get('residual_micro'))
            self.assertGreaterEqual(g.structural.get('residual_assembly_family_count',0),2)

    def test_residual_micro_tokens_are_region_gated_and_capped(self):
        r=V40Renderer(seed=37003)
        rng=SplitMix64(37004)
        micro=dict(short_span=20*r.U,cell_count=2)
        g=r._make_residual_filler_component(rng,0,micro)
        self.assertTrue(g.structural.get('residual_micro'))
        self.assertFalse(g.structural.get('residual_compound'))
        self.assertEqual(r.component_micro_filler_limit,8)

    def test_reference_seed_residual_completion_is_compound_dominant(self):
        rep=self._reference_report(); r=V40Renderer(1200,1200,seed=rep['base_seed'])
        self.assertGreaterEqual(rep['component_residual_gap_fill_actual'],0.50)
        self.assertLessEqual(rep['component_residual_gap_fill_actual'],0.62)
        self.assertLessEqual(rep['component_residual_gap_micro_filler_count'],r.component_micro_filler_limit)
        self.assertGreaterEqual(rep['component_residual_gap_compound_filler_fraction'],0.75)
        self.assertEqual(rep.get('local_component_clearance_violation_count',0),0)

    def test_v40_renderer_is_behavior_equivalent_to_v39(self):
        root=Path(__file__).resolve().parents[2]
        old=(root/'archive'/'releases'/'v39'/'pcb_v39_renderer.py').read_text()
        expected=old.replace('Authority: chip_design_language_v39_variance_driven.md','Authority: chip_design_language.md')                    .replace('class V39Renderer:','class V40Renderer:')                    .replace('r=V39Renderer(args.width,args.height,args.seed,args.main_scale)','r=V40Renderer(args.width,args.height,args.seed,args.main_scale)')                    .replace('pcb_v39_','pcb_v40_')                    .replace("Path('v39_output')","Path('v40_output')")
        self.assertEqual((root/'pcb_v40_renderer.py').read_text(),expected)

    def test_v39_exact_dir8_rejects_non_octilinear_segment(self):
        self.assertEqual(exact_dir8_index(12.0,0.0),0)
        self.assertEqual(exact_dir8_index(5.0,-5.0),1)
        self.assertIsNone(exact_dir8_index(10.0,3.0))

    def test_v39_connection_junction_rejects_90_allows_45(self):
        r=V40Renderer(1200,1200,seed=39001)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        self.assertFalse(p._connection_junction_turn_ok([(0.0,0.0),(10.0,0.0)],[(10.0,10.0),(10.0,0.0)]))
        self.assertTrue(p._connection_junction_turn_ok([(0.0,0.0),(10.0,0.0)],[(20.0,10.0),(10.0,0.0)]))

    def test_v39_commit_rejects_direct_90_degree_turn(self):
        r=V40Renderer(1200,1200,seed=38001)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        f=self._planner_front(p,38002,(200.0,200.0),0,chip=0)
        # Give the front one already-materialized eastbound leg.  A direct southbound commit
        # is a two-octant / 90-degree corner and must fail before it can enter path history.
        f['path']=[(160.0,200.0),(200.0,200.0)]; f['dir']=0; f['gestures']=1; f['local_gestures']=1
        end=(200.0,160.0); g=p._corridor_geom(f,f['path'][-1],end)
        bad=dict(front=f['id'],start=f['path'][-1],end=end,dir=2,modules=2,geom=g,score=1.0)
        with self.assertRaisesRegex(RuntimeError,'illegal pathway turn at commit'):
            p._accept(f,bad,defer_post=True)

    def test_v39_reference_local_fill_is_bent_dominant_and_45_degree_only(self):
        rep=self._reference_report()
        self.assertGreaterEqual(rep['pathway_local_gap_fill_actual'],0.80)
        self.assertLessEqual(rep['pathway_local_gap_straight_visible_trace_fraction'],0.20)
        self.assertGreater(rep['pathway_local_gap_mopup_bent_trace_count'],0)
        self.assertGreaterEqual(rep['pathway_local_gap_mopup_bent_trace_count'],.85*rep['pathway_local_gap_mopup_trace_count'])
        self.assertEqual(rep['pathway_local_gap_max_single_vertex_turn_degrees'],45)
        self.assertEqual(rep['pathway_local_gap_illegal_turn_count'],0)
        self.assertEqual(rep['pathway_illegal_turn_count'],0)
        self.assertEqual(rep['pathway_non_octilinear_segment_count'],0)
        self.assertEqual(rep['pathway_illegal_connection_junction_turn_count'],0)
        self.assertEqual(rep['pathway_unmarked_clearance_violation_count'],0)
        self.assertEqual(rep['pathway_main_source_marker_count'],rep['pathway_launch_trace_count'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
