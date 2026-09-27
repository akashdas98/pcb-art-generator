import math
import unittest
from unittest import mock
from types import SimpleNamespace
from shapely.geometry import box, Point
from pcb_v48_renderer import V48Renderer, SplitMix64, BundleGesturePlanner, SpatialHash, sample_seed


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

    def test_v48_component_core_locates_centers_without_clipping_glyph_capacity(self):
        r=V48Renderer(seed=102)
        r._active_component_fill_target=.55
        r._active_residual_density_budget={'local_absolute_budget':.4}
        nx,ny=r.component_gap_grid_shape()
        cells={(x,y) for y in range(ny) for x in range(nx)}
        r._build_residual_composition_ownership(cells,[],SplitMix64(102))
        owners=r._residual_component_macro_owners
        self.assertTrue(owners)
        key=next(iter(owners))
        tile=owners[key]
        x0,y0,x1,y1=tile.bounds
        anchors=[c for c,k in r._residual_component_macro_by_cell.items() if k==key]
        c=min(anchors,key=lambda c:abs((c[0]+.5)*r.W/nx-(x0+x1)/2)+
                                  abs((c[1]+.5)*r.H/ny-(y0+y1)/2))
        cx,cy=(c[0]+.5)*r.W/nx,(c[1]+.5)*r.H/ny
        # A large canonical footprint may extend past the anchor core while
        # its center and entire collision body remain owned and exactly clear.
        hx=.9*min(cx-x0,x1-cx); hy=.9*min(cy-y0,y1-cy)
        geom=box(cx-hx,cy-hy,cx+hx,cy+hy)
        glyph=SimpleNamespace(bounds=geom.bounds,collision_geom=geom)
        self.assertTrue(r._residual_composition_component_geometry_owned(glyph))
        self.assertTrue(any(not r._residual_composition_component_center(p)
                            for p in ((cx-hx,cy),(cx+hx,cy),(cx,cy-hy),(cx,cy+hy))))
        # Crossing the selected modality tile still fails exact containment.
        geom=box(x0-1,cy-hy,x1+1,cy+hy)
        glyph=SimpleNamespace(bounds=geom.bounds,collision_geom=geom)
        self.assertFalse(r._residual_composition_component_geometry_owned(glyph))
