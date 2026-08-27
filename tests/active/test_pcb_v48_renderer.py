import math
import copy
import json
import statistics
import gc
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from shapely.geometry import LineString, Point

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pcb_v48_renderer import V48Renderer, BundleGesturePlanner, SplitMix64, sample_seed, chip_seed, collection_seed, placement_seed, retry_seed, nearest_dir_index, exact_dir8_index, nearest_point_on_polyline_segments, point_bounds_distance, point_along_dir, SIDE_TO_DIR, dir_vec, Group, SpatialHash, prim_rect_fill, prim_circle, prim_polyline

class V48RendererTests(unittest.TestCase):
    @classmethod
    def _reference_report(cls):
        """Fresh V44 production acceptance snapshot for current integration contracts."""
        root=Path(__file__).resolve().parents[2]
        return json.loads((root/'tests'/'fixtures'/'V44_REFERENCE_REPORT.json').read_text())

    def _prepare_component_templates(self,r,sample_index):
        """Prepare the current non-spatial component population without routing.

        This is the correct fixture for component grammar and scale contracts.
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
        r=V48Renderer(seed=31001)
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

    def test_v48_final_source_egress_totality_restores_launch_after_deep_traceback(self):
        r=V48Renderer(seed=310011)
        chip=Group('fake-chip',[prim_rect_fill(600.0,500.0,120.0,100.0,0,r.FG)],dict(placement_kind='chip'))
        planner=BundleGesturePlanner(r,sample_seed(r.seed,0),[chip])
        planner._launch_fronts()
        f=sorted((x for x in planner.fronts.values() if x.get('parent') is None and x.get('chip')==0),
                 key=lambda x:x['id'])[0]
        for _ in range(2):
            start=f['path'][-1]; vx,vy=dir_vec(f['initial_dir']); end=(start[0]+vx*2*planner.module,start[1]+vy*2*planner.module)
            g=planner._corridor_geom(f,start,end)
            self.assertTrue(planner._gesture_clear(f,start,end,g,allow_outside=False))
            planner._accept(f,dict(front=f['id'],start=start,end=end,dir=f['initial_dir'],modules=2,geom=g,score=1.0),defer_post=True)
        self.assertFalse(planner._source_egress_pending(f))
        f['reroute_pending']=True; f['reroute_ready_round']=0; f['reroute_attempts']=3
        self.assertGreaterEqual(planner._traceback_for_reroute(f),2)
        self.assertTrue(planner._source_egress_pending(f))
        self.assertLess(planner._minimum_materialized_lane_length(f),4*planner.module-1e-7)
        planner._settle_final_source_egress_totality()
        self.assertFalse(planner._source_egress_pending(f))
        self.assertGreaterEqual(planner._minimum_materialized_lane_length(f),4*planner.module-1e-7)
        self.assertFalse(f.get('protected_launch_unresolved'))

    def test_v48_exhausted_unmaterialized_structural_intent_is_not_hard_validity_debt(self):
        r,planner=self._planner_with_fake_chip(310012)
        f=self._root_family_front(planner,310012,lane_count=2,fan_pending=False)
        for _ in range(3):
            start=f['path'][-1]; end=(start[0]+2*planner.module,start[1])
            g=planner._corridor_geom(f,start,end)
            planner._accept(f,dict(front=f['id'],start=start,end=end,dir=0,modules=2,geom=g,score=1.0),defer_post=True)
        self._add_satisfied_side_sibling(planner,310013)
        f['fan_pending']=True; f['fragment_pending']=True; f['branch_stage']=1; f['branch_turn']=1
        self.assertTrue(planner._persistence_hard_debt(f))
        self.assertEqual(set(planner._persistence_hard_debt_reasons(f)),
                         {'fan_pending','fragment_pending','branch_stage'})
        cleared=planner._settle_exhausted_mature_structural_intents()
        self.assertEqual(cleared,6)
        self.assertFalse(f['fan_pending']); self.assertFalse(f['fragment_pending'])
        self.assertIsNone(f['branch_stage']); self.assertIsNone(f['branch_turn'])
        self.assertFalse(planner._persistence_hard_debt(f))

    def test_v47_incremental_main_rollback_matches_authoritative_rebuild_state(self):
        r=V48Renderer(seed=31005)
        planner=BundleGesturePlanner(r, sample_seed(r.seed,0), [])
        f=self._planner_front(planner, 8, (200.0,200.0), 0)
        for _ in range(3):
            start=f['path'][-1]; end=(start[0]+2*planner.module,start[1])
            g=planner._corridor_geom(f,start,end)
            planner._accept(f,dict(front=f['id'],start=start,end=end,dir=0,modules=2,geom=g,score=1.0),defer_post=True)
        self.assertEqual(len(planner.path_segments),3)
        f['reroute_attempts']=0
        removed=planner._traceback_for_reroute(f,defer_rebuild=True)
        self.assertEqual(removed,2)
        whole=(-10.0,-10.0,planner.W+10.0,planner.H+10.0)
        inc_live=[rec for rec in planner.path_index.query(whole) if not rec.get('_retired')]
        inc_sig=sorted((rec['front'],rec['start'],rec['end']) for rec in inc_live)
        inc_coverage=set(planner.coverage_cells)
        inc_congestion=tuple(tuple(row) for row in planner.congestion_grid)
        self.assertEqual(planner.stats['pathway_incremental_rollback_segment_remove_count'],2)
        planner._rebuild_path_index_and_coverage(rebuild_local_coverage=False)
        rebuilt=planner.path_index.query(whole)
        rebuilt_sig=sorted((rec['front'],rec['start'],rec['end']) for rec in rebuilt)
        self.assertEqual(inc_sig,rebuilt_sig)
        self.assertEqual(inc_coverage,planner.coverage_cells)
        self.assertEqual(inc_congestion,tuple(tuple(row) for row in planner.congestion_grid))
        self.assertEqual(len(planner.path_segments),1)

    def test_v47_chip_only_capacity_index_matches_historical_general_static_filter(self):
        r=V48Renderer(seed=41117)
        chips=[
            Group('chip-a',[prim_rect_fill(180,180,120,100,0,r.FG)],dict(placement_kind='chip')),
            Group('chip-b',[prim_rect_fill(720,540,150,130,0,r.FG)],dict(placement_kind='chip')),
        ]
        # Primitive-expanded secondary content deliberately pollutes the general static index.
        comp=Group('secondary',[prim_circle(400+i*18,330+(i%3)*16,5,r.FG,True) for i in range(12)],
                   dict(placement_kind='collection'))
        planner=BundleGesturePlanner(r,sample_seed(r.seed,0),chips+[comp])
        self.assertEqual(len(planner.chip_capacity_index.objects),len(chips))
        self.assertGreater(len(planner.static_index.objects),len(planner.chip_capacity_index.objects))
        f=self._planner_front(planner,17,(250.0,250.0),0,chip=0)

        def historical(p,max_radius=None):
            max_radius=(3.8*planner.module if max_radius is None else float(max_radius))
            x,y=p
            if x<0 or y<0 or x>planner.W or y>planner.H: return 0.0
            free=min(max_radius,x,y,planner.W-x,planner.H-y)
            half=planner._front_half_width(f)
            reach=max_radius+planner.r.pathway_main_chip_keepout+half
            seen=set()
            for gi,g in planner.static_index.query((x-reach,y-reach,x+reach,y+reach)):
                if gi>=len(planner.chips) or gi==f.get('chip') or gi in seen:
                    continue
                seen.add(gi)
                free=min(free,max(0.0,point_bounds_distance(p,g.bounds)-planner.r.pathway_main_chip_keepout-half))
                if free<=0.0: break
            congestion=planner._congestion_at(p)
            free*=max(0.0,1.0-min(1.0,congestion/3.2))
            return max(0.0,free)

        for p0 in ((250.0,250.0),(500.0,350.0),(650.0,500.0),(1000.0,900.0)):
            self.assertEqual(planner._point_free_radius(f,p0),historical(p0))

    def test_v47_congestion_cache_invalidates_only_local_dependency_and_remains_exact(self):
        r=V48Renderer(seed=47148)
        planner=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        p=(planner.W*0.5,planner.H*0.5)
        before=planner._congestion_at(p)
        key=planner._grid_cell(p)
        self.assertIn(key,planner._congestion_cache)
        a=(p[0]-0.1*planner.module,p[1]); b=(p[0]+0.1*planner.module,p[1])
        planner._grid_add_segment(a,b,1)
        after=planner._congestion_at(p)
        self.assertGreater(after,before)
        planner._congestion_cache.clear()
        self.assertAlmostEqual(after,planner._congestion_at(p),places=15)

    def test_v47_group_batch_translation_matches_scalar_primitive_translation_exactly(self):
        ps=[prim_rect_fill(0.0,0.0,40.0,20.0,0.0,'#fff'),
            prim_circle(25.0,-15.0,8.0,'#fff'),
            prim_polyline([(0.0,0.0),(20.0,20.0),(40.0,20.0)],3.0,'#fff')]
        g=Group('translate-fixture',ps,{'placement_kind':'collection'})
        for tx,ty,scale in ((123.25,-77.5,1.0),(41.5,-12.75,.82),(0.0,0.0,1.17)):
            moved=g.transformed(tx,ty,scale)
            scalar=[p.transformed(tx,ty,scale) for p in ps]
            scalar_group=Group('scalar-transform-fixture',scalar,{})
            self.assertEqual([p.svg for p in moved.primitives],[p.svg for p in scalar])
            self.assertEqual([p.signature for p in moved.primitives],[p.signature for p in scalar])
            self.assertEqual(moved.bounds,scalar_group.bounds)
            for a,b in zip(moved.primitives,scalar):
                self.assertTrue(a.geom.equals_exact(b.geom,0.0))

    def test_v47_local_gap_target_uses_bounded_chunk_local_state(self):
        r=V48Renderer(seed=47149)
        planner=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        nx,ny=r.local_gap_grid_shape(); cw=r.W/nx; ch=r.H/ny
        cells={(gx,gy) for gy in range(min(ny,30)) for gx in range(min(nx,30))
               if (3*gx+5*gy)%11 != 0}
        planner.local_gap_regions=[dict(id=0,cells=set(cells),cell_count=len(cells),center=(15*cw,15*ch),
                                        width=30*cw,height=30*ch,short_span=30*ch,long_span=30*cw,
                                        dir=0,size='large')]
        planner.local_gap_region_by_cell={c:0 for c in cells}
        planner.local_gap_open_cells=set(cells)
        planner.local_gap_untouched_cells=set(cells)
        planner.local_gap_untouched_by_region={0:set(cells)}
        span=planner.local_gap_chunk_span; chunks={}
        for c in cells:
            ck=(c[0]//span,c[1]//span)
            chunks.setdefault(ck,set()).add(c)
            planner.local_gap_chunk_key_by_cell[c]=(0,ck)
        planner.local_gap_chunk_cells_by_region={0:{k:frozenset(v) for k,v in chunks.items()}}
        planner._reset_local_gap_chunk_state()
        planner.congestion_grid=[[((11*x+17*y)%23) for x in range(planner.grid_nx)] for y in range(planner.grid_ny)]
        planner._congestion_cache.clear()
        center=((12.5)*cw,(12.5)*ch)
        before_cells=planner.stats.get('pathway_local_gap_target_cell_evaluation_count',0)
        before_fallback=planner.stats.get('pathway_local_gap_target_chunk_fallback_count',0)
        target=planner._local_gap_target(center,SplitMix64(88000),0)
        after_cells=planner.stats.get('pathway_local_gap_target_cell_evaluation_count',0)
        after_fallback=planner.stats.get('pathway_local_gap_target_chunk_fallback_count',0)
        self.assertIn(planner._gap_cell(target),cells)
        self.assertLessEqual(after_cells-before_cells,span*span)
        self.assertEqual(after_fallback,before_fallback)
        self.assertLessEqual(planner.stats.get('pathway_local_gap_target_chunk_evaluation_count',0),21)

    def test_v47_deferred_subgroup_transform_preserves_historical_collection_payloads(self):
        import hashlib, json
        cases=[
            (0x123456789ABCDEF,700,dict(families=['ic','dense','capacitor_circle'],border=True,family_count=3,complexity=.5,tier=3),'95d6b6d7b6e6716465b3440a2ba269cf9090342f97ede85cea26b29552bc8200'),
            (0x123456789ABCDEF+17,701,dict(families=['square','circle','dash'],border=False,family_count=3,complexity=.5,tier=3),'bee77a3239e79526feab156edc2d36dd59b23e5d51922fb81e5acc03411a4735'),
            (0x123456789ABCDEF+34,702,dict(families=['dense','dot','capacitor_circle','ic'],border=True,family_count=4,complexity=.5,tier=4),'b3bab21e26ae7c2f1a0d85e7961ab713e1dc7ac882876ee80c6d4a513b7ad480'),
        ]
        r=V48Renderer(aspect_ratio='1:1',scale=1.0,seed=20260816)
        for seed,idx,assignment,expected in cases:
            g=r._make_collection_once(SplitMix64(seed),idx,assignment)
            payload=json.dumps([[p.kind,p.svg,p.signature] for p in g.primitives],sort_keys=True,separators=(',',':'))
            self.assertEqual(hashlib.sha256(payload.encode()).hexdigest(),expected)

    def test_v47_local_gap_congestion_cell_mapping_matches_historical_point_mapping_exactly(self):
        r=V48Renderer((1200,2200),seed=47151,scale=.75)
        planner=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        nx,ny=r.local_gap_grid_shape(); cw=r.W/nx; ch=r.H/ny
        xmap=[planner._grid_cell(((gx+.5)*cw,0.0))[0] for gx in range(nx)]
        ymap=[planner._grid_cell((0.0,(gy+.5)*ch))[1] for gy in range(ny)]
        for gy in range(ny):
            for gx in range(nx):
                p=((gx+.5)*cw,(gy+.5)*ch)
                self.assertEqual((xmap[gx],ymap[gy]),planner._grid_cell(p))
        a=(.31*r.W,.42*r.H); b=(.67*r.W,.58*r.H)
        planner._grid_add_segment(a,b,1)
        for gy in range(0,ny,max(1,ny//7)):
            for gx in range(0,nx,max(1,nx//7)):
                p=((gx+.5)*cw,(gy+.5)*ch)
                self.assertEqual(planner._congestion_at(p),planner._congestion_at_cell(xmap[gx],ymap[gy]))

    def test_v47_component_collection_path_predicate_is_set_equivalent_to_primitive_loop(self):
        r=V48Renderer(seed=47150)
        cand=Group('candidate',[
            prim_rect_fill(0.0,0.0,28.0,14.0,0.0,'#fff'),
            prim_circle(42.0,4.0,7.0,'#fff'),
            prim_polyline([(15.0,24.0),(30.0,39.0),(48.0,39.0)],3.0,'#fff'),
        ],{})
        cgeoms=r._group_collision_geoms(cand)
        for x in (-20.0,5.0,26.0,55.0,90.0):
            raw=LineString([(x,-18.0),(x,62.0)])
            keepout=raw.buffer(r.component_pathway_clearance,quad_segs=4)
            old_hit=any(cg.intersects(keepout) for cg in cgeoms)
            self.assertEqual(cand.collision_geom.intersects(keepout),old_hit)
            allowed=LineString([(x-4.0,15.0),(x+4.0,15.0)]).buffer(9.0,quad_segs=8)
            old_outside=any((not (inter:=cg.intersection(keepout)).is_empty) and
                            (not inter.difference(allowed).is_empty) for cg in cgeoms)
            inter=cand.collision_geom.intersection(keepout)
            new_outside=(not inter.is_empty) and (not inter.difference(allowed).is_empty)
            self.assertEqual(new_outside,old_outside)

    def test_v47_spatial_hash_query_filters_same_cell_nonoverlapping_aabbs(self):
        index=SpatialHash(100.0)
        near={'name':'near'}; far={'name':'far'}
        index.insert(near,(10.0,10.0,20.0,20.0))
        index.insert(far,(80.0,80.0,90.0,90.0))
        # Both records share hash cell (0,0), but only the first overlaps the exact query box.
        self.assertEqual(index.query((0.0,0.0,30.0,30.0)),[near])

    def test_v47_spatial_hash_sparse_object_shortcut_skips_empty_cell_walk(self):
        index=SpatialHash(1.0)
        left={'name':'left'}; right={'name':'right'}
        index.insert(left,(10.0,10.0,10.5,10.5))
        index.insert(right,(90.0,90.0,90.5,90.5))
        class NoCellLookup(dict):
            def get(self,*args,**kwargs):
                raise AssertionError('sparse-object query should not walk empty hash cells')
        index.cells=NoCellLookup(index.cells)
        self.assertEqual(set(map(id,index.query((0.0,0.0,20.0,20.0)))),{id(left)})

    def test_joint_conflict_solution_is_insertion_order_invariant(self):
        r=V48Renderer(seed=31002)
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
        r=V48Renderer(seed=31003)
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
        r=V48Renderer(seed=31004)
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
        r=V48Renderer(seed=seed)
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
                              rng=SplitMix64(seed))
        f['fan_parts']=[ids[:max(1,lane_count//2)],ids[max(1,lane_count//2):]] if lane_count>1 else [ids]
        f['fan_pending']=bool(fan_pending and lane_count>1)
        f['launch_family_key']=(0,0,'right')
        f['launch_egress_pending']=True
        for tid in ids:
            start=(360.0,300.0+offsets[tid])
            end=(360.0+planner.launch_egress_modules*planner.module,start[1])
            rad=.5*thicknesses[tid]+planner.r.pathway_interroute_keepout
            from shapely.geometry import LineString, Point
            rec=dict(owner=(0,0,'right'),tid=tid,active=True,
                geom=LineString([start,end]).buffer(rad,cap_style='round',join_style='mitre',quad_segs=4))
            planner.source_egress_reservations.append(rec)
            planner.source_egress_by_owner.setdefault((0,0,'right'),[]).append(rec)
            planner.source_egress_index.insert(rec,rec['geom'].bounds)
        return f

    def _add_satisfied_side_sibling(self, planner, seed=99999, length_modules=8.5):
        s=self._planner_front(planner,seed,(360.0,520.0),0,chip=0)
        start=s['path'][-1]; end=(start[0]+length_modules*planner.module,start[1])
        g=planner._corridor_geom(s,start,end)
        planner._accept(s,dict(front=s['id'],start=start,end=end,dir=0,modules=length_modules,geom=g,score=1.0),defer_post=True)
        s['status']='terminated'; s['lifecycle']='TERMINAL'; s['termination_reason']='side_progress_fixture'
        return s

    def test_root_bundle_cannot_structurally_split_before_physical_egress(self):
        r,planner=self._planner_with_fake_chip(32001)
        f=self._root_family_front(planner, 11, lane_count=4, fan_pending=True)
        self.assertTrue(planner._source_egress_pending(f))
        # Gesture zero still emerges perpendicular to the chip.
        self.assertEqual(planner._direction_candidates(f),[f['initial_dir']])
        self.assertEqual(planner._branch_front(f),[])
        self.assertFalse(planner._fragment_bundled_front(f))

    def test_root_can_turn_before_four_module_survival_floor(self):
        r,planner=self._planner_with_fake_chip(32002)
        f=self._root_family_front(planner, 12, lane_count=3, fan_pending=False)
        self.assertFalse(f['fan_pending'])
        self.assertTrue(planner._source_egress_pending(f))
        # The first gesture is still perpendicular, but it is no longer forced to consume
        # the whole four-module survival floor in one straight run.
        self.assertEqual(planner._direction_candidates(f),[f['initial_dir']])
        self.assertEqual(planner._module_counts(f),[1,2])
        start=f['path'][-1]
        vx,vy=dir_vec(f['dir']); end=(start[0]+vx*planner.module,start[1]+vy*planner.module)
        geom=planner._corridor_geom(f,start,end)
        proposal=dict(front=f['id'],start=start,end=end,dir=f['dir'],modules=1,geom=geom,
                      future_geom=geom,score=1.0,priority=1.0)
        planner._accept(f,proposal,defer_post=True)
        self.assertTrue(planner._source_egress_pending(f))
        self.assertLess(planner._minimum_materialized_lane_length(f),4.0*planner.module)
        dirs=planner._direction_candidates(f)
        self.assertIn(f['dir'],dirs)
        self.assertIn((f['dir']-1)%8,dirs)
        self.assertIn((f['dir']+1)%8,dirs)
        # Early turning does not weaken the hard minimum: termination remains illegal below 4.
        self.assertTrue(planner._main_launch_physically_protected(f))

    def test_v48_recovery_fragmentation_cannot_export_underfloor_survival_debt_to_singletons(self):
        _r,planner=self._planner_with_fake_chip(320021)
        f=self._root_family_front(planner,12021,lane_count=3,fan_pending=False)
        start=f['path'][-1]; end=(start[0]+2.0*planner.module,start[1])
        geom=planner._corridor_geom(f,start,end)
        planner._accept(f,dict(front=f['id'],start=start,end=end,dir=0,modules=2,geom=geom,score=1.0),defer_post=True)
        ancestor=self._planner_front(planner,120210,(900.0,700.0),0,chip=0)
        ancestor['status']='branched'
        f['parent']=ancestor['id']
        f['launch_egress_pending']=False
        planner._release_source_egress(planner._launch_family_key(f))
        self.assertLess(planner._minimum_materialized_lane_length(f),4.0*planner.module-1e-7)
        before=set(planner.fronts)
        self.assertFalse(planner._fragment_bundled_front(f))
        self.assertEqual(set(planner.fronts),before)
        self.assertEqual(f['status'],'active')
        self.assertGreaterEqual(planner.stats.get('pathway_underfloor_fragment_reject_count',0),1)

    def test_v48_young_main_branch_commits_survival_transaction_before_parent_is_replaced(self):
        _r,planner=self._planner_with_fake_chip(320022)
        f=self._root_family_front(planner,12022,lane_count=4,fan_pending=False)
        start=f['path'][-1]; end=(start[0]+2.0*planner.module,start[1])
        geom=planner._corridor_geom(f,start,end)
        planner._accept(f,dict(front=f['id'],start=start,end=end,dir=0,modules=2,geom=geom,score=1.0),defer_post=True)
        ancestor=self._planner_front(planner,120220,(900.0,700.0),0,chip=0)
        ancestor['status']='branched'
        f['parent']=ancestor['id']
        f['launch_egress_pending']=False
        planner._release_source_egress(planner._launch_family_key(f))
        self.assertLess(planner._minimum_materialized_lane_length(f),4.0*planner.module-1e-7)
        children=planner._branch_front(f)
        self.assertTrue(children)
        self.assertEqual(f['status'],'branched')
        for child in children:
            self.assertGreaterEqual(planner._minimum_materialized_lane_length(child),4.0*planner.module-1e-7)
            self.assertIsNone(child.get('branch_stage'))
        self.assertGreaterEqual(planner.stats.get('pathway_young_branch_survival_transaction_count',0),1)

    def test_v48_root_fan_becomes_transactionally_ready_after_one_real_emergence_gesture(self):
        _r,p=self._planner_with_fake_chip(480101)
        f=self._root_family_front(p,480101,lane_count=12,fan_pending=True)
        self.assertFalse(p._launch_fan_ready(f))
        start=f['path'][-1]; end=(start[0]+p.module,start[1]); g=p._corridor_geom(f,start,end)
        p._accept(f,dict(front=f['id'],start=start,end=end,dir=0,modules=1,geom=g,score=1.0),defer_post=True)
        # Source egress is still below four, but the root no longer owns four unsplit modules.
        self.assertTrue(p._source_egress_pending(f))
        self.assertTrue(p._launch_fan_ready(f))
        self.assertEqual(p._direction_candidates(f),[f['dir']])
        children=p._fan_front(f)
        self.assertGreaterEqual(len(children),2)
        self.assertEqual(f['status'],'branched')
        self.assertTrue(all(p._minimum_materialized_lane_length(c)>=4.0*p.module-1e-7 for c in children))
        self.assertFalse(any(rec.get('active',True) for rec in p.source_egress_reservations))
        self.assertEqual(p.main_launch_maturity_modules,4.0)

    def test_v48_transactional_fan_survival_certificate_is_a_traceback_floor(self):
        _r,p=self._planner_with_fake_chip(4801011)
        f=self._root_family_front(p,4801011,lane_count=12,fan_pending=True)
        start=f['path'][-1]; end=(start[0]+p.module,start[1]); g=p._corridor_geom(f,start,end)
        p._accept(f,dict(front=f['id'],start=start,end=end,dir=0,modules=1,geom=g,score=1.0),defer_post=True)
        children=p._fan_front(f)
        turning=next(c for c in children if c.get('fan_birth_turn') in (-1,1))
        before=p._minimum_materialized_lane_length(turning)
        self.assertGreaterEqual(before,4.0*p.module-1e-7)
        self.assertIsNone(turning.get('branch_stage'))
        self.assertEqual(turning.get('recovery_floor_segments'),len(turning['path'])-1)
        turning['reroute_attempts']=4
        p._traceback_for_reroute(turning)
        self.assertGreaterEqual(p._minimum_materialized_lane_length(turning),4.0*p.module-1e-7)
        self.assertIsNone(turning.get('branch_stage'))
        self.assertEqual(len(turning['path'])-1,turning.get('recovery_floor_segments'))

    def test_v48_fan_uses_seeded_space_legal_spread_instead_of_one_whole_bus_bend(self):
        _r,p=self._planner_with_fake_chip(480102)
        f=self._root_family_front(p,991,lane_count=15,fan_pending=True)
        ids=list(f['ids']); f['fan_parts']=[ids[0:3],ids[3:6],ids[6:9],ids[9:12],ids[12:15]]
        start=f['path'][-1]; end=(start[0]+p.module,start[1]); g=p._corridor_geom(f,start,end)
        p._accept(f,dict(front=f['id'],start=start,end=end,dir=0,modules=1,geom=g,score=1.0),defer_post=True)
        children=p._fan_front(f)
        turns=[c.get('fan_birth_turn') for c in children]
        self.assertIn(0,turns)
        self.assertTrue(any(t in (-1,1) for t in turns))
        self.assertGreaterEqual(len(set(turns)),2)
        self.assertGreaterEqual(p.stats.get('pathway_fan_permutation_viable_option_count',0),2)
        self.assertTrue(all(p._minimum_materialized_lane_length(c)>=4.0*p.module-1e-7 for c in children))

    def test_v48_fan_rebase_exemption_never_legalizes_a_first_turn_across_sibling_corridor(self):
        _r,p=self._planner_with_fake_chip(4801021)
        parent=self._root_family_front(p,4801021,lane_count=2,fan_pending=False)
        # Two direct fan siblings with parallel inherited rebase corridors.  `a` has not yet
        # accumulated a local gesture, which is the historical stale-exemption condition.
        ta,tb=parent['ids']
        a=p._make_front(ids=[ta],chip=0,side='right',side_index=0,path=[(500.0,400.0)],direction=0,
                        offsets={ta:0.0},thicknesses={ta:3.0*p.U},prefixes={ta:[]},rng=SplitMix64(11),
                        parent=parent['id'],branch_turn=0,fan_group=(0,0),forced_straight_modules=2)
        b=p._make_front(ids=[tb],chip=0,side='right',side_index=0,path=[(500.0,412.0)],direction=0,
                        offsets={tb:0.0},thicknesses={tb:3.0*p.U},prefixes={tb:[]},rng=SplitMix64(12),
                        parent=parent['id'],branch_turn=0,fan_group=(0,0),forced_straight_modules=2)
        for front,y,run_modules in ((a,400.0,3),(b,412.0,6)):
            front['branch_stage']=0; front['local_gestures']=0
            start=front['path'][-1]; end=(start[0]+run_modules*p.module,y); g=p._corridor_geom(front,start,end)
            p._record_segment(front,start,end,g,normal=False)
        # A straight continuation may use the sibling rebase exemption.  A diagonal candidate
        # crossing B's committed straight corridor may not.
        a['path'].append((500.0+3*p.module,400.0)); a['dir']=0
        start=a['path'][-1]; end=(start[0]+2*p.module*2**-.5,start[1]+2*p.module*2**-.5)
        g=p._corridor_geom(a,start,end)
        self.assertFalse(p._gesture_clear(a,start,end,g,allow_outside=False))

    def test_v48_main_launch_cohorts_are_several_balanced_bundles(self):
        _r,p=self._planner_with_fake_chip(480103)
        for n in (9,12,18,24):
            parts=p._cohort_slices(n,SplitMix64(480103+n))
            self.assertGreaterEqual(len(parts),3)
            self.assertLessEqual(len(parts),7)
            self.assertEqual(sum(len(x) for x in parts),n)
            self.assertLessEqual(max(len(x) for x in parts),5)
            self.assertLessEqual(max(map(len,parts))-min(map(len,parts)),1)

    def test_v48_last_unsatisfied_side_outcome_cannot_terminalize_below_side_progress_floor(self):
        _r,p=self._planner_with_fake_chip(480104)
        f=self._root_family_front(p,480104,lane_count=1,fan_pending=False)
        start=f['path'][-1]; end=(start[0]+6.5*p.module,start[1]); g=p._corridor_geom(f,start,end)
        p._accept(f,dict(front=f['id'],start=start,end=end,dir=0,modules=6.5,geom=g,score=1.0),defer_post=True)
        self.assertTrue(p._main_side_progress_debt(f))
        p._terminate_front(f,'fixture')
        self.assertEqual(f['status'],'active')
        self.assertEqual(f.get('quality_repair_reason'),'side_progress_persistence')
        self._add_satisfied_side_sibling(p,480105)
        self.assertFalse(p._main_side_progress_debt(f))
        p._terminate_front(f,'fixture')
        self.assertEqual(f['status'],'terminated')
        self.assertEqual(p.main_launch_maturity_modules,4.0)

    def test_v48_same_chip_different_sides_are_connection_compatible_after_egress(self):
        _r,p=self._planner_with_fake_chip(480106)
        a=self._planner_front(p,480106,(420.0,420.0),0,chip=0)
        tid=p.next_trace_id; p.next_trace_id+=1
        b=p._make_front(ids=[tid],chip=0,side='top',side_index=1,path=[(520.0,420.0)],direction=4,
                        offsets={tid:0.0},thicknesses={tid:3.0*p.U},prefixes={tid:[]},rng=SplitMix64(480107))
        # Give both families mature histories so this cannot create a corner shortcut through
        # their source package.
        for front,direction in ((a,0),(b,4)):
            start=front['path'][-1]; end=point_along_dir(start,direction,4.5*p.module); g=p._corridor_geom(front,start,end)
            p._accept(front,dict(front=front['id'],start=start,end=end,dir=direction,modules=4.5,geom=g,score=1.0),defer_post=True)
        self.assertNotEqual(p._launch_family_key(a),p._launch_family_key(b))
        self.assertTrue(p._connection_family_compatible(a,b))
        c=self._planner_front(p,480108,(420.0,500.0),0,chip=0)
        self.assertFalse(p._connection_family_compatible(a,c))

    def test_v48_terminal_head_sweep_considers_same_chip_different_side_families(self):
        _r,p=self._planner_with_fake_chip(480109)
        a=self._planner_front(p,480109,(400.0,400.0),0,chip=0)
        tid=p.next_trace_id; p.next_trace_id+=1
        b=p._make_front(ids=[tid],chip=0,side='top',side_index=1,path=[(400.0+10.0*p.module,400.0)],direction=4,
                        offsets={tid:0.0},thicknesses={tid:3.0*p.U},prefixes={tid:[]},rng=SplitMix64(480110))
        for front,direction in ((a,0),(b,4)):
            start=front['path'][-1]; end=point_along_dir(start,direction,4.5*p.module); g=p._corridor_geom(front,start,end)
            p._accept(front,dict(front=front['id'],start=start,end=end,dir=direction,modules=4.5,geom=g,score=1.0),defer_post=True)
            front['status']='terminated'; front['lifecycle']='TERMINAL'
        with mock.patch.object(p,'_try_connect_specific_terminal_heads',return_value=True) as join:
            made=p._connect_near_main_terminals(max_pairs=8)
        self.assertEqual(made,1)
        join.assert_called_once()

    def test_v48_early_turn_under_floor_final_settlement_rewinds_to_emergence_fallback(self):
        _r,planner=self._planner_with_fake_chip(320021)
        f=self._root_family_front(planner, 121, lane_count=1, fan_pending=False)
        # One straight module followed by one legal diagonal module: still below four, so no
        # bent survival certificate exists yet. Final settlement must rewind this partial bend
        # to emergence before using the original protected straight corridor.
        a=f['path'][-1]; b=point_along_dir(a,0,planner.module); g=planner._corridor_geom(f,a,b)
        planner._accept(f,dict(front=f['id'],start=a,end=b,dir=0,modules=1,geom=g,score=1.0),defer_post=True)
        a=f['path'][-1]; b=point_along_dir(a,1,planner.module); g=planner._corridor_geom(f,a,b)
        self.assertTrue(planner._gesture_clear(f,a,b,g,allow_outside=False))
        planner._accept(f,dict(front=f['id'],start=a,end=b,dir=1,modules=1,geom=g,score=1.0),defer_post=True)
        self.assertTrue(planner._source_egress_pending(f))
        self.assertIsNone(f.get('launch_survival_prefix_path'))
        planner._settle_final_source_egress_totality()
        self.assertFalse(planner._source_egress_pending(f))
        self.assertGreaterEqual(planner._minimum_materialized_lane_length(f),4*planner.module-1e-7)
        dirs=[exact_dir8_index(b[0]-a[0],b[1]-a[1]) for a,b in zip(f['path'],f['path'][1:])]
        self.assertTrue(dirs and all(d==f['initial_dir'] for d in dirs))

    def test_v48_mature_bent_survival_prefix_replays_after_deep_traceback(self):
        _r,planner=self._planner_with_fake_chip(320022)
        f=self._root_family_front(planner, 122, lane_count=1, fan_pending=False)
        # Mature through a bend rather than a four-module straight ray.
        for d,mods in ((0,2),(1,3)):
            a=f['path'][-1]; b=point_along_dir(a,d,mods*planner.module); g=planner._corridor_geom(f,a,b)
            self.assertTrue(planner._gesture_clear(f,a,b,g,allow_outside=False))
            planner._accept(f,dict(front=f['id'],start=a,end=b,dir=d,modules=mods,geom=g,score=1.0),defer_post=True)
        captured=list(f.get('launch_survival_prefix_path') or ())
        self.assertGreaterEqual(len(captured),3)
        self.assertEqual(exact_dir8_index(captured[2][0]-captured[1][0],captured[2][1]-captured[1][1]),1)
        self.assertFalse(planner._source_egress_pending(f))
        f['reroute_pending']=True; f['reroute_ready_round']=0; f['reroute_attempts']=3
        self.assertGreaterEqual(planner._traceback_for_reroute(f),2)
        self.assertTrue(planner._source_egress_pending(f))
        planner._settle_final_source_egress_totality()
        self.assertFalse(planner._source_egress_pending(f))
        self.assertEqual(f['path'],captured)
        self.assertGreaterEqual(planner._minimum_materialized_lane_length(f),4*planner.module-1e-7)

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

    def test_young_structural_hold_fairness_prefers_previously_held_sibling(self):
        _r,planner=self._planner_with_fake_chip(320041)
        a=self._root_family_front(planner, 1401, lane_count=1, fan_pending=False)
        b=self._root_family_front(planner, 1501, lane_count=1, fan_pending=False)
        b['path']=[(420.0,240.0)]; b['origin']=b['path'][0]
        for f in (a,b):
            f['launch_family_key']=(0,0,'right')
            f['parent']=999
            f['branch_stage']=0
            f['local_gestures']=0
            f['travel']=4.0*planner.module
            f['structural_hold_streak']=0
        # Canonical tie-breaking would pick the lower front id.  A sibling that already
        # HOLDed once must instead receive the one-round first-rebase anti-starvation edge.
        b['structural_hold_streak']=1
        def prop(f,end,d):
            g=planner._corridor_geom(f,f['path'][-1],end)
            return dict(front=f['id'],start=f['path'][-1],end=end,dir=d,modules=2,geom=g,
                        future_geom=g,future_option_count=1,score=1.0,priority=1.0)
        pa=prop(a,(500.0,300.0),0)
        pb=prop(b,(420.0,360.0),2)
        sol=planner._solve_conflict_group([a['id'],b['id']],{a['id']:[pa],b['id']:[pb]})
        self.assertIsNotNone(sol)
        self.assertEqual([q['front'] for q in sol],[b['id']])
        self.assertEqual(b['structural_hold_streak'],0)
        self.assertEqual(a['structural_hold_streak'],1)

    def test_residual_structural_persistence_settlement_is_shared_snapshot_atomic(self):
        _r,planner=self._planner_with_fake_chip(320042)
        a=self._planner_front(planner, 1601, (300.0,300.0), 0, chip=0)
        b=self._planner_front(planner, 1602, (420.0,240.0), 2, chip=0)
        for f in (a,b):
            f['parent']=999
            f['branch_stage']=0
            f['branch_turn']=1
            f['local_gap']=False
            f['fan_pending']=False
        ga=planner._corridor_geom(a,a['path'][-1],(500.0,300.0))
        gb=planner._corridor_geom(b,b['path'][-1],(420.0,360.0))
        pa=dict(front=a['id'],start=a['path'][-1],end=(500.0,300.0),dir=0,modules=2,geom=ga,
                future_geom=ga,future_option_count=1,score=1.0,priority=1.0)
        pb=dict(front=b['id'],start=b['path'][-1],end=(420.0,360.0),dir=2,modules=2,geom=gb,
                future_geom=gb,future_option_count=1,score=1.0,priority=1.0)
        accepted=[]
        def variants(f,_count):
            return [pa] if f['id']==a['id'] else [pb]
        with mock.patch.object(planner,'_proposal_variants',side_effect=variants), \
             mock.patch.object(planner,'_conflict_groups',return_value=[[a['id'],b['id']]]), \
             mock.patch.object(planner,'_future_conflict',side_effect=lambda p,q:p['front']!=q['front']), \
             mock.patch.object(planner,'_accept',side_effect=lambda f,p,defer_post=True: accepted.append(p['front'])), \
             mock.patch.object(planner,'_minimum_materialized_lane_length',return_value=0.0):
            moved=planner._settle_structural_persistence_debt_atomic(100,rounds=1)
        self.assertEqual(moved,1)
        self.assertEqual(len(accepted),1)
        self.assertGreater(planner.stats['pathway_structural_persistence_conflict_combination_count'],0)

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

    def test_v46_preflight_intersection_repairs_only_one_causal_side_per_pair(self):
        r,planner=self._planner_with_fake_chip(44073)
        newf=self._planner_front(planner, 440731, (300.0,320.0), 2)
        oldf=self._planner_front(planner, 440732, (360.0,250.0), 0)
        for f in (newf,oldf):
            f['status']='terminated'
        calls=[]
        stats={'pathway_zigzag_cleanup_details':[],
               'pathway_main_unaccounted_launch_trace_ids':[newf['ids'][0]],
               'pathway_main_unaccounted_launch_trace_count':1,
               'pathway_intersection_cleanup_pairs':[{
                   'new_front':newf['id'],'old_front':oldf['id'],
                   'new_tid':newf['ids'][0],'old_tid':oldf['ids'][0]}]}
        cleared=dict(stats,pathway_main_unaccounted_launch_trace_ids=[],
                     pathway_main_unaccounted_launch_trace_count=0,
                     pathway_intersection_cleanup_pairs=[])
        def fake_tx(f,current,*args,**kwargs):
            calls.append(f['id']); return True,cleared
        with mock.patch.object(planner,'_transactional_main_preflight_attempt',side_effect=fake_tx):
            self.assertTrue(planner._repair_main_preflight_materialization(stats))
        self.assertEqual(calls,[newf['id']])


    def test_escaped_trace_is_clipped_at_first_frame_crossing(self):
        r=V48Renderer(seed=32006)
        planner=BundleGesturePlanner(r, sample_seed(r.seed,0), [])
        pts=[(100.0,100.0),(-10.0,100.0),(-10.0,220.0)]
        clipped=planner._clip_escaped_polyline_to_frame(pts)
        self.assertEqual(len(clipped),2)
        self.assertAlmostEqual(clipped[-1][0],0.0,places=6)
        self.assertAlmostEqual(clipped[-1][1],100.0,places=6)

    def test_tall_canvas_micro_escape_cleanup_preserves_octilinear_previous_leg(self):
        # Regression for the V40 tall-canvas rejection: a legal 45-degree leg followed by
        # a sub-0.10-module horizontal escape used to move the diagonal endpoint sideways
        # to the *horizontal* frame crossing, manufacturing a non-octilinear visible leg.
        for height in (6248,8046):
            r=V48Renderer((1200,height),seed=41001)
            planner=BundleGesturePlanner(r, sample_seed(r.seed,0), [])
            pts=[(1100.0,1100.0),(1160.0,1160.0),(1198.0,1198.0),(1202.0,1198.0)]
            clipped=planner._clip_escaped_polyline_to_frame(pts)
            dirs,malformed=planner._exact_turn_directions(clipped)
            self.assertEqual(malformed,0,(height,clipped))
            self.assertTrue(planner._exact_path_grammar_ok(clipped),(height,clipped,dirs))
            self.assertAlmostEqual(clipped[-1][0],1200.0,places=6)
            self.assertAlmostEqual(clipped[-1][1],1200.0,places=6)
            self.assertGreaterEqual(math.hypot(clipped[-1][0]-clipped[-2][0],clipped[-1][1]-clipped[-2][1]),
                                    .10*planner.module-1e-9)

    def test_component_path_keepout_wkb_cache_is_exact_compact_and_reuses_buffer(self):
        r=V48Renderer(seed=9089)
        raw=LineString([(10.0,10.0),(80.0,10.0),(110.0,40.0)])
        class CountingGeom:
            def __init__(self, geom):
                self.geom=geom; self.buffer_calls=0
            def buffer(self, *args, **kwargs):
                self.buffer_calls += 1
                return self.geom.buffer(*args, **kwargs)
        class DummyPrimitive: pass
        prim=DummyPrimitive(); prim.geom=CountingGeom(raw)
        cache={}
        first=r._component_path_keepout(prim,cache)
        second=r._component_path_keepout(prim,cache)
        historical=raw.buffer(r.component_pathway_clearance,quad_segs=4)
        self.assertEqual(prim.geom.buffer_calls,1)
        self.assertEqual(len(cache),1)
        blob=next(iter(cache.values()))
        self.assertIsInstance(blob,bytes)
        self.assertEqual(first.wkb,historical.wkb)
        self.assertEqual(second.wkb,historical.wkb)

    def test_component_fallback_reuses_precomputed_route_keepout(self):
        r = V48Renderer(seed=9090)
        cap = r.generate_isolated_capacitors(sample_seed(r.seed, 0))[0]
        # Block essentially the whole legal component field so the bounded fallback executes.
        blocker = Group('blocking-path', [prim_rect_fill(r.W/2, r.H/2, r.W-30*r.U, r.H-30*r.U, 0, r.FG)],
                        dict(placement_kind='pathway', pathway=True))
        original = r._component_candidate_valid
        missing = {'path': 0, 'chip': 0}
        def wrapped(cand, kind, chips, pathways, accepted, attachment_point=None,
                    chip_keepout=None, pathway_keepout=None, accepted_index=None, pathway_component_index=None,
                    chip_component_index=None, pathway_keepout_wkb_cache=None):
            if chip_keepout is None: missing['chip'] += 1
            if pathway_keepout is None: missing['path'] += 1
            return original(cand, kind, chips, pathways, accepted, attachment_point,
                            chip_keepout, pathway_keepout, accepted_index, pathway_component_index,
                            chip_component_index, pathway_keepout_wkb_cache)
        with mock.patch.object(r, '_component_candidate_valid', side_effect=wrapped):
            placed, stats = r.place_residual_components([], [cap], [], [blocker], SplitMix64(1234),
                                                         target=.85, fallback_attempts=12)
        self.assertEqual(stats['component_unplaced_count'], 1)
        # V29 forgot these arguments in the hot fallback loop, rebuilding the complete route
        # keepout on every random candidate.  Every placement call must receive the cached unions.
        self.assertEqual(missing['chip'], 0)
        self.assertEqual(missing['path'], 0)

    def test_post_route_component_failure_never_restarts_routing_internally(self):
        class ComponentFailureRenderer(V48Renderer):
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
                }
        r = ComponentFailureRenderer(seed=15317896771924782433)
        with self.assertRaisesRegex(RuntimeError, 'component constructive completion violated'):
            r.generate_sample(0, max_sample_restarts=4, collection_plan_attempts=128, calibration_rounds=96)
        self.assertEqual(r.route_calls, 1)

    def test_exact_quota_assignment(self):
        r = V48Renderer(seed=777)
        for i in range(100):
            rng = SplitMix64(sample_seed(r.seed, i))
            N = r.collection_count(rng)
            assigned = r.assign_collection_families(rng, N)
            self.assertNotEqual(assigned,(None,None))
            assigns, q = assigned
            self.assertEqual(sum('ic' in a['families'] for a in assigns), q['N_ic'])
            self.assertEqual(sum('dense' in a['families'] for a in assigns), q['N_dense'])
            self.assertEqual(sum(a['border'] for a in assigns), q['N_border'])
            for a in assigns:
                self.assertEqual(len(a['families']), a['family_count'])
                self.assertEqual(len(a['families']), len(set(a['families'])))

    def test_ic_arrays_are_procedural_and_connected(self):
        r = V48Renderer(seed=1)
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
        r = V48Renderer(seed=222)
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
        r = V48Renderer(seed=999)
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
        r = V48Renderer(seed=333)
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
        r = V48Renderer(seed=444)
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
        r = V48Renderer(seed=445)
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
        src = (Path(__file__).resolve().parents[2] / 'pcb_v48_renderer.py').read_text()
        self.assertNotIn('shape=rng.weighted([((1,2)', src)
        self.assertNotIn('dims=rng.weighted([((1,4)', src)
        self.assertIn('_procedural_dims(', src)

    def test_bundle_gesture_pathways_are_direct_modular_and_collision_clean(self):
        rep=self._reference_report(); r=V48Renderer((1200,1200),seed=rep['base_seed'])
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
        a=V48Renderer((1200,1200),seed=20260806); b=V48Renderer((1200,1200),seed=20260806)
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

    def test_main_chip_density_tracks_logical_zoom_area(self):
        # Absolute SVG size is presentation space; scale is a design-space zoom.  Chip density
        # still derives only from normalized logical territory.  The new default selects one
        # member of each historical opportunity pair; it does not replace the area law.
        for W,H in ((1200,1200),(1600,1600),(2400,2400)):
            for ms in (1.0,0.75,0.5,0.35):
                r=V48Renderer((W,H),seed=24680,scale=ms)
                self.assertAlmostEqual(r.canvas_territory_scale(),1.0)
                self.assertAlmostEqual(r.population_area_scale(),1.0/(ms*ms))
                T,full,frac=r.population_parts()
                counts=[r.chip_count(SplitMix64(sample_seed(r.seed,i))) for i in range(160)]
                self.assertTrue(all(0 <= c <= 2*full+(2 if frac>0 else 0) for c in counts))
                self.assertAlmostEqual(sum(counts)/len(counts),T,delta=max(.28,.10*T))
        # Extending either axis and zooming obey the same rotation-invariant logical-area law.
        a=V48Renderer((1200,6248),seed=24680,scale=.5)
        b=V48Renderer((6248,1200),seed=24680,scale=.5)
        expected=(6248/1200)/(.5**2)
        self.assertAlmostEqual(a.population_area_scale(),expected)
        self.assertAlmostEqual(a.population_area_scale(),b.population_area_scale())
        ca=[a.chip_count(SplitMix64(sample_seed(a.seed,i))) for i in range(40)]
        cb=[b.chip_count(SplitMix64(sample_seed(b.seed,i))) for i in range(40)]
        self.assertEqual(ca,cb)

    def test_v48_main_chip_density_multiplier_contract_preserves_historical_opportunities(self):
        # Bounds/default are product spec.  Multiplier 2.0 must recover the previous count law
        # exactly, including downstream RNG state, while 1.0 halves expected opportunity density.
        with self.assertRaises(ValueError): V48Renderer(seed=1,main_chip_density_multiplier=.1999)
        with self.assertRaises(ValueError): V48Renderer(seed=1,main_chip_density_multiplier=2.0001)
        with self.assertRaises(ValueError): V48Renderer(seed=1,main_run_length_multiplier=.1999)
        with self.assertRaises(ValueError): V48Renderer(seed=1,main_run_length_multiplier=3.0001)
        default=V48Renderer((1,1),scale=.5,seed=24681)  # T=4 => historical count 8, new mean 4
        restored=V48Renderer((1,1),scale=.5,seed=24681,main_chip_density_multiplier=2.0)
        low=V48Renderer((1,1),scale=.5,seed=24681,main_chip_density_multiplier=.2)
        self.assertEqual(default.main_chip_opportunity_activation_probability(),.5)
        self.assertEqual(restored.main_chip_opportunity_activation_probability(),1.0)
        self.assertEqual(low.main_chip_opportunity_activation_probability(),.1)
        ds=[]; ls=[]
        for i in range(400):
            sd=sample_seed(default.seed,i)
            rd=SplitMix64(sd); rr=SplitMix64(sd)
            ds.append(default.chip_count(rd)); c2=restored.chip_count(rr)
            self.assertEqual(c2,8)
            # Integer territory historically consumed no chip-count draws; 2.0 preserves that.
            self.assertEqual(rr.state,sd & ((1<<64)-1))
            ls.append(low.chip_count(SplitMix64(sd)))
        # Complete territories are exactly halved at the default: four historical pairs -> 4.
        self.assertEqual(set(ds),{4})
        # The raw low-density mean is .8 here; the physical one-chip floor clips zero draws.
        self.assertTrue(all(c>=1 for c in ls))
        self.assertAlmostEqual(sum(ls)/len(ls),1.21,delta=.13)
        self.assertGreater(len(set(ls)),2)
        square_low=V48Renderer((1,1),seed=999,main_chip_density_multiplier=.2)
        self.assertTrue(all(square_low.chip_count(SplitMix64(sample_seed(square_low.seed,i)))==1 for i in range(64)))

    def test_v48_main_run_length_multiplier_scales_existing_main_journey_only(self):
        # Item 4 scales the already-sampled whole-route MAIN residency pool.  0.5 restores the
        # historical journey, the new default doubles it, and 3.0 yields six times historical.
        fronts=[]
        for mult in (.5,1.0,3.0):
            r=V48Renderer(seed=24683,main_run_length_multiplier=mult)
            chip=Group('fake-chip',[prim_rect_fill(80,80,40,40,0,r.FG)],dict(placement_kind='chip'))
            planner=BundleGesturePlanner(r,sample_seed(r.seed,0),[chip])
            f=self._planner_front(planner,42001,(500.0,500.0),0,chip=0)
            fronts.append((planner,f))
        historical=fronts[0][1]['historical_max_gestures']
        self.assertEqual([f['historical_max_gestures'] for _,f in fronts],[historical]*3)
        self.assertEqual(fronts[0][1]['max_gestures'],historical)
        self.assertEqual(fronts[1][1]['max_gestures'],2*historical)
        self.assertEqual(fronts[2][1]['max_gestures'],6*historical)
        # LOCAL route life is outside this knob and therefore remains byte-for-byte unchanged.
        local=[]
        for mult in (.2,1.0,3.0):
            r=V48Renderer(seed=24684,main_run_length_multiplier=mult)
            planner=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
            local.append(self._planner_front(planner,42002,(500.0,500.0),0,chip=0)['max_gestures'])
        self.assertEqual(len(set(local)),1)

    def test_v48_main_run_length_high_setting_extends_only_existing_shared_clock_capacity(self):
        # The historical ordinary clock/RNG draw is preserved.  Default residency still fits it;
        # only high requested route life extends the same shared clock enough to realise the work.
        rows=[]
        for mult in (.5,1.0,3.0):
            r=V48Renderer(seed=24685,main_run_length_multiplier=mult)
            p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
            rows.append(p.profile)
        historical=rows[0]['historical_max_rounds']
        self.assertEqual([x['historical_max_rounds'] for x in rows],[historical]*3)
        self.assertEqual(rows[0]['max_rounds'],historical)
        self.assertEqual(rows[1]['max_rounds'],historical)
        self.assertGreaterEqual(rows[2]['max_rounds'],90)
        self.assertEqual([x['main_run_residency_factor'] for x in rows],[1.0,2.0,6.0])

    def test_v48_legal_cross_chip_head_join_wins_before_voluntary_journey_limit(self):
        # Reaching the stochastic journey target is only a voluntary free-running stop.  An
        # already-legal foreign-chip head join gets first refusal and is successful even when the
        # old probability gate would have been zero.  No search/clearance rule is bypassed.
        r=V48Renderer(seed=24686,main_run_length_multiplier=1.0)
        chips=[
            Group('chip-a',[prim_rect_fill(80,80,40,40,0,r.FG)],dict(placement_kind='chip')),
            Group('chip-b',[prim_rect_fill(1120,1120,40,40,0,r.FG)],dict(placement_kind='chip')),
        ]
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),chips)
        p.profile['connection_appetite']=0.0
        def make(seed,start,direction,chip):
            f=self._planner_front(p,seed,start,direction,chip=chip)
            f['gestures']=f['max_gestures']; f['local_gestures']=f['gestures']
            f['journey_limit_pending']=True; f['launch_egress_pending']=False
            p.fronts[f['id']]=f
            return f
        a=make(42003,(500.0,500.0),0,0)
        b=make(42004,(500.0+3.0*p.module,500.0),4,1)
        self.assertTrue(p._connection_family_compatible(a,b))
        p._connect_singletons()
        self.assertEqual((a['status'],b['status']),('connected','connected'))
        self.assertEqual(p.stats['pathway_cross_chip_connection_count'],1)
        self.assertFalse(a['journey_limit_pending']); self.assertFalse(b['journey_limit_pending'])
        self.assertNotEqual(a.get('termination_reason'),'journey_limit')
        self.assertNotEqual(b.get('termination_reason'),'journey_limit')

    def test_v48_main_chip_density_thinning_does_not_perturb_downstream_population_rng(self):
        # The knob changes chip workload only. Collection/family randomness following chip_count
        # must see the same RNG state for every density setting.
        rs=[V48Renderer((1,1.3),scale=.75,seed=24682,main_chip_density_multiplier=m)
            for m in (.2,1.0,2.0)]
        states=[]; collections=[]
        for r in rs:
            srng=SplitMix64(sample_seed(r.seed,0))
            r.chip_count(srng)
            states.append(srng.state)
            collections.append(r.collection_count(srng))
        self.assertEqual(states[0],states[1]); self.assertEqual(states[1],states[2])
        self.assertEqual(collections[0],collections[1]); self.assertEqual(collections[1],collections[2])

    def test_secondary_components_keep_main_chip_breathing_room(self):
        r=V48Renderer((1200,1200),seed=40001)
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

    def test_v48_component_chip_clearance_uses_exact_distance_not_polygonized_buffer(self):
        # Regression for the historical late ``pair_chip_isolated`` failure.  A finite-segment
        # round buffer is slightly INSIDE the true Euclidean offset between its arc vertices.
        # This fixture sits in that thin annulus: the old buffer-intersection admission gate
        # accepted it, while the final exact distance validator correctly rejected it.
        r=V48Renderer((1200,1200),seed=480020)
        U=r.U; gap=r.component_chip_clearance
        chip=Group('chip-buffer-regression',
                   [prim_rect_fill(600,600,120*U,100*U,0,r.FG)],
                   {'placement_kind':'chip','q_chip':100*U})
        x1,y1=chip.bounds[2],chip.bounds[3]
        radius=.02*U
        theta=math.radians(5.625)  # midpoint between quad_segs=8 corner-buffer vertices
        centre_radius=gap-.05*U+radius
        cx=x1+centre_radius*math.cos(theta); cy=y1+centre_radius*math.sin(theta)
        cap=Group('isolated-buffer-regression',[prim_circle(cx,cy,radius,r.FG,True)],
                  {'placement_kind':'isolated'})
        self.assertLess(chip.geom.distance(cap.geom),gap)
        self.assertFalse(cap.collision_geom.intersects(chip.geom.buffer(gap,quad_segs=8)))
        conservative=chip.geom.buffer(r._conservative_clearance_buffer_radius(gap,8),quad_segs=8)
        self.assertTrue(cap.collision_geom.intersects(conservative))
        self.assertFalse(r._component_candidate_valid(cap,'isolated',[chip],[],[]))
        self.assertEqual(r._component_chip_clearance_violation_count([cap],[chip]),1)
        errs=r.validate_sample([chip,cap],1,0,{'N_ic':0,'N_dense':0,'N_border':0})
        self.assertIn('pair_chip_isolated',errs)

    def test_v48_residual_static_clearance_certificate_is_conservative_against_exact_gap(self):
        # The fast residual field may use polygonized buffers only when they are conservative.
        # Every stored clearance must be <= the exact available Euclidean clearance, so the later
        # candidate-radius certificate can never overstate safe room near a chip.
        r=V48Renderer((1200,1200),seed=480021)
        U=r.U
        chip=Group('chip-residual-clearance',
                   [prim_rect_fill(600,600,120*U,100*U,0,r.FG)],
                   {'placement_kind':'chip','q_chip':100*U})
        r._find_residual_gap_sites([chip],[],SplitMix64(1),1)
        nx,ny=r._component_gap_grid_shape; cw=r.W/nx; ch=r.H/ny
        self.assertTrue(r._component_gap_clearance)
        for (gx,gy),stored in r._component_gap_clearance.items():
            p=Point((gx+.5)*cw,(gy+.5)*ch)
            expected=p.distance(chip.geom)-r.component_chip_clearance
            self.assertGreater(expected,0.0)
            self.assertLessEqual(stored,expected+1e-9)

    def test_routes_before_secondary_components_exist(self):
        class RouteOrderProbe(V48Renderer):
            def generate_main_pathways(self, sseed, placed):
                self.kinds_seen_by_router=[g.structural.get('placement_kind') for g in placed]
                raise RuntimeError('ROUTE_ORDER_PROBE')
        r=RouteOrderProbe(seed=20260808)
        with self.assertRaisesRegex(RuntimeError, 'ROUTE_ORDER_PROBE'):
            r.generate_sample(0,max_sample_restarts=1)
        self.assertTrue(r.kinds_seen_by_router)
        self.assertEqual(set(r.kinds_seen_by_router), {'chip'})

    def test_scale_expands_logical_viewbox_without_changing_design_geometry(self):
        a=V48Renderer((1,1),seed=9,scale=1.0)
        b=V48Renderer((1,1),seed=9,scale=0.65)
        self.assertAlmostEqual(b.W/a.W,1/0.65)
        self.assertAlmostEqual(b.H/a.H,1/0.65)
        self.assertAlmostEqual(b.U,a.U)
        ga=a.generate_chip(chip_seed(sample_seed(a.seed,0),0),0)
        gb=b.generate_chip(chip_seed(sample_seed(b.seed,0),0),0)
        self.assertAlmostEqual(gb.structural['q_chip'],ga.structural['q_chip'],places=6)
        with self.assertRaises(ValueError):
            V48Renderer(scale=0)

    def test_hard_stops_use_deferred_reroute_before_forced_termination(self):
        r=V48Renderer(seed=40002)
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
        rep=self._reference_report(); r=V48Renderer((1200,1200),seed=rep['base_seed'])
        self.assertGreater(rep['pathway_holistic_connection_pair_count'],0)
        self.assertGreater(rep['pathway_lookahead_evaluation_count'],0)
        self.assertGreater(rep['pathway_loop_candidate_reject_count'],0)
        self.assertGreater(rep['pathway_traceback_count'],0)
        self.assertGreater(rep['pathway_deep_traceback_count'],0)
        self.assertGreater(rep['pathway_recovery_fragment_count'],0)
        self.assertEqual(rep['pathway_profile']['reroute_budget'],7)
        self.assertAlmostEqual(rep['pathway_profile']['late_life_branch_start'],.60)
        self.assertAlmostEqual(rep['pathway_profile']['late_life_branch_multiplier'],1.50)
        self.assertEqual(rep['pathway_compensating_zigzag_count'],0)
        # Live scheduling contracts must be asserted from the live planner, never from a historical
        # acceptance report.  This exact mistake allowed V45/V46's deleted persistence to pass.
        p=BundleGesturePlanner(r,sample_seed(r.seed,99),[])
        self.assertGreaterEqual(p.profile['max_rounds'],48)
        self.assertLessEqual(p.profile['max_rounds'],56)
        self.assertGreaterEqual(p.profile['persistence_shared_ticks'],10)
        self.assertLessEqual(p.profile['persistence_shared_ticks'],12)
        a=self._planner_front(p,42001,(300.0,400.0),0,chip=0)
        b=self._planner_front(p,42002,(300.0+3*p.module,400.0),4,chip=1)
        for f in (a,b):
            f['gestures']=2; f['local_gestures']=2; f['launch_egress_pending']=False; f['intent']='connect'; f['travel']=5*p.module
        self.assertEqual(p._assign_round_connection_targets([a,b],1),1)
        self.assertEqual(a['round_connection_peer'],b['id'])
        a['gestures']=4; a['initial_dir']=0
        self.assertTrue(p._candidate_loop_risk(a,4,(a['path'][-1][0]-2*p.module,a['path'][-1][1])))

    def test_single_sample_invariants(self):
        r=V48Renderer(seed=20260806)
        prep=self._prepare_component_templates(r,0)
        self.assertIsNotNone(prep)
        N=prep['N']; quotas=prep['quotas']; chips=prep['chips']
        cols,_caps=prep['population']
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
        self.assertFalse(hasattr(r,'batch_fingerprints'))
        self.assertFalse(hasattr(r,'batch_buckets'))
        self.assertFalse(hasattr(r,'collection_fingerprint'))
        self.assertFalse(hasattr(r,'near_duplicate'))

    def test_cross_sample_aesthetic_history_is_absent(self):
        r=V48Renderer(seed=20260806)
        first=self._prepare_component_templates(r,0)
        self.assertIsNotNone(first)
        second=self._prepare_component_templates(r,2)
        self.assertIsNotNone(second)
        self.assertFalse(hasattr(r,'batch_fingerprints'))
        self.assertFalse(hasattr(r,'batch_buckets'))
        for population in (first['population'],second['population']):
            cols,_caps=population
            self.assertTrue(all('fingerprint' not in g.structural for g in cols))

    def test_batch_seed_totality_never_skips_failed_logical_seed(self):
        class FailFirst(V48Renderer):
            def __init__(self,*args,**kwargs):
                super().__init__(*args,**kwargs); self.calls=[]
            def generate_sample(self,sample_index=0,**kwargs):
                self.calls.append(sample_index)
                if sample_index==0:
                    raise RuntimeError('synthetic construction invariant')
                return [],dict(seed=sample_seed(self.seed,sample_index),base_seed=self.seed,
                               logical_sample_index=sample_index,renderer_identity=id(self))
            def svg_for(self,placed,report):
                return '<svg xmlns="http://www.w3.org/2000/svg"/>'
        r=FailFirst(seed=12345)
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError,'synthetic construction invariant'):
                r.render_batch(1,Path(td),max_sample_restarts=99,skip_deadlocks=True,max_logical_samples=999)
            self.assertEqual(r.calls,[0])
            self.assertEqual(list(Path(td).iterdir()),[])

    def test_generate_sample_seed_totality_never_reseeds_whole_board(self):
        class FailAssignmentOnce(V48Renderer):
            def __init__(self,*args,**kwargs):
                super().__init__(*args,**kwargs); self.assignment_calls=0
            def assign_collection_families(self,rng,N):
                self.assignment_calls+=1
                if self.assignment_calls==1:
                    return None,None
                return super().assign_collection_families(rng,N)
        r=FailAssignmentOnce(seed=12345)
        with self.assertRaisesRegex(RuntimeError,'collection family construction unexpectedly returned no assignment'):
            r.generate_sample(0,max_sample_restarts=99)
        self.assertEqual(r.assignment_calls,1)

    def test_component_hard_floor_completion_is_not_stopped_by_legacy_global_filler_cap(self):
        r=V48Renderer(seed=1)
        chip=Group('chip',[prim_rect_fill(600,600,150,100,0,r.FG)],dict(placement_kind='chip'))
        tiny=Group('tiny',[prim_circle(0,0,2*r.U,r.FG,True)],dict(family='dot'))
        # A zero legacy cap used to stop completion immediately and make the enclosing sample
        # fail its 50% hard floor.  Seed-total construction must instead terminate by consuming
        # the finite residual service field.
        r.component_extra_filler_limit=0
        placed,stats=r.place_residual_components([tiny],[],[chip],[],SplitMix64(123),target=.50)
        self.assertGreaterEqual(stats['component_residual_gap_fill_actual'],.50-1e-9)
        self.assertGreater(stats['component_residual_gap_extra_filler_count'],0)
        self.assertFalse(stats['component_residual_gap_completion_uses_legacy_filler_cap'])
        self.assertEqual(stats['component_residual_gap_extra_filler_limit'],0)

    def test_v38_space_aware_causal_contract(self):
        rep=self._reference_report(); r=V48Renderer((1200,1200),seed=rep['base_seed'])
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

    def test_v46_canonical_design_scale_and_population_follow_logical_territory_only(self):
        # Use density=2.0 to isolate the historical territory law from the new density knob.
        r=V48Renderer((1,1),seed=1,main_chip_density_multiplier=2.0)
        self.assertAlmostEqual(r.S,1200.0)
        self.assertAlmostEqual(r.U,0.75)
        self.assertAlmostEqual(r.chip_chip_clearance,322.5)
        self.assertEqual(r.chip_count_probability(),0.0)
        class Fixed:
            def __init__(self,*xs): self.xs=list(xs); self.i=0
            def random(self):
                x=self.xs[min(self.i,len(self.xs)-1)]; self.i+=1; return x
        self.assertEqual(r.chip_count(Fixed(0.0)),2)
        self.assertEqual(V48Renderer((2400,2400),seed=1,main_chip_density_multiplier=2.0).chip_count(Fixed(.999999)),2)
        ext=V48Renderer((2,3),seed=1,main_chip_density_multiplier=2.0)
        self.assertAlmostEqual(ext.chip_count_probability(),0.5)
        self.assertEqual(ext.chip_count(Fixed(.4,.6)),3)
        self.assertEqual(ext.chip_count(Fixed(.6,.6)),2)
        self.assertEqual(V48Renderer((2,3),seed=1,scale=.5,main_chip_density_multiplier=2.0).chip_count_probability(),0.0)

    def test_v38_traceback_blacklists_actual_replayed_corridor_at_rollback_junction(self):
        r=V48Renderer(seed=340034)
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
        r=V48Renderer((1200,1200),seed=99)
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
        r=V48Renderer((1200,1200),seed=100)
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
        r=V48Renderer(seed=37001)
        rng=SplitMix64(37002)
        medium=dict(short_span=90*r.U,cell_count=18)
        large=dict(short_span=180*r.U,cell_count=60)
        for i,reg in enumerate((medium,large)):
            g=r._make_residual_filler_component(rng,i,reg)
            self.assertTrue(g.structural.get('residual_compound'))
            self.assertFalse(g.structural.get('residual_micro'))
            self.assertGreaterEqual(g.structural.get('residual_assembly_family_count',0),2)

    def test_residual_micro_tokens_are_region_gated_and_capped(self):
        r=V48Renderer(seed=37003)
        rng=SplitMix64(37004)
        micro=dict(short_span=20*r.U,cell_count=2)
        g=r._make_residual_filler_component(rng,0,micro)
        self.assertTrue(g.structural.get('residual_micro'))
        self.assertFalse(g.structural.get('residual_compound'))
        self.assertEqual(r.component_micro_filler_limit,8)

    def test_reference_seed_residual_completion_is_compound_dominant(self):
        rep=self._reference_report(); r=V48Renderer((1200,1200),seed=rep['base_seed'])
        self.assertGreaterEqual(rep['component_residual_gap_fill_actual'],0.50)
        self.assertLessEqual(rep['component_residual_gap_fill_actual'],0.62)
        self.assertLessEqual(rep['component_residual_gap_micro_filler_count'],r.component_micro_filler_limit)
        self.assertGreaterEqual(rep['component_residual_gap_compound_filler_fraction'],0.75)
        self.assertEqual(rep.get('local_component_clearance_violation_count',0),0)

    def test_v39_exact_dir8_rejects_non_octilinear_segment(self):
        self.assertEqual(exact_dir8_index(12.0,0.0),0)
        self.assertEqual(exact_dir8_index(5.0,-5.0),1)
        self.assertIsNone(exact_dir8_index(10.0,3.0))

    def test_v39_connection_junction_rejects_90_allows_45(self):
        r=V48Renderer((1200,1200),seed=39001)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        self.assertFalse(p._connection_junction_turn_ok([(0.0,0.0),(10.0,0.0)],[(10.0,10.0),(10.0,0.0)]))
        self.assertTrue(p._connection_junction_turn_ok([(0.0,0.0),(10.0,0.0)],[(20.0,10.0),(10.0,0.0)]))

    def test_v39_commit_rejects_direct_90_degree_turn(self):
        r=V48Renderer((1200,1200),seed=38001)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        f=self._planner_front(p,38002,(200.0,200.0),0,chip=0)
        # Give the front one already-materialized eastbound leg.  A direct southbound commit
        # is a two-octant / 90-degree corner and must fail before it can enter path history.
        f['path']=[(160.0,200.0),(200.0,200.0)]; f['dir']=0; f['gestures']=1; f['local_gestures']=1
        end=(200.0,160.0); g=p._corridor_geom(f,f['path'][-1],end)
        bad=dict(front=f['id'],start=f['path'][-1],end=end,dir=2,modules=2,geom=g,score=1.0)
        with self.assertRaisesRegex(RuntimeError,'illegal pathway turn at commit'):
            p._accept(f,bad,defer_post=True)

    def test_v46_reference_local_fill_is_bent_dominant_and_45_degree_only(self):
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

    def test_v46_local_grid_preserves_reference_physical_cell_size(self):
        square=V48Renderer((1200,1200),seed=42001)
        self.assertEqual(square.local_gap_grid_shape(),(56,56))
        for W,H,expected in ((1200,6248,(56,292)),(1200,8046,(56,375)),(6248,1200,(292,56))):
            r=V48Renderer((W,H),seed=42001)
            self.assertEqual(r.local_gap_grid_shape(),expected)
            nx,ny=expected
            cw=W/nx; ch=H/ny
            self.assertLess(abs(cw-ch)/max(cw,ch),0.012)

    def test_v46_component_grid_preserves_physical_locality_and_rotation(self):
        expected={(1200,1200):(56,56),(1200,6248):(56,292),(1200,8046):(56,375),
                  (6248,1200):(292,56),(8046,1200):(375,56)}
        for (W,H),shape in expected.items():
            r=V48Renderer((W,H),seed=42002)
            self.assertEqual(r.component_gap_grid_shape(),shape)
            self.assertEqual(r.component_gap_grid_n,56)
            nx,ny=shape; cw=W/nx; ch=H/ny
            self.assertLess(abs(cw-ch)/max(cw,ch),0.012)

    def test_v46_local_work_allowance_is_linear_in_normalized_territory(self):
        r=V48Renderer((1200,8046),seed=42003)
        area=r.population_area_scale()
        self.assertAlmostEqual(area,8046/1200)
        self.assertAlmostEqual(r.local_pathway_work_scale(),area)
        self.assertEqual(r.local_pathway_gesture_check_budget,22000)
        self.assertEqual(int(math.ceil(r.local_pathway_gesture_check_budget*r.local_pathway_work_scale())),
                         int(math.ceil(22000*area)))
        self.assertEqual(r.local_fragment_mopup_cap(),math.ceil(40*area))
        # Territory scales the opportunity *inside* a wave; the number of whole-board rescans
        # is deliberately bounded so extended canvases stay stationary instead of O(T^2).
        self.assertEqual(r.local_wave_source_cap(),math.ceil(24*area))
        self.assertEqual(r.local_branch_birth_cap(),math.ceil(2*area))
        self.assertEqual(r.local_late_wave_cap(),2)
        self.assertEqual(r.local_hard_floor_rescue_cap(),3)
        square=V48Renderer((1200,1200),seed=42003)
        self.assertEqual(square.local_fragment_mopup_cap(),0)
        self.assertEqual(square.local_late_wave_cap(),0)
        self.assertEqual(square.local_hard_floor_rescue_cap(),3)


    def test_v46_population_area_scale_is_rotation_invariant_and_zoom_scaled(self):
        for W,H in ((1200,6248),(6248,1200),(1200,8046),(8046,1200)):
            for ms in (1.0,.5,.35):
                a=V48Renderer((W,H),seed=43001,scale=ms)
                b=V48Renderer((H,W),seed=43001,scale=ms)
                expected=(max(W,H)/min(W,H))/(ms**2)
                self.assertAlmostEqual(a.population_area_scale(),b.population_area_scale())
                self.assertAlmostEqual(a.population_area_scale(),expected)

    def test_v46_fractional_chip_opportunities_are_independent(self):
        # At density=2.0 the historical law is exact: T=1.25 => two Bernoulli(.25)
        # fractional opportunities, independently consuming the original stream.
        r=V48Renderer((1200,1500),seed=43002,main_chip_density_multiplier=2.0)
        class Fixed:
            def __init__(self,vals): self.vals=iter(vals)
            def random(self): return next(self.vals)
        self.assertEqual(r.chip_count(Fixed([.1,.1])),4)
        self.assertEqual(r.chip_count(Fixed([.1,.9])),3)
        self.assertEqual(r.chip_count(Fixed([.9,.1])),3)
        self.assertEqual(r.chip_count(Fixed([.9,.9])),2)

    def test_v46_prepared_collection_distribution_transposes_exactly(self):
        a=V48Renderer((1200,6248),seed=43003); b=V48Renderer((6248,1200),seed=43003)
        for i in range(40):
            sa=SplitMix64(sample_seed(a.seed,i)); sb=SplitMix64(sample_seed(b.seed,i))
            # Consume chip-count draws first, exactly as production does.
            self.assertEqual(a.chip_count(sa),b.chip_count(sb))
            self.assertEqual(a.collection_count(sa),b.collection_count(sb))

    def test_v46_population_caps_are_rotation_invariant_and_territory_scaled(self):
        for W,H in ((1200,6248),(6248,1200),(1200,8046),(8046,1200)):
            a=V48Renderer((W,H),seed=43004); b=V48Renderer((H,W),seed=43004)
            self.assertEqual(a.component_extra_filler_limit,b.component_extra_filler_limit)
            self.assertEqual(a.component_micro_filler_limit,b.component_micro_filler_limit)
            self.assertEqual(a.component_density_cap,b.component_density_cap)
            self.assertEqual(a.local_gap_trace_population_cap(),b.local_gap_trace_population_cap())
            T=a.population_area_scale()
            self.assertEqual(a.component_extra_filler_limit,max(96,math.ceil(96*T)))
            self.assertEqual(a.component_micro_filler_limit,max(8,math.ceil(8*T)))

    def test_v46_main_gesture_budget_is_territory_scaled_and_rotation_invariant(self):
        a=V48Renderer((1200,6248),seed=43005); b=V48Renderer((6248,1200),seed=43005)
        self.assertEqual(a.main_pathway_gesture_check_budget,b.main_pathway_gesture_check_budget)
        self.assertEqual(a.main_pathway_gesture_check_budget,math.ceil(52000*a.population_area_scale()))

    def test_v46_service_grids_transpose_under_rotation(self):
        for W,H in ((1200,6248),(1200,8046),(1800,3000)):
            a=V48Renderer((W,H),seed=43006); b=V48Renderer((H,W),seed=43006)
            anx,any_=a.local_gap_grid_shape(); bnx,bny=b.local_gap_grid_shape()
            self.assertEqual((anx,any_),(bny,bnx))
            anx,any_=a.component_gap_grid_shape(); bnx,bny=b.component_gap_grid_shape()
            self.assertEqual((anx,any_),(bny,bnx))

    def test_v46_main_chip_placement_spans_every_long_axis_quarter_across_maintained_seeds(self):
        def quarter_counts(W,H,seed):
            r=V48Renderer((W,H),seed=seed); ss=sample_seed(seed,0); rng=SplitMix64(ss)
            n=r.chip_count(rng); chips=[]; sigs=set()
            for j in range(n):
                base=chip_seed(ss,j); g=None
                for rr in range(128):
                    try: cand=r.generate_chip(retry_seed(base,rr) if rr else base,j)
                    except RuntimeError: continue
                    sig=(cand.structural.get('orientation'),cand.structural.get('aspect_bin'),cand.structural.get('motifs'),
                         cand.structural.get('inner_border_count'),cand.structural.get('exterior_side_set_configuration'))
                    if sig not in sigs: g=cand; sigs.add(sig); break
                self.assertIsNotNone(g); chips.append(g)
            placed=r.place_objects(chips,[],[],SplitMix64(placement_seed(ss)))
            self.assertIsNotNone(placed)
            vals=[]
            for g in placed:
                cx=(g.bounds[0]+g.bounds[2])/2; cy=(g.bounds[1]+g.bounds[3])/2
                vals.append(cy/H if H>=W else cx/W)
            q=[0,0,0,0]
            for v in vals: q[min(3,int(v*4))]+=1
            return q
        for seed in (430071,430072,430073,430074,430075):
            for W,H in ((1200,6248),(6248,1200)):
                q=quarter_counts(W,H,seed)
                # The half-density default must still span the long axis without changing the
                # placement algorithm merely to keep an old high-population occupancy test true.
                self.assertGreater(q[0],0); self.assertGreater(q[3],0)
                self.assertGreaterEqual(sum(bool(x) for x in q),3)

        # At multiplier 2.0 the historical population is restored, so the historical every-
        # quarter maintained-seed coverage remains exact.
        def quarter_counts_restored(W,H,seed):
            r=V48Renderer((W,H),seed=seed,main_chip_density_multiplier=2.0); ss=sample_seed(seed,0); rng=SplitMix64(ss)
            n=r.chip_count(rng); chips=[]; sigs=set()
            for j in range(n):
                base=chip_seed(ss,j); g=None
                for rr in range(128):
                    try: cand=r.generate_chip(retry_seed(base,rr) if rr else base,j)
                    except RuntimeError: continue
                    sig=(cand.structural.get('orientation'),cand.structural.get('aspect_bin'),cand.structural.get('motifs'),
                         cand.structural.get('inner_border_count'),cand.structural.get('exterior_side_set_configuration'))
                    if sig not in sigs: g=cand; sigs.add(sig); break
                self.assertIsNotNone(g); chips.append(g)
            placed=r.place_objects(chips,[],[],SplitMix64(placement_seed(ss)))
            self.assertIsNotNone(placed)
            q=[0,0,0,0]
            for g in placed:
                cx=(g.bounds[0]+g.bounds[2])/2; cy=(g.bounds[1]+g.bounds[3])/2
                v=cy/H if H>=W else cx/W
                q[min(3,int(v*4))]+=1
            return q
        for seed in (430071,430072,430073,430074,430075):
            self.assertTrue(all(quarter_counts_restored(1200,6248,seed)))
            self.assertTrue(all(quarter_counts_restored(6248,1200,seed)))

    def test_v46_local_target_work_is_chunk_bounded_not_aspect_triggered(self):
        src=(Path(__file__).resolve().parents[2]/'pcb_v48_renderer.py').read_text()
        self.assertNotIn('tall_area_scale() > 1.25 and len(pool)',src)
        self.assertIn('self.local_gap_chunk_span=6',src)
        self.assertIn('def _local_gap_target_chunk(',src)
        self.assertIn('for step in range(1,5):',src)
        self.assertIn('_local_gap_extreme_shortlist(None,targetable,hint,96)',src)
        self.assertNotIn('heapq.nlargest(512,pool',src)

    def test_v46_local_branch_trace_cap_is_stationary_per_territory(self):
        sq=V48Renderer((1200,1200),seed=43009)
        p=V48Renderer((1200,6248),seed=43009); l=V48Renderer((6248,1200),seed=43009)
        self.assertEqual(sq.local_gap_trace_population_cap(),256)
        self.assertEqual(p.local_gap_trace_population_cap(),l.local_gap_trace_population_cap())
        self.assertEqual(p.local_gap_trace_population_cap(),math.ceil(256*p.population_area_scale()))

    def test_v46_local_budget_scales_exactly_once_not_quadratically(self):
        r=V48Renderer((1200,6248),seed=43010)
        self.assertEqual(r.local_pathway_gesture_check_budget,22000)
        final=math.ceil(r.local_pathway_gesture_check_budget*r.local_pathway_work_scale())
        self.assertEqual(final,math.ceil(22000*r.population_area_scale()))
        self.assertLess(final,22000*r.population_area_scale()**2)

    def test_v46_no_fixed_component_service_grid_on_extended_canvas(self):
        sq=V48Renderer((1200,1200),seed=43011)
        ext=V48Renderer((1200,6248),seed=43011)
        self.assertEqual(sq.component_gap_grid_shape(),(56,56))
        self.assertGreater(ext.component_gap_grid_shape()[1],56)
        self.assertAlmostEqual((1200/56),(6248/ext.component_gap_grid_shape()[1]),delta=.3)

    def test_v46_fragment_region_priority_handles_none_and_numeric_ids(self):
        items=[(7,None),(7,2),(9,None),(7,1)]
        ordered=sorted(items,key=BundleGesturePlanner._local_region_priority_key,reverse=True)
        self.assertEqual(ordered[0],(9,None))
        self.assertEqual(ordered[1:3],[(7,2),(7,1)])
        self.assertEqual(ordered[-1],(7,None))

    def test_v46_hard_floor_reserve_is_not_cancelled_by_one_zero_gain_wave(self):
        src=(Path(__file__).resolve().parents[2]/'pcb_v48_renderer.py').read_text()
        start=src.index('while (self._local_gap_service_fraction()+1e-9 < hard_floor_abs and rescue_count<rescue_cap):')
        end=src.index("self.stats['pathway_local_gap_hard_floor_rescue_wave_count']",start)
        block=src[start:end]
        self.assertNotIn('after<=before',block)
        self.assertIn('rescue_count+=1',block)
        self.assertIn('if not spawned: break',block)

    def test_v46_local_region_source_ceiling_is_stationary_per_territory(self):
        sq=V48Renderer((1200,1200),seed=43013)
        portrait=V48Renderer((1200,8046),seed=43013)
        landscape=V48Renderer((8046,1200),seed=43013)
        huge=10**9
        self.assertEqual(sq.local_gap_region_source_cap(huge),34)
        expected=math.ceil(34*portrait.population_area_scale())
        self.assertEqual(portrait.local_gap_region_source_cap(huge),expected)
        self.assertEqual(landscape.local_gap_region_source_cap(huge),expected)
        # Local area still wins for genuinely small rooms.
        self.assertEqual(portrait.local_gap_region_source_cap(32),2)

    def test_v46_partial_service_retarget_uses_same_area_metric_as_hard_floor(self):
        r=V48Renderer((1200,1200),seed=43014)
        p=BundleGesturePlanner(r,43014,[])
        p.local_gap_open_cells={(0,0),(1,0),(2,0)}
        p.local_gap_coverage_touched_cells={(0,0),(1,0)}
        p.local_gap_untouched_cells={(2,0)}
        p.local_gap_coverage_mask_by_cell={(0,0):(1<<4)-1,(1,0):(1<<13)-1}
        self.assertEqual(p._local_gap_covered_cells(),{(0,0),(1,0)})
        p.local_gap_retarget_cells={(0,0)}
        self.assertEqual(p._local_gap_covered_cells(),{(1,0)})
        # Service itself is untouched by retargeting; only candidate eligibility changes.
        # The canonical denominator is the original post-MAIN service field, not the smaller
        # physical post-component routing field.  This guards against the historical double
        # normalization that overstated LOCAL's 80-90%-of-remainder result.
        p.local_gap_served_subcell_count=17
        p.local_gap_service_denominator_cell_count=5
        before=p._local_gap_service_fraction()
        self.assertAlmostEqual(before,17/(5*16))
        self.assertAlmostEqual(p._local_gap_physical_post_component_service_fraction(),17/(3*16))
        self.assertNotAlmostEqual(before,p._local_gap_physical_post_component_service_fraction())
        p.local_gap_retarget_cells=set()
        self.assertEqual(p._local_gap_service_fraction(),before)


    def test_v46_fine_scale_service_and_main_grids_follow_design_unit_not_canvas_pixels(self):
        # Every spatial bookkeeping grid follows design-local distance.  Zooming out exposes
        # more logical cells on the same SVG for main routing and residual service alike.
        cases={
            (1200,1200):(160,160),
            (1200,6248):(160,833),
            (6248,1200):(833,160),
            (1200,8046):(160,1073),
            (8046,1200):(1073,160),
        }
        for (W,H),shape in cases.items():
            r=V48Renderer((W,H),seed=44001,scale=.35)
            self.assertEqual(r.component_gap_grid_shape(),shape)
            self.assertEqual(r.local_gap_grid_shape(),shape)
            self.assertEqual(r._aspect_grid_shape(56),shape)

    def test_v46_fine_scale_expands_primary_population_and_detail_capacity_together(self):
        for W,H in ((1200,1200),(1200,6248),(6248,1200),(1200,8046)):
            a=V48Renderer((W,H),seed=44002,scale=1.0)
            b=V48Renderer((W,H),seed=44002,scale=.35)
            expected=a.population_area_scale()/(.35**2)
            self.assertAlmostEqual(b.population_area_scale(),expected)
            self.assertAlmostEqual(b.design_detail_area_scale(),expected)
            self.assertAlmostEqual(b.design_distance_scale(),1/.35)
            # Fine scale must create genuinely more primary population opportunity, not merely
            # shrink the old sparse layout and let residual filler compensate for it.
            for i in range(12):
                ra=SplitMix64(sample_seed(a.seed,i)); rb=SplitMix64(sample_seed(b.seed,i))
                ca=a.chip_count(ra); cb=b.chip_count(rb)
                self.assertGreater(cb,ca)
                na=a.collection_count(ra); nb=b.collection_count(rb)
                self.assertGreater(nb,na)
            self.assertEqual(b.component_extra_filler_limit,max(96,math.ceil(96*expected)))
            self.assertEqual(b.component_micro_filler_limit,max(8,math.ceil(8*expected)))
            self.assertEqual(b.component_density_cap,max(300,math.ceil(300*expected)))
            self.assertEqual(b.local_gap_trace_population_cap(),max(256,math.ceil(256*expected)))

    def test_v46_fine_scale_work_budgets_scale_by_logical_area(self):
        r=V48Renderer((1200,6248),seed=44003,scale=.35)
        T=r.population_area_scale(); D=r.design_detail_area_scale()
        self.assertAlmostEqual(T,D)
        self.assertEqual(r.main_pathway_gesture_check_budget,math.ceil(52000*T))
        self.assertEqual(r.local_pathway_gesture_check_budget,22000)
        self.assertEqual(math.ceil(r.local_pathway_gesture_check_budget*r.local_pathway_work_scale()),math.ceil(22000*D))
        self.assertEqual(r.local_fragment_mopup_cap(),math.ceil(40*D))
        self.assertEqual(r.local_wave_source_cap(),math.ceil(24*D))
        self.assertEqual(r.local_branch_birth_cap(),math.ceil(2*D))
        self.assertEqual(r.local_late_wave_cap(),2)
        self.assertEqual(r.local_hard_floor_rescue_cap(),3)

    def test_v46_fragment_child_first_gesture_cannot_complete_inherited_zigzag(self):
        r=V48Renderer((1200,6248),seed=44004,scale=.35)
        p=BundleGesturePlanner(r,44004,[])
        # Exact shape of the scale-.35 failure class: inherited ...A,B,A then the newborn
        # fragment tries B as its first centerline gesture. The prefix by itself is legal at the
        # two-module boundary; B would turn it into the forbidden repeated weave A,B,A,B.
        old_pref=[
            (1022.4356079562618,3133.215094558349),
            (1022.4356079562618,3092.6385263660827),
            (1022.4356079562618,3072.3502422699494),
            (1022.4356079562618,3021.6295320296163),
            (1022.4356079562618,3002.2008233074166),
            (1036.7815912192768,2987.8548400444015),
            (1036.7815912192768,2956.562838526268),
        ]
        pref=[(x/.35,y/.35) for x,y in old_pref]
        tid=353
        f={'path':[pref[-1]],'dir':6,'ids':[tid],'offsets':{tid:0.0},'prefixes':{tid:pref}}
        bad=(1058.3005661137993/.35,2935.0438636317454/.35)
        straight=(1036.7815912192768/.35,2936.274554430135/.35)
        self.assertFalse(p._visible_lane_tail_grammar_ok(f,bad))
        self.assertTrue(p._visible_lane_tail_grammar_ok(f,straight))

    def test_v46_incremental_local_targetable_sets_match_legacy_set_semantics(self):
        r=V48Renderer((1200,1200),seed=44005,scale=.35)
        p=BundleGesturePlanner(r,44005,[])
        cells={(0,0),(1,0),(2,0),(3,0)}
        p.local_gap_open_cells=set(cells)
        p.local_gap_regions=[dict(id=0,cells=set(cells),cell_count=4,center=(0,0),width=1,height=1,
                                  short_span=1,long_span=4,dir=0,size='small')]
        p.local_gap_region_by_cell={c:0 for c in cells}
        p.local_gap_coverage_touched_cells={(0,0),(1,0)}
        p.local_gap_untouched_cells={(2,0),(3,0)}
        p.local_gap_untouched_by_region={0:{(2,0),(3,0)}}
        self.assertEqual(set(p._local_gap_targetable_cells()),cells-p.local_gap_coverage_touched_cells)
        self.assertEqual(set(p._local_gap_targetable_cells(0)),{(2,0),(3,0)})
        p.local_gap_retarget_cells={(1,0)}
        expected=cells-(p.local_gap_coverage_touched_cells-p.local_gap_retarget_cells)
        self.assertEqual(set(p._local_gap_targetable_cells()),expected)
        self.assertEqual(set(p._local_gap_targetable_cells(0)),expected)

    def test_v46_local_first_touch_updates_incremental_targeting_and_capture(self):
        r=V48Renderer((1200,1200),seed=44006,scale=1.0)
        p=BundleGesturePlanner(r,44006,[])
        nx,ny=r.local_gap_grid_shape(); cw=r.W/nx; ch=r.H/ny
        cells={(27,27),(28,27)}
        p.local_gap_open_cells=set(cells)
        p.local_gap_regions=[dict(id=0,cells=set(cells),cell_count=2,center=(28*cw,27.5*ch),
                                  width=2*cw,height=ch,short_span=ch,long_span=2*cw,dir=0,size='small')]
        p.local_gap_region_by_cell={c:0 for c in cells}
        p.local_gap_untouched_cells=set(cells)
        p.local_gap_untouched_by_region={0:set(cells)}
        p.local_gap_region_touch_version={0:0}
        p._local_gap_new_touch_capture=set()
        f={'ids':[1],'thicknesses':{1:2.55*r.U}}
        a=((27+.5)*cw,(27+.5)*ch); b=((28+.5)*cw,(27+.5)*ch)
        p._mark_local_gap_segment_coverage(a,b,f)
        captured=set(p._local_gap_new_touch_capture)
        p._local_gap_new_touch_capture=None
        self.assertTrue(captured)
        self.assertTrue(captured <= cells)
        self.assertTrue(captured.isdisjoint(p.local_gap_untouched_cells))
        self.assertEqual(p.local_gap_untouched_by_region[0],p.local_gap_untouched_cells)
        self.assertEqual(p.local_gap_region_touch_version[0],len(captured))

    def test_v47_direct_mopup_safety_opportunity_tracks_logical_territory(self):
        # The historical 96-line reserve remains naturally inactive through the healthy
        # 0.75 reference, then grows with logical territory so a square-era constant cannot
        # force fine-scale boards prematurely into expensive rescue regimes.
        self.assertEqual(V48Renderer((1200,1200),seed=440059,scale=1.0).local_direct_mopup_cap(),96)
        self.assertEqual(V48Renderer((1200,1200),seed=440059,scale=.75).local_direct_mopup_cap(),96)
        self.assertEqual(V48Renderer((1200,1200),seed=440059,scale=.55).local_direct_mopup_cap(),179)
        self.assertEqual(V48Renderer((1200,1200),seed=440059,scale=.5).local_direct_mopup_cap(),216)

    def test_v48_quarantined_direct_run_families_retire_from_live_region_scan(self):
        # LOCAL-1 is a bookkeeping optimization only: a family that reaches the existing
        # invariant retry cap leaves the live region cache before the next scan instead of
        # being rediscovered and membership-skipped on every later successful iteration.
        src=(Path(__file__).resolve().parents[2]/'pcb_v48_renderer.py').read_text()
        start=src.index('def _local_gap_direct_mopup(')
        end=src.index('def _local_gap_fragment_mopup(',start)
        block=src[start:end]
        self.assertIn('direct_run_family_dirty_regions=set()',block)
        self.assertIn('direct_run_family_dirty_regions.add(run_family_key[0])',block)
        self.assertIn("if r['id'] in direct_run_family_dirty_regions:",block)
        self.assertIn('enriched=[item for item in enriched if item[4] not in direct_run_family_quarantined]',block)
        live_loop=block[block.index('for L,runlen,a,b,run_family_key in enriched:'):block.index('if not candidates: break')]
        self.assertNotIn('run_family_key in direct_run_family_quarantined',live_loop)

    def test_v47_direct_run_family_attempt_budget_is_scale_and_aspect_invariant(self):
        # More territory creates more independent local corridor families; it must not buy more
        # stochastic polling of one unchanged family.
        cases=[
            ((1200,1200),1.0),((1200,1200),.75),((1200,1200),.55),((1200,1200),.5),
            ((1200,6248),1.0),((1200,6248),.35),
        ]
        for aspect,scale in cases:
            self.assertEqual(V48Renderer(aspect,seed=440063,scale=scale).local_direct_run_family_attempt_cap(),3)

    def test_v47_direct_failure_certificate_is_one_sided_and_thickness_monotonic(self):
        cache={}
        key=('first',10.0,20.0,30.0,40.0)
        BundleGesturePlanner._local_direct_failure_cert_record(cache,key,2.5)
        self.assertFalse(BundleGesturePlanner._local_direct_failure_cert_should_skip(cache,key,2.49))
        self.assertTrue(BundleGesturePlanner._local_direct_failure_cert_should_skip(cache,key,2.5))
        self.assertTrue(BundleGesturePlanner._local_direct_failure_cert_should_skip(cache,key,3.0))
        # A thinner exact failure tightens the certificate; a thicker one may not weaken it.
        BundleGesturePlanner._local_direct_failure_cert_record(cache,key,2.0)
        BundleGesturePlanner._local_direct_failure_cert_record(cache,key,2.8)
        self.assertEqual(cache[key],2.0)
        self.assertFalse(BundleGesturePlanner._local_direct_failure_cert_should_skip(cache,key,1.99))
        self.assertTrue(BundleGesturePlanner._local_direct_failure_cert_should_skip(cache,key,2.0))

    def test_v47_fragment_candidate_work_budget_scales_with_territory_not_successes(self):
        self.assertEqual(V48Renderer((1200,1200),seed=440060,scale=1.0).local_fragment_candidate_work_cap(),500)
        self.assertEqual(V48Renderer((1200,1200),seed=440060,scale=.75).local_fragment_candidate_work_cap(),889)
        self.assertEqual(V48Renderer((1200,1200),seed=440060,scale=.5).local_fragment_candidate_work_cap(),2000)


    def test_v47_emergency_service_debt_cleanup_targets_hard_floor_not_sampled_preference(self):
        # The partial-service direct/fragment reserve is an emergency floor repair.  It must
        # temporarily stop on hard_floor_abs rather than continuing toward the optional sampled
        # 80-90% preference, then restore the sampled target afterwards.
        src=(Path(__file__).resolve().parents[2]/'pcb_v48_renderer.py').read_text()
        start=src.index("if self._local_gap_service_fraction()+1e-9 < hard_floor_abs:", src.index("# Canonical service-debt reserve"))
        end=src.index("partial_cap=self.r.local_hard_floor_rescue_cap()", start)
        block=src[start:end]
        self.assertIn("_saved_local_target=self.local_gap_target_fraction",block)
        self.assertIn("self.local_gap_target_fraction=hard_floor_abs",block)
        self.assertIn("self.local_gap_target_fraction=_saved_local_target",block)

    def test_v47_hard_floor_rescue_transitions_from_binary_spread_to_subcell_debt(self):
        # Broad ordinary rescue is a binary untouched-cell spread opportunity.  Once those two
        # opportunities are exhausted, remaining hard-floor deficit must be ranked by the same
        # subcell service debt that the 80% invariant measures, without a global normal-mode tax.
        src=(Path(__file__).resolve().parents[2]/'pcb_v48_renderer.py').read_text()
        run_start=src.index('# Hard-floor reserve:')
        run_end=src.index('partial_cap=self.r.local_hard_floor_rescue_cap()',run_start)
        block=src[run_start:run_end]
        self.assertIn('rescue_cap=min(2,self.r.local_hard_floor_rescue_cap())',block)
        self.assertIn('self._local_gap_service_debt_priority_by_region=_debt_by_region',block)
        self.assertIn('self._local_gap_service_debt_touch_capture=None',block)
        direct_start=src.index('def _local_gap_direct_mopup(')
        direct_end=src.index('def _local_gap_fragment_mopup(',direct_start)
        direct=src[direct_start:direct_end]
        self.assertIn("debt_priority_by_region=getattr(self,'_local_gap_service_debt_priority_by_region',None)",direct)
        self.assertIn('served_priority=plan_service_priority(served_cells)',direct)
        self.assertIn("self._local_gap_service_debt_touch_capture={}",direct)
        coverage_start=src.index('def _mark_local_gap_segment_coverage(')
        coverage_end=src.index('def _local_gap_service_fraction(',coverage_start)
        coverage=src[coverage_start:coverage_end]
        self.assertIn("_debt_capture=getattr(self,'_local_gap_service_debt_touch_capture',None)",coverage)

    def test_v47_partial_service_candidate_work_budget_scales_with_territory(self):
        self.assertEqual(V48Renderer((1200,1200),seed=440062,scale=1.0).local_partial_service_candidate_work_cap(),600)
        self.assertEqual(V48Renderer((1200,1200),seed=440062,scale=.75).local_partial_service_candidate_work_cap(),1067)
        self.assertEqual(V48Renderer((1200,1200),seed=440062,scale=.5).local_partial_service_candidate_work_cap(),2400)

    def test_v47_partial_service_debt_retires_live_at_thirteen_subcells(self):
        r=V48Renderer((1200,1200),seed=440061,scale=1.0)
        p=BundleGesturePlanner(r,440061,[])
        nx,ny=r.local_gap_grid_shape(); cw=r.W/nx; ch=r.H/ny
        cell=(27,27); full=(1<<16)-1
        p.local_gap_open_cells={cell}
        p.local_gap_regions=[dict(id=0,cells={cell},cell_count=1,center=((27.5)*cw,(27.5)*ch),
                                  width=cw,height=ch,short_span=ch,long_span=cw,dir=0,size='small')]
        p.local_gap_region_by_cell={cell:0}
        p.local_gap_region_touch_version={0:0}
        # Leave the second subcell row unpaid; a horizontal service ribbon through the cell
        # necessarily adds at least one of those bits and crosses the 13/16 eligibility floor.
        p.local_gap_coverage_mask_by_cell={cell:full ^ (0xF<<4)}
        p.local_gap_served_subcell_count=12
        p.local_gap_coverage_touched_cells={cell}
        p.local_gap_untouched_cells=set(); p.local_gap_untouched_by_region={0:set()}
        p.local_gap_retarget_cells={cell}
        f={'ids':[1],'thicknesses':{1:2.55*r.U}}
        a=(27.05*cw,27.5*ch); b=(27.95*cw,27.5*ch)
        p._mark_local_gap_segment_coverage(a,b,f)
        self.assertGreaterEqual(p.local_gap_coverage_mask_by_cell[cell].bit_count(),13)
        self.assertNotIn(cell,p.local_gap_retarget_cells)
        self.assertEqual(p.local_gap_region_touch_version[0],1)

    def test_v46_local_coverage_rebuild_resynchronizes_incremental_targeting(self):
        r=V48Renderer((1200,1200),seed=44007,scale=1.0)
        p=BundleGesturePlanner(r,44007,[])
        cells={(10,10),(11,10)}
        p.local_gap_open_cells=set(cells)
        p.local_gap_regions=[dict(id=0,cells=set(cells),cell_count=2,center=(0,0),width=1,height=1,
                                  short_span=1,long_span=2,dir=0,size='small')]
        p.local_gap_region_by_cell={c:0 for c in cells}
        p.local_gap_coverage_touched_cells={(10,10)}
        p.local_gap_coverage_mask_by_cell={(10,10):1}
        p.local_gap_untouched_cells={(11,10)}
        p.local_gap_untouched_by_region={0:{(11,10)}}
        p.local_gap_region_touch_version={0:1}
        p.path_segments=[]
        p.frozen_main_render_records=[]
        p._rebuild_path_index_and_coverage(rebuild_local_coverage=True)
        self.assertEqual(p.local_gap_coverage_touched_cells,set())
        self.assertEqual(p.local_gap_coverage_mask_by_cell,{})
        self.assertEqual(p.local_gap_untouched_cells,cells)
        self.assertEqual(p.local_gap_untouched_by_region[0],cells)
        self.assertEqual(p.local_gap_region_touch_version[0],0)

    def test_v46_local_visible_markers_preserve_frozen_component_moat(self):
        """Final local admission covers marker extent, not only the routed stroke body."""
        r=V48Renderer((1200,1200),seed=44008,scale=1.0)
        comp=Group('fixture-component',[prim_rect_fill(300.0,300.0,40.0,40.0,0.0,r.FG)],
                   {'placement_kind':'collection'})
        planner=BundleGesturePlanner(r,sample_seed(r.seed,0),[comp])
        gap=r.component_pathway_clearance
        # The thin line body clears the component moat, while the larger source-dot extent does
        # not.  Final rendered admission must therefore preserve the line and reject the marker.
        x=320.0+gap+2.0*r.U
        line=prim_polyline([(x,280.0),(x,320.0)],1.0*r.U,r.FG,round_caps=False)
        marker_prim=prim_circle(x,300.0,3.0*r.U,r.FG,True)
        self.assertTrue(planner._local_visible_primitive_static_clear(line))
        self.assertFalse(planner._local_visible_primitive_static_clear(marker_prim))



    def test_v46_public_geometry_api_is_aspect_ratio_and_scale_only(self):
        r=V48Renderer('5:2',scale=.5,seed=46001)
        self.assertAlmostEqual(r.W/r.H,2.5)
        self.assertAlmostEqual(min(r.W,r.H),1200/.5)
        with self.assertRaises(TypeError):
            V48Renderer(width=1200,height=1200,seed=46001)
        with self.assertRaises(TypeError):
            V48Renderer((1,1),main_scale=.35,seed=46001)
        svg=r.svg_for([],{})
        root=svg.splitlines()[0]
        self.assertIn('viewBox="0 0 ',root)
        self.assertNotIn(' width=',root)
        self.assertNotIn(' height=',root)

    def test_v46_aspect_extension_and_zoom_share_one_logical_territory_law(self):
        long=V48Renderer((4,1),scale=1.0,seed=46002)
        zoom=V48Renderer((1,1),scale=.5,seed=46002)
        self.assertAlmostEqual(long.population_area_scale(),4.0)
        self.assertAlmostEqual(zoom.population_area_scale(),4.0)
        self.assertAlmostEqual(long.U,zoom.U)
        self.assertEqual(long.local_wave_source_cap(),zoom.local_wave_source_cap())
        self.assertEqual(long.local_branch_birth_cap(),zoom.local_branch_birth_cap())
        self.assertEqual(long.local_gap_trace_population_cap(),zoom.local_gap_trace_population_cap())
        for i in range(12):
            a=SplitMix64(sample_seed(long.seed,i)); b=SplitMix64(sample_seed(zoom.seed,i))
            self.assertEqual(long.chip_count(a),zoom.chip_count(b))
            self.assertEqual(long.collection_count(a),zoom.collection_count(b))
        seed=chip_seed(sample_seed(long.seed,0),0)
        ga=long.generate_chip(seed,0); gb=zoom.generate_chip(seed,0)
        self.assertEqual(ga.structural,gb.structural)
        self.assertEqual([p.svg for p in ga.primitives],[p.svg for p in gb.primitives])

    def test_v46_shared_head_index_matches_bruteforce_across_radius_expansion(self):
        r=V48Renderer(seed=46003)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        radius=max(4.0*p.module,80.0*p.U)
        origin=(600.0,600.0)
        a=self._planner_front(p,1,origin,0,chip=0); a['gestures']=2
        # Inside the first square query but outside its circular radius: this specifically
        # guards the V46 seen-set bug where the head could be skipped on the next expansion.
        q=(origin[0]+.90*radius,origin[1]+.90*radius)
        b=self._planner_front(p,2,q,0,chip=1); b['gestures']=2
        p._refresh_active_head_snapshot([a,b])
        got=p._nearest_foreign_head_distance(origin,0)
        expect=math.hypot(q[0]-origin[0],q[1]-origin[1])
        self.assertAlmostEqual(got,expect,places=8)

    def test_v46_terminal_conflict_spatial_pairs_match_bruteforce_order(self):
        r=V48Renderer(seed=46004); p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        discs=[]
        specs=[(100,100,8),(112,100,8),(180,100,9),(190,108,7),(300,300,8)]
        for i,(x,y,rad) in enumerate(specs):
            f={'id':i,'local_gap':False,'chip':0}
            d=prim_circle(x,y,rad,r.FG,True).geom
            discs.append((f,1000+i,(x,y),d,float(rad)))
        got=[(a[0]['id'],b[0]['id']) for a,b in p._terminal_conflict_pairs(discs,extra_gap=1.25)]
        brute=[]
        for i,a in enumerate(discs):
            for b in discs[i+1:]:
                if p._terminal_record_conflict(a,b,extra_gap=1.25): brute.append((a[0]['id'],b[0]['id']))
        self.assertEqual(got,brute)

    def test_v46_primitive_group_clearance_matches_union_predicate(self):
        r=V48Renderer(seed=46005)
        a=Group('a',[prim_rect_fill(100,100,20,10,0,r.FG),prim_circle(130,100,5,r.FG,True)],{})
        b=Group('b',[prim_rect_fill(154,100,12,12,0,r.FG),prim_circle(190,100,4,r.FG,True)],{})
        for gap in (0.0,5.0,12.0,20.0):
            expect=a.geom.intersects(b.geom) or a.geom.distance(b.geom)<gap
            self.assertEqual(r._groups_violate_clearance(a,b,gap),expect)

    def test_v47_vectorized_component_claimed_cells_matches_historical_primitive_loop(self):
        r=V48Renderer(seed=20260816)
        r._component_gap_grid_shape=(12,10)
        r._component_gap_open_cells={(x,y) for x in range(12) for y in range(10)}
        g=Group('claim',[
            prim_rect_fill(260.0,220.0,70.0,34.0,3.0,r.FG),
            prim_circle(315.0,245.0,15.0,r.FG),
            prim_polyline([(220.0,260.0),(260.0,300.0),(330.0,300.0)],5.0,r.FG),
        ])
        nx,ny=r._component_gap_grid_shape; cw=r.W/nx; ch=r.H/ny
        for claim in (0.0,0.5*r.component_component_clearance,r.component_component_clearance):
            historical=set(); geoms=r._group_collision_geoms(g); b=g.bounds
            gx0=max(0,int(math.floor((b[0]-claim)/cw-.5))); gx1=min(nx-1,int(math.ceil((b[2]+claim)/cw-.5)))
            gy0=max(0,int(math.floor((b[1]-claim)/ch-.5))); gy1=min(ny-1,int(math.ceil((b[3]+claim)/ch-.5)))
            for gx in range(gx0,gx1+1):
                for gy in range(gy0,gy1+1):
                    c=(gx,gy)
                    if c not in r._component_gap_open_cells: continue
                    pt=Point((gx+.5)*cw,(gy+.5)*ch)
                    if any(pg.intersects(pt) or pg.distance(pt)<=claim for pg in geoms): historical.add(c)
            self.assertEqual(historical,r._component_cells_claimed_by_group(g,claim))

    def test_v47_nearest_foreign_static_tree_matches_bruteforce_group_distance(self):
        r=V48Renderer(seed=20260816)
        chip0=Group('chip0',[prim_rect_fill(80.0,80.0,30.0,24.0,2.0,r.FG)],{'placement_kind':'chip'})
        chip1=Group('chip1',[prim_rect_fill(240.0,90.0,36.0,28.0,2.0,r.FG)],{'placement_kind':'chip'})
        comp=Group('comp',[prim_circle(160.0,150.0,8.0,r.FG),prim_rect_fill(180.0,150.0,10.0,16.0,1.0,r.FG)],{'placement_kind':'collection'})
        planner=BundleGesturePlanner(r,sample_seed(r.seed,0),[chip0,chip1,comp])
        probes=[
            LineString([(110.0,110.0),(145.0,110.0)]).buffer(2.0,cap_style='flat'),
            LineString([(190.0,120.0),(215.0,135.0)]).buffer(1.5,cap_style='flat'),
        ]
        static=[chip0,chip1,comp]
        for geom in probes:
            for own_chip in (0,1,999):
                expected_static=min((geom.distance(g.geom) for gi,g in enumerate(static) if gi!=own_chip),default=0.0)
                expected_chip=min((geom.distance(g.geom) for gi,g in enumerate((chip0,chip1)) if gi!=own_chip),default=0.0)
                got_static,got_chip=planner._nearest_foreign_static_clearances(geom,own_chip)
                self.assertEqual(expected_static,got_static)
                self.assertEqual(expected_chip,got_chip)

    def test_v47_geometry_only_group_transform_matches_full_transform_geometry_and_bounds(self):
        r=V48Renderer(seed=20260816)
        g=Group('probe',[
            prim_rect_fill(10.0,20.0,18.0,9.0,1.5,r.FG),
            prim_circle(30.0,14.0,5.0,r.FG),
            prim_polyline([(4.0,6.0),(14.0,16.0),(28.0,16.0)],2.0,r.FG),
        ])
        for tx,ty,scale in ((0.0,0.0,1.0),(11.25,-7.5,1.0),(-3.0,9.0,0.72),(5.0,6.0,1.31)):
            full=g.transformed(tx,ty,scale)
            probe=g.transformed_geometry_only(tx,ty,scale)
            self.assertEqual(full.bounds,probe.bounds)
            self.assertEqual(len(full.primitives),len(probe.primitives))
            for a,b in zip(full.primitives,probe.primitives):
                self.assertTrue(a.geom.equals_exact(b.geom,0.0))

    def test_v47_splitmix64_random_many_matches_scalar_sequence_and_state_exactly(self):
        for seed in (0, 1, 20260816, (1 << 64) - 1):
            for n in (0, 1, 2, 17, 31, 32, 64, 511, 4096):
                scalar = SplitMix64(seed)
                batched = SplitMix64(seed)
                expected = [scalar.random() for _ in range(n)]
                actual = list(batched.random_many(n))
                self.assertEqual(expected, actual)
                self.assertEqual(scalar.state, batched.state)

    def test_v47_nearest_static_clearance_avoids_expanding_static_hash_rescans(self):
        r=V48Renderer(seed=47152)
        c0=Group('c0',[prim_rect_fill(100,100,20,20,0,r.FG)],{'placement_kind':'chip'})
        c1=Group('c1',[prim_rect_fill(300,100,20,20,0,r.FG)],{'placement_kind':'chip'})
        comp=Group('comp',[prim_rect_fill(200,220,16,16,0,r.FG)],{'placement_kind':'collection'})
        planner=BundleGesturePlanner(r,sample_seed(r.seed,0),[c0,c1,comp])
        geom=LineString([(140.0,140.0),(170.0,150.0)]).buffer(2.0,cap_style='flat')
        expected_static=min(geom.distance(g.geom) for gi,g in enumerate((c0,c1,comp)) if gi!=0)
        expected_chip=geom.distance(c1.geom)
        with mock.patch.object(planner.static_index,'query',side_effect=AssertionError('expanding static query must not run')):
            got1=planner._nearest_foreign_static_clearances(geom,0)
            cache1=planner._foreign_static_nearest_cache
            got2=planner._nearest_foreign_static_clearances(geom,0)
            cache2=planner._foreign_static_nearest_cache
        self.assertEqual(got1,(expected_static,expected_chip))
        self.assertEqual(got2,got1)
        self.assertIs(cache1,cache2)

    def test_v46_foreign_static_spatial_clearance_matches_bruteforce(self):
        r=V48Renderer(seed=46006)
        c0=Group('c0',[prim_rect_fill(200,200,60,60,0,r.FG)],{'placement_kind':'chip'})
        c1=Group('c1',[prim_rect_fill(650,220,80,70,0,r.FG)],{'placement_kind':'chip'})
        comp=Group('comp',[prim_rect_fill(430,450,30,20,0,r.FG)],{'placement_kind':'collection'})
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[c0,c1,comp])
        geom=prim_polyline([(260,260),(360,360)],3,r.FG,round_caps=False).geom
        got_all,got_chip=p._nearest_foreign_static_clearances(geom,0)
        brute=[(gi,geom.distance(g.geom)) for gi,g in enumerate(p.static) if gi!=0]
        expect_all=min(d for _gi,d in brute)
        expect_chip=min(d for gi,d in brute if gi<len(p.chips))
        self.assertAlmostEqual(got_all,expect_all,places=8)
        self.assertAlmostEqual(got_chip,expect_chip,places=8)

    def test_v46_large_collection_calibration_solver_is_bounded_and_satisfies_same_needs(self):
        r=V48Renderer(seed=46007)
        pools=[]
        for i in range(160):
            # Values equal their masks so the resulting hard-counts are directly observable.
            pools.append({(0,0,0):(0,0,0),(1,1,0):(1,1,0),(0,1,1):(0,1,1),(1,1,1):(1,1,1)})
        needs=(81,128,96)
        sel=r._solve_collection_pool_selection(pools,needs)
        self.assertIsNotNone(sel)
        counts=tuple(sum(x[j] for x in sel) for j in range(3))
        self.assertTrue(all(counts[j]>=needs[j] for j in range(3)))

    def test_v46_front_snapshot_restore_never_replaces_unrelated_route_history(self):
        r=V48Renderer(seed=46008); p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        a=self._planner_front(p,11,(100,100),0,chip=0)
        b=self._planner_front(p,12,(100,300),0,chip=1)
        for f in (a,b):
            end=(f['path'][-1][0]+2*p.module,f['path'][-1][1])
            g=p._corridor_geom(f,f['path'][-1],end)
            p._accept(f,dict(front=f['id'],start=f['path'][-1],end=end,dir=0,modules=2,geom=g,score=1),defer_post=True)
        b_before=[(rec['start'],rec['end']) for rec in p.path_segments_by_front[b['id']]]
        saved_front=copy.deepcopy(a); saved=[dict(rec) for rec in p.path_segments_by_front[a['id']]]
        p._retire_front_segments(a['id']); p._rebuild_path_index_and_coverage()
        p._restore_front_owned_snapshot(saved_front,saved)
        b_after=[(rec['start'],rec['end']) for rec in p.path_segments_by_front[b['id']]]
        self.assertEqual(b_after,b_before)
        self.assertEqual(len(p.path_segments_by_front[a['id']]),len(saved))

    def test_v46_unbundled_local_trace_keeps_target_until_real_bundle_release(self):
        r=V48Renderer(seed=46009); p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        f=self._planner_front(p,20,(300,300),0,chip=len(p.chips)+10)
        f['local_gap']=True; f['target']=(777.0,333.0); f['local_bundle_peer']=None; f['local_bundle_times']=1
        with mock.patch.object(p,'_local_gap_target',return_value=(1.0,2.0)) as retarget:
            p._assign_local_bundle_affinities([f],4)
            retarget.assert_not_called()
        self.assertEqual(f['target'],(777.0,333.0))
        g=self._planner_front(p,21,(310,300),0,chip=len(p.chips)+11)
        g['local_gap']=True; g['local_bundle_times']=1
        f['local_bundle_peer']=g['id']; g['local_bundle_peer']=f['id']
        f['local_bundle_until']=g['local_bundle_until']=4
        with mock.patch.object(p,'_local_gap_target',return_value=(9.0,9.0)) as retarget:
            p._assign_local_bundle_affinities([f,g],4)
            self.assertEqual(retarget.call_count,2)
        self.assertEqual(f['target'],(9.0,9.0)); self.assertEqual(g['target'],(9.0,9.0))

    def test_v46_visible_side_progress_repair_extends_geometry_without_lowering_hard_floor(self):
        r=V48Renderer(seed=46010)
        chip=Group('chip',[prim_rect_fill(1000,1000,40,40,0,r.FG)],{'placement_kind':'chip'})
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[chip])
        f=self._planner_front(p,30,(120.0,120.0),0,chip=0)
        # Build a legal 7.5-module singleton, then terminate it.  The repair must physically
        # extend this lane through ordinary proposals rather than changing the 8-module audit.
        for _ in range(3):
            a=f['path'][-1]; b=(a[0]+2.5*p.module,a[1])
            g=p._corridor_geom(f,a,b)
            p._accept(f,dict(front=f['id'],start=a,end=b,dir=0,modules=2.5,geom=g,score=1.0),defer_post=True)
        f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']='fixture'
        tid=f['ids'][0]
        before=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(p._materialized_paths(f)[tid],p._materialized_paths(f)[tid][1:]))
        self.assertLess(before,8.0*p.module)
        stats={'pathway_main_stalled_side_details':[{'root':[0,0,'right'],'candidates':[{'front':f['id'],'tid':tid,'visible_length':before}]}]}
        with mock.patch.object(p,'_proposal_variants',wraps=p._proposal_variants) as proposals, \
             mock.patch.object(p,'_gesture_clear',wraps=p._gesture_clear) as clear:
            self.assertTrue(p._repair_main_stalled_side_progress(stats))
            self.assertGreater(proposals.call_count,0)
            self.assertGreater(clear.call_count,0)
        f=p.fronts[f['id']]
        after_pts=p._materialized_paths(f)[tid]
        after=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(after_pts,after_pts[1:]))
        self.assertGreaterEqual(after,9.0*p.module-1e-7)
        self.assertEqual(f['status'],'terminated')
        self.assertTrue(p._exact_path_grammar_ok(after_pts))
        src=(Path(__file__).resolve().parents[2]/'pcb_v48_renderer.py').read_text()
        self.assertIn("max(length for _,length in items)<8.0*self.module",src)

    def test_v48_stalled_singleton_dead_head_rolls_back_then_regrows_to_hard_side_floor(self):
        r=V48Renderer(seed=460101)
        chip=Group('chip',[prim_rect_fill(1000,1000,40,40,0,r.FG)],{'placement_kind':'chip'})
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[chip])
        f=self._planner_front(p,301,(120.0,120.0),0,chip=0)
        for _ in range(2):
            a=f['path'][-1]; b=(a[0]+3.0*p.module,a[1]); g=p._corridor_geom(f,a,b)
            p._accept(f,dict(front=f['id'],start=a,end=b,dir=0,modules=3.0,geom=g,score=1.0),defer_post=True)
        f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']='fixture_dead_head'
        tid=f['ids'][0]
        before=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(p._materialized_paths(f)[tid],p._materialized_paths(f)[tid][1:]))
        self.assertLess(before,8.0*p.module)
        stats={'pathway_main_stalled_side_details':[{'root':[0,0,'right'],'candidates':[{'front':f['id'],'tid':tid,'visible_length':before}]}]}
        # Force the historical forward-only repair to see a dead head.  The bounded rollback
        # fallback does not use _proposal_variants; it uses the exact survival beam instead.
        with mock.patch.object(p,'_proposal_variants',return_value=[]):
            self.assertTrue(p._repair_main_stalled_side_progress(stats))
        f=p.fronts[f['id']]
        pts=p._materialized_paths(f)[tid]
        after=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:]))
        self.assertGreaterEqual(after,9.0*p.module-1e-7)
        self.assertEqual(f['status'],'terminated')
        self.assertTrue(p._exact_path_grammar_ok(pts))
        self.assertGreaterEqual(p.stats.get('pathway_visible_side_progress_rollback_regrow_count',0),1)

    def test_v48_stalled_child_with_only_inherited_prefix_rolls_prefix_checkpoint_then_regrows(self):
        r=V48Renderer(seed=460102)
        chip=Group('chip',[prim_rect_fill(1000,1000,40,40,0,r.FG)],{'placement_kind':'chip'})
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[chip])
        parent=self._planner_front(p,460100,(120.0,160.0),0,chip=0)
        parent['status']='branched'
        tid=p.next_trace_id; p.next_trace_id+=1
        prefix=[(120.0,160.0),(120.0+3*p.module,160.0),(120.0+6*p.module,160.0)]
        f=p._make_front(ids=[tid],chip=0,side='right',side_index=0,path=[prefix[-1]],direction=0,
                        offsets={tid:0.0},thicknesses={tid:3.0*p.U},prefixes={tid:list(prefix)},
                        rng=SplitMix64(460102),parent=parent['id'])
        f['route_history']=[]; f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']='fixture_prefix_dead_head'
        before=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(prefix,prefix[1:]))
        self.assertLess(before,8.0*p.module)
        stats={'pathway_main_stalled_side_details':[{'root':[0,0,'right'],'candidates':[{'front':f['id'],'tid':tid,'visible_length':before}]}]}
        with mock.patch.object(p,'_proposal_variants',return_value=[]):
            self.assertTrue(p._repair_main_stalled_side_progress(stats))
        f=p.fronts[f['id']]; pts=p._materialized_paths(f)[tid]
        after=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:]))
        self.assertGreaterEqual(after,9.0*p.module-1e-7)
        self.assertTrue(p._exact_path_grammar_ok(pts))
        self.assertGreaterEqual(p.stats.get('pathway_visible_side_progress_prefix_regrow_count',0),1)

    def test_v46_visible_side_progress_can_fragment_only_outer_terminal_lane_then_extend_legally(self):
        r=V48Renderer(seed=46013)
        chip=Group('chip',[prim_rect_fill(1000,1000,40,40,0,r.FG)],{'placement_kind':'chip'})
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[chip])
        t0,t1=p.next_trace_id,p.next_trace_id+1; p.next_trace_id+=2
        f=p._make_front(ids=[t0,t1],chip=0,side='right',side_index=0,path=[(120.0,180.0)],direction=0,
                        offsets={t0:-3.0*p.U,t1:3.0*p.U},thicknesses={t0:3.0*p.U,t1:3.0*p.U},
                        prefixes={t0:[],t1:[]},rng=SplitMix64(46013))
        for _ in range(3):
            a=f['path'][-1]; b=(a[0]+2.5*p.module,a[1]); g=p._corridor_geom(f,a,b)
            p._accept(f,dict(front=f['id'],start=a,end=b,dir=0,modules=2.5,geom=g,score=1.0),defer_post=True)
        f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']='fixture'
        before_ids=set(f['ids']); before_other=list(p._materialized_paths(f)[t1])
        before_len=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(p._materialized_paths(f)[t0],p._materialized_paths(f)[t0][1:]))
        stats={'pathway_main_stalled_side_details':[{'root':[0,0,'right'],'candidates':[{'front':f['id'],'tid':t0,'visible_length':before_len}]}]}
        self.assertTrue(p._repair_main_stalled_side_progress(stats))
        parent=p.fronts[f['id']]
        self.assertEqual(set(parent['ids']),before_ids-{t0})
        self.assertEqual(parent['status'],'terminated')
        child=[x for x in p.fronts.values() if x.get('parent')==parent['id'] and x.get('ids')==[t0]][0]
        self.assertEqual(child['status'],'terminated')
        pts=p._materialized_paths(child)[t0]
        L=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:]))
        self.assertGreaterEqual(L,9.0*p.module-1e-7)
        self.assertTrue(p._exact_path_grammar_ok(pts))
        # The sibling lane's old materialized geometry remains its prefix under the terminal parent.
        self.assertEqual(p._materialized_paths(parent)[t1],before_other)
        self.assertGreaterEqual(p.stats.get('pathway_visible_side_progress_fragment_count',0),1)

    def test_v46_planner_bounds_broadphase_contract_is_available_to_all_spatial_repairs(self):
        r=V48Renderer(seed=46011); p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        self.assertTrue(p._bounds_within_gap((0,0,10,10),(11,0,20,10),1.0))
        self.assertFalse(p._bounds_within_gap((0,0,10,10),(11.01,0,20,10),1.0))

    def test_v46_mixed_static_index_bounds_contract_handles_component_primitives(self):
        r=V48Renderer(seed=46012)
        comp=Group('comp',[prim_rect_fill(300,300,40,30,0,r.FG),prim_circle(330,300,6,r.FG,True)],{'placement_kind':'collection'})
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[comp])
        nearby=[obj for _gi,obj in p.static_index.query((250,250,360,350))]
        self.assertTrue(any(not hasattr(obj,'bounds') for obj in nearby))
        for obj in nearby:
            b=p._indexed_static_bounds(obj)
            self.assertEqual(len(b),4)
            self.assertTrue(all(math.isfinite(float(v)) for v in b))
        f=self._planner_front(p,31,(200,300),0,chip=len(p.chips)+1)
        # Ranking-only candidate scoring must accept the same mixed index without throwing.
        score=p._score_candidate(f,0,2,(200+2*p.module,300))
        self.assertTrue(math.isfinite(score))

    def test_v46_component_rank_closure_is_initialized_before_first_heap_use(self):
        src=(Path(__file__).resolve().parents[2]/'pcb_v48_renderer.py').read_text()
        start=src.index('    def place_residual_components(')
        end=src.index('    def _validate_component_templates',start)
        block=src[start:end]
        init=block.index('capacity_fraction,region_component_counts,region_quota_units,region_capacity_units=self._component_region_capacity_fraction(accepted)')
        closure=block.index('def _region_rank_values(rid):')
        first_push=block.index('_push_region_rank(_rid)')
        self.assertLess(init,closure)
        self.assertLess(closure,first_push)

    def test_v46_static_audit_guards_against_reintroduced_global_inner_work(self):
        src=(Path(__file__).resolve().parents[2]/'pcb_v48_renderer.py').read_text()
        self.assertNotIn('saved_segments=[dict(rec) for rec in self.path_segments]',src)
        self.assertNotIn('viable=[r for r in eligible',src)
        self.assertIn('alloc_heap=[]',src)
        self.assertIn('quota_heap=[]',src)
        self.assertIn('region_priority_heap=[]',src)
        self.assertIn('_region_rank_heap=[]',src)
        self.assertIn('path_segments_by_front',src)


    def test_v47_profile_restores_natural_route_life_with_only_exceptional_shared_tail(self):
        r=V48Renderer(seed=47001)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        # V45's 24-28 cap caused the premature-route regression.  Natural route life is ordinary
        # shared-clock work again; only a short debt-filtered residue tail remains.
        self.assertGreaterEqual(p.profile['max_rounds'],48)
        self.assertLessEqual(p.profile['max_rounds'],56)
        self.assertEqual(p.profile.get('persistence_tail_rounds'),0)
        self.assertGreaterEqual(p.profile['persistence_shared_ticks'],10)
        self.assertLessEqual(p.profile['persistence_shared_ticks'],12)

    def test_v47_restored_final_settlement_budgets_are_live(self):
        _r,p=self._planner_with_fake_chip(470011)
        p.fronts.clear(); p.profile['max_rounds']=0; p.profile['persistence_shared_ticks']=0
        with mock.patch.object(p,'_settle_stalled_main_families',return_value=0) as settle:
            p._run_rounds()
        self.assertEqual(settle.call_count,2)
        self.assertEqual(settle.call_args_list[0].kwargs.get('rounds'),6)
        self.assertEqual(settle.call_args_list[1].kwargs.get('rounds'),8)

    def test_v47_general_final_escape_opportunity_is_live(self):
        _r,p=self._planner_with_fake_chip(470012)
        f=self._planner_front(p,470012,(300.0,400.0),0,chip=0)
        f['launch_egress_pending']=False; f['gestures']=6; f['local_gestures']=6
        f['travel']=8*p.module; f['max_gestures']=12; f['lifecycle']='NORMAL'
        p.profile['max_rounds']=0; p.profile['persistence_shared_ticks']=0
        def escaped(front):
            front['status']='escaped'; front['lifecycle']='TERMINAL'; return True
        with mock.patch.object(p,'_settle_stalled_main_families',return_value=0), \
             mock.patch.object(p,'_try_final_escape',side_effect=escaped) as final_escape:
            p._run_rounds()
        final_escape.assert_called_once_with(f)
        self.assertEqual(f['status'],'escaped')

    def test_v47_closed_form_straight_corridor_matches_flat_buffer(self):
        _r,p=self._planner_with_fake_chip(470013)
        f=self._planner_front(p,470013,(300.0,400.0),0,chip=0)
        a=f['path'][-1]; b=(a[0]+3*p.module,a[1])
        half=p._front_half_width(f)
        expected=LineString([a,b]).buffer(half,cap_style='flat',join_style='mitre',quad_segs=4)
        actual=p._corridor_geom(f,a,b)
        self.assertLess(actual.symmetric_difference(expected).area,1e-8)

    def test_v48_five_module_main_route_is_soft_work_debt_not_hard_validity_debt(self):
        _r,p=self._planner_with_fake_chip(47002)
        f=self._root_family_front(p,47002,lane_count=1,fan_pending=False)
        start=f['path'][-1]; end=(start[0]+5.0*p.module,start[1])
        g=p._corridor_geom(f,start,end)
        p._accept(f,dict(front=f['id'],start=start,end=end,dir=0,modules=5,geom=g,score=1.0),defer_post=True)
        self._add_satisfied_side_sibling(p,470020)
        self.assertTrue(p._persistence_work_debt(f))
        self.assertFalse(p._persistence_hard_debt(f))

    def test_v48_final_relational_persistence_is_progress_driven_beyond_fixed_tick_counts(self):
        _r,p=self._planner_with_fake_chip(470021)
        f=self._planner_front(p,470021,(300.0,400.0),0,chip=0)
        f['launch_egress_pending']=False; f['fan_pending']=False; f['fragment_pending']=False
        f['branch_stage']=None; f['travel']=6*p.module; f['gestures']=6; f['local_gestures']=6
        accepted=[]
        def residue():
            return [f] if f.get('status')=='active' else []
        def variants(front,_limit):
            step=len(accepted)+1
            return [dict(front=front['id'],score=1.0,dir=0,end=(300.0+step*p.module,400.0))]
        def accept(front,proposal,defer_post=True):
            accepted.append(proposal['front'])
            if len(accepted)>=5:
                front['status']='terminated'
        with mock.patch.object(p,'_final_relational_persistence_residue',side_effect=residue), \
             mock.patch.object(p,'_assign_round_connection_targets',return_value=0), \
             mock.patch.object(p,'_proposal_variants',side_effect=variants), \
             mock.patch.object(p,'_conflict_groups',return_value=[]), \
             mock.patch.object(p,'_accept',side_effect=accept), \
             mock.patch.object(p,'_post_accept',return_value=None), \
             mock.patch.object(p,'_connect_singletons',return_value=None):
            moved=p._settle_final_relational_persistence_progress(100)
        self.assertEqual(moved,5)
        self.assertEqual(len(accepted),5)
        self.assertEqual(p.stats['pathway_final_relational_progress_tick_count'],5)

    def test_v48_final_relational_zero_proposal_is_geometric_exhaustion_not_clock_failure(self):
        _r,p=self._planner_with_fake_chip(470022)
        f=self._planner_front(p,470022,(300.0,400.0),0,chip=0)
        f['launch_egress_pending']=False; f['fan_pending']=False; f['fragment_pending']=False
        f['branch_stage']=None; f['travel']=6*p.module; f['gestures']=6; f['local_gestures']=6
        with mock.patch.object(p,'_final_relational_persistence_residue',return_value=[f]), \
             mock.patch.object(p,'_assign_round_connection_targets',return_value=0), \
             mock.patch.object(p,'_proposal_variants',return_value=[]):
            moved=p._settle_final_relational_persistence_progress(100)
        self.assertEqual(moved,0)
        self.assertTrue(f['protected_launch_unresolved'])
        self.assertEqual(p.stats['pathway_final_relational_geometric_exhaustion_trace_count'],1)

    def test_v48_under_preferred_visible_length_is_diagnostic_not_preflight_hard_metric(self):
        self.assertNotIn('pathway_main_free_terminal_under_preferred_visible_trace_count',
                         BundleGesturePlanner._main_preflight_hard_metric_keys())

    def test_v47_mature_reroute_pending_route_does_not_hold_late_clock_open(self):
        _r,p=self._planner_with_fake_chip(47003)
        f=self._root_family_front(p,47003,lane_count=1,fan_pending=False)
        start=f['path'][-1]; end=(start[0]+6.5*p.module,start[1])
        g=p._corridor_geom(f,start,end)
        p._accept(f,dict(front=f['id'],start=start,end=end,dir=0,modules=6.5,geom=g,score=1.0),defer_post=True)
        self._add_satisfied_side_sibling(p,470030)
        f['reroute_pending']=True; f['reroute_ready_round']=999; f['lifecycle']='RECOVERING'
        self.assertFalse(p._persistence_hard_debt(f))

    def test_v47_close_head_detachment_preflight_is_all_or_nothing(self):
        _r,p=self._planner_with_fake_chip(47004)
        a=self._root_family_front(p,47004,lane_count=2,fan_pending=False)
        b=self._root_family_front(p,47005,lane_count=3,fan_pending=False)
        before_a=list(a['ids']); before_b=list(b['ids']); before_next=p.next_front_id
        before_detach=p.stats['pathway_close_head_lane_detach_count']
        self.assertFalse(p._detachment_batch_possible(((a,a['ids'][0]),(b,b['ids'][1]))))
        self.assertEqual(a['ids'],before_a)
        self.assertEqual(b['ids'],before_b)
        self.assertEqual(p.next_front_id,before_next)
        self.assertEqual(p.stats['pathway_close_head_lane_detach_count'],before_detach)

    def test_v47_terminal_record_pairer_accepts_historical_four_and_canonical_five_fields(self):
        from shapely.geometry import Point
        r=V48Renderer(seed=47005); p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        d0=Point(100,100).buffer(3); d1=Point(106,100).buffer(3)
        four=(1,(100.0,100.0),d0,3.0)
        five=(7,2,(106.0,100.0),d1,3.0)
        self.assertEqual(p._normalize_terminal_record(four)[0],None)
        self.assertEqual(p._normalize_terminal_record(five),five)
        pairs=p._terminal_conflict_pairs([four,five])
        self.assertEqual(len(pairs),1)
        self.assertEqual((pairs[0][0][1],pairs[0][1][1]),(1,2))

    def test_v47_exact_polyline_projection_matches_geos_without_geometry_allocation_contract(self):
        from shapely.geometry import LineString, Point
        pts=[(0.0,0.0),(10.0,0.0),(15.0,5.0),(15.0,15.0)]
        q=(12.0,4.0)
        line=LineString(pts); ref=line.interpolate(line.project(Point(q)))
        got=nearest_point_on_polyline_segments(q,pts)
        self.assertAlmostEqual(got[0],ref.x,places=9)
        self.assertAlmostEqual(got[1],ref.y,places=9)

    def test_v47_component_claim_membership_does_not_copy_board_open_cell_set(self):
        class NoIterSet(set):
            def __iter__(self):
                raise AssertionError('board-sized open-cell set was copied/iterated')
        r=V48Renderer(seed=47006)
        r._component_gap_grid_shape=(4,4)
        r._component_gap_open_cells=NoIterSet({(1,1)})
        g=Group('tiny',[prim_circle((1.5/4)*r.W,(1.5/4)*r.H,2.0*r.U,r.FG,True)],{'placement_kind':'isolated'})
        claimed=r._component_cells_claimed_by_group(g,claim=0.0)
        self.assertIsInstance(claimed,set)

    def test_v47_phase_release_discards_only_rebuildable_state(self):
        r=V48Renderer(seed=47007)
        g=Group('cache',[prim_rect_fill(100,100,20,20,0,r.FG)],{'placement_kind':'chip'})
        _=g.geom; _=g.collision_geom; _=g.primitive_index; b=g.bounds
        self.assertIsNotNone(g._union); self.assertIsNotNone(g._collision_collection); self.assertIsNotNone(g._primitive_index)
        r._release_group_derived_caches([g])
        self.assertIsNone(g._union); self.assertIsNone(g._collision_collection); self.assertIsNone(g._primitive_index)
        self.assertEqual(g.bounds,b)
        for name in ('_component_gap_regions','_component_gap_open_cells','_component_gap_region_by_cell','_component_gap_clearance','_component_gap_grid_shape','_component_gap_grid_n'):
            setattr(r,name,{'sentinel':1})
        r._release_component_residual_state()
        self.assertFalse(any(name in r.__dict__ for name in ('_component_gap_regions','_component_gap_open_cells','_component_gap_region_by_cell','_component_gap_clearance','_component_gap_grid_shape','_component_gap_grid_n')))

    def test_v48_wide_fragment_birth_commits_one_side_progress_leader(self):
        _r,p=self._planner_with_fake_chip(48001)
        f=self._root_family_front(p,48001,lane_count=13,fan_pending=False)
        # The hard source-egress floor remains four modules.  This fixture represents the exact
        # wide-cohort condition that used to appear at the persistence horizon: a mature bus
        # below the separate eight-module side-progress audit, about to fragment into singletons.
        f['launch_egress_pending']=False
        p._release_source_egress(p._launch_family_key(f))
        f['path']=[f['path'][0],(f['path'][0][0]+4.25*p.module,f['path'][0][1])]
        f['travel']=4.25*p.module; f['gestures']=2; f['local_gestures']=2
        chosen={'fid':None}
        def survival(child,**_kwargs):
            # Deterministically prove the third candidate only.  The production method itself
            # owns the bounded route commit; this regression is about transactional birth and
            # trace-level obligation propagation, not the beam's independent search grammar.
            if chosen['fid'] is None:
                chosen['fid']=sorted(x['id'] for x in p.fronts.values() if x.get('parent')==f['id'])[2]
            return child['id']==chosen['fid']
        with mock.patch.object(p,'_try_young_survival_beam',side_effect=survival) as beam:
            self.assertTrue(p._fragment_bundled_front(f))
        children=sorted((x for x in p.fronts.values() if x.get('parent')==f['id']),key=lambda x:x['id'])
        self.assertEqual(len(children),13)
        self.assertGreaterEqual(beam.call_count,1)
        leaders=[x for x in children if x.get('main_side_progress_leader')]
        self.assertEqual(len(leaders),1)
        leader=leaders[0]
        self.assertIn(leader['ids'][0],p.main_side_progress_trace_ids)
        self.assertEqual(p.stats.get('pathway_wide_fragment_side_progress_leader_count'),1)
        self.assertEqual(f['status'],'branched')
        # This feature must not redefine the ordinary source-egress/maturity floor.
        self.assertEqual(p.main_launch_maturity_modules,4.0)

    def test_v48_wide_fragment_side_progress_leader_renders_at_least_eight_modules(self):
        r=V48Renderer(seed=48002)
        chip=Group('chip',[prim_rect_fill(100,100,40,40,0,r.FG)],{'placement_kind':'chip'})
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[chip])
        tid=p.next_trace_id; p.next_trace_id+=1; p.main_launch_trace_ids.add(tid)
        p.main_side_progress_trace_ids.add(tid)
        start=(350.0,600.0); end=(350.0+8.05*p.module,600.0)
        f=p._make_front(ids=[tid],chip=0,side='right',side_index=0,path=[start],direction=0,
                        offsets={tid:0.0},thicknesses={tid:3.0*p.U},prefixes={tid:[]},rng=SplitMix64(48002))
        f['path'].append(end); f['travel']=8.05*p.module; f['gestures']=2; f['local_gestures']=2
        f['main_side_progress_leader']=True
        f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']='fixture'
        p.stats['pathway_launch_trace_count']=1
        _groups,stats=p._materialize()
        visible=stats['pathway_main_visible_length_modules_by_trace'][str(tid)]
        self.assertGreaterEqual(visible,8.0-1e-7)
        self.assertEqual(stats['pathway_main_free_terminal_under_preferred_visible_trace_count'],0)
        self.assertEqual(stats['pathway_main_unaccounted_launch_trace_count'],0)
        self.assertEqual(p._main_terminal_visible_floor_modules(f,tid),8.0)
        self.assertEqual(p.main_launch_maturity_modules,4.0)

    def test_v47_marker_style_cannot_shorten_free_main_terminal_below_six_visible_modules(self):
        r=V48Renderer(seed=47008)
        chip=Group('chip',[prim_rect_fill(100,100,40,40,0,r.FG)],{'placement_kind':'chip'})
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[chip])
        tid=p.next_trace_id; p.next_trace_id+=1; p.main_launch_trace_ids.add(tid)
        start=(350.0,600.0); end=(350.0+6.05*p.module,600.0)
        f=p._make_front(ids=[tid],chip=0,side='right',side_index=0,path=[start],direction=0,
                        offsets={tid:0.0},thicknesses={tid:3.0*p.U},prefixes={tid:[]},rng=SplitMix64(47008))
        f['path'].append(end); f['travel']=6.05*p.module; f['gestures']=1; f['local_gestures']=1
        f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']='fixture'
        p.stats['pathway_launch_trace_count']=1
        _groups,stats=p._materialize()
        self.assertEqual(stats['pathway_main_free_terminal_under_preferred_visible_trace_count'],0)
        self.assertEqual(stats['pathway_main_unaccounted_launch_trace_count'],0)
        self.assertGreaterEqual(stats['pathway_main_visible_length_modules_by_trace'][str(tid)],6.0-1e-7)


    def test_v47_coordinated_root_terminal_group_is_atomic_nearest_neighbor_safe(self):
        r,p=self._planner_with_fake_chip(47009)
        fronts=[]
        for i,x in enumerate((500.0,500.0+.8*p.module,500.0+1.6*p.module,500.0+2.4*p.module)):
            tid=p.next_trace_id; p.next_trace_id+=1
            modules=10.0 if i in (0,3) else 8.0
            f=p._make_front(ids=[tid],chip=0,side='bottom',side_index=0,
                            path=[(x,450.0),(x,450.0+modules*p.module)],direction=6,
                            offsets={tid:0.0},thicknesses={tid:3.0*p.U},prefixes={tid:[]},
                            rng=SplitMix64(47009+i))
            f.update(launch_egress_pending=False,fan_pending=False,fragment_pending=False,
                     branch_stage=None,travel=modules*p.module,gestures=4,local_gestures=4)
            fronts.append(f)
        fronts[0]['status']='connected'; fronts[3]['status']='connected'
        # Each middle lane alone is a forbidden singular stop between continuing neighbours.
        self.assertTrue(p._singleton_between_live_siblings(fronts[1]))
        self.assertTrue(p._singleton_between_live_siblings(fronts[2]))
        self.assertFalse(p._coordinated_root_terminal_group_safe([fronts[1]]))
        # Ending the adjacent pair atomically makes each one's nearest interior neighbour end
        # with it; farther continuing lanes cannot turn that pair back into singleton corpses.
        self.assertTrue(p._coordinated_root_terminal_group_safe([fronts[1],fronts[2]]))

    def test_v47_coordinated_fragment_terminal_group_clears_relational_embedding_atomically(self):
        r,p=self._planner_with_fake_chip(47010)
        fronts=[]
        group=991
        for i,x in enumerate((500.0,500.0+.8*p.module)):
            tid=p.next_trace_id; p.next_trace_id+=1
            f=p._make_front(ids=[tid],chip=0,side='bottom',side_index=0,
                            path=[(x,450.0),(x,450.0+8.0*p.module)],direction=6,
                            offsets={tid:0.0},thicknesses={tid:3.0*p.U},prefixes={tid:[]},
                            rng=SplitMix64(47010+i))
            f.update(launch_egress_pending=False,fan_pending=False,fragment_pending=False,
                     branch_stage=None,travel=8.0*p.module,gestures=4,local_gestures=4,
                     fragment_group=group)
            fronts.append(f)
            p.fragment_members.setdefault(group,set()).add(f['id'])
        self.assertTrue(p._fragment_singleton_still_embedded(fronts[0]))
        self.assertTrue(p._fragment_singleton_still_embedded(fronts[1]))
        self.assertTrue(p._persistence_hard_debt(fronts[0]))
        # One child cannot erase a live sibling's physical embedding debt by itself.
        self.assertFalse(p._coordinated_fragment_terminal_group_safe([fronts[0]]))
        # Ending the complete mature fragment family is one transaction; the only remaining
        # debt is relational to the sibling that is ending in that same commit.
        self.assertTrue(p._coordinated_fragment_terminal_group_safe(fronts))

    def test_v47_exhausted_embedded_middle_lane_becomes_legally_terminable_only_at_final_cohort(self):
        r,p=self._planner_with_fake_chip(47011)
        fronts=[]
        for i,x in enumerate((500.0,500.0+.8*p.module,500.0+1.6*p.module)):
            tid=p.next_trace_id; p.next_trace_id+=1
            modules=10.0 if i in (0,2) else 8.0
            f=p._make_front(ids=[tid],chip=0,side='bottom',side_index=0,
                            path=[(x,450.0),(x,450.0+modules*p.module)],direction=6,
                            offsets={tid:0.0},thicknesses={tid:3.0*p.U},prefixes={tid:[]},
                            rng=SplitMix64(47011+i))
            f.update(launch_egress_pending=False,fan_pending=False,fragment_pending=False,
                     branch_stage=None,travel=modules*p.module,gestures=4,local_gestures=4)
            fronts.append(f)
        fronts[0]['status']='connected'; fronts[2]['status']='connected'
        middle=fronts[1]
        self.assertTrue(p._singleton_between_live_siblings(middle))
        self.assertFalse(p._coordinated_root_terminal_group_safe([middle]))
        # The exception is horizon-only and proves bounded separation was actually attempted.
        self.assertFalse(p._coordinated_root_terminal_group_safe([middle],allow_exhausted_embedding=True))
        middle['protected_launch_unresolved']=True
        self.assertTrue(p._coordinated_root_terminal_group_safe([middle],allow_exhausted_embedding=True))
        self.assertGreaterEqual(p._minimum_materialized_lane_length(middle),6.0*p.module)


    def test_v47_preflight_transaction_rolls_back_nonimproving_local_success(self):
        r,planner=self._planner_with_fake_chip(47120)
        f=self._planner_front(planner, 471201, (300.0,320.0), 0)
        f['path']=[(300.0,320.0),(300.0+8.0*planner.module,320.0)]
        f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']='fixture'
        tid=f['ids'][0]
        planner.main_launch_trace_ids.add(tid)
        planner.stats['pathway_launch_trace_count']=1
        baseline={'pathway_main_unaccounted_launch_trace_ids':[tid],
                  'pathway_main_unaccounted_launch_trace_count':1,
                  'pathway_intersection_cleanup_pairs':[]}
        original=copy.deepcopy(f['path'])
        def fake_local(front,**_kwargs):
            front['path']=[front['path'][0],(front['path'][0][0],front['path'][0][1]+10.0*planner.module)]
            return True
        trial=dict(baseline)
        with mock.patch.object(planner,'_repair_main_preflight_front',side_effect=fake_local), \
             mock.patch.object(planner,'_materialize',side_effect=[([],trial),([],trial)]):
            committed,restored=planner._transactional_main_preflight_attempt(f,baseline)
        self.assertFalse(committed)
        self.assertEqual(planner.fronts[f['id']]['path'],original)
        self.assertEqual(restored['pathway_main_unaccounted_launch_trace_count'],1)
        self.assertEqual(planner.stats['pathway_preflight_transaction_rollback_count'],1)

    def test_v47_preflight_transaction_commits_rendered_launch_recovery(self):
        r,planner=self._planner_with_fake_chip(47121)
        f=self._planner_front(planner, 471211, (300.0,320.0), 0)
        f['path']=[(300.0,320.0),(300.0+8.0*planner.module,320.0)]
        f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']='fixture'
        tid=f['ids'][0]
        planner.main_launch_trace_ids.add(tid)
        planner.stats['pathway_launch_trace_count']=1
        baseline={'pathway_main_unaccounted_launch_trace_ids':[tid],
                  'pathway_main_unaccounted_launch_trace_count':1,
                  'pathway_intersection_cleanup_pairs':[]}
        recovered=dict(baseline,pathway_main_unaccounted_launch_trace_ids=[],
                       pathway_main_unaccounted_launch_trace_count=0,
                       pathway_visible_launch_trace_count=1)
        repaired_path=[f['path'][0],(f['path'][0][0]+10.0*planner.module,f['path'][0][1])]
        def fake_local(front,**_kwargs):
            front['path']=list(repaired_path)
            return True
        with mock.patch.object(planner,'_repair_main_preflight_front',side_effect=fake_local), \
             mock.patch.object(planner,'_materialize',return_value=([],recovered)):
            committed,stats=planner._transactional_main_preflight_attempt(f,baseline)
        self.assertTrue(committed)
        self.assertEqual(planner.fronts[f['id']]['path'],repaired_path)
        self.assertEqual(stats['pathway_main_unaccounted_launch_trace_count'],0)
        self.assertEqual(planner.stats['pathway_preflight_transaction_commit_count'],1)
        self.assertEqual(planner.stats['pathway_preflight_transaction_launches_recovered'],1)

    def test_v47_preflight_budget_counts_only_eligible_transactions(self):
        r,planner=self._planner_with_fake_chip(47127)
        missing=[]; pairs=[]
        for j in range(13):
            f=self._planner_front(planner, 471270+j, (100.0+5*j,500.0), 0)
            tid=f['ids'][0]; missing.append(tid)
            f['status']='connected' if j<12 else 'terminated'
            f['lifecycle']='TERMINAL'
            pairs.append(dict(new_front=f['id'],new_tid=tid,old_front=None,old_tid=None))
        baseline={'pathway_main_unaccounted_launch_trace_ids':missing,
                  'pathway_intersection_cleanup_pairs':pairs,
                  'pathway_zigzag_cleanup_details':[]}
        clean={'pathway_main_unaccounted_launch_trace_ids':[],
               'pathway_intersection_cleanup_pairs':[],
               'pathway_zigzag_cleanup_details':[]}
        with mock.patch.object(planner,'_transactional_main_preflight_attempt',return_value=(True,clean)) as attempt, \
             mock.patch.object(planner,'_rebuild_path_index_and_coverage'):
            repaired,latest=planner._repair_main_preflight_materialization(baseline)
        self.assertTrue(repaired)
        self.assertEqual(latest,clean)
        self.assertEqual(attempt.call_count,1)
        self.assertEqual(planner.stats['pathway_preflight_candidate_attempt_count'],1)
        self.assertGreaterEqual(planner.stats['pathway_preflight_candidate_ineligible_count'],12)

    def test_v47_preflight_local_repair_budget_scales_with_observed_defects(self):
        r=V48Renderer('6:1',1.0,seed=47128)
        chip=Group('chip',[prim_rect_fill(100,100,40,40,0,r.FG)],{'placement_kind':'chip'})
        planner=BundleGesturePlanner(r,sample_seed(r.seed,0),[chip])
        def make_front(seed,start,direction):
            tid=planner.next_trace_id; planner.next_trace_id+=1
            f=planner._make_front(ids=[tid],chip=0,side='right',side_index=0,path=[start],direction=direction,
                                  offsets={tid:0.0},thicknesses={tid:3.0*planner.U},prefixes={tid:[]},
                                  rng=SplitMix64(seed))
            f.update(launch_egress_pending=False,fan_pending=False,fragment_pending=False,branch_stage=None,
                     travel=1000.0,gestures=4,local_gestures=4,status='terminated',lifecycle='TERMINAL',
                     termination_reason='fixture')
            planner.main_launch_trace_ids.add(tid)
            return f
        for j in range(13):
            x0=200.0+j*500.0
            blocker=make_front(471280+j*2,(x0,700.0),0)
            blocker['path']=[(x0,700.0),(x0+400.0,700.0)]
            missing=make_front(471281+j*2,(x0+200.0,100.0),2)
            missing['path']=[(x0+200.0,100.0),(x0+200.0,400.0),(x0+200.0,650.0),(x0+200.0,1100.0)]
        planner.stats['pathway_launch_trace_count']=26
        planner._reset_materialization_pass_diagnostics()
        _groups,baseline=planner._materialize()
        self.assertEqual(baseline['pathway_main_unaccounted_launch_trace_count'],13)
        self.assertEqual(len(baseline['pathway_intersection_cleanup_pairs']),13)
        repaired,latest=planner._repair_main_preflight_materialization(baseline)
        self.assertTrue(repaired)
        self.assertEqual(latest['pathway_main_unaccounted_launch_trace_count'],0)
        self.assertEqual(latest['pathway_visible_launch_trace_count'],26)
        self.assertEqual(planner.stats['pathway_preflight_transaction_commit_count'],13)
        self.assertGreaterEqual(planner.stats['pathway_preflight_local_transaction_budget'],13)
        self.assertEqual(planner.stats['pathway_preflight_local_defect_count'],13)

    def test_v47_preflight_transaction_uses_fast_trial_materialization(self):
        r,planner=self._planner_with_fake_chip(47124)
        f=self._planner_front(planner, 471241, (300.0,320.0), 0)
        f['path']=[(300.0,320.0),(300.0+8.0*planner.module,320.0)]
        f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']='fixture'
        tid=f['ids'][0]
        planner.main_launch_trace_ids.add(tid)
        planner.stats['pathway_launch_trace_count']=1
        baseline={'pathway_main_unaccounted_launch_trace_ids':[tid],
                  'pathway_main_unaccounted_launch_trace_count':1,
                  'pathway_intersection_cleanup_pairs':[]}
        recovered=dict(baseline,pathway_main_unaccounted_launch_trace_ids=[],
                       pathway_main_unaccounted_launch_trace_count=0,
                       pathway_visible_launch_trace_count=1)
        with mock.patch.object(planner,'_repair_main_preflight_front',return_value=True), \
             mock.patch.object(planner,'_materialize',return_value=([],recovered)) as materialize:
            committed,_stats=planner._transactional_main_preflight_attempt(f,baseline)
        self.assertTrue(committed)
        self.assertTrue(materialize.call_args.kwargs['preflight_trial'])
        self.assertIn('preflight_trial_hard_baseline',materialize.call_args.kwargs)

        # Once the fast transactional trial has proven the repaired visible state, the core
        # preflight must not pay for another full-board materialization before run_main_only's
        # mandatory final full audit.  Initial full + final full = exactly two calls.
        r2,planner2=self._planner_with_fake_chip(471240)
        dirty={'pathway_launch_trace_count':1,'pathway_visible_launch_trace_count':0,
               'pathway_main_unaccounted_launch_trace_ids':[1],
               'pathway_main_unaccounted_launch_trace_count':1}
        clean={'pathway_launch_trace_count':1,'pathway_visible_launch_trace_count':1,
               'pathway_main_unaccounted_launch_trace_ids':[],
               'pathway_main_unaccounted_launch_trace_count':0,
               'pathway_main_short_termination_trace_count':0,
               'pathway_main_stalled_side_count':0,
               'pathway_main_free_terminal_under_preferred_visible_trace_count':0,
               'pathway_main_active_unmaterialized_launch_trace_count':0}
        with mock.patch.object(planner2,'_launch_fronts'), \
             mock.patch.object(planner2,'_run_rounds'), \
             mock.patch.object(planner2,'_connect_near_main_terminals'), \
             mock.patch.object(planner2,'_repair_terminal_marker_conflicts'), \
             mock.patch.object(planner2,'_repair_main_preflight_materialization',return_value=(True,clean)), \
             mock.patch.object(planner2,'_materialize',side_effect=[([],dirty),([],clean)]) as full_materialize:
            _groups,final_stats=planner2.run_main_only()
        self.assertEqual(full_materialize.call_count,2)
        self.assertEqual(planner2.stats['pathway_preflight_deferred_full_audit_count'],1)
        self.assertEqual(final_stats['pathway_visible_launch_trace_count'],1)

    def test_v47_segment_local_render_index_keeps_true_crossings_and_drops_empty_bbox_candidates(self):
        from shapely.geometry import LineString, Point
        r,planner=self._planner_with_fake_chip(47126)
        index=SpatialHash(50.0)
        old_points=[(0.0,0.0),(1000.0,1000.0)]
        old_line=LineString(old_points)
        old_prim=prim_polyline(old_points,3.0,planner.r.FG)
        old=dict(tid=1,line=old_line,primitive=old_prim,front=1,render_order=0,thickness=3.0,local_gap=False)
        planner._render_line_index_insert(index,old,old_points)
        crossing=[(0.0,1000.0),(1000.0,0.0)]
        self.assertEqual([x['tid'] for x in planner._render_line_index_query(index,crossing,5.0)],[1])
        # This small line sits inside the *global* diagonal AABB but hundreds of units from the
        # actual trace. The segment-local broad phase must not manufacture a GEOS candidate.
        empty_bbox_region=[(50.0,950.0),(100.0,950.0)]
        self.assertEqual(planner._render_line_index_query(index,empty_bbox_region,5.0),[])

    def test_v47_fast_trial_materialization_defers_full_pair_audit_but_keeps_launch_identity(self):
        r,planner=self._planner_with_fake_chip(47125)
        a=self._planner_front(planner, 471251, (100.0,700.0), 0)
        b=self._planner_front(planner, 471252, (550.0,100.0), 2)
        a['path']=[(100.0,700.0),(1100.0,700.0)]
        b['path']=[(550.0,100.0),(550.0,1100.0)]
        for f in (a,b):
            f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']='fixture'
            f['travel']=1000.0; f['launch_egress_pending']=False
            planner.main_launch_trace_ids.update(f['ids'])
        planner.stats['pathway_launch_trace_count']=2
        planner._reset_materialization_pass_diagnostics()
        with mock.patch.object(planner,'_audit_trace_pair_geometry',side_effect=AssertionError('full pair audit entered')):
            _groups,trial=planner._materialize(
                preflight_trial=True,
                preflight_trial_hard_baseline={k:0 for k in planner._main_preflight_hard_metric_keys()})
        self.assertEqual(trial['pathway_visible_launch_trace_count'],1)
        self.assertEqual(trial['pathway_main_unaccounted_launch_trace_count'],1)
        self.assertEqual(trial['pathway_intersection_trace_cleanup_count'],1)
        self.assertEqual(trial['pathway_preflight_trial_deferred_full_audit'],1)
        self.assertGreaterEqual(trial['pathway_preflight_fast_trial_count'],1)

    def test_v47_intersection_cleanup_reports_the_suppressed_launch_identity(self):
        r,planner=self._planner_with_fake_chip(47122)
        a=self._planner_front(planner, 471221, (100.0,700.0), 0)
        b=self._planner_front(planner, 471222, (550.0,100.0), 2)
        a['path']=[(100.0,700.0),(1100.0,700.0)]
        b['path']=[(550.0,100.0),(550.0,1100.0)]
        for f in (a,b):
            f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']='fixture'
            f['travel']=1000.0; f['launch_egress_pending']=False
            planner.main_launch_trace_ids.update(f['ids'])
        planner.stats['pathway_launch_trace_count']=2
        planner._reset_materialization_pass_diagnostics()
        _groups,stats=planner._materialize()
        self.assertEqual(stats['pathway_visible_launch_trace_count'],1)
        self.assertEqual(stats['pathway_main_unaccounted_launch_trace_count'],1)
        missing=stats['pathway_main_unaccounted_launch_trace_ids'][0]
        self.assertIn(missing,planner.main_launch_trace_ids)
        self.assertEqual(stats['pathway_intersection_trace_cleanup_count'],1)
        pair=stats['pathway_intersection_cleanup_pairs'][0]
        self.assertEqual(pair['new_tid'],missing)
        self.assertIn(pair['old_tid'],planner.main_launch_trace_ids)



    def test_v47_rendered_prefix_checkpoint_recovers_intersecting_mature_launch_without_moving_source(self):
        r,planner=self._planner_with_fake_chip(47123)
        a=self._planner_front(planner, 471231, (100.0,700.0), 0)
        b=self._planner_front(planner, 471232, (550.0,100.0), 2)
        a['path']=[(100.0,700.0),(1100.0,700.0)]
        # Existing vertices before the crossing provide legal checkpoint choices.
        b['path']=[(550.0,100.0),(550.0,400.0),(550.0,650.0),(550.0,1100.0)]
        for f in (a,b):
            f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']='fixture'
            f['travel']=1000.0; f['launch_egress_pending']=False
            planner.main_launch_trace_ids.update(f['ids'])
        planner.stats['pathway_launch_trace_count']=2
        planner._reset_materialization_pass_diagnostics()
        _groups,baseline=planner._materialize()
        self.assertEqual(baseline['pathway_main_unaccounted_launch_trace_ids'],[b['ids'][0]])
        source=planner._materialized_paths(b)[b['ids'][0]][0]
        with mock.patch.object(planner,'_repair_main_preflight_front',return_value=False):
            committed,trial=planner._transactional_main_preflight_attempt(
                b,baseline,target_tid=b['ids'][0],blocker_front_id=a['id'],blocker_tid=a['ids'][0])
        self.assertTrue(committed)
        self.assertEqual(trial['pathway_main_unaccounted_launch_trace_count'],0)
        restored=planner._materialized_paths(planner.fronts[b['id']])[b['ids'][0]]
        self.assertEqual(restored[0],source)
        visible=sum(math.hypot(q[0]-p[0],q[1]-p[1]) for p,q in zip(restored,restored[1:]))
        self.assertGreaterEqual(visible,planner.main_launch_preferred_terminal_modules*planner.module-1e-7)
        self.assertEqual(planner.fronts[b['id']]['termination_reason'],'preflight_rendered_prefix_checkpoint')
        self.assertEqual(planner.stats['pathway_preflight_rendered_prefix_checkpoint_count'],1)



    def test_v47_gesture_clear_uses_record_specific_path_bounds_broadphase(self):
        r=V48Renderer(seed=47201)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        f=self._planner_front(p,472011,(200.0,200.0),0)
        f['local_gap']=True
        other=self._planner_front(p,472012,(200.0,260.0),0)
        other['local_gap']=True
        og=p._corridor_geom(other,(200.0,260.0),(700.0,260.0))
        rec=dict(geom=og,front=other['id'],root=(0,'right',0),chip=0,
                 start=(200.0,260.0),end=(700.0,260.0),round_index=0,
                 local_gap=True,max_thickness=2.0*p.U)
        rec['_path_index_oid']=p.path_index.insert(rec,og.bounds)
        p.path_segments.append(rec)
        p.max_committed_path_thickness=20.0*p.U
        end=(200.0+3.0*p.module,200.0)
        geom=p._corridor_geom(f,f['path'][-1],end)
        import pcb_v48_renderer as pcb
        with mock.patch.object(p,'_source_egress_clear_for_gesture',return_value=True), \
             mock.patch.object(p.path_index,'query',return_value=[rec]), \
             mock.patch.object(pcb,'bounds_within_gap',wraps=pcb.bounds_within_gap) as broad:
            p._gesture_clear(f,f['path'][-1],end,geom,allow_outside=False)
        self.assertGreater(broad.call_count,0)



    def test_v48_gesture_budget_is_diagnostic_not_seed_acceptance(self):
        r=V48Renderer(seed=480001)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        p.gesture_check_budget=0
        p._consume_gesture_check()
        self.assertEqual(p.gesture_check_count,1)
        self.assertTrue(p.stats.get('pathway_gesture_clear_check_budget_exceeded'))
        self.assertEqual(p.stats.get('pathway_gesture_clear_check_budget_overage'),1)

    def test_v48_chip_regeneration_exhaustion_constructs_in_language_fallback(self):
        class NoProceduralChip(V48Renderer):
            def _generate_chip_once(self,rng,idx):
                return None
        r=NoProceduralChip(seed=480002)
        g=r.generate_chip(chip_seed(sample_seed(r.seed,0),0),0)
        self.assertTrue(g.structural.get('constructive_fallback'))
        self.assertGreater(len(g.primitives),0)
        self.assertTrue(.078*r.S <= g.structural['q_chip'] <= .105*r.S)
        self.assertTrue(.110*r.S <= max(g.structural['width'],g.structural['height']) <= .151*r.S)

    def test_v48_chip_uniqueness_is_exact_geometry_not_coarse_signature(self):
        r=V48Renderer(seed=480003)
        base=chip_seed(sample_seed(r.seed,0),0)
        a=r._construct_chip_fallback(base,0)
        b=r._construct_chip_fallback(base+1,1)
        # Force the legacy coarse fields equal; distinct geometry must remain distinct.
        for k in ('orientation','aspect_bin','motifs','inner_border_count','exterior_side_set_configuration'):
            b.structural[k]=a.structural.get(k)
        self.assertNotEqual(r._chip_geometry_fingerprint(a),r._chip_geometry_fingerprint(b))

    def test_v48_main_chip_random_placement_exhaustion_has_deterministic_completion(self):
        class CornerRng:
            def uniform(self,a,b): return a
            def random(self): return 0.0
        r=V48Renderer(seed=480004)
        a=r._construct_chip_fallback(1001,0)
        b=r._construct_chip_fallback(1002,1)
        placed=r.place_objects([a,b],[],[],CornerRng())
        self.assertIsNotNone(placed)
        self.assertEqual(len(placed),2)
        self.assertTrue(any(g.structural.get('deterministic_placement_completion') for g in placed))
        self.assertGreaterEqual(placed[0].geom.distance(placed[1].geom),r.chip_chip_clearance-1e-7)

    def test_v48_collection_plan_budget_zero_constructs_valid_collection(self):
        r=V48Renderer(seed=480005)
        rng=SplitMix64(12345); N=r.collection_count(rng)
        assigns,quotas=r.assign_collection_families(rng,N)
        g=r.first_valid_collection_plan(collection_seed(sample_seed(r.seed,0),0),0,assigns[0],max_attempts=0)
        self.assertIsNotNone(g)
        self.assertTrue(g.structural.get('constructive_fallback'))
        self.assertTrue(.040*r.S <= max(g.bounds[2]-g.bounds[0],g.bounds[3]-g.bounds[1]) <= .052*r.S)

    def test_v48_component_calibration_budget_zero_is_constructive(self):
        class NoPoolSolution(V48Renderer):
            def _solve_collection_pool_selection(self,pools,needs):
                return None
        r=NoPoolSolution(seed=480006)
        s=sample_seed(r.seed,0); rng=SplitMix64(s)
        nc=r.chip_count(rng); N=r.collection_count(rng); assigns,quotas=r.assign_collection_families(rng,N)
        chips=[r.generate_chip(chip_seed(s,i),i) for i in range(nc)]
        placed=r.place_objects(chips,[],[],SplitMix64(placement_seed(s)))
        initial=[r.first_valid_collection_plan(collection_seed(s,i),i,a,max_attempts=0) for i,a in enumerate(assigns)]
        out=r.calibrate_collections(s,placed,assigns,initial,max_rounds=0)
        self.assertIsNotNone(out)
        self.assertEqual(r._validate_component_templates(out,placed,quotas),[])
        self.assertTrue(all(g.structural.get('constructive_fallback') for g in out))

    def test_v48_component_preparation_zero_budgets_still_constructs_population(self):
        r=V48Renderer(seed=480007)
        s=sample_seed(r.seed,0); rng=SplitMix64(s)
        nc=r.chip_count(rng); N=r.collection_count(rng); assigns,quotas=r.assign_collection_families(rng,N)
        chips=[r.generate_chip(chip_seed(s,i),i) for i in range(nc)]
        placed=r.place_objects(chips,[],[],SplitMix64(placement_seed(s)))
        pop=r._prepare_component_population_once(s,placed,assigns,quotas,0,0,0)
        self.assertIsNotNone(pop)
        self.assertEqual(r._validate_component_templates(pop[0],placed,quotas),[])

    def test_v48_component_random_recovery_budget_zero_uses_residual_center_completion(self):
        class BadSampledSites(V48Renderer):
            def _find_residual_gap_sites(self,chips,pathways,rng,site_count):
                sites=super()._find_residual_gap_sites(chips,pathways,rng,site_count)
                return [(0.0,0.0,sites[0][2] if sites else None)] if sites else []
        r=BadSampledSites(seed=480008)
        chip=Group('chip',[prim_rect_fill(600,600,150,100,0,r.FG)],dict(placement_kind='chip'))
        tiny=Group('tiny',[prim_circle(0,0,2*r.U,r.FG,True)],dict(family='dot'))
        placed,stats=r.place_residual_components([tiny],[],[chip],[],SplitMix64(123),target=.50,fallback_attempts=0)
        self.assertEqual(stats['component_unplaced_count'],0)
        self.assertGreaterEqual(stats['component_residual_gap_fill_actual'],.50-1e-9)
        self.assertTrue(any(g.structural.get('deterministic_residual_completion') for g in placed))

    def test_v48_local_hard_floor_has_deterministic_exact_legal_debt_completion(self):
        r=V48Renderer((1200,1200),seed=480009)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        p.local_gap_service_denominator_cell_count=1
        p.local_gap_remaining_service_fraction=1.0
        p.local_gap_absolute_target_fraction=.8
        p.local_gap_target_fraction=.8
        p._launch_local_gap_fronts(source_cap=0)  # initialize canonical residual field
        p.local_gap_service_denominator_cell_count=20
        before=p._local_gap_service_fraction()
        made=p._local_gap_deterministic_debt_completion(.80)
        self.assertGreater(made,0)
        self.assertGreater(p._local_gap_service_fraction(),before)
        self.assertGreaterEqual(p._local_gap_service_fraction(),.80-1e-9)


    def test_v48_local2_partial_service_reserve_is_one_debt_campaign(self):
        # LOCAL-2 removes repeated whole-field rescue campaigns without reducing the historical
        # total source opportunity or changing ordinary local routing/legality semantics.
        src=(Path(__file__).resolve().parents[2]/'pcb_v48_renderer.py').read_text()
        start=src.index("partial_cap=self.r.local_hard_floor_rescue_cap()")
        end=src.index("def _local_gap_deterministic_debt_completion",start)
        block=src[start:end]
        self.assertIn("total_source_opportunity=partial_cap*self.r.local_wave_source_cap()",block)
        self.assertIn("wave_source_cap_override=total_source_opportunity",block)
        self.assertIn("candidate_work_cap=partial_candidate_cap",block)
        self.assertNotIn("while (self._local_gap_service_fraction()+1e-9 < hard_floor_abs",block)
        self.assertEqual(block.count("self._launch_local_gap_fronts("),1)

    def test_v48_local2_deterministic_debt_reuses_exact_first_leg_legality(self):
        # The first leg is identical while only the second-leg turn/length varies.  Cache only
        # that exact first-leg result; second-leg exact clearance and first-success ordering stay live.
        src=(Path(__file__).resolve().parents[2]/'pcb_v48_renderer.py').read_text()
        start=src.index("def _local_gap_deterministic_debt_completion")
        end=src.index("def run(self):",start)
        block=src[start:end]
        self.assertIn("first_leg_cache={}",block)
        self.assertIn("first_leg_cache_hits=0; first_leg_cache_misses=0",block)
        self.assertIn("_first_key=(cell,round(center[0],9),round(center[1],9),d0,round(m1,6))",block)
        self.assertIn("first_leg_cache[_first_key]=g1",block)
        self.assertIn("first_leg_cache[_first_key]=None",block)
        self.assertIn("self._gesture_clear(tf,pivot,end,g2,allow_outside=False,extra_segments=(g1,))",block)
        self.assertIn("pathway_local_gap_deterministic_debt_first_leg_cache_hit_count",block)


    def test_v48_main1_cross_round_proposal_pool_reuses_exact_local_legality_and_invalidates_on_nearby_commit(self):
        # MAIN-1 may replay only the legality membership proved for the exact unchanged head and
        # exact unchanged local dynamic board dependencies. A new nearby committed path must make
        # the pool ineligible before any replay can occur.
        r=V48Renderer(seed=480010); p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        f=self._planner_front(p,1,(300.0,300.0),0); p.fronts[f['id']]=f
        first=p._proposal_variants(f,count=2)
        self.assertTrue(first); self.assertIsNotNone(p._valid_proposal_reuse_pool(f))
        p._proposal_variants(f,count=2)
        self.assertEqual(p.stats.get('pathway_cross_round_proposal_pool_hit_count',0),1)
        b=f['_proposal_cross_round_pool']['_reuse_bounds']; x=(b[0]+b[2])/2; y=(b[1]+b[3])/2
        other=self._planner_front(p,2,(x,y-.4*p.module),2,chip=1); p.fronts[other['id']]=other
        a=other['path'][-1]; end=(a[0],a[1]+.8*p.module); geom=p._corridor_geom(other,a,end)
        p._record_segment(other,a,end,geom,normal=False)
        self.assertIsNone(p._valid_proposal_reuse_pool(f))

    def test_v48_main1_future_success_proof_reuses_exact_local_state_and_invalidates_on_nearby_commit(self):
        # Successful future-leg clearance is a reusable proof only while the exact local committed
        # path/source-egress dependency signature remains unchanged. Keep one cached leg here so a
        # nearby mutation cannot be hidden by hits on unrelated cached future alternatives.
        r=V48Renderer(seed=480011); p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        f=self._planner_front(p,3,(300.0,300.0),0); p.fronts[f['id']]=f
        proposal=p._propose(f); self.assertIsNotNone(proposal)
        first=p._future_options(f,proposal,limit=1); self.assertEqual(len(first),1)
        self.assertEqual(p.stats.get('pathway_future_success_proof_store_count',0),1)
        second=p._future_options(f,proposal,limit=1); self.assertEqual(len(second),1)
        self.assertEqual(p.stats.get('pathway_future_success_proof_hit_count',0),1)
        _,(cached_geom,cached_sig)=next(iter(f['_future_success_cache'].items()))
        b=cached_geom.bounds; x=(b[0]+b[2])/2; y=(b[1]+b[3])/2
        blocker=self._planner_front(p,4,(x,y-.35*p.module),2,chip=1); p.fronts[blocker['id']]=blocker
        a=blocker['path'][-1]; end=(a[0],a[1]+.7*p.module); geom=p._corridor_geom(blocker,a,end)
        p._record_segment(blocker,a,end,geom,normal=False)
        self.assertNotEqual(cached_sig,p._main_dynamic_leg_dependency_signature(cached_geom.bounds))
        before=p.stats.get('pathway_future_success_proof_hit_count',0)
        p._future_options(f,proposal,limit=1)
        self.assertEqual(p.stats.get('pathway_future_success_proof_hit_count',0),before)


    def test_v48_cross_chip_connection_is_opportunistic_not_global_acceptance(self):
        """A board need not manufacture a foreign-chip encounter merely to be valid."""
        r=V48Renderer(seed=27001)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        clean={
            'pathway_visible_launch_trace_count':0,
            'pathway_launch_trace_count':0,
            'pathway_main_short_termination_trace_count':0,
            'pathway_main_stalled_side_count':0,
            'pathway_main_unaccounted_launch_trace_count':0,
            'pathway_main_active_unmaterialized_launch_trace_count':0,
            'pathway_unmarked_stroke_overlap_count':0,
            'pathway_unmarked_clearance_violation_count':0,
            'pathway_unmarked_overlap_count':0,
            'pathway_static_intersection_count':0,
            'pathway_illegal_turn_count':0,
            'pathway_non_octilinear_segment_count':0,
            'pathway_curved_primitive_count':0,
            'pathway_cross_chip_connection_count':0,
        }
        with mock.patch.object(p,'_run_main_core_and_preflight',return_value=None), \
             mock.patch.object(p,'_repair_terminal_marker_conflicts',return_value=None), \
             mock.patch.object(p,'_materialize',return_value=([],dict(clean))):
            _groups,stats=p.run_main_only()
        self.assertEqual(stats['pathway_cross_chip_connection_count'],0)
        self.assertEqual(stats['pathway_phase'],'main_chip_network_frozen_before_residual_fill')

    def test_v48_residual_cluster_cardinality_language_has_full_1_through_12_support(self):
        r=V48Renderer(seed=27002)
        rng=SplitMix64(0xA11CE)
        values=[r.residual_fill_cluster_member_target(rng) for _ in range(8192)]
        self.assertEqual(set(values),set(range(1,13)))
        self.assertGreater(values.count(1),0)
        self.assertTrue(any(10<=v<=12 for v in values))
        self.assertTrue(all(1<=v<=12 for v in values))

    def test_v48_component_residual_clusters_partition_population_without_megacluster(self):
        r=V48Renderer(seed=27003)
        nx=ny=40
        cells={(x,y) for x in range(nx) for y in range(ny)}
        r._component_gap_grid_shape=(nx,ny)
        r._component_gap_region_by_cell={c:0 for c in cells}
        regions=[dict(id=0,cells=cells,cell_count=len(cells),width=r.W,height=r.H,
                      area=r.W*r.H,center=(r.W/2,r.H/2),short_span=min(r.W,r.H),long_span=max(r.W,r.H))]
        clearance={c:1000.0 for c in cells}
        sites=r._component_clustered_gap_sites(regions,cells,clearance,SplitMix64(7),120,60)
        targets=[m['target_members'] for m in r._component_gap_cluster_meta.values()]
        self.assertEqual(len(sites),120)
        self.assertEqual(sum(targets),60)
        self.assertGreater(len(targets),1)
        self.assertTrue(all(1<=v<=12 for v in targets))
        self.assertIn(1,targets)

    def test_v48_component_completion_clusters_are_macroscopically_dispersed(self):
        """Sparse residual completion must not recombine bounded clusters into one colony."""
        r=V48Renderer(aspect_ratio='1:1',scale=.75,seed=20260827184756,
                      main_chip_density_multiplier=.25,main_run_length_multiplier=.25)
        placed,report=r.generate_sample(0)
        clusters={}
        for g in placed:
            cid=g.structural.get('residual_fill_cluster_id')
            if cid is None:
                continue
            b=g.bounds; center=((b[0]+b[2])*.5,(b[1]+b[3])*.5)
            clusters.setdefault(cid,[]).append(center)
        tile_counts={}
        for pts in clusters.values():
            x=sum(p[0] for p in pts)/len(pts); y=sum(p[1] for p in pts)/len(pts)
            key=(min(7,max(0,int(8*x/r.W))),min(7,max(0,int(8*y/r.H))))
            tile_counts[key]=tile_counts.get(key,0)+1
        self.assertGreaterEqual(report.get('component_residual_fill_completion_cluster_count',0),8)
        self.assertTrue(all(len(v)<=12 for v in clusters.values()))
        self.assertGreaterEqual(len(tile_counts),min(16,max(1,len(clusters)//2)))
        self.assertLessEqual(max(tile_counts.values(),default=0),3)
        self.assertEqual(report.get('pathway_main_stalled_side_count'),0)
        self.assertEqual(report.get('pathway_main_short_termination_trace_count'),0)

    def test_v48_local_residual_first_wave_spreads_across_compact_parcels(self):
        """A large connected room is many LOCAL clusters, not one line-only territory."""
        r=V48Renderer(seed=27004,scale=1.0)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        p.local_gap_open_cells=p._residual_gap_cells()
        p.local_gap_service_denominator_cell_count=len(p.local_gap_open_cells)
        p.local_gap_target_fraction=.40
        p.local_gap_target_count=int(.40*len(p.local_gap_open_cells))
        self.assertGreater(len(p.local_fill_cluster_meta),12)
        targets=[m['target_sources'] for m in p.local_fill_cluster_meta.values()]
        self.assertTrue(all(1<=v<=12 for v in targets))
        spawned=p._launch_local_gap_fronts(source_cap=12)
        roots=[f for f in p.fronts.values() if f.get('local_gap') and f.get('parent') is None]
        cluster_ids=[f.get('local_fill_cluster_id') for f in roots]
        self.assertEqual(spawned,12)
        self.assertEqual(len(set(cluster_ids)),12)
        self.assertTrue(all(cid in p.local_fill_cluster_meta for cid in cluster_ids))


if __name__ == '__main__':
    unittest.main(verbosity=2)

class ProductionUseContractTests(unittest.TestCase):
    def test_production_entrypoint_renders_requested_svg_only_and_preserves_omitted_seed(self):
        import generate_pcb

        seen = {}

        class FakeRenderer:
            def __init__(self, aspect_ratio, scale, seed, **kwargs):
                seen['init'] = (aspect_ratio, scale, seed, kwargs)

            def generate_sample(self, logical_index):
                return [], {'seed': 9000 + logical_index}

            def svg_for(self, placed, report):
                return f'<svg><metadata>{report["seed"]}</metadata></svg>'

        with tempfile.TemporaryDirectory() as td, mock.patch.object(generate_pcb, 'V48Renderer', FakeRenderer):
            out = Path(td)
            paths = generate_pcb.render_requested(
                aspect_ratio='1:6', scale=0.35, seed=None, count=2, out_dir=out,
                main_chip_density_multiplier=.6, main_run_length_multiplier=1.4,
            )
            self.assertEqual(seen['init'], ('1:6', 0.35, None, {
                'main_chip_density_multiplier': .6, 'main_run_length_multiplier': 1.4
            }))
            self.assertEqual([p.name for p in paths], [
                'pcb_v48_00_seed_9000.svg', 'pcb_v48_01_seed_9001.svg'
            ])
            self.assertEqual(sorted(p.suffix for p in out.iterdir()), ['.svg', '.svg'])
            self.assertFalse(list(out.glob('*report*.json')))

        source = Path(generate_pcb.__file__).read_text(encoding='utf-8')
        for forbidden in (
            'assert_single_canonical_repo', 'run_release_tests', 'run_stress_tests',
            'build_handoff_bundle', 'perf_harness', 'safe_seed', 'safe seed',
        ):
            self.assertNotIn(forbidden, source)

    def test_agent_use_mode_precedes_development_and_forbids_repository_gates(self):
        root = Path(__file__).resolve().parents[2]
        agents = (root / 'AGENTS.md').read_text(encoding='utf-8')
        use_at = agents.index('### PRODUCTION USE mode')
        dev_at = agents.index('### DEVELOPMENT mode')
        self.assertLess(use_at, dev_at)
        use = agents[use_at:dev_at]
        self.assertIn('python generate_pcb.py', use)
        self.assertIn('DO NOT run `tools/assert_single_canonical_repo.py`', use)
        self.assertIn('DO NOT run release tests, stress tests', use)
        self.assertIn('DO NOT run `tools/build_handoff_bundle.py`', use)
        self.assertIn('leave it omitted', use)
