import unittest
from types import SimpleNamespace
from unittest import mock
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
from pcb_v48_renderer import (V48Renderer, BundleGesturePlanner, Group,
                              sample_seed, prim_rect_outline, prim_polyline)


class ResidualAreaDensityTests(unittest.TestCase):
    def test_v48_density_allocations_are_literal_service_at_default_and_endpoints(self):
        for density,share in ((1,.5898123324396783),(.9,.6),(.05,.01),(.05,.99),(0,.6),(1,0),(1,1)):
            r=V48Renderer(seed=102,local_density=density,component_density=share)
            b=r.residual_density_budget(sample_seed(102,0))
            self.assertFalse(b['legacy_exact'])
            self.assertEqual(b['total_target'],density)
            self.assertAlmostEqual(b['component_target'],density*share)
            self.assertAlmostEqual(b['local_absolute_budget'],density*(1-share))
            self.assertEqual(b['component_floor'],0)
            self.assertEqual(b['local_floor_absolute_budget'],0)

    def test_v48_component_area_counts_enclosed_interior_and_half_spacing_once(self):
        r=V48Renderer(seed=102);r._ensure_residual_area_field([],[])
        g=Group('enclosure',[prim_rect_outline(400,400,120,80,0,2*r.U,r.FG)])
        mask=r._component_enclosure_area_mask(g)
        nx,ny=r.component_gap_grid_shape();cw=r.W/nx;ch=r.H/ny
        enclosure=box(*g.bounds).buffer(.5*r.component_component_clearance)
        expected={}
        for cell,bits in r._residual_area_masks.items():
            for sy in range(4):
                for sx in range(4):
                    flag=1<<(sy*4+sx)
                    pt=Point((cell[0]+(sx+.5)/4)*cw,(cell[1]+(sy+.5)/4)*ch)
                    if bits&flag and enclosure.covers(pt):expected[cell]=expected.get(cell,0)|flag
        self.assertEqual(mask,expected)
        # Empty enclosure interiors receive area, not just outline paint.
        self.assertTrue(any(bits==65535 for bits in mask.values()))
        union={};first=r._merge_area_mask(union,mask)
        self.assertGreater(first,0)
        self.assertEqual(r._merge_area_mask(union,mask),0)
        self.assertEqual(first,sum(bits.bit_count() for bits in union.values()))

    def test_v48_cluster_interior_credit_is_exact_and_never_bridges_other_clusters(self):
        r=V48Renderer(seed=102);r._ensure_residual_area_field([],[])
        groups=[
            Group('left',[prim_rect_outline(390,390,20,20,0,2*r.U,r.FG)],
                  dict(residual_fill_cluster_id=7,residual_fill_cluster_target=2)),
            Group('right',[prim_rect_outline(590,390,20,20,0,2*r.U,r.FG)],
                  dict(residual_fill_cluster_id=7,residual_fill_cluster_target=2)),
            Group('other',[prim_rect_outline(490,590,20,20,0,2*r.U,r.FG)],
                  dict(residual_fill_cluster_id=8,residual_fill_cluster_target=1)),
        ]
        individual={}
        for g in groups:r._merge_area_mask(individual,r._component_enclosure_area_mask(g))
        actual={};hulls={}
        gains=[r._component_area_ledger_add(actual,hulls,g) for g in groups]
        self.assertEqual(set(hulls),{7,8})
        self.assertEqual([g.structural['residual_fill_cluster_target'] for g in groups],[2,2,1])
        self.assertEqual(r._component_area_ledger_add(actual,hulls,groups[-1]),0)
        self.assertEqual(sum(gains),sum(bits.bit_count() for bits in actual.values()))

        cluster_hulls=[unary_union([g.collision_geom.convex_hull for g in groups[:2]]).convex_hull,
                       groups[2].collision_geom.convex_hull]
        expected=dict(individual)
        nx,ny=r.component_gap_grid_shape();cw=r.W/nx;ch=r.H/ny
        for cell,bits in r._residual_area_masks.items():
            for sy in range(4):
                for sx in range(4):
                    flag=1<<(sy*4+sx)
                    if not bits&flag:continue
                    pt=Point((cell[0]+(sx+.5)/4)*cw,(cell[1]+(sy+.5)/4)*ch)
                    if any(h.covers(pt) for h in cluster_hulls):
                        expected[cell]=expected.get(cell,0)|flag
        self.assertEqual(actual,expected)
        self.assertGreater(sum((bits&~individual.get(c,0)).bit_count() for c,bits in actual.items()),0)
        all_hull=unary_union([g.collision_geom.convex_hull for g in groups]).convex_hull
        all_hull_mask=r._component_cluster_hull_area_mask(all_hull)
        self.assertTrue(any(bits&~actual.get(c,0) for c,bits in all_hull_mask.items()))

    def test_v48_joint_component_credit_and_local_exclusion_use_same_cluster_hull(self):
        r=V48Renderer(seed=102,component_density=1.0,local_density=.9)
        r._ensure_residual_area_field([],[])
        r._active_residual_density_budget=r.residual_density_budget(sample_seed(102,0))
        first=Group('first',[prim_rect_outline(390,390,20,20,0,2*r.U,r.FG)],
                    dict(residual_fill_cluster_id=7))
        second=Group('second',[prim_rect_outline(590,390,20,20,0,2*r.U,r.FG)],
                     dict(residual_fill_cluster_id=7))
        r._joint_local_atlas=dict(families={},baseline_components=(first,))
        r._reset_joint_local_atlas();atlas=r._joint_local_atlas
        before=dict(atlas['component_masks']);old_bits=atlas['component_bits']
        r._joint_candidate_cluster_id=7
        plan=r._joint_component_capacity_plan(second)
        self.assertIsNotNone(plan)
        self.assertEqual(plan[4],sum((bits&~before.get(c,0)).bit_count()
                                     for c,bits in plan[1].items()))
        self.assertGreater(plan[4],0)
        r._commit_joint_component(second)
        self.assertEqual(atlas['component_bits'],old_bits+plan[4])
        self.assertEqual(atlas['component_bits'],sum(bits.bit_count() for bits in atlas['component_masks'].values()))
        self.assertEqual(atlas['component_hulls'][7],
                         unary_union([first.collision_geom,second.collision_geom]).convex_hull)
        # The newly credited interior is unavailable to LOCAL on the same canonical samples.
        interior={c:bits&~before.get(c,0) for c,bits in atlas['component_masks'].items()}
        self.assertTrue(any(interior.values()))
        allowed={c:bits&~atlas['component_masks'].get(c,0)
                 for c,bits in r._residual_area_masks.items()}
        self.assertTrue(all(not bits&allowed.get(c,0) for c,bits in interior.items()))

    def test_v48_local_area_uses_same_free_samples_and_excludes_component_bits(self):
        r=V48Renderer(seed=102);r._ensure_residual_area_field([],[])
        p=BundleGesturePlanner(r,sample_seed(102,0),[])
        p.local_gap_open_cells=p._residual_gap_cells()
        g=Group('component',[prim_rect_outline(425,400,70,70,0,2*r.U,r.FG)])
        c=r._component_enclosure_area_mask(g)
        p.local_gap_area_allowed_masks={cell:bits&~c.get(cell,0) for cell,bits in r._residual_area_masks.items()}
        p.local_gap_service_denominator_bit_count=r._residual_area_bit_count
        points=[(300,400),(500,400)];thickness=3*r.U
        mask=p._local_capacity_service_mask(points,thickness)
        self.assertTrue(mask)
        self.assertTrue(all(not bits&c.get(cell,0) for cell,bits in mask.items()))
        half=.5*thickness+max(.5*r.local_gap_line_edge_gap_factor*thickness,
                             .5*r.component_pathway_clearance)
        ribbon=LineString(points).buffer(half,cap_style=2)
        nx,ny=r.local_gap_grid_shape();cw=r.W/nx;ch=r.H/ny
        expected={}
        for cell,bits in p.local_gap_area_allowed_masks.items():
            for sy in range(4):
                for sx in range(4):
                    flag=1<<(sy*4+sx)
                    pt=Point((cell[0]+(sx+.5)/4)*cw,(cell[1]+(sy+.5)/4)*ch)
                    if bits&flag and ribbon.covers(pt):expected[cell]=expected.get(cell,0)|flag
        self.assertEqual(mask,expected)
        # Scheduling membership cannot silently discard canonical edge subcells.
        p.local_gap_open_cells=set()
        self.assertEqual(p._local_capacity_service_mask(points,thickness),expected)

    def test_v48_joint_atlas_preserves_whole_connected_dependency_families(self):
        r=V48Renderer(seed=102,component_density=.6,local_density=.9)
        r._active_residual_density_budget=r.residual_density_budget(sample_seed(102,0))
        emitted=[]
        for sid,y in ((1,300),(2,500)):
            prim=prim_polyline([(300,y),(450,y),(500,y+50)],2*r.U,r.FG)
            emitted.append(Group(f'pathway-local-gap-{sid}',[prim],dict(local_gap_pathway=True)))
        def ordinary(p,*args):
            p.trace_records=[dict(tid=sid,front=sid,root=(10000+sid,sid,'local'),local_gap=True,
                                 points=g.primitives[0].svg['points'],primitive=g.primitives[0])
                             for sid,g in zip((1,2),emitted)]
            p.connection_pairs={(1,2):(450,400)}
            return emitted,{}
        with mock.patch.object(BundleGesturePlanner,'run_local_after_components',new=ordinary):
            r._plan_residual_local_atlas(sample_seed(102,0),[],[])
        atlas=r._joint_local_atlas
        self.assertEqual(len(atlas['families']),1)
        family=next(iter(atlas['families'].values()))
        self.assertEqual(family['groups'],emitted)
        self.assertEqual(len(family['records']),2)
        self.assertGreater(atlas['local_bits'],0)

    def test_v48_joint_guard_accounts_prospective_cluster_hull_and_keeps_unrelated_capacity(self):
        r=V48Renderer(seed=102,component_density=.6)
        r._ensure_residual_area_field([],[])
        r._active_residual_density_budget=r.residual_density_budget(sample_seed(102,0))
        p=BundleGesturePlanner(r,sample_seed(102,0),[])
        p.local_gap_open_cells=p._residual_gap_cells()
        p.local_gap_area_allowed_masks=dict(r._residual_area_masks)
        families={}
        for fid,points in ((1,[(500,370),(500,430)]),(2,[(200,850),(1000,850)])):
            prim=prim_polyline(points,3*r.U,r.FG)
            g=Group(str(fid),[prim])
            families[fid]=dict(groups=[g],mask=p._local_capacity_service_mask(points,3*r.U),records=[])
        r._joint_local_atlas=dict(families=families,baseline_components=())
        r._reset_joint_local_atlas()
        atlas=r._joint_local_atlas
        atlas['component_hulls'][7]=box(395,395,405,405)
        r._joint_candidate_cluster_id=7
        candidate=SimpleNamespace(bounds=(595,395,605,405),collision_geom=box(595,395,605,405))
        # New glyph alone clears the first route. Their common cluster interior does not.
        self.assertGreater(candidate.collision_geom.distance(families[1]['groups'][0].geom),r.component_pathway_clearance)
        plan=r._joint_component_capacity_plan(candidate)
        self.assertIsNotNone(plan)
        self.assertEqual(plan[0],{1})
        before=atlas['local_bits'];r._commit_joint_component(candidate)
        self.assertEqual(atlas['alive'],{2})
        self.assertLess(atlas['local_bits'],before)
        self.assertEqual(atlas['component_bits'],sum(b.bit_count() for b in atlas['component_masks'].values()))
        # Removing the remaining certificate would destroy the promised ratio capacity.
        bad=SimpleNamespace(bounds=(590,845,610,855),collision_geom=box(590,845,610,855))
        self.assertIsNone(r._joint_component_capacity_plan(bad))
        self.assertEqual(atlas['alive'],{2})

    def test_v48_atlas_retains_route_outside_bare_cluster_hull(self):
        r=V48Renderer(seed=102,component_density=.99)
        r._ensure_residual_area_field([],[])
        r._active_residual_density_budget=r.residual_density_budget(sample_seed(102,0))
        p=BundleGesturePlanner(r,sample_seed(102,0),[])
        p.local_gap_open_cells=p._residual_gap_cells()
        p.local_gap_area_allowed_masks=dict(r._residual_area_masks)
        points=[(480,414),(520,414)]
        prim=prim_polyline(points,3*r.U,r.FG)
        family=dict(groups=[Group('near-cluster',[prim])],
                    mask=p._local_capacity_service_mask(points,3*r.U),records=[])
        r._joint_local_atlas=dict(families={1:family},baseline_components=())
        r._reset_joint_local_atlas()
        r._joint_local_atlas['component_hulls'][7]=box(395,395,405,405)
        r._joint_candidate_cluster_id=7
        candidate=SimpleNamespace(bounds=(595,395,605,405),
                                  collision_geom=box(595,395,605,405))
        # A path near the empty outer edge of the cluster remains outside its
        # actual convex interior and keeps the exact moat from both glyphs.
        hull=box(395,395,605,405)
        self.assertFalse(prim.geom.intersects(hull))
        self.assertGreater(prim.geom.distance(candidate.collision_geom),r.component_pathway_clearance)
        plan=r._joint_component_capacity_plan(candidate)
        self.assertIsNotNone(plan)
        self.assertEqual(plan[0],set())

    def test_v48_ordinary_atlas_freezes_prepared_baseline_and_snapshots_planning_stats(self):
        r=V48Renderer(seed=102,component_density=.6)
        r._ensure_residual_area_field([],[])
        denominator=r._residual_area_bit_count
        baseline=Group('baseline',[prim_rect_outline(400,400,70,70,0,2*r.U,r.FG)],
                       dict(placement_kind='collection',residual_fill_cluster_id=7))
        r._residual_component_area_masks=r._component_enclosure_area_mask(baseline)
        r._active_residual_density_budget=r.residual_density_budget(sample_seed(102,0))
        captured=[]
        def ordinary(p,*args):
            captured.append(p)
            self.assertIn(baseline,p.cols)
            self.assertTrue(all(not bits&r._residual_component_area_masks.get(cell,0)
                                for cell,bits in p.local_gap_area_allowed_masks.items()))
            p.trace_records=[];p.connection_pairs={}
            p.stats['pathway_local_gap_source_count']=7
            return [],p.stats
        with mock.patch.object(BundleGesturePlanner,'run_local_after_components',new=ordinary):
            r._plan_residual_local_atlas(sample_seed(102,0),[],[],[baseline])
        self.assertEqual(r._residual_area_bit_count,denominator)
        self.assertGreater(r._joint_local_atlas['component_bits'],0)
        self.assertIn(7,r._joint_local_atlas['component_hulls'])
        captured[0].stats['pathway_local_gap_source_count']=1
        self.assertEqual(r._joint_local_atlas['stats']['pathway_local_gap_source_count'],7)

    def test_v48_atlas_retirement_removes_actual_gap_dependency(self):
        r=V48Renderer(seed=102,local_density=.9,component_density=1.0)
        r._ensure_residual_area_field([],[])
        r._active_residual_density_budget=r.residual_density_budget(sample_seed(102,0))
        p=BundleGesturePlanner(r,sample_seed(102,0),[])
        p.local_gap_area_allowed_masks=r._residual_area_masks
        families={}
        for fid,y in enumerate((400,400+p.module)):
            primitive=prim_polyline([(300,y),(600,y)],2*r.U,r.FG)
            mask=p._local_capacity_service_mask(primitive.svg['points'],2*r.U,canonical=True)
            families[fid]=dict(groups=[Group(str(fid),[primitive])],mask=mask,trace_masks=[mask])
        r._joint_local_atlas=dict(planner=p,families=families,baseline_components=())
        r._reset_joint_local_atlas(); atlas=r._joint_local_atlas
        base={}
        for family in families.values():r._merge_area_mask(base,family['mask'])
        self.assertGreater(atlas['local_bits'],sum(bits.bit_count() for bits in base.values()))
        candidate=Group('replacement',[prim_rect_outline(310,396,12,8,0,r.U,r.FG)])
        plan=r._joint_component_capacity_plan(candidate)
        self.assertEqual(plan[0],{0})
        r._commit_joint_component(candidate)
        expected={c:bits&~atlas['component_masks'].get(c,0) for c,bits in families[1]['mask'].items()}
        self.assertEqual(atlas['local_bits'],sum(bits.bit_count() for bits in expected.values()))
        self.assertEqual(atlas['area_field'].output_mask(),families[1]['mask'])

    def test_v48_near_endpoint_low_density_reuse_matches_fresh_logical_sample(self):
        kwargs=dict(seed=102,scale=1.0,local_density=.05,component_density=.01)
        reused=V48Renderer(**kwargs)
        reused.generate_sample(0)
        placed,report=reused.generate_sample(1)
        fresh=V48Renderer(**kwargs)
        expected,expected_report=fresh.generate_sample(1)
        self.assertEqual(reused.svg_for(placed,report),fresh.svg_for(expected,expected_report))
        # The opposite near endpoint must also report an indivisible allocation
        # or construction shortfall honestly, rather than reject its valid seed.
        high=V48Renderer(seed=102,scale=1.0,local_density=.05,component_density=.99)
        _placed,high_report=high.generate_sample(0)
        for rep,share in ((report,.01),(high_report,.99)):
            self.assertEqual(rep['residual_density_area_measure_version'],5)
            c=rep['residual_density_component_area_actual'];l=rep['residual_density_local_area_actual']
            service_c=rep['residual_density_component_service_actual']
            self.assertEqual(rep['residual_density_score_measure'],
                             'component_region_capacity_and_distribution_plus_local_area')
            self.assertAlmostEqual(rep['pathway_local_gap_area_target_absolute'],min(.05*(1-share),max(0,1-service_c)))
            self.assertAlmostEqual(rep['residual_density_physical_total'],c+l)
            self.assertAlmostEqual(rep['residual_density_score_total_actual'],service_c+l)
            self.assertAlmostEqual(rep['residual_density_actual_total'],service_c+l)
            actual=service_c/(service_c+l) if service_c+l else 0
            self.assertAlmostEqual(rep['residual_density_actual_component_share'],actual)
            self.assertAlmostEqual(rep['residual_density_component_share_error'],actual-share)
            self.assertAlmostEqual(rep['residual_density_total_shortfall'],max(0,.05-service_c-l))
            self.assertEqual(rep['local_component_clearance_violation_count'],0)
            self.assertEqual(rep['pathway_main_local_clearance_violation_count'],0)
