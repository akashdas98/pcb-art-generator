import math
import unittest
from unittest import mock
from types import SimpleNamespace
from shapely.geometry import box, Point
from pcb_v48_renderer import V48Renderer, SplitMix64, BundleGesturePlanner, SpatialHash, sample_seed, prim_polyline, prim_circle


class ResidualCompositionCapacityTests(unittest.TestCase):
    def test_v48_debt_admission_matches_exact_terminal_circle_spacing(self):
        r=V48Renderer(seed=102,scale=.75,component_density=0.0)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        t=1.9*r.U
        radius=r._termination_dot_radius(t)+.5*r.termination_dot_hollow_stroke
        gap=r.termination_dot_min_gap
        start=(400.0,400.0); pivot=(600.0,400.0); end=(750.0,550.0)
        f=dict(ids=[0],thicknesses={0:t},local_gap=True,local_gap_special=False,parent=None)
        for deficit,accepted in ((1e-4,False),(-1e-4,True)):
            with self.subTest(deficit=deficit):
                distance=2*radius+gap-deficit
                angle=math.pi/48
                other=(end[0]+distance*math.cos(angle),end[1]+distance*math.sin(angle))
                old=Point(other).buffer(radius,quad_segs=12)
                candidate=Point(end).buffer(radius,quad_segs=12)
                # Polygon faceting says clear even for the truly conflicting pair.
                self.assertGreaterEqual(candidate.distance(old),gap)
                logical=SpatialHash(100.0)
                logical.insert(dict(geom=old,tid=99,point=other,radius=radius),old.bounds)
                with mock.patch.object(p,'_backoff_local_terminal_from_components',side_effect=lambda pts,t:(pts,0.0)), \
                     mock.patch.object(p,'_backoff_terminal_points',side_effect=lambda f,tid,pts,index:(pts,0.0)), \
                     mock.patch.object(p,'_local_component_territory_clear',return_value=True), \
                     mock.patch.object(p,'_local_fill_parcel_clear',return_value=True), \
                     mock.patch.object(p,'_local_visible_primitive_static_clear',return_value=True):
                    package=p._local_debt_visible_package(f,start,pivot,end,
                        SpatialHash(100.0),logical,SpatialHash(100.0))
                self.assertEqual(package is not None,accepted)

    def test_v48_special_cap_clearance_uses_emitted_extent_and_exact_gap(self):
        r=V48Renderer(seed=102,component_density=0.0)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        t=12*r.U;cap=.5*t;gap=r.termination_dot_min_gap
        start=(400.0,400.0);pivot=(600.0,400.0);end=(750.0,550.0)
        f=dict(ids=[0],thicknesses={0:t},local_gap=True,local_gap_special=True,parent=None)
        ordinary=r._termination_dot_radius(t)+.5*r.termination_dot_hollow_stroke
        for deficit,accepted in ((1e-4,False),(-1e-4,True)):
            with self.subTest(deficit=deficit):
                distance=2*cap+gap-deficit
                self.assertLess(distance,ordinary+cap+gap)
                other=(end[0]+distance,end[1]);disc=Point(other).buffer(cap,quad_segs=12)
                logical=SpatialHash(100.0)
                logical.insert(dict(geom=disc,tid=99,point=other,radius=cap),disc.bounds)
                with mock.patch.object(p,'_backoff_terminal_points',side_effect=lambda f,tid,pts,index:(pts,0.0)), \
                     mock.patch.object(p,'_local_component_territory_clear',return_value=True), \
                     mock.patch.object(p,'_local_fill_parcel_clear',return_value=True), \
                     mock.patch.object(p,'_local_visible_primitive_static_clear',return_value=True):
                    package=p._local_debt_visible_package(f,start,pivot,end,
                        SpatialHash(100.0),logical,SpatialHash(100.0))
                self.assertEqual(package is not None,accepted)
                if accepted:
                    self.assertAlmostEqual(package[2].bounds[2]-end[0],cap)
                    self.assertEqual(package[3].svg.get('linecap'),'round')

    def test_v48_special_body_clearance_uses_stroke_and_cap_geometry(self):
        r=V48Renderer(seed=102);p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        t=12*r.U;cap=.5*t
        f=dict(ids=[0],thicknesses={0:t},local_gap_special=True,local_fill_cluster_id=0)
        p.local_route_clusters={0:dict(macro_id=0)}
        p.local_macro_geoms={0:box(0,0,r.W,r.H)}
        body=prim_polyline([(400,400),(600,400)],t,r.FG).geom
        cases=((box(450,400+cap+1e-4,500,450),True),
               (box(450,400+cap-1e-4,500,450),False),
               (box(600+cap-1e-4,399,650,401),False))
        for protected,expected in cases:
            with self.subTest(protected=protected.bounds):
                p.local_component_cluster_territory_index=SpatialHash(100)
                p.local_component_cluster_territory_index.insert((1,protected),protected.bounds)
                self.assertEqual(p._local_gesture_envelope_clear(f,body,(600,400)),expected)
        # Ordinary dot-bearing fronts keep their established broad reservation.
        protected=cases[0][0]
        p.local_component_cluster_territory_index=SpatialHash(100)
        p.local_component_cluster_territory_index.insert((1,protected),protected.bounds)
        f['local_gap_special']=False
        self.assertFalse(p._local_gesture_envelope_clear(f,body,(600,400)))

    def test_v48_bare_cluster_hull_protects_interior_without_grid_halo(self):
        r=V48Renderer(seed=102);p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        first=box(400,400,420,420);second=box(480,400,500,420)
        p.cols=[SimpleNamespace(collision_geom=g,structural={'residual_fill_cluster_id':7})
                for g in (first,second)]
        p.isolated=[]
        nx,ny=r.local_gap_grid_shape();cw=r.W/nx;ch=r.H/ny
        p._build_local_component_cluster_territory(nx,ny,cw,ch)
        self.assertEqual(len(p.local_component_cluster_territory),1)
        cid,hull=p.local_component_cluster_territory[0]
        self.assertEqual(cid,7)
        self.assertTrue(hull.covers(Point(450,410)))
        self.assertFalse(p._local_component_territory_clear(Point(450,410)))
        self.assertTrue(p._local_component_territory_clear(Point(450,420+1e-4)))
        self.assertEqual(hull.bounds,(400.0,400.0,500.0,420.0))

    def test_v48_rendered_component_moat_remains_exact_ten_u(self):
        r=V48Renderer(seed=102);p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        self.assertEqual(r.component_pathway_clearance,10*r.U)
        line=prim_polyline([(400,400),(600,400)],2*r.U,r.FG)
        for delta,expected in ((-1e-4,False),(1e-4,True)):
            with self.subTest(delta=delta):
                component=box(450,400+r.U+10*r.U+delta,500,450)
                p.static_index=SpatialHash(100)
                p.static_index.insert((0,SimpleNamespace(geom=component)),component.bounds)
                self.assertEqual(p._local_visible_primitive_static_clear(line),expected)

    def test_v48_endpoint_extent_matches_special_singleton_materialization_rule(self):
        r=V48Renderer(seed=102);p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        t=12*r.U;ordinary=r._termination_dot_radius(t)+.5*r.termination_dot_hollow_stroke
        for ids,special,expected in (([0],True,.5*t),([0,1],True,ordinary),([0],False,ordinary)):
            with self.subTest(ids=ids,special=special):
                f=dict(ids=ids,local_gap_special=special)
                self.assertAlmostEqual(p._front_endpoint_outer_radius(f,t),expected)

    def test_v48_special_debt_continuation_freezes_cap_without_ordinary_dot(self):
        r=V48Renderer(seed=102,component_density=0.0)
        r._ensure_residual_area_field([],[])
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        p.local_gap_open_cells=p._residual_gap_cells()
        p.local_gap_area_allowed_masks=dict(r._residual_area_masks)
        p.local_gap_service_denominator_bit_count=r._residual_area_bit_count
        start=(400.0,400.0);pivot=(400.0+1.5*p.module,400.0)
        step=1.5*p.module/math.sqrt(2);end=(pivot[0]+step,pivot[1]+step)
        cid=p.local_gap_region_by_cell[p._gap_cell(start)];t=12*r.U
        f=p._make_front(ids=[17],chip=0,side='local',side_index=0,
            path=[start,pivot,end],direction=7,offsets={17:0.0},thicknesses={17:t},prefixes={17:[]},
            rng=SplitMix64(123),intent='explore',target=None,local_cluster_id=cid)
        f.update(status='terminated',local_gap=True,local_gap_special=True,local_gap_region_id=cid,
            local_gap_min_terminal_modules=3.0)
        p.local_gap_absolute_target_fraction=1.0
        prim=prim_polyline([start,pivot,end],t,r.FG,round_caps=True)
        p.trace_records=[dict(tid=17,front=f['id'],points=[start,pivot,end],primitive=prim,
            local_gap=True,terminal_marker=None)]
        # Exercise the real continuation package and geometry gates in an open field.
        self.assertEqual(p._extend_local_gap_debt_packets([17]),1)
        frozen=p._local_frozen_visible_packets[17]
        self.assertIsNone(frozen['terminal_marker'])
        self.assertEqual(frozen['primitive'].svg.get('linecap'),'round')

    def test_v48_component_parcels_schedule_without_clipping_glyph_capacity(self):
        r=V48Renderer(seed=102)
        r._active_component_fill_target=.55
        r._active_residual_density_budget={'local_absolute_budget':.4}
        nx,ny=r.component_gap_grid_shape()
        cells={(x,y) for y in range(ny) for x in range(nx)}
        r._build_residual_composition_ownership(cells,[],SplitMix64(102))
        self.assertEqual(r._residual_composition_component_cells,cells)
        mx,my=r._residual_macro_grid_shape
        self.assertGreater(mx,1)
        # A canonical glyph straddles a scheduler seam. Both sides remain
        # eligible and the whole footprint is legal within the board.
        sx=r.W/mx; cy=.5*r.H
        geom=box(sx-20,cy-20,sx+20,cy+20)
        glyph=SimpleNamespace(bounds=geom.bounds,collision_geom=geom)
        self.assertTrue(r._residual_composition_component_geometry_owned(glyph))
        self.assertTrue(r._residual_composition_component_center((sx-10,cy)))
        self.assertTrue(r._residual_composition_component_center((sx+10,cy)))
        geom=box(-1,cy-20,30,cy+20)
        glyph=SimpleNamespace(bounds=geom.bounds,collision_geom=geom)
        self.assertFalse(r._residual_composition_component_geometry_owned(glyph))

    def test_v48_local_scheduler_seams_do_not_fragment_physical_route_domain(self):
        r=V48Renderer(seed=102)
        r._active_component_fill_target=.55
        r._active_residual_density_budget={'local_absolute_budget':.4}
        nx,ny=r.component_gap_grid_shape()
        cells={(x,y) for y in range(ny) for x in range(nx)}
        r._build_residual_composition_ownership(cells,[],SplitMix64(102))
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        physical=p._residual_gap_cells()
        self.assertEqual(p.local_gap_route_cells,physical)
        self.assertGreater(len(p.local_route_clusters),1)
        sx=12*r.W/nx; cy=.5*r.H
        left=p._gap_cell((sx-1,cy)); right=p._gap_cell((sx+1,cy))
        cid=p.local_gap_route_domain_by_cell[left]
        other=p.local_gap_route_domain_by_cell[right]
        self.assertNotEqual(cid,other)
        f={'local_gap':True,'local_fill_cluster_id':cid}
        self.assertTrue(p._local_fill_parcel_clear(f,box(sx-10,cy-10,sx+10,cy+10)))
        # Crossing a scheduler seam is legal; roaming to a remote parcel is
        # still excluded for this source and all descendants retaining its ID.
        self.assertFalse(p._local_fill_parcel_clear(f,box(r.W-20,20,r.W-10,30)))

    def test_v48_debt_equal_priority_round_robin_has_no_top_prefix(self):
        r=V48Renderer(seed=102)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        p.local_gap_open_cells=p._residual_gap_cells()
        ordered=p._local_gap_debt_cell_order()
        span=p.local_gap_chunk_span
        nchunks=len({(x//span,y//span) for x,y in p.local_gap_route_cells})
        first=ordered[:nchunks]
        self.assertEqual(len({(x//span,y//span) for x,y in first}),nchunks)
        self.assertEqual(set(ordered),p.local_gap_route_cells)
        nx,ny=r.local_gap_grid_shape()
        self.assertEqual({min(3,4*y//ny) for x,y in first},{0,1,2,3})
        self.assertEqual(ordered,p._local_gap_debt_cell_order())
        # Debt amount remains primary despite spatial fairness within each band.
        p.local_gap_coverage_mask_by_cell[first[0]]=15
        self.assertEqual(p._local_gap_debt_cell_order()[-1],first[0])

    def _visible_debt_fixture(self):
        r=V48Renderer(seed=102)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        p.local_gap_open_cells=p._residual_gap_cells()
        p.local_gap_service_denominator_cell_count=len(p.local_gap_open_cells)
        p.local_gap_target_fraction=.8
        p.local_gap_absolute_target_fraction=.8
        center=(400.0,400.0)
        pivot=(center[0]+2.5*p.module,center[1])
        end=(pivot[0]+2.5*p.module/math.sqrt(2),pivot[1]+2.5*p.module/math.sqrt(2))
        cid=p.local_gap_route_domain_by_cell[p._gap_cell(center)]
        tid=p.next_trace_id; p.next_trace_id+=1
        f=p._make_front(ids=[tid],chip=400000,side='local',side_index=0,
            path=[center,pivot,end],direction=1,offsets={tid:0.0},
            thicknesses={tid:1.90*r.U},prefixes={tid:[]},rng=SplitMix64(123),
            intent='explore',target=end,local_cluster_id=cid)
        f.update(local_gap=True,local_gap_special=False,local_gap_region_id=cid,
            status='terminated',termination_reason='local_gap_deterministic_debt_completion',
            gestures=2,local_gestures=2,travel=5.0*p.module,fan_pending=False)
        for a,b in zip(f['path'],f['path'][1:]):
            p._record_segment(f,a,b,p._corridor_geom(f,a,b),normal=False)
        p._materialize()
        rec=next(rec for rec in p.trace_records if rec['tid']==tid)
        return p,f,tid,rec

    def test_v48_debt_continuation_preserves_complete_certificate_and_adds_service(self):
        p,f,tid,rec=self._visible_debt_fixture()
        old_mask=p._local_capacity_service_mask(rec['points'],f['thicknesses'][tid])
        old_length=sum(math.dist(a,b) for a,b in zip(rec['points'],rec['points'][1:]))
        p._extend_local_gap_debt_packets([tid])
        self.assertEqual(p.stats['pathway_local_gap_debt_continuation_trace_count'],1)
        service_before_recount=p._local_gap_service_fraction()
        p._materialize()
        self.assertAlmostEqual(p._local_gap_service_fraction(),service_before_recount)
        new=next(rec for rec in p.trace_records if rec['tid']==tid)
        new_mask=p._local_capacity_service_mask(new['points'],f['thicknesses'][tid])
        self.assertTrue(all(bits&~new_mask.get(cell,0)==0 for cell,bits in old_mask.items()))
        self.assertGreater(sum(math.dist(a,b) for a,b in zip(new['points'],new['points'][1:])),old_length)
        self.assertGreater(p.stats['pathway_local_gap_debt_continuation_added_service_bits'],0)

    def test_v48_blocked_debt_continuation_retains_original_visible_packet(self):
        p,f,tid,rec=self._visible_debt_fixture()
        path=list(f['path']); old_mask=p._local_capacity_service_mask(rec['points'],f['thicknesses'][tid])
        with mock.patch.object(p,'_gesture_clear',return_value=False) as gate:
            self.assertEqual(p._extend_local_gap_debt_packets([tid]),0)
        self.assertGreater(gate.call_count,0)
        self.assertEqual(f['path'],path)
        service_before_recount=p._local_gap_service_fraction()
        p._materialize()
        self.assertAlmostEqual(p._local_gap_service_fraction(),service_before_recount)
        new=next(rec for rec in p.trace_records if rec['tid']==tid)
        self.assertEqual(new['points'],rec['points'])
        self.assertEqual(p._local_capacity_service_mask(new['points'],f['thicknesses'][tid]),old_mask)

    def test_v48_debt_continuation_rejects_partial_certificate_replacement(self):
        p,f,tid,rec=self._visible_debt_fixture()
        path=list(f['path']); cell=p._gap_cell(path[0])
        masks=[{cell:3}]+[{cell:1}]*3
        with mock.patch.object(p,'_local_capacity_service_mask',side_effect=masks):
            self.assertEqual(p._extend_local_gap_debt_packets([tid]),0)
        self.assertEqual(f['path'],path)
        self.assertEqual(p._local_frozen_visible_packets[tid]['points'],rec['points'])

    def _visible_atlas_fixture(self):
        r=V48Renderer(seed=102)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        p.local_gap_open_cells=p._residual_gap_cells()
        p.local_gap_service_denominator_cell_count=len(p.local_gap_open_cells)
        p.local_gap_target_fraction=.8; p.local_gap_absolute_target_fraction=.8
        tids=[]
        for y in range(4):
            for x in range(4):
                center=(150.0+300*x,150.0+300*y)
                pivot=(center[0]+2.5*p.module,center[1])
                end=(pivot[0]+2.5*p.module/math.sqrt(2),pivot[1]+2.5*p.module/math.sqrt(2))
                cid=p.local_gap_route_domain_by_cell[p._gap_cell(center)]
                tid=p.next_trace_id; p.next_trace_id+=1; tids.append(tid)
                f=p._make_front(ids=[tid],chip=400000+tid,side='local',side_index=tid,
                    path=[center,pivot,end],direction=1,offsets={tid:0.0},
                    thicknesses={tid:1.90*r.U},prefixes={tid:[]},rng=SplitMix64(123+tid),
                    intent='explore',target=end,local_cluster_id=cid)
                f.update(local_gap=True,local_gap_special=False,local_gap_region_id=cid,
                    status='terminated',termination_reason='local_gap_deterministic_debt_completion',
                    gestures=2,local_gestures=2,travel=5.0*p.module,fan_pending=False)
                for a,b in zip(f['path'],f['path'][1:]):
                    p._record_segment(f,a,b,p._corridor_geom(f,a,b),normal=False)
                for key in ('pathway_bundle_count','pathway_local_gap_source_count',
                            'pathway_local_gap_trace_count','pathway_local_gap_independent_source_count'):
                    p.stats[key]+=1
        p._materialize()
        return p,tids

    def test_v48_partial_debt_selection_is_boardwide_and_retires_unused_atlas(self):
        p,tids=self._visible_atlas_fixture()
        atlas_service=p._local_gap_service_fraction()
        old_points={rec['tid']:list(rec['points']) for rec in p.trace_records}
        selected=p._select_local_gap_debt_certificates(tids,{},.24*atlas_service)
        self.assertLess(len(selected),len(tids))
        self.assertGreaterEqual(p._local_gap_service_fraction()+1e-9,.24*atlas_service)
        sources=[p.fronts[rec['front']]['path'][0] for rec in p.trace_records]
        self.assertGreaterEqual(max(y for x,y in sources)-min(y for x,y in sources),.5*p.H)
        self.assertGreaterEqual(max(x for x,y in sources)-min(x for x,y in sources),.5*p.W)
        self.assertEqual({rec['tid'] for rec in p.trace_records},set(selected))
        self.assertEqual(p.stats['pathway_local_gap_source_count'],len(selected))
        self.assertEqual(p.stats['pathway_local_gap_debt_capacity_planned_trace_count'],len(tids))
        self.assertTrue(all(rec['points']==old_points[rec['tid']] for rec in p.trace_records))
        self.assertEqual(set(p.fronts),{rec['front'] for rec in p.trace_records})
        self.assertTrue(all(rec['front'] in p.fronts for rec in p.path_index.objects.values()))
        self.assertEqual(set(p._local_frozen_visible_packets),set(selected))

    def test_v48_full_debt_selection_preserves_proven_visible_capacity(self):
        p,tids=self._visible_atlas_fixture()
        atlas_service=p._local_gap_service_fraction()
        masks=dict(p.local_gap_coverage_mask_by_cell)
        selected=p._select_local_gap_debt_certificates(tids,{},atlas_service)
        self.assertEqual(set(selected),set(tids))
        self.assertEqual(p.local_gap_coverage_mask_by_cell,masks)
        self.assertAlmostEqual(p._local_gap_service_fraction(),atlas_service)
        self.assertEqual(p.stats['pathway_local_gap_debt_capacity_retired_trace_count'],0)

    def test_v48_debt_replacement_indexes_use_actual_offset_terminal_endpoints(self):
        r=V48Renderer(seed=102)
        p=BundleGesturePlanner(r,sample_seed(r.seed,0),[])
        p.local_gap_target_fraction=.8
        f=p._make_front(ids=[17,18],chip=0,side='N',side_index=0,
            path=[(400.0,400.0),(600.0,400.0)],direction=0,
            offsets={17:-8.0,18:8.0},thicknesses={17:2.0,18:2.0},prefixes={},
            rng=SplitMix64(123),intent='explore',target=None)
        f.update(status='terminated',local_gap=False)
        paths=p._materialized_paths(f)
        p.trace_records=[dict(tid=tid,front=f['id'],points=pts,
            primitive=prim_polyline(pts,2.0,r.FG),local_gap=False,
            terminal_marker=prim_circle(*pts[-1],r._termination_dot_radius(2.0),r.FG))
            for tid,pts in paths.items()]
        logical=[]; original=SpatialHash.insert
        def capture(index,obj,bounds):
            if isinstance(obj,dict) and 'point' in obj and 'radius' in obj:
                logical.append((obj['tid'],obj['point']))
            return original(index,obj,bounds)
        with mock.patch.object(SpatialHash,'insert',new=capture):
            p._extend_local_gap_debt_packets([])
        self.assertEqual(dict(logical),{tid:pts[-1] for tid,pts in paths.items()})
        self.assertEqual(len(set(point for tid,point in logical)),2)
        self.assertTrue(all(point!=f['path'][-1] for tid,point in logical))
