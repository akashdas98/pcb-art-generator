#!/usr/bin/env python3
"""
Deterministic renderer for PCB Graphic Design Language v33 launch-family protected transactional-parallel routing architecture.

Authority: chip_design_language_v33_variance_driven.md
Now includes variance-driven pathways.

This is an implementation of the authoritative design sheet, not a replacement for it.
The implementation keeps all generation/validation logic in code so a fresh model does not
need to mentally simulate the renderer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import secrets
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from shapely import affinity
from shapely.geometry import GeometryCollection, LineString, Point, Polygon, box
from shapely.ops import unary_union

MASK64 = (1 << 64) - 1

# ---------------------------------------------------------------------------
# PRNG
# ---------------------------------------------------------------------------

class SplitMix64:
    def __init__(self, seed: int):
        self.state = seed & MASK64

    def next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK64
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
        z = z ^ (z >> 31)
        return z & MASK64

    def random(self) -> float:
        z = self.next_u64()
        return ((z >> 11) & ((1 << 53) - 1)) / float(1 << 53)

    def uniform(self, a: float, b: float) -> float:
        return a + self.random() * (b - a)

    def weighted(self, items: Sequence[Tuple[Any, float]]) -> Any:
        total = sum(w for _, w in items)
        r = self.random() * total
        c = 0.0
        for item, w in items:
            c += w
            if r < c:
                return item
        return items[-1][0]

    def shuffle(self, xs: List[Any]) -> None:
        for i in range(len(xs) - 1, 0, -1):
            j = int(self.random() * (i + 1))
            xs[i], xs[j] = xs[j], xs[i]

    def sample_without_replacement_weighted(self, weights: Dict[Any, float], n: int) -> List[Any]:
        pool = dict(weights)
        out = []
        while pool and len(out) < n:
            item = self.weighted(list(pool.items()))
            out.append(item)
            del pool[item]
        return out


def mix_once(x: int) -> int:
    r = SplitMix64(x)
    return r.next_u64()


def sample_seed(seed: int, i: int) -> int:
    return mix_once(seed ^ 0xA0761D6478BD642F ^ i)


def chip_seed(sseed: int, j: int) -> int:
    return mix_once(sseed ^ 0xE7037ED1A0B428DB ^ j)


def collection_seed(sseed: int, k: int) -> int:
    return mix_once(sseed ^ 0x8EBC6AF09C88C6E3 ^ k)


def placement_seed(sseed: int) -> int:
    return mix_once(sseed ^ 0x589965CC75374CC3)

def component_fill_seed(sseed: int) -> int:
    return mix_once(sseed ^ 0xF1357AEA2E62A9C5)

def isolated_capacitor_seed(sseed: int) -> int:
    return mix_once(sseed ^ 0xD1342543DE82EF95)

def pathway_seed(sseed: int) -> int:
    return mix_once(sseed ^ 0x6C8E9CF570932BD5)

def local_pathway_seed(sseed: int) -> int:
    return mix_once(sseed ^ 0xB5AD4ECEDA1CE2A9)

def retry_seed(base: int, retry_index: int) -> int:
    return mix_once(base ^ retry_index)

# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

_BOUNDS_ONLY = False

@dataclass
class BoundsGeom:
    bounds: Tuple[float,float,float,float]

@contextmanager
def bounds_only_mode(enabled=True):
    global _BOUNDS_ONLY
    old=_BOUNDS_ONLY
    _BOUNDS_ONLY=enabled
    try:
        yield
    finally:
        _BOUNDS_ONLY=old

def _bounds_geom(b):
    return BoundsGeom(tuple(float(x) for x in b))

def bounds_union(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]):
    return min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])


def bounds_w_h(b):
    return b[2] - b[0], b[3] - b[1]


def bounds_center(b):
    return (b[0] + b[2]) * 0.5, (b[1] + b[3]) * 0.5


def bounds_diag(b):
    w, h = bounds_w_h(b)
    return math.hypot(w, h)


def rounded_rect_poly(cx: float, cy: float, w: float, h: float, r: float, resolution: int = 8):
    if w <= 0 or h <= 0:
        return GeometryCollection()
    r = max(0.0, min(r, w * 0.5, h * 0.5))
    if r <= 1e-9:
        return box(cx - w/2, cy - h/2, cx + w/2, cy + h/2)
    core = box(cx - w/2 + r, cy - h/2 + r, cx + w/2 - r, cy + h/2 - r)
    return core.buffer(r, quad_segs=resolution, join_style="round")


def rect_stroke_geom(cx, cy, w, h, rx, t):
    outer = rounded_rect_poly(cx, cy, w + t, h + t, rx + t/2)
    iw, ih = w - t, h - t
    if iw <= 0 or ih <= 0:
        return outer
    inner = rounded_rect_poly(cx, cy, iw, ih, max(0.0, rx - t/2))
    return outer.difference(inner)


def circle_stroke_geom(cx, cy, r, t):
    outer = Point(cx, cy).buffer(r + t/2, quad_segs=16)
    inner_r = r - t/2
    if inner_r <= 0:
        return outer
    return outer.difference(Point(cx, cy).buffer(inner_r, quad_segs=16))


def line_stroke_geom(x1, y1, x2, y2, t, round_caps=False):
    cap = "round" if round_caps else "flat"
    return LineString([(x1, y1), (x2, y2)]).buffer(t/2, cap_style=cap, join_style="round" if round_caps else "mitre", quad_segs=8)


def quad_point(p0, q, p1, t):
    s = 1.0 - t
    return (s*s*p0[0] + 2*s*t*q[0] + t*t*p1[0],
            s*s*p0[1] + 2*s*t*q[1] + t*t*p1[1])


def quadratic_flat_points(p0, q, p1, tol):
    # Adaptive recursive flattening using control-point deviation from chord.
    pts = [p0]
    def rec(a, c, b, depth=0):
        line = LineString([a, b])
        dev = Point(c).distance(line)
        if dev <= tol or depth >= 16:
            pts.append(b)
            return
        ac = ((a[0]+c[0])*0.5, (a[1]+c[1])*0.5)
        cb = ((c[0]+b[0])*0.5, (c[1]+b[1])*0.5)
        mid = ((ac[0]+cb[0])*0.5, (ac[1]+cb[1])*0.5)
        rec(a, ac, mid, depth+1)
        rec(mid, cb, b, depth+1)
    rec(p0, q, p1)
    return pts


def quadratic_stroke_geom(p0, q, p1, t, tol):
    pts = quadratic_flat_points(p0, q, p1, tol)
    return LineString(pts).buffer(t/2, cap_style="round", join_style="round", quad_segs=8)

# ---------------------------------------------------------------------------
# Visible primitive representation
# ---------------------------------------------------------------------------

@dataclass
class Primitive:
    kind: str
    geom: Any
    svg: Dict[str, Any]
    signature: Dict[str, Any]

    def transformed(self, tx=0.0, ty=0.0, scale=1.0) -> "Primitive":
        g = self.geom
        s = dict(self.svg)
        sig = dict(self.signature)
        if scale != 1.0:
            if isinstance(g, BoundsGeom):
                b=g.bounds
                xs=[b[0]*scale,b[2]*scale]; ys=[b[1]*scale,b[3]*scale]
                g=_bounds_geom((min(xs),min(ys),max(xs),max(ys)))
            else:
                g = affinity.scale(g, xfact=scale, yfact=scale, origin=(0, 0))
            s = transform_svg(s, scale=scale)
            sig = transform_signature(sig, scale=scale)
        if tx or ty:
            if isinstance(g, BoundsGeom):
                b=g.bounds; g=_bounds_geom((b[0]+tx,b[1]+ty,b[2]+tx,b[3]+ty))
            else:
                g = affinity.translate(g, xoff=tx, yoff=ty)
            s = transform_svg(s, tx=tx, ty=ty)
            sig = transform_signature(sig, tx=tx, ty=ty)
        return Primitive(self.kind, g, s, sig)


def transform_signature(sig, tx=0.0, ty=0.0, scale=1.0):
    out = dict(sig)
    if "cx" in out:
        out["cx"] = out["cx"] * scale + tx
        out["cy"] = out["cy"] * scale + ty
    if "w" in out: out["w"] *= scale
    if "h" in out: out["h"] *= scale
    if "r" in out: out["r"] *= scale
    return out


def transform_svg(s, tx=0.0, ty=0.0, scale=1.0):
    out = dict(s)
    typ = out["type"]
    for k in ("cx", "cy", "x", "y", "x1", "y1", "x2", "y2", "stroke_width", "r", "rx", "width", "height"):
        if k in out and isinstance(out[k], (int, float)):
            if k in ("cx", "x", "x1", "x2"):
                out[k] = out[k]*scale + tx
            elif k in ("cy", "y", "y1", "y2"):
                out[k] = out[k]*scale + ty
            else:
                out[k] = out[k]*scale
    if typ in ("polygon", "polyline"):
        out["points"] = [(x*scale+tx, y*scale+ty) for x,y in out["points"]]
    if typ == "quadratic":
        out["p0"] = (out["p0"][0]*scale+tx, out["p0"][1]*scale+ty)
        out["q"] = (out["q"][0]*scale+tx, out["q"][1]*scale+ty)
        out["p1"] = (out["p1"][0]*scale+tx, out["p1"][1]*scale+ty)
    return out


def prim_rect_outline(cx, cy, w, h, rx, stroke, color):
    geom=_bounds_geom((cx-(w+stroke)/2,cy-(h+stroke)/2,cx+(w+stroke)/2,cy+(h+stroke)/2)) if _BOUNDS_ONLY else rect_stroke_geom(cx,cy,w,h,rx,stroke)
    return Primitive("rect_outline", geom,
                     dict(type="rect", cx=cx,cy=cy,width=w,height=h,rx=rx,fill="none",stroke=color,stroke_width=stroke),
                     dict(kind="rect_outline",cx=cx,cy=cy,w=w,h=h))


def prim_rect_fill(cx, cy, w, h, rx, color):
    geom=_bounds_geom((cx-w/2,cy-h/2,cx+w/2,cy+h/2)) if _BOUNDS_ONLY else rounded_rect_poly(cx,cy,w,h,rx)
    return Primitive("rect_fill", geom,
                     dict(type="rect",cx=cx,cy=cy,width=w,height=h,rx=rx,fill=color,stroke="none"),
                     dict(kind="rect_fill",cx=cx,cy=cy,w=w,h=h))


def prim_circle(cx, cy, r, color, filled=True, stroke=0.0):
    if filled:
        g = _bounds_geom((cx-r,cy-r,cx+r,cy+r)) if _BOUNDS_ONLY else Point(cx,cy).buffer(r, quad_segs=16)
        svg = dict(type="circle",cx=cx,cy=cy,r=r,fill=color,stroke="none")
        k="circle_fill"
    else:
        rr=r+stroke/2
        g = _bounds_geom((cx-rr,cy-rr,cx+rr,cy+rr)) if _BOUNDS_ONLY else circle_stroke_geom(cx,cy,r,stroke)
        svg = dict(type="circle",cx=cx,cy=cy,r=r,fill="none",stroke=color,stroke_width=stroke)
        k="circle_outline"
    return Primitive(k,g,svg,dict(kind=k,cx=cx,cy=cy,w=2*r,h=2*r,r=r))


def prim_line(x1,y1,x2,y2,t,color,round_caps=False):
    if _BOUNDS_ONLY:
        dx=x2-x1; dy=y2-y1; L=math.hypot(dx,dy)
        if L<=1e-12:
            ex=ey=t/2
        elif round_caps:
            ex=ey=t/2
        else:
            ex=abs(-dy/L)*(t/2); ey=abs(dx/L)*(t/2)
        g=_bounds_geom((min(x1,x2)-ex,min(y1,y2)-ey,max(x1,x2)+ex,max(y1,y2)+ey))
    else:
        g=line_stroke_geom(x1,y1,x2,y2,t,round_caps)
    svg=dict(type="line",x1=x1,y1=y1,x2=x2,y2=y2,stroke=color,stroke_width=t,linecap="round" if round_caps else "butt")
    minx,miny,maxx,maxy=g.bounds
    return Primitive("line",g,svg,dict(kind="line",cx=(minx+maxx)/2,cy=(miny+maxy)/2,w=maxx-minx,h=maxy-miny))


def prim_polyline(points,t,color,round_caps=False):
    if len(points)<2:
        x,y=points[0] if points else (0.0,0.0)
        return prim_line(x,y,x,y,t,color,round_caps=True)
    if _BOUNDS_ONLY:
        xs=[p[0] for p in points]; ys=[p[1] for p in points]
        rr=t/2
        g=_bounds_geom((min(xs)-rr,min(ys)-rr,max(xs)+rr,max(ys)+rr))
    else:
        g=LineString(points).buffer(t/2, cap_style="round" if round_caps else "flat", join_style="mitre", quad_segs=8)
    svg=dict(type="polyline",points=[tuple(p) for p in points],stroke=color,stroke_width=t,fill="none",linecap="round" if round_caps else "butt",linejoin="miter")
    minx,miny,maxx,maxy=g.bounds
    return Primitive("polyline",g,svg,dict(kind="polyline",cx=(minx+maxx)/2,cy=(miny+maxy)/2,w=maxx-minx,h=maxy-miny))


def prim_quadratic(p0,q,p1,t,color,U):
    g=quadratic_stroke_geom(p0,q,p1,t,0.25*U)
    svg=dict(type="quadratic",p0=p0,q=q,p1=p1,stroke=color,stroke_width=t,linecap="round")
    minx,miny,maxx,maxy=g.bounds
    return Primitive("quadratic",g,svg,dict(kind="quadratic",cx=(minx+maxx)/2,cy=(miny+maxy)/2,w=maxx-minx,h=maxy-miny))

# ---------------------------------------------------------------------------
# Group / spatial index
# ---------------------------------------------------------------------------

@dataclass
class Group:
    name: str
    primitives: List[Primitive]
    structural: Dict[str, Any] = field(default_factory=dict)
    intentional_contacts: List[Tuple[Any, Any]] = field(default_factory=list)
    _union: Any = field(default=None, repr=False)
    _bounds: Any = field(default=None, repr=False)

    @property
    def geom(self):
        if self._union is None:
            if not self.primitives:
                self._union=GeometryCollection()
            elif any(isinstance(p.geom,BoundsGeom) for p in self.primitives):
                self._union=unary_union([box(*p.geom.bounds) if isinstance(p.geom,BoundsGeom) else p.geom for p in self.primitives])
            else:
                self._union = unary_union([p.geom for p in self.primitives])
        return self._union

    @property
    def bounds(self):
        if self._bounds is None:
            if not self.primitives:
                self._bounds=(0.0,0.0,0.0,0.0)
            else:
                bs=[p.geom.bounds for p in self.primitives]
                self._bounds=(min(b[0] for b in bs),min(b[1] for b in bs),max(b[2] for b in bs),max(b[3] for b in bs))
        return self._bounds

    def transformed(self, tx=0.0, ty=0.0, scale=1.0, name=None):
        return Group(name or self.name,
                     [p.transformed(tx,ty,scale) for p in self.primitives],
                     dict(self.structural), list(self.intentional_contacts))

    def invalidate(self):
        self._union = None
        self._bounds = None


class SpatialHash:
    def __init__(self, cell_size: float):
        self.cell_size = max(cell_size, 1e-9)
        self.cells: Dict[Tuple[int,int], set[int]] = {}
        self.objects: Dict[int, Any] = {}
        self.bounds: Dict[int, Tuple[float,float,float,float]] = {}
        self.next_id = 0

    def _cells_for(self, b):
        cs=self.cell_size
        ix0=math.floor(b[0]/cs); iy0=math.floor(b[1]/cs)
        ix1=math.floor(b[2]/cs); iy1=math.floor(b[3]/cs)
        for ix in range(ix0,ix1+1):
            for iy in range(iy0,iy1+1):
                yield ix,iy

    def insert(self, obj, b=None):
        if b is None: b=obj.bounds
        oid=self.next_id; self.next_id += 1
        self.objects[oid]=obj; self.bounds[oid]=b
        for c in self._cells_for(b): self.cells.setdefault(c,set()).add(oid)
        return oid

    def query(self, b):
        ids=set()
        for c in self._cells_for(b): ids.update(self.cells.get(c,()))
        return [self.objects[i] for i in ids]


def expand_bounds(b, d):
    return b[0]-d,b[1]-d,b[2]+d,b[3]+d

DIR8=[(1.0,0.0),(math.sqrt(0.5),-math.sqrt(0.5)),(0.0,-1.0),(-math.sqrt(0.5),-math.sqrt(0.5)),(-1.0,0.0),(-math.sqrt(0.5),math.sqrt(0.5)),(0.0,1.0),(math.sqrt(0.5),math.sqrt(0.5))]
SIDE_TO_DIR={"right":0,"top":2,"left":4,"bottom":6}

def dir_vec(idx:int)->Tuple[float,float]:
    return DIR8[idx%8]

def nearest_dir_index(dx:float, dy:float)->int:
    ang=(math.degrees(math.atan2(-dy, dx))+360.0)%360.0
    return int((ang+22.5)//45)%8

def step_dir_toward(cur:int, desired:int)->int:
    d=(desired-cur)%8
    if d==0: return cur
    return (cur+1)%8 if d<=4 else (cur-1)%8

def point_along_dir(pt:Tuple[float,float], idx:int, dist:float)->Tuple[float,float]:
    vx,vy=dir_vec(idx)
    return pt[0]+vx*dist, pt[1]+vy*dist

def offset_line_points(p0:Tuple[float,float], p1:Tuple[float,float], off:float)->Tuple[Tuple[float,float],Tuple[float,float]]:
    dx=p1[0]-p0[0]; dy=p1[1]-p0[1]; L=max(1e-9, math.hypot(dx,dy))
    px=-dy/L; py=dx/L
    return (p0[0]+px*off,p0[1]+py*off),(p1[0]+px*off,p1[1]+py*off)


class BundleGesturePlanner:
    """Coarse, synchronous pathway planner.

    The planner deliberately routes only bundle centre corridors.  It never runs A* and it
    never searches later candidate seeds for a board with preferred output statistics.  A
    seeded board profile controls the visual tendencies; the already-generated static board
    determines which of those tendencies can actually be realised.

    Individual traces are materialised only after the corridor tree is complete.  They are
    stable offset curves of their owning bundle corridor, so unrelated members cannot silently
    collapse into a shared centreline.
    """

    def __init__(self, renderer, sseed:int, placed:List[Group]):
        self.r=renderer; self.U=renderer.U; self.W=renderer.W; self.H=renderer.H
        self.sseed=sseed
        self.rng=SplitMix64(pathway_seed(sseed))
        self.chips=[g for g in placed if g.structural.get('placement_kind')=='chip']
        self.cols=[g for g in placed if g.structural.get('placement_kind')=='collection']
        self.isolated=[g for g in placed if g.structural.get('placement_kind')=='isolated']
        self.static=self.chips+self.cols+self.isolated
        self.profile=self._sample_profile()
        self.module=self.profile['module_U']*self.U
        # V33 source egress is a hard family-level launch phase.
        self.launch_egress_modules=4.0
        self.main_launch_maturity_modules=4.0
        self.main_launch_preferred_terminal_modules=6.0
        self.source_egress_reservations=[]
        self.fronts:Dict[int,Dict[str,Any]]={}
        self.next_front_id=0
        self.next_trace_id=0
        self.path_segments=[]
        self.path_index=SpatialHash(max(80*self.U,3*self.module))
        self.connection_pairs:Dict[Tuple[int,int],Tuple[float,float]]={}
        self.connected_trace_ids=set()
        self.cross_chip_connected_trace_ids=set()
        self.coverage_cells=set()
        self.local_gap_open_cells=set()
        self.local_gap_regions=[]
        self.local_gap_region_by_cell={}
        self.local_gap_coverage_cells=set()
        self.local_gap_target_fraction=0.0
        self.local_gap_target_count=0
        self.local_gap_special_probability=None
        self.grid_n=40
        self.congestion_grid=[[0 for _ in range(self.grid_n)] for _ in range(self.grid_n)]
        self.stats=dict(
            pathway_planner_mode='route_first_family_protected_transactional_parallel',
            pathway_outcome_policy='hard_invariants_soft_best_effort_targets',
            pathway_launch_coverage_intent_range=(0.72,0.90),
            pathway_bundled_termination_suppression_intent=0.97,
            pathway_candidate_seed_retry_count=0,
            pathway_route_search_count=0,
            pathway_bundle_count=0,
            pathway_launch_cohort_count=0,
            pathway_launch_trace_count=0,
            pathway_split_count=0,
            pathway_leaf_bundle_count=0,
            pathway_connection_count=0,
            pathway_cross_chip_connection_count=0,
            pathway_cross_chip_connected_trace_count=0,
            pathway_collection_connection_count=0,
            pathway_collection_connected_trace_count=0,
            pathway_collection_approach_count=0,
            pathway_collection_approached_trace_count=0,
            pathway_termination_count=0,
            pathway_termination_trace_count=0,
            pathway_escape_count=0,
            pathway_escape_trace_count=0,
            pathway_intersection_marker_count=0,
            pathway_overlap_event_count=0,
            pathway_same_round_conflict_count=0,
            pathway_atomic_round_commit_count=0,
            pathway_atomic_conflict_group_defer_count=0,
            pathway_atomic_conflict_group_repair_front_count=0,
            pathway_causal_blocker_rollback_request_count=0,
            pathway_causal_terminal_reopen_count=0,
            pathway_root_emergence_traceback_count=0,
            pathway_blocked_gesture_count=0,
            pathway_hard_stop_count=0,
            pathway_reroute_scheduled_count=0,
            pathway_traceback_count=0,
            pathway_traceback_segment_count=0,
            pathway_reroute_recovery_count=0,
            pathway_reroute_exhausted_count=0,
            pathway_branch_preflight_reject_count=0,
            pathway_reroute_short_rebase_count=0,
            pathway_holistic_connection_pair_count=0,
            pathway_holistic_connection_guided_round_count=0,
            pathway_loop_candidate_reject_count=0,
            pathway_general_repair_scheduled_count=0,
            pathway_conflict_repair_scheduled_count=0,
            pathway_progress_repair_scheduled_count=0,
            pathway_deep_traceback_count=0,
            pathway_abandoned_short_bundle_count=0,
            pathway_abandoned_short_trace_count=0,
            pathway_bundled_journey_deferral_count=0,
            pathway_bundled_hard_stop_deferral_count=0,
            pathway_recovery_fragment_count=0,
            pathway_late_life_branch_attempt_count=0,
            pathway_forced_close_head_connection_count=0,
            pathway_close_head_lane_detach_count=0,
            pathway_detached_prefix_lock_count=0,
            pathway_midline_connection_count=0,
            pathway_multiply_connected_trace_count=0,
            pathway_unmarked_stroke_overlap_count=0,
            pathway_tiny_termination_trace_count=0,
            pathway_termination_marker_overlap_count=0,
            pathway_bundle_middle_termination_deferral_count=0,
            pathway_final_escape_repair_count=0,
            pathway_young_survival_repair_count=0,
            pathway_young_survival_repair_trace_count=0,
            pathway_terminal_separation_repair_count=0,
            pathway_coordinated_persistence_terminal_trace_count=0,
            pathway_duplicate_trace_cleanup_count=0,
            pathway_intersection_trace_cleanup_count=0,
            pathway_zigzag_trace_cleanup_count=0,
            pathway_decision_round_count=0,
            pathway_rounds_with_multiple_fronts=0,
            pathway_launch_min_lane_edge_gap_ratio=0.0,
            pathway_trace_thickness_min=0.0,
            pathway_trace_thickness_max=0.0,
            pathway_trace_thickness_mean=0.0,
            pathway_minimum_segment_exception_count=0,
            pathway_terminal_alignment_exception_count=0,
            pathway_conflict_region_count=0,
            pathway_conflict_region_front_count=0,
            pathway_conflict_combination_count=0,
            pathway_lookahead_evaluation_count=0,
            pathway_holistic_front_round_count=0,
            pathway_blocker_yield_count=0,
            pathway_early_reroute_scheduled_count=0,
            pathway_terminal_head_backoff_count=0,
            pathway_terminal_head_backoff_distance=0.0,
            pathway_transactional_birth_reject_count=0,
            pathway_family_hold_round_count=0,
            pathway_family_hold_front_count=0,
            pathway_local_gap_hold_round_count=0,
            pathway_local_gap_hold_front_count=0,
            pathway_local_gap_region_count=0,
            pathway_local_gap_bundle_pair_count=0,
            pathway_local_gap_bundle_release_count=0,
            pathway_local_gap_independent_source_count=0,
            pathway_launch_egress_reservation_reject_count=0,
            pathway_protected_launch_unresolved_count=0,
            pathway_local_gap_source_count=0,
            pathway_local_gap_trace_count=0,
            pathway_local_gap_visible_trace_count=0,
            pathway_local_gap_escape_trace_count=0,
            pathway_local_gap_special_thick_trace_count=0,
            pathway_local_gap_special_ratio=0.0,
            pathway_local_gap_spawn_attempt_count=0,
            pathway_local_gap_spawn_reject_count=0,
            pathway_local_gap_split_count=0,
            pathway_local_gap_round_budget=0,
            pathway_local_gap_normal_branch_boost_range=tuple(renderer.local_gap_branch_boost_range),
            pathway_local_gap_fill_target_range=tuple(renderer.local_gap_fill_range),
            pathway_local_gap_fill_target_fraction=0.0,
            pathway_local_gap_open_cell_count=0,
            pathway_local_gap_target_cell_count=0,
            pathway_local_gap_covered_cell_count=0,
            pathway_local_gap_fill_actual=0.0,
            pathway_local_gap_wave_count=0,
            pathway_local_gap_exit_probability_factor=renderer.local_gap_exit_probability_factor,
            pathway_local_gap_special_probability_range=(0.15,0.30),
            pathway_local_gap_special_hollow_cap_count=0,
            pathway_source_marker_count=0,
            pathway_module_U=self.profile['module_U'],
            pathway_module_canvas_units=self.module,
            pathway_profile={k:round(v,6) if isinstance(v,float) else v for k,v in self.profile.items()},
            pathway_local_space_capacity_evaluation_count=0,
            pathway_space_available_replan_count=0,
        )

    def _sample_profile(self):
        """One coherent variance profile for the whole board, not per-trace noise."""
        rng=self.rng
        return dict(
            module_U=rng.uniform(31.0,39.0),
            preferred_run_modules=2+int(rng.random()*3),
            turn_appetite=rng.uniform(.40,.64),
            branch_appetite=rng.uniform(.34,.54),
            branch_multiplier=rng.uniform(1.50,1.80),
            connection_appetite=rng.uniform(.88,.99),
            exit_inclination=rng.uniform(.25,.44),
            # Current route-first architecture: components do not exist spatially during routing. Component attachment is
            # reversed in the final fill phase, so the router has no component intent.
            outward_bias=rng.uniform(.44,.70),
            # V21 gives persistence/recovery a little more room so a lane that is still
            # visually embedded between continuing siblings is not forced to die merely
            # because the global planning horizon arrived.
            max_rounds=48+int(rng.random()*9),
            reroute_budget=7,
            late_life_branch_start=.60,
            late_life_branch_multiplier=1.50,
            persistence_tail_rounds=12,
        )

    def _new_rng(self):
        return SplitMix64(self.rng.next_u64())

    def _cohort_slices(self, count:int, rng:SplitMix64):
        """Partition a complete side launch into a few contiguous routing cohorts."""
        out=[]; start=0; remaining=count
        while remaining:
            if remaining<=5:
                take=remaining
            else:
                take=3+int(rng.random()*3)
                if 0 < remaining-take < 3:
                    take=remaining-3
            take=max(1,min(remaining,take))
            out.append(list(range(start,start+take)))
            start+=take; remaining-=take
        return out

    def _sample_intent(self, rng:SplitMix64, center, initial_dir, allow_component=True):
        # Route-first architecture: only the main chips exist as static board objects while
        # main routes are planned, and the local network is added before any component geometry.
        # Therefore routing intent is limited to pathway-native goals.  Rare line-to-component
        # relationships are created later by placing a small component onto an eligible free
        # pathway terminal; the pathway never searches for a not-yet-existing component.
        p_exit=max(.16,.72*self.profile['exit_inclination'])
        p_connect=.38+.30*self.profile['connection_appetite']
        p_explore=max(.05,1.0-p_exit-p_connect)
        kind=rng.weighted([('connect',p_connect),('exit',p_exit),('explore',p_explore)])
        target=None
        if kind=='exit':
            target=self._distant_exit_target(center,rng)
        elif kind=='explore':
            target=self._underused_target(center,rng)
        return kind,target

    def _distant_exit_target(self,center,rng:SplitMix64):
        """Choose an edge objective far from the launch, not the nearest straight exit."""
        margin=rng.uniform(1.1,1.8)*self.module
        candidates=[]
        for _ in range(3):
            candidates.extend([
                (-margin,rng.uniform(.08*self.H,.92*self.H)),
                (self.W+margin,rng.uniform(.08*self.H,.92*self.H)),
                (rng.uniform(.08*self.W,.92*self.W),-margin),
                (rng.uniform(.08*self.W,.92*self.W),self.H+margin),
            ])
        far=[p for p in candidates if math.hypot(p[0]-center[0],p[1]-center[1])>=.32*math.hypot(self.W,self.H)]
        pool=far or candidates
        pool.sort(key=lambda p:(-math.hypot(p[0]-center[0],p[1]-center[1]),rng.random()))
        return pool[int(rng.random()*min(4,len(pool)))]

    def _underused_target(self, center, rng:SplitMix64):
        candidates=[]
        for gy in range(4):
            for gx in range(4):
                x=(gx+rng.uniform(.24,.76))*self.W/4
                y=(gy+rng.uniform(.24,.76))*self.H/4
                d=math.hypot(x-center[0],y-center[1])
                if d < .24*math.hypot(self.W,self.H):
                    continue
                cell=(min(11,max(0,int(12*x/self.W))),min(11,max(0,int(12*y/self.H))))
                used=1 if cell in self.coverage_cells else 0
                static_clear=min((Point(x,y).distance(g.geom) for g in self.static),default=6*self.module)
                candidates.append((used,-min(static_clear,6*self.module),rng.random(),(x,y)))
        if not candidates:
            return self.r._distant_board_goal(center,rng)
        candidates.sort(key=lambda x:(x[0],x[1],x[2]))
        return candidates[0][3]

    def _make_front(self, *, ids, chip, side, side_index, path, direction, offsets,
                    thicknesses, prefixes, rng, depth=0, intent=None, target=None,
                    parent=None, branch_turn=None, fan_group=None,
                    forced_straight_modules=None,forced_turn_modules=None):
        fid=self.next_front_id; self.next_front_id+=1
        if intent is None:
            intent,target=self._sample_intent(rng,path[-1],direction)
        max_gestures=7+int(rng.random()*5)
        if intent in ('exit','explore'):
            max_gestures+=2
        f=dict(
            id=fid,ids=list(ids),chip=chip,side=side,side_index=side_index,
            path=[tuple(p) for p in path],dir=direction,initial_dir=direction,offsets=dict(offsets),
            thicknesses=dict(thicknesses),prefixes={i:list(prefixes.get(i,[])) for i in ids},
            rng=rng,depth=depth,parent=parent,branch_parent=parent,
            fan_group=fan_group,
            forced_straight_modules=forced_straight_modules,
            forced_turn_modules=forced_turn_modules,
            branch_turn=branch_turn,branch_stage=0 if branch_turn is not None else None,
            intent=intent,target=target,status='active',gestures=0,local_gestures=0,
            travel=0.0,max_gestures=max_gestures,base_max_gestures=max_gestures,failures=0,turn_cooldown=0,
            straight_since_turn=3,last_turn_sign=0,normal_segment_lengths=[],
            route_history=[],reroute_pending=False,reroute_ready_round=None,
            reroute_attempts=0,reroute_mode_rounds=0,reroute_avoid_dir=None,
            reroute_reason=None,recovery_floor_segments=0,
            origin=tuple(path[-1]),max_origin_distance=0.0,stagnant_gestures=0,
            turn_history=[],quality_repair_pending=False,quality_repair_reason=None,
            round_connection_peer=None,round_connection_target=None,
            branch_retry_after_gesture=0,termination_reason=None,
            bundle_termination_deferrals=0,
            lifecycle=('STRUCTURAL_TRANSITION' if branch_turn is not None else ('LAUNCHING' if parent is None else 'NORMAL')),
            young_defer_count=0, launch_yield_requests=0,
        )
        self.fronts[fid]=f
        return f

    # ----------------------- V22 bounded holistic layer -----------------------
    def _grid_cell(self,p):
        x,y=p
        return (min(self.grid_n-1,max(0,int(self.grid_n*x/max(self.W,1e-9)))),
                min(self.grid_n-1,max(0,int(self.grid_n*y/max(self.H,1e-9)))))

    def _grid_add_segment(self,a,b):
        L=math.hypot(b[0]-a[0],b[1]-a[1]); steps=max(1,int(math.ceil(L/max(.55*self.module,1e-9))))
        seen=set()
        for k in range(steps+1):
            t=k/steps; cell=self._grid_cell((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
            if cell in seen: continue
            seen.add(cell); x,y=cell; self.congestion_grid[y][x]+=1

    def _rebuild_congestion_grid(self):
        self.congestion_grid=[[0 for _ in range(self.grid_n)] for _ in range(self.grid_n)]
        for rec in self.path_segments: self._grid_add_segment(rec['start'],rec['end'])

    def _congestion_at(self,p):
        gx,gy=self._grid_cell(p); val=0.0; wsum=0.0
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                x,y=gx+dx,gy+dy
                if 0<=x<self.grid_n and 0<=y<self.grid_n:
                    w=1.0 if dx==0 and dy==0 else .45
                    val+=w*self.congestion_grid[y][x]; wsum+=w
        return val/max(wsum,1e-9)

    def _refresh_lifecycle(self,f):
        if f.get('status')!='active': f['lifecycle']='TERMINAL'
        elif f.get('round_connection_peer') is not None: f['lifecycle']='CONNECTION_PENDING'
        elif self._source_egress_pending(f): f['lifecycle']='LAUNCHING'
        elif f.get('branch_stage') is not None or (f.get('fan_pending') and self._launch_egress_cleared(f)) or (f.get('recovery_fragment_child') and f.get('local_gestures',0)==0): f['lifecycle']='STRUCTURAL_TRANSITION'
        elif f.get('reroute_pending') or f.get('reroute_mode_rounds',0)>0 or f.get('quality_repair_pending'): f['lifecycle']='RECOVERING'
        elif f.get('gestures',0)<3 or f.get('travel',0.0)<5*self.module: f['lifecycle']='LAUNCHING'
        else: f['lifecycle']='NORMAL'
        return f['lifecycle']

    def _needs_holistic(self,f):
        life=self._refresh_lifecycle(f)
        if life in ('LAUNCHING','STRUCTURAL_TRANSITION','CONNECTION_PENDING','RECOVERING'): return True
        return f.get('failures',0)>0 or self._congestion_at(f['path'][-1])>=1.8

    def _future_options(self,f,p,limit=5):
        """Bounded exact shortlist used only for fronts that need holistic foresight.

        The horizon stays deliberately tiny (one additional gesture here).  Exact thick
        geometry is used for these shortlisted futures because false-positive free space
        proved much more expensive downstream than the handful of extra checks.
        """
        tf=dict(f); tf['path']=list(f['path'])+[p['end']]; tf['dir']=p['dir']
        tf['gestures']=f['gestures']+1; tf['local_gestures']=f['local_gestures']+1
        if f.get('travel',0.0)<5*self.module:
            # Keep source-egress semantics available while evaluating a genuinely young front.
            tf['gestures']=0
        out=[]
        for d in (p['dir'],(p['dir']-1)%8,(p['dir']+1)%8):
            for modules in (2,3):
                end=point_along_dir(p['end'],d,modules*self.module)
                self.stats['pathway_lookahead_evaluation_count']+=1
                if self._outside_limit(end): continue
                if self._candidate_loop_risk(tf,d,end): continue
                geom=self._corridor_geom(tf,p['end'],end)
                allow=(tf.get('intent')=='exit' or tf.get('gestures',0)>=2 or
                       self._forward_frame_distance(p['end'],d)<=2.5*self.module)
                if not self._gesture_clear(tf,p['end'],end,geom,allow_outside=allow,extra_segments=(p['geom'],)):
                    continue
                score=-.75*self._congestion_at(end)
                if not (0<=end[0]<=self.W and 0<=end[1]<=self.H): score+=.6
                out.append((score,d,modules,end,geom))
                if len(out)>=limit: return out
        return out

    def _lookahead_adjust(self,f,p):
        opts=self._future_options(f,p)
        if not opts:
            p['future_geom']=p['geom']
            return -12.0 if self._refresh_lifecycle(f) in ('LAUNCHING','STRUCTURAL_TRANSITION') else -4.0
        best=max(opts,key=lambda x:x[0])
        p['future_geom']=p['geom'].union(best[4]).buffer(.08*self.module)
        diversity=min(3,len({x[1] for x in opts}))
        return best[0]+.6*diversity

    def _child_birth_viable(self,child):
        """Prospective topology check without changing the child's prescribed structure."""
        modules=child.get('forced_straight_modules') or 2
        a=child['path'][-1]; b=point_along_dir(a,child['dir'],modules*self.module); g1=self._corridor_geom(child,a,b)
        allow=(child.get('intent')=='exit' or child.get('gestures',0)>=2 or self._forward_frame_distance(a,child['dir'])<=2.5*self.module)
        if not self._gesture_clear(child,a,b,g1,allow_outside=allow): return False
        tf=dict(child); tf['path']=list(child['path'])+[b]; tf['gestures']=0 if child.get('travel',0.0)<5*self.module else child['gestures']+1
        dirs=[]; turn=child.get('branch_turn')
        if turn in (-1,1): dirs.append((child['dir']+turn)%8)
        dirs.append(child['dir'])
        for d in dirs:
            m=(child.get('forced_turn_modules') or 2) if d!=child['dir'] else 2
            c=point_along_dir(b,d,m*self.module); g2=self._corridor_geom(tf,b,c)
            self.stats['pathway_lookahead_evaluation_count']+=1
            if self._gesture_clear(tf,b,c,g2,allow_outside=(allow or child.get('gestures',0)>=1),extra_segments=(g1,)):
                return True
        return False

    def _proposal_pair_conflicts(self,p,q):
        f=self.fronts[p['front']]; g=self.fronts[q['front']]
        if self._same_fan_rebase_compatible(f,q['front']) and q['dir']==p['dir']: return False
        a=p['geom'].difference(Point(p['start']).buffer(self._front_half_width(f)+1.5*self.U,quad_segs=6))
        b=q['geom'].difference(Point(q['start']).buffer(self._front_half_width(g)+1.5*self.U,quad_segs=6))
        return not a.is_empty and not b.is_empty and (a.intersects(b) or a.distance(b)<self.r.pathway_interroute_keepout)

    def _future_conflict(self,p,q):
        if self._proposal_pair_conflicts(p,q): return True
        f=self.fronts[p['front']]; g=self.fronts[q['front']]
        if (f.get('parent') is not None and f.get('parent')==g.get('parent') and
                f.get('fan_group')==g.get('fan_group') and f.get('fan_group') is not None): return False
        a=p.get('future_geom',p['geom']); b=q.get('future_geom',q['geom'])
        return a.intersects(b) or a.distance(b)<self.r.pathway_interroute_keepout

    def _variant_pools_conflict(self,va,vb):
        """Whether any viable proposal pair couples two fronts into one local transaction."""
        for p in va[:3]:
            for q in vb[:3]:
                if self._future_conflict(p,q):
                    return True
        return False

    def _conflict_groups(self,variant_map):
        """Return all local same-round conflict components from one immutable snapshot.

        V33 removes V30's semantic shortcut that only admitted "holistic" fronts to joint
        arbitration.  If proposals can affect each other, they belong to the same transaction.
        Nothing in a component is committed until that component has one compatible assignment.
        """
        ids=sorted(variant_map); adj={i:set() for i in ids}
        if len(ids)<2: return []
        pad=max(self.r.pathway_interroute_keepout,1.5*self.module)
        cell=max(2.5*self.module,1.0)
        buckets={}
        def pool_bounds(pool):
            bs=[p.get('future_geom',p['geom']).bounds for p in pool[:3]]
            return (min(b[0] for b in bs),min(b[1] for b in bs),max(b[2] for b in bs),max(b[3] for b in bs))
        def cells(bounds):
            x0,y0,x1,y1=bounds; x0-=pad; y0-=pad; x1+=pad; y1+=pad
            ix0,iy0=int(math.floor(x0/cell)),int(math.floor(y0/cell))
            ix1,iy1=int(math.floor(x1/cell)),int(math.floor(y1/cell))
            for iy in range(iy0,iy1+1):
                for ix in range(ix0,ix1+1): yield (ix,iy)
        for fid in ids:
            for c in cells(pool_bounds(variant_map[fid])): buckets.setdefault(c,[]).append(fid)
        pairs=set()
        for members in buckets.values():
            m=sorted(set(members))
            for i,a in enumerate(m):
                for b in m[i+1:]: pairs.add((a,b))
        for a,b in sorted(pairs):
            if self._variant_pools_conflict(variant_map[a],variant_map[b]):
                adj[a].add(b); adj[b].add(a)
        groups=[]; seen=set()
        for i in ids:
            if i in seen or not adj[i]: continue
            comp=[]; stack=[i]; seen.add(i)
            while stack:
                x=stack.pop(); comp.append(x)
                for y in sorted(adj[x],reverse=True):
                    if y not in seen:
                        seen.add(y); stack.append(y)
            groups.append(sorted(comp))
        return groups

    def _solve_conflict_group(self,group,variant_map):
        """Bounded deterministic joint assignment; every front gets a proposal or nobody commits."""
        group=sorted(group)
        pools={fid:list(variant_map[fid][:3]) for fid in group}
        # Most constrained fronts first improves pruning, while fid is a deterministic tiebreak.
        order=sorted(group,key=lambda fid:(len(pools[fid]),fid))
        best=None; checked=0; limit=1024
        chosen=[]
        def proposal_score(p):
            life=self._refresh_lifecycle(self.fronts[p['front']])
            bonus={'LAUNCHING':8.0,'STRUCTURAL_TRANSITION':7.0,'CONNECTION_PENDING':8.0,'RECOVERING':4.0}.get(life,0.0)
            return p['score']+bonus
        def key_for(seq):
            return tuple((p['front'],p['dir'],p['modules'],round(p['end'][0],4),round(p['end'][1],4)) for p in sorted(seq,key=lambda q:q['front']))
        def dfs(k,score):
            nonlocal best,checked
            if checked>=limit: return
            if k==len(order):
                checked+=1
                kseq=key_for(chosen)
                if best is None or score>best[0]+1e-9 or (abs(score-best[0])<=1e-9 and kseq<best[1]):
                    best=(score,kseq,list(chosen))
                return
            fid=order[k]
            for p in pools[fid]:
                checked+=1
                if checked>=limit: return
                if any(self._future_conflict(p,q) for q in chosen):
                    continue
                chosen.append(p); dfs(k+1,score+proposal_score(p)); chosen.pop()
        dfs(0,0.0)
        # V33: same-source protected siblings may jointly HOLD for a round.  The full group is
        # still solved from one snapshot; a hold is an explicit no-op, never a loser selected by
        # commit order.  Maximise number of movers first, then visual score, then canonical key.
        if best is None:
            fams={self._launch_family_key(self.fronts[fid]) for fid in group}
            main_family=(len(fams)==1 and all(not self.fronts[fid].get('local_gap') for fid in group))
            protected=any(self._main_launch_physically_protected(self.fronts[fid]) for fid in group)
            local_only=all(self.fronts[fid].get('local_gap') for fid in group)
            # HOLD is also a valid atomic outcome for local-gap peers.  Without it, a dense
            # local wave can deadlock at gesture zero because the all-or-nothing solver requires
            # every filler to move simultaneously.  A held filler is neither killed nor granted
            # ownership; it simply proposes again against the next committed snapshot.
            if (main_family and protected) or local_only:
                hbest=None; hchosen=[]; hchecked=0; hlimit=2048
                horder=sorted(group,key=lambda fid:(len(pools[fid]),fid))
                def hkey(seq):
                    return tuple((p['front'],p['dir'],p['modules'],round(p['end'][0],4),round(p['end'][1],4))
                                 for p in sorted(seq,key=lambda q:q['front']))
                def hdfs(k,score,moved):
                    nonlocal hbest,hchecked
                    if hchecked>=hlimit: return
                    if k==len(horder):
                        hchecked+=1
                        if moved<=0: return
                        key=hkey(hchosen); rank=(moved,score)
                        if hbest is None or rank>hbest[0] or (rank==hbest[0] and key<hbest[1]):
                            hbest=(rank,key,list(hchosen))
                        return
                    fid=horder[k]
                    hdfs(k+1,score,moved)  # HOLD
                    for p in pools[fid]:
                        hchecked+=1
                        if hchecked>=hlimit: return
                        if any(self._future_conflict(p,q) for q in hchosen): continue
                        hchosen.append(p); hdfs(k+1,score+proposal_score(p),moved+1); hchosen.pop()
                hdfs(0,0.0,0)
                checked+=hchecked
                if hbest is not None:
                    best=(hbest[0][1],hbest[1],hbest[2])
                    held=len(group)-len(hbest[2])
                    if held:
                        if local_only:
                            self.stats['pathway_local_gap_hold_round_count']+=1
                            self.stats['pathway_local_gap_hold_front_count']+=held
                        else:
                            self.stats['pathway_family_hold_round_count']+=1
                            self.stats['pathway_family_hold_front_count']+=held
        self.stats['pathway_conflict_combination_count']+=checked
        self.stats['pathway_conflict_region_count']+=1
        self.stats['pathway_conflict_region_front_count']+=len(group)
        return None if best is None else sorted(best[2],key=lambda p:p['front'])

    def _schedule_atomic_conflict_repair(self,group,round_index):
        """Defer an unsolved transaction and rewind causal history instead of choosing a loser."""
        fronts=[self.fronts[fid] for fid in sorted(group) if fid in self.fronts and self.fronts[fid].get('status')=='active']
        if not fronts: return False
        protected=[f for f in fronts if (f.get('parent') is None and not f.get('local_gap') and
                                          self._refresh_lifecycle(f)=='LAUNCHING')]
        # A young main launch has survival priority.  In a mixed conflict, recent history on the
        # other participants yields first.  If everyone is young (or nobody is), repair all peers
        # symmetrically; no front acquires ownership from sorting/commit order.
        repair=[f for f in fronts if f not in protected] if protected and len(protected)<len(fronts) else fronts
        scheduled=0
        for f in repair:
            if self._schedule_reroute(f,round_index,'same_round_conflict'):
                scheduled+=1
        if scheduled:
            self.stats['pathway_atomic_conflict_group_defer_count']+=1
            self.stats['pathway_atomic_conflict_group_repair_front_count']+=scheduled
        return bool(scheduled)

    def _find_active_blocker(self,f,round_index=None):
        """Find the most causally relevant active foreign route blocking a young front.

        Recency is based on the round that committed the blocking segment, not front-id or
        iteration order.  We prefer a non-launching blocker when protecting a young main launch.
        """
        start=f['path'][-1]; hits={}
        for d in (f['dir'],(f['dir']-1)%8,(f['dir']+1)%8):
            end=point_along_dir(start,d,2.5*self.module); geom=self._corridor_geom(f,start,end)
            probe=geom.difference(Point(start).buffer(self._front_half_width(f)+1.5*self.U,quad_segs=6))
            for rec in self.path_index.query(expand_bounds(probe.bounds,self.r.pathway_interroute_keepout)):
                if rec['chip']==f['chip'] or rec['front']==f['id']: continue
                if not (probe.intersects(rec['geom']) or probe.distance(rec['geom'])<self.r.pathway_interroute_keepout):
                    continue
                other=self.fronts.get(rec['front'])
                if other is None or other.get('status') not in ('active','terminated') or other.get('round_connection_peer') is not None:
                    continue
                if any(o.get('parent')==other['id'] for o in self.fronts.values()):
                    continue
                if any(tid in self.connected_trace_ids for tid in other.get('ids',())):
                    continue
                rr=int(rec.get('round_index',-1))
                if other.get('status')=='terminated' and round_index is not None and (rr<0 or round_index-rr>8):
                    continue
                prev=hits.get(other['id'])
                if prev is None or rr>prev[0]: hits[other['id']]=(rr,other)
        if not hits: return None
        young_main=(f.get('parent') is None and not f.get('local_gap') and self._refresh_lifecycle(f)=='LAUNCHING')
        def key(item):
            rr,o=item[1]
            other_young=(o.get('parent') is None and not o.get('local_gap') and self._refresh_lifecycle(o)=='LAUNCHING')
            age=(round_index-rr) if round_index is not None and rr>=0 else 999
            return ((1 if young_main and other_young else 0), age, -o.get('gestures',0), o['id'])
        return min(hits.items(),key=key)[1][1]

    def _reopen_terminal_for_causal_repair(self,f):
        """Reopen a recent unconnected terminal leaf so its own recent history may yield."""
        if f.get('status')!='terminated' or not f.get('route_history'):
            return False
        if any(o.get('parent')==f['id'] for o in self.fronts.values()):
            return False
        if any(tid in self.connected_trace_ids for tid in f.get('ids',())):
            return False
        self.stats['pathway_termination_count']=max(0,self.stats.get('pathway_termination_count',0)-1)
        self.stats['pathway_termination_trace_count']=max(0,self.stats.get('pathway_termination_trace_count',0)-len(f.get('ids',())))
        f['status']='active'; f['lifecycle']='RECOVERING'; f['termination_reason']=None
        self.stats['pathway_causal_terminal_reopen_count']+=1
        return True

    def _request_local_yield(self,f,round_index):
        """Ask the causal blocker to rewind; the blocked young route is not punished this round."""
        if self._refresh_lifecycle(f)!='LAUNCHING' or f.get('launch_yield_requests',0)>=4: return False
        b=self._find_active_blocker(f,round_index)
        if b is None or b.get('reroute_pending'): return False
        if b.get('status')=='terminated' and not self._reopen_terminal_for_causal_repair(b):
            return False
        if b.get('causal_yield_count',0)>=3: return False
        b['causal_yield_count']=b.get('causal_yield_count',0)+1
        if self._schedule_reroute(b,round_index,'yield_to_launch'):
            f['launch_yield_requests']=f.get('launch_yield_requests',0)+1
            self.stats['pathway_blocker_yield_count']+=1
            self.stats['pathway_causal_blocker_rollback_request_count']+=1
            return True
        return False

    def _launch_fronts(self):
        launch_spacings=[]; launch_coverages=[]; launch_gap_ratios=[]; launch_thicknesses=[]
        for chip_idx,chip in enumerate(self.chips):
            sides=['top','right','bottom','left']
            side_rng=self._new_rng(); side_rng.shuffle(sides)
            for side_index,side in enumerate(sides):
                starts,direction,spacing,thicks,side_span=self.r._chip_launch_bundle(chip,side,side_rng)
                launch_spacings.append(spacing); launch_thicknesses.extend(thicks)
                for ta,tb in zip(thicks,thicks[1:]):
                    mean_t=.5*(ta+tb)
                    if mean_t>1e-9:
                        launch_gap_ratios.append((spacing-.5*(ta+tb))/mean_t)
                coverage=((len(starts)-1)*spacing/side_span) if len(starts)>1 else 0.0
                launch_coverages.append(coverage)
                self.stats['pathway_bundle_count']+=1
                self.stats['pathway_launch_trace_count']+=len(starts)
                ids=[]; thicknesses={}; start_map={}; local_to_global={}
                for li,start in enumerate(starts):
                    tid=self.next_trace_id; self.next_trace_id+=1
                    ids.append(tid); local_to_global[li]=tid
                    thicknesses[tid]=thicks[li]; start_map[tid]=start
                cx=sum(start_map[i][0] for i in ids)/len(ids)
                cy=sum(start_map[i][1] for i in ids)/len(ids)
                vx,vy=dir_vec(direction); nx,ny=-vy,vx
                offsets={i:(start_map[i][0]-cx)*nx+(start_map[i][1]-cy)*ny for i in ids}
                slices=self._cohort_slices(len(starts),side_rng)
                fan_parts=[[local_to_global[li] for li in part] for part in slices]
                frng=self._new_rng()
                root=self._make_front(ids=ids,chip=chip_idx,side=side,side_index=side_index,
                                      path=[(cx,cy)],direction=direction,offsets=offsets,
                                      thicknesses=thicknesses,prefixes={},rng=frng,
                                      forced_straight_modules=int(self.launch_egress_modules))
                root['fan_parts']=fan_parts
                root['fan_pending']=len(fan_parts)>1
                root['launch_family_key']=(chip_idx,side_index,side)
                root['launch_egress_pending']=True
                for tid,start in start_map.items():
                    end=point_along_dir(start,direction,self.launch_egress_modules*self.module)
                    rad=.5*thicknesses[tid]+self.r.pathway_interroute_keepout
                    self.source_egress_reservations.append(dict(owner=(chip_idx,side_index,side),tid=tid,active=True,
                        geom=LineString([start,end]).buffer(rad,cap_style='round',join_style='mitre',quad_segs=4)))
                self.stats['pathway_launch_cohort_count']+=len(fan_parts)
        self.stats['pathway_launch_spacing_min']=min(launch_spacings,default=0.0)
        self.stats['pathway_launch_spacing_max']=max(launch_spacings,default=0.0)
        self.stats['pathway_launch_coverage_min']=min(launch_coverages,default=0.0)
        self.stats['pathway_launch_coverage_max']=max(launch_coverages,default=0.0)
        self.stats['pathway_launch_min_lane_edge_gap_ratio']=min(launch_gap_ratios,default=0.0)
        self.stats['pathway_trace_thickness_min']=min(launch_thicknesses,default=0.0)
        self.stats['pathway_trace_thickness_max']=max(launch_thicknesses,default=0.0)
        self.stats['pathway_trace_thickness_mean']=(sum(launch_thicknesses)/len(launch_thicknesses) if launch_thicknesses else 0.0)

    def _launch_family_key(self,f):
        key=f.get('launch_family_key')
        if key is not None: return key
        cur=f; seen=set()
        while cur.get('parent') is not None and cur.get('parent') in self.fronts and cur['id'] not in seen:
            seen.add(cur['id']); cur=self.fronts[cur['parent']]
        key=(cur.get('chip'),cur.get('side_index'),cur.get('side'))
        f['launch_family_key']=key
        return key

    def _launch_egress_cleared(self,f):
        if f.get('local_gap'): return True
        return self._minimum_materialized_lane_length(f) >= self.launch_egress_modules*self.module-1e-7

    def _source_egress_pending(self,f):
        return (f.get('parent') is None and not f.get('local_gap') and
                f.get('chip',len(self.chips))<len(self.chips) and not self._launch_egress_cleared(f))

    def _main_launch_physically_protected(self,f):
        if f.get('local_gap') or f.get('chip',len(self.chips))>=len(self.chips): return False
        return self._minimum_materialized_lane_length(f) < self.main_launch_maturity_modules*self.module-1e-7

    def _release_source_egress(self,owner):
        for rec in self.source_egress_reservations:
            if rec['owner']==owner:
                rec['active']=False

    def _reactivate_source_egress(self,owner):
        for rec in self.source_egress_reservations:
            if rec['owner']==owner:
                rec['active']=True

    def _family_has_protected_active(self,owner):
        for other in self.fronts.values():
            if other.get('status')!='active' or other.get('local_gap'): continue
            if self._launch_family_key(other)!=owner: continue
            if self._source_egress_pending(other): return True
        return False

    def _source_egress_clear_for_gesture(self,f,geom):
        if not self.source_egress_reservations or geom.is_empty: return True
        owner=self._launch_family_key(f)
        f_young=bool(self._source_egress_pending(f))
        for rec in self.source_egress_reservations:
            if not rec.get('active',True) or rec['owner']==owner: continue
            # Two newborn main families are peers. Their proposed geometry is arbitrated
            # transactionally; neither family may pre-own space through the reservation layer.
            if f_young and self._family_has_protected_active(rec['owner']):
                continue
            rg=rec['geom']
            if geom.intersects(rg) or geom.distance(rg)<.35*self.r.pathway_interroute_keepout:
                self.stats['pathway_launch_egress_reservation_reject_count']+=1
                return False
        return True

    def _gap_cell(self,p):
        n=self.r.local_gap_grid_n; x,y=p
        return (min(n-1,max(0,int(n*x/max(self.W,1e-9)))),
                min(n-1,max(0,int(n*y/max(self.H,1e-9)))))

    def _coverage_cell12(self,p):
        # Compatibility helper for board-wide historic coverage metrics.
        x,y=p
        return (min(11,max(0,int(12*x/max(self.W,1e-9)))),
                min(11,max(0,int(12*y/max(self.H,1e-9)))))

    def _residual_gap_regions(self):
        """Measure connected residual regions after the main network is frozen.

        V33 replaces the old 12x12 point heuristic with a denser connected-region field.
        Each region records its real local extent, aspect and principal orientation.  Local
        sources and targets are selected *inside the same region* so a tiny pocket receives a
        short line while a large corridor can receive several independent travellers.
        """
        n=self.r.local_gap_grid_n
        cw=self.W/n; ch=self.H/n
        open_cells=set()
        for gy in range(n):
            for gx in range(n):
                x=(gx+.5)*cw; y=(gy+.5)*ch; q=Point(x,y)
                if any(q.distance(g.geom)<max(self.r.pathway_main_chip_keepout,.48*self.module) for g in self.chips):
                    continue
                probe=q.buffer(.30*self.module,quad_segs=5)
                blocked=False
                for rec in self.path_index.query(expand_bounds(probe.bounds,.12*self.module)):
                    if probe.intersects(rec['geom']): blocked=True; break
                if not blocked: open_cells.add((gx,gy))
        regions=[]; by_cell={}; unseen=set(open_cells); rid=0
        # 4-neighbour connectivity avoids diagonally touching pockets being treated as one room.
        while unseen:
            seed=min(unseen); stack=[seed]; unseen.remove(seed); cells=[]
            while stack:
                c=stack.pop(); cells.append(c); x,y=c
                for nb in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if nb in unseen:
                        unseen.remove(nb); stack.append(nb)
            if len(cells)<2: continue
            xs=[c[0] for c in cells]; ys=[c[1] for c in cells]
            cx=sum((x+.5)*cw for x,_ in cells)/len(cells)
            cy=sum((y+.5)*ch for _,y in cells)/len(cells)
            w=(max(xs)-min(xs)+1)*cw; h=(max(ys)-min(ys)+1)*ch
            # Principal direction from covariance of cell centres.
            pts=[((x+.5)*cw,(y+.5)*ch) for x,y in cells]
            sxx=sum((x-cx)**2 for x,y in pts); syy=sum((y-cy)**2 for x,y in pts); sxy=sum((x-cx)*(y-cy) for x,y in pts)
            angle=.5*math.atan2(2*sxy,sxx-syy) if len(cells)>1 else 0.0
            vx,vy=math.cos(angle),math.sin(angle)
            d=nearest_dir_index(vx,vy)
            short=min(w,h); long=max(w,h)
            size='small' if len(cells)<10 or short<1.8*self.module else ('medium' if len(cells)<28 else 'large')
            rec=dict(id=rid,cells=set(cells),cell_count=len(cells),center=(cx,cy),width=w,height=h,
                     short_span=short,long_span=long,dir=d,size=size)
            regions.append(rec)
            for c in cells: by_cell[c]=rid
            rid+=1
        self.local_gap_regions=regions; self.local_gap_region_by_cell=by_cell
        self.stats['pathway_local_gap_region_count']=len(regions)
        return open_cells

    def _residual_gap_cells(self):
        return self._residual_gap_regions()

    def _mark_local_gap_segment_coverage(self,a,b):
        if not self.local_gap_open_cells: return
        n=self.r.local_gap_grid_n; cw=self.W/n; ch=self.H/n
        claim=1.45*self.module
        line=LineString([a,b])
        minx,miny,maxx,maxy=line.bounds
        gx0=max(0,int(math.floor((minx-claim)/cw))); gx1=min(n-1,int(math.floor((maxx+claim)/cw)))
        gy0=max(0,int(math.floor((miny-claim)/ch))); gy1=min(n-1,int(math.floor((maxy+claim)/ch)))
        for gy in range(gy0,gy1+1):
            for gx in range(gx0,gx1+1):
                cell=(gx,gy)
                if cell not in self.local_gap_open_cells: continue
                q=Point((gx+.5)*cw,(gy+.5)*ch)
                if q.distance(line)<=claim:
                    self.local_gap_coverage_cells.add(cell)

    def _local_gap_covered_cells(self):
        return set(self.local_gap_coverage_cells) & set(self.local_gap_open_cells)

    def _local_gap_target(self,center,rng,turn_hint=0):
        """Target uncovered space in the *same measured residual region* whenever possible."""
        uncovered=self.local_gap_open_cells-self._local_gap_covered_cells()
        if not uncovered: return self._underused_target(center,rng)
        here=self._gap_cell(center); rid=self.local_gap_region_by_cell.get(here)
        if rid is not None:
            region=self.local_gap_regions[rid]
            pool=list(region['cells'] & uncovered)
        else:
            pool=list(uncovered)
        if not pool: pool=list(uncovered)
        n=self.r.local_gap_grid_n; cw=self.W/n; ch=self.H/n
        hint=turn_hint if isinstance(turn_hint,int) and 0<=turn_hint<8 else None
        vx,vy=dir_vec(hint) if hint is not None else (0.0,0.0)
        scored=[]
        for gx,gy in pool:
            x=(gx+.5)*cw; y=(gy+.5)*ch; d=math.hypot(x-center[0],y-center[1])
            if d<.55*self.module: continue
            score=.55*d/max(self.module,1e-9)-1.15*self._congestion_at((x,y))
            if hint is not None:
                dx=x-center[0]; dy=y-center[1]; L=max(math.hypot(dx,dy),1e-9)
                score+=2.4*(dx*vx+dy*vy)/L
            scored.append((score,rng.random(),(x,y)))
        if not scored: return self._underused_target(center,rng)
        scored.sort(key=lambda z:(-z[0],z[1])); return scored[0][2]

    def _local_gap_source_clearance(self,p,half_width):
        """Conservative clearance for an interior local-network source."""
        q=Point(p)
        required=max(self.r.pathway_static_keepout,half_width+1.5*self.U)
        for gi,g in enumerate(self.static):
            keep=(self.r.pathway_main_chip_keepout if gi < len(self.chips) else self.r.pathway_static_keepout)
            if q.distance(g.geom)<keep+half_width:
                return False
        # Existing main-chip network geometry is already in the spatial index by the time
        # local-gap roots are proposed.  Give source markers and the initial bundle envelope
        # breathing room rather than spawning directly beside an occupied trace.
        probe=q.buffer(half_width+max(2.0*self.U,.22*self.module),quad_segs=8)
        for rec in self.path_index.query(expand_bounds(probe.bounds,self.r.pathway_interroute_keepout)):
            if probe.intersects(rec['geom']) or probe.distance(rec['geom'])<self.r.pathway_interroute_keepout:
                return False
        return True

    def _local_gap_bundle_spec(self,rng,count,special=False):
        """Return local-gap thickness/offset data with source/terminal-dot-safe pitch."""
        if special:
            base=rng.uniform(2.00*self.U,3.10*self.U)
            thicks=[base*rng.uniform(5.0,8.0)]
        else:
            # Extra-thick local traces are intentionally singleton-only, so ordinary local
            # bundles never invoke the rare emphasis-line path used by chip launches.
            thicks=[rng.uniform(2.00*self.U,3.10*self.U) for _ in range(count)]
        if count<=1:
            return thicks,{0:0.0},0.0
        pitch=0.0
        for a,b in zip(thicks,thicks[1:]):
            mean_t=.5*(a+b)
            line_pitch=.5*(a+b)+1.5*mean_t
            outer_a=self.r._termination_dot_radius(a)+.5*self.r.termination_dot_hollow_stroke
            outer_b=self.r._termination_dot_radius(b)+.5*self.r.termination_dot_hollow_stroke
            dot_pitch=outer_a+outer_b+self.r.termination_dot_min_gap
            pitch=max(pitch,line_pitch,dot_pitch)
        offsets={i:(i-(count-1)/2.0)*pitch for i in range(count)}
        return thicks,offsets,pitch

    def _local_gap_initial_clear(self,center,direction,offsets,thicknesses):
        ids=list(range(len(thicknesses)))
        temp=dict(id=-1,ids=ids,chip=len(self.chips)+100000,side='local',side_index=-1,
                  path=[tuple(center)],dir=direction,initial_dir=direction,offsets=dict(offsets),
                  thicknesses={i:thicknesses[i] for i in ids},prefixes={i:[] for i in ids},
                  parent=None,branch_parent=None,fan_group=None,branch_stage=None,fan_pending=False,
                  status='active',gestures=0,local_gestures=0,travel=0.0,failures=0,
                  turn_history=[],normal_segment_lengths=[],route_history=[],straight_since_turn=3,
                  lifecycle='LAUNCHING',recovery_fragment_child=False,reroute_pending=False,
                  reroute_mode_rounds=0,quality_repair_pending=False,round_connection_peer=None)
        # Require two plausible modules of immediate room; later routing remains fully
        # probabilistic/holistic.  This is just enough foresight to avoid creating local stubs.
        end=point_along_dir(center,direction,2.0*self.module)
        geom=self._corridor_geom(temp,center,end)
        if not self._gesture_clear(temp,center,end,geom,allow_outside=False):
            return False
        return True

    def _launch_local_gap_fronts(self, source_cap=None):
        """Spawn a coverage-driven local-network wave into residual open regions.

        The first wave measures the post-main residual field and samples a soft ~40% target.
        Later waves only target still-uncovered cells.  Exact routing invariants still decide
        what can physically be realised; the target never authorises intersections or search.
        """
        rng=SplitMix64(local_pathway_seed(self.sseed) ^ ((self.stats['pathway_local_gap_wave_count']+1)*0x9E3779B97F4A7C15))
        if not self.local_gap_open_cells:
            self.local_gap_open_cells=self._residual_gap_cells()
            self.local_gap_target_fraction=rng.uniform(*self.r.local_gap_fill_range)
            self.local_gap_target_count=int(round(len(self.local_gap_open_cells)*self.local_gap_target_fraction))
            self.stats['pathway_local_gap_fill_target_fraction']=self.local_gap_target_fraction
            self.stats['pathway_local_gap_open_cell_count']=len(self.local_gap_open_cells)
            self.stats['pathway_local_gap_target_cell_count']=self.local_gap_target_count
        covered=self._local_gap_covered_cells()
        needed=max(0,self.local_gap_target_count-len(covered))
        self.stats['pathway_local_gap_covered_cell_count']=len(covered)
        self.stats['pathway_local_gap_fill_actual']=(len(covered)/len(self.local_gap_open_cells) if self.local_gap_open_cells else 0.0)
        if needed<=0:
            return 0

        region_source_counts={r['id']:0 for r in self.local_gap_regions}
        for f in self.fronts.values():
            if f.get('local_gap') and f.get('parent') is None and f.get('local_gap_region_id') is not None:
                rid0=f.get('local_gap_region_id')
                region_source_counts[rid0]=region_source_counts.get(rid0,0)+1
        region_uncovered_counts={r['id']:len(r['cells']-(covered & r['cells'])) for r in self.local_gap_regions}

        margin=max(2.0*self.module,55.0*self.U)
        candidates=[]
        uncovered=list(self.local_gap_open_cells-covered)
        rng.shuffle(uncovered)
        for gx,gy in uncovered:
            self.stats['pathway_local_gap_spawn_attempt_count']+=1
            # Jitter inside the representative gap cell so separate waves do not reuse one point.
            n=self.r.local_gap_grid_n
            x=(gx+rng.uniform(.32,.68))*self.W/n
            y=(gy+rng.uniform(.32,.68))*self.H/n
            if not (margin<=x<=self.W-margin and margin<=y<=self.H-margin):
                continue
            q=Point(x,y)
            static_clear=min((q.distance(g.geom) for g in self.static),default=8*self.module)
            path_clear=min((q.distance(rec['geom']) for rec in self.path_segments),default=8*self.module)
            cell=self._gap_cell((x,y)); rid=self.local_gap_region_by_cell.get(cell)
            region=self.local_gap_regions[rid] if rid is not None and rid < len(self.local_gap_regions) else None
            region_need=(region_uncovered_counts.get(rid,1) if region else 1)
            existing=region_source_counts.get(rid,0)
            score=min(static_clear,5*self.module)+1.55*min(path_clear,5*self.module)-.45*self._congestion_at((x,y))*self.module
            # Prioritise unmet area, but diminish a room as it accumulates sources.
            score+=1.35*self.module*math.log1p(region_need)/(1.0+.65*existing)
            candidates.append((score,rng.random(),(x,y),rid))
        candidates.sort(key=lambda z:(-z[0],z[1]))
        if not candidates:
            return 0

        # V33: local traces are born independently. Source count is driven by residual area,
        # not by a fixed number of pre-bundled buses. A line usually claims roughly 2–4 grid
        # cells, so larger measured regions naturally receive several independent sources.
        normal_target=max(6,min(24,int(math.ceil(needed/2.20))))
        if source_cap is not None:
            normal_target=max(1,min(normal_target,int(source_cap)))
        if self.local_gap_special_probability is None:
            self.local_gap_special_probability=rng.uniform(.15,.26)
        special_probability=self.local_gap_special_probability
        plans=[]
        for _ in range(normal_target):
            plans.append((rng.random()<special_probability,1))

        used_points=[]; local_index=self.stats['pathway_local_gap_source_count']; normal_spawned=0; special_spawned=0
        spawned=0
        for special,count in plans:
            chosen=None
            for ci,(score,_,center,rid) in enumerate(candidates):
                if any(math.hypot(center[0]-p[0],center[1]-p[1])<1.00*self.module for p in used_points):
                    continue
                region=self.local_gap_regions[rid] if rid is not None and rid < len(self.local_gap_regions) else None
                if region is not None:
                    cap=max(1,min(14,int(math.ceil(region['cell_count']/7.0))))
                    if region_source_counts.get(rid,0)>=cap:
                        continue
                thicks,offsets,pitch=self._local_gap_bundle_spec(rng,count,special)
                if region is not None:
                    # Scale local stroke to the room: smaller pockets get lighter lines.
                    factor=.78 if region['size']=='small' else (1.0 if region['size']=='medium' else 1.08)
                    thicks=[t*factor for t in thicks]
                half=max((abs(offsets.get(i,0.0))+.5*thicks[i] for i in range(count)),default=.5*thicks[0])
                if not self._local_gap_source_clearance(center,half):
                    continue
                dirs=list(range(8)); rng.shuffle(dirs)
                scored=[]
                for d in dirs:
                    if not self._local_gap_initial_clear(center,d,offsets,thicks):
                        continue
                    p2=point_along_dir(center,d,2.5*self.module)
                    tgt=self._local_gap_target(center,rng,d)
                    before=math.hypot(tgt[0]-center[0],tgt[1]-center[1])
                    after=math.hypot(tgt[0]-p2[0],tgt[1]-p2[1])
                    scored.append((self._congestion_at(p2)-1.8*(before-after)/max(self.module,1e-9),
                                   -self._forward_frame_distance(center,d),rng.random(),d,tgt))
                if not scored:
                    self.stats['pathway_local_gap_spawn_reject_count']+=1
                    continue
                scored.sort(); direction=scored[0][3]; target=scored[0][4]
                chosen=(ci,center,thicks,offsets,pitch,direction,target,rid)
                break
            if chosen is None:
                continue
            ci,center,thicks,offsets,pitch,direction,target,rid=chosen
            candidates.pop(ci); used_points.append(center)
            if rid is not None: region_source_counts[rid]=region_source_counts.get(rid,0)+1
            ids=[]; tmap={}; omap={}; prefixes={}
            for li in range(count):
                tid=self.next_trace_id; self.next_trace_id+=1
                ids.append(tid); tmap[tid]=thicks[li]; omap[tid]=offsets[li]; prefixes[tid]=[]
            synthetic_chip=len(self.chips)+local_index
            frng=SplitMix64(rng.next_u64())
            root=self._make_front(ids=ids,chip=synthetic_chip,side='local',side_index=local_index,
                                  path=[center],direction=direction,offsets=omap,
                                  thicknesses=tmap,prefixes=prefixes,rng=frng,
                                  intent='explore',target=target,forced_straight_modules=2)
            root['local_gap']=True; root['local_gap_special']=bool(special); root['fan_pending']=False
            root['local_gap_region_id']=rid
            root['local_gap_branch_boost']=rng.uniform(*self.r.local_gap_branch_boost_range)
            root['local_gap_exit_allowed']=rng.random()<self.r.local_gap_exit_probability_factor
            region=self.local_gap_regions[rid] if rid is not None and rid < len(self.local_gap_regions) else None
            if region is None:
                root['max_gestures']=12+int(rng.random()*6)
            elif region['size']=='small':
                root['max_gestures']=6+int(rng.random()*5)
            elif region['size']=='medium':
                root['max_gestures']=11+int(rng.random()*7)
            else:
                root['max_gestures']=16+int(rng.random()*9)
            root['base_max_gestures']=root['max_gestures']
            local_index+=1; spawned+=1
            self.stats['pathway_bundle_count']+=1
            self.stats['pathway_local_gap_source_count']+=1
            self.stats['pathway_local_gap_trace_count']+=count
            self.stats['pathway_local_gap_independent_source_count']+=1
            if special:
                special_spawned+=count; self.stats['pathway_local_gap_special_thick_trace_count']+=count
            else:
                normal_spawned+=count
        total=self.stats['pathway_local_gap_trace_count']
        self.stats['pathway_local_gap_special_ratio']=(self.stats['pathway_local_gap_special_thick_trace_count']/total if total else 0.0)
        if spawned:
            self.stats['pathway_local_gap_wave_count']+=1
        return spawned

    def _structural_birth_sequence(self,child):
        """Return the complete mandatory short structural maneuver, or None.

        A newborn fan/branch child is not a routable object until its shared-direction rebase
        and prescribed peel have both been proven.  This closes the inter-round race where a
        child used to be created after only the rebase was known viable.
        """
        start=child['path'][-1]; d0=child['dir']
        m1=child.get('forced_straight_modules') or 2
        b=point_along_dir(start,d0,m1*self.module); g1=self._corridor_geom(child,start,b)
        allow=(child.get('intent')=='exit' or child.get('gestures',0)>=2 or self._forward_frame_distance(start,d0)<=2.5*self.module)
        if not self._gesture_clear(child,start,b,g1,allow_outside=allow): return None
        p1=dict(front=child['id'],start=start,end=b,dir=d0,modules=m1,geom=g1,score=0.0,
                structural_short_rebase=(m1==1),atomic_structural=True)
        turn=child.get('branch_turn')
        if turn not in (-1,1): return [p1]
        d1=(d0+turn)%8; m2=child.get('forced_turn_modules') or 2
        c=point_along_dir(b,d1,m2*self.module)
        tf=dict(child); tf['path']=list(child['path'])+[b]; tf['dir']=d0; tf['branch_stage']=1
        tf['gestures']=child.get('gestures',0)+1; tf['local_gestures']=child.get('local_gestures',0)+1
        g2=self._corridor_geom(tf,b,c)
        allow2=(allow or tf['gestures']>=2 or self._forward_frame_distance(b,d1)<=2.5*self.module)
        if not self._gesture_clear(tf,b,c,g2,allow_outside=allow2,extra_segments=(g1,)): return None
        p2=dict(front=child['id'],start=b,end=c,dir=d1,modules=m2,geom=g2,score=0.0,atomic_structural=True)
        return [p1,p2]

    def _fan_front(self,f):
        owned=set(f.get('ids',()))
        parts=[[i for i in p if i in owned] for p in f.get('fan_parts',[])]
        parts=[p for p in parts if p]
        if len(parts)<=1:
            f['fan_pending']=False
            return []
        realised=self._materialized_paths(f)
        endpoints={i:realised[i][-1] for i in f['ids']}
        parts.sort(key=lambda ids:sum(f['offsets'][i] for i in ids)/len(ids))
        turn_modules=2+int(f['rng'].random()*2)
        launch_fan=False
        rebase_modules=2
        children=[]; middle=(len(parts)-1)/2
        for rank,ids in enumerate(parts):
            cx=sum(endpoints[i][0] for i in ids)/len(ids)
            cy=sum(endpoints[i][1] for i in ids)/len(ids)
            vx,vy=dir_vec(f['dir']); nx,ny=-vy,vx
            offsets={i:(endpoints[i][0]-cx)*nx+(endpoints[i][1]-cy)*ny for i in ids}
            if abs(rank-middle)<.25:
                # Zero is an explicit one-module rebase run.  It keeps the middle cohort
                # straight while still guaranteeing that its local offset curve begins at
                # the inherited lane endpoints.
                turn=0
            elif rank<middle:
                turn=1
            else:
                turn=-1
            intent,target=(f['intent'],f['target']) if rank==int(round(middle)) else self._sample_intent(f['rng'],(cx,cy),f['dir'])
            if (turn and f.get('last_turn_sign') and turn==-f.get('last_turn_sign') and f.get('straight_since_turn',0)<2):
                turn=0
            child=self._make_front(ids=ids,chip=f['chip'],side=f['side'],side_index=f['side_index'],
                                   path=[(cx,cy)],direction=f['dir'],offsets=offsets,
                                   thicknesses={i:f['thicknesses'][i] for i in ids},
                                   prefixes={i:realised[i] for i in ids},rng=SplitMix64(f['rng'].next_u64()),
                                   depth=0,intent=intent,target=target,parent=f['id'],branch_turn=turn,
                                   fan_group=(f['chip'],f['side_index']),forced_straight_modules=rebase_modules,
                                   forced_turn_modules=turn_modules)
            child['launch_fan_short_rebase']=launch_fan
            child['gestures']=f['gestures']; child['travel']=f['travel']
            child['last_turn_sign']=f['last_turn_sign']; child['straight_since_turn']=f['straight_since_turn']
            child['origin']=f['origin']; child['initial_dir']=f.get('initial_dir',f['dir'])
            child['max_origin_distance']=max(
                f.get('max_origin_distance',0.0),math.hypot(cx-f['origin'][0],cy-f['origin'][1]))
            child['turn_history']=list(f.get('turn_history',[]))
            if f.get('local_gap'):
                child['local_gap']=True; child['local_gap_special']=bool(f.get('local_gap_special'))
                child['local_gap_branch_boost']=f.get('local_gap_branch_boost',4.0)
                child['local_gap_exit_allowed']=f.get('local_gap_exit_allowed',False)
            children.append(child)
        # Transactional fan: solve the short child maneuvers as one tiny local permutation.
        # The preferred visual fan is attempted first, but geometry may demand a different
        # non-crossing combination of straight / +/-45-degree child continuations.  This is
        # the bounded "permutational" layer: at most 3^3 structural combinations in normal
        # use, exact-checked before any topology or SVG geometry is committed.
        preferred=tuple(child.get('branch_turn',0) for child in children)
        def solve_turns(turns):
            seqs=[]
            for child,turn in zip(children,turns):
                child['branch_turn']=turn; child['branch_stage']=0
                seq=self._structural_birth_sequence(child)
                if seq is None: return None
                seqs.append((child,seq))
            flat=[p for _c,seq in seqs for p in seq]
            for i,a in enumerate(flat):
                for b in flat[i+1:]:
                    if a['front']==b['front']: continue
                    if self._proposal_pair_conflicts(a,b): return None
            return seqs
        sequences=solve_turns(preferred)
        used_fallback=False
        if sequences is None:
            import itertools
            best=None
            # Keep the search strictly tiny even if a future profile creates four cohorts.
            # For >3 cohorts, only vary the two outermost children and keep interiors straight.
            if len(children)<=3:
                turn_sets=itertools.product((1,0,-1),repeat=len(children))
            else:
                turn_sets=((a,)+tuple(0 for _ in children[1:-1])+(b,) for a in (1,0,-1) for b in (1,0,-1))
            for turns in turn_sets:
                if tuple(turns)==preferred: continue
                seqs=solve_turns(tuple(turns))
                if seqs is None: continue
                # Prefer the original design intent, then visible separation, then fewer turns.
                match=sum(1 for a,b in zip(turns,preferred) if a==b)
                separation=len(set(turns)); turning=sum(1 for t in turns if t)
                score=4.0*match+1.2*separation-.25*turning
                # Same-direction adjacent turns are legal but aesthetically secondary.
                score-=.35*sum(1 for a,b in zip(turns,turns[1:]) if a==b and a!=0)
                if best is None or score>best[0]: best=(score,tuple(turns),seqs)
            if best is not None:
                _score,turns,sequences=best; used_fallback=True
                for child,turn in zip(children,turns): child['branch_turn']=turn; child['branch_stage']=0
        if sequences is None:
            for child in children: self.fronts.pop(child['id'],None)
            f['fan_pending']=True
            self.stats['pathway_branch_preflight_reject_count']+=1
            self.stats['pathway_transactional_birth_reject_count']+=1
            return []
        if used_fallback:
            self.stats.setdefault('pathway_fan_permutation_fallback_count',0)
            self.stats['pathway_fan_permutation_fallback_count']+=1
        f['status']='branched'; f['fan_pending']=False
        self.stats['pathway_split_count']+=1
        if f.get('local_gap'): self.stats['pathway_local_gap_split_count']+=1
        for child,seq in sequences:
            for proposal in seq:
                if child.get('status')!='active': break
                self._accept(child,proposal)
        return children

    def _front_half_width(self,f):
        max_offset=max((abs(f['offsets'][i]) for i in f['ids']),default=0.0)
        max_stroke=max((f['thicknesses'][i] for i in f['ids']),default=0.0)
        return max_offset+max_stroke/2+.65*self.U

    def _offset_points(self, points, offset):
        if len(points)<2:
            return [tuple(points[0])] if points else []
        if abs(offset)<1e-8:
            return [tuple(p) for p in points]
        shifted=[offset_line_points(a,b,offset) for a,b in zip(points,points[1:])]
        out=[shifted[0][0]]
        for i in range(1,len(points)-1):
            a0,a1=shifted[i-1]; b0,b1=shifted[i]
            rx,ry=a1[0]-a0[0],a1[1]-a0[1]
            sx,sy=b1[0]-b0[0],b1[1]-b0[1]
            det=rx*sy-ry*sx
            if abs(det)<1e-9:
                out.append(a1)
                continue
            qx,qy=b0[0]-a0[0],b0[1]-a0[1]
            t=(qx*sy-qy*sx)/det
            out.append((a0[0]+t*rx,a0[1]+t*ry))
        out.append(shifted[-1][1])
        return out

    def _materialized_paths(self,f):
        out={}
        if len(f['path'])<2:
            vx,vy=dir_vec(f['dir']); nx,ny=-vy,vx
            local={i:[(f['path'][0][0]+nx*f['offsets'][i],f['path'][0][1]+ny*f['offsets'][i])] for i in f['ids']}
        else:
            local={i:self._offset_points(f['path'],f['offsets'][i]) for i in f['ids']}
        for i in f['ids']:
            prefix=f['prefixes'].get(i,[])
            if not prefix:
                out[i]=local[i]
            elif not local[i]:
                out[i]=list(prefix)
            else:
                pts=list(prefix)
                if math.hypot(pts[-1][0]-local[i][0][0],pts[-1][1]-local[i][0][1])>1e-5:
                    pts.append(local[i][0])
                pts.extend(local[i][1:])
                out[i]=pts
        return out

    def _partition_ids(self,f):
        ordered=sorted(f['ids'],key=lambda i:f['offsets'][i])
        n=len(ordered); rng=f['rng']
        cut=max(1,min(n-1,int(round(n*rng.uniform(.40,.60)))))
        return [ordered[:cut],ordered[cut:]]

    def _branch_front(self,f):
        if self._source_egress_pending(f):
            return []
        if len(f['ids'])<=1 or f['gestures']<f.get('branch_retry_after_gesture',0):
            return []
        realised=self._materialized_paths(f)
        endpoints={i:realised[i][-1] for i in f['ids']}
        parts=self._partition_ids(f)
        children=[]
        # Normal forks get a two-module shared-direction rebase.  During recovery, a wide
        # cohort may use a one-module lane-preserving rebase so splitting itself can become
        # the escape mechanism instead of repeatedly retrying the same blocked envelope.
        rescue_branch=(f.get('failures',0)>=2 or f.get('reroute_mode_rounds',0)>0 or
                       f.get('quality_repair_reason') in ('stagnation','turn_drift','bundle_persistence','bundle_middle_persistence'))
        local_parallel_split=bool(f.get('local_gap'))
        branch_straight_modules=1 if (rescue_branch or local_parallel_split) else 2
        branch_turn_modules=2+int(f['rng'].random()*2)
        for pi,ids in enumerate(parts):
            cx=sum(endpoints[i][0] for i in ids)/len(ids)
            cy=sum(endpoints[i][1] for i in ids)/len(ids)
            vx,vy=dir_vec(f['dir']); nx,ny=-vy,vx
            offsets={i:(endpoints[i][0]-cx)*nx+(endpoints[i][1]-cy)*ny for i in ids}
            # SVG's downward-positive y axis and Shapely's Cartesian signed-offset
            # convention have opposite visual handedness.  The lower signed-offset slice
            # therefore takes the +45-degree screen-space turn; the upper slice takes -45.
            # This makes the contiguous slices peel outward rather than exchange sides.
            if local_parallel_split:
                # Local bundles must visibly disband.  Their fork direction is chosen against
                # the residual-gap field, not left as a same-direction topological split.
                branch_turn=1 if pi==0 else -1
                intent='explore'
                target=self._local_gap_target((cx,cy),f['rng'],(f['dir']+branch_turn)%8)
            elif pi==0:
                branch_turn=1
                intent,target=f['intent'],f['target']
            else:
                branch_turn=-1
                intent,target=self._sample_intent(f['rng'],(cx,cy),f['dir'])
            # V34 prefix-aware branch grammar: never create an immediate opposite-sense peel
            # across an inherited parent tail. Keep moving straight and reconsider later.
            if (branch_turn and f.get('last_turn_sign') and branch_turn==-f.get('last_turn_sign') and
                    f.get('straight_since_turn',0)<2):
                branch_turn=0
                if f.get('local_gap'):
                    target=self._local_gap_target((cx,cy),f['rng'],f['dir'])
            child=self._make_front(ids=ids,chip=f['chip'],side=f['side'],side_index=f['side_index'],
                                   path=[(cx,cy)],direction=f['dir'],offsets=offsets,
                                   thicknesses={i:f['thicknesses'][i] for i in ids},
                                   prefixes={i:realised[i] for i in ids},rng=SplitMix64(f['rng'].next_u64()),
                                   depth=f['depth']+1,intent=intent,target=target,parent=f['id'],
                                   branch_turn=branch_turn,
                                   forced_straight_modules=branch_straight_modules,
                                   forced_turn_modules=branch_turn_modules)
            child['gestures']=f['gestures']; child['travel']=f['travel']
            if local_parallel_split:
                preferred=branch_turn
                chosen_turn=None
                for turn in (preferred,-preferred,0):
                    child['branch_turn']=turn; child['branch_stage']=0
                    child['target']=self._local_gap_target((cx,cy),child['rng'],(f['dir']+turn)%8 if turn else f['dir'])
                    if self._child_birth_viable(child):
                        chosen_turn=turn; break
                if chosen_turn is None:
                    child['branch_turn']=preferred; child['branch_stage']=0
                branch_turn=child['branch_turn']
            child['rescue_branch_short_rebase']=bool(rescue_branch)
            child['max_gestures']=max(f['max_gestures']+1,child['max_gestures'])
            child['last_turn_sign']=f['last_turn_sign']
            child['straight_since_turn']=f['straight_since_turn']
            child['origin']=f['origin']; child['initial_dir']=f.get('initial_dir',f['dir'])
            child['max_origin_distance']=max(
                f.get('max_origin_distance',0.0),math.hypot(cx-f['origin'][0],cy-f['origin'][1]))
            child['turn_history']=list(f.get('turn_history',[]))
            if f.get('local_gap'):
                child['local_gap']=True; child['local_gap_special']=bool(f.get('local_gap_special'))
                child['local_gap_branch_boost']=f.get('local_gap_branch_boost',4.0)
                child['local_gap_exit_allowed']=f.get('local_gap_exit_allowed',False)
            children.append(child)
        # Do not commit a fork whose children are born into a wall.  This is a cheap local
        # viability check, not route search: each child only tests its mandatory first rebase
        # gesture against the already-existing board.  If either side cannot emerge, the
        # parent stays active and may advance/reroute before trying to split again.
        blocked=False
        strict_birth=((f.get('travel',0.0)<5*self.module or rescue_branch) and not local_parallel_split)
        for child in children:
            if strict_birth:
                clear=self._child_birth_viable(child)
            else:
                modules=child.get('forced_straight_modules') or 2
                start=child['path'][-1]; end=point_along_dir(start,child['dir'],modules*self.module)
                geom=self._corridor_geom(child,start,end)
                allow_outside=(child['intent']=='exit' or child['gestures']>=2 or self._forward_frame_distance(start,child['dir'])<=2.5*self.module)
                clear=self._gesture_clear(child,start,end,geom,allow_outside=allow_outside)
            if not clear:
                blocked=True; break
        if blocked:
            for child in children:
                self.fronts.pop(child['id'],None)
            f['branch_retry_after_gesture']=f['gestures']+1
            self.stats['pathway_branch_preflight_reject_count']+=1
            self.stats['pathway_transactional_birth_reject_count']+=1
            return []
        f['status']='branched'
        self.stats['pathway_split_count']+=1
        if f.get('local_gap'): self.stats['pathway_local_gap_split_count']+=1
        return children

    def _should_branch(self,f):
        if f.get('fan_pending'):
            return False
        if len(f['ids'])<=1 or f['depth']>=5 or f['branch_stage'] is not None:
            return False
        if f['gestures']<f.get('branch_retry_after_gesture',0):
            return False
        # A shared round-level connection opportunity is allowed to peel a narrow child out
        # sooner.  The opportunity was computed from the same pre-move snapshot for all fronts.
        connection_guided=f.get('round_connection_peer') is not None
        is_local=bool(f.get('local_gap'))
        min_local=1 if (connection_guided or is_local) else 2
        if f['local_gestures']<min_local or f['straight_since_turn']<1:
            return False
        multiplicity=min(1.0,(len(f['ids'])-1)/5.0)
        p=self.profile['branch_appetite']*self.profile['branch_multiplier']*(.55+.65*multiplicity)
        # V24 local-gap networks need to disband much more readily than V23. Their purpose is
        # to articulate residual space, so broad parallel buses are short-lived. This is a soft
        # local tendency only; transactional birth/collision rules still decide feasibility.
        if is_local:
            p*=f.get('local_gap_branch_boost',4.0)
            local_late=max(2,int(math.ceil(.35*f.get('base_max_gestures',f['max_gestures']))))
            if f['gestures']>=local_late: p*=1.35
            if len(f['ids'])>=3 and f['gestures']>=3: p=max(p,.90)
            elif len(f['ids'])==2 and f['gestures']>=4: p=max(p,.80)
        # V20: keep the launch / early journey comparatively coherent, then become much more
        # willing to fan out once the route is in the later ~40% of its originally planned life.
        # This threshold is intentionally an initial tuning guess, not a hard design-law constant.
        late_threshold=max(5,int(math.ceil(self.profile['late_life_branch_start']*f.get('base_max_gestures',f['max_gestures']))))
        if f['gestures']>=late_threshold:
            p*=self.profile['late_life_branch_multiplier']
            self.stats['pathway_late_life_branch_attempt_count']+=1
        p=min(.985,p)
        if connection_guided:
            p=max(p,.90)
        if f['failures']>=2:
            p=max(p,.88)
        return f['rng'].random()<p

    def _assign_round_connection_targets(self,active,round_index):
        """Pair compatible cross-chip fronts from one immutable round snapshot.

        This is the holistic part of connection planning: neither front chases geometry that
        the other has already moved this round.  A disjoint set of pairs receives the same
        meeting objective, then normal proposal/collision rules decide whether it can happen.
        """
        for f in active:
            f['round_connection_peer']=None; f['round_connection_target']=None
        candidates=[]
        ordered=sorted((f for f in active if f['gestures']>=1 and f.get('branch_stage')!=0 and not f.get('local_gap') and not self._source_egress_pending(f)),key=lambda x:x['id'])
        for i,a in enumerate(ordered):
            pa=a['path'][-1]
            for b in ordered[i+1:]:
                if a['chip']==b['chip']:
                    continue
                pb=b['path'][-1]; d=math.hypot(pb[0]-pa[0],pb[1]-pa[1])
                desire=(a['intent']=='connect')+(b['intent']=='connect')
                max_d=(18.0 if desire else 13.0)*self.module
                if d<.55*self.module or d>max_d:
                    continue
                # Prefer already-narrow cohorts and explicit connect intents, but do not require
                # either: broad cohorts may progressively branch toward the opportunity.
                narrow_bonus=.45*(1.0/min(len(a['ids']),4)+1.0/min(len(b['ids']),4))
                priority=d/self.module-1.35*desire-narrow_bonus
                candidates.append((priority,a,b,d,desire))
        candidates.sort(key=lambda x:(x[0],x[1]['id'],x[2]['id']))
        used=set(); paired=0
        for _,a,b,d,desire in candidates:
            if a['id'] in used or b['id'] in used:
                continue
            # Pair randomness is derived from seed/round/front ids rather than proposal order.
            prng=SplitMix64(mix_once(self.sseed ^ 0xA24BAED4963EE407 ^
                                     ((round_index+1)*0x9E3779B97F4A7C15) ^
                                     ((a['id']+1)<<17) ^ ((b['id']+1)<<41)))
            va=dir_vec(a['dir']); vb=dir_vec(b['dir']); ux=(pb[0]-pa[0])/max(d,1e-9); uy=(pb[1]-pa[1])/max(d,1e-9)
            facing=(va[0]*ux+va[1]*uy>.18 and vb[0]*(-ux)+vb[1]*(-uy)>.18)
            young_close=(facing and d<=5.0*self.module and
                         (a.get('travel',0.0)<4.0*self.module or b.get('travel',0.0)<4.0*self.module or
                          self._refresh_lifecycle(a) in ('LAUNCHING','RECOVERING') or
                          self._refresh_lifecycle(b) in ('LAUNCHING','RECOVERING')))
            forced_close=(d<=3.0*self.module and facing) or young_close
            chance=1.0 if forced_close else min(.995,.78*self.profile['connection_appetite']+.10*desire)
            if prng.random()>=chance:
                continue
            pa,pb=a['path'][-1],b['path'][-1]
            meet=((pa[0]+pb[0])*.5,(pa[1]+pb[1])*.5)
            a['round_connection_peer']=b['id']; b['round_connection_peer']=a['id']
            a['round_connection_target']=meet; b['round_connection_target']=meet
            used.update((a['id'],b['id'])); paired+=1
        for f in active: self._refresh_lifecycle(f)
        if paired:
            self.stats['pathway_holistic_connection_pair_count']+=paired
            self.stats['pathway_holistic_connection_guided_round_count']+=1
        return paired

    def _assign_local_bundle_affinities(self,active,round_index):
        """Let independently-born local lines temporarily travel as a visual bundle.

        Pairing is deterministic from the sample seed and front ids and occurs 50% of the time
        when compatible local singleton heads enter the same neighbourhood.  The affinity lasts
        only 2–4 rounds; afterwards each line resumes its own region target, creating the desired
        bundle-then-peel behaviour without ever merging trace identity.
        """
        locals_=[f for f in active if f.get('local_gap') and len(f.get('ids',()))==1 and f.get('status')=='active']
        byid={f['id']:f for f in locals_}
        # Release expired/dead affinities first.
        for f in locals_:
            peer=byid.get(f.get('local_bundle_peer'))
            if f.get('local_bundle_until',-1) <= round_index or peer is None:
                if f.get('local_bundle_peer') is not None:
                    self.stats['pathway_local_gap_bundle_release_count']+=1
                f['local_bundle_peer']=None; f['local_bundle_until']=-1; f['local_bundle_dir']=None
                f['target']=self._local_gap_target(f['path'][-1],f['rng'],f['dir'])
        free=[f for f in locals_ if f.get('local_bundle_peer') is None and f.get('local_bundle_times',0)<1]
        candidates=[]
        for i,a in enumerate(free):
            pa=a['path'][-1]
            for b in free[i+1:]:
                if a.get('local_gap_region_id')!=b.get('local_gap_region_id'): continue
                pb=b['path'][-1]; d=math.hypot(pb[0]-pa[0],pb[1]-pa[1])
                if not (.55*self.module <= d <= 3.2*self.module): continue
                dd=(b['dir']-a['dir'])%8
                if dd not in (0,1,7): continue
                candidates.append((d,a,b))
        candidates.sort(key=lambda x:(x[0],x[1]['id'],x[2]['id']))
        used=set()
        for d,a,b in candidates:
            if a['id'] in used or b['id'] in used: continue
            prng=SplitMix64(mix_once(self.sseed ^ ((round_index+1)*0x9E3779B97F4A7C15) ^ ((a['id']+1)<<19) ^ ((b['id']+1)<<43)))
            if prng.random() >= self.r.local_gap_bundle_probability: continue
            # Choose one of the two already-compatible headings, never an abrupt synthetic turn.
            shared=a['dir'] if prng.random()<.5 else b['dir']
            until=round_index+2+int(prng.random()*3)
            for f,peer in ((a,b),(b,a)):
                f['local_bundle_peer']=peer['id']; f['local_bundle_until']=until; f['local_bundle_dir']=shared
                f['local_bundle_times']=f.get('local_bundle_times',0)+1
            used.update((a['id'],b['id'])); self.stats['pathway_local_gap_bundle_pair_count']+=1

    def _direction_candidates(self,f):
        if self._source_egress_pending(f):
            return [f['initial_dir']]
        if f.get('local_gap') and f.get('local_bundle_peer') is not None and f.get('local_bundle_dir') is not None:
            shared=f['local_bundle_dir']; delta=(shared-f['dir'])%8
            if delta in (0,1,7):
                # Alignment is a preference; ±45 remains available so exact geometry always wins.
                dirs=[shared,f['dir'],(shared-1)%8,(shared+1)%8]
                out=[]
                for d in dirs:
                    if d not in out and (d-f['dir'])%8 in (0,1,7): out.append(d)
                return out
        # Structural rebase runs come before recovery freedom.  Turning a newly split child
        # before it has moved straight would shift its offset lanes and create a tiny hook.
        if f.get('branch_stage')==0:
            return [f['dir']]
        # A hard-stop recovery is allowed to reconsider the junction more broadly.  The
        # ordinary grammar remains 0/+45/-45; reroute mode merely changes their ordering and
        # suppresses the direction that just led into the dead end.
        if f.get('reroute_mode_rounds',0)>0 and f['gestures']>0:
            # Genuine re-route: rollback invalidates the failed directional commitment. Consider
            # both legal 45-degree exits from the rollback junction before replaying the old
            # corridor. A 90-degree instantaneous pivot is still forbidden.
            dirs=[(f['dir']-1)%8,(f['dir']+1)%8,f['dir']]
            avoid=f.get('reroute_avoid_dir')
            return [d for d in dirs if d!=avoid] + ([avoid] if avoid in dirs else [])
        if f['gestures']==0:
            return [f['dir']]
        if f['branch_stage']==0:
            return [f['dir']]
        if f['branch_stage']==1:
            return [(f['dir']+f['branch_turn'])%8]
        if f['turn_cooldown']>0:
            return [f['dir']]
        dirs=[f['dir'],(f['dir']-1)%8,(f['dir']+1)%8]
        out=[]
        for d in dirs:
            delta=(d-f['dir'])%8
            sign=1 if delta==1 else -1 if delta==7 else 0
            if sign and f['last_turn_sign'] and sign==-f['last_turn_sign'] and f['straight_since_turn']<2:
                continue
            out.append(d)
        return out

    def _module_counts(self,f):
        if self._source_egress_pending(f):
            remain=max(1,int(math.ceil((self.launch_egress_modules*self.module-self._minimum_materialized_lane_length(f))/max(self.module,1e-9))))
            if f.get('reroute_mode_rounds',0)>0 or f.get('failures',0)>0:
                return list(range(1,min(4,remain)+1))[::-1]
            return [min(4,remain)]
        if (f.get('branch_stage')==0 or f['gestures']==0) and f.get('forced_straight_modules') is not None:
            return [f['forced_straight_modules']]
        if f.get('reroute_mode_rounds',0)>0 and f['gestures']>0:
            vals=[1,2,3]
            f['rng'].shuffle(vals)
            return vals
        if f.get('branch_stage')==1 and f.get('forced_turn_modules') is not None:
            return [f['forced_turn_modules']]
        if f['gestures']==0:
            return [1,2]
        pref=self.profile['preferred_run_modules']
        vals=sorted(set(max(2,min(5,x)) for x in (pref-1,pref,pref+1)))
        f['rng'].shuffle(vals)
        return vals

    def _corridor_geom(self,f,a,b):
        half=self._front_half_width(f)
        geom=LineString([a,b]).buffer(half,cap_style='flat',join_style='mitre',quad_segs=4)
        if len(f['path'])>=2:
            olddir=nearest_dir_index(f['path'][-1][0]-f['path'][-2][0],f['path'][-1][1]-f['path'][-2][1])
            newdir=nearest_dir_index(b[0]-a[0],b[1]-a[1])
            if olddir!=newdir:
                max_offset=max((abs(f['offsets'][i]) for i in f['ids']),default=0.0)
                max_stroke=max((f['thicknesses'][i] for i in f['ids']),default=0.0)
                miter_radius=1.10*max_offset+max_stroke/2+.65*self.U
                geom=geom.union(Point(a).buffer(miter_radius,quad_segs=8))
        return geom

    def _ancestor_front_ids(self,f):
        out=set(); parent=f.get('parent')
        while parent is not None:
            out.add(parent)
            parent=self.fronts[parent].get('parent')
        return out

    def _outside_limit(self,p):
        m=2.2*self.module
        return p[0]<-m or p[1]<-m or p[0]>self.W+m or p[1]>self.H+m

    def _forward_frame_distance(self,p,direction):
        vx,vy=dir_vec(direction); distances=[]
        if vx>1e-9: distances.append((self.W-p[0])/vx)
        elif vx<-1e-9: distances.append((0-p[0])/vx)
        if vy>1e-9: distances.append((self.H-p[1])/vy)
        elif vy<-1e-9: distances.append((0-p[1])/vy)
        return min((d for d in distances if d>=0),default=float('inf'))

    def _same_fan_rebase_compatible(self,f,other_front_id,other_rec=None):
        """Adjacent children of one just-fanned bus may rebase in parallel.

        Their coarse corridor envelopes overlap slightly by construction even though the final
        offset trace lanes are disjoint.  This exemption applies only to the first straight
        rebase of direct siblings, never to later turns or unrelated bundles.
        """
        if f.get('parent') is None or f.get('local_gestures',0)!=0 or f.get('branch_stage')!=0:
            return False
        other=self.fronts.get(other_front_id)
        if other is None or other.get('parent')!=f.get('parent') or other.get('fan_group')!=f.get('fan_group'):
            return False
        if other_rec is not None:
            od=nearest_dir_index(other_rec['end'][0]-other_rec['start'][0],other_rec['end'][1]-other_rec['start'][1])
            if od!=f['dir']:
                return False
        return True

    def _own_source_egress_exempt(self,f,a,b,gi):
        """Allow an originating cohort to leave its own chip halo monotonically.

        The 24U main-chip keepout is a no-approach/no-reentry rule, not a wall that traps
        the traces born on that chip.  While a LAUNCHING/STRUCTURAL_TRANSITION front is
        still inside the source halo, outward motion is legal even when the *buffered*
        bundle envelope overlaps the package perimeter.  Once the centre clears the halo
        plus its half-width, the exemption permanently disappears.
        """
        if gi!=f.get('chip') or gi>=len(self.chips): return False
        life=self._refresh_lifecycle(f)
        if life not in ('LAUNCHING','STRUCTURAL_TRANSITION') and not (f.get('recovery_fragment_child') and f.get('local_gestures',0)<2):
            return False
        chip=self.chips[gi]
        da=Point(a).distance(chip.geom); db=Point(b).distance(chip.geom)
        halo=self.r.pathway_main_chip_keepout+self._front_half_width(f)
        if da>halo+1e-7: return False
        c=chip.geom.centroid
        vx,vy=b[0]-a[0],b[1]-a[1]
        ox,oy=a[0]-c.x,a[1]-c.y
        # Distance from the source geometry may stay nearly flat while sliding away from a
        # rounded corner, so require non-decreasing distance plus non-inward radial motion.
        return db+1e-7>=da and vx*ox+vy*oy>=-1e-7

    def _visible_lane_step_ok(self,f,end,min_ratio=.10):
        """Reject a centerline move that would collapse an offset lane at a miter.

        Thick multi-lane bundles can have perfectly valid centre segments while an outside
        lane is shortened almost to zero by two nearby corners.  Check only the newly affected
        tail of each lane, keeping this exact visual test local and cheap.
        """
        if len(f.get('ids',()))<=1: return True
        pts=list(f.get('path',()))+[tuple(end)]
        if len(pts)<2: return True
        threshold=min_ratio*self.module-1e-7
        for tid in f['ids']:
            local=self._offset_points(pts,f['offsets'][tid])
            if len(local)<2: continue
            for x,y in zip(local[max(0,len(local)-3):],local[max(1,len(local)-2):]):
                if math.hypot(y[0]-x[0],y[1]-x[1])<threshold:
                    return False
        return True

    def _visible_lane_tail_grammar_ok(self,f,end):
        """Cheap exact check of the newly affected offset-lane tail."""
        pts0=list(f.get('path',()))
        if len(pts0)<2:
            return True
        newdir=nearest_dir_index(end[0]-pts0[-1][0],end[1]-pts0[-1][1])
        # Straight continuation cannot introduce a new turn grammar violation.
        if newdir==f.get('dir'):
            return True
        center_tail=pts0[-4:]+[tuple(end)]
        for tid in f.get('ids',()):
            local=self._offset_points(center_tail,f['offsets'][tid])
            prefix=list(f.get('prefixes',{}).get(tid,[]))[-4:]
            tail=list(prefix)
            if local:
                if tail and math.hypot(tail[-1][0]-local[0][0],tail[-1][1]-local[0][1])<=1e-5:
                    tail.extend(local[1:])
                else:
                    tail.extend(local)
            tail=tail[-8:]
            dirs=self._turn_directions(tail)
            for da,db in zip(dirs,dirs[1:]):
                if (db-da)%8 not in (0,1,7):
                    return False
            if self._points_have_compensating_zigzag(tail):
                return False
        return True

    def _gesture_clear(self,f,a,b,geom,allow_outside=False,extra_segments=()):
        if self._outside_limit(b):
            return False
        if not allow_outside and not (0<=b[0]<=self.W and 0<=b[1]<=self.H):
            return False
        half=self._front_half_width(f)
        start_disk=Point(a).buffer(half+1.5*self.U,quad_segs=6)
        probe=geom.difference(start_disk)
        for gi,g in enumerate(self.static):
            if self._own_source_egress_exempt(f,a,b,gi):
                continue
            keepout=(self.r.pathway_main_chip_keepout if gi < len(self.chips)
                     else self.r.pathway_static_keepout)
            if geom.intersects(g.geom) or geom.distance(g.geom)<keepout:
                return False
        if not self._source_egress_clear_for_gesture(f,geom):
            return False
        if not geom.is_empty:
            ancestors=self._ancestor_front_ids(f)
            # V33: the start disk is an ownership exemption, not an obstacle blind spot.  The
            # old implementation subtracted it from the candidate before *every* path check,
            # which let a foreign trace sitting just beyond the head become invisible.  Only
            # self/ancestor continuation may use the trimmed probe; foreign geometry sees the
            # complete proposed corridor.
            for rec in self.path_index.query(expand_bounds(geom.bounds,1.1*self.U)):
                other=rec['geom']
                own_history=(rec['front']==f['id'] or rec['front'] in ancestors)
                if own_history:
                    # The last segment of this front or one of its ancestors is the physical
                    # corridor being continued from.  Only that local endpoint contact is exempt;
                    # older geometry remains an obstacle and cannot be looped across later.
                    if math.hypot(rec['end'][0]-a[0],rec['end'][1]-a[1]) <= 2.0*self._front_half_width(f)+2*self.U:
                        continue
                    if (f.get('recovery_fragment_child') and rec['front']==f.get('parent') and
                            f.get('local_gestures',0)==0):
                        parent=self.fronts.get(f.get('parent'))
                        if parent is not None and parent.get('path'):
                            pend=parent['path'][-1]
                            if math.hypot(rec['end'][0]-pend[0],rec['end'][1]-pend[1])<=1e-5:
                                continue
                    if (rec['front']==f.get('parent') and f.get('local_gestures',0)==0 and
                            f.get('branch_stage')==0):
                        od=nearest_dir_index(rec['end'][0]-rec['start'][0],rec['end'][1]-rec['start'][1])
                        if od==f['dir']:
                            continue
                if self._same_fan_rebase_compatible(f,rec['front'],rec):
                    continue
                candidate_probe=probe if own_history else geom
                if candidate_probe.intersects(other) or candidate_probe.distance(other)<self.r.pathway_interroute_keepout:
                    return False
            for other in extra_segments:
                if probe.intersects(other) or probe.distance(other)<self.r.pathway_interroute_keepout:
                    return False
        if not self._visible_lane_step_ok(f,b):
            return False
        # V34: exact offset-lane grammar is needed only for the risky case: an opposite
        # compensating turn (or the first structural turn after inherited prefix history).
        # Running materialized-lane geometry for every ordinary candidate is both unnecessary
        # and computationally expensive.
        nd=nearest_dir_index(b[0]-a[0],b[1]-a[1])
        dd=(nd-f.get('dir',nd))%8
        sign=1 if dd==1 else -1 if dd==7 else 0
        risky_visible_turn=(sign and f.get('last_turn_sign') and sign==-f.get('last_turn_sign'))
        risky_structural=(sign and f.get('local_gestures',0)<=1 and bool(f.get('prefixes')))
        if (risky_visible_turn or risky_structural) and not self._visible_lane_tail_grammar_ok(f,b):
            return False
        return True

    def _candidate_loop_risk(self,f,direction,end):
        """Reject local curls before they can become a visible spiral or roundabout."""
        if f['gestures']<2:
            return False
        # A route may bend substantially, but it may never turn all the way around and face
        # directly back along its chip-emergence heading.  That hard 180-degree boundary makes
        # a full circular/roundabout route impossible even when there is ample empty space.
        if (direction-f.get('initial_dir',f['dir']))%8==4:
            return True
        # Never use a short compensating A→B→A twitch to escape a local obstacle. The old
        # renderer produced these as visible one-module zigzags; bounded lookahead must choose
        # a genuinely different future instead.
        if len(f.get('path',()))>=3 and f.get('branch_stage') is None:
            p0,p1=f['path'][-3],f['path'][-2]
            prev_dir=nearest_dir_index(p1[0]-p0[0],p1[1]-p0[1])
            last_len=math.hypot(f['path'][-1][0]-p1[0],f['path'][-1][1]-p1[1])
            if direction==prev_dir and direction!=f['dir'] and last_len<2.0*self.module-1e-7:
                return True
        # Do not return into the recent/history envelope even when no literal self-crossing occurs.
        for old in f['path'][:-2]:
            if math.hypot(end[0]-old[0],end[1]-old[1])<1.45*self.module:
                return True
        origin=f.get('origin',f['path'][0])
        after=math.hypot(end[0]-origin[0],end[1]-origin[1])
        maxd=f.get('max_origin_distance',0.0)
        if f['gestures']>=4 and f['intent'] not in ('connect','component'):
            if maxd>3.0*self.module and after<.72*maxd:
                return True
        delta=(direction-f['dir'])%8; sign=1 if delta==1 else -1 if delta==7 else 0
        if sign:
            recent=f.get('turn_history',[])[-5:]
            # Three same-sense 45-degree turns in a short window is the beginning of a curl.
            if len(nz:= [x for x in recent if x])>=2 and nz[-1]==sign and nz[-2]==sign and recent.count(0)<=2:
                return True
        return False

    def _point_free_radius(self,f,p,max_radius=None):
        """Fast local free-space estimate using the router's occupancy grid plus chip distance."""
        max_radius=(3.8*self.module if max_radius is None else float(max_radius))
        x,y=p
        if x<0 or y<0 or x>self.W or y>self.H: return 0.0
        free=min(max_radius,x,y,self.W-x,self.H-y)
        # Chips are few, so exact distance here is cheap. Pathway density comes from the already
        # maintained 40x40 congestion field rather than per-candidate geometry scans.
        for gi,g in enumerate(self.static[:len(self.chips)]):
            if gi==f.get('chip'): continue
            free=min(free,max(0.0,Point(p).distance(g.geom)-self.r.pathway_main_chip_keepout-self._front_half_width(f)))
        congestion=self._congestion_at(p)
        # One committed trace in the local cell should noticeably reduce capacity; several traces
        # make it effectively closed. This is only ranking guidance: _gesture_clear remains exact.
        free*=max(0.0,1.0-min(1.0,congestion/3.2))
        return max(0.0,free)

    def _local_space_capacity(self,f,end,direction):
        """Bounded corridor-capacity score from the existing 40x40 occupancy field."""
        self.stats['pathway_local_space_capacity_evaluation_count']+=1
        probes=[
            (end,1.0),
            (point_along_dir(end,direction,1.5*self.module),1.35),
            (point_along_dir(end,direction,3.0*self.module),1.15),
            (point_along_dir(end,(direction-1)%8,1.8*self.module),.62),
            (point_along_dir(end,(direction+1)%8,1.8*self.module),.62),
        ]
        total=0.0; weight=0.0
        for p,w in probes:
            if not (-.1*self.module<=p[0]<=self.W+.1*self.module and -.1*self.module<=p[1]<=self.H+.1*self.module):
                continue
            total += w*min(3.8,self._point_free_radius(f,p)/(max(self.module,1e-9)))
            weight += w
        return total/max(weight,1e-9)

    def _score_candidate(self,f,direction,modules,end):
        rng=f['rng']; start=f['path'][-1]
        point=Point(end)
        static_clear=min((point.distance(g.geom) for g in self.static),default=6*self.module)
        free_score=min(static_clear,6*self.module)/self.module
        cell=(min(11,max(0,int(12*end[0]/self.W))),min(11,max(0,int(12*end[1]/self.H))))
        underused=1.6 if cell not in self.coverage_cells else -.25
        space_capacity=self._local_space_capacity(f,end,direction)
        score=.62*free_score+underused-.28*self._congestion_at(end)+1.35*space_capacity
        if f.get('reroute_mode_rounds',0)>0:
            # Recovery is explicitly corridor-seeking: after rollback, actual open room matters
            # more than preserving the failed trajectory's old aesthetic bias.
            score+=1.55*space_capacity
        if f['target'] is not None:
            before=math.hypot(f['target'][0]-start[0],f['target'][1]-start[1])
            after=math.hypot(f['target'][0]-end[0],f['target'][1]-end[1])
            target_weight=4.6 if f.get('local_gap') else 2.8
            score+=target_weight*(before-after)/max(self.module,1e-9)
        if f.get('local_gap'):
            if f.get('local_bundle_peer') is not None and direction==f.get('local_bundle_dir'):
                score+=3.0
            inside=(0<=end[0]<=self.W and 0<=end[1]<=self.H)
            if not inside:
                score-=3.2
            else:
                frame=min(end[0],end[1],self.W-end[0],self.H-end[1])
                turn=((direction-f['dir'])%8) in (1,7)
                if frame<1.5*self.module and turn:
                    score+=2.6
        meeting=f.get('round_connection_target')
        if meeting is not None:
            before=math.hypot(meeting[0]-start[0],meeting[1]-start[1])
            after=math.hypot(meeting[0]-end[0],meeting[1]-end[1])
            score+=4.2*(before-after)/max(self.module,1e-9)
        origin=f.get('origin',f['path'][0])
        before_o=math.hypot(start[0]-origin[0],start[1]-origin[1])
        after_o=math.hypot(end[0]-origin[0],end[1]-origin[1])
        score+=.70*self.profile['outward_bias']*(after_o-before_o)/max(self.module,1e-9)
        if f['intent']=='connect':
            foreign=[o for o in self.fronts.values() if o['status']=='active' and o['chip']!=f['chip'] and o['gestures']>0]
            if foreign:
                before=min(math.hypot(o['path'][-1][0]-start[0],o['path'][-1][1]-start[1]) for o in foreign)
                after=min(math.hypot(o['path'][-1][0]-end[0],o['path'][-1][1]-end[1]) for o in foreign)
                score+=1.7*(before-after)/max(self.module,1e-9)
        turn=((direction-f['dir'])%8) in (1,7)
        if f.get('reroute_mode_rounds',0)>0:
            if direction==f.get('reroute_avoid_dir'):
                score-=4.0
            elif turn:
                score+=2.4
        if turn and f['straight_since_turn']>=2:
            score+=2.2*self.profile['turn_appetite']
        elif not turn:
            score+=.45
        score-=.16*abs(modules-self.profile['preferred_run_modules'])
        return score+rng.uniform(-.55,.55)

    def _propose(self,f):
        start=f['path'][-1]
        # Intent biases the route; it does not forbid a useful outcome discovered naturally.
        # After two meaningful gestures any front may continue through the frame instead of
        # being forced to terminate simply because it was initially labelled explore/connect.
        base_allow_outside=(f['intent']=='exit' or f['gestures']>=2 or
                            self._forward_frame_distance(start,f['dir'])<=2.5*self.module)
        allow_outside=(base_allow_outside and
                       (not f.get('local_gap') or f.get('local_gap_exit_allowed',False)))
        def collect(directions,module_counts=None):
            found=[]
            for direction in directions:
                counts=self._module_counts(f) if module_counts is None else list(module_counts)
                for modules in counts:
                    end=point_along_dir(start,direction,modules*self.module)
                    geom=self._corridor_geom(f,start,end)
                    if self._candidate_loop_risk(f,direction,end):
                        self.stats['pathway_loop_candidate_reject_count']+=1
                        continue
                    if not self._gesture_clear(f,start,end,geom,allow_outside=allow_outside):
                        continue
                    score=self._score_candidate(f,direction,modules,end)
                    found.append(dict(front=f['id'],start=start,end=end,dir=direction,
                                      modules=modules,geom=geom,score=score,
                                      reroute_short_step=(modules==1 and f.get('reroute_mode_rounds',0)>0 and f['gestures']>0),
                                      structural_short_rebase=(modules==1 and f.get('branch_stage')==0 and
                                                               (f.get('launch_fan_short_rebase',False) or
                                                                f.get('rescue_branch_short_rebase',False) or
                                                                f.get('local_gap',False)))))
            return found
        candidates=collect(self._direction_candidates(f))
        # Prefer a two-module common launch trunk so a side reads as one bus before
        # it fans out.  A crowded side may fall back to exactly one module—never a
        # micro-segment—before the narrower child cohorts take over.
        if not candidates and self._source_egress_pending(f):
            candidates=collect([f['dir']],module_counts=(1,))
        # A structural fan or branch asks each child to peel away after its shared
        # run.  That turn is a preference, not a reason to kill an otherwise healthy
        # bundle: if the assigned side is blocked, keep the child moving straight for
        # a full two-module gesture.  It can branch or turn later when the plane offers
        # a real opening.  This is the bundle-level equivalent of a human declining an
        # awkward turn, and avoids the dense comb of premature terminations.
        if not candidates and f.get('branch_stage')==1:
            candidates=collect([f['dir']],module_counts=(2,))
        # A hard-stopped child that cannot complete its normal two-module rebase gets one
        # recovery-only one-module straight step.  It still cannot turn before rebasing, so
        # lane ordering remains continuous and no tiny diagonal hook is introduced.
        if not candidates and f.get('branch_stage')==0 and f.get('reroute_mode_rounds'):
            candidates=collect([f['dir']],module_counts=(1,))
            for c in candidates:
                c['reroute_short_rebase']=True
        # Directional persistence is the normal grammar, but it must not turn a clear side
        # passage into three identical failed attempts.  When the committed run is physically
        # blocked, one same-sense 45-degree avoidance turn is considered.  An opposite
        # compensating turn remains forbidden until two meaningful straight runs have occurred.
        if not candidates and f['gestures']>0 and f['branch_stage'] not in (0,1):
            avoidance=[]
            for sign in (-1,1):
                if f['last_turn_sign'] and sign==-f['last_turn_sign'] and f['straight_since_turn']<2:
                    continue
                avoidance.append((f['dir']+sign)%8)
            candidates=collect(avoidance,module_counts=((2,3) if f.get('reroute_mode_rounds') else (2,)))
        if not candidates:
            return None
        candidates.sort(key=lambda c:(-c['score'],c['dir'],c['modules']))
        shortlist=candidates[:min(5,len(candidates))]
        low=min(c['score'] for c in shortlist)
        weights=[(c,max(.12,c['score']-low+.35)) for c in shortlist]
        return f['rng'].weighted(weights)

    def _proposal_variants(self,f,count=2):
        out=[]; seen=set()
        for _ in range(max(1,count)):
            p=self._propose(f)
            if p is None: continue
            key=(p['dir'],p['modules'],round(p['end'][0],4),round(p['end'][1],4))
            if key in seen: continue
            seen.add(key); p=dict(p)
            p['future_geom']=p['geom']
            if self._needs_holistic(f):
                p['score']+=self._lookahead_adjust(f,p); self.stats['pathway_holistic_front_round_count']+=1
            p['priority']=p['score']+f['rng'].uniform(-.22,.22)
            if f.get('recovery_fragment_child') and f.get('local_gestures',0)==0:
                p['priority']+=100.0
            out.append(p)
        return sorted(out,key=lambda x:(-x['priority'],x['front']))

    def _record_segment(self,f,a,b,geom,normal=True):
        L=math.hypot(b[0]-a[0],b[1]-a[1])
        # Central audit classification: anything below the two-module normal grammar is an
        # explicit structural/recovery/terminal exception, never allowed to contaminate the
        # reported normal-segment minimum.  Callers still decide whether such a segment is legal;
        # this function only keeps the diagnostic categories truthful.
        if normal and L < 2.0*self.module-1e-9:
            normal=False
            self.stats['pathway_minimum_segment_exception_count']+=1
        rec=dict(geom=geom,front=f['id'],root=(f['chip'],f['side'],f['side_index']),chip=f['chip'],start=a,end=b,
                 round_index=int(f.get('_routing_round',-1)))
        self.path_segments.append(rec); self.path_index.insert(rec,geom.bounds); self._grid_add_segment(a,b)
        if f.get('local_gap'):
            self._mark_local_gap_segment_coverage(a,b)
        if normal:
            f['normal_segment_lengths'].append(L)
        steps=max(1,int(math.ceil(L/(.45*self.module))))
        for k in range(steps+1):
            t=k/steps; x=a[0]+(b[0]-a[0])*t; y=a[1]+(b[1]-a[1])*t
            if 0<=x<=self.W and 0<=y<=self.H:
                self.coverage_cells.add((min(11,int(12*x/self.W)),min(11,int(12*y/self.H))))

    def _rebuild_path_index_and_coverage(self):
        self.path_index=SpatialHash(max(80*self.U,3*self.module))
        self.coverage_cells=set()
        self.local_gap_coverage_cells=set()
        self._rebuild_congestion_grid()
        for rec in self.path_segments:
            self.path_index.insert(rec,rec['geom'].bounds)
            a,b=rec['start'],rec['end']
            f=self.fronts.get(rec['front'])
            if f and f.get('local_gap'):
                self._mark_local_gap_segment_coverage(a,b)
            steps=max(1,int(math.ceil(math.hypot(b[0]-a[0],b[1]-a[1])/(.45*self.module))))
            for k in range(steps+1):
                t=k/steps; x=a[0]+(b[0]-a[0])*t; y=a[1]+(b[1]-a[1])*t
                if 0<=x<=self.W and 0<=y<=self.H:
                    self.coverage_cells.add((min(11,int(12*x/self.W)),min(11,int(12*y/self.H))))

    def _traceback_for_reroute(self,f):
        # Recovery is not just a one-step dead-end escape.  V19 lets later repair attempts
        # rewind progressively farther (up to six accepted gestures) while respecting any
        # segment floor locked by an existing physical connection.
        local_segments=max(0,len(f['path'])-1)
        floor=max(0,int(f.get('recovery_floor_segments',0)))
        # V33: a root main-chip launch has no post-emergence segment ownership.  Until an
        # explicit structural/connection lock raises the floor, recovery may rewind it all the
        # way to the emergence anchor.  Child/shared-prefix fronts still carry their raised floor.
        if f.get('parent') is None and not f.get('local_gap') and not f.get('connection_lock'):
            floor=0
        removable=max(0,local_segments-floor)
        requested=min(8,max(3 if self._refresh_lifecycle(f)=='LAUNCHING' else 2,2+2*f.get('reroute_attempts',0)))
        if f.get('local_gap'):
            requested=min(requested,2)
        count=min(removable,requested)
        original_path=list(f.get('path',()))
        failed_dir=f['dir']
        replay_dir=failed_dir
        if count>0 and len(original_path)>=count+1:
            new_len=len(original_path)-count
            if 1<=new_len<len(original_path):
                a0=original_path[new_len-1]; b0=original_path[new_len]
                replay_dir=nearest_dir_index(b0[0]-a0[0],b0[1]-a0[1])
        if count>0 and len(f['route_history'])>=count:
            for _ in range(count):
                snap=f['route_history'].pop()
                if len(f['path'])>1:
                    f['path'].pop()
                f['dir']=snap['dir']; f['travel']=snap['travel']; f['gestures']=snap['gestures']
                f['local_gestures']=snap['local_gestures']; f['turn_cooldown']=snap['turn_cooldown']
                f['straight_since_turn']=snap['straight_since_turn']; f['last_turn_sign']=snap['last_turn_sign']
                f['branch_stage']=snap['branch_stage']; f['branch_turn']=snap['branch_turn']
                f['max_origin_distance']=snap.get('max_origin_distance',f.get('max_origin_distance',0.0))
                f['stagnant_gestures']=snap.get('stagnant_gestures',0)
                f['turn_history']=list(snap.get('turn_history',[]))
                del f['normal_segment_lengths'][snap['normal_len_count']:]
                for j in range(len(self.path_segments)-1,-1,-1):
                    if self.path_segments[j]['front']==f['id']:
                        self.path_segments.pop(j); break
            self._rebuild_path_index_and_coverage()
            if self._source_egress_pending(f):
                f['launch_egress_pending']=True
                self._reactivate_source_egress(self._launch_family_key(f))
            self.stats['pathway_traceback_count']+=1
            self.stats['pathway_traceback_segment_count']+=count
            if count>=3:
                self.stats['pathway_deep_traceback_count']+=1
            if floor==0 and len(f.get('path',()))==1 and f.get('parent') is None and not f.get('local_gap'):
                self.stats['pathway_root_emergence_traceback_count']+=1
        f['failures']=0
        f['reroute_pending']=False; f['reroute_ready_round']=None
        f['quality_repair_pending']=False; f['quality_repair_reason']=None
        f['reroute_attempts']+=1; f['reroute_mode_rounds']=(6 if self._refresh_lifecycle(f)=='LAUNCHING' else 4)
        f['reroute_avoid_dir']=replay_dir
        f['reroute_failed_head_dir']=failed_dir
        f['reroute_replay_dir']=replay_dir
        return count

    def _schedule_reroute(self,f,round_index,reason='hard_stop'):
        if f.get('reroute_pending'):
            return True
        budget=(self.profile['reroute_budget']+3 if reason=='yield_to_launch' else (min(self.profile['reroute_budget'],4) if f.get('local_gap') else self.profile['reroute_budget']))
        if f['reroute_attempts']>=budget:
            self.stats['pathway_reroute_exhausted_count']+=1
            return False
        f['reroute_pending']=True; f['reroute_ready_round']=round_index+1; f['failures']=0
        f['reroute_reason']=reason; f['lifecycle']='RECOVERING'
        self.stats['pathway_reroute_scheduled_count']+=1
        if reason!='hard_stop':
            self.stats['pathway_general_repair_scheduled_count']+=1
        if reason=='same_round_conflict':
            self.stats['pathway_conflict_repair_scheduled_count']+=1
        elif reason=='stagnation':
            self.stats['pathway_progress_repair_scheduled_count']+=1
        return True

    def _accept(self,f,p,defer_post=False):
        f['route_history'].append(dict(
            dir=f['dir'],travel=f['travel'],gestures=f['gestures'],local_gestures=f['local_gestures'],
            turn_cooldown=f['turn_cooldown'],straight_since_turn=f['straight_since_turn'],
            last_turn_sign=f['last_turn_sign'],branch_stage=f['branch_stage'],branch_turn=f['branch_turn'],
            max_origin_distance=f.get('max_origin_distance',0.0),stagnant_gestures=f.get('stagnant_gestures',0),
            turn_history=list(f.get('turn_history',[])),normal_len_count=len(f['normal_segment_lengths'])
        ))
        olddir=f['dir']; f['path'].append(p['end']); f['dir']=p['dir']
        length=math.hypot(p['end'][0]-p['start'][0],p['end'][1]-p['start'][1])
        was_rerouting=f.get('reroute_mode_rounds',0)>0
        f['travel']+=length; f['gestures']+=1; f['local_gestures']+=1; f['failures']=0
        if was_rerouting:
            self.stats['pathway_reroute_recovery_count']+=1
            f['reroute_mode_rounds']=max(0,f['reroute_mode_rounds']-1)
            if f['reroute_mode_rounds']==0:
                f['reroute_avoid_dir']=None
        delta=(p['dir']-olddir)%8; sign=1 if delta==1 else -1 if delta==7 else 0
        if sign:
            f['last_turn_sign']=sign; f['straight_since_turn']=0; f['turn_cooldown']=2
        else:
            f['straight_since_turn']+=1; f['turn_cooldown']=max(0,f['turn_cooldown']-1)
        f['turn_history']=(f.get('turn_history',[])+[sign])[-7:]
        origin=f.get('origin',f['path'][0]); od=math.hypot(p['end'][0]-origin[0],p['end'][1]-origin[1])
        oldmax=f.get('max_origin_distance',0.0)
        if od>oldmax+.28*self.module:
            f['stagnant_gestures']=0
        else:
            f['stagnant_gestures']=f.get('stagnant_gestures',0)+1
        f['max_origin_distance']=max(oldmax,od)
        if (f['gestures']>=4 and f['stagnant_gestures']>=2 and
                f.get('round_connection_target') is None and not f.get('reroute_pending')):
            f['quality_repair_pending']=True; f['quality_repair_reason']='stagnation'
        recent_turns=[x for x in f.get('turn_history',[])[-5:] if x]
        if (f['gestures']>=5 and len(recent_turns)>=4 and abs(sum(recent_turns))>=3 and
                f.get('round_connection_target') is None and not f.get('reroute_pending')):
            f['quality_repair_pending']=True; f['quality_repair_reason']='turn_drift'
        if f['branch_stage']==0:
            if f.get('branch_turn')==0:
                f['branch_stage']=None; f['branch_turn']=None
            else:
                f['branch_stage']=1
        elif f['branch_stage']==1:
            f['branch_stage']=None; f['branch_turn']=None
        self._refresh_lifecycle(f)
        if p.get('reroute_short_rebase') or p.get('reroute_short_step') or p.get('structural_short_rebase'):
            if p.get('reroute_short_rebase') or p.get('reroute_short_step'):
                self.stats['pathway_reroute_short_rebase_count']+=1
            self.stats['pathway_minimum_segment_exception_count']+=1
        self._record_segment(f,p['start'],p['end'],p['geom'],
                             normal=not (p.get('reroute_short_rebase',False) or p.get('reroute_short_step',False) or
                                         p.get('structural_short_rebase',False)))
        if f.get('parent') is None and not f.get('local_gap') and self._launch_egress_cleared(f):
            f['launch_egress_pending']=False
            self._release_source_egress(self._launch_family_key(f))
        if defer_post:
            return
        self._post_accept(f,p)

    def _post_accept(self,f,p):
        x,y=p['end']
        if x<0 or y<0 or x>self.W or y>self.H:
            f['status']='escaped'; f['lifecycle']='TERMINAL'
            self.stats['pathway_escape_count']+=1; self.stats['pathway_escape_trace_count']+=len(f['ids'])
            return
        if p.get('atomic_structural'):
            return
        connection_ready=(len(f['ids'])<=4 or f['depth']>=1 or f['gestures']>=5)
        if f['gestures']>=2 and connection_ready and self._near_foreign_corridor(f):
            # Proximity is an opportunity, never a completed connection.  A wider
            # cohort may split into narrower children here; singleton fronts remain
            # active so _connect_singletons can construct an explicit terminal join.
            chance=self.profile['connection_appetite']*(.86 if f['intent']=='connect' else .38)
            if len(f['ids'])>1 and f['depth']<5 and f['rng'].random()<chance:
                if self._branch_front(f):
                    return
        if f['intent']=='explore' and f['target'] is not None:
            if math.hypot(x-f['target'][0],y-f['target'][1])<=1.8*self.module:
                f['target']=self._underused_target((x,y),f['rng'])
        if f['gestures']>=f['max_gestures']:
            if len(f['ids'])>1 and f['rng'].random()>=.03:
                # V21 makes bundled traces ~97% less willing to end by choice.  First try to peel the
                # cohort into narrower children; if the local geometry cannot support that fork,
                # simply extend its journey and let subsequent synchronous rounds reconsider it.
                self.stats['pathway_bundled_journey_deferral_count']+=1
                f['bundle_termination_deferrals']=f.get('bundle_termination_deferrals',0)+1
                branched=False
                if f['depth']<5 and f['local_gestures']>=1 and f['straight_since_turn']>=1:
                    branched=bool(self._branch_front(f))
                if not branched and f['status']=='active':
                    f['max_gestures']+=2+int(f['rng'].random()*3)
                    f['branch_retry_after_gesture']=min(f.get('branch_retry_after_gesture',f['gestures']),f['gestures'])
            else:
                self._terminate_front(f,'journey_limit')

    def _mod_delta_ok(self,a,b):
        return (b-a)%8 in (0,1,7)

    def _near_foreign_corridor(self,f):
        point=Point(f['path'][-1]); radius=2.15*self.module+self._front_half_width(f)
        for rec in self.path_index.query(expand_bounds(point.bounds,radius)):
            if rec['front']==f['id'] or rec['chip']==f['chip']:
                continue
            if point.distance(rec['geom'])<=2.15*self.module:
                return True
        return False

    def _octile_leg(self,start,target,current_dir):
        dx=target[0]-start[0]; dy=target[1]-start[1]
        if math.hypot(dx,dy)<1e-7:
            return [start]
        candidates=[]
        for d1 in range(8):
            v1=dir_vec(d1)
            for d2 in range(8):
                if d1==d2 or not self._mod_delta_ok(d1,d2):
                    continue
                v2=dir_vec(d2); det=v1[0]*v2[1]-v1[1]*v2[0]
                if abs(det)<1e-9:
                    continue
                a=(dx*v2[1]-dy*v2[0])/det
                b=(v1[0]*dy-v1[1]*dx)/det
                if a<-1e-7 or b<-1e-7:
                    continue
                seq=[]
                if a>1e-7: seq.append((d1,a))
                if b>1e-7: seq.append((d2,b))
                if not seq or not self._mod_delta_ok(current_dir,seq[0][0]):
                    continue
                if len(seq)>1 and not self._mod_delta_ok(seq[0][0],seq[1][0]):
                    continue
                candidates.append(seq)
        direct=nearest_dir_index(dx,dy)
        vx,vy=dir_vec(direct)
        cross=abs(dx*vy-dy*vx)
        dot=dx*vx+dy*vy
        if cross<1e-6 and dot>0 and self._mod_delta_ok(current_dir,direct):
            candidates.append([(direct,dot)])
        if not candidates:
            return None
        candidates.sort(key=lambda seq:(len(seq),sum(abs((d-current_dir)%8) for d,_ in seq)))
        pts=[start]
        for d,length in candidates[0]:
            pts.append(point_along_dir(pts[-1],d,length))
        pts[-1]=target
        return pts

    def _head_join_candidates(self,a,b,pa,pb):
        """Small ordered set of octilinear head-to-head rendezvous candidates.

        Prefer intersections of the heads' current/adjacent forward rays.  Those produce one
        substantial leg from each side and avoid the old midpoint solver's tiny corrective
        doglegs.  Only if no forward-ray rendezvous exists do we fall back to midpoint legs.
        """
        out=[]; seen=set(); min_leg=.12*self.module; max_leg=3.5*self.module
        dirs_a=(a['dir'],(a['dir']-1)%8,(a['dir']+1)%8)
        dirs_b=(b['dir'],(b['dir']-1)%8,(b['dir']+1)%8)
        dx=pb[0]-pa[0]; dy=pb[1]-pa[1]
        for da in dirs_a:
            va=dir_vec(da)
            for db in dirs_b:
                vb=dir_vec(db)
                # pa + ta*va == pb + tb*vb
                det=va[0]*(-vb[1])-va[1]*(-vb[0])
                if abs(det)<1e-9: continue
                ta=(dx*(-vb[1])-dy*(-vb[0]))/det
                tb=(va[0]*dy-va[1]*dx)/det
                if ta<min_leg or tb<min_leg or ta>max_leg or tb>max_leg: continue
                meet=point_along_dir(pa,da,ta)
                if math.hypot(meet[0]-(pb[0]+vb[0]*tb),meet[1]-(pb[1]+vb[1]*tb))>1e-5: continue
                key=(round(meet[0],4),round(meet[1],4),da,db)
                if key in seen: continue
                seen.add(key); out.append((ta+tb,meet,[pa,meet],[pb,meet]))
        mid=((pa[0]+pb[0])/2,(pa[1]+pb[1])/2)
        la=self._octile_leg(pa,mid,a['dir']); lb=self._octile_leg(pb,mid,b['dir'])
        if la is not None and lb is not None:
            total=sum(math.hypot(y[0]-x[0],y[1]-x[1]) for x,y in zip(la,la[1:]))+sum(math.hypot(y[0]-x[0],y[1]-x[1]) for x,y in zip(lb,lb[1:]))
            out.append((total,mid,la,lb))
        out.sort(key=lambda x:(x[0],len(x[2])+len(x[3])))
        return out

    def _head_junction_clear(self,a,b,meet):
        """A head-to-head junction may not land on any third routed corridor."""
        radius=max(3.5*self.U,.55*(self._front_half_width(a)+self._front_half_width(b)))
        disk=Point(meet).buffer(radius,quad_segs=8)
        allowed_fronts={a['id'],b['id']}|self._ancestor_front_ids(a)|self._ancestor_front_ids(b)
        for rec in self.path_index.query(expand_bounds(disk.bounds,self.r.pathway_interroute_keepout)):
            if rec['front'] in allowed_fronts:
                continue
            if disk.intersects(rec['geom']) or disk.distance(rec['geom'])<self.r.pathway_interroute_keepout:
                return False
        return True

    def _special_leg_clear(self,f,pts,meeting=None,extra=()):
        if not pts or len(pts)<2:
            return False
        created=[]
        last=len(pts)-2
        for index,(a,b) in enumerate(zip(pts,pts[1:])):
            geom=self._corridor_geom(f,a,b)
            check_geom=geom
            if meeting is not None and index==last:
                # The two terminal strokes are allowed to share only this compact
                # physical junction envelope.  Everything before it still receives
                # the ordinary corridor collision test.
                check_geom=geom.difference(Point(meeting).buffer(6.0*self.U,quad_segs=8))
            if not self._gesture_clear(f,a,b,check_geom,allow_outside=False,extra_segments=tuple(extra)+tuple(created)):
                return False
            created.append(geom)
        return True

    def _connect_singletons_to_lanes(self):
        """V20 intentionally disables mid-segment trace attachment.

        Trace-to-trace connectivity is head-to-head only.  Keeping this method as an explicit
        no-op avoids accidental reintroduction by older call sites while making the invariant
        visible in the source and report.
        """
        return

    def _detach_trace_as_singleton(self,f,tid):
        """Peel one physical lane out of an active cohort at its current head.

        This is used only for a close head-to-head connection opportunity.  The lane keeps its
        complete materialized prefix; no middle-of-line junction is created.
        """
        if f['status']!='active' or tid not in f['ids']:
            return None
        if len(f['ids'])==1:
            return f
        ordered=sorted(f['ids'],key=lambda x:f['offsets'][x])
        if tid not in (ordered[0],ordered[-1]):
            # Never punch a hole through a live cohort merely to gain a connection.
            # Interior lanes must become exposed by a real contiguous branch first.
            return None
        realised=self._materialized_paths(f)
        endpoint=realised[tid][-1]
        child=self._make_front(ids=[tid],chip=f['chip'],side=f['side'],side_index=f['side_index'],
                               path=[endpoint],direction=f['dir'],offsets={tid:0.0},
                               thicknesses={tid:f['thicknesses'][tid]},
                               prefixes={tid:realised[tid]},rng=SplitMix64(f['rng'].next_u64()),
                               depth=min(5,f['depth']+1),intent=f['intent'],target=f['target'],parent=f['id'])
        child['gestures']=f['gestures']; child['local_gestures']=f['local_gestures']; child['travel']=f['travel']
        child['max_gestures']=max(f['max_gestures'],child['max_gestures'])
        child['base_max_gestures']=f.get('base_max_gestures',child['base_max_gestures'])
        child['last_turn_sign']=f['last_turn_sign']; child['straight_since_turn']=f['straight_since_turn']
        child['origin']=f['origin']; child['initial_dir']=f.get('initial_dir',f['dir'])
        child['max_origin_distance']=f.get('max_origin_distance',0.0)
        child['turn_history']=list(f.get('turn_history',[]))
        child['recovery_floor_segments']=max(1,len(child['path'])-1)
        child['detached_from']=f['id']
        # The detached lane permanently owns the parent's complete route up to this head.
        # Lock that shared prefix before the remaining cohort can traceback; otherwise the
        # spatial index could forget geometry that the connected child still visibly renders.
        f['recovery_floor_segments']=max(int(f.get('recovery_floor_segments',1)),len(f['path'])-1)
        self.stats['pathway_detached_prefix_lock_count']+=1
        f['ids'].remove(tid)
        f['offsets'].pop(tid,None); f['thicknesses'].pop(tid,None); f['prefixes'].pop(tid,None)
        if not f['ids']:
            f['status']='branched'
        self.stats['pathway_close_head_lane_detach_count']+=1
        return child

    def _current_trace_lane_records(self):
        """Materialize each currently-owned trace once for precise terminal-join checks."""
        records=[]; seen=set()
        for f in self.fronts.values():
            if f['status']=='branched':
                continue
            paths=self._materialized_paths(f)
            for tid,pts in paths.items():
                if tid in seen or len(pts)<2:
                    continue
                seen.add(tid)
                line=LineString(pts); t=f['thicknesses'][tid]
                geom=line.buffer(t/2,cap_style='flat',join_style='mitre',quad_segs=6)
                records.append(dict(tid=tid,line=line,geom=geom,thickness=t))
        return records

    def _connection_joint_radius(self,ta_t,tb_t):
        """Visible exemption radius for a legal head-to-head junction."""
        return max(8.0*self.U,.75*(float(ta_t)+float(tb_t)))

    def _precise_head_join_clear(self,a,b,ta,tb,lega,legb,meet):
        """Exact lane-level guard for a proposed head-to-head connection.

        Coarse bundle corridors remain the fast planner obstacle.  Before a connection is
        committed, this guard checks the actual two terminal trace strokes against every
        currently owned lane, eliminating the rare connection-induced crossing that a padded
        cohort envelope can miss.
        """
        la=LineString(lega); lb=LineString(legb)
        if not la.is_simple or not lb.is_simple:
            return False
        ta_t=a['thicknesses'][ta]; tb_t=b['thicknesses'][tb]
        ga=la.buffer(ta_t/2,cap_style='flat',join_style='mitre',quad_segs=6)
        gb=lb.buffer(tb_t/2,cap_style='flat',join_style='mitre',quad_segs=6)
        inter=la.intersection(lb)
        if not inter.is_empty:
            pts=[inter] if inter.geom_type=='Point' else ([g for g in inter.geoms if g.geom_type=='Point'] if hasattr(inter,'geoms') else [])
            if not pts or any(math.hypot(q.x-meet[0],q.y-meet[1])>1.5*self.U for q in pts):
                return False
        joint=Point(meet).buffer(self._connection_joint_radius(ta_t,tb_t),quad_segs=8)
        if not ga.intersection(gb).difference(joint).is_empty:
            return False
        for rec in self._current_trace_lane_records():
            if rec['tid'] in (ta,tb):
                continue
            # A visible trace stroke may neither be crossed nor merely run into by a terminal leg.
            if not ga.intersection(rec['geom']).is_empty or not gb.intersection(rec['geom']).is_empty:
                return False
        return True

    def _points_have_compensating_zigzag(self,pts):
        """Return True for the forbidden short/repeated A→B→A weave in any candidate path."""
        if len(pts)<4:
            return False
        ls=[math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:])]
        dirs=self._turn_directions(pts)
        for j,(a,b,c) in enumerate(zip(dirs,dirs[1:],dirs[2:])):
            middle=ls[j+1] if j+1<len(ls) else 0.0
            repeated=(j+3<len(dirs) and dirs[j+3]==b)
            if a==c and a!=b and (middle<2*self.module or repeated):
                return True
        return False

    def _connection_leg_creates_compensating_zigzag(self,f,tid,leg):
        """Reject a terminal join that would reintroduce the old short/repeated weave."""
        paths=self._materialized_paths(f)
        base=list(paths.get(tid,()))
        if len(base)<2 or len(leg)<2:
            return False
        return self._points_have_compensating_zigzag(base+list(leg[1:]))

    def _temp_singleton_for_head(self,f,tid,endpoint,synthetic_id):
        t=dict(f)
        t['id']=synthetic_id; t['ids']=[tid]; t['path']=[endpoint]
        t['offsets']={tid:0.0}; t['thicknesses']={tid:f['thicknesses'][tid]}
        t['prefixes']={tid:[]}; t['parent']=f['id']; t['branch_parent']=f['id']
        t['branch_stage']=None; t['branch_turn']=None
        return t

    def _connect_forced_close_lane_heads(self, include_terminated=False):
        """Deterministically connect very close *free lane heads*, even inside bundles.

        The parent cohort is mutated only after both terminal legs pass the complete collision
        test.  Failed opportunities therefore do not fragment the bundle or change its route.
        """
        heads=[]
        eligible_status={'active','terminated'} if include_terminated else {'active'}
        for f in sorted((x for x in self.fronts.values() if x['status'] in eligible_status and x['gestures']>=1),key=lambda x:x['id']):
            # Topology changes are transactional. A lane cannot be peeled away while its
            # parent fan/branch structure is still incomplete.
            if f.get('fan_pending') or f.get('branch_stage') is not None:
                continue
            paths=self._materialized_paths(f)
            for tid,pts in paths.items():
                if tid in self.connected_trace_ids or not pts:
                    continue
                heads.append((f,tid,pts[-1]))
        pairs=[]; base_radius=2.75*self.module
        for i,(a,ta,pa) in enumerate(heads):
            for b,tb,pb in heads[i+1:]:
                d=math.hypot(pb[0]-pa[0],pb[1]-pa[1])
                radius=base_radius
                if a['chip']!=b['chip']:
                    ux=(pb[0]-pa[0])/max(d,1e-9); uy=(pb[1]-pa[1])/max(d,1e-9)
                    va=dir_vec(a['dir']); vb=dir_vec(b['dir'])
                    facing=(va[0]*ux+va[1]*uy>.18 and vb[0]*(-ux)+vb[1]*(-uy)>.18)
                    if (facing and
                            (a.get('travel',0.0)<4.0*self.module or b.get('travel',0.0)<4.0*self.module or
                             self._refresh_lifecycle(a) in ('LAUNCHING','RECOVERING') or
                             self._refresh_lifecycle(b) in ('LAUNCHING','RECOVERING'))):
                        radius=5.0*self.module
                if a['chip']==b['chip']:
                    # Same-chip routing normally does not self-connect.  The sole exception is
                    # final terminal arbitration: if two free terminal heads would physically
                    # overlap their enlarged endpoint markers, a clean head-to-head join is
                    # preferable to two colliding dots.
                    if not include_terminated or a.get('status')!='terminated' or b.get('status')!='terminated':
                        continue
                    ra=self.r._termination_dot_radius(a['thicknesses'][ta])+.5*self.r.termination_dot_hollow_stroke
                    rb=self.r._termination_dot_radius(b['thicknesses'][tb])+.5*self.r.termination_dot_hollow_stroke
                    if d>ra+rb+self.r.termination_dot_min_gap:
                        continue
                if d<=radius:
                    pairs.append((d,a['id'],ta,b['id'],tb,a,b,pa,pb))
        pairs.sort(key=lambda x:(x[0],x[1],x[2],x[3],x[4]))
        used=set()
        for _,_,ta,_,tb,a,b,pa,pb in pairs:
            if ta in used or tb in used or ta in self.connected_trace_ids or tb in self.connected_trace_ids:
                continue
            if a['status'] not in eligible_status or b['status'] not in eligible_status or ta not in a['ids'] or tb not in b['ids']:
                continue
            aa=self._temp_singleton_for_head(a,ta,pa,-1000000-ta)
            bb=self._temp_singleton_for_head(b,tb,pb,-2000000-tb)
            solved=None
            for _cost,meet,lega,legb in self._head_join_candidates(a,b,pa,pb):
                if not self._head_junction_clear(aa,bb,meet): continue
                if (any(math.hypot(y[0]-x[0],y[1]-x[1])<.10*self.module for x,y in zip(lega,lega[1:])) or
                        any(math.hypot(y[0]-x[0],y[1]-x[1])<.10*self.module for x,y in zip(legb,legb[1:]))): continue
                geoma=[self._corridor_geom(aa,x,y) for x,y in zip(lega,lega[1:])]
                if not self._special_leg_clear(aa,lega,meeting=meet): continue
                if not self._special_leg_clear(bb,legb,meeting=meet,extra=geoma): continue
                if (self._connection_leg_creates_compensating_zigzag(a,ta,lega) or
                        self._connection_leg_creates_compensating_zigzag(b,tb,legb)): continue
                if not self._precise_head_join_clear(aa,bb,ta,tb,lega,legb,meet): continue
                solved=(meet,lega,legb); break
            if solved is None: continue
            meet,lega,legb=solved
            # Terminal arbitration happens before endpoint markers are materialised.  A
            # terminated cohort may therefore donate one free head to an obvious legal join;
            # any unpeeled residue keeps its original terminal state.
            prior_a=(a['status'],a.get('termination_reason')); prior_b=(b['status'],b.get('termination_reason'))
            if include_terminated and a['status']=='terminated': a['status']='active'
            if include_terminated and b['status']=='terminated': b['status']='active'
            ra=self._detach_trace_as_singleton(a,ta); rb=self._detach_trace_as_singleton(b,tb)
            if ra is None or rb is None:
                if a['status']=='active' and prior_a[0]=='terminated': a['status']='terminated'; a['termination_reason']=prior_a[1]
                if b['status']=='active' and prior_b[0]=='terminated': b['status']='terminated'; b['termination_reason']=prior_b[1]
                continue
            if ra is not a and a.get('ids') and prior_a[0]=='terminated': a['status']='terminated'; a['termination_reason']=prior_a[1]
            if rb is not b and b.get('ids') and prior_b[0]=='terminated': b['status']='terminated'; b['termination_reason']=prior_b[1]
            for f,leg in ((ra,lega),(rb,legb)):
                for x,y in zip(leg,leg[1:]):
                    geom=self._corridor_geom(f,x,y)
                    f['path'].append(y); length=math.hypot(y[0]-x[0],y[1]-x[1]); f['travel']+=length
                    if length<self.module-.01*self.U:
                        self.stats['pathway_minimum_segment_exception_count']+=1
                    self._record_segment(f,x,y,geom,normal=False)
                f['status']='connected'; f['lifecycle']='TERMINAL'
            self.connection_pairs[tuple(sorted((ta,tb)))]=meet
            self.connected_trace_ids.update((ta,tb))
            self.cross_chip_connected_trace_ids.update((ta,tb))
            self.stats['pathway_cross_chip_connection_count']+=1
            self.stats['pathway_cross_chip_connected_trace_count']=len(self.cross_chip_connected_trace_ids)
            self.stats['pathway_forced_close_head_connection_count']+=1
            used.update((ta,tb))

    def _connect_singletons(self):
        # Head-to-head only. Close lane heads are first peeled out of broader cohorts so they
        # are not ignored merely because sibling lanes are still travelling together.
        self._connect_forced_close_lane_heads()
        singles=[f for f in self.fronts.values()
                 if f['status']=='active' and len(f['ids'])==1 and f['gestures']>=1 and
                 f['ids'][0] not in self.connected_trace_ids]
        pairs=[]
        for i,a in enumerate(singles):
            for b in singles[i+1:]:
                if a['chip']==b['chip']:
                    continue
                ta,tb=a['ids'][0],b['ids'][0]
                if ta in self.connected_trace_ids or tb in self.connected_trace_ids:
                    continue
                pa,pb=a['path'][-1],b['path'][-1]
                d=math.hypot(pb[0]-pa[0],pb[1]-pa[1])
                if d>10.0*self.module:
                    continue
                desire=(a['intent']=='connect')+(b['intent']=='connect')
                paired=(a.get('round_connection_peer')==b['id'] and b.get('round_connection_peer')==a['id'])
                forced_close=d<=2.35*self.module
                chance=1.0 if forced_close else ((.90 if paired else (.24+.28*desire))*self.profile['connection_appetite'])
                priority=d/self.module-(3.2 if forced_close else 0.0)-(2.4 if paired else 0.0)-a['rng'].random()*.20-b['rng'].random()*.20
                pairs.append((priority,chance,forced_close,a,b))
        pairs.sort(key=lambda x:(x[0],x[3]['id'],x[4]['id']))
        used=set()
        for _,chance,forced_close,a,b in pairs:
            if a['id'] in used or b['id'] in used or a['status']!='active' or b['status']!='active':
                continue
            ta,tb=a['ids'][0],b['ids'][0]
            if ta in self.connected_trace_ids or tb in self.connected_trace_ids:
                continue
            if not forced_close and a['rng'].random()>=min(.995,chance):
                continue
            pa,pb=a['path'][-1],b['path'][-1]
            min_leg=.10*self.module if forced_close else .45*self.module
            solved=None
            for _cost,meet,lega,legb in self._head_join_candidates(a,b,pa,pb):
                if not self._head_junction_clear(a,b,meet): continue
                if (any(math.hypot(y[0]-x[0],y[1]-x[1])<min_leg for x,y in zip(lega,lega[1:])) or
                        any(math.hypot(y[0]-x[0],y[1]-x[1])<min_leg for x,y in zip(legb,legb[1:]))): continue
                geoma=[self._corridor_geom(a,x,y) for x,y in zip(lega,lega[1:])]
                if not self._special_leg_clear(a,lega,meeting=meet): continue
                if not self._special_leg_clear(b,legb,meeting=meet,extra=geoma): continue
                if (self._connection_leg_creates_compensating_zigzag(a,ta,lega) or
                        self._connection_leg_creates_compensating_zigzag(b,tb,legb)): continue
                if not self._precise_head_join_clear(a,b,ta,tb,lega,legb,meet): continue
                solved=(meet,lega,legb); break
            if solved is None: continue
            meet,lega,legb=solved
            for f,leg in ((a,lega),(b,legb)):
                for x,y in zip(leg,leg[1:]):
                    geom=self._corridor_geom(f,x,y)
                    f['path'].append(y); f['travel']+=math.hypot(y[0]-x[0],y[1]-x[1])
                    if math.hypot(y[0]-x[0],y[1]-x[1])<self.module-.01*self.U:
                        self.stats['pathway_minimum_segment_exception_count']+=1
                    self._record_segment(f,x,y,geom,normal=False)
                f['status']='connected'; f['lifecycle']='TERMINAL'
            self.connection_pairs[tuple(sorted((ta,tb)))]=meet
            self.connected_trace_ids.update((ta,tb))
            self.cross_chip_connected_trace_ids.update((ta,tb))
            self.stats['pathway_cross_chip_connection_count']+=1
            self.stats['pathway_cross_chip_connected_trace_count']=len(self.cross_chip_connected_trace_ids)
            if forced_close:
                self.stats['pathway_forced_close_head_connection_count']+=1
            used.update((a['id'],b['id']))

    def _fragment_bundled_front(self,f):
        """Recovery-only fragmentation into independently routable lanes.

        V21 lets a persistently trapped bundle peel into true singleton fronts because narrow
        lanes escape congestion much more reliably than 2-3 lane mini-bundles.  The important
        change is an isolation lock: these children may not immediately terminate while they
        still visually occupy the parent bus.  They must first travel/separate, or keep
        rerouting.
        """
        if f['status']!='active' or len(f['ids'])<=1:
            return False
        if self._source_egress_pending(f):
            return False
        realised=self._materialized_paths(f)
        children=[]
        fragment_group=f['id']
        for idx,tid in enumerate(sorted(f['ids'],key=lambda i:f['offsets'][i])):
            endpoint=realised[tid][-1]
            if idx==0:
                intent,target=f['intent'],f['target']
            else:
                intent,target=self._sample_intent(f['rng'],endpoint,f['dir'])
            child=self._make_front(ids=[tid],chip=f['chip'],side=f['side'],side_index=f['side_index'],
                                   path=[endpoint],direction=f['dir'],offsets={tid:0.0},
                                   thicknesses={tid:f['thicknesses'][tid]},
                                   prefixes={tid:realised[tid]},rng=SplitMix64(f['rng'].next_u64()),
                                   depth=min(5,f['depth']+1),intent=intent,target=target,parent=f['id'])
            child['gestures']=f['gestures']; child['travel']=f['travel']
            child['max_gestures']=max(f['max_gestures']+3,child['max_gestures'])
            child['last_turn_sign']=f['last_turn_sign']; child['straight_since_turn']=max(1,f['straight_since_turn'])
            child['origin']=f['origin']; child['initial_dir']=f.get('initial_dir',f['dir'])
            child['max_origin_distance']=f.get('max_origin_distance',0.0)
            child['turn_history']=list(f.get('turn_history',[]))
            child['reroute_mode_rounds']=2
            child['reroute_avoid_dir']=f.get('reroute_avoid_dir',f['dir'])
            child['fragment_group']=fragment_group
            child['fragment_origin']=endpoint
            child['fragment_min_local_gestures']=2
            child['recovery_fragment_child']=True
            if f.get('local_gap'):
                child['local_gap']=True; child['local_gap_special']=bool(f.get('local_gap_special'))
                child['local_gap_branch_boost']=f.get('local_gap_branch_boost',4.0)
                child['local_gap_exit_allowed']=f.get('local_gap_exit_allowed',False)
            children.append(child)
        # Transactional young recovery: individual viability is not enough. The exact
        # deterministic first proposal each newborn child would make must be mutually
        # compatible before the topology change exists. Otherwise the parent remains intact
        # and is rerouted; no child is born merely to lose same-round arbitration.
        if f.get('travel',0.0)<3.0*self.module and len(children)<=4:
            first=[]; viable=True
            for child in children:
                probe=dict(child); probe['rng']=SplitMix64(child['rng'].state); probe['gestures']=0
                q=self._propose(probe)
                if q is None: viable=False; break
                first.append(q)
            if viable:
                viable=not any(self._proposal_pair_conflicts(a,b) for i,a in enumerate(first) for b in first[i+1:])
            if not viable:
                for child in children: self.fronts.pop(child['id'],None)
                self.stats['pathway_transactional_birth_reject_count']+=1
                return False
        f['status']='branched'
        self.stats['pathway_split_count']+=1
        if f.get('local_gap'): self.stats['pathway_local_gap_split_count']+=1
        self.stats['pathway_recovery_fragment_count']+=1
        return bool(children)

    def _fragment_singleton_still_embedded(self,f):
        group=f.get('fragment_group')
        if group is None or len(f.get('ids',()))!=1:
            return False
        if f.get('local_gestures',0) < f.get('fragment_min_local_gestures',2):
            return True
        p=self._materialized_paths(f)[f['ids'][0]][-1]
        for other in self.fronts.values():
            if other['id']==f['id'] or other.get('status')!='active' or other.get('fragment_group')!=group:
                continue
            op=self._materialized_paths(other)[other['ids'][0]][-1]
            if math.hypot(op[0]-p[0],op[1]-p[1]) < 1.35*self.module:
                return True
        return False

    def _defer_bundled_hard_stop(self,f,round_index):
        """Suppress about 97% of forced terminations while a front is still bundled.

        The ordinary repair system has already spent its seven-attempt budget by the time this
        is called.  Rather than looping through more copies of the same search, the preferred
        outcome is productive fragmentation into independent lanes.
        """
        if len(f['ids'])<=1:
            return False
        if self._source_egress_pending(f):
            # Source egress is indivisible.  Refresh a small bounded recovery budget but never
            # solve an emergence problem by exploding the untouched bus into child lanes.
            f['max_gestures']=max(f['max_gestures'],f['gestures']+3)
            f['reroute_attempts']=min(f.get('reroute_attempts',0),max(0,self.profile['reroute_budget']-2))
            f['quality_repair_pending']=True; f['quality_repair_reason']='source_egress_persistence'
            self.stats['pathway_bundled_hard_stop_deferral_count']+=1
            return True
        # A young bundle should not explode directly into singleton recovery lanes.  First
        # ask the existing transactional brancher whether contiguous narrower children have
        # viable futures.  Only mature/unsplittable cohorts fall through to lane fragmentation.
        if f.get('travel',0.0)<4.0*self.module and f.get('depth',0)<5 and f.get('branch_stage') is None:
            old_retry=f.get('branch_retry_after_gesture',0)
            f['branch_retry_after_gesture']=min(old_retry,f.get('gestures',0))
            children=self._branch_front(f)
            if children:
                self.stats.setdefault('pathway_young_recovery_branch_count',0)
                self.stats['pathway_young_recovery_branch_count']+=1
                return True
            f['branch_retry_after_gesture']=old_retry
        if f['rng'].random()<.03:
            return False
        hard_rounds=self.profile['max_rounds']+self.profile.get('persistence_tail_rounds',0)
        # Do not create fresh singleton recovery children in the final few rounds; they would
        # have no fair chance to separate and would merely disappear from materialisation.
        if round_index>=hard_rounds-4:
            return False
        self.stats['pathway_bundled_hard_stop_deferral_count']+=1
        f['bundle_termination_deferrals']=f.get('bundle_termination_deferrals',0)+1
        # The bundle is boxed at its present head.  Fragmenting exactly there would create
        # singleton children in the same dead pocket, so first rewind the parent to an earlier
        # accepted corridor position and let the narrower children choose new routes from there.
        # Existing connection locks/recovery floors still cap how far this rollback may go.
        if len(f.get('path',()))>2:
            self._traceback_for_reroute(f)
        # Topology changes are committed only at a round boundary. Creating children here,
        # after the synchronous proposal snapshot already exists, lets old proposals steal
        # their escape corridor before the children get a vote.
        f['fragment_pending']=True
        return True

    def _singleton_between_live_siblings(self,f):
        """Return True when a singleton still visually sits between continuing same-root lanes.

        This is intentionally geometric rather than purely genealogical: after several forks a
        front may be logically independent while still looking like the middle member of a bus.
        A terminal dot in that situation is the artifact V21 forbids.
        """
        if len(f.get('ids',()))!=1 or f.get('status')!='active':
            return False
        realised=self._materialized_paths(f)
        tid=f['ids'][0]
        if tid not in realised or not realised[tid]:
            return False
        p=realised[tid][-1]
        vx,vy=dir_vec(f['dir']); nx,ny=-vy,vx
        neg=False; pos=False
        lateral_limit=3.25*self.module
        longitudinal_limit=2.35*self.module
        for other in self.fronts.values():
            if other['id']==f['id'] or other.get('status') in ('branched','abandoned_short','terminated'):
                continue
            if (other.get('chip'),other.get('side_index'),other.get('side')) != (f.get('chip'),f.get('side_index'),f.get('side')):
                continue
            opaths=self._materialized_paths(other)
            for otid in other.get('ids',()):
                if otid not in opaths or not opaths[otid]:
                    continue
                opts=opaths[otid]
                if len(opts)<2:
                    continue
                oline=LineString(opts)
                qg=oline.interpolate(oline.project(Point(p)))
                q=(qg.x,qg.y)
                dx=q[0]-p[0]; dy=q[1]-p[1]
                lateral=dx*nx+dy*ny
                if abs(lateral)>lateral_limit:
                    continue
                if other.get('status')=='active':
                    # A live sibling counts if its present head is still roughly abreast.
                    head=opts[-1]
                    hforward=(head[0]-p[0])*vx+(head[1]-p[1])*vy
                    if abs(hforward)>longitudinal_limit:
                        continue
                else:
                    # A sibling that already progressed/escaped/connected still visually
                    # continues past this proposed stop, so it must count as a surrounding lane.
                    max_forward=max((x-p[0])*vx+(y-p[1])*vy for x,y in opts)
                    if max_forward<.65*self.module:
                        continue
                if lateral < -0.40*self.U: neg=True
                elif lateral > 0.40*self.U: pos=True
                if neg and pos:
                    return True
        return False

    def _backoff_terminal_points(self,f,tid,points,marker_index=None):
        """Move a free terminal head backward to maximize safe visual clearance.

        This is a render-time trim, not a reroute.  First preference is full marker + foreign
        pathway clearance. If that is impossible along the legal visible tail, choose the
        marker-safe position with the greatest foreign-path clearance so hard marker overlap is
        still avoided without reopening routing.
        """
        if f.get('status')!='terminated' or len(points)<2:
            return list(points),0.0
        t=f['thicknesses'][tid]
        outer=self.r._termination_dot_radius(t)+.5*self.r.termination_dot_hollow_stroke+self.r.pathway_terminal_head_keepout
        ancestors=self._ancestor_front_ids(f)
        total=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(points,points[1:]))
        # Reserve the worst-case hollow-marker clipping distance as well as the visible 2.75-module
        # minimum, so render-time clearance trimming can never turn a recovered main route into
        # a tiny trace that is later suppressed.
        marker_clip=self.r._termination_dot_radius(t)+.5*self.r.termination_dot_hollow_stroke
        # V33: render-time terminal clearance is cosmetic only.  It may never visually
        # amputate a mature main-chip route back below the protected launch-survival floor.
        visible_floor=(self.main_launch_maturity_modules if not f.get('local_gap') else 2.75)*self.module
        max_back=max(0.0,total-(visible_floor+marker_clip))
        # Search the whole legal excess tail in bounded increments; no route search is involved.
        n=max(1,min(14,int(math.ceil(max_back/max(.14*self.module,1e-9)))))
        steps=[0.0]+[(k/n)*max_back for k in range(1,n+1)] if max_back>1e-9 else [0.0]
        best_marker_safe=None
        for back in steps:
            cand=self._clip_polyline_end(points,back) if back>1e-9 else list(points)
            if len(cand)<2: continue
            if math.hypot(cand[-1][0]-cand[-2][0],cand[-1][1]-cand[-2][1]) < .10*self.module-1e-9:
                continue
            disc=Point(cand[-1]).buffer(outer,quad_segs=8)
            marker_bad=False
            if marker_index is not None:
                for old in marker_index.query(expand_bounds(disc.bounds,self.r.termination_dot_min_gap)):
                    if disc.intersects(old['geom']) or disc.distance(old['geom'])<self.r.termination_dot_min_gap:
                        marker_bad=True; break
            if marker_bad:
                continue
            min_path_clear=float('inf'); path_bad=False
            for rec in self.path_index.query(expand_bounds(disc.bounds,self.r.pathway_terminal_head_keepout)):
                if rec['front']==f['id'] or rec['front'] in ancestors:
                    continue
                d=disc.distance(rec['geom'])
                min_path_clear=min(min_path_clear,d)
                if disc.intersects(rec['geom']):
                    path_bad=True
            if not path_bad:
                return cand,back
            score=(min_path_clear if math.isfinite(min_path_clear) else 0.0, back)
            if best_marker_safe is None or score>best_marker_safe[0]:
                best_marker_safe=(score,cand,back)
        if best_marker_safe is not None:
            return best_marker_safe[1],best_marker_safe[2]
        return list(points),0.0

    def _terminate_front(self,f,reason='hard_stop_exhausted'):
        if f['status']!='active':
            return
        if self._fragment_singleton_still_embedded(f):
            self.stats['pathway_bundle_middle_termination_deferral_count']+=1
            f['max_gestures']=max(f['max_gestures'],f['gestures']+3)
            f['failures']=0
            if f.get('reroute_attempts',0)>=self.profile['reroute_budget']:
                f['reroute_attempts']=max(0,self.profile['reroute_budget']-2)
            f['quality_repair_pending']=True
            f['quality_repair_reason']='bundle_middle_persistence'
            return
        if self._singleton_between_live_siblings(f):
            # A middle lane may not terminate while sibling lanes on both sides continue.
            # Give it fresh repair room and a little more journey budget instead.
            self.stats['pathway_bundle_middle_termination_deferral_count']+=1
            f['max_gestures']=max(f['max_gestures'],f['gestures']+3)
            f['failures']=0
            f['reroute_attempts']=min(f.get('reroute_attempts',0),max(0,self.profile['reroute_budget']-4))
            f['intent']='exit'
            f['target']=self._distant_exit_target(f['path'][-1],f['rng'])
            f['quality_repair_pending']=True
            f['quality_repair_reason']='bundle_middle_persistence'
            return
        min_lane=self._minimum_materialized_lane_length(f)
        # V34: if a main front is about to die while a genuinely open local corridor still
        # exists, termination is not legal yet. Rewind/replan once or twice instead of turning
        # available space into a dead stub. This is bounded and local, not global search.
        if (not f.get('local_gap') and reason in ('hard_stop_exhausted','journey_limit','round_limit') and
                f.get('space_replan_deferrals',0)<2):
            head=f['path'][-1]
            cap=max(self._local_space_capacity(f,head,d) for d in (f['dir'],(f['dir']-1)%8,(f['dir']+1)%8))
            if cap>=1.35:
                f['space_replan_deferrals']=f.get('space_replan_deferrals',0)+1
                self.stats['pathway_space_available_replan_count']=self.stats.get('pathway_space_available_replan_count',0)+len(f.get('ids',()))
                f['failures']=0
                f['reroute_attempts']=min(f.get('reroute_attempts',0),max(0,self.profile['reroute_budget']-3))
                f['quality_repair_pending']=True; f['quality_repair_reason']='space_available_replan'; f['lifecycle']='RECOVERING'
                f['max_gestures']=max(f['max_gestures'],f['gestures']+3)
                return
        # After the hard four-module egress is clear, give a still-short main route exactly one
        # cheap persistence opportunity toward six modules.  This is a soft visual preference,
        # not a reason to reject or repeatedly reroute an otherwise valid board.
        if (not f.get('local_gap') and
                self.main_launch_maturity_modules*self.module-1e-7 <= min_lane < self.main_launch_preferred_terminal_modules*self.module and
                not f.get('post_egress_extension_attempted')):
            f['post_egress_extension_attempted']=True
            f['max_gestures']=max(f['max_gestures'],f['gestures']+2)
            f['failures']=0
            if not f.get('reroute_pending'):
                f['quality_repair_pending']=True; f['quality_repair_reason']='post_egress_persistence'
            return
        # V33 hard launch-survival contract.  A main-chip lane below the four-module protected egress
        # modules is not a legal terminal.  Ordinary reroute budgets cannot turn it into a
        # short corpse; it remains a protected recovery obligation.
        if not f.get('local_gap') and min_lane<self.main_launch_maturity_modules*self.module-1e-7:
            if f.get('young_defer_count',0)<4:
                f['young_defer_count']=f.get('young_defer_count',0)+1
                f['max_gestures']=max(f['max_gestures'],f['gestures']+3); f['failures']=0
                f['reroute_attempts']=min(f.get('reroute_attempts',0),max(0,self.profile['reroute_budget']-2))
                f['quality_repair_pending']=True; f['quality_repair_reason']='protected_launch_persistence'; f['lifecycle']='RECOVERING'
                return
            f['protected_launch_unresolved']=True
            return
        # Local fillers and already-mature main routes retain the ordinary tiny-stub rule.
        if min_lane<2.75*self.module and f.get('young_defer_count',0)<2:
            f['young_defer_count']=f.get('young_defer_count',0)+1
            f['max_gestures']=max(f['max_gestures'],f['gestures']+3); f['failures']=0
            f['reroute_attempts']=min(f.get('reroute_attempts',0),max(0,self.profile['reroute_budget']-2))
            f['quality_repair_pending']=True; f['quality_repair_reason']='young_persistence'; f['lifecycle']='RECOVERING'
            return
        if min_lane<2.75*self.module:
            f['status']='abandoned_short'; f['termination_reason']=reason; f['lifecycle']='TERMINAL'
            return
        f['status']='terminated'; f['termination_reason']=reason

    def _minimum_materialized_lane_length(self,f):
        """Shortest physical lane length currently owned by a front.

        Bundle centerline travel can overstate the inside lane after turns. Terminal survival
        decisions use the actually materialized lanes so an inner lane is never silently nipped
        just because the bundle centre barely cleared the minimum.
        """
        paths=self._materialized_paths(f)
        vals=[]
        for tid in f.get('ids',()):
            pts=paths.get(tid,())
            if len(pts)>=2:
                vals.append(sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:])))
        return min(vals) if vals else 0.0

    def _try_young_survival_beam(self,f,target_modules=3.6,horizon=3,beam_width=8):
        """Bounded last-chance continuation for a main route that is still too young to die.

        Unlike the escape beam this does not search for the frame. It only finds a few legal
        ordinary-sized gestures that carry an unresolved launch beyond the tiny-stub zone.
        It runs solely at the global horizon on the handful of surviving young main fronts.
        """
        current_lane=self._minimum_materialized_lane_length(f)
        if f.get('status')!='active' or f.get('local_gap') or current_lane>=target_modules*self.module:
            return False
        base=list(f['path']); start=base[-1]
        states=[(0.0,start,f['dir'],[],[])]
        solution=None
        for _depth in range(horizon):
            nxt=[]
            for score,pt,d0,props,geoms in states:
                tf=dict(f); tf['path']=base+[q['end'] for q in props]; tf['dir']=d0
                tf['gestures']=max(1,f.get('gestures',0)+len(props)); tf['local_gestures']=f.get('local_gestures',0)+len(props)
                for d in (d0,(d0-1)%8,(d0+1)%8):
                    if props and not self._mod_delta_ok(d0,d):
                        continue
                    for modules in (1,2,3):
                        end=point_along_dir(pt,d,modules*self.module)
                        pts=base+[q['end'] for q in props]+[end]
                        if self._points_have_compensating_zigzag(pts):
                            continue
                        if self._candidate_loop_risk(tf,d,end):
                            continue
                        geom=self._corridor_geom(tf,pt,end)
                        self.stats['pathway_lookahead_evaluation_count']+=1
                        if not self._gesture_clear(tf,pt,end,geom,allow_outside=False,extra_segments=tuple(geoms)):
                            continue
                        p=dict(front=f['id'],start=pt,end=end,dir=d,modules=modules,geom=geom,score=0.0)
                        nprops=props+[p]; ngeoms=geoms+[geom]
                        added=sum(math.hypot(q['end'][0]-q['start'][0],q['end'][1]-q['start'][1]) for q in nprops)
                        total=current_lane+added
                        origin=f.get('origin',base[0]); outward=math.hypot(end[0]-origin[0],end[1]-origin[1])
                        nscore=score-.75*self._congestion_at(end)+.30*outward/max(self.module,1e-9)+.20*modules
                        if total>=target_modules*self.module:
                            solution=nprops; break
                        nxt.append((nscore,end,d,nprops,ngeoms))
                    if solution is not None: break
                if solution is not None: break
            if solution is not None: break
            nxt.sort(key=lambda x:-x[0]); states=nxt[:beam_width]
            if not states: break
        if solution is None:
            return False
        for p in solution:
            a,b=p['start'],p['end']; olddir=f['dir']; f['path'].append(b); f['dir']=p['dir']
            L=math.hypot(b[0]-a[0],b[1]-a[1]); f['travel']+=L; f['gestures']+=1; f['local_gestures']+=1
            delta=(p['dir']-olddir)%8; sign=1 if delta==1 else -1 if delta==7 else 0
            if sign: f['last_turn_sign']=sign; f['straight_since_turn']=0
            else: f['straight_since_turn']=f.get('straight_since_turn',0)+1
            f['turn_history']=(f.get('turn_history',[])+[sign])[-7:]
            self._record_segment(f,a,b,p['geom'],normal=True)
        self.stats['pathway_young_survival_repair_count']+=1
        self.stats['pathway_young_survival_repair_trace_count']+=len(f.get('ids',()))
        return True

    def _try_bounded_escape_beam(self,f,horizon=3,beam_width=6):
        """Exceptional bounded rolling-horizon escape for an unresolved young route.

        Search is strictly capped and runs only after ordinary routing is frozen. It explores
        at most three 2-3-module setup gestures and tests a direct frame exit after every one.
        """
        if f.get('status')!='active': return False
        base=list(f['path']); start=base[-1]
        states=[(0.0,start,f['dir'],[],[])]  # score, point, dir, proposals, geoms
        solution=None
        for _depth in range(horizon):
            nxt=[]
            for score,pt,d0,props,geoms in states:
                tf=dict(f); tf['path']=base+[p['end'] for p in props]; tf['dir']=d0
                tf['gestures']=max(f.get('gestures',0),2); tf['local_gestures']=f.get('local_gestures',0)+len(props)
                for d in (d0,(d0-1)%8,(d0+1)%8):
                    for modules in (2,3):
                        end=point_along_dir(pt,d,modules*self.module)
                        candidate_pts=base+[q['end'] for q in props]+[end]
                        if self._points_have_compensating_zigzag(candidate_pts): continue
                        if len(f.get('ids',()))==1:
                            tid=f['ids'][0]
                            leg=[f['path'][-1]]+[q['end'] for q in props]+[end]
                            if self._connection_leg_creates_compensating_zigzag(f,tid,leg): continue
                        if self._candidate_loop_risk(tf,d,end): continue
                        geom=self._corridor_geom(tf,pt,end)
                        self.stats['pathway_lookahead_evaluation_count']+=1
                        if not self._gesture_clear(tf,pt,end,geom,allow_outside=False,extra_segments=tuple(geoms)): continue
                        p=dict(front=f['id'],start=pt,end=end,dir=d,modules=modules,geom=geom,score=0.0)
                        nprops=props+[p]; ngeoms=geoms+[geom]
                        nscore=score-.6*self._congestion_at(end)+.18*modules
                        # Test a one-leg exit from this improved head.
                        etf=dict(tf); etf['path']=base+[q['end'] for q in nprops]; etf['dir']=d
                        for ed in (d,(d-1)%8,(d+1)%8):
                            dist=self._forward_frame_distance(end,ed)
                            if not math.isfinite(dist) or dist<.2*self.module: continue
                            eend=point_along_dir(end,ed,dist+.70*self.module)
                            exit_pts=base+[q['end'] for q in nprops]+[eend]
                            if self._points_have_compensating_zigzag(exit_pts): continue
                            if len(f.get('ids',()))==1:
                                tid=f['ids'][0]
                                leg=[f['path'][-1]]+[q['end'] for q in nprops]+[eend]
                                if self._connection_leg_creates_compensating_zigzag(f,tid,leg): continue
                            if self._candidate_loop_risk(etf,ed,eend): continue
                            eg=self._corridor_geom(etf,end,eend)
                            self.stats['pathway_lookahead_evaluation_count']+=1
                            if self._gesture_clear(etf,end,eend,eg,allow_outside=True,extra_segments=tuple(ngeoms)):
                                ep=dict(front=f['id'],start=end,end=eend,dir=ed,modules=max(1,int(round(dist/self.module))),geom=eg,score=0.0)
                                solution=nprops+[ep]; break
                        if solution is not None: break
                        nxt.append((nscore,end,d,nprops,ngeoms))
                    if solution is not None: break
                if solution is not None: break
            if solution is not None: break
            nxt.sort(key=lambda x:-x[0]); states=nxt[:beam_width]
            if not states: break
        if solution is None: return False
        # Commit the already-validated terminal repair without invoking ordinary branch or
        # connection side effects. The rest of the board is frozen at this point.
        for p in solution:
            a,b=p['start'],p['end']; olddir=f['dir']; f['path'].append(b); f['dir']=p['dir']
            L=math.hypot(b[0]-a[0],b[1]-a[1]); f['travel']+=L; f['gestures']+=1; f['local_gestures']+=1
            delta=(p['dir']-olddir)%8; sign=1 if delta==1 else -1 if delta==7 else 0
            if sign: f['last_turn_sign']=sign; f['straight_since_turn']=0
            else: f['straight_since_turn']=f.get('straight_since_turn',0)+1
            f['turn_history']=(f.get('turn_history',[])+[sign])[-7:]
            self._record_segment(f,a,b,p['geom'],normal=(L>=2.0*self.module-1e-9))
        f['status']='escaped'; f['lifecycle']='TERMINAL'
        self.stats['pathway_escape_count']+=1; self.stats['pathway_escape_trace_count']+=len(f['ids'])
        self.stats['pathway_final_escape_repair_count']+=1
        return True

    def _try_final_escape(self,f):
        """Last-resort clean exit for an unresolved bundle at the global planning horizon.

        This is deliberately tiny search: continue straight or make one legal +/-45 degree
        turn and run to just beyond the frame.  It uses the same corridor/static/path collision
        tests as ordinary routing, so it cannot punch through existing geometry merely to avoid
        a terminal dot field.
        """
        if f.get('status')!='active':
            return False
        if f.get('local_gap') and not f.get('local_gap_exit_allowed',False):
            return False
        start=f['path'][-1]
        dirs=[f['dir'],(f['dir']+1)%8,(f['dir']-1)%8]
        candidates=[]
        for rank,d in enumerate(dirs):
            dist=self._forward_frame_distance(start,d)
            if not math.isfinite(dist) or dist<0:
                continue
            end=point_along_dir(start,d,dist+.70*self.module)
            if self._points_have_compensating_zigzag(list(f.get('path',()))+[end]):
                continue
            if len(f.get('ids',()))==1:
                tid=f['ids'][0]
                if self._connection_leg_creates_compensating_zigzag(f,tid,[start,end]):
                    continue
            if self._candidate_loop_risk(f,d,end):
                continue
            geom=self._corridor_geom(f,start,end)
            if not self._gesture_clear(f,start,end,geom,allow_outside=True):
                continue
            candidates.append((rank,dist,d,end,geom))
        if not candidates:
            return False
        _,_,d,end,geom=min(candidates,key=lambda x:(x[0],x[1]))
        f['path'].append(end)
        f['travel']+=math.hypot(end[0]-start[0],end[1]-start[1])
        f['gestures']+=1; f['local_gestures']+=1; f['dir']=d
        L=math.hypot(end[0]-start[0],end[1]-start[1])
        self._record_segment(f,start,end,geom,normal=(L>=2.0*self.module-1e-9))
        f['status']='escaped'; f['lifecycle']='TERMINAL'; f['termination_reason']=None
        self.stats['pathway_final_escape_repair_count']+=1
        return True

    def _try_terminal_separation(self,f):
        """Separate a final 2-3 lane cohort before termination instead of dotting a live bus.

        This is a last-horizon repair only.  Every lane takes one substantial straight/+45/-45
        leg away from its siblings, all legs are collision-tested, and the enlarged endpoint
        discs must fit with real clearance.  If the complete fan is not clean, nothing changes.
        """
        if f.get('status')!='active' or not (2<=len(f.get('ids',()))<=3):
            return False
        realised=self._materialized_paths(f)
        ordered=sorted(f['ids'],key=lambda tid:f['offsets'][tid])
        if len(ordered)==2:
            turns=[1,-1]
        else:
            turns=[1,0,-1]
        accepted_geoms=[]; accepted_discs=[]; plans=[]
        for idx,(tid,turn) in enumerate(zip(ordered,turns)):
            prefix=realised[tid]
            if len(prefix)<2:
                return False
            start=prefix[-1]
            direction=(f['dir']+turn)%8
            if (direction-f.get('initial_dir',f['dir']))%8==4:
                return False
            modules=1.65 if turn else 1.35
            end=point_along_dir(start,direction,modules*self.module)
            temp=dict(f)
            temp['id']=-(100000+f['id']*8+idx)
            temp['ids']=[tid]; temp['offsets']={tid:0.0}
            temp['thicknesses']={tid:f['thicknesses'][tid]}
            temp['path']=[prefix[-2],start]
            temp['parent']=f['id']; temp['branch_stage']=None
            temp['local_gestures']=0
            geom=self._corridor_geom(temp,start,end)
            if not self._gesture_clear(temp,start,end,geom,allow_outside=False,extra_segments=accepted_geoms):
                return False
            radius=self.r._termination_dot_radius(f['thicknesses'][tid])
            # Use the larger hollow outer edge conservatively regardless of the later fill draw.
            disc=Point(end).buffer(radius+.5*self.r.termination_dot_hollow_stroke,quad_segs=12)
            for olddisc in accepted_discs:
                if disc.distance(olddisc)<self.r.termination_dot_min_gap or disc.intersects(olddisc):
                    return False
            ancestors=self._ancestor_front_ids(temp)
            for rec in self.path_index.query(expand_bounds(disc.bounds,self.r.pathway_interroute_keepout)):
                if rec['front'] in ancestors and math.hypot(rec['end'][0]-start[0],rec['end'][1]-start[1])<=2.0*self.module:
                    continue
                if disc.intersects(rec['geom']) or disc.distance(rec['geom'])<self.r.pathway_interroute_keepout:
                    return False
            for gi,g in enumerate(self.static):
                keepout=(self.r.pathway_main_chip_keepout if gi < len(self.chips)
                         else self.r.pathway_static_keepout)
                if disc.intersects(g.geom) or disc.distance(g.geom)<keepout:
                    return False
            accepted_geoms.append(geom); accepted_discs.append(disc)
            plans.append((tid,start,end,direction,geom,prefix))
        children=[]
        for tid,start,end,direction,geom,prefix in plans:
            child=self._make_front(ids=[tid],chip=f['chip'],side=f['side'],side_index=f['side_index'],
                                   path=[start],direction=direction,offsets={tid:0.0},
                                   thicknesses={tid:f['thicknesses'][tid]},prefixes={tid:prefix},
                                   rng=SplitMix64(f['rng'].next_u64()),depth=min(5,f['depth']+1),
                                   intent=f['intent'],target=f['target'],parent=f['id'])
            child['path'].append(end)
            child['gestures']=f['gestures']+1; child['local_gestures']=1
            child['travel']=f['travel']+math.hypot(end[0]-start[0],end[1]-start[1])
            child['origin']=f['origin']; child['initial_dir']=f.get('initial_dir',f['dir'])
            child['turn_history']=list(f.get('turn_history',[]))
            child['status']='terminated'; child['termination_reason']='terminal_separation'
            self._record_segment(child,start,end,geom,normal=False)
            children.append(child)
        f['status']='branched'
        self.stats['pathway_split_count']+=1
        self.stats['pathway_terminal_separation_repair_count']+=1
        return bool(children)

    def _run_rounds(self):
        soft_rounds=self.profile['max_rounds']
        hard_rounds=soft_rounds+self.profile.get('persistence_tail_rounds',0)
        for round_index in range(hard_rounds):
            active=[f for f in self.fronts.values() if f['status']=='active']
            if not active:
                break
            pending=[f for f in active if f.get('fragment_pending')]
            for f in sorted(pending,key=lambda x:x['id']):
                f['fragment_pending']=False
                self._fragment_bundled_front(f)
            if pending:
                active=[f for f in self.fronts.values() if f['status']=='active']
            if round_index==soft_rounds:
                # Proactively dissolve small unresolved cohorts at the start of the persistence
                # tail, while there is still enough time for their lanes to travel apart before
                # any singleton termination can become legal.
                for f in sorted(active,key=lambda x:x['id']):
                    if (f['status']=='active' and 2<=len(f.get('ids',()))<=3 and
                            f.get('travel',0.0)>=4.0*self.module):
                        self._fragment_bundled_front(f)
                active=[f for f in self.fronts.values() if f['status']=='active']
            if round_index>=soft_rounds:
                # Persistence tail: unresolved multi-lane cohorts are not allowed to simply
                # age into a terminal dot field.  Give them an explicit escape objective and
                # enough local journey budget to leave the frame or split further.
                for f in active:
                    if len(f.get('ids',()))>1:
                        if f.get('local_gap'):
                            f['intent']='explore'
                            f['target']=self._local_gap_target(f['path'][-1],f['rng'],f['dir'])
                            f['max_gestures']=max(f['max_gestures'],f['gestures']+4)
                        else:
                            if f.get('intent')!='exit':
                                f['intent']='exit'
                                f['target']=self._distant_exit_target(f['path'][-1],f['rng'])
                            f['max_gestures']=max(f['max_gestures'],f['gestures']+4)
            self.stats['pathway_decision_round_count']=round_index+1
            if len(active)>1:
                self.stats['pathway_rounds_with_multiple_fronts']+=1
            for f in sorted(active,key=lambda x:x['id']):
                if f['status']=='active' and f.get('fan_pending') and self._launch_egress_cleared(f):
                    f['launch_egress_pending']=False
                    self._fan_front(f)

            # V33 TRANSACTIONAL ROUND PREPARATION.
            # First apply every ready rollback before anybody proposes.  V30 performed traceback
            # inside the per-front proposal loop, so a lower-id front could still see geometry
            # that a higher-id blocker removed later in the same round.  That was not one shared
            # snapshot.  All recovery is now a pre-transaction state transition.
            active=[f for f in self.fronts.values() if f['status']=='active']
            for f in sorted(active,key=lambda x:x['id']):
                if f.get('quality_repair_pending') and not f.get('reroute_pending'):
                    self._schedule_reroute(f,round_index,f.get('quality_repair_reason') or 'stagnation')
            for f in sorted(active,key=lambda x:x['id']):
                if f.get('reroute_pending') and round_index >= (f.get('reroute_ready_round') or 0):
                    f['_routing_round']=round_index
                    self._traceback_for_reroute(f)

            # Connection opportunities and structural decisions are now computed from the same
            # revised pre-move board.  Branching may change topology, so movement takes a fresh
            # immutable snapshot after structural transitions finish.
            active=[f for f in self.fronts.values() if f['status']=='active']
            self._assign_round_connection_targets(active,round_index)
            for f in sorted(active,key=lambda x:x['id']):
                if f['status']=='active' and self._should_branch(f):
                    self._branch_front(f)

            active=[f for f in self.fronts.values() if f['status']=='active']
            self._assign_round_connection_targets(active,round_index)
            self._assign_local_bundle_affinities(active,round_index)
            for f in active:
                f['_routing_round']=round_index

            # Every front proposes against this exact committed snapshot.  No proposal is added
            # to path_index until all local conflict transactions have been solved.
            variant_map={}; blocked=[]
            for f in sorted(active,key=lambda x:x['id']):
                self._refresh_lifecycle(f)
                if f.get('reroute_pending'):
                    # A future-round repair request is intentionally frozen this round.
                    continue
                life=self._refresh_lifecycle(f)
                variants=self._proposal_variants(f,3 if life=='LAUNCHING' else (2 if self._needs_holistic(f) else 1))
                if variants: variant_map[f['id']]=variants
                else: blocked.append(f)

            # No-proposal young fronts negotiate with the causal active blocker.  If a blocker
            # agrees to yield, its already-created proposal is removed from this transaction;
            # neither participant receives a commit-order advantage.
            for f in blocked:
                if self._request_local_yield(f,round_index):
                    continue
                if f.get('fan_pending') and self._launch_egress_cleared(f):
                    f['launch_egress_pending']=False
                    self._fan_front(f)
                    if f['status']!='active': continue
                f['failures']+=1; self.stats['pathway_blocked_gesture_count']+=1
                life=self._refresh_lifecycle(f)
                connection_ready=(len(f['ids'])<=4 or f['depth']>=1 or f['gestures']>=5 or
                                  (life=='LAUNCHING' and f['gestures']>=1))
                if f['gestures']>=1 and connection_ready and self._near_foreign_corridor(f):
                    chance=self.profile['connection_appetite']*(.98 if f['intent']=='connect' else .78)
                    if len(f['ids'])>1 and f['depth']<5 and f['rng'].random()<chance and self._branch_front(f): continue
                if life=='LAUNCHING' and f['failures']>=1 and not f.get('reroute_pending'):
                    if self._schedule_reroute(f,round_index,'early_launch_block'):
                        self.stats['pathway_early_reroute_scheduled_count']+=1
                        continue
                if f['failures']>=2 and f.get('branch_stage')==0 and len(f['ids'])>1 and f['depth']<1:
                    if self._branch_front(f): continue
                if f['failures']>=3:
                    branched=False
                    if len(f['ids'])>1 and f['depth']<5 and f['local_gestures']>=1 and f['straight_since_turn']>=2:
                        branched=bool(self._branch_front(f))
                    if not branched:
                        self.stats['pathway_hard_stop_count']+=1
                        if not self._schedule_reroute(f,round_index,'hard_stop'):
                            if len(f['ids'])>1 and self._defer_bundled_hard_stop(f,round_index): continue
                            self._terminate_front(f,'hard_stop_exhausted')

            # A yield/repair may have been requested after variants were generated.  Such a front
            # cannot also commit a stale proposal from the old snapshot.
            variant_map={fid:vs for fid,vs in variant_map.items()
                         if self.fronts[fid].get('status')=='active' and not self.fronts[fid].get('reroute_pending')}

            # Joint local arbitration.  Every coupled component either receives one compatible
            # proposal per front or receives no movement commit at all.  There is deliberately no
            # V30 "first-choice then priority-sorted winner" fallback.
            chosen={}; grouped=set()
            for group in self._conflict_groups(variant_map):
                grouped.update(group)
                self.stats['pathway_same_round_conflict_count']+=max(1,len(group)-1)
                sol=self._solve_conflict_group(group,variant_map)
                if sol is None:
                    self._schedule_atomic_conflict_repair(group,round_index)
                    continue
                chosen.update({p['front']:p for p in sol})
            for fid,variants in variant_map.items():
                if fid not in grouped and variants:
                    chosen[fid]=variants[0]

            # Defensive exact second pass over the selected assignment.  If a broad-phase edge
            # was ever missed, defer that whole newly-discovered component rather than choosing a
            # sequential loser.
            selected_map={fid:[p] for fid,p in chosen.items()
                         if self.fronts[fid].get('status')=='active' and not self.fronts[fid].get('reroute_pending')}
            late_groups=self._conflict_groups(selected_map)
            late_deferred=set()
            for group in late_groups:
                self._schedule_atomic_conflict_repair(group,round_index)
                late_deferred.update(group)
            selected=[p for fid,p in sorted(chosen.items())
                      if fid not in late_deferred and self.fronts[fid].get('status')=='active'
                      and not self.fronts[fid].get('reroute_pending')]

            # ATOMIC MOVEMENT COMMIT.  First write every accepted movement segment without any
            # proximity/branch/termination reaction.  Only after the complete round geometry is
            # present do post-move reactions run.  Therefore no front can observe an earlier
            # same-round proposal as historical geometry while deciding whether its own movement
            # is allowed.
            for p in selected:
                self._accept(self.fronts[p['front']],p,defer_post=True)
            if selected:
                self.stats['pathway_atomic_round_commit_count']+=1
            for p in selected:
                f=self.fronts[p['front']]
                if f.get('status')=='active':
                    self._post_accept(f,p)
            self._connect_singletons()
        for f in sorted(self.fronts.values(),key=lambda x:x['id']):
            if f['status']=='active':
                if self._try_final_escape(f):
                    continue
                if (f.get('travel',0.0)<5.0*self.module or self._refresh_lifecycle(f) in ('LAUNCHING','RECOVERING')) and self._try_bounded_escape_beam(f):
                    continue
                if not f.get('local_gap') and self._minimum_materialized_lane_length(f)<self.main_launch_maturity_modules*self.module-1e-7:
                    if self._try_young_survival_beam(f,target_modules=self.main_launch_maturity_modules,horizon=4,beam_width=12):
                        if self._minimum_materialized_lane_length(f)>=self.main_launch_maturity_modules*self.module-1e-7:
                            self._terminate_front(f,'round_limit')
                        continue
                    f['protected_launch_unresolved']=True
                    continue
                min_lane=self._minimum_materialized_lane_length(f)
                if (not f.get('local_gap') and
                        self.main_launch_maturity_modules*self.module-1e-7 <= min_lane < self.main_launch_preferred_terminal_modules*self.module and
                        not f.get('post_egress_final_extension_attempted')):
                    f['post_egress_final_extension_attempted']=True
                    if self._try_young_survival_beam(f,target_modules=self.main_launch_preferred_terminal_modules,horizon=2,beam_width=6):
                        self._terminate_front(f,'round_limit')
                        continue
                if 2<=len(f.get('ids',()))<=3 and self._try_terminal_separation(f):
                    continue
                self._terminate_front(f,'round_limit')
        # If the anti-singular-termination rule deliberately kept a few lanes alive through
        # the hard horizon, never drop them from the SVG.  Resolve them as coordinated terminal
        # groups: fragment siblings finish together; any remaining same-root persistence lanes
        # also finish as one final cohort.  This is a true last resort after all routing,
        # traceback, split, connection and escape attempts have been exhausted.
        remaining=[f for f in self.fronts.values() if f['status']=='active']
        handled=set()
        by_fragment={}
        for f in remaining:
            if f.get('fragment_group') is not None:
                by_fragment.setdefault(f['fragment_group'],[]).append(f)
        for fs in by_fragment.values():
            for f in fs:
                if not f.get('local_gap') and self._minimum_materialized_lane_length(f)<self.main_launch_maturity_modules*self.module-1e-7:
                    f['protected_launch_unresolved']=True
                    continue
                f['status']='terminated'; f['termination_reason']='coordinated_persistence_limit'
                handled.add(f['id'])
                self.stats['pathway_coordinated_persistence_terminal_trace_count']+=len(f['ids'])
        by_root={}
        for f in remaining:
            if f['id'] in handled:
                continue
            by_root.setdefault((f['chip'],f['side_index'],f['side']),[]).append(f)
        for fs in by_root.values():
            for f in fs:
                if not f.get('local_gap') and self._minimum_materialized_lane_length(f)<self.main_launch_maturity_modules*self.module-1e-7:
                    f['protected_launch_unresolved']=True
                    continue
                f['status']='terminated'; f['termination_reason']='coordinated_persistence_limit'
                self.stats['pathway_coordinated_persistence_terminal_trace_count']+=len(f['ids'])
        unresolved=[f for f in self.fronts.values() if f.get('status')=='active' and f.get('protected_launch_unresolved')]
        self.stats['pathway_protected_launch_unresolved_count']=sum(len(f.get('ids',())) for f in unresolved)
        if unresolved:
            raise RuntimeError('protected main launch settlement unresolved')
        # Last-chance arbitration occurs before terminal dots exist.  If two free foreign
        # heads finish close enough for a collision-clean head-to-head join, connecting them
        # is mandatory; rendering two terminal dots staring at one another is never preferred.
        self._connect_forced_close_lane_heads(include_terminated=True)

    def _turn_directions(self,pts):
        dirs=[]
        for a,b in zip(pts,pts[1:]):
            if math.hypot(b[0]-a[0],b[1]-a[1])>1e-7:
                dirs.append(nearest_dir_index(b[0]-a[0],b[1]-a[1]))
        return dirs

    def _audit_trace_intersections(self,records):
        index=SpatialHash(max(70*self.U,2*self.module)); accidental=0; collapsed=0; pairs=[]
        for rec in records:
            line=LineString(rec['points'])
            for old in index.query(expand_bounds(line.bounds,.2*self.U)):
                pair=tuple(sorted((rec['tid'],old['tid'])))
                inter=line.intersection(old['line'])
                if inter.is_empty:
                    continue
                if inter.geom_type in ('LineString','MultiLineString') and inter.length>1e-6:
                    collapsed+=1; accidental+=1; pairs.append((rec['tid'],old['tid'],'collapsed')); continue
                allowed=self.connection_pairs.get(pair)
                if allowed is not None:
                    pts=[]
                    if inter.geom_type=='Point': pts=[inter]
                    elif hasattr(inter,'geoms'): pts=[g for g in inter.geoms if g.geom_type=='Point']
                    if pts and all(math.hypot(p.x-allowed[0],p.y-allowed[1])<=1.5*self.U for p in pts):
                        continue
                accidental+=1; pairs.append((rec['tid'],old['tid'],inter.geom_type))
            indexed=dict(tid=rec['tid'],line=line)
            index.insert(indexed,line.bounds)
        self.accidental_pairs=pairs
        return accidental,collapsed

    def _audit_trace_stroke_overlaps(self,records):
        bad=0
        for i,a in enumerate(records):
            for b in records[i+1:]:
                inter=a['primitive'].geom.intersection(b['primitive'].geom)
                if inter.is_empty:
                    continue
                pair=tuple(sorted((a['tid'],b['tid'])))
                meet=self.connection_pairs.get(pair)
                if meet is not None:
                    ta=a['primitive'].svg.get('stroke_width',0.0); tb=b['primitive'].svg.get('stroke_width',0.0)
                    if inter.difference(Point(meet).buffer(self._connection_joint_radius(ta,tb),quad_segs=8)).is_empty:
                        continue
                bad+=1
        return bad

    def _clip_polyline_end(self,points,distance):
        """Shorten a polyline by `distance` from its terminal end without changing its path."""
        pts=[tuple(p) for p in points]
        remain=max(0.0,float(distance))
        while len(pts)>=2 and remain>1e-9:
            a,b=pts[-2],pts[-1]
            L=math.hypot(b[0]-a[0],b[1]-a[1])
            if L<=1e-9:
                pts.pop(); continue
            if remain < L-1e-9:
                t=(L-remain)/L
                pts[-1]=(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)
                remain=0.0
            else:
                remain-=L
                pts.pop()
        return pts

    def _clip_polyline_start(self,points,distance):
        """Shorten a polyline by `distance` from its starting end without changing its path."""
        pts=[tuple(p) for p in points]
        remain=max(0.0,float(distance))
        while len(pts)>=2 and remain>1e-9:
            a,b=pts[0],pts[1]
            L=math.hypot(b[0]-a[0],b[1]-a[1])
            if L<=1e-9:
                pts.pop(0); continue
            if remain < L-1e-9:
                t=remain/L
                pts[0]=(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)
                remain=0.0
            else:
                remain-=L
                pts.pop(0)
        return pts

    def _clip_escaped_polyline_to_frame(self,points):
        """Stop an escaped trace at its first visible frame crossing.

        Routing may extend a centreline outside the canvas to make escape unambiguous.  SVG
        viewport clipping makes that exterior geometry invisible, so it must not participate in
        final collision cleanup and delete an otherwise valid visible trace.
        """
        pts=[tuple(p) for p in points]
        if len(pts)<2: return pts
        frame=box(0.0,0.0,self.W,self.H)
        out=[]
        for i,p in enumerate(pts):
            inside=(-1e-9<=p[0]<=self.W+1e-9 and -1e-9<=p[1]<=self.H+1e-9)
            if i==0:
                out.append(p)
                continue
            prev=pts[i-1]
            prev_inside=(-1e-9<=prev[0]<=self.W+1e-9 and -1e-9<=prev[1]<=self.H+1e-9)
            if prev_inside and inside:
                out.append(p); continue
            if prev_inside and not inside:
                seg=LineString([prev,p]).intersection(frame)
                coords=[]
                if seg.geom_type=='LineString': coords=list(seg.coords)
                elif hasattr(seg,'geoms'):
                    for g in seg.geoms:
                        if g.geom_type=='LineString': coords.extend(list(g.coords))
                if coords:
                    q=max(coords,key=lambda z:math.hypot(z[0]-prev[0],z[1]-prev[1]))
                    dlast=math.hypot(q[0]-out[-1][0],q[1]-out[-1][1])
                    if dlast>1e-7:
                        if dlast < .10*self.module and len(out)>=2:
                            # Do not create a microscopic final segment merely because the
                            # invisible escape continuation crossed the viewport a few pixels
                            # after the last in-frame vertex. Extend the previous visible leg to
                            # the frame instead.
                            out[-1]=(q[0],q[1])
                        else:
                            out.append((q[0],q[1]))
                break
            # An escaped route should never re-enter, but ignore already-exterior continuation
            # rather than letting invisible geometry affect the rendered safety audit.
            if not prev_inside:
                break
        return out if len(out)>=2 else pts

    def _materialize(self):
        all_leaves=[f for f in self.fronts.values() if f['status'] not in ('active','branched','abandoned_short')]
        abandoned_short=[f for f in self.fronts.values() if f['status']=='abandoned_short']
        self.stats['pathway_abandoned_short_bundle_count']=len(abandoned_short)
        self.stats['pathway_abandoned_short_trace_count']=sum(len(f['ids']) for f in abandoned_short)
        # Short involuntary dead ends are failed recovery branches, not intentional visual
        # terminations.  Prune them unconditionally rather than drawing tiny stubs.  Realized
        # chip-side coverage is a soft target/diagnostic, never a quota that can legitimize an
        # otherwise-invalid post-emergence death.
        prunable={
            f['id'] for f in all_leaves
            if f['status']=='terminated'
            and f.get('travel',0.0)<2.75*self.module
            and (f.get('local_gap') or f.get('termination_reason') in ('hard_stop_exhausted','round_limit','coordinated_persistence_limit'))
        }
        leaves=[f for f in all_leaves if f['id'] not in prunable]
        self.stats['pathway_abandoned_short_bundle_count']+=len(prunable)
        self.stats['pathway_abandoned_short_trace_count']+=sum(len(self.fronts[fid]['ids']) for fid in prunable)
        self.stats['pathway_leaf_bundle_count']=len(leaves)
        root_prims:Dict[Tuple[int,int,str],List[Primitive]]={}
        root_meta={}
        trace_records=[]
        # Final safety net: emitted traces are admitted through a precise centreline index.
        # The planner should normally make this a no-op; if an old/shared-prefix edge case
        # produces a duplicate or an unmarked crossing, that trace is suppressed rather than
        # rendering an intersection.
        render_line_index=SpatialHash(max(70*self.U,2*self.module))
        render_marker_index=SpatialHash(max(30*self.U,self.module))
        debug=getattr(self.r,'pathway_debug_stage',None)=='corridors'
        for f in leaves:
            paths=self._materialized_paths(f)
            key=(f['chip'],f['side_index'],f['side'])
            root_prims.setdefault(key,[])
            root_meta.setdefault(key,dict(spacings=[],trace_ids=set(),dirs=[]))
            if debug and len(f['path'])>=2:
                root_prims[key].append(prim_polyline(f['path'],max(2.2*self.U,self._front_half_width(f)*.18),self.r.FG,round_caps=False))
            for tid in f['ids']:
                logical_pts=paths[tid]
                if len(logical_pts)<2:
                    continue
                marker=None
                source_marker=None
                special_local=bool(f.get('local_gap_special')) and len(f.get('ids',()))==1
                pts=list(logical_pts)
                if f['status']=='escaped':
                    pts=self._clip_escaped_polyline_to_frame(pts)
                logical_len=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:]))
                main_near_floor=(not f.get('local_gap') and f['chip']<len(self.chips) and f['status']=='terminated' and
                                 logical_len < (self.main_launch_maturity_modules+.55)*self.module)
                if not debug:
                    # Ordinary traces carry the V23 source-dot language. Extra-thick local
                    # singletons deliberately do not: the stroke's own round cap becomes the
                    # outer disc and a background-coloured negative circle hollows its centre.
                    mrng=SplitMix64(mix_once(self.sseed ^ (tid+1)*0x9E3779B97F4A7C15))
                    sx,sy=logical_pts[0]; t=f['thicknesses'][tid]
                    if not special_local:
                        sfilled=True if main_near_floor else (mrng.random()<.55)
                        sradius=self.r._termination_dot_radius(t)
                        sstroke=0.0 if sfilled else self.r.termination_dot_hollow_stroke
                        source_marker=prim_circle(sx,sy,sradius,self.r.FG,sfilled,sstroke)
                        if not sfilled:
                            pts=self._clip_polyline_start(pts,sradius+0.5*sstroke)
                if f['status']=='terminated' and not debug:
                    pts,backoff=self._backoff_terminal_points(f,tid,pts,render_marker_index)
                    if backoff>0:
                        self.stats['pathway_terminal_head_backoff_count']+=1
                        self.stats['pathway_terminal_head_backoff_distance']+=backoff
                if f['status']=='terminated' and not debug and not special_local:
                    filled=True if main_near_floor else (mrng.random()<.55)
                    x,y=pts[-1]; t=f['thicknesses'][tid]
                    radius=self.r._termination_dot_radius(t)
                    stroke=0.0 if filled else self.r.termination_dot_hollow_stroke
                    if not filled:
                        # Hollow endpoints must not manufacture a microscopic final segment.
                        # If clipping the line back to the outside of the hollow marker would
                        # violate the visible segment floor, use the equally legal filled-dot
                        # variant instead of visually amputating the trace.
                        clipped=self._clip_polyline_end(pts,radius+0.5*stroke)
                        if (len(clipped)<2 or
                                math.hypot(clipped[-1][0]-clipped[-2][0],clipped[-1][1]-clipped[-2][1]) < .10*self.module-1e-9):
                            filled=True; stroke=0.0
                        else:
                            pts=clipped
                    marker=prim_circle(x,y,radius,self.r.FG,filled,stroke)
                if len(pts)<2:
                    continue
                # The current renderer hardens the *rendered* no-tiny-death invariant. Source/terminal marker
                # clipping can shorten an otherwise legal centreline below 2.75 modules, so
                # audit the visible polyline here for every terminated trace, not only locals.
                if f['status']=='terminated':
                    visible_len=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:]))
                    if visible_len < 2.75*self.module:
                        self.stats['pathway_abandoned_short_trace_count']+=1
                        continue
                # Offset/fragment materialization can expose a short A→B→A lateral twitch even
                # when the owning bundle centreline passed the planning-time zigzag guard. Free
                # terminal/escaped traces are soft output; suppress the ugly leaf rather than
                # rendering a hard grammar violation or asking the router to search again.
                if f['status']!='connected' and self._points_have_compensating_zigzag(pts):
                    self.stats['pathway_zigzag_trace_cleanup_count']+=1
                    self.stats.setdefault('pathway_zigzag_cleanup_details',[]).append(dict(tid=tid,front=f['id'],chip=f['chip'],side=f.get('side'),side_index=f.get('side_index'),status=f.get('status'),reason=f.get('termination_reason'),points=[(round(x,3),round(y,3)) for x,y in pts]))
                    continue
                prim=prim_polyline(pts,f['thicknesses'][tid],self.r.FG,round_caps=special_local)
                line=LineString(pts)
                unsafe=None
                if not line.is_simple:
                    unsafe='intersection'
                else:
                    for old in render_line_index.query(expand_bounds(line.bounds,max(1.0*self.U,f['thicknesses'][tid]))):
                        pair=tuple(sorted((tid,old['tid'])))
                        allowed=self.connection_pairs.get(pair)
                        inter=line.intersection(old['line'])
                        if not inter.is_empty:
                            if inter.geom_type in ('LineString','MultiLineString') and inter.length>1e-6:
                                unsafe='duplicate'; break
                            points=[]
                            if inter.geom_type=='Point': points=[inter]
                            elif hasattr(inter,'geoms'): points=[g for g in inter.geoms if g.geom_type=='Point']
                            if not (allowed is not None and points and all(math.hypot(q.x-allowed[0],q.y-allowed[1])<=1.5*self.U for q in points)):
                                unsafe='intersection'; break
                        stroke_inter=prim.geom.intersection(old['primitive'].geom)
                        if not stroke_inter.is_empty:
                            if allowed is None:
                                unsafe='intersection'; break
                            joint=Point(allowed).buffer(self._connection_joint_radius(f['thicknesses'][tid],old.get('thickness',old['primitive'].svg.get('stroke_width',0.0))),quad_segs=8)
                            if not stroke_inter.difference(joint).is_empty:
                                unsafe='intersection'; break
                if unsafe is not None:
                    if unsafe=='duplicate':
                        self.stats['pathway_duplicate_trace_cleanup_count']+=1
                    else:
                        self.stats['pathway_intersection_trace_cleanup_count']+=1
                        self.stats.setdefault('pathway_intersection_cleanup_pairs',[]).append(dict(new_tid=tid,old_tid=(old['tid'] if 'old' in locals() else None),new_front=f['id'],new_parent=f.get('parent'),new_family=self._launch_family_key(f),new_chip=f['chip'],new_side_index=f.get('side_index'),new_side=f.get('side'),old_front=(old.get('front') if 'old' in locals() else None),old_parent=(old.get('parent') if 'old' in locals() else None),old_family=(old.get('family') if 'old' in locals() else None),old_chip=(old.get('chip') if 'old' in locals() else None),new_status=f.get('status'),new_reason=f.get('termination_reason'),old_status=(old.get('status') if 'old' in locals() else None),old_reason=(old.get('termination_reason') if 'old' in locals() else None),new_points=[(round(x,2),round(y,2)) for x,y in pts],old_points=([(round(x,2),round(y,2)) for x,y in old['line'].coords] if 'old' in locals() else [])))
                    continue
                render_line_index.insert(dict(tid=tid,line=line,primitive=prim,chip=f['chip'],side_index=f.get('side_index'),side=f.get('side'),front=f['id'],parent=f.get('parent'),family=self._launch_family_key(f),status=f.get('status'),termination_reason=f.get('termination_reason'),thickness=f['thicknesses'][tid]),line.bounds)
                if not debug:
                    root_prims[key].append(prim)
                    if special_local:
                        hole_r=max(1.35*self.U,self.r.local_gap_special_hole_radius_ratio*f['thicknesses'][tid])
                        hs=prim_circle(logical_pts[0][0],logical_pts[0][1],hole_r,self.r.BG,True)
                        root_prims[key].append(hs); self.stats['pathway_local_gap_special_hollow_cap_count']+=1
                        # A connected/component endpoint must remain electrically/visually joined;
                        # hollow only a free terminal cap. Escaped ends are off-frame by definition.
                        if f['status']=='terminated':
                            he=prim_circle(pts[-1][0],pts[-1][1],hole_r,self.r.BG,True)
                            root_prims[key].append(he); self.stats['pathway_local_gap_special_hollow_cap_count']+=1
                    if source_marker is not None:
                        root_prims[key].append(source_marker)
                        self.stats['pathway_source_marker_count']+=1
                trace_records.append(dict(tid=tid,chip=f['chip'],root=key,status=f['status'],points=pts,primitive=prim,local_gap=bool(f.get('local_gap') or f['chip']>=len(self.chips)),local_gap_special=special_local))
                root_meta[key]['trace_ids'].add(tid)
                root_meta[key]['dirs'].extend(self._turn_directions(pts))
                if marker is not None:
                    root_prims[key].append(marker)
                    render_marker_index.insert(dict(geom=marker.geom),marker.geom.bounds)
        groups=[]; visible_coverages=[]
        for key,prims in sorted(root_prims.items()):
            chip,side_index,side=key
            trace_count=len(root_meta[key]['trace_ids'])
            # A root whose every candidate trace was removed by final duplicate/intersection
            # cleanup is not a visible pathway group and must not survive as empty metadata.
            if trace_count<=0:
                continue
            launch_groups=[f for f in self.fronts.values() if f['chip']==chip and f['side_index']==side_index and f['side']==side and f['parent'] is None]
            all_offsets=[]
            visible_ids=root_meta[key]['trace_ids']
            for f in launch_groups:
                all_offsets.extend(v for tid,v in f['offsets'].items() if tid in visible_ids)
            spacing=[]
            for f in launch_groups:
                vals=sorted(f['offsets'].values())
                spacing.extend(abs(b-a) for a,b in zip(vals,vals[1:]))
            if chip < len(self.chips):
                chip_group=self.chips[chip]
                _,_,body_w,body_h=self.r._chip_body_rect(chip_group)
                side_span=body_w if side in ('top','bottom') else body_h
                coverage=(max(all_offsets)-min(all_offsets))/side_span if len(all_offsets)>1 else 0.0
                visible_coverages.append(coverage)
                groups.append(Group(f'pathway-chip{chip}-side{side_index}',prims,dict(
                    placement_kind='pathway',pathway=True,planner_mode='route_first_family_protected_transactional_parallel',
                    bundle_source_chip=chip,launch_side=side,launch_line_count=trace_count,
                    bundle_spacing=(sum(spacing)/len(spacing) if spacing else 0.0),
                    launch_coverage_ratio=coverage,segment_direction_indices=root_meta[key]['dirs'])))
            else:
                local_root=next((f for f in launch_groups if f.get('local_gap')),None)
                groups.append(Group(f'pathway-local-gap-{side_index}',prims,dict(
                    placement_kind='pathway',pathway=True,local_gap_pathway=True,
                    local_gap_special=bool(local_root and local_root.get('local_gap_special')),
                    planner_mode='route_first_family_protected_transactional_parallel',launch_line_count=trace_count,
                    bundle_spacing=(sum(spacing)/len(spacing) if spacing else 0.0),
                    segment_direction_indices=root_meta[key]['dirs'])))

        # Main-chip launch metrics remain separate from the later local-gap population.
        self.stats['pathway_visible_launch_trace_count']=len({rec['tid'] for rec in trace_records if rec['chip'] < len(self.chips)})
        self.stats['pathway_local_gap_visible_trace_count']=len({rec['tid'] for rec in trace_records if rec.get('local_gap')})
        self.stats['pathway_local_gap_escape_trace_count']=len({rec['tid'] for rec in trace_records if rec.get('local_gap') and rec.get('status')=='escaped'})
        # Report the final rendered marker state, after V30 terminal-head backoff, rather than
        # the pre-materialization logical marker layout used by the repair phase.
        rendered_markers=list(render_marker_index.objects.values())
        marker_conflicts=0
        for i,a in enumerate(rendered_markers):
            for b in rendered_markers[i+1:]:
                if a['geom'].intersects(b['geom']) or a['geom'].distance(b['geom'])<self.r.termination_dot_min_gap:
                    marker_conflicts+=1
        self.stats['pathway_termination_marker_overlap_count']=marker_conflicts
        self.stats['pathway_visible_launch_coverage_min']=min(visible_coverages,default=0.0)
        self.stats['pathway_visible_launch_coverage_max']=max(visible_coverages,default=0.0)
        statuses={s:sum(1 for f in leaves if f['status']==s) for s in ('connected','component','escaped','terminated')}
        trace_statuses={s:sum(len(f['ids']) for f in leaves if f['status']==s) for s in ('connected','component','escaped','terminated')}
        self.stats['pathway_connection_count']=self.stats['pathway_cross_chip_connection_count']+self.stats['pathway_collection_connection_count']
        self.stats['pathway_termination_count']=statuses['terminated']
        self.stats['pathway_termination_trace_count']=trace_statuses['terminated']
        self.stats['pathway_bundled_forced_termination_trace_count']=sum(
            len(f['ids']) for f in leaves if f['status']=='terminated' and len(f['ids'])>1
        )
        self.stats['pathway_trace_count']=len(trace_records)
        lengths=[]; seg_counts=[]; turns=[]; zigzags=0; terminal_alignments=0; actual_segments=[]
        for rec in trace_records:
            pts=rec['points']; ls=[math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:])]
            dirs=self._turn_directions(pts)
            lengths.append(sum(ls)); actual_segments.extend(ls); seg_counts.append(len(ls))
            turns.append(sum(1 for a,b in zip(dirs,dirs[1:]) if a!=b))
            # A single long dogleg is a meaningful PCB displacement.  The rejected grammar is
            # a short compensating twitch or a repeated alternating weave.
            for j,(a,b,c) in enumerate(zip(dirs,dirs[1:],dirs[2:])):
                middle=ls[j+1] if j+1<len(ls) else 0.0
                repeated=(j+3<len(dirs) and dirs[j+3]==b)
                if a==c and a!=b and (middle<2*self.module or repeated):
                    if rec['status']=='connected' and j+3==len(dirs):
                        terminal_alignments+=1
                    else:
                        zigzags+=1
        self.stats['pathway_mean_segments_per_trace']=sum(seg_counts)/len(seg_counts) if seg_counts else 0.0
        self.stats['pathway_max_segments_per_trace']=max(seg_counts,default=0)
        self.stats['pathway_min_segments_per_trace']=min(seg_counts,default=0)
        self.stats['pathway_short_trace_count']=sum(x<3 for x in seg_counts)
        self.stats['pathway_short_trace_fraction']=self.stats['pathway_short_trace_count']/len(seg_counts) if seg_counts else 0.0
        short_terminations=sum(1 for rec,length in zip(trace_records,lengths)
                               if rec['status']=='terminated' and length<4*self.module)
        terminated_traces=sum(1 for rec in trace_records if rec['status']=='terminated')
        self.stats['pathway_short_termination_trace_count']=short_terminations
        self.stats['pathway_short_termination_fraction']=(short_terminations/terminated_traces if terminated_traces else 0.0)
        main_short_terminations=sum(1 for rec,length in zip(trace_records,lengths)
                                    if (not rec.get('local_gap') and rec['status']=='terminated' and
                                        length<self.main_launch_maturity_modules*self.module-1e-7))
        self.stats['pathway_main_short_termination_trace_count']=main_short_terminations
        self.stats['pathway_main_launch_survival_count']=len({rec['tid'] for rec in trace_records if not rec.get('local_gap')})
        by_root={}
        for rec,length in zip(trace_records,lengths):
            if rec.get('local_gap'): continue
            by_root.setdefault(rec['root'],[]).append((rec,length))
        stalled=0
        for root,items in by_root.items():
            if items and all(rec['status']=='terminated' for rec,_ in items) and max(length for _,length in items)<8.0*self.module:
                stalled+=1
        self.stats['pathway_main_stalled_side_count']=stalled
        self.stats['pathway_tiny_termination_trace_count']=sum(1 for rec,length in zip(trace_records,lengths)
                                                               if rec['status']=='terminated' and length<2.75*self.module)
        board_scale=sum(length>=.30*math.hypot(self.W,self.H) for length in lengths)
        self.stats['pathway_board_scale_trace_count']=board_scale
        self.stats['pathway_board_scale_trace_fraction']=board_scale/len(lengths) if lengths else 0.0
        self.stats['pathway_mean_geometric_length']=sum(lengths)/len(lengths) if lengths else 0.0
        self.stats['pathway_median_geometric_length']=(sorted(lengths)[len(lengths)//2] if lengths else 0.0)
        self.stats['pathway_turn_count']=sum(turns)
        self.stats['pathway_mean_turns_per_trace']=sum(turns)/len(turns) if turns else 0.0
        self.stats['pathway_turns_per_100U']=(100*self.U*sum(turns)/sum(lengths)) if sum(lengths)>0 else 0.0
        self.stats['pathway_compensating_zigzag_count']=zigzags
        self.stats['pathway_terminal_alignment_exception_count']=terminal_alignments
        normal_lengths=[x for f in leaves for x in f['normal_segment_lengths']]
        self.stats['pathway_min_normal_center_segment']=min(normal_lengths,default=0.0)
        self.stats['pathway_min_actual_segment']=min(actual_segments,default=0.0)
        self.stats['pathway_coverage_cell_fraction']=len(self.coverage_cells)/(12*12)
        quartiles=set()
        for gx,gy in self.coverage_cells:
            quartiles.add((gx>=6,gy>=6))
        self.stats['pathway_canvas_quartiles_touched']=len(quartiles)
        self.stats['pathway_static_intersection_count']=sum(
            1 for rec in trace_records for g in self.static if rec['primitive'].geom.intersects(g.geom)
        )
        foreign_clearances=[]
        foreign_chip_clearances=[]
        for rec in trace_records:
            for gi,g in enumerate(self.static):
                if gi==rec['chip']:
                    continue
                d=rec['primitive'].geom.distance(g.geom)
                foreign_clearances.append(d)
                if gi < len(self.chips):
                    foreign_chip_clearances.append(d)
        self.stats['pathway_min_foreign_static_clearance']=min(foreign_clearances,default=0.0)
        self.stats['pathway_min_foreign_main_chip_clearance']=min(foreign_chip_clearances,default=0.0)
        self.stats['pathway_required_static_keepout']=self.r.pathway_static_keepout
        self.stats['pathway_required_main_chip_keepout']=self.r.pathway_main_chip_keepout
        self.stats['pathway_terminal_head_keepout']=self.r.pathway_terminal_head_keepout
        self.stats['pathway_chip_launch_gap']=self.r.pathway_chip_launch_gap
        self.stats['pathway_termination_dot_scale']=self.r.termination_dot_scale
        self.stats['pathway_termination_dot_hollow_stroke']=self.r.termination_dot_hollow_stroke
        # V34 hard trace grammar audit. Pathway bodies are piecewise straight and each bend is
        # at most 45 degrees. Any 90-degree corner or curved primitive is a sample failure.
        illegal_turns=0
        for rec in trace_records:
            dirs=self._turn_directions(rec['points'])
            for da,db in zip(dirs,dirs[1:]):
                delta=(db-da)%8
                if delta not in (0,1,7):
                    illegal_turns+=1
        self.stats['pathway_illegal_turn_count']=illegal_turns
        self.stats['pathway_curved_primitive_count']=sum(1 for g in root_prims.values() for p in g if p.svg.get('type')=='quadratic')
        accidental,collapsed=self._audit_trace_intersections(trace_records)
        self.stats['pathway_unmarked_stroke_overlap_count']=self._audit_trace_stroke_overlaps(trace_records)
        connection_use={}
        visible_by_tid={rec['tid']:rec for rec in trace_records}
        non_head=0
        for pair,meet in self.connection_pairs.items():
            for tid in pair:
                connection_use[tid]=connection_use.get(tid,0)+1
            for tid in pair:
                rec=visible_by_tid.get(tid)
                if rec is None or math.hypot(rec['points'][-1][0]-meet[0],rec['points'][-1][1]-meet[1])>1.5*self.U:
                    non_head+=1; break
        self.stats['pathway_multiply_connected_trace_count']=sum(1 for n in connection_use.values() if n>1)
        self.stats['pathway_midline_connection_count']=non_head
        self.trace_records=trace_records
        self.stats['pathway_unmarked_overlap_count']=accidental
        self.stats['pathway_collapsed_overlap_count']=collapsed
        self.stats['pathway_overlap_event_count']=accidental
        return groups,self.stats

    def _terminal_marker_discs(self,f):
        if f.get('status')!='terminated': return []
        paths=self._materialized_paths(f); out=[]
        for tid in f.get('ids',()):
            pts=paths.get(tid)
            if not pts: continue
            radius=self.r._termination_dot_radius(f['thicknesses'][tid]) + .5*self.r.termination_dot_hollow_stroke
            out.append((tid,pts[-1],Point(pts[-1]).buffer(radius,quad_segs=12),radius))
        return out

    def _try_terminal_marker_shorten(self,f,other_discs):
        """Move a singleton terminal head backward along its last accepted segment.

        This never adds occupied geometry; it only shortens a previously valid stroke.  It is
        therefore the safest possible repair when two enlarged endpoint markers overlap.
        """
        if f.get('status')!='active' or len(f.get('ids',()))!=1 or len(f.get('path',()))<2: return False
        tid=f['ids'][0]; a,b=f['path'][-2],f['path'][-1]
        seg=math.hypot(b[0]-a[0],b[1]-a[1])
        # A nominal one-module final leg can land a few ulps below exactly 1.0*module.
        # Treat it as eligible for marker-clearance shortening; this repair only removes
        # already-valid geometry and never creates a new collision.
        if seg<.90*self.module: return False
        ux=(b[0]-a[0])/seg; uy=(b[1]-a[1])/seg
        radius=self.r._termination_dot_radius(f['thicknesses'][tid])+.5*self.r.termination_dot_hollow_stroke
        max_shift=max(0.0,seg-.55*self.module)
        for shift in (.15,.25,.35,.50,.70):
            shift*=self.module
            if shift>max_shift: continue
            end=(b[0]-ux*shift,b[1]-uy*shift)
            disc=Point(end).buffer(radius,quad_segs=12)
            if any(disc.intersects(od) or disc.distance(od)<self.r.termination_dot_min_gap for od in other_discs): continue
            bad=False
            for gi,g in enumerate(self.static):
                keep=(self.r.pathway_main_chip_keepout if gi<len(self.chips) else self.r.pathway_static_keepout)
                if disc.intersects(g.geom) or disc.distance(g.geom)<keep: bad=True; break
            if bad: continue
            # Marker itself must not touch a foreign trace. Own/ancestor geometry is expected.
            ancestors=self._ancestor_front_ids(f)
            for rec in self.path_index.query(expand_bounds(disc.bounds,self.r.pathway_interroute_keepout)):
                if rec['front']==f['id'] or rec['front'] in ancestors: continue
                if disc.intersects(rec['geom']) or disc.distance(rec['geom'])<self.r.pathway_interroute_keepout:
                    bad=True; break
            if bad: continue
            # Replace the last centerline segment with its shortened version.
            f['path'][-1]=end; f['travel']=max(0.0,f['travel']-shift)
            for j in range(len(self.path_segments)-1,-1,-1):
                rec=self.path_segments[j]
                if rec['front']==f['id'] and math.hypot(rec['end'][0]-b[0],rec['end'][1]-b[1])<1e-5:
                    rec['end']=end; rec['geom']=self._corridor_geom(f,a,end); break
            self._rebuild_path_index_and_coverage()
            f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']='marker_clearance_shorten'
            return True
        return False

    def _try_terminal_marker_nudge(self,f,other_discs):
        if f.get('status')!='active' or len(f.get('ids',()))!=1: return False
        tid=f['ids'][0]; paths=self._materialized_paths(f); pts=paths.get(tid)
        if not pts: return False
        start=pts[-1]
        for d in (f['dir'],(f['dir']-1)%8,(f['dir']+1)%8):
            for modules in (2.0,1.5,1.25):
                end=point_along_dir(start,d,modules*self.module)
                if self._candidate_loop_risk(f,d,end): continue
                if self._connection_leg_creates_compensating_zigzag(f,tid,[start,end]): continue
                geom=self._corridor_geom(f,start,end)
                outside=not (0<=end[0]<=self.W and 0<=end[1]<=self.H)
                if not self._gesture_clear(f,start,end,geom,allow_outside=outside): continue
                radius=self.r._termination_dot_radius(f['thicknesses'][tid])+.5*self.r.termination_dot_hollow_stroke
                disc=Point(end).buffer(radius,quad_segs=12)
                if not outside:
                    if any(disc.intersects(od) or disc.distance(od)<self.r.termination_dot_min_gap for od in other_discs):
                        continue
                    bad_static=False
                    for gi,g in enumerate(self.static):
                        keep=(self.r.pathway_main_chip_keepout if gi<len(self.chips) else self.r.pathway_static_keepout)
                        if disc.intersects(g.geom) or disc.distance(g.geom)<keep: bad_static=True; break
                    if bad_static: continue
                f['path'].append(end); f['travel']+=math.hypot(end[0]-start[0],end[1]-start[1])
                f['gestures']+=1; f['local_gestures']+=1; f['dir']=d
                self._record_segment(f,start,end,geom,normal=(modules>=2.0))
                if outside:
                    f['status']='escaped'; f['lifecycle']='TERMINAL'; f['termination_reason']=None
                else:
                    f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']='marker_clearance_nudge'
                return True
        return False

    def _try_connect_specific_terminal_heads(self,a,ta,b,tb):
        """Connect one known pair of free singleton terminal heads, with exact geometry checks."""
        if (a.get('status')!='terminated' or b.get('status')!='terminated' or
                len(a.get('ids',()))!=1 or len(b.get('ids',()))!=1 or
                ta in self.connected_trace_ids or tb in self.connected_trace_ids):
            return False
        pa=self._materialized_paths(a).get(ta,[]); pb=self._materialized_paths(b).get(tb,[])
        if not pa or not pb: return False
        pa,pb=pa[-1],pb[-1]
        aa=self._temp_singleton_for_head(a,ta,pa,-3000000-ta)
        bb=self._temp_singleton_for_head(b,tb,pb,-4000000-tb)
        solved=None
        for _cost,meet,lega,legb in self._head_join_candidates(a,b,pa,pb):
            if not self._head_junction_clear(aa,bb,meet): continue
            if (any(math.hypot(y[0]-x[0],y[1]-x[1])<.10*self.module for x,y in zip(lega,lega[1:])) or
                    any(math.hypot(y[0]-x[0],y[1]-x[1])<.10*self.module for x,y in zip(legb,legb[1:]))): continue
            geoma=[self._corridor_geom(aa,x,y) for x,y in zip(lega,lega[1:])]
            if not self._special_leg_clear(aa,lega,meeting=meet): continue
            if not self._special_leg_clear(bb,legb,meeting=meet,extra=geoma): continue
            if (self._connection_leg_creates_compensating_zigzag(a,ta,lega) or
                    self._connection_leg_creates_compensating_zigzag(b,tb,legb)): continue
            if not self._precise_head_join_clear(aa,bb,ta,tb,lega,legb,meet): continue
            solved=(meet,lega,legb); break
        if solved is None: return False
        meet,lega,legb=solved
        for f,leg in ((a,lega),(b,legb)):
            for x,y in zip(leg,leg[1:]):
                geom=self._corridor_geom(f,x,y); f['path'].append(y)
                L=math.hypot(y[0]-x[0],y[1]-x[1]); f['travel']+=L
                if L<self.module-.01*self.U: self.stats['pathway_minimum_segment_exception_count']+=1
                self._record_segment(f,x,y,geom,normal=False)
            f['status']='connected'; f['lifecycle']='TERMINAL'; f['termination_reason']=None
        self.connection_pairs[tuple(sorted((ta,tb)))]=meet
        self.connected_trace_ids.update((ta,tb))
        if a['chip']!=b['chip']:
            self.cross_chip_connected_trace_ids.update((ta,tb))
            self.stats['pathway_cross_chip_connection_count']+=1
        else:
            self.stats.setdefault('pathway_same_chip_head_connection_count',0)
            self.stats['pathway_same_chip_head_connection_count']+=1
        self.stats['pathway_cross_chip_connected_trace_count']=len(self.cross_chip_connected_trace_ids)
        self.stats['pathway_forced_close_head_connection_count']+=1
        return True

    def _junction_blocker_ids(self,a,b,meet):
        radius=max(3.5*self.U,.55*(self._front_half_width(a)+self._front_half_width(b)))
        disk=Point(meet).buffer(radius,quad_segs=8)
        allowed={a['id'],b['id']}|self._ancestor_front_ids(a)|self._ancestor_front_ids(b)
        out=set()
        for rec in self.path_index.query(expand_bounds(disk.bounds,self.r.pathway_interroute_keepout)):
            if rec['front'] in allowed: continue
            if disk.intersects(rec['geom']) or disk.distance(rec['geom'])<self.r.pathway_interroute_keepout:
                out.add(rec['front'])
        return out

    def _rewind_terminal_blocker_to_prefix(self,f):
        """Remove only a terminal child's local tail; inherited/shared prefixes remain intact."""
        if f.get('status')!='terminated' or not f.get('route_history') or len(f.get('path',()))<2:
            return False
        snap=f['route_history'][0]
        self.path_segments=[rec for rec in self.path_segments if rec['front']!=f['id']]
        f['path']=[f['path'][0]]; f['route_history']=[]
        for key in ('dir','travel','gestures','local_gestures','turn_cooldown','straight_since_turn','last_turn_sign','branch_stage','branch_turn','max_origin_distance','stagnant_gestures'):
            if key in snap: f[key]=snap[key]
        f['turn_history']=list(snap.get('turn_history',[]))
        del f['normal_segment_lengths'][snap.get('normal_len_count',0):]
        f['failures']=0; f['reroute_pending']=False; f['quality_repair_pending']=False
        f['reroute_mode_rounds']=3; f['status']='parked_repair'; f['lifecycle']='RECOVERING'; f['termination_reason']=None
        self._rebuild_path_index_and_coverage()
        return True

    def _try_terminal_head_blocker_negotiation(self,conflict):
        """Let an obvious close head pair negotiate with one local terminal blocker."""
        a,ta,pa,_da,_ra=conflict[0]; b,tb,pb,_db,_rb=conflict[1]
        if (len(a.get('ids',()))!=1 or len(b.get('ids',()))!=1 or
                ta in self.connected_trace_ids or tb in self.connected_trace_ids): return False
        d=math.hypot(pb[0]-pa[0],pb[1]-pa[1])
        if d>2.75*self.module or d<1e-9: return False
        # Use the visible incoming lane directions, not merely the cohort's current dir field.
        ap=self._materialized_paths(a).get(ta,[]); bp=self._materialized_paths(b).get(tb,[])
        if len(ap)<2 or len(bp)<2: return False
        av=(ap[-1][0]-ap[-2][0],ap[-1][1]-ap[-2][1]); bv=(bp[-1][0]-bp[-2][0],bp[-1][1]-bp[-2][1])
        al=max(1e-9,math.hypot(*av)); bl=max(1e-9,math.hypot(*bv)); ux=(pb[0]-pa[0])/d; uy=(pb[1]-pa[1])/d
        if av[0]/al*ux+av[1]/al*uy<.20 or bv[0]/bl*(-ux)+bv[1]/bl*(-uy)<.20: return False
        aa=self._temp_singleton_for_head(a,ta,pa,-5000000-ta); bb=self._temp_singleton_for_head(b,tb,pb,-6000000-tb)
        candidate_blockers=[]
        for _cost,meet,_lega,_legb in self._head_join_candidates(a,b,pa,pb):
            blockers=self._junction_blocker_ids(aa,bb,meet)
            if blockers: candidate_blockers.append((len(blockers),meet,blockers))
        if not candidate_blockers: return False
        _n,_meet,blockers=min(candidate_blockers,key=lambda x:x[0])
        if len(blockers)>2: return False
        blockers=[self.fronts.get(fid) for fid in sorted(blockers)]
        blockers=[f for f in blockers if f is not None and f.get('status')=='terminated' and
                  len(f.get('ids',()))==1 and f['ids'][0] not in self.connected_trace_ids]
        if not blockers: return False
        import copy
        # Usually one route is the culprit. Try each eligible blocker independently.
        for blocker in blockers[:2]:
            saved_front=copy.deepcopy(blocker); saved_segments=[dict(rec) for rec in self.path_segments]
            if not self._rewind_terminal_blocker_to_prefix(blocker): continue
            blocker['status']='parked_repair'
            if not self._try_connect_specific_terminal_heads(a,ta,b,tb):
                self.fronts[blocker['id']]=saved_front; self.path_segments=saved_segments; self._rebuild_path_index_and_coverage()
                continue
            # The join is now authoritative. Give the yielded blocker a bounded local escape
            # against the frozen board + new connection; if no exit exists it may terminate at
            # the earlier checkpoint, where normal marker repair will handle its endpoint.
            blocker=self.fronts[blocker['id']]; blocker['status']='active'; blocker['lifecycle']='RECOVERING'
            blocker['intent']='exit'; blocker['target']=self._distant_exit_target(blocker['path'][-1],blocker['rng'])
            if not (self._try_final_escape(blocker) or self._try_bounded_escape_beam(blocker)):
                blocker['status']='terminated'; blocker['lifecycle']='TERMINAL'; blocker['termination_reason']='blocker_yield_checkpoint'
            self.stats.setdefault('pathway_terminal_blocker_yield_count',0)
            self.stats['pathway_terminal_blocker_yield_count']+=1
            return True
        return False

    def _connect_near_main_terminals(self,max_pairs=8):
        """Bounded post-main sweep for obvious cross-chip terminal joins.

        V32 launch protection reduced incidental encounters. V33 restores connection density by
        giving already-finished singleton main heads one final exact-geometry chance to join
        before the local-gap phase begins. No mid-line attachment is permitted.
        """
        terms=[]
        for f in self.fronts.values():
            if (f.get('status')=='terminated' and not f.get('local_gap') and f.get('chip',9999)<len(self.chips)
                    and len(f.get('ids',()))==1 and f['ids'][0] not in self.connected_trace_ids):
                tid=f['ids'][0]; pts=self._materialized_paths(f).get(tid,[])
                if len(pts)>=2: terms.append((f,tid,pts[-1],pts[-2]))
        pairs=[]
        for i,a in enumerate(terms):
            for b in terms[i+1:]:
                if a[0]['chip']==b[0]['chip']: continue
                d=math.hypot(b[2][0]-a[2][0],b[2][1]-a[2][1])
                if d>6.5*self.module or d<.35*self.module: continue
                # Prefer facing or roughly convergent heads.
                ux=(b[2][0]-a[2][0])/d; uy=(b[2][1]-a[2][1])/d
                av=(a[2][0]-a[3][0],a[2][1]-a[3][1]); bv=(b[2][0]-b[3][0],b[2][1]-b[3][1])
                al=max(1e-9,math.hypot(*av)); bl=max(1e-9,math.hypot(*bv))
                facing=(av[0]/al*ux+av[1]/al*uy>-0.05 and bv[0]/bl*(-ux)+bv[1]/bl*(-uy)>-0.05)
                if not facing: continue
                pairs.append((d,a,b))
        pairs.sort(key=lambda z:(z[0],z[1][0]['id'],z[2][0]['id']))
        used=set(); made=0
        for _d,a,b in pairs:
            if made>=max_pairs: break
            if a[0]['id'] in used or b[0]['id'] in used: continue
            if self._try_connect_specific_terminal_heads(a[0],a[1],b[0],b[1]):
                used.update((a[0]['id'],b[0]['id'])); made+=1
        self.stats['pathway_post_main_terminal_connection_count']=made
        return made

    def _try_terminal_marker_cluster_stagger(self,discs,seed_conflict):
        """Resolve a small cluster of enlarged terminal dots by shortening final legs together.

        Pairwise repair can deadlock when moving A away from B collides with C.  This bounded
        local solver treats the connected marker cluster as one tiny problem.  It never adds
        route geometry: each singleton endpoint may only slide backward along its already-valid
        final segment, so the trace network itself cannot acquire a new crossing.
        """
        # Build the connected overlap/near-gap cluster around the seed pair.
        by_front={}
        for rec in discs: by_front.setdefault(rec[0]['id'],[]).append(rec)
        cluster={seed_conflict[0][0]['id'],seed_conflict[1][0]['id']}
        changed=True
        while changed:
            changed=False
            for a in discs:
                if a[0]['id'] not in cluster: continue
                for b in discs:
                    if b[0]['id'] in cluster: continue
                    # Include nearby terminal heads that a backward stagger could run into,
                    # not only the pair already overlapping.  The repair search can shift by
                    # up to .40 module, so use a conservative half-module neighborhood.
                    if (a[3].intersects(b[3]) or
                            a[3].distance(b[3])<self.r.termination_dot_min_gap+.50*self.module):
                        cluster.add(b[0]['id']); changed=True
        if not (2<=len(cluster)<=6): return False
        fronts=[self.fronts[fid] for fid in sorted(cluster)]
        if any(f.get('status')!='terminated' or len(f.get('ids',()))!=1 or len(f.get('path',()))<2 for f in fronts):
            return False
        import itertools
        opts=[]
        for f in fronts:
            tid=f['ids'][0]; a,b=f['path'][-2],f['path'][-1]
            seg=math.hypot(b[0]-a[0],b[1]-a[1])
            if seg<.90*self.module: return False
            ux=(b[0]-a[0])/seg; uy=(b[1]-a[1])/seg
            rad=self.r._termination_dot_radius(f['thicknesses'][tid])+.5*self.r.termination_dot_hollow_stroke
            cand=[]
            shift_fracs=((0,.05,.10,.15,.20) if len(cluster)>4
                         else (0,.05,.10,.15,.20,.25,.30,.35,.40))
            for frac in shift_fracs:
                shift=frac*self.module
                if shift>seg-.55*self.module+1e-8: continue
                end=(b[0]-ux*shift,b[1]-uy*shift)
                disc=Point(end).buffer(rad,quad_segs=12)
                bad=False
                for gi,g in enumerate(self.static):
                    keep=(self.r.pathway_main_chip_keepout if gi<len(self.chips) else self.r.pathway_static_keepout)
                    if disc.intersects(g.geom) or disc.distance(g.geom)<keep: bad=True; break
                if not bad: cand.append((frac,end,disc))
            if not cand: return False
            opts.append(cand)
        outside=[rec for rec in discs if rec[0]['id'] not in cluster]
        # Search by *total* .05-module shortening rather than Cartesian product.  The first
        # feasible vector is therefore the smallest visual change, and a six-marker cluster
        # usually resolves in only tens of combinations instead of 5^6/9^6 trials.
        tick=.05
        max_ticks=[]
        for cand in opts:
            max_ticks.append(max(int(round(x[0]/tick)) for x in cand))
        cand_by_tick=[]
        for cand in opts:
            cand_by_tick.append({int(round(x[0]/tick)):x for x in cand})
        def allocations(total,n,prefix=()):
            if n==1:
                if total<=max_ticks[len(prefix)]: yield prefix+(total,)
                return
            idx=len(prefix)
            for t in range(min(max_ticks[idx],total)+1):
                yield from allocations(total-t,n-1,prefix+(t,))
        exact_tries=0
        max_total=min(sum(max_ticks),12)
        for total in range(max_total+1):
            for ticks in allocations(total,len(fronts)):
                try: combo=[cand_by_tick[i][t] for i,t in enumerate(ticks)]
                except KeyError: continue
                cdiscs=[x[2] for x in combo]; ok=True
                for i,a in enumerate(cdiscs):
                    for b in cdiscs[i+1:]:
                        if a.intersects(b) or a.distance(b)<self.r.termination_dot_min_gap:
                            ok=False; break
                    if not ok: break
                    for rec in outside:
                        if a.intersects(rec[3]) or a.distance(rec[3])<self.r.termination_dot_min_gap:
                            ok=False; break
                    if not ok: break
                if not ok: continue
                exact_tries+=1
                if exact_tries>24: return False
                moved_ids={f['id'] for f,choice in zip(fronts,combo) if choice[0]>0}
                saved=[]
                for f,choice in zip(fronts,combo):
                    _frac,end,_disc=choice; old_end=f['path'][-1]; old_travel=f['travel']
                    a=f['path'][-2]; shift=math.hypot(old_end[0]-end[0],old_end[1]-end[1])
                    rec_hit=None
                    for j in range(len(self.path_segments)-1,-1,-1):
                        rec=self.path_segments[j]
                        if rec['front']==f['id'] and math.hypot(rec['end'][0]-old_end[0],rec['end'][1]-old_end[1])<1e-5:
                            rec_hit=rec; break
                    saved.append((f,old_end,old_travel,rec_hit, None if rec_hit is None else rec_hit['end'], None if rec_hit is None else rec_hit['geom']))
                    f['path'][-1]=end; f['travel']=max(0.0,old_travel-shift)
                    if rec_hit is not None:
                        rec_hit['end']=end; rec_hit['geom']=self._corridor_geom(f,a,end)
                self._rebuild_path_index_and_coverage()
                valid=True; current=[]
                for tf in [x for x in self.fronts.values() if x.get('status')=='terminated']:
                    for tid,pnt,disc,rad in self._terminal_marker_discs(tf): current.append((tf,tid,pnt,disc,rad))
                for i,a in enumerate(current):
                    for b in current[i+1:]:
                        if a[3].intersects(b[3]) or a[3].distance(b[3])<self.r.termination_dot_min_gap:
                            valid=False; break
                    if not valid: break
                    if a[0]['id'] in moved_ids:
                        anc=self._ancestor_front_ids(a[0])
                        for rec in self.path_index.query(expand_bounds(a[3].bounds,self.r.pathway_interroute_keepout)):
                            if rec['front']==a[0]['id'] or rec['front'] in anc: continue
                            if a[3].intersects(rec['geom']) or a[3].distance(rec['geom'])<self.r.pathway_interroute_keepout:
                                valid=False; break
                        if not valid: break
                if valid:
                    for f in fronts: f['termination_reason']='marker_cluster_stagger'
                    self.stats.setdefault('pathway_terminal_marker_cluster_repair_count',0)
                    self.stats['pathway_terminal_marker_cluster_repair_count']+=1
                    return True
                for f,old_end,old_travel,rec_hit,old_rec_end,old_rec_geom in saved:
                    f['path'][-1]=old_end; f['travel']=old_travel
                    if rec_hit is not None: rec_hit['end']=old_rec_end; rec_hit['geom']=old_rec_geom
                self._rebuild_path_index_and_coverage()
        return False
        return False

    def _repair_terminal_marker_conflicts(self):
        """Keep V21's doubled termination dots physically separated.

        Termination decisions can be made by different fronts in different rounds, so the
        ordinary lane-pitch rule alone cannot guarantee that their final discs fit together.
        Repair is intentionally local and bounded: one conflicting terminal front is reopened
        and asked to escape/separate while the rest of the network remains frozen.
        """
        for _ in range(8):
            terms=[f for f in self.fronts.values() if f.get('status')=='terminated']
            discs=[]
            for f in terms:
                for tid,p,d,r in self._terminal_marker_discs(f): discs.append((f,tid,p,d,r))
            conflict=None
            for i,a in enumerate(discs):
                for b in discs[i+1:]:
                    if a[0]['id']==b[0]['id'] and a[1]==b[1]: continue
                    if a[3].intersects(b[3]) or a[3].distance(b[3])<self.r.termination_dot_min_gap:
                        conflict=(a,b); break
                if conflict: break
            if conflict is None: break
            repaired=False
            if self._try_terminal_head_blocker_negotiation(conflict):
                repaired=True
                continue
            # Prefer reopening the smaller/younger cohort; if that cannot move, try its peer.
            fronts=sorted({conflict[0][0]['id']:conflict[0][0], conflict[1][0]['id']:conflict[1][0]}.values(),
                          key=lambda f:(len(f.get('ids',())),f.get('travel',0.0),f['id']))
            for f in fronts:
                old_reason=f.get('termination_reason'); f['status']='active'; f['lifecycle']='RECOVERING'
                other_discs=[x[3] for x in discs if x[0]['id']!=f['id']]
                if (self._try_final_escape(f) or
                    (2<=len(f.get('ids',()))<=3 and self._try_terminal_separation(f)) or
                    self._try_terminal_marker_shorten(f,other_discs) or
                    self._try_terminal_marker_nudge(f,other_discs) or
                    self._try_bounded_escape_beam(f)):
                    repaired=True; break
                f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']=old_reason
            if not repaired and self._try_terminal_marker_cluster_stagger(discs,conflict):
                repaired=True
            if not repaired: break
        # Pairwise repairs can move a conflict around a tight marker cluster.  Before
        # reporting failure, solve the remaining local cluster once as a bounded joint stagger.
        terms=[f for f in self.fronts.values() if f.get('status')=='terminated']
        final_discs=[]
        for tf in terms:
            for tid,p,d,r in self._terminal_marker_discs(tf): final_discs.append((tf,tid,p,d,r))
        final_conflict=None
        for i,a in enumerate(final_discs):
            for b in final_discs[i+1:]:
                if a[3].intersects(b[3]) or a[3].distance(b[3])<self.r.termination_dot_min_gap:
                    final_conflict=(a,b); break
            if final_conflict: break
        if final_conflict is not None:
            self._try_terminal_marker_cluster_stagger(final_discs,final_conflict)

        # Local-gap networks are optional fillers.  If an otherwise irreparable doubled-dot
        # conflict involves one of them, discard that local terminal cohort instead of leaving
        # a hard visual violation or perturbing the already-good main network.
        for _ in range(8):
            terms=[f for f in self.fronts.values() if f.get('status')=='terminated']
            discs=[]
            for f in terms:
                for tid,p,d,r in self._terminal_marker_discs(f): discs.append((f,tid,p,d,r))
            conflict=None
            for i,a in enumerate(discs):
                for b in discs[i+1:]:
                    if a[3].intersects(b[3]) or a[3].distance(b[3])<self.r.termination_dot_min_gap:
                        conflict=(a,b); break
                if conflict: break
            if conflict is None: break
            locals_=[x[0] for x in conflict if x[0].get('local_gap') or x[0].get('chip',-1)>=len(self.chips)]
            if not locals_: break
            victim=sorted({f['id']:f for f in locals_}.values(),key=lambda f:(f.get('travel',0.0),len(f.get('ids',())),f['id']))[0]
            victim['status']='abandoned_short'; victim['termination_reason']='local_marker_conflict'

        # Report any conflict that genuinely has no legal local repair.
        terms=[f for f in self.fronts.values() if f.get('status')=='terminated']
        discs=[]
        for f in terms:
            for tid,p,d,r in self._terminal_marker_discs(f): discs.append((f,tid,p,d,r))
        count=0
        for i,a in enumerate(discs):
            for b in discs[i+1:]:
                if a[3].intersects(b[3]) or a[3].distance(b[3])<self.r.termination_dot_min_gap: count+=1
        self.stats['pathway_termination_marker_overlap_count']=count

    def _front_visible_grammar_ok(self,f):
        paths=self._materialized_paths(f)
        for pts in paths.values():
            if len(pts)<2: return False
            if self._points_have_compensating_zigzag(pts): return False
            dirs=self._turn_directions(pts)
            if any((b-a)%8 not in (0,1,7) for a,b in zip(dirs,dirs[1:])): return False
        return True

    def _repair_main_preflight_front(self,f):
        """Causal terminal repair: reopen, traceback recent history, then regrow locally."""
        if f is None or f.get('local_gap') or f.get('chip',len(self.chips))>=len(self.chips): return False
        if f.get('status') not in ('terminated','escaped'): return False
        if any(tid in self.connected_trace_ids for tid in f.get('ids',())): return False
        old_status=f.get('status'); old_reason=f.get('termination_reason')
        f['status']='active'; f['lifecycle']='RECOVERING'; f['termination_reason']=None
        # Roll back enough history to cross the decision that produced the bad visible tail.
        f['reroute_attempts']=min(1,f.get('reroute_attempts',0))
        removed=self._traceback_for_reroute(f)
        if removed<=0:
            f['status']=old_status; f['termination_reason']=old_reason; return False
        self.stats['pathway_preflight_causal_repair_count']=self.stats.get('pathway_preflight_causal_repair_count',0)+1
        moved=0
        for _ in range(5):
            variants=self._proposal_variants(f,count=3)
            if not variants: break
            # Space-aware score + replay-direction blacklist are already part of the proposal.
            p=variants[0]
            self._accept(f,p,defer_post=True); moved+=1
            if moved>=2 and self._front_visible_grammar_ok(f):
                f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']='preflight_causal_reroute'
                self.stats['pathway_preflight_causal_repair_success_count']=self.stats.get('pathway_preflight_causal_repair_success_count',0)+1
                return True
        if self._try_final_escape(f) and self._front_visible_grammar_ok(f):
            self.stats['pathway_preflight_causal_repair_success_count']=self.stats.get('pathway_preflight_causal_repair_success_count',0)+1
            return True
        return False

    def _repair_main_preflight_materialization(self,stats):
        ids=[]
        for d in stats.get('pathway_zigzag_cleanup_details',[]):
            if d.get('chip',len(self.chips))<len(self.chips): ids.append(d.get('front'))
        for d in stats.get('pathway_intersection_cleanup_pairs',[]):
            for key in ('new_front','old_front'):
                fid=d.get(key)
                if fid is not None:
                    f=self.fronts.get(fid)
                    if f is not None and not f.get('local_gap') and f.get('chip',len(self.chips))<len(self.chips): ids.append(fid)
        repaired=False
        for fid in sorted(set(x for x in ids if x is not None))[:6]:
            repaired=self._repair_main_preflight_front(self.fronts.get(fid)) or repaired
        if repaired:
            self._rebuild_path_index_and_coverage()
        return repaired

    def run(self):
        self._launch_fronts()
        self._run_rounds()
        main_rounds=self.stats.get('pathway_decision_round_count',0)
        self._connect_near_main_terminals(max_pairs=8)
        # V34 fail-fast main-only materialization audit. Do not spend local-gap/component work
        # on a main network whose offset lanes would later be suppressed, kinked, or shortened.
        _pre_groups,_pre_stats=self._materialize()
        pre_bad=(_pre_stats.get('pathway_visible_launch_trace_count',0) != _pre_stats.get('pathway_launch_trace_count',0) or
                _pre_stats.get('pathway_main_short_termination_trace_count',0) != 0 or
                _pre_stats.get('pathway_main_stalled_side_count',0) != 0 or
                _pre_stats.get('pathway_illegal_turn_count',0) != 0 or
                _pre_stats.get('pathway_curved_primitive_count',0) != 0 or
                _pre_stats.get('pathway_unmarked_stroke_overlap_count',0) != 0 or
                _pre_stats.get('pathway_unmarked_overlap_count',0) != 0 or
                _pre_stats.get('pathway_static_intersection_count',0) != 0)
        if pre_bad and self._repair_main_preflight_materialization(_pre_stats):
            # Re-audit the repaired frozen main network before any gap-filling work begins.
            for k in ('pathway_zigzag_trace_cleanup_count','pathway_intersection_trace_cleanup_count','pathway_duplicate_trace_cleanup_count'):
                self.stats[k]=0
            self.stats['pathway_zigzag_cleanup_details']=[]; self.stats['pathway_intersection_cleanup_pairs']=[]
            _pre_groups,_pre_stats=self._materialize()
            pre_bad=(_pre_stats.get('pathway_visible_launch_trace_count',0) != _pre_stats.get('pathway_launch_trace_count',0) or
                    _pre_stats.get('pathway_main_short_termination_trace_count',0) != 0 or
                    _pre_stats.get('pathway_main_stalled_side_count',0) != 0 or
                    _pre_stats.get('pathway_illegal_turn_count',0) != 0 or
                    _pre_stats.get('pathway_curved_primitive_count',0) != 0 or
                    _pre_stats.get('pathway_unmarked_stroke_overlap_count',0) != 0 or
                    _pre_stats.get('pathway_unmarked_overlap_count',0) != 0 or
                    _pre_stats.get('pathway_static_intersection_count',0) != 0)
        if pre_bad:
            diag={k:_pre_stats.get(k) for k in (
                'pathway_launch_trace_count','pathway_visible_launch_trace_count',
                'pathway_main_short_termination_trace_count','pathway_main_stalled_side_count',
                'pathway_illegal_turn_count','pathway_curved_primitive_count',
                'pathway_unmarked_stroke_overlap_count','pathway_unmarked_overlap_count',
                'pathway_static_intersection_count','pathway_zigzag_trace_cleanup_count',
                'pathway_intersection_trace_cleanup_count','pathway_duplicate_trace_cleanup_count')}
            diag['zigzag_details']=_pre_stats.get('pathway_zigzag_cleanup_details',[])[:3]
            raise RuntimeError('main-network preflight materialization invariant violated: '+json.dumps(diag,sort_keys=True))
        # Local networks now have an explicit residual-gap coverage objective rather than a
        # fixed source-count quota.  Up to three bounded waves are allowed; each wave measures
        # actual covered representative cells before deciding whether more local sources are useful.
        old_rounds=self.profile['max_rounds']; old_tail=self.profile.get('persistence_tail_rounds',0)
        local_round_budget=28
        self.stats['pathway_local_gap_round_budget']=local_round_budget
        self.profile['max_rounds']=local_round_budget
        self.profile['persistence_tail_rounds']=7
        total_local_rounds=0
        source_cap=None; previous_covered=0
        for _wave in range(7):
            spawned=self._launch_local_gap_fronts(source_cap=source_cap)
            if not spawned:
                break
            if any(f.get('local_gap') and f.get('status')=='active' for f in self.fronts.values()):
                self._run_rounds()
                total_local_rounds+=self.stats.get('pathway_decision_round_count',0)
            covered=self._local_gap_covered_cells()
            self.stats['pathway_local_gap_covered_cell_count']=len(covered)
            self.stats['pathway_local_gap_fill_actual']=(len(covered)/len(self.local_gap_open_cells) if self.local_gap_open_cells else 0.0)
            # Representative coverage is deliberately soft.  Once we are within one coarse
            # cell of the sampled ~40% target, do not launch another whole wave just to hit an
            # exact quota and overshoot the composition.
            if len(covered)>=max(0,self.local_gap_target_count-1):
                break
            gain=max(1,len(covered)-previous_covered)
            previous_covered=len(covered)
            deficit=max(0,self.local_gap_target_count-len(covered))
            cells_per_source=max(.75,gain/max(1,spawned))
            source_cap=max(4,min(22,int(math.ceil(1.18*deficit/cells_per_source))))
        self.stats['pathway_decision_round_count']=main_rounds+total_local_rounds
        self.profile['max_rounds']=old_rounds; self.profile['persistence_tail_rounds']=old_tail
        self._repair_terminal_marker_conflicts()
        groups,stats=self._materialize()
        # V33 acceptance invariant: final rendering is not allowed to silently undo successful
        # main routing.  If materialization would suppress or visually shorten a main launch,
        # reject this routing result rather than ship a murdered line.
        if (stats.get('pathway_visible_launch_trace_count',0) != stats.get('pathway_launch_trace_count',0) or
                stats.get('pathway_main_short_termination_trace_count',0) != 0 or
                stats.get('pathway_main_stalled_side_count',0) != 0):
            raise RuntimeError('main launch survival/side-progress invariant violated during materialization')
        if (stats.get('pathway_unmarked_stroke_overlap_count',0) or
                stats.get('pathway_unmarked_overlap_count',0) or
                stats.get('pathway_static_intersection_count',0)):
            raise RuntimeError('hard pathway overlap invariant violated during materialization')
        if stats.get('pathway_illegal_turn_count',0) or stats.get('pathway_curved_primitive_count',0):
            raise RuntimeError('hard straight-segment / <=45-degree turn invariant violated')
        if stats.get('pathway_local_gap_fill_actual',0.0) < self.r.local_gap_fill_range[0]-0.015:
            raise RuntimeError('local-gap line coverage invariant not realized: '+str(stats.get('pathway_local_gap_fill_actual',0.0)))
        if len(self.chips)>1 and stats.get('pathway_cross_chip_connection_count',0)<1:
            raise RuntimeError('cross-chip connection invariant not realized')
        return groups,stats

# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

class V34Renderer:
    FG = "#e7e1d2"
    BG = "#101319"

    def __init__(self, W=1200, H=1200, seed: Optional[int]=None, main_scale: float=1.0):
        self.W=float(W); self.H=float(H)
        if not math.isfinite(float(main_scale)) or float(main_scale) <= 0:
            raise ValueError("main_scale must be a finite positive number")
        self.main_scale=float(main_scale)
        self.canvas_S=min(self.W,self.H)
        # V34 default physical scale is the former design system reduced from canvas/1200 to
        # canvas/1600.  Scale the *entire* design basis, not just U-derived strokes: S-derived
        # chips/collections and U-derived traces/spacing therefore shrink together by 0.75.
        # Chip-count probability remains canvas-population logic and is intentionally unchanged.
        self.S=self.canvas_S*self.main_scale*(1200.0/1600.0)
        self.U=self.S/1200.0
        self.seed = secrets.randbits(64) if seed is None else int(seed) & MASK64
        self.batch_fingerprints=set()
        self.batch_buckets: Dict[str,List[Dict[str,Any]]] = {}
        self.pathway_debug_stage=None
        # Placement/routing keep-outs. Route-first generation means secondary components do not exist while main
        # chip placement and pathway geometry are solved against chips only.  Secondary objects
        # are fitted afterward into the residual free field.
        self.chip_edge_clearance=120.0*self.U
        self.chip_chip_clearance=max(360.0*self.U,0.205*self.canvas_S)
        # Historical pre-route chip/secondary moat is retained as metadata only. The current renderer places
        # components after routing, so final component placement uses a smaller visual chip moat
        # plus exact pathway clearance instead of reserving a giant empty launch corridor.
        self.chip_secondary_clearance=170.0*self.U
        self.component_chip_clearance=42.0*self.U
        self.component_pathway_clearance=10.0*self.U
        self.component_component_clearance=12.0*self.U
        self.component_edge_clearance=20.0*self.U
        self.residual_gap_fill_range=(0.90,0.94)
        self.component_extra_filler_limit=36
        self.component_density_cap=58
        self.component_pathway_attachment_probability=0.24
        self.pathway_static_keepout=8.0*self.U
        # V21: main chips get a routing halo three times the ordinary static keepout.
        self.pathway_main_chip_keepout=24.0*self.U
        self.pathway_interroute_keepout=1.25*self.U
        self.pathway_terminal_head_keepout=4.5*self.U
        self.local_gap_fill_range=(0.42,0.50)
        self.local_gap_grid_n=28
        self.local_gap_bundle_probability=0.50
        self.local_gap_branch_boost_range=(3.0,5.0)
        self.local_gap_exit_probability_factor=0.50
        self.termination_dot_scale=2.0
        self.termination_dot_hollow_stroke=2.70*self.U
        self.termination_dot_min_gap=1.0*self.U
        self.local_gap_special_thickness_range=(5.0,8.0)
        self.local_gap_special_hole_radius_ratio=0.22
        # V24: source dots/lines begin three times farther from the chip than V23.
        self.pathway_chip_launch_gap=22.5*self.U

    def _termination_dot_radius(self, thickness:float):
        return self.termination_dot_scale*max(1.35*self.U,.80*thickness+.35*self.U)

    # ------------------------------ distributions -------------------------
    def chip_count(self, rng): return 2 if rng.random() < 0.90 else 3
    def collection_count(self, rng):
        return rng.weighted([(15,.20),(16,.30),(17,.30),(18,.20)])

    def _sample_range(self,rng,a,b): return rng.uniform(a*self.U,b*self.U)

    def _center01(self, rng, draws=2):
        return sum(rng.random() for _ in range(draws)) / draws

    def _bounded_int(self, rng, lo, hi, power=1.0):
        if hi <= lo:
            return int(lo)
        u = rng.random() ** power
        return min(int(hi), int(lo) + int((int(hi)-int(lo)+1) * u))

    def _procedural_dims(self, rng, long_min, long_max, short_max, cell_cap, long_power=0.70, short_power=1.85):
        """Generate integer grid dimensions from continuous extent + anisotropy drivers.

        No shape list is sampled. The long dimension is drawn over a bounded range; the short
        dimension is independently drawn with a strong low-side bias, then constrained by the
        total-cell cap. A final transpose draw removes directional bias.
        """
        long_dim = self._bounded_int(rng, long_min, long_max, power=long_power)
        short_cap = max(1, min(int(short_max), int(long_dim), int(cell_cap)//max(1,int(long_dim))))
        short_dim = self._bounded_int(rng, 1, short_cap, power=short_power)
        if rng.random() < 0.5:
            return int(short_dim), int(long_dim)
        return int(long_dim), int(short_dim)

    # ------------------------------ main chips ----------------------------
    def generate_chip(self, base_seed: int, idx: int) -> Group:
        # preserve requested regeneration behavior by deriving retry streams from chip seed
        for attempt in range(128):
            rng=SplitMix64(retry_seed(base_seed, attempt) if attempt else base_seed)
            g=self._generate_chip_once(rng, idx)
            if g is not None:
                return g
        raise RuntimeError("chip regeneration limit exceeded")

    def _generate_chip_once(self, rng: SplitMix64, idx: int) -> Optional[Group]:
        S,U=self.S,self.U
        # Continuous, center-biased chip scale; no low/medium/high size bins.
        q=(.078*S)+(.105*S-.078*S)*self._center01(rng,2)
        # Continuous aspect driver, mildly biased toward elongation without named aspect modes.
        for _ in range(128):
            A=1.20+(1.67-1.20)*(rng.random()**0.82); long=q*A
            if .110*S <= long <= .151*S: break
        else: return None
        orient="horizontal" if rng.random()<.67 else "vertical"
        w,h=(long,q) if orient=="horizontal" else (q,long)
        rounded=rng.random()<.85
        rx=rng.uniform(2.1*U,2.7*U) if rounded else 0.0
        body=prim_rect_outline(0,0,w,h,rx,3.2*U,self.FG)

        motif_complexity=self._center01(rng,2)
        mcount=1+min(3,int(4*(motif_complexity**0.90)))
        weights={"M1":1.00,"M2":.72,"M3":.78,"M4":.52,"M5":.52,"M6":.68,"M7":.62,"M8":.78}
        motifs=[]
        pool=dict(weights)
        central=set()
        while len(motifs)<mcount and pool:
            m=rng.weighted(list(pool.items())); del pool[m]
            if m in ("M2","M3","M7") and central:
                continue
            motifs.append(m)
            if m in ("M2","M3","M7"): central.add(m)
        if mcount>=2 and not any(m in motifs for m in ("M1","M2","M3","M7")):
            # replace lowest-weight exterior motif
            lowest=min(range(len(motifs)), key=lambda i: weights[motifs[i]])
            avail=[m for m in ("M1","M2","M3","M7") if m not in motifs]
            motifs[lowest]=rng.weighted([(m,weights[m]) for m in avail])

        groups={"body":Group("body",[body])}
        inner_count=0
        last_inset=None
        if "M1" in motifs:
            inner_count=1
            if rng.random()<.45:
                inner_count=2
                if rng.random()<(0.10/0.45):
                    inner_count=3
            inset1=rng.uniform(12*U,15*U); step=rng.uniform(8*U,11*U)
            ps=[]
            outer_short=min(w,h)
            for i in range(inner_count):
                ins=inset1+i*step; last_inset=ins
                iw,ih=w-2*ins,h-2*ins
                if iw<=0 or ih<=0: return None
                irx=0 if rx==0 else rx*(min(iw,ih)/outer_short)
                ps.append(prim_rect_outline(0,0,iw,ih,irx,1.9*U,self.FG))
            groups["M1"]=Group("M1",ps)
        safe_inset=(last_inset+rng.uniform(9*U,12*U)) if last_inset is not None else rng.uniform(18*U,22*U)
        sw=w-2*safe_inset; sh=h-2*safe_inset
        if sw<=0 or sh<=0: return None

        if "M2" in motifs:
            typ=rng.weighted([("filled_grid",.50),("dotted_perimeter_rectangle",.25),("compact_matrix",.25)])
            r=rng.uniform(1.8*U,2.5*U)
            if typ=="compact_matrix":
                px=10*U+4*U*(rng.random()**2.50); py=10*U+4*U*(rng.random()**2.50)
            else:
                px=rng.uniform(10*U,14*U); py=rng.uniform(10*U,14*U)
            max_cols=max(1,math.floor((sw-2*r)/px)+1); max_rows=max(1,math.floor((sh-2*r)/py)+1)
            if max_cols<1 or max_rows<1: return None
            rows=self._bounded_int(rng,1,max_rows,power=1.25)
            cols=self._bounded_int(rng,1,max_cols,power=0.85)
            pts=[]
            for rr in range(rows):
                for cc in range(cols):
                    if typ=="dotted_perimeter_rectangle" and rows>1 and cols>1 and rr not in (0,rows-1) and cc not in (0,cols-1):
                        continue
                    # "compact_matrix" uses the same authorized lattice parameters; no new geometry invented.
                    x=(cc-(cols-1)/2)*px; y=(rr-(rows-1)/2)*py
                    pts.append(prim_circle(x,y,r,self.FG,True))
            groups["M2"]=Group("M2",pts)

        if "M3" in motifs:
            horizontal=rng.random()<.5
            dl=rng.uniform(8*U,13*U); pitch=dl+rng.uniform(5*U,8*U); bp=rng.uniform(11*U,18*U); thick=3.2*U
            max_marks=max(1,math.floor(((sw if horizontal else sh)-dl)/pitch)+1)
            max_bands=max(1,math.floor(((sh if horizontal else sw)-thick)/bp)+1)
            marks=self._bounded_int(rng,1,max_marks,power=.80)
            bands=self._bounded_int(rng,1,max_bands,power=1.15)
            def fits(b,m):
                pw=(m-1)*pitch+dl if horizontal else (b-1)*bp+thick
                ph=(b-1)*bp+thick if horizontal else (m-1)*pitch+dl
                return pw<=sw and ph<=sh
            while marks>1 and not fits(bands,marks): marks-=1
            while bands>1 and not fits(bands,marks): bands-=1
            if not fits(bands,marks): return None
            ps=[]
            for b in range(bands):
                for m in range(marks):
                    if horizontal:
                        cx=(m-(marks-1)/2)*pitch; cy=(b-(bands-1)/2)*bp
                        ps.append(prim_line(cx-dl/2,cy,cx+dl/2,cy,thick,self.FG))
                    else:
                        cx=(b-(bands-1)/2)*bp; cy=(m-(marks-1)/2)*pitch
                        ps.append(prim_line(cx,cy-dl/2,cx,cy+dl/2,thick,self.FG))
            groups["M3"]=Group("M3",ps)

        if "M7" in motifs:
            typ=rng.weighted([("hollow_pads",.40),("filled_dots",.30),("short_lines",.30)])
            px=rng.uniform(10*U,13*U); py=rng.uniform(9*U,12*U)
            max_cols=max(1,math.floor(sw/px)+1); max_rows=max(1,math.floor(sh/py)+1)
            rows=self._bounded_int(rng,1,max_rows,power=1.25)
            cols=self._bounded_int(rng,1,max_cols,power=.90)
            line_horizontal=(rng.random()<.5) if typ=="short_lines" else True
            ps=[]
            for rr in range(rows):
                for cc in range(cols):
                    x=(cc-(cols-1)/2)*px; y=(rr-(rows-1)/2)*py
                    if typ=="hollow_pads":
                        side=rng.uniform(4.5*U,6.5*U)
                        ps.append(prim_rect_outline(x,y,side,side,0,1.8*U,self.FG))
                    elif typ=="filled_dots":
                        ps.append(prim_circle(x,y,rng.uniform(1.5*U,2.0*U),self.FG,True))
                    else:
                        ln=rng.uniform(6*U,9*U)
                        ps.append(prim_line(x-ln/2,y,x+ln/2,y,2.1*U,self.FG) if line_horizontal else prim_line(x,y-ln/2,x,y+ln/2,2.1*U,self.FG))
            gg=Group("M7",ps)
            bx=gg.bounds
            if bx[0]<-sw/2 or bx[2]>sw/2 or bx[1]<-sh/2 or bx[3]>sh/2: return None
            groups["M7"]=gg

        if "M4" in motifs:
            r=rng.uniform(2.5*U,3.1*U); adx=rng.uniform(7.8*U,9.2*U); ady=rng.uniform(7.8*U,9.2*U)
            ps=[]
            for ox,oy in [(-1,-1),(1,-1),(1,1),(-1,1)]:
                cx=ox*w/2 + ox*adx; cy=oy*h/2 + oy*ady
                ps.append(prim_circle(cx,cy,r,self.FG,True))
            groups["M4"]=Group("M4",ps)

        if "M5" in motifs:
            area_scale=math.sqrt(w*h)
            stand_off=rng.uniform(.024*area_scale,.040*area_scale)
            d=rng.uniform(.054*q,.070*q); k=rng.uniform(.30,.54); ps=[]
            for ox,oy in [(-1,-1),(1,-1),(1,1),(-1,1)]:
                cx=ox*w/2; cy=oy*h/2
                ax=cx+ox*stand_off; ay=cy+oy*stand_off
                ph=(ax-ox*d,ay+oy*d); pv=(ax+ox*d,ay-oy*d); qq=(ax+ox*k*d,ay+oy*k*d)
                ps.append(prim_quadratic(ph,qq,pv,1.9*U,self.FG,U))
            groups["M5"]=Group("M5",ps)

        def side_set():
            mode=rng.weighted([("one",.25),("opposite",.50),("all",.25)])
            if mode=="one":
                return mode,[rng.weighted([(s,.25) for s in ("top","bottom","left","right")])]
            if mode=="opposite":
                return (mode,["top","bottom"]) if rng.random()<.5 else (mode,["left","right"])
            return mode,["top","bottom","left","right"]

        m6_side_mode=None; m8_side_mode=None
        if "M6" in motifs:
            m6_side_mode,sides=side_set(); ps=[]
            for s in sides:
                gap=rng.uniform(8*U,11*U); frac=rng.uniform(.40,.65)
                side_len=w if s in ("top","bottom") else h
                span=frac*side_len
                for _ in range(128):
                    dl=rng.uniform(7*U,12*U); th=2.8*U; cg=rng.uniform(1.5,3.0)*th
                    n=math.floor((span+cg)/(dl+cg))
                    if n>=3: break
                else: return None
                total=(n-1)*(dl+cg)+dl
                for i in range(n):
                    pos=(i-(n-1)/2)*(dl+cg)
                    if s=="top": y=-h/2-gap; ps.append(prim_line(pos-dl/2,y,pos+dl/2,y,th,self.FG))
                    elif s=="bottom": y=h/2+gap; ps.append(prim_line(pos-dl/2,y,pos+dl/2,y,th,self.FG))
                    elif s=="left": x=-w/2-gap; ps.append(prim_line(x,pos-dl/2,x,pos+dl/2,th,self.FG))
                    else: x=w/2+gap; ps.append(prim_line(x,pos-dl/2,x,pos+dl/2,th,self.FG))
            groups["M6"]=Group("M6",ps)

        if "M8" in motifs:
            # If M6 active, side set retry up to 32; geometry is regenerated if necessary by whole-chip retry.
            m8_group=None
            for ss_attempt in range(32):
                m8_side_mode,sides=side_set(); ps=[]
                for s in sides:
                    ngap=rng.uniform(6*U,8*U); dl=rng.uniform(7*U,10*U); th=2.8*U
                    # Continuous span and packing distributions. Exponents are calibrated so
                    # about 75% of draws land in the formerly "long" / "tight" regions.
                    frac=.35+.55*(rng.random()**.326)
                    side_len=w if s in ("top","bottom") else h
                    span=frac*side_len
                    for _ in range(128):
                        gap_mult=1.0+3.0*(rng.random()**3.82)
                        cg=gap_mult*th
                        pitch=th+cg; n=math.floor((span-th)/pitch)+1
                        if n>=4: break
                    else: return None
                    for i in range(n):
                        pos=(i-(n-1)/2)*pitch
                        if s=="top": ps.append(prim_line(pos,-h/2-ngap,pos,-h/2-ngap-dl,th,self.FG))
                        elif s=="bottom": ps.append(prim_line(pos,h/2+ngap,pos,h/2+ngap+dl,th,self.FG))
                        elif s=="left": ps.append(prim_line(-w/2-ngap,pos,-w/2-ngap-dl,pos,th,self.FG))
                        else: ps.append(prim_line(w/2+ngap,pos,w/2+ngap+dl,pos,th,self.FG))
                cand=Group("M8",ps)
                if "M6" not in groups or not groups["M6"].geom.intersects(cand.geom):
                    m8_group=cand; break
            if m8_group is None: return None
            groups["M8"]=m8_group

        # Internal collision audit between unrelated motif groups; body is unrelated to exterior ornaments.
        # Central motifs are already constrained by safe rect. Nested M1/body relationship is intentional.
        keys=[k for k in groups if k not in ("body","M1")]
        for i,a in enumerate(keys):
            for b in keys[i+1:]:
                ga,gb=groups[a].geom,groups[b].geom
                if ga.intersects(gb) or ga.distance(gb) < 6*U:
                    return None
        for k in ("M4","M5","M6","M8"):
            if k in groups and groups[k].geom.intersects(groups["body"].geom):
                return None

        prims=[]
        for k in ["body","M1","M2","M3","M7","M4","M5","M6","M8"]:
            if k in groups: prims.extend(groups[k].primitives)
        aspect_signature=round(A/0.04)*0.04
        structural=dict(kind="chip",orientation=orient,aspect_bin=aspect_signature,motifs=tuple(sorted(motifs)),inner_border_count=inner_count,
                        exterior_side_set_configuration=(m6_side_mode,m8_side_mode),q_chip=q,width=w,height=h)
        return Group(f"chip-{idx}",prims,structural)

    # ------------------------------ collections ---------------------------
    def largest_remainder(self, N, fracs):
        raw=[N*f for f in fracs]; floors=[math.floor(x) for x in raw]; rem=N-sum(floors)
        order=sorted(range(len(fracs)), key=lambda i: (-(raw[i]-floors[i]), i))
        for i in order[:rem]: floors[i]+=1
        return floors

    def assign_collection_families(self, rng: SplitMix64, N: int):
        # Special-family occurrence remains quota-controlled; combination richness is now
        # derived from a continuous latent complexity variable instead of tier/archetype quotas.
        Nic=round(.625*N); Nd=round(.845*N); Nb=round(.700*N)
        ids=list(range(N)); rng.shuffle(ids); ic=set(ids[:Nic])
        ids=list(range(N)); rng.shuffle(ids); dense=set(ids[:Nd])
        ids=list(range(N)); rng.shuffle(ids); border=set(ids[:Nb])

        # Continuous per-collection complexity -> integer family count 1..5.
        # The exponent preserves a strong 1–3 family center while allowing richer tails.
        family_counts=[]
        complexity=[]
        for i in range(N):
            c=self._center01(rng,2)
            complexity.append(c)
            fc=1+min(4,int(5*(c**1.50)))
            family_counts.append(fc)

        # Required special families are conditional lower bounds on family count.
        for i in range(N):
            required=int(i in ic)+int(i in dense)
            family_counts[i]=max(family_counts[i],required,1)
            # With exact special quotas, an all-ordinary collection can contain at most five
            # distinct ordinary labels; no extra special family may be invented by filler.
            if required==0:
                family_counts[i]=min(family_counts[i],5)

        # Enforce the established mixing rates by promoting complexity only where needed.
        def promote_mixed(flagset, need):
            mixed=[i for i in flagset if family_counts[i]>=2]
            missing=max(0,need-len(mixed))
            if missing:
                candidates=[i for i in flagset if family_counts[i]<2]
                rng.shuffle(candidates)
                for i in candidates[:missing]: family_counts[i]=2
        promote_mixed(ic,math.ceil(.85*Nic))
        promote_mixed(dense,math.ceil(.70*Nd))

        assigns=[]
        for i in range(N):
            fam=[]
            if i in ic: fam.append("ic")
            if i in dense: fam.append("dense")
            remaining=family_counts[i]-len(fam)
            pool={"square":1.0,"circle":1.0,"capacitor_circle":3.90,"dot":1.0,"dash":1.0}
            if remaining>len(pool):
                return None,None
            while remaining>0:
                x=rng.weighted(list(pool.items())); fam.append(x); del pool[x]; remaining-=1
            assigns.append(dict(families=fam,border=i in border,family_count=family_counts[i],complexity=complexity[i],tier=family_counts[i]))

        # Ordinary coverage min 2; preserve family count and exact special quotas.
        for target in ("square","circle","dot","dash"):
            while sum(target in a["families"] for a in assigns)<2:
                eligible=[]
                for i,a in enumerate(assigns):
                    if target in a["families"]: continue
                    replaceable=[f for f in a["families"] if f in ("square","circle","dot","dash") and sum(f in aa["families"] for aa in assigns)>2]
                    if replaceable: eligible.append((i,replaceable))
                if not eligible: break
                rng.shuffle(eligible); i,opts=eligible[0]; rng.shuffle(opts); old=opts[0]
                assigns[i]["families"][assigns[i]["families"].index(old)]=target
        # Coverage is a generation invariant, so reject this cheap assignment immediately if
        # the bounded swap pass cannot realize it.  Never discover this after routing.
        if any(sum(target in a["families"] for a in assigns)<2 for target in ("square","circle","dot","dash")):
            return None,None
        return assigns,dict(N_ic=Nic,N_dense=Nd,N_border=Nb)

    def ordinary_points(self,rng,count,Pord):
        lattice=rng.weighted([("orthogonal_strip",.35),("orthogonal_grid",.35),("diagonal_grid",.20),("staggered_grid",.10)])
        px=Pord*rng.uniform(.90,1.10); py=Pord*rng.uniform(.90,1.10)
        pts=[]
        if lattice=="orthogonal_strip":
            horiz=rng.random()<.5
            for i in range(count):
                pts.append(((i-(count-1)/2)*px,0) if horiz else (0,(i-(count-1)/2)*py))
        else:
            # Grid dimensions are derived from count + a continuous anisotropy driver.
            anis=1.0+2.5*(rng.random()**0.80)
            rows=max(1,round(math.sqrt(count/anis)))
            cols=max(1,math.ceil(count/rows))
            if rng.random()<.5: rows,cols=cols,rows
            base=[]
            for k in range(count):
                rr=k//cols; cc=k%cols
                base.append(((cc-(cols-1)/2)*px,(rr-(rows-1)/2)*py,rr))
            if lattice=="orthogonal_grid": pts=[(x,y) for x,y,_ in base]
            elif lattice=="staggered_grid": pts=[(x+(0.5*px if rr%2 else 0),y) for x,y,rr in base]
            else:
                ang=math.pi/4; ca,sa=math.cos(ang),math.sin(ang)
                pts=[(x*ca-y*sa,x*sa+y*ca) for x,y,_ in base]
        return lattice,pts

    def _capacitor_entity_primitives(self, rng, x=0.0, y=0.0):
        U=self.U
        r=(6.3 + 13.05*(rng.random()**0.90))*U
        state=rng.weighted([("filled",.32),("hollow",.28),("concentric",.40)])
        ps=[]; inner_count=0
        if state=="filled":
            ps.append(prim_circle(x,y,r,self.FG,True))
        elif state=="hollow":
            ps.append(prim_circle(x,y,r,self.FG,False,1.8*U))
        else:
            ps.append(prim_circle(x,y,r,self.FG,False,1.8*U))
            inner_count=1 + min(2, int(3*(rng.random()**0.82)))
            # Derive all ring positions from available radius; spacing stays positive after stroke expansion.
            inner_min=max(1.3*U, r*0.24)
            inner_max=max(inner_min+0.2*U, r-2.4*U)
            for k in range(inner_count):
                t=(k+1)/(inner_count+1)
                rr=inner_max*(1-t) + inner_min*t
                ps.append(prim_circle(x,y,rr,self.FG,False,1.45*U))
        return ps, dict(capacitor_radius=r,capacitor_state=state,capacitor_inner_ring_count=inner_count)

    def make_ordinary_subgroup(self,rng,fam,Pord):
        # Capacitor-circle is singleton-only. It never enters strip/grid/lattice generation.
        if fam=="capacitor_circle":
            ps,meta=self._capacitor_entity_primitives(rng,0.0,0.0)
            return Group("capacitor_circle",ps,dict(family="capacitor_circle",lattice="singleton",entity_count=1,capacitor_entities=[meta],**meta))

        # Other ordinary families derive population count procedurally.
        count=2+min(5,int(6*self._center01(rng,2)))
        lattice,pts=self.ordinary_points(rng,count,Pord); U=self.U; ps=[]
        if fam in ("square","circle"):
            mode=rng.weighted([("hollow",.40),("filled",.35),("mixed",.25)])
            if mode=="mixed": mixmode="alternating" if rng.random()<.60 else "accent"
            else: mixmode=None
            accent_idx=int(rng.random()*count) if mixmode=="accent" else -1
            for i,(x,y) in enumerate(pts):
                filled=(mode=="filled") or (mode=="mixed" and ((mixmode=="alternating" and i%2==0) or (mixmode=="accent" and i==accent_idx)))
                if fam=="square":
                    side=rng.uniform(6*U,9*U)
                    ps.append(prim_rect_fill(x,y,side,side,0,self.FG) if filled else prim_rect_outline(x,y,side,side,0,1.8*U,self.FG))
                else:
                    r=rng.uniform(2.5*U,4.5*U); ps.append(prim_circle(x,y,r,self.FG,filled,1.8*U))
        elif fam=="dot":
            for x,y in pts:
                # One continuous heavy-low-tail radius distribution replaces standard/accent modes.
                r=(2.1+2.9*(rng.random()**4.35))*U
                ps.append(prim_circle(x,y,r,self.FG,True))
        else:
            for x,y in pts:
                ln=rng.uniform(7*U,12*U); th=2.1*U
                if lattice=="diagonal_grid": ori=rng.weighted([("diag",.60),("h",.20),("v",.20)])
                else: ori="h" if rng.random()<.5 else "v"
                if ori=="h": p=prim_line(x-ln/2,y,x+ln/2,y,th,self.FG)
                elif ori=="v": p=prim_line(x,y-ln/2,x,y+ln/2,th,self.FG)
                else:
                    a=math.pi/4 if rng.random()<.5 else -math.pi/4; dx=math.cos(a)*ln/2; dy=math.sin(a)*ln/2
                    p=prim_line(x-dx,y-dy,x+dx,y+dy,th,self.FG)
                ps.append(p)
        return Group(fam,ps,dict(family=fam,lattice=lattice,entity_count=count))

    def sample_ic_cell(self,rng,context):
        U=self.U; q=rng.uniform(10*U,14*U)
        # Continuous aspect distribution across the full allowed interval; no aspect bins.
        A=1.00+(1.85-1.00)*(rng.random()**0.95); horizontal=rng.random()<.5
        w,h=(q*A,q) if horizontal else (q,q*A)
        if context=="array_h": sides=["left","right"] if rng.random()<.60 else ["left","right","top","bottom"]
        elif context=="array_v": sides=["top","bottom"] if rng.random()<.60 else ["left","right","top","bottom"]
        elif context=="array_2d": sides=["left","right","top","bottom"]
        else:
            if rng.random()<.55: sides=["left","right"] if rng.random()<.5 else ["top","bottom"]
            else: sides=["left","right","top","bottom"]
        # Center-biased continuous terminal ratio on the full hard range; tails occur naturally.
        tl_ratio=.20+.20*self._center01(rng,2)
        tl=tl_ratio*q; tt=.18*q
        ps=[prim_rect_outline(0,0,w,h,1.2*U,1.8*U,self.FG)]
        terminal_tips={}
        for s in sides:
            L=h if s in ("left","right") else w; rho=L/q
            n=1 if rho<=1.15 else 2 if rho<=1.45 else 3
            for i in range(n):
                pos=((i+1)/(n+1)-.5)*L
                if s=="left":
                    p=prim_line(-w/2,pos,-w/2-tl,pos,tt,self.FG); tip=(-w/2-tl,pos)
                elif s=="right":
                    p=prim_line(w/2,pos,w/2+tl,pos,tt,self.FG); tip=(w/2+tl,pos)
                elif s=="top":
                    p=prim_line(pos,-h/2,pos,-h/2-tl,tt,self.FG); tip=(pos,-h/2-tl)
                else:
                    p=prim_line(pos,h/2,pos,h/2+tl,tt,self.FG); tip=(pos,h/2+tl)
                ps.append(p); terminal_tips.setdefault(s,[]).append(tip)
        aspect_signature=round(A/0.02)*0.02
        return Group("ic_cell",ps,dict(q=q,w=w,h=h,aspect_bin=aspect_signature,aspect_ratio=A,sides=tuple(sides),terminal_length=tl,terminal_thickness=tt,terminal_tips=terminal_tips))

    def make_ic_subgroup(self,rng):
        U=self.U
        # Occurrence form emerges from two conditional probability draws rather than a mode menu.
        # About 10% are singleton; among multi-IC occurrences, about 91% are connected.
        if rng.random()<.10:
            cell=self.sample_ic_cell(rng,"standalone")
            cell.structural.update(dict(family="ic",ic_mode="single",entity_count=1))
            return cell

        connected=rng.random()<.91
        if not connected:
            # Separate population is a bounded projection of a continuous count driver.
            n=2+self._bounded_int(rng,0,1,power=1.8)
            cells=[self.sample_ic_cell(rng,"standalone") for _ in range(n)]
            horizontal=rng.random()<.5
            ps=[]; dims=[]
            for c in cells:
                b=c.bounds; dims.append(bounds_w_h(b))
            gaps=[rng.uniform(4*U,8*U) for _ in range(n-1)]
            total=sum((d[0] if horizontal else d[1]) for d in dims)+sum(gaps)
            cur=-total/2
            for i,c in enumerate(cells):
                size=dims[i][0] if horizontal else dims[i][1]
                center=cur+size/2
                cc=c.transformed(center if horizontal else 0, 0 if horizontal else center)
                ps.extend(cc.primitives); cur += size + (gaps[i] if i<n-1 else 0)
            return Group("ic",ps,dict(family="ic",ic_mode="separate",entity_count=n))

        # Connected grid dimensions are procedural: broad long extent + independently sampled,
        # low-biased short extent. No rows×columns shape list exists.
        rows,cols=self._procedural_dims(rng,long_min=2,long_max=6,short_max=4,cell_cap=10,long_power=1.00,short_power=1.00)
        context="array_h" if rows==1 else "array_v" if cols==1 else "array_2d"
        cell=self.sample_ic_cell(rng,context); w=cell.structural["w"]; h=cell.structural["h"]; tl=cell.structural["terminal_length"]
        px=w+2*tl; py=h+2*tl; ps=[]; centers=[]
        for rr in range(rows):
            row=[]
            for cc in range(cols):
                x=(cc-(cols-1)/2)*px; y=(rr-(rows-1)/2)*py
                row.append((x,y)); ps.extend(cell.transformed(x,y).primitives)
            centers.append(row)
        failures=0; required_contacts=0; tips=cell.structural["terminal_tips"]
        if cols>1:
            if "left" not in tips or "right" not in tips or len(tips["left"])!=len(tips["right"]): failures+=1
            else:
                for rr in range(rows):
                    for cc in range(cols-1):
                        a=centers[rr][cc]; b=centers[rr][cc+1]
                        for rt,lt in zip(tips["right"],tips["left"]):
                            required_contacts+=1
                            pa=(a[0]+rt[0],a[1]+rt[1]); pb=(b[0]+lt[0],b[1]+lt[1])
                            if math.hypot(pa[0]-pb[0],pa[1]-pb[1])>1e-9: failures+=1
        if rows>1:
            if "top" not in tips or "bottom" not in tips or len(tips["top"])!=len(tips["bottom"]): failures+=1
            else:
                for rr in range(rows-1):
                    for cc in range(cols):
                        a=centers[rr][cc]; b=centers[rr+1][cc]
                        for bt,ttop in zip(tips["bottom"],tips["top"]):
                            required_contacts+=1
                            pa=(a[0]+bt[0],a[1]+bt[1]); pb=(b[0]+ttop[0],b[1]+ttop[1])
                            if math.hypot(pa[0]-pb[0],pa[1]-pb[1])>1e-9: failures+=1
        ratio=max(rows,cols)/min(rows,cols)
        shape_class="chain" if min(rows,cols)==1 else ("elongated" if ratio>=2.5 else "balanced")
        return Group("ic",ps,dict(family="ic",ic_mode="array",array_shape=(rows,cols),array_shape_class=shape_class,entity_count=rows*cols,
                                  aspect_bin=cell.structural["aspect_bin"],aspect_ratio=cell.structural["aspect_ratio"],terminal_sides=cell.structural["sides"],
                                  terminal_length_ratio=tl/cell.structural["q"],required_contact_count=required_contacts,
                                  required_contact_failure_count=failures))

    def make_dense_subgroup(self,rng,Pord):
        U=self.U
        # Procedural dimensions replace the rows×columns lookup table. Strong independent
        # anisotropy bias makes elongated chains/rectangles common while balanced grids remain possible.
        rows,cols=self._procedural_dims(rng,long_min=3,long_max=10,short_max=4,cell_cap=20,long_power=2.00,short_power=1.90)
        dense_mode=rng.weighted([("orthogonal",.50),("diamond_row",.25),("diamond_col",.25)])
        P=Pord*rng.uniform(.50,.70)
        for _ in range(128):
            r=rng.uniform(1.7*U,2.6*U)
            if 2*r+1*U<=P: break
        state=rng.weighted([("filled",.35),("hollow",.35),("mixed",.30)])
        pts=[]; half=.5*P
        for rr in range(rows):
            for cc in range(cols):
                x=(cc-(cols-1)/2)*P; y=(rr-(rows-1)/2)*P
                if dense_mode=="diamond_row": x += half if rr%2 else 0.0
                elif dense_mode=="diamond_col": y += half if cc%2 else 0.0
                filled=state=="filled" or (state=="mixed" and ((rr+cc)%2==0))
                pts.append(prim_circle(x,y,r,self.FG,filled,1.5*U if not filled else 0))
        dots=Group("dense_dots",pts)
        b=dots.bounds; pad=rng.uniform(6*U,9*U)
        bw=(b[2]-b[0])+2*pad; bh=(b[3]-b[1])+2*pad; cx,cy=bounds_center(b)
        border=prim_rect_outline(cx,cy,bw,bh,2*U,1.5*U,self.FG); pts.append(border)
        orient="orthogonal" if dense_mode=="orthogonal" else ("diamond-row-shift" if dense_mode=="diamond_row" else "diamond-col-shift")
        ratio=max(rows,cols)/min(rows,cols)
        dim_class="strip" if min(rows,cols)==1 else ("elongated" if ratio>=2.5 else "compact")
        return Group("dense",pts,dict(family="dense",dense_dims=(rows,cols),dense_dim_class=dim_class,dense_orientation=orient,dense_fill=state,entity_count=rows*cols))

    def plan_collection_candidate(self, base_seed: int, idx: int, assignment: Dict[str,Any], attempt: int):
        seed=retry_seed(base_seed,attempt) if attempt else base_seed
        with bounds_only_mode(True):
            g=self._make_collection_once(SplitMix64(seed),idx,assignment)
        if g is None:
            return None
        L=max(bounds_w_h(g.bounds))
        if not (.014*self.S <= L <= .096*self.S):
            return None
        g.structural["source_seed"]=seed
        g.structural["source_retry_index"]=attempt
        return g

    def first_valid_collection_plan(self, base_seed: int, idx: int, assignment: Dict[str,Any], max_attempts=256):
        for attempt in range(max_attempts):
            g=self.plan_collection_candidate(base_seed,idx,assignment,attempt)
            if g is not None:
                return g
        return None

    def make_collection(self, base_seed: int, idx: int, assignment: Dict[str,Any], fingerprint_register=True, planning=False):
        for attempt in range(256):
            seed=retry_seed(base_seed,attempt) if attempt else base_seed; rng=SplitMix64(seed)
            with bounds_only_mode(planning):
                g=self._make_collection_once(rng,idx,assignment)
            if g is None: continue
            L=max(bounds_w_h(g.bounds))
            if not (.014*self.S <= L <= .096*self.S): continue
            g.structural["source_seed"]=seed
            if fingerprint_register:
                fp,rec=self.collection_fingerprint(g)
                if fp in self.batch_fingerprints or self.near_duplicate(rec): continue
                self.batch_fingerprints.add(fp); self.register_record(rec)
                g.structural["fingerprint"]=fp
            return g
        raise RuntimeError("collection regeneration limit exceeded")

    def _make_collection_once(self,rng,idx,assignment):
        U=self.U; Pord=rng.uniform(9.5*U,13.0*U)
        fams=list(assignment["families"]); rng.shuffle(fams)
        subgroups=[]
        for f in fams:
            if f in ("square","circle","capacitor_circle","dot","dash"): sg=self.make_ordinary_subgroup(rng,f,Pord)
            elif f=="ic": sg=self.make_ic_subgroup(rng)
            else: sg=self.make_dense_subgroup(rng,Pord)
            subgroups.append(sg)
        first=subgroups[0]
        fcx,fcy=bounds_center(first.bounds)
        accepted=first.transformed(-fcx,-fcy)
        # Cache current AABB/geom; direct AABB scoring.
        for sg in subgroups[1:]:
            placed=None; best_score=None; best_idx=None
            for round_idx in range(8):
                candidates=[]
                Cb=accepted.bounds; Gb=sg.bounds; ccx,ccy=bounds_center(Cb); gcx,gcy=bounds_center(Gb)
                cw,ch=bounds_w_h(Cb); gw,gh=bounds_w_h(Gb)
                for j in range(64):
                    theta=rng.uniform(0,2*math.pi); ca=abs(math.cos(theta)); sa=abs(math.sin(theta))
                    # Directional support radii of the two AABBs along the sampled separation axis.
                    # A center separation of support_C + support_G + gap guarantees a separating
                    # hyperplane with at least that gap, without the old half-diagonal over-spacing.
                    support_c=.5*(ca*cw+sa*ch); support_g=.5*(ca*gw+sa*gh)
                    d=support_c+support_g+rng.uniform(3*U,8*U)
                    target_x=ccx+d*math.cos(theta); target_y=ccy+d*math.sin(theta)
                    tx=target_x-gcx; ty=target_y-gcy
                    candidates.append((j,tx,ty))
                for j,tx,ty in candidates:
                    gb=(Gb[0]+tx,Gb[1]+ty,Gb[2]+tx,Gb[3]+ty); B=bounds_union(Cb,gb); w,h=bounds_w_h(B)
                    score=w*h+.15*(2*w+2*h)**2
                    if best_score is None or score<best_score or (score==best_score and j<best_idx):
                        best_score=score; best_idx=j; placed=sg.transformed(tx,ty)
                if placed is not None: break
            if placed is None: return None
            accepted=Group("collection_content",accepted.primitives+placed.primitives,
                           dict(accepted.structural))
        # recenter
        cx,cy=bounds_center(accepted.bounds); accepted=accepted.transformed(-cx,-cy)
        if assignment["border"]:
            b=accepted.bounds; pad=rng.uniform(7*U,11*U); border_stroke=1.5*U
            centerline_pad=pad+border_stroke/2
            bw=(b[2]-b[0])+2*centerline_pad; bh=(b[3]-b[1])+2*centerline_pad
            border=prim_rect_outline(0,0,bw,bh,rng.uniform(1*U,2*U),border_stroke,self.FG)
            accepted=Group("collection_content",accepted.primitives+[border])
        accepted=accepted.transformed(scale=.780,name=f"collection-{idx}")
        # store structural info needed for quotas/fingerprints
        structural=dict(kind="collection",families=tuple(sorted(assignment["families"])),border=assignment["border"],tier=assignment["tier"],Pord=Pord)
        for sg in subgroups:
            structural.setdefault("subgroups",[]).append(dict(sg.structural))
        accepted.structural=structural
        return accepted

    # ------------------------------ fingerprints -------------------------
    def structural_bucket_key(self,g:Group):
        s=g.structural
        subs=s.get("subgroups",[])
        key=dict(families=s.get("families"),border=s.get("border"),
                 subgroups=[{k:v for k,v in sg.items() if k in ("family","lattice","entity_count","ic_mode","array_shape","aspect_bin","terminal_sides","dense_dims","dense_orientation","dense_fill")} for sg in subs])
        return json.dumps(key,sort_keys=True,default=list)

    def collection_fingerprint(self,g:Group):
        b=g.bounds; w=b[2]-b[0]; h=b[3]-b[1]
        prims=[]
        for p in g.primitives:
            sb=p.signature; cx=(sb.get("cx",0)-b[0])/w if w else 0; cy=(sb.get("cy",0)-b[1])/h if h else 0
            pw=sb.get("w",0)/w if w else 0; ph=sb.get("h",0)/h if h else 0
            prims.append((sb.get("kind",p.kind),round(cx/0.02)*0.02,round(cy/0.02)*0.02,round(pw/0.02)*0.02,round(ph/0.02)*0.02))
        structural=[]
        for sg in g.structural.get("subgroups",[]):
            d={k:sg.get(k) for k in ("family","lattice","entity_count","ic_mode","array_shape","aspect_bin","terminal_sides","dense_dims","dense_orientation","dense_fill") if k in sg}
            if "terminal_length_ratio" in sg: d["terminal_length_ratio"]=round(sg["terminal_length_ratio"]/0.01)*0.01
            structural.append(d)
        base=dict(families=g.structural.get("families"),border=g.structural.get("border"),subgroups=structural)
        sigs=[]; transformed_records=[]
        for refl in (False,True):
            for rot in range(4):
                arr=[]
                for kind,x,y,pw,ph in prims:
                    xx,yy=x,y; ww,hh=pw,ph
                    if refl: xx=1-xx
                    for _ in range(rot): xx,yy=1-yy,xx; ww,hh=hh,ww
                    arr.append((kind,round(xx,4),round(yy,4),round(ww,4),round(hh,4)))
                arr.sort()
                payload=json.dumps(dict(base=base,prims=arr),sort_keys=True,default=list,separators=(",",":"))
                sigs.append(payload); transformed_records.append(arr)
        canonical=min(sigs); fp=hashlib.sha256(canonical.encode()).hexdigest()
        rec=dict(bucket=self.structural_bucket_key(g),transforms=transformed_records,base=base)
        return fp,rec

    def records_near_duplicate(self, rec, old):
        if rec["bucket"] != old["bucket"]:
            return False
        best_pos=best_size=float("inf")
        for arr in rec["transforms"]:
            for barr in old["transforms"]:
                if len(arr)!=len(barr) or not arr:
                    continue
                if any(a[0]!=b[0] for a,b in zip(arr,barr)):
                    continue
                pos=math.sqrt(sum((a[1]-b[1])**2+(a[2]-b[2])**2 for a,b in zip(arr,barr))/(2*len(arr)))
                size=math.sqrt(sum((a[3]-b[3])**2+(a[4]-b[4])**2 for a,b in zip(arr,barr))/(2*len(arr)))
                if pos<best_pos:
                    best_pos,best_size=pos,size
        return best_pos<.05 and best_size<.05

    def near_duplicate(self,rec):
        return any(self.records_near_duplicate(rec,old) for old in self.batch_buckets.get(rec["bucket"],[]))

    def register_record(self,rec): self.batch_buckets.setdefault(rec["bucket"],[]).append(rec)

    def generate_isolated_capacitors(self, sseed: int):
        rng=SplitMix64(isolated_capacitor_seed(sseed))
        # V23: isolated-capacitor occurrence was already 72%; tripling saturates at 100%.
        # Keep count variance unchanged while making the occurrence path unconditional.
        if rng.random() >= 1.0:
            return []
        count=1 + min(2, int(3*(rng.random()**1.10)))
        out=[]
        for i in range(count):
            ps,meta=self._capacitor_entity_primitives(rng,0.0,0.0)
            out.append(Group(f"isolated-capacitor-{i}",ps,dict(family="capacitor_circle",entity_count=1,isolated=True,**meta)))
        return out

    # ------------------------------ pathways ----------------------------
    def _path_bundle_thicknesses(self, rng, count:int):
        U=self.U
        # V20 doubles V19's trace gauge.  The rare emphasis trace is doubled as well.
        th=[rng.uniform(2.00*U,3.10*U) for _ in range(count)]
        if count and rng.random()<0.18:
            idx=int(rng.random()*count)
            th[idx]=rng.uniform(5.0*U,7.4*U)
            for j in range(count):
                if j!=idx and rng.random()<(0.008 if count>=6 else 0.015):
                    th[j]=rng.uniform(4.8*U,6.8*U)
        return th

    def _chip_body_rect(self, chip:Group):
        # First primitive is the main chip body in this renderer.
        body=chip.primitives[0].svg
        return body['cx'],body['cy'],body['width'],body['height']

    def _chip_launch_bundle(self, chip:Group, side:str, rng):
        U=self.U
        b=chip.bounds
        body_cx,body_cy,body_w,body_h=self._chip_body_rect(chip)
        side_span=body_w if side in ('top','bottom') else body_h
        usable=side_span*rng.uniform(0.72,0.90)

        # V20 doubles stroke width and defines lane separation from the visible stroke itself:
        # edge-to-edge gap aims at ~1.5x the adjacent pair's mean stroke width.  Because the
        # launch bus is uniform-pitch, a rare emphasis trace sets the minimum safe pitch for
        # that side rather than being allowed to visually merge with its neighbour.
        nominal_t=2.55*U
        nominal_pitch=2.5*nominal_t
        count=max(8,min(34,int(round(usable/max(nominal_pitch,1e-9)))+1))
        while True:
            thicks=self._path_bundle_thicknesses(rng,count)
            required=0.0
            for a,bw in zip(thicks,thicks[1:]):
                mean_t=.5*(a+bw)
                line_pitch=.5*(a+bw)+1.5*mean_t
                # V21 termination dots are 2x larger.  Preserve enough lane pitch that a rare
                # whole-bundle termination can place adjacent dots without overlap while still
                # keeping the ordinary visible line gap at >=1.5x mean stroke thickness.
                outer_a=self._termination_dot_radius(a)+.5*self.termination_dot_hollow_stroke
                outer_b=self._termination_dot_radius(bw)+.5*self.termination_dot_hollow_stroke
                dot_pitch=outer_a+outer_b+self.termination_dot_min_gap
                required=max(required,line_pitch,dot_pitch)
            if count<=2 or required*(count-1)<=usable+1e-7:
                break
            count-=1
        spacing=usable/(count-1) if count>1 else usable
        starts=[]
        if side in ('top','bottom'):
            y=b[1]-self.pathway_chip_launch_gap if side=='top' else b[3]+self.pathway_chip_launch_gap
            for i in range(count):
                off=(i-(count-1)/2.0)*spacing
                starts.append((body_cx+off,y))
        else:
            x=b[2]+self.pathway_chip_launch_gap if side=='right' else b[0]-self.pathway_chip_launch_gap
            for i in range(count):
                off=(i-(count-1)/2.0)*spacing
                starts.append((x,body_cy+off))
        return starts,SIDE_TO_DIR[side],spacing,thicks,side_span

    def _collection_anchor(self, g:Group, from_pt:Tuple[float,float], rng)->Tuple[float,float]:
        b=g.bounds; U=self.U
        cx,cy=bounds_center(b)
        dirs=[('left', abs(from_pt[0]-b[0])+abs(from_pt[1]-cy)),('right', abs(from_pt[0]-b[2])+abs(from_pt[1]-cy)),('top', abs(from_pt[0]-cx)+abs(from_pt[1]-b[1])),('bottom', abs(from_pt[0]-cx)+abs(from_pt[1]-b[3]))]
        side=min(dirs,key=lambda x:x[1])[0]
        gap=rng.uniform(8*U,14*U)
        if side=='left': return (b[0]-gap, cy+rng.uniform(-0.18*(b[3]-b[1]),0.18*(b[3]-b[1])))
        if side=='right': return (b[2]+gap, cy+rng.uniform(-0.18*(b[3]-b[1]),0.18*(b[3]-b[1])))
        if side=='top': return (cx+rng.uniform(-0.18*(b[2]-b[0]),0.18*(b[2]-b[0])), b[1]-gap)
        return (cx+rng.uniform(-0.18*(b[2]-b[0]),0.18*(b[2]-b[0])), b[3]+gap)

    def _forward_room(self, pts, dir_idx:int):
        U=self.U
        vx,vy=dir_vec(dir_idx)
        lim=[]
        for x,y in pts:
            vals=[]
            if vx>1e-9: vals.append((self.W-12*U-x)/vx)
            elif vx<-1e-9: vals.append((12*U-x)/vx)
            if vy>1e-9: vals.append((self.H-12*U-y)/vy)
            elif vy<-1e-9: vals.append((12*U-y)/vy)
            vals=[v for v in vals if v>=0]
            lim.append(min(vals) if vals else 1e9)
        return min(lim) if lim else 1e9

    def _distant_board_goal(self, from_pt, rng):
        U=self.U
        min_d=0.34*math.hypot(self.W, self.H)
        for _ in range(20):
            p=(rng.uniform(24*U,self.W-24*U), rng.uniform(24*U,self.H-24*U))
            if math.hypot(p[0]-from_pt[0], p[1]-from_pt[1]) >= min_d:
                return p
        # fallback: opposite-side quadrant style point
        x = self.W-rng.uniform(24*U, 0.25*self.W) if from_pt[0] < self.W/2 else rng.uniform(24*U, 0.25*self.W)
        y = self.H-rng.uniform(24*U, 0.25*self.H) if from_pt[1] < self.H/2 else rng.uniform(24*U, 0.25*self.H)
        return (x,y)

    def _off_canvas_goal(self, from_pt, dir_idx:int, rng):
        U=self.U
        vx,vy=dir_vec(dir_idx)
        x,y=from_pt
        # march toward the corresponding exterior half-plane
        if abs(vx) >= abs(vy):
            tx = self.W + rng.uniform(18*U, 48*U) if vx >= 0 else -rng.uniform(18*U, 48*U)
            if abs(vx) < 1e-9:
                ty = self.H + rng.uniform(18*U, 48*U) if vy >= 0 else -rng.uniform(18*U, 48*U)
                return (x,ty)
            t=(tx-x)/vx
            return (tx, y + vy*t)
        else:
            ty = self.H + rng.uniform(18*U, 48*U) if vy >= 0 else -rng.uniform(18*U, 48*U)
            t=(ty-y)/max(vy,1e-9) if vy>=0 else (ty-y)/min(vy,-1e-9)
            return (x + vx*t, ty)

    def _bundle_segment_geom(self, before, after, ids, thicknesses):
        U=self.U
        if not ids: return GeometryCollection()
        if len(ids)==1:
            tid=ids[0]; a=before[tid]; b=after[tid]
            return line_stroke_geom(a[0],a[1],b[0],b[1],thicknesses[tid]+0.8*U,round_caps=True)
        # Contiguous bundle members remain ordered, so the convex envelope of the two outer
        # traces is a conservative collision corridor for every member in between.
        first,last=ids[0],ids[-1]
        pts=[before[first],before[last],after[last],after[first]]
        poly=Polygon(pts)
        if not poly.is_valid or poly.area<1e-9:
            poly=LineString([before[first],after[first],after[last],before[last]])
        return poly.convex_hull.buffer(max(thicknesses[i] for i in ids)/2 + 0.55*U,join_style='mitre')

    def _bundle_segment_clear(self, before, after, ids, thicknesses, obstacles, path_index, allow_overlap=False, junction_point=None, junction_radius=0.0, allow_exit=False):
        U=self.U
        for tid in ids:
            a=after[tid]
            if allow_exit:
                if a[0] < -56*U or a[1] < -56*U or a[0] > self.W+56*U or a[1] > self.H+56*U:
                    return False,None
            else:
                if a[0]<12*U or a[1]<12*U or a[0]>self.W-12*U or a[1]>self.H-12*U:
                    return False,None
        geom=self._bundle_segment_geom(before,after,ids,thicknesses)
        for obs in obstacles:
            if geom.intersects(obs) or geom.distance(obs)<2.2*U:
                return False,None
        if not allow_overlap:
            q=expand_bounds(geom.bounds,1.0*U)
            probe=geom
            if junction_point is not None and junction_radius>0:
                probe=geom.difference(Point(junction_point[0],junction_point[1]).buffer(junction_radius,quad_segs=8))
            if not probe.is_empty:
                for pg in path_index.query(q):
                    if probe.intersects(pg) or probe.distance(pg)<1.25*U:
                        return False,None
        return True,geom

    def _partition_trace_ids(self, ids, rng):
        n=len(ids)
        if n<=1: return [list(ids)]
        # Usually split into two; a three-way split is possible only when there are enough members.
        parts=3 if n>=10 and rng.random()<0.10 else 2
        cuts=[]
        remaining=n
        start=0
        for pi in range(parts-1):
            min_left=parts-pi-1
            lo=1; hi=remaining-min_left
            # Keep variance broad but avoid pathologically tiny first children every time.
            take=max(lo,min(hi,int(round(remaining*rng.uniform(0.28,0.62)))))
            cuts.append(ids[start:start+take]); start+=take; remaining-=take
        cuts.append(ids[start:])
        return [c for c in cuts if c]

    def _oriented_split_children(self, parts, current, curdir):
        # Children peel according to their lateral position within the parent bundle,
        # not in random deflection order. This reduces sibling self-intersections.
        nx,ny = dir_vec((curdir+2)%8)
        scored=[]
        for child in parts:
            cx=sum(current[i][0] for i in child)/len(child)
            cy=sum(current[i][1] for i in child)/len(child)
            scored.append((cx*nx + cy*ny, child))
        scored.sort(key=lambda t:t[0])
        ordered=[child for _,child in scored]
        if len(ordered)==2:
            offs=[-1,1]
        elif len(ordered)==3:
            offs=[-1,0,1]
        else:
            offs=[0]*len(ordered)
        return list(zip(ordered, offs))

    def _termination_markers_for_ids(self, trace_points, ids, thicknesses, rng):
        U=self.U; filled=rng.random()<0.55; ps=[]
        for tid in ids:
            x,y=trace_points[tid][-1]
            r=self._termination_dot_radius(thicknesses[tid])
            ps.append(prim_circle(x,y,r,self.FG,filled,self.termination_dot_hollow_stroke if not filled else 0.0))
        return ps

    def _generate_pathways_v12_legacy(self, sseed:int, placed:List[Group]):
        rng=SplitMix64(pathway_seed(sseed)); U=self.U
        chips=[g for g in placed if g.structural.get('placement_kind')=='chip']
        cols=[g for g in placed if g.structural.get('placement_kind')=='collection']
        isolated=[g for g in placed if g.structural.get('placement_kind')=='isolated']
        static_items=[(g,g.geom.buffer(5.0*U)) for g in (chips+cols+isolated)]
        path_index=SpatialHash(90*U)
        # Anchors are points on completed pathways and are tagged by source chip.
        anchors=[]
        trace_records=[]
        endpoint_markers=[]
        stats=dict(pathway_bundle_count=0,pathway_launch_trace_count=0,pathway_split_count=0,pathway_leaf_bundle_count=0,pathway_connection_count=0,pathway_collection_connection_count=0,pathway_termination_count=0,pathway_intersection_marker_count=0,pathway_overlap_event_count=0)

        for chip_idx,chip in enumerate(chips):
            chip_obstacles=[geom for grp,geom in static_items if grp is not chip]
            source_chip_obstacle=chip.geom.buffer(2.0*U)
            # Every chip emits on all four sides so the board-wide network covers the canvas.
            sides=['top','right','bottom','left']; rng.shuffle(sides)
            side_count=4
            for side_index,side in enumerate(sides[:side_count]):
                starts,initial_dir,spacing,thicks,side_span=self._chip_launch_bundle(chip,side,rng)
                n=len(starts)
                stats['pathway_bundle_count'] += 1
                stats['pathway_launch_trace_count'] += n
                trace_points={i:[starts[i]] for i in range(n)}
                current={i:starts[i] for i in range(n)}
                thicknesses={i:thicks[i] for i in range(n)}
                initial_goal=None
                foreign_launch=[a for a in anchors if a['chip']!=chip_idx]
                center0=(sum(p[0] for p in starts)/n,sum(p[1] for p in starts)/n)
                if foreign_launch and rng.random()<0.92:
                    nearest=min(foreign_launch,key=lambda a:(a['point'][0]-center0[0])**2+(a['point'][1]-center0[1])**2)
                    ap=nearest['point']; d=math.hypot(ap[0]-center0[0],ap[1]-center0[1])
                    spread=max(math.hypot(p0[0]-center0[0],p0[1]-center0[1]) for p0 in starts)
                    ux=(center0[0]-ap[0])/max(d,1e-9); uy=(center0[1]-ap[1])/max(d,1e-9)
                    stop_gap=spread+rng.uniform(18*U,28*U)
                    initial_goal=('path',(ap[0]+ux*stop_gap,ap[1]+uy*stop_gap))
                elif cols and rng.random()<0.30:
                    nearcols=sorted(cols,key=lambda g:(bounds_center(g.bounds)[0]-center0[0])**2+(bounds_center(g.bounds)[1]-center0[1])**2)
                    if nearcols:
                        initial_goal=('collection',self._collection_anchor(nearcols[0],center0,rng))
                elif rng.random()<0.88:
                    initial_goal=('terminate', self._distant_board_goal(center0, rng))
                # Each active sub-bundle owns a contiguous subset of the original launch members.
                active=[dict(ids=list(range(n)),dir=initial_dir,steps=0,depth=0,goal=initial_goal,min_steps=20,max_steps=40+int(12*rng.random()),must_follow_dir=True,launch_lock_until=2,escape_bias=(rng.random()<0.55))]
                local_waypoints=[]
                while active:
                    br=active.pop(0)
                    ids=br['ids']; curdir=br['dir']; steps=br['steps']; depth=br['depth']; goal=br['goal']
                    min_steps=br['min_steps']; max_steps=br['max_steps']; must_follow=br.get('must_follow_dir',False) or (depth==0 and steps < br.get('launch_lock_until',0)); escape_bias=br.get('escape_bias', False)
                    finished=False
                    while not finished:
                        # Center of the live sub-bundle.
                        center=(sum(current[i][0] for i in ids)/len(ids),sum(current[i][1] for i in ids)/len(ids))
                        sample_pts=trace_points[ids[0]]
                        visible_prev=curdir if len(sample_pts)<2 else nearest_dir_index(sample_pts[-1][0]-sample_pts[-2][0],sample_pts[-1][1]-sample_pts[-2][1])
                        if must_follow:
                            # An undrawn child heading may never drift more than one visible 45° step
                            # away from the last actually rendered segment, even after repeated re-splits.
                            delta=(curdir-visible_prev)%8
                            if delta not in (0,1,7):
                                curdir=step_dir_toward(visible_prev,curdir)
                        foreign=[a for a in anchors if a['chip']!=chip_idx]
                        # Tiny-component connection is sampled first but at a much lower rate,
                        # so it remains visible without competing with pathway-to-pathway joins.
                        if goal is None and steps>=8 and cols and rng.random()<0.12:
                            nearcols=sorted(cols,key=lambda g:(bounds_center(g.bounds)[0]-center[0])**2+(bounds_center(g.bounds)[1]-center[1])**2)
                            if nearcols:
                                goal=('collection',self._collection_anchor(nearcols[0],center,rng))
                        # Pathway-to-pathway connection is the dominant connection mode.
                        if goal is None and steps>=3 and foreign:
                            nearest=min(foreign,key=lambda a:(a['point'][0]-center[0])**2+(a['point'][1]-center[1])**2)
                            ap=nearest['point']
                            d=math.hypot(ap[0]-center[0],ap[1]-center[1])
                            if d<760*U and rng.random()<1.0:
                                spread=max(math.hypot(current[i][0]-center[0],current[i][1]-center[1]) for i in ids) if ids else 0.0
                                ux=(center[0]-ap[0])/max(d,1e-9); uy=(center[1]-ap[1])/max(d,1e-9)
                                stop_gap=spread + rng.uniform(8*U,16*U)
                                goal=('path',(ap[0]+ux*stop_gap,ap[1]+uy*stop_gap))
                        # Abrupt stop probability falls sharply with bundle multiplicity.
                        if goal is None and steps>=min_steps:
                            m=len(ids)
                            term_p=0.002*(max(1,m)**-1.55)
                            if rng.random()<term_p:
                                goal=('escape', self._off_canvas_goal(center, curdir, rng)) if escape_bias else ('terminate', self._distant_board_goal(center, rng))

                        # Repeated splitting is strongly encouraged; large bundles split earlier and more often.
                        split_p=0.0 if len(ids)<=1 else min(0.16,0.02+0.12*(1.0-math.exp(-(len(ids)-1)/7.5)))
                        if goal is None and len(ids)>1 and depth<5 and steps>=10 and rng.random()<split_p:
                            parts=self._partition_trace_ids(ids,rng)
                            if len(parts)>1:
                                stats['pathway_split_count'] += 1
                                for child,doff in self._oriented_split_children(parts,current,curdir):
                                    active.append(dict(ids=child,dir=(curdir+doff)%8,steps=steps,depth=depth+1,goal=None,min_steps=max(min_steps,steps+6),max_steps=max_steps+6+int(5*rng.random()),must_follow_dir=True,launch_lock_until=1,escape_bias=escape_bias))
                                finished=True
                                break

                        # At maximum journey length, prefer connection if available; otherwise terminate.
                        if steps>=max_steps and goal is None:
                            if foreign:
                                nearest=min(foreign,key=lambda a:(a['point'][0]-center[0])**2+(a['point'][1]-center[1])**2)
                                ap=nearest['point']; d=math.hypot(ap[0]-center[0],ap[1]-center[1])
                                if d<520*U:
                                    spread=max(math.hypot(current[i][0]-center[0],current[i][1]-center[1]) for i in ids) if ids else 0.0
                                    ux=(center[0]-ap[0])/max(d,1e-9); uy=(center[1]-ap[1])/max(d,1e-9)
                                    stop_gap=spread+rng.uniform(24*U,34*U)
                                    goal=('path',(ap[0]+ux*stop_gap,ap[1]+uy*stop_gap))
                                else:
                                    goal=('escape', self._off_canvas_goal(center, curdir, rng)) if escape_bias else ('terminate', self._distant_board_goal(center, rng))
                            else:
                                goal=('escape', self._off_canvas_goal(center, curdir, rng)) if escape_bias else ('terminate', self._distant_board_goal(center, rng))

                        if goal is not None:
                            gkind,gpt=goal
                            goal_d=math.hypot(gpt[0]-center[0],gpt[1]-center[1])
                            if gkind=='path' and goal_d <= 150*U and steps>=4:
                                stats['pathway_connection_count'] += 1
                                stats['pathway_leaf_bundle_count'] += 1
                                finished=True
                                break
                            if gkind=='collection' and goal_d <= 72*U and steps>=4:
                                stats['pathway_collection_connection_count'] += 1
                                stats['pathway_connection_count'] += 1
                                stats['pathway_leaf_bundle_count'] += 1
                                finished=True
                                break
                        if goal is not None and gkind=='escape' and ((center[0] < -8*U) or (center[1] < -8*U) or (center[0] > self.W+8*U) or (center[1] > self.H+8*U)):
                            stats['pathway_leaf_bundle_count'] += 1
                            finished=True
                            break
                        # Direction choice. Goal steering changes heading by at most one 45° step.
                        finish_goal=False; gkind=None
                        if goal is not None:
                            gkind,gpt=goal
                            desired=nearest_dir_index(gpt[0]-center[0],gpt[1]-center[1])
                            ndir=curdir if must_follow else step_dir_toward(curdir,desired)
                            dist=math.hypot(gpt[0]-center[0],gpt[1]-center[1])
                            if gkind=='path':
                                gap=0.0
                            elif gkind=='collection':
                                gap=rng.uniform(8*U,14*U)
                            else:
                                gap=0.0
                            if dist<=110*U and not must_follow:
                                seg_len=max(20*U,dist-gap)
                                finish_goal=True
                            else:
                                if must_follow and depth==0 and steps < br.get('launch_lock_until',0):
                                    room=self._forward_room([before_i for before_i in current.values()], ndir)
                                    seg_len=min(rng.uniform(30*U,52*U), max(18*U, room-6*U))
                                else:
                                    seg_len=rng.uniform(124*U,196*U)
                        else:
                            if must_follow:
                                ndir=curdir
                            else:
                                delta=rng.weighted([(0,0.22),(-1,0.39),(1,0.39)])
                                ndir=(curdir+delta)%8
                            if must_follow and depth==0 and steps < br.get('launch_lock_until',0):
                                room=self._forward_room([current[i] for i in ids], ndir)
                                seg_len=min(rng.uniform(30*U,52*U), max(18*U, room-6*U))
                            else:
                                seg_len=rng.uniform(132*U,208*U)

                        before={i:current[i] for i in ids}
                        vx,vy=dir_vec(ndir)
                        after={i:(before[i][0]+vx*seg_len,before[i][1]+vy*seg_len) for i in ids}
                        allow_overlap=False
                        early_free = (depth == 0 and steps < 1)
                        route_obstacles=chip_obstacles + ([source_chip_obstacle] if steps>=2 else [])
                        accepted,seggeom=self._bundle_segment_clear(before,after,ids,thicknesses,route_obstacles,path_index,allow_overlap=(allow_overlap or early_free),junction_point=center if must_follow else None,junction_radius=(max(math.hypot(current[i][0]-center[0],current[i][1]-center[1]) for i in ids)+4*U) if must_follow else 0.0, allow_exit=(goal is not None and gkind=='escape'))
                        # Try nearby 45° alternatives rather than severing or abandoning the route.
                        tries=0
                        while not accepted and tries<10:
                            tries+=1
                            # Before a split-child has drawn its assigned branch segment, retries may
                            # vary only segment length, not heading. After that, ±45° alternatives are legal.
                            ndir=curdir if must_follow else (curdir + (1 if tries%2 else -1))%8
                            seg_len=(min(rng.uniform(26*U,56*U), max(18*U, self._forward_room([current[i] for i in ids], ndir)-4*U)) if must_follow and depth==0 and steps < br.get('launch_lock_until',0) else rng.uniform(78*U,138*U))
                            vx,vy=dir_vec(ndir)
                            after={i:(before[i][0]+vx*seg_len,before[i][1]+vy*seg_len) for i in ids}
                            accepted,seggeom=self._bundle_segment_clear(before,after,ids,thicknesses,route_obstacles,path_index,allow_overlap=(allow_overlap or early_free),junction_point=center if must_follow else None,junction_radius=(max(math.hypot(current[i][0]-center[0],current[i][1]-center[1]) for i in ids)+4*U) if must_follow else 0.0, allow_exit=(goal is not None and gkind=='escape'))
                            finish_goal=False
                        if not accepted:
                            # A blocked multi-line bundle must split before it is allowed to die. This prevents
                            # wide launch bundles from becoming short stubs beside the source chip.
                            if len(ids)>1 and depth<5:
                                parts=self._partition_trace_ids(ids,rng)
                                if len(parts)>1:
                                    stats['pathway_split_count'] += 1
                                    oriented=self._oriented_split_children(parts,current,(visible_prev if must_follow else curdir))
                                    goal_idx=None
                                    if goal is not None:
                                        _,gpt=goal
                                        goal_idx=min(range(len(oriented)), key=lambda ci: (sum(current[i][0] for i in oriented[ci][0])/len(oriented[ci][0]) - gpt[0])**2 + (sum(current[i][1] for i in oriented[ci][0])/len(oriented[ci][0]) - gpt[1])**2)
                                    launch_locked = steps < br.get('launch_lock_until',0)
                                    for ci,(child,doff) in enumerate(oriented):
                                        child_goal=goal if (goal is not None and ci==goal_idx) else None
                                        child_dir=((visible_prev if must_follow else curdir)+(0 if launch_locked else doff))%8
                                        active.append(dict(ids=child,dir=child_dir,steps=steps,depth=depth+1,goal=child_goal,min_steps=max(min_steps,steps+6),max_steps=max_steps+8+int(6*rng.random()),must_follow_dir=True,launch_lock_until=max(0, br.get('launch_lock_until',0)-steps),escape_bias=escape_bias))
                                    finished=True
                                    break
                            # Single traces / already deeply split branches get extra short-step routing attempts.
                            rescued=False
                            if len(ids)<=2:
                                before={i:current[i] for i in ids}
                                choices=[curdir] if must_follow else [curdir,(curdir-1)%8,(curdir+1)%8]
                                for _rescue in range(14):
                                    ndir=choices[int(rng.random()*len(choices))]
                                    seg_len=rng.uniform(22*U,68*U)
                                    vx,vy=dir_vec(ndir)
                                    after={i:(before[i][0]+vx*seg_len,before[i][1]+vy*seg_len) for i in ids}
                                    accepted,seggeom=self._bundle_segment_clear(before,after,ids,thicknesses,route_obstacles,path_index,allow_overlap=early_free,junction_point=center if must_follow else None,junction_radius=(max(math.hypot(current[i][0]-center[0],current[i][1]-center[1]) for i in ids)+4*U) if must_follow else 0.0, allow_exit=(goal is not None and gkind=='escape'))
                                    if accepted:
                                        for i in ids:
                                            current[i]=after[i]
                                            trace_points[i].append(after[i])
                                        path_index.insert(seggeom,seggeom.bounds)
                                        center=(sum(current[i][0] for i in ids)/len(ids),sum(current[i][1] for i in ids)/len(ids))
                                        local_waypoints.append(dict(point=center,chip=chip_idx))
                                        steps+=1; curdir=ndir; must_follow=False; rescued=True
                                        break
                            if rescued:
                                continue
                            # Only a sufficiently travelled small descendant may terminate because routing is exhausted.
                            if steps>=min_steps:
                                if goal is not None and goal[0]=='path' and math.hypot(goal[1][0]-center[0],goal[1][1]-center[1]) < 210*U:
                                    stats['pathway_connection_count'] += 1
                                    stats['pathway_leaf_bundle_count'] += 1
                                    finished=True
                                    break
                                endpoint_markers.extend(self._termination_markers_for_ids(trace_points,ids,thicknesses,rng))
                                stats['pathway_termination_count'] += 1
                                stats['pathway_leaf_bundle_count'] += 1
                                finished=True
                                break
                            # Otherwise force one more split opportunity / defer termination.
                            if len(ids)>1:
                                parts=self._partition_trace_ids(ids,rng)
                                if len(parts)>1:
                                    stats['pathway_split_count'] += 1
                                    oriented=self._oriented_split_children(parts,current,(visible_prev if must_follow else curdir))
                                    goal_idx=None
                                    if goal is not None:
                                        _,gpt=goal
                                        goal_idx=min(range(len(oriented)), key=lambda ci: (sum(current[i][0] for i in oriented[ci][0])/len(oriented[ci][0]) - gpt[0])**2 + (sum(current[i][1] for i in oriented[ci][0])/len(oriented[ci][0]) - gpt[1])**2)
                                    launch_locked = steps < br.get('launch_lock_until',0)
                                    for ci,(child,doff) in enumerate(oriented):
                                        child_goal=goal if (goal is not None and ci==goal_idx) else None
                                        child_dir=((visible_prev if must_follow else curdir)+(0 if launch_locked else doff))%8
                                        active.append(dict(ids=child,dir=child_dir,steps=steps,depth=depth+1,goal=child_goal,min_steps=max(min_steps,steps+6),max_steps=max_steps+8,must_follow_dir=True,launch_lock_until=max(0, br.get('launch_lock_until',0)-steps),escape_bias=escape_bias))
                                    finished=True
                                    break
                            # Last-resort pre-minimum-journery continuation: allow pathway-pathway crossing but
                            # still respect static board objects. This is preferable to a one-segment stub.
                            before={i:current[i] for i in ids}
                            forced=False
                            for doff in ((0,) if must_follow else (0,-1,1)):
                                ndir=(curdir+doff)%8
                                seg_len=20*U
                                vx,vy=dir_vec(ndir)
                                after={i:(before[i][0]+vx*seg_len,before[i][1]+vy*seg_len) for i in ids}
                                accepted,seggeom=self._bundle_segment_clear(before,after,ids,thicknesses,route_obstacles,path_index,allow_overlap=early_free,junction_point=center if must_follow else None,junction_radius=(max(math.hypot(current[i][0]-center[0],current[i][1]-center[1]) for i in ids)+4*U) if must_follow else 0.0, allow_exit=(goal is not None and gkind=='escape'))
                                if accepted:
                                    for i in ids:
                                        current[i]=after[i]
                                        trace_points[i].append(after[i])
                                    path_index.insert(seggeom,seggeom.bounds)
                                    center=(sum(current[i][0] for i in ids)/len(ids),sum(current[i][1] for i in ids)/len(ids))
                                    local_waypoints.append(dict(point=center,chip=chip_idx))
                                    steps+=1; curdir=ndir; must_follow=False; forced=True
                                    break
                            if forced:
                                continue
                            # Truly boxed in by static geometry: terminate as the only remaining escape hatch.
                            endpoint_markers.extend(self._termination_markers_for_ids(trace_points,ids,thicknesses,rng))
                            stats['pathway_termination_count'] += 1
                            stats['pathway_leaf_bundle_count'] += 1
                            finished=True
                            break

                        # The important continuity invariant: each trace gets the new vertex appended to its ONE polyline.
                        for i in ids:
                            current[i]=after[i]
                            trace_points[i].append(after[i])
                        path_index.insert(seggeom,seggeom.bounds)
                        center=(sum(current[i][0] for i in ids)/len(ids),sum(current[i][1] for i in ids)/len(ids))
                        local_waypoints.append(dict(point=center,chip=chip_idx))
                        steps+=1; curdir=ndir; must_follow=False

                        # Natural encounter connection: if this travelling sub-bundle comes close to
                        # a pathway from another chip, it may stop there instead of needing to target it first.
                        foreign_now=[a for a in anchors if a['chip']!=chip_idx]
                        if goal is None and steps>=4 and foreign_now:
                            nearest=min(foreign_now,key=lambda a:(a['point'][0]-center[0])**2+(a['point'][1]-center[1])**2)
                            encounter_d=math.hypot(nearest['point'][0]-center[0],nearest['point'][1]-center[1])
                            spread=max(math.hypot(current[i][0]-center[0],current[i][1]-center[1]) for i in ids) if ids else 0.0
                            if encounter_d <= spread + 144*U and rng.random()<0.98:
                                stats['pathway_connection_count'] += 1
                                stats['pathway_leaf_bundle_count'] += 1
                                finished=True
                                break
                        # Rare natural encounter with a small collection.
                        if goal is None and steps>=6 and cols and rng.random()<0.08:
                            nearcol=min(cols,key=lambda g:g.geom.distance(Point(center)))
                            if nearcol.geom.distance(Point(center)) < 56*U:
                                stats['pathway_collection_connection_count'] += 1
                                stats['pathway_connection_count'] += 1
                                stats['pathway_leaf_bundle_count'] += 1
                                finished=True
                                break

                        if finish_goal and goal is not None:
                            if gkind=='terminate':
                                endpoint_markers.extend(self._termination_markers_for_ids(trace_points,ids,thicknesses,rng))
                                stats['pathway_termination_count'] += 1
                            elif gkind=='collection':
                                stats['pathway_collection_connection_count'] += 1
                                stats['pathway_connection_count'] += 1
                            elif gkind=='escape':
                                pass
                            else:
                                stats['pathway_connection_count'] += 1
                            stats['pathway_leaf_bundle_count'] += 1
                            finished=True
                            break
                        goal=None if goal and finish_goal else goal

                    # end branch while
                # Render each original launch member as one continuous polyline. Branching only changes its future vertices.
                group_prims=[]
                for tid,pts in trace_points.items():
                    if len(pts)>=2:
                        group_prims.append(prim_polyline(pts,thicknesses[tid],self.FG,round_caps=False))
                        trace_records.append(dict(chip=chip_idx,points=pts,primitive=group_prims[-1]))
                group_prims.extend(endpoint_markers)
                endpoint_markers=[]
                if group_prims:
                    dirs=[]
                    for tid,pts in trace_points.items():
                        for a,b in zip(pts,pts[1:]): dirs.append(nearest_dir_index(b[0]-a[0],b[1]-a[1]))
                    cov_ratio=((n-1)*spacing/side_span) if n>1 else 0.0
                    trace_group=Group(f'pathway-chip{chip_idx}-side{side_index}',group_prims,dict(placement_kind='pathway',pathway=True,bundle_source_chip=chip_idx,launch_side=side,launch_line_count=n,bundle_spacing=spacing,launch_coverage_ratio=cov_ratio,segment_direction_indices=dirs))
                    # Path corridor becomes available to later bundles/chips.
                    anchors.extend(local_waypoints if len(local_waypoints) <= 24 else local_waypoints[::2])
                    # Ensure branch endpoints are always targetable too.
                    for ids in [list(range(n))]:
                        c=(sum(current[i][0] for i in ids)/len(ids),sum(current[i][1] for i in ids)/len(ids))
                        anchors.append(dict(point=c,chip=chip_idx))
                    # Store now; final list assembled after intersection markers.
                    if '_path_groups' not in locals(): _path_groups=[]
                    _path_groups.append(trace_group)

        groups=locals().get('_path_groups',[])
        # Mark actual rare intersections / overlaps between traces from different chips.
        markers=[]; seen=[]
        trace_index=SpatialHash(90*U)
        for rec in trace_records:
            line=LineString(rec['points'])
            for ochip,other in trace_index.query(expand_bounds(line.bounds,1.0*U)):
                if rec['chip']==ochip: continue
                inter=line.intersection(other)
                if inter.is_empty: continue
                pts=[]
                if inter.geom_type=='Point': pts=[inter]
                elif inter.geom_type.startswith('Multi') or inter.geom_type=='GeometryCollection': pts=[g for g in inter.geoms if g.geom_type=='Point']
                elif inter.geom_type in ('LineString','MultiLineString'): pts=[inter.representative_point()]
                for pt in pts:
                    x,y=pt.x,pt.y
                    if any((x-sx)**2+(y-sy)**2<(6*U)**2 for sx,sy in seen): continue
                    seen.append((x,y))
                    markers.append(prim_circle(x,y,rng.uniform(1.7*U,2.6*U),self.FG,filled=rng.random()<0.55,stroke=1.25*U))
                    stats['pathway_intersection_marker_count'] += 1
            trace_index.insert((rec['chip'],line),line.bounds)
        if markers:
            groups.append(Group('pathway-intersections',markers,dict(placement_kind='pathway',pathway=True,pathway_marker=True)))
        stats['pathway_overlap_event_count']=stats['pathway_intersection_marker_count']
        seg_counts=[max(0,len(rec['points'])-1) for rec in trace_records]
        stats['pathway_trace_count']=len(seg_counts)
        stats['pathway_mean_segments_per_trace']=(sum(seg_counts)/len(seg_counts)) if seg_counts else 0.0
        stats['pathway_max_segments_per_trace']=max(seg_counts) if seg_counts else 0
        stats['pathway_min_segments_per_trace']=min(seg_counts) if seg_counts else 0
        return groups,stats

    def generate_pathways(self, sseed:int, placed:List[Group]):
        """Generate pathways directly from the supplied sample seed.

        The active renderer uses coarse synchronous bundle gestures.  The old v12.1 serial
        routine remains named explicitly above only as baseline history; it is never called by
        sample generation.
        """
        planner=BundleGesturePlanner(self,sseed,placed)
        self.last_pathway_planner=planner
        return planner.run()

    # ------------------------------ placement ----------------------------
    def legal_center_ranges(self,g:Group,edge):
        b=g.bounds; left=-b[0]+edge; right=self.W-b[2]-edge; top=-b[1]+edge; bottom=self.H-b[3]-edge
        return left,right,top,bottom

    def placement_spread_score(self, cand: Group, placed: List[Group], kind: str) -> float:
        if not placed:
            return 1e18
        cx, cy = bounds_center(cand.bounds)
        spread_class = "secondary" if kind in ("collection","isolated") else kind
        all_d=[]; same_d=[]
        sector_same=0; sector_all=0
        sx=min(2, max(0, int(3*cx/self.W))); sy=min(2, max(0, int(3*cy/self.H)))
        for other in placed:
            ox, oy = bounds_center(other.bounds)
            d=math.hypot(cx-ox, cy-oy)
            all_d.append(d)
            osx=min(2, max(0, int(3*ox/self.W))); osy=min(2, max(0, int(3*oy/self.H)))
            if (osx,osy)==(sx,sy):
                sector_all += 1
            other_kind=other.structural.get("placement_kind")
            other_class="secondary" if other_kind in ("collection","isolated") else other_kind
            if other_class==spread_class:
                same_d.append(d)
                if (osx,osy)==(sx,sy):
                    sector_same += 1
        min_all=min(all_d) if all_d else 0.0
        min_same=min(same_d) if same_d else min_all
        emptiness=(1.0/(1.0+sector_same)) + 0.35*(1.0/(1.0+sector_all))
        return 0.65*min_same + 0.35*min_all + 90*self.U*emptiness

    def place_objects(self,chips,collections,isolated,rng):
        placed=[]; index=SpatialHash(120*self.U)
        plan=[("chip",chips,self.chip_edge_clearance,4096,16,1.00),("collection",collections,20*self.U,4096,8,0.72),("isolated",isolated,20*self.U,4096,8,0.72)]
        for kind,objs,edge,max_attempt,proposal_batch,spread_prob in plan:
            for obj in objs:
                l,r,t,b=self.legal_center_ranges(obj,edge)
                if l>r or t>b: raise RuntimeError("object cannot fit legal frame bounds")
                ok=None; attempts=0
                while attempts < max_attempt and ok is None:
                    valids=[]
                    batch=min(proposal_batch, max_attempt-attempts)
                    for _ in range(batch):
                        attempts += 1
                        x=rng.uniform(l,r); y=rng.uniform(t,b); cand=obj.transformed(x,y)
                        qbounds=expand_bounds(cand.bounds,max(60*self.U,self.chip_secondary_clearance))
                        valid=True
                        for other in index.query(qbounds):
                            okind=other.structural.get("placement_kind")
                            clearance=(self.chip_chip_clearance if kind=="chip" and okind=="chip" else self.chip_secondary_clearance if "chip" in (kind,okind) else 12*self.U)
                            if cand.geom.intersects(other.geom) or cand.geom.distance(other.geom)<clearance:
                                valid=False; break
                        if valid:
                            cand.structural=dict(obj.structural); cand.structural["placement_kind"]=kind
                            valids.append(cand)
                    if valids:
                        if rng.random() < spread_prob and len(valids) > 1:
                            ok=max(valids, key=lambda g: self.placement_spread_score(g, placed, kind))
                        else:
                            ok=valids[0]
                if ok is None: return None
                placed.append(ok); index.insert(ok)
        return placed

    # ------------------------------ validation ---------------------------
    def _free_terminal_points(self, pathways: List[Group]):
        """Return visible free pathway terminals suitable for a later small-component attachment.

        The current renderer intentionally discovers these after the full main + local network is frozen. A
        terminal is eligible only when the materialized pathway group contains a foreground
        endpoint marker close to the *last* point of one of its polylines.  This excludes source
        markers and avoids attaching to explicit head-to-head joins, which do not carry a free
        termination marker.
        """
        out=[]
        for g in pathways:
            polylines=[p.svg for p in g.primitives if p.svg.get('type')=='polyline' and p.svg.get('points')]
            markers=[p.svg for p in g.primitives if p.svg.get('type')=='circle' and p.svg.get('fill')!=self.BG]
            if not polylines or not markers:
                continue
            starts=[tuple(pl['points'][0]) for pl in polylines]
            for pl in polylines:
                end=tuple(pl['points'][-1])
                if not (0 <= end[0] <= self.W and 0 <= end[1] <= self.H):
                    continue
                # The source marker can be near a very short line's end; reject anything also
                # close to a known source point.
                if any(math.hypot(end[0]-q[0],end[1]-q[1]) <= 4.0*self.U for q in starts):
                    continue
                near=[m for m in markers if math.hypot(end[0]-m['cx'],end[1]-m['cy']) <= max(5.0*self.U, m['r']+m.get('stroke_width',0.0))]
                if near:
                    out.append(end)
        # Deduplicate terminals created by multi-primitive materialization.
        dedup=[]
        for p0 in out:
            if not any(math.hypot(p0[0]-q[0],p0[1]-q[1]) <= 3.0*self.U for q in dedup):
                dedup.append(p0)
        return dedup

    def _component_candidate_valid(self, cand: Group, kind: str, chips: List[Group], pathways: List[Group],
                                   accepted: List[Group], attachment_point: Optional[Tuple[float,float]]=None,
                                   chip_keepout=None, pathway_keepout=None) -> bool:
        b=cand.bounds; edge=self.component_edge_clearance
        if b[0] < edge or b[1] < edge or self.W-b[2] < edge or self.H-b[3] < edge:
            return False
        # Final residual fill uses precomputed buffered unions whenever available. This turns the
        # expensive "candidate x every path" loop into two exact broad geometry tests.
        if chip_keepout is None:
            chip_keepout=unary_union([g.geom.buffer(self.component_chip_clearance,quad_segs=8) for g in chips]) if chips else GeometryCollection()
        if pathway_keepout is None:
            pathway_keepout=unary_union([g.geom.buffer(self.component_pathway_clearance,quad_segs=8) for g in pathways]) if pathways else GeometryCollection()
        if not chip_keepout.is_empty and cand.geom.intersects(chip_keepout):
            return False
        if not pathway_keepout.is_empty and cand.geom.intersects(pathway_keepout):
            if attachment_point is None:
                return False
            r=max(bounds_w_h(cand.bounds))/2 + self.component_pathway_clearance + 3.0*self.U
            allowed=Point(attachment_point).buffer(r,quad_segs=12)
            conflict=cand.geom.intersection(pathway_keepout)
            if not conflict.is_empty and not conflict.difference(allowed).is_empty:
                return False
        for other in accepted:
            if cand.geom.intersects(other.geom) or cand.geom.distance(other.geom) < self.component_component_clearance:
                return False
        return True

    def _residual_gap_site_count(self, component_count:int, target:float) -> int:
        if component_count <= 0:
            return 0
        # Pick an integer denominator whose realized component/site ratio is nearest the sampled
        # target while remaining inside the governing 75–90% soft band whenever possible.
        lo=max(component_count, math.ceil(component_count/self.residual_gap_fill_range[1]))
        hi=max(lo, math.floor(component_count/self.residual_gap_fill_range[0]))
        ideal=component_count/max(1e-9,target)
        return min(hi,max(lo,int(round(ideal))))

    def _find_residual_gap_sites(self, chips:List[Group], pathways:List[Group], rng:SplitMix64, count:int):
        """Return area-weighted sites from connected residual regions after all routing.

        V33 uses a 28x28 free-space field and connected components.  Site quotas are allocated
        proportional to region area, so a large room gets several component opportunities while
        a small pocket gets one small-object opportunity instead of being treated equivalently.
        Returned tuples are (x, y, region_id); placement remains exact-geometry validated.
        """
        if count <= 0: self._component_gap_regions=[]; return []
        buffered=[g.geom.buffer(self.component_chip_clearance,quad_segs=8) for g in chips]
        buffered += [g.geom.buffer(self.component_pathway_clearance,quad_segs=8) for g in pathways]
        blocked=unary_union(buffered) if buffered else GeometryCollection()
        n=28; cw=self.W/n; ch=self.H/n; edge=self.component_edge_clearance
        open_cells=set(); clearance={}
        for gy in range(n):
            for gx in range(n):
                x=(gx+.5)*cw; y=(gy+.5)*ch
                if x<edge or y<edge or x>self.W-edge or y>self.H-edge: continue
                p=Point(x,y)
                if not blocked.is_empty and blocked.intersects(p): continue
                open_cells.add((gx,gy))
                clearance[(gx,gy)]=(p.distance(blocked) if not blocked.is_empty else min(self.W,self.H))
        regions=[]; unseen=set(open_cells); rid=0
        while unseen:
            seed=min(unseen); unseen.remove(seed); stack=[seed]; cells=[]
            while stack:
                c=stack.pop(); cells.append(c); x,y=c
                for nb in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if nb in unseen: unseen.remove(nb); stack.append(nb)
            if not cells: continue
            xs=[x for x,y in cells]; ys=[y for x,y in cells]
            w=(max(xs)-min(xs)+1)*cw; h=(max(ys)-min(ys)+1)*ch
            cx=sum((x+.5)*cw for x,y in cells)/len(cells); cy=sum((y+.5)*ch for x,y in cells)/len(cells)
            regions.append(dict(id=rid,cells=set(cells),cell_count=len(cells),width=w,height=h,
                                area=len(cells)*cw*ch,center=(cx,cy),short_span=min(w,h),long_span=max(w,h)))
            rid+=1
        self._component_gap_regions=regions
        self._component_gap_open_cells=set(open_cells)
        self._component_gap_region_by_cell={c:r['id'] for r in regions for c in r['cells']}
        self._component_gap_grid_n=n
        if not regions: return []
        total=sum(r['cell_count'] for r in regions)
        # First guarantee representation of the largest connected rooms until they account for
        # roughly 90% of residual area. Remaining slots are then distributed by area. This makes
        # the user's "fill the remaining gaps" instruction spatial, not just a count ratio.
        quotas={r['id']:0 for r in regions}; used=0; represented=0
        ordered_regions=sorted(regions,key=lambda r:(-r['cell_count'],r['id']))
        coverage_goal=self.residual_gap_fill_range[0]
        for r in ordered_regions:
            if used>=count or represented/max(1,total)>=coverage_goal: break
            quotas[r['id']]=1; used+=1; represented+=r['cell_count']
        # Area-weight the remaining opportunities, favoring already-represented large rooms but
        # still allowing the next substantial unrepresented room to receive a site.
        while used<count:
            best=None
            for r in ordered_regions:
                q=quotas[r['id']]
                score=r['cell_count']/(q+1.0)
                cand=(score,-r['id'],r)
                if best is None or cand[:2]>best[:2]: best=cand
            if best is None: break
            r=best[2]; quotas[r['id']]+=1; used+=1
        sites=[]
        for r in sorted(regions,key=lambda z:(-z['cell_count'],z['id'])):
            want=quotas.get(r['id'],0)
            if want<=0: continue
            candidates=[]
            for gx,gy in r['cells']:
                x=(gx+.5)*cw; y=(gy+.5)*ch
                # Clearance first; mild centre preference avoids hugging ragged region edges.
                c=clearance.get((gx,gy),0.0)
                dc=math.hypot(x-r['center'][0],y-r['center'][1])
                candidates.append((c-.08*dc,rng.random(),x,y))
            candidates.sort(key=lambda z:(-z[0],z[1]))
            selected=[]; sep=.75*max(cw,ch)
            for _,_,x,y in candidates:
                if any(math.hypot(x-a,y-b)<sep for a,b in selected): continue
                selected.append((x,y)); sites.append((x,y,r['id']))
                if len(selected)>=want: break
            if len(selected)<want:
                for _,_,x,y in candidates:
                    if (x,y) in selected: continue
                    selected.append((x,y)); sites.append((x,y,r['id']))
                    if len(selected)>=want: break
        return sites[:count]

    def _component_cells_claimed_by_group(self,g,claim=None):
        """Return residual service-grid cells claimed by one component.

        V34 keeps the 90% component target spatial without repeatedly rebuilding a union of
        every accepted component during pocket mop-up.  Exact geometry is still authoritative
        for placement; this is only the bounded visual-service measurement field.
        """
        cells=set(getattr(self,'_component_gap_open_cells',set()))
        if not cells: return set()
        n=getattr(self,'_component_gap_grid_n',28); cw=self.W/n; ch=self.H/n
        if claim is None: claim=2.15*max(cw,ch)
        bg=g.geom.buffer(claim,quad_segs=4)
        b=bg.bounds
        gx0=max(0,int(math.floor(b[0]/cw-.5))); gx1=min(n-1,int(math.ceil(b[2]/cw-.5)))
        gy0=max(0,int(math.floor(b[1]/ch-.5))); gy1=min(n-1,int(math.ceil(b[3]/ch-.5)))
        out=set()
        for gx in range(gx0,gx1+1):
            for gy in range(gy0,gy1+1):
                c=(gx,gy)
                if c not in cells: continue
                if bg.intersects(Point((gx+.5)*cw,(gy+.5)*ch)): out.add(c)
        return out

    def _component_claimed_gap_cells(self,components):
        """Residual cells visually served by component geometry plus a bounded breathing halo."""
        out=set()
        for g in components: out.update(self._component_cells_claimed_by_group(g))
        return out

    def _make_residual_filler_component(self,rng,idx,region):
        """Generate a small component family matched to a measured residual pocket."""
        size='small'
        if region is not None:
            size=('small' if region['short_span']<1.8*55*self.U or region['cell_count']<5 else
                  'medium' if region['cell_count']<14 else 'large')
        if size=='small' or rng.random()<.30:
            ps,meta=self._capacitor_entity_primitives(rng,0.0,0.0)
            return Group(f"residual-filler-{idx}",ps,dict(family='capacitor_circle',entity_count=1,isolated=True,residual_filler=True,**meta))
        fam=rng.weighted([('dot',.30),('dash',.25),('square',.22),('circle',.23)])
        P=(9.0 if size=='medium' else 12.5)*self.U
        g=self.make_ordinary_subgroup(rng,fam,P)
        g.name=f"residual-filler-{idx}"
        g.structural=dict(g.structural); g.structural['isolated']=True; g.structural['residual_filler']=True
        return g

    def place_residual_components(self, collections:List[Group], isolated:List[Group], chips:List[Group],
                                  pathways:List[Group], rng:SplitMix64, target=None, fallback_attempts=28):
        """Final pass: populate the routed board's residual gaps with components."""
        accepted=[]; attached=[]; remaining_isolated=list(isolated)
        chip_keepout=unary_union([g.geom.buffer(self.component_chip_clearance,quad_segs=8) for g in chips]) if chips else GeometryCollection()
        pathway_keepout=unary_union([g.geom.buffer(self.component_pathway_clearance,quad_segs=8) for g in pathways]) if pathways else GeometryCollection()
        terminals=self._free_terminal_points(pathways)
        rng.shuffle(terminals)
        # Rare reversed connection: the component adapts to a free pathway endpoint, never the
        # other way around.  Restrict this to small isolated capacitors so no route search or
        # arbitrary collection alignment is required.
        if remaining_isolated and terminals and rng.random() < self.component_pathway_attachment_probability:
            cap=remaining_isolated.pop(0)
            for pt in terminals:
                cand=cap.transformed(pt[0],pt[1])
                cand.structural['placement_kind']='isolated'
                cand.structural['component_pathway_attached']=True
                cand.structural['component_pathway_attachment_point']=(pt[0],pt[1])
                if self._component_candidate_valid(cand,'isolated',chips,pathways,accepted,attachment_point=pt,chip_keepout=chip_keepout,pathway_keepout=pathway_keepout):
                    accepted.append(cand); attached.append(cand); break

        gap_objects=[('collection',g) for g in collections] + [('isolated',g) for g in remaining_isolated]
        # Fit larger objects first so capacitors naturally mop up smaller residual pockets.
        gap_objects.sort(key=lambda kg:(bounds_w_h(kg[1].bounds)[0]*bounds_w_h(kg[1].bounds)[1]),reverse=True)
        target=(rng.uniform(*self.residual_gap_fill_range) if target is None else float(target))
        site_count=self._residual_gap_site_count(len(gap_objects),target)
        sites=self._find_residual_gap_sites(chips,pathways,rng,site_count)
        unused=list(sites)
        region_map={r['id']:r for r in getattr(self,'_component_gap_regions',[])}
        failed=[]; served_rids=set()
        for kind,obj in gap_objects:
            chosen=None; chosen_idx=None
            # Try the representative gap sites first, with small seeded jitter around each one.
            order=list(range(len(unused)))
            ow,oh=bounds_w_h(obj.bounds); oarea=max(ow*oh,1e-9)
            # Match object scale to measured room scale before exact collision checks. Large
            # collections prefer large/long rooms; small capacitors naturally fall to pockets.
            def fit_key(idx):
                sx,sy,rid=unused[idx]; reg=region_map.get(rid)
                if reg is None: return (0.0,rng.random())
                ratio=reg['area']/max(oarea,1e-9)
                shape_ok=min(reg['width']/max(ow,1e-9),reg['height']/max(oh,1e-9))
                score=-abs(math.log(max(ratio/5.0,1e-6))) + .45*min(shape_ok,3.0)
                if rid not in served_rids and shape_ok>=.72: score+=9.0
                return (-score,rng.random())
            order.sort(key=fit_key)
            for idx in order:
                sx,sy,rid=unused[idx]
                for attempt in range(8):
                    if attempt==0:
                        x,y=sx,sy
                    else:
                        radius=(6.0+5.0*attempt)*self.U
                        ang=2*math.pi*rng.random()
                        x=sx+math.cos(ang)*radius; y=sy+math.sin(ang)*radius
                    cand=obj.transformed(x,y)
                    cand.structural['placement_kind']=kind
                    if self._component_candidate_valid(cand,kind,chips,pathways,accepted,chip_keepout=chip_keepout,pathway_keepout=pathway_keepout):
                        chosen=cand; chosen_idx=idx; break
                if chosen is not None:
                    break
            # Bounded fallback: search the whole residual field, still selecting only exact-valid
            # placements.  This avoids turning the gap-site abstraction into a hard packing quota.
            if chosen is None:
                best=None; best_score=-1.0
                l,r,t,b=self.legal_center_ranges(obj,self.component_edge_clearance)
                if l<=r and t<=b:
                    for _ in range(max(0,int(fallback_attempts))):
                        x=rng.uniform(l,r); y=rng.uniform(t,b)
                        cand=obj.transformed(x,y); cand.structural['placement_kind']=kind
                        if not self._component_candidate_valid(cand,kind,chips,pathways,accepted,
                                                               chip_keepout=chip_keepout,
                                                               pathway_keepout=pathway_keepout):
                            continue
                        # Prefer open, under-filled regions without requiring a global optimizer.
                        # Reuse the already-built keepout unions; never rebuild or rescan the
                        # complete routed network inside this hot fallback loop.
                        obstacle_dist=min(
                            cand.geom.distance(chip_keepout) if not chip_keepout.is_empty else 1e9,
                            cand.geom.distance(pathway_keepout) if not pathway_keepout.is_empty else 1e9,
                        )
                        accepted_dist=min((cand.geom.distance(g.geom) for g in accepted),default=1e9)
                        score=min(obstacle_dist,accepted_dist)
                        if score>best_score:
                            best_score=score; best=cand
                    chosen=best
            if chosen is None:
                failed.append((kind,obj))
                continue
            accepted.append(chosen)
            if chosen_idx is not None:
                if 0 <= chosen_idx < len(unused): served_rids.add(unused[chosen_idx][2])
                unused.pop(chosen_idx)
            else:
                # Fallback placements are attributed to the nearest measured residual region.
                cx,cy=bounds_center(chosen.bounds)
                regs=getattr(self,'_component_gap_regions',[])
                if regs:
                    served_rids.add(min(regs,key=lambda r:(r['center'][0]-cx)**2+(r['center'][1]-cy)**2)['id'])

        regs=getattr(self,'_component_gap_regions',[])
        total_region_cells=sum(r['cell_count'] for r in regs)
        served_region_cells=sum(r['cell_count'] for r in regs if r['id'] in served_rids)
        served_area_fraction=(served_region_cells/total_region_cells if total_region_cells else 1.0)

        # V33 literal residual-field mop-up. Normal collections establish the large-scale
        # component language first. Then bounded gap-sized fillers target uncovered residual
        # cells until the area-claim target is reached. Exact collision checks remain final.
        extra_fillers=[]; attempted_cells=set()
        open_cells=set(getattr(self,'_component_gap_open_cells',set()))
        region_map={r['id']:r for r in regs}; cell_region=getattr(self,'_component_gap_region_by_cell',{})
        nreg=getattr(self,'_component_gap_grid_n',28); cw=self.W/nreg; ch=self.H/nreg
        fill_goal=max(.90,min(.94,target))
        claimed=self._component_claimed_gap_cells(accepted)
        claimed_fraction=(len(claimed)/len(open_cells) if open_cells else 1.0)
        desired_total=max(len(accepted),min(self.component_density_cap,int(math.ceil(len(open_cells)/10.0))))
        # Serve >=90% of residual-region area and keep a density proportional to available gap
        # area. Claimed-cell fraction is diagnostic, not a literal packing quota.
        while ((claimed_fraction+1e-9 < fill_goal) or len(accepted)<desired_total) and len(extra_fillers)<self.component_extra_filler_limit:
            uncovered=list(open_cells-claimed-attempted_cells)
            if not uncovered: break
            # Prefer cells in the most-uncovered large region, then cells far from existing
            # components so filler does not simply cluster around already-served islands.
            reg_uncovered={}
            for c in uncovered:
                rid=cell_region.get(c); reg_uncovered[rid]=reg_uncovered.get(rid,0)+1
            accepted_centers=[bounds_center(g.bounds) for g in accepted]
            def cell_score(c):
                gx,gy=c; rid=cell_region.get(c)
                x=(gx+.5)*cw; y=(gy+.5)*ch
                # Distance-to-centre is deliberately only a distribution heuristic.  Exact
                # component geometry remains the final legality check below.
                d2=min(((x-a)**2+(y-b)**2 for a,b in accepted_centers),default=(4*max(cw,ch))**2)
                return (reg_uncovered.get(rid,0), min(d2,(4*max(cw,ch))**2))
            uncovered.sort(key=cell_score,reverse=True)
            placed=None; chosen_cell=None
            # Try a handful of the strongest uncovered cells; failed cells are remembered so a
            # narrow impossible pocket cannot dominate the loop.
            for cell in uncovered[:18]:
                gx,gy=cell; rid=cell_region.get(cell); reg=region_map.get(rid)
                filler=self._make_residual_filler_component(rng,len(extra_fillers),reg)
                sx=(gx+.5)*cw; sy=(gy+.5)*ch
                for attempt in range(5):
                    if attempt==0: x,y=sx,sy
                    else:
                        rad=(2.5+3.0*attempt)*self.U; ang=2*math.pi*rng.random()
                        x=sx+math.cos(ang)*rad; y=sy+math.sin(ang)*rad
                    cand=filler.transformed(x,y); cand.structural['placement_kind']='isolated'
                    if self._component_candidate_valid(cand,'isolated',chips,pathways,accepted,
                                                       chip_keepout=chip_keepout,pathway_keepout=pathway_keepout):
                        placed=cand; chosen_cell=cell; break
                if placed is not None: break
                attempted_cells.add(cell)
            if placed is None: break
            accepted.append(placed); extra_fillers.append(placed)
            rid=cell_region.get(chosen_cell)
            if rid is not None: served_rids.add(rid)
            # Incremental service accounting: do not rebuild/rebuffer the whole accepted set.
            claimed.update(self._component_cells_claimed_by_group(placed))
            claimed_fraction=(len(claimed)/len(open_cells) if open_cells else 1.0)

        served_region_cells=sum(r['cell_count'] for r in regs if r['id'] in served_rids)
        served_area_fraction=(served_region_cells/total_region_cells if total_region_cells else 1.0)

        placed_gap_count=len(accepted)-len(attached)
        # Coverage count includes the bounded residual fillers; sites remain the area-weighted
        # normal population benchmark, so cap at 1.0 rather than reporting >100%.
        site_actual=min(1.0,(placed_gap_count/len(sites))) if sites else (1.0 if placed_gap_count==0 else 0.0)
        actual=claimed_fraction
        stats=dict(
            component_placement_mode='post_route_residual_gap_fill',
            component_residual_gap_fill_target=target,
            component_residual_gap_site_count=len(sites),
            component_residual_gap_site_requested_count=site_count,
            component_residual_gap_region_count=len(getattr(self,'_component_gap_regions',[])),
            component_residual_gap_open_cell_count=sum(r['cell_count'] for r in getattr(self,'_component_gap_regions',[])),
            component_residual_gap_served_region_area_fraction=served_area_fraction,
            component_residual_gap_claimed_cell_count=len(claimed),
            component_residual_gap_claimed_area_fraction=claimed_fraction,
            component_residual_gap_served_region_count=len(served_rids),
            component_residual_gap_extra_filler_count=len(extra_fillers),
            component_residual_gap_density_target_count=desired_total,
            component_residual_gap_total_component_count=len(accepted),
            component_residual_gap_placed_count=placed_gap_count,
            component_residual_gap_fill_actual=actual,
            component_residual_gap_site_fill_actual=site_actual,
            component_pathway_attachment_count=len(attached),
            component_pathway_attachment_probability=self.component_pathway_attachment_probability,
            component_unplaced_count=len(failed),
            component_chip_clearance=self.component_chip_clearance,
            component_pathway_clearance=self.component_pathway_clearance,
            component_component_clearance=self.component_component_clearance,
        )
        return accepted,stats

    def validate_sample(self,placed,chip_count,N,quotas):
        U,S=self.U,self.S
        chips=[g for g in placed if g.structural.get("placement_kind")=="chip"]
        cols=[g for g in placed if g.structural.get("placement_kind")=="collection"]
        isolated=[g for g in placed if g.structural.get("placement_kind")=="isolated"]
        errors=[]
        # frame edges
        for g in chips:
            b=g.bounds
            if (b[0]<self.chip_edge_clearance-1e-7 or b[1]<self.chip_edge_clearance-1e-7 or
                    self.W-b[2]<self.chip_edge_clearance-1e-7 or self.H-b[3]<self.chip_edge_clearance-1e-7):
                errors.append("chip_frame")
        for g in cols:
            b=g.bounds
            if b[0]<self.component_edge_clearance-1e-7 or b[1]<self.component_edge_clearance-1e-7 or self.W-b[2]<self.component_edge_clearance-1e-7 or self.H-b[3]<self.component_edge_clearance-1e-7: errors.append("collection_frame")
        for g in isolated:
            b=g.bounds
            if b[0]<self.component_edge_clearance-1e-7 or b[1]<self.component_edge_clearance-1e-7 or self.W-b[2]<self.component_edge_clearance-1e-7 or self.H-b[3]<self.component_edge_clearance-1e-7: errors.append("isolated_frame")
        # pair clearances exact
        for i,a in enumerate(placed):
            for b in placed[i+1:]:
                ka=a.structural.get("placement_kind"); kb=b.structural.get("placement_kind")
                gap=self.chip_chip_clearance if ka==kb=="chip" else self.component_chip_clearance if "chip" in (ka,kb) else self.component_component_clearance
                if a.geom.intersects(b.geom) or a.geom.distance(b.geom)<gap-1e-7: errors.append(f"pair_{ka}_{kb}")
        # scale calibration
        L=[max(bounds_w_h(g.bounds)) for g in cols]; qs=[g.structural["q_chip"] for g in chips]
        if L:
            if sum(.026*S<=x<=.073*S for x in L)/len(L)<.80: errors.append("collection_core_fraction")
            med=lambda xs: sorted(xs)[len(xs)//2] if len(xs)%2 else .5*(sorted(xs)[len(xs)//2-1]+sorted(xs)[len(xs)//2])
            mL=med(L); mq=med(qs)
            if not (.040*S<=mL<=.052*S): errors.append("collection_median")
            if not (.42<=mL/mq<=.56): errors.append("collection_chip_ratio")
        # quotas / coverage
        fams=[set(g.structural.get("families",())) for g in cols]
        if sum("ic" in f for f in fams)!=quotas["N_ic"]: errors.append("ic_quota")
        if sum("dense" in f for f in fams)!=quotas["N_dense"]: errors.append("dense_quota")
        if sum(bool(g.structural.get("border")) for g in cols)!=quotas["N_border"]: errors.append("border_quota")
        for f in ("square","circle","dot","dash"):
            if sum(f in x for x in fams)<2: errors.append(f"coverage_{f}")
        # dense shape balance
        dense_shapes=[]
        for g in cols:
            for sg in g.structural.get("subgroups",[]):
                if sg.get("family")=="dense": dense_shapes.append(sg.get("dense_dims"))
        if dense_shapes and sum(max(r,c)/min(r,c)>=2.5 for r,c in dense_shapes)/len(dense_shapes)<.60: errors.append("dense_shape_balance")
        ic_contact_failures=sum(sg.get("required_contact_failure_count",0) for g in cols for sg in g.structural.get("subgroups",[]) if sg.get("family")=="ic" and sg.get("ic_mode")=="array")
        if ic_contact_failures:
            errors.append("IC_required_contact_failure")
        # chip diversity signature
        sigs=set()
        for g in chips:
            s=(g.structural.get("orientation"),g.structural.get("aspect_bin"),g.structural.get("motifs"),g.structural.get("inner_border_count"),g.structural.get("exterior_side_set_configuration"))
            if s in sigs: errors.append("chip_duplicate_signature")
            sigs.add(s)
        return errors

    # ------------------------------ batch calibration -------------------
    def calibrate_collections(self, cur_seed, chips, assigns, initial_cols, max_rounds=256, base_seeds=None):
        """Solve §16 + §22.4 as a finite candidate-selection problem.

        Each candidate is produced by the original collection generator from that collection's
        retry stream. The solver merely chooses one already-valid retry candidate per collection
        so the batch acceptance constraints hold. It does not alter geometry, probabilities,
        family assignments, scales, or validation thresholds.
        """
        N=len(initial_cols); S=self.S
        med=lambda xs: sorted(xs)[len(xs)//2] if len(xs)%2 else .5*(sorted(xs)[len(xs)//2-1]+sorted(xs)[len(xs)//2])
        mq=med([g.structural["q_chip"] for g in chips])
        median_lo=max(.040*S,.42*mq)
        median_hi=min(.052*S,.56*mq)
        if median_lo>median_hi:
            return None
        core_lo,core_hi=.026*S,.073*S
        median_need=N//2+1
        core_need=math.ceil(.80*N)
        dense_total=sum("dense" in a["families"] for a in assigns)
        dense_good_need=math.ceil(.60*dense_total)

        bases=list(base_seeds) if base_seeds is not None else [collection_seed(cur_seed,i) for i in range(N)]
        counters=[int(initial_cols[i].structural.get("source_retry_index",0))+1 for i in range(N)]
        # Keep the first representative for each relevant acceptance category.
        pools: List[Dict[Tuple[int,int,int],Group]]=[{} for _ in range(N)]

        def category(i,g):
            L=max(bounds_w_h(g.bounds))
            m=int(median_lo<=L<=median_hi)
            c=int(core_lo<=L<=core_hi)
            d=0
            if "dense" in assigns[i]["families"]:
                dims=[sg.get("dense_dims") for sg in g.structural.get("subgroups",[]) if sg.get("family")=="dense"]
                d=int(bool(dims) and all(max(r,c0)/min(r,c0)>=2.5 for r,c0 in dims))
            return (m,c,d)

        for i,g in enumerate(initial_cols):
            pools[i][category(i,g)]=g

        def solve():
            # DP state counts are capped at requirements; state space stays tiny (N<=18).
            dp={(0,0,0): []}
            for i in range(N):
                ndp={}
                for (m,c,d),sel in dp.items():
                    for (am,ac,ad),g in pools[i].items():
                        ns=(min(median_need,m+am),min(core_need,c+ac),min(dense_good_need,d+ad))
                        if ns not in ndp:
                            ndp[ns]=sel+[g]
                dp=ndp
            return dp.get((median_need,core_need,dense_good_need))

        chosen=solve()
        if chosen is not None:
            return chosen

        for _round in range(max_rounds):
            for i in range(N):
                # Once all 8 boolean categories relevant to this collection are represented,
                # more candidates cannot improve the batch-count solver.
                possible_cap=8 if "dense" in assigns[i]["families"] else 4
                if len(pools[i])>=possible_cap:
                    continue
                attempt=counters[i]; counters[i]+=1
                if attempt>=256:
                    continue
                g=self.plan_collection_candidate(bases[i],i,assigns[i],attempt)
                if g is None:
                    continue
                pools[i].setdefault(category(i,g),g)
            chosen=solve()
            if chosen is not None:
                # Verify exact numerical conditions on the chosen geometry.
                L=[max(bounds_w_h(g.bounds)) for g in chosen]
                mL=med(L)
                dense_shapes=[sg["dense_dims"] for g in chosen for sg in g.structural.get("subgroups",[]) if sg.get("family")=="dense"]
                if (sum(core_lo<=x<=core_hi for x in L)>=core_need and
                    .040*S<=mL<=.052*S and .42<=mL/mq<=.56 and
                    (not dense_shapes or sum(max(r,c)/min(r,c)>=2.5 for r,c in dense_shapes)>=dense_good_need)):
                    return chosen
        return None

    # ------------------------------ sample generation --------------------
    def _validate_component_templates(self, cols, chips, quotas):
        """Pre-route validation for every invariant independent of final XY placement."""
        errors=[]; S=self.S
        L=[max(bounds_w_h(g.bounds)) for g in cols]
        qs=[g.structural["q_chip"] for g in chips]
        if L:
            if sum(.026*S<=x<=.073*S for x in L)/len(L)<.80:
                errors.append("collection_core_fraction")
            med=lambda xs: sorted(xs)[len(xs)//2] if len(xs)%2 else .5*(sorted(xs)[len(xs)//2-1]+sorted(xs)[len(xs)//2])
            mL=med(L); mq=med(qs)
            if not (.040*S<=mL<=.052*S): errors.append("collection_median")
            if not (.42<=mL/mq<=.56): errors.append("collection_chip_ratio")
        fams=[set(g.structural.get("families",())) for g in cols]
        if sum("ic" in f for f in fams)!=quotas["N_ic"]: errors.append("ic_quota")
        if sum("dense" in f for f in fams)!=quotas["N_dense"]: errors.append("dense_quota")
        if sum(bool(g.structural.get("border")) for g in cols)!=quotas["N_border"]: errors.append("border_quota")
        for fam in ("square","circle","dot","dash"):
            if sum(fam in x for x in fams)<2: errors.append(f"coverage_{fam}")
        dense_shapes=[sg.get("dense_dims") for g in cols for sg in g.structural.get("subgroups",[]) if sg.get("family")=="dense"]
        if dense_shapes and sum(max(r,c)/min(r,c)>=2.5 for r,c in dense_shapes)/len(dense_shapes)<.60:
            errors.append("dense_shape_balance")
        ic_contact_failures=sum(sg.get("required_contact_failure_count",0) for g in cols for sg in g.structural.get("subgroups",[]) if sg.get("family")=="ic" and sg.get("ic_mode")=="array")
        if ic_contact_failures:
            errors.append("IC_required_contact_failure")
        return errors

    def _unauthorized_component_pathway_overlap_count(self,components,pathways):
        """Exact final audit: components may touch a path only at an explicit attachment terminal."""
        count=0
        for comp in components:
            pt=comp.structural.get('component_pathway_attachment_point')
            allowed=(Point(pt).buffer(max(5.0*self.U,.22*max(bounds_w_h(comp.bounds))),quad_segs=10) if pt else None)
            for pg in pathways:
                inter=comp.geom.intersection(pg.geom)
                if inter.is_empty: continue
                if allowed is not None and inter.difference(allowed).is_empty:
                    continue
                count+=1
        return count

    def _prepare_component_population_once(self, cur_seed, placed_chips, assigns, quotas,
                                           collection_plan_attempts=128, calibration_rounds=96,
                                           population_attempt=0):
        """Generate/calibrate component templates without placing them on the board.

        This phase is intentionally allowed before routing because template geometry does not
        participate in routing occupancy.  Expensive pathway work must never be discarded merely
        because a later component template/calibration attempt was unlucky.
        """
        N=len(assigns)
        bases=[]
        for k in range(N):
            base=collection_seed(cur_seed,k)
            if population_attempt:
                base=retry_seed(base,0x10000+population_attempt)
            bases.append(base)

        temp_cols=[]
        for k,a in enumerate(assigns):
            g=self.first_valid_collection_plan(bases[k],k,a,max_attempts=collection_plan_attempts)
            if g is None:
                return None
            temp_cols.append(g)

        temp_cols=self.calibrate_collections(cur_seed,placed_chips,assigns,temp_cols,
                                             max_rounds=calibration_rounds,base_seeds=bases)
        if temp_cols is None:
            return None

        full_cols=[]
        for k,(plan,a) in enumerate(zip(temp_cols,assigns)):
            src=plan.structural.get("source_seed")
            if src is None:
                return None
            g=self._make_collection_once(SplitMix64(src),k,a)
            if g is None:
                return None
            g.structural["source_seed"]=src
            pb=plan.bounds; gb=g.bounds
            if max(abs(pb[j]-gb[j]) for j in range(4))>1e-6:
                return None
            full_cols.append(g)

        # Uniqueness is a component-template concern, so reject/regenerate it before routing.
        pending=[]; local_fps=set(); local_recs=[]
        for g in full_cols:
            fp,rec=self.collection_fingerprint(g)
            if (fp in self.batch_fingerprints or fp in local_fps or self.near_duplicate(rec) or
                    any(self.records_near_duplicate(rec,old) for old in local_recs)):
                return None
            local_fps.add(fp); local_recs.append(rec); pending.append((fp,rec,g))
            g.structural["fingerprint"]=fp

        if self._validate_component_templates(full_cols,placed_chips,quotas):
            return None

        cap_seed=cur_seed if population_attempt==0 else retry_seed(cur_seed,0x20000+population_attempt)
        isolated_caps=self.generate_isolated_capacitors(cap_seed)
        return full_cols, isolated_caps, pending

    def _place_component_population_on_frozen_routes(self, cur_seed, population, placed_chips, pathways,
                                                     layout_attempts=4):
        """Place one prepared population without ever changing the frozen route network."""
        collections,isolated_caps,pending=population
        fill_base=component_fill_seed(cur_seed)
        target=SplitMix64(fill_base).uniform(*self.residual_gap_fill_range)
        best=None
        attempts=max(1,int(layout_attempts))
        for layout_attempt in range(attempts):
            # Keep the sampled fill target stable; vary only the deterministic placement stream.
            seed=retry_seed(fill_base,0x30000+layout_attempt)
            placed_components,fill_stats=self.place_residual_components(
                collections,isolated_caps,placed_chips,pathways,SplitMix64(seed),target=target)
            fill_stats['component_layout_attempt_index']=layout_attempt
            fill_stats['component_layout_attempt_count']=layout_attempt+1
            fill_stats['component_pathway_unauthorized_overlap_count']=self._unauthorized_component_pathway_overlap_count(placed_components,pathways)
            key=(-fill_stats['component_unplaced_count'],
                 -fill_stats['component_pathway_unauthorized_overlap_count'],
                 int(fill_stats['component_residual_gap_fill_actual']>=self.residual_gap_fill_range[0]),
                 fill_stats['component_residual_gap_fill_actual'])
            if best is None or key>best[0]:
                best=(key,placed_components,fill_stats,pending)
            if fill_stats['component_unplaced_count']==0 and fill_stats.get('component_pathway_unauthorized_overlap_count',0)==0:
                break
        return best[1],best[2],best[3]

    def generate_sample(self, sample_index=0, max_sample_restarts=256, collection_plan_attempts=256, calibration_rounds=256):
        sseed=sample_seed(self.seed,sample_index)
        for restart in range(max_sample_restarts):
            cur_seed=retry_seed(sseed,restart) if restart else sseed
            srng=SplitMix64(cur_seed)
            nc=self.chip_count(srng); N=self.collection_count(srng)
            assigns,quotas=self.assign_collection_families(srng,N)
            if assigns is None:
                continue

            # PHASE A — MAIN CHIPS ONLY.
            chips=[]; chip_sigs=set(); chip_failed=False
            for j in range(nc):
                base=chip_seed(cur_seed,j); found=None
                for rr in range(128):
                    try:
                        g=self.generate_chip(retry_seed(base,rr) if rr else base,j)
                    except RuntimeError:
                        continue
                    sig=(g.structural.get("orientation"),g.structural.get("aspect_bin"),g.structural.get("motifs"),g.structural.get("inner_border_count"),g.structural.get("exterior_side_set_configuration"))
                    if sig not in chip_sigs:
                        found=g; chip_sigs.add(sig); break
                if found is None:
                    chip_failed=True; break
                chips.append(found)
            if chip_failed:
                continue
            chip_rng=SplitMix64(placement_seed(cur_seed))
            placed_chips=self.place_objects(chips,[],[],chip_rng)
            if placed_chips is None:
                continue

            # Prepare non-spatial component templates *before* routing.  They are not board
            # obstacles and cannot steer a trace; this merely moves cheap failure modes ahead of
            # the expensive route phase so a calibration miss never throws away a routed board.
            population=None; population_attempt=0
            for pa in range(3):
                population=self._prepare_component_population_once(
                    cur_seed,placed_chips,assigns,quotas,collection_plan_attempts,calibration_rounds,pa)
                if population is not None:
                    population_attempt=pa; break
            if population is None:
                continue

            # PHASES B + C — route against chips only, then populate residual gaps with the
            # local network.  Component templates above remain non-spatial and invisible here.
            pathways,path_stats=self.generate_pathways(cur_seed, placed_chips)

            # PHASE D — place components on the frozen route network.  A bad greedy layout gets
            # component-only retries.  It must never trigger traceback, rerouting, or a new board.
            placed_components,fill_stats,pending=self._place_component_population_on_frozen_routes(
                cur_seed,population,placed_chips,pathways,layout_attempts=2)

            # If the first prepared population still cannot fit completely, regenerate only the
            # component templates and placement on the same frozen routes.  This is bounded and
            # deterministic; pathways are never recomputed for filler placement.
            if fill_stats['component_unplaced_count']:
                for pa in range(population_attempt+1,population_attempt+4):
                    alt=self._prepare_component_population_once(
                        cur_seed,placed_chips,assigns,quotas,collection_plan_attempts,calibration_rounds,pa)
                    if alt is None:
                        continue
                    cand_components,cand_stats,cand_pending=self._place_component_population_on_frozen_routes(
                        cur_seed,alt,placed_chips,pathways,layout_attempts=2)
                    cur_key=(-fill_stats['component_unplaced_count'],
                             -fill_stats.get('component_pathway_unauthorized_overlap_count',0),
                             int(fill_stats['component_residual_gap_fill_actual']>=self.residual_gap_fill_range[0]),
                             fill_stats['component_residual_gap_fill_actual'])
                    new_key=(-cand_stats['component_unplaced_count'],
                             -cand_stats.get('component_pathway_unauthorized_overlap_count',0),
                             int(cand_stats['component_residual_gap_fill_actual']>=self.residual_gap_fill_range[0]),
                             cand_stats['component_residual_gap_fill_actual'])
                    if new_key>cur_key:
                        placed_components,fill_stats,pending=cand_components,cand_stats,cand_pending
                    if fill_stats['component_unplaced_count']==0:
                        break

            # The established component population remains a hard static-language invariant.
            # If bounded component-only recovery cannot realise it, skip this logical sample;
            # importantly, no post-route failure can cause an internal full-board restart.
            if fill_stats['component_unplaced_count'] or fill_stats.get('component_pathway_unauthorized_overlap_count',0):
                raise RuntimeError("post-route component-only recovery exhausted or overlap remained")
            if fill_stats.get('component_residual_gap_fill_actual',0.0) < self.residual_gap_fill_range[0]-1e-9:
                raise RuntimeError("component residual-gap service invariant not realized")

            static_final=placed_chips + placed_components
            errors=self.validate_sample(static_final,nc,N,quotas)
            if errors:
                raise RuntimeError("post-route validation failed: "+','.join(errors))

            for fp,rec,g in pending:
                self.batch_fingerprints.add(fp); self.register_record(rec); g.structural["fingerprint"]=fp

            report=self.build_report(static_final,cur_seed,nc,N,quotas,restart)
            report.update(path_stats); report.update(fill_stats)
            report['generation_order']='main_chips -> primary_pathways -> local_gap_pathways -> residual_components'
            report['component_templates_prepared_before_routing']=True
            report['route_restarted_for_component_failure']=False
            report['main_scale']=self.main_scale
            report['canvas_scale_basis']=self.canvas_S
            report['design_scale_basis']=self.S
            report['design_unit_divisor']=1600
            report['design_unit_canvas_fraction']=self.main_scale/1600.0
            report["logical_sample_index"] = sample_index
            return static_final + pathways,report
        raise RuntimeError("complete sample restart limit exceeded")

    def build_report(self,placed,seed,nc,N,quotas,restart):
        cols=[g for g in placed if g.structural.get("placement_kind")=="collection"]
        chips=[g for g in placed if g.structural.get("placement_kind")=="chip"]
        isolated=[g for g in placed if g.structural.get("placement_kind")=="isolated"]
        arrays=[]; contact_failures=0; required_contacts=0
        collection_cap_groups=0; collection_cap_entities=0
        for g in cols:
            if "capacitor_circle" in g.structural.get("families",()):
                collection_cap_groups += 1
            for sg in g.structural.get("subgroups",[]):
                if sg.get("family")=="capacitor_circle":
                    collection_cap_entities += sg.get("entity_count",0)
            for sg in g.structural.get("subgroups",[]):
                if sg.get("family")=="ic" and sg.get("ic_mode")=="array":
                    arrays.append(sg.get("array_shape"))
                    contact_failures+=sg.get("required_contact_failure_count",0)
                    required_contacts+=sg.get("required_contact_count",0)
        chip_pair_min_clearance=min((a.geom.distance(b.geom) for i,a in enumerate(chips) for b in chips[i+1:]),default=None)
        return dict(seed=seed,base_seed=self.seed,restart_index=restart,chip_count=nc,collection_count=N,quotas=quotas,
                    main_chip_pair_min_clearance=chip_pair_min_clearance,
                    main_chip_pair_required_clearance=self.chip_chip_clearance,
                    ic_array_count=len(arrays),ic_array_shapes=arrays,IC_required_contact_count=required_contacts,
                    forbidden_intersection_count=0,forbidden_touch_count=0,clearance_violation_count=0,IC_required_contact_failure_count=contact_failures,
                    chip_q=[g.structural["q_chip"] for g in chips],
                    chip_motifs=[list(g.structural.get("motifs",())) for g in chips],
                    isolated_capacitor_count=len(isolated),
                    isolated_capacitor_states=[g.structural.get("capacitor_state") for g in isolated],
                    isolated_capacitor_radii=[g.structural.get("capacitor_radius") for g in isolated],
                    collection_capacitor_group_count=collection_cap_groups,
                    collection_capacitor_entity_count=collection_cap_entities,
                    collection_long=[max(bounds_w_h(g.bounds)) for g in cols],
                    collection_fingerprints=[g.structural.get("fingerprint") for g in cols])

    # ------------------------------ SVG ----------------------------------
    def svg_for(self,placed,report):
        lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.W:g}" height="{self.H:g}" viewBox="0 0 {self.W:g} {self.H:g}">',
               f'<metadata>{json.dumps(report,separators=(",",":"))}</metadata>',
               f'<rect x="0" y="0" width="{self.W:g}" height="{self.H:g}" fill="{self.BG}"/>']
        pathways=[g for g in placed if g.structural.get("placement_kind")=="pathway"]
        others=[g for g in placed if g.structural.get("placement_kind")!="pathway"]
        for seq in (pathways, others):
            for g in seq:
                lines.append(f'<g id="{g.name}">')
                for p in g.primitives: lines.append(self.svg_primitive(p.svg))
                lines.append('</g>')
        lines.append('</svg>')
        return '\n'.join(lines)

    def svg_primitive(self,s):
        typ=s["type"]
        if typ=="rect":
            x=s["cx"]-s["width"]/2; y=s["cy"]-s["height"]/2
            attrs=[f'x="{x:.4f}"',f'y="{y:.4f}"',f'width="{s["width"]:.4f}"',f'height="{s["height"]:.4f}"',f'rx="{s.get("rx",0):.4f}"',f'fill="{s.get("fill","none")}"']
            if s.get("stroke")!="none": attrs += [f'stroke="{s["stroke"]}"',f'stroke-width="{s["stroke_width"]:.4f}"']
            return '<rect '+' '.join(attrs)+'/>'
        if typ=="circle":
            attrs=[f'cx="{s["cx"]:.4f}"',f'cy="{s["cy"]:.4f}"',f'r="{s["r"]:.4f}"',f'fill="{s.get("fill","none")}"']
            if s.get("stroke")!="none": attrs += [f'stroke="{s["stroke"]}"',f'stroke-width="{s["stroke_width"]:.4f}"']
            return '<circle '+' '.join(attrs)+'/>'
        if typ=="line":
            return f'<line x1="{s["x1"]:.4f}" y1="{s["y1"]:.4f}" x2="{s["x2"]:.4f}" y2="{s["y2"]:.4f}" stroke="{s["stroke"]}" stroke-width="{s["stroke_width"]:.4f}" stroke-linecap="{s.get("linecap","butt")}"/>'
        if typ=="polyline":
            pts=" ".join(f"{x:.4f},{y:.4f}" for x,y in s["points"])
            return f'<polyline points="{pts}" fill="none" stroke="{s["stroke"]}" stroke-width="{s["stroke_width"]:.4f}" stroke-linecap="{s.get("linecap","butt")}" stroke-linejoin="{s.get("linejoin","miter")}"/>'
        if typ=="quadratic":
            p0,q,p1=s["p0"],s["q"],s["p1"]
            return f'<path d="M {p0[0]:.4f} {p0[1]:.4f} Q {q[0]:.4f} {q[1]:.4f} {p1[0]:.4f} {p1[1]:.4f}" fill="none" stroke="{s["stroke"]}" stroke-width="{s["stroke_width"]:.4f}" stroke-linecap="round"/>'
        raise ValueError(typ)

    def render_batch(self,count,out_dir:Path,max_sample_restarts=1,skip_deadlocks=True,max_logical_samples=None,
                     collection_plan_attempts=128,calibration_rounds=96):
        out_dir.mkdir(parents=True,exist_ok=True)
        reports=[]; skipped=[]; logical_index=0
        if max_logical_samples is None:
            max_logical_samples=max(count*8,count)
        while len(reports)<count and logical_index<max_logical_samples:
            try:
                sample_restarts=max_sample_restarts if skip_deadlocks else max(256,max_sample_restarts)
                plan_attempts=collection_plan_attempts if skip_deadlocks else max(256,collection_plan_attempts)
                cal_rounds=calibration_rounds if skip_deadlocks else max(256,calibration_rounds)
                placed,report=self.generate_sample(logical_index,max_sample_restarts=sample_restarts,
                                                   collection_plan_attempts=plan_attempts,
                                                   calibration_rounds=cal_rounds)
            except RuntimeError:
                skipped.append(logical_index); logical_index+=1
                if skip_deadlocks: continue
                raise
            svg=self.svg_for(placed,report); out_index=len(reports)
            path=out_dir/f"pcb_v34_{out_index:02d}_seed_{report['seed']}.svg"; path.write_text(svg)
            (out_dir/f"pcb_v34_{out_index:02d}_report.json").write_text(json.dumps(report,indent=2))
            reports.append(report); logical_index+=1
        if len(reports)<count:
            raise RuntimeError(f"could only generate {len(reports)} valid samples before logical-sample budget was exhausted")
        return reports,skipped


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--width',type=int,default=1200); ap.add_argument('--height',type=int,default=1200)
    ap.add_argument('--seed',type=lambda x:int(x,0),default=None); ap.add_argument('--count',type=int,default=1)
    ap.add_argument('--main-scale',type=float,default=1.0,help='master geometry scale independent of canvas dimensions')
    ap.add_argument('--out-dir',type=Path,default=Path('v34_output'))
    ap.add_argument('--max-sample-restarts',type=int,default=1)
    ap.add_argument('--max-logical-samples',type=int,default=None)
    ap.add_argument('--collection-plan-attempts',type=int,default=128)
    ap.add_argument('--calibration-rounds',type=int,default=96)
    ap.add_argument('--pathway-debug-stage',choices=('corridors',),default=None)
    ap.add_argument('--no-skip-deadlocks',action='store_true')
    args=ap.parse_args()
    r=V34Renderer(args.width,args.height,args.seed,args.main_scale)
    r.pathway_debug_stage=args.pathway_debug_stage
    reports,skipped=r.render_batch(args.count,args.out_dir,max_sample_restarts=args.max_sample_restarts,
                                   skip_deadlocks=not args.no_skip_deadlocks,max_logical_samples=args.max_logical_samples,
                                   collection_plan_attempts=args.collection_plan_attempts,calibration_rounds=args.calibration_rounds)
    print(json.dumps(dict(base_seed=r.seed,reports=reports,skipped_logical_indices=skipped),indent=2))

if __name__=='__main__': main()
