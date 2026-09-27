#!/usr/bin/env python3
"""
Deterministic renderer for PCB Graphic Design Language v46 logical-viewBox, locality-preserving optimization, and exact-octilinear routing architecture.

Authority: chip_design_language.md
Now includes variance-driven pathways.

This is an implementation of the authoritative design sheet, not a replacement for it.
The implementation keeps all generation/validation logic in code so a fresh model does not
need to mentally simulate the renderer.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
from html import escape as xml_escape
import heapq
import json
import math
import secrets
import numpy as np
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from shapely import affinity
import shapely
from shapely.geometry import GeometryCollection, LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

MASK64 = (1 << 64) - 1

# Residual-fill control defaults.  The historical component phase samples 50..60% of
# post-MAIN residual service, then LOCAL samples 80..90% of what components leave.  At
# the midpoint convention that makes components 0.55 / (0.55 + 0.45*0.85) of the
# combined residual fill.  Keep this exact scalar public so CLI/API/docs agree.
DEFAULT_LOCAL_DENSITY = 1.0
DEFAULT_COMPONENT_DENSITY = 0.55 / (0.55 + (1.0 - 0.55) * 0.85)

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

    def random_many(self, n: int):
        """Return exactly the next ``n`` ``random()`` values with one vectorized SplitMix64 mix.

        This is sequence-identical to repeated ``random()`` calls.  It is used only where a
        caller already needs a bulk run of independent tie-break draws with no intervening RNG
        consumption.
        """
        n=int(n)
        if n <= 0:
            return np.empty(0,dtype=np.float64)
        steps=np.arange(1,n+1,dtype=np.uint64)
        states=np.uint64(self.state) + np.multiply(steps,np.uint64(0x9E3779B97F4A7C15),dtype=np.uint64)
        z=states.copy()
        z=np.multiply(z ^ (z >> np.uint64(30)),np.uint64(0xBF58476D1CE4E5B9),dtype=np.uint64)
        z=np.multiply(z ^ (z >> np.uint64(27)),np.uint64(0x94D049BB133111EB),dtype=np.uint64)
        z=z ^ (z >> np.uint64(31))
        self.state=int(states[-1])
        return (z >> np.uint64(11)).astype(np.float64) / float(1 << 53)

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
        # Planning-only BoundsGeom primitives are never rendered or fingerprinted.  Preserve
        # their immutable payload dictionaries by reference and transform only the AABB; this
        # removes thousands of dead SVG/signature copies from residual size-risk preflight.
        if _BOUNDS_ONLY and isinstance(g, BoundsGeom):
            b=g.bounds
            xs=[b[0]*scale+tx,b[2]*scale+tx]; ys=[b[1]*scale+ty,b[3]*scale+ty]
            return Primitive(self.kind,_bounds_geom((min(xs),min(ys),max(xs),max(ys))),self.svg,self.signature)
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
    _collision_collection: Any = field(default=None, repr=False)
    _bounds: Any = field(default=None, repr=False)
    _primitive_index: Any = field(default=None, repr=False)

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
    def collision_geom(self):
        """Set-equivalent primitive collection for collision tests without topology union."""
        if self._collision_collection is None:
            geoms=[box(*p.geom.bounds) if isinstance(p.geom,BoundsGeom) else p.geom for p in self.primitives]
            self._collision_collection=GeometryCollection(geoms) if geoms else GeometryCollection()
        return self._collision_collection

    @property
    def primitive_index(self):
        if self._primitive_index is None:
            b=self.bounds; span=max(b[2]-b[0],b[3]-b[1],1e-6)
            idx=SpatialHash(max(span/8.0,1e-6))
            for p in self.primitives: idx.insert(p,p.geom.bounds)
            self._primitive_index=idx
        return self._primitive_index

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
        # Component placement/calibration transforms thousands of candidate groups.  Apply the
        # same scalar coordinate operations to the complete Shapely geometry array in one pass
        # rather than one affinity dispatch per primitive.  Operation order matches the historical
        # Primitive.transformed path exactly: scale about (0,0), then translate.
        if (scale != 1.0 or tx or ty) and self.primitives and all(not isinstance(p.geom,BoundsGeom) for p in self.primitives):
            geoms=[p.geom for p in self.primitives]
            def _transform_coords(coords):
                out=coords.copy()
                if scale != 1.0:
                    out[:,0]*=scale; out[:,1]*=scale
                if tx:
                    out[:,0]+=tx
                if ty:
                    out[:,1]+=ty
                return out
            moved=shapely.transform(geoms,_transform_coords)
            ps=[]
            for p,g in zip(self.primitives,moved):
                ps.append(Primitive(p.kind,g,transform_svg(dict(p.svg),tx=tx,ty=ty,scale=scale),
                                    transform_signature(dict(p.signature),tx=tx,ty=ty,scale=scale)))
            out=Group(name or self.name,ps,dict(self.structural),list(self.intentional_contacts))
        else:
            out=Group(name or self.name,
                      [p.transformed(tx,ty,scale) for p in self.primitives],
                      dict(self.structural), list(self.intentional_contacts))
        # Uniform scale + translation transforms the group AABB exactly; preserve that tiny
        # immutable fact instead of re-querying every transformed Shapely primitive later.
        b=self.bounds
        x0=b[0]*scale+tx; x1=b[2]*scale+tx; y0=b[1]*scale+ty; y1=b[3]*scale+ty
        out._bounds=(min(x0,x1),min(y0,y1),max(x0,x1),max(y0,y1))
        return out

    def transformed_geometry_only(self, tx=0.0, ty=0.0, scale=1.0, name=None):
        """Transform collision geometry/bounds only for a placement probe.

        Rejected placement candidates never need transformed SVG/signature payloads.  They share
        their source payload dictionaries; a passing candidate is materialized through
        ``transformed`` before it is committed.
        """
        if (scale != 1.0 or tx or ty) and self.primitives and all(not isinstance(p.geom,BoundsGeom) for p in self.primitives):
            geoms=[p.geom for p in self.primitives]
            def _transform_coords(coords):
                out=coords.copy()
                if scale != 1.0:
                    out[:,0]*=scale; out[:,1]*=scale
                if tx:
                    out[:,0]+=tx
                if ty:
                    out[:,1]+=ty
                return out
            moved=shapely.transform(geoms,_transform_coords)
            ps=[Primitive(src.kind,g,src.svg,src.signature) for src,g in zip(self.primitives,moved)]
            out=Group(name or self.name,ps,dict(self.structural),list(self.intentional_contacts))
        else:
            out=Group(name or self.name,[Primitive(p.kind,p.geom,p.svg,p.signature) for p in self.primitives],
                      dict(self.structural),list(self.intentional_contacts))
        b=self.bounds
        x0=b[0]*scale+tx; x1=b[2]*scale+tx; y0=b[1]*scale+ty; y1=b[3]*scale+ty
        out._bounds=(min(x0,x1),min(y0,y1),max(x0,x1),max(y0,y1))
        return out

    def invalidate(self):
        self._union = None
        self._collision_collection = None
        self._bounds = None
        self._primitive_index = None

    def release_derived_caches(self, keep_bounds=True):
        """Release rebuildable GEOS/index state while preserving immutable primitives.

        V47 phase boundaries keep the finished primitive geometry authoritative, but derived
        unions, collision collections and primitive spatial indexes must not stay live merely
        because they were touched by an earlier phase. Bounds are tiny tuples and may be kept.
        """
        self._union = None
        self._collision_collection = None
        self._primitive_index = None
        if not keep_bounds:
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

    def remove(self, oid):
        """Remove one indexed object without rebuilding unrelated hash cells."""
        b=self.bounds.pop(oid,None)
        obj=self.objects.pop(oid,None)
        if b is None:
            return obj
        for c in self._cells_for(b):
            bucket=self.cells.get(c)
            if bucket is None:
                continue
            bucket.discard(oid)
            if not bucket:
                self.cells.pop(c,None)
        return obj

    def query(self, b):
        cs=self.cell_size
        ix0=math.floor(b[0]/cs); iy0=math.floor(b[1]/cs)
        ix1=math.floor(b[2]/cs); iy1=math.floor(b[3]/cs)
        query_cell_count=max(0,ix1-ix0+1)*max(0,iy1-iy0+1)
        ids=set()
        # Exact sparse-object shortcut.  For tiny immutable/static indexes a broad query can
        # cross dozens of empty hash cells even though only a handful of objects exist.  Scan
        # those object AABBs directly only when that is conservatively much cheaper than the
        # cell walk.  The final id set/AABB predicate is exactly the same.
        if self.objects and 2*len(self.objects) < query_cell_count:
            x0,y0,x1,y1=b
            for i,ib in self.bounds.items():
                if not (ib[2] < x0 or x1 < ib[0] or ib[3] < y0 or y1 < ib[1]):
                    ids.add(i)
        else:
            for ix in range(ix0,ix1+1):
                for iy in range(iy0,iy1+1):
                    ids.update(self.cells.get((ix,iy),()))
        x0,y0,x1,y1=b
        return [self.objects[i] for i in ids
                if not (self.bounds[i][2] < x0 or x1 < self.bounds[i][0] or
                        self.bounds[i][3] < y0 or y1 < self.bounds[i][1])]


def expand_bounds(b, d):
    return b[0]-d,b[1]-d,b[2]+d,b[3]+d

def point_bounds_distance(p,b):
    """Euclidean distance from a point to an axis-aligned bounds rectangle."""
    x,y=p
    dx=max(b[0]-x,0.0,x-b[2])
    dy=max(b[1]-y,0.0,y-b[3])
    return math.hypot(dx,dy)

def bounds_within_gap(a,b,gap):
    """Cheap exact broad-phase: whether two AABBs can be within ``gap``."""
    return not (a[2]+gap < b[0] or b[2]+gap < a[0] or a[3]+gap < b[1] or b[3]+gap < a[1])

def nearest_point_on_polyline_segments(point, points):
    """Exact Euclidean nearest point on a straight-segment polyline.

    This is mathematically equivalent to ``LineString.interpolate(LineString.project(Point))``
    for the non-degenerate straight segments emitted by the renderer, but avoids constructing
    GEOS objects in the sibling-embedding persistence hot path. Stable first-segment tie-breaking
    matches linear-reference traversal order.
    """
    px,py=point
    best=None
    best_d2=float('inf')
    for i,(a,b) in enumerate(zip(points,points[1:])):
        ax,ay=a; bx,by=b; vx=bx-ax; vy=by-ay
        den=vx*vx+vy*vy
        if den<=1e-24:
            q=(ax,ay)
        else:
            t=((px-ax)*vx+(py-ay)*vy)/den
            if t<=0.0: q=(ax,ay)
            elif t>=1.0: q=(bx,by)
            else: q=(ax+t*vx,ay+t*vy)
        dx=q[0]-px; dy=q[1]-py; d2=dx*dx+dy*dy
        if d2 < best_d2-1e-18:
            best_d2=d2; best=q
    if best is None:
        return tuple(points[0]) if points else tuple(point)
    return best

DIR8=[(1.0,0.0),(math.sqrt(0.5),-math.sqrt(0.5)),(0.0,-1.0),(-math.sqrt(0.5),-math.sqrt(0.5)),(-1.0,0.0),(-math.sqrt(0.5),math.sqrt(0.5)),(0.0,1.0),(math.sqrt(0.5),math.sqrt(0.5))]
SIDE_TO_DIR={"right":0,"top":2,"left":4,"bottom":6}

def dir_vec(idx:int)->Tuple[float,float]:
    return DIR8[idx%8]

def nearest_dir_index(dx:float, dy:float)->int:
    ang=(math.degrees(math.atan2(-dy, dx))+360.0)%360.0
    return int((ang+22.5)//45)%8

def exact_dir8_index(dx:float, dy:float, tol:float=1e-6):
    """Return the exact octilinear heading, or ``None`` for a non-0/45-degree segment.

    V39 uses this as a structural grammar primitive rather than relying on nearest-angle
    quantization.  The tolerance scales with segment magnitude only to absorb floating-point
    roundoff from line/ray intersections; it is far too small to reinterpret a visibly skewed
    segment as legal.
    """
    dx=float(dx); dy=float(dy)
    if not (math.isfinite(dx) and math.isfinite(dy)):
        return None
    ax=abs(dx); ay=abs(dy); scale=max(1.0,ax,ay); eps=max(1e-7,float(tol)*scale)
    if max(ax,ay)<=eps:
        return None
    if ay<=eps:
        return 0 if dx>0 else 4
    if ax<=eps:
        return 6 if dy>0 else 2
    if abs(ax-ay)<=eps:
        if dx>0 and dy<0: return 1
        if dx<0 and dy<0: return 3
        if dx<0 and dy>0: return 5
        if dx>0 and dy>0: return 7
    return None

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

    def __init__(self, renderer, sseed:int, placed:List[Group], enable_failure_certificates:bool=False):
        self.r=renderer; self.U=renderer.U; self.W=renderer.W; self.H=renderer.H
        self.sseed=sseed
        self.failure_certificate_enabled=bool(enable_failure_certificates)
        self.rng=SplitMix64(pathway_seed(sseed))
        self.chips=[g for g in placed if g.structural.get('placement_kind')=='chip']
        self.cols=[g for g in placed if g.structural.get('placement_kind')=='collection']
        self.isolated=[g for g in placed if g.structural.get('placement_kind')=='isolated']
        self.static=self.chips+self.cols+self.isolated
        # LOCAL composition excludes the interior of each already placed component
        # cluster.  This is built only for the post-component planner; MAIN has no
        # component territory to reserve.
        self.local_component_cluster_territory=[]
        self.local_component_cluster_territory_index=None
        # V37 local routing may start after dozens of components already exist.  Keep a spatial
        # broad-phase for static obstacles so exact component geometry is tested only nearby.
        self.static_index=SpatialHash(max(80.0*self.U,4.0*renderer.component_pathway_clearance))
        # Capacity ranking asks only about main-chip breathing room.  Keep a tiny immutable
        # chip-only index so those probes never enumerate primitive-expanded components merely
        # to discard them.  Exact routing admission continues to use the general static index.
        self.chip_capacity_index=SpatialHash(max(80.0*self.U,4.0*renderer.component_pathway_clearance))
        for gi,g in enumerate(self.static):
            if gi < len(self.chips):
                self.static_index.insert((gi,g),g.bounds)
                self.chip_capacity_index.insert((gi,g),g.bounds)
            else:
                # Do not repeatedly distance-test local candidates against a dissolved union of
                # a complex component collection.  Index the collection's exact primitives
                # individually under the same group id; min distance / intersection against the
                # primitive set is geometrically equivalent to testing the union, but avoids
                # rare GEOS topology pathologies on 50–70-primitive collections.
                for prim in g.primitives:
                    gb=prim.geom.bounds
                    if len(gb)==4 and all(math.isfinite(float(v)) for v in gb):
                        self.static_index.insert((gi,prim),gb)
        self.profile=self._sample_profile()
        self.module=self.profile['module_U']*self.U
        # V33 source egress is a hard family-level launch phase.
        self.launch_egress_modules=4.0
        self.main_launch_maturity_modules=4.0
        self.main_launch_preferred_terminal_modules=6.0
        self.source_egress_reservations=[]
        self.source_egress_by_owner={}
        self._protected_family_owners=set()
        self.source_egress_index=SpatialHash(max(80.0*self.U,3.0*self.module))
        self._active_head_index=None
        self.fronts:Dict[int,Dict[str,Any]]={}
        self.children_by_parent:Dict[int,set[int]]={}
        self.fragment_members:Dict[int,set[int]]={}
        self.fronts_by_side:Dict[Tuple[Any,Any,Any],set[int]]={}
        self.next_front_id=0
        self.next_trace_id=0
        self.main_launch_trace_ids=set()
        # A wide recovery fragmentation must not let an entire source side die together just
        # beyond the ordinary four-module maturity floor.  The designated trace id is carried
        # independently of front ownership so later rebases/branches cannot lose its rendered
        # side-progress obligation.
        self.main_side_progress_trace_ids=set()
        self.path_segments=[]
        # Per-front ownership makes rollback proportional to the trace history being rewound,
        # rather than rescanning the entire board history for each removed gesture.
        self.path_segments_by_front:Dict[int,list]= {}
        self._lane_cache_version=0
        self._lane_cache_built_version=-1
        self._lane_cache_records=[]
        self._lane_cache_index=None
        self._lane_cache_tree=None
        self._lane_cache_geoms=[]
        self._persistence_materialized_cache=None
        self.frozen_main_render_records=[]
        self.max_committed_path_thickness=0.0
        self.path_index=SpatialHash(max(80*self.U,3*self.module))
        self._path_index_generation=0
        self.connection_pairs:Dict[Tuple[int,int],Tuple[float,float]]={}
        self.branch_junction_pairs:Dict[Tuple[int,int],Tuple[float,float]]={}
        self.connected_trace_ids=set()
        self.cross_chip_connected_trace_ids=set()
        self.coverage_cells=set()
        self.coverage_cell_counts={}
        self.local_gap_open_cells=set()
        # Physical service and route opportunity are different fields.  Policy seams and
        # component-cluster interiors restrict route construction, not the service audit.
        self.local_gap_route_cells=set()
        self.local_gap_route_domain_by_cell={}
        self.local_gap_regions=[]
        self.local_gap_region_by_cell={}
        self.local_fill_cluster_root_counts={}
        # Route ownership is fixed by connected physical rooms and composition owners.
        self.local_route_clusters={}
        # Four immutable projection orders per residual region.  Dynamic coverage only removes
        # eligibility, so these arrays stay valid and let large-room targeting inspect bounded
        # geometric extremes instead of rescanning every cell for every trace decision.
        self.local_gap_directional_cells={}
        # LOCAL-1A: residual rooms are partitioned once into fixed grid chunks. Targeting then
        # consumes bounded local chunk state instead of rescanning every cell in the room for
        # every local-line retarget. The immutable chunk membership is built with the residual
        # field; untouched membership is maintained incrementally as service is committed.
        self.local_gap_chunk_span=6
        self.local_gap_chunk_cells_by_region={}
        self.local_gap_chunk_key_by_cell={}
        self.local_gap_untouched_by_chunk={}
        self.local_gap_chunk_cycle_by_region={}
        self.local_gap_retarget_chunk_epoch={}
        self.local_gap_coverage_cells=set()
        self.local_gap_coverage_touched_cells=set()
        self.local_gap_coverage_mask_by_cell={}
        # Exact running numerator for the 16-subcell local service metric.  Every mutation of
        # the mask map updates this count, so reading service fraction is O(1) rather than a
        # whole-field scan.
        self.local_gap_served_subcell_count=0
        # LOCAL service is accounted against the canonical post-MAIN residual service field.
        # The physical post-component open field remains the routing domain, but it is not a new
        # percentage denominator.  generate_local_gap_pathways() supplies the canonical count.
        self.local_gap_service_denominator_cell_count=None
        # V44 fine-scale bookkeeping: keep the complement incrementally instead of rebuilding
        # ``open - touched`` for every local target.  Per-region sets preserve exactly the same
        # target eligibility while making cost proportional to the room being queried.
        self.local_gap_untouched_cells=set()
        self.local_gap_untouched_by_region={}
        self.local_gap_region_touch_version={}
        self._local_gap_new_touch_capture=None
        # Hard-floor-only retarget set: lets the ordinary router revisit partially served
        # cells when the area-based service audit is still below its floor.
        self.local_gap_retarget_cells=set()
        self.local_gap_target_fraction=0.0
        self.local_gap_target_count=0
        self.local_gap_special_probability=None
        # Deterministic geometry-work budget.  Default batch mode skips a pathological logical
        # sample once it has consumed substantially more exact gesture checks than healthy boards.
        # This is count-based (never wall-clock based), so seeded geometry remains deterministic.
        self.gesture_check_budget=int(getattr(renderer,'main_pathway_gesture_check_budget',52000))
        self.gesture_check_count=0
        self._capture_gesture_failure_cert=False
        self._last_gesture_failure_cert=None
        self.grid_nx,self.grid_ny=self.r._aspect_grid_shape(40)
        self.grid_n=max(self.grid_nx,self.grid_ny)  # legacy diagnostic compatibility
        self.congestion_grid=[[0 for _ in range(self.grid_nx)] for _ in range(self.grid_ny)]
        self._congestion_cache={}
        self.coverage_grid_nx,self.coverage_grid_ny=self.r._aspect_grid_shape(12)
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
            pathway_persistence_shared_tick_budget=self.profile.get('persistence_shared_ticks',0),
            pathway_persistence_shared_tick_count=0,
            pathway_persistence_shared_rebuild_count=0,
            pathway_persistence_hard_debt_peak=0,
            pathway_persistence_horizon_unresolved_trace_count=0,
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
            pathway_gesture_clear_check_count=0,
            pathway_gesture_clear_check_budget=self.gesture_check_budget,
        )

    @staticmethod
    def _bounds_within_gap(a,b,gap):
        """Planner-local exact AABB broad-phase wrapper shared by V46 spatial hot paths."""
        return bounds_within_gap(a,b,gap)

    @staticmethod
    def _indexed_static_bounds(obj):
        """Return bounds for either a Group or an indexed Primitive static record."""
        b=getattr(obj,'bounds',None)
        return b if b is not None else obj.geom.bounds

    def _sample_profile(self):
        """One coherent variance profile for the whole board, not per-trace noise."""
        rng=self.rng
        # Preserve the historical RNG draw order byte-for-byte.  Item 4 changes only the values
        # derived from the already-existing route-life draws; it must not reshuffle the board's
        # stochastic profile or downstream front seeds merely because the knob exists.
        module_U=rng.uniform(31.0,39.0)
        preferred_run_modules=2+int(rng.random()*3)
        turn_appetite=rng.uniform(.40,.64)
        branch_appetite=rng.uniform(.34,.54)
        branch_multiplier=rng.uniform(1.50,1.80)
        connection_appetite=rng.uniform(.88,.99)
        exit_inclination=rng.uniform(.25,.44)
        outward_bias=rng.uniform(.44,.70)
        historical_max_rounds=48+int(rng.random()*9)
        persistence_shared_ticks=10+int(rng.random()*3)
        # Item 4 is a workload/geometry knob, not a routing-algorithm change.  The historical
        # ordinary clock remains untouched until the requested whole-route residency can no
        # longer physically fit inside it.  Only then extend that same shared clock by the
        # bounded amount required to let the existing per-front journey target be realised.
        # Historical MAIN journey ceilings are 13 gestures (11 + the exit/explore bonus).
        run_factor=2.0*float(self.r.main_run_length_multiplier)
        required_main_rounds=int(math.ceil(13.0*run_factor))+12
        return dict(
            module_U=module_U,
            preferred_run_modules=preferred_run_modules,
            turn_appetite=turn_appetite,
            branch_appetite=branch_appetite,
            branch_multiplier=branch_multiplier,
            connection_appetite=connection_appetite,
            exit_inclination=exit_inclination,
            # Main routing still has no component intent.  V37's later local planner receives
            # frozen components as static obstacles but does not seek or attach to them.
            outward_bias=outward_bias,
            # V21 gives persistence/recovery a little more room so a lane that is still
            # visually embedded between continuing siblings is not forced to die merely
            # because the global planning horizon arrived.
            # V47 root-cause correction: V45 cut the ordinary shared-clock lifetime to 24-28
            # rounds as a speed shortcut, which changed behavior and caused premature route deaths.
            # Restore the original 48-56 ordinary opportunity window, independent of scale/aspect.
            # Performance must come from locality, exact broad phases and incremental state—not
            # from shortening a front's route-life grammar.
            max_rounds=max(historical_max_rounds,required_main_rounds),
            historical_max_rounds=historical_max_rounds,
            main_run_residency_factor=run_factor,
            reroute_budget=7,
            late_life_branch_start=.60,
            late_life_branch_multiplier=1.50,
            persistence_tail_rounds=0,
            # Only a short debt-filtered exceptional tail remains after ordinary route life.
            # This is not the former 32-40-tick compensating recovery campaign.
            persistence_shared_ticks=persistence_shared_ticks,
        )

    def _new_rng(self):
        return SplitMix64(self.rng.next_u64())

    def _cohort_slices(self, count:int, rng:SplitMix64):
        """Partition a side bus into several contiguous, visually useful cohorts.

        MAIN launches are normally 9--24 traces.  The old greedy 3--5 lane chunker could turn
        a nine-line side into only two giant routing objects, which made the subsequent bus read
        as one claustrophobic ribbon.  Choose a seeded 3--7 cohort count around four lanes per
        cohort, then balance sizes.  This changes topology variety without changing trace count.
        """
        count=int(count)
        if count<=1: return [list(range(max(0,count)))]
        if count<6:
            k=2
        else:
            base=max(3,min(7,int(round(count/4.0))))
            wiggle=(-1,0,1)[int(rng.random()*3)]
            k=max(3,min(7,count,base+wiggle))
            k=max(k,int(math.ceil(count/5.0)))
            # Keep ordinary MAIN cohorts at two or more lanes whenever the population permits.
            if count>=2*k:
                pass
            else:
                k=max(2,count//2)
        q,rem=divmod(count,k)
        sizes=[q]*k
        order=list(range(k))
        # Seed which cohorts receive the remainder without disturbing contiguity/order itself.
        for i in range(len(order)-1,0,-1):
            j=int(rng.random()*(i+1)); order[i],order[j]=order[j],order[i]
        for i in order[:rem]: sizes[i]+=1
        out=[]; start=0
        for take in sizes:
            out.append(list(range(start,start+take))); start+=take
        return out

    def _routing_horizon(self):
        """One local design-territory span in canvas units.

        Zooming out exposes more territories; it must not silently make every individual route
        chase a target across all newly exposed territory.  Global coverage comes from the larger
        primary population.  Route journey statistics remain local in design units.
        """
        return max(12.0*self.module,float(self.r.S))

    def _sample_intent(self, rng:SplitMix64, center, initial_dir, allow_component=True):
        # Route-first architecture: only the main chips exist as static board objects while
        # main routes are planned.  Intent probabilities remain stationary; only target distance
        # is design-local so a zoomed-out board behaves like more board, not longer individual
        # routes stretched across the enlarged logical field.
        p_exit=max(.16,.72*self.profile['exit_inclination'])
        p_connect=.38+.30*self.profile['connection_appetite']
        p_explore=max(.05,1.0-p_exit-p_connect)
        kind=rng.weighted([('connect',p_connect),('exit',p_exit),('explore',p_explore)])
        target=None
        if kind=='exit':
            target=self._distant_exit_target(center,rng)
            if target is None:
                kind='explore'
                target=self._underused_target(center,rng)
        elif kind=='explore':
            target=self._underused_target(center,rng)
        return kind,target

    def _distant_exit_target(self,center,rng:SplitMix64):
        """Choose a reachable frame objective within one design-local routing horizon.

        On a zoomed-out board, interior networks are no longer coerced into crossing several
        logical territories merely to preserve a scale-1 exit ratio.  Chips close enough to a
        real frame edge still receive the same exit behavior.
        """
        margin=rng.uniform(1.1,1.8)*self.module
        horizon=self._routing_horizon()
        cx,cy=center
        candidates=[]
        # Sample edge coordinates near the launch projection instead of anywhere on a long frame.
        for _ in range(3):
            y=min(self.H,max(0.0,cy+rng.uniform(-.72,.72)*horizon))
            x=min(self.W,max(0.0,cx+rng.uniform(-.72,.72)*horizon))
            candidates.extend([(-margin,y),(self.W+margin,y),(x,-margin),(x,self.H+margin)])
        reachable=[]
        for q in candidates:
            d=math.hypot(q[0]-cx,q[1]-cy)
            if .22*horizon <= d <= 1.10*horizon:
                reachable.append((d,rng.random(),q))
        if not reachable:
            return None
        reachable.sort(key=lambda x:(-x[0],x[1]))
        return reachable[int(rng.random()*min(4,len(reachable)))][2]

    def _underused_target(self, center, rng:SplitMix64):
        """Choose a design-local underused target using the spatial index for static clearance."""
        candidates=[]
        horizon=self._routing_horizon()
        cx,cy=center
        for _ in range(16):
            d=rng.uniform(.24,.82)*horizon
            ang=rng.uniform(0.0,2.0*math.pi)
            x=min(self.W,max(0.0,cx+math.cos(ang)*d))
            y=min(self.H,max(0.0,cy+math.sin(ang)*d))
            actual=math.hypot(x-cx,y-cy)
            if actual < .18*horizon:
                continue
            cell=self._coverage_cell12((x,y))
            used=1 if cell in self.coverage_cells else 0
            scan=6.0*self.module
            static_clear=scan
            seen=set()
            for gi,g in self.static_index.query((x-scan,y-scan,x+scan,y+scan)):
                # Target ranking is approximate only; final route legality is exact.
                key=(gi,id(g))
                if key in seen: continue
                seen.add(key)
                static_clear=min(static_clear,point_bounds_distance((x,y),self._indexed_static_bounds(g)))
                if static_clear<=0.0: break
            candidates.append((used,-min(static_clear,scan),rng.random(),(x,y)))
        if not candidates:
            # Deterministic local fallback, still bounded by one design territory.
            d=.45*horizon; direction=int(rng.random()*8)%8
            x,y=point_along_dir(center,direction,d)
            return (min(self.W,max(0.0,x)),min(self.H,max(0.0,y)))
        candidates.sort(key=lambda x:(x[0],x[1],x[2]))
        return candidates[0][3]

    def _local_route_cluster_for_source(self,p,create=False):
        """Assign a LOCAL root to one precomputed connected route domain."""
        return self.local_gap_route_domain_by_cell.get(self._gap_cell(p))

    def _make_front(self, *, ids, chip, side, side_index, path, direction, offsets,
                    thicknesses, prefixes, rng, depth=0, intent=None, target=None,
                    parent=None, branch_turn=None, fan_group=None,
                    forced_straight_modules=None,forced_turn_modules=None,
                    local_cluster_id=None):
        fid=self.next_front_id; self.next_front_id+=1
        if intent is None:
            intent,target=self._sample_intent(rng,path[-1],direction)
        historical_max_gestures=7+int(rng.random()*5)
        if intent in ('exit','explore'):
            historical_max_gestures+=2
        # The run-length knob scales only the existing whole-route MAIN residency pool.  It does
        # not alter per-gesture module lengths, turn grammar, proposal breadth, clearance logic,
        # or LOCAL routing.  Multiplier .5 is therefore the historical MAIN journey distribution;
        # the new default 1.0 is exactly twice that sampled residency, and 3.0 is six times it.
        is_main=(chip < len(self.chips))
        run_factor=(2.0*float(self.r.main_run_length_multiplier)) if is_main else 1.0
        max_gestures=max(1,int(math.floor(historical_max_gestures*run_factor+.5)))
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
            travel=0.0,max_gestures=max_gestures,base_max_gestures=max_gestures,
            historical_max_gestures=historical_max_gestures,main_run_residency_factor=run_factor,
            journey_limit_pending=False,failures=0,turn_cooldown=0,
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
        if parent is not None and parent in self.fronts and self.fronts[parent].get('local_gap'):
            f['local_gap']=True
            f['local_fill_cluster_id']=self.fronts[parent].get('local_fill_cluster_id')
            f['local_fill_route_tile']=self.fronts[parent].get('local_fill_route_tile')
        elif side=='local':
            f['local_gap']=True
            f['local_fill_cluster_id']=(local_cluster_id if local_cluster_id is not None else
                                        self._local_route_cluster_for_source(path[-1],create=False))
            f['local_fill_route_tile']=None
        if f.get('local_gap') and parent is None:
            cid=f.get('local_fill_cluster_id')
            if cid is not None:
                self.local_fill_cluster_root_counts[cid]=self.local_fill_cluster_root_counts.get(cid,0)+1
        self.fronts_by_side.setdefault((chip,side_index,side),set()).add(fid)
        if parent is not None: self.children_by_parent.setdefault(parent,set()).add(fid)
        return f

    def _drop_front(self,fid):
        f=self.fronts.pop(fid,None)
        if f is None: return None
        if f.get('local_gap') and f.get('parent') is None:
            cid=f.get('local_fill_cluster_id')
            if cid is not None:
                self.local_fill_cluster_root_counts[cid]=max(0,self.local_fill_cluster_root_counts.get(cid,0)-1)
                # The immutable route domain survives failed trial fronts.
        parent=f.get('parent')
        if parent is not None:
            kids=self.children_by_parent.get(parent)
            if kids is not None:
                kids.discard(fid)
                if not kids: self.children_by_parent.pop(parent,None)
        fragment_group=f.get('fragment_group')
        if fragment_group is not None:
            members=self.fragment_members.get(fragment_group)
            if members is not None:
                members.discard(fid)
                if not members: self.fragment_members.pop(fragment_group,None)
        side_key=(f.get('chip'),f.get('side_index'),f.get('side'))
        side_members=self.fronts_by_side.get(side_key)
        if side_members is not None:
            side_members.discard(fid)
            if not side_members: self.fronts_by_side.pop(side_key,None)
        return f

    def _front_has_children(self,fid):
        return bool(self.children_by_parent.get(fid))

    # ----------------------- V22 bounded holistic layer -----------------------
    def _grid_cell(self,p):
        x,y=p
        return (min(self.grid_nx-1,max(0,int(self.grid_nx*x/max(self.W,1e-9)))),
                min(self.grid_ny-1,max(0,int(self.grid_ny*y/max(self.H,1e-9)))))

    def _grid_add_segment(self,a,b,delta=1):
        L=math.hypot(b[0]-a[0],b[1]-a[1]); steps=max(1,int(math.ceil(L/max(.55*self.module,1e-9))))
        seen=set()
        for k in range(steps+1):
            t=k/steps; cell=self._grid_cell((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
            if cell in seen: continue
            seen.add(cell); x,y=cell
            old=self.congestion_grid[y][x]
            new=max(0,old+int(delta))
            if new!=old:
                self.congestion_grid[y][x]=new
                # A cached 3x3 weighted neighborhood depends only on cells at Chebyshev
                # distance <=1. Mutating one congestion cell therefore invalidates exactly
                # the nine query cells whose result can change—never the rest of the board.
                cache=self._congestion_cache
                for qy in range(max(0,y-1),min(self.grid_ny,y+2)):
                    for qx in range(max(0,x-1),min(self.grid_nx,x+2)):
                        cache.pop((qx,qy),None)

    def _rebuild_congestion_grid(self):
        self.congestion_grid=[[0 for _ in range(self.grid_nx)] for _ in range(self.grid_ny)]
        self._congestion_cache.clear()
        for rec in self.path_segments:
            if not rec.get('_retired'):
                self._grid_add_segment(rec['start'],rec['end'])

    def _congestion_at_cell(self,gx,gy):
        key=(gx,gy); cached=self._congestion_cache.get(key)
        if cached is not None:
            return cached
        val=0.0; wsum=0.0
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                x,y=gx+dx,gy+dy
                if 0<=x<self.grid_nx and 0<=y<self.grid_ny:
                    w=1.0 if dx==0 and dy==0 else .45
                    val+=w*self.congestion_grid[y][x]; wsum+=w
        out=val/max(wsum,1e-9); self._congestion_cache[key]=out
        return out

    def _congestion_at(self,p):
        gx,gy=self._grid_cell(p)
        return self._congestion_at_cell(gx,gy)

    def _refresh_lifecycle(self,f):
        if f.get('status')!='active': f['lifecycle']='TERMINAL'
        elif f.get('round_connection_peer') is not None: f['lifecycle']='CONNECTION_PENDING'
        elif self._source_egress_pending(f): f['lifecycle']='LAUNCHING'
        elif f.get('branch_stage') is not None or self._launch_fan_ready(f) or (f.get('recovery_fragment_child') and f.get('local_gestures',0)==0): f['lifecycle']='STRUCTURAL_TRANSITION'
        elif f.get('reroute_pending') or f.get('reroute_mode_rounds',0)>0 or f.get('quality_repair_pending'): f['lifecycle']='RECOVERING'
        elif f.get('gestures',0)<3 or f.get('travel',0.0)<5*self.module: f['lifecycle']='LAUNCHING'
        else: f['lifecycle']='NORMAL'
        return f['lifecycle']

    def _needs_holistic(self,f):
        life=self._refresh_lifecycle(f)
        if life in ('LAUNCHING','STRUCTURAL_TRANSITION','CONNECTION_PENDING','RECOVERING'): return True
        if self._main_side_progress_debt(f): return True
        return f.get('failures',0)>0 or self._congestion_at(f['path'][-1])>=1.8

    def _future_options(self,f,p,limit=5):
        """Bounded exact shortlist used only for fronts that need holistic foresight.

        Lookahead is a ranking heuristic, not a legality gate for the committed gesture.  V45
        first ranks the tiny six-option horizon with the existing congestion score, then spends
        exact thick-geometry checks on the three most promising futures.  If all three are
        blocked, the remaining candidates are checked until one legal escape is found.  This
        preserves the no-false-dead-end purpose of lookahead while avoiding six GEOS corridor
        audits for every young fine-scale front on an otherwise open board.
        """
        tf=dict(f); tf['path']=list(f['path'])+[p['end']]; tf['dir']=p['dir']
        tf['gestures']=f['gestures']+1; tf['local_gestures']=f['local_gestures']+1
        future_failure_certs=None
        future_success_cache=None
        if not f.get('local_gap'):
            success_head=self._proposal_reuse_front_state(f)
            if f.get('_future_success_cache_head')!=success_head:
                f['_future_success_cache_head']=success_head; f['_future_success_cache']={}
            future_success_cache=f.setdefault('_future_success_cache',{})
        if self.failure_certificate_enabled:
            prev=(f['path'][-2] if len(f.get('path',()))>=2 else None); start=f['path'][-1]
            future_head=((prev,start),f.get('branch_stage'),int(f.get('local_gestures',0)),f.get('parent'),
                         bool(f.get('recovery_fragment_child')),f.get('fan_group'),bool(f.get('local_gap')),tuple(f.get('ids',())))
            if f.get('_future_failure_cert_head')!=future_head:
                f['_future_failure_cert_head']=future_head; f['_future_failure_cert_cache']={}
            future_failure_certs=f.setdefault('_future_failure_cert_cache',{})
        if f.get('travel',0.0)<5*self.module:
            # Keep source-egress semantics available while evaluating a genuinely young front.
            tf['gestures']=0
        prelim=[]
        order=0
        for d in (p['dir'],(p['dir']-1)%8,(p['dir']+1)%8):
            for modules in (2,3):
                end=point_along_dir(p['end'],d,modules*self.module)
                self.stats['pathway_lookahead_evaluation_count']+=1
                if self._outside_limit(end):
                    order+=1; continue
                if self._candidate_loop_risk(tf,d,end):
                    order+=1; continue
                score=-.75*self._congestion_at(end)
                if not (0<=end[0]<=self.W and 0<=end[1]<=self.H): score+=.6
                prelim.append((score,order,d,modules,end))
                order+=1
        prelim.sort(key=lambda x:(-x[0],x[1]))
        out=[]
        # Three exact futures are enough to evaluate direction diversity on the normal path.
        # Only when all of them are physically blocked do we inspect the lower-ranked residue,
        # so the heuristic never fabricates a dead end merely to save work.
        first_budget=min(3,len(prelim))
        for rank,rec in enumerate(prelim):
            if rank>=first_budget and out:
                break
            score,_order,d,modules,end=rec
            allow=(tf.get('intent')=='exit' or tf.get('gestures',0)>=2 or
                   self._forward_frame_distance(p['end'],d)<=2.5*self.module)
            fkey=(round(p['start'][0],6),round(p['start'][1],6),round(p['end'][0],6),round(p['end'][1],6),
                  int(p['dir']),int(p['modules']),int(d),int(modules),round(end[0],6),round(end[1],6),bool(allow))
            success=(future_success_cache.get(fkey) if future_success_cache is not None else None)
            if success is not None:
                cached_geom,cached_sig=success
                if cached_sig==self._main_dynamic_leg_dependency_signature(cached_geom.bounds):
                    self.stats['pathway_future_success_proof_hit_count']=self.stats.get('pathway_future_success_proof_hit_count',0)+1
                    out.append((score,d,modules,end,cached_geom))
                    if len(out)>=limit:
                        break
                    continue
                future_success_cache.pop(fkey,None)
            cert=(future_failure_certs.get(fkey) if future_failure_certs is not None else None)
            if cert is not None:
                kind,obj=cert
                if (kind in ('static','extra') or (kind=='path' and not obj.get('_retired')) or
                    (kind=='grammar' and obj==self._local_visible_state_signature(tf))):
                    self.stats['pathway_future_failure_certificate_hit_count']=self.stats.get('pathway_future_failure_certificate_hit_count',0)+1
                    if kind=='grammar':
                        self.stats['pathway_future_local_visible_failure_certificate_hit_count']=self.stats.get('pathway_future_local_visible_failure_certificate_hit_count',0)+1
                    continue
                future_failure_certs.pop(fkey,None); cert=None
            if not self._local_visible_candidate_ok(tf,end):
                self._consume_gesture_check()
                self.stats['pathway_future_local_visible_preflight_reject_count']=self.stats.get('pathway_future_local_visible_preflight_reject_count',0)+1
                if future_failure_certs is not None:
                    future_failure_certs[fkey]=('grammar',self._local_visible_state_signature(tf))
                    self.stats['pathway_future_local_visible_failure_certificate_store_count']=self.stats.get('pathway_future_local_visible_failure_certificate_store_count',0)+1
                continue
            # Construct exact corridor geometry only after a valid failure certificate and the
            # board-independent visible-lane grammar have both been ruled out.
            geom=self._corridor_geom(tf,p['end'],end)
            if future_failure_certs is None:
                clear=self._gesture_clear(tf,p['end'],end,geom,allow_outside=allow,extra_segments=(p['geom'],),local_grammar_prechecked=True)
            else:
                self._capture_gesture_failure_cert=True
                try:
                    clear=self._gesture_clear(tf,p['end'],end,geom,allow_outside=allow,extra_segments=(p['geom'],),local_grammar_prechecked=True)
                finally:
                    self._capture_gesture_failure_cert=False
            if not clear:
                if future_failure_certs is not None and self._last_gesture_failure_cert is not None:
                    future_failure_certs[fkey]=self._last_gesture_failure_cert
                    self.stats['pathway_future_failure_certificate_store_count']=self.stats.get('pathway_future_failure_certificate_store_count',0)+1
                continue
            out.append((score,d,modules,end,geom))
            if future_success_cache is not None:
                future_success_cache[fkey]=(geom,self._main_dynamic_leg_dependency_signature(geom.bounds))
                self.stats['pathway_future_success_proof_store_count']=self.stats.get('pathway_future_success_proof_store_count',0)+1
            if len(out)>=limit:
                break
        return out

    def _lookahead_adjust(self,f,p):
        opts=self._future_options(f,p)
        p['future_option_count']=len(opts)
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
            if self._gesture_clear(tf,b,c,g2,allow_outside=(allow or child.get('gestures',0)>=1)):
                return True
        return False

    def _interroute_gap_for_fronts(self,f,g=None,other_thickness=None,other_local=False,other_cluster_id=None):
        gap=self.r.pathway_interroute_keepout
        local=bool(f.get('local_gap')) or bool(g and g.get('local_gap')) or bool(other_local)
        if not local:
            return gap
        t1=max((f['thicknesses'][i] for i in f.get('ids',())),default=2.55*self.U)
        if g is not None:
            t2=max((g['thicknesses'][i] for i in g.get('ids',())),default=t1)
        else:
            t2=float(other_thickness if other_thickness is not None else t1)
        mean=.5*(t1+t2)
        gap=max(gap,self.r.local_gap_line_edge_gap_factor*mean)
        return gap

    def _proposal_conflict_geom(self,p,f):
        cached=p.get('_conflict_geom')
        if cached is not None:
            return cached
        cached=p['geom'].difference(Point(p['start']).buffer(self._front_half_width(f)+1.5*self.U,quad_segs=6))
        p['_conflict_geom']=cached
        return cached

    def _proposal_pair_conflicts(self,p,q):
        f=self.fronts[p['front']]; g=self.fronts[q['front']]
        if self._same_fan_rebase_compatible(f,q['front']) and q['dir']==p['dir']: return False
        gap=self._interroute_gap_for_fronts(f,g)
        # Exact no-conflict rejection before either start-disk difference or GEOS distance.
        if not bounds_within_gap(p['geom'].bounds,q['geom'].bounds,gap): return False
        a=self._proposal_conflict_geom(p,f)
        b=self._proposal_conflict_geom(q,g)
        if a.is_empty or b.is_empty or not bounds_within_gap(a.bounds,b.bounds,gap): return False
        return a.intersects(b) or a.distance(b)<gap

    def _future_conflict(self,p,q):
        f=self.fronts[p['front']]; g=self.fronts[q['front']]
        gap=self._interroute_gap_for_fronts(f,g)
        # Same-round arbitration used to dispatch GEOS even for proposals whose AABBs were
        # separated by many local modules.  At true zoom-out population that hidden all-pairs
        # tax dominates late rounds.  Bounds rejection is mathematically exact and changes no
        # conflict result.
        pa=p.get('future_geom',p['geom']); qb=q.get('future_geom',q['geom'])
        primary_possible=bounds_within_gap(p['geom'].bounds,q['geom'].bounds,gap)
        future_possible=bounds_within_gap(pa.bounds,qb.bounds,gap)
        if not primary_possible and not future_possible: return False
        if primary_possible and self._proposal_pair_conflicts(p,q): return True
        if (f.get('parent') is not None and f.get('parent')==g.get('parent') and
                f.get('fan_group')==g.get('fan_group') and f.get('fan_group') is not None): return False
        if not future_possible: return False
        return pa.intersects(qb) or pa.distance(qb)<gap

    def _variant_pools_conflict(self,va,vb):
        """Whether any viable proposal pair couples two fronts into one local transaction."""
        for p in va[:3]:
            for q in vb[:3]:
                if self._future_conflict(p,q):
                    return True
        return False

    def _conflict_groups(self,variant_map):
        """Return all local same-round conflict components from one immutable snapshot.

        Proposal pools are indexed by their exact future-geometry bounds.  Earlier versions
        expanded every occupied grid bucket into an all-pairs set first; that was equivalent at
        scale 1 but became the dominant late-round cost once true zoom-out exposed hundreds of
        simultaneous fronts.  The spatial query below enumerates only pool bounds that can
        actually approach within the route moat, then retains the same exact geometry predicate.
        """
        ids=sorted(variant_map); adj={i:set() for i in ids}
        if len(ids)<2: return []
        pad=max(self.r.pathway_interroute_keepout,1.5*self.module)
        cell=max(2.5*self.module,1.0)
        def pool_bounds(pool):
            bs=[p.get('future_geom',p['geom']).bounds for p in pool[:3]]
            return (min(b[0] for b in bs),min(b[1] for b in bs),max(b[2] for b in bs),max(b[3] for b in bs))
        pb={fid:pool_bounds(variant_map[fid]) for fid in ids}
        index=SpatialHash(cell)
        for fid in ids:
            index.insert(fid,pb[fid])
        for a in ids:
            for b in sorted(x for x in index.query(expand_bounds(pb[a],pad)) if x>a):
                if not bounds_within_gap(pb[a],pb[b],pad):
                    continue
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
        """Bounded deterministic joint assignment from one immutable round snapshot.

        Main-network groups retain the exhaustive transactional solver.  Dense local-only groups
        use an explicit HOLD scheduler instead: all fillers proposed from the same snapshot, then
        a deterministic maximum-quality compatible subset advances while the rest hold this tick.
        This avoids spending main-network causal/permutation budgets on decorative residual fill.
        """
        group=sorted(group)
        pools={fid:list(variant_map[fid][:3]) for fid in group}
        if group and all(self.fronts[fid].get('local_gap') for fid in group):
            # Local fronts are independent peers; HOLD is a first-class atomic outcome.  Use a
            # rotating deterministic fairness key so a repeatedly-conflicted filler cannot be
            # permanently starved by front-id/order.  Every chosen proposal is still pairwise
            # exact-checked before the single atomic commit.
            candidates=[]
            for fid in group:
                f=self.fronts[fid]
                streak=int(f.get('local_hold_streak',0))
                for rank,p in enumerate(pools[fid][:2]):
                    # Long-held fronts get first opportunity; then proposal score/variant rank.
                    key=(-streak,-float(p.get('score',0.0)),rank,
                         mix_once(self.sseed ^ ((fid+1)<<19) ^ ((int(f.get('_routing_round',0))+1)<<43)))
                    candidates.append((key,fid,p))
            candidates.sort(key=lambda z:z[0])
            chosen=[]; moved=set()
            for _key,fid,p in candidates:
                if fid in moved: continue
                if any(self._future_conflict(p,q) for q in chosen): continue
                chosen.append(p); moved.add(fid)
            held=0
            for fid in group:
                f=self.fronts[fid]
                if fid in moved:
                    f['local_hold_streak']=0
                else:
                    f['local_hold_streak']=int(f.get('local_hold_streak',0))+1; held+=1
            if held:
                self.stats['pathway_local_gap_hold_round_count']+=1
                self.stats['pathway_local_gap_hold_front_count']+=held
            self.stats['pathway_conflict_combination_count']+=len(candidates)
            self.stats['pathway_conflict_region_count']+=1
            self.stats['pathway_conflict_region_front_count']+=len(group)
            return sorted(chosen,key=lambda p:p['front']) if chosen else None
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
            recovery_family=(main_family and any(self.fronts[fid].get('recovery_fragment_child') for fid in group))
            young_structural={fid for fid in group if (not self.fronts[fid].get('local_gap') and
                              self.fronts[fid].get('parent') is not None and
                              self._refresh_lifecycle(self.fronts[fid])=='STRUCTURAL_TRANSITION' and
                              self.fronts[fid].get('branch_stage')==0 and
                              int(self.fronts[fid].get('local_gestures',0))<=1 and
                              self.fronts[fid].get('travel',0.0)<=10.0*self.module and
                              any(int(p.get('future_option_count',0))>0 for p in pools[fid]))}
            if (main_family and (protected or recovery_family)) or local_only or young_structural:
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
                        key=hkey(hchosen)
                        if young_structural:
                            fairness=sum(int(self.fronts[p['front']].get('structural_hold_streak',0))
                                         for p in hchosen if p['front'] in young_structural)
                            rank=(moved,fairness,score)
                        else:
                            rank=(moved,score)
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
                    best=(hbest[0][-1],hbest[1],hbest[2])
                    chosen_ids={p['front'] for p in hbest[2]}
                    if young_structural:
                        for sfid in young_structural:
                            sf=self.fronts[sfid]
                            if sfid in chosen_ids:
                                sf['structural_hold_streak']=0
                            else:
                                sf['structural_hold_streak']=int(sf.get('structural_hold_streak',0))+1
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
                if rec['front']==f['id'] or rec.get('root')==self._launch_family_key(f): continue
                if not (probe.intersects(rec['geom']) or probe.distance(rec['geom'])<self.r.pathway_interroute_keepout):
                    continue
                other=self.fronts.get(rec['front'])
                if other is None or other.get('status') not in ('active','terminated') or other.get('round_connection_peer') is not None:
                    continue
                if self._front_has_children(other['id']):
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
        if self._front_has_children(f['id']):
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
                    self.main_launch_trace_ids.add(tid)
                    thicknesses[tid]=thicks[li]; start_map[tid]=start
                cx=sum(start_map[i][0] for i in ids)/len(ids)
                cy=sum(start_map[i][1] for i in ids)/len(ids)
                vx,vy=dir_vec(direction); nx,ny=-vy,vx
                offsets={i:(start_map[i][0]-cx)*nx+(start_map[i][1]-cy)*ny for i in ids}
                slices=self._cohort_slices(len(starts),side_rng)
                fan_parts=[[local_to_global[li] for li in part] for part in slices]
                frng=self._new_rng()
                # The four-module launch contract is a cumulative visible-survival floor,
                # not a four-module collinearity requirement.  A root still emerges
                # perpendicular on its first gesture through the ordinary gesture grammar,
                # but may make a legal +/-45-degree turn before reaching four total modules.
                root=self._make_front(ids=ids,chip=chip_idx,side=side,side_index=side_index,
                                      path=[(cx,cy)],direction=direction,offsets=offsets,
                                      thicknesses=thicknesses,prefixes={},rng=frng)
                root['fan_parts']=fan_parts
                root['fan_pending']=len(fan_parts)>1
                root['launch_family_key']=(chip_idx,side_index,side)
                root['launch_egress_pending']=True
                for tid,start in start_map.items():
                    end=point_along_dir(start,direction,self.launch_egress_modules*self.module)
                    rad=.5*thicknesses[tid]+self.r.pathway_interroute_keepout
                    erec=dict(owner=(chip_idx,side_index,side),tid=tid,active=True,radius=rad,
                        geom=LineString([start,end]).buffer(rad,cap_style='round',join_style='mitre',quad_segs=4))
                    self.source_egress_reservations.append(erec)
                    self.source_egress_by_owner.setdefault(erec['owner'],[]).append(erec)
                    self.source_egress_index.insert(erec,erec['geom'].bounds)
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

    def _launch_fan_ready(self,f):
        """Whether a root side bus has completed its physical emergence gesture.

        The four-module rule is a *lane-survival* floor, not a requirement that the complete
        9-24 lane bus remain one unsplit corridor for four modules.  A root therefore becomes
        eligible for its transactional fan immediately after one real perpendicular emergence
        gesture.  `_fan_front()` proves the complete newborn child maneuver and will not commit
        the fan unless every child lane reaches the ordinary four-module survival floor.
        """
        return (f.get('status')=='active' and f.get('parent') is None and
                not f.get('local_gap') and bool(f.get('fan_pending')) and
                int(f.get('gestures',0))>=1 and
                self._minimum_materialized_lane_length(f)>=1.0*self.module-1e-7)

    def _source_egress_pending(self,f):
        return (f.get('parent') is None and not f.get('local_gap') and
                f.get('chip',len(self.chips))<len(self.chips) and not self._launch_egress_cleared(f))

    def _main_launch_physically_protected(self,f):
        if f.get('local_gap') or f.get('chip',len(self.chips))>=len(self.chips): return False
        return self._minimum_materialized_lane_length(f) < self.main_launch_maturity_modules*self.module-1e-7

    def _maximum_materialized_lane_length(self,f):
        paths=self._materialized_paths(f)
        vals=[]
        for tid in f.get('ids',()):
            pts=paths.get(tid,())
            if len(pts)>=2:
                vals.append(sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:])))
        return max(vals) if vals else 0.0

    def _main_side_progress_satisfied(self,side_key):
        """True once one physical outcome from a launch side has genuinely progressed.

        Materialization's stalled-side audit is intentionally side-level: a side is bad only
        when every surviving outcome terminates below eight modules.  Keep the same predicate
        available *during construction* so the planner can preserve useful space before that
        condition becomes a late preflight surprise.
        """
        for fid in self.fronts_by_side.get(side_key,()):
            f=self.fronts.get(fid)
            if f is None or f.get('local_gap') or f.get('status')=='branched':
                continue
            if f.get('status') in ('escaped','connected'):
                return True
            if self._maximum_materialized_lane_length(f)>=8.0*self.module-1e-7:
                return True
        return False

    def _main_side_progress_debt(self,f):
        if (f.get('status')!='active' or f.get('local_gap') or
                f.get('chip',len(self.chips))>=len(self.chips)):
            return False
        return not self._main_side_progress_satisfied(self._launch_family_key(f))

    def _other_active_main_side_fronts(self,f):
        key=self._launch_family_key(f)
        return [self.fronts[fid] for fid in self.fronts_by_side.get(key,())
                if fid!=f.get('id') and fid in self.fronts and
                self.fronts[fid].get('status')=='active' and not self.fronts[fid].get('local_gap')]

    def _connection_family_compatible(self,a,b):
        """MAIN heads may connect across distinct launch families, even on one chip.

        Siblings from the same emitted side are one routing family and must never silently merge.
        Two different sides of the same chip, however, are genuinely foreign pathway networks;
        treating them as forever non-connectable is what produced obvious head-to-head terminal
        pairs with dots touching instead of one physical junction.
        """
        if a.get('local_gap') or b.get('local_gap'):
            return False
        return self._launch_family_key(a)!=self._launch_family_key(b)

    def _release_source_egress(self,owner):
        for rec in self.source_egress_by_owner.get(owner,()): rec['active']=False

    def _reactivate_source_egress(self,owner):
        for rec in self.source_egress_by_owner.get(owner,()): rec['active']=True

    def _rebuild_source_egress_index(self):
        """Reindex the small source-egress reservation set after a certificate shape changes."""
        self.source_egress_index=SpatialHash(max(80.0*self.U,3.0*self.module))
        for rec in self.source_egress_reservations:
            self.source_egress_index.insert(rec,rec['geom'].bounds)

    def _sync_source_egress_reservation_for_front(self,f):
        """Make reservation activity agree with one restored root front snapshot."""
        if f.get('parent') is not None or f.get('local_gap') or f.get('chip',len(self.chips))>=len(self.chips):
            return
        owner=self._launch_family_key(f)
        if self._source_egress_pending(f):
            f['launch_egress_pending']=True
            self._reactivate_source_egress(owner)
        else:
            f['launch_egress_pending']=False
            self._release_source_egress(owner)

    def _capture_source_egress_survival_prefix(self,f):
        """Promote the first actually-mature root prefix into its replay reservation.

        Early turning makes the historical straight four-module ray only a fallback certificate.
        Once every materialized lane first clears the hard four-module floor, the exact visible
        bent prefix is the stronger certificate.  Compute every lane geometry first, then swap
        the family reservation atomically and rebuild its tiny spatial index.
        """
        if (f.get('parent') is not None or f.get('local_gap') or
                f.get('chip',len(self.chips))>=len(self.chips) or
                f.get('launch_survival_prefix_path') is not None or
                not self._launch_egress_cleared(f)):
            return False
        owner=self._launch_family_key(f)
        recs=list(self.source_egress_by_owner.get(owner,()))
        paths=self._materialized_paths(f)
        pending=[]
        for rec in recs:
            pts=list(paths.get(rec['tid'],()))
            if len(pts)<2:
                return False
            length=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:]))
            if length < self.launch_egress_modules*self.module-1e-7:
                return False
            rad=float(rec.get('radius',.5*f['thicknesses'][rec['tid']]+self.r.pathway_interroute_keepout))
            geom=LineString(pts).buffer(rad,cap_style='round',join_style='mitre',quad_segs=4)
            pending.append((rec,geom))
        # All lanes are proven before mutating any reservation record.
        f['launch_survival_prefix_path']=[tuple(x) for x in f.get('path',())]
        for rec,geom in pending:
            rec['geom']=geom
        if pending:
            self._rebuild_source_egress_index()
        self.stats.setdefault('pathway_source_egress_bent_prefix_capture_count',0)
        self.stats['pathway_source_egress_bent_prefix_capture_count']+=1
        return True

    def _rewind_root_to_emergence_for_source_egress(self,f):
        """Transactionally remove only this root's committed tail back to its emergence anchor."""
        if f.get('parent') is not None or f.get('local_gap'):
            return 0
        self._reactivate_source_egress(self._launch_family_key(f))
        removed=0
        owned=self.path_segments_by_front.setdefault(f['id'],[])
        while len(f.get('path',()))>1:
            if not f.get('route_history'):
                raise RuntimeError(f'source-egress rewind history invariant failed (sample_seed={self.sseed}, front={f["id"]})')
            snap=f['route_history'].pop()
            f['path'].pop()
            f['dir']=snap['dir']; f['travel']=snap['travel']; f['gestures']=snap['gestures']
            f['local_gestures']=snap['local_gestures']; f['turn_cooldown']=snap['turn_cooldown']
            f['straight_since_turn']=snap['straight_since_turn']; f['last_turn_sign']=snap['last_turn_sign']
            f['branch_stage']=snap['branch_stage']; f['branch_turn']=snap['branch_turn']
            f['max_origin_distance']=snap.get('max_origin_distance',f.get('max_origin_distance',0.0))
            f['stagnant_gestures']=snap.get('stagnant_gestures',0)
            f['turn_history']=list(snap.get('turn_history',[]))
            del f['normal_segment_lengths'][snap['normal_len_count']:]
            if not owned:
                raise RuntimeError(f'source-egress rewind ownership invariant failed (sample_seed={self.sseed}, front={f["id"]})')
            rec=owned.pop(); rec['_retired']=True; removed+=1
        if removed:
            self._rebuild_path_index_and_coverage(rebuild_local_coverage=False)
        f['launch_egress_pending']=True
        f['protected_launch_unresolved']=True
        self.stats.setdefault('pathway_final_source_egress_rewind_segment_count',0)
        self.stats['pathway_final_source_egress_rewind_segment_count']+=removed
        return removed

    def _family_has_protected_active(self,owner):
        # Round snapshots precompute this family-local predicate once.  Fallback keeps exact
        # behavior for repair helpers invoked outside an ordinary synchronized round.
        if owner in getattr(self,'_protected_family_owners',set()): return True
        for other in self.fronts.values():
            if other.get('status')!='active' or other.get('local_gap'): continue
            if self._launch_family_key(other)==owner and self._source_egress_pending(other): return True
        return False

    def _source_egress_clear_for_gesture(self,f,geom):
        if not self.source_egress_reservations or geom.is_empty: return True
        owner=self._launch_family_key(f)
        f_young=bool(self._source_egress_pending(f))
        reach=.35*self.r.pathway_interroute_keepout
        nearby=self.source_egress_index.query(expand_bounds(geom.bounds,reach))
        for rec in nearby:
            if not rec.get('active',True) or rec['owner']==owner: continue
            if f_young and self._family_has_protected_active(rec['owner']):
                continue
            rg=rec['geom']
            if geom.intersects(rg) or geom.distance(rg)<reach:
                self.stats['pathway_launch_egress_reservation_reject_count']+=1
                return False
        return True

    def _gap_cell(self,p):
        nx,ny=self.r.local_gap_grid_shape(); x,y=p
        return (min(nx-1,max(0,int(nx*x/max(self.W,1e-9)))),
                min(ny-1,max(0,int(ny*y/max(self.H,1e-9)))))

    def _coverage_cell12(self,p):
        # V43 keeps the historic physical coverage-cell size while allowing the long axis to
        # contain proportionally more cells. The name remains for compatibility.
        x,y=p; nx,ny=self.coverage_grid_nx,self.coverage_grid_ny
        return (min(nx-1,max(0,int(nx*x/max(self.W,1e-9)))),
                min(ny-1,max(0,int(ny*y/max(self.H,1e-9)))))

    def _build_local_component_cluster_territory(self,nx,ny,cw,ch):
        """Reserve compact placed-component cluster interiors for LOCAL composition.

        The exact component moat remains the legality authority.  This additional
        raster/geometry ownership boundary prevents an otherwise legal LOCAL route
        from threading the empty space *inside* a group of components.  Every
        Construction follows component population and protected raster area
        rather than component pairs, regardless of cluster member count.
        """
        members={}
        for g in self.cols+self.isolated:
            cid=g.structural.get('residual_fill_cluster_id')
            if cid is not None:
                members.setdefault(cid,[]).append(g)
        territory=[]
        margin=.55*max(cw,ch)
        for cid,groups in sorted(members.items()):
            # A singleton receives only a compact breathing envelope.  Two or
            # more members reserve their common convex interior as one cluster.
            hull=unary_union([g.collision_geom.convex_hull for g in groups]).convex_hull
            if not hull.is_empty:
                territory.append((cid,hull.buffer(margin,quad_segs=4)))
        self.local_component_cluster_territory=territory
        index=SpatialHash(max(2.0*max(cw,ch),1e-6))
        blocked=set()
        for cid,geom in territory:
            index.insert((cid,geom),geom.bounds)
            x0,y0,x1,y1=geom.bounds
            gx0=max(0,int(math.floor(x0/cw-.5))); gx1=min(nx-1,int(math.ceil(x1/cw-.5)))
            gy0=max(0,int(math.floor(y0/ch-.5))); gy1=min(ny-1,int(math.ceil(y1/ch-.5)))
            for gy in range(gy0,gy1+1):
                for gx in range(gx0,gx1+1):
                    if geom.covers(Point((gx+.5)*cw,(gy+.5)*ch)):
                        blocked.add((gx,gy))
        self.local_component_cluster_territory_index=index
        self.local_component_cluster_territory_cells=blocked
        self.stats['pathway_local_component_territory_cluster_count']=len(territory)
        self.stats['pathway_local_component_territory_cell_count']=len(blocked)

    def _residual_gap_regions(self):
        """Measure connected residual regions after the main network is frozen.

        V33 replaces the old 12x12 point heuristic with a denser connected-region field.
        Each region records its real local extent, aspect and principal orientation.  Local
        sources and targets are selected *inside the same region* so a tiny pocket receives a
        short line while a large corridor can receive several independent travellers.
        """
        nx,ny=self.r.local_gap_grid_shape()
        cw=self.W/nx; ch=self.H/ny
        self._build_local_component_cluster_territory(nx,ny,cw,ch)
        open_cells=set()
        for gy in range(ny):
            for gx in range(nx):
                x=(gx+.5)*cw; y=(gy+.5)*ch; q=Point(x,y)
                # V37 residual field is measured *after components*.  A cell belongs to the
                # local-line denominator only when it clears chips and already-placed components
                # by the same visual moat that a real local trace must respect.
                static_blocked=False
                reach=max(self.r.pathway_main_chip_keepout,self.r.component_pathway_clearance)+.30*self.module
                qb=(x-reach,y-reach,x+reach,y+reach)
                for gi,g in self.static_index.query(qb):
                    keep=(self.r.pathway_main_chip_keepout if gi < len(self.chips)
                          else self.r.component_pathway_clearance)
                    if q.distance(g.geom) < keep + .30*self.module:
                        static_blocked=True; break
                if static_blocked:
                    continue
                probe=q.buffer(.30*self.module,quad_segs=5)
                blocked=False
                for rec in self.path_index.query(expand_bounds(probe.bounds,.12*self.module)):
                    if probe.intersects(rec['geom']): blocked=True; break
                if not blocked: open_cells.add((gx,gy))
        # The physical field is the service numerator's raster.  Build the ownership
        # atlas separately; a policy seam cannot erase physical residual service.
        self._init_local_route_composition(open_cells)
        protected=self.local_component_cluster_territory_cells
        route_cells=set()
        for gx,gy in open_cells:
            cell=(gx,gy)
            if cell in protected or cell not in self.local_macro_allowed_cells:
                continue
            mid=self.local_macro_by_cell.get(cell)
            owner=self.local_macro_geoms.get(mid)
            if owner is not None and owner.covers(Point((gx+.5)*cw,(gy+.5)*ch)):
                route_cells.add(cell)
        self.local_gap_route_cells=route_cells
        regions=[]; by_cell={}; unseen=set(route_cells); rid=0
        # A gx-major grid walk preserves the former min(unseen) seed order in linear work.
        # Four-neighbour connectivity keeps diagonally touching pockets separate.
        for seed_gx in range(nx):
            for seed_gy in range(ny):
                seed=(seed_gx,seed_gy)
                if seed not in unseen: continue
                stack=[seed]; unseen.remove(seed); cells=[]
                while stack:
                    c=stack.pop(); cells.append(c); x,y=c
                    for nb in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                        if nb in unseen and self.local_macro_by_cell.get(nb)==self.local_macro_by_cell.get(c):
                            unseen.remove(nb); stack.append(nb)
                xs=[c[0] for c in cells]; ys=[c[1] for c in cells]
                cx=sum((x+.5)*cw for x,_ in cells)/len(cells)
                cy=sum((y+.5)*ch for _,y in cells)/len(cells)
                w=(max(xs)-min(xs)+1)*cw; h=(max(ys)-min(ys)+1)*ch
                pts=[((x+.5)*cw,(y+.5)*ch) for x,y in cells]
                sxx=sum((x-cx)**2 for x,y in pts); syy=sum((y-cy)**2 for x,y in pts); sxy=sum((x-cx)*(y-cy) for x,y in pts)
                angle=.5*math.atan2(2*sxy,sxx-syy) if len(cells)>1 else 0.0
                vx,vy=math.cos(angle),math.sin(angle)
                d=nearest_dir_index(vx,vy)
                short=min(w,h); long=max(w,h)
                size='small' if len(cells)<10 or short<1.8*self.module else ('medium' if len(cells)<28 else 'large')
                rec=dict(id=rid,cells=set(cells),cell_count=len(cells),center=(cx,cy),width=w,height=h,
                         short_span=short,long_span=long,dir=d,size=size,
                         macro_id=self.local_macro_by_cell.get(seed))
                regions.append(rec)
                for c in cells: by_cell[c]=rid
                rid+=1
        self.local_gap_regions=regions; self.local_gap_region_by_cell=by_cell
        self.local_gap_route_domain_by_cell=by_cell
        self.local_route_clusters={}
        self.local_fill_cluster_root_counts={}
        for region in regions:
            cid=region['id']
            self.local_route_clusters[cid]=dict(anchor=region['center'],
                target_sources=max(1,self.r.local_gap_region_source_cap(region['cell_count'])),
                target_cells=frozenset(region['cells']),macro_id=region['macro_id'])
            self.local_fill_cluster_root_counts[cid]=0
        # Immutable per-region projection orders for bounded targeting in genuinely huge rooms.
        # The exact scoring function below is unchanged; this is only the broad phase.  Four
        # projections cover the eight octilinear extrema (each list can be read from either end).
        self.local_gap_directional_cells={}
        for r in regions:
            cells=r['cells']
            self.local_gap_directional_cells[r['id']]=(
                sorted(cells,key=lambda c:(c[0],c[1])),
                sorted(cells,key=lambda c:(c[1],c[0])),
                sorted(cells,key=lambda c:(c[0]-c[1],c[0],c[1])),
                sorted(cells,key=lambda c:(c[0]+c[1],c[0],c[1])),
            )
        # LOCAL-1A chunk index: immutable room membership plus mutable untouched subsets.
        # Six grid cells per side bounds exact target scoring to at most 36 cells after a cheap
        # chunk-level choice.  The physical chunk size stays in canonical local-gap units because
        # the service grid itself scales with logical territory.
        self.local_gap_chunk_cells_by_region={}
        self.local_gap_chunk_key_by_cell={}
        span=max(1,int(self.local_gap_chunk_span))
        for r in regions:
            chunks={}
            for c in r['cells']:
                ck=(c[0]//span,c[1]//span)
                chunks.setdefault(ck,set()).add(c)
                self.local_gap_chunk_key_by_cell[c]=(r['id'],ck)
            self.local_gap_chunk_cells_by_region[r['id']]={k:frozenset(v) for k,v in chunks.items()}
        # V44: materialize the targetable complement once.  A cell leaves these sets exactly
        # when its legitimate 4x4 service mask receives its first covered subcell.
        self.local_gap_untouched_cells=set(route_cells)
        self.local_gap_untouched_by_region={r['id']:set(r['cells']) for r in regions}
        self.local_gap_region_touch_version={r['id']:0 for r in regions}
        self._reset_local_gap_chunk_state()
        self.stats['pathway_local_gap_region_count']=len(regions)
        self.stats['pathway_local_gap_route_cell_count']=len(route_cells)
        return open_cells

    def _init_local_route_composition(self,open_cells):
        """Measure the shared C/LOCAL field and grow route-capable LOCAL territories."""
        self.local_sector_open={}
        self.local_sector_components={}
        nx,ny=self.r.local_gap_grid_shape()
        for gx,gy in open_cells:
            key=(min(3,4*gx//nx),min(3,4*gy//ny))
            self.local_sector_open[key]=self.local_sector_open.get(key,0)+1
        for g in self.cols+self.isolated:
            x,y=bounds_center(g.bounds)
            key=(min(3,max(0,int(4*x/self.W))),min(3,max(0,int(4*y/self.H))))
            self.local_sector_components[key]=self.local_sector_components.get(key,0)+1
        self._plan_local_route_territories(open_cells)

    def _plan_local_route_territories(self,open_cells):
        """Plan paired macro C/LOCAL territory while retaining every service cell.

        The lattice was chosen after MAIN and before component placement.  LOCAL
        microclusters remain varied, but their visible routes share a larger lobe.
        Compact C cores and seams are route boundaries, not denominator changes.
        """
        nx,ny=self.r.local_gap_grid_shape(); cw=self.W/nx; ch=self.H/ny
        fallback_n=int(getattr(self.r,'_residual_macro_lattice_n',5))
        mx,my=getattr(self.r,'_residual_macro_grid_shape',(fallback_n,fallback_n))
        mx=max(1,int(mx)); my=max(1,int(my))
        planned_cowners=getattr(self.r,'_residual_component_macro_owners',{})
        # Components have now frozen.  Keep each actual cluster's buffered
        # territory inside its planned C owner and return unused planned fringe
        # to LOCAL opportunity.  The physical service denominator is untouched;
        # component geometry and its cluster hull remain exact route obstacles.
        cowners={}
        # Cluster territories already include their .55-cell breathing envelope.
        # The LOCAL owner gets its own 10U outer erosion below; another module
        # of C buffering here would reserve the same moat a third time.
        buffered_clusters={cid:territory for cid,territory in self.local_component_cluster_territory}
        for key,planned in planned_cowners.items():
            occupied=[buffered_clusters[cid]
                      for cid,_territory in self.local_component_cluster_territory_index.query(
                          planned.bounds)
                      if buffered_clusters[cid].intersects(planned)]
            if occupied:
                retained=unary_union(occupied).intersection(planned)
                if not retained.is_empty:
                    cowners[key]=retained
        self.stats['pathway_local_planned_component_owner_count']=len(planned_cowners)
        self.stats['pathway_local_retained_component_owner_count']=len(cowners)
        self._local_effective_cowners=cowners
        if not cowners:
            # An all-LOCAL budget has one unseamed routing field.  Natural physical
            # obstacles still divide it into connected route domains below.
            self.local_macro_geoms={0:box(0.0,0.0,self.W,self.H)}
            self.local_macro_by_cell={(gx,gy):0 for gy in range(ny) for gx in range(nx)}
            self.local_macro_allowed_cells=set(self.local_macro_by_cell)
            self.local_territory_by_cell=None
            self.stats['pathway_local_macro_count']=1
            return
        # Component cores are selected by seeded density, not checkerboard parity.  An
        # actual unowned macro tile is a LOCAL anchor; cells outside a C core inherit
        # the nearest such anchor.  Query the anchor STRtree once per macro tile, then
        # assign each service cell by O(1) lookup rather than scanning all anchors.
        open_macro_keys=set(); free_macro_keys=set()
        for gx,gy in open_cells:
            key=(min(mx-1,int(mx*(gx+.5)/nx)),min(my-1,int(my*(gy+.5)/ny)))
            open_macro_keys.add(key)
            owner=cowners.get(key)
            if owner is None or not owner.covers(Point((gx+.5)*cw,(gy+.5)*ch)):
                free_macro_keys.add(key)
        anchor_keys=sorted(key for key in open_macro_keys if key not in cowners)
        if not anchor_keys:
            # A high C share can select every macro tile while leaving a legitimate
            # physical LOCAL shell outside the compact core in each one.
            anchor_keys=sorted(free_macro_keys)
        lseeds=[(ix,iy,((ix+.5)*self.W/mx,(iy+.5)*self.H/my))
                for ix,iy in anchor_keys]
        if not lseeds:
            self.local_macro_geoms={}; self.local_macro_by_cell={}
            self.local_macro_allowed_cells=set(); self.local_territory_by_cell=None
            self.stats['pathway_local_macro_count']=0
            return
        anchor_tree=STRtree([Point(pt) for _ix,_iy,pt in lseeds])
        # Join adjacent LOCAL anchors before eroding their outer boundary.  Eroding
        # each tile separately makes an artificial wall through one physical room.
        # Seeded small connected groups keep the composition varied without letting
        # a chain of LOCAL tiles percolate into a board-scale owner.
        remaining=set(anchor_keys)
        anchor_group={}
        group_rng=SplitMix64(mix_once(self.sseed ^ 0x4C4F43414C434F4C))
        group_sizes=(1,2,2,3,3,3,4,4,5,6)
        group_id=0
        for seed in anchor_keys:
            if seed not in remaining:
                continue
            remaining.remove(seed)
            members=[seed]
            frontier=set()
            limit=group_sizes[group_rng.next_u64()%len(group_sizes)]
            while len(members)<limit:
                for tx,ty in members:
                    for nb in ((tx-1,ty),(tx+1,ty),(tx,ty-1),(tx,ty+1)):
                        if nb in remaining:
                            frontier.add(nb)
                if not frontier:
                    break
                ordered=sorted(frontier)
                nb=ordered[group_rng.next_u64()%len(ordered)]
                frontier.remove(nb)
                remaining.remove(nb)
                members.append(nb)
            for key in members:
                anchor_group[key]=group_id
            group_id+=1
        macro_owner={}
        for ty in range(my):
            for tx in range(mx):
                q=Point((tx+.5)*self.W/mx,(ty+.5)*self.H/my)
                nearest=min(int(i) for i in anchor_tree.query_nearest(q,all_matches=True))
                macro_owner[(tx,ty)]=anchor_group[anchor_keys[nearest]]
        macro_cells={i:[] for i in range(group_id)}; by_cell={}; allowed_cells=set()
        for gy in range(ny):
            for gx in range(nx):
                x=(gx+.5)*cw; y=(gy+.5)*ch
                tx=min(mx-1,max(0,int(mx*x/self.W)))
                ty=min(my-1,max(0,int(my*y/self.H)))
                mid=macro_owner[(tx,ty)]
                by_cell[(gx,gy)]=mid
                owner=cowners.get((tx,ty))
                if owner is None or not owner.covers(Point(x,y)):
                    macro_cells[mid].append(box(gx*cw,gy*ch,(gx+1)*cw,(gy+1)*ch))
                    allowed_cells.add((gx,gy))
        seam=10.0*self.U
        self.local_macro_geoms={i:unary_union(cells).buffer(-seam,join_style=2)
                                for i,cells in macro_cells.items() if cells}
        self.local_macro_by_cell=by_cell
        self.local_macro_allowed_cells={c for c in allowed_cells
            if by_cell[c] in self.local_macro_geoms and
            self.local_macro_geoms[by_cell[c]].covers(Point((c[0]+.5)*cw,(c[1]+.5)*ch))}
        self.local_territory_by_cell=None
        self.stats['pathway_local_macro_count']=len(self.local_macro_geoms)

    def _expand_local_fill_debt_targets(self):
        """Let unpaid domains spend additional ordinary source opportunity."""
        expanded=0
        for cid,meta in self.local_route_clusters.items():
            if any(self.local_gap_coverage_mask_by_cell.get(c,0).bit_count()<13
                   for c in meta['target_cells']):
                target=max(meta['target_sources'],self.local_fill_cluster_root_counts.get(cid,0)+
                    self.r.local_gap_region_source_cap(len(meta['target_cells'])))
                if target>meta['target_sources']:
                    meta['target_sources']=target; expanded+=1
        self.stats['pathway_local_gap_debt_expanded_cluster_count']=expanded
        self.stats['pathway_local_gap_debt_target_sum']=sum(
            int(meta['target_sources']) for meta in self.local_route_clusters.values())


    def _residual_gap_cells(self):
        return self._residual_gap_regions()

    def _local_gap_service_halfwidth(self,f):
        """Half-width of visually served gap area for one local trace.

        Service is the actual stroke plus *half* of the required edge-to-edge gap on each side.
        With the governing 1.5x-thickness edge gap, one isolated trace therefore owns a service
        half-width of 0.5t + 0.75t = 1.25t.  This replaces V34's oversized 1.45-module halo.
        """
        t=max((f['thicknesses'][i] for i in f.get('ids',())),default=2.55*self.U)
        line_share=.5*self.r.local_gap_line_edge_gap_factor*t
        # V37 local lines are placed after components.  The service ribbon retains the same visual
        # perimeter convention as V35 while exact component geometry is already excluded from the
        # residual field and enforced separately by collision/clearance checks.
        component_share=self.r.component_pathway_clearance
        return .5*t + max(line_share,component_share)

    def _mark_local_gap_segment_coverage(self,a,b,f=None):
        """Rasterize legitimate local-line service onto a deterministic 4x4 mask per gap cell.

        The service width is still the real rendered stroke plus its allocated exclusion
        perimeter.  V37 deliberately avoids Shapely polygon unions here: repeated exact
        buffering/intersection of hundreds of filler segments made the *measurement* much more
        expensive than the routing.  A fixed 4x4 subcell mask gives a stable ~1/16-cell area
        estimate, unions overlaps exactly at that raster resolution, and is sufficient for a
        board-level "roughly 40%" occupancy target without inventing any extra halo.
        """
        if not self.local_gap_open_cells: return
        nx,ny=self.r.local_gap_grid_shape(); cw=self.W/nx; ch=self.H/ny
        half=self._local_gap_service_halfwidth(f) if f is not None else 1.25*2.55*self.U
        ax,ay=a; bx,by=b; vx=bx-ax; vy=by-ay; L2=vx*vx+vy*vy
        if L2<=1e-12: return
        minx=min(ax,bx)-half; maxx=max(ax,bx)+half
        miny=min(ay,by)-half; maxy=max(ay,by)+half
        gx0=max(0,int(math.floor(minx/cw))); gx1=min(nx-1,int(math.floor(maxx/cw)))
        gy0=max(0,int(math.floor(miny/ch))); gy1=min(ny-1,int(math.floor(maxy/ch)))
        sub=4; fullmask=(1<<(sub*sub))-1; cell_area=cw*ch
        for gy in range(gy0,gy1+1):
            for gx in range(gx0,gx1+1):
                cell=(gx,gy)
                if cell not in self.local_gap_open_cells: continue
                old=self.local_gap_coverage_mask_by_cell.get(cell,0)
                if old==fullmask: continue
                mask=old; bit=0
                for sy in range(sub):
                    py=(gy+(sy+.5)/sub)*ch
                    for sx in range(sub):
                        bmask=1<<bit; bit+=1
                        if mask & bmask: continue
                        px=(gx+(sx+.5)/sub)*cw
                        t=((px-ax)*vx+(py-ay)*vy)/L2
                        # Flat service caps: only the actual segment extent counts.
                        if t<0.0 or t>1.0: continue
                        qx=ax+t*vx; qy=ay+t*vy
                        dx=px-qx; dy=py-qy
                        if dx*dx+dy*dy <= half*half+1e-12:
                            mask |= bmask
                if mask!=old:
                    old_bits=old.bit_count(); new_bits=mask.bit_count()
                    self.local_gap_coverage_mask_by_cell[cell]=mask
                    self.local_gap_served_subcell_count += new_bits-old_bits
                    _debt_capture=getattr(self,'_local_gap_service_debt_touch_capture',None)
                    if _debt_capture is not None:
                        _prev=_debt_capture.get(cell)
                        if _prev is None:
                            _debt_capture[cell]=(old_bits,new_bits)
                        else:
                            _debt_capture[cell]=(_prev[0],new_bits)
                    self.local_gap_coverage_touched_cells.add(cell)
                    # Partial-service debt is a live state, not a phase-start snapshot.  Once a
                    # retargeted cell reaches the same 13/16 service threshold used to create the
                    # debt set, retire it immediately so later cleanup work cannot keep polling
                    # already-paid debt.  Crossing that eligibility boundary invalidates cached
                    # residual runs for the region just like a first touch does.
                    if cell in self.local_gap_retarget_cells and old_bits<13<=new_bits:
                        self.local_gap_retarget_cells.discard(cell)
                        rid=self.local_gap_region_by_cell.get(cell)
                        if rid is not None:
                            self.local_gap_region_touch_version[rid]=self.local_gap_region_touch_version.get(rid,0)+1
                    if old==0:
                        # First touch only: targeting is binary even though the service audit
                        # remains the exact 16-subcell mask.  Keep both views synchronized.
                        self.local_gap_untouched_cells.discard(cell)
                        rid=self.local_gap_region_by_cell.get(cell)
                        if rid in self.local_gap_untouched_by_region:
                            self.local_gap_untouched_by_region[rid].discard(cell)
                            tagged=self.local_gap_chunk_key_by_cell.get(cell)
                            if tagged is not None:
                                self.local_gap_untouched_by_chunk.get(tagged,set()).discard(cell)
                            self.local_gap_region_touch_version[rid]=self.local_gap_region_touch_version.get(rid,0)+1
                        if self._local_gap_new_touch_capture is not None:
                            self._local_gap_new_touch_capture.add(cell)
                    if mask.bit_count() >= (sub*sub)//2:
                        self.local_gap_coverage_cells.add(cell)

    def _reset_local_gap_chunk_state(self):
        """Reset mutable LOCAL-1A chunk state from immutable residual-room membership."""
        self.local_gap_untouched_by_chunk={}
        self.local_gap_chunk_cycle_by_region={}
        self.local_gap_retarget_chunk_epoch={}
        for rid,chunks in self.local_gap_chunk_cells_by_region.items():
            self.local_gap_chunk_cycle_by_region[rid]=deque(sorted(chunks))
            for ck,cells in chunks.items():
                self.local_gap_untouched_by_chunk[(rid,ck)]=set(cells)

    def _local_gap_chunk_targetable_cells(self,rid,ck):
        """Return current targetable cells for one fixed residual chunk in bounded work."""
        base=self.local_gap_untouched_by_chunk.get((rid,ck),set())
        if not self.local_gap_retarget_cells:
            return base
        original=self.local_gap_chunk_cells_by_region.get(rid,{}).get(ck,())
        if not original:
            return base
        return base | (set(original) & self.local_gap_retarget_cells)

    def _local_gap_target_chunk(self,center,rid,hint):
        """Choose one bounded local chunk for target scoring.

        Ordinary targeting walks a short forward/local chunk stencil.  If that stencil is fully
        serviced, a deterministic round-robin cursor selects another still-live chunk in the
        *same residual region*. Empty chunks are discarded lazily, so draining a region costs
        O(number of chunks) total rather than O(region cells) per retarget.
        """
        chunks=self.local_gap_chunk_cells_by_region.get(rid)
        if not chunks:
            return None,None
        here=self._gap_cell(center)
        tagged=self.local_gap_chunk_key_by_cell.get(here)
        ck0=tagged[1] if tagged is not None and tagged[0]==rid else None
        keys=[]; seen=set()
        def add(k):
            if k in chunks and k not in seen:
                seen.add(k); keys.append(k)
        if ck0 is not None:
            add(ck0)
            # Immediate neighborhood keeps turns/local exploration available.
            for oy in (-1,0,1):
                for ox in (-1,0,1):
                    if ox or oy: add((ck0[0]+ox,ck0[1]+oy))
            if hint is not None:
                vx,vy=dir_vec(hint)
                hx=1 if vx>.25 else (-1 if vx<-.25 else 0)
                hy=1 if vy>.25 else (-1 if vy<-.25 else 0)
                px,py=-hy,hx
                # Four chunks of look-ahead are enough for a traveller to cross a large room
                # chunk-by-chunk without turning target selection back into a room scan.
                for step in range(1,5):
                    bx=ck0[0]+hx*step; by=ck0[1]+hy*step
                    for lat in (-1,0,1):
                        add((bx+px*lat,by+py*lat))

        self.stats.setdefault('pathway_local_gap_target_chunk_evaluation_count',0)
        self.stats['pathway_local_gap_target_chunk_evaluation_count']+=len(keys)
        if keys:
            nx,ny=self.r.local_gap_grid_shape(); cw=self.W/nx; ch=self.H/ny
            cvx,cvy=dir_vec(hint) if hint is not None else (0.0,0.0)
            best=None
            for ck in keys:
                cells=self._local_gap_chunk_targetable_cells(rid,ck)
                if not cells: continue
                original=chunks[ck]
                sx=sum(c[0]+.5 for c in original)/len(original)*cw
                sy=sum(c[1]+.5 for c in original)/len(original)*ch
                dx=sx-center[0]; dy=sy-center[1]; d=math.hypot(dx,dy)
                score=.55*d/max(self.module,1e-9)
                if hint is not None and d>1e-9:
                    score+=2.4*(dx*cvx+dy*cvy)/d
                # A small occupancy preference avoids selecting an almost-drained neighbouring
                # chunk when an equally suitable chunk still contains substantial untouched room.
                score+=.08*len(cells)/max(len(original),1)
                key=(score,-ck[1],-ck[0])
                if best is None or key>best[0]: best=(key,ck,cells)
            if best is not None:
                return best[1],best[2]

        # The front has serviced its immediate chunk neighbourhood. Rotate through the still-live
        # chunks of this same measured room rather than rescanning the room to discover one.
        q=self.local_gap_chunk_cycle_by_region.get(rid)
        if not q and self.local_gap_retarget_cells:
            epoch=id(self.local_gap_retarget_cells)
            if self.local_gap_retarget_chunk_epoch.get(rid)!=epoch:
                keys={self.local_gap_chunk_key_by_cell[c][1]
                      for c in self.local_gap_retarget_cells
                      if self.local_gap_region_by_cell.get(c)==rid}
                q=deque(sorted(keys))
                self.local_gap_chunk_cycle_by_region[rid]=q
                self.local_gap_retarget_chunk_epoch[rid]=epoch
        if q:
            checks=len(q)
            for _ in range(checks):
                ck=q.popleft()
                cells=self._local_gap_chunk_targetable_cells(rid,ck)
                if cells:
                    q.append(ck)
                    self.stats.setdefault('pathway_local_gap_target_chunk_fallback_count',0)
                    self.stats['pathway_local_gap_target_chunk_fallback_count']+=1
                    return ck,cells
                # Empty ordinary chunks never become untouched again except during an
                # authoritative rollback, which rebuilds this queue from scratch.
        return None,None

    def _local_gap_targetable_cells(self,rid=None):
        """Cells currently eligible for ordinary local targeting.

        This is set-equivalent to ``route_cells - touched_route_cells`` but uses the
        incrementally maintained untouched complement.  During the hard-floor-only partial
        reserve, partially served retarget cells are unioned back in exactly as before.
        """
        if rid is None:
            base=self.local_gap_untouched_cells
            if not self.local_gap_retarget_cells:
                return base
            return base | self.local_gap_retarget_cells
        base=self.local_gap_untouched_by_region.get(rid,set())
        if not self.local_gap_retarget_cells:
            return base
        r=self.local_gap_regions[rid] if rid is not None and rid < len(self.local_gap_regions) else None
        if r is None:
            return base
        return base | (r['cells'] & self.local_gap_retarget_cells)

    def _local_gap_covered_cells(self):
        # Targeting uses every cell already touched by a legitimate service ribbon so later
        # waves seek genuinely untouched rooms instead of spawning beside earlier fillers.
        # The *coverage percentage* remains the exact served-area fraction below.
        covered=self.local_gap_coverage_touched_cells & self.local_gap_open_cells
        if self.local_gap_retarget_cells:
            covered=covered-self.local_gap_retarget_cells
        return covered

    def _local_gap_service_fraction(self):
        """Absolute LOCAL service on the canonical post-MAIN residual budget."""
        denom=self.local_gap_service_denominator_cell_count
        if denom is None:
            denom=len(self.local_gap_open_cells)
        if denom<=0: return 0.0
        # The numerator contains only legitimate LOCAL service inside the physically available
        # post-component field.  Dividing by the original post-MAIN residual cell count keeps
        # component and LOCAL service in the same units, as required by the V36+ contract.
        return min(1.0,self.local_gap_served_subcell_count/max(int(denom)*16,1))

    def _recount_visible_local_gap_service(self,trace_records):
        """Replace planned service with the exact raster of emitted LOCAL strokes."""
        if not self.local_gap_open_cells:
            return
        self.local_gap_coverage_mask_by_cell={}
        self.local_gap_coverage_cells=set()
        self.local_gap_coverage_touched_cells=set()
        self.local_gap_served_subcell_count=0
        self.local_gap_retarget_cells=set()
        self.local_gap_untouched_cells=set(self.local_gap_route_cells)
        self.local_gap_untouched_by_region={r['id']:set(r['cells']) for r in self.local_gap_regions}
        self._reset_local_gap_chunk_state()
        for rec in trace_records:
            if not rec.get('local_gap'):
                continue
            tid=rec['tid']
            thickness=float(rec['primitive'].svg['stroke_width'])
            stroke=dict(ids=(tid,),thicknesses={tid:thickness})
            for a,b in zip(rec['points'],rec['points'][1:]):
                self._mark_local_gap_segment_coverage(a,b,stroke)
        self.stats['pathway_local_gap_covered_cell_count']=len(self.local_gap_coverage_touched_cells)
        self.stats['pathway_local_gap_fill_actual']=self._local_gap_service_fraction()

    def _settle_local_nonemittable_fronts(self):
        """Retire LOCAL segments that final materialization would omit."""
        victims=[]
        for f in self.fronts.values():
            if not f.get('local_gap'):
                continue
            if (f.get('status')=='abandoned_short' or
                    (f.get('status')=='terminated' and f.get('travel',0.0)+1e-9<2.75*self.module)):
                if f.get('status')!='abandoned_short':
                    f['status']='abandoned_short'
                    f['termination_reason']='local_nonemittable_short'
                    f['lifecycle']='TERMINAL'
                victims.append(f['id'])
        return self._prune_abandoned_local_segments(victims)

    def _local_gap_physical_post_component_service_fraction(self):
        """Diagnostic: LOCAL service as a fraction of the physical post-component open field."""
        if not self.local_gap_open_cells: return 0.0
        return min(1.0,self.local_gap_served_subcell_count/max(len(self.local_gap_open_cells)*16,1))

    def _local_gap_extreme_shortlist(self,rid,targetable,hint,limit=512):
        """Bounded candidate broad-phase for very large residual rooms.

        V45 already stopped exhaustive *scoring* above 4096 cells, but still walked the whole
        room to build its rough top-512 heap.  Residual rooms are immutable while service only
        removes eligibility, so four pre-sorted octilinear projections can recover far/forward
        candidates in bounded work.  Exact congestion/distance/direction scoring remains in
        ``_local_gap_target``.
        """
        if rid is None or rid not in self.local_gap_directional_cells:
            out=[]
            for c in targetable:
                out.append(c)
                if len(out)>=limit: break
            return out
        orders=self.local_gap_directional_cells[rid]
        # projection/end aligned with DIR8: E, NE, N, NW, W, SW, S, SE
        pref={0:(0,True),1:(2,True),2:(1,False),3:(3,False),
              4:(0,False),5:(2,False),6:(1,True),7:(3,True)}
        endpoints=[]
        if hint is not None:
            endpoints.append(pref[hint])
            endpoints.append(pref[(hint-1)%8]); endpoints.append(pref[(hint+1)%8])
        # Distance remains part of the exact score, so retain representatives from every
        # octilinear extreme rather than only the forward edge.
        for d in range(8):
            ep=pref[d]
            if ep not in endpoints: endpoints.append(ep)
        out=[]; seen=set(); primary=max(48,limit//3); secondary=max(12,limit//16)
        for ei,(oi,rev) in enumerate(endpoints):
            quota=primary if ei==0 and hint is not None else secondary
            seq=reversed(orders[oi]) if rev else iter(orders[oi])
            taken=0
            for c in seq:
                if c not in targetable or c in seen: continue
                seen.add(c); out.append(c); taken+=1
                if len(out)>=limit or taken>=quota: break
            if len(out)>=limit: break
        if len(out)<limit:
            for c in targetable:
                if c in seen: continue
                seen.add(c); out.append(c)
                if len(out)>=limit: break
        return out

    def _local_gap_target(self,center,rng,turn_hint=0,cluster_id=None):
        """Choose an uncovered target through LOCAL-1A's bounded residual-chunk state."""
        self.stats.setdefault('pathway_local_gap_target_call_count',0)
        self.stats['pathway_local_gap_target_call_count']+=1
        here=self._gap_cell(center)
        rid=(cluster_id if cluster_id in self.local_route_clusters
             else self.local_gap_region_by_cell.get(here))
        if rid is None:
            return center
        hint=turn_hint if isinstance(turn_hint,int) and 0<=turn_hint<8 else None
        cluster=self.local_route_clusters.get(cluster_id)
        own=cluster['target_cells'] if cluster is not None else None
        eval_pool=None
        if rid is not None:
            _ck,chunk_cells=self._local_gap_target_chunk(center,rid,hint)
            if chunk_cells:
                # Chunk membership is bounded (<= 6x6), so sorting is constant-sized and gives
                # an explicit deterministic candidate order across Python processes.
                eval_pool=sorted(c for c in chunk_cells if own is None or c in own)
        if not eval_pool:
            targetable=self._local_gap_targetable_cells(rid)
            if not targetable:
                return center
            eval_pool=list(self._local_gap_extreme_shortlist(rid,targetable,hint,96))
        nx,ny=self.r.local_gap_grid_shape(); cw=self.W/nx; ch=self.H/ny
        maps=getattr(self,'_local_gap_congestion_cell_maps',None)
        map_sig=(nx,ny,cw,ch)
        if maps is None or maps[0]!=map_sig:
            xmap=[self._grid_cell(((gx+.5)*cw,0.0))[0] for gx in range(nx)]
            ymap=[self._grid_cell((0.0,(gy+.5)*ch))[1] for gy in range(ny)]
            maps=(map_sig,xmap,ymap); self._local_gap_congestion_cell_maps=maps
        _sig,xmap,ymap=maps
        vx,vy=dir_vec(hint) if hint is not None else (0.0,0.0)
        cx,cy=center; module_denom=max(self.module,1e-9); min_target_distance=.55*self.module
        best_key=None; best_point=None; evaluated=0
        for gx,gy in eval_pool:
            x=(gx+.5)*cw; y=(gy+.5)*ch; dx=x-cx; dy=y-cy; d=math.hypot(dx,dy)
            if d<min_target_distance: continue
            evaluated+=1
            score=.55*d/module_denom-1.15*self._congestion_at_cell(xmap[gx],ymap[gy])
            if cluster is not None:
                ax,ay=cluster['anchor']
                score-=.25*math.hypot(x-ax,y-ay)/module_denom
            if hint is not None:
                score+=2.4*(dx*vx+dy*vy)/max(d,1e-9)
            key=(-score,rng.random())
            if best_key is None or key<best_key:
                best_key=key; best_point=(x,y)
        self.stats.setdefault('pathway_local_gap_target_cell_evaluation_count',0)
        self.stats['pathway_local_gap_target_cell_evaluation_count']+=evaluated
        if best_point is None:
            return center
        return best_point

    def _local_component_territory_clear(self,geom,extra=0.0):
        index=self.local_component_cluster_territory_index
        if index is None:
            return True
        for _cid,protected in index.query(expand_bounds(geom.bounds,extra)):
            if geom.intersects(protected) or (extra>0.0 and geom.distance(protected)<extra):
                return False
        return True

    def _local_fill_parcel_clear(self,f,geom,extra=0.0):
        cid=f.get('local_fill_cluster_id')
        meta=self.local_route_clusters.get(cid)
        if meta is None:
            return False
        macro_id=meta.get('macro_id')
        macro_geom=getattr(self,'local_macro_geoms',{}).get(macro_id)
        if macro_geom is not None:
            probe=geom.buffer(extra,quad_segs=4) if extra>0.0 else geom
            if not macro_geom.covers(probe):
                self.stats['pathway_local_macro_boundary_reject_count']=self.stats.get('pathway_local_macro_boundary_reject_count',0)+1
                return False
        return True

    def _local_macro_endpoint_excluded(self,f,p):
        """Reject only an endpoint provably outside its exact owner geometry."""
        meta=self.local_route_clusters.get(f.get('local_fill_cluster_id'))
        if meta is None or meta.get('macro_id') not in self.local_macro_geoms:
            return True
        # Physical cell-centre sampling defines source/target opportunity, not a
        # geometric wall.  Subcell endpoints can be legal even when their sampled
        # cell is absent from the connected route field.  The exact owner and the
        # subsequent corridor/obstacle checks remain the authority.
        return not self.local_macro_geoms[meta['macro_id']].covers(Point(p))

    def _local_gap_source_clearance(self,p,half_width,marker_extent=None,cluster_id=None):
        """Conservative clearance for an interior local-network source."""
        cid=(cluster_id if cluster_id is not None else
             self._local_route_cluster_for_source(p,create=False))
        if cid is None or self.local_gap_route_domain_by_cell.get(self._gap_cell(p))!=cid:
            return False
        q=Point(p)
        extent=max(half_width,float(marker_extent if marker_extent is not None else half_width))
        # The rendered source dot uses sixteen arc segments per quadrant.  The old
        # six-segment probe was inscribed and could admit a dot across a concave
        # parcel edge even though its centre and first stroke were contained.
        visible_disc=q.buffer(extent,quad_segs=16)
        if not self._local_component_territory_clear(visible_disc):
            return False
        if cid is not None and not self._local_fill_parcel_clear(
                {'local_fill_cluster_id':cid},visible_disc):
            return False
        required=max(self.r.pathway_static_keepout,extent+1.5*self.U)
        reach=max(self.r.pathway_main_chip_keepout,self.r.component_pathway_clearance)+extent
        qb=(p[0]-reach,p[1]-reach,p[0]+reach,p[1]+reach)
        for gi,g in self.static_index.query(qb):
            keep=(self.r.pathway_main_chip_keepout if gi < len(self.chips) else self.r.component_pathway_clearance)
            if q.distance(g.geom)<keep+extent:
                return False
        # Existing main-chip network geometry is already in the spatial index by the time
        # local-gap roots are proposed.  Give source markers and the initial bundle envelope
        # breathing room rather than spawning directly beside an occupied trace.
        probe=q.buffer(half_width+max(2.0*self.U,.22*self.module),quad_segs=8)
        for rec in self.path_index.query(expand_bounds(probe.bounds,self.r.pathway_interroute_keepout+self.U)):
            gap=self.r.pathway_interroute_keepout
            if probe.intersects(rec['geom']) or probe.distance(rec['geom'])<gap:
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

    def _local_gap_initial_clear(self,center,direction,offsets,thicknesses,cluster_id=None):
        ids=list(range(len(thicknesses)))
        temp=dict(id=-1,ids=ids,chip=len(self.chips)+100000,side='local',side_index=-1,
                  local_gap=True,
                  local_fill_cluster_id=cluster_id,
                  local_fill_route_tile=None,
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

    def _launch_local_gap_fronts(self, source_cap=None, allow_region_overflow=False, candidate_work_cap=None, prefer_service_debt=False,
                                 wave_source_cap_override=None):
        """Spawn a coverage-driven local-network wave into residual open regions.

        The first wave measures the post-main residual field and samples a soft ~40% target.
        Later waves only target still-uncovered cells.  Exact routing invariants still decide
        what can physically be realised; the target never authorises intersections or search.
        """
        rng=SplitMix64(local_pathway_seed(self.sseed) ^ ((self.stats['pathway_local_gap_wave_count']+1)*0x9E3779B97F4A7C15))
        if not self.local_gap_open_cells:
            self.local_gap_open_cells=self._residual_gap_cells()
            self.local_gap_target_fraction=float(getattr(self,'local_gap_absolute_target_fraction',
                                                         rng.uniform(*self.r.local_gap_fill_range)))
            service_cells=max(1,int(self.local_gap_service_denominator_cell_count or len(self.local_gap_open_cells)))
            self.local_gap_target_count=int(round(service_cells*self.local_gap_target_fraction))
            # Internal planner target is expressed against the main-residual service budget.
            # V37 also reports the normalized 80-90% share of the post-component remainder.
            self.stats['pathway_local_gap_fill_target_fraction']=self.local_gap_target_fraction
            self.stats['pathway_local_gap_open_cell_count']=len(self.local_gap_open_cells)
            self.stats['pathway_local_gap_target_cell_count']=self.local_gap_target_count
        covered=self._local_gap_covered_cells()
        actual=self._local_gap_service_fraction()
        # Convert the honest served-area deficit to equivalent grid cells for source budgeting.
        # The stopping rule itself is area-based, not "number of cells touched".
        service_cells=max(1,int(self.local_gap_service_denominator_cell_count or len(self.local_gap_open_cells)))
        needed=max(0.0,(self.local_gap_target_fraction-actual)*service_cells)
        self.stats['pathway_local_gap_covered_cell_count']=len(covered)
        self.stats['pathway_local_gap_fill_actual']=actual
        if needed<=1e-9:
            return 0

        region_source_counts={r['id']:0 for r in self.local_gap_regions}
        cluster_source_counts=dict(self.local_fill_cluster_root_counts)
        sector_root_counts={}
        for f in self.fronts.values():
            if f.get('local_gap') and f.get('parent') is None and f.get('local_gap_region_id') is not None:
                rid0=f.get('local_gap_region_id')
                region_source_counts[rid0]=region_source_counts.get(rid0,0)+1
                x0,y0=f['path'][0]
                sector=(min(3,max(0,int(4*x0/self.W))),min(3,max(0,int(4*y0/self.H))))
                sector_root_counts[sector]=sector_root_counts.get(sector,0)+1
        region_uncovered_counts={r['id']:len(self._local_gap_targetable_cells(r['id'])) for r in self.local_gap_regions}

        margin=max(2.0*self.module,55.0*self.U)
        candidates=[]
        # V46: preserve the exact shuffled-cell / jitter RNG sequence, but batch the two nearest
        # geometry measurements.  The historical score clamps both distances at five modules,
        # and distance to a geometry collection is exactly the minimum distance to its members.
        uncovered=list(self._local_gap_targetable_cells())
        if candidate_work_cap is not None and prefer_service_debt and len(uncovered)>int(candidate_work_cap):
            # Partial-service rescue is a debt problem, not a fresh-coverage lottery.  Admit the
            # most under-served cells first, with seeded variation only inside equal-debt bands.
            # This keeps candidate work bounded while directing that work toward maximum physical
            # service gain instead of rescoring the entire partial-debt field every rescue wave.
            buckets={}
            for c in uncovered:
                debt_bits=self.local_gap_coverage_mask_by_cell.get(c,0).bit_count()
                buckets.setdefault(debt_bits,[]).append(c)
            admitted=[]
            for bits in sorted(buckets):
                band=buckets[bits]
                rng.shuffle(band)
                need=int(candidate_work_cap)-len(admitted)
                if need<=0: break
                admitted.extend(band[:need])
            uncovered=admitted
        else:
            rng.shuffle(uncovered)
            if candidate_work_cap is not None and len(uncovered)>int(candidate_work_cap):
                uncovered=uncovered[:int(candidate_work_cap)]
        raw=[]; xs=[]; ys=[]
        nx,ny=self.r.local_gap_grid_shape()
        for gx,gy in uncovered:
            self.stats['pathway_local_gap_spawn_attempt_count']+=1
            x=(gx+rng.uniform(.32,.68))*self.W/nx
            y=(gy+rng.uniform(.32,.68))*self.H/ny
            if not (margin<=x<=self.W-margin and margin<=y<=self.H-margin):
                continue
            raw.append((gx,gy,x,y)); xs.append(x); ys.append(y)

        score_cap=5.0*self.module
        if raw:
            qpts=shapely.points(xs,ys)
            static_geoms=[obj.geom for _oid,(_gi,obj) in self.static_index.objects.items()]
            if static_geoms:
                stree=STRtree(static_geoms)
                _pairs,sd=stree.query_nearest(qpts,return_distance=True,all_matches=False)
                static_dists=[min(score_cap,float(v)) for v in sd]
            else:
                static_dists=[score_cap]*len(raw)
            path_geoms=[rec['geom'] for rec in self.path_index.objects.values()]
            if path_geoms:
                ptree=STRtree(path_geoms)
                _pairs,pd=ptree.query_nearest(qpts,return_distance=True,all_matches=False)
                path_dists=[min(score_cap,float(v)) for v in pd]
            else:
                path_dists=[score_cap]*len(raw)
        else:
            static_dists=[]; path_dists=[]

        for (gx,gy,x,y),static_clear,path_clear in zip(raw,static_dists,path_dists):
            cell=(gx,gy); rid=self.local_gap_region_by_cell.get(cell)
            cid=self._local_route_cluster_for_source((x,y),create=False)
            region=self.local_gap_regions[rid] if rid is not None and rid < len(self.local_gap_regions) else None
            region_need=(region_uncovered_counts.get(rid,1) if region else 1)
            existing=region_source_counts.get(rid,0)
            score=static_clear+1.55*path_clear-.45*self._congestion_at((x,y))*self.module
            score+=1.35*self.module*math.log1p(region_need)/(1.0+.65*existing)
            sector=(min(3,max(0,int(4*x/self.W))),min(3,max(0,int(4*y/self.H))))
            open_mass=max(1,self.local_sector_open.get(sector,0))
            # Normalize both populations by genuinely available post-component
            # floor in this sector.  Static clearance still decides the source.
            score-=self.module*(8.0*sector_root_counts.get(sector,0)+
                2.0*self.local_sector_components.get(sector,0))/open_mass
            if region is not None and region['size']!='small':
                rvx,rvy=dir_vec(region['dir'])
                proj=abs((x-region['center'][0])*rvx+(y-region['center'][1])*rvy)
                norm=proj/max(.5*region['long_span'],1e-9)
                score+=(1.15 if region['size']=='large' else .65)*self.module*min(1.0,norm)
            candidates.append((score,rng.random(),(x,y),rid,cid))
        candidates.sort(key=lambda z:(-z[0],z[1]))
        if not candidates:
            return 0
        # Allocation below requests a specific residual region.  Preserve the exact global sort
        # order *within each region* once, rather than rescanning the whole board for every
        # planned source.  Candidate ids replace O(N) middle-list deletion.
        candidates_by_region={}
        for candidate_id,rec in enumerate(candidates):
            candidates_by_region.setdefault(rec[3],[]).append((candidate_id,)+rec)
        selected_candidate_ids=set()

        # V33: local traces are born independently. Source count is driven by residual area,
        # not by a fixed number of pre-bundled buses. A line usually claims roughly 2–4 grid
        # cells, so larger measured regions naturally receive several independent sources.
        wave_source_cap=(int(wave_source_cap_override) if wave_source_cap_override is not None
                         else self.r.local_wave_source_cap())
        min_wave_sources=max(1,int(getattr(self,'local_gap_min_wave_sources',6)))
        normal_target=max(min_wave_sources,min(wave_source_cap,int(math.ceil(needed/1.35))))
        if source_cap is not None:
            normal_target=max(1,min(normal_target,int(source_cap)))
        remaining_trace_capacity=max(0,self.r.local_gap_trace_population_cap()-self._local_gap_realized_trace_count())
        normal_target=min(normal_target,remaining_trace_capacity)
        if normal_target<=0:
            return 0
        if self.local_gap_special_probability is None:
            self.local_gap_special_probability=rng.uniform(.15,.26)
        special_probability=self.local_gap_special_probability

        # Connected route domains are immutable.  Build each source pool in one
        # pass from the already-ranked candidates; no foreign-domain candidate
        # can be nominated and rejected later by the macro geometry gate.
        caps={r['id']:(max(self.r.local_gap_region_source_cap(r['cell_count']),
                           region_source_counts.get(r['id'],0)+normal_target) if allow_region_overflow
                           else self.r.local_gap_region_source_cap(r['cell_count']))
              for r in self.local_gap_regions}
        candidates_by_cluster={}
        cluster_caps={}
        cluster_region={}
        for candidate_id,rec in enumerate(candidates):
            cid=rec[4]
            if cid in self.local_route_clusters:
                candidates_by_cluster.setdefault(cid,[]).append((candidate_id,)+rec)
        for cid,meta in self.local_route_clusters.items():
            have=cluster_source_counts.get(cid,0)
            cap=(max(int(meta['target_sources']),have+normal_target) if allow_region_overflow
                 else int(meta['target_sources']))
            if have>=cap:
                continue
            pool=candidates_by_cluster.get(cid,[])
            if not pool:
                continue
            cluster_caps[cid]=cap
            cluster_region[cid]=cid

        # Candidate pools outlive source quotas across successive waves.  Only active
        # domains enter capacity accounting and allocation; a spent domain has a
        # pool but no cap, so retaining it here both miscounts and raises KeyError.
        candidates_by_cluster={cid:pool for cid,pool in candidates_by_cluster.items()
                               if cid in cluster_caps and
                               region_source_counts.get(cid,0)<caps.get(cid,0)}

        capacity=sum(min(cluster_caps[cid]-cluster_source_counts.get(cid,0),
                         len(pool)) for cid,pool in candidates_by_cluster.items())
        normal_target=min(normal_target,capacity)
        if normal_target<=0:
            return 0

        alloc={cid:0 for cid in candidates_by_cluster}
        planned_region={r['id']:0 for r in self.local_gap_regions}
        heap=[]
        for cid,pool in candidates_by_cluster.items():
            rid=cluster_region[cid]
            if region_source_counts.get(rid,0)>=caps.get(rid,1):
                continue
            need=sum(16-self.local_gap_coverage_mask_by_cell.get(
                self._gap_cell(rec[3]),0).bit_count() for rec in pool)
            weight=need/(1.0+cluster_source_counts.get(cid,0))
            heapq.heappush(heap,(-weight,cid,need))
        remaining=normal_target
        while remaining>0 and heap:
            _weight,cid,need=heapq.heappop(heap)
            rid=cluster_region[cid]
            if (cluster_source_counts.get(cid,0)+alloc[cid]>=cluster_caps[cid] or
                    alloc[cid]>=len(candidates_by_cluster[cid]) or
                    region_source_counts.get(rid,0)+planned_region.get(rid,0)>=caps.get(rid,1)):
                continue
            alloc[cid]+=1; planned_region[rid]=planned_region.get(rid,0)+1; remaining-=1
            if cluster_source_counts.get(cid,0)+alloc[cid]<cluster_caps[cid]:
                heapq.heappush(heap,(-need/(1.0+cluster_source_counts.get(cid,0)+alloc[cid]),cid,need))
        ordered_cids=[cid for cid,q in alloc.items() if q]
        rng.shuffle(ordered_cids)
        plans=[]
        for cid in ordered_cids:
            plans.extend((rng.random()<special_probability,1,cluster_region[cid],cid)
                         for _ in range(alloc[cid]))


        used_points=[]
        used_point_index=SpatialHash(max(2.20*self.module,1e-6))
        local_index=self.stats['pathway_local_gap_source_count']; normal_spawned=0; special_spawned=0
        spawned=0
        source_sep=2.20*self.module
        # A rejected source can only become harder to admit within this wave:
        # accepted roots add separation, while static/route obstacles persist.
        # Keep a cursor for each domain and stroke mode so later plans do not
        # repeatedly rescan its already tried prefix.
        source_cursor={}
        for special,count,wanted_rid,wanted_cluster in plans:
            chosen=None
            cursor_key=(wanted_cluster,bool(special))
            pool=candidates_by_cluster.get(wanted_cluster,())
            cursor=source_cursor.get(cursor_key,0)
            while cursor<len(pool):
                candidate_id,score,_,center,rid,_candidate_cid=pool[cursor]
                cursor+=1
                source_cursor[cursor_key]=cursor
                cid=wanted_cluster
                if candidate_id in selected_candidate_ids:
                    continue
                cx,cy=center
                if any(math.hypot(cx-p[0],cy-p[1])<source_sep
                       for p in used_point_index.query((cx-source_sep,cy-source_sep,cx+source_sep,cy+source_sep))):
                    continue
                region=self.local_gap_regions[rid] if rid is not None and rid < len(self.local_gap_regions) else None
                if region is not None:
                    cap=caps.get(rid,self.r.local_gap_region_source_cap(region['cell_count']))
                    if region_source_counts.get(rid,0)>=cap:
                        continue
                thicks,offsets,pitch=self._local_gap_bundle_spec(rng,count,special)
                if region is not None:
                    # Scale local stroke to the room: smaller pockets get lighter lines.
                    factor=.78 if region['size']=='small' else (1.0 if region['size']=='medium' else 1.08)
                    thicks=[t*factor for t in thicks]
                half=max((abs(offsets.get(i,0.0))+.5*thicks[i] for i in range(count)),default=.5*thicks[0])
                marker_extent=(half if special else
                               self.r._termination_dot_radius(max(thicks))+.5*self.r.termination_dot_hollow_stroke)
                if not self._local_gap_source_clearance(center,half,marker_extent=marker_extent,
                                                        cluster_id=cid):
                    continue
                dirs=list(range(8)); rng.shuffle(dirs)
                scored=[]
                for d in dirs:
                    if not self._local_gap_initial_clear(center,d,offsets,thicks,cluster_id=cid):
                        continue
                    p2=point_along_dir(center,d,2.5*self.module)
                    tgt=self._local_gap_target(center,rng,d,cluster_id=cid)
                    before=math.hypot(tgt[0]-center[0],tgt[1]-center[1])
                    after=math.hypot(tgt[0]-p2[0],tgt[1]-p2[1])
                    scored.append((self._congestion_at(p2)-1.8*(before-after)/max(self.module,1e-9),
                                   -self._forward_frame_distance(center,d),rng.random(),d,tgt))
                if not scored:
                    self.stats['pathway_local_gap_spawn_reject_count']+=1
                    continue
                scored.sort(); direction=scored[0][3]; target=scored[0][4]
                chosen=(candidate_id,center,thicks,offsets,pitch,direction,target,rid,cid)
                break
            if chosen is None:
                continue
            candidate_id,center,thicks,offsets,pitch,direction,target,rid,cid=chosen
            selected_candidate_ids.add(candidate_id); used_points.append(center)
            used_point_index.insert(center,(center[0],center[1],center[0],center[1]))
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
                                  intent='explore',target=target,forced_straight_modules=2,
                                  local_cluster_id=cid)
            root['local_gap']=True; root['local_gap_special']=bool(special); root['fan_pending']=False
            root['local_gap_region_id']=rid
            root['local_fill_cluster_target']=cluster_caps[cid]
            cluster_source_counts[cid]=cluster_source_counts.get(cid,0)+1
            root['local_gap_turn_count']=0
            root['local_gap_turn_due_straights']=1+int(rng.random()*3)
            root['local_gap_branch_boost']=rng.uniform(*self.r.local_gap_branch_boost_range)
            root['local_gap_exit_allowed']=rng.random()<self.r.local_gap_exit_probability_factor
            region=self.local_gap_regions[rid] if rid is not None and rid < len(self.local_gap_regions) else None
            if region is None:
                root['max_gestures']=14+int(rng.random()*7); root['local_gap_min_terminal_modules']=3.75
            elif region['size']=='small':
                root['max_gestures']=7+int(rng.random()*6); root['local_gap_min_terminal_modules']=2.75
            elif region['size']=='medium':
                root['max_gestures']=14+int(rng.random()*9); root['local_gap_min_terminal_modules']=3.5
            else:
                root['max_gestures']=22+int(rng.random()*11); root['local_gap_min_terminal_modules']=5.0
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
        realized=[cluster_source_counts.get(cid,0) for cid in cluster_caps]
        self.stats['pathway_local_gap_fill_cluster_realized_max']=max(realized,default=0)
        self.stats['pathway_local_gap_fill_cluster_realized_min']=min((v for v in realized if v>0),default=0)
        self.stats['pathway_local_gap_fill_cluster_realized_nonempty_count']=sum(1 for v in realized if v>0)
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
        if not self._gesture_clear(tf,b,c,g2,allow_outside=allow2): return None
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
        # Fan as soon as the perpendicular emergence gesture exists.  The child transaction
        # carries the remainder of the ordinary four-module survival obligation.  Importantly,
        # this is no longer an *unsplit root-bus* lock: ownership is already partitioned after
        # the first emergence gesture, and each cohort's survival maneuver is solved separately.
        root_min_modules=self._minimum_materialized_lane_length(f)/max(self.module,1e-9)
        survival_remainder=max(2,min(4,int(math.ceil(max(0.0,self.main_launch_maturity_modules-root_min_modules)-1e-9))))
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
                                   fan_group=(f['chip'],f['side_index']),forced_straight_modules=survival_remainder,
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
                child['local_gap_turn_count']=int(f.get('local_gap_turn_count',0))
                child['local_gap_turn_due_straights']=int(f.get('local_gap_turn_due_straights',2))
            children.append(child)
        # Transactional fan: solve the short child maneuvers as one tiny local permutation.
        # V48 used one fixed outward/straight pattern whenever it was merely legal and consulted
        # the permutation layer only on failure.  That made launch topology look authored by a
        # deterministic rule rather than sampled from the available space.  We now inspect a
        # bounded seeded shortlist of legal non-crossing permutations on every launch and choose
        # among their space-aware scores.  This remains a tiny local transaction, never routing
        # search: at most four viable alternatives are scored.
        preferred=tuple(child.get('branch_turn',0) for child in children)
        def solve_turns(turns):
            seqs=[]; physical_tails={}
            for child,turn in zip(children,turns):
                child['branch_turn']=turn; child['branch_stage']=0
                child['forced_straight_modules']=survival_remainder
                child['forced_turn_modules']=turn_modules
                seq=self._structural_birth_sequence(child)
                if seq is None: return None
                # Early fan is legal only if the complete newborn maneuver itself proves the
                # hard per-lane survival floor.  Simulate materialized offset lanes before any
                # parent topology is mutated.
                tf=dict(child)
                tf['path']=list(child.get('path',()))+[p['end'] for p in seq]
                tf['dir']=seq[-1]['dir'] if seq else child['dir']
                paths=self._materialized_paths(tf)
                for tid in child.get('ids',()):
                    pts=paths.get(tid,())
                    L=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:]))
                    if L<self.main_launch_maturity_modules*self.module-1e-7:
                        return None
                # Coarse cohort envelopes intentionally overlap near a fan split, so using the
                # generic bundle-envelope conflict predicate here falsely rejected every turning
                # fan.  Validate the actual rendered lanes instead.  The local offset tails begin
                # at the inherited split endpoints and contain only this newborn transaction.
                physical_tails[child['id']]={
                    tid:self._offset_points(tf['path'],child['offsets'][tid])
                    for tid in child.get('ids',())}
                seqs.append((child,seq))
            for i,(ca,_sa) in enumerate(seqs):
                for cb,_sb in seqs[i+1:]:
                    for ta,pa in physical_tails[ca['id']].items():
                        if len(pa)<2: continue
                        la=LineString(pa)
                        for tb,pb in physical_tails[cb['id']].items():
                            if len(pb)<2: continue
                            required=.5*(ca['thicknesses'][ta]+cb['thicknesses'][tb])+self.r.pathway_interroute_keepout
                            lb=LineString(pb)
                            if la.intersects(lb) or la.distance(lb)<required-1e-7:
                                return None
            return seqs
        # A fan is an ordered family, so useful spread permutations are monotone rather than
        # arbitrary 3^N turn tuples: some number of cohorts may peel outward from each edge
        # while interior cohorts continue straight.  This gives 3-way visual spread without
        # making siblings cross through each other.  Even an eight-cohort bus has only 25 such
        # layouts, so we can inspect a seeded bounded sample on every launch.
        n=len(children); mid=(n-1)/2
        top=[i for i in range(n) if i<mid]
        bottom=[i for i in range(n) if i>mid]
        turn_sets=[]
        for nt in range(len(top)+1):
            for nb in range(len(bottom)+1):
                turns=[0]*n
                for i in top[:nt]: turns[i]=1
                for i in bottom[len(bottom)-nb:]: turns[i]=-1
                turn_sets.append(tuple(turns))
        if preferred not in turn_sets:
            turn_sets.append(preferred)
        # Stable per-launch randomization: this does not consume the downstream route RNG.
        # Geometry remains the dominant score, but equally-open fan layouts genuinely vary by
        # seed instead of a fixed outward/straight recipe always winning merely because legal.
        prng=SplitMix64(mix_once(self.sseed ^ 0x6A09E667F3BCC909 ^ ((f['id']+1)<<23)))
        decorated=[]
        for turns in dict.fromkeys(turn_sets):
            diversity=len(set(turns)); turning=sum(1 for t in turns if t)
            all_straight=(turning==0)
            order_key=prng.random()-.10*diversity+(.18 if all_straight else 0.0)
            decorated.append((order_key,tuple(turns)))
        decorated.sort(key=lambda x:(x[0],x[1]))
        viable=[]
        for _order,turns in decorated:
            seqs=solve_turns(turns)
            if seqs is None: continue
            # Rank the *space after the fan*, not just whether the first two gestures fit.
            caps=[]
            for child,seq in seqs:
                last=seq[-1]
                caps.append(self._local_space_capacity(child,last['end'],last['dir']))
            diversity=len(set(turns)); turning=sum(1 for t in turns if t)
            all_straight=(turning==0)
            mean_cap=sum(caps)/max(1,len(caps)); min_cap=min(caps,default=0.0)
            score=mean_cap+0.35*min_cap+0.30*diversity-0.06*turning-(0.85 if all_straight else 0.0)
            score+=prng.uniform(-.70,.70)
            viable.append((score,tuple(turns),seqs))
            if len(viable)>=min(10,len(decorated)):
                break
        sequences=None; chosen_turns=None
        if viable:
            viable.sort(key=lambda x:(-x[0],x[1]))
            _score,chosen_turns,sequences=viable[0]
            for child,turn in zip(children,chosen_turns):
                child['branch_turn']=turn; child['branch_stage']=0; child['fan_birth_turn']=turn
        if sequences is None:
            for child in children: self._drop_front(child['id'])
            f['fan_pending']=True
            self.stats['pathway_branch_preflight_reject_count']+=1
            self.stats['pathway_transactional_birth_reject_count']+=1
            return []
        if chosen_turns!=preferred:
            self.stats.setdefault('pathway_fan_permutation_fallback_count',0)
            self.stats['pathway_fan_permutation_fallback_count']+=1
        self.stats.setdefault('pathway_fan_permutation_viable_option_count',0)
        self.stats['pathway_fan_permutation_viable_option_count']+=len(viable)
        self.stats.setdefault('pathway_fan_birth_turning_cohort_count',0)
        self.stats.setdefault('pathway_fan_birth_straight_cohort_count',0)
        self.stats.setdefault('pathway_fan_birth_direction_diversity_sum',0)
        self.stats['pathway_fan_birth_turning_cohort_count']+=sum(1 for t in chosen_turns if t)
        self.stats['pathway_fan_birth_straight_cohort_count']+=sum(1 for t in chosen_turns if not t)
        self.stats['pathway_fan_birth_direction_diversity_sum']+=len(set(chosen_turns))
        f['status']='branched'; f['fan_pending']=False
        self.stats['pathway_split_count']+=1
        if f.get('local_gap'): self.stats['pathway_local_gap_split_count']+=1
        for child,seq in sequences:
            for proposal in seq:
                if child.get('status')!='active': break
                self._accept(child,proposal)
            # Early fan-out replaces the root bus only because this exact maneuver proves the
            # newborn cohort's four-module survival.  Preserve those owned structural segments
            # as a topology rollback floor.  A later reroute can change the route beyond the
            # fan, but cannot rewind through the certificate and leave an impossible
            # under-survival branch_stage cohort behind.
            child['recovery_floor_segments']=max(
                int(child.get('recovery_floor_segments',0)),len(child.get('path',()))-1)
            self.stats.setdefault('pathway_transactional_survival_floor_lock_count',0)
            self.stats['pathway_transactional_survival_floor_lock_count']+=1
        # The fan transaction itself discharged every child's four-module survival debt, so the
        # old straight source-ray reservations are no longer needed and must not occupy empty
        # space after the children have visibly peeled away.
        if all(self._minimum_materialized_lane_length(child)>=self.main_launch_maturity_modules*self.module-1e-7
               for child in children):
            self._release_source_egress(self._launch_family_key(f))
            f['launch_egress_pending']=False
        else:
            raise RuntimeError(f'launch fan survival transaction invariant failed (sample_seed={self.sseed}, front={f["id"]})')
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

    def _branch_local_singleton(self,f):
        """Fork one independently-born local line into a new physical trace.

        V23-V34 multiplied the local branch *probability* but singleton local sources could not
        actually branch because the generic brancher only partitions multi-lane bundles.  V37
        makes the rule real: a mature local singleton may sprout one ±45-degree child toward
        uncovered capacity while the parent keeps travelling independently.
        """
        if (not f.get('local_gap') or f.get('local_gap_special') or len(f.get('ids',()))!=1 or
                f.get('local_gap_branch_count',0)>=1 or f.get('depth',0)>=2 or f.get('gestures',0)<2 or
                self._local_gap_realized_trace_count()>=self.r.local_gap_trace_population_cap()):
            return []
        head=f['path'][-1]; parent_tid=f['ids'][0]
        candidates=[]
        for turn in (-1,1):
            d=(f['dir']+turn)%8
            tid=self.next_trace_id
            t=f['thicknesses'][parent_tid]*f['rng'].uniform(.88,1.06)
            child=self._make_front(ids=[tid],chip=f['chip'],side=f['side'],side_index=f['side_index'],
                                   path=[head],direction=d,offsets={tid:0.0},thicknesses={tid:t},prefixes={tid:[]},
                                   rng=SplitMix64(f['rng'].next_u64()),depth=f.get('depth',0)+1,intent='explore',
                                   target=self._local_gap_target(head,f['rng'],d,
                                       cluster_id=f.get('local_fill_cluster_id')),parent=f['id'])
            child['local_gap']=True; child['local_gap_special']=False; child['fan_pending']=False
            child['local_gap_region_id']=f.get('local_gap_region_id')
            child['local_gap_turn_count']=0
            child['local_gap_turn_due_straights']=1+int(f['rng'].random()*3)
            child['local_gap_branch_boost']=f.get('local_gap_branch_boost',4.0)
            child['local_gap_exit_allowed']=f.get('local_gap_exit_allowed',False)
            child['local_gap_min_terminal_modules']=max(3.5,.78*float(f.get('local_gap_min_terminal_modules',5.0)))
            child['max_gestures']=max(7,min(20,int(f.get('max_gestures',12)-f.get('gestures',0)+5)))
            child['base_max_gestures']=child['max_gestures']
            end=point_along_dir(head,d,2.0*self.module); geom=self._corridor_geom(child,head,end)
            if self._gesture_clear(child,head,end,geom,allow_outside=False):
                cap=self._local_space_capacity(child,head,d)
                candidates.append((cap,turn,child,tid,end,geom))
            else:
                self._drop_front(child['id'])
        if not candidates:
            return []
        candidates.sort(key=lambda z:(-z[0],z[1]))
        _cap,_turn,child,tid,end,geom=candidates[0]
        for losing in candidates[1:]:
            self._drop_front(losing[2]['id'])
        self.next_trace_id=max(self.next_trace_id,tid+1)
        child['path'].append(end); child['travel']=2.0*self.module; child['gestures']=1; child['local_gestures']=1
        child['straight_since_turn']=1; child['dir']=nearest_dir_index(end[0]-head[0],end[1]-head[1])
        self._record_segment(child,head,end,geom,normal=True)
        f['local_gap_branch_count']=f.get('local_gap_branch_count',0)+1
        self.branch_junction_pairs[tuple(sorted((parent_tid,tid)))]=head
        self.stats['pathway_split_count']+=1; self.stats['pathway_local_gap_split_count']+=1
        self.stats['pathway_local_gap_trace_count']+=1
        self.stats.setdefault('pathway_local_gap_singleton_branch_count',0)
        self.stats['pathway_local_gap_singleton_branch_count']+=1
        return [child]

    def _branch_front(self,f):
        if self._source_egress_pending(f):
            return []
        if f.get('local_gap') and len(f.get('ids',()))==1:
            return self._branch_local_singleton(f)
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
                target=self._local_gap_target((cx,cy),f['rng'],(f['dir']+branch_turn)%8,
                    cluster_id=f.get('local_fill_cluster_id'))
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
                    target=self._local_gap_target((cx,cy),f['rng'],f['dir'],
                        cluster_id=f.get('local_fill_cluster_id'))
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
                    child['target']=self._local_gap_target((cx,cy),child['rng'],
                        (f['dir']+turn)%8 if turn else f['dir'],
                        cluster_id=child.get('local_fill_cluster_id'))
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
                child['local_gap_turn_count']=int(f.get('local_gap_turn_count',0))
                child['local_gap_turn_due_straights']=int(f.get('local_gap_turn_due_straights',2))
            children.append(child)
        # Do not commit a fork whose children are born into a wall.  This is a cheap local
        # viability check, not route search: each child only tests its mandatory first rebase
        # gesture against the already-existing board.  If either side cannot emerge, the
        # parent stays active and may advance/reroute before trying to split again.
        blocked=False
        # A MAIN family that is still below the hard four-module survival floor may branch,
        # but it may not hand that debt to newborn children and hope later arbitration happens
        # to complete their mandatory rebase/peel.  That was a real totality hole: the parent
        # topology could be discarded after only an individual viability probe, then two young
        # siblings could HOLD/block one another until the finite persistence clock expired with
        # ``under_survival_floor + branch_stage`` debt.
        #
        # For such young MAIN branches, prove the *complete* mandatory structural maneuver for
        # every child from the same committed snapshot and require that maneuver itself to carry
        # every physical lane across the unchanged four-module survival floor.  The tiny sibling
        # transaction is also checked at rendered-lane level, because coarse cohort envelopes
        # intentionally overlap around a legal split.  Only after this proof succeeds may the
        # parent topology be replaced; the proved sequence is then committed immediately.
        young_main_transaction=(not f.get('local_gap') and
                                self._minimum_materialized_lane_length(f) <
                                self.main_launch_maturity_modules*self.module-1e-7)
        young_sequences=[]
        if young_main_transaction:
            physical_tails={}
            for child in children:
                seq=self._structural_birth_sequence(child)
                if seq is None:
                    blocked=True
                    break
                tf=dict(child)
                tf['path']=list(child.get('path',()))+[p['end'] for p in seq]
                tf['dir']=seq[-1]['dir'] if seq else child['dir']
                paths=self._materialized_paths(tf)
                if any(
                    sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(paths.get(tid,()),paths.get(tid,())[1:])) <
                    self.main_launch_maturity_modules*self.module-1e-7
                    for tid in child.get('ids',())
                ):
                    blocked=True
                    break
                physical_tails[child['id']]={
                    tid:self._offset_points(tf['path'],child['offsets'][tid])
                    for tid in child.get('ids',())}
                young_sequences.append((child,seq))
            if not blocked:
                for i,(ca,_sa) in enumerate(young_sequences):
                    for cb,_sb in young_sequences[i+1:]:
                        for ta,pa in physical_tails[ca['id']].items():
                            if len(pa)<2: continue
                            la=LineString(pa)
                            for tb,pb in physical_tails[cb['id']].items():
                                if len(pb)<2: continue
                                required=.5*(ca['thicknesses'][ta]+cb['thicknesses'][tb])+self.r.pathway_interroute_keepout
                                lb=LineString(pb)
                                if la.intersects(lb) or la.distance(lb)<required-1e-7:
                                    blocked=True
                                    break
                            if blocked: break
                        if blocked: break
                    if blocked: break
        strict_birth=((f.get('travel',0.0)<5*self.module or rescue_branch) and not local_parallel_split)
        for child in children if not young_main_transaction else ():
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
                self._drop_front(child['id'])
            f['branch_retry_after_gesture']=f['gestures']+1
            self.stats['pathway_branch_preflight_reject_count']+=1
            self.stats['pathway_transactional_birth_reject_count']+=1
            return []
        f['status']='branched'
        self.stats['pathway_split_count']+=1
        if f.get('local_gap'): self.stats['pathway_local_gap_split_count']+=1
        if young_main_transaction:
            for child,seq in young_sequences:
                for proposal in seq:
                    if child.get('status')!='active': break
                    self._accept(child,proposal)
                # The committed structural maneuver is the certificate that made replacing
                # the young parent topology legal.  Ordinary traceback may reroute *after*
                # that certificate, but it may not erase it while leaving the child topology
                # in existence; doing so recreates an under-survival branch_stage child that
                # could never have been born legally.
                child['recovery_floor_segments']=max(
                    int(child.get('recovery_floor_segments',0)),len(child.get('path',()))-1)
                self.stats.setdefault('pathway_transactional_survival_floor_lock_count',0)
                self.stats['pathway_transactional_survival_floor_lock_count']+=1
            if any(
                child.get('status')=='active' and
                self._minimum_materialized_lane_length(child) <
                self.main_launch_maturity_modules*self.module-1e-7
                for child,_seq in young_sequences
            ):
                raise RuntimeError(
                    f'young MAIN branch survival transaction invariant failed '
                    f'(sample_seed={self.sseed}, parent={f["id"]})')
            self.stats.setdefault('pathway_young_branch_survival_transaction_count',0)
            self.stats['pathway_young_branch_survival_transaction_count']+=1
        return children

    def _should_branch(self,f):
        if f.get('fan_pending'):
            return False
        is_local=bool(f.get('local_gap'))
        if len(f['ids'])<=1:
            if (not is_local or f.get('local_gap_special') or f.get('depth',0)>=2 or
                    f.get('local_gap_branch_count',0)>=1 or f.get('gestures',0)<2 or
                    f.get('straight_since_turn',0)<1 or self._local_gap_realized_trace_count()>=self.r.local_gap_trace_population_cap()):
                return False
            boost=float(f.get('local_gap_branch_boost',4.0))
            return f['rng'].random()<min(.30,.055*boost)
        if f['depth']>=5 or f['branch_stage'] is not None:
            return False
        if f['gestures']<f.get('branch_retry_after_gesture',0):
            return False
        # A shared round-level connection opportunity is allowed to peel a narrow child out
        # sooner.  The opportunity was computed from the same pre-move snapshot for all fronts.
        connection_guided=f.get('round_connection_peer') is not None
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

    def _refresh_active_head_snapshot(self,active):
        """Build one shared deterministic broad phase for an immutable routing-round snapshot."""
        heads=[f for f in active if f.get('status')=='active' and f.get('path')]
        self._active_head_index=SpatialHash(max(8.0*self.module,80.0*self.U))
        self._active_head_count=0
        self._active_head_distance_cache={}
        self._protected_family_owners={self._launch_family_key(f) for f in heads if not f.get('local_gap') and self._source_egress_pending(f)}
        for f in heads:
            x,y=f['path'][-1]
            self._active_head_index.insert(f,(x,y,x,y)); self._active_head_count+=1

    def _nearest_foreign_head_distance(self,p,chip):
        """Exact nearest foreign-head distance using the shared spatial hash.

        Radius expansion stops as soon as any foreign head is found; at that point every
        unqueried head is farther than the search radius, so the minimum among queried foreign
        heads is the global minimum.  This replaces one STRtree-per-chip snapshot rebuild.
        """
        if self._active_head_index is None or not getattr(self,'_active_head_count',0): return None
        cache=getattr(self,'_active_head_distance_cache',None)
        key=(float(p[0]),float(p[1]),int(chip))
        if cache is not None and key in cache:
            return cache[key]
        x,y=p; radius=max(4.0*self.module,80.0*self.U)
        max_radius=max(radius,math.hypot(self.W,self.H)+2.0*self.module)
        while radius<=max_radius+1e-9:
            nearby=self._active_head_index.query((x-radius,y-radius,x+radius,y+radius))
            best=None
            for f in nearby:
                if f.get('chip')==chip or f.get('gestures',0)<=0 or not f.get('path'): continue
                q=f['path'][-1]; d=math.hypot(q[0]-x,q[1]-y)
                if d<=radius+1e-9 and (best is None or d<best): best=d
            if best is not None:
                if cache is not None: cache[key]=best
                return best
            # Do not permanently suppress heads that were inside the square query but outside
            # this circular radius: they become eligible on a later expansion.
            radius*=2.0
        if cache is not None: cache[key]=None
        return None

    def _assign_round_connection_targets(self,active,round_index):
        """Pair compatible MAIN launch families from one immutable round snapshot via a local broad phase."""
        for f in active:
            f['round_connection_peer']=None; f['round_connection_target']=None
        self._refresh_active_head_snapshot(active)
        candidates=[]
        ordered=sorted((f for f in active if f['gestures']>=1 and f.get('branch_stage')!=0 and
                        not f.get('local_gap') and not self._source_egress_pending(f)),key=lambda x:x['id'])
        eligible={f['id']:f for f in ordered}
        max_global=18.0*self.module
        for a in ordered:
            pa=a['path'][-1]
            nearby=(self._active_head_index.query((pa[0]-max_global,pa[1]-max_global,pa[0]+max_global,pa[1]+max_global))
                    if self._active_head_index is not None else ordered)
            for b in nearby:
                if b['id']<=a['id'] or b['id'] not in eligible or not self._connection_family_compatible(a,b):
                    continue
                pb=b['path'][-1]; d=math.hypot(pb[0]-pa[0],pb[1]-pa[1])
                desire=(a['intent']=='connect')+(b['intent']=='connect')
                max_d=(18.0 if desire else 13.0)*self.module
                if d<.55*self.module or d>max_d: continue
                narrow_bonus=.45*(1.0/min(len(a['ids']),4)+1.0/min(len(b['ids']),4))
                cross_chip=(a['chip']!=b['chip'])
                priority=d/self.module-1.35*desire-narrow_bonus-(4.0 if cross_chip else 0.0)
                candidates.append((priority,a,b,d,desire,cross_chip))
        candidates.sort(key=lambda x:(x[0],x[1]['id'],x[2]['id']))
        used=set(); paired=0
        for _,a,b,d,desire,cross_chip in candidates:
            if a['id'] in used or b['id'] in used: continue
            prng=SplitMix64(mix_once(self.sseed ^ 0xA24BAED4963EE407 ^
                                     ((round_index+1)*0x9E3779B97F4A7C15) ^
                                     ((a['id']+1)<<17) ^ ((b['id']+1)<<41)))
            pa,pb=a['path'][-1],b['path'][-1]
            va=dir_vec(a['dir']); vb=dir_vec(b['dir']); ux=(pb[0]-pa[0])/max(d,1e-9); uy=(pb[1]-pa[1])/max(d,1e-9)
            facing=(va[0]*ux+va[1]*uy>.18 and vb[0]*(-ux)+vb[1]*(-uy)>.18)
            young_close=(facing and d<=5.0*self.module and
                         (a.get('travel',0.0)<4.0*self.module or b.get('travel',0.0)<4.0*self.module or
                          self._refresh_lifecycle(a) in ('LAUNCHING','RECOVERING') or
                          self._refresh_lifecycle(b) in ('LAUNCHING','RECOVERING')))
            forced_close=(d<=3.0*self.module and facing) or young_close
            chance=1.0 if (forced_close or cross_chip) else min(.995,.78*self.profile['connection_appetite']+.10*desire)
            if not cross_chip and prng.random()>=chance: continue
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
        # Release only affinities that actually existed and have now expired/lost their peer.
        # An ordinary unbundled local trace must keep its existing journey target; treating
        # ``peer is None`` as a bundle release retargeted every free trace every round, changing
        # intended behavior and repeatedly re-ranking whole residual regions.
        for f in locals_:
            peer_id=f.get('local_bundle_peer')
            if peer_id is None:
                continue
            peer=byid.get(peer_id)
            if f.get('local_bundle_until',-1) <= round_index or peer is None:
                self.stats['pathway_local_gap_bundle_release_count']+=1
                f['local_bundle_peer']=None; f['local_bundle_until']=-1; f['local_bundle_dir']=None
                f['target']=self._local_gap_target(f['path'][-1],f['rng'],f['dir'],
                    cluster_id=f.get('local_fill_cluster_id'))
        free=[f for f in locals_ if f.get('local_bundle_peer') is None and f.get('local_bundle_times',0)<1]
        candidates=[]
        # Pairing is intrinsically local (same residual region, <=3.2 modules).  V45 still
        # compared every free local trace with every other trace each round, turning a dense
        # filler wave into O(N^2).  Spatial enumeration below returns the exact same eligible
        # pairs; the historical distance/direction/probability rules and final ordering remain.
        pair_radius=3.2*self.module
        free_index=SpatialHash(max(pair_radius,1e-6)); free_order={}
        for i,f in enumerate(free):
            free_order[f['id']]=i; px,py=f['path'][-1]; free_index.insert(f,(px,py,px,py))
        for i,a in enumerate(free):
            pa=a['path'][-1]
            nearby=free_index.query((pa[0]-pair_radius,pa[1]-pair_radius,pa[0]+pair_radius,pa[1]+pair_radius))
            for b in nearby:
                if free_order[b['id']]<=i: continue
                if a.get('local_gap_region_id')!=b.get('local_gap_region_id'): continue
                pb=b['path'][-1]; d=math.hypot(pb[0]-pa[0],pb[1]-pa[1])
                if not (.55*self.module <= d <= pair_radius): continue
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
        # Source egress is a survival obligation, not a straight-run lock.  The ordinary
        # grammar below already keeps gesture zero perpendicular to the chip; after that
        # a still-young root may use the same legal straight/+45/-45 choices as any route.
        if f.get('local_gap') and f.get('local_bundle_peer') is not None and f.get('local_bundle_dir') is not None:
            shared=f['local_bundle_dir']; delta=(shared-f['dir'])%8
            if delta in (0,1,7):
                # Alignment is a preference; ±45 remains available so exact geometry always wins.
                dirs=[shared,f['dir'],(shared-1)%8,(shared+1)%8]
                out=[]
                for d in dirs:
                    if d not in out and (d-f['dir'])%8 in (0,1,7): out.append(d)
                return out
        # A root side bus should read as one perpendicular emergence followed by a fan.  If the
        # transactional fan is not yet viable, keep advancing that *same emergence corridor*
        # rather than allowing the complete unsplit bus to make an ordinary aesthetic bend.
        # This is geometry-driven fan deferral, not a four-module straight lock.
        if f.get('parent') is None and f.get('fan_pending') and not f.get('local_gap'):
            return [f['dir']]
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
        # Do not consume the four-module survival floor as one forced straight gesture.
        # Segment lengths follow the ordinary gesture grammar; source-egress persistence
        # remains hard until cumulative materialized lane length reaches four modules.
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
        # A flat-capped buffer of one straight segment is exactly its oriented rectangle.
        # Construct that primitive directly so ordinary candidate checks avoid an expensive GEOS
        # buffer operation; keep the existing circular miter envelope unchanged at real turns.
        dx=b[0]-a[0]; dy=b[1]-a[1]; L=math.hypot(dx,dy)
        if L<=1e-12:
            return GeometryCollection()
        px=-dy/L*half; py=dx/L*half
        geom=Polygon(((a[0]+px,a[1]+py),(b[0]+px,b[1]+py),
                      (b[0]-px,b[1]-py),(a[0]-px,a[1]-py)))
        if len(f['path'])>=2:
            olddir=nearest_dir_index(f['path'][-1][0]-f['path'][-2][0],f['path'][-1][1]-f['path'][-2][1])
            newdir=nearest_dir_index(dx,dy)
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
        """Cheap exact check of the newly affected offset-lane tail.

        V44 also evaluates the *first* gesture of a structural/fragment child.  Such a child
        starts with a one-point centerline but already owns a real rendered prefix; returning
        True merely because ``len(path)==1`` allowed the first newborn turn to complete an
        inherited A→B→A→B weave.
        """
        pts0=list(f.get('path',()))
        if not pts0:
            return True
        newdir=nearest_dir_index(end[0]-pts0[-1][0],end[1]-pts0[-1][1])
        has_prefix=any(bool(f.get('prefixes',{}).get(tid)) for tid in f.get('ids',()))
        # A straight continuation cannot introduce a new turn only when there is no inherited
        # visible history whose last headings need to be reconciled with the newborn centerline.
        if newdir==f.get('dir') and not has_prefix:
            return True
        center_tail=(pts0[-4:] if len(pts0)>=2 else [pts0[-1]])+[tuple(end)]
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


    def _consume_gesture_check(self):
        """Record one logical exact-gesture check.

        The budget is diagnostic/work-accounting only.  Every caller is already inside a
        finite candidate/round loop; making this counter fatal turned a performance guard into
        a seed-acceptance mechanism.  V48 records over-budget work loudly without changing
        whether a valid deterministic seed exists.
        """
        self.gesture_check_count+=1
        self.stats['pathway_gesture_clear_check_count']=self.gesture_check_count
        self.stats['pathway_gesture_clear_check_budget']=self.gesture_check_budget
        if self.gesture_check_count>self.gesture_check_budget:
            self.stats['pathway_gesture_clear_check_budget_exceeded']=True
            self.stats['pathway_gesture_clear_check_budget_overage']=self.gesture_check_count-self.gesture_check_budget

    def _local_visible_state_signature(self,f):
        """Exact dependency state for the board-independent visible-lane gate."""
        ids=tuple(f.get('ids',()))
        return (tuple(f.get('path',())),int(f.get('dir',-1)),f.get('last_turn_sign'),ids,
                tuple((tid,tuple(f.get('prefixes',{}).get(tid,())),f.get('offsets',{}).get(tid)) for tid in ids))

    def _local_visible_candidate_ok(self,f,end):
        """Exact board-independent visible-lane gate for one candidate endpoint."""
        if not self._visible_lane_step_ok(f,end):
            return False
        nd=nearest_dir_index(end[0]-f['path'][-1][0],end[1]-f['path'][-1][1])
        dd=(nd-f.get('dir',nd))%8
        sign=1 if dd==1 else -1 if dd==7 else 0
        risky_visible_turn=(sign and f.get('last_turn_sign') and sign==-f.get('last_turn_sign'))
        risky_structural=(sign and bool(f.get('prefixes')))
        return not ((risky_visible_turn or risky_structural) and not self._visible_lane_tail_grammar_ok(f,end))

    def _gesture_clear(self,f,a,b,geom,allow_outside=False,extra_segments=(),local_grammar_prechecked=False):
        if self._capture_gesture_failure_cert:
            self._last_gesture_failure_cert=None
        self._consume_gesture_check()
        # Reject malformed/empty candidate geometry before it reaches any spatial broad phase.
        # Shapely empty geometries expose NaN bounds; the one intentional empty-difference case
        # (a terminal connection leg wholly inside its junction envelope) is handled explicitly
        # by _special_leg_clear instead of being treated as an ordinary gesture.
        if (not all(math.isfinite(float(v)) for v in (a[0],a[1],b[0],b[1])) or
                geom is None or geom.is_empty):
            return False
        gb=geom.bounds
        if len(gb)!=4 or not all(math.isfinite(float(v)) for v in gb):
            return False
        if f.get('local_gap'):
            cid=f.get('local_fill_cluster_id')
            if self._local_macro_endpoint_excluded(f,b):
                self.stats['pathway_local_macro_boundary_reject_count']=self.stats.get('pathway_local_macro_boundary_reject_count',0)+1
                self.stats['pathway_local_macro_endpoint_fast_reject_count']=self.stats.get('pathway_local_macro_endpoint_fast_reject_count',0)+1
                return False
            thick=max(f.get('thicknesses',{}).values(),default=0.0)
            marker=self.r._termination_dot_radius(thick)+.5*self.r.termination_dot_hollow_stroke
            # Flat corridor caps do not extend toward a parcel boundary at an
            # endpoint.  Reserve the full eventual visible terminal dot.
            extra=marker
            if (not self._local_component_territory_clear(geom,max(marker,.5*thick)) or
                    not self._local_fill_parcel_clear(f,geom,extra) or
                    not self._local_fill_parcel_clear(f,Point(b).buffer(marker,quad_segs=16))):
                return False
        # V39 hard proposal grammar: the candidate segment itself must be exactly horizontal,
        # vertical or 45-degree diagonal.  Nearest-octant quantization is diagnostic only and
        # can no longer legalize an arbitrary segment.  Adjacent headings are 0/+/-45 only.
        nd_exact=exact_dir8_index(b[0]-a[0],b[1]-a[1])
        if nd_exact is None:
            return False
        if len(f.get('path',()))>=2:
            pa,pb=f['path'][-2],f['path'][-1]
            prev=exact_dir8_index(pb[0]-pa[0],pb[1]-pa[1])
            if prev is None or (nd_exact-prev)%8 not in (0,1,7):
                return False
        if self._outside_limit(b):
            return False
        if not allow_outside and not (0<=b[0]<=self.W and 0<=b[1]<=self.H):
            return False
        half=self._front_half_width(f)
        # The start-disk subtraction is needed only when comparing against owned history or
        # an explicit just-proposed predecessor.  Most primary candidates see only their own
        # immediately preceding segment (which is exempt below), so defer the GEOS buffer/
        # difference until a comparison actually requires the trimmed corridor.
        probe=None
        def trimmed_probe():
            nonlocal probe
            if probe is None:
                start_disk=Point(a).buffer(half+1.5*self.U,quad_segs=6)
                probe=geom.difference(start_disk)
            return probe
        static_reach=max(self.r.pathway_main_chip_keepout,self.r.component_pathway_clearance)
        for gi,g in self.static_index.query(expand_bounds(geom.bounds,static_reach)):
            if self._own_source_egress_exempt(f,a,b,gi):
                continue
            keepout=(self.r.pathway_main_chip_keepout if gi < len(self.chips)
                     else self.r.component_pathway_clearance)
            if geom.intersects(g.geom) or geom.distance(g.geom)<keepout:
                if self._capture_gesture_failure_cert and gi!=f.get('chip'):
                    self._last_gesture_failure_cert=('static',g)
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
            new_t=max((f['thicknesses'][i] for i in f.get('ids',())),default=2.55*self.U)
            if f.get('local_gap'):
                query_reach=max(1.1*self.U,self.r.pathway_interroute_keepout,
                                self.r.local_gap_line_edge_gap_factor*.5*(new_t+self.max_committed_path_thickness))+self.U
            else:
                query_reach=max(1.1*self.U,self.r.pathway_interroute_keepout)
            path_records=self.path_index.query(expand_bounds(geom.bounds,query_reach))
            # Item-21 regional success certificate.  Failure proofs already persist by blocker;
            # successful primary proposals previously re-scanned the same local committed-path
            # set every time an unchanged head held while unrelated fronts moved elsewhere.
            # For ordinary MAIN gestures, path collision depends only on this candidate/front
            # state and the path records returned by the exact local spatial query.  Reuse only
            # that path-clear sub-proof when the local record-id signature is unchanged.  Static,
            # source-egress, endpoint and visible-lane checks still run on every gesture call.
            reuse_path_clear=False; path_clear_key=None; path_signature=None; path_clear_cache=None
            if not extra_segments and not f.get('local_gap'):
                prev=(f['path'][-2] if len(f.get('path',()))>=2 else None)
                proof_head=(prev,a,int(f.get('dir',-1)),f.get('branch_stage'),int(f.get('local_gestures',0)),f.get('parent'),
                            bool(f.get('recovery_fragment_child')),f.get('fan_group'),tuple(f.get('ids',())))
                if f.get('_primary_path_clear_proof_head')!=proof_head:
                    f['_primary_path_clear_proof_head']=proof_head; f['_primary_path_clear_proof_cache']={}
                path_clear_cache=f.setdefault('_primary_path_clear_proof_cache',{})
                path_clear_key=(a,b,bool(allow_outside))
                path_signature=(int(getattr(self,'_path_index_generation',0)),
                                frozenset((rec.get('_path_index_oid') if rec.get('_path_index_oid') is not None else id(rec)) for rec in path_records))
                reuse_path_clear=(path_clear_cache.get(path_clear_key)==path_signature)
                if reuse_path_clear:
                    self.stats['pathway_primary_path_clear_proof_hit_count']=self.stats.get('pathway_primary_path_clear_proof_hit_count',0)+1
            if not reuse_path_clear:
                for rec in path_records:
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
                    if nd_exact==f['dir'] and self._same_fan_rebase_compatible(f,rec['front'],rec):
                        continue
                    candidate_probe=trimmed_probe() if own_history else geom
                    gap=self._interroute_gap_for_fronts(f,other_thickness=rec.get('max_thickness'),
                        other_local=rec.get('local_gap',False),other_cluster_id=rec.get('local_fill_cluster_id'))
                    # Exact negative broad phase: the path-index query uses a conservative reach based
                    # on the thickest committed LOCAL lane.  Most returned records are thinner.
                    # If the two exact corridor AABBs cannot come within this record's actual required
                    # gap, the geometries cannot intersect or violate clearance, so GEOS is unnecessary.
                    rec_oid=rec.get('_path_index_oid')
                    other_bounds=self.path_index.bounds.get(rec_oid) if rec_oid is not None else None
                    probe_bounds=(candidate_probe.bounds if own_history else gb)
                    if other_bounds is not None and not bounds_within_gap(probe_bounds,other_bounds,gap):
                        continue
                    if candidate_probe.intersects(other) or candidate_probe.distance(other)<gap:
                        if self._capture_gesture_failure_cert:
                            self._last_gesture_failure_cert=('path',rec)
                        return False
                if path_clear_cache is not None:
                    path_clear_cache[path_clear_key]=path_signature
            if extra_segments:
                candidate_probe=trimmed_probe()
                for other in extra_segments:
                    if candidate_probe.intersects(other) or candidate_probe.distance(other)<self.r.pathway_interroute_keepout:
                        if self._capture_gesture_failure_cert:
                            self._last_gesture_failure_cert=('extra',None)
                        return False
        if f.get('local_gap'):
            capacity_heads=getattr(self,'_local_capacity_head_index',None)
            if capacity_heads is not None:
                for old in capacity_heads.query(geom.bounds):
                    if old.get('released') or old['front']==f['id'] or old['front'] in self._ancestor_front_ids(f):
                        continue
                    if geom.intersects(old['geom']):
                        return False
        if not local_grammar_prechecked and not self._local_visible_candidate_ok(f,b):
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
        half=self._front_half_width(f)
        # Canvas/chip capacity is immutable for one front geometry.  Blocked/recovery fronts can
        # rescore the same endpoints across many transactional rounds; only congestion changes.
        # Cache the exact pre-congestion radius, then apply the live congestion term below on
        # every call.  Raw float coordinates are the key, so no quantization changes ranking.
        static_cache=f.setdefault('_point_static_free_cache',{})
        static_key=(p,max_radius,half)
        free=static_cache.get(static_key)
        if free is None:
            free=min(max_radius,x,y,self.W-x,self.H-y)
            # Only chips close enough to reduce ``free`` can matter.  Query the existing static
            # spatial hash instead of scanning every chip.  This is exact with respect to the old
            # ranking result: a chip farther than max_radius + keepout + half-width can never lower
            # the current free-radius bound.
            reach=max_radius+self.r.pathway_main_chip_keepout+half
            for gi,g in self.chip_capacity_index.query((x-reach,y-reach,x+reach,y+reach)):
                if gi==f.get('chip'):
                    continue
                free=min(free,max(0.0,point_bounds_distance(p,g.bounds)-self.r.pathway_main_chip_keepout-half))
                if free<=0.0:
                    break
            static_cache[static_key]=free
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
        # V45 performance: every proposal variant for one front in a transactional round
        # observes the same immutable board snapshot.  The expensive deterministic score
        # terms are therefore identical; only the seeded final score noise is intentionally
        # redrawn for each variant.  Cache only the deterministic base so RNG consumption,
        # weighted-choice behavior and same-seed determinism remain unchanged.
        rng=f['rng']; start=f['path'][-1]
        cache=f.setdefault('_proposal_score_base_cache',{})
        cache_round=int(f.get('_routing_round',-1))
        if f.get('_proposal_score_base_cache_round')!=cache_round:
            cache.clear(); f['_proposal_score_base_cache_round']=cache_round
        skey=(round(start[0],6),round(start[1],6),int(direction),int(modules),
              round(end[0],6),round(end[1],6))
        base=cache.get(skey)
        if base is None:
            scan=6*self.module
            nearby=[g for _gi,g in self.static_index.query((end[0]-scan,end[1]-scan,end[0]+scan,end[1]+scan))]
            static_clear=min((point_bounds_distance(end,self._indexed_static_bounds(g)) for g in nearby),default=scan)
            free_score=min(static_clear,scan)/self.module
            cell=self._coverage_cell12(end)
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
                # V38: a local target is a region-level attraction, not a rail.  V37 weighted
                # target progress so strongly that a long open room overwhelmingly selected the
                # same heading until termination.  Main routes retain their old target behavior;
                # local fillers trade some beeline progress for deliberate exploration.
                target_weight=1.4 if f.get('local_gap') else 2.8
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
                before=self._nearest_foreign_head_distance(start,f['chip'])
                after=self._nearest_foreign_head_distance(end,f['chip'])
                if before is not None and after is not None:
                    score+=1.7*(before-after)/max(self.module,1e-9)
            turn=((direction-f['dir'])%8) in (1,7)
            if f.get('reroute_mode_rounds',0)>0:
                if direction==f.get('reroute_avoid_dir'):
                    score-=4.0
                elif turn:
                    score+=2.4
            if f.get('local_gap'):
                # V38 local turn appetite.  Open space should invite articulation instead of
                # producing start-to-end rulers.  Each local front has a seeded straight-run
                # allowance (normally 1-3 gestures).  Once due, a legal +/-45 turn receives a
                # strong but still soft preference; if both turns are blocked, straight remains
                # legal and the exact geometry rules win.  The two-gesture cooldown after a turn
                # prevents this from degenerating into rapid zig-zagging.
                due=max(1,int(f.get('local_gap_turn_due_straights',2)))
                run=int(f.get('straight_since_turn',0))
                turn_count=int(f.get('local_gap_turn_count',0))
                if turn:
                    score+=1.55
                    if run>=due:
                        score+=5.8+.85*min(3,run-due)
                    if turn_count==0 and f.get('gestures',0)>=1:
                        score+=1.8
                else:
                    score+=.15
                    if run>=due:
                        score-=3.9+.65*min(3,run-due)
                    if turn_count==0 and f.get('gestures',0)>=2:
                        score-=1.25
            elif not turn:
                # Ordinary MAIN does not receive a synthetic "time to bend" reward.  A bend
                # still wins naturally when target progress, open-space capacity, connection
                # geometry or seeded proposal noise makes it the better local continuation.
                # Keep only mild directional inertia so open straight corridors remain visually
                # plausible instead of every route articulating on a fixed cadence.
                score+=.30
            score-=.16*abs(modules-self.profile['preferred_run_modules'])
            base=score
            cache[skey]=base
        return base+rng.uniform(-.55,.55)

    def _propose(self,f,_capture_pool=None):
        start=f['path'][-1]
        # V47 computational-locality optimization: corridor geometry is a pure function of this
        # front's local centerline tail and immutable lane width. Keep exactly one head-state
        # cache across blocked rounds. Movement/rollback changes (previous,start) and replaces
        # the dict, so unrelated distant board activity cannot force this geometry to rebuild.
        # This preserves every proposal/RNG/collision decision; only repeated Polygon/union
        # construction for an unchanged head is removed.
        prev=(f['path'][-2] if len(f.get('path',()))>=2 else None)
        head_key=(prev,start)
        if f.get('_proposal_corridor_cache_head')!=head_key:
            f['_proposal_corridor_cache_head']=head_key
            f['_proposal_corridor_cache']={}
        gcache=f.setdefault('_proposal_corridor_cache',{})
        failure_certs=None
        if self.failure_certificate_enabled:
            cert_head=(head_key,f.get('branch_stage'),int(f.get('local_gestures',0)),f.get('parent'),
                       bool(f.get('recovery_fragment_child')),f.get('fan_group'),bool(f.get('local_gap')),tuple(f.get('ids',())))
            if f.get('_proposal_failure_cert_head')!=cert_head:
                f['_proposal_failure_cert_head']=cert_head
                f['_proposal_failure_cert_cache']={}
            failure_certs=f.setdefault('_proposal_failure_cert_cache',{})
        # Intent biases the route; it does not forbid a useful outcome discovered naturally.
        # After two meaningful gestures any front may continue through the frame instead of
        # being forced to terminate simply because it was initially labelled explore/connect.
        base_allow_outside=(f['intent']=='exit' or f['gestures']>=2 or
                            self._forward_frame_distance(start,f['dir'])<=2.5*self.module)
        allow_outside=(base_allow_outside and
                       (not f.get('local_gap') or f.get('local_gap_exit_allowed',False)))
        if _capture_pool is not None:
            _capture_pool.clear()
            _capture_pool['state']={}
            _capture_pool['templates']={}
        def collect(directions,module_counts=None):
            found=[]
            for direction in directions:
                counts=self._module_counts(f) if module_counts is None else list(module_counts)
                for modules in counts:
                    end=point_along_dir(start,direction,modules*self.module)
                    gkey=(int(direction),int(modules),round(end[0],6),round(end[1],6))
                    if self._candidate_loop_risk(f,direction,end):
                        self.stats['pathway_loop_candidate_reject_count']+=1
                        if _capture_pool is not None:
                            _capture_pool['state'][gkey]='loop'
                        continue
                    cache=f.setdefault('_proposal_legality_cache',{})
                    cache_round=int(f.get('_routing_round',-1))
                    if f.get('_proposal_legality_cache_round')!=cache_round:
                        cache.clear(); f['_proposal_legality_cache_round']=cache_round
                    lkey=(round(start[0],6),round(start[1],6),direction,int(modules),bool(allow_outside))
                    clear=cache.get(lkey)
                    geom=None
                    if clear is None:
                        cert=(failure_certs.get(lkey) if failure_certs is not None else None)
                        if cert is not None:
                            kind,obj=cert
                            if (kind=='static' or (kind=='path' and not obj.get('_retired')) or
                                    (kind=='grammar' and obj==self._local_visible_state_signature(f))):
                                clear=False
                                self.stats['pathway_proposal_failure_certificate_hit_count']=self.stats.get('pathway_proposal_failure_certificate_hit_count',0)+1
                                if kind=='grammar':
                                    self.stats['pathway_local_visible_failure_certificate_hit_count']=self.stats.get('pathway_local_visible_failure_certificate_hit_count',0)+1
                            else:
                                failure_certs.pop(lkey,None); cert=None
                        if cert is None:
                            if not self._local_visible_candidate_ok(f,end):
                                # Preserve the historical deterministic gesture-check budget/count
                                # even though the expensive corridor/collision work is skipped.
                                self._consume_gesture_check()
                                clear=False
                                self.stats['pathway_local_visible_preflight_reject_count']=self.stats.get('pathway_local_visible_preflight_reject_count',0)+1
                                if failure_certs is not None:
                                    failure_certs[lkey]=('grammar',self._local_visible_state_signature(f))
                                    self.stats['pathway_local_visible_failure_certificate_store_count']=self.stats.get('pathway_local_visible_failure_certificate_store_count',0)+1
                            else:
                                geom=gcache.get(gkey)
                                if geom is None:
                                    geom=self._corridor_geom(f,start,end)
                                    gcache[gkey]=geom
                                if failure_certs is None:
                                    clear=self._gesture_clear(f,start,end,geom,allow_outside=allow_outside,local_grammar_prechecked=True)
                                else:
                                    self._capture_gesture_failure_cert=True
                                    try:
                                        clear=self._gesture_clear(f,start,end,geom,allow_outside=allow_outside,local_grammar_prechecked=True)
                                    finally:
                                        self._capture_gesture_failure_cert=False
                                    if not clear and self._last_gesture_failure_cert is not None:
                                        failure_certs[lkey]=self._last_gesture_failure_cert
                                        self.stats['pathway_proposal_failure_certificate_store_count']=self.stats.get('pathway_proposal_failure_certificate_store_count',0)+1
                        cache[lkey]=bool(clear)
                    if clear and geom is None:
                        geom=gcache.get(gkey)
                        if geom is None:
                            geom=self._corridor_geom(f,start,end)
                            gcache[gkey]=geom
                    if not clear:
                        if _capture_pool is not None:
                            _capture_pool['state'][gkey]='blocked'
                        continue
                    score=self._score_candidate(f,direction,modules,end)
                    candidate=dict(front=f['id'],start=start,end=end,dir=direction,
                                   modules=modules,geom=geom,score=score,
                                   reroute_short_step=(modules==1 and f.get('reroute_mode_rounds',0)>0 and f['gestures']>0),
                                   structural_short_rebase=(modules==1 and f.get('branch_stage')==0 and
                                                            (f.get('launch_fan_short_rebase',False) or
                                                             f.get('rescue_branch_short_rebase',False) or
                                                             f.get('local_gap',False))))
                    found.append(candidate)
                    if _capture_pool is not None:
                        _capture_pool['state'][gkey]='legal'
                        template=dict(candidate); template.pop('score',None)
                        _capture_pool['templates'][gkey]=template
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

    def _replay_propose_from_pool(self,f,pool):
        """Replay one stochastic `_propose` draw from first-draw legality membership.

        The board/head snapshot is immutable inside one `_proposal_variants` call.  Module-list
        shuffles are still executed so RNG state and candidate score-noise association remain
        exactly as in the historical repeated `_propose` call; only loop-risk, corridor construction
        and legality/cache traversal are skipped because first-draw membership already proves them.
        """
        start=f['path'][-1]
        state=pool.get('state',{}); templates=pool.get('templates',{})
        def collect(directions,module_counts=None):
            found=[]
            for direction in directions:
                counts=self._module_counts(f) if module_counts is None else list(module_counts)
                for modules in counts:
                    end=point_along_dir(start,direction,modules*self.module)
                    gkey=(int(direction),int(modules),round(end[0],6),round(end[1],6))
                    verdict=state.get(gkey)
                    if verdict=='loop':
                        self.stats['pathway_loop_candidate_reject_count']+=1
                        continue
                    if verdict!='legal':
                        continue
                    template=templates.get(gkey)
                    if template is None:
                        raise RuntimeError('proposal replay pool missing legal template')
                    c=dict(template)
                    c['score']=self._score_candidate(f,direction,modules,end)
                    found.append(c)
            return found
        candidates=collect(self._direction_candidates(f))
        if not candidates and self._source_egress_pending(f):
            candidates=collect([f['dir']],module_counts=(1,))
        if not candidates and f.get('branch_stage')==1:
            candidates=collect([f['dir']],module_counts=(2,))
        if not candidates and f.get('branch_stage')==0 and f.get('reroute_mode_rounds'):
            candidates=collect([f['dir']],module_counts=(1,))
            for c in candidates:
                c['reroute_short_rebase']=True
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

    def _proposal_reuse_front_state(self,f):
        # Exact proposal-membership dependencies that may change without moving the head.
        # Score/target/head-neighbour state is intentionally absent: replay recomputes scores.
        return (
            tuple(f.get('path',())), int(f.get('dir',-1)), int(f.get('gestures',0)),
            int(f.get('local_gestures',0)), float(f.get('travel',0.0)), int(f.get('failures',0)),
            f.get('branch_stage'), f.get('branch_turn'), int(f.get('turn_cooldown',0)),
            int(f.get('straight_since_turn',0)), f.get('last_turn_sign'), tuple(f.get('turn_history',())),
            int(f.get('initial_dir',f.get('dir',-1))), f.get('intent'), f.get('origin'),
            float(f.get('max_origin_distance',0.0)), int(f.get('reroute_mode_rounds',0)),
            f.get('reroute_avoid_dir'), f.get('forced_straight_modules'), f.get('forced_turn_modules'),
            f.get('parent'), bool(f.get('recovery_fragment_child')), f.get('fan_group'),
            bool(f.get('fan_pending')), bool(f.get('fragment_pending')), bool(f.get('local_gap')),
            tuple(f.get('ids',())), tuple(sorted((tid,tuple(f.get('prefixes',{}).get(tid,())),
                                                   f.get('offsets',{}).get(tid)) for tid in f.get('ids',()))),
            f.get('round_connection_peer'), bool(f.get('reroute_pending')), bool(f.get('quality_repair_pending')),
        )

    def _main_dynamic_leg_dependency_signature(self,bounds):
        # Exact dynamic dependencies of ordinary MAIN gesture legality. Static component/chip
        # geometry is immutable for the routing phase; committed paths and source-egress state
        # are the only board-side inputs that can change while a front head is held.
        reach=max(1.1*self.U,self.r.pathway_interroute_keepout)
        records=self.path_index.query(expand_bounds(bounds,reach))
        path_sig=(int(getattr(self,'_path_index_generation',0)),
                  frozenset((rec.get('_path_index_oid') if rec.get('_path_index_oid') is not None else id(rec))
                            for rec in records))
        ereach=.35*self.r.pathway_interroute_keepout
        egress=self.source_egress_index.query(expand_bounds(bounds,ereach))
        egress_sig=(frozenset((int(rec.get('tid',-1)),rec.get('owner'),bool(rec.get('active',True))) for rec in egress),
                    frozenset(getattr(self,'_protected_family_owners',set())))
        return path_sig,egress_sig

    def _proposal_pool_dependency_signature(self,f,pool):
        bounds=pool.get('_reuse_bounds')
        if bounds is None:
            return None
        return self._main_dynamic_leg_dependency_signature(bounds)

    def _finalize_proposal_reuse_pool(self,f,pool):
        if not pool or not pool.get('state'):
            return
        gcache=f.get('_proposal_corridor_cache',{})
        bs=[]
        for gkey in pool.get('state',{}):
            geom=gcache.get(gkey)
            if geom is not None and not geom.is_empty:
                bs.append(geom.bounds)
        if not bs:
            return
        b=bs[0]
        for ob in bs[1:]:
            b=bounds_union(b,ob)
        pool['_reuse_bounds']=b
        pool['_reuse_front_state']=self._proposal_reuse_front_state(f)
        pool['_reuse_dependency_signature']=self._proposal_pool_dependency_signature(f,pool)
        f['_proposal_cross_round_pool']=pool

    def _valid_proposal_reuse_pool(self,f):
        pool=f.get('_proposal_cross_round_pool')
        if not pool or pool.get('_reuse_front_state')!=self._proposal_reuse_front_state(f):
            return None
        if pool.get('_reuse_dependency_signature')!=self._proposal_pool_dependency_signature(f,pool):
            return None
        return pool

    def _proposal_variants(self,f,count=2):
        out=[]; seen=set()
        draws=max(1,count)
        pool={} if draws>1 else None
        reuse_pool=(self._valid_proposal_reuse_pool(f) if pool is not None else None)
        for draw in range(draws):
            if draw==0:
                if reuse_pool is not None:
                    pool=reuse_pool
                    p=self._replay_propose_from_pool(f,pool)
                    self.stats['pathway_cross_round_proposal_pool_hit_count']=self.stats.get('pathway_cross_round_proposal_pool_hit_count',0)+1
                else:
                    p=(self._propose(f,_capture_pool=pool) if pool is not None else self._propose(f))
                    if pool is not None:
                        self._finalize_proposal_reuse_pool(f,pool)
                        self.stats['pathway_cross_round_proposal_pool_miss_count']=self.stats.get('pathway_cross_round_proposal_pool_miss_count',0)+1
            else:
                p=self._replay_propose_from_pool(f,pool)
                self.stats['pathway_proposal_replay_draw_count']=self.stats.get('pathway_proposal_replay_draw_count',0)+1
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
        # V39 structural rendered-centreline grammar gate.  Every committed segment must itself
        # be exactly octilinear; only then may its heading continue straight or turn by +/-45.
        # This covers ordinary proposals, repair paths, connections and residual mop-up alike.
        nd=exact_dir8_index(b[0]-a[0],b[1]-a[1])
        if nd is None:
            raise RuntimeError('non-octilinear rendered pathway segment')
        path=f.get('path',())
        if len(path)>=3 and math.hypot(path[-1][0]-b[0],path[-1][1]-b[1])<=1e-5 and math.hypot(path[-2][0]-a[0],path[-2][1]-a[1])<=1e-5:
            pd=exact_dir8_index(path[-2][0]-path[-3][0],path[-2][1]-path[-3][1])
            if pd is None or (nd-pd)%8 not in (0,1,7):
                raise RuntimeError(f'illegal rendered pathway turn: {pd}->{nd}')
        # Central audit classification: anything below the two-module normal grammar is an
        # explicit structural/recovery/terminal exception, never allowed to contaminate the
        # reported normal-segment minimum.  Callers still decide whether such a segment is legal;
        # this function only keeps the diagnostic categories truthful.
        if normal and L < 2.0*self.module-1e-9:
            normal=False
            self.stats['pathway_minimum_segment_exception_count']+=1
        rec=dict(geom=geom,front=f['id'],root=(f['chip'],f['side'],f['side_index']),chip=f['chip'],start=a,end=b,
                 round_index=int(f.get('_routing_round',-1)),local_gap=bool(f.get('local_gap')),
                 local_fill_cluster_id=f.get('local_fill_cluster_id'),
                 max_thickness=max((f['thicknesses'][i] for i in f.get('ids',())),default=2.55*self.U))
        self.path_segments.append(rec)
        self.path_segments_by_front.setdefault(f['id'],[]).append(rec)
        rec['_path_index_oid']=self.path_index.insert(rec,geom.bounds); self._grid_add_segment(a,b)
        self._lane_cache_version+=1
        self.max_committed_path_thickness=max(self.max_committed_path_thickness,float(rec.get('max_thickness',0.0)))
        if f.get('local_gap') and not f.get('_defer_local_service_mark'):
            self._mark_local_gap_segment_coverage(a,b,f)
        if normal:
            f['normal_segment_lengths'].append(L)
        self._coverage_add_segment(a,b,1)

    def _segment_coverage_cells(self,a,b):
        L=math.hypot(b[0]-a[0],b[1]-a[1]); steps=max(1,int(math.ceil(L/(.45*self.module))))
        out=set()
        for k in range(steps+1):
            t=k/steps; x=a[0]+(b[0]-a[0])*t; y=a[1]+(b[1]-a[1])*t
            if 0<=x<=self.W and 0<=y<=self.H:
                out.add(self._coverage_cell12((x,y)))
        return out

    def _coverage_add_segment(self,a,b,delta=1):
        for cell in self._segment_coverage_cells(a,b):
            n=int(self.coverage_cell_counts.get(cell,0))+int(delta)
            if n<=0:
                self.coverage_cell_counts.pop(cell,None); self.coverage_cells.discard(cell)
            else:
                self.coverage_cell_counts[cell]=n; self.coverage_cells.add(cell)

    def _retire_path_record_incremental(self,rec):
        """Remove one committed main segment from live spatial/coverage state exactly.

        The record stays as a tombstone in ``path_segments`` until a cheap compaction boundary,
        avoiding O(board_history) list deletion during rollback.  All query-visible state is
        removed immediately, so subsequent proposals see exactly the same board they would see
        after an authoritative rebuild.
        """
        if rec.get('_retired'):
            return False
        rec['_retired']=True
        oid=rec.pop('_path_index_oid',None)
        if oid is not None:
            self.path_index.remove(oid)
        self._grid_add_segment(rec['start'],rec['end'],-1)
        self._coverage_add_segment(rec['start'],rec['end'],-1)
        self._lane_cache_version+=1
        self.stats.setdefault('pathway_incremental_rollback_segment_remove_count',0)
        self.stats['pathway_incremental_rollback_segment_remove_count']+=1
        return True

    def _compact_retired_path_records(self):
        if not any(rec.get('_retired') for rec in self.path_segments):
            return 0
        before=len(self.path_segments)
        self.path_segments=[rec for rec in self.path_segments if not rec.get('_retired')]
        removed=before-len(self.path_segments)
        self.stats.setdefault('pathway_incremental_rollback_compacted_segment_count',0)
        self.stats['pathway_incremental_rollback_compacted_segment_count']+=removed
        return removed

    def _rebuild_path_index_and_coverage(self,rebuild_local_coverage=True):
        self._lane_cache_version+=1
        # Traceback marks only the handful of owned tail records as retired.  Compact once for
        # the whole rollback transaction and rebuild the owner map authoritatively here.
        if any(rec.get('_retired') for rec in self.path_segments):
            self.path_segments=[rec for rec in self.path_segments if not rec.get('_retired')]
        self.path_segments_by_front={}
        for rec in self.path_segments:
            self.path_segments_by_front.setdefault(rec['front'],[]).append(rec)
        self.path_index=SpatialHash(max(80*self.U,3*self.module))
        self._path_index_generation=getattr(self,'_path_index_generation',0)+1
        self.max_committed_path_thickness=0.0
        self.coverage_cells=set(); self.coverage_cell_counts={}
        if rebuild_local_coverage:
            self.local_gap_coverage_cells=set()
            self.local_gap_coverage_touched_cells=set()
            self.local_gap_coverage_mask_by_cell={}
            self.local_gap_served_subcell_count=0
            # Rebuild the incremental targeting complement from the same authoritative open
            # field before replaying committed local segments.  A rollback/rebuild can make a
            # previously touched cell untouched again; leaving it absent here would silently
            # starve later targeting even though the 16-subcell audit had been reset.
            self.local_gap_untouched_cells=set(self.local_gap_route_cells)
            self.local_gap_untouched_by_region={r['id']:set(r['cells']) for r in self.local_gap_regions}
            self.local_gap_region_touch_version={r['id']:0 for r in self.local_gap_regions}
            self._reset_local_gap_chunk_state()
        # Rebuild congestion in the same authoritative segment pass as the spatial/coverage
        # indexes.  The old helper walked the entire board once, then this loop walked it again.
        self.congestion_grid=[[0 for _ in range(self.grid_nx)] for _ in range(self.grid_ny)]
        self._congestion_cache.clear()
        for rec in self.path_segments:
            rec['_path_index_oid']=self.path_index.insert(rec,rec['geom'].bounds)
            self.max_committed_path_thickness=max(self.max_committed_path_thickness,float(rec.get('max_thickness',0.0)))
            a,b=rec['start'],rec['end']; self._grid_add_segment(a,b)
            f=self.fronts.get(rec['front'])
            if rebuild_local_coverage and f and f.get('local_gap'):
                self._mark_local_gap_segment_coverage(a,b,f)
            self._coverage_add_segment(a,b,1)

        for rec in self.frozen_main_render_records:
            rec['_path_index_oid']=self.path_index.insert(rec,rec['geom'].bounds)
            self.max_committed_path_thickness=max(self.max_committed_path_thickness,float(rec.get('max_thickness',0.0)))

    def _traceback_for_reroute(self,f,defer_rebuild=False):
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
                owned=self.path_segments_by_front.get(f['id'],[])
                if owned:
                    # The synchronous round can remove its exact owned tail from every live
                    # index incrementally.  The global history list keeps only a tombstone until
                    # the next compaction boundary, so rollback cost is proportional to removed
                    # history rather than total board history.
                    rec=owned.pop()
                    if defer_rebuild and not f.get('local_gap'):
                        self._retire_path_record_incremental(rec)
                    else:
                        rec['_retired']=True
            if not defer_rebuild:
                self._rebuild_path_index_and_coverage(rebuild_local_coverage=bool(f.get('local_gap')))
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
        # MAIN-1: when a bundled main front is repeatedly hard-stopped by a concrete active
        # foreign blocker, same-width retries are the wrong recovery representation. Preserve
        # two exact attempts, then let the existing caller switch the cohort into its narrower
        # branch/fragment recovery instead of spending the whole generic reroute budget.
        if (reason=='hard_stop' and not f.get('local_gap') and len(f.get('ids',()))>1 and
                not self._source_egress_pending(f)):
            blocker=self._find_active_blocker(f,round_index)
            if blocker is not None and blocker.get('status')=='active':
                budget=min(budget,2)
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
        olddir=f['dir']
        # V39 hard commit-time grammar.  The declared direction must agree with the actual
        # candidate coordinates, and both must be exact octilinear geometry.
        actual_dir=exact_dir8_index(p['end'][0]-p['start'][0],p['end'][1]-p['start'][1])
        if actual_dir is None or actual_dir!=(p['dir']%8):
            raise RuntimeError(f'non-octilinear or mismatched pathway segment at commit: declared={p["dir"]} actual={actual_dir}')
        delta_commit=(actual_dir-olddir)%8
        if delta_commit not in (0,1,7):
            raise RuntimeError(f'illegal pathway turn at commit: {olddir}->{actual_dir}')
        f['path'].append(p['end']); f['dir']=actual_dir
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
            if f.get('local_gap'):
                f['local_gap_turn_count']=int(f.get('local_gap_turn_count',0))+1
                # Resample the next straight-run allowance after every legal bend.  This keeps
                # cadence varied while making long entirely-straight fillers uncommon.
                f['local_gap_turn_due_straights']=1+int(f['rng'].random()*3)
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
            self._capture_source_egress_survival_prefix(f)
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
            # A journey limit is only a voluntary free-running stop.  Defer it until the existing
            # head-connection sweep has had first right of refusal.  This is ordering only: no new
            # search, radius, or legality rule is introduced.
            f['journey_limit_pending']=True

    def _apply_journey_limit(self,f):
        """Apply the historical voluntary journey-limit policy after connection arbitration."""
        f['journey_limit_pending']=False
        if f.get('status')!='active' or f.get('gestures',0)<f.get('max_gestures',0):
            return
        if getattr(self,'_in_shared_persistence',False) and self._persistence_work_debt(f):
            f['max_gestures']=max(f['max_gestures'],f['gestures']+2)
            return
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

    def _settle_pending_journey_limits(self):
        """Settle voluntary limits only after the current exact head-connection opportunity."""
        for f in sorted(self.fronts.values(),key=lambda x:x['id']):
            if not f.get('journey_limit_pending'):
                continue
            if f.get('status')!='active':
                f['journey_limit_pending']=False
                continue
            self._apply_journey_limit(f)

    def _mod_delta_ok(self,a,b):
        return (b-a)%8 in (0,1,7)

    def _near_foreign_corridor(self,f):
        point=Point(f['path'][-1]); radius=2.15*self.module+self._front_half_width(f)
        for rec in self.path_index.query(expand_bounds(point.bounds,radius)):
            if rec['front']==f['id'] or rec.get('root')==self._launch_family_key(f):
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
                lega=[pa,meet]; legb=[pb,meet]
                if not self._connection_junction_turn_ok(lega,legb):
                    continue
                seen.add(key); out.append((ta+tb,meet,lega,legb))
        mid=((pa[0]+pb[0])/2,(pa[1]+pb[1])/2)
        la=self._octile_leg(pa,mid,a['dir']); lb=self._octile_leg(pb,mid,b['dir'])
        if la is not None and lb is not None and self._connection_junction_turn_ok(la,lb):
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
            if check_geom.is_empty:
                # A very short final rendezvous leg can lie wholly inside the already-audited
                # junction envelope.  Empty Shapely geometry has NaN bounds, so do not feed it
                # to the generic spatial hash.  The junction disk has already been checked for
                # third routed corridors; still enforce finite/full-geometry static clearance.
                gb=geom.bounds
                if len(gb)!=4 or not all(math.isfinite(float(v)) for v in gb):
                    return False
                if f.get('local_gap'):
                    thick=max(f.get('thicknesses',{}).values(),default=0.0)
                    marker=self.r._termination_dot_radius(thick)+.5*self.r.termination_dot_hollow_stroke
                    extra=marker
                    if (not self._local_component_territory_clear(geom,max(marker,.5*thick)) or
                            not self._local_fill_parcel_clear(f,geom,extra)):
                        return False
                static_reach=max(self.r.pathway_main_chip_keepout,self.r.component_pathway_clearance)
                for gi,g in self.static_index.query(expand_bounds(gb,static_reach)):
                    if self._own_source_egress_exempt(f,a,b,gi):
                        continue
                    keepout=(self.r.pathway_main_chip_keepout if gi < len(self.chips)
                             else self.r.component_pathway_clearance)
                    if geom.intersects(g.geom) or geom.distance(g.geom)<keepout:
                        return False
                if not self._source_egress_clear_for_gesture(f,geom):
                    return False
            elif not self._gesture_clear(f,a,b,check_geom,allow_outside=False,extra_segments=tuple(extra)+tuple(created)):
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

    def _rebase_singleton_to_materialized_head(self,f,tid):
        """Make a one-lane front's centreline head equal its rendered physical head.

        Split children can contain a single trace while retaining a non-zero bundle offset.
        Head-to-head connection legs are planned in rendered coordinates.  Appending such a
        physical leg to the still-offset centreline would apply the offset a second time during
        materialization and can manufacture a tiny 90-degree terminal kink.  Before committing
        a connection, preserve the complete visible history as prefix and reset the terminal
        singleton to zero offset at that exact physical head.
        """
        if f is None or len(f.get('ids',()))!=1 or tid not in f.get('ids',()):
            return f
        if abs(float(f.get('offsets',{}).get(tid,0.0)))<=1e-9:
            return f
        realised=list(self._materialized_paths(f).get(tid,()))
        if not realised:
            return f
        endpoint=realised[-1]
        f['prefixes'][tid]=realised
        f['path']=[endpoint]
        f['offsets'][tid]=0.0
        f['route_history']=[]
        f['recovery_floor_segments']=0
        f['local_gestures']=0
        return f

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

    def _detachment_batch_possible(self,requests,eligible_status=('active',)):
        """Pure preflight for a multi-family lane-detachment transaction.

        Every requested peel is simulated against the original cohort state before any front,
        child id, RNG stream, recovery floor or ownership map is mutated.  This closes the V46
        A-detaches/B-fails lifecycle leak in final close-head arbitration.
        """
        simulated={}
        for f,tid in requests:
            if f.get('status') not in set(eligible_status):
                return False
            fid=f['id']
            if fid not in simulated:
                simulated[fid]=list(sorted(f.get('ids',()),key=lambda x:f['offsets'][x]))
            ids=simulated[fid]
            if tid not in ids:
                return False
            if len(ids)>1 and tid not in (ids[0],ids[-1]):
                return False
            ids.remove(tid)
        return True

    def _current_trace_lane_records(self):
        """Versioned exact-lane snapshot with unchanged-geometry reuse and immutable STRtree.

        Exact LineString/buffer objects are reused only when a lane's materialized point sequence
        and thickness are byte-for-byte Python-value identical to the prior snapshot.  The current
        snapshot itself remains global and immutable until ``_lane_cache_version`` changes.  Its
        spatial broad phase is an STRtree over the same exact buffered geometries, avoiding
        SpatialHash cell amplification for long lane AABBs.  Final GEOS intersection predicates
        are unchanged and the geometry cache is pruned to currently visible lanes every rebuild.
        """
        if self._lane_cache_built_version==self._lane_cache_version:
            return self._lane_cache_records
        old_geom_cache=getattr(self,'_lane_exact_geom_cache',{})
        next_geom_cache={}
        records=[]; geoms=[]; seen=set()
        for f in self.fronts.values():
            if f['status']=='branched': continue
            paths=self._materialized_paths(f)
            for tid,pts in paths.items():
                if tid in seen or len(pts)<2: continue
                seen.add(tid); t=f['thicknesses'][tid]
                sig=(float(t),tuple(pts))
                cached=old_geom_cache.get(tid)
                if cached is not None and cached[0]==sig:
                    rec=cached[1]
                else:
                    line=LineString(pts)
                    geom=line.buffer(t/2,cap_style='flat',join_style='mitre',quad_segs=6)
                    rec=dict(tid=tid,line=line,geom=geom,thickness=t)
                next_geom_cache[tid]=(sig,rec)
                records.append(rec); geoms.append(rec['geom'])
        self._lane_exact_geom_cache=next_geom_cache
        self._lane_cache_records=records; self._lane_cache_geoms=geoms
        self._lane_cache_tree=(STRtree(geoms) if geoms else None)
        self._lane_cache_index=None
        self._lane_cache_built_version=self._lane_cache_version
        return records

    def _trace_lane_records_near(self,bounds,gap=0.0):
        self._current_trace_lane_records()
        if self._lane_cache_tree is None:
            return ()
        q=box(*expand_bounds(bounds,gap))
        return [self._lane_cache_records[int(i)] for i in self._lane_cache_tree.query(q)]

    def _static_intersection_group_count(self,geom):
        """Exact number of static groups intersecting ``geom`` via the static spatial index."""
        hit_groups=set()
        for gi,obj in self.static_index.query(geom.bounds):
            if gi in hit_groups:
                continue
            if geom.intersects(obj.geom):
                hit_groups.add(gi)
        return len(hit_groups)

    def _nearest_foreign_static_clearances(self,geom,own_chip):
        """Exact nearest foreign-static and foreign-chip distances from immutable local indexes.

        Components are represented by their exact primitive set, so nearest distance to one
        STRtree primitive is exactly nearest distance to the component union.  Main-chip count is
        small; scanning only foreign chip groups avoids the source chip without any expanding
        whole-static search.  This function feeds diagnostics only; routing admission is unchanged.
        """
        if not self.static:
            return (0.0,0.0)
        cache=getattr(self,'_foreign_static_nearest_cache',None)
        if cache is None:
            component_geoms=[]
            for _oid,(gi,obj) in self.static_index.objects.items():
                if gi>=len(self.chips):
                    component_geoms.append(obj.geom)
            cache=(component_geoms,STRtree(component_geoms) if component_geoms else None)
            self._foreign_static_nearest_cache=cache
        component_geoms,component_tree=cache
        best_component=None
        if component_tree is not None:
            idxs=component_tree.query_nearest(geom,all_matches=False)
            if len(idxs):
                best_component=geom.distance(component_geoms[int(idxs[0])])
        best_chip=None
        for gi,g in enumerate(self.chips):
            if gi==own_chip:
                continue
            d=geom.distance(g.geom)
            if best_chip is None or d<best_chip:
                best_chip=d
        vals=[d for d in (best_component,best_chip) if d is not None]
        best=min(vals) if vals else None
        return (0.0 if best is None else best,0.0 if best_chip is None else best_chip)

    def _connection_joint_radius(self,ta_t,tb_t):
        """Visible exemption radius for a legal head-to-head junction."""
        return max(8.0*self.U,.75*(float(ta_t)+float(tb_t)))

    def _connection_junction_turn_ok(self,lega,legb):
        """Whether traversing through a head-to-head join is straight or one 45-degree turn.

        V38 checked each trace independently, so two individually legal trace heads could form
        a 90-degree L when connected.  V39 treats the junction as a real network vertex: arrive
        along A's final leg, leave along the reverse of B's final incoming leg, and require the
        resulting turn to be 0/+/-45 degrees.
        """
        if len(lega)<2 or len(legb)<2:
            return False
        a0,a1=lega[-2],lega[-1]; b0,b1=legb[-2],legb[-1]
        da=exact_dir8_index(a1[0]-a0[0],a1[1]-a0[1])
        db_in=exact_dir8_index(b1[0]-b0[0],b1[1]-b0[1])
        if da is None or db_in is None:
            return False
        db_out=(db_in+4)%8
        return (db_out-da)%8 in (0,1,7)

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
        join_bounds=bounds_union(ga.bounds,gb.bounds)
        for rec in self._trace_lane_records_near(join_bounds):
            if rec['tid'] in (ta,tb): continue
            # Exact predicate unchanged; only impossible distant lanes are excluded by bounds.
            if (self._bounds_within_gap(ga.bounds,rec['geom'].bounds,0.0) and not ga.intersection(rec['geom']).is_empty) or \
               (self._bounds_within_gap(gb.bounds,rec['geom'].bounds,0.0) and not gb.intersection(rec['geom']).is_empty):
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
        """Reject a join that would violate the visible octilinear lane grammar.

        Connection rendezvous are geometry of the rendered trace too.  V34/V37 previously
        checked these short terminal legs for compensating zigzags but not for an outright
        >45-degree change from the incoming physical lane.  That let a tiny final junction leg
        create a visible 90-degree kink even though ordinary route proposals forbid one.
        """
        paths=self._materialized_paths(f)
        base=list(paths.get(tid,()))
        if len(base)<2 or len(leg)<2:
            return False
        pts=base+list(leg[1:])
        dirs=self._turn_directions(pts)
        if any((b-a)%8 not in (0,1,7) for a,b in zip(dirs,dirs[1:])):
            return True
        return self._points_have_compensating_zigzag(pts)

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
        # Broad-phase only: no pair farther than 5 modules can satisfy the exact forced-close
        # rules below (same-chip terminal-marker arbitration is much tighter).  V43 scanned all
        # lane-head pairs every round, which became quadratic when fine zoom legitimately
        # produced hundreds of lane heads.  Preserve the exact pair logic and deterministic
        # ordering, but enumerate only spatially possible neighbours.
        max_radius=5.0*self.module
        head_index=SpatialHash(max(max_radius,80.0*self.U,1e-6))
        head_order={}
        for hi,rec in enumerate(heads):
            head_order[(rec[0]['id'],rec[1])]=hi
            px,py=rec[2]; head_index.insert(rec,(px,py,px,py))
        for i,(a,ta,pa) in enumerate(heads):
            nearby=head_index.query((pa[0]-max_radius,pa[1]-max_radius,pa[0]+max_radius,pa[1]+max_radius))
            nearby=sorted((rec for rec in nearby if head_order[(rec[0]['id'],rec[1])]>i),
                          key=lambda rec:head_order[(rec[0]['id'],rec[1])])
            for b,tb,pb in nearby:
                if not self._connection_family_compatible(a,b):
                    continue
                if (a['chip']==b['chip'] and
                        (self._source_egress_pending(a) or self._source_egress_pending(b))):
                    continue
                d=math.hypot(pb[0]-pa[0],pb[1]-pa[1])
                radius=base_radius
                ux=(pb[0]-pa[0])/max(d,1e-9); uy=(pb[1]-pa[1])/max(d,1e-9)
                va=dir_vec(a['dir']); vb=dir_vec(b['dir'])
                facing=(va[0]*ux+va[1]*uy>.18 and vb[0]*(-ux)+vb[1]*(-uy)>.18)
                if (facing and
                        (a.get('travel',0.0)<4.0*self.module or b.get('travel',0.0)<4.0*self.module or
                         self._refresh_lifecycle(a) in ('LAUNCHING','RECOVERING') or
                         self._refresh_lifecycle(b) in ('LAUNCHING','RECOVERING'))):
                    radius=max_radius
                if d<=radius:
                    cross_rank=0 if a['chip']!=b['chip'] else 1
                    pairs.append((cross_rank,d,a['id'],ta,b['id'],tb,a,b,pa,pb))
        pairs.sort(key=lambda x:(x[0],x[1],x[2],x[3],x[4],x[5]))
        used=set()
        for _,_,_,ta,_,tb,a,b,pa,pb in pairs:
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
            # V47 transactional close-head fix: prove *both* cohort mutations on the untouched
            # families before either lane is peeled. A failed opportunity is bit-for-bit inert.
            if not self._detachment_batch_possible(((a,ta),(b,tb)),eligible_status=eligible_status):
                continue
            if include_terminated and a['status']=='terminated': a['status']='active'
            if include_terminated and b['status']=='terminated': b['status']='active'
            ra=self._detach_trace_as_singleton(a,ta); rb=self._detach_trace_as_singleton(b,tb)
            if ra is None or rb is None:
                raise RuntimeError('MAIN detachment preflight/commit contract violated')
            if ra is not a and a.get('ids') and prior_a[0]=='terminated': a['status']='terminated'; a['termination_reason']=prior_a[1]
            if rb is not b and b.get('ids') and prior_b[0]=='terminated': b['status']='terminated'; b['termination_reason']=prior_b[1]
            ra=self._rebase_singleton_to_materialized_head(ra,ta)
            rb=self._rebase_singleton_to_materialized_head(rb,tb)
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
            if ra['chip']!=rb['chip']:
                self.cross_chip_connected_trace_ids.update((ta,tb))
                self.stats['pathway_cross_chip_connection_count']+=1
            else:
                self.stats.setdefault('pathway_same_chip_head_connection_count',0)
                self.stats['pathway_same_chip_head_connection_count']+=1
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
        max_pair_distance=10.0*self.module
        singleton_index=SpatialHash(max(max_pair_distance,80.0*self.U,1e-6))
        singleton_order={f['id']:i for i,f in enumerate(singles)}
        for f in singles:
            px,py=f['path'][-1]; singleton_index.insert(f,(px,py,px,py))
        for i,a in enumerate(singles):
            pa=a['path'][-1]
            nearby=singleton_index.query((pa[0]-max_pair_distance,pa[1]-max_pair_distance,
                                          pa[0]+max_pair_distance,pa[1]+max_pair_distance))
            nearby=sorted((b for b in nearby if singleton_order[b['id']]>i),key=lambda b:singleton_order[b['id']])
            for b in nearby:
                if a.get('local_gap') or b.get('local_gap'):
                    continue
                if not self._connection_family_compatible(a,b):
                    continue
                ta,tb=a['ids'][0],b['ids'][0]
                if ta in self.connected_trace_ids or tb in self.connected_trace_ids:
                    continue
                pb=b['path'][-1]
                d=math.hypot(pb[0]-pa[0],pb[1]-pa[1])
                if d>max_pair_distance:
                    continue
                desire=(a['intent']=='connect')+(b['intent']=='connect')
                paired=(a.get('round_connection_peer')==b['id'] and b.get('round_connection_peer')==a['id'])
                forced_close=d<=2.35*self.module
                cross_chip=(a['chip']!=b['chip'])
                chance=1.0 if (forced_close or cross_chip) else ((.90 if paired else (.24+.28*desire))*self.profile['connection_appetite'])
                priority=(d/self.module-(4.0 if cross_chip else 0.0)-(3.2 if forced_close else 0.0)-
                          (2.4 if paired else 0.0)-a['rng'].random()*.20-b['rng'].random()*.20)
                pairs.append((priority,chance,forced_close,cross_chip,a,b))
        pairs.sort(key=lambda x:(x[0],x[4]['id'],x[5]['id']))
        used=set()
        for _,chance,forced_close,cross_chip,a,b in pairs:
            if a['id'] in used or b['id'] in used or a['status']!='active' or b['status']!='active':
                continue
            ta,tb=a['ids'][0],b['ids'][0]
            if ta in self.connected_trace_ids or tb in self.connected_trace_ids:
                continue
            if not forced_close and not cross_chip and a['rng'].random()>=min(.995,chance):
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
            a=self._rebase_singleton_to_materialized_head(a,ta)
            b=self._rebase_singleton_to_materialized_head(b,tb)
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
            if a['chip']!=b['chip']:
                self.cross_chip_connected_trace_ids.update((ta,tb))
                self.stats['pathway_cross_chip_connection_count']+=1
            else:
                self.stats.setdefault('pathway_same_chip_head_connection_count',0)
                self.stats['pathway_same_chip_head_connection_count']+=1
            self.stats['pathway_cross_chip_connected_trace_count']=len(self.cross_chip_connected_trace_ids)
            if forced_close:
                self.stats['pathway_forced_close_head_connection_count']+=1
            used.update((a['id'],b['id']))
        # Journey-limit termination is voluntary free-running completion.  A legal head join—
        # especially a foreign-chip join—wins first using the exact existing connection machinery.
        self._settle_pending_journey_limits()

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
        # Recovery fragmentation is a representation change, not a way to distribute unresolved
        # launch-survival debt across singleton children.  If any MAIN lane is still below the
        # four-module floor, keep the family intact so ordinary branch/reroute construction can
        # solve that debt transactionally.  The old path could fragment a young boxed bus, after
        # which the newborn singleton siblings became one another's blockers and reached the
        # horizon as ``under_survival_floor + between_siblings/fragment_embedded`` residue.
        if (not f.get('local_gap') and f.get('chip',len(self.chips))<len(self.chips) and
                self._minimum_materialized_lane_length(f) <
                self.main_launch_maturity_modules*self.module-1e-7):
            self.stats.setdefault('pathway_underfloor_fragment_reject_count',0)
            self.stats['pathway_underfloor_fragment_reject_count']+=1
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
            self.fragment_members.setdefault(fragment_group,set()).add(child['id'])
            child['fragment_origin']=endpoint
            child['fragment_min_local_gestures']=2
            child['recovery_fragment_child']=True
            if f.get('local_gap'):
                child['local_gap']=True; child['local_gap_special']=bool(f.get('local_gap_special'))
                child['local_gap_branch_boost']=f.get('local_gap_branch_boost',4.0)
                child['local_gap_exit_allowed']=f.get('local_gap_exit_allowed',False)
                child['local_gap_turn_count']=int(f.get('local_gap_turn_count',0))
                child['local_gap_turn_due_straights']=int(f.get('local_gap_turn_due_straights',2))
            children.append(child)
        # Transactional recovery fragmentation: a dead-end parent may split only when its
        # tiny newborn cohort has a *short structural future*, not merely one lucky first step.
        # V47's shared persistence clock exposed the old one-step loophole: 2-3 singleton
        # children could be born into a pocket, take/offer one legal gesture, then mutually box
        # each other forever.  For cohorts up to four lanes, enumerate at most two deterministic
        # two-gesture futures per child and prove that one complete combination is mutually
        # clearance-compatible before mutating the parent topology.  This is a fixed tiny local
        # transaction (<= 2^4 combinations), never a board search.
        if len(children)<=4:
            import itertools

            def advance_probe(front,proposal):
                tf=dict(front)
                tf['path']=list(front.get('path',()))+[proposal['end']]
                olddir=front['dir']; nd=proposal['dir']
                tf['dir']=nd
                tf['gestures']=front.get('gestures',0)+1
                tf['local_gestures']=front.get('local_gestures',0)+1
                tf['travel']=front.get('travel',0.0)+math.hypot(
                    proposal['end'][0]-proposal['start'][0],proposal['end'][1]-proposal['start'][1])
                delta=(nd-olddir)%8; sign=1 if delta==1 else -1 if delta==7 else 0
                tf['last_turn_sign']=sign if sign else front.get('last_turn_sign',0)
                tf['straight_since_turn']=0 if sign else front.get('straight_since_turn',0)+1
                tf['turn_history']=(list(front.get('turn_history',[]))+[sign])[-7:]
                tf['reroute_mode_rounds']=max(0,int(front.get('reroute_mode_rounds',0))-1)
                tf['rng']=SplitMix64(front['rng'].state)
                # Proposal caches describe the old head and must not leak into the simulated step.
                tf.pop('_proposal_corridor_cache',None); tf.pop('_proposal_legality_cache',None)
                tf.pop('_proposal_corridor_cache_round',None); tf.pop('_proposal_legality_cache_round',None)
                return tf

            def future_options(child):
                root=dict(child); root['rng']=SplitMix64(child['rng'].state)
                # Keep the real inherited gesture count.  Recovery mode already broadens the
                # legal direction order; zeroing it here made the old preflight less faithful.
                first=self._proposal_variants(root,count=4)[:3]
                out=[]
                for p1 in first:
                    tf=advance_probe(root,p1)
                    second=self._proposal_variants(tf,count=4)[:3]
                    for p2 in second:
                        # The two proposed segments share only their own endpoint; exact visible
                        # grammar is checked against the inherited prefix by _gesture_clear.
                        pts=list(root.get('path',()))+[p1['end'],p2['end']]
                        if self._points_have_compensating_zigzag(pts):
                            continue
                        out.append((p1,p2,tf,p2['end']))
                        if len(out)>=2:
                            return out
                return out

            option_sets=[future_options(child) for child in children]
            viable=all(option_sets)
            if viable:
                def futures_compatible(combo):
                    for i,(oa,ca) in enumerate(zip(combo,children)):
                        for ob,cb in zip(combo[i+1:],children[i+1:]):
                            gap=max(self.r.pathway_interroute_keepout,self._interroute_gap_for_fronts(ca,cb))
                            for ga in (oa[0]['geom'],oa[1]['geom']):
                                for gb in (ob[0]['geom'],ob[1]['geom']):
                                    if ga.intersects(gb) or ga.distance(gb)<gap:
                                        return False
                            if math.hypot(oa[3][0]-ob[3][0],oa[3][1]-ob[3][1]) < 1.35*self.module:
                                return False
                    return True
                viable=any(futures_compatible(combo) for combo in itertools.product(*option_sets))
            if not viable:
                for child in children: self._drop_front(child['id'])
                self.stats['pathway_transactional_birth_reject_count']+=1
                self.stats.setdefault('pathway_fragment_short_future_reject_count',0)
                self.stats['pathway_fragment_short_future_reject_count']+=1
                return False
        # Wide MAIN recovery cohorts used to bypass the short-future proof above entirely.
        # At the hard horizon that could create 10+ singleton siblings at the four-module floor,
        # let them occupy each other's escape room for a few settlement ticks, then legally
        # terminalize the whole family before *any* lane established real side progression.
        #
        # Before mutating that topology, prove and commit one bounded ordinary-clearance future
        # for one physical lane.  This is O(lanes) with a fixed beam/horizon, not a board search.
        # The rest of the newborn siblings still route through the normal shared-snapshot solver.
        # A trace-id certificate (rather than a front flag) preserves the obligation through any
        # later rebase/branch, and render-time terminal backoff may not amputate that one trace
        # below the same eight-module side-progress audit used by materialization.
        wide_main=(len(children)>4 and not f.get('local_gap') and
                   f.get('chip',len(self.chips))<len(self.chips) and
                   self._minimum_materialized_lane_length(f)<8.0*self.module-1e-7)
        if wide_main:
            ranked=sorted(
                children,
                key=lambda child:(
                    self._congestion_at(child['path'][-1]),
                    abs(f['offsets'].get(child['ids'][0],0.0)),
                    child['id']))
            leader=None
            for child in ranked:
                if self._try_young_survival_beam(child,target_modules=9.0,horizon=4,beam_width=12):
                    leader=child
                    break
            if leader is None:
                for child in children: self._drop_front(child['id'])
                self.stats['pathway_transactional_birth_reject_count']+=1
                self.stats.setdefault('pathway_wide_fragment_side_progress_reject_count',0)
                self.stats['pathway_wide_fragment_side_progress_reject_count']+=1
                return False
            self.main_side_progress_trace_ids.add(leader['ids'][0])
            leader['main_side_progress_leader']=True
            self.stats.setdefault('pathway_wide_fragment_side_progress_leader_count',0)
            self.stats['pathway_wide_fragment_side_progress_leader_count']+=1
        f['status']='branched'
        self.stats['pathway_split_count']+=1
        if f.get('local_gap'): self.stats['pathway_local_gap_split_count']+=1
        self.stats['pathway_recovery_fragment_count']+=1
        return bool(children)

    def _fragment_singleton_still_embedded(self,f):
        group=f.get('fragment_group')
        if group is None or len(f.get('ids',()))!=1:
            return False
        # Isolation is a physical condition, not a blind gesture counter.  A recovery child
        # remains locked while another *live* fragment sibling is still within the bus-width
        # neighborhood.  If its siblings have already escaped/connected/legally terminated, or
        # the child has physically separated in one decisive gesture, keeping it alive merely
        # to satisfy an arbitrary two-gesture counter would create false persistence debt.
        p=self._persistence_materialized_paths(f)[f['ids'][0]][-1]
        for oid in self.fragment_members.get(group,()):
            if oid==f['id']:
                continue
            other=self.fronts.get(oid)
            if other is None or other.get('status')!='active':
                continue
            op=self._persistence_materialized_paths(other)[other['ids'][0]][-1]
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
            # This hard-stop deferral executes inside the synchronized MAIN round.  The exact
            # incremental rollback path already removes the owned tail from path queries,
            # congestion and coverage immediately.  Do not rebuild every surviving board
            # segment merely to reach the same pre-snapshot state; the existing round-end
            # compaction retires the tombstones once after routing.
            self._traceback_for_reroute(f,defer_rebuild=True)
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
        realised=self._persistence_materialized_paths(f)
        tid=f['ids'][0]
        if tid not in realised or not realised[tid]:
            return False
        p=realised[tid][-1]
        vx,vy=dir_vec(f['dir']); nx,ny=-vy,vx
        neg=False; pos=False
        lateral_limit=3.25*self.module
        longitudinal_limit=2.35*self.module
        side_key=(f.get('chip'),f.get('side_index'),f.get('side'))
        for oid in self.fronts_by_side.get(side_key,()):
            if oid==f['id']:
                continue
            other=self.fronts.get(oid)
            if other is None or other.get('status') in ('branched','abandoned_short','terminated'):
                continue
            opaths=self._persistence_materialized_paths(other)
            for otid in other.get('ids',()):
                if otid not in opaths or not opaths[otid]:
                    continue
                opts=opaths[otid]
                if len(opts)<2:
                    continue
                q=nearest_point_on_polyline_segments(p,opts)
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

    def _coordinated_terminal_group_safe(self,fronts,allow_fragment_cohort=False,allow_exhausted_embedding=False):
        """Whether an active visual cohort may terminate atomically at the hard horizon.

        The anti-singular-terminal rule is about the *nearest visible lateral neighbours*.  A
        pair/cluster of adjacent mature lanes that end together is not a singleton corpse merely
        because farther same-root lanes continue on both sides.  V47 therefore evaluates the
        final cohort transaction as a unit: every member must have cleared all non-terminal
        persistence debt, and for each singleton the nearest visible lane on at least one side
        must also belong to the ending cohort (or already be a non-continuing terminal).
        """
        fs=[f for f in fronts if f.get('status')=='active']
        if not fs:
            return False
        ending={f['id'] for f in fs}
        for f in fs:
            if f.get('local_gap') or f.get('chip',len(self.chips))>=len(self.chips):
                return False
            if self._minimum_materialized_lane_length(f) < self.main_launch_maturity_modules*self.module-1e-7:
                return False
            if self._source_egress_pending(f) or f.get('fan_pending') or f.get('fragment_pending'):
                return False
            if f.get('branch_stage') is not None:
                return False
            if self._fragment_singleton_still_embedded(f):
                # During normal/shared persistence this remains hard debt.  At the final
                # coordinated horizon only, an already-attempted/failed bounded separation may
                # become legally terminable.  Otherwise every live fragment sibling causing the
                # relational embedding must participate in this same atomic commit.
                if allow_exhausted_embedding and f.get('protected_launch_unresolved'):
                    pass
                elif allow_fragment_cohort:
                    group=f.get('fragment_group')
                    if group is None:
                        return False
                    for oid in self.fragment_members.get(group,()):
                        if oid==f['id']:
                            continue
                        other=self.fronts.get(oid)
                        if other is not None and other.get('status')=='active' and oid not in ending:
                            return False
                else:
                    return False
            if len(f.get('ids',()))!=1:
                continue
            paths=self._materialized_paths(f); tid=f['ids'][0]
            if tid not in paths or not paths[tid]:
                return False
            p=paths[tid][-1]; vx,vy=dir_vec(f['dir']); nx,ny=-vy,vx
            lateral_limit=3.25*self.module; longitudinal_limit=2.35*self.module
            nearest={-1:None,1:None}
            side_key=(f.get('chip'),f.get('side_index'),f.get('side'))
            for oid in self.fronts_by_side.get(side_key,()):
                if oid==f['id']:
                    continue
                other=self.fronts.get(oid)
                if other is None or other.get('status') in ('branched','abandoned_short'):
                    continue
                opaths=self._materialized_paths(other)
                for otid in other.get('ids',()):
                    opts=opaths.get(otid)
                    if not opts or len(opts)<2:
                        continue
                    q=nearest_point_on_polyline_segments(p,opts)
                    dx=q[0]-p[0]; dy=q[1]-p[1]; lateral=dx*nx+dy*ny
                    if abs(lateral)>lateral_limit or abs(lateral)<=.40*self.U:
                        continue
                    head=opts[-1]
                    if oid in ending or other.get('status')=='terminated':
                        # A neighbour ending at roughly the same longitudinal station visually
                        # breaks the bus; farther continuing lanes must not make this terminal
                        # look singular through that nearer endpoint.
                        hforward=(head[0]-p[0])*vx+(head[1]-p[1])*vy
                        if abs(hforward)>longitudinal_limit:
                            continue
                        continues=False
                    elif other.get('status')=='active':
                        hforward=(head[0]-p[0])*vx+(head[1]-p[1])*vy
                        if abs(hforward)>longitudinal_limit:
                            continue
                        continues=True
                    else:
                        max_forward=max((x-p[0])*vx+(y-p[1])*vy for x,y in opts)
                        if max_forward<.65*self.module:
                            continue
                        continues=True
                    sign=-1 if lateral<0 else 1
                    cand=(abs(lateral),continues,oid,otid)
                    if nearest[sign] is None or cand[0]<nearest[sign][0]:
                        nearest[sign]=cand
            if nearest[-1] is not None and nearest[1] is not None and nearest[-1][1] and nearest[1][1]:
                if not (allow_exhausted_embedding and f.get('protected_launch_unresolved')):
                    return False
        return True

    def _coordinated_root_terminal_group_safe(self,fronts,allow_exhausted_embedding=False):
        return self._coordinated_terminal_group_safe(
            fronts,allow_fragment_cohort=False,allow_exhausted_embedding=allow_exhausted_embedding)

    def _coordinated_fragment_terminal_group_safe(self,fronts,allow_exhausted_embedding=False):
        """Evaluate one recovery-fragment family as a single terminal transaction.

        Individual fragment children can correctly report physical embedding while their live
        siblings are still beside them.  At the hard horizon that relational debt disappears
        only if every such live sibling terminates in the same atomic cohort; all other visible
        and structural persistence obligations remain unchanged.
        """
        fs=[f for f in fronts if f.get('status')=='active']
        groups={f.get('fragment_group') for f in fs}
        if not fs or None in groups or len(groups)!=1:
            return False
        return self._coordinated_terminal_group_safe(
            fs,allow_fragment_cohort=True,allow_exhausted_embedding=allow_exhausted_embedding)

    def _main_terminal_visible_floor_modules(self,f,tid):
        """Rendered terminal-length floor for one physical MAIN trace.

        Six modules remains the ordinary preferred free-terminal floor.  A trace explicitly
        chosen as a wide-fragment side-progress leader carries the stronger eight-module cohort
        obligation because losing that one visible tail can turn an otherwise valid family into
        an all-young stalled side.
        """
        floor=self.main_launch_preferred_terminal_modules
        if (tid in self.main_side_progress_trace_ids and not f.get('local_gap') and
                f.get('chip',len(self.chips))<len(self.chips)):
            floor=max(floor,8.0)
        return floor

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
        visible_floor=(self._main_terminal_visible_floor_modules(f,tid) if not f.get('local_gap') else 2.75)*self.module
        visible_floor=max(visible_floor,float(f.get('_local_capacity_visible_floor',0.0)))
        max_back=max(0.0,total-(visible_floor+marker_clip))
        # Search the whole legal excess tail in bounded increments; no route search is involved.
        n=max(1,min(14,int(math.ceil(max_back/max(.14*self.module,1e-9)))))
        steps=[0.0]+[(k/n)*max_back for k in range(1,n+1)] if max_back>1e-9 else [0.0]
        # A certified filled LOCAL endpoint does not consume hollow-marker
        # clipping. Preserve ordinary candidates/order, then include its exact
        # already-proven visible-prefix endpoint as a legal final settlement.
        if f.get('_local_capacity_visible_floor') is not None:
            crng=SplitMix64(mix_once(self.sseed ^ (tid+1)*0x9E3779B97F4A7C15))
            special=bool(f.get('local_gap_special'))
            if not special and f.get('parent') is None:
                crng.random()
            if special or crng.random()<.55:
                certified_back=max(0.0,total-visible_floor)
                if certified_back>max_back+1e-9:
                    steps.append(certified_back)
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
        # Side-totality is a construction obligation, not a materialization-time rejection.
        # If this is the last live outcome from a chip side and no sibling outcome has yet made
        # eight visible modules (or escaped/connected), ordinary exhaustion may not kill it.
        # Give that survivor fresh local planning room; other sibling fronts remain free to die
        # independently, so this is not an all-lanes-must-be-long rule.
        if (not f.get('local_gap') and self._main_side_progress_debt(f) and
                not self._other_active_main_side_fronts(f)):
            self.stats.setdefault('pathway_side_progress_termination_deferral_count',0)
            self.stats['pathway_side_progress_termination_deferral_count']+=len(f.get('ids',()))
            f['max_gestures']=max(f['max_gestures'],f['gestures']+4)
            f['failures']=0
            f['reroute_attempts']=min(f.get('reroute_attempts',0),max(0,self.profile['reroute_budget']-3))
            f['quality_repair_pending']=True
            f['quality_repair_reason']='side_progress_persistence'
            f['lifecycle']='RECOVERING'
            return
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
                self.main_launch_maturity_modules*self.module-1e-7 <= min_lane < self.main_launch_preferred_terminal_modules*self.module-1e-7):
            # V47: 4 modules is the inviolable visible floor, not the normal stopping target.
            # Keep this family alive through the bounded shared persistence clock until six
            # modules are physically visible, without resurrecting whole-board V44 rounds.
            f['post_egress_extension_attempted']=True
            f['max_gestures']=max(f['max_gestures'],f['gestures']+2)
            f['failures']=0
            if not f.get('reroute_pending') and f.get('reroute_attempts',0)<self.profile['reroute_budget']:
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
        # V37 local fillers are not decorative stubs.  Their minimum useful journey follows
        # the measured room they were spawned to serve.  If a line is still short for that room,
        # pivot/recover toward its remaining uncovered area instead of terminating immediately.
        if f.get('local_gap'):
            want=float(f.get('local_gap_min_terminal_modules',4.0))*self.module
            if min_lane < want-1e-7 and f.get('local_gap_persistence_deferrals',0)<4:
                f['local_gap_persistence_deferrals']=f.get('local_gap_persistence_deferrals',0)+1
                f['max_gestures']=max(f['max_gestures'],f['gestures']+4)
                f['failures']=0
                f['reroute_attempts']=min(f.get('reroute_attempts',0),max(0,self.profile['reroute_budget']-3))
                f['quality_repair_pending']=True; f['quality_repair_reason']='local_gap_region_persistence'; f['lifecycle']='RECOVERING'
                f['target']=self._local_gap_target(f['path'][-1],f['rng'],f['dir'],
                    cluster_id=f.get('local_fill_cluster_id'))
                return
        # Local fillers and already-mature main routes retain the ordinary tiny-stub rule.
        if min_lane+1e-9<2.75*self.module and f.get('young_defer_count',0)<2:
            f['young_defer_count']=f.get('young_defer_count',0)+1
            f['max_gestures']=max(f['max_gestures'],f['gestures']+3); f['failures']=0
            f['reroute_attempts']=min(f.get('reroute_attempts',0),max(0,self.profile['reroute_budget']-2))
            f['quality_repair_pending']=True; f['quality_repair_reason']='young_persistence'; f['lifecycle']='RECOVERING'
            return
        if min_lane+1e-9<2.75*self.module:
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
                            if (not math.isfinite(dist) or dist<.2*self.module or
                                    dist>1.10*self._routing_horizon()): continue
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
            if not math.isfinite(dist) or dist<0 or dist>1.10*self._routing_horizon():
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

    def _try_embedded_singleton_separation(self,f,max_steps=3):
        """Bounded exact local repair for a singleton that still looks embedded in a live bus.

        The repair uses only ordinary straight/+45/-45 gestures and the normal collision gate.
        It never performs a board search.  Each accepted step must improve geometric separation;
        once the lane is genuinely independent it may terminate normally.
        """
        if f.get('status')!='active' or len(f.get('ids',()))!=1 or f.get('local_gap'):
            return False
        def embedded(front):
            return self._fragment_singleton_still_embedded(front) or self._singleton_between_live_siblings(front)
        if not embedded(f):
            return False
        moved=0
        for _ in range(max(1,int(max_steps))):
            if not embedded(f): break
            start=f['path'][-1]
            # Score candidate heads by distance from live same-side siblings.  Candidate legality
            # is still decided by the authoritative gesture-clear predicate.
            siblings=[]; side_key=(f.get('chip'),f.get('side_index'),f.get('side'))
            for oid in self.fronts_by_side.get(side_key,()):
                if oid==f['id']: continue
                other=self.fronts.get(oid)
                if other is None or other.get('status') in ('branched','abandoned_short','terminated'):
                    continue
                for pts in self._materialized_paths(other).values():
                    if pts: siblings.append(pts[-1])
            def sep(pt):
                return min((math.hypot(pt[0]-q[0],pt[1]-q[1]) for q in siblings),default=99.0*self.module)
            old_sep=sep(start); candidates=[]
            for d in (f['dir'],(f['dir']-1)%8,(f['dir']+1)%8):
                if not self._mod_delta_ok(f['dir'],d): continue
                for modules in (1.0,1.5,2.0,2.5,3.0):
                    end=point_along_dir(start,d,modules*self.module)
                    if not (0<=end[0]<=self.W and 0<=end[1]<=self.H): continue
                    pts=list(f['path'])+[end]
                    if self._points_have_compensating_zigzag(pts) or self._candidate_loop_risk(f,d,end):
                        continue
                    geom=self._corridor_geom(f,start,end)
                    self.stats['pathway_lookahead_evaluation_count']+=1
                    if not self._gesture_clear(f,start,end,geom,allow_outside=False):
                        continue
                    tf=dict(f); tf['path']=pts; tf['dir']=d
                    new_sep=sep(end)
                    clears=not embedded(tf)
                    # Never spend a separation repair on a step that geometrically regresses.
                    if modules<2.0 and not clears:
                        continue
                    if not clears and new_sep<=old_sep+.20*self.module:
                        continue
                    score=(1 if clears else 0,new_sep,modules,-abs((d-f['dir'])%8))
                    candidates.append((score,dict(front=f['id'],start=start,end=end,dir=d,modules=modules,geom=geom,score=0.0)))
            if not candidates: break
            _score,proposal=max(candidates,key=lambda x:x[0])
            self._accept(f,proposal,defer_post=True); moved+=1
        if moved:
            self.stats.setdefault('pathway_embedded_singleton_separation_repair_count',0)
            self.stats['pathway_embedded_singleton_separation_repair_count']+=1
        if not embedded(f):
            return True

        return False

    def _settle_structural_persistence_debt_atomic(self,round_index_base,rounds=2):
        """Complete residual branch transitions from shared snapshots, never sequentially.

        The old horizon loop called _try_complete_structural_persistence_debt() front-by-front.
        That could commit a logical gesture that ordinary same-round arbitration had already
        proven incompatible with a sibling, creating render-only crossings later removed by
        preflight.  Here HOLD is a first-class outcome: choose the maximum compatible subset,
        commit it atomically, and let held peers re-propose against the next snapshot.
        """
        moved_total=0
        for tick in range(max(1,int(rounds))):
            active=[f for f in self.fronts.values() if f.get('status')=='active' and
                    not f.get('local_gap') and f.get('branch_stage') is not None]
            if not active: break
            rr=int(round_index_base)+tick
            variant_map={}; blocked=[]
            for f in sorted(active,key=lambda x:x['id']):
                f['_routing_round']=rr
                vs=self._proposal_variants(f,3)
                if vs: variant_map[f['id']]=vs
                else: blocked.append(f)
            # No legal structural gesture: on a mature lane cancel only the unmaterialized
            # decorative preference.  Existing visible geometry is preserved exactly.
            for f in blocked:
                if (self._minimum_materialized_lane_length(f) >=
                        self.main_launch_preferred_terminal_modules*self.module-1e-7 and
                        not self._source_egress_pending(f) and not f.get('fan_pending')):
                    f['branch_stage']=None; f['branch_turn']=None
                    self.stats.setdefault('pathway_structural_persistence_exhausted_count',0)
                    self.stats['pathway_structural_persistence_exhausted_count']+=1
            chosen={}; grouped=set()
            for group in self._conflict_groups(variant_map):
                grouped.update(group)
                pools={fid:list(variant_map[fid][:3]) for fid in group}
                order=sorted(group,key=lambda fid:(len(pools[fid]),fid))
                best=None; seq=[]; checked=0; limit=2048
                def score(p):
                    life=self._refresh_lifecycle(self.fronts[p['front']])
                    bonus={'STRUCTURAL_TRANSITION':7.0,'CONNECTION_PENDING':8.0,'RECOVERING':4.0}.get(life,0.0)
                    return float(p.get('score',0.0))+bonus
                def key_for(xs):
                    return tuple((p['front'],p['dir'],p['modules'],round(p['end'][0],4),round(p['end'][1],4))
                                 for p in sorted(xs,key=lambda q:q['front']))
                def dfs(k,total):
                    nonlocal best,checked
                    if checked>=limit: return
                    if k==len(order):
                        checked+=1
                        if not seq: return
                        rank=(len(seq),total); key=key_for(seq)
                        if best is None or rank>best[0] or (rank==best[0] and key<best[1]):
                            best=(rank,key,list(seq))
                        return
                    fid=order[k]
                    dfs(k+1,total)  # HOLD
                    for p in pools[fid]:
                        checked+=1
                        if checked>=limit: return
                        if any(self._future_conflict(p,q) for q in seq): continue
                        seq.append(p); dfs(k+1,total+score(p)); seq.pop()
                dfs(0,0.0)
                self.stats.setdefault('pathway_structural_persistence_conflict_combination_count',0)
                self.stats['pathway_structural_persistence_conflict_combination_count']+=checked
                if best is not None:
                    chosen.update({p['front']:p for p in best[2]})
                    held=len(group)-len(best[2])
                    if held:
                        self.stats.setdefault('pathway_structural_persistence_hold_front_count',0)
                        self.stats['pathway_structural_persistence_hold_front_count']+=held
            for fid,vs in variant_map.items():
                if fid not in grouped and vs: chosen[fid]=vs[0]
            selected=[p for fid,p in sorted(chosen.items()) if
                      self.fronts[fid].get('status')=='active' and self.fronts[fid].get('branch_stage') is not None]
            for p in selected: self._accept(self.fronts[p['front']],p,defer_post=True)
            if selected:
                moved_total+=len(selected)
                self.stats.setdefault('pathway_structural_persistence_atomic_round_count',0)
                self.stats['pathway_structural_persistence_atomic_round_count']+=1
            self.stats.setdefault('pathway_structural_persistence_atomic_tick_count',0)
            self.stats['pathway_structural_persistence_atomic_tick_count']+=1
        # A structural preference that remained mutually incompatible through the bounded shared
        # ticks is not permission to create a crossing.  Mature lanes retain their clean prefix;
        # cancel only the unmaterialized turn intention, exactly as the old no-variant fallback.
        for f in self.fronts.values():
            if (f.get('status')=='active' and not f.get('local_gap') and f.get('branch_stage') is not None and
                    self._minimum_materialized_lane_length(f) >= self.main_launch_preferred_terminal_modules*self.module-1e-7 and
                    not self._source_egress_pending(f) and not f.get('fan_pending')):
                f['branch_stage']=None; f['branch_turn']=None
                self.stats.setdefault('pathway_structural_persistence_exhausted_count',0)
                self.stats['pathway_structural_persistence_exhausted_count']+=1
        if moved_total:
            self.stats.setdefault('pathway_structural_persistence_repair_count',0)
            self.stats['pathway_structural_persistence_repair_count']+=moved_total
        return moved_total

    def _try_complete_structural_persistence_debt(self,f,max_steps=2):
        """Finish at most two ordinary branch-transition gestures at the late horizon."""
        if f.get('status')!='active' or f.get('local_gap') or f.get('branch_stage') is None:
            return False
        moved=0
        for _ in range(max(1,int(max_steps))):
            if f.get('branch_stage') is None: break
            variants=self._proposal_variants(f,3)
            if not variants:
                # At the bounded late horizon a mature child may have completed the visible
                # straight rebase but be physically unable to perform the sampled decorative
                # branch turn.  The turn is a preference (ordinary routing already falls back
                # to straight motion); once every exact continuation is exhausted, cancel only
                # the unmaterialized turn intention.  No rendered geometry is deleted or bent.
                if (self._minimum_materialized_lane_length(f) >=
                        self.main_launch_preferred_terminal_modules*self.module-1e-7 and
                        not self._source_egress_pending(f) and not f.get('fan_pending')):
                    f['branch_stage']=None; f['branch_turn']=None
                    self.stats.setdefault('pathway_structural_persistence_exhausted_count',0)
                    self.stats['pathway_structural_persistence_exhausted_count']+=1
                break
            self._accept(f,variants[0],defer_post=True); moved+=1
        if moved:
            self.stats.setdefault('pathway_structural_persistence_repair_count',0)
            self.stats['pathway_structural_persistence_repair_count']+=1
        return f.get('branch_stage') is None

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
            max_keepout=max(self.r.pathway_main_chip_keepout,self.r.pathway_static_keepout)
            checked=set()
            for gi,obj in self.static_index.query(expand_bounds(disc.bounds,max_keepout)):
                # Complex component groups may contribute several primitive records; each exact
                # primitive is sufficient for union intersection/distance, so duplicate group ids
                # need not be rechecked once a violation is found.
                keepout=(self.r.pathway_main_chip_keepout if gi < len(self.chips)
                         else self.r.pathway_static_keepout)
                if not self._bounds_within_gap(disc.bounds,obj.geom.bounds,keepout):
                    continue
                if disc.intersects(obj.geom) or disc.distance(obj.geom)<keepout:
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

    def _retire_front_segments(self,front_id):
        """Mark one front's owned segments for authoritative removal on the next rebuild."""
        owned=self.path_segments_by_front.get(front_id,[])
        if not owned: return 0
        for rec in owned: rec['_retired']=True
        n=len(owned); self.path_segments_by_front[front_id]=[]
        return n

    def _restore_front_owned_snapshot(self,saved_front,saved_segments,rebuild_local_coverage=False):
        """Restore one front transactionally without snapshotting unrelated board history."""
        fid=saved_front['id']
        self._retire_front_segments(fid)
        self.fronts[fid]=saved_front
        for rec0 in saved_segments:
            rec=dict(rec0); rec.pop('_retired',None)
            self.path_segments.append(rec)
        self._rebuild_path_index_and_coverage(rebuild_local_coverage=rebuild_local_coverage)
        return self.fronts[fid]

    def _prune_abandoned_local_segments(self,front_ids):
        """Remove non-rendered local filler history from occupancy and coverage immediately.

        A local line that is declared ``abandoned_short`` is not emitted in the SVG.  Its old
        segments therefore cannot continue to count toward the 40% service target or block later
        filler waves as invisible geometry.  Prune a whole batch and rebuild once per tick.
        """
        ids=set(int(x) for x in front_ids)
        if not ids: return 0
        before=len(self.path_segments)
        self.path_segments=[rec for rec in self.path_segments if rec.get('front') not in ids]
        removed=before-len(self.path_segments)
        if removed:
            self._rebuild_path_index_and_coverage()
            self.stats.setdefault('pathway_local_gap_abandoned_segment_prune_count',0)
            self.stats['pathway_local_gap_abandoned_segment_prune_count']+=removed
        return removed

    @staticmethod
    def _local_direct_failure_cert_should_skip(cache,key,thickness):
        """Return True only for a previously proven failure at <= this thickness.

        The direct mop-up call is monotonic: committed obstacles can only be added while the
        call runs.  A static/path-blocked centerline that failed at thickness ``t`` therefore
        cannot become legal later at an equal-or-larger thickness.  Thinner retries must still
        execute the exact checker, and successes are never cached.
        """
        failed_t=cache.get(key)
        return failed_t is not None and float(thickness)+1e-12>=float(failed_t)

    @staticmethod
    def _local_direct_failure_cert_record(cache,key,thickness):
        """Record the thinnest proven static/path failure for one direct centerline key."""
        t=float(thickness); prev=cache.get(key)
        if prev is None or t<float(prev):
            cache[key]=t

    def _local_gap_direct_mopup(self,max_lines=48):
        """Fast exact *bent* mop-up for substantial still-open residual corridors.

        V37 finished the service target with many start-to-end ruler strokes.  V38 keeps the
        cheap tail pass, but every substantial mop-up candidate first has to prove a legal
        +/-45-degree pivot in the middle of the available corridor.  Only genuinely narrow
        pockets may use a rare straight fallback, and even those are globally capped.

        The maneuver is transactional for its first bend: both the incoming leg and the turned
        leg are exact-checked before either is committed.  After that, the normal local proposal
        grammar may extend the line for a few more gestures, so long rooms can be articulated
        rather than merely bisected.
        """
        if not self.local_gap_open_cells: return 0
        rng=SplitMix64(local_pathway_seed(self.sseed)^0xD1B54A32D192ED03)
        nx,ny=self.r.local_gap_grid_shape(); cw=self.W/nx; ch=self.H/ny
        made=0; bent_made=0; straight_made=0; exhausted=set()
        # Undirected grid axes: horizontal, vertical and the two diagonals.
        axes=((1,0),(0,1),(1,1),(1,-1))
        straight_cap=max(1,int(math.ceil(max_lines*.09)))
        # Cache expensive axis-run extraction per residual region.  Only a first touch in that
        # region can change its binary uncovered-cell set, and the coverage raster increments
        # ``local_gap_region_touch_version`` exactly at that event.
        run_cache={}
        # Cache immutable run-family identity alongside each versioned residual run list.
        # Endpoint rounding and family-key construction do not depend on retry state, so they
        # should not be regenerated after every mop-up batch.
        enriched_run_cache={}
        plan_sample_cache={}
        rescue_plan_sample_cache={}
        # One-sided exact-failure certificates scoped to this monotonic cleanup call.  LOCAL
        # direct mop-up only commits new obstacles while it runs; it does not remove them.
        direct_failure_width={}
        # Approach-level bound: one unchanged direct run family gets only a small number of
        # stochastic thickness/order retries.  Reconsidering the same corridor dozens of times
        # is polling, not new geometric work.  Three attempts preserve every observed healthy
        # 0.75 retry-success while making work per run family locally bounded.
        direct_run_family_attempts={}
        direct_run_family_quarantined=set()
        direct_run_family_dirty_regions=set()
        direct_run_family_retry_cap=self.r.local_direct_run_family_attempt_cap()
        def note_direct_run_failure(run_family_key):
            if (direct_run_family_attempts.get(run_family_key,0)>=direct_run_family_retry_cap and
                    run_family_key not in direct_run_family_quarantined):
                direct_run_family_quarantined.add(run_family_key)
                # LOCAL-1: quarantine is monotonic for this direct-mopup call.  Mark only the
                # owning region dirty; before that region is scanned again, compact its cached
                # ordered run list once.  This preserves production list iteration/candidate
                # order while removing dead families from the live search surface.
                direct_run_family_dirty_regions.add(run_family_key[0])
                self.stats.setdefault('pathway_local_gap_direct_run_family_quarantine_count',0)
                self.stats['pathway_local_gap_direct_run_family_quarantine_count']+=1
                self.stats.setdefault('pathway_local_gap_direct_run_family_retired_count',0)
                self.stats['pathway_local_gap_direct_run_family_retired_count']+=1
        def certified_gesture_clear(f,a,b,geom,key,thickness,extra_segments=()):
            if self._local_direct_failure_cert_should_skip(direct_failure_width,key,thickness):
                self.stats.setdefault('pathway_local_gap_direct_failure_cert_hit_count',0)
                self.stats['pathway_local_gap_direct_failure_cert_hit_count']+=1
                return False
            old_capture=self._capture_gesture_failure_cert; old_cert=self._last_gesture_failure_cert
            self._capture_gesture_failure_cert=True; self._last_gesture_failure_cert=None
            try:
                ok=self._gesture_clear(f,a,b,geom,allow_outside=False,extra_segments=extra_segments)
                cert=self._last_gesture_failure_cert
            finally:
                self._capture_gesture_failure_cert=old_capture
                self._last_gesture_failure_cert=old_cert
            if not ok and cert is not None and cert[0] in ('static','path'):
                self._local_direct_failure_cert_record(direct_failure_width,key,thickness)
            return ok

        def runs_for_region(region):
            # The authoritative per-region targetable set is already maintained incrementally;
            # do not rebuild ``region cells & whole-board uncovered`` for every mop-up attempt.
            cells=self._local_gap_targetable_cells(region['id'])
            if len(cells)<3: return []
            out=[]
            for dx,dy in axes:
                for c in cells:
                    prev=(c[0]-dx,c[1]-dy)
                    if prev in cells: continue
                    run=[]; q=c
                    while q in cells:
                        run.append(q); q=(q[0]+dx,q[1]+dy)
                    if len(run)<3: continue
                    a=((run[0][0]+.5)*cw,(run[0][1]+.5)*ch)
                    b=((run[-1][0]+.5)*cw,(run[-1][1]+.5)*ch)
                    L=math.hypot(b[0]-a[0],b[1]-a[1])
                    if L < 3.25*self.module: continue
                    out.append((L,len(run),a,b))
            return out

        def sampled_uncovered_score(points,uncovered):
            touched=set()
            for a,b in zip(points,points[1:]):
                L=math.hypot(b[0]-a[0],b[1]-a[1])
                steps=max(2,int(math.ceil(L/max(.45*self.module,1e-9))))
                for i in range(steps+1):
                    t=i/steps
                    c=self._gap_cell((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
                    if c in uncovered: touched.add(c)
            return len(touched)

        def immutable_sample_cells(points):
            """Exact historical service-sample cells for a fixed centerline plan.

            Repeated mop-up retries change only the current uncovered set and stroke width; the
            centerline sample locations for a given residual run are immutable.  Cache those cell
            identities once, then recover the historical served score by set intersection.
            """
            touched=set()
            for a,b in zip(points,points[1:]):
                L=math.hypot(b[0]-a[0],b[1]-a[1])
                steps=max(2,int(math.ceil(L/max(.45*self.module,1e-9))))
                for i in range(steps+1):
                    t=i/steps
                    touched.add(self._gap_cell((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)))
            return frozenset(touched)

        debt_priority_by_region=getattr(self,'_local_gap_service_debt_priority_by_region',None)
        debt_priority_mode=debt_priority_by_region is not None
        def plan_service_priority(cells):
            if not debt_priority_mode:
                return float(len(cells))
            return sum(max(0,13-self.local_gap_coverage_mask_by_cell.get(c,0).bit_count()) for c in cells)/13.0
        def begin_debt_capture():
            if debt_priority_mode:
                self._local_gap_service_debt_touch_capture={}
        def apply_debt_capture():
            if not debt_priority_mode:
                return
            capture=getattr(self,'_local_gap_service_debt_touch_capture',None) or {}
            self._local_gap_service_debt_touch_capture=None
            for cell,(old_bits,new_bits) in capture.items():
                paid=max(0,min(new_bits,13)-min(old_bits,13))/13.0
                if not paid:
                    continue
                rid=self.local_gap_region_by_cell.get(cell)
                if rid is not None:
                    debt_priority_by_region[rid]=max(0.0,debt_priority_by_region.get(rid,0.0)-paid)

        counts={r['id']:0 for r in self.local_gap_regions}
        for f in self.fronts.values():
            if f.get('local_gap') and f.get('status') in ('terminated','escaped'):
                rid=f.get('local_gap_region_id'); counts[rid]=counts.get(rid,0)+1

        while made<max_lines and self._local_gap_service_fraction()+1e-9<self.local_gap_target_fraction:
            uncovered=self._local_gap_targetable_cells()
            if not uncovered: break
            candidates=[]
            for r in self.local_gap_regions:
                if r['id'] in exhausted: continue
                uc=len(self._local_gap_targetable_cells(r['id']))
                if uc<3 or (r['size']=='small' and uc<5): continue
                service_mass=(debt_priority_by_region.get(r['id'],0.0) if debt_priority_mode else float(uc))
                ver=self.local_gap_region_touch_version.get(r['id'],0)
                cached=run_cache.get(r['id'])
                if cached is None or cached[0]!=ver:
                    rr=runs_for_region(r)
                    run_cache[r['id']]=(ver,rr)
                else:
                    rr=cached[1]
                if not rr:
                    exhausted.add(r['id']); continue
                ecached=enriched_run_cache.get(r['id'])
                if ecached is None or ecached[0]!=ver:
                    enriched=[]
                    retired_on_rebuild=0
                    for L,runlen,a,b in rr:
                        _p0=(round(a[0],6),round(a[1],6)); _p1=(round(b[0],6),round(b[1],6))
                        run_family_key=(r['id'],)+tuple(sorted((_p0,_p1)))
                        if run_family_key in direct_run_family_quarantined:
                            retired_on_rebuild+=1
                            continue
                        enriched.append((L,runlen,a,b,run_family_key))
                    if retired_on_rebuild:
                        self.stats.setdefault('pathway_local_gap_direct_run_family_quarantine_skip_count',0)
                        self.stats['pathway_local_gap_direct_run_family_quarantine_skip_count']+=retired_on_rebuild
                    enriched_run_cache[r['id']]=(ver,enriched)
                    direct_run_family_dirty_regions.discard(r['id'])
                else:
                    enriched=ecached[1]
                    if r['id'] in direct_run_family_dirty_regions:
                        before=len(enriched)
                        enriched=[item for item in enriched if item[4] not in direct_run_family_quarantined]
                        retired=before-len(enriched)
                        if retired:
                            self.stats.setdefault('pathway_local_gap_direct_run_family_quarantine_skip_count',0)
                            self.stats['pathway_local_gap_direct_run_family_quarantine_skip_count']+=retired
                        enriched_run_cache[r['id']]=(ver,enriched)
                        direct_run_family_dirty_regions.discard(r['id'])
                for L,runlen,a,b,run_family_key in enriched:
                    score=L*(1.0+.012*service_mass)/(1.0+.12*counts.get(r['id'],0))
                    candidates.append((score,L,runlen,-r['id'],r,a,b,run_family_key))
            if not candidates: break
            candidates.sort(reverse=True,key=lambda z:(z[0],z[1],z[2],z[3]))

            placed=False; tried_regions=set()
            for _score,L,_runlen,_neg,r,a,b,run_family_key in candidates[:24]:
                tried_regions.add(r['id'])
                direct_run_family_attempts[run_family_key]=direct_run_family_attempts.get(run_family_key,0)+1
                if rng.random()<.5: a,b=b,a
                d=nearest_dir_index(b[0]-a[0],b[1]-a[1])
                vx,vy=dir_vec(d); inset=.18*min(cw,ch)
                a2=(a[0]+vx*inset,a[1]+vy*inset)
                b2=(b[0]-vx*inset,b[1]-vy*inset)
                corridor_len=math.hypot(b2[0]-a2[0],b2[1]-a2[1])
                if corridor_len < 3.0*self.module:
                    note_direct_run_failure(run_family_key); continue
                plan_key=(r['id'],round(a2[0],6),round(a2[1],6),round(b2[0],6),round(b2[1],6),d)
                fixed_plans=plan_sample_cache.get(plan_key)
                if fixed_plans is None:
                    fixed_plans={}
                    for _frac in (.36,.50,.64):
                        _dist1=max(2.1*self.module,min(corridor_len*.68,_frac*corridor_len))
                        if _dist1>corridor_len-.85*self.module: continue
                        _pivot=point_along_dir(a2,d,_dist1)
                        if self._gap_cell(_pivot) not in r['cells']: continue
                        for _sign in (-1,1):
                            _d2=(d+_sign)%8
                            for _m2 in (2,3,4):
                                _end2=point_along_dir(_pivot,_d2,_m2*self.module)
                                if self._gap_cell(_end2) not in r['cells']: continue
                                fixed_plans[(_frac,_sign,_m2)]=(
                                    _pivot,_d2,_end2,_dist1,
                                    immutable_sample_cells((a2,_pivot,_end2)))
                    plan_sample_cache[plan_key]=fixed_plans

                t=rng.uniform(1.85,2.85)*self.U
                tid=self.next_trace_id
                synthetic_chip=len(self.chips)+100000+self.stats.get('pathway_local_gap_source_count',0)+made
                f=self._make_front(ids=[tid],chip=synthetic_chip,side='local',side_index=synthetic_chip,
                                   path=[a2],direction=d,offsets={tid:0.0},thicknesses={tid:t},prefixes={tid:[]},
                                   rng=SplitMix64(rng.next_u64()),intent='explore',target=b2,
                                   local_cluster_id=r['id'])
                f['local_gap']=True; f['local_gap_special']=False; f['fan_pending']=False
                f['local_gap_region_id']=r['id']; f['local_gap_branch_boost']=rng.uniform(*self.r.local_gap_branch_boost_range)
                f['local_gap_exit_allowed']=False
                f['local_gap_min_terminal_modules']=2.75 if r['size']=='small' else (3.5 if r['size']=='medium' else 5.0)
                f['local_gap_turn_count']=0; f['local_gap_turn_due_straights']=1
                half=.5*t
                marker_extent=self.r._termination_dot_radius(t)+.5*self.r.termination_dot_hollow_stroke
                source_key=('source',round(a2[0],5),round(a2[1],5))
                if self._local_direct_failure_cert_should_skip(direct_failure_width,source_key,t):
                    self.stats.setdefault('pathway_local_gap_direct_failure_cert_hit_count',0)
                    self.stats['pathway_local_gap_direct_failure_cert_hit_count']+=1
                    self._drop_front(f['id']); note_direct_run_failure(run_family_key); continue
                if not self._local_gap_source_clearance(a2,half,marker_extent=marker_extent,
                                                        cluster_id=r['id']):
                    self._local_direct_failure_cert_record(direct_failure_width,source_key,t)
                    self._drop_front(f['id']); note_direct_run_failure(run_family_key); continue

                # Prove a bend near the body of the corridor, never as a tiny decorative kink at
                # an endpoint.  First rank variants on the cheap residual grid, then exact-check
                # only the strongest handful.  This keeps V38's richer articulation within the
                # same bounded-runtime architecture as V37.
                pivot_fracs=[.36,.50,.64]; rng.shuffle(pivot_fracs)
                turn_signs=[-1,1]; rng.shuffle(turn_signs)
                m2s=[2,3,4]; rng.shuffle(m2s)
                coarse=[]
                for frac in pivot_fracs:
                    for sign in turn_signs:
                        for m2 in m2s:
                            fixed=fixed_plans.get((frac,sign,m2))
                            if fixed is None: continue
                            pivot,d2,end2,dist1,sample_cells=fixed
                            served_cells=sample_cells & uncovered
                            served=len(served_cells)
                            if served<2: continue
                            served_priority=plan_service_priority(served_cells)
                            # Coarse capacity comes from the residual map only.  Exact obstacle
                            # geometry is intentionally deferred until after ranking.
                            cap=self._local_space_capacity(f,end2,d2)
                            total=dist1+m2*self.module
                            cscore=3.1*served_priority+1.15*cap+total/max(self.module,1e-9)-1.2*abs(frac-.50)
                            coarse.append((cscore,rng.random(),pivot,d2,end2,dist1,m2))
                coarse.sort(key=lambda z:(-z[0],z[1]))
                bend_plans=[]; first_leg_cache={}
                for cscore,_rand,pivot,d2,end2,dist1,m2 in coarse[:6]:
                    pkey=(round(pivot[0],5),round(pivot[1],5))
                    cached=first_leg_cache.get(pkey)
                    if cached is None:
                        k1=('first',round(a2[0],5),round(a2[1],5),round(pivot[0],5),round(pivot[1],5))
                        if self._local_direct_failure_cert_should_skip(direct_failure_width,k1,t):
                            self.stats.setdefault('pathway_local_gap_direct_failure_cert_hit_count',0)
                            self.stats['pathway_local_gap_direct_failure_cert_hit_count']+=1
                            ok=False; g1=None
                        else:
                            g1=self._corridor_geom(f,a2,pivot)
                            ok=certified_gesture_clear(f,a2,pivot,g1,k1,t)
                        first_leg_cache[pkey]=(ok,g1)
                    else:
                        ok,g1=cached
                    if not ok: continue
                    k2=('second',round(a2[0],5),round(a2[1],5),round(pivot[0],5),round(pivot[1],5),round(end2[0],5),round(end2[1],5))
                    if self._local_direct_failure_cert_should_skip(direct_failure_width,k2,t):
                        self.stats.setdefault('pathway_local_gap_direct_failure_cert_hit_count',0)
                        self.stats['pathway_local_gap_direct_failure_cert_hit_count']+=1
                        continue
                    tf=dict(f); tf['path']=[a2,pivot]; tf['dir']=d; tf['gestures']=1; tf['local_gestures']=1
                    tf['straight_since_turn']=max(3,int(f.get('straight_since_turn',3)))
                    g2=self._corridor_geom(tf,pivot,end2)
                    if not certified_gesture_clear(tf,pivot,end2,g2,k2,t,extra_segments=(g1,)):
                        continue
                    # ``coarse`` is already sorted by exactly the same (score, tie) key used
                    # below.  The first exact-valid plan is therefore the eventual winner; any
                    # later exact checks can only confirm lower-ranked alternatives that will be
                    # discarded.  Stop here without removing a selectable plan.
                    bend_plans.append((cscore,_rand,pivot,d2,end2,g1,g2,dist1,m2))
                    break
                if bend_plans:
                    _bs,_rand,pivot,d2,end2,g1,g2,dist1,m2=bend_plans[0]
                    p1=dict(front=f['id'],start=a2,end=pivot,dir=d,modules=max(2,int(round(dist1/self.module))),geom=g1,score=0.0)
                    p2=dict(front=f['id'],start=pivot,end=end2,dir=d2,modules=m2,geom=g2,score=0.0)
                    begin_debt_capture()
                    self._accept(f,p1,defer_post=True)
                    self._accept(f,p2,defer_post=True)
                    # Give the cheap tail one to three normal exploratory continuations.  The
                    # local scoring profile now wants another turn after its cooldown when room
                    # permits, so large spaces often become 2-3-bend paths rather than L-shapes.
                    f['target']=self._local_gap_target(end2,f['rng'],d2,
                        cluster_id=f.get('local_fill_cluster_id'))
                    extra_steps=1+int(rng.random()*3)
                    for _ in range(extra_steps):
                        q=self._propose(f)
                        if q is None: break
                        self._accept(f,q,defer_post=True)
                    apply_debt_capture()
                    f['status']='terminated'; f['termination_reason']='local_gap_mopup_bent'; f['lifecycle']='TERMINAL'
                    self.next_trace_id+=1; made+=1; bent_made+=1
                    self.stats['pathway_bundle_count']+=1; self.stats['pathway_local_gap_source_count']+=1
                    self.stats['pathway_local_gap_trace_count']+=1; self.stats['pathway_local_gap_independent_source_count']+=1
                    counts[r['id']]=counts.get(r['id'],0)+1
                    placed=True; break

                # Rare exception: a truly narrow room can physically admit only a straight line.
                # Do not fabricate a bend or fail the whole board for that pocket.  Straight
                # tail fillers are globally capped to ~6% of this pass and require a narrow
                # measured short span plus a seeded 35% admission probability.
                narrow=(float(r.get('short_span',0.0)) < 2.25*self.module)
                if (narrow and straight_made<straight_cap and rng.random()<.72):
                    geom=self._corridor_geom(f,a2,b2)
                    if self._gesture_clear(f,a2,b2,geom,allow_outside=False):
                        p=dict(front=f['id'],start=a2,end=b2,dir=d,modules=max(2,int(round(corridor_len/self.module))),geom=geom,score=0.0)
                        begin_debt_capture()
                        self._accept(f,p,defer_post=True)
                        apply_debt_capture()
                        f['status']='terminated'; f['termination_reason']='local_gap_mopup_narrow_straight'; f['lifecycle']='TERMINAL'
                        self.next_trace_id+=1; made+=1; straight_made+=1
                        self.stats['pathway_bundle_count']+=1; self.stats['pathway_local_gap_source_count']+=1
                        self.stats['pathway_local_gap_trace_count']+=1; self.stats['pathway_local_gap_independent_source_count']+=1
                        counts[r['id']]=counts.get(r['id'],0)+1
                        placed=True; break
                self._drop_front(f['id'])
                note_direct_run_failure(run_family_key)

            if not placed:
                if debt_priority_mode:
                    service_cells=max(1,int(self.local_gap_service_denominator_cell_count or len(self.local_gap_open_cells)))
                    remaining_debt_cells=max(0.0,(self.local_gap_target_fraction-self._local_gap_service_fraction())*service_cells)
                    if remaining_debt_cells>1.0:
                        # A failed batch proves only the attempted run families.  While more
                        # than one canonical service cell of hard-floor debt remains, keep the
                        # region live so bounded family certificates can expose independent
                        # alternatives.  This avoids a fine-scale region-retirement cliff.
                        pass
                    else:
                        # Sub-cell debt is cheaper for the tiny fallback than another family
                        # search.  Preserve the historical coarse retirement at that horizon.
                        exhausted.update(tried_regions)
                else:
                    exhausted.update(tried_regions)

        # Fragmented-room rescue: the long-run scan above can exhaust when the remaining open
        # cells no longer form a clean 3-cell axis run even though a useful two-leg maneuver still
        # fits.  Recover that service with compact doglegs only; this pass has *no* straight
        # fallback and therefore cannot undo the articulation contract.
        rescue_made=0; rescue_attempts=0
        while (made<max_lines and rescue_attempts<420 and
               self._local_gap_service_fraction()+1e-9<self.local_gap_target_fraction):
            uncovered_set=self._local_gap_targetable_cells()
            if not uncovered_set: break
            # Prefer substantial deficit regions, then draw a bounded set of geometric extremes
            # from each.  This replaces a whole-board copy+shuffle on every rescue attempt while
            # preserving the same region-size / interior-space preference and exact legality gate.
            ranked=[]
            region_order=sorted(
                ((len(self._local_gap_targetable_cells(r['id'])),r['id'],r) for r in self.local_gap_regions
                 if r['cell_count']>=3 and self._local_gap_targetable_cells(r['id'])),
                key=lambda z:(-z[0],z[1]))
            for _uc,_rid,r in region_order[:24]:
                cells=self._local_gap_extreme_shortlist(r['id'],self._local_gap_targetable_cells(r['id']),r['dir'],24)
                for c in cells:
                    center=((c[0]+.5)*cw,(c[1]+.5)*ch)
                    edge=min(center[0],center[1],self.W-center[0],self.H-center[1])
                    ranked.append((_uc+.015*edge,rng.random(),center,r))
                    if len(ranked)>=220: break
                if len(ranked)>=220: break
            ranked.sort(key=lambda z:(-z[0],z[1]))
            placed_rescue=False
            for _rank,_rand,center,r in ranked[:44]:
                rescue_attempts+=1
                t=rng.uniform(1.85,2.75)*self.U
                half=.5*t; marker_extent=self.r._termination_dot_radius(t)+.5*self.r.termination_dot_hollow_stroke
                if not self._local_gap_source_clearance(center,half,marker_extent=marker_extent,
                                                        cluster_id=r['id']): continue
                # V39 fragmented-space rescue may approach the pocket from any octilinear
                # heading, still requiring the second leg to turn exactly +/-45.  V38 only
                # tried the region's principal axis and its reverse, which became unnecessarily
                # restrictive once 90-degree connection shortcuts were removed upstream.
                base=r['dir']
                base_dirs=[base,(base+4)%8,(base-1)%8,(base+1)%8,(base+3)%8,(base+5)%8,(base-2)%8,(base+2)%8]
                # Stable seeded tie variation without losing the principal-axis preference.
                head=base_dirs[:2]; tail=base_dirs[2:]; rng.shuffle(tail); base_dirs=head+tail
                plans=[]
                for d0 in base_dirs:
                    for m1 in (2.0,2.6,3.2):
                        pivot=point_along_dir(center,d0,m1*self.module)
                        if self._gap_cell(pivot) not in r['cells']: continue
                        for sign in (-1,1):
                            d1=(d0+sign)%8
                            for m2 in (2.0,2.6,3.2,3.8):
                                end=point_along_dir(pivot,d1,m2*self.module)
                                if self._gap_cell(end) not in r['cells']: continue
                                sample_key=(center,d0,m1,sign,m2)
                                sample_cells=rescue_plan_sample_cache.get(sample_key)
                                if sample_cells is None:
                                    sample_cells=immutable_sample_cells((center,pivot,end))
                                    rescue_plan_sample_cache[sample_key]=sample_cells
                                served=len(sample_cells & uncovered_set)
                                if served<2: continue
                                plans.append((served+m1+m2,rng.random(),d0,m1,pivot,d1,m2,end))
                plans.sort(key=lambda z:(-z[0],z[1]))
                for _ps,_pr,d0,m1,pivot,d1,m2,end in plans[:5]:
                    tid=self.next_trace_id
                    synthetic_chip=len(self.chips)+200000+self.stats.get('pathway_local_gap_source_count',0)+made
                    f=self._make_front(ids=[tid],chip=synthetic_chip,side='local',side_index=synthetic_chip,
                                       path=[center],direction=d0,offsets={tid:0.0},thicknesses={tid:t},prefixes={tid:[]},
                                       rng=SplitMix64(rng.next_u64()),intent='explore',target=end,
                                       local_cluster_id=r['id'])
                    f['local_gap']=True; f['local_gap_special']=False; f['fan_pending']=False
                    f['local_gap_region_id']=r['id']; f['local_gap_branch_boost']=rng.uniform(*self.r.local_gap_branch_boost_range)
                    f['local_gap_exit_allowed']=False; f['local_gap_min_terminal_modules']=3.5
                    f['local_gap_turn_count']=0; f['local_gap_turn_due_straights']=1
                    g1=self._corridor_geom(f,center,pivot)
                    if not self._gesture_clear(f,center,pivot,g1,allow_outside=False):
                        self._drop_front(f['id']); continue
                    tf=dict(f); tf['path']=[center,pivot]; tf['dir']=d0; tf['gestures']=1; tf['local_gestures']=1; tf['straight_since_turn']=3
                    g2=self._corridor_geom(tf,pivot,end)
                    if not self._gesture_clear(tf,pivot,end,g2,allow_outside=False,extra_segments=(g1,)):
                        self._drop_front(f['id']); continue
                    p1=dict(front=f['id'],start=center,end=pivot,dir=d0,modules=max(2,int(round(m1))),geom=g1,score=0.0)
                    p2=dict(front=f['id'],start=pivot,end=end,dir=d1,modules=max(2,int(round(m2))),geom=g2,score=0.0)
                    self._accept(f,p1,defer_post=True); self._accept(f,p2,defer_post=True)
                    # One optional continuation gives the rescue enough area efficiency without
                    # turning it into another expensive search phase.
                    f['target']=self._local_gap_target(end,f['rng'],d1,
                        cluster_id=f.get('local_fill_cluster_id'))
                    q=self._propose(f)
                    if q is not None: self._accept(f,q,defer_post=True)
                    f['status']='terminated'; f['termination_reason']='local_gap_mopup_bent_rescue'; f['lifecycle']='TERMINAL'
                    self.next_trace_id+=1; made+=1; bent_made+=1; rescue_made+=1
                    self.stats['pathway_bundle_count']+=1; self.stats['pathway_local_gap_source_count']+=1
                    self.stats['pathway_local_gap_trace_count']+=1; self.stats['pathway_local_gap_independent_source_count']+=1
                    placed_rescue=True; break
                if placed_rescue: break
            if not placed_rescue: break

        self.stats.setdefault('pathway_local_gap_mopup_bent_rescue_trace_count',0)
        self.stats['pathway_local_gap_mopup_bent_rescue_trace_count']+=rescue_made

        self.stats.setdefault('pathway_local_gap_direct_run_family_attempt_count',0)
        self.stats['pathway_local_gap_direct_run_family_attempt_count']+=sum(direct_run_family_attempts.values())
        self.stats.setdefault('pathway_local_gap_direct_run_family_unique_attempted_count',0)
        self.stats['pathway_local_gap_direct_run_family_unique_attempted_count']+=len(direct_run_family_attempts)
        self.stats.setdefault('pathway_local_gap_mopup_trace_count',0)
        self.stats['pathway_local_gap_mopup_trace_count']+=made
        self.stats.setdefault('pathway_local_gap_mopup_bent_trace_count',0)
        self.stats['pathway_local_gap_mopup_bent_trace_count']+=bent_made
        self.stats.setdefault('pathway_local_gap_mopup_straight_trace_count',0)
        self.stats['pathway_local_gap_mopup_straight_trace_count']+=straight_made
        return made

    @staticmethod
    def _local_region_priority_key(item):
        """Stable numeric region ordering even when an uncovered cell has no region id."""
        count,rid=item
        return (count, -1 if rid is None else int(rid))

    def _local_gap_fragment_mopup(self,max_lines=200):
        """Efficient bounded articulated cleanup before returning to normal local waves.

        This pass deliberately stops before the dense-field diminishing-return regime.  It uses
        only the established 0/+/-45-degree local grammar and exact clearance checks.  Any
        remaining service is handled by ordinary local waves in ``run_local_after_components``.
        """
        if not self.local_gap_open_cells:
            return 0
        rng=SplitMix64(local_pathway_seed(self.sseed)^0xA24BAED4963EE407)
        nx,ny=self.r.local_gap_grid_shape(); cw=self.W/nx; ch=self.H/ny
        step=max(.55*self.module,min(cw,ch))
        attempted=set(); made=0
        # Work-budget architecture: cleanup opportunity scales with logical territory, but
        # failed dense-field searches may not grow without bound merely because the historical
        # output cap asks for more successful fragments.  One token is one candidate debt cell
        # admitted to exact source/gesture evaluation.  The hard 80% service floor remains a
        # separate correctness gate in run_local_after_components.
        candidate_work_cap=self.r.local_fragment_candidate_work_cap()
        candidate_work_tokens=0; candidate_work_exhausted=False

        def segment_stays_in_region(a,b,region):
            L=math.hypot(b[0]-a[0],b[1]-a[1])
            samples=max(2,int(math.ceil(L/max(step,1e-9))))
            for kk in range(1,samples+1):
                t=kk/samples
                q=(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t)
                if not (0<=q[0]<=self.W and 0<=q[1]<=self.H): return False
                if region is not None and self._gap_cell(q) not in region['cells']: return False
            return True

        uncovered=set(self._local_gap_targetable_cells())
        region_uncovered={}
        region_heaps={}
        for c in uncovered:
            rid=self.local_gap_region_by_cell.get(c)
            region_uncovered[rid]=region_uncovered.get(rid,0)+1
            r=self.local_gap_regions[rid] if rid is not None and rid < len(self.local_gap_regions) else None
            if r is None: dist=0.0
            else:
                x=(c[0]+.5)*cw; y=(c[1]+.5)*ch
                dist=math.hypot(x-r['center'][0],y-r['center'][1])
            heapq.heappush(region_heaps.setdefault(rid,[]),(-dist,c[0],c[1],c))

        # Exact lazy version of the historical per-line full region sort.  Priority is
        # (uncovered count, region-id ordering) and only a retired cell can change it.
        region_priority_version={rid:0 for rid in region_uncovered}
        region_priority_heap=[]
        def _region_priority_ridkey(rid):
            return -1 if rid is None else int(rid)
        def _push_region_priority(rid):
            cnt=region_uncovered.get(rid,0)
            if cnt<=0: return
            # ``sorted(..., key=(count,ridkey), reverse=True)`` => min-heap key below.
            heapq.heappush(region_priority_heap,(-cnt,-_region_priority_ridkey(rid),rid,region_priority_version[rid]))
        def _pop_valid_region_priority():
            while region_priority_heap:
                rec=heapq.heappop(region_priority_heap)
                _nc,_nr,rid,ver=rec
                if ver!=region_priority_version.get(rid,-1) or region_uncovered.get(rid,0)<=0:
                    continue
                return rec
            return None
        for _rid in region_uncovered: _push_region_priority(_rid)

        def retire(c):
            if c not in uncovered: return
            uncovered.discard(c)
            rid=self.local_gap_region_by_cell.get(c)
            if region_uncovered.get(rid,0)>0:
                region_uncovered[rid]-=1
                region_priority_version[rid]+=1
                _push_region_priority(rid)

        def mark_attempted(c):
            if c in attempted: return
            attempted.add(c); retire(c)

        def next_candidates(limit=80):
            out=[]; held_regions=[]; held_cells={}
            while len(out)<limit:
                rrec=_pop_valid_region_priority()
                if rrec is None: break
                rid=rrec[2]; held_regions.append(rrec)
                h=region_heaps.get(rid,[]); tmp=[]
                while h and len(out)<limit:
                    item=heapq.heappop(h); c=item[-1]
                    if c not in uncovered or c in attempted: continue
                    out.append(c); tmp.append(item)
                if tmp: held_cells[rid]=tmp
            for rec in held_regions: heapq.heappush(region_priority_heap,rec)
            for rid,items in held_cells.items():
                for item in items: heapq.heappush(region_heaps[rid],item)
            return out

        while (made<max_lines and not candidate_work_exhausted and
               self._local_gap_service_fraction()+1e-9<self.local_gap_target_fraction):
            if not uncovered: break
            remaining_tokens=candidate_work_cap-candidate_work_tokens
            if remaining_tokens<=0: break
            candidates=next_candidates(min(80,remaining_tokens))
            if not candidates: break
            placed=False
            for cell in candidates:
                if candidate_work_tokens>=candidate_work_cap:
                    candidate_work_exhausted=True; break
                candidate_work_tokens+=1
                gx,gy=cell; rid=self.local_gap_region_by_cell.get(cell)
                region=self.local_gap_regions[rid] if rid is not None and rid < len(self.local_gap_regions) else None
                center=((gx+.5)*cw,(gy+.5)*ch)
                t=rng.uniform(1.85,2.85)*self.U
                marker_extent=self.r._termination_dot_radius(t)+.5*self.r.termination_dot_hollow_stroke
                if not self._local_gap_source_clearance(center,.5*t,marker_extent=marker_extent,
                                                        cluster_id=rid):
                    mark_attempted(cell); continue
                base=region['dir'] if region is not None else int(rng.random()*8)
                starts=[base,(base+4)%8,(base+1)%8,(base-1)%8]; rng.shuffle(starts)
                for d0 in starts:
                    tid=self.next_trace_id
                    synthetic_chip=len(self.chips)+300000+self.stats.get('pathway_local_gap_source_count',0)+made
                    f=self._make_front(ids=[tid],chip=synthetic_chip,side='local',side_index=synthetic_chip,
                                       path=[center],direction=d0,offsets={tid:0.0},thicknesses={tid:t},prefixes={tid:[]},
                                       rng=SplitMix64(rng.next_u64()),intent='explore',target=None,
                                       local_cluster_id=rid)
                    f['local_gap']=True; f['local_gap_special']=False; f['fan_pending']=False
                    f['local_gap_region_id']=rid; f['local_gap_branch_boost']=rng.uniform(*self.r.local_gap_branch_boost_range)
                    f['local_gap_exit_allowed']=False; f['local_gap_min_terminal_modules']=3.0
                    cur=center; curdir=d0; geoms=[]; segments=[]; turns=0; straight_run=0; total_len=0.0
                    for gesture in range(6):
                        if gesture==0: dir_opts=[curdir]
                        else:
                            signs=[-1,1]; rng.shuffle(signs)
                            dir_opts=[(curdir+signs[0])%8,curdir,(curdir+signs[1])%8] if straight_run>=1 else [curdir,(curdir+signs[0])%8,(curdir+signs[1])%8]
                        # All legality candidates in one gesture share exactly the same committed
                        # temporary history.  Materialize that tiny front/history snapshot once
                        # instead of rebuilding it for every direction×length probe.
                        tf=dict(f); tf['path']=[center]+[seg[1] for seg in segments]
                        tf['dir']=curdir; tf['gestures']=len(segments); tf['local_gestures']=len(segments)
                        extra_geoms=tuple(geoms)
                        chosen=None
                        for dd in dir_opts:
                            if ((dd-curdir+4)%8)-4 not in (-1,0,1): continue
                            lengths=(9,7,5,4) if gesture<3 else (7,5,4,3)
                            for cells_long in lengths:
                                L=cells_long*step; end=point_along_dir(cur,dd,L)
                                if not segment_stays_in_region(cur,end,region): continue
                                geom=self._corridor_geom(tf,cur,end)
                                if not self._gesture_clear(tf,cur,end,geom,allow_outside=False,extra_segments=extra_geoms): continue
                                chosen=(dd,end,geom,L); break
                            if chosen is not None: break
                        if chosen is None: break
                        dd,end,geom,L=chosen
                        if dd!=curdir: turns+=1; straight_run=0
                        else: straight_run+=1
                        segments.append((cur,end,dd,geom,L)); geoms.append(geom)
                        cur=end; curdir=dd; total_len+=L
                    if turns<1 or len(segments)<2 or total_len<8.0*step:
                        self._drop_front(f['id']); continue
                    # Capture only cells that this one accepted fragment touches for the first
                    # time.  V43 copied the entire board-wide touched set before every fragment
                    # and subtracted it afterwards; at fine scale that becomes quadratic in
                    # service-grid area.  The rasterizer already knows the exact first-touch
                    # event, so collect it directly.
                    self._local_gap_new_touch_capture=set()
                    try:
                        f['path']=[center]; f['dir']=d0; f['gestures']=0; f['local_gestures']=0; f['travel']=0.0
                        for a,b,dd,geom,L in segments:
                            pr=dict(front=f['id'],start=a,end=b,dir=dd,modules=max(1,int(round(L/max(self.module,1e-9)))),geom=geom,score=0.0)
                            self._accept(f,pr,defer_post=True)
                        newly=set(self._local_gap_new_touch_capture)
                    finally:
                        self._local_gap_new_touch_capture=None
                    f['status']='terminated'; f['termination_reason']='local_gap_fragment_mopup_bent'; f['lifecycle']='TERMINAL'
                    self.next_trace_id+=1; made+=1
                    self.stats['pathway_bundle_count']+=1; self.stats['pathway_local_gap_source_count']+=1
                    self.stats['pathway_local_gap_trace_count']+=1; self.stats['pathway_local_gap_independent_source_count']+=1
                    for c in newly: retire(c)
                    placed=True; break
                if placed: break
                mark_attempted(cell)
            if not placed: continue
        self.stats.setdefault('pathway_local_gap_fragment_mopup_trace_count',0)
        self.stats['pathway_local_gap_fragment_mopup_trace_count']+=made
        self.stats.setdefault('pathway_local_gap_fragment_candidate_work_token_count',0)
        self.stats['pathway_local_gap_fragment_candidate_work_token_count']+=candidate_work_tokens
        self.stats.setdefault('pathway_local_gap_fragment_candidate_work_cap_hit_count',0)
        if candidate_work_exhausted or candidate_work_tokens>=candidate_work_cap:
            self.stats['pathway_local_gap_fragment_candidate_work_cap_hit_count']+=1
        self.stats['pathway_local_gap_fragment_candidate_work_cap']=candidate_work_cap
        return made

    def _run_local_gap_fast_rounds(self,round_budget=20):
        """Lightweight synchronous growth for the post-main residual filler network.

        Main-chip routing needs causal history, protected egress, cross-chip connection search and
        transactional rollback.  Residual fillers do not: they are independent singleton traces
        operating after the main network is frozen.  This loop preserves the important semantics
        (one immutable committed snapshot per tick, exact geometry, HOLD instead of same-round
        killing, 0/±45 turns, local capacity targets, one-time temporary bundling) without paying
        the main router's expensive causal/permutation machinery on dozens of filler fronts.
        """
        rounds=0
        wave_abandoned=set()
        for round_index in range(max(1,int(round_budget))):
            active=[f for f in self.fronts.values() if f.get('local_gap') and f.get('status')=='active']
            if not active: break
            if (not getattr(self,'_local_gap_capacity_realizing',False) and
                    self._local_gap_service_fraction()+1e-9 >= self.local_gap_target_fraction): break
            rounds+=1
            newly_abandoned=[]
            for f in active:
                f['_routing_round']=round_index
                # No main-network recovery state is carried into the local lightweight loop.
                f['quality_repair_pending']=False; f['quality_repair_reason']=None
                f['reroute_pending']=False
            self._assign_local_bundle_affinities(active,round_index)
            self._refresh_active_head_snapshot(active)

            variant_map={}; blocked=[]
            for f in sorted(active,key=lambda x:x['id']):
                # One exact candidate is enough for ordinary motion; a held/blocked filler gets
                # a fresh seeded choice next tick after its target/avoid direction is adjusted.
                proposals=[]; seen=set()
                tries=2 if (f.get('local_hold_streak',0)>0 or f.get('local_fast_blocked_rounds',0)>0) else 1
                for _ in range(tries):
                    p=self._propose(f)
                    if p is None: continue
                    key=(p['dir'],p['modules'],round(p['end'][0],4),round(p['end'][1],4))
                    if key in seen: continue
                    seen.add(key); p=dict(p); p['future_geom']=p['geom']; p['priority']=p.get('score',0.0)
                    proposals.append(p)
                if not proposals:
                    blocked.append(f); continue
                variant_map[f['id']]=proposals

            chosen={}; grouped=set()
            for group in self._conflict_groups(variant_map):
                grouped.update(group)
                sol=self._solve_conflict_group(group,variant_map)
                if sol:
                    chosen.update({p['front']:p for p in sol})
            for fid,pool in variant_map.items():
                if fid not in grouped and pool: chosen[fid]=pool[0]

            # Atomic local commit: no selected proposal exists in path_index until every local
            # peer has proposed from the same pre-round geometry.
            selected=[p for fid,p in sorted(chosen.items())
                      if self.fronts[fid].get('status')=='active']
            for p in selected:
                self._accept(self.fronts[p['front']],p,defer_post=True)
            if selected:
                self.stats['pathway_atomic_round_commit_count']+=1
            moved={p['front'] for p in selected}
            for p in selected:
                f=self.fronts[p['front']]
                f['failures']=0; f['local_fast_blocked_rounds']=0
                if f.get('reroute_mode_rounds',0)>0:
                    f['reroute_mode_rounds']=max(0,f['reroute_mode_rounds']-1)
                x,y=p['end']
                if x<0 or y<0 or x>self.W or y>self.H:
                    f['status']='escaped'; f['lifecycle']='TERMINAL'
                    self.stats['pathway_escape_count']+=1
                    self.stats['pathway_escape_trace_count']+=len(f.get('ids',()))

            # BLOCK/HOLD is not death.  Re-aim at unmet local space and suppress the just-failed
            # heading for two ticks.  Only after several genuinely distinct failed ticks may an
            # already-useful local filler terminate.
            held=[f for f in active if f['id'] not in moved and f.get('status')=='active']
            for f in held:
                f['local_fast_blocked_rounds']=int(f.get('local_fast_blocked_rounds',0))+1
                f['failures']=f['local_fast_blocked_rounds']
                if f['local_fast_blocked_rounds']>=2:
                    f['reroute_mode_rounds']=2
                    f['reroute_avoid_dir']=f['dir']
                    f['target']=self._local_gap_target(f['path'][-1],f['rng'],f['dir'],
                        cluster_id=f.get('local_fill_cluster_id'))
                if f['local_fast_blocked_rounds']>=5:
                    if self._minimum_materialized_lane_length(f)+1e-9>=float(f.get('local_gap_min_terminal_modules',3.5))*self.module:
                        f['status']='terminated'; f['termination_reason']='local_gap_fast_blocked'; f['lifecycle']='TERMINAL'
                    else:
                        f['status']='abandoned_short'; f['termination_reason']='local_gap_fast_blocked'; f['lifecycle']='TERMINAL'; newly_abandoned.append(f['id'])

            # Region-scaled journey limits; large rooms already received longer budgets at spawn.
            for f in active:
                if f.get('status')=='active' and f.get('gestures',0)>=f.get('max_gestures',12):
                    if self._minimum_materialized_lane_length(f)+1e-9>=float(f.get('local_gap_min_terminal_modules',3.5))*self.module:
                        f['status']='terminated'; f['termination_reason']='local_gap_region_limit'; f['lifecycle']='TERMINAL'
                    else:
                        # A short line in a large room gets one last pivot window, not immediate death.
                        if not f.get('local_fast_limit_extension'):
                            f['local_fast_limit_extension']=True
                            f['max_gestures']=f.get('gestures',0)+4
                            f['reroute_mode_rounds']=2; f['reroute_avoid_dir']=f['dir']
                            f['target']=self._local_gap_target(f['path'][-1],f['rng'],f['dir'],
                                cluster_id=f.get('local_fill_cluster_id'))
                        else:
                            f['status']='abandoned_short'; f['termination_reason']='local_gap_region_limit'; f['lifecycle']='TERMINAL'; newly_abandoned.append(f['id'])

            # Keep abandoned geometry only until this synchronized wave ends.  Rebuilding the
            # spatial/coverage indices on every tick is disproportionately expensive once the
            # board is dense.  These provisional corpses may conservatively block peers for the
            # remainder of the current wave, but are removed in one batch before the next wave
            # and therefore can never count toward final service or obstruct later allocation.
            wave_abandoned.update(newly_abandoned)

            # Make the advertised 3–5x local branching real, but keep it capacity-bounded.  At
            # most two singleton branches are born in one tick and no line branches twice.
            if (getattr(self,'_local_gap_capacity_realizing',False) or
                    self._local_gap_service_fraction()+1e-9 < self.local_gap_target_fraction):
                branchable=[f for f in active if f.get('status')=='active' and f.get('gestures',0)>=2 and
                            not f.get('local_gap_special') and f.get('local_gap_branch_count',0)<1]
                branchable.sort(key=lambda f:(-self._local_space_capacity(f,f['path'][-1],f['dir']),f['id']))
                made=0; branch_tick_cap=self.r.local_branch_birth_cap()
                for f in branchable:
                    if made>=branch_tick_cap or self._local_gap_realized_trace_count()>=self.r.local_gap_trace_population_cap(): break
                    boost=float(f.get('local_gap_branch_boost',4.0))
                    if f['rng'].random() < min(.28,.055*boost):
                        if self._branch_local_singleton(f): made+=1
        # Bound each wave as a self-contained visual operation.  Do not carry a large crowd
        # of unresolved fillers into the next region-allocation wave; useful lines terminate,
        # unusably short lines are pruned and cannot count as service/obstacles.
        abandoned=[]
        for f in [x for x in self.fronts.values() if x.get('local_gap') and x.get('status')=='active']:
            if self._minimum_materialized_lane_length(f)+1e-9>=float(f.get('local_gap_min_terminal_modules',3.5))*self.module:
                f['status']='terminated'; f['termination_reason']='local_gap_wave_limit'; f['lifecycle']='TERMINAL'
            else:
                f['status']='abandoned_short'; f['termination_reason']='local_gap_wave_limit'; f['lifecycle']='TERMINAL'; abandoned.append(f['id'])
        wave_abandoned.update(abandoned)
        if wave_abandoned:
            self._prune_abandoned_local_segments(wave_abandoned)
        self.stats.setdefault('pathway_local_gap_fast_round_count',0)
        self.stats['pathway_local_gap_fast_round_count']+=rounds
        return rounds

    def _persistence_materialized_paths(self,f):
        cache=self._persistence_materialized_cache
        if cache is None:
            return self._materialized_paths(f)
        fid=f['id']; paths=cache.get(fid)
        if paths is None:
            paths=self._materialized_paths(f); cache[fid]=paths
        return paths

    def _persistence_debt_batch(self,active):
        """Return late work debt, including the soft six-module quality preference.

        The shared persistence clock is a work scheduler, not a validity oracle.  Routes between
        the hard four-module survival floor and the preferred six-module journey still receive
        ordinary opportunities here, but failure to reach six cannot by itself reject a seed.
        """
        previous=self._persistence_materialized_cache
        self._persistence_materialized_cache={}
        try:
            return [f for f in active if self._persistence_work_debt(f)]
        finally:
            self._persistence_materialized_cache=previous

    def _persistence_work_debt(self,f):
        """Whether a live main front still deserves late routing work."""
        if f.get('status')!='active' or f.get('local_gap') or f.get('chip',len(self.chips))>=len(self.chips):
            return False
        min_lane=self._minimum_materialized_lane_length(f)
        if self._main_side_progress_debt(f):
            return True
        if min_lane < self.main_launch_preferred_terminal_modules*self.module-1e-7:
            return True
        if self._source_egress_pending(f) or f.get('fan_pending') or f.get('fragment_pending'):
            return True
        if f.get('branch_stage') is not None:
            return True
        if self._fragment_singleton_still_embedded(f):
            return True
        if self._singleton_between_live_siblings(f):
            return True
        return False

    def _persistence_hard_debt(self,f):
        """Whether a live main front still owes *validity* completion debt.

        Four visible modules is the launch-survival floor.  Six modules remains a preferred
        journey and is intentionally handled by _persistence_work_debt(), not by this rejection
        predicate.  Recovery/reroute bookkeeping by itself is not hard debt once geometry is
        mature.
        """
        if f.get('status')!='active' or f.get('local_gap') or f.get('chip',len(self.chips))>=len(self.chips):
            return False
        min_lane=self._minimum_materialized_lane_length(f)
        if self._main_side_progress_debt(f):
            return True
        if min_lane < self.main_launch_maturity_modules*self.module-1e-7:
            return True
        if self._source_egress_pending(f) or f.get('fan_pending') or f.get('fragment_pending'):
            return True
        if f.get('branch_stage') is not None:
            return True
        if self._fragment_singleton_still_embedded(f):
            return True
        if self._singleton_between_live_siblings(f):
            return True
        return False

    def _assign_persistence_connection_targets(self,active,debt,round_index):
        """Refresh compatible MAIN-family connection targets while scoring only pairs touching hard debt.

        Every live head remains visible in the shared snapshot, but mature unrelated families do
        not re-enter the expensive late proposal campaign.  A mature head can still become the
        peer of a debt front and participate in that one tick's atomic transaction.
        """
        for f in active:
            f['round_connection_peer']=None; f['round_connection_target']=None
        self._refresh_active_head_snapshot(active)
        debt_ids={f['id'] for f in debt}
        eligible={f['id']:f for f in active if f.get('gestures',0)>=1 and f.get('branch_stage')!=0 and
                  not f.get('local_gap') and not self._source_egress_pending(f)}
        candidates=[]; seen=set(); max_global=18.0*self.module
        for a in sorted((f for f in debt if f['id'] in eligible),key=lambda x:x['id']):
            pa=a['path'][-1]
            nearby=self._active_head_index.query((pa[0]-max_global,pa[1]-max_global,pa[0]+max_global,pa[1]+max_global))
            for b in nearby:
                if b['id']==a['id'] or b['id'] not in eligible or not self._connection_family_compatible(a,b):
                    continue
                pair=tuple(sorted((a['id'],b['id'])))
                if pair in seen: continue
                seen.add(pair)
                pb=b['path'][-1]; d=math.hypot(pb[0]-pa[0],pb[1]-pa[1])
                desire=(a['intent']=='connect')+(b['intent']=='connect')
                max_d=(18.0 if desire else 13.0)*self.module
                if d<.55*self.module or d>max_d: continue
                narrow_bonus=.45*(1.0/min(len(a['ids']),4)+1.0/min(len(b['ids']),4))
                cross_chip=(a['chip']!=b['chip'])
                candidates.append((d/self.module-1.35*desire-narrow_bonus-(4.0 if cross_chip else 0.0),
                                   a,b,d,desire,cross_chip))
        candidates.sort(key=lambda x:(x[0],x[1]['id'],x[2]['id']))
        used=set(); paired=0
        for _,a,b,d,desire,cross_chip in candidates:
            if a['id'] in used or b['id'] in used: continue
            prng=SplitMix64(mix_once(self.sseed ^ 0xA24BAED4963EE407 ^
                                     ((round_index+1)*0x9E3779B97F4A7C15) ^
                                     ((a['id']+1)<<17) ^ ((b['id']+1)<<41)))
            pa,pb=a['path'][-1],b['path'][-1]
            va=dir_vec(a['dir']); vb=dir_vec(b['dir']); ux=(pb[0]-pa[0])/max(d,1e-9); uy=(pb[1]-pa[1])/max(d,1e-9)
            facing=(va[0]*ux+va[1]*uy>.18 and vb[0]*(-ux)+vb[1]*(-uy)>.18)
            young_close=(facing and d<=5.0*self.module and
                         (a.get('travel',0.0)<4.0*self.module or b.get('travel',0.0)<4.0*self.module or
                          self._refresh_lifecycle(a) in ('LAUNCHING','RECOVERING') or
                          self._refresh_lifecycle(b) in ('LAUNCHING','RECOVERING')))
            forced_close=(d<=3.0*self.module and facing) or young_close
            chance=1.0 if (forced_close or cross_chip) else min(.995,.78*self.profile['connection_appetite']+.10*desire)
            if not cross_chip and prng.random()>=chance: continue
            meet=((pa[0]+pb[0])*.5,(pa[1]+pb[1])*.5)
            a['round_connection_peer']=b['id']; b['round_connection_peer']=a['id']
            a['round_connection_target']=meet; b['round_connection_target']=meet
            used.update((a['id'],b['id'])); paired+=1
        if paired:
            self.stats['pathway_holistic_connection_pair_count']+=paired
            self.stats['pathway_holistic_connection_guided_round_count']+=1
        return paired

    def _run_rounds(self):
        soft_rounds=self.profile['max_rounds']
        shared_ticks=int(self.profile.get('persistence_shared_ticks',0))
        hard_rounds=soft_rounds+shared_ticks
        round_index=-1
        for round_index in range(hard_rounds):
            self._in_shared_persistence=(round_index>=soft_rounds)
            active=[f for f in self.fronts.values() if f['status']=='active']
            if not active:
                break
            if self._in_shared_persistence:
                debt=self._persistence_debt_batch(active); debt_ids={f['id'] for f in debt}
                self.stats['pathway_persistence_hard_debt_peak']=max(
                    self.stats.get('pathway_persistence_hard_debt_peak',0),sum(len(f.get('ids',())) for f in debt))
                if not debt:
                    break
                self.stats['pathway_persistence_shared_tick_count']+=1
            pending=[f for f in active if f.get('fragment_pending')]
            for f in sorted(pending,key=lambda x:x['id']):
                f['fragment_pending']=False
                self._fragment_bundled_front(f)
            if pending:
                active=[f for f in self.fronts.values() if f['status']=='active']
                if self._in_shared_persistence:
                    debt=self._persistence_debt_batch(active); debt_ids={f['id'] for f in debt}
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
                    if self._persistence_work_debt(f) and len(f.get('ids',()))>1:
                        if f.get('local_gap'):
                            f['intent']='explore'
                            f['target']=self._local_gap_target(f['path'][-1],f['rng'],f['dir'],
                                cluster_id=f.get('local_fill_cluster_id'))
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
                if (f['status']=='active' and self._launch_fan_ready(f) and
                        (not self._in_shared_persistence or f['id'] in debt_ids)):
                    self._fan_front(f)

            # V33 TRANSACTIONAL ROUND PREPARATION.
            # First apply every ready rollback before anybody proposes.  V30 performed traceback
            # inside the per-front proposal loop, so a lower-id front could still see geometry
            # that a higher-id blocker removed later in the same round.  That was not one shared
            # snapshot.  All recovery is now a pre-transaction state transition.
            active=[f for f in self.fronts.values() if f['status']=='active']
            if self._in_shared_persistence:
                debt=self._persistence_debt_batch(active); debt_ids={f['id'] for f in debt}
            for f in sorted(active,key=lambda x:x['id']):
                if (f.get('quality_repair_pending') and not f.get('reroute_pending') and
                        (not self._in_shared_persistence or f['id'] in debt_ids)):
                    self._schedule_reroute(f,round_index,f.get('quality_repair_reason') or 'stagnation')
            ready_reroutes=[]
            rebuild_local_coverage=False
            for f in sorted(active,key=lambda x:x['id']):
                if f.get('reroute_pending') and round_index >= (f.get('reroute_ready_round') or 0):
                    f['_routing_round']=round_index
                    ready_reroutes.append(f)
                    rebuild_local_coverage = rebuild_local_coverage or bool(f.get('local_gap'))
                    self._traceback_for_reroute(f,defer_rebuild=True)
            if ready_reroutes:
                # Exact incremental main rollback: each owned tail has already been removed from
                # live spatial/coverage/congestion state. Keep the authoritative rebuild fallback
                # only for local-gap state, which this main loop does not normally carry.
                if rebuild_local_coverage:
                    self._rebuild_path_index_and_coverage(rebuild_local_coverage=True)
                    if self._in_shared_persistence:
                        self.stats['pathway_persistence_shared_rebuild_count']+=1
                else:
                    self.stats.setdefault('pathway_incremental_rollback_batch_count',0)
                    self.stats['pathway_incremental_rollback_batch_count']+=1

            # Connection opportunities and structural decisions are now computed from the same
            # revised pre-move board.  Branching may change topology, so movement takes a fresh
            # immutable snapshot after structural transitions finish.
            active=[f for f in self.fronts.values() if f['status']=='active']
            if self._in_shared_persistence:
                debt=self._persistence_debt_batch(active); debt_ids={f['id'] for f in debt}
                self._assign_persistence_connection_targets(active,debt,round_index)
            else:
                self._assign_round_connection_targets(active,round_index)
            for f in sorted(active,key=lambda x:x['id']):
                if (f['status']=='active' and (not self._in_shared_persistence or f['id'] in debt_ids)
                        and self._should_branch(f)):
                    self._branch_front(f)

            active=[f for f in self.fronts.values() if f['status']=='active']
            if self._in_shared_persistence:
                debt=self._persistence_debt_batch(active); debt_ids={f['id'] for f in debt}
                self._assign_persistence_connection_targets(active,debt,round_index)
                active=[f for f in active if f['id'] in debt_ids or f.get('round_connection_peer') is not None]
            else:
                self._assign_round_connection_targets(active,round_index)
                self._assign_local_bundle_affinities(active,round_index)
                self._refresh_active_head_snapshot(active)
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
                if self._launch_fan_ready(f):
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
                            if self._in_shared_persistence and f['id'] in debt_ids:
                                # Shared late clock: hard debt may HOLD, but it may not horizon-kill.
                                f['max_gestures']=max(f['max_gestures'],f['gestures']+2)
                                f['failures']=0
                                continue
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
        self._in_shared_persistence=False
        self._compact_retired_path_records()
        # A still-intact main-side family is not allowed to become a coordinated four-module
        # corpse merely because its coarse fan permutation failed. Settle it at real-lane level.
        self._settle_stalled_main_families(round_index,rounds=6)
        # V47 bounded horizon cleanup.  The shared clock does the real routing work; this pass is
        # only for the small residue of structural/embedded debt and uses ordinary exact gestures.
        self._settle_structural_persistence_debt_atomic(round_index+1,rounds=2)
        for f in sorted(self.fronts.values(),key=lambda x:x['id']):
            if f.get('status')!='active' or f.get('local_gap'):
                continue
            if (f.get('status')=='active' and len(f.get('ids',()))==1 and
                    (self._fragment_singleton_still_embedded(f) or self._singleton_between_live_siblings(f))):
                self._try_embedded_singleton_separation(f,max_steps=3)
        for f in sorted(self.fronts.values(),key=lambda x:x['id']):
            if f['status']=='active':
                # Restore the general final escape opportunities removed by the V45 performance
                # shortcut. These are bounded local exact checks, not another routing campaign.
                if self._try_final_escape(f):
                    continue
                if ((f.get('travel',0.0)<5.0*self.module or
                     self._refresh_lifecycle(f) in ('LAUNCHING','RECOVERING')) and
                        self._try_bounded_escape_beam(f)):
                    continue
                min_lane=self._minimum_materialized_lane_length(f)
                if not f.get('local_gap') and min_lane<self.main_launch_preferred_terminal_modules*self.module-1e-7:
                    # Six modules is preferred visible work, not validity.  Give the residue one
                    # bounded exact opportunity to reach that quality target; if it cannot, only
                    # a route still below the true four-module survival floor is hard unresolved.
                    if self._try_young_survival_beam(
                            f,target_modules=self.main_launch_preferred_terminal_modules,horizon=4,beam_width=12):
                        min_lane=self._minimum_materialized_lane_length(f)
                    if min_lane<self.main_launch_maturity_modules*self.module-1e-7:
                        f['protected_launch_unresolved']=True
                        continue
                if len(f.get('ids',()))==1 and (self._fragment_singleton_still_embedded(f) or self._singleton_between_live_siblings(f)):
                    if not self._try_embedded_singleton_separation(f,max_steps=2):
                        f['protected_launch_unresolved']=True
                        continue
                if 2<=len(f.get('ids',()))<=3 and self._try_terminal_separation(f):
                    continue
                if f.get('fan_pending') and not f.get('local_gap'):
                    # An intact source-side family gets one bounded lane-level settlement pass
                    # below. Mature already-fanned routes may terminate locally immediately.
                    continue
                self._terminate_front(f,'round_limit')
        # A root launch may have been valid earlier and then rewound below the hard floor by
        # legitimate causal recovery.  Its source-egress corridor remains continuously reserved;
        # constructively restore that local obligation before final topology settlement.
        self._settle_final_source_egress_totality()
        # Some intact buses only reached the egress boundary during the final survival beam.
        # They must now actually fan/fragment and explore; egress clearance is not success.
        self._settle_stalled_main_families(round_index+1,rounds=8)
        # After all exact fan/fragment/branch settlement opportunities are exhausted, future-only
        # topology intent is not validity debt for an already-mature visible route.
        self._settle_exhausted_mature_structural_intents()
        # Fixed persistence ticks may schedule work, but they may not decide validity.  Only now,
        # after every historical bounded cleanup has run, settle the true mature relational
        # residue by exact shared-snapshot progress until it clears or is genuinely exhausted.
        self._settle_final_relational_persistence_progress(round_index+10)
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
            # Fragment embedding is a cohort-relative debt: siblings that are each mature but
            # still physically adjacent must be judged together.  Sequential evaluation makes
            # every member see the others as continuing blockers and can leave a false horizon
            # debt forever.  Commit the whole fragment terminal cohort or none of it.
            coordinated=self._coordinated_fragment_terminal_group_safe(fs,allow_exhausted_embedding=True)
            if coordinated:
                exhausted=sum(len(f.get('ids',())) for f in fs if f.get('protected_launch_unresolved') and
                              (self._fragment_singleton_still_embedded(f) or self._singleton_between_live_siblings(f)))
                if exhausted:
                    self.stats.setdefault('pathway_exhausted_embedded_terminal_trace_count',0)
                    self.stats['pathway_exhausted_embedded_terminal_trace_count']+=exhausted
                for f in fs:
                    f['status']='terminated'; f['termination_reason']='coordinated_persistence_limit'
                    handled.add(f['id'])
                    self.stats['pathway_coordinated_persistence_terminal_trace_count']+=len(f['ids'])
                self.stats.setdefault('pathway_coordinated_fragment_terminal_group_count',0)
                self.stats['pathway_coordinated_fragment_terminal_group_count']+=1
                continue
            for f in fs:
                if not f.get('local_gap') and self._persistence_hard_debt(f):
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
            # Finalization is atomic at the visual cohort level.  The historical per-front
            # loop evaluated every lane while all siblings were still live, so two adjacent
            # mature endings could each be falsely classified as a singular middle-lane dot.
            # Only the nearest-neighbour-safe cohort transaction may bypass that one debt bit;
            # every other hard maturity/egress/structural/fragment obligation remains hard.
            coordinated=self._coordinated_root_terminal_group_safe(fs,allow_exhausted_embedding=True)
            if coordinated:
                exhausted=sum(len(f.get('ids',())) for f in fs if f.get('protected_launch_unresolved') and
                              (self._fragment_singleton_still_embedded(f) or self._singleton_between_live_siblings(f)))
                if exhausted:
                    self.stats.setdefault('pathway_exhausted_embedded_terminal_trace_count',0)
                    self.stats['pathway_exhausted_embedded_terminal_trace_count']+=exhausted
                for f in fs:
                    f['status']='terminated'; f['termination_reason']='coordinated_persistence_limit'
                    self.stats['pathway_coordinated_persistence_terminal_trace_count']+=len(f['ids'])
                    handled.add(f['id'])
                self.stats.setdefault('pathway_coordinated_root_terminal_group_count',0)
                self.stats['pathway_coordinated_root_terminal_group_count']+=1
                continue
            for f in fs:
                if not f.get('local_gap') and self._persistence_hard_debt(f):
                    f['protected_launch_unresolved']=True
                    continue
                f['status']='terminated'; f['termination_reason']='coordinated_persistence_limit'
                self.stats['pathway_coordinated_persistence_terminal_trace_count']+=len(f['ids'])
        unresolved=[f for f in self.fronts.values() if f.get('status')=='active' and
                    (f.get('protected_launch_unresolved') or self._persistence_hard_debt(f))]
        self.stats['pathway_protected_launch_unresolved_count']=sum(len(f.get('ids',())) for f in unresolved)
        self.stats['pathway_persistence_horizon_unresolved_trace_count']=self.stats['pathway_protected_launch_unresolved_count']
        if unresolved:
            reason_counts={}
            for f in unresolved:
                for reason in self._persistence_hard_debt_reasons(f):
                    reason_counts[reason]=reason_counts.get(reason,0)+len(f.get('ids',()))
            raise RuntimeError(
                'MAIN persistence horizon unresolved '
                f'(sample_seed={self.sseed}, aspect_ratio={self.r.aspect_ratio[0]:g}:{self.r.aspect_ratio[1]:g}, '
                f'scale={self.r.scale:g}, reasons={reason_counts}, '
                f'front_ids={[f["id"] for f in unresolved[:12]]})')
        # Last-chance arbitration occurs before terminal dots exist.  If two free foreign
        # heads finish close enough for a collision-clean head-to-head join, connecting them
        # is mandatory; rendering two terminal dots staring at one another is never preferred.
        self._connect_forced_close_lane_heads(include_terminated=True)

    def _settle_final_source_egress_totality(self):
        """Constructively restore every root MAIN launch to the hard four-module floor.

        Early turns are legal.  A root that once matured owns its exact first mature bent prefix
        as the replay certificate.  A root that never matured still owns the original straight
        emergence reservation; any partial under-floor bend is first rewound to emergence before
        that fallback is consumed.  No seed retry, board restart, or clearance relaxation exists.
        """
        moved=0
        for f in sorted(self.fronts.values(),key=lambda x:x['id']):
            if (f.get('status')!='active' or f.get('local_gap') or f.get('parent') is not None or
                    f.get('chip',len(self.chips))>=len(self.chips) or not self._source_egress_pending(f)):
                continue
            f['reroute_pending']=False; f['reroute_ready_round']=None
            f['quality_repair_pending']=False; f['quality_repair_reason']=None
            f['failures']=0; f['protected_launch_unresolved']=False
            owner=self._launch_family_key(f)
            self._reactivate_source_egress(owner)
            saved_prefix=[tuple(x) for x in f.get('launch_survival_prefix_path',())]

            # A never-mature partial bend has no protected bent certificate; replay must begin
            # from emergence.  A previously-mature route may continue in place only when its
            # surviving centerline is still an exact prefix of the captured certificate.
            aligned=False
            if saved_prefix and len(f.get('path',()))<=len(saved_prefix):
                aligned=all(math.hypot(a[0]-b[0],a[1]-b[1])<=1e-7
                            for a,b in zip(f.get('path',()),saved_prefix[:len(f.get('path',()))]))
            if (not saved_prefix and len(f.get('path',()))>1) or (saved_prefix and not aligned):
                self._rewind_root_to_emergence_for_source_egress(f)

            guard=0
            while self._source_egress_pending(f):
                guard+=1
                if guard>12:
                    raise RuntimeError(f'final source-egress constructive settlement invariant failed (sample_seed={self.sseed}, front={f["id"]})')
                start_pt=f['path'][-1]
                if saved_prefix:
                    idx=len(f['path'])
                    if idx>=len(saved_prefix):
                        raise RuntimeError(f'final source-egress replay prefix exhausted (sample_seed={self.sseed}, front={f["id"]})')
                    end_pt=saved_prefix[idx]
                    d=exact_dir8_index(end_pt[0]-start_pt[0],end_pt[1]-start_pt[1])
                    if d is None:
                        raise RuntimeError(f'final source-egress replay non-octilinear prefix (sample_seed={self.sseed}, front={f["id"]})')
                    modules=math.hypot(end_pt[0]-start_pt[0],end_pt[1]-start_pt[1])/max(self.module,1e-9)
                else:
                    d=int(f.get('initial_dir',f['dir']))%8
                    remain=max(0.0,self.launch_egress_modules*self.module-self._minimum_materialized_lane_length(f))
                    modules=max(1.0,min(3.0,math.ceil(remain/max(self.module,1e-9)-1e-9)))
                    end_pt=point_along_dir(start_pt,d,modules*self.module)
                geom=self._corridor_geom(f,start_pt,end_pt)
                if not self._gesture_clear(f,start_pt,end_pt,geom,allow_outside=False):
                    raise RuntimeError(f'final source-egress reserved corridor blocked (sample_seed={self.sseed}, front={f["id"]})')
                proposal=dict(front=f['id'],start=start_pt,end=end_pt,dir=d,modules=modules,geom=geom,score=0.0)
                self._accept(f,proposal,defer_post=True); moved+=1
            f['launch_egress_pending']=False
            f['protected_launch_unresolved']=False
            self._release_source_egress(owner)
            self.stats.setdefault('pathway_final_source_egress_completion_trace_count',0)
            self.stats['pathway_final_source_egress_completion_trace_count']+=len(f.get('ids',()))
        return moved

    def _settle_exhausted_mature_structural_intents(self):
        """Drop only unmaterialized structural intent after exact settlement is exhausted.

        Fan/fragment/branch flags describe future topology, not already-rendered geometry. Once a
        MAIN route is physically mature and clear of source egress, failure to realize one of
        those optional structural transactions may not invalidate the whole seed. Preserve every
        rendered segment and cancel only the future intent bit; relational embedding remains hard.
        """
        cleared=0
        for f in sorted(self.fronts.values(),key=lambda x:x['id']):
            if (f.get('status')!='active' or f.get('local_gap') or
                    f.get('chip',len(self.chips))>=len(self.chips)):
                continue
            if self._minimum_materialized_lane_length(f) < self.main_launch_maturity_modules*self.module-1e-7:
                continue
            if self._source_egress_pending(f):
                continue
            if f.get('fan_pending'):
                f['fan_pending']=False; cleared+=len(f.get('ids',()))
                self.stats.setdefault('pathway_final_exhausted_fan_intent_trace_count',0)
                self.stats['pathway_final_exhausted_fan_intent_trace_count']+=len(f.get('ids',()))
            if f.get('fragment_pending'):
                f['fragment_pending']=False; cleared+=len(f.get('ids',()))
                self.stats.setdefault('pathway_final_exhausted_fragment_intent_trace_count',0)
                self.stats['pathway_final_exhausted_fragment_intent_trace_count']+=len(f.get('ids',()))
            if f.get('branch_stage') is not None:
                f['branch_stage']=None; f['branch_turn']=None; cleared+=len(f.get('ids',()))
                self.stats.setdefault('pathway_final_exhausted_branch_intent_trace_count',0)
                self.stats['pathway_final_exhausted_branch_intent_trace_count']+=len(f.get('ids',()))
            self._refresh_lifecycle(f)
        return cleared

    def _persistence_hard_debt_reasons(self,f):
        """Diagnostic decomposition of the exact final hard-debt predicate."""
        if f.get('status')!='active' or f.get('local_gap') or f.get('chip',len(self.chips))>=len(self.chips):
            return ()
        out=[]
        if self._main_side_progress_debt(f): out.append('side_progress')
        if self._minimum_materialized_lane_length(f) < self.main_launch_maturity_modules*self.module-1e-7:
            out.append('under_survival_floor')
        if self._source_egress_pending(f): out.append('source_egress')
        if f.get('fan_pending'): out.append('fan_pending')
        if f.get('fragment_pending'): out.append('fragment_pending')
        if f.get('branch_stage') is not None: out.append('branch_stage')
        if self._fragment_singleton_still_embedded(f): out.append('fragment_embedded')
        if self._singleton_between_live_siblings(f): out.append('between_siblings')
        return tuple(out)

    def _final_relational_persistence_residue(self):
        """Mature MAIN fronts with genuine relational/side-level validity debt.

        This used to reopen only singleton sibling-embedding residue.  A side whose entire
        family is still below the eight-module progress certificate is the same kind of live
        construction debt and must be settled before coordinated terminal arbitration.
        """
        residue=[]
        for f in sorted(self.fronts.values(),key=lambda x:x['id']):
            if (f.get('status')!='active' or f.get('local_gap') or
                    f.get('chip',len(self.chips))>=len(self.chips)):
                continue
            if self._minimum_materialized_lane_length(f) < self.main_launch_maturity_modules*self.module-1e-7:
                continue
            if (self._source_egress_pending(f) or f.get('fan_pending') or f.get('fragment_pending') or
                    f.get('branch_stage') is not None):
                continue
            relational=(len(f.get('ids',()))==1 and
                        (self._fragment_singleton_still_embedded(f) or self._singleton_between_live_siblings(f)))
            if relational or self._main_side_progress_debt(f):
                residue.append(f)
        return residue

    def _settle_final_relational_persistence_progress(self,round_index_base):
        """Settle true final sibling-embedding residue by progress, never by a validity clock.

        This runs only after all existing bounded final cleanup.  Each tick proposes ordinary
        exact gestures from one committed snapshot, then atomically commits a deterministic
        conflict-clean subset.  Held lanes re-propose against the next snapshot.  The loop ends
        only when relational debt is discharged or when *no* residual lane has any legal ordinary
        proposal; that latter state is genuine local exhaustion and is handed to coordinated
        terminal arbitration.  There is deliberately no aspect-specific or correctness tick cap.
        """
        moved_total=0; tick=0
        while True:
            residue=self._final_relational_persistence_residue()
            if not residue:
                break
            rr=int(round_index_base)+1+tick; tick+=1
            # These flags may have been set by the earlier bounded separation attempt.  We are
            # actively reopening exactly that relational debt now; only a genuine zero-proposal
            # exhaustion below re-establishes the marker for final cohort arbitration.
            for f in residue:
                f['protected_launch_unresolved']=False
                f['_routing_round']=rr
            all_active=[f for f in self.fronts.values() if f.get('status')=='active']
            self._assign_round_connection_targets(all_active,rr)
            variant_map={}
            for f in residue:
                if f.get('status')!='active':
                    continue
                variants=self._proposal_variants(f,3)
                if variants:
                    variant_map[f['id']]=variants
            if not variant_map:
                for f in self._final_relational_persistence_residue():
                    f['protected_launch_unresolved']=True
                self.stats.setdefault('pathway_final_relational_geometric_exhaustion_trace_count',0)
                self.stats['pathway_final_relational_geometric_exhaustion_trace_count']+=sum(
                    len(f.get('ids',())) for f in self._final_relational_persistence_residue())
                break

            # HOLD is explicit and fair.  Sort all proposals by prior HOLD streak, then visual
            # score/canonical identity; admit at most one per front and exact-check every
            # same-snapshot pair.  If any legal proposal exists this always commits at least one.
            candidates=[]
            for fid,variants in variant_map.items():
                f=self.fronts[fid]; streak=int(f.get('final_relational_hold_streak',0))
                for rank,p in enumerate(variants):
                    candidates.append(((-streak,-float(p.get('score',0.0)),rank,fid,
                                        p['dir'],round(p['end'][0],6),round(p['end'][1],6)),fid,p))
            candidates.sort(key=lambda x:x[0])
            chosen=[]; moved_ids=set()
            for _key,fid,p in candidates:
                if fid in moved_ids:
                    continue
                if any(self._future_conflict(p,q) for q in chosen):
                    continue
                chosen.append(p); moved_ids.add(fid)
            if not chosen:
                # Defensive: individually legal variants existed, so this should be unreachable;
                # never reinterpret a solver artifact as geometric exhaustion.
                raise RuntimeError('final relational persistence arbitration made no progress')

            selected_map={p['front']:[p] for p in chosen}
            late_groups=self._conflict_groups(selected_map)
            late_deferred={fid for group in late_groups for fid in group}
            selected=[p for p in chosen if p['front'] not in late_deferred]
            if not selected:
                raise RuntimeError('final relational persistence late arbitration made no progress')
            for p in selected:
                self._accept(self.fronts[p['front']],p,defer_post=True)
            for p in selected:
                f=self.fronts[p['front']]
                if f.get('status')=='active':
                    self._post_accept(f,p)
            self._connect_singletons()
            moved_total+=len(selected)
            for f in residue:
                if f.get('status')!='active':
                    continue
                if f['id'] in moved_ids:
                    f['final_relational_hold_streak']=0
                else:
                    f['final_relational_hold_streak']=int(f.get('final_relational_hold_streak',0))+1
            self.stats.setdefault('pathway_final_relational_progress_tick_count',0)
            self.stats['pathway_final_relational_progress_tick_count']+=1
            self.stats.setdefault('pathway_final_relational_progress_move_count',0)
            self.stats['pathway_final_relational_progress_move_count']+=len(selected)
        return moved_total

    def _settle_stalled_main_families(self,round_index_base,rounds=6):
        """Give an intact main-side bus a real lane-level escape before horizon termination.

        A source family can clear the four-module egress yet still fail its coarse cohort fan.
        That is not evidence that the individual lanes are trapped.  At the hard horizon, only
        such still-intact main families are dissolved into their real lanes, then those siblings
        receive a few atomic same-family settlement ticks.  HOLD is a first-class outcome: a
        compatible subset may advance while the rest wait and re-propose from the next snapshot.
        No sequential winner becomes historical geometry in the same tick.
        """
        roots=[]
        for f in sorted(self.fronts.values(),key=lambda x:x['id']):
            if (f.get('status')=='active' and not f.get('local_gap') and
                    f.get('chip',len(self.chips))<len(self.chips) and f.get('parent') is None and
                    len(f.get('ids',()))>1 and f.get('fan_pending') and
                    self._launch_egress_cleared(f)):
                roots.append(f)
        settlement_ids=set()
        for root in roots:
            # One final normal cohort fan is always preferred.  Only if the coarse fan remains
            # impossible do we change representation to individual physical lanes.
            children=self._fan_front(root)
            if children:
                settlement_ids.update(c['id'] for c in children if c.get('status')=='active')
                continue
            if root.get('status')=='active' and self._fragment_bundled_front(root):
                settlement_ids.update(fid for fid in self.children_by_parent.get(root['id'],())
                                      if fid in self.fronts and self.fronts[fid].get('status')=='active')
                self.stats['pathway_main_horizon_family_fragment_count']=self.stats.get('pathway_main_horizon_family_fragment_count',0)+1
        if not settlement_ids:
            return 0
        moved_total=0
        for tick in range(max(1,int(rounds))):
            active=[self.fronts[fid] for fid in sorted(settlement_ids)
                    if fid in self.fronts and self.fronts[fid].get('status')=='active']
            if not active: break
            rr=int(round_index_base)+1+tick
            # Ready causal rollback is a pre-snapshot transition, as in ordinary main routing.
            for f in active:
                if f.get('quality_repair_pending') and not f.get('reroute_pending'):
                    self._schedule_reroute(f,rr,f.get('quality_repair_reason') or 'horizon_family_settlement')
            for f in active:
                if f.get('reroute_pending') and rr >= (f.get('reroute_ready_round') or 0):
                    f['_routing_round']=rr; self._traceback_for_reroute(f)
            active=[f for f in active if f.get('status')=='active' and not f.get('reroute_pending')]
            if not active: continue
            self._assign_round_connection_targets(active,rr)
            variant_map={}
            blocked=[]
            for f in active:
                f['_routing_round']=rr
                vs=self._proposal_variants(f,3)
                if vs: variant_map[f['id']]=vs
                else: blocked.append(f)
            chosen={}; grouped=set()
            for group in self._conflict_groups(variant_map):
                grouped.update(group)
                sol=self._solve_conflict_group(group,variant_map)
                if sol is None:
                    self._schedule_atomic_conflict_repair(group,rr)
                    continue
                chosen.update({p['front']:p for p in sol})
            for fid,vs in variant_map.items():
                if fid not in grouped and vs: chosen[fid]=vs[0]
            selected=[p for fid,p in sorted(chosen.items())
                      if self.fronts[fid].get('status')=='active' and not self.fronts[fid].get('reroute_pending')]
            for p in selected: self._accept(self.fronts[p['front']],p,defer_post=True)
            for p in selected:
                f=self.fronts[p['front']]
                if f.get('status')=='active': self._post_accept(f,p)
            if selected:
                moved_total+=len(selected); self.stats['pathway_atomic_round_commit_count']+=1
            self._connect_singletons()
            # A blocked sibling is held, not killed.  Re-aim after one held tick; after two,
            # schedule ordinary causal traceback so it can choose a different local corridor.
            for f in blocked:
                if f.get('status')!='active': continue
                f['settlement_hold_streak']=int(f.get('settlement_hold_streak',0))+1
                if f['settlement_hold_streak']>=2 and not f.get('reroute_pending'):
                    self._schedule_reroute(f,rr,'horizon_family_settlement')
            self.stats['pathway_main_horizon_settlement_round_count']=self.stats.get('pathway_main_horizon_settlement_round_count',0)+1
        self.stats['pathway_main_horizon_settlement_move_count']=self.stats.get('pathway_main_horizon_settlement_move_count',0)+moved_total
        return moved_total

    def _turn_directions(self,pts):
        dirs=[]
        for a,b in zip(pts,pts[1:]):
            if math.hypot(b[0]-a[0],b[1]-a[1])>1e-7:
                dirs.append(nearest_dir_index(b[0]-a[0],b[1]-a[1]))
        return dirs

    def _exact_turn_directions(self,pts):
        """Return exact octilinear headings plus a count of malformed visible segments."""
        dirs=[]; malformed=0
        for a,b in zip(pts,pts[1:]):
            dx=b[0]-a[0]; dy=b[1]-a[1]
            if math.hypot(dx,dy)<=1e-7:
                continue
            d=exact_dir8_index(dx,dy)
            if d is None:
                malformed+=1
            else:
                dirs.append(d)
        return dirs,malformed

    def _exact_path_grammar_ok(self,pts):
        dirs,malformed=self._exact_turn_directions(pts)
        if malformed:
            return False
        return all((b-a)%8 in (0,1,7) for a,b in zip(dirs,dirs[1:]))

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
                allowed=self.connection_pairs.get(pair) or self.branch_junction_pairs.get(pair)
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
        max_t=max((float(r['primitive'].svg.get('stroke_width',0.0)) for r in records),default=0.0)
        index=SpatialHash(max(70*self.U,2*self.module,max_t+2*self.r.pathway_interroute_keepout))
        for a in records:
            ta=float(a['primitive'].svg.get('stroke_width',0.0))
            reach=.5*(ta+max_t)+max(self.r.pathway_interroute_keepout,
                                    self.r.local_gap_line_edge_gap_factor*.5*(ta+max_t))
            for b in index.query(expand_bounds(a['primitive'].geom.bounds,reach)):
                inter=a['primitive'].geom.intersection(b['primitive'].geom)
                if inter.is_empty: continue
                pair=tuple(sorted((a['tid'],b['tid'])))
                meet=self.connection_pairs.get(pair) or self.branch_junction_pairs.get(pair)
                if meet is not None:
                    tb=b['primitive'].svg.get('stroke_width',0.0)
                    if inter.difference(Point(meet).buffer(self._connection_joint_radius(ta,tb),quad_segs=8)).is_empty:
                        continue
                bad+=1
            index.insert(a,a['primitive'].geom.bounds)
        return bad

    def _audit_trace_edge_clearances(self,records):
        """Exact rendered stroke-to-stroke moat audit with a conservative spatial broad phase."""
        bad=0; min_margin=float('inf')
        max_t=max((float(r['primitive'].svg.get('stroke_width',0.0)) for r in records),default=0.0)
        index=SpatialHash(max(70*self.U,2*self.module,max_t+2*self.r.pathway_interroute_keepout))
        for a in records:
            ta=float(a['primitive'].svg.get('stroke_width',0.0)); al=bool(a.get('local_gap'))
            reach=.5*(ta+max_t)+max(self.r.pathway_interroute_keepout,
                                    self.r.local_gap_line_edge_gap_factor*.5*(ta+max_t))
            for b in index.query(expand_bounds(a['primitive'].geom.bounds,reach)):
                tb=float(b['primitive'].svg.get('stroke_width',0.0)); bl=bool(b.get('local_gap'))
                gap=self.r.pathway_interroute_keepout
                if al or bl: gap=max(gap,self.r.local_gap_line_edge_gap_factor*.5*(ta+tb))
                pair=tuple(sorted((a['tid'],b['tid'])))
                meet=self.connection_pairs.get(pair) or self.branch_junction_pairs.get(pair)
                ga=a['primitive'].geom; gb=b['primitive'].geom
                if meet is not None:
                    jr=max(self._connection_joint_radius(ta,tb),4.0*gap)
                    joint=Point(meet).buffer(jr,quad_segs=8)
                    ga=ga.difference(joint); gb=gb.difference(joint)
                    if ga.is_empty or gb.is_empty: continue
                d=ga.distance(gb); min_margin=min(min_margin,d-gap)
                if ga.intersects(gb) or d<gap-1e-7: bad+=1
            index.insert(a,a['primitive'].geom.bounds)
        self.stats['pathway_min_unconnected_stroke_clearance_margin']=(0.0 if min_margin==float('inf') else min_margin)
        return bad

    def _audit_trace_pair_geometry(self,records):
        """One exact spatial pair pass for centreline, stroke-overlap and moat audits.

        V46 performed three whole-record pair enumerations over the same rendered traces. V47
        uses one conservative broad phase and applies the same exact predicates for each nearby
        pair.  Connection/branch junction exemptions remain identical.
        """
        accidental=collapsed=stroke_bad=clearance_bad=0
        min_margin=float('inf'); pairs=[]
        max_t=max((float(r['primitive'].svg.get('stroke_width',0.0)) for r in records),default=0.0)
        max_gap=max(self.r.pathway_interroute_keepout,self.r.local_gap_line_edge_gap_factor*max_t)
        index=SpatialHash(max(70*self.U,2*self.module,max_t+2*max_gap))
        for a in records:
            ta=float(a['primitive'].svg.get('stroke_width',0.0)); al=bool(a.get('local_gap'))
            aline=LineString(a['points']); aga=a['primitive'].geom
            reach=.5*(ta+max_t)+max(self.r.pathway_interroute_keepout,
                                    self.r.local_gap_line_edge_gap_factor*.5*(ta+max_t),.2*self.U)
            for b in index.query(expand_bounds(aga.bounds,reach)):
                tb=float(b['primitive'].svg.get('stroke_width',0.0)); bl=bool(b.get('local_gap'))
                pair=tuple(sorted((a['tid'],b['tid'])))
                meet=self.connection_pairs.get(pair) or self.branch_junction_pairs.get(pair)

                # Historical centreline-intersection audit.
                inter=aline.intersection(b['_audit_line'])
                if not inter.is_empty:
                    if inter.geom_type in ('LineString','MultiLineString') and inter.length>1e-6:
                        collapsed+=1; accidental+=1; pairs.append((a['tid'],b['tid'],'collapsed'))
                    else:
                        allowed=False
                        if meet is not None:
                            pts=[inter] if inter.geom_type=='Point' else ([g for g in inter.geoms if g.geom_type=='Point'] if hasattr(inter,'geoms') else [])
                            allowed=bool(pts) and all(math.hypot(q.x-meet[0],q.y-meet[1])<=1.5*self.U for q in pts)
                        if not allowed:
                            accidental+=1; pairs.append((a['tid'],b['tid'],inter.geom_type))

                ga=aga; gb=b['primitive'].geom
                stroke_inter=ga.intersection(gb)
                stroke_exempt=False
                if not stroke_inter.is_empty and meet is not None:
                    stroke_exempt=stroke_inter.difference(Point(meet).buffer(self._connection_joint_radius(ta,tb),quad_segs=8)).is_empty
                if not stroke_inter.is_empty and not stroke_exempt:
                    stroke_bad+=1

                gap=self.r.pathway_interroute_keepout
                if al or bl:
                    gap=max(gap,self.r.local_gap_line_edge_gap_factor*.5*(ta+tb))
                cga,cgb=ga,gb
                if meet is not None:
                    jr=max(self._connection_joint_radius(ta,tb),4.0*gap)
                    joint=Point(meet).buffer(jr,quad_segs=8)
                    cga=cga.difference(joint); cgb=cgb.difference(joint)
                if not cga.is_empty and not cgb.is_empty:
                    d=cga.distance(cgb); min_margin=min(min_margin,d-gap)
                    if cga.intersects(cgb) or d<gap-1e-7:
                        clearance_bad+=1
            a['_audit_line']=aline
            index.insert(a,aga.bounds)
        for rec in records:
            rec.pop('_audit_line',None)
        self.accidental_pairs=pairs
        self.stats['pathway_min_unconnected_stroke_clearance_margin']=(0.0 if min_margin==float('inf') else min_margin)
        self.stats['pathway_render_pair_audit_pass_count']=1
        return accidental,collapsed,stroke_bad,clearance_bad

    def _audit_connection_junction_turns(self,records):
        """Count head-to-head network vertices that form a >45-degree through-turn."""
        by_tid={r['tid']:r for r in records}
        bad=0; max_turn=0
        for pair,meet in self.connection_pairs.items():
            a=by_tid.get(pair[0]); b=by_tid.get(pair[1])
            if a is None or b is None:
                continue
            def incoming(rec):
                pts=rec['points']
                if len(pts)<2:
                    return None
                if math.hypot(pts[-1][0]-meet[0],pts[-1][1]-meet[1])<=1.5*self.U:
                    return exact_dir8_index(pts[-1][0]-pts[-2][0],pts[-1][1]-pts[-2][1])
                if math.hypot(pts[0][0]-meet[0],pts[0][1]-meet[1])<=1.5*self.U:
                    return exact_dir8_index(pts[0][0]-pts[1][0],pts[0][1]-pts[1][1])
                return None
            da=incoming(a); db=incoming(b)
            if da is None or db is None:
                bad+=1; continue
            through=(db+4-da)%8; mag=min(through,8-through); deg=45*mag
            max_turn=max(max_turn,deg)
            if through not in (0,1,7):
                bad+=1
        self.stats['pathway_max_connection_junction_turn_degrees']=max_turn
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
                            # after the last in-frame vertex.  Extend the *previous visible leg*
                            # to its frame crossing instead.  V40 accidentally moved the prior
                            # vertex to the current leg's crossing, which can skew an incoming
                            # 45-degree leg into a non-octilinear segment.
                            pa,pb=out[-2],out[-1]
                            pd=exact_dir8_index(pb[0]-pa[0],pb[1]-pa[1])
                            if pd is None:
                                raise RuntimeError('escaped-trace previous visible leg is non-octilinear')
                            prev_frame_dist=self._forward_frame_distance(pb,pd)
                            if not math.isfinite(prev_frame_dist):
                                raise RuntimeError('escaped-trace previous visible leg cannot reach canvas frame')
                            rq=point_along_dir(pb,pd,prev_frame_dist)
                            out[-1]=(min(self.W,max(0.0,rq[0])),min(self.H,max(0.0,rq[1])))
                        else:
                            out.append((q[0],q[1]))
                break
            # An escaped route should never re-enter, but ignore already-exterior continuation
            # rather than letting invisible geometry affect the rendered safety audit.
            if not prev_inside:
                break
        return out if len(out)>=2 else pts

    def _local_visible_primitive_static_clear(self,primitive):
        """Exact rendered-primitive admission against the frozen chip/component field.

        Planning and marker backoff already preserve these moats, but final materialization can
        add visible source/terminal marker extent that is not represented by the centreline
        stroke itself.  Local fillers are optional, so any visible primitive that cannot preserve
        the exact frozen moat rejects the whole trace rather than weakening clearance.
        """
        if primitive is None or primitive.geom is None or primitive.geom.is_empty:
            return True
        # Markers and round end caps are finalized after gesture routing.  Enforce
        # composition ownership on the exact visible primitives as well.
        if not self._local_component_territory_clear(primitive.geom):
            return False
        reach=max(self.r.pathway_main_chip_keepout,self.r.component_pathway_clearance)
        for gi,obj in self.static_index.query(expand_bounds(primitive.geom.bounds,reach)):
            keep=(self.r.pathway_main_chip_keepout if gi < len(self.chips) else self.r.component_pathway_clearance)
            if primitive.geom.intersects(obj.geom) or primitive.geom.distance(obj.geom)<keep-1e-7:
                return False
        return True

    def _backoff_local_terminal_from_components(self,pts,thickness):
        """Move a final local endpoint backward until its marker clears all frozen components."""
        if len(pts)<2 or not (self.cols or self.isolated):
            return list(pts),0.0
        marker_extent=self.r._termination_dot_radius(thickness)+.5*self.r.termination_dot_hollow_stroke
        required=self.r.component_pathway_clearance+marker_extent
        original=[tuple(p) for p in pts]
        total_len=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(original,original[1:]))
        # V37: do not stop after an arbitrary 1.6 modules when a terminal marker is running
        # alongside a tall frozen component.  Retreat anywhere along the already-legal polyline
        # provided the surviving visible trace still satisfies the normal termination-length floor.
        min_remaining=2.75*self.module
        max_back=max(0.0,total_len-min_remaining)
        step=max(.75*self.U,.025*self.module)
        d=0.0
        while d<=max_back+1e-9:
            cand=self._clip_polyline_end(original,d) if d>0 else list(original)
            if len(cand)<2: break
            q=cand[-1]
            qb=(q[0]-required,q[1]-required,q[0]+required,q[1]+required)
            bad=False
            for gi,g in self.static_index.query(qb):
                if gi < len(self.chips): continue
                if Point(q).distance(g.geom)<required:
                    bad=True; break
            if not bad:
                # Avoid manufacturing a microscopic last visible segment.
                if math.hypot(cand[-1][0]-cand[-2][0],cand[-1][1]-cand[-2][1]) < .10*self.module and len(cand)>2:
                    d += math.hypot(cand[-1][0]-cand[-2][0],cand[-1][1]-cand[-2][1]) + step
                    continue
                return cand,d
            d+=step
        # No legal marker position exists without reducing the filler below its visible length
        # floor.  Local fillers are optional: signal materialization to prune this trace instead
        # of weakening the component moat or drawing a marker inside it.
        return list(original),None

    @staticmethod
    def _polyline_spatial_chunk_bounds(points,max_span):
        """Yield tight AABBs that follow a polyline instead of its empty global rectangle.

        Long 45-degree traces are pathological for a whole-polyline AABB: the box contains a
        large triangular region that the trace never touches. Subdividing each straight segment
        so neither axis spans more than one hash cell keeps the broad phase local. Exact GEOS
        predicates remain authoritative after this candidate filter.
        """
        span=max(float(max_span),1e-9)
        for a,b in zip(points,points[1:]):
            ax,ay=a; bx,by=b
            steps=max(1,int(math.ceil(max(abs(bx-ax),abs(by-ay))/span)))
            px,py=ax,ay
            for i in range(1,steps+1):
                t=i/steps
                qx=ax+(bx-ax)*t; qy=ay+(by-ay)*t
                yield (min(px,qx),min(py,qy),max(px,qx),max(py,qy))
                px,py=qx,qy

    def _render_line_index_insert(self,index,item,points):
        """Insert one rendered trace through segment-local chunks into ``index``."""
        for b in self._polyline_spatial_chunk_bounds(points,index.cell_size):
            index.insert(item,b)

    def _render_line_index_query(self,index,points,reach):
        """Return nearby rendered traces once each, ordered by original admission order."""
        found={}
        for b in self._polyline_spatial_chunk_bounds(points,index.cell_size):
            for old in index.query(expand_bounds(b,reach)):
                key=old.get('render_order',old.get('tid'))
                found[key]=old
        return [found[k] for k in sorted(found)]

    def _finish_main_preflight_trial_stats(self,trace_records,root_prims,hard_baseline=None):
        """Finish only the rendered facts needed by a speculative main-network transaction.

        The admission loop that produced ``trace_records`` already applies the exact rendered
        centreline/stroke/edge-gap predicates in final draw order. A speculative repair therefore
        only needs launch identity conservation plus cheap persistence/grammar facts before it can
        be provisionally committed. Expensive whole-board static and pair audits are deferred to
        the single authoritative normal materialization after the bounded repair loop.

        ``hard_baseline`` carries the last authoritative values for deferred invariants. A trial
        never claims to have re-audited them; every provisional sequence still has to survive a
        normal full materialization before preflight can pass or any SVG can be emitted.
        """
        lengths=[]
        for rec in trace_records:
            pts=rec['points']
            lengths.append(sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:])))

        main_items=[(rec,length) for rec,length in zip(trace_records,lengths) if not rec.get('local_gap')]
        launch_ids=set(self.main_launch_trace_ids)
        visible_launch_ids={rec['tid'] for rec,_ in main_items if rec['tid'] in launch_ids}
        active_launch_ids={tid for f in self.fronts.values() if f.get('status')=='active'
                           for tid in f.get('ids',()) if tid in launch_ids}
        missing_launch_ids=sorted(launch_ids-visible_launch_ids)
        self.stats['pathway_visible_launch_trace_count']=len(visible_launch_ids)
        self.stats['pathway_main_launch_survival_count']=len({rec['tid'] for rec,_ in main_items})
        self.stats['pathway_main_unaccounted_launch_trace_count']=len(missing_launch_ids)
        self.stats['pathway_main_unaccounted_launch_trace_ids']=missing_launch_ids[:64]
        self.stats['pathway_main_active_unmaterialized_launch_trace_count']=len(active_launch_ids)
        self.stats['pathway_main_active_unmaterialized_launch_trace_ids']=sorted(active_launch_ids)[:64]

        preferred=self.main_launch_preferred_terminal_modules*self.module
        free_under=[(rec,length) for rec,length in main_items
                    if rec.get('status')=='terminated' and length<preferred-1e-7]
        self.stats['pathway_main_free_terminal_under_preferred_visible_trace_count']=len(free_under)
        self.stats['pathway_main_short_termination_trace_count']=sum(
            1 for rec,length in main_items
            if rec.get('status')=='terminated' and length<self.main_launch_maturity_modules*self.module-1e-7)

        by_root={}
        for rec,length in main_items:
            by_root.setdefault(rec['root'],[]).append((rec,length))
        self.stats['pathway_main_stalled_side_count']=sum(
            1 for items in by_root.values()
            if items and all(rec['status']=='terminated' for rec,_ in items)
            and max(length for _,length in items)<8.0*self.module)

        illegal_turns=0; non_octilinear=0
        for rec in trace_records:
            dirs,malformed=self._exact_turn_directions(rec['points'])
            non_octilinear+=malformed
            illegal_turns+=sum(1 for da,db in zip(dirs,dirs[1:]) if (db-da)%8 not in (0,1,7))
        junction_bad=self._audit_connection_junction_turns(trace_records)
        self.stats['pathway_non_octilinear_segment_count']=non_octilinear
        self.stats['pathway_illegal_connection_junction_turn_count']=junction_bad
        self.stats['pathway_illegal_turn_count']=illegal_turns+junction_bad
        self.stats['pathway_curved_primitive_count']=sum(
            1 for g in root_prims.values() for prim in g if prim.svg.get('type')=='quadratic')

        baseline=hard_baseline or {}
        for key in ('pathway_unmarked_stroke_overlap_count','pathway_unmarked_clearance_violation_count',
                    'pathway_unmarked_overlap_count','pathway_static_intersection_count'):
            self.stats[key]=int(baseline.get(key,self.stats.get(key,0)) or 0)
        self.stats['pathway_preflight_trial_deferred_full_audit']=1
        self.stats.setdefault('pathway_preflight_fast_trial_count',0)
        self.stats['pathway_preflight_fast_trial_count']+=1
        return [],self.stats

    def _materialize(self,preflight_trial=False,preflight_trial_hard_baseline=None):
        # Visible marker counts describe this materialization pass, not the number of preflight
        # times the same geometry has been inspected.
        self.stats['pathway_source_marker_count']=0
        self.stats['pathway_main_source_marker_count']=0
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
            and f.get('travel',0.0)+1e-9<2.75*self.module
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
        render_line_max_thickness=0.0
        # In a local-only planner, pre-admit the exact frozen rendered main polylines.  This is
        # a redundant visible-geometry safety net in addition to their planner obstacles.
        render_order=0
        for frec in getattr(self,'frozen_main_render_records',()):
            t=float(frec.get('max_thickness',frec['primitive'].svg.get('stroke_width',0.0)))
            item=dict(tid=frec['tid'],line=frec.get('line',LineString(frec.get('points',()))),primitive=frec['primitive'],
                      chip=-1,side_index=-1,side='frozen_main',front=frec['front'],parent=None,
                      family=('frozen_main',frec['front']),status='frozen',termination_reason=None,
                      thickness=t,local_gap=False,frozen_main=True,render_order=render_order)
            render_order+=1
            self._render_line_index_insert(render_line_index,item,list(item['line'].coords))
            render_line_max_thickness=max(render_line_max_thickness,t)
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
                    # V39 restores main-chip emergence dots as trace-owned geometry.  A main
                    # physical lane keeps the same original launch point even after its current
                    # owning front becomes a branch/rebase child, so leaf parentage must never
                    # decide whether the source marker exists.  Local filler child branches keep
                    # the historical root-only marker rule.
                    main_physical_trace=(not f.get('local_gap') and f.get('chip',len(self.chips))<len(self.chips))
                    source_owned=main_physical_trace or f.get('parent') is None
                    if not special_local and source_owned:
                        sradius=self.r._termination_dot_radius(t)
                        hollow_source_clip=sradius+0.5*self.r.termination_dot_hollow_stroke
                        # V47 marker fidelity: hollow styling is optional; six-module visible
                        # persistence is not.  If source clipping alone would drop a completed
                        # main route below the preferred journey, use the legal filled variant.
                        main_visible_floor=(self._main_terminal_visible_floor_modules(f,tid)*self.module
                                            if main_physical_trace else self.main_launch_preferred_terminal_modules*self.module)
                        preserve_preferred=(main_physical_trace and
                            logical_len-hollow_source_clip < main_visible_floor-1e-7)
                        sfilled=True if (main_near_floor or preserve_preferred) else (mrng.random()<.55)
                        sstroke=0.0 if sfilled else self.r.termination_dot_hollow_stroke
                        source_marker=prim_circle(sx,sy,sradius,self.r.FG,sfilled,sstroke)
                        if not sfilled:
                            pts=self._clip_polyline_start(pts,hollow_source_clip)
                if f['status']=='terminated' and not debug:
                    if f.get('local_gap') and not special_local:
                        pts,component_backoff=self._backoff_local_terminal_from_components(pts,f['thicknesses'][tid])
                        if component_backoff is None:
                            self.stats.setdefault('pathway_local_gap_component_marker_prune_count',0)
                            self.stats['pathway_local_gap_component_marker_prune_count']+=1
                            continue
                        if component_backoff>0:
                            self.stats.setdefault('pathway_local_gap_component_marker_backoff_count',0)
                            self.stats.setdefault('pathway_local_gap_component_marker_backoff_distance',0.0)
                            self.stats['pathway_local_gap_component_marker_backoff_count']+=1
                            self.stats['pathway_local_gap_component_marker_backoff_distance']+=component_backoff
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
                        clipped_len=(sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(clipped,clipped[1:]))
                                     if len(clipped)>=2 else 0.0)
                        main_trace=(not f.get('local_gap') and f.get('chip',len(self.chips))<len(self.chips))
                        if (len(clipped)<2 or
                                math.hypot(clipped[-1][0]-clipped[-2][0],clipped[-1][1]-clipped[-2][1]) < .10*self.module-1e-9 or
                                (main_trace and clipped_len < self._main_terminal_visible_floor_modules(f,tid)*self.module-1e-7)):
                            filled=True; stroke=0.0
                        else:
                            pts=clipped
                    marker=prim_circle(x,y,radius,self.r.FG,filled,stroke)
                # Once component-first LOCAL routing has been exactly materialized,
                # its emitted packages are fixed while the debt pass adds later
                # traces.  Re-running cosmetic backoff against those later paths
                # can otherwise silently shorten old visible service even though
                # the debt router keeps their actual heads clear.
                frozen=getattr(self,'_local_frozen_visible_packets',{}).get(tid)
                if frozen is not None:
                    pts=list(frozen['points'])
                    source_marker=frozen['source_marker']
                    marker=frozen['terminal_marker']
                if len(pts)<2:
                    continue
                # The current renderer hardens the *rendered* no-tiny-death invariant. Source/terminal marker
                # clipping can shorten an otherwise legal centreline below 2.75 modules, so
                # audit the visible polyline here for every terminated trace, not only locals.
                if f['status']=='terminated':
                    visible_len=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:]))
                    if visible_len+1e-9 < 2.75*self.module:
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
                # V39 render-time static moat admission for local fillers.  The planner uses
                # flat corridor caps for cheap routing, while a special thick trace is visibly
                # round-capped.  Test the actual rendered stroke against frozen chips/components
                # here so the cap can never protrude into a component moat.  Local fillers are
                # optional; if the visible primitive cannot fit, omit it rather than weaken the
                # frozen-geometry contract.
                if f.get('local_gap'):
                    # Admit the complete visible local trace package, not only the routed stroke.
                    # Source/terminal dots carry real rendered area and must preserve the same
                    # frozen component/chip moat as the line itself.  This redundant final gate
                    # closes marker-only clearance violations without changing planner behavior.
                    visible_static_prims=[prim]
                    if source_marker is not None:
                        visible_static_prims.append(source_marker)
                    if marker is not None:
                        visible_static_prims.append(marker)
                    if any((not self._local_component_territory_clear(vp.geom) or
                            not self._local_fill_parcel_clear(f,vp.geom)) for vp in visible_static_prims):
                        raise RuntimeError('visible LOCAL primitive escaped its route cluster')
                    if any(not self._local_visible_primitive_static_clear(vp) for vp in visible_static_prims):
                        self.stats.setdefault('pathway_static_clearance_trace_cleanup_count',0)
                        self.stats['pathway_static_clearance_trace_cleanup_count']+=1
                        self.stats.setdefault('pathway_static_clearance_visible_primitive_cleanup_count',0)
                        self.stats['pathway_static_clearance_visible_primitive_cleanup_count']+=1
                        continue
                line=LineString(pts)
                unsafe=None
                if not line.is_simple:
                    unsafe='intersection'
                else:
                    new_t=float(f['thicknesses'][tid])
                    query_reach=.5*(new_t+render_line_max_thickness)+max(
                        self.r.pathway_interroute_keepout,
                        self.r.local_gap_line_edge_gap_factor*.5*(new_t+render_line_max_thickness))
                    for old in self._render_line_index_query(
                            render_line_index,pts,max(1.0*self.U,query_reach)):
                        pair=tuple(sorted((tid,old['tid'])))
                        allowed=self.connection_pairs.get(pair) or self.branch_junction_pairs.get(pair)
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
                        # V39 exact rendered edge-gap admission.  Planner corridors normally
                        # guarantee this already, but render-only features such as the round cap
                        # on an extra-thick local trace can enlarge the actual visible stroke.
                        # Never admit a later trace that violates the line-to-line moat.
                        gap=self._interroute_gap_for_fronts(
                            f,other_thickness=old.get('thickness',old['primitive'].svg.get('stroke_width',0.0)),
                            other_local=old.get('local_gap',False),
                            other_cluster_id=old.get('local_fill_cluster_id'))
                        ga=prim.geom; gb=old['primitive'].geom
                        if allowed is not None:
                            jr=max(self._connection_joint_radius(f['thicknesses'][tid],old.get('thickness',old['primitive'].svg.get('stroke_width',0.0))),4.0*gap)
                            joint=Point(allowed).buffer(jr,quad_segs=8)
                            ga=ga.difference(joint); gb=gb.difference(joint)
                        if not ga.is_empty and not gb.is_empty and ga.distance(gb)<gap-1e-7:
                            unsafe='clearance'; break
                if unsafe is not None:
                    cleanup_pair=dict(new_tid=tid,old_tid=(old['tid'] if 'old' in locals() else None),
                                      new_front=f['id'],new_parent=f.get('parent'),new_family=self._launch_family_key(f),
                                      new_chip=f['chip'],new_side_index=f.get('side_index'),new_side=f.get('side'),
                                      old_front=(old.get('front') if 'old' in locals() else None),
                                      old_parent=(old.get('parent') if 'old' in locals() else None),
                                      old_family=(old.get('family') if 'old' in locals() else None),
                                      old_chip=(old.get('chip') if 'old' in locals() else None),
                                      new_status=f.get('status'),new_reason=f.get('termination_reason'),
                                      old_status=(old.get('status') if 'old' in locals() else None),
                                      old_reason=(old.get('termination_reason') if 'old' in locals() else None),
                                      new_points=[(round(x,2),round(y,2)) for x,y in pts],
                                      old_points=([(round(x,2),round(y,2)) for x,y in old['line'].coords] if 'old' in locals() else []))
                    if unsafe=='duplicate':
                        self.stats['pathway_duplicate_trace_cleanup_count']+=1
                        self.stats.setdefault('pathway_duplicate_cleanup_pairs',[]).append(cleanup_pair)
                    elif unsafe=='clearance':
                        self.stats.setdefault('pathway_clearance_trace_cleanup_count',0)
                        self.stats['pathway_clearance_trace_cleanup_count']+=1
                        self.stats.setdefault('pathway_clearance_cleanup_pairs',[]).append(cleanup_pair)
                    else:
                        self.stats['pathway_intersection_trace_cleanup_count']+=1
                        self.stats.setdefault('pathway_intersection_cleanup_pairs',[]).append(cleanup_pair)
                    continue
                render_item=dict(tid=tid,line=line,primitive=prim,chip=f['chip'],side_index=f.get('side_index'),side=f.get('side'),front=f['id'],parent=f.get('parent'),family=self._launch_family_key(f),status=f.get('status'),termination_reason=f.get('termination_reason'),thickness=f['thicknesses'][tid],local_gap=bool(f.get('local_gap') or f['chip']>=len(self.chips)),local_fill_cluster_id=f.get('local_fill_cluster_id'),render_order=render_order)
                render_order+=1
                self._render_line_index_insert(render_line_index,render_item,pts)
                render_line_max_thickness=max(render_line_max_thickness,float(f['thicknesses'][tid]))
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
                        if not f.get('local_gap') and f.get('chip',len(self.chips))<len(self.chips):
                            self.stats.setdefault('pathway_main_source_marker_count',0)
                            self.stats['pathway_main_source_marker_count']+=1
                trace_records.append(dict(tid=tid,front=f['id'],chip=f['chip'],root=key,status=f['status'],termination_reason=f.get('termination_reason'),points=pts,primitive=prim,source_marker=source_marker,terminal_marker=marker,local_gap=bool(f.get('local_gap') or f['chip']>=len(self.chips)),local_gap_special=special_local,local_fill_cluster_id=f.get('local_fill_cluster_id')))
                root_meta[key]['trace_ids'].add(tid)
                root_meta[key]['dirs'].extend(self._turn_directions(pts))
                if marker is not None:
                    root_prims[key].append(marker)
                    render_marker_index.insert(dict(geom=marker.geom,mid=len(render_marker_index.objects),
                                                    front=f['id'],tid=tid),marker.geom.bounds)
        if preflight_trial:
            return self._finish_main_preflight_trial_stats(
                trace_records,root_prims,hard_baseline=preflight_trial_hard_baseline)
        groups=[]; visible_coverages=[]
        for key,prims in sorted(root_prims.items()):
            chip,side_index,side=key
            trace_count=len(root_meta[key]['trace_ids'])
            # A root whose every candidate trace was removed by final duplicate/intersection
            # cleanup is not a visible pathway group and must not survive as empty metadata.
            if trace_count<=0:
                continue
            launch_groups=[self.fronts[fid] for fid in self.fronts_by_side.get((chip,side_index,side),())
                           if fid in self.fronts and self.fronts[fid].get('parent') is None]
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
                    local_fill_cluster_id=(local_root.get('local_fill_cluster_id') if local_root else None),
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
        marker_conflicts=0; marker_pairs=set()
        for a in rendered_markers:
            query=expand_bounds(a['geom'].bounds,self.r.termination_dot_min_gap)
            for b in render_marker_index.query(query):
                if b is a: continue
                pair=tuple(sorted((int(a['mid']),int(b['mid']))))
                if pair in marker_pairs: continue
                marker_pairs.add(pair)
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
        # V47 rendered-route observability.  Logical travel is not authoritative once marker
        # clipping/backoff has happened; every launch is accounted from the actual emitted polyline.
        main_items=[(rec,length) for rec,length in zip(trace_records,lengths) if not rec.get('local_gap')]
        launch_ids=set(self.main_launch_trace_ids)
        visible_launch_ids={rec['tid'] for rec,_ in main_items if rec['tid'] in launch_ids}
        active_launch_ids={tid for f in self.fronts.values() if f.get('status')=='active'
                           for tid in f.get('ids',()) if tid in launch_ids}
        missing_launch_ids=sorted(launch_ids-visible_launch_ids)
        self.stats['pathway_main_preferred_visible_modules']=self.main_launch_preferred_terminal_modules
        self.stats['pathway_main_visible_length_modules_by_trace']={
            str(rec['tid']):round(length/max(self.module,1e-9),6) for rec,length in main_items if rec['tid'] in launch_ids}
        self.stats['pathway_main_outcome_by_trace']={
            str(rec['tid']):[rec.get('status'),rec.get('termination_reason'),round(length/max(self.module,1e-9),6)]
            for rec,length in main_items if rec['tid'] in launch_ids}
        self.stats['pathway_main_unaccounted_launch_trace_count']=len(missing_launch_ids)
        self.stats['pathway_main_unaccounted_launch_trace_ids']=missing_launch_ids[:64]
        self.stats['pathway_main_active_unmaterialized_launch_trace_count']=len(active_launch_ids)
        self.stats['pathway_main_active_unmaterialized_launch_trace_ids']=sorted(active_launch_ids)[:64]
        self.stats['pathway_main_frame_exit_trace_count']=sum(1 for rec,_ in main_items if rec.get('status')=='escaped')
        self.stats['pathway_main_connected_trace_count']=sum(1 for rec,_ in main_items if rec.get('status')=='connected')
        preferred=self.main_launch_preferred_terminal_modules*self.module
        free_under=[(rec,length) for rec,length in main_items
                    if rec.get('status')=='terminated' and length<preferred-1e-7]
        horizon_reasons={'round_limit','coordinated_persistence_limit','hard_stop_exhausted','journey_limit'}
        horizon_under=[(rec,length) for rec,length in free_under if rec.get('termination_reason') in horizon_reasons]
        self.stats['pathway_main_free_terminal_under_preferred_visible_trace_count']=len(free_under)
        self.stats['pathway_main_horizon_under_preferred_visible_trace_count']=len(horizon_under)
        self.stats['pathway_main_floor_hugging_terminal_trace_count']=sum(
            1 for rec,length in main_items if rec.get('status')=='terminated' and
            self.main_launch_maturity_modules*self.module-1e-7 <= length < (self.main_launch_maturity_modules+.55)*self.module)
        self.stats['pathway_main_under_preferred_visible_details']=[
            dict(tid=rec['tid'],front=rec.get('front'),root=list(rec.get('root',())),status=rec.get('status'),
                 termination_reason=rec.get('termination_reason'),visible_modules=round(length/max(self.module,1e-9),6))
            for rec,length in free_under[:64]]
        short_by_root={}
        total_by_root={}
        for rec,length in main_items:
            root=rec['root']; total_by_root[root]=total_by_root.get(root,0)+1
            if rec.get('status')=='terminated' and length<preferred-1e-7:
                short_by_root[root]=short_by_root.get(root,0)+1
        self.stats['pathway_main_under_preferred_root_count']=len(short_by_root)
        self.stats['pathway_main_under_preferred_root_max_fraction']=max(
            (short_by_root[r]/max(1,total_by_root.get(r,0)) for r in short_by_root),default=0.0)

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
        stalled=0; stalled_details=[]
        for root,items in by_root.items():
            if items and all(rec['status']=='terminated' for rec,_ in items) and max(length for _,length in items)<8.0*self.module:
                stalled+=1
                ranked=sorted(items,key=lambda item:(-item[1],item[0].get('front',10**18),item[0]['tid']))
                stalled_details.append(dict(
                    root=list(root),
                    max_visible_length=max(length for _,length in items),
                    candidates=[dict(front=rec.get('front'),tid=rec['tid'],visible_length=length)
                                for rec,length in ranked],
                ))
        self.stats['pathway_main_stalled_side_count']=stalled
        self.stats['pathway_main_stalled_side_details']=stalled_details
        self.stats['pathway_tiny_termination_trace_count']=sum(1 for rec,length in zip(trace_records,lengths)
                                                               if rec['status']=='terminated' and length+1e-9<2.75*self.module)
        board_scale=sum(length>=.30*math.hypot(self.W,self.H) for length in lengths)
        self.stats['pathway_board_scale_trace_count']=board_scale
        self.stats['pathway_board_scale_trace_fraction']=board_scale/len(lengths) if lengths else 0.0
        self.stats['pathway_mean_geometric_length']=sum(lengths)/len(lengths) if lengths else 0.0
        self.stats['pathway_median_geometric_length']=(sorted(lengths)[len(lengths)//2] if lengths else 0.0)
        self.stats['pathway_turn_count']=sum(turns)
        self.stats['pathway_mean_turns_per_trace']=sum(turns)/len(turns) if turns else 0.0
        self.stats['pathway_turns_per_100U']=(100*self.U*sum(turns)/sum(lengths)) if sum(lengths)>0 else 0.0
        # V38 local articulation diagnostics are computed from the actual rendered trace
        # polylines.  These make the visual contract measurable instead of inferring it from
        # proposal probabilities.
        local_records=[rec for rec in trace_records if rec.get('local_gap')]
        local_turn_counts=[]; local_max_vertex_turn=0
        for rec in local_records:
            ds=self._turn_directions(rec['points']); tc=0
            for da,db in zip(ds,ds[1:]):
                delta=(db-da)%8; mag=min(delta,8-delta)
                if mag:
                    tc+=1; local_max_vertex_turn=max(local_max_vertex_turn,45*mag)
            local_turn_counts.append(tc)
        self.stats['pathway_local_gap_straight_visible_trace_count']=sum(1 for n in local_turn_counts if n==0)
        self.stats['pathway_local_gap_straight_visible_trace_fraction']=(
            self.stats['pathway_local_gap_straight_visible_trace_count']/len(local_turn_counts) if local_turn_counts else 0.0)
        self.stats['pathway_local_gap_mean_turns_per_visible_trace']=(sum(local_turn_counts)/len(local_turn_counts) if local_turn_counts else 0.0)
        self.stats['pathway_local_gap_max_single_vertex_turn_degrees']=local_max_vertex_turn
        self.stats['pathway_compensating_zigzag_count']=zigzags
        self.stats['pathway_terminal_alignment_exception_count']=terminal_alignments
        normal_lengths=[x for f in leaves for x in f['normal_segment_lengths']]
        self.stats['pathway_min_normal_center_segment']=min(normal_lengths,default=0.0)
        self.stats['pathway_min_actual_segment']=min(actual_segments,default=0.0)
        self.stats['pathway_coverage_cell_fraction']=len(self.coverage_cells)/max(1,self.coverage_grid_nx*self.coverage_grid_ny)
        quartiles=set()
        for gx,gy in self.coverage_cells:
            quartiles.add((gx>=self.coverage_grid_nx/2,gy>=self.coverage_grid_ny/2))
        self.stats['pathway_canvas_quartiles_touched']=len(quartiles)
        static_intersections=0
        min_foreign_static=None; min_foreign_chip=None
        for rec in trace_records:
            geom=rec['primitive'].geom
            static_intersections+=self._static_intersection_group_count(geom)
            ds,dc=self._nearest_foreign_static_clearances(geom,rec['chip'])
            if ds>0.0 or len(self.static)>1:
                min_foreign_static=ds if min_foreign_static is None else min(min_foreign_static,ds)
            if dc>0.0 or len(self.chips)>1:
                min_foreign_chip=dc if min_foreign_chip is None else min(min_foreign_chip,dc)
        self.stats['pathway_static_intersection_count']=static_intersections
        self.stats['pathway_min_foreign_static_clearance']=0.0 if min_foreign_static is None else min_foreign_static
        self.stats['pathway_min_foreign_main_chip_clearance']=0.0 if min_foreign_chip is None else min_foreign_chip
        self.stats['pathway_required_static_keepout']=self.r.pathway_static_keepout
        self.stats['pathway_required_main_chip_keepout']=self.r.pathway_main_chip_keepout
        self.stats['pathway_terminal_head_keepout']=self.r.pathway_terminal_head_keepout
        self.stats['pathway_chip_launch_gap']=self.r.pathway_chip_launch_gap
        self.stats['pathway_termination_dot_scale']=self.r.termination_dot_scale
        self.stats['pathway_termination_dot_hollow_stroke']=self.r.termination_dot_hollow_stroke
        # V39 hard trace grammar audit.  Nearest-octant quantization is no longer sufficient:
        # every rendered segment must itself be exact octilinear geometry, every in-trace vertex
        # may change heading only by 0/+/-45, and head-to-head connection vertices obey the same
        # through-path rule.
        illegal_turns=0; non_octilinear=0
        for rec in trace_records:
            dirs,malformed=self._exact_turn_directions(rec['points'])
            non_octilinear+=malformed
            for da,db in zip(dirs,dirs[1:]):
                if (db-da)%8 not in (0,1,7):
                    illegal_turns+=1
        junction_bad=self._audit_connection_junction_turns(trace_records)
        illegal_turns+=junction_bad
        self.stats['pathway_non_octilinear_segment_count']=non_octilinear
        self.stats['pathway_illegal_connection_junction_turn_count']=junction_bad
        self.stats['pathway_illegal_turn_count']=illegal_turns
        self.stats['pathway_curved_primitive_count']=sum(1 for g in root_prims.values() for p in g if p.svg.get('type')=='quadratic')
        accidental,collapsed,stroke_bad,clearance_bad=self._audit_trace_pair_geometry(trace_records)
        self.stats['pathway_unmarked_stroke_overlap_count']=stroke_bad
        self.stats['pathway_unmarked_clearance_violation_count']=clearance_bad
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
        self._local_render_marker_records=list(render_marker_index.objects.values())
        self._local_render_line_records=list(getattr(self,'frozen_main_render_records',()))+list(trace_records)
        self._recount_visible_local_gap_service(trace_records)
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

    def _normalize_terminal_record(self,rec):
        """Canonicalize live/preflight marker records to (front, tid, point, disc, radius).

        V46's optimized spatial pairer accidentally assumed the five-field preflight shape while
        the live materializer also exposes the historical four-field ``(tid, point, disc, radius)``
        shape. V47 makes that internal contract explicit at the pairer boundary.
        """
        if len(rec)==5:
            return rec
        if len(rec)==4:
            tid,point,disc,radius=rec
            return (None,tid,point,disc,radius)
        raise ValueError('terminal marker record must have 4 or 5 fields')

    def _terminal_record_conflict(self,a,b,extra_gap=0.0):
        """Exact circle-circle terminal spacing without expensive polygon distance calls."""
        a=self._normalize_terminal_record(a); b=self._normalize_terminal_record(b)
        pa,pb=a[2],b[2]; ra,rb=float(a[4]),float(b[4])
        lim=ra+rb+self.r.termination_dot_min_gap+float(extra_gap)
        dx=pa[0]-pb[0]; dy=pa[1]-pb[1]
        return dx*dx+dy*dy < lim*lim-1e-12

    def _terminal_conflict_pairs(self,discs,extra_gap=0.0):
        """Enumerate exactly the historical conflicting pairs in original i/j order."""
        if len(discs)<2: return []
        records=[self._normalize_terminal_record(rec) for rec in discs]
        max_r=max(float(rec[4]) for rec in records)
        reach=max(1e-6,2.0*max_r+self.r.termination_dot_min_gap+float(extra_gap))
        index=SpatialHash(reach); pos={}
        for i,rec in enumerate(records):
            pos[id(rec)]=i; x,y=rec[2]; index.insert(rec,(x,y,x,y))
        out=[]
        for i,a in enumerate(records):
            x,y=a[2]; r=float(a[4])+max_r+self.r.termination_dot_min_gap+float(extra_gap)
            near=index.query((x-r,y-r,x+r,y+r))
            js=sorted({pos[id(b)] for b in near if pos[id(b)]>i})
            for j in js:
                b=records[j]
                if self._terminal_record_conflict(a,b,extra_gap=extra_gap): out.append((a,b))
        return out

    def _first_terminal_conflict(self,discs,extra_gap=0.0):
        pairs=self._terminal_conflict_pairs(discs,extra_gap=extra_gap)
        return pairs[0] if pairs else None

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
            max_keep=max(self.r.pathway_main_chip_keepout,self.r.pathway_static_keepout)
            for gi,g in self.static_index.query(expand_bounds(disc.bounds,max_keep)):
                keep=(self.r.pathway_main_chip_keepout if gi<len(self.chips) else self.r.pathway_static_keepout)
                if not self._bounds_within_gap(disc.bounds,g.geom.bounds,keep):
                    continue
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
            # The last segment of this front is indexed directly; never walk the entire
            # board's segment history for a one-terminal repair.
            for rec in reversed(self.path_segments_by_front.get(f['id'],())):
                if not rec.get('_retired') and math.hypot(rec['end'][0]-b[0],rec['end'][1]-b[1])<1e-5:
                    rec['end']=end; rec['geom']=self._corridor_geom(f,a,end); break
            self._rebuild_path_index_and_coverage(rebuild_local_coverage=bool(f.get('local_gap')))
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
                    max_keep=max(self.r.pathway_main_chip_keepout,self.r.pathway_static_keepout)
                    for gi,g in self.static_index.query(expand_bounds(disc.bounds,max_keep)):
                        keep=(self.r.pathway_main_chip_keepout if gi<len(self.chips) else self.r.pathway_static_keepout)
                        if not self._bounds_within_gap(disc.bounds,g.geom.bounds,keep):
                            continue
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
        a=self._rebase_singleton_to_materialized_head(a,ta)
        b=self._rebase_singleton_to_materialized_head(b,tb)
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
        self._retire_front_segments(f['id'])
        f['path']=[f['path'][0]]; f['route_history']=[]
        for key in ('dir','travel','gestures','local_gestures','turn_cooldown','straight_since_turn','last_turn_sign','branch_stage','branch_turn','max_origin_distance','stagnant_gestures'):
            if key in snap: f[key]=snap[key]
        f['turn_history']=list(snap.get('turn_history',[]))
        del f['normal_segment_lengths'][snap.get('normal_len_count',0):]
        f['failures']=0; f['reroute_pending']=False; f['quality_repair_pending']=False
        f['reroute_mode_rounds']=3; f['status']='parked_repair'; f['lifecycle']='RECOVERING'; f['termination_reason']=None
        self._rebuild_path_index_and_coverage(rebuild_local_coverage=bool(f.get('local_gap')))
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
        # Usually one route is the culprit. Try each eligible blocker independently.  Snapshot
        # only that blocker's owned segment tail; copying the entire board's route history here
        # made one rare terminal negotiation scale with total logical territory.
        for blocker in blockers[:2]:
            saved_front=copy.deepcopy(blocker)
            saved_segments=[dict(rec) for rec in self.path_segments_by_front.get(blocker['id'],()) if not rec.get('_retired')]
            if not self._rewind_terminal_blocker_to_prefix(blocker): continue
            blocker['status']='parked_repair'
            if not self._try_connect_specific_terminal_heads(a,ta,b,tb):
                self.fronts[blocker['id']]=saved_front
                self.path_segments.extend(saved_segments)
                self._rebuild_path_index_and_coverage(rebuild_local_coverage=bool(saved_front.get('local_gap')))
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
        """Bounded spatial sweep for obvious compatible MAIN-family terminal joins."""
        terms=[]
        for f in self.fronts.values():
            if (f.get('status')=='terminated' and not f.get('local_gap') and f.get('chip',9999)<len(self.chips)
                    and len(f.get('ids',()))==1 and f['ids'][0] not in self.connected_trace_ids):
                tid=f['ids'][0]; pts=self._materialized_paths(f).get(tid,[])
                if len(pts)>=2: terms.append((f,tid,pts[-1],pts[-2]))
        max_d=6.5*self.module
        index=SpatialHash(max(max_d,80.0*self.U,1e-6)); order={}
        for i,rec in enumerate(terms):
            order[(rec[0]['id'],rec[1])]=i; x,y=rec[2]; index.insert(rec,(x,y,x,y))
        pairs=[]
        for i,a in enumerate(terms):
            ax,ay=a[2]
            nearby=index.query((ax-max_d,ay-max_d,ax+max_d,ay+max_d))
            nearby=sorted((b for b in nearby if order[(b[0]['id'],b[1])]>i),key=lambda b:order[(b[0]['id'],b[1])])
            for b in nearby:
                if not self._connection_family_compatible(a[0],b[0]): continue
                d=math.hypot(b[2][0]-a[2][0],b[2][1]-a[2][1])
                if d>max_d or d<.35*self.module: continue
                ux=(b[2][0]-a[2][0])/d; uy=(b[2][1]-a[2][1])/d
                av=(a[2][0]-a[3][0],a[2][1]-a[3][1]); bv=(b[2][0]-b[3][0],b[2][1]-b[3][1])
                al=max(1e-9,math.hypot(*av)); bl=max(1e-9,math.hypot(*bv))
                facing=(av[0]/al*ux+av[1]/al*uy>-0.05 and bv[0]/bl*(-ux)+bv[1]/bl*(-uy)>-0.05)
                if facing: pairs.append((0 if a[0]['chip']!=b[0]['chip'] else 1,d,a,b))
        pairs.sort(key=lambda z:(z[0],z[1],z[2][0]['id'],z[3][0]['id']))
        used=set(); made=0
        for _cross_rank,_d,a,b in pairs:
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
        # Same connected-neighbour relation as the historical all-pairs expansion, enumerated
        # once through a spatial broad phase.
        adj={fid:set() for fid in by_front}
        for a,b in self._terminal_conflict_pairs(discs,extra_gap=.50*self.module):
            fa,fb=a[0]['id'],b[0]['id']; adj.setdefault(fa,set()).add(fb); adj.setdefault(fb,set()).add(fa)
        stack=list(sorted(cluster))
        while stack:
            fid=stack.pop()
            for nb in sorted(adj.get(fid,())):
                if nb not in cluster: cluster.add(nb); stack.append(nb)
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
                max_keep=max(self.r.pathway_main_chip_keepout,self.r.pathway_static_keepout)
                for gi,obj in self.static_index.query(expand_bounds(disc.bounds,max_keep)):
                    keep=(self.r.pathway_main_chip_keepout if gi<len(self.chips) else self.r.pathway_static_keepout)
                    if not self._bounds_within_gap(disc.bounds,obj.geom.bounds,keep):
                        continue
                    if disc.intersects(obj.geom) or disc.distance(obj.geom)<keep:
                        bad=True; break
                if not bad: cand.append((frac,end,disc))
            if not cand: return False
            opts.append(cand)
        outside=[rec for rec in discs if rec[0]['id'] not in cluster]
        # Outside markers are immutable throughout this tiny solver.  Preserve the historical
        # global-conflict predicate by evaluating outside-vs-outside once, then spatially query
        # only outside markers near each candidate cluster disc.
        outside_conflict=bool(self._first_terminal_conflict(outside))
        outside_index=SpatialHash(max(32.0*self.U,4.0*self.r.termination_dot_min_gap))
        for rec in outside:
            outside_index.insert(rec,rec[3].bounds)
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
                cdiscs=[x[2] for x in combo]; ok=not outside_conflict
                for i,a in enumerate(cdiscs):
                    if not ok: break
                    for b in cdiscs[i+1:]:
                        if a.intersects(b) or a.distance(b)<self.r.termination_dot_min_gap:
                            ok=False; break
                    if not ok: break
                    for rec in outside_index.query(expand_bounds(a.bounds,self.r.termination_dot_min_gap)):
                        if a.intersects(rec[3]) or a.distance(rec[3])<self.r.termination_dot_min_gap:
                            ok=False; break
                if not ok: continue
                exact_tries+=1
                if exact_tries>24: return False
                moved_ids={f['id'] for f,choice in zip(fronts,combo) if choice[0]>0}
                saved=[]
                for f,choice in zip(fronts,combo):
                    _frac,end,_disc=choice; old_end=f['path'][-1]; old_travel=f['travel']
                    a=f['path'][-2]; shift=math.hypot(old_end[0]-end[0],old_end[1]-end[1])
                    rec_hit=None
                    for rec in reversed(self.path_segments_by_front.get(f['id'],())):
                        if not rec.get('_retired') and math.hypot(rec['end'][0]-old_end[0],rec['end'][1]-old_end[1])<1e-5:
                            rec_hit=rec; break
                    saved.append((f,old_end,old_travel,rec_hit, None if rec_hit is None else rec_hit['end'], None if rec_hit is None else rec_hit['geom']))
                    f['path'][-1]=end; f['travel']=max(0.0,old_travel-shift)
                    if rec_hit is not None:
                        rec_hit['end']=end; rec_hit['geom']=self._corridor_geom(f,a,end)
                self._rebuild_path_index_and_coverage(rebuild_local_coverage=any(f.get('local_gap') for f in fronts))
                # Marker-vs-marker legality for this combo was proved immediately above against
                # every immutable outside marker and every cluster peer.  Rebuilding *all*
                # terminal discs and repeating the global conflict sweep here is therefore
                # redundant.  Only the moved discs need the separate foreign-trace predicate.
                valid=True
                for f,choice in zip(fronts,combo):
                    if f['id'] not in moved_ids:
                        continue
                    disc=choice[2]; anc=self._ancestor_front_ids(f)
                    for rec in self.path_index.query(expand_bounds(disc.bounds,self.r.pathway_interroute_keepout)):
                        if rec['front']==f['id'] or rec['front'] in anc: continue
                        if disc.intersects(rec['geom']) or disc.distance(rec['geom'])<self.r.pathway_interroute_keepout:
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
                self._rebuild_path_index_and_coverage(rebuild_local_coverage=any(f.get('local_gap') for f in fronts))
        return False
        return False

    def _repair_terminal_marker_conflicts(self):
        """Keep V21's doubled termination dots physically separated.

        Termination decisions can be made by different fronts in different rounds, so the
        ordinary lane-pitch rule alone cannot guarantee that their final discs fit together.
        Repair is intentionally local and bounded: one conflicting terminal front is reopened
        and asked to escape/separate while the rest of the network remains frozen.
        """
        # First remove *all* optional local-marker conflicts in one batch.  V37 can carry well
        # over a hundred local fillers; pruning one corpse and rebuilding the whole spatial/
        # service index after every pair made marker cleanup dominate runtime.  Greedy deletion
        # is deterministic and safe because local fillers are optional and main geometry wins.
        terms=[f for f in self.fronts.values() if f.get('status')=='terminated']
        initial=[]
        for f in terms:
            for tid,p,d,r in self._terminal_marker_discs(f): initial.append((f,tid,p,d,r))
        victims=set()
        for a,b in self._terminal_conflict_pairs(initial):
            if a[0]['id'] in victims or b[0]['id'] in victims: continue
            locals_=[x[0] for x in (a,b) if x[0].get('local_gap') or x[0].get('chip',-1)>=len(self.chips)]
            if not locals_: continue
            victim=sorted({f['id']:f for f in locals_}.values(),
                          key=lambda f:(f.get('travel',0.0),len(f.get('ids',())),f['id']))[0]
            victims.add(victim['id'])
        if victims:
            for fid in sorted(victims):
                vf=self.fronts[fid]; vf['status']='abandoned_short'; vf['termination_reason']='local_marker_conflict'
            self._prune_abandoned_local_segments(victims)

        for _ in range(8):
            terms=[f for f in self.fronts.values() if f.get('status')=='terminated']
            discs=[]
            for f in terms:
                for tid,p,d,r in self._terminal_marker_discs(f): discs.append((f,tid,p,d,r))
            conflict=self._first_terminal_conflict(discs)
            if conflict is None: break
            # Local filler traces are optional.  Do not run the expensive main-network terminal
            # negotiation/cluster solver for a decorative marker conflict: discard the shorter
            # conflicting local cohort, remove its invisible history from occupancy/service, and
            # continue.  Main-main conflicts still receive the full bounded repair machinery.
            local_conflict=[x[0] for x in conflict if x[0].get('local_gap') or x[0].get('chip',-1)>=len(self.chips)]
            if local_conflict:
                victim=sorted({f['id']:f for f in local_conflict}.values(),
                              key=lambda f:(f.get('travel',0.0),len(f.get('ids',())),f['id']))[0]
                victim['status']='abandoned_short'; victim['termination_reason']='local_marker_conflict'
                self._prune_abandoned_local_segments([victim['id']])
                continue
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
        final_conflict=self._first_terminal_conflict(final_discs)
        if final_conflict is not None:
            self._try_terminal_marker_cluster_stagger(final_discs,final_conflict)

        # Local-gap networks are optional fillers.  If an otherwise irreparable doubled-dot
        # conflict involves one of them, discard that local terminal cohort instead of leaving
        # a hard visual violation or perturbing the already-good main network.
        final_local_victims=[]
        for _ in range(8):
            terms=[f for f in self.fronts.values() if f.get('status')=='terminated']
            discs=[]
            for f in terms:
                for tid,p,d,r in self._terminal_marker_discs(f): discs.append((f,tid,p,d,r))
            conflict=self._first_terminal_conflict(discs)
            if conflict is None: break
            locals_=[x[0] for x in conflict if x[0].get('local_gap') or x[0].get('chip',-1)>=len(self.chips)]
            if not locals_: break
            victim=sorted({f['id']:f for f in locals_}.values(),key=lambda f:(f.get('travel',0.0),len(f.get('ids',())),f['id']))[0]
            victim['status']='abandoned_short'; victim['termination_reason']='local_marker_conflict'
            final_local_victims.append(victim['id'])
        if final_local_victims:
            self._prune_abandoned_local_segments(final_local_victims)

        # Report any conflict that genuinely has no legal local repair.
        terms=[f for f in self.fronts.values() if f.get('status')=='terminated']
        discs=[]
        for f in terms:
            for tid,p,d,r in self._terminal_marker_discs(f): discs.append((f,tid,p,d,r))
        self.stats['pathway_termination_marker_overlap_count']=len(self._terminal_conflict_pairs(discs))

    def _front_visible_grammar_ok(self,f):
        paths=self._materialized_paths(f)
        for pts in paths.values():
            if len(pts)<2: return False
            if self._points_have_compensating_zigzag(pts): return False
            if not self._exact_path_grammar_ok(pts): return False
        return True

    def _repair_main_preflight_front(self,f):
        """Causal preflight repair with a visible-prefix checkpoint fallback.

        First perform the genuine V34/V37 operation: reopen the offending main child,
        traceback committed history, blacklist the replay corridor, and regrow against the
        frozen main network.  A shared-prefix child can occasionally have no legal local tail
        even though its inherited physical lane is already long and perfectly valid.  In that
        case the old code left the failed repair *active* and rejected the whole logical sample.
        V37 now restores the original state and, only after real reroute has been exhausted,
        terminates that one lane at its last valid inherited prefix checkpoint.  No lane is
        deleted and no invalid tail is allowed to survive.
        """
        if f is None or f.get('local_gap') or f.get('chip',len(self.chips))>=len(self.chips): return False
        if f.get('status') not in ('terminated','escaped'): return False
        if any(tid in self.connected_trace_ids for tid in f.get('ids',())): return False
        import copy
        saved_front=copy.deepcopy(f)
        saved_segments=[dict(rec) for rec in self.path_segments_by_front.get(f['id'],()) if not rec.get('_retired')]
        old_status=f.get('status'); old_reason=f.get('termination_reason')
        f['status']='active'; f['lifecycle']='RECOVERING'; f['termination_reason']=None
        # Roll back enough history to cross the decision that produced the bad visible tail.
        f['reroute_attempts']=min(1,f.get('reroute_attempts',0))
        removed=self._traceback_for_reroute(f)
        if removed>0:
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

        # Restore exactly before considering the bounded fallback.  The previous implementation
        # could leave a failed repair active with mutated history, making a later preflight both
        # misleading and expensive.
        f=self._restore_front_owned_snapshot(saved_front,saved_segments,rebuild_local_coverage=False)

        # Shared-prefix fallback: if every physical lane already owns a sufficiently long,
        # grammar-clean inherited prefix, drop only this invalid local tail and terminate at the
        # checkpoint.  This is not a substitute for rerouting: it is reached only after the real
        # rollback/regrow attempt above has no legal alternate corridor.
        if f.get('parent') is not None and f.get('prefixes'):
            prefixes=[list(f.get('prefixes',{}).get(tid,())) for tid in f.get('ids',())]
            def _prefix_ok(pts):
                if len(pts)<2: return False
                length=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:]))
                if length < self.main_launch_preferred_terminal_modules*self.module-1e-7: return False
                if self._points_have_compensating_zigzag(pts): return False
                return self._exact_path_grammar_ok(pts)
            if prefixes and all(_prefix_ok(pts) for pts in prefixes):
                self._retire_front_segments(f['id'])
                f['path']=[f['path'][0]]
                f['route_history']=[]
                # Orient terminal bookkeeping to the actual visible incoming prefix tail.
                tail_dirs=[nearest_dir_index(pts[-1][0]-pts[-2][0],pts[-1][1]-pts[-2][1]) for pts in prefixes]
                if tail_dirs and len(set(tail_dirs))==1:
                    f['dir']=tail_dirs[0]
                f['status']='terminated'; f['lifecycle']='TERMINAL'
                f['termination_reason']='preflight_valid_prefix_checkpoint'
                f['reroute_pending']=False; f['reroute_ready_round']=None
                f['quality_repair_pending']=False; f['quality_repair_reason']=None
                self._rebuild_path_index_and_coverage(rebuild_local_coverage=False)
                if self._front_visible_grammar_ok(f):
                    self.stats['pathway_preflight_prefix_checkpoint_count']=self.stats.get('pathway_preflight_prefix_checkpoint_count',0)+1
                    self.stats['pathway_preflight_causal_repair_success_count']=self.stats.get('pathway_preflight_causal_repair_success_count',0)+1
                    return True

        # Fallback itself was not viable: restore the original terminal/escaped state exactly.
        f=self._restore_front_owned_snapshot(saved_front,saved_segments,rebuild_local_coverage=False)
        f['status']=old_status; f['termination_reason']=old_reason
        return False

    def _preflight_rollback_front_tail_exact(self,f,count):
        """Rollback exactly ``count`` owned gestures for one local preflight transaction."""
        count=max(0,min(int(count),len(f.get('path',()))-1,len(f.get('route_history',()))))
        owned=self.path_segments_by_front.setdefault(f['id'],[])
        removed=0
        for _ in range(count):
            snap=f['route_history'].pop(); f['path'].pop()
            f['dir']=snap['dir']; f['travel']=snap['travel']; f['gestures']=snap['gestures']
            f['local_gestures']=snap['local_gestures']; f['turn_cooldown']=snap['turn_cooldown']
            f['straight_since_turn']=snap['straight_since_turn']; f['last_turn_sign']=snap['last_turn_sign']
            f['branch_stage']=snap['branch_stage']; f['branch_turn']=snap['branch_turn']
            f['max_origin_distance']=snap.get('max_origin_distance',f.get('max_origin_distance',0.0))
            f['stagnant_gestures']=snap.get('stagnant_gestures',0)
            f['turn_history']=list(snap.get('turn_history',[]))
            del f['normal_segment_lengths'][snap['normal_len_count']:]
            if not owned:
                raise RuntimeError(f'preflight rollback ownership invariant failed (sample_seed={self.sseed}, front={f["id"]})')
            rec=owned.pop(); rec['_retired']=True; removed+=1
        if removed:
            self._rebuild_path_index_and_coverage(rebuild_local_coverage=False)
        self._sync_source_egress_reservation_for_front(f)
        return removed

    def _repair_main_stalled_side_progress(self,stats):
        """Physically extend a visibly short main side without weakening its 8-module rule.

        Terminal/source-marker clipping can make a lane whose routed centreline was already
        mature render a fraction below the hard visible 8-module side-progress threshold.  The
        repair reopens exactly one diagnosed physical lane and extends it through ordinary
        proposal generation, ``_gesture_clear`` and ``_accept``.  A singleton is repaired in
        place.  When the useful lane still belongs to a terminated multi-lane cohort, only an
        *outer* lane may be peeled into a recovery singleton; interior lanes are never punched
        out of a bundle.  The remaining cohort stays terminated and visually unchanged.

        No threshold, clearance, turn rule or admission gate is bypassed.  The 9-module raw
        target leaves enough headroom for terminal-dot backoff before the caller rematerializes
        and re-audits the complete network.
        """
        details=list(stats.get('pathway_main_stalled_side_details',()))
        if not details:
            return False
        import copy

        def lane_length(front,tid):
            pts=self._materialized_paths(front).get(tid,())
            return sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:]))

        def extend_singleton(front,tid):
            target=9.0*self.module; moved=0
            while moved<4 and lane_length(front,tid)<target:
                variants=self._proposal_variants(front,count=3)
                if not variants:
                    break
                self._accept(front,variants[0],defer_post=True); moved+=1
            if moved and lane_length(front,tid)>=target and self._front_visible_grammar_ok(front):
                front['status']='terminated'; front['lifecycle']='TERMINAL'
                front['termination_reason']='preflight_visible_side_progress'
                return True
            return False

        def rollback_regrow_singleton(saved_front,saved_segments,tid):
            max_depth=min(6,len(saved_front.get('path',()))-1,len(saved_front.get('route_history',())))
            if max_depth<=0:
                return False
            for depth in range(1,max_depth+1):
                # Fresh deep copies are mandatory: a failed shallow attempt may mutate RNG,
                # route history, reservation activity and path records.  No attempt may inherit it.
                trial_front=copy.deepcopy(saved_front)
                trial_segments=[dict(rec) for rec in saved_segments]
                front=self._restore_front_owned_snapshot(trial_front,trial_segments,rebuild_local_coverage=False)
                self._sync_source_egress_reservation_for_front(front)
                front['status']='active'; front['lifecycle']='RECOVERING'; front['termination_reason']=None
                front['reroute_pending']=False; front['reroute_ready_round']=None
                front['quality_repair_pending']=False; front['quality_repair_reason']=None
                if self._preflight_rollback_front_tail_exact(front,depth)<=0:
                    continue
                if self._try_young_survival_beam(front,target_modules=9.0,horizon=4,beam_width=10):
                    self._capture_source_egress_survival_prefix(front)
                    self._sync_source_egress_reservation_for_front(front)
                    if lane_length(front,tid)>=9.0*self.module-1e-7 and self._front_visible_grammar_ok(front):
                        front['status']='terminated'; front['lifecycle']='TERMINAL'
                        front['termination_reason']='preflight_visible_side_progress_rollback_regrow'
                        self.stats.setdefault('pathway_visible_side_progress_rollback_regrow_count',0)
                        self.stats['pathway_visible_side_progress_rollback_regrow_count']+=1
                        return True
            # Restore the pristine original transaction on total failure.
            front=self._restore_front_owned_snapshot(copy.deepcopy(saved_front),[dict(rec) for rec in saved_segments],rebuild_local_coverage=False)
            self._sync_source_egress_reservation_for_front(front)
            return False

        def prefix_checkpoint_regrow_singleton(saved_front,saved_segments,tid):
            """Rollback a child singleton inside its inherited visible prefix, then regrow.

            Split/detached children can own almost no centerline tail: their 4-6 module visible
            corpse lives in ``prefixes[tid]``.  Truncate only this trace's inherited prefix to an
            earlier checkpoint, leaving every sibling front untouched, and search an ordinary
            legal continuation from that exact physical point.  Every attempt starts from a fresh
            snapshot and total failure restores the original terminal child exactly.
            """
            realised=list(self._materialized_paths(saved_front).get(tid,()))
            if len(realised)<3:
                return False
            # Try nearest checkpoints first, then progressively earlier ones.  Keep at least the
            # first perpendicular emergence gesture; never rewrite the chip-side source point.
            cuts=list(range(len(realised)-2,0,-1))[:8]
            for cut in cuts:
                trial_front=copy.deepcopy(saved_front)
                trial_segments=[dict(rec) for rec in saved_segments]
                front=self._restore_front_owned_snapshot(trial_front,trial_segments,rebuild_local_coverage=False)
                self._sync_source_egress_reservation_for_front(front)
                self._retire_front_segments(front['id'])
                prefix=[tuple(x) for x in realised[:cut+1]]
                if len(prefix)<2:
                    continue
                d=exact_dir8_index(prefix[-1][0]-prefix[-2][0],prefix[-1][1]-prefix[-2][1])
                if d is None or not self._exact_path_grammar_ok(prefix):
                    continue
                front['prefixes'][tid]=prefix
                front['path']=[prefix[-1]]
                front['offsets'][tid]=0.0
                front['dir']=d
                front['route_history']=[]
                front['normal_segment_lengths']=[]
                front['travel']=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(prefix,prefix[1:]))
                dirs=[exact_dir8_index(b[0]-a[0],b[1]-a[1]) for a,b in zip(prefix,prefix[1:])]
                signs=[]
                for da,db in zip(dirs,dirs[1:]):
                    dd=(db-da)%8; signs.append(1 if dd==1 else -1 if dd==7 else 0)
                front['gestures']=max(1,len(prefix)-1); front['local_gestures']=front['gestures']
                front['last_turn_sign']=next((x for x in reversed(signs) if x),0)
                straight=0
                for x in reversed(signs):
                    if x: break
                    straight+=1
                front['straight_since_turn']=straight
                front['turn_cooldown']=0
                front['turn_history']=signs[-7:]
                front['recovery_floor_segments']=0
                front['status']='active'; front['lifecycle']='RECOVERING'; front['termination_reason']=None
                front['reroute_pending']=False; front['reroute_ready_round']=None
                front['quality_repair_pending']=False; front['quality_repair_reason']=None
                self._rebuild_path_index_and_coverage(rebuild_local_coverage=False)
                if self._try_young_survival_beam(front,target_modules=9.0,horizon=5,beam_width=12):
                    if lane_length(front,tid)>=9.0*self.module-1e-7 and self._front_visible_grammar_ok(front):
                        front['status']='terminated'; front['lifecycle']='TERMINAL'
                        front['termination_reason']='preflight_visible_side_progress_prefix_regrow'
                        self.stats.setdefault('pathway_visible_side_progress_prefix_regrow_count',0)
                        self.stats['pathway_visible_side_progress_prefix_regrow_count']+=1
                        return True
            front=self._restore_front_owned_snapshot(copy.deepcopy(saved_front),[dict(rec) for rec in saved_segments],rebuild_local_coverage=False)
            self._sync_source_egress_reservation_for_front(front)
            return False

        repaired=False
        for detail in details:
            side_done=False
            for cand in detail.get('candidates',()):
                fid=cand.get('front'); tid=cand.get('tid'); f=self.fronts.get(fid)
                if (f is None or f.get('local_gap') or f.get('chip',len(self.chips))>=len(self.chips) or
                        f.get('status')!='terminated' or tid not in f.get('ids',()) or
                        tid in self.connected_trace_ids):
                    continue

                # Ordinary singleton: transactional local extension.
                if len(f.get('ids',()))==1:
                    saved_front=copy.deepcopy(f)
                    saved_segments=[dict(rec) for rec in self.path_segments_by_front.get(fid,()) if not rec.get('_retired')]
                    f=self._rebase_singleton_to_materialized_head(f,tid)
                    f['status']='active'; f['lifecycle']='RECOVERING'; f['termination_reason']=None
                    f['reroute_pending']=False; f['reroute_ready_round']=None
                    f['quality_repair_pending']=False; f['quality_repair_reason']=None
                    if extend_singleton(f,tid):
                        repaired=True; side_done=True
                        break
                    self._restore_front_owned_snapshot(copy.deepcopy(saved_front),[dict(rec) for rec in saved_segments],rebuild_local_coverage=False)
                    self._sync_source_egress_reservation_for_front(self.fronts[fid])
                    if rollback_regrow_singleton(saved_front,saved_segments,tid):
                        repaired=True; side_done=True
                        break
                    if prefix_checkpoint_regrow_singleton(saved_front,saved_segments,tid):
                        repaired=True; side_done=True
                        break
                    continue

                # Dense-board edge case: the longest physical lane can still be embedded in a
                # terminated cohort.  Reuse the existing edge-lane detach operation, but only as
                # a recovery transaction.  Failure removes the child and restores the parent
                # (including its RNG) exactly; success preserves every old visible prefix and
                # appends one ordinary legal singleton continuation.
                ordered=sorted(f['ids'],key=lambda x:f['offsets'][x])
                if tid not in (ordered[0],ordered[-1]):
                    continue
                saved_parent=copy.deepcopy(f); saved_next_front=self.next_front_id
                saved_detached=self.stats.get('pathway_close_head_lane_detach_count',0)
                saved_lock=self.stats.get('pathway_detached_prefix_lock_count',0)
                old_reason=f.get('termination_reason')
                f['status']='active'; f['lifecycle']='RECOVERING'; f['termination_reason']=None
                child=self._detach_trace_as_singleton(f,tid)
                if child is None or child is f:
                    self.fronts[fid]=saved_parent
                    continue
                # Sibling lanes were terminal before recovery and stay terminal.
                f['status']='terminated'; f['lifecycle']='TERMINAL'; f['termination_reason']=old_reason
                child['status']='active'; child['lifecycle']='RECOVERING'; child['termination_reason']=None
                child['reroute_pending']=False; child['reroute_ready_round']=None
                child['quality_repair_pending']=False; child['quality_repair_reason']=None
                if extend_singleton(child,tid):
                    self.stats.setdefault('pathway_visible_side_progress_fragment_count',0)
                    self.stats['pathway_visible_side_progress_fragment_count']+=1
                    repaired=True; side_done=True
                    break

                self._retire_front_segments(child['id'])
                self._drop_front(child['id'])
                self.fronts[fid]=saved_parent
                self.next_front_id=saved_next_front
                self.stats['pathway_close_head_lane_detach_count']=saved_detached
                self.stats['pathway_detached_prefix_lock_count']=saved_lock
                self._rebuild_path_index_and_coverage(rebuild_local_coverage=False)
            if side_done:
                self.stats.setdefault('pathway_visible_side_progress_repair_count',0)
                self.stats['pathway_visible_side_progress_repair_count']+=1
        if repaired:
            self._rebuild_path_index_and_coverage(rebuild_local_coverage=False)
        return repaired

    def _reset_materialization_pass_diagnostics(self):
        """Reset counters that describe one rendered-admission/materialization pass.

        Preflight may materialize the same frozen logical network several times while testing a
        bounded repair.  These counters describe the *current* visible candidate and therefore
        must never accumulate across speculative attempts.
        """
        for k in ('pathway_zigzag_trace_cleanup_count','pathway_intersection_trace_cleanup_count',
                  'pathway_duplicate_trace_cleanup_count','pathway_clearance_trace_cleanup_count',
                  'pathway_static_clearance_trace_cleanup_count',
                  'pathway_static_clearance_visible_primitive_cleanup_count'):
            self.stats[k]=0
        self.stats['pathway_zigzag_cleanup_details']=[]
        self.stats['pathway_intersection_cleanup_pairs']=[]
        self.stats['pathway_clearance_cleanup_pairs']=[]
        self.stats['pathway_duplicate_cleanup_pairs']=[]

    @staticmethod
    def _main_preflight_hard_metric_keys():
        return (
            'pathway_main_short_termination_trace_count','pathway_main_stalled_side_count',
            'pathway_main_active_unmaterialized_launch_trace_count',
            'pathway_illegal_turn_count','pathway_non_octilinear_segment_count',
            'pathway_illegal_connection_junction_turn_count','pathway_curved_primitive_count',
            'pathway_unmarked_stroke_overlap_count','pathway_unmarked_clearance_violation_count',
            'pathway_unmarked_overlap_count','pathway_static_intersection_count')

    def _main_rendered_prefix_checkpoint_candidate(self,f,tid,blocker_front_id=None,blocker_tid=None):
        """Return the latest already-rendered safe prefix for one mature terminated launch.

        This fallback is intentionally narrower than rerouting. It is considered only after the
        ordinary causal reroute/checkpoint operation fails. The candidate must end at an existing
        rendered vertex, remain at least six visible modules long, preserve exact octilinear
        grammar, and be visibly clear of the diagnosed blocker including a conservative terminal
        marker envelope. The complete network is rematerialized transactionally before commit.
        """
        if (f is None or f.get('status')!='terminated' or f.get('local_gap') or
                len(f.get('ids',()))!=1 or tid not in f.get('ids',()) or
                tid in self.connected_trace_ids):
            return None
        pts=list(self._materialized_paths(f).get(tid,()))
        if len(pts)<3:
            return None
        blocker=None; blocker_t=None
        if blocker_front_id is not None and blocker_tid is not None:
            bf=self.fronts.get(blocker_front_id)
            if bf is not None and blocker_tid in bf.get('ids',()):
                bpts=list(self._materialized_paths(bf).get(blocker_tid,()))
                if len(bpts)>=2:
                    blocker=prim_polyline(bpts,bf['thicknesses'][blocker_tid],self.r.FG,round_caps=False).geom
                    blocker_t=float(bf['thicknesses'][blocker_tid])
        t=float(f['thicknesses'][tid])
        preferred=self.main_launch_preferred_terminal_modules*self.module
        for cut in range(len(pts)-1,1,-1):
            cand=pts[:cut]
            length=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(cand,cand[1:]))
            if length < preferred-1e-7:
                break
            if self._points_have_compensating_zigzag(cand) or not self._exact_path_grammar_ok(cand):
                continue
            if blocker is not None:
                cgeom=prim_polyline(cand,t,self.r.FG,round_caps=False).geom
                gap=self._interroute_gap_for_fronts(f,other_thickness=blocker_t,other_local=False)
                if cgeom.intersects(blocker) or cgeom.distance(blocker)<gap-1e-7:
                    continue
                radius=self.r._termination_dot_radius(t)+.5*self.r.termination_dot_hollow_stroke
                disc=Point(cand[-1]).buffer(radius,quad_segs=12)
                if disc.intersects(blocker) or disc.distance(blocker)<gap-1e-7:
                    continue
            return cand
        return None

    def _apply_main_rendered_prefix_checkpoint(self,f,tid,candidate):
        """Replace one terminated singleton tail by an already-rendered physical prefix."""
        if not candidate or len(candidate)<2:
            return False
        self._retire_front_segments(f['id'])
        f['prefixes'][tid]=list(candidate)
        f['path']=[tuple(candidate[-1])]
        f['offsets'][tid]=0.0
        f['route_history']=[]
        f['recovery_floor_segments']=0
        f['local_gestures']=0
        f['dir']=nearest_dir_index(candidate[-1][0]-candidate[-2][0],
                                   candidate[-1][1]-candidate[-2][1])
        f['travel']=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(candidate,candidate[1:]))
        f['status']='terminated'; f['lifecycle']='TERMINAL'
        f['termination_reason']='preflight_rendered_prefix_checkpoint'
        f['reroute_pending']=False; f['reroute_ready_round']=None
        f['quality_repair_pending']=False; f['quality_repair_reason']=None
        f['branch_stage']=None; f['branch_turn']=None
        return True

    def _transactional_main_preflight_attempt(self,f,baseline_stats,target_tid=None,
                                              blocker_front_id=None,blocker_tid=None):
        """Try one causal front repair and commit only strict rendered-ID improvement.

        The post-repair missing-launch set must be a *proper subset* of the baseline set; count
        improvement alone is insufficient because it could hide an identity swap. Ordinary
        reroute/checkpoint repair is tried first. Only after it fails rendered validation may a
        mature terminated singleton be shortened to its latest already-rendered safe prefix.
        """
        if f is None:
            return (False,baseline_stats)
        import copy
        fid=f['id']
        saved_front=copy.deepcopy(f)
        saved_segments=[dict(rec) for rec in self.path_segments_by_front.get(fid,()) if not rec.get('_retired')]
        saved_stats=copy.deepcopy(self.stats)
        before_missing=set(baseline_stats.get('pathway_main_unaccounted_launch_trace_ids',()))
        before_hard={k:int(baseline_stats.get(k,0) or 0) for k in self._main_preflight_hard_metric_keys()}

        def trial_commit_ok(trial_stats):
            after_missing=set(trial_stats.get('pathway_main_unaccounted_launch_trace_ids',()))
            hard_ok=all(int(trial_stats.get(k,0) or 0) <= before_hard[k]
                        for k in self._main_preflight_hard_metric_keys())
            return after_missing < before_missing and hard_ok

        def note_commit(trial_stats,prefix=False):
            recovered=len(before_missing)-len(set(trial_stats.get('pathway_main_unaccounted_launch_trace_ids',())))
            self.stats.setdefault('pathway_preflight_transaction_commit_count',0)
            self.stats['pathway_preflight_transaction_commit_count']+=1
            self.stats.setdefault('pathway_preflight_transaction_launches_recovered',0)
            self.stats['pathway_preflight_transaction_launches_recovered']+=recovered
            if prefix:
                self.stats.setdefault('pathway_preflight_rendered_prefix_checkpoint_count',0)
                self.stats['pathway_preflight_rendered_prefix_checkpoint_count']+=1

        # 1) Normal causal reroute / inherited-prefix checkpoint.
        locally_repaired=self._repair_main_preflight_front(self.fronts.get(fid))
        if locally_repaired:
            self._reset_materialization_pass_diagnostics()
            _groups,trial_stats=self._materialize(
                preflight_trial=True,preflight_trial_hard_baseline=before_hard)
            if trial_commit_ok(trial_stats):
                note_commit(trial_stats,prefix=False)
                return (True,trial_stats)

        # Restore the exact baseline before the narrower rendered-prefix fallback.
        self._restore_front_owned_snapshot(saved_front,saved_segments,rebuild_local_coverage=False)
        self.stats.clear(); self.stats.update(saved_stats)

        # 2) Mature terminated singleton: keep the latest already-visible prefix before blocker.
        cur=self.fronts.get(fid)
        if target_tid is not None:
            candidate=self._main_rendered_prefix_checkpoint_candidate(
                cur,target_tid,blocker_front_id=blocker_front_id,blocker_tid=blocker_tid)
            if candidate is not None and self._apply_main_rendered_prefix_checkpoint(cur,target_tid,candidate):
                self._rebuild_path_index_and_coverage(rebuild_local_coverage=False)
                self._reset_materialization_pass_diagnostics()
                _groups,trial_stats=self._materialize(
                    preflight_trial=True,preflight_trial_hard_baseline=before_hard)
                if trial_commit_ok(trial_stats):
                    note_commit(trial_stats,prefix=True)
                    return (True,trial_stats)

        # Neither legal operation improved the actual rendered identity set. Roll back exactly
        # and retain the already-materialized baseline diagnostics without paying for another
        # redundant full render pass.
        self._restore_front_owned_snapshot(saved_front,saved_segments,rebuild_local_coverage=False)
        self.stats.clear(); self.stats.update(saved_stats)
        self.stats.setdefault('pathway_preflight_transaction_rollback_count',0)
        self.stats['pathway_preflight_transaction_rollback_count']+=1
        return (False,baseline_stats)

    def _repair_main_preflight_materialization(self,stats):
        """Transactionally repair the causal side of rendered main-network defects.

        Render-cleanup diagnostics are ordered: ``new_front`` is the later trace whose admission
        collided with ``old_front``. Intersection, exact edge-clearance and duplicate suppression
        are all causal local defects and receive the same transactional repair path. Each candidate
        is validated by a fresh rendered pass before it is committed. After every accepted repair
        the diagnostics are refreshed, so stale pairs can never drive a second mutation. The work
        budget is bounded per observed local defect; unresolved geometry remains a hard assertion
        rather than being hidden by whole-sample rejection.
        """
        current_stats=stats
        repaired_any=False
        attempted=set()
        initial_missing=set(current_stats.get('pathway_main_unaccounted_launch_trace_ids',()))
        initial_cleanup_count=(len(current_stats.get('pathway_zigzag_cleanup_details',())) +
                               len(current_stats.get('pathway_intersection_cleanup_pairs',())) +
                               len(current_stats.get('pathway_clearance_cleanup_pairs',())) +
                               len(current_stats.get('pathway_duplicate_cleanup_pairs',())))
        # This is a *local defect* work budget, not a whole-sample retry budget.  A fixed 12
        # transactions per board made large canvases non-total: the 13th independently repairable
        # rendered defect could invalidate the entire seed.  Give each observed defect a small
        # bounded transaction allowance while keeping an absolute safety ceiling.
        defect_count=max(1,len(initial_missing),initial_cleanup_count)
        attempt_cap=min(256,max(12,4*defect_count))
        self.stats['pathway_preflight_local_defect_count']=defect_count
        self.stats['pathway_preflight_local_transaction_budget']=attempt_cap
        attempts=0

        while attempts < attempt_cap:
            missing=set(current_stats.get('pathway_main_unaccounted_launch_trace_ids',()))
            zig=list(current_stats.get('pathway_zigzag_cleanup_details',()))
            pair_groups=(('intersection',list(current_stats.get('pathway_intersection_cleanup_pairs',()))),
                         ('clearance',list(current_stats.get('pathway_clearance_cleanup_pairs',()))),
                         ('duplicate',list(current_stats.get('pathway_duplicate_cleanup_pairs',()))))
            if not missing and not zig and not any(pairs for _kind,pairs in pair_groups):
                break

            candidates=[]
            for d in zig:
                fid=d.get('front')
                if fid is not None:
                    candidates.append((fid,'zigzag',d.get('tid'),None,None))
            for kind,pairs in pair_groups:
                for d in pairs:
                    ntid=d.get('new_tid'); otid=d.get('old_tid')
                    if missing and ntid not in missing and otid not in missing:
                        continue
                    # Repair the actually suppressed launch identity first.  Only if that side is
                    # immutable/unrepairable should its blocker be considered.
                    order=(('new_front','new_tid'),('old_front','old_tid'))
                    if otid in missing and ntid not in missing:
                        order=(('old_front','old_tid'),('new_front','new_tid'))
                    for key,tidkey in order:
                        fid=d.get(key)
                        if fid is not None:
                            blocker_front=(d.get('old_front') if key=='new_front' else d.get('new_front'))
                            blocker_tid=(d.get('old_tid') if key=='new_front' else d.get('new_tid'))
                            candidates.append((fid,kind,d.get(tidkey),blocker_front,blocker_tid))

            progressed=False
            signature=tuple(sorted(missing))
            for fid,kind,tid,blocker_front,blocker_tid in candidates:
                token=(signature,fid,kind,tid)
                if token in attempted:
                    continue
                attempted.add(token)
                self.stats.setdefault('pathway_preflight_candidate_seen_count',0)
                self.stats['pathway_preflight_candidate_seen_count']+=1
                f=self.fronts.get(fid)
                if (f is None or f.get('local_gap') or f.get('chip',len(self.chips))>=len(self.chips) or
                        f.get('status') not in ('terminated','escaped')):
                    self.stats.setdefault('pathway_preflight_candidate_ineligible_count',0)
                    self.stats['pathway_preflight_candidate_ineligible_count']+=1
                    continue
                if any(tid0 in self.connected_trace_ids for tid0 in f.get('ids',())):
                    self.stats.setdefault('pathway_preflight_candidate_connected_count',0)
                    self.stats['pathway_preflight_candidate_connected_count']+=1
                    continue
                # The cap limits expensive transactional mutations, not cheap candidate
                # inspection. V47 previously incremented it before eligibility checks, so an
                # already-connected or otherwise immutable collision participant could consume
                # one of the bounded repair slots without attempting any repair at all.
                attempts+=1
                self.stats.setdefault('pathway_preflight_candidate_attempt_count',0)
                self.stats['pathway_preflight_candidate_attempt_count']+=1
                committed,trial_stats=self._transactional_main_preflight_attempt(
                    f,current_stats,target_tid=tid,blocker_front_id=blocker_front,blocker_tid=blocker_tid)
                current_stats=trial_stats
                if committed:
                    repaired_any=True; progressed=True
                    break
                if attempts>=attempt_cap:
                    break
            if not progressed:
                break

        if repaired_any:
            self._rebuild_path_index_and_coverage(rebuild_local_coverage=False)
        return repaired_any,current_stats

    def _run_main_core_and_preflight(self):
        """Route and validate only the main-chip network.

        V37 deliberately freezes this network before any residual object exists.  Components and
        local fillers can react to the resulting free field, but they may never steer or reroute
        the main-chip network.
        """
        self._launch_fronts()
        self._run_rounds()
        self._connect_near_main_terminals(max_pairs=8)
        _pre_groups,_pre_stats=self._materialize()
        pre_bad=(_pre_stats.get('pathway_visible_launch_trace_count',0) != _pre_stats.get('pathway_launch_trace_count',0) or
                _pre_stats.get('pathway_main_short_termination_trace_count',0) != 0 or
                _pre_stats.get('pathway_main_stalled_side_count',0) != 0 or
                _pre_stats.get('pathway_illegal_turn_count',0) != 0 or
                _pre_stats.get('pathway_non_octilinear_segment_count',0) != 0 or
                _pre_stats.get('pathway_curved_primitive_count',0) != 0 or
                _pre_stats.get('pathway_unmarked_stroke_overlap_count',0) != 0 or
                _pre_stats.get('pathway_unmarked_clearance_violation_count',0) != 0 or
                _pre_stats.get('pathway_unmarked_overlap_count',0) != 0 or
                _pre_stats.get('pathway_static_intersection_count',0) != 0)
        if pre_bad and _pre_stats.get('pathway_main_stalled_side_count',0):
            if self._repair_main_stalled_side_progress(_pre_stats):
                _pre_groups,_pre_stats=self._materialize()
                pre_bad=(_pre_stats.get('pathway_visible_launch_trace_count',0) != _pre_stats.get('pathway_launch_trace_count',0) or
                        _pre_stats.get('pathway_main_short_termination_trace_count',0) != 0 or
                        _pre_stats.get('pathway_main_stalled_side_count',0) != 0 or
                        _pre_stats.get('pathway_illegal_turn_count',0) != 0 or
                        _pre_stats.get('pathway_non_octilinear_segment_count',0) != 0 or
                        _pre_stats.get('pathway_curved_primitive_count',0) != 0 or
                        _pre_stats.get('pathway_unmarked_stroke_overlap_count',0) != 0 or
                        _pre_stats.get('pathway_unmarked_clearance_violation_count',0) != 0 or
                        _pre_stats.get('pathway_unmarked_overlap_count',0) != 0 or
                        _pre_stats.get('pathway_static_intersection_count',0) != 0)
        if pre_bad:
            _preflight_repaired,_trial_stats=self._repair_main_preflight_materialization(_pre_stats)
        else:
            _preflight_repaired,_trial_stats=False,_pre_stats
        if pre_bad and _preflight_repaired:
            for k in ('pathway_zigzag_trace_cleanup_count','pathway_intersection_trace_cleanup_count','pathway_duplicate_trace_cleanup_count'):
                self.stats[k]=0
            self.stats['pathway_zigzag_cleanup_details']=[]; self.stats['pathway_intersection_cleanup_pairs']=[]
            # The transactional trial has already re-materialized the exact repaired visible
            # trace set and checked every repair-sensitive invariant.  Its four expensive
            # whole-board hard audits deliberately carry the last authoritative baseline; the
            # mandatory final materialization in run_main_only() re-audits them before output.
            # Do not perform an otherwise redundant full-board materialization here.
            _pre_groups,_pre_stats=[],_trial_stats
            self.stats.setdefault('pathway_preflight_deferred_full_audit_count',0)
            self.stats['pathway_preflight_deferred_full_audit_count']+=1
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
                'pathway_illegal_turn_count','pathway_non_octilinear_segment_count','pathway_illegal_connection_junction_turn_count','pathway_curved_primitive_count',
                'pathway_unmarked_stroke_overlap_count','pathway_unmarked_clearance_violation_count','pathway_unmarked_overlap_count',
                'pathway_static_intersection_count','pathway_zigzag_trace_cleanup_count',
                'pathway_intersection_trace_cleanup_count','pathway_duplicate_trace_cleanup_count')}
            diag['sample_seed']=int(self.sseed)
            diag['canvas']=[float(self.W),float(self.H)]
            diag['scale']=float(getattr(self.r,'scale',1.0))
            diag['aspect_ratio']=list(getattr(self.r,'aspect_ratio',(1.0,1.0)))
            diag['module_U']=float(self.U)
            diag['zigzag_details']=_pre_stats.get('pathway_zigzag_cleanup_details',[])[:3]
            diag['intersection_cleanup_pairs']=_pre_stats.get('pathway_intersection_cleanup_pairs',[])[:8]
            diag['preflight_causal_repairs']=self.stats.get('pathway_preflight_causal_repair_count',0)
            diag['preflight_causal_repair_successes']=self.stats.get('pathway_preflight_causal_repair_success_count',0)
            diag['preflight_prefix_checkpoints']=self.stats.get('pathway_preflight_prefix_checkpoint_count',0)
            diag['stalled_side_details']=_pre_stats.get('pathway_main_stalled_side_details',[])[:3]
            diag['visible_side_progress_repairs']=self.stats.get('pathway_visible_side_progress_repair_count',0)
            diag['visible_side_progress_fragments']=self.stats.get('pathway_visible_side_progress_fragment_count',0)
            raise RuntimeError('main-network preflight materialization invariant violated: '+json.dumps(diag,sort_keys=True))

    def run_main_only(self):
        self._run_main_core_and_preflight()
        self._repair_terminal_marker_conflicts()
        groups,stats=self._materialize()
        if (stats.get('pathway_visible_launch_trace_count',0) != stats.get('pathway_launch_trace_count',0) or
                stats.get('pathway_main_short_termination_trace_count',0) != 0 or
                stats.get('pathway_main_stalled_side_count',0) != 0 or
                stats.get('pathway_main_unaccounted_launch_trace_count',0) != 0 or
                stats.get('pathway_main_active_unmaterialized_launch_trace_count',0) != 0):
            raise RuntimeError('MAIN launch survival/persistence/accounting invariant violated during materialization')
        if (stats.get('pathway_unmarked_stroke_overlap_count',0) or
                stats.get('pathway_unmarked_clearance_violation_count',0) or
                stats.get('pathway_unmarked_overlap_count',0) or
                stats.get('pathway_static_intersection_count',0)):
            raise RuntimeError('hard main-pathway overlap/clearance invariant violated during materialization')
        if (stats.get('pathway_illegal_turn_count',0) or stats.get('pathway_non_octilinear_segment_count',0) or
                stats.get('pathway_curved_primitive_count',0)):
            raise RuntimeError('hard exact-octilinear / <=45-degree main-turn invariant violated')
        stats['pathway_phase']='main_chip_network_frozen_before_residual_fill'
        return groups,stats

    def _preload_frozen_pathway_groups(self,pathways):
        """Insert each frozen main trace once as exact rendered geometry.

        V47 replays segment centres into the congestion/coverage grids, but does not retain a
        second buffered GEOS obstacle for every segment.  The exact rendered polyline primitive
        is the authoritative immutable obstacle and closes the same joint/clearance geometry.
        """
        synthetic=-1; rendered=[]; replayed_segments=0
        for pg in pathways:
            for prim in pg.primitives:
                svg=prim.svg
                if svg.get('type')!='polyline' or len(svg.get('points',()))<2:
                    continue
                pts=[tuple(p) for p in svg['points']]
                t=float(svg.get('stroke_width',2.55*self.U))
                for a,b in zip(pts,pts[1:]):
                    if math.hypot(b[0]-a[0],b[1]-a[1])<=1e-7:
                        continue
                    replayed_segments+=1
                    self._grid_add_segment(a,b)
                    steps=max(1,int(math.ceil(math.hypot(b[0]-a[0],b[1]-a[1])/(.45*self.module))))
                    for k in range(steps+1):
                        q=k/steps; x=a[0]+(b[0]-a[0])*q; y=a[1]+(b[1]-a[1])*q
                        if 0<=x<=self.W and 0<=y<=self.H:
                            self.coverage_cells.add(self._coverage_cell12((x,y)))
                line=LineString(pts)
                rrec=dict(geom=prim.geom,front=synthetic,root=('frozen_main_render',synthetic,0),chip=-1,
                          start=pts[0],end=pts[-1],round_index=-1,local_gap=False,max_thickness=t,
                          frozen_main=True,frozen_main_render=True,primitive=prim,line=line,points=pts,tid=synthetic)
                synthetic-=1
                rendered.append(rrec); self.path_index.insert(rrec,prim.geom.bounds)
                self.max_committed_path_thickness=max(self.max_committed_path_thickness,t)
        self.frozen_main_render_records=rendered
        self.stats['pathway_local_gap_frozen_main_segment_count']=replayed_segments
        self.stats['pathway_local_gap_frozen_main_retained_segment_buffer_count']=0
        self.stats['pathway_local_gap_frozen_main_render_primitive_count']=len(rendered)

    def _local_gap_realized_trace_count(self):
        """Ordinary population excludes dormant, exact service certificates."""
        return max(0,self.stats.get('pathway_local_gap_trace_count',0)-
                   getattr(self,'_local_gap_dormant_trace_count',0))

    def _local_capacity_service_mask(self,points,thickness):
        """Bounded exact service bits for one packet, without mutating live coverage."""
        nx,ny=self.r.local_gap_grid_shape(); cw=self.W/nx; ch=self.H/ny
        half=self._local_gap_service_halfwidth(dict(ids=(0,),thicknesses={0:thickness}))
        result={}
        for a,b in zip(points,points[1:]):
            vx=b[0]-a[0]; vy=b[1]-a[1]; ll=vx*vx+vy*vy
            if ll<=1e-12: continue
            for gy in range(max(0,int(math.floor((min(a[1],b[1])-half)/ch))),
                            min(ny-1,int(math.floor((max(a[1],b[1])+half)/ch)))+1):
                for gx in range(max(0,int(math.floor((min(a[0],b[0])-half)/cw))),
                                min(nx-1,int(math.floor((max(a[0],b[0])+half)/cw)))+1):
                    cell=(gx,gy)
                    if cell not in self.local_gap_open_cells: continue
                    mask=result.get(cell,0)
                    for sy in range(4):
                        py=(gy+(sy+.5)/4)*ch
                        for sx in range(4):
                            bit=1<<(sy*4+sx)
                            if mask&bit: continue
                            px=(gx+(sx+.5)/4)*cw
                            u=((px-a[0])*vx+(py-a[1])*vy)/ll
                            if 0<=u<=1 and (px-a[0]-u*vx)**2+(py-a[1]-u*vy)**2<=half*half+1e-12:
                                mask|=bit
                    if mask: result[cell]=mask
        return result

    def _prepare_local_gap_capacity(self,round_budget):
        """Reserve exact visible service before ordinary routes fragment the field.

        Certificates are dormant fallback packets.  A seeded ordinary singleton may
        take ownership only after its complete wider visible prefix passes exact
        geometry and preserves every certificate service bit.  Realized roots then
        receive the ordinary affinity, branching and independent tail lifecycle.
        """
        if not self.local_gap_open_cells:
            self.local_gap_open_cells=self._residual_gap_cells()
        self.local_gap_target_fraction=float(getattr(self,'local_gap_absolute_target_fraction',
            self.r.local_gap_fill_range[0]))
        service_cells=max(1,int(self.local_gap_service_denominator_cell_count or len(self.local_gap_open_cells)))
        self.local_gap_target_count=int(round(service_cells*self.local_gap_target_fraction))
        self.stats['pathway_local_gap_fill_target_fraction']=self.local_gap_target_fraction
        self.stats['pathway_local_gap_open_cell_count']=len(self.local_gap_open_cells)
        self.stats['pathway_local_gap_target_cell_count']=self.local_gap_target_count
        hard=float(getattr(self,'local_gap_hard_floor_absolute',
            self.r.local_gap_fill_range[0]*getattr(self,'local_gap_remaining_service_fraction',1.0)))
        if not self.local_gap_open_cells or hard<=0:
            return 0
        self._materialize()
        self._local_gap_deterministic_debt_completion(hard)
        self._materialize()
        packets={rec['tid']:rec for rec in self.trace_records if rec.get('local_gap')}
        self._local_frozen_visible_packets=dict(packets)
        self._local_gap_dormant_trace_count=len(packets)
        self.stats['pathway_local_gap_capacity_reserved_trace_count']=len(packets)
        self.stats['pathway_local_gap_capacity_reserved_service']=self._local_gap_service_fraction()

        # Every index is built once. Replacements retire only their owned entries.
        line_index=SpatialHash(max(70*self.U,2*self.module))
        marker_index=SpatialHash(max(30*self.U,self.module))
        logical_index=SpatialHash(max(30*self.U,self.module))
        self._local_capacity_head_index=SpatialHash(max(30*self.U,self.module))
        entries={}; heads={}
        def insert_packet(rec):
            tid=rec['tid']; f=self.fronts.get(rec['front']); refs=[]
            pts=rec['points']; t=rec['primitive'].svg['stroke_width']
            item=dict(rec,line=LineString(pts),thickness=t,render_order=tid)
            for bounds in self._polyline_spatial_chunk_bounds(pts,line_index.cell_size):
                refs.append((line_index,line_index.insert(item,bounds)))
            if f is not None and f.get('local_gap'):
                terminal=rec.get('terminal_marker')
                if terminal is not None:
                    obj=dict(geom=terminal.geom,front=f['id'],tid=tid)
                    refs.append((marker_index,marker_index.insert(obj,obj['geom'].bounds)))
                radius=self.r._termination_dot_radius(t)+.5*self.r.termination_dot_hollow_stroke
                disc=Point(f['path'][-1]).buffer(radius,quad_segs=12)
                obj=dict(geom=disc,front=f['id'],tid=tid,
                         point=f['path'][-1],radius=radius)
                refs.append((logical_index,logical_index.insert(obj,disc.bounds)))
                end=(tuple(terminal.geom.centroid.coords[0]) if terminal is not None else pts[-1])
                head=LineString([end,f['path'][-1]]).buffer(radius+self.r.pathway_terminal_head_keepout,quad_segs=8)
                obj=dict(geom=head,front=f['id'],tid=tid,released=False)
                refs.append((self._local_capacity_head_index,self._local_capacity_head_index.insert(obj,head.bounds)))
                heads[tid]=obj
            entries[tid]=refs
        for rec in self.trace_records:
            insert_packet(rec)
        rng=SplitMix64(local_pathway_seed(self.sseed)^0x4341504143495459)
        self.local_gap_special_probability=rng.uniform(.15,.26)
        tids=sorted(packets); rng.shuffle(tids)
        realized=0; special_realized=0
        for tid in tids:
            if self._local_gap_realized_trace_count()>=self.r.local_gap_trace_population_cap(): break
            rec=packets[tid]; f=self.fronts[rec['front']]
            if len(f['path'])!=3: continue
            special=rng.random()<self.local_gap_special_probability
            thickness=self._local_gap_bundle_spec(rng,1,special)[0][0]
            rid=f.get('local_gap_region_id')
            region=self.local_gap_regions[rid] if rid is not None and rid<len(self.local_gap_regions) else None
            if region is not None:
                thickness*=.78 if region['size']=='small' else (1.0 if region['size']=='medium' else 1.08)
            tf=dict(f); tf['thicknesses']={tid:thickness}; tf['local_gap_special']=special
            for index,oid in entries.pop(tid): index.remove(oid)
            old_segments=list(self.path_segments_by_front.get(f['id'],()))
            for old in old_segments: self._retire_path_record_incremental(old)
            center,pivot,end=f['path']
            package=self._local_debt_visible_package(tf,center,pivot,end,marker_index,logical_index,line_index)
            if package is not None:
                d0=exact_dir8_index(pivot[0]-center[0],pivot[1]-center[1])
                sf=dict(tf,path=[center],dir=d0,gestures=0,local_gestures=0)
                g1=self._corridor_geom(sf,center,pivot)
                first_clear=self._gesture_clear(sf,center,pivot,g1,allow_outside=False)
                sf.update(path=[center,pivot],gestures=1,local_gestures=1)
                g2=self._corridor_geom(sf,pivot,end)
                if not first_clear or not self._gesture_clear(sf,pivot,end,g2,allow_outside=False,extra_segments=(g1,)):
                    package=None
            if package is not None and not self._local_gap_source_clearance(
                    center,.5*thickness,marker_extent=(.5*thickness if special else
                    self.r._termination_dot_radius(thickness)+.5*self.r.termination_dot_hollow_stroke),
                    cluster_id=f.get('local_fill_cluster_id')):
                package=None
            if package is not None:
                old_mask=self._local_capacity_service_mask(rec['points'],rec['primitive'].svg['stroke_width'])
                new_mask=self._local_capacity_service_mask(package[0],thickness)
                if any(bits&~new_mask.get(cell,0) for cell,bits in old_mask.items()): package=None
            if package is None:
                self.path_segments_by_front[f['id']]=[]
                for old in old_segments:
                    self._record_segment(f,old['start'],old['end'],old['geom'],normal=False)
                insert_packet(rec)
                continue
            f['thicknesses']={tid:thickness}; f['local_gap_special']=special
            self.path_segments_by_front[f['id']]=[]
            for a,b in zip(f['path'],f['path'][1:]):
                self._record_segment(f,a,b,self._corridor_geom(f,a,b),normal=False)
            pts,terminal_geom,_logical,prim,_line=package
            updated=dict(rec,points=pts,primitive=prim)
            # Active roots release their former terminal; no marker remains mid-line.
            updated['terminal_marker']=None if special else Primitive('circle',terminal_geom,{}, {})
            insert_packet(updated)
            # Retain the certificate's old head envelope as a local rollback
            # reserve. Its owner/descendants may continue through it; unrelated
            # ordinary routes cannot consume its already-proven terminal room.
            f['_local_capacity_visible_floor']=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:]))
            self._local_frozen_visible_packets.pop(tid,None)
            self._local_gap_dormant_trace_count-=1
            f['status']='active'; f['lifecycle']='ACTIVE'; f['termination_reason']=None
            f['local_gap_turn_due_straights']=1+int(rng.random()*3)
            f['local_gap_branch_boost']=rng.uniform(*self.r.local_gap_branch_boost_range)
            f['local_gap_exit_allowed']=rng.random()<self.r.local_gap_exit_probability_factor
            f['target']=self._local_gap_target(end,f['rng'],f['dir'],cluster_id=f.get('local_fill_cluster_id'))
            size=region['size'] if region is not None else 'medium'
            f['max_gestures']=(7+int(rng.random()*6) if size=='small' else
                               14+int(rng.random()*9) if size=='medium' else 22+int(rng.random()*11))
            f['base_max_gestures']=f['max_gestures']
            realized+=1; special_realized+=int(special)
        self._compact_retired_path_records()
        self.stats['pathway_local_gap_capacity_realized_trace_count']=realized
        self.stats['pathway_local_gap_special_thick_trace_count']+=special_realized
        self.stats['pathway_local_gap_capacity_special_realized_trace_count']=special_realized
        self._local_gap_capacity_realizing=True
        try:
            rounds=self._run_local_gap_fast_rounds(round_budget=round_budget) if realized else 0
        finally:
            self._local_gap_capacity_realizing=False
        return rounds

    def run_local_after_components(self,frozen_main_pathways):
        """Fill the post-component residual field with the existing local-line language.

        Main pathways and components are immutable obstacles. Local fillers preserve V35's
        independent-birth, temporary-bundle, branching, 0/±45-degree and exact-clearance
        language, but V37 runs that language only after the component-first residual phase.
        """
        self._preload_frozen_pathway_groups(frozen_main_pathways)
        old_rounds=self.profile['max_rounds']; old_tail=self.profile.get('persistence_tail_rounds',0)
        local_round_budget=12
        self.stats['pathway_local_gap_round_budget']=local_round_budget
        self.profile['max_rounds']=local_round_budget
        self.profile['persistence_tail_rounds']=7
        capacity_first=bool(getattr(self,'local_gap_capacity_first',False))
        total_local_rounds=(self._prepare_local_gap_capacity(local_round_budget) if capacity_first else 0)
        if not capacity_first:
            source_cap=None; previous_covered=0.0
            wave_cap=3
            self.stats['pathway_local_gap_wave_work_cap']=wave_cap
            for _wave in range(wave_cap):
                spawned=self._launch_local_gap_fronts(source_cap=source_cap)
                if not spawned:
                    break
                if any(f.get('local_gap') and f.get('status')=='active' for f in self.fronts.values()):
                    total_local_rounds+=self._run_local_gap_fast_rounds(round_budget=local_round_budget)
                covered=self._local_gap_covered_cells()
                self.stats['pathway_local_gap_covered_cell_count']=len(covered)
                actual=self._local_gap_service_fraction()
                self.stats['pathway_local_gap_fill_actual']=actual
                if actual+1e-9>=self.local_gap_target_fraction:
                    break
                service_cells=max(1,int(self.local_gap_service_denominator_cell_count or len(self.local_gap_open_cells)))
                gain=max(.25,(actual*service_cells)-previous_covered)
                previous_covered=actual*service_cells
                deficit=max(0.0,(self.local_gap_target_fraction-actual)*service_cells)
                cells_per_source=max(.35,gain/max(1,spawned))
                min_wave_sources=max(1,int(getattr(self,'local_gap_min_wave_sources',6)))
                source_cap=max(min_wave_sources,min(self.r.local_wave_source_cap(),int(math.ceil(1.15*deficit/cells_per_source))))
            if self._local_gap_service_fraction()+1e-9 < self.local_gap_target_fraction:
                self._expand_local_fill_debt_targets()
            if self._local_gap_service_fraction()+1e-9 < self.local_gap_target_fraction:
                # Keep the established 96-line direct mop-up as the first bounded late pass on every
                # canvas. Extended territory receives additional stationary articulated/ordinary
                # opportunities below; no aspect-specific visual mode is introduced here.
                mopup_cap=self.r.local_direct_mopup_cap()
                self.stats['pathway_local_gap_mopup_work_cap']=mopup_cap
                self._local_gap_direct_mopup(max_lines=mopup_cap)
                if self._local_gap_service_fraction()+1e-9 < self.local_gap_target_fraction:
                    # Additional opportunity is derived only from normalized territory.  On a square
                    # the caps are zero; on any extended orientation they scale identically with T.
                    fragment_cap=self.r.local_fragment_mopup_cap()
                    self.stats['pathway_local_gap_fragment_mopup_work_cap']=fragment_cap
                    if fragment_cap>0:
                        self._local_gap_fragment_mopup(max_lines=fragment_cap)
                    # Once the hard 80% residual-service contract is already satisfied, do not
                    # open additional ordinary waves merely to chase the sampled 80-90% preference.
                    # The sampled point is explicitly best-effort; every value at/above the 80% floor
                    # remains inside the governing visual range.
                    hard_floor_now=float(getattr(self,'local_gap_hard_floor_absolute', self.r.local_gap_fill_range[0]*float(getattr(self,'local_gap_remaining_service_fraction',1.0))))
                    late_wave_cap=(self.r.local_late_wave_cap()
                                   if self._local_gap_service_fraction()+1e-9 < hard_floor_now else 0)
                    self.stats['pathway_local_gap_late_wave_work_cap']=late_wave_cap
                    stagnant=0; prev=self._local_gap_service_fraction()
                    for _late in range(late_wave_cap):
                        if self._local_gap_service_fraction()+1e-9 >= self.local_gap_target_fraction: break
                        spawned=self._launch_local_gap_fronts(source_cap=self.r.local_wave_source_cap())
                        if not spawned: break
                        if any(f.get('local_gap') and f.get('status')=='active' for f in self.fronts.values()):
                            total_local_rounds+=self._run_local_gap_fast_rounds(round_budget=local_round_budget)
                        now=self._local_gap_service_fraction()
                        if now-prev < 0.0025: stagnant+=1
                        else: stagnant=0
                        prev=now
                        if stagnant>=2: break
            # Hard-floor reserve: an ordinary execution cap is never allowed to be the sole reason
            # a geometrically valid board stops below the normative 80%-of-remainder floor.  Use
            # only the ordinary local router; no special geometry or relaxed clearance is introduced.
            remaining=float(getattr(self,'local_gap_remaining_service_fraction',1.0))
            hard_floor_abs=float(getattr(self,'local_gap_hard_floor_absolute', self.r.local_gap_fill_range[0]*remaining))
            # Two broad untouched-cell rescue opportunities are enough to exploit ordinary
            # spatial spread.  Remaining hard-floor deficit is a subcell service-debt problem and
            # proceeds to the debt-aware direct/fragment reserve below instead of opening another
            # whole-field binary wave.
            rescue_cap=min(2,self.r.local_hard_floor_rescue_cap())
            self.stats['pathway_local_gap_hard_floor_rescue_wave_cap']=rescue_cap
            rescue_count=0
            while (self._local_gap_service_fraction()+1e-9 < hard_floor_abs and rescue_count<rescue_cap):
                spawned=self._launch_local_gap_fronts(source_cap=self.r.local_wave_source_cap(),allow_region_overflow=True)
                if not spawned: break
                if any(f.get('local_gap') and f.get('status')=='active' for f in self.fronts.values()):
                    total_local_rounds+=self._run_local_gap_fast_rounds(round_budget=local_round_budget)
                rescue_count+=1
                # Do not collapse a territory-scaled reserve because one wave happened to add no
                # measured service.  Later ordinary waves consume different deterministic source/
                # routing opportunities and remain legal until the bounded cap is exhausted.
            self.stats['pathway_local_gap_hard_floor_rescue_wave_count']=rescue_count

            # Area-aligned final reserve.  The service invariant is measured at 16 subcells per
            # residual cell, while ordinary targeting intentionally treats any touched cell as
            # covered to avoid visual clustering.  If that binary targeting convention alone leaves
            # the board below the hard 80% service floor after all untouched-cell rescue waves,
            # temporarily retarget only cells that are still <80% serviced and run the SAME ordinary
            # local router with the same geometry/probabilities.  This is universal, target-gated,
            # and bounded; it is not an aspect-ratio mode.
            # Canonical service-debt reserve.  Ordinary LOCAL targeting intentionally retires a
            # cell after its first legitimate touch so successive waves spread across the board.
            # The hard service invariant, however, is area/subcell based.  If untouched-cell routing
            # stalls below the 80%-of-remainder floor, reuse the established exact bent/fragment
            # grammars against partially serviced cells before spawning more short ordinary fronts.
            # This keeps the visual grammar and exact clearance rules unchanged while making the
            # reserve operate on the same service debt that the contract measures.
            if self._local_gap_service_fraction()+1e-9 < hard_floor_abs:
                self.local_gap_retarget_cells={
                    c for c in self.local_gap_route_cells
                    if 0 < self.local_gap_coverage_mask_by_cell.get(c,0).bit_count() < 13
                }
                debt_mopup_cap=max(24,int(math.ceil(24.0*self.r.design_detail_area_scale())))
                self.stats['pathway_local_gap_service_debt_mopup_work_cap']=debt_mopup_cap
                # This reserve exists only because the board is below the normative 80% floor.
                # Normal cleanup may pursue the sampled 80-90% preference, but emergency debt work
                # must not keep generating geometry toward that optional preference after the hard
                # invariant has already been satisfied.  Temporarily make the hard floor the direct/
                # fragment stop target, then restore the sampled target for reporting/downstream use.
                _saved_local_target=self.local_gap_target_fraction
                self.local_gap_target_fraction=hard_floor_abs
                _debt_by_region={}
                for _c in self._local_gap_targetable_cells():
                    _rid=self.local_gap_region_by_cell.get(_c)
                    if _rid is None: continue
                    _bits=self.local_gap_coverage_mask_by_cell.get(_c,0).bit_count()
                    _debt_by_region[_rid]=_debt_by_region.get(_rid,0.0)+max(0,13-_bits)/13.0
                self._local_gap_service_debt_priority_by_region=_debt_by_region
                try:
                    direct_before=self.stats.get('pathway_local_gap_mopup_trace_count',0)
                    self._local_gap_direct_mopup(max_lines=debt_mopup_cap)
                    self.stats['pathway_local_gap_service_debt_direct_trace_count']=max(
                        0,self.stats.get('pathway_local_gap_mopup_trace_count',0)-direct_before)
                    if self._local_gap_service_fraction()+1e-9 < hard_floor_abs:
                        fragment_before=self.stats.get('pathway_local_gap_fragment_mopup_trace_count',0)
                        self._local_gap_fragment_mopup(max_lines=debt_mopup_cap)
                        self.stats['pathway_local_gap_service_debt_fragment_trace_count']=max(
                            0,self.stats.get('pathway_local_gap_fragment_mopup_trace_count',0)-fragment_before)
                finally:
                    self._local_gap_service_debt_touch_capture=None
                    self.local_gap_target_fraction=_saved_local_target
                    self._local_gap_service_debt_priority_by_region=None
                self.local_gap_retarget_cells=set()

            partial_cap=self.r.local_hard_floor_rescue_cap()
            partial_count=0
            partial_candidate_cap=self.r.local_partial_service_candidate_work_cap()
            partial_candidate_tokens=0
            self.stats['pathway_local_gap_partial_service_rescue_wave_cap']=partial_cap
            self.stats['pathway_local_gap_partial_service_candidate_work_cap_per_wave']=partial_candidate_cap
            # LOCAL-2: the former reserve reopened the same whole debt field up to three times.
            # Treat that as one monotonic debt campaign instead: preserve the exact total source
            # opportunity (partial_cap * ordinary wave source cap), but score/jitter the unpaid field
            # once.  The ordinary local router, candidate ranking, exact geometry and hard-floor
            # deterministic completion remain unchanged; only the redundant global campaign restart
            # disappears.
            if self._local_gap_service_fraction()+1e-9 < hard_floor_abs:
                self.local_gap_retarget_cells={
                    c for c in self.local_gap_route_cells
                    if 0 < self.local_gap_coverage_mask_by_cell.get(c,0).bit_count() < 13
                }
                if self.local_gap_retarget_cells:
                    _before_partial_attempts=self.stats.get('pathway_local_gap_spawn_attempt_count',0)
                    total_source_opportunity=partial_cap*self.r.local_wave_source_cap()
                    spawned=self._launch_local_gap_fronts(source_cap=total_source_opportunity,allow_region_overflow=True,
                                                          candidate_work_cap=partial_candidate_cap,prefer_service_debt=True,
                                                          wave_source_cap_override=total_source_opportunity)
                    partial_candidate_tokens += max(0,self.stats.get('pathway_local_gap_spawn_attempt_count',0)-_before_partial_attempts)
                    if spawned:
                        if any(f.get('local_gap') and f.get('status')=='active' for f in self.fronts.values()):
                            total_local_rounds+=self._run_local_gap_fast_rounds(round_budget=local_round_budget)
                        partial_count=1
            self.local_gap_retarget_cells=set()
            self.stats['pathway_local_gap_partial_service_rescue_wave_count']=partial_count
            self.stats['pathway_local_gap_partial_service_candidate_work_token_count']=partial_candidate_tokens
        self._settle_local_nonemittable_fronts()
        self._repair_terminal_marker_conflicts()
        self._settle_local_nonemittable_fronts()
        _pre_groups,_pre_stats=self._materialize()
        visible_ids={rec['tid'] for rec in self.trace_records if rec.get('local_gap')}
        invisible_fronts=[]
        for f in self.fronts.values():
            if (f.get('local_gap') and f.get('status') in ('terminated','escaped','connected','component')
                    and any(tid not in visible_ids for tid in f.get('ids',()))):
                f['status']='abandoned_short'
                f['termination_reason']='local_nonemittable_visible_package'
                f['lifecycle']='TERMINAL'
                invisible_fronts.append(f['id'])
        if invisible_fronts:
            self._prune_abandoned_local_segments(invisible_fronts)
            self._recount_visible_local_gap_service([
                rec for rec in self.trace_records if rec.get('front') not in invisible_fronts])
        self._local_frozen_visible_packets={
            rec['tid']:rec for rec in self.trace_records
            if rec.get('local_gap') and rec.get('front') not in invisible_fronts}
        self.stats['pathway_local_gap_predebt_nonemittable_front_count']=len(invisible_fronts)
        hard_floor_abs=float(getattr(self,'local_gap_hard_floor_absolute',
            self.r.local_gap_fill_range[0]*float(getattr(self,'local_gap_remaining_service_fraction',1.0))))
        best_effort=bool(getattr(self,'local_gap_best_effort_full_endpoint',False))
        if not best_effort and self._local_gap_service_fraction()+1e-9 < hard_floor_abs:
            self._local_gap_deterministic_debt_completion(hard_floor_abs)
        self.stats['pathway_local_gap_fill_actual']=self._local_gap_service_fraction()
        self.stats['pathway_decision_round_count']=total_local_rounds
        self.profile['max_rounds']=old_rounds; self.profile['persistence_tail_rounds']=old_tail
        self._repair_terminal_marker_conflicts()
        groups,stats=self._materialize()
        if (stats.get('pathway_unmarked_stroke_overlap_count',0) or
                stats.get('pathway_unmarked_clearance_violation_count',0) or
                stats.get('pathway_unmarked_overlap_count',0) or
                stats.get('pathway_static_intersection_count',0)):
            raise RuntimeError('hard post-component local-pathway overlap/clearance invariant violated')
        if (stats.get('pathway_illegal_turn_count',0) or stats.get('pathway_non_octilinear_segment_count',0) or
                stats.get('pathway_curved_primitive_count',0)):
            raise RuntimeError('hard exact-octilinear / <=45-degree local-turn invariant violated')
        # Keep the governing 80%-of-remainder service floor under route ownership.
        actual_abs=stats.get('pathway_local_gap_fill_actual',0.0)
        remaining=float(getattr(self,'local_gap_remaining_service_fraction',1.0))
        hard_floor_abs=float(getattr(self,'local_gap_hard_floor_absolute', self.r.local_gap_fill_range[0]*remaining))
        stats['pathway_local_gap_hard_floor_absolute']=hard_floor_abs
        stats['pathway_local_gap_sampled_target_shortfall']=max(0.0,self.local_gap_target_fraction-actual_abs)
        stats['pathway_local_gap_80pct_shortfall_absolute']=max(0.0,hard_floor_abs-actual_abs)
        stats['pathway_local_gap_fill_cluster_root_max']=max(self.local_fill_cluster_root_counts.values(),default=0)
        stats['pathway_local_gap_fill_cluster_root_cap_hits']=sum(
            self.local_fill_cluster_root_counts.get(cid,0)>=meta['target_sources']
            for cid,meta in self.local_route_clusters.items())
        stats['pathway_local_gap_fill_cluster_count']=len(self.local_route_clusters)
        stats['pathway_local_gap_fill_cluster_target_sum']=sum(
            meta['target_sources'] for meta in self.local_route_clusters.values())
        targets=[meta['target_sources'] for meta in self.local_route_clusters.values()]
        stats['pathway_local_gap_fill_cluster_target_min']=min(targets,default=0)
        stats['pathway_local_gap_fill_cluster_target_max']=max(targets,default=0)
        stats['pathway_local_gap_unowned_visible_root_count']=sum(
            g.structural.get('local_fill_cluster_id') is None for g in groups
            if g.structural.get('local_gap_pathway'))
        stats['pathway_local_gap_denominator']='canonical_post_main_residual_service_field'
        stats['pathway_local_gap_phase']='after_components'
        stats['pathway_local_gap_capacity_first']=capacity_first
        stats['pathway_local_gap_full_endpoint_best_effort']=best_effort
        if not best_effort and actual_abs+1e-9 < hard_floor_abs:
            raise RuntimeError(
                f'LOCAL service below hard floor: {actual_abs:.6f} < {hard_floor_abs:.6f}')
        return groups,stats

    def _local_debt_visible_package(self,f,center,pivot,end,marker_index,logical_marker_index,line_index):
        """Preflight one completion trace as the normal materializer will render it."""
        tid=f['ids'][0]; thickness=f['thicknesses'][tid]
        tf=dict(f); tf['path']=[center,pivot,end]; tf['status']='terminated'
        pts=[center,pivot,end]
        mrng=SplitMix64(mix_once(self.sseed ^ (tid+1)*0x9E3779B97F4A7C15))
        special=bool(f.get('local_gap_special'))
        radius=self.r._termination_dot_radius(thickness)
        source_filled=True if special else mrng.random()<.55
        source_stroke=0.0 if source_filled else self.r.termination_dot_hollow_stroke
        source_marker=prim_circle(center[0],center[1],radius,self.r.FG,source_filled,source_stroke)
        if not source_filled:
            pts=self._clip_polyline_start(pts,radius+.5*source_stroke)
        pts,component_backoff=(pts,0.0) if special else self._backoff_local_terminal_from_components(pts,thickness)
        if component_backoff is None:
            return None
        pts,_backoff=self._backoff_terminal_points(tf,tid,pts,marker_index)
        if len(pts)<2:
            return None
        terminal_filled=True if special else mrng.random()<.55
        terminal_stroke=0.0 if terminal_filled else self.r.termination_dot_hollow_stroke
        terminal=pts[-1]
        if not terminal_filled:
            clipped=self._clip_polyline_end(pts,radius+.5*terminal_stroke)
            clipped_len=sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(clipped,clipped[1:])) if len(clipped)>=2 else 0.0
            if (len(clipped)<2 or
                    math.hypot(clipped[-1][0]-clipped[-2][0],clipped[-1][1]-clipped[-2][1])<.10*self.module-1e-9):
                terminal_filled=True; terminal_stroke=0.0
            else:
                pts=clipped
        if len(pts)<2 or sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(pts,pts[1:]))+1e-9<2.75*self.module:
            return None
        prim=prim_polyline(pts,thickness,self.r.FG,round_caps=special)
        terminal_marker=prim_circle(terminal[0],terminal[1],.5*thickness if special else radius,self.r.FG,terminal_filled,terminal_stroke)
        for visible in ((prim,) if special else (prim,source_marker,terminal_marker)):
            if (not self._local_component_territory_clear(visible.geom) or
                    not self._local_fill_parcel_clear(tf,visible.geom) or
                    not self._local_visible_primitive_static_clear(visible)):
                return None
        logical_radius=radius+.5*self.r.termination_dot_hollow_stroke
        logical_disc=Point(end).buffer(logical_radius,quad_segs=12)
        for old in logical_marker_index.query(expand_bounds(logical_disc.bounds,self.r.termination_dot_min_gap)):
            # Match the final logical-marker guard exactly. Faceted GEOS discs
            # can admit a near-tangent pair whose true circles violate the gap.
            if self._terminal_record_conflict(
                    (None,tid,end,logical_disc,logical_radius),
                    (None,old.get('tid'),old['point'],old['geom'],old['radius'])):
                return None
        line=LineString(pts)
        for old in self._render_line_index_query(line_index,pts,max(
                2.0*self.module,self.r.pathway_interroute_keepout+thickness)):
            old_line=old['line']
            if not line.intersection(old_line).is_empty or not prim.geom.intersection(old['primitive'].geom).is_empty:
                return None
            gap=self._interroute_gap_for_fronts(
                tf,other_thickness=old.get('thickness',old['primitive'].svg.get('stroke_width',0.0)),
                other_local=old.get('local_gap',False),
                other_cluster_id=old.get('local_fill_cluster_id'))
            if prim.geom.distance(old['primitive'].geom)<gap-1e-7:
                return None
        return pts,terminal_marker.geom,logical_disc,prim,line

    def _local_gap_deterministic_debt_completion(self, hard_floor_abs):
        """Finite exact-legal completion of remaining LOCAL service debt.

        Ordinary waves/mop-up remain probabilistic for visual variety and speed.  If those
        bounded fast paths stop below the hard 80% contract, visit the finite residual debt
        cells deterministically and try the established octilinear straight/bent grammar from
        several subcell source positions.  Each candidate is checked by the same exact gesture
        and static-clearance gates.  No retry counter decides whether the seed exists.
        """
        if not self.local_gap_open_cells:
            return 0
        nx,ny=self.r.local_gap_grid_shape(); cw=self.W/nx; ch=self.H/ny
        step=max(.50*self.module,min(cw,ch))
        made=0; attempts=0
        # LOCAL-2 deterministic-tail cache.  For a fixed debt cell/source offset/d0/m1, the
        # first leg is identical across the six possible second-leg candidates (two turn signs
        # x three lengths).  The historical loop re-ran the same exact gesture-clearance query
        # for each one.  Cache only that immutable first-leg verdict/geometry; second-leg order,
        # exact checks and first-success semantics remain byte-for-byte equivalent.
        first_leg_cache={}
        first_leg_cache_hits=0; first_leg_cache_misses=0
        marker_index=SpatialHash(max(30*self.U,self.module))
        head_index=SpatialHash(max(30*self.U,self.module))
        for rec in getattr(self,'_local_render_marker_records',()):
            owner=self.fronts.get(rec.get('front'))
            if owner is not None and owner.get('status')!='abandoned_short':
                marker_index.insert(rec,rec['geom'].bounds)
                t=owner['thicknesses'][rec['tid']]
                reach=(self.r._termination_dot_radius(t)+.5*self.r.termination_dot_hollow_stroke+
                       self.r.pathway_terminal_head_keepout)
                rendered=tuple(rec['geom'].centroid.coords[0])
                logical=self._materialized_paths(owner)[rec['tid']][-1]
                head=LineString([rendered,logical]).buffer(reach,quad_segs=8)
                head_index.insert(dict(geom=head),head.bounds)
        logical_marker_index=SpatialHash(max(30*self.U,self.module))
        for old in self.fronts.values():
            if old.get('status')!='terminated':
                continue
            for _tid,_p,disc,_radius in self._terminal_marker_discs(old):
                logical_marker_index.insert(dict(geom=disc,tid=_tid,point=_p,radius=_radius),disc.bounds)
        line_index=SpatialHash(max(70*self.U,2*self.module))
        render_order=0
        for old in getattr(self,'_local_render_line_records',()):
            owner=self.fronts.get(old.get('front'))
            if owner is not None and owner.get('status')=='abandoned_short':
                continue
            pts=old.get('points')
            if pts is None:
                pts=list(old.get('line',LineString()).coords)
            item=dict(tid=old['tid'],line=old.get('line',LineString(pts)),primitive=old['primitive'],
                      thickness=old.get('thickness',old['primitive'].svg.get('stroke_width',0.0)),
                      local_gap=old.get('local_gap',False),
                      local_fill_cluster_id=old.get('local_fill_cluster_id'),render_order=render_order)
            self._render_line_index_insert(line_index,item,pts)
            render_order+=1
        cells=sorted(self.local_gap_route_cells,
                     key=lambda c:(self.local_gap_coverage_mask_by_cell.get(c,0).bit_count(),c[1],c[0]))

        def in_region_segment(a,b,region):
            # The board rectangle is convex: endpoints certify a straight leg.
            # Exact gesture/static/macro gates govern the stroke; raster region
            # cells nominate work and are not additional geometric walls.
            return (0<=a[0]<=self.W and 0<=a[1]<=self.H and
                    0<=b[0]<=self.W and 0<=b[1]<=self.H)

        for cell in cells:
            if self._local_gap_service_fraction()+1e-9 >= hard_floor_abs:
                break
            if self.local_gap_coverage_mask_by_cell.get(cell,0).bit_count()>=13:
                continue
            rid=self.local_gap_region_by_cell.get(cell)
            region=self.local_gap_regions[rid] if rid is not None and rid < len(self.local_gap_regions) else None
            base=((cell[0]+.5)*cw,(cell[1]+.5)*ch)
            offsets=((0.0,0.0),(.22*cw,0.0),(-.22*cw,0.0),(0.0,.22*ch),(0.0,-.22*ch))
            placed=False
            for ox,oy in offsets:
                center=(base[0]+ox,base[1]+oy)
                t=1.90*self.U
                marker_extent=self.r._termination_dot_radius(t)+.5*self.r.termination_dot_hollow_stroke
                if not self._local_gap_source_clearance(center,.5*t,marker_extent=marker_extent,
                                                        cluster_id=rid):
                    continue
                for d0 in range(8):
                    for m1 in (2.5,2.0,1.5):
                        pivot=point_along_dir(center,d0,m1*self.module)
                        if not in_region_segment(center,pivot,region): continue
                        for sign in (-1,1):
                            d1=(d0+sign)%8
                            for m2 in (2.5,2.0,1.5):
                                attempts+=1
                                end=point_along_dir(pivot,d1,m2*self.module)
                                if not in_region_segment(pivot,end,region): continue
                                tid=self.next_trace_id
                                synthetic_chip=len(self.chips)+400000+self.stats.get('pathway_local_gap_source_count',0)+made
                                f=self._make_front(ids=[tid],chip=synthetic_chip,side='local',side_index=synthetic_chip,
                                                   path=[center],direction=d0,offsets={tid:0.0},thicknesses={tid:t},prefixes={tid:[]},
                                                   rng=SplitMix64(local_pathway_seed(self.sseed)^tid),intent='explore',target=end,
                                                   local_cluster_id=rid)
                                f['local_gap']=True; f['local_gap_special']=False; f['fan_pending']=False
                                f['local_gap_region_id']=rid; f['local_gap_exit_allowed']=False
                                f['local_gap_min_terminal_modules']=3.0
                                _first_key=(cell,round(center[0],9),round(center[1],9),d0,round(m1,6))
                                _cached_first=first_leg_cache.get(_first_key,'__missing__')
                                if _cached_first=='__missing__':
                                    first_leg_cache_misses+=1
                                    g1=self._corridor_geom(f,center,pivot)
                                    if self._gesture_clear(f,center,pivot,g1,allow_outside=False):
                                        first_leg_cache[_first_key]=g1
                                    else:
                                        first_leg_cache[_first_key]=None
                                        self._drop_front(f['id']); continue
                                elif _cached_first is None:
                                    first_leg_cache_hits+=1
                                    self._drop_front(f['id']); continue
                                else:
                                    first_leg_cache_hits+=1
                                    g1=_cached_first
                                tf=dict(f); tf['path']=[center,pivot]; tf['dir']=d0; tf['gestures']=1; tf['local_gestures']=1
                                g2=self._corridor_geom(tf,pivot,end)
                                if not self._gesture_clear(tf,pivot,end,g2,allow_outside=False,extra_segments=(g1,)):
                                    self._drop_front(f['id']); continue
                                # A later stroke inside a previously accepted terminal head's
                                # visual keepout would make final materialization back that
                                # earlier head off, invalidating its service preflight.
                                head_blocked=False
                                for route_geom in (g1,g2):
                                    for old in head_index.query(route_geom.bounds):
                                        if route_geom.intersects(old['geom']):
                                            head_blocked=True; break
                                    if head_blocked: break
                                if head_blocked:
                                    self._drop_front(f['id']); continue
                                package=self._local_debt_visible_package(
                                    f,center,pivot,end,marker_index,logical_marker_index,line_index)
                                if package is None:
                                    self._drop_front(f['id']); continue
                                p1=dict(front=f['id'],start=center,end=pivot,dir=d0,modules=max(1,int(round(m1))),geom=g1,score=0.0)
                                p2=dict(front=f['id'],start=pivot,end=end,dir=d1,modules=max(1,int(round(m2))),geom=g2,score=0.0)
                                f['_defer_local_service_mark']=True
                                self._accept(f,p1,defer_post=True); self._accept(f,p2,defer_post=True)
                                f.pop('_defer_local_service_mark',None)
                                f['status']='terminated'; f['termination_reason']='local_gap_deterministic_debt_completion'; f['lifecycle']='TERMINAL'
                                visible_pts,terminal_geom,logical_disc,visible_prim,visible_line=package
                                for a,b in zip(visible_pts,visible_pts[1:]):
                                    self._mark_local_gap_segment_coverage(a,b,f)
                                marker_index.insert(dict(geom=terminal_geom,front=f['id'],tid=tid),terminal_geom.bounds)
                                head_reach=(self.r._termination_dot_radius(t)+.5*self.r.termination_dot_hollow_stroke+
                                            self.r.pathway_terminal_head_keepout)
                                head=LineString([tuple(terminal_geom.centroid.coords[0]),end]).buffer(
                                    head_reach,quad_segs=8)
                                head_index.insert(dict(geom=head),head.bounds)
                                logical_marker_index.insert(dict(geom=logical_disc,tid=tid,point=end,
                                    radius=self.r._termination_dot_radius(t)+.5*self.r.termination_dot_hollow_stroke),logical_disc.bounds)
                                render_item=dict(tid=tid,line=visible_line,primitive=visible_prim,
                                    thickness=t,local_gap=True,local_fill_cluster_id=rid,
                                    render_order=render_order)
                                self._render_line_index_insert(line_index,render_item,visible_pts)
                                render_order+=1
                                self.next_trace_id+=1; made+=1
                                self.stats['pathway_bundle_count']+=1; self.stats['pathway_local_gap_source_count']+=1
                                self.stats['pathway_local_gap_trace_count']+=1; self.stats['pathway_local_gap_independent_source_count']+=1
                                placed=True; break
                            if placed: break
                        if placed: break
                    if placed: break
                if placed: break
        self.stats['pathway_local_gap_deterministic_debt_completion_trace_count']=made
        self.stats['pathway_local_gap_deterministic_debt_completion_candidate_count']=attempts
        self.stats['pathway_local_gap_deterministic_debt_first_leg_cache_hit_count']=first_leg_cache_hits
        self.stats['pathway_local_gap_deterministic_debt_first_leg_cache_miss_count']=first_leg_cache_misses
        return made

    def run(self):
        """Compatibility entry point: V37's production renderer calls split phases explicitly."""
        return self.run_main_only()

# ---------------------------------------------------------------------------
# Public geometry interface
# ---------------------------------------------------------------------------

def parse_aspect_ratio(value):
    """Return a positive (width, height) ratio pair.

    V46 exposes shape, not pixel dimensions.  Accepted forms are ``"W:H"``,
    a two-item sequence, or a positive scalar interpreted as width/height.
    The pair is normalized only when deriving the logical rectangle; the
    original orientation is preserved.
    """
    if isinstance(value, str):
        text=value.strip()
        if ':' in text:
            a,b=text.split(':',1)
            w,h=float(a),float(b)
        elif '/' in text:
            a,b=text.split('/',1)
            w,h=float(a),float(b)
        else:
            w=float(text); h=1.0
    elif isinstance(value, (tuple,list)) and len(value)==2:
        w,h=float(value[0]),float(value[1])
    else:
        w=float(value); h=1.0
    if not (math.isfinite(w) and math.isfinite(h) and w>0.0 and h>0.0):
        raise ValueError("aspect_ratio must contain two finite positive values")
    return (w,h)

# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

class V48Renderer:
    FG = "#e7e1d2"
    BG = "#101319"

    CANONICAL_SHORT_SIDE = 1200.0

    def __init__(self, aspect_ratio=(1.0,1.0), scale: float=1.0, seed: Optional[int]=None,
                 main_chip_density_multiplier: float=1.0, main_run_length_multiplier: float=1.0,
                 local_density: float=DEFAULT_LOCAL_DENSITY,
                 component_density: float=DEFAULT_COMPONENT_DENSITY):
        ratio_w,ratio_h=parse_aspect_ratio(aspect_ratio)
        if not math.isfinite(float(scale)) or float(scale) <= 0:
            raise ValueError("scale must be a finite positive number")
        chip_mult=float(main_chip_density_multiplier)
        run_mult=float(main_run_length_multiplier)
        local_density=float(local_density)
        component_density=float(component_density)
        if not math.isfinite(chip_mult) or not (0.2 <= chip_mult <= 2.0):
            raise ValueError("main_chip_density_multiplier must be finite and within 0.2..2.0")
        if not math.isfinite(run_mult) or not (0.2 <= run_mult <= 3.0):
            raise ValueError("main_run_length_multiplier must be finite and within 0.2..3.0")
        if not math.isfinite(local_density) or not (0.0 <= local_density <= 1.0):
            raise ValueError("local_density must be finite and within 0..1")
        if not math.isfinite(component_density) or not (0.0 <= component_density <= 1.0):
            raise ValueError("component_density must be finite and within 0..1")
        self.aspect_ratio=(ratio_w,ratio_h)
        self.scale=float(scale)
        self.main_chip_density_multiplier=chip_mult
        self.local_density=local_density
        self.component_density=component_density
        # Item 4 is a pure MAIN workload/geometry control.  The planner scales only the existing
        # whole-route residency distribution; proposal/clearance/search algorithms stay unchanged.
        self.main_run_length_multiplier=run_mult
        self.canonical_short_side=float(self.CANONICAL_SHORT_SIDE)
        ratio_short=min(ratio_w,ratio_h)
        # V46 unifies aspect extension and zoom.  The generator receives one logical
        # rectangle.  A lower scale exposes proportionally more logical territory;
        # entity dimensions and all local design rules stay canonical in logical units.
        logical_short=self.canonical_short_side/self.scale
        self.W=logical_short*(ratio_w/ratio_short)
        self.H=logical_short*(ratio_h/ratio_short)
        self.S=self.canonical_short_side
        self.U=self.S/1600.0
        self.seed = secrets.randbits(64) if seed is None else int(seed) & MASK64
        self.pathway_debug_stage=None
        # Placement/routing keep-outs. Main-chip routing is solved against chips only. Components are
        # then fitted into the post-main residual field and frozen before local-gap routing begins.
        self.chip_edge_clearance=120.0*self.U
        self.chip_chip_clearance=430.0*self.U
        self.chip_secondary_clearance=170.0*self.U
        self.component_chip_clearance=42.0*self.U
        self.component_pathway_clearance=10.0*self.U
        self.component_component_clearance=12.0*self.U
        self.component_edge_clearance=20.0*self.U
        self.residual_gap_fill_range=(0.50,0.60)
        self.main_pathway_gesture_check_budget=52000
        self.local_pathway_gesture_check_budget=22000
        territory=self.population_area_scale()
        detail_area=self.design_detail_area_scale()
        self.main_pathway_gesture_check_budget=max(52000,int(math.ceil(52000*territory)))
        self.local_pathway_gesture_check_budget=22000
        self.component_extra_filler_limit=max(96,int(math.ceil(96*detail_area)))
        self.component_micro_filler_limit=max(8,int(math.ceil(8*detail_area)))
        self.component_density_cap=max(300,int(math.ceil(300*detail_area)))
        self.component_gap_grid_n=56
        self.component_pathway_attachment_probability=0.24
        self.pathway_static_keepout=8.0*self.U
        self.pathway_main_chip_keepout=24.0*self.U
        self.pathway_interroute_keepout=1.25*self.U
        self.pathway_terminal_head_keepout=4.5*self.U
        self.local_gap_fill_range=(0.80,0.90)
        self.local_gap_grid_n=56
        self.local_gap_line_edge_gap_factor=1.50
        self.local_gap_bundle_probability=0.50
        self.local_gap_branch_boost_range=(3.0,5.0)
        self.local_gap_exit_probability_factor=0.50
        self.termination_dot_scale=2.0
        self.termination_dot_hollow_stroke=2.70*self.U
        self.termination_dot_min_gap=1.0*self.U
        self.local_gap_special_thickness_range=(5.0,8.0)
        self.local_gap_special_hole_radius_ratio=0.22
        self.pathway_chip_launch_gap=22.5*self.U

    def _legacy_residual_fill_draws(self, sseed:int):
        """Return the two seeded residual-fill draws used by the pre-knob renderer.

        These draws are independent SplitMix streams, so consulting them here does not perturb
        component placement or LOCAL routing RNG.
        """
        component_target=SplitMix64(component_fill_seed(sseed)).uniform(*self.residual_gap_fill_range)
        local_target=SplitMix64(local_pathway_seed(sseed) ^ 0xD36D36D36D36D36D).uniform(*self.local_gap_fill_range)
        return component_target,local_target

    def residual_density_budget(self, sseed:int):
        """Map the two user knobs onto one post-MAIN residual-service budget.

        ``local_density=1`` means the same total residual service that this renderer would have
        requested before these knobs existed.  ``component_density`` is the component share of
        that combined budget.  The exact default pair takes a legacy fast path so existing default
        renders keep their historical seeded 50..60% component target followed by 80..90% LOCAL
        of the remainder.
        """
        legacy_component,legacy_local=self._legacy_residual_fill_draws(sseed)
        legacy_local_abs=(1.0-legacy_component)*legacy_local
        legacy_total=legacy_component+legacy_local_abs
        exact_default=(abs(self.local_density-DEFAULT_LOCAL_DENSITY)<=1e-15 and
                       abs(self.component_density-DEFAULT_COMPONENT_DENSITY)<=1e-15)
        if exact_default:
            component_target=legacy_component
            local_budget=legacy_local_abs
            total_target=legacy_total
            component_floor=self.residual_gap_fill_range[0]
            local_floor_abs=(1.0-legacy_component)*self.local_gap_fill_range[0]
        else:
            total_target=max(0.0,min(1.0,self.local_density*legacy_total))
            component_target=total_target*self.component_density
            local_budget=total_target-component_target
            # Preserve the historical target-vs-hard-floor relationship while scaling density.
            # Knob targets remain preferences; exact geometry is never relaxed to reach them.
            component_floor=(component_target*self.residual_gap_fill_range[0]/max(legacy_component,1e-9)
                             if component_target>0.0 else 0.0)
            full_local_budget=legacy_total*(1.0-self.component_density)
            full_local_floor=min(full_local_budget, self.local_gap_fill_range[0],
                                 full_local_budget*self.local_gap_fill_range[0]/max(legacy_local,1e-9))
            local_floor_abs=self.local_density*full_local_floor
            # Density above the historical phase range is a best-effort visual target, not a
            # license to turn the old 50% component / 80%-of-remainder LOCAL hard floors into
            # expensive new 90%+ construction invariants.  Scale floors downward with density,
            # but cap them at the renderer's established hard contracts.
            component_floor=min(component_target,self.residual_gap_fill_range[0],component_floor)
            local_floor_abs=min(local_budget,local_floor_abs)
        return dict(
            legacy_exact=exact_default,
            legacy_component_target=legacy_component,
            legacy_local_remainder_target=legacy_local,
            legacy_total_target=legacy_total,
            total_target=total_target,
            component_target=component_target,
            component_floor=component_floor,
            local_absolute_budget=local_budget,
            local_floor_absolute_budget=local_floor_abs,
            component_population_scale=(min(1.0,component_target/max(legacy_component,1e-9))
                                        if component_target>0.0 else 0.0),
        )

    def _density_scaled_component_population(self, population, sseed:int, scale:float):
        """Seeded subset of prepared residual components for below-legacy component budgets.

        Completion fillers still close any remaining service target.  Default/above-default
        component density returns the original lists untouched and consumes no extra RNG.
        """
        collections,isolated=population
        scale=max(0.0,min(1.0,float(scale)))
        if scale>=1.0-1e-15:
            return collections,isolated
        tagged=[('collection',i,g) for i,g in enumerate(collections)]
        tagged += [('isolated',i,g) for i,g in enumerate(isolated)]
        if not tagged or scale<=0.0:
            return [],[]
        exact=len(tagged)*scale
        keep=int(math.floor(exact))
        rrng=SplitMix64(mix_once(component_fill_seed(sseed) ^ 0xA5A5A5A55A5A5A5A))
        if rrng.random() < exact-keep:
            keep+=1
        if keep<=0:
            return [],[]
        ranked=[]
        for serial,rec in enumerate(tagged):
            ranked.append((rrng.next_u64(),serial,rec))
        ranked.sort(key=lambda z:(z[0],z[1]))
        chosen={(kind,i) for _k,_s,(kind,i,_g) in ranked[:keep]}
        return ([g for i,g in enumerate(collections) if ('collection',i) in chosen],
                [g for i,g in enumerate(isolated) if ('isolated',i) in chosen])

    def _termination_dot_radius(self, thickness:float):
        return self.termination_dot_scale*max(1.35*self.U,.80*thickness+.35*self.U)

    def _aspect_grid_shape(self, base_n:int):
        """Bookkeeping grid with canonical design-local cell size."""
        base=max(1,int(base_n))
        design_short=max(self.S,1e-9)
        nx=max(1,int(round(base*self.W/design_short)))
        ny=max(1,int(round(base*self.H/design_short)))
        return nx,ny

    def _service_grid_shape(self, base_n:int):
        """Coverage/service grid in the same canonical logical units."""
        return self._aspect_grid_shape(base_n)

    def local_gap_grid_shape(self):
        return self._service_grid_shape(self.local_gap_grid_n)

    def component_gap_grid_shape(self):
        return self._service_grid_shape(self.component_gap_grid_n)

    def canvas_territory_scale(self):
        """Aspect-only territory at scale 1.0."""
        rw,rh=self.aspect_ratio
        short=max(min(rw,rh),1e-9)
        return max(1.0,(rw*rh)/(short*short))

    def population_area_scale(self):
        """Logical board area in canonical square territories."""
        return max(1.0,(self.W*self.H)/(self.S*self.S))

    def tall_area_scale(self):
        return self.population_area_scale()

    def population_parts(self):
        T=self.population_area_scale(); full=max(1,int(math.floor(T))); frac=max(0.0,min(1.0,T-full))
        return T,full,frac

    def design_distance_scale(self):
        """Logical viewport enlargement relative to scale 1."""
        return 1.0/self.scale

    def design_detail_area_scale(self):
        return self.population_area_scale()

    def local_pathway_work_scale(self):
        # Exact local routing work follows the amount of design-scale area that must be serviced.
        return self.design_detail_area_scale()

    def local_direct_mopup_cap(self):
        # The historical fixed 96-line ceiling is a safety reserve, not a visual target.  It is
        # naturally inactive through the healthy 0.75 reference (72 lines used there), but at
        # finer scales it became the reason efficient direct articulation stopped and expensive
        # rescue stages took over.  Keep the same 96 opportunity through 0.75, then scale the
        # non-semantic ceiling with logical territory so the service target/exhaustion—not a
        # square-era constant—decides when this operator is done.
        T=self.design_detail_area_scale()
        return max(96,int(math.ceil(54.0*T)))

    def local_direct_run_family_attempt_cap(self):
        # One unchanged residual corridor may receive an initial stochastic realization plus two
        # retries for thickness/order variance.  The budget is intentionally independent of
        # territory: larger boards create more local run families, not more polling of each
        # unchanged family.  Once exhausted, the family leaves this direct-mop-up call's
        # candidate pool; exact geometry remains authoritative for every admitted attempt.
        return 3

    def local_fragment_mopup_cap(self):
        # Square output retains the old no-fragment behavior. Extended territory gets a bounded
        # articulated cleanup allowance per unit territory, independent of orientation.
        D=self.design_detail_area_scale()
        return int(math.ceil(40.0*D)) if D>1.25 else 0

    def local_fragment_candidate_work_cap(self):
        # Work, not accepted output, is the scaling invariant.  Each admitted fragment candidate
        # can trigger exact source and multi-gesture legality checks, so bound candidate-cell
        # opportunity directly per logical territory.  500/territory leaves the healthy 0.75
        # reference workload unchanged while preventing fine-scale failed-search amplification.
        return max(256,int(math.ceil(500.0*self.design_detail_area_scale())))

    def local_partial_service_candidate_work_cap(self):
        # Partial-service rescue exists only after untouched/debt operators fail the hard floor.
        # At fine scale, rescoring every partially served cell per rescue wave makes failed work
        # grow faster than territory.  Bound admitted debt candidates per wave while prioritising
        # the least-served cells; 600/territory is inactive on the healthy 1.0/0.75 references.
        return max(512,int(math.ceil(600.0*self.design_detail_area_scale())))

    def local_wave_source_cap(self):
        # Stationary source opportunity per logical territory; board-wide wave count stays bounded.
        return max(24,int(math.ceil(24.0*self.design_detail_area_scale())))

    def local_branch_birth_cap(self):
        # The historical square admits at most two new singleton branches per local tick.
        return max(2,int(math.ceil(2.0*self.design_detail_area_scale())))

    def local_late_wave_cap(self):
        # More territory means more sources *inside* a wave, not more full-board rescans.
        return 2 if self.design_detail_area_scale()>1.25 else 0

    def local_hard_floor_rescue_cap(self):
        # Bounded globally; each rescue wave has territory-scaled source opportunity.
        return 3

    def local_gap_trace_population_cap(self):
        # Safety ceiling only.  V47's former 144/territory cap was calibrated while LOCAL
        # accidentally measured service on the smaller post-component denominator.  With the
        # canonical post-MAIN service budget restored, keep proportional opportunity but raise
        # the non-semantic ceiling so the 80% hard floor, not stale bookkeeping, stops the phase.
        return max(256,int(math.ceil(256.0*self.design_detail_area_scale())))

    def local_gap_region_source_cap(self, cell_count):
        # V33/V34's hard 34-source ceiling was calibrated to one square-reference territory.
        # Keep the same density on extended canvases while preserving the cell-count capacity.
        territory_ceiling=max(34,int(math.ceil(34.0*self.design_detail_area_scale())))
        return max(1,min(territory_ceiling,int(math.ceil(float(cell_count)/16.0))))

    # ------------------------------ distributions -------------------------
    def chip_count_probability(self):
        """Compatibility diagnostic: historical fractional-territory opportunity probability."""
        return self.population_parts()[2]

    def main_chip_opportunity_activation_probability(self):
        """Marginal activation probability of either historical chip opportunity.

        V48 historically supplied a *pair* of chip opportunities per normalized territory.
        The density knob keeps those same paired opportunities but couples their activation so
        multiplier 1.0 selects exactly one member of every complete pair (a true 50% baseline),
        values below 1.0 probabilistically admit that one member, and values above 1.0
        probabilistically restore the second.  Either member is symmetric, so its marginal
        activation probability remains multiplier/2.  Multiplier 2.0 restores both members and
        therefore the complete historical count law exactly.
        """
        return 0.5*self.main_chip_density_multiplier

    def _main_chip_pair_mask(self, thinning):
        """Return the active historical opportunity bits for one territory pair.

        The two-bit mask is selected on a private density substream.  This is geometry-only
        population control: it neither changes the historical fractional-territory draws nor
        perturbs the downstream collection/family RNG.
        """
        m=self.main_chip_density_multiplier
        if m>=2.0-1e-15:
            return 0b11
        gate=thinning.random()
        primary=0b01 if thinning.random()<0.5 else 0b10
        if m<=1.0:
            return primary if gate<m else 0
        return 0b11 if gate<(m-1.0) else primary

    def chip_count(self, rng):
        _T,full,frac=self.population_parts()

        # Density selection lives on its own deterministic substream.  Production SplitMix64
        # exposes `state`; the fallback keeps lightweight test RNGs supported without making
        # chip_count() depend on a richer RNG interface than random().
        rng_state=getattr(rng,'state',mix_once(self.seed ^ 0x9E3779B97F4A7C15))
        thinning=SplitMix64(mix_once(rng_state ^ 0xD1B54A32D192ED03))

        if self.main_chip_density_multiplier>=2.0-1e-15:
            # Exact compatibility fast path: no new pair-selection work for the historical law.
            count=2*full
        else:
            count=sum(self._main_chip_pair_mask(thinning).bit_count() for _ in range(full))

        if frac>0.0:
            mask=self._main_chip_pair_mask(thinning)
            # Consume the exact two historical fractional-opportunity draws for every multiplier.
            # At multiplier 2.0 both mask bits are active, reproducing the old law and downstream
            # RNG state byte-for-byte.
            for bit in (0b01,0b10):
                historical_present=(rng.random()<frac)
                if historical_present and (mask & bit):
                    count+=1
        # MAIN is the first routed phase and the rest of the V48 design language is defined around
        # at least one main-chip source.  The user knob therefore saturates at one physical chip
        # rather than exporting a zero-source topology into unrelated component/routing code.
        return max(1,count)

    def collection_count(self, rng):
        """Stationary prepared-collection population per normalized territory."""
        _T,full,frac=self.population_parts()
        draw=lambda: int(rng.weighted([(15,.20),(16,.30),(17,.30),(18,.20)]))
        total=sum(draw() for _ in range(full))
        if frac>0.0:
            fractional=draw()
            total += sum(1 for _ in range(fractional) if rng.random()<frac)
        return total

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
    def _chip_geometry_fingerprint(self, g: Group):
        """Exact generated-geometry identity for pre-placement main chips.

        V47 used a coarse motif/aspect signature as an acceptance gate.  Distinct chips could
        collide in those bins and eventually kill an otherwise valid seed.  Geometry identity
        is the actual requirement: reject only literal generated duplicates.
        """
        out=[]
        for p in g.primitives:
            geom=p.geom
            out.append((p.svg.get('type'),geom.wkb_hex,
                        p.svg.get('fill'),p.svg.get('stroke'),
                        round(float(p.svg.get('stroke_width',0.0)),9)))
        return tuple(out)

    def _construct_chip_fallback(self, base_seed: int, idx: int) -> Group:
        """Deterministic in-language chip constructor used only after procedural exhaustion."""
        rng=SplitMix64(base_seed ^ 0xA24BAED4963EE407 ^ (idx*0x9E3779B97F4A7C15))
        # Stay comfortably inside the normal calibrated q/long intervals.
        q=(.082+.006*rng.random())*self.S
        A=1.42+.10*rng.random()
        long=q*A
        orient='horizontal' if rng.random()<.67 else 'vertical'
        w,h=(long,q) if orient=='horizontal' else (q,long)
        rx=2.35*self.U
        ps=[prim_rect_outline(0,0,w,h,rx,3.2*self.U,self.FG)]
        # M1/M2-like interior language, deliberately simple and collision-proof.
        inset=7.0*self.U
        iw=max(8*self.U,w-2*inset); ih=max(8*self.U,h-2*inset)
        ps.append(prim_rect_outline(0,0,iw,ih,1.7*self.U,1.8*self.U,self.FG))
        cr=max(2.6*self.U,min(iw,ih)*.075)
        ps.append(prim_circle(0,0,cr,self.FG,False,1.8*self.U))
        # Seed/index-specific legal interior dash makes literal duplicates impossible without
        # changing the language or the external launch envelope.
        off=(rng.random()-.5)*.22*iw
        ps.append(prim_line(off-.08*iw,0,off+.08*iw,0,1.8*self.U,self.FG))
        aspect_signature=round(A/0.04)*0.04
        structural=dict(kind='chip',orientation=orient,aspect_bin=aspect_signature,
                        motifs=('M1','M2'),inner_border_count=1,
                        exterior_side_set_configuration=(None,None),q_chip=q,width=w,height=h,
                        constructive_fallback=True)
        return Group(f'chip-{idx}',ps,structural)

    def generate_chip(self, base_seed: int, idx: int) -> Group:
        # preserve requested regeneration behavior by deriving retry streams from chip seed
        for attempt in range(128):
            rng=SplitMix64(retry_seed(base_seed, attempt) if attempt else base_seed)
            g=self._generate_chip_once(rng, idx)
            if g is not None:
                return g
        return self._construct_chip_fallback(base_seed,idx)

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

        # Ordinary coverage min 2; construct it locally instead of rejecting the whole sample.
        # ``capacitor_circle`` has no exact quota and is therefore the first safe donor.  If a
        # low-complexity draw simply did not create enough ordinary slots, promote one collection
        # by one family rather than rerolling every chip/pathway decision downstream.
        coverage=("square","circle","dot","dash")
        for target in coverage:
            while sum(target in a["families"] for a in assigns)<2:
                eligible=[]
                counts={f:sum(f in aa["families"] for aa in assigns) for f in coverage}
                for i,a in enumerate(assigns):
                    if target in a["families"]: continue
                    replaceable=[f for f in a["families"]
                                 if f=="capacitor_circle" or (f in coverage and counts[f]>2)]
                    if replaceable: eligible.append((i,replaceable))
                if eligible:
                    rng.shuffle(eligible); i,opts=eligible[0]; rng.shuffle(opts); donor=opts[0]
                    assigns[i]["families"][assigns[i]["families"].index(donor)]=target
                    continue
                promotable=[i for i,a in enumerate(assigns) if target not in a["families"] and len(a["families"])<5]
                if promotable:
                    # Promote the least-complex collection first; seeded tie-breaking preserves
                    # variance while keeping this exceptional repair local and deterministic.
                    best=min(a["complexity"] for i,a in enumerate(assigns) if i in promotable)
                    cohort=[i for i in promotable if abs(assigns[i]["complexity"]-best)<=1e-15]
                    rng.shuffle(cohort); i=cohort[0]
                    assigns[i]["families"].append(target)
                    assigns[i]["family_count"]=len(assigns[i]["families"])
                    assigns[i]["tier"]=assigns[i]["family_count"]
                    continue
                raise RuntimeError("collection family coverage construction invariant exhausted")
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
        return self._construct_collection_fallback(base_seed,idx,assignment,planning=True)

    def _construct_collection_fallback(self, base_seed: int, idx: int, assignment: Dict[str,Any],
                                       target_span=None, planning=False):
        """Deterministic grammar-preserving collection constructor.

        Stochastic subgroup/assembly draws remain the normal path.  Exhausting them cannot make
        the whole seed invalid: this local constructor deliberately searches only for structural
        properties required by the collection language, then scales the finished assembly into
        the calibrated span.  It never changes assignment quotas/families.
        """
        chosen=None; chosen_seed=None
        for probe in range(96):
            seed=retry_seed(base_seed,0x40000+probe)
            with bounds_only_mode(planning):
                g=self._make_collection_once(SplitMix64(seed),idx,assignment)
            if g is None:
                continue
            dense=[sg.get('dense_dims') for sg in g.structural.get('subgroups',[]) if sg.get('family')=='dense']
            if dense and any(max(rc)/min(rc)<2.5 for rc in dense):
                continue
            ic_bad=sum(sg.get('required_contact_failure_count',0) for sg in g.structural.get('subgroups',[])
                       if sg.get('family')=='ic' and sg.get('ic_mode')=='array')
            if ic_bad:
                continue
            chosen=g; chosen_seed=seed; break
        if chosen is None:
            # The subgroup primitives above are themselves total under valid renderer geometry;
            # reaching this point is implementation corruption, not an unlucky seed.
            raise RuntimeError('constructive collection grammar invariant unavailable')
        L=max(bounds_w_h(chosen.bounds))
        target=float(target_span if target_span is not None else .046*self.S)
        target=max(.040*self.S,min(.052*self.S,target))
        if L<=1e-12:
            raise RuntimeError('constructive collection produced empty geometry')
        chosen=chosen.transformed(scale=target/L,name=f'collection-{idx}')
        chosen.structural=dict(chosen.structural)
        chosen.structural['source_seed']=chosen_seed
        chosen.structural['source_retry_index']=-1
        chosen.structural['constructive_fallback']=True
        chosen.structural['constructive_target_span']=target
        return chosen

    def make_collection(self, base_seed: int, idx: int, assignment: Dict[str,Any], planning=False):
        for attempt in range(256):
            seed=retry_seed(base_seed,attempt) if attempt else base_seed; rng=SplitMix64(seed)
            with bounds_only_mode(planning):
                g=self._make_collection_once(rng,idx,assignment)
            if g is None: continue
            L=max(bounds_w_h(g.bounds))
            if not (.014*self.S <= L <= .096*self.S): continue
            g.structural["source_seed"]=seed
            return g
        return self._construct_collection_fallback(base_seed,idx,assignment,planning=planning)

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
            placed=None; best_score=None; best_idx=None; best_offset=None
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
                        best_score=score; best_idx=j; best_offset=(tx,ty)
                if best_offset is not None:
                    placed=sg.transformed(best_offset[0],best_offset[1])
                    break
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
        # store structural info needed for component quotas/reporting
        structural=dict(kind="collection",families=tuple(sorted(assignment["families"])),border=assignment["border"],tier=assignment["tier"],Pord=Pord)
        for sg in subgroups:
            structural.setdefault("subgroups",[]).append(dict(sg.structural))
        accepted.structural=structural
        return accepted

    def generate_isolated_capacitors(self, sseed: int):
        rng=SplitMix64(isolated_capacitor_seed(sseed))
        _T,full,frac=self.population_parts()
        out=[]
        territory_index=0
        def emit_batch(tidx):
            # Preserve the historical saturated occurrence draw as part of the deterministic
            # random stream even though it always succeeds for a complete territory.
            _occurrence_draw=rng.random()
            count=1 + min(2, int(3*(rng.random()**1.10)))
            for _ in range(count):
                ps,meta=self._capacitor_entity_primitives(rng,0.0,0.0)
                i=len(out)
                out.append(Group(f"isolated-capacitor-{i}",ps,dict(
                    family="capacitor_circle",entity_count=1,isolated=True,
                    population_territory_index=tidx,**meta)))
        for territory_index in range(full):
            emit_batch(territory_index)
        # A fractional territory carries the same batch opportunity with probability frac.
        if frac>0.0 and rng.random()<frac:
            emit_batch(full)
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

    def _release_group_derived_caches(self,groups):
        """Release rebuildable GEOS/index caches at an explicit phase boundary."""
        seen=set()
        for g in groups:
            if id(g) in seen: continue
            seen.add(id(g))
            release=getattr(g,'release_derived_caches',None)
            if release is not None:
                release(keep_bounds=True)

    def _release_component_residual_state(self):
        """Discard component-placement raster/region fields before local routing starts."""
        for name in (
            '_component_gap_regions','_component_gap_open_cells','_component_gap_region_by_cell',
            '_component_gap_clearance','_component_gap_grid_shape','_component_gap_grid_n',
        ):
            self.__dict__.pop(name,None)

    def generate_main_pathways(self, sseed:int, placed_chips:List[Group]):
        """Route and freeze the main-chip network against chips only."""
        planner=BundleGesturePlanner(self,sseed,placed_chips,enable_failure_certificates=True)
        groups,stats=planner.run_main_only()
        # V47 lifetime contract: finished geometry/stats survive; transient planner graph/history
        # state does not remain retained by Renderer after the main phase is frozen.
        return groups,dict(stats)

    def generate_local_gap_pathways(self, sseed:int, placed_chips:List[Group], placed_components:List[Group],
                                    frozen_main_pathways:List[Group], component_service_fraction:float,
                                    post_main_service_cell_count:int):
        """Route the LOCAL allocation of the shared post-MAIN residual-density budget."""
        planner=BundleGesturePlanner(self,local_pathway_seed(sseed),placed_chips+placed_components)
        remaining=max(0.0,1.0-float(component_service_fraction))
        rrng=SplitMix64(local_pathway_seed(sseed) ^ 0xD36D36D36D36D36D)
        legacy_normalized_target=rrng.uniform(*self.local_gap_fill_range)
        budget=getattr(self,'_active_residual_density_budget',None)
        if budget is None or budget.get('legacy_exact'):
            normalized_target=legacy_normalized_target
            absolute_target=remaining*normalized_target
            hard_floor_abs=remaining*self.local_gap_fill_range[0]
        else:
            total_target=float(budget['total_target'])
            local_budget=float(budget['local_absolute_budget'])
            # Components are placed first.  If discrete component geometry overshoots its share,
            # reduce LOCAL rather than exceeding the requested total.  Component under-realization
            # is not back-filled by LOCAL because component_density owns the modality split.
            absolute_target=min(remaining,local_budget,max(0.0,total_target-float(component_service_fraction)))
            normalized_target=(absolute_target/remaining if remaining>1e-12 else 0.0)
            hard_floor_abs=min(absolute_target,float(budget['local_floor_absolute_budget']),
                               remaining*self.local_gap_fill_range[0])
        work_scale=self.local_pathway_work_scale()
        planner.gesture_check_budget=int(math.ceil(self.local_pathway_gesture_check_budget*work_scale))
        planner.stats['pathway_gesture_clear_check_budget']=planner.gesture_check_budget
        planner.stats['pathway_tall_work_scale']=work_scale
        planner.local_gap_service_denominator_cell_count=max(1,int(post_main_service_cell_count))
        planner.local_gap_remaining_service_fraction=remaining
        planner.local_gap_remaining_target_fraction=normalized_target
        planner.local_gap_absolute_target_fraction=absolute_target
        planner.local_gap_hard_floor_absolute=hard_floor_abs
        planner.local_gap_min_wave_sources=(6 if budget is None or budget.get('legacy_exact') else 1)
        legacy_local_abs=(float(budget['legacy_total_target'])-float(budget['legacy_component_target'])
                          if budget is not None else absolute_target)
        planner.local_gap_capacity_first=(budget is not None and not budget.get('legacy_exact') and
                                          float(budget['local_absolute_budget'])>legacy_local_abs+1e-12)
        planner.local_gap_best_effort_full_endpoint=(abs(self.local_density-1.0)<=1e-15 and
                                                    abs(self.component_density)<=1e-15)
        groups,stats=planner.run_local_after_components(frozen_main_pathways)
        absolute=stats.get('pathway_local_gap_fill_actual',0.0)
        physical=planner._local_gap_physical_post_component_service_fraction()
        stats['pathway_local_gap_fill_actual_absolute_service']=absolute
        stats['pathway_local_gap_physical_post_component_service_fraction']=physical
        stats['pathway_local_gap_post_main_service_cell_count']=planner.local_gap_service_denominator_cell_count
        stats['pathway_local_gap_post_component_open_cell_count']=len(planner.local_gap_open_cells)
        stats['pathway_local_gap_remaining_service_fraction']=remaining
        stats['pathway_local_gap_fill_target_fraction']=normalized_target
        stats['pathway_local_gap_absolute_target_fraction']=planner.local_gap_absolute_target_fraction
        stats['pathway_local_gap_hard_floor_absolute']=hard_floor_abs
        stats['pathway_local_gap_fill_actual']=(min(1.0,absolute/max(remaining,1e-9)) if remaining>1e-9 else 1.0)
        stats['pathway_local_gap_denominator']='canonical_post_main_residual_service_field'
        return groups,stats

    def generate_pathways(self, sseed:int, placed:List[Group]):
        """Compatibility alias: V37 production generation uses the split phase methods."""
        return self.generate_main_pathways(sseed,placed)

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
        def candidate_valid(cand,kind):
            query_clearance=(self.chip_chip_clearance if kind=="chip" else self.chip_secondary_clearance)
            qbounds=expand_bounds(cand.bounds,max(60*self.U,query_clearance))
            for other in index.query(qbounds):
                okind=other.structural.get("placement_kind")
                clearance=(self.chip_chip_clearance if kind=="chip" and okind=="chip" else
                           self.chip_secondary_clearance if "chip" in (kind,okind) else 12*self.U)
                if cand.geom.intersects(other.geom) or cand.geom.distance(other.geom)<clearance:
                    return False
            return True

        def deterministic_scan(obj,kind,l,r,t,b):
            """Finite geometry-driven completion after stochastic placement exhausts.

            This is not another retry budget: it deterministically covers a lattice whose pitch
            is derived from the object's footprint + applicable clearance, then a half-pitch
            offset lattice.  Main-chip density is calibrated well below this packing capacity.
            """
            ow,oh=bounds_w_h(obj.bounds)
            clearance=self.chip_chip_clearance if kind=='chip' else max(12*self.U,self.chip_secondary_clearance)
            px=max(8*self.U,ow+clearance); py=max(8*self.U,oh+clearance)
            phases=((0.0,0.0),(.5,.5),(.5,0.0),(0.0,.5))
            for phx,phy in phases:
                nx=max(1,int(math.floor((r-l)/px))+1); ny=max(1,int(math.floor((b-t)/py))+1)
                xs=[min(r,l+(i+phx)*px) for i in range(nx+1) if l+(i+phx)*px<=r+1e-9]
                ys=[min(b,t+(j+phy)*py) for j in range(ny+1) if t+(j+phy)*py<=b+1e-9]
                # Include exact frame-limited extrema; they frequently hold legal edge slots.
                xs=sorted(set([l,r]+xs)); ys=sorted(set([t,b]+ys))
                for j,y in enumerate(ys):
                    row=xs if j%2==0 else list(reversed(xs))
                    for x in row:
                        cand=obj.transformed(x,y)
                        if candidate_valid(cand,kind):
                            cand.structural=dict(obj.structural); cand.structural['placement_kind']=kind
                            cand.structural['deterministic_placement_completion']=True
                            return cand
            return None
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
                        # The broad phase must cover the largest exact clearance that can apply
                        # to this candidate. V44 queried only ~60U/chip-secondary range even
                        # though chip-chip legality requires 430U; low chip counts hid the miss.
                        # True zoom exposes enough chips for that false-negative broad phase to
                        # become visible, so query the complete relevant moat before the same
                        # exact GEOS distance/intersection test below.
                        if candidate_valid(cand,kind):
                            cand.structural=dict(obj.structural); cand.structural["placement_kind"]=kind
                            valids.append(cand)
                    if valids:
                        if rng.random() < spread_prob and len(valids) > 1:
                            ok=max(valids, key=lambda g: self.placement_spread_score(g, placed, kind))
                        else:
                            ok=valids[0]
                if ok is None:
                    ok=deterministic_scan(obj,kind,l,r,t,b)
                if ok is None: return None
                placed.append(ok); index.insert(ok)
        return placed

    def _deterministic_place_main_chip_population(self,chips):
        """Construct a globally legal Phase-A chip layout on a clearance-safe lattice.

        Used only if the ordinary spread placement plus per-chip deterministic scan paints a
        later chip into a corner.  MAIN has not started yet, so repositioning the chip population
        is local Phase-A recovery and discards no routed/component work.
        """
        if not chips: return []
        maxw=max(bounds_w_h(g.bounds)[0] for g in chips)
        maxh=max(bounds_w_h(g.bounds)[1] for g in chips)
        halfw=.5*maxw; halfh=.5*maxh
        left=self.chip_edge_clearance+halfw; right=self.W-self.chip_edge_clearance-halfw
        top=self.chip_edge_clearance+halfh; bottom=self.H-self.chip_edge_clearance-halfh
        if left>right or top>bottom: return None
        pitchx=maxw+self.chip_chip_clearance; pitchy=maxh+self.chip_chip_clearance
        nx=max(1,int(math.floor((right-left)/pitchx))+1)
        ny=max(1,int(math.floor((bottom-top)/pitchy))+1)
        if nx*ny < len(chips):
            return None
        # Spread occupied slots over the complete legal lattice instead of filling one corner.
        slots=[(left+i*pitchx,top+j*pitchy) for j in range(ny) for i in range(nx)]
        if len(chips)<len(slots):
            step=len(slots)/len(chips)
            picks=[]; used=set()
            for k in range(len(chips)):
                q=min(len(slots)-1,int((k+.5)*step))
                while q in used and q+1<len(slots): q+=1
                while q in used and q>0: q-=1
                used.add(q); picks.append(slots[q])
            slots=picks
        out=[]
        for g,(x,y) in zip(chips,slots):
            cand=g.transformed(x,y); cand.structural=dict(g.structural)
            cand.structural['placement_kind']='chip'; cand.structural['deterministic_population_placement']=True
            out.append(cand)
        # Exact audit of the construction before returning it.
        for i,a in enumerate(out):
            ab=a.bounds
            if (ab[0]<self.chip_edge_clearance-1e-7 or ab[1]<self.chip_edge_clearance-1e-7 or
                    self.W-ab[2]<self.chip_edge_clearance-1e-7 or self.H-ab[3]<self.chip_edge_clearance-1e-7):
                return None
            for b in out[i+1:]:
                if a.geom.intersects(b.geom) or a.geom.distance(b.geom)<self.chip_chip_clearance-1e-7:
                    return None
        return out

    # ------------------------------ validation ---------------------------
    def _free_terminal_records(self, pathways: List[Group]):
        """Return (free-terminal point, owning pathway group) records.

        Ownership is part of the semantic result: later component attachment can validate the
        actual endpoint contact locally instead of rediscovering the owning group by rescanning
        the complete pathway population for every terminal candidate.
        """
        out=[]
        for g in pathways:
            polylines=[p.svg for p in g.primitives if p.svg.get('type')=='polyline' and p.svg.get('points')]
            markers=[p.svg for p in g.primitives if p.svg.get('type')=='circle' and p.svg.get('fill')!=self.BG]
            if not polylines or not markers:
                continue
            starts=[tuple(pl['points'][0]) for pl in polylines]
            start_r=4.0*self.U
            start_index=SpatialHash(max(start_r,1e-6))
            for q in starts:
                start_index.insert(q,(q[0],q[1],q[0],q[1]))
            marker_index=SpatialHash(max(5.0*self.U,1e-6))
            for m in markers:
                reach=max(5.0*self.U,m['r']+m.get('stroke_width',0.0))
                marker_index.insert((m,reach),(m['cx']-reach,m['cy']-reach,m['cx']+reach,m['cy']+reach))
            for pl in polylines:
                end=tuple(pl['points'][-1])
                if not (0 <= end[0] <= self.W and 0 <= end[1] <= self.H):
                    continue
                if any(math.hypot(end[0]-q[0],end[1]-q[1]) <= start_r
                       for q in start_index.query((end[0]-start_r,end[1]-start_r,end[0]+start_r,end[1]+start_r))):
                    continue
                if any(math.hypot(end[0]-m['cx'],end[1]-m['cy']) <= reach
                       for m,reach in marker_index.query((end[0],end[1],end[0],end[1]))):
                    out.append((end,g))
        # Preserve historical first-seen terminal deduplication; the retained owner is exactly
        # the group that supplied that first-seen terminal.
        dedup=[]; dedup_r=3.0*self.U; dedup_index=SpatialHash(max(dedup_r,1e-6))
        for p0,g in out:
            near=dedup_index.query((p0[0]-dedup_r,p0[1]-dedup_r,p0[0]+dedup_r,p0[1]+dedup_r))
            if any(math.hypot(p0[0]-rec[0][0],p0[1]-rec[0][1]) <= dedup_r for rec in near):
                continue
            rec=(p0,g); dedup.append(rec); dedup_index.insert(rec,(p0[0],p0[1],p0[0],p0[1]))
        return dedup

    def _free_terminal_points(self, pathways: List[Group]):
        """Compatibility view of the free-terminal records."""
        return [pt for pt,_owner in self._free_terminal_records(pathways)]

    def _group_collision_geoms(self,g):
        """Primitive geometries representing a group as a set, without topology-unioning it."""
        return [box(*p.geom.bounds) if isinstance(p.geom,BoundsGeom) else p.geom for p in g.primitives]

    def _bounds_within_gap(self,a,b,gap):
        return not (a[2]+gap < b[0] or b[2]+gap < a[0] or a[3]+gap < b[1] or b[3]+gap < a[1])

    def _groups_violate_clearance(self,a,b,gap):
        if not self._bounds_within_gap(a.bounds,b.bounds,gap): return False
        # Distance/intersection of two primitive unions is the minimum over primitive pairs.
        # Query only bounds-compatible pairs; this is exact and avoids pathological GEOS work on
        # very large GeometryCollections.
        left,right=(a,b) if len(a.primitives)<=len(b.primitives) else (b,a)
        rindex=right.primitive_index
        for p in left.primitives:
            pg=p.geom
            for q in rindex.query(expand_bounds(pg.bounds,gap)):
                qg=q.geom
                if not self._bounds_within_gap(pg.bounds,qg.bounds,gap): continue
                if (pg.intersects(qg) if gap<=0.0 else pg.distance(qg)<gap): return True
        return False

    def _group_intersects_geometry(self,g,geom):
        if geom.is_empty: return False
        gb=geom.bounds
        for pg in self._group_collision_geoms(g):
            if not self._bounds_within_gap(pg.bounds,gb,0.0): continue
            if pg.intersects(geom): return True
        return False

    def _component_attachment_exact_valid(self,cand,pt,pathways):
        """Allow one exact terminal contact, never a blanket overlap exemption around that point.

        Intersection of two primitive unions is non-empty iff at least one primitive pair
        intersects.  Check those local pairs directly so a rare attachment never topology-unions
        an entire branched pathway group.
        """
        allowed=Point(pt).buffer(max(5.0*self.U,.22*max(bounds_w_h(cand.bounds))),quad_segs=10)
        target_hits=0
        for pg in pathways:
            if not self._bounds_within_gap(cand.bounds,pg.bounds,0.0):
                continue
            hit=False
            for cp in cand.primitives:
                cg=cp.geom
                for pp in pg.primitive_index.query(cg.bounds):
                    pgm=pp.geom
                    if not self._bounds_within_gap(cg.bounds,pgm.bounds,0.0): continue
                    if not cg.intersects(pgm): continue
                    inter=cg.intersection(pgm)
                    if inter.is_empty: continue
                    hit=True
                    if not inter.difference(allowed).is_empty:
                        return False
            if not hit: continue
            endpoint=False
            for prim in pg.primitives:
                svg=prim.svg
                if svg.get('type')!='polyline' or not svg.get('points'): continue
                end=svg['points'][-1]
                if math.hypot(end[0]-pt[0],end[1]-pt[1])<=max(5.0*self.U,1.5*self.component_pathway_clearance):
                    endpoint=True; break
            if not endpoint:
                return False
            target_hits+=1
            if target_hits>1:
                return False
        return target_hits==1

    def _component_attachment_local_valid(self,cand,pt,owner,pathway_component_index):
        """Exact attachment proof using terminal ownership and the existing local primitive index.

        A valid attachment may intersect exactly the owning pathway group, and every such
        intersection must remain inside the strict terminal-contact bubble. Any intersecting
        non-owner pathway group is invalid. `_free_terminal_records` already proves that `pt` is
        a marked free endpoint of `owner`, so no global owner rediscovery is necessary here.
        """
        allowed=Point(pt).buffer(max(5.0*self.U,.22*max(bounds_w_h(cand.bounds))),quad_segs=10)
        owner_hit=False
        seen=set()
        for cp in cand.primitives:
            cg=cp.geom
            for rec in pathway_component_index.query(cg.bounds):
                raw=rec['primitive'].geom
                if not self._bounds_within_gap(cg.bounds,raw.bounds,0.0):
                    continue
                key=(id(cp),id(rec['primitive']))
                if key in seen:
                    continue
                seen.add(key)
                if not cg.intersects(raw):
                    continue
                inter=cg.intersection(raw)
                if inter.is_empty:
                    continue
                if not inter.difference(allowed).is_empty:
                    return False
                if rec['pathway'] is not owner:
                    return False
                owner_hit=True
        return owner_hit

    def _component_path_keepout(self, primitive, pathway_keepout_wkb_cache=None):
        """Return the exact historical component-clearance keepout for one frozen path primitive.

        During component placement pathways are immutable.  Re-buffering the same long polyline
        hundreds of times is pure repeated work, while retaining GEOS keepout polygons caused a
        large RSS regression in earlier experiments.  When a phase-local cache is supplied, keep
        only compact WKB bytes and reconstruct a temporary exact GEOS object on reuse.
        """
        raw=primitive.geom
        if pathway_keepout_wkb_cache is None:
            return raw.buffer(self.component_pathway_clearance,quad_segs=4)
        pk=id(primitive)
        blob=pathway_keepout_wkb_cache.get(pk)
        if blob is None:
            pg=raw.buffer(self.component_pathway_clearance,quad_segs=4)
            pathway_keepout_wkb_cache[pk]=shapely.to_wkb(pg)
            return pg
        return shapely.from_wkb(blob)

    def _component_candidate_valid(self, cand: Group, kind: str, chips: List[Group], pathways: List[Group],
                                   accepted: List[Group], attachment_point: Optional[Tuple[float,float]]=None,
                                   chip_keepout=None, pathway_keepout=None, accepted_index=None, pathway_component_index=None, chip_component_index=None,
                                   pathway_keepout_wkb_cache=None) -> bool:
        b=cand.bounds; edge=self.component_edge_clearance
        if b[0] < edge or b[1] < edge or self.W-b[2] < edge or self.H-b[3] < edge:
            return False
        if attachment_point is None and not self._residual_composition_component_geometry_owned(cand):
            return False
        # Chip/component clearance is an exact Euclidean invariant.  A finite-segment round
        # buffer at the *nominal* gap is an inscribed approximation and historically left a thin
        # false-safe annulus that could survive until final validation as ``pair_chip_isolated``.
        # Use a conservatively inflated round buffer instead: it contains the true Euclidean gap
        # neighbourhood, so this fast intersection test may reject an extremely close valid
        # candidate but can never admit an invalid one.  The phase-local exact audit below remains
        # the construction guard.
        if chip_keepout is None and chip_component_index is None:
            q=8; rr=self._conservative_clearance_buffer_radius(self.component_chip_clearance,q)
            chip_keepout=unary_union([g.geom.buffer(rr,quad_segs=q) for g in chips]) if chips else GeometryCollection()
        if pathway_keepout is None and pathway_component_index is None:
            pathway_keepout=unary_union([g.geom.buffer(self.component_pathway_clearance,quad_segs=8) for g in pathways]) if pathways else GeometryCollection()
        elif pathway_keepout is None:
            pathway_keepout=GeometryCollection()
        # GeometryCollection is set-equivalent for intersects/distance but avoids topology-
        # dissolving large multi-primitive component collections (the pathological GEOS case
        # that V37 removes).  It is substantially faster than primitive-by-primitive checks in
        # the ordinary hot path while still having bounded construction cost.
        cgeom=cand.collision_geom
        if chip_component_index is not None:
            for crec in chip_component_index.query(cand.bounds):
                if cgeom.intersects(crec['geom']):
                    return False
        elif not chip_keepout.is_empty and cgeom.intersects(chip_keepout):
            return False
        # Route keepout is checked through a spatial index of individually buffered pathway
        # groups.  A single topology-unioned board keepout can trigger pathological GEOS
        # intersection time for a 60+ primitive collection even though only a few traces are
        # spatially relevant to that candidate.
        if pathway_component_index is not None:
            allowed=None
            if attachment_point is not None:
                rr=max(bounds_w_h(cand.bounds))/2 + self.component_pathway_clearance + 3.0*self.U
                allowed=Point(attachment_point).buffer(rr,quad_segs=12)
            for prec in pathway_component_index.query(cand.bounds):
                raw=prec['primitive'].geom
                if not self._bounds_within_gap(cand.bounds,raw.bounds,self.component_pathway_clearance):
                    continue
                pg=self._component_path_keepout(prec['primitive'],pathway_keepout_wkb_cache)
                if not cgeom.intersects(pg):
                    continue
                if allowed is None:
                    return False
                inter=cgeom.intersection(pg)
                if not inter.is_empty and not inter.difference(allowed).is_empty:
                    return False
        elif not pathway_keepout.is_empty and cgeom.intersects(pathway_keepout):
            if attachment_point is None:
                return False
            rr=max(bounds_w_h(cand.bounds))/2 + self.component_pathway_clearance + 3.0*self.U
            allowed=Point(attachment_point).buffer(rr,quad_segs=12)
            conflict=cgeom.intersection(pathway_keepout)
            if not conflict.is_empty and not conflict.difference(allowed).is_empty:
                return False
        nearby=(accepted_index.query(expand_bounds(cand.bounds,self.component_component_clearance))
                if accepted_index is not None else accepted)
        for other in nearby:
            if self._groups_violate_clearance(cand,other,self.component_component_clearance):
                return False
        return True

    def _component_candidate_valid_after_static_certificate(self,cand:Group,accepted,accepted_index=None):
        """Exact remainder of component admission after immutable board clearance is proven.

        Residual-cell clearance is the exact distance to chip/pathway geometry *already buffered*
        by the required component keepouts.  When a translated candidate is wholly inside that
        clearance disk, repeating chip/pathway GEOS queries cannot change the answer.  Frame and
        accepted-component checks remain live and exact.
        """
        b=cand.bounds; edge=self.component_edge_clearance
        if b[0] < edge or b[1] < edge or self.W-b[2] < edge or self.H-b[3] < edge:
            return False
        if not self._residual_composition_component_geometry_owned(cand):
            return False
        nearby=(accepted_index.query(expand_bounds(cand.bounds,self.component_component_clearance))
                if accepted_index is not None else accepted)
        for other in nearby:
            if self._groups_violate_clearance(cand,other,self.component_component_clearance):
                return False
        return True

    def _residual_gap_site_count(self, component_count:int, target:float) -> int:
        if component_count <= 0:
            return 0
        target=max(1e-9,min(1.0,float(target)))
        # Preserve the exact historical denominator rule at the legacy 50..60% target.  Outside
        # that band the density knob owns the target directly, so use the corresponding finite
        # component/site ratio instead of clamping back into the legacy band.
        if self.residual_gap_fill_range[0]-1e-15 <= target <= self.residual_gap_fill_range[1]+1e-15:
            lo=max(component_count, math.ceil(component_count/self.residual_gap_fill_range[1]))
            hi=max(lo, math.floor(component_count/self.residual_gap_fill_range[0]))
            ideal=component_count/target
            return min(hi,max(lo,int(round(ideal))))
        return max(component_count,int(round(component_count/target)))

    def _conservative_clearance_buffer_radius(self, gap:float, quad_segs:int=8) -> float:
        """Radius whose finite round-buffer polygon contains the true ``gap`` neighbourhood.

        GEOS/Shapely approximates each quarter-circle with ``quad_segs`` chords.  The minimum
        radial extent between adjacent vertices is ``R*cos(pi/(4*quad_segs))``.  Inflating the
        construction radius by the reciprocal cosine therefore makes the polygonized buffer a
        conservative *superset* of the exact Euclidean ``gap`` offset instead of the historical
        under-approximation that could admit ``pair_chip_isolated`` failures.
        """
        q=max(1,int(quad_segs))
        return float(gap)/math.cos(math.pi/(4.0*q)) + 1e-12*max(1.0,self.U)

    def residual_fill_cluster_member_target(self, rng:SplitMix64) -> int:
        """Seeded residual-fill cluster cardinality with full 1..12 design-language support.

        The cluster *cardinality* is a visual composition rule, not a placement/routing search
        budget.  Singulars are common, small/medium clusters dominate, and genuinely large
        10--12 member clusters remain a normal but minority outcome.
        """
        band=rng.weighted([('single',.18),('small',.27),('medium',.28),('large',.17),('xlarge',.10)])
        if band=='single':
            return 1
        if band=='small':
            return 2+int(rng.random()*2)
        if band=='medium':
            return 4+int(rng.random()*3)
        if band=='large':
            return 7+int(rng.random()*3)
        return 10+int(rng.random()*3)

    def _build_residual_composition_ownership(self,open_cells,regions,rng):
        """Plan paired C cores and LOCAL lobes on the post-MAIN service field.

        Compact feasible cores own component centers; their selected physical
        tiles contain complete glyphs. Prepared, recovery and completion
        candidates share these gates. The canonical service field is unchanged.
        """
        nx,ny=self.component_gap_grid_shape()
        # A parcel is about fifteen service cells on either physical axis.  One scalar
        # lattice count made a 1:6 tile six times taller than it was wide, while its C
        # owner remained a short-axis square and lost most of its useful capacity.
        pitch=math.sqrt(165.0)
        mx=max(1,int(round(nx/pitch)))
        my=max(1,int(round(ny/pitch)))
        self._residual_macro_grid_shape=(mx,my)
        self._residual_macro_lattice_n=mx  # compatibility with older diagnostics
        cw=self.W/nx; ch=self.H/ny
        component_target=max(0.0,float(getattr(self,'_active_component_fill_target',0.0)))
        budget=getattr(self,'_active_residual_density_budget',{}) or {}
        local_budget=max(0.0,float(budget.get('local_absolute_budget',0.0)))
        share=(component_target/(component_target+local_budget)
               if component_target+local_budget>1e-12 else 0.0)
        # A 2x2 physical parcel group is the smallest composition unit. Seeded
        # selection varies the shape of neighbouring C/LOCAL clusters while
        # keeping each modality spread over the board. Literal endpoints reserve
        # no territory for the absent modality.
        selected=set()
        for by in range(0,my,2):
            for bx in range(0,mx,2):
                keys=[(x,y) for y in range(by,min(my,by+2))
                      for x in range(bx,min(mx,bx+2))]
                rng.shuffle(keys)
                exact=len(keys)*share
                count=min(len(keys),int(math.floor(exact))+
                          int(rng.random()<exact-math.floor(exact)))
                selected.update(keys[:count])
        buckets={}
        for c in open_cells:
            key=(min(mx-1,mx*c[0]//nx),min(my-1,my*c[1]//ny))
            if key in selected:
                buckets.setdefault(key,[]).append(c)
        owners={}; eligible=set(); by_cell={}; capacity={}
        clearance=getattr(self,'_component_gap_clearance',{})
        # About half the truly feasible C-tile cells must remain eligible to
        # supply the component capacity floor.  A weak tile still receives a
        # useful minimum quota; the total automatically follows residual work.
        total_tile_cells=sum(len(cells) for cells in buckets.values())
        desired_total=int(math.ceil((1.0 if local_budget<=1e-12 else .48)*total_tile_cells))
        for key,cells in sorted(buckets.items()):
            gx0=(key[0]*nx+mx-1)//mx; gx1=((key[0]+1)*nx+mx-1)//mx-1
            gy0=(key[1]*ny+my-1)//my; gy1=((key[1]+1)*ny+my-1)//my-1
            width=gx1-gx0+1; height=gy1-gy0+1
            available=set(cells)
            prefix=[[0]*(width+1) for _ in range(height+1)]
            for gy in range(gy0,gy1+1):
                row=0
                for gx in range(gx0,gx1+1):
                    row+=int((gx,gy) in available)
                    prefix[gy-gy0+1][gx-gx0+1]=prefix[gy-gy0][gx-gx0+1]+row
            def count_rect(x0,y0,x1,y1):
                a=x0-gx0; b=y0-gy0; c=x1-gx0+1; d=y1-gy0+1
                return prefix[d][c]-prefix[b][c]-prefix[d][a]+prefix[b][a]
            goal=min(len(cells),max(1,int(math.ceil(desired_total*len(cells)/max(1,total_tile_cells)))))
            tx=(key[0]+.5)*self.W/mx; ty=(key[1]+.5)*self.H/my
            tile=box(key[0]*self.W/mx,key[1]*self.H/my,
                     (key[0]+1)*self.W/mx,(key[1]+1)*self.H/my)
            chosen=None
            for fraction in ((.5,) if local_budget<=1e-12 else (.31,.35,.39,.43,.47)):
                radius_x=fraction*self.W/mx
                radius_y=fraction*self.H/my
                best=None
                for gy in range(gy0,gy1+1):
                    for gx in range(gx0,gx1+1):
                        sx=(gx+.5)*cw; sy=(gy+.5)*ch
                        x0=max(gx0,int(math.ceil((sx-radius_x)/cw-.5)))
                        x1=min(gx1,int(math.floor((sx+radius_x)/cw-.5)))
                        y0=max(gy0,int(math.ceil((sy-radius_y)/ch-.5)))
                        y1=min(gy1,int(math.floor((sy+radius_y)/ch-.5)))
                        if x0>x1 or y0>y1: continue
                        count=count_rect(x0,y0,x1,y1)
                        rank=(count,-math.hypot(sx-tx,sy-ty),
                              float(clearance.get((gx,gy),0.0)),-gy,-gx)
                        if best is None or rank>best[0]:
                            best=(rank,sx,sy)
                if best is None: continue
                chosen=(best[1],best[2],radius_x,radius_y)
                if best[0][0]>=goal: break
            if chosen is None: continue
            sx,sy,radius_x,radius_y=chosen
            owner=box(sx-radius_x,sy-radius_y,sx+radius_x,sy+radius_y).intersection(tile)
            owned=[c for c in cells if owner.covers(Point((c[0]+.5)*cw,(c[1]+.5)*ch))]
            if not owned: continue
            # The fitted core owns cluster centers; the selected composition
            # tile owns complete canonical glyphs. Conflating these footprints
            # strands legal constructor capacity at the core boundary.
            owners[key]=tile; capacity[key]=len(owned)
            eligible.update(owned)
            for c in owned: by_cell[c]=key
        self._residual_component_macro_owners=owners
        self._residual_local_macro_keys={(x,y) for y in range(my) for x in range(mx)}-set(owners)
        self._residual_component_macro_by_cell=by_cell
        self._residual_component_macro_capacity_cells=capacity
        self._residual_composition_component_cells=eligible
        self._residual_composition_component_tiles=None
        self._residual_composition_parcels={}
        self._residual_composition_parcel_by_cell={}
        self._residual_composition_grid_shape=(nx,ny)

    def _residual_composition_component_center(self,p):
        cells=getattr(self,'_residual_composition_component_cells',None)
        if cells is None:
            return True
        nx,ny=self._residual_composition_grid_shape
        gx=min(nx-1,max(0,int(p[0]*nx/max(self.W,1e-9))))
        gy=min(ny-1,max(0,int(p[1]*ny/max(self.H,1e-9))))
        return (gx,gy) in cells

    def _residual_composition_component_geometry_owned(self,cand):
        owners=getattr(self,'_residual_component_macro_owners',None)
        if owners is not None:
            cx,cy=bounds_center(cand.bounds)
            nx,ny=self._residual_composition_grid_shape
            c=(min(nx-1,max(0,int(cx*nx/max(self.W,1e-9)))),
               min(ny-1,max(0,int(cy*ny/max(self.H,1e-9)))))
            key=self._residual_component_macro_by_cell.get(c)
            if key is None:
                return False
            x0,y0,x1,y1=owners[key].bounds
            a0,b0,a1,b1=cand.collision_geom.bounds
            # Each owner is an axis-aligned rectangle clipped by its tile, so
            # AABB containment is an exact positive and negative geometry test.
            return x0<=a0 and y0<=b0 and a1<=x1 and b1<=y1
        tiles=getattr(self,'_residual_composition_component_tiles',None)
        if tiles is None:
            return True
        nx,ny=self._residual_composition_grid_shape
        span=self._residual_composition_tile_span
        cw=self.W/nx; ch=self.H/ny
        tw=span*cw; th=span*ch
        halo=.5*self.component_component_clearance
        b=cand.bounds
        tx0=max(0,int(math.floor((b[0]-halo)/tw)))
        tx1=min((nx-1)//span,int(math.floor((b[2]+halo)/tw)))
        ty0=max(0,int(math.floor((b[1]-halo)/th)))
        ty1=min((ny-1)//span,int(math.floor((b[3]+halo)/th)))
        foreign=[]
        for ty in range(ty0,ty1+1):
            for tx in range(tx0,tx1+1):
                if (tx,ty) not in tiles:
                    foreign.append((tx,ty))
        if not foreign:
            return True
        geom=cand.collision_geom
        for tx,ty in foreign:
            limit=box(tx*tw,ty*th,min(self.W,(tx+1)*tw),min(self.H,(ty+1)*th))
            if geom.intersects(limit) or geom.distance(limit)<halo:
                return False
        return True

    def _component_clustered_gap_sites(self, regions, open_cells, clearance, rng, count, component_count):
        """Plan spatially distributed component-cluster opportunities in O(cells + sites).

        Component placement still happens before LOCAL routing so exact collision ownership stays
        simple, but the *opportunities* are no longer one global region-first stream.  Prepared
        components are assigned to seeded clusters whose requested cardinalities span 1..12 and
        whose anchors are spread over the measured post-MAIN residual field.  Each cluster only
        receives nearby residual-cell sites, which prevents one open room from turning into one
        macroscopic component colony.  The placement predicates themselves are unchanged.
        """
        count=max(0,int(count)); component_count=max(0,int(component_count))
        if count<=0 or component_count<=0 or not open_cells or not regions:
            self._component_gap_cluster_meta={}
            self._component_gap_site_cluster_ids=[]
            return []
        seed_state=getattr(rng,'state',mix_once(self.seed ^ 0x6A09E667F3BCC909))
        prng=SplitMix64(mix_once(int(seed_state) ^ 0xC13FA9A902A6328F))

        # Cardinalities sum exactly to the prepared component population.  Later emergency
        # residual fillers are deliberately treated as scattered/singular recovery objects, so
        # they cannot silently grow any prepared cluster past its design-language target.
        targets=[]; remaining=component_count
        while remaining>0:
            n=min(remaining,self.residual_fill_cluster_member_target(prng))
            targets.append(n); remaining-=n
        nclusters=len(targets)

        # Distribute site opportunity in proportion to requested cluster membership.  At least
        # one site is reserved per cluster when possible; the historical site-count denominator
        # is otherwise preserved exactly.
        quotas=[0]*nclusters
        used=0
        if count>=nclusters:
            quotas=[1]*nclusters; used=nclusters
        heap=[]
        for cid,t in enumerate(targets):
            heapq.heappush(heap,(-(t/(quotas[cid]+1.0)),cid))
        while used<count and heap:
            _score,cid=heapq.heappop(heap)
            quotas[cid]+=1; used+=1
            heapq.heappush(heap,(-(targets[cid]/(quotas[cid]+1.0)),cid))

        region_map={r['id']:r for r in regions}
        region_members={r['id']:0 for r in regions}
        cluster_region={}
        # Large requested clusters get first choice of physical room, but region load is
        # normalized by already-planned membership so no one room monopolizes the board.
        order=sorted(range(nclusters),key=lambda cid:(-targets[cid],prng.random(),cid))
        region_heap=[(-r['cell_count'],r['id']) for r in regions]
        heapq.heapify(region_heap)
        for cid in order:
            _score,rid=heapq.heappop(region_heap)
            cluster_region[cid]=rid
            region_members[rid]+=targets[cid]
            heapq.heappush(region_heap,(-region_map[rid]['cell_count']/(1.0+region_members[rid]),rid))

        # Plan anchors jointly over residual rooms and fixed board sectors.  A sector
        # receives no territory reservation: its load only determines where the next
        # compact component group starts.  A room may span many sectors, so region-only
        # shuffling would repeatedly pick one part of that room.
        nx,ny=getattr(self,'_component_gap_grid_shape',self.component_gap_grid_shape())
        def sector(c):
            return (min(7,8*c[0]//max(1,nx)),min(7,8*c[1]//max(1,ny)))
        sector_cells={}
        for reg in regions:
            rid=reg['id']
            for c in reg['cells']:
                sector_cells.setdefault((rid,sector(c)),[]).append(c)
        for cells in sector_cells.values():
            cells.sort(key=lambda c:(-float(clearance.get(c,0.0)),prng.random(),c[1],c[0]))
        region_sectors={rid:[] for rid in region_map}
        for rid,sec in sector_cells:
            region_sectors[rid].append(sec)
        sector_load={}; anchor_index=SpatialHash(max(2.0,float(max(nx,ny)//8)))
        anchor_sep=max(2,int(round(.62*math.sqrt(max(1.0,len(open_cells)/max(1,nclusters))))))
        anchors={}
        for cid in order:
            rid=cluster_region[cid]
            choices=region_sectors[rid]
            def sector_rank(sec):
                sx,sy=sec
                macro_nx,macro_ny=getattr(
                    self,'_residual_macro_grid_shape',
                    (max(1,int(round(nx/math.sqrt(165.0)))),
                     max(1,int(round(ny/math.sqrt(165.0))))))
                macro_x=min(macro_nx-1,int(macro_nx*(sx+.5)/8))
                macro_y=min(macro_ny-1,int(macro_ny*(sy+.5)/8))
                paired_owner=(macro_x+macro_y)%2
                neighbours=sum(sector_load.get((sx+dx,sy+dy),0)
                               for dx in (-1,0,1) for dy in (-1,0,1)
                               if dx or dy)
                return (paired_owner,sector_load.get(sec,0),neighbours,
                        -len(sector_cells[(rid,sec)]),sec[1],sec[0])
            selected_sector=min(choices,key=sector_rank)
            cells=sector_cells[(rid,selected_sector)]
            chosen=None
            for c in cells[:min(len(cells),32)]:
                x,y=c
                near=anchor_index.query((x-anchor_sep,y-anchor_sep,x+anchor_sep,y+anchor_sep))
                if all((x-a[0])**2+(y-a[1])**2>=anchor_sep*anchor_sep for a in near):
                    chosen=c; break
            if chosen is None:
                chosen=cells[0]
            anchors[cid]=chosen
            sector_load[selected_sector]=sector_load.get(selected_sector,0)+targets[cid]
            anchor_index.insert(chosen,(chosen[0],chosen[1],chosen[0],chosen[1]))
        self._component_gap_planned_sector_load=dict(sector_load)

        cw=self.W/max(1,nx); ch=self.H/max(1,ny)
        used_cells=set(); sites=[]; site_cids=[]; meta={}
        for cid in range(nclusters):
            rid=cluster_region[cid]; reg=region_map[rid]; ax,ay=anchors[cid]
            want=quotas[cid]
            # A 12-member cluster gets a larger neighbourhood than a singular, but the radius is
            # bounded by the 1..12 language and therefore independent of total board territory.
            base_radius=max(3,int(math.ceil(2.4*math.sqrt(max(1,targets[cid])))))
            candidate_records=[]; seen=set()
            for radius in (base_radius,base_radius+3,base_radius+6):
                for gy in range(max(0,ay-radius),min(ny-1,ay+radius)+1):
                    for gx in range(max(0,ax-radius),min(nx-1,ax+radius)+1):
                        c=(gx,gy)
                        if c in seen or c in used_cells or c not in reg['cells']:
                            continue
                        seen.add(c)
                        d2=(gx-ax)*(gx-ax)+(gy-ay)*(gy-ay)
                        candidate_records.append((d2,-float(clearance.get(c,0.0)),prng.random(),c))
                if len(candidate_records)>=max(want*4,want+8):
                    break
            candidate_records.sort()
            selected=[]
            # Keep neighbouring opportunities near the shared anchor, but not on top of one
            # another.  Exact component clearance remains the authority during placement.
            for _d2,_negc,_rand,c in candidate_records:
                if any((c[0]-q[0])**2+(c[1]-q[1])**2<2.25 for q in selected):
                    continue
                selected.append(c); used_cells.add(c)
                if len(selected)>=want:
                    break
            # Tight pockets may not admit the preferred inter-site separation.  Reuse additional
            # nearby cells before ever leaving the cluster neighbourhood.
            if len(selected)<want:
                for _d2,_negc,_rand,c in candidate_records:
                    if c in selected or c in used_cells:
                        continue
                    selected.append(c); used_cells.add(c)
                    if len(selected)>=want:
                        break
            anchor_pt=((ax+.5)*cw,(ay+.5)*ch)
            meta[cid]=dict(id=cid,region_id=reg.get('parent_region_id',rid),target_members=int(targets[cid]),
                           anchor_cell=(ax,ay),anchor=anchor_pt,site_count=len(selected))
            for gx,gy in selected:
                sites.append(((gx+.5)*cw,(gy+.5)*ch,reg.get('parent_region_id',rid))); site_cids.append(cid)

        # If an exceptionally tight residual field yielded fewer site tokens than the historical
        # denominator requested, fill only the missing *opportunities* from still-open cells.
        # Assign each one to the nearest cluster in its region.  This is a rare construction
        # backstop and does not change cluster membership caps.
        if len(sites)<count:
            anchors_by_region={}
            for cid,m in meta.items(): anchors_by_region.setdefault(m['region_id'],[]).append(cid)
            leftovers=list(open_cells-used_cells); prng.shuffle(leftovers)
            for c in leftovers:
                rid=self._component_gap_region_by_cell.get(c)
                cids=anchors_by_region.get(rid) or list(meta)
                if not cids: break
                cid=min(cids,key=lambda z:(c[0]-anchors[z][0])**2+(c[1]-anchors[z][1])**2)
                gx,gy=c; sites.append(((gx+.5)*cw,(gy+.5)*ch,rid)); site_cids.append(cid)
                if len(sites)>=count: break

        self._component_gap_cluster_meta=meta
        self._component_gap_site_cluster_ids=site_cids[:len(sites)]
        self._component_gap_cluster_targets=[int(x) for x in targets]
        return sites[:count]

    def _find_residual_gap_sites(self, chips:List[Group], pathways:List[Group], rng:SplitMix64, count:int, component_count=None):
        """Return area-weighted sites from connected residual regions after the frozen main network.

        V33 uses a 28x28 free-space field and connected components.  Site quotas are allocated
        proportional to region area, so a large room gets several component opportunities while
        a small pocket gets one small-object opportunity instead of being treated equivalently.
        Returned tuples are (x, y, region_id); placement remains exact-geometry validated.
        """
        requested_count=max(0,int(count))
        # Even a zero-component budget still needs the canonical post-MAIN residual denominator
        # for LOCAL density accounting.  Build the field, then return no component sites.
        # Residual-cell certificates use a fast buffered-obstacle STRtree.  The buffer radii are
        # deliberately inflated so the finite-segment polygons are conservative supersets of the
        # exact Euclidean keepouts (see `_conservative_clearance_buffer_radius`).  Distance to
        # this superset may be slightly smaller than the true available clearance, never larger;
        # therefore the later 1-Lipschitz candidate-radius certificate cannot admit a component
        # that violates exact chip/pathway clearance.
        q=8
        chip_radius=self._conservative_clearance_buffer_radius(self.component_chip_clearance,q)
        path_radius=self._conservative_clearance_buffer_radius(self.component_pathway_clearance,q)
        buffered=[g.geom.buffer(chip_radius,quad_segs=q) for g in chips]
        buffered += [p.geom.buffer(path_radius,quad_segs=q) for g in pathways for p in g.primitives]
        blocked_tree=STRtree(buffered) if buffered else None
        nx,ny=self.component_gap_grid_shape(); cw=self.W/nx; ch=self.H/ny; edge=self.component_edge_clearance
        open_cells=set(); clearance={}
        cells=[]; xs=[]; ys=[]
        for gy in range(ny):
            for gx in range(nx):
                x=(gx+.5)*cw; y=(gy+.5)*ch
                if x<edge or y<edge or x>self.W-edge or y>self.H-edge: continue
                cells.append((gx,gy)); xs.append(x); ys.append(y)
        if blocked_tree is None:
            dists=[min(self.W,self.H)]*len(cells)
        elif cells:
            qpts=shapely.points(xs,ys)
            _pairs,darray=blocked_tree.query_nearest(qpts,return_distance=True,all_matches=False)
            dists=[float(x) for x in darray]
        else:
            dists=[]
        for cell,d in zip(cells,dists):
            if d<=1e-12: continue
            open_cells.add(cell); clearance[cell]=d
        regions=[]; unseen=set(open_cells); rid=0
        # NIGHTLY Item-23: preserve the exact historical ``min(unseen)`` region-seed order
        # without rescanning the entire remaining set once per connected component.  Tuple
        # ordering is gx-major then gy, so a fixed gx/gy grid walk is identical to repeatedly
        # taking min(unseen), but connected-region discovery is linear in the service grid.
        for seed_gx in range(nx):
            for seed_gy in range(ny):
                seed=(seed_gx,seed_gy)
                if seed not in unseen:
                    continue
                unseen.remove(seed); stack=[seed]; cells=[]
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
        self._component_gap_clearance=dict(clearance)
        self._component_gap_grid_shape=(nx,ny)
        self._component_gap_grid_n=max(nx,ny)  # legacy diagnostic compatibility only
        self._build_residual_composition_ownership(open_cells,regions,rng)
        if not regions or requested_count<=0:
            self._component_gap_cluster_meta={}
            self._component_gap_site_cluster_ids=[]
            self._component_gap_cluster_targets=[]
            return []
        count=requested_count
        if component_count is None:
            component_count=getattr(self,'_component_gap_planned_component_count',None)
        if component_count is not None:
            component_cells=self._residual_composition_component_cells
            owned_regions=[]
            for reg in regions:
                cells=reg['cells'] & component_cells
                if not cells: continue
                xs=[c[0] for c in cells]; ys=[c[1] for c in cells]
                owned_regions.append(dict(reg,cells=cells,cell_count=len(cells),
                    width=(max(xs)-min(xs)+1)*cw,height=(max(ys)-min(ys)+1)*ch,
                    parent_region_id=reg['id']))
            return self._component_clustered_gap_sites(
                owned_regions,component_cells,clearance,rng,count,max(1,int(component_count)))
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
        # Area-weight the remaining opportunities with the exact historical priority, but do
        # not rescan every region for every additional site.  Only the selected region's quota
        # changes, so a pop/update/push heap reproduces max(cell_count/(q+1), -rid) exactly.
        quota_heap=[]
        for r in ordered_regions:
            rid=r['id']; score=r['cell_count']/(quotas[rid]+1.0)
            heapq.heappush(quota_heap,(-score,rid))
        while used<count and quota_heap:
            _neg_score,rid=heapq.heappop(quota_heap)
            quotas[rid]+=1; used+=1
            r=regions[rid]; score=r['cell_count']/(quotas[rid]+1.0)
            heapq.heappush(quota_heap,(-score,rid))
        sites=[]
        for r in sorted(regions,key=lambda z:(-z['cell_count'],z['id'])):
            want=quotas.get(r['id'],0)
            if want<=0: continue
            # NIGHTLY Item-23: generate the exact historical seeded rank records, then
            # consume only as much of that order as placement actually needs.  Full sorting was
            # O(N log N) for every residual region even when only a few sites were requested.
            # A heap preserves the same (-clearance-score, random, stable-input-order) ordering
            # while avoiding ranking cells that are never inspected.
            candidates=[]
            for serial,(gx,gy) in enumerate(r['cells']):
                x=(gx+.5)*cw; y=(gy+.5)*ch
                # Clearance first; mild centre preference avoids hugging ragged region edges.
                c=clearance.get((gx,gy),0.0)
                dc=math.hypot(x-r['center'][0],y-r['center'][1])
                candidates.append((-(c-.08*dc),rng.random(),serial,x,y))
            heapq.heapify(candidates)
            selected=[]; popped=[]; sep=.75*max(cw,ch)
            selected_index=SpatialHash(max(sep,1e-6))
            while candidates and len(selected)<want:
                rec=heapq.heappop(candidates); popped.append(rec)
                _neg,_rand,_serial,x,y=rec
                if any(math.hypot(x-a,y-b)<sep
                       for a,b in selected_index.query((x-sep,y-sep,x+sep,y+sep))):
                    continue
                selected.append((x,y)); selected_index.insert((x,y),(x,y,x,y)); sites.append((x,y,r['id']))
            if len(selected)<want:
                # The separation pass only reaches this branch after exhausting the heap, so
                # ``popped`` is the complete historical rank order.  Reuse it for the original
                # no-separation fallback without another sort.
                for _neg,_rand,_serial,x,y in popped:
                    if (x,y) in selected: continue
                    selected.append((x,y)); sites.append((x,y,r['id']))
                    if len(selected)>=want: break
        return sites[:count]

    def _component_region_is_substantial(self,region):
        """Whether a residual region belongs to the mandatory component-fill field.

        V37 intentionally allows thin slivers and tiny isolated cavities to remain negative
        space.  A mandatory room must contain at least four service-grid cells and be at least
        about two cells wide on its short axis; larger cell counts can rescue mildly irregular
        rooms.  Optional pockets may still receive micro fillers when they happen to fit.
        """
        cells=max(0,int(region.get('cell_count',0)))
        nx,ny=getattr(self,'_component_gap_grid_shape',self.component_gap_grid_shape())
        cell_short=min(self.W/max(1,nx),self.H/max(1,ny))
        short=float(region.get('short_span',0.0))
        return cells>=4 and (short>=1.75*cell_short or cells>=10)

    def _component_region_quota_units(self,region):
        """Gap-aware size×quantity requirement for a substantial residual room.

        Thin/tiny optional pockets carry zero mandatory quota.  Substantial rooms require one
        useful unit at minimum, then progressively more units with area; a large room therefore
        cannot be declared served by one token dot, but it also does not demand dozens of
        components merely because routing fragmented the board into many small cells.
        """
        if not self._component_region_is_substantial(region):
            return 0.0
        cells=max(1,int(region.get('cell_count',1)))
        short_u=float(region.get('short_span',0.0))/max(self.U,1e-9)
        if cells<=10 or short_u<70.0:
            return 1.0
        if cells<=24 or short_u<150.0:
            return max(1.0,math.ceil(cells/14.0))
        return max(2.0,math.ceil(cells/13.0))

    def _component_group_capacity_units(self,g):
        """Physical size contribution used by the residual-region service target."""
        w,h=bounds_w_h(g.bounds)
        span=max(w,h); base=max(34.0*self.U,1e-9)
        # Tiny pocket motifs still count, but a large collection can satisfy several units of
        # a large room's requirement.  Cap it so one giant group cannot represent a whole room.
        return max(.45,min(2.75,span/base))

    def _component_region_capacity_fraction(self,components):
        regs=getattr(self,'_component_gap_regions',[])
        if not regs: return 1.0,{},{},{}
        nx,ny=getattr(self,'_component_gap_grid_shape',self.component_gap_grid_shape())
        cw=self.W/max(1,nx); ch=self.H/max(1,ny); bycell=getattr(self,'_component_gap_region_by_cell',{})
        units={r['id']:0.0 for r in regs}; counts={r['id']:0 for r in regs}
        center_tree=STRtree([Point(r['center']) for r in regs]) if regs else None
        for g in components:
            cx,cy=bounds_center(g.bounds)
            cell=(min(nx-1,max(0,int(cx/cw))),min(ny-1,max(0,int(cy/ch))))
            rid=bycell.get(cell)
            if rid is None and center_tree is not None:
                # Exact nearest region centre.  all_matches=True plus the lowest source index
                # preserves the historical stable-list tie break of ``min(regs, key=distance)``.
                near=center_tree.query_nearest(Point(cx,cy),all_matches=True)
                rid=regs[min(int(i) for i in near)]['id']
            units[rid]=units.get(rid,0.0)+self._component_group_capacity_units(g)
            counts[rid]=counts.get(rid,0)+1
        mandatory=[r for r in regs if self._component_region_is_substantial(r)]
        total=sum(r['cell_count'] for r in mandatory)
        served=0.0; quotas={}
        for r in regs:
            q=self._component_region_quota_units(r); quotas[r['id']]=q
            if q<=0.0: continue
            served += r['cell_count']*min(1.0,units.get(r['id'],0.0)/q)
        return ((served/max(1,total)) if mandatory else 1.0),counts,quotas,units

    def _component_cells_claimed_by_group(self,g,claim=None):
        """Residual service-grid cells touched by actual component primitives + half spacing."""
        # V47: the open-cell field is phase-owned read-only state here.  Do not copy the
        # entire board-sized set for every candidate group; membership queries are sufficient.
        cells=getattr(self,'_component_gap_open_cells',set())
        if not cells: return set()
        nx,ny=getattr(self,'_component_gap_grid_shape',self.component_gap_grid_shape()); cw=self.W/max(1,nx); ch=self.H/max(1,ny)
        if claim is None: claim=.5*self.component_component_clearance
        b=g.bounds
        gx0=max(0,int(math.floor((b[0]-claim)/cw-.5))); gx1=min(nx-1,int(math.ceil((b[2]+claim)/cw-.5)))
        gy0=max(0,int(math.floor((b[1]-claim)/ch-.5))); gy1=min(ny-1,int(math.ceil((b[3]+claim)/ch-.5)))
        candidates=[]; xs=[]; ys=[]
        for gx in range(gx0,gx1+1):
            for gy in range(gy0,gy1+1):
                c=(gx,gy)
                if c not in cells: continue
                candidates.append(c); xs.append((gx+.5)*cw); ys.append((gy+.5)*ch)
        if not candidates:
            return set()
        points=shapely.points(xs,ys)
        mask=shapely.dwithin(g.collision_geom,points,claim)
        return {c for c,hit in zip(candidates,mask) if bool(hit)}

    def _component_claimed_gap_cells(self,components):
        """Residual cells visually served by component geometry plus a bounded breathing halo."""
        out=set()
        for g in components: out.update(self._component_cells_claimed_by_group(g))
        return out

    def _component_residual_size_class(self,region):
        """Classify a connected residual room by its real physical extent, not one chosen cell."""
        if region is None:
            return 'small'
        short_u=float(region.get('short_span',0.0))/max(self.U,1e-9)
        cells=max(1,int(region.get('cell_count',1)))
        if short_u<30.0 or cells<=3:
            return 'micro'
        if short_u<55.0 or cells<8:
            return 'small'
        if short_u<125.0 or cells<26:
            return 'medium'
        return 'large'

    def _make_residual_micro_component(self,rng,idx):
        """True tiny-pocket fallback.  Never used as the normal language of an open room."""
        fam=rng.weighted([('dot',.38),('dash',.28),('square',.20),('circle',.14)])
        if fam=='dot':
            rad=rng.uniform(1.8,3.2)*self.U
            ps=[prim_circle(0.0,0.0,rad,self.FG,True)]
        elif fam=='dash':
            ln=rng.uniform(4.0,8.0)*self.U; th=rng.uniform(1.5,2.2)*self.U
            if rng.random()<.5: ps=[prim_line(-ln/2,0.0,ln/2,0.0,th,self.FG)]
            else: ps=[prim_line(0.0,-ln/2,0.0,ln/2,th,self.FG)]
        elif fam=='square':
            side=rng.uniform(4.0,7.0)*self.U
            ps=[prim_rect_outline(0.0,0.0,side,side,0.0,max(1.2*self.U,.24*side),self.FG)]
        else:
            rad=rng.uniform(2.2,3.8)*self.U
            ps=[prim_circle(0.0,0.0,rad,self.FG,False,max(1.2*self.U,.38*rad))]
        return Group(f"residual-micro-{idx}",ps,dict(
            family=fam,entity_count=1,isolated=True,residual_filler=True,
            residual_compound=False,residual_micro=True,residual_gap_size='micro',
            residual_gap_scale_P=max(bounds_w_h(Group('tmp',ps,{}).bounds))))

    def _make_compact_residual_compound(self,rng,idx,parent_size):
        """Construct a canonical two-family collection for a tight site in a larger room."""
        anchor='ic' if rng.random()<.52 else 'dense'
        family=rng.weighted([('capacitor_circle',.32),('square',.17),
                             ('circle',.17),('dot',.17),('dash',.17)])
        border_probability=.92 if parent_size=='large' else .82
        border=rng.random()<border_probability
        assignment=dict(families=[anchor,family],border=border,family_count=2,
                        complexity=.5,tier=2)
        collection=self._make_collection_once(rng,10000+idx,assignment)
        if collection is None:
            collection=self._construct_collection_fallback(
                rng.state,10000+idx,assignment,planning=_BOUNDS_ONLY)
        collection.name=f'residual-assembly-{idx}'
        collection.structural.update(dict(
            isolated=True,residual_filler=True,residual_compound=True,residual_micro=False,
            residual_gap_size=parent_size,residual_compact_fit=True,
            residual_assembly_border=border,residual_assembly_family_count=2))
        return collection

    def _make_residual_compound_component(self,rng,idx,region):
        """Build a coherent multi-family residual assembly using the established collection grammar.

        V33-V36 allowed medium and large rooms to be completed by standalone ordinary subgroups.
        That was geometrically legal but visually regressed into scattered dots/dashes.  V37 uses
        the same IC/dense/ordinary collection machinery as the historical proper components, with
        a high border probability and gap-aware scale.  Single-token primitives remain micro-only.
        """
        size=self._component_residual_size_class(region)
        if size=='micro':
            return self._make_residual_micro_component(rng,idx)
        if region.get('compact_local_opportunity',False) and size in ('medium','large'):
            return self._make_compact_residual_compound(rng,idx,size)

        # A small residual room may legitimately want one capacitor, but otherwise every
        # non-micro recovery object is a compound assembly with at least two entity families.
        if size=='small' and not region.get('require_compound',False) and rng.random()<.34:
            ps,meta=self._capacitor_entity_primitives(rng,0.0,0.0)
            return Group(f"residual-capacitor-{idx}",ps,dict(
                family='capacitor_circle',entity_count=1,isolated=True,residual_filler=True,
                residual_compound=False,residual_micro=False,residual_gap_size='small',**meta))

        if size=='small':
            family_count=2
            border_probability=.68
            scale_range=(.68,.84)
        elif size=='medium':
            family_count=2 if rng.random()<.42 else 3
            border_probability=.82
            scale_range=(.82,1.00)
        else:
            family_count=3 if rng.random()<.55 else 4
            border_probability=.92
            scale_range=(.96,1.16)

        ordinary=['square','circle','capacitor_circle','dot','dash']
        for _ in range(28):
            families=[]
            # Medium/large assemblies are anchored by an unmistakably structured entity family.
            if size in ('medium','large'):
                families.append('ic' if rng.random()<.52 else 'dense')
                if size=='large' and family_count>=4 and rng.random()<.62:
                    families.append('dense' if families[0]=='ic' else 'ic')
            elif rng.random()<.55:
                families.append('dense' if rng.random()<.55 else 'ic')
            pool=[f for f in ordinary if f not in families]
            while len(families)<family_count and pool:
                weights=[]
                for f in pool:
                    w=2.0 if f=='capacitor_circle' else 1.0
                    weights.append((f,w))
                f=rng.weighted(weights); families.append(f); pool.remove(f)
            if len(families)<2:
                continue
            assignment=dict(families=families,border=(rng.random()<border_probability),
                            family_count=len(families),complexity=.5,tier=len(families))
            g=self._make_collection_once(rng,10000+idx,assignment)
            if g is None:
                continue
            g=g.transformed(scale=rng.uniform(*scale_range),name=f"residual-assembly-{idx}")
            g.structural=dict(g.structural)
            g.structural.update(dict(isolated=True,residual_filler=True,residual_compound=True,
                                     residual_micro=False,residual_gap_size=size,
                                     residual_assembly_border=bool(assignment['border']),
                                     residual_assembly_family_count=len(families)))
            return g
        # Deterministic bounded fallback: a capacitor is still a coherent component entity and
        # is preferable to inventing a standalone dash/dot in a room large enough for assembly.
        ps,meta=self._capacitor_entity_primitives(rng,0.0,0.0)
        return Group(f"residual-capacitor-{idx}",ps,dict(
            family='capacitor_circle',entity_count=1,isolated=True,residual_filler=True,
            residual_compound=False,residual_micro=False,residual_gap_size=size,**meta))

    def _make_residual_filler_component(self,rng,idx,region):
        # Compatibility entry point retained for tests/callers; V37's implementation is
        # assembly-first and delegates singleton geometry only to genuine micro rooms.
        return self._make_residual_compound_component(rng,idx,region)

    def _component_sentinel_rejects_accepted(self, obj:Group, x:float, y:float, accepted_index, cache) -> bool:
        """Conservative accepted-component broad phase using at most two candidate primitives.

        A sentinel collision is a sufficient condition for whole-candidate rejection.  A miss is
        deliberately inconclusive and falls through to the historical exact validator.
        """
        if accepted_index is None or not obj.primitives:
            return False
        cached=cache.get('current')
        sentinels=(cached[1] if cached is not None and cached[0] is obj else None)
        if sentinels is None:
            ob=obj.bounds; ocx=(ob[0]+ob[2])*.5; ocy=(ob[1]+ob[3])*.5
            ranked=[]
            for i,p in enumerate(obj.primitives):
                b=p.geom.bounds; w=b[2]-b[0]; h=b[3]-b[1]; pcx=(b[0]+b[2])*.5; pcy=(b[1]+b[3])*.5
                # Favor substantial, central primitives; deterministic index tie-break.
                score=(w*h)/(1.0+math.hypot(pcx-ocx,pcy-ocy)/max(self.U,1e-9))
                ranked.append((-score,i,p))
            ranked.sort(key=lambda z:(z[0],z[1]))
            sentinels=tuple(z[2] for z in ranked[:2])
            cache.clear(); cache['current']=(obj,sentinels)
        gap=self.component_component_clearance
        for p in sentinels:
            def _move(coords):
                out=coords.copy(); out[:,0]+=x; out[:,1]+=y; return out
            pg=shapely.transform([p.geom],_move)[0]
            pb=pg.bounds
            nearby=accepted_index.query(expand_bounds(pb,gap))
            for other in nearby:
                if not self._bounds_within_gap(pb,other.bounds,gap):
                    continue
                # Distance to a GeometryCollection is the exact minimum over its member
                # primitives, matching the historical primitive-pair clearance predicate while
                # avoiding a second Python-level spatial-index walk for this one sentinel.
                if pg.distance(other.collision_geom)<gap:
                    return True
        return False

    def place_residual_components(self, collections:List[Group], isolated:List[Group], chips:List[Group],
                                  pathways:List[Group], rng:SplitMix64, target=None, fallback_attempts=28):
        """Final pass: populate the routed board's residual gaps with components."""
        accepted=[]; attached=[]; remaining_isolated=list(isolated)
        accepted_index=SpatialHash(max(48.0*self.U,4.0*self.component_component_clearance))
        component_sentinel_cache={}
        chip_keepout=GeometryCollection()
        chip_component_index=SpatialHash(max(64.0*self.U,4.0*self.component_chip_clearance))
        chip_q=8
        chip_keepout_radius=self._conservative_clearance_buffer_radius(self.component_chip_clearance,chip_q)
        for cg0 in chips:
            kg=cg0.geom.buffer(chip_keepout_radius,quad_segs=chip_q)
            chip_component_index.insert(dict(geom=kg,chip=cg0),kg.bounds)
        pathway_keepout=GeometryCollection()  # exact candidate checks use the indexed per-path keepouts below
        pathway_component_index=SpatialHash(max(64.0*self.U,4.0*self.component_pathway_clearance))
        for pg in pathways:
            for prim in pg.primitives:
                # V47 memory: index immutable raw path primitives.  Do not retain one buffered
                # GEOS keepout per rendered primitive for the entire component phase; exact
                # buffers are materialized only for nearby candidate queries.
                pathway_component_index.insert(dict(pathway=pg,primitive=prim),
                                               expand_bounds(prim.geom.bounds,self.component_pathway_clearance))
        # V47 locality: component-pathway keepouts are immutable during this phase, but
        # retaining their GEOS polygons costs tens of MiB.  Cache only compact WKB bytes and
        # reconstruct temporary exact GEOS objects on reuse; the dict dies with this phase.
        pathway_keepout_wkb_cache={}
        terminal_records=self._free_terminal_records(pathways)
        rng.shuffle(terminal_records)
        # Rare reversed connection: preserve the historical draw/order, but treat free terminals
        # as owned local opportunities. Prove the strict endpoint-contact semantics first; only a
        # genuine attachment opportunity pays the general component admission gate.
        if remaining_isolated and terminal_records and rng.random() < self.component_pathway_attachment_probability:
            cap=remaining_isolated.pop(0)
            for pt,owner in terminal_records:
                probe=cap.transformed_geometry_only(pt[0],pt[1])
                if (self._component_attachment_local_valid(probe,pt,owner,pathway_component_index) and
                        self._component_candidate_valid(probe,'isolated',chips,pathways,accepted,attachment_point=pt,chip_keepout=chip_keepout,pathway_keepout=pathway_keepout,accepted_index=accepted_index,pathway_component_index=pathway_component_index,chip_component_index=chip_component_index,pathway_keepout_wkb_cache=pathway_keepout_wkb_cache)):
                    cand=cap.transformed(pt[0],pt[1])
                    cand.structural['placement_kind']='isolated'
                    cand.structural['component_pathway_attached']=True
                    cand.structural['component_pathway_attachment_point']=(pt[0],pt[1])
                    accepted.append(cand); accepted_index.insert(cand,cand.bounds); attached.append(cand); break

        gap_objects=[('collection',g) for g in collections] + [('isolated',g) for g in remaining_isolated]
        # Fit larger objects first so capacitors naturally mop up smaller residual pockets.
        gap_objects.sort(key=lambda kg:(bounds_w_h(kg[1].bounds)[0]*bounds_w_h(kg[1].bounds)[1]),reverse=True)
        target=(rng.uniform(*self.residual_gap_fill_range) if target is None else float(target))
        # Direct placement callers supply the same component service obligation as
        # the full pipeline.  Ownership must use that obligation even when no
        # enclosing generate_sample call installed the density budget.
        self._active_component_fill_target=target
        site_count=self._residual_gap_site_count(len(gap_objects),target)
        # Preserve the historical overridable _find_residual_gap_sites(chips,pathways,rng,count)
        # contract used by deterministic recovery fixtures.  Base production reads this transient
        # population hint to activate the composition-cluster planner; subclasses need not grow
        # a new parameter merely because composition scheduling changed.
        self._component_gap_planned_component_count=len(gap_objects)
        sites=self._find_residual_gap_sites(chips,pathways,rng,site_count)
        # V46 locality: a site's fit score is region-level; only exact placement is site-level.
        # The historical implementation globally re-sorted every still-unused site for every
        # component, making prepared placement O(components * sites log sites).  Keep one seeded
        # random ordering per region, rank regions per object with the same room-fit formula, and
        # run the unchanged exact collision gate at candidate sites.  This preserves the visual
        # preferences/probabilities while making work follow local opportunities.
        # V47 2B architecture reset: service residual territory first instead of making every
        # prepared component search/re-search the global site population.  ``sites`` are already
        # area-weighted opportunities emitted per connected residual region.  Each site token is
        # consumed once and may inspect only a bounded number of prepared objects; each object may
        # spend only a bounded number of local site failures before entering a bounded recovery
        # path.  Therefore prepared placement work is O(sites + components) for fixed component
        # grammar/local retry constants, rather than O(components * sites).
        #
        # This intentionally does NOT preserve historical failed-attempt/RNG order.  That order is
        # not part of the renderer contract.  The protected contract is same-version determinism,
        # gap-aware population, component grammar/distributions, and exact collision/clearance.
        site_records=list(sites)
        region_map={r['id']:r for r in getattr(self,'_component_gap_regions',[])}
        cluster_meta=dict(getattr(self,'_component_gap_cluster_meta',{}))
        site_cluster_ids=list(getattr(self,'_component_gap_site_cluster_ids',[]))
        if len(site_cluster_ids)<len(site_records):
            site_cluster_ids.extend([None]*(len(site_records)-len(site_cluster_ids)))
        site_ids_by_cluster={}
        for sid,_rec in enumerate(site_records):
            site_ids_by_cluster.setdefault(site_cluster_ids[sid],[]).append(sid)
        # Round-robin cluster servicing is the residual-fill composition rule: singular/small
        # clusters receive their first member alongside the larger 10--12-member clusters instead
        # of one large room consuming the prepared population before another room is visited.
        # Within each cluster, the sites were already generated in seeded near-anchor order.
        cluster_order=list(site_ids_by_cluster)
        cluster_order.sort(key=lambda cid:(rng.random(),-1 if cid is None else int(cid)))
        site_tokens=[]; depth=0
        while True:
            added=False
            for cid in cluster_order:
                ids=site_ids_by_cluster.get(cid,())
                if depth<len(ids):
                    site_tokens.append(ids[depth]); added=True
            if not added:
                break
            depth+=1
        cluster_success_count={cid:0 for cid in cluster_meta}
        cluster_target_count={cid:int(m.get('target_members',12)) for cid,m in cluster_meta.items()}
        recovery_spill_cluster_count=0

        # One max-heap owns the still-unplaced prepared population.  Site servicing peeks at only
        # a fixed metadata lookahead and performs only a fixed number of exact candidate probes.
        # Non-fitting objects are returned immediately; a site can never trigger a scan of the
        # whole prepared population.
        object_records={}
        object_heap=[]
        for oid,(kind,obj) in enumerate(gap_objects):
            ow,oh=bounds_w_h(obj.bounds); area=max(ow*oh,1e-9)
            object_records[oid]=(kind,obj,ow,oh,area)
            heapq.heappush(object_heap,(-area,oid))
        placed_object_ids=set()
        recovery_object_ids=set()
        site_failure_count={oid:0 for oid in object_records}
        served_rids=set()
        scheduler_site_token_count=0
        scheduler_metadata_probe_count=0
        scheduler_exact_candidate_count=0
        scheduler_local_attempt_count=0
        scheduler_recovery_attempt_count=0
        scheduler_site_success_count=0
        # Constants bound *work*, not design population.  They do not scale with board territory.
        metadata_lookahead=32
        exact_candidates_per_site=4
        local_site_fail_budget=4

        def _region_fit_variant(kind,obj,ow,oh,reg,sx,sy):
            """Choose a prepared scale that fits its actual C owner at this site."""
            scales=(1.0,.90,.82,.75,.68,.62) if kind=='collection' else (1.0,)
            nx,ny=self._residual_composition_grid_shape
            c=(min(nx-1,max(0,int(sx*nx/max(self.W,1e-9)))),
               min(ny-1,max(0,int(sy*ny/max(self.H,1e-9)))))
            owner_key=self._residual_component_macro_by_cell.get(c)
            owner=self._residual_component_macro_owners.get(owner_key)
            if owner is None:
                return None
            ob=owner.bounds; b=obj.bounds
            # The connected parent room may cross several disconnected C cores; its bounding
            # box is not a fit certificate for any particular site.  This cheap per-core AABB
            # preflight avoids spending exact geometry work on impossible prepared candidates.
            rw=.98*max(reg.get('width',0.0),1e-9) if reg is not None else float('inf')
            rh=.98*max(reg.get('height',0.0),1e-9) if reg is not None else float('inf')
            for scale in scales:
                if (ow*scale<=rw and oh*scale<=rh and
                        ob[0]<=sx+b[0]*scale and sx+b[2]*scale<=ob[2] and
                        ob[1]<=sy+b[1]*scale and sy+b[3]*scale<=ob[3]):
                    return scale
            return None

        def _try_local_site(kind,obj,scale,sx,sy,local_attempts):
            nonlocal scheduler_local_attempt_count
            sobj=(obj if abs(scale-1.0)<=1e-12 else obj.transformed(scale=scale))
            for attempt in range(local_attempts):
                scheduler_local_attempt_count+=1
                if attempt==0:
                    x,y=sx,sy
                else:
                    radius=(5.0+4.5*attempt)*self.U
                    ang=2*math.pi*rng.random()
                    x=sx+math.cos(ang)*radius; y=sy+math.sin(ang)*radius
                if accepted and self._component_sentinel_rejects_accepted(sobj,x,y,accepted_index,component_sentinel_cache):
                    continue
                probe=sobj.transformed_geometry_only(x,y)
                if not self._component_candidate_valid(probe,kind,chips,pathways,accepted,
                                                       chip_keepout=chip_keepout,pathway_keepout=pathway_keepout,
                                                       accepted_index=accepted_index,pathway_component_index=pathway_component_index,
                                                       chip_component_index=chip_component_index,
                                                       pathway_keepout_wkb_cache=pathway_keepout_wkb_cache):
                    continue
                chosen=sobj.transformed(x,y); chosen.structural['placement_kind']=kind
                if scale<1.0-1e-12:
                    chosen.structural['residual_gap_fit_scale']=scale
                return chosen
            return None

        for sid in site_tokens:
            if not object_heap:
                break
            scheduler_site_token_count+=1
            sx,sy,rid=site_records[sid]
            cid=site_cluster_ids[sid] if sid < len(site_cluster_ids) else None
            if cid is not None and cluster_success_count.get(cid,0) >= cluster_target_count.get(cid,12):
                continue
            reg=region_map.get(rid)
            held=[]
            chosen=None; chosen_oid=None
            exact_used=0
            metadata_used=0
            while object_heap and metadata_used<metadata_lookahead and exact_used<exact_candidates_per_site:
                neg_area,oid=heapq.heappop(object_heap)
                if oid in placed_object_ids or oid in recovery_object_ids:
                    continue
                kind,obj,ow,oh,_area=object_records[oid]
                metadata_used+=1; scheduler_metadata_probe_count+=1
                scale=_region_fit_variant(kind,obj,ow,oh,reg,sx,sy)
                if scale is None:
                    held.append((neg_area,oid))
                    continue
                exact_used+=1; scheduler_exact_candidate_count+=1
                local_attempts=8 if abs(scale-1.0)<=1e-12 else 5
                cand=_try_local_site(kind,obj,scale,sx,sy,local_attempts)
                if cand is not None:
                    chosen=cand; chosen_oid=oid
                    break
                site_failure_count[oid]+=1
                if site_failure_count[oid]>=local_site_fail_budget:
                    recovery_object_ids.add(oid)
                else:
                    held.append((neg_area,oid))
            for rec in held:
                heapq.heappush(object_heap,rec)
            if chosen is None:
                continue
            placed_object_ids.add(chosen_oid)
            if cid is not None:
                chosen.structural['residual_fill_cluster_id']=int(cid)
                chosen.structural['residual_fill_cluster_target']=int(cluster_target_count.get(cid,12))
                cluster_success_count[cid]=cluster_success_count.get(cid,0)+1
            accepted.append(chosen); accepted_index.insert(chosen,chosen.bounds)
            scheduler_site_success_count+=1
            if rid is not None:
                served_rids.add(rid)

        # Anything not consumed by local territory tokens receives a bounded recovery budget.
        # This is intentionally O(components): no recovery object may enumerate the site set.
        remaining_ids=set(recovery_object_ids)
        while object_heap:
            _neg,oid=heapq.heappop(object_heap)
            if oid not in placed_object_ids:
                remaining_ids.add(oid)
        failed=[]
        for oid in sorted(remaining_ids,key=lambda i:(-object_records[i][4],i)):
            kind,obj,ow,oh,_area=object_records[oid]
            chosen=None; chosen_rid=None
            scales=(1.0,.90,.82,.75) if kind=='collection' else (1.0,)
            # Prefer bounded samples from measured residual territories.  Each draw is O(1) and
            # may revisit a site; the number of draws never grows with site population.
            if site_records:
                local_budget=max(4,min(max(0,int(fallback_attempts)),16))
                underfilled=[cid for cid in cluster_meta
                             if cluster_success_count.get(cid,0) < cluster_target_count.get(cid,12)
                             and site_ids_by_cluster.get(cid)]
                for _ in range(local_budget):
                    scheduler_recovery_attempt_count+=1
                    if underfilled:
                        # Seeded bounded servicing of outstanding prepared-cluster membership.
                        cid=underfilled[int(rng.random()*len(underfilled)) % len(underfilled)]
                        ids=site_ids_by_cluster[cid]
                        sid=ids[int(rng.random()*len(ids)) % len(ids)]
                    else:
                        cid=None
                        sid=int(rng.random()*len(site_records))
                    sx,sy,rid=site_records[min(sid,len(site_records)-1)]
                    if cid is not None and cluster_success_count.get(cid,0)>=cluster_target_count.get(cid,12):
                        continue
                    reg=region_map.get(rid)
                    scale=_region_fit_variant(kind,obj,ow,oh,reg,sx,sy)
                    if scale is None:
                        continue
                    cand=_try_local_site(kind,obj,scale,sx,sy,3)
                    if cand is not None:
                        chosen=cand; chosen_rid=rid
                        if cid is not None:
                            chosen.structural['residual_fill_cluster_id']=int(cid)
                            chosen.structural['residual_fill_cluster_target']=int(cluster_target_count.get(cid,12))
                            cluster_success_count[cid]=cluster_success_count.get(cid,0)+1
                        break
            # Last-resort board-wide placement remains bounded per object.  It is recovery, not
            # the normal scheduler, and therefore cannot recreate a component x site wedge.
            if chosen is None:
                for scale in scales:
                    sobj=(obj if abs(scale-1.0)<=1e-12 else obj.transformed(scale=scale))
                    l,r,t,b=self.legal_center_ranges(sobj,self.component_edge_clearance)
                    if l>r or t>b:
                        continue
                    budget=max(0,int(fallback_attempts))
                    for _ in range(budget):
                        scheduler_recovery_attempt_count+=1
                        x=rng.uniform(l,r); y=rng.uniform(t,b)
                        if not self._residual_composition_component_center((x,y)):
                            continue
                        if accepted and self._component_sentinel_rejects_accepted(sobj,x,y,accepted_index,component_sentinel_cache):
                            continue
                        probe=sobj.transformed_geometry_only(x,y)
                        if not self._component_candidate_valid(probe,kind,chips,pathways,accepted,
                                                               chip_keepout=chip_keepout,pathway_keepout=pathway_keepout,
                                                               accepted_index=accepted_index,pathway_component_index=pathway_component_index,
                                                               chip_component_index=chip_component_index,
                                                               pathway_keepout_wkb_cache=pathway_keepout_wkb_cache):
                            continue
                        chosen=sobj.transformed(x,y); chosen.structural['placement_kind']=kind
                        if scale<1.0-1e-12:
                            chosen.structural['residual_gap_fit_scale']=scale
                        break
                    if chosen is not None:
                        break
            # Deterministic residual-center completion.  The stochastic scheduler above exists
            # for speed/visual variance; it is not allowed to decide whether this prepared
            # component exists.  Exhaust the finite measured residual centers exactly, with the
            # same gap-aware scale variants and unchanged collision/clearance predicates.
            if chosen is None:
                deterministic_centers=[]
                seen_centers=set()
                for sx,sy,rid in site_records:
                    key=(round(sx,9),round(sy,9))
                    if key not in seen_centers:
                        seen_centers.add(key); deterministic_centers.append((sx,sy,rid))
                # Site sampling can be intentionally sparse.  Add every residual service-cell
                # center so the completion path covers the actual finite residual field.
                ocells=sorted(getattr(self,'_component_gap_open_cells',set()) &
                              getattr(self,'_residual_composition_component_cells',set()))
                gx,gy=getattr(self,'_component_gap_grid_shape',self.component_gap_grid_shape())
                gcw=self.W/max(1,gx); gch=self.H/max(1,gy)
                cmap=getattr(self,'_component_gap_region_by_cell',{})
                for cell in ocells:
                    sx=(cell[0]+.5)*gcw; sy=(cell[1]+.5)*gch; rid=cmap.get(cell)
                    key=(round(sx,9),round(sy,9))
                    if key not in seen_centers:
                        seen_centers.add(key); deterministic_centers.append((sx,sy,rid))
                for scale in scales:
                    sobj=(obj if abs(scale-1.0)<=1e-12 else obj.transformed(scale=scale))
                    for sx,sy,rid in deterministic_centers:
                        scheduler_recovery_attempt_count+=1
                        if accepted and self._component_sentinel_rejects_accepted(sobj,sx,sy,accepted_index,component_sentinel_cache):
                            continue
                        probe=sobj.transformed_geometry_only(sx,sy)
                        if not self._component_candidate_valid(probe,kind,chips,pathways,accepted,
                                                               chip_keepout=chip_keepout,pathway_keepout=pathway_keepout,
                                                               accepted_index=accepted_index,pathway_component_index=pathway_component_index,
                                                               chip_component_index=chip_component_index,
                                                               pathway_keepout_wkb_cache=pathway_keepout_wkb_cache):
                            continue
                        chosen=sobj.transformed(sx,sy); chosen.structural['placement_kind']=kind
                        chosen.structural['deterministic_residual_completion']=True
                        if scale<1.0-1e-12:
                            chosen.structural['residual_gap_fit_scale']=scale
                        chosen_rid=rid
                        break
                    if chosen is not None:
                        break
            if chosen is None:
                failed.append((kind,obj))
                continue
            if 'residual_fill_cluster_id' not in chosen.structural:
                spill_id=1_000_000+recovery_spill_cluster_count
                recovery_spill_cluster_count+=1
                chosen.structural['residual_fill_cluster_id']=spill_id
                chosen.structural['residual_fill_cluster_target']=1
                chosen.structural['residual_fill_cluster_recovery_spill']=True
            accepted.append(chosen); accepted_index.insert(chosen,chosen.bounds)
            placed_object_ids.add(oid)
            if chosen_rid is not None:
                served_rids.add(chosen_rid)
            else:
                cx,cy=bounds_center(chosen.bounds)
                regs0=getattr(self,'_component_gap_regions',[])
                if regs0:
                    served_rids.add(min(regs0,key=lambda rr:(rr['center'][0]-cx)**2+(rr['center'][1]-cy)**2)['id'])

        regs=getattr(self,'_component_gap_regions',[])
        mandatory_regs=[r for r in regs if self._component_region_is_substantial(r)]
        total_region_cells=sum(r['cell_count'] for r in mandatory_regs)
        served_region_cells=sum(r['cell_count'] for r in mandatory_regs if r['id'] in served_rids)
        served_area_fraction=(served_region_cells/total_region_cells if total_region_cells else 1.0)

        # V37 assembly-first residual completion.  Normal collections establish the primary
        # component language.  Additional capacity is supplied by coherent multi-family residual
        # assemblies; single dots/dashes are legal only in genuinely micro connected pockets.
        extra_fillers=[]; attempted_cells=set()
        compound_fillers=[]; micro_fillers=[]; singleton_fillers=[]
        filler_static_clearance_certificate_hits=0
        open_cells=set(getattr(self,'_component_gap_open_cells',set())) & set(
            getattr(self,'_residual_composition_component_cells',set()))
        region_map={r['id']:r for r in regs}; cell_region=getattr(self,'_component_gap_region_by_cell',{})
        nxreg,nyreg=getattr(self,'_component_gap_grid_shape',self.component_gap_grid_shape()); cw=self.W/max(1,nxreg); ch=self.H/max(1,nyreg)
        fill_goal=max(0.0,min(1.0,float(target)))
        claimed=self._component_claimed_gap_cells(accepted)
        claimed_fraction=(len(claimed)/len(open_cells) if open_cells else 1.0)
        # Coarse mosaic occupancy is composition bookkeeping only.  It prevents the residual
        # completion path from repeatedly selecting the same macroscopic patch of a large room.
        mosaic_nx=mosaic_ny=8
        component_mosaic_counts={}
        def _component_mosaic_key_xy(x,y):
            return (min(mosaic_nx-1,max(0,int(mosaic_nx*x/max(self.W,1e-9)))),
                    min(mosaic_ny-1,max(0,int(mosaic_ny*y/max(self.H,1e-9)))))
        for _g in accepted:
            _cx,_cy=bounds_center(_g.bounds); _mk=_component_mosaic_key_xy(_cx,_cy)
            component_mosaic_counts[_mk]=component_mosaic_counts.get(_mk,0)+1
        def _component_mosaic_count_cell(c):
            _x=(c[0]+.5)*cw; _y=(c[1]+.5)*ch
            return component_mosaic_counts.get(_component_mosaic_key_xy(_x,_y),0)
        def _component_mosaic_key_cell(c):
            _x=(c[0]+.5)*cw; _y=(c[1]+.5)*ch
            return _component_mosaic_key_xy(_x,_y)

        # Completion fillers are ordinary residual composition too.  Treating every one as an
        # unrelated singleton lets hundreds of individually legal fillers visually coalesce into
        # one macroscopic colony.  Keep one bounded active 1..12-member completion cluster at a
        # time and disperse *cluster anchors* across the coarse residual mosaic.  The component
        # constructors and exact placement predicates below remain unchanged.
        completion_cluster_rng=SplitMix64(mix_once(int(getattr(rng,'state',0)) ^ 0xD1B54A32D192ED03))
        completion_cluster_active=None
        completion_cluster_serial=0
        component_cluster_tile_counts={}
        _existing_cluster_centres={}
        for _g in accepted:
            _cid=_g.structural.get('residual_fill_cluster_id')
            if _cid is None:
                continue
            _cx,_cy=bounds_center(_g.bounds)
            _sx,_sy,_n=_existing_cluster_centres.get(_cid,(0.0,0.0,0))
            _existing_cluster_centres[_cid]=(_sx+_cx,_sy+_cy,_n+1)
        for _sx,_sy,_n in _existing_cluster_centres.values():
            _mk=_component_mosaic_key_xy(_sx/_n,_sy/_n)
            component_cluster_tile_counts[_mk]=component_cluster_tile_counts.get(_mk,0)+1
        def _completion_cluster_radius(target):
            # Bounded in the 1..12 design language.  This is composition locality, not search
            # breadth; exact component clearance still decides every admitted object.
            return max(3,min(7,int(math.ceil(1.55*math.sqrt(max(1,int(target)))))))
        def _completion_cluster_cells(cluster,limit=48):
            ax,ay=cluster['anchor_cell']; rid=cluster['region_id']; radius=cluster['radius']+2
            out=[]
            for gy in range(max(0,ay-radius),min(nyreg-1,ay+radius)+1):
                for gx in range(max(0,ax-radius),min(nxreg-1,ax+radius)+1):
                    c=(gx,gy)
                    if c in _unavailable or c not in open_cells or cell_region.get(c)!=rid:
                        continue
                    d2=(gx-ax)*(gx-ax)+(gy-ay)*(gy-ay)
                    if d2>(radius*radius):
                        continue
                    out.append((d2,-_gap_clear.get(c,0.0),c[1],c[0],c))
            out.sort()
            return [rec[-1] for rec in out[:limit]]
        # V44 fine-scale performance: completion ranking is region-first by definition.
        # The old implementation rebuilt ``open - claimed - attempted`` and rescanned every
        # residual cell after *every* filler merely to discover the same ranking:
        #   (region quota deficit, region uncovered-cell count, cell clearance).
        # At scale=.35 that logical field contains ~8x as many cells, turning an otherwise local
        # completion process into O(cells * fillers).  Maintain the same ordering incrementally:
        # region-level keys are recomputed cheaply, while each region owns a static clearance-
        # sorted cell list and unavailable cells are skipped lazily.  Exact placement/clearance
        # validation below is unchanged.
        _gap_clear=getattr(self,'_component_gap_clearance',{})
        _unavailable=set(claimed)

        # Constant-size board mosaic (8x8) is the macroscopic composition scheduler.  New
        # completion-cluster anchors service the least-loaded *open-space-normalized* tile first,
        # then exact region deficit/clearance decides the concrete cell.  This is what prevents a
        # single huge connected residual region from owning hundreds of fillers merely because it
        # has the largest regional quota.  Sixty-four tiles is a fixed bound, so this adds no
        # scale-dependent search term.
        _tile_cells={}
        _tile_open_count={}
        for _c in open_cells:
            _mk=_component_mosaic_key_cell(_c)
            _tile_cells.setdefault(_mk,[]).append(_c)
            _tile_open_count[_mk]=_tile_open_count.get(_mk,0)+1
        _tile_cells_sorted={mk:sorted(cells,key=lambda c:(-_gap_clear.get(c,0.0),c[1],c[0]))
                            for mk,cells in _tile_cells.items()}
        _tile_cursor={mk:0 for mk in _tile_cells_sorted}
        _tile_available_count={mk:sum(1 for c in cells if c not in _unavailable)
                               for mk,cells in _tile_cells.items()}
        component_tile_capacity_units={}
        for _g in accepted:
            _cx,_cy=bounds_center(_g.bounds); _mk=_component_mosaic_key_xy(_cx,_cy)
            component_tile_capacity_units[_mk]=component_tile_capacity_units.get(_mk,0.0)+self._component_group_capacity_units(_g)

        _region_available_count={r['id']:sum(1 for c in r['cells'] if c in open_cells and c not in _unavailable) for r in regs}
        _available_cell_total=sum(_region_available_count.values())
        _region_cells_sorted={}
        _region_cursor={}
        for r in regs:
            rid=r['id']
            _region_cells_sorted[rid]=sorted((c for c in r['cells'] if c in open_cells),
                                             key=lambda c:(-_gap_clear.get(c,0.0),c[1],c[0]))
            _region_cursor[rid]=0
        # Residual completion's semantic region priority changes only when that region loses an
        # available cell or gains component-capacity units.  Keep an exact lazy priority heap
        # rather than rebuilding + sorting every region for every filler.  The heap key is the
        # historical sort key expressed for a min-heap: highest deficit, then highest remaining
        # cell count, then lowest region id.
        capacity_fraction,region_component_counts,region_quota_units,region_capacity_units=self._component_region_capacity_fraction(accepted)
        _region_rank_version={rid:0 for rid in _region_available_count}
        _region_rank_heap=[]
        def _region_rank_values(rid):
            count_avail=_region_available_count.get(rid,0)
            q=float(region_quota_units.get(rid,0.0))
            have=region_capacity_units.get(rid,0.0)
            deficit=(max(0.0,1.0-have/q) if q>0.0 else -1.0)
            return deficit,count_avail
        def _push_region_rank(rid):
            deficit,count_avail=_region_rank_values(rid)
            if count_avail<=0:
                return
            heapq.heappush(_region_rank_heap,(-deficit,-count_avail,rid,_region_rank_version[rid]))
        def _peek_valid_region_rank():
            while _region_rank_heap:
                rec=_region_rank_heap[0]
                _nd,_nc,rid,ver=rec
                if ver!=_region_rank_version.get(rid,-1) or _region_available_count.get(rid,0)<=0:
                    heapq.heappop(_region_rank_heap)
                    continue
                return rec
            return None
        for _rid in _region_available_count:
            _push_region_rank(_rid)
        def _refresh_region_rank(rid):
            if rid not in _region_rank_version:
                return
            _region_rank_version[rid]+=1
            _push_region_rank(rid)
        def _mark_component_cell_unavailable(c):
            nonlocal _available_cell_total
            if c in _unavailable or c not in open_cells:
                return
            _unavailable.add(c)
            mk=_component_mosaic_key_cell(c)
            if mk in _tile_available_count:
                _tile_available_count[mk]=max(0,_tile_available_count[mk]-1)
            rid=cell_region.get(c)
            if rid in _region_available_count:
                before=_region_available_count[rid]
                after=max(0,before-1)
                _region_available_count[rid]=after
                _available_cell_total-=before-after
                _refresh_region_rank(rid)
        def _top_component_cells(rid,limit):
            seq=_region_cells_sorted.get(rid,())
            i=_region_cursor.get(rid,0)
            while i<len(seq) and seq[i] in _unavailable:
                i+=1
            _region_cursor[rid]=i
            out=[]; j=i
            while j<len(seq) and len(out)<limit:
                c=seq[j]
                if c not in _unavailable:
                    out.append(c)
                j+=1
            return out
        def _top_component_tile_cells(mk,limit):
            seq=_tile_cells_sorted.get(mk,())
            i=_tile_cursor.get(mk,0)
            while i<len(seq) and seq[i] in _unavailable:
                i+=1
            _tile_cursor[mk]=i
            out=[]; j=i
            while j<len(seq) and len(out)<limit:
                c=seq[j]
                if c not in _unavailable:
                    out.append(c)
                j+=1
            return out
        macro_nx,macro_ny=self._residual_macro_grid_shape
        macro_owner_keys=tuple(getattr(self,'_residual_component_macro_owners',{}))
        parcel_pitch=min(self.W/macro_nx,self.H/macro_ny)
        tile_nearest_c={}
        for mk in _tile_open_count:
            x=(mk[0]+.5)*self.W/mosaic_nx; y=(mk[1]+.5)*self.H/mosaic_ny
            tile_nearest_c[mk]=min(
                ((x-(ix+.5)*self.W/macro_nx)**2+
                 (y-(iy+.5)*self.H/macro_ny)**2 for ix,iy in macro_owner_keys),
                default=float('inf'))
        def _component_tile_rank(mk):
            denom=max(1,_tile_open_count.get(mk,0))
            cluster_count=component_cluster_tile_counts.get(mk,0)
            anchor_density=component_cluster_tile_counts.get(mk,0)/denom
            capacity_density=component_tile_capacity_units.get(mk,0.0)/denom
            availability=_tile_available_count.get(mk,0)/denom
            return (cluster_count,
                    int(tile_nearest_c.get(mk,float('inf'))/(.22*parcel_pitch)**2),
                    anchor_density,capacity_density,-availability,mk[1],mk[0])
        # A large residual room must contain multiple size-appropriate component units.  Raw
        # component count is a secondary density floor; the primary ~90% metric is the
        # area-weighted fulfilment of those per-region capacity requirements.
        mandatory_cell_count=sum(r['cell_count'] for r in mandatory_regs)
        # V37's first residual phase is governed by the 50-60% area-weighted capacity target.
        # The V35 90% regime needed an additional dense-count floor; retaining that floor here
        # would mechanically drive the board back toward ~100% component service before local
        # lines even start.  Regional quota units already encode size×quantity variation, so no
        # independent density quota is needed in the 50-60% phase.
        desired_total=len(accepted)
        _comp_loop_iter=0
        # Seed-totality: completion is bounded by monotonic residual-cell retirement, not by
        # an arbitrary board-wide filler-count ceiling.  Every failed candidate below retires
        # its attempted service cell; every successful filler claims/retire at least its chosen
        # cell.  Therefore this loop is finite in the residual service-field size while remaining
        # free to reach the hard floor whenever legal residual capacity still exists.
        while ((capacity_fraction+1e-9 < fill_goal) or (served_area_fraction+1e-9 < fill_goal) or len(accepted)<desired_total):
            _comp_loop_iter+=1
            if _available_cell_total<=0: break
            # Preserve the V37 ranking exactly: region deficit first, then remaining unserved
            # area, then frozen residual-cell clearance.  Pull only enough highest-ranked
            # regions to supply the historical 48-cell shortlist; lazy versions discard stale
            # heap entries after local state changes.
            strongest=[]; _rank_records_to_restore=[]
            # Continue the current bounded cluster locally.  If that parcel is exhausted, close
            # it early and start a new dispersed cluster rather than spilling into its neighbours.
            if completion_cluster_active is not None:
                strongest=_completion_cluster_cells(completion_cluster_active,48)
                if not strongest:
                    completion_cluster_active=None
            if not strongest:
                # New clusters are chosen across the whole residual field by macroscopic tile
                # load, not by connected-region quota.  Region quota still remains the capacity
                # accounting/termination authority and is a secondary ranking inside each tile.
                tile_order=sorted((mk for mk,n in _tile_available_count.items() if n>0),key=_component_tile_rank)
                pool=[]
                for mk in tile_order[:8]:
                    pool.extend(_top_component_tile_cells(mk,8))
                def _new_cluster_cell_key(c):
                    mk=_component_mosaic_key_cell(c); rid=cell_region.get(c)
                    deficit=_region_rank_values(rid)[0] if rid in _region_available_count else -1.0
                    return (_component_tile_rank(mk),-deficit,
                            component_cluster_tile_counts.get(mk,0),
                            _component_mosaic_count_cell(c),-_gap_clear.get(c,0.0),c[1],c[0])
                pool.sort(key=_new_cluster_cell_key)
                strongest=pool[:48]
            for rec in _rank_records_to_restore:
                heapq.heappush(_region_rank_heap,rec)
            if not strongest:
                break
            placed=None; chosen_cell=None
            # Try a handful of the strongest uncovered cells; failed cells are remembered so a
            # narrow impossible pocket cannot dominate the loop.
            for cell in strongest:
                gx,gy=cell; rid=cell_region.get(cell); reg=region_map.get(rid)
                # Fine-scale pressure creates many locally tight cells whose sampled residual
                # assemblies are guaranteed to die at the size gate.  Do not burden ordinary
                # cells with a planning pass: only locally tight rooms enter this preflight.
                # The thresholds are expressed solely in canonical component units and depend
                # on the existing residual size class, never on canvas aspect ratio or scale.
                static_clear=float(getattr(self,'_component_gap_clearance',{}).get(cell,max(cw,ch)))
                sx=(gx+.5)*cw; sy=(gy+.5)*ch
                owner_key=self._residual_component_macro_by_cell.get(cell)
                owner=self._residual_component_macro_owners.get(owner_key)
                if owner is None:
                    attempted_cells.add(cell); _mark_component_cell_unavailable(cell)
                    continue
                ox0,oy0,ox1,oy1=owner.bounds
                owner_clear=max(0.0,min(sx-ox0,ox1-sx,sy-oy0,oy1-sy))
                local_clear=min(static_clear,owner_clear)
                # A large connected parent room can contain a small remaining
                # component opportunity. Measure accepted geometry locally before
                # choosing the assembly size; the parent room still owns its
                # original service quota and tiny motifs stay micro-room only.
                if accepted and local_clear>0.0:
                    search=local_clear+self.component_component_clearance
                    point=Point(sx,sy)
                    near=accepted_index.query((sx-search,sy-search,sx+search,sy+search))
                    for other in near:
                        local_clear=min(local_clear,max(0.0,
                            point.distance(other.collision_geom)-self.component_component_clearance))
                fit_region=reg
                if reg is not None and self._component_residual_size_class(reg) in ('medium','large') and local_clear<40.0*self.U:
                    fit_region=dict(reg,compact_local_opportunity=True,require_compound=True)
                filler=None
                risk_limit=None
                # The widest preflight band is 40U.  Most ordinary/easy-board cells are wider
                # than that and stay on the historical direct-construction path without even
                # paying a residual-size classification call.
                if local_clear < 40.0*self.U:
                    size_class=self._component_residual_size_class(fit_region)
                    if size_class=='large': risk_limit=40.0*self.U
                    elif size_class=='medium': risk_limit=22.0*self.U
                    else: risk_limit=14.0*self.U
                if risk_limit is not None and local_clear < risk_limit:
                    filler_rng_state=rng.state
                    plan_rng=SplitMix64(filler_rng_state)
                    with bounds_only_mode(True):
                        filler_plan=self._make_residual_filler_component(plan_rng,len(extra_fillers),fit_region)
                    planned_post_state=plan_rng.state
                    plan_micro=bool(filler_plan.structural.get('residual_micro'))
                    plan_compound=bool(filler_plan.structural.get('residual_compound'))
                    if plan_micro and len(micro_fillers)>=self.component_micro_filler_limit:
                        rng.state=planned_post_state
                        attempted_cells.add(cell); _mark_component_cell_unavailable(cell)
                        continue
                    pfw,pfh=bounds_w_h(filler_plan.bounds); pfspan=max(pfw,pfh)
                    pspan_factor=1.90 if plan_compound else 1.62
                    pmax_span=max((18.0 if plan_compound else 8.0)*self.U,pspan_factor*local_clear)
                    pmin_scale=.72 if plan_compound else (.62 if plan_micro else .72)
                    # Bounds-only envelopes and exact GEOS AABBs can differ by a few ulps.
                    # Pre-reject only with a much larger guard band; all ambiguous candidates
                    # replay into exact geometry and use the historical exact size calculation.
                    span_guard=max(1e-9*self.U,1e-12*max(1.0,abs(pfspan),abs(pmax_span)))
                    if pfspan-span_guard > pmax_span/pmin_scale:
                        rng.state=planned_post_state
                        attempted_cells.add(cell); _mark_component_cell_unavailable(cell)
                        continue
                    exact_rng=SplitMix64(filler_rng_state)
                    filler=self._make_residual_filler_component(exact_rng,len(extra_fillers),fit_region)
                    if exact_rng.state != planned_post_state:
                        raise RuntimeError('residual filler risk preflight RNG replay diverged')
                    rng.state=planned_post_state
                else:
                    filler=self._make_residual_filler_component(rng,len(extra_fillers),fit_region)
                is_micro=bool(filler.structural.get('residual_micro'))
                is_compound=bool(filler.structural.get('residual_compound'))
                if is_micro and len(micro_fillers)>=self.component_micro_filler_limit:
                    attempted_cells.add(cell); _mark_component_cell_unavailable(cell)
                    continue
                # Local clearance chooses *where* a room can host an assembly; it no longer
                # crushes a proper medium/large assembly into a token-sized glyph.  If a compound
                # object would need more than modest adaptation, skip this cell and seek a wider
                # point in the same/another room.  Tiny geometry is reserved for micro regions.
                fw,fh=bounds_w_h(filler.bounds); fspan=max(fw,fh)
                span_factor=1.90 if is_compound else 1.62
                max_span=max((18.0 if is_compound else 8.0)*self.U,span_factor*local_clear)
                if fspan>max_span and fspan>1e-9:
                    needed=max_span/fspan
                    min_scale=.72 if is_compound else (.62 if is_micro else .72)
                    if needed<min_scale:
                        attempted_cells.add(cell); _mark_component_cell_unavailable(cell)
                        continue
                    filler=filler.transformed(scale=needed)
                    filler.structural['residual_gap_clearance_scaled']=True
                for attempt in range(5):
                    if attempt==0: x,y=sx,sy
                    else:
                        rad=(2.5+3.0*attempt)*self.U; ang=2*math.pi*rng.random()
                        x=sx+math.cos(ang)*rad; y=sy+math.sin(ang)*rad
                    if accepted and self._component_sentinel_rejects_accepted(filler,x,y,accepted_index,component_sentinel_cache):
                        continue
                    probe=filler.transformed_geometry_only(x,y)
                    # The residual field stores exact distance from this cell centre to immutable
                    # chip/pathway geometry already expanded by component keepout. Distance-to-set
                    # is 1-Lipschitz, so a jitter of d leaves at least (local_clear-d) guaranteed
                    # radial room. A bounds-corner radius encloses every candidate collision point.
                    fb=filler.bounds
                    radial=max(abs(fb[0]),abs(fb[2])); radial_y=max(abs(fb[1]),abs(fb[3]))
                    radial=math.hypot(radial,radial_y)
                    jitter=math.hypot(x-sx,y-sy)
                    static_certified=(radial <= max(0.0,local_clear-jitter)+1e-12)
                    if static_certified:
                        valid=self._component_candidate_valid_after_static_certificate(probe,accepted,accepted_index)
                        if valid:
                            filler_static_clearance_certificate_hits+=1
                    else:
                        valid=self._component_candidate_valid(probe,'isolated',chips,pathways,accepted,
                                                             chip_keepout=chip_keepout,pathway_keepout=pathway_keepout,accepted_index=accepted_index,pathway_component_index=pathway_component_index,chip_component_index=chip_component_index,pathway_keepout_wkb_cache=pathway_keepout_wkb_cache)
                    if valid:
                        placed=filler.transformed(x,y); placed.structural['placement_kind']='isolated'
                        chosen_cell=cell; break
                if placed is not None: break
                attempted_cells.add(cell); _mark_component_cell_unavailable(cell)
            if placed is None:
                # The highest-priority cells may belong to a locally saturated pocket.  Close an
                # under-realized completion cluster rather than letting it leak into a distant
                # parcel; the next iteration will choose a new dispersed anchor.
                if completion_cluster_active is not None:
                    completion_cluster_active=None
                continue
            if completion_cluster_active is None:
                _target=self.residual_fill_cluster_member_target(completion_cluster_rng)
                _cid=2_000_000+completion_cluster_serial
                completion_cluster_serial+=1
                completion_cluster_active=dict(
                    id=_cid,target=int(_target),count=0,
                    anchor_cell=chosen_cell,region_id=cell_region.get(chosen_cell),
                    radius=_completion_cluster_radius(_target),
                    center_sum_x=0.0,center_sum_y=0.0,mosaic_key=None,
                )
            _cluster=completion_cluster_active
            placed.structural['residual_fill_cluster_id']=int(_cluster['id'])
            placed.structural['residual_fill_cluster_target']=int(_cluster['target'])
            placed.structural['residual_fill_cluster_completion']=True
            _cluster['count']+=1
            accepted.append(placed); accepted_index.insert(placed,placed.bounds); extra_fillers.append(placed)
            _pcx,_pcy=bounds_center(placed.bounds); _pmk=_component_mosaic_key_xy(_pcx,_pcy)
            _cluster['center_sum_x']+=_pcx; _cluster['center_sum_y']+=_pcy
            _new_cluster_mk=_component_mosaic_key_xy(
                _cluster['center_sum_x']/_cluster['count'],
                _cluster['center_sum_y']/_cluster['count'])
            _old_cluster_mk=_cluster['mosaic_key']
            if _new_cluster_mk!=_old_cluster_mk:
                if _old_cluster_mk is not None:
                    component_cluster_tile_counts[_old_cluster_mk]-=1
                component_cluster_tile_counts[_new_cluster_mk]=component_cluster_tile_counts.get(_new_cluster_mk,0)+1
                _cluster['mosaic_key']=_new_cluster_mk
            if _cluster['count']>=_cluster['target']:
                completion_cluster_active=None
            component_mosaic_counts[_pmk]=component_mosaic_counts.get(_pmk,0)+1
            component_tile_capacity_units[_pmk]=component_tile_capacity_units.get(_pmk,0.0)+self._component_group_capacity_units(placed)
            if placed.structural.get('residual_compound'):
                compound_fillers.append(placed)
            elif placed.structural.get('residual_micro'):
                micro_fillers.append(placed)
            else:
                singleton_fillers.append(placed)
            rid=cell_region.get(chosen_cell)
            was_served=(rid in served_rids) if rid is not None else False
            if rid is not None: served_rids.add(rid)
            # V42 performance: update residual service incrementally. Recomputing the capacity
            # of every accepted component after each new filler made tall-board completion
            # quadratic in component count. Only the chosen region's units can change here.
            newly_claimed=self._component_cells_claimed_by_group(placed)-claimed
            claimed.update(newly_claimed)
            for c in newly_claimed:
                _mark_component_cell_unavailable(c)
            _mark_component_cell_unavailable(chosen_cell)
            claimed_fraction=(len(claimed)/len(open_cells) if open_cells else 1.0)
            if rid is not None:
                old_units=float(region_capacity_units.get(rid,0.0))
                add_units=self._component_group_capacity_units(placed)
                new_units=old_units+add_units
                region_capacity_units[rid]=new_units
                region_component_counts[rid]=region_component_counts.get(rid,0)+1
                _refresh_region_rank(rid)
                q=float(region_quota_units.get(rid,0.0))
                reg=region_map.get(rid)
                if q>0.0 and reg is not None and total_region_cells:
                    old_share=min(1.0,old_units/q)
                    new_share=min(1.0,new_units/q)
                    capacity_fraction += (reg['cell_count']*(new_share-old_share))/total_region_cells
                    capacity_fraction=min(1.0,max(0.0,capacity_fraction))
                if (not was_served) and reg is not None and self._component_region_is_substantial(reg):
                    served_region_cells += reg['cell_count']
            served_area_fraction=(served_region_cells/total_region_cells if total_region_cells else 1.0)

        served_region_cells=sum(r['cell_count'] for r in mandatory_regs if r['id'] in served_rids)
        served_area_fraction=(served_region_cells/total_region_cells if total_region_cells else 1.0)

        placed_gap_count=len(accepted)-len(attached)
        # Coverage count includes the bounded residual fillers; sites remain the area-weighted
        # normal population benchmark, so cap at 1.0 rather than reporting >100%.
        site_actual=min(1.0,(placed_gap_count/len(sites))) if sites else (1.0 if placed_gap_count==0 else 0.0)
        # V47: capacity_fraction/counts/units have been maintained incrementally for every
        # filler accepted after the one initial baseline recount above.  A second all-component
        # recount here is redundant and was a tall-board quadratic hot path.
        actual=min(capacity_fraction,served_area_fraction)
        size_counts={}
        size_spans={}
        for g in accepted:
            sz=g.structural.get('residual_gap_size')
            if sz is None: continue
            size_counts[sz]=size_counts.get(sz,0)+1
            size_spans.setdefault(sz,[]).append(max(bounds_w_h(g.bounds)))
        size_span_means={k:(sum(v)/len(v) if v else 0.0) for k,v in size_spans.items()}
        component_cluster_counts={}
        component_cluster_targets={}
        component_cluster_spills=0
        component_completion_cluster_ids=set()
        for g in accepted:
            cid=g.structural.get('residual_fill_cluster_id')
            if cid is None:
                continue
            component_cluster_counts[cid]=component_cluster_counts.get(cid,0)+1
            component_cluster_targets[cid]=int(g.structural.get('residual_fill_cluster_target',1))
            if g.structural.get('residual_fill_cluster_recovery_spill'):
                component_cluster_spills+=1
            if g.structural.get('residual_fill_cluster_completion'):
                component_completion_cluster_ids.add(cid)
        component_cluster_realized=list(component_cluster_counts.values())
        component_cluster_target_values=list(component_cluster_targets.values())
        stats=dict(
            component_placement_mode='post_main_pre_local_residual_gap_fill',
            component_residual_gap_fill_target=target,
            component_residual_gap_site_count=len(sites),
            component_residual_gap_site_requested_count=site_count,
            component_residual_gap_region_count=len(getattr(self,'_component_gap_regions',[])),
            component_residual_gap_mandatory_region_count=len(mandatory_regs),
            component_residual_gap_optional_region_count=max(0,len(regs)-len(mandatory_regs)),
            component_residual_gap_open_cell_count=sum(r['cell_count'] for r in getattr(self,'_component_gap_regions',[])),
            component_residual_gap_served_region_area_fraction=served_area_fraction,
            component_residual_gap_claimed_cell_count=len(claimed),
            component_residual_gap_claimed_area_fraction=claimed_fraction,
            component_residual_gap_region_capacity_fraction=capacity_fraction,
            component_residual_gap_region_component_counts=dict(region_component_counts),
            component_residual_gap_region_quota_units=dict(region_quota_units),
            component_residual_gap_served_region_count=len(served_rids),
            component_residual_gap_extra_filler_count=len(extra_fillers),
            component_residual_gap_compound_filler_count=len(compound_fillers),
            component_residual_gap_micro_filler_count=len(micro_fillers),
            component_residual_gap_singleton_filler_count=len(singleton_fillers),
            component_residual_gap_static_clearance_certificate_hits=filler_static_clearance_certificate_hits,
            component_residual_gap_compound_filler_fraction=(len(compound_fillers)/len(extra_fillers) if extra_fillers else 1.0),
            component_residual_gap_micro_filler_limit=self.component_micro_filler_limit,
            component_residual_gap_extra_filler_limit=self.component_extra_filler_limit,
            component_residual_gap_completion_uses_legacy_filler_cap=False,
            component_residual_gap_completion_remaining_open_cell_count=_available_cell_total,
            component_residual_gap_grid_shape=list(getattr(self,'_component_gap_grid_shape',self.component_gap_grid_shape())),
            component_residual_gap_density_target_count=desired_total,
            component_residual_gap_total_component_count=len(accepted),
            component_residual_gap_size_counts=dict(size_counts),
            component_residual_gap_size_mean_spans=dict(size_span_means),
            component_residual_gap_placed_count=placed_gap_count,
            component_residual_gap_fill_actual=actual,
            component_residual_gap_site_fill_actual=site_actual,
            component_residual_fill_cluster_count=len(component_cluster_counts),
            component_residual_fill_cluster_realized_min=min(component_cluster_realized,default=0),
            component_residual_fill_cluster_realized_max=max(component_cluster_realized,default=0),
            component_residual_fill_cluster_target_min=min(component_cluster_target_values,default=0),
            component_residual_fill_cluster_target_max=max(component_cluster_target_values,default=0),
            component_residual_fill_cluster_singleton_count=sum(1 for v in component_cluster_realized if v==1),
            component_residual_fill_cluster_large_10_12_count=sum(1 for v in component_cluster_realized if 10<=v<=12),
            component_residual_fill_cluster_recovery_spill_count=component_cluster_spills,
            component_residual_fill_completion_cluster_count=len(component_completion_cluster_ids),
            component_gap_scheduler_mode='territory_first_bounded_local_tokens',
            component_gap_scheduler_site_token_count=scheduler_site_token_count,
            component_gap_scheduler_site_success_count=scheduler_site_success_count,
            component_gap_scheduler_metadata_probe_count=scheduler_metadata_probe_count,
            component_gap_scheduler_exact_candidate_count=scheduler_exact_candidate_count,
            component_gap_scheduler_local_attempt_count=scheduler_local_attempt_count,
            component_gap_scheduler_recovery_attempt_count=scheduler_recovery_attempt_count,
            component_gap_scheduler_recovery_object_count=len(recovery_object_ids),
            component_gap_scheduler_prepared_object_count=len(gap_objects),
            component_pathway_attachment_count=len(attached),
            component_pathway_attachment_probability=self.component_pathway_attachment_probability,
            component_unplaced_count=len(failed),
            component_chip_clearance=self.component_chip_clearance,
            component_pathway_clearance=self.component_pathway_clearance,
            component_component_clearance=self.component_component_clearance,
        )
        return accepted,stats

    def _component_chip_clearance_violation_count(self, components:List[Group], chips:List[Group]) -> int:
        """Exact component↔chip clearance audit used as a phase-local construction guard.

        Component placement is required to make this zero by construction.  This audit is not
        an acceptance lottery and never causes a whole-board seed retry; it guards the component
        phase itself so an admission-regression cannot survive until the final sample validator.
        """
        if not components or not chips:
            return 0
        idx=SpatialHash(max(64.0*self.U,4.0*self.component_chip_clearance))
        for chip in chips:
            idx.insert(chip,expand_bounds(chip.bounds,self.component_chip_clearance))
        n=0
        for comp in components:
            for chip in idx.query(expand_bounds(comp.bounds,self.component_chip_clearance)):
                if self._groups_violate_clearance(comp,chip,self.component_chip_clearance-1e-7):
                    n+=1
        return n

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
        # Pair clearances exact, with a spatial broad phase.  Dense V37 residual fill can contain
        # hundreds of components; the old all-to-all loop also topology-unioned every complex
        # collection on demand, which became pathological on some otherwise-valid seeds.
        pindex=SpatialHash(max(48.0*self.U,4.0*self.component_component_clearance))
        pid={id(g):i for i,g in enumerate(placed)}
        for g in placed: pindex.insert(g,g.bounds)
        seen_pairs=set()
        for a in placed:
            ka=a.structural.get("placement_kind")
            query_gap=(self.chip_chip_clearance if ka=="chip" else self.component_chip_clearance)
            for b in pindex.query(expand_bounds(a.bounds,query_gap)):
                if b is a: continue
                pair=tuple(sorted((pid[id(a)],pid[id(b)])))
                if pair in seen_pairs: continue
                seen_pairs.add(pair)
                kb=b.structural.get("placement_kind")
                gap=self.chip_chip_clearance if ka==kb=="chip" else self.component_chip_clearance if "chip" in (ka,kb) else self.component_component_clearance
                # Fast bounds rejection for the actual pair-specific gap before exact geometry.
                ab=a.bounds; bb=b.bounds
                if (ab[2]+gap < bb[0] or bb[2]+gap < ab[0] or ab[3]+gap < bb[1] or bb[3]+gap < ab[1]):
                    continue
                if self._groups_violate_clearance(a,b,max(0.0,gap-1e-7)): errors.append(f"pair_{ka}_{kb}")
        # Batch-level component-language quotas/calibration describe the full legacy component
        # population.  When the new residual density knobs deliberately thin that population,
        # those *count/distribution* contracts are no longer applicable; exact frame/clearance and
        # per-object construction/contact validity remain mandatory.  At the default (or any
        # above-legacy component budget) the full population is retained and the historical
        # validation path is byte-for-byte unchanged.
        full_component_language=(float(getattr(self,'_active_component_population_scale',1.0))>=1.0-1e-15)
        fams=[set(g.structural.get("families",())) for g in cols]
        if full_component_language:
            # Scale calibration belongs to the generated component language, not the final
            # gap-adapted instance footprint.  V37 may boundedly shrink an oversized collection to
            # 90/82/75% so it fits a real residual room; the source template was already calibrated
            # and validated before routing.  Undo only that explicit fit scale here so a legitimate
            # space-aware adaptation cannot trigger an expensive late whole-board rejection.
            L=[max(bounds_w_h(g.bounds))/max(1e-9,float(g.structural.get("residual_gap_fit_scale",1.0))) for g in cols]
            qs=[g.structural["q_chip"] for g in chips]
            if L:
                if sum(.026*S<=x<=.073*S for x in L)/len(L)<.80: errors.append("collection_core_fraction")
                med=lambda xs: sorted(xs)[len(xs)//2] if len(xs)%2 else .5*(sorted(xs)[len(xs)//2-1]+sorted(xs)[len(xs)//2])
                mL=med(L); mq=med(qs)
                if not (.040*S<=mL<=.052*S): errors.append("collection_median")
                if not (.42<=mL/mq<=.56): errors.append("collection_chip_ratio")
            # quotas / coverage
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
        # Chip uniqueness is literal generated geometry, not a coarse motif/aspect bin.
        sigs=set()
        for g in chips:
            s=self._chip_geometry_fingerprint(g)
            if s in sigs: errors.append("chip_duplicate_geometry")
            sigs.add(s)
        return errors

    def _collection_calibration_thresholds(self, chips, assigns):
        S=self.S
        med=lambda xs: sorted(xs)[len(xs)//2] if len(xs)%2 else .5*(sorted(xs)[len(xs)//2-1]+sorted(xs)[len(xs)//2])
        qs=[g.structural["q_chip"] for g in chips]
        mq=med(qs)
        median_lo=max(.040*S,.42*mq); median_hi=min(.052*S,.56*mq)
        return dict(mq=mq,median_lo=median_lo,median_hi=median_hi,core_lo=.026*S,core_hi=.073*S)

    def _collection_calibration_category(self, chips, assigns, i, g, thresholds=None):
        t=thresholds or self._collection_calibration_thresholds(chips,assigns)
        L=max(bounds_w_h(g.bounds))
        m=int(t['median_lo']<=L<=t['median_hi'])
        c=int(t['core_lo']<=L<=t['core_hi'])
        d=0
        if "dense" in assigns[i]["families"]:
            dims=[sg.get("dense_dims") for sg in g.structural.get("subgroups",[]) if sg.get("family")=="dense"]
            d=int(bool(dims) and all(max(r,c0)/min(r,c0)>=2.5 for r,c0 in dims))
        return (m,c,d)

    def _solve_collection_pool_selection(self, pools, needs):
        """Choose one existing candidate per collection without N-scaled DP memory.

        For legacy-size populations (<=32) V46 deliberately runs the historical exact capped
        DP, which makes differential tests exact.  Large true-zoom populations use deterministic
        deficit repair over the same candidate masks; candidate generation continues if the
        current pool is not yet sufficient.  The acceptance predicates themselves are unchanged.
        """
        N=len(pools); median_need,core_need,dense_need=needs
        if N<=32:
            dp={(0,0,0): []}
            for i in range(N):
                ndp={}
                for (m,c,d),sel in dp.items():
                    for (am,ac,ad),g in sorted(pools[i].items()):
                        ns=(min(median_need,m+am),min(core_need,c+ac),min(dense_need,d+ad))
                        if ns not in ndp: ndp[ns]=sel+[g]
                dp=ndp
            return dp.get((median_need,core_need,dense_need))
        # Impossible individual maxima can be rejected immediately.
        maxima=[sum(max((mask[j] for mask in pool),default=0) for pool in pools) for j in range(3)]
        if maxima[0]<median_need or maxima[1]<core_need or maxima[2]<dense_need:
            return None
        req=(median_need,core_need,dense_need)
        # Several deterministic weightings cover the only meaningful tradeoff between median/core/dense.
        weight_sets=((6,3,3),(5,5,3),(5,4,5),(4,6,4),(4,4,6),(8,5,5),(5,8,5),(5,5,8),(1,1,1))
        for weights in weight_sets:
            masks=[]
            for pool in pools:
                best=max(sorted(pool),key=lambda m:(sum(weights[j]*m[j] for j in range(3)),sum(m),m))
                masks.append(best)
            counts=[sum(m[j] for m in masks) for j in range(3)]
            # Deterministic single-item augmentations; never sacrifice a requirement already at its floor.
            for _ in range(12):
                deficits=[max(0,req[j]-counts[j]) for j in range(3)]
                if not any(deficits):
                    return [pools[i][masks[i]] for i in range(N)]
                best_move=None
                for i,pool in enumerate(pools):
                    cur=masks[i]
                    for alt in sorted(pool):
                        if alt==cur: continue
                        nc=[counts[j]-cur[j]+alt[j] for j in range(3)]
                        # Do not move a satisfied dimension below its hard requirement.
                        if any(counts[j]>=req[j] and nc[j]<req[j] for j in range(3)): continue
                        gain=sum(max(0,req[j]-counts[j])-max(0,req[j]-nc[j]) for j in range(3))
                        if gain<=0: continue
                        slack=sum(max(0,nc[j]-req[j]) for j in range(3))
                        key=(gain,slack,sum(alt),tuple(alt),-i)
                        if best_move is None or key>best_move[0]: best_move=(key,i,alt,nc)
                if best_move is None: break
                _key,i,alt,nc=best_move; masks[i]=alt; counts=nc
            if all(counts[j]>=req[j] for j in range(3)):
                return [pools[i][masks[i]] for i in range(N)]
        return None

    # ------------------------------ batch calibration -------------------
    def calibrate_collections(self, cur_seed, chips, assigns, initial_cols, max_rounds=256, base_seeds=None):
        """Select already-generated retry candidates so the unchanged batch constraints hold."""
        N=len(initial_cols); S=self.S
        thresholds=self._collection_calibration_thresholds(chips,assigns)
        mq=thresholds['mq']; median_lo=thresholds['median_lo']; median_hi=thresholds['median_hi']
        core_lo,core_hi=thresholds['core_lo'],thresholds['core_hi']
        if median_lo>median_hi: return None
        median_need=N//2+1; core_need=math.ceil(.80*N)
        dense_total=sum("dense" in a["families"] for a in assigns)
        dense_good_need=math.ceil(.60*dense_total)
        bases=list(base_seeds) if base_seeds is not None else [collection_seed(cur_seed,i) for i in range(N)]
        counters=[int(initial_cols[i].structural.get("source_retry_index",0))+1 for i in range(N)]
        pools=[{} for _ in range(N)]
        for i,g in enumerate(initial_cols):
            pools[i][self._collection_calibration_category(chips,assigns,i,g,thresholds)]=g
        needs=(median_need,core_need,dense_good_need)
        chosen=self._solve_collection_pool_selection(pools,needs)
        if chosen is not None: return chosen
        for _round in range(max_rounds):
            for i in range(N):
                possible_cap=6 if "dense" in assigns[i]["families"] else 3  # median=>core eliminates two impossible masks
                if len(pools[i])>=possible_cap: continue
                attempt=counters[i]; counters[i]+=1
                if attempt>=256: continue
                g=self.plan_collection_candidate(bases[i],i,assigns[i],attempt)
                if g is None: continue
                pools[i].setdefault(self._collection_calibration_category(chips,assigns,i,g,thresholds),g)
            chosen=self._solve_collection_pool_selection(pools,needs)
            if chosen is not None:
                # Exact numerical verification; these are the historical acceptance rules.
                L=[max(bounds_w_h(g.bounds)) for g in chosen]
                med=lambda xs: sorted(xs)[len(xs)//2] if len(xs)%2 else .5*(sorted(xs)[len(xs)//2-1]+sorted(xs)[len(xs)//2])
                mL=med(L)
                dense_shapes=[sg["dense_dims"] for g in chosen for sg in g.structural.get("subgroups",[]) if sg.get("family")=="dense"]
                if (sum(core_lo<=x<=core_hi for x in L)>=core_need and
                    .040*S<=mL<=.052*S and .42<=mL/mq<=.56 and
                    (not dense_shapes or sum(max(r,c)/min(r,c)>=2.5 for r,c in dense_shapes)>=dense_good_need)):
                    return chosen
        # Calibration is a construction problem, not a whole-sample acceptance lottery.
        # Build one grammar-valid collection per already-fixed assignment at the midpoint of the
        # exact admissible median interval.  This preserves every quota/family decision while
        # making the numerical batch calibration true by construction.
        target=.5*(median_lo+median_hi)
        if not (median_lo<=target<=median_hi):
            raise RuntimeError('component calibration interval is geometrically inconsistent')
        return [self._construct_collection_fallback(bases[i],i,assigns[i],target_span=target,planning=True)
                for i in range(N)]

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

    def _main_local_pathway_clearance_violation_count(self,main_pathways,local_pathways):
        """Exact final edge-gap audit between frozen main traces and later local fillers."""
        index=SpatialHash(max(64.0*self.U,4.0*self.pathway_interroute_keepout))
        main_prims=[]; max_main_t=0.0
        for g in main_pathways:
            for p in g.primitives:
                if p.svg.get('type')!='polyline': continue
                t=float(p.svg.get('stroke_width',0.0)); rec=dict(geom=p.geom,t=t)
                max_main_t=max(max_main_t,t); main_prims.append(rec); index.insert(rec,p.geom.bounds)
        bad=0
        for g in local_pathways:
            for p in g.primitives:
                if p.svg.get('type')!='polyline': continue
                lt=float(p.svg.get('stroke_width',0.0))
                max_gap=max(self.pathway_interroute_keepout,self.local_gap_line_edge_gap_factor*.5*(lt+max_main_t))
                query=expand_bounds(p.geom.bounds,max_gap+.5*max_main_t)
                for rec in index.query(query):
                    gap=max(self.pathway_interroute_keepout,self.local_gap_line_edge_gap_factor*.5*(lt+rec['t']))
                    if p.geom.intersects(rec['geom']) or p.geom.distance(rec['geom']) < gap-1e-7:
                        bad+=1
        return bad

    def _local_component_clearance_violation_count(self,components,local_pathways):
        """Local lines are born after components and must preserve the full component moat."""
        if not components or not local_pathways: return 0
        index=SpatialHash(max(64.0*self.U,4.0*self.component_pathway_clearance))
        for pg in local_pathways:
            index.insert(pg,pg.bounds)
        bad=0
        for comp in components:
            for pg in index.query(expand_bounds(comp.bounds,self.component_pathway_clearance)):
                if self._groups_violate_clearance(comp,pg,self.component_pathway_clearance):
                    bad+=1
        return bad

    def _unauthorized_component_pathway_overlap_count(self,components,pathways):
        """Exact final audit with a spatial broad phase.

        V37 can contain hundreds of residual components.  Auditing every component against every
        pathway group (and topology-unioning complex collections just to ask whether they touch)
        created a pathological all-to-all GEOS workload on some seeds.  Bounds hashing removes
        impossible pairs; GeometryCollection-based collision geometry remains set-equivalent for
        the exact intersection test.
        """
        count=0
        pindex=SpatialHash(max(64.0*self.U,4.0*self.component_pathway_clearance))
        for pg in pathways:
            pindex.insert(pg,pg.bounds)
        for comp in components:
            pt=comp.structural.get('component_pathway_attachment_point')
            allowed=(Point(pt).buffer(max(5.0*self.U,.22*max(bounds_w_h(comp.bounds))),quad_segs=10) if pt else None)
            cgeoms=self._group_collision_geoms(comp)
            for pg in pindex.query(comp.bounds):
                violated=False
                for cg in cgeoms:
                    for pp in pg.primitive_index.query(cg.bounds):
                        pgeom=pp.geom
                        if not self._bounds_within_gap(cg.bounds,pgeom.bounds,0.0): continue
                        if not cg.intersects(pgeom): continue
                        inter=cg.intersection(pgeom)
                        if inter.is_empty: continue
                        if allowed is not None and inter.difference(allowed).is_empty:
                            continue
                        violated=True; break
                    if violated: break
                if violated: count+=1
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
            if plan.structural.get('constructive_fallback'):
                g=self._construct_collection_fallback(
                    bases[k],k,a,target_span=plan.structural.get('constructive_target_span'),planning=False)
            else:
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

        # Natural repeated or near-similar component collections are valid outcomes.
        # Physical fit/clearance is enforced later; aesthetic similarity is not an acceptance gate.

        if self._validate_component_templates(full_cols,placed_chips,quotas):
            return None

        cap_seed=cur_seed if population_attempt==0 else retry_seed(cur_seed,0x20000+population_attempt)
        isolated_caps=self.generate_isolated_capacitors(cap_seed)
        return full_cols, isolated_caps

    def _place_component_population_on_frozen_routes(self, cur_seed, population, placed_chips, pathways,
                                                     layout_attempts=4):
        """Place one prepared population without ever changing the frozen route network."""
        collections,isolated_caps=population
        fill_base=component_fill_seed(cur_seed)
        legacy_target=SplitMix64(fill_base).uniform(*self.residual_gap_fill_range)
        target=float(getattr(self,'_active_component_fill_target',legacy_target))
        population_scale=float(getattr(self,'_active_component_population_scale',1.0))
        collections,isolated_caps=self._density_scaled_component_population(
            (collections,isolated_caps),cur_seed,population_scale)
        component_floor=float(getattr(self,'_active_component_fill_floor',self.residual_gap_fill_range[0]))
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
            fill_stats['component_chip_clearance_violation_count']=self._component_chip_clearance_violation_count(placed_components,placed_chips)
            key=(-fill_stats['component_unplaced_count'],
                 -fill_stats['component_pathway_unauthorized_overlap_count'],
                 -fill_stats['component_chip_clearance_violation_count'],
                 int(fill_stats['component_residual_gap_fill_actual']>=component_floor-1e-9),
                 fill_stats['component_residual_gap_fill_actual'])
            if best is None or key>best[0]:
                best=(key,placed_components,fill_stats)
            if (fill_stats['component_unplaced_count']==0 and
                    fill_stats.get('component_pathway_unauthorized_overlap_count',0)==0 and
                    fill_stats.get('component_chip_clearance_violation_count',0)==0):
                break
        return best[1],best[2]

    def generate_sample(self, sample_index=0, max_sample_restarts=256, collection_plan_attempts=256, calibration_rounds=256):
        # Seed totality: one logical seed owns one board. Whole-board regeneration is not
        # a production recovery mechanism; all ordinary retries below are phase/local.
        sseed=sample_seed(self.seed,sample_index)
        cur_seed=sseed; restart=0
        srng=SplitMix64(cur_seed)
        nc=self.chip_count(srng); N=self.collection_count(srng)
        assigns,quotas=self.assign_collection_families(srng,N)
        if assigns is None:
            raise RuntimeError("collection family construction unexpectedly returned no assignment")

        # PHASE A — MAIN CHIPS ONLY.
        chips=[]; chip_sigs=set(); chip_failed=False
        for j in range(nc):
            base=chip_seed(cur_seed,j); found=None
            for rr in range(128):
                try:
                    g=self.generate_chip(retry_seed(base,rr) if rr else base,j)
                except RuntimeError:
                    continue
                sig=self._chip_geometry_fingerprint(g)
                if sig not in chip_sigs:
                    found=g; chip_sigs.add(sig); break
            if found is None:
                # Literal-duplicate exhaustion is repaired by constructing a deterministic
                # geometry-distinct chip for this same logical chip opportunity.
                for salt in range(256):
                    g=self._construct_chip_fallback(retry_seed(base,0x50000+salt),j)
                    sig=self._chip_geometry_fingerprint(g)
                    if sig not in chip_sigs:
                        found=g; chip_sigs.add(sig); break
                if found is None:
                    chip_failed=True; break
            chips.append(found)
        if chip_failed:
            raise RuntimeError("chip uniqueness construction exhausted for requested seed")
        chip_rng=SplitMix64(placement_seed(cur_seed))
        placed_chips=self.place_objects(chips,[],[],chip_rng)
        if placed_chips is None:
            placed_chips=self._deterministic_place_main_chip_population(chips)
        if placed_chips is None:
            raise RuntimeError("main-chip population cannot fit the valid canvas under hard clearances")

        # PHASE B — MAIN-CHIP ROUTING ONLY.  Freeze it before any residual object exists.
        main_pathways,main_path_stats=self.generate_main_pathways(cur_seed, placed_chips)
        self._release_group_derived_caches(placed_chips + main_pathways)

        # V47 phase lifetime: only after the main planner is gone and the routed geometry is
        # frozen do we instantiate component templates/population.  Components still cannot
        # steer main routing, and tall boards no longer retain both large planner history and
        # a complete prepared component population at the same time.
        #
        # NIGHTLY Item-24: all ordinary component recovery is phase-local once MAIN freezes.
        # Historically three unlucky population-preparation attempts executed the outer
        # sample ``continue`` and discarded a valid/expensive MAIN network.  Use one bounded
        # deterministic post-MAIN attempt stream instead.  Attempt 0 is the exact historical
        # success path; later attempts exist only when preparation/placement/overlap/fill
        # recovery is actually required.
        residual_budget=self.residual_density_budget(cur_seed)
        self._active_residual_density_budget=residual_budget
        self._active_component_fill_target=float(residual_budget['component_target'])
        self._active_component_fill_floor=float(residual_budget['component_floor'])
        self._active_component_population_scale=float(residual_budget['component_population_scale'])
        component_floor=self._active_component_fill_floor
        placed_components=None; fill_stats=None; best_component_result=None

        if self._active_component_fill_target<=1e-12:
            # Literal component_density=0 endpoint: measure the post-MAIN residual field for the
            # shared denominator, but emit no residual components.
            fill_base=component_fill_seed(cur_seed)
            seed=retry_seed(fill_base,0x30000)
            placed_components,fill_stats=self.place_residual_components(
                [],[],placed_chips,main_pathways,SplitMix64(seed),target=0.0)
            fill_stats['component_layout_attempt_index']=0
            fill_stats['component_layout_attempt_count']=1
            fill_stats['component_pathway_unauthorized_overlap_count']=0
            fill_stats['component_chip_clearance_violation_count']=0

        for population_attempt in (() if placed_components is not None else range(6)):
            population=self._prepare_component_population_once(
                cur_seed,placed_chips,assigns,quotas,collection_plan_attempts,
                calibration_rounds,population_attempt)
            if population is None:
                continue
            cand_components,cand_stats=self._place_component_population_on_frozen_routes(
                cur_seed,population,placed_chips,main_pathways,layout_attempts=1)
            cand_key=(-cand_stats.get('component_unplaced_count',0),
                      -cand_stats.get('component_pathway_unauthorized_overlap_count',0),
                      -cand_stats.get('component_chip_clearance_violation_count',0),
                      int(cand_stats.get('component_residual_gap_fill_actual',0.0)>=component_floor-1e-9),
                      cand_stats.get('component_residual_gap_fill_actual',0.0))
            if best_component_result is None or cand_key>best_component_result[0]:
                best_component_result=(cand_key,cand_components,cand_stats,population_attempt)
            if (cand_stats.get('component_unplaced_count',0)==0 and
                    cand_stats.get('component_pathway_unauthorized_overlap_count',0)==0 and
                    cand_stats.get('component_chip_clearance_violation_count',0)==0 and
                    cand_stats.get('component_residual_gap_fill_actual',0.0)>=component_floor-1e-9):
                placed_components,fill_stats=cand_components,cand_stats
                break
        if placed_components is None:
            # One final deterministic compact population keeps the exact family/quotas while
            # increasing fit capacity in a difficult frozen residual field.  This is local to
            # the component phase; MAIN remains untouched.
            thresholds=self._collection_calibration_thresholds(placed_chips,assigns)
            compact_target=max(.040*self.S,thresholds['median_lo'])
            compact_cols=[self._construct_collection_fallback(collection_seed(cur_seed,k),k,a,
                                                               target_span=compact_target,planning=False)
                          for k,a in enumerate(assigns)]
            compact_pop=(compact_cols,self.generate_isolated_capacitors(retry_seed(cur_seed,0x6C6C6C)))
            cand_components,cand_stats=self._place_component_population_on_frozen_routes(
                cur_seed,compact_pop,placed_chips,main_pathways,layout_attempts=1)
            if (cand_stats.get('component_unplaced_count',0)==0 and
                    cand_stats.get('component_pathway_unauthorized_overlap_count',0)==0 and
                    cand_stats.get('component_chip_clearance_violation_count',0)==0 and
                    cand_stats.get('component_residual_gap_fill_actual',0.0)>=component_floor-1e-9):
                placed_components,fill_stats=cand_components,cand_stats
            else:
                raise RuntimeError("component constructive completion violated hard placement/service invariant")

        if (fill_stats['component_unplaced_count'] or
                fill_stats.get('component_pathway_unauthorized_overlap_count',0) or
                fill_stats.get('component_chip_clearance_violation_count',0)):
            raise RuntimeError("post-main component-only recovery exhausted or overlap remained")
        if fill_stats.get('component_residual_gap_fill_actual',0.0) < component_floor-1e-9:
            raise RuntimeError("component residual-density hard floor not realized: %.4f floor %.4f components %d" % (fill_stats.get('component_residual_gap_fill_actual',0.0), component_floor, fill_stats.get('component_residual_gap_total_component_count',0)))

        # The component residual raster/connected-region machinery is finished.  Preserve
        # only the scalar report and accepted geometry before allocating the local planner.
        self._release_component_residual_state()
        self._release_group_derived_caches(placed_chips + main_pathways + placed_components)

        # PHASE D — LOCAL LINES LAST.  Components and the main network are immutable
        # obstacles.  Route the active LOCAL share of the shared post-MAIN residual budget;
        # exact defaults preserve the historical 80-90% remainder convention.
        local_pathways,local_path_stats=self.generate_local_gap_pathways(
            cur_seed,placed_chips,placed_components,main_pathways,
            fill_stats.get('component_residual_gap_fill_actual',0.0),
            fill_stats.get('component_residual_gap_open_cell_count',0))
        pathways=main_pathways+local_pathways

        # Components were fitted before local lines, so final exact validation is repeated
        # against the complete pathway set.  Local routing is required to preserve their moat.
        # MAIN/component overlap was already exact-audited and required to be zero before LOCAL
        # existed. MAIN and components are immutable after that gate, so the final incremental
        # audit needs to inspect only the newly introduced LOCAL pathway geometry.
        final_component_overlap=(fill_stats.get('component_pathway_unauthorized_overlap_count',0)+
                                 self._unauthorized_component_pathway_overlap_count(placed_components,local_pathways))
        local_component_clearance=self._local_component_clearance_violation_count(placed_components,local_pathways)
        main_local_clearance=self._main_local_pathway_clearance_violation_count(main_pathways,local_pathways)
        if final_component_overlap or local_component_clearance or main_local_clearance:
            raise RuntimeError("post-component local routing violated frozen geometry clearance")
        fill_stats['component_pathway_unauthorized_overlap_count']=final_component_overlap
        fill_stats['local_component_clearance_violation_count']=local_component_clearance
        path_stats_clearance=(main_local_clearance)

        # Keep both pathway phase reports explicit; main-routing statistics are not allowed
        # to be overwritten by the later decorative local planner.
        path_stats=dict(main_path_stats)
        for k,v in local_path_stats.items():
            if k.startswith('pathway_local_gap_'):
                path_stats[k]=v
        path_stats['pathway_local_gap_fill_target_range']=tuple(self.local_gap_fill_range)
        path_stats['pathway_local_gap_fill_actual']=local_path_stats.get('pathway_local_gap_fill_actual',0.0)
        path_stats['pathway_local_gap_visible_trace_count']=local_path_stats.get('pathway_local_gap_visible_trace_count',0)
        path_stats['pathway_local_gap_trace_count']=local_path_stats.get('pathway_local_gap_trace_count',0)
        path_stats['pathway_local_gap_source_count']=local_path_stats.get('pathway_local_gap_source_count',0)
        path_stats['pathway_local_gap_region_count']=local_path_stats.get('pathway_local_gap_region_count',0)
        path_stats['pathway_local_gap_phase']='after_components'
        path_stats['pathway_local_gap_denominator']='canonical_post_main_residual_service_field'
        path_stats['pathway_main_local_clearance_violation_count']=path_stats_clearance
        path_stats['pathway_local_gap_illegal_turn_count']=local_path_stats.get('pathway_illegal_turn_count',0)
        path_stats['pathway_local_gap_non_octilinear_segment_count']=local_path_stats.get('pathway_non_octilinear_segment_count',0)
        path_stats['pathway_local_gap_illegal_connection_junction_turn_count']=local_path_stats.get('pathway_illegal_connection_junction_turn_count',0)
        path_stats['pathway_local_gap_curved_primitive_count']=local_path_stats.get('pathway_curved_primitive_count',0)
        path_stats['pathway_local_gap_unmarked_overlap_count']=local_path_stats.get('pathway_unmarked_overlap_count',0)
        path_stats['pathway_local_gap_unmarked_clearance_violation_count']=local_path_stats.get('pathway_unmarked_clearance_violation_count',0)
        path_stats['pathway_local_gap_static_intersection_count']=local_path_stats.get('pathway_static_intersection_count',0)
        path_stats['pathway_illegal_turn_count']=main_path_stats.get('pathway_illegal_turn_count',0)+local_path_stats.get('pathway_illegal_turn_count',0)
        path_stats['pathway_non_octilinear_segment_count']=main_path_stats.get('pathway_non_octilinear_segment_count',0)+local_path_stats.get('pathway_non_octilinear_segment_count',0)
        path_stats['pathway_illegal_connection_junction_turn_count']=main_path_stats.get('pathway_illegal_connection_junction_turn_count',0)+local_path_stats.get('pathway_illegal_connection_junction_turn_count',0)
        path_stats['pathway_unmarked_clearance_violation_count']=main_path_stats.get('pathway_unmarked_clearance_violation_count',0)+local_path_stats.get('pathway_unmarked_clearance_violation_count',0)
        path_stats['pathway_curved_primitive_count']=main_path_stats.get('pathway_curved_primitive_count',0)+local_path_stats.get('pathway_curved_primitive_count',0)

        static_final=placed_chips + placed_components
        errors=self.validate_sample(static_final,nc,N,quotas)
        if errors:
            raise RuntimeError("post-route validation failed: "+','.join(errors))

        report=self.build_report(static_final,cur_seed,nc,N,quotas,restart)
        report.update(path_stats); report.update(fill_stats)
        _component_actual=max(0.0,float(fill_stats.get('component_residual_gap_fill_actual',0.0)))
        _local_actual_abs=max(0.0,float(local_path_stats.get('pathway_local_gap_fill_actual_absolute_service',0.0)))
        _residual_actual_total=min(1.0,_component_actual+_local_actual_abs)
        report['residual_density_actual_total']=_residual_actual_total
        report['residual_density_actual_component_share']=(_component_actual/_residual_actual_total if _residual_actual_total>1e-12 else 0.0)
        report['renderer_version']='V48'
        report['generation_order']='main_chips -> primary_pathways -> residual_components_density_budget -> local_gap_pathways_density_budget'
        report['component_templates_prepared_before_routing']=False
        report['route_restarted_for_component_failure']=False
        report['scale']=self.scale
        report['aspect_ratio']=[self.aspect_ratio[0],self.aspect_ratio[1]]
        report['logical_viewbox']=[self.W,self.H]
        report['canonical_short_side']=self.canonical_short_side
        report['design_scale_basis']=self.S
        report['design_unit_divisor']=1600
        report['design_unit_viewbox_fraction']=self.U/max(min(self.W,self.H),1e-9)
        T,full,frac=self.population_parts()
        report['population_area_scale']=T
        report['canvas_territory_scale']=self.canvas_territory_scale()
        report['design_distance_scale']=self.design_distance_scale()
        report['design_detail_area_scale']=self.design_detail_area_scale()
        report['service_grid_scale_basis']='canonical_design_units_over_logical_viewbox'
        report['chip_count_probability_3']=frac  # compatibility key: historical fractional-territory opportunity probability
        report['chip_count_fractional_territory_probability']=frac
        report['main_chip_density_multiplier']=self.main_chip_density_multiplier
        report['main_chip_density_multiplier_range']=(0.2,2.0)
        report['main_run_length_multiplier']=self.main_run_length_multiplier
        report['main_run_length_multiplier_range']=(0.2,3.0)
        report['main_free_run_residency_factor']=2.0*self.main_run_length_multiplier
        report['main_run_length_basis']='existing_whole_route_max_gestures_distribution_only'
        report['local_density']=self.local_density
        report['local_density_range']=(0.0,1.0)
        report['component_density']=self.component_density
        report['component_density_range']=(0.0,1.0)
        report['component_density_default']=DEFAULT_COMPONENT_DENSITY
        report['residual_density_legacy_exact_default']=bool(residual_budget.get('legacy_exact'))
        report['residual_density_legacy_total_target']=residual_budget.get('legacy_total_target')
        report['residual_density_total_target']=residual_budget.get('total_target')
        report['residual_density_component_target']=residual_budget.get('component_target')
        report['residual_density_local_absolute_budget']=residual_budget.get('local_absolute_budget')
        report['main_chip_opportunity_activation_probability']=self.main_chip_opportunity_activation_probability()
        report['chip_count_expected_unfloored']=2.0*T*self.main_chip_opportunity_activation_probability()
        report['chip_count_minimum']=1
        report['chip_count_expected']=max(1.0,report['chip_count_expected_unfloored'])
        report['chip_count_historical_expected_at_multiplier_2']=2.0*T
        report['chip_count_population_basis']='thinned_historical_two_opportunities_per_logical_territory'
        report['pathway_local_gap_service_definition']='visible_stroke_plus_legitimate_exclusion_perimeter'
        report['component_residual_gap_fill_definition']='component_density_share_of_local_density_post_main_residual_budget; exact defaults preserve legacy_50_60'
        report['pathway_local_gap_fill_definition']='remaining_local_density_budget_by_visible_stroke_plus_legitimate_perimeter; exact defaults preserve legacy_80_90_of_remainder'
        report["logical_sample_index"] = sample_index
        return static_final + pathways,report

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
        if len(chips)>=2:
            chip_geoms=[g.geom for g in chips]
            _pairs,_dists=STRtree(chip_geoms).query_nearest(
                chip_geoms,return_distance=True,exclusive=True,all_matches=False)
            chip_pair_min_clearance=min((float(d) for d in _dists),default=None)
        else:
            chip_pair_min_clearance=None
        long_axis='x' if self.W>=self.H else 'y'
        long_len=self.W if long_axis=='x' else self.H
        def axis_value(g):
            c=bounds_center(g.bounds); return c[0] if long_axis=='x' else c[1]
        def quarters(groups):
            q=[0,0,0,0]
            for g in groups:
                v=axis_value(g); q[min(3,max(0,int(4*v/max(long_len,1e-9))))]+=1
            return q
        def span_fraction(groups):
            vals=[axis_value(g) for g in groups]
            return ((max(vals)-min(vals))/max(long_len,1e-9)) if len(vals)>=2 else 0.0
        components=cols+isolated
        return dict(seed=seed,base_seed=self.seed,restart_index=restart,chip_count=nc,collection_count=N,quotas=quotas,
                    population_area_scale=self.population_area_scale(),population_long_axis=long_axis,
                    main_chip_long_axis_quarter_counts=quarters(chips),main_chip_long_axis_span_fraction=span_fraction(chips),
                    component_long_axis_quarter_counts=quarters(components),component_long_axis_span_fraction=span_fraction(components),
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
                    collection_long=[max(bounds_w_h(g.bounds)) for g in cols])

    # ------------------------------ SVG ----------------------------------
    def _svg_attr_value(self,value):
        if value is None:
            return None
        if isinstance(value,bool):
            return 'true' if value else 'false'
        if isinstance(value,float):
            return f'{value:.6f}'.rstrip('0').rstrip('.') if math.isfinite(value) else str(value)
        if isinstance(value,(list,tuple,dict)):
            return json.dumps(value,separators=(",",":"))
        return str(value)

    def _svg_attr_string(self,attrs):
        parts=[]
        for key,value in attrs.items():
            value=self._svg_attr_value(value)
            if value is None:
                continue
            parts.append(f'{key}="{xml_escape(value,quote=True)}"')
        return ' '.join(parts)

    def _semantic_group_descriptor(self,g):
        s=g.structural
        pk=s.get('placement_kind')
        kind='entity'
        classes=['pcb-entity']
        attrs={'id':g.name,'data-entity-id':g.name,'data-placement-kind':pk}
        meta={'id':g.name,'placement_kind':pk,'bounds':[round(x,4) for x in g.bounds],'primitive_count':len(g.primitives)}
        if pk=='chip':
            kind='main-chip'; classes.append('pcb-main-chip')
            chip_id=int(g.name.split('-')[-1]) if g.name.startswith('chip-') else None
            attrs.update({'data-kind':kind,'data-chip-id':chip_id})
            meta.update({'kind':kind,'chip_id':chip_id,'orientation':s.get('orientation'),'motifs':list(s.get('motifs',()))})
        elif pk=='pathway':
            if s.get('local_gap_pathway'):
                kind='local-pathway'; classes.extend(['pcb-pathway-group','pcb-local-pathway-group'])
                attrs.update({'data-kind':kind,'data-local-gap-special':bool(s.get('local_gap_special'))})
                meta.update({'kind':kind,'launch_line_count':s.get('launch_line_count'),
                             'bundle_spacing':s.get('bundle_spacing'),
                             'local_gap_special':bool(s.get('local_gap_special'))})
            else:
                kind='main-pathway'; classes.extend(['pcb-pathway-group','pcb-main-pathway-group'])
                attrs.update({'data-kind':kind,'data-source-chip-id':s.get('bundle_source_chip'),'data-launch-side':s.get('launch_side')})
                meta.update({'kind':kind,'source_chip_id':s.get('bundle_source_chip'),'launch_side':s.get('launch_side'),
                             'launch_line_count':s.get('launch_line_count'),'bundle_spacing':s.get('bundle_spacing'),
                             'launch_coverage_ratio':s.get('launch_coverage_ratio')})
        elif pk in ('collection','isolated'):
            kind='component-group'; classes.append('pcb-component-group')
            families=s.get('families')
            if families is None:
                fam=s.get('family')
                families=[fam] if fam else []
            families=list(families)
            primary_family=(families[0] if families else (s.get('family') or 'mixed'))
            attrs.update({'data-kind':kind,'data-component-family':primary_family,
                          'data-component-families':families if families else None,
                          'data-cluster-id':s.get('residual_fill_cluster_id')})
            if pk=='collection':
                classes.append('pcb-component-collection')
            else:
                classes.append('pcb-component-isolated')
            if primary_family:
                classes.append(f'pcb-component-family-{primary_family}')
            meta.update({'kind':kind,'component_family':primary_family,'component_families':families,
                         'cluster_id':s.get('residual_fill_cluster_id'),'cluster_target':s.get('residual_fill_cluster_target'),
                         'is_completion_cluster':bool(s.get('residual_fill_cluster_completion')),
                         'is_recovery_spill':bool(s.get('residual_fill_cluster_recovery_spill')),
                         'is_residual_filler':bool(s.get('residual_filler'))})
        else:
            attrs.update({'data-kind':kind})
            meta.update({'kind':kind})
        meta['class_list']=classes
        return kind,classes,attrs,meta

    def _pathway_marker_roles(self,g):
        starts=[]; ends=[]; eps=1e-6
        for p in g.primitives:
            typ=p.svg.get('type')
            if typ=='polyline':
                pts=p.svg.get('points',[])
                if pts:
                    starts.append(tuple(pts[0])); ends.append(tuple(pts[-1]))
            elif typ=='line':
                starts.append((p.svg['x1'],p.svg['y1'])); ends.append((p.svg['x2'],p.svg['y2']))
            elif typ=='quadratic':
                starts.append(tuple(p.svg['p0'])); ends.append(tuple(p.svg['p1']))
        def _matches(c,target):
            return abs(c[0]-target[0])<=eps and abs(c[1]-target[1])<=eps
        roles={}
        for idx,p in enumerate(g.primitives):
            if p.svg.get('type')!='circle':
                continue
            center=(p.svg['cx'],p.svg['cy'])
            at_start=any(_matches(center,pt) for pt in starts)
            at_end=any(_matches(center,pt) for pt in ends)
            if at_start and not at_end:
                role='source-marker'
            elif at_end and not at_start:
                role='terminal-marker'
            elif at_start and at_end:
                role='endpoint-marker'
            else:
                role='junction-marker'
            roles[idx]=role
        return roles

    def _primitive_semantic_descriptors(self,g,group_kind):
        role_counts={}
        marker_roles=self._pathway_marker_roles(g) if group_kind in ('main-pathway','local-pathway') else {}
        descriptors=[]
        for idx,p in enumerate(g.primitives):
            svg=p.svg; typ=svg['type']
            if group_kind=='main-pathway' and typ in ('polyline','line','quadratic'):
                kind='main-trace'; classes=['pcb-primitive','pcb-main-trace']
            elif group_kind=='local-pathway' and typ in ('polyline','line','quadratic'):
                kind='local-trace'; classes=['pcb-primitive','pcb-local-trace']
            elif group_kind in ('main-pathway','local-pathway') and typ=='circle':
                role=marker_roles.get(idx,'pathway-marker')
                base='main-trace-marker' if group_kind=='main-pathway' else 'local-trace-marker'
                kind=base; classes=['pcb-primitive',f'pcb-{role}',f'pcb-{base}']
            elif group_kind=='main-chip':
                kind='main-chip-geometry'; classes=['pcb-primitive','pcb-main-chip-geometry']
            elif group_kind=='component-group':
                kind='component-geometry'; classes=['pcb-primitive','pcb-component-geometry']
            else:
                kind='entity-geometry'; classes=['pcb-primitive','pcb-entity-geometry']
            role_counts[kind]=role_counts.get(kind,0)+1
            prim_id=f'{g.name}__{kind}-{role_counts[kind]-1}'
            attrs={'id':prim_id,'class':' '.join(classes),'data-kind':kind,'data-parent-entity-id':g.name,
                   'data-primitive-index':idx,'data-svg-type':typ}
            meta={'id':prim_id,'parent_entity_id':g.name,'kind':kind,'svg_type':typ,
                  'bounds':[round(x,4) for x in p.geom.bounds], 'primitive_index':idx, 'class_list':classes}
            if kind.endswith('marker'):
                role=marker_roles.get(idx,'pathway-marker')
                attrs['data-marker-role']=role
                meta['marker_role']=role
            if typ=='polyline':
                pts=svg.get('points',[])
                if pts:
                    start,end=pts[0],pts[-1]
                    attrs.update({'data-start-x':start[0],'data-start-y':start[1],'data-end-x':end[0],'data-end-y':end[1],
                                  'data-point-count':len(pts),'data-stroke-width':svg.get('stroke_width')})
                    meta.update({'start':[round(start[0],4),round(start[1],4)],'end':[round(end[0],4),round(end[1],4)],
                                 'point_count':len(pts),'stroke_width':svg.get('stroke_width')})
            elif typ=='line':
                start,end=(svg['x1'],svg['y1']),(svg['x2'],svg['y2'])
                attrs.update({'data-start-x':start[0],'data-start-y':start[1],'data-end-x':end[0],'data-end-y':end[1],
                              'data-stroke-width':svg.get('stroke_width')})
                meta.update({'start':[round(start[0],4),round(start[1],4)],'end':[round(end[0],4),round(end[1],4)],
                             'stroke_width':svg.get('stroke_width')})
            elif typ=='quadratic':
                start,end=tuple(svg['p0']),tuple(svg['p1'])
                attrs.update({'data-start-x':start[0],'data-start-y':start[1],'data-end-x':end[0],'data-end-y':end[1],
                              'data-stroke-width':svg.get('stroke_width')})
                meta.update({'start':[round(start[0],4),round(start[1],4)],'end':[round(end[0],4),round(end[1],4)],
                             'stroke_width':svg.get('stroke_width')})
            elif typ=='circle':
                attrs.update({'data-center-x':svg['cx'],'data-center-y':svg['cy'],'data-radius':svg['r']})
                meta.update({'center':[round(svg['cx'],4),round(svg['cy'],4)],'radius':svg['r']})
            elif typ=='rect':
                attrs.update({'data-center-x':svg['cx'],'data-center-y':svg['cy'],'data-width':svg['width'],'data-height':svg['height']})
                meta.update({'center':[round(svg['cx'],4),round(svg['cy'],4)],'width':svg['width'],'height':svg['height']})
            descriptors.append((attrs,meta))
        return descriptors

    def _semantic_svg_payload(self,placed,report):
        entities=[]; primitives=[]; counts={}
        for g in placed:
            gkind,gclasses,gattrs,gmeta=self._semantic_group_descriptor(g)
            prim_desc=self._primitive_semantic_descriptors(g,gkind)
            gmeta['primitive_ids']=[attrs['id'] for attrs,_ in prim_desc]
            entities.append(gmeta)
            primitives.extend(meta for _,meta in prim_desc)
            counts[gkind]=counts.get(gkind,0)+1
        return {
            'schema':'pcb-art-semantic-svg',
            'schema_version':'1.0',
            'renderer_version':report.get('renderer_version'),
            'entity_count':len(entities),
            'primitive_count':len(primitives),
            'entity_kind_counts':counts,
            'entities':entities,
            'primitives':primitives,
        }

    def svg_for(self,placed,report):
        semantic=self._semantic_svg_payload(placed,report)
        metadata_payload=dict(report)
        metadata_payload['semantic_svg']=semantic
        root_attrs=self._svg_attr_string({
            'xmlns':'http://www.w3.org/2000/svg',
            'viewBox':f'0 0 {self.W:g} {self.H:g}',
            'data-schema':'pcb-art-semantic-svg',
            'data-schema-version':'1.0',
            'data-renderer-version':report.get('renderer_version','V48'),
            'data-semantic-entity-count':semantic['entity_count'],
            'data-semantic-primitive-count':semantic['primitive_count'],
        })
        lines=[f'<svg {root_attrs}>',
               f'<metadata>{json.dumps(metadata_payload,separators=(",",":"))}</metadata>',
               f'<rect x="0" y="0" width="{self.W:g}" height="{self.H:g}" fill="{self.BG}" class="pcb-background" data-kind="background"/>']
        pathways=[g for g in placed if g.structural.get("placement_kind")=="pathway"]
        others=[g for g in placed if g.structural.get("placement_kind")!="pathway"]
        for seq in (pathways, others):
            for g in seq:
                gkind,gclasses,gattrs,_=self._semantic_group_descriptor(g)
                gattrs['class']=' '.join(gclasses)
                lines.append(f'<g {self._svg_attr_string(gattrs)}>')
                for prim_attrs,pmeta in self._primitive_semantic_descriptors(g,gkind):
                    lines.append(self.svg_primitive(g.primitives[pmeta['primitive_index']].svg,prim_attrs))
                lines.append('</g>')
        lines.append('</svg>')
        return '\n'.join(lines)

    def svg_primitive(self,s,extra_attrs=None):
        typ=s["type"]
        extra_attrs=dict(extra_attrs or {})
        if typ=="rect":
            x=s["cx"]-s["width"]/2; y=s["cy"]-s["height"]/2
            attrs=dict(extra_attrs)
            attrs.update({'x':f'{x:.4f}','y':f'{y:.4f}','width':f'{s["width"]:.4f}','height':f'{s["height"]:.4f}','rx':f'{s.get("rx",0):.4f}','fill':s.get("fill","none")})
            if s.get("stroke")!="none": attrs.update({'stroke':s["stroke"],'stroke-width':f'{s["stroke_width"]:.4f}'})
            return '<rect '+self._svg_attr_string(attrs)+'/>'
        if typ=="circle":
            attrs=dict(extra_attrs)
            attrs.update({'cx':f'{s["cx"]:.4f}','cy':f'{s["cy"]:.4f}','r':f'{s["r"]:.4f}','fill':s.get("fill","none")})
            if s.get("stroke")!="none": attrs.update({'stroke':s["stroke"],'stroke-width':f'{s["stroke_width"]:.4f}'})
            return '<circle '+self._svg_attr_string(attrs)+'/>'
        if typ=="line":
            attrs=dict(extra_attrs)
            attrs.update({'x1':f'{s["x1"]:.4f}','y1':f'{s["y1"]:.4f}','x2':f'{s["x2"]:.4f}','y2':f'{s["y2"]:.4f}','stroke':s["stroke"],'stroke-width':f'{s["stroke_width"]:.4f}','stroke-linecap':s.get("linecap","butt")})
            return '<line '+self._svg_attr_string(attrs)+'/>'
        if typ=="polyline":
            pts=" ".join(f"{x:.4f},{y:.4f}" for x,y in s["points"])
            attrs=dict(extra_attrs)
            attrs.update({'points':pts,'fill':'none','stroke':s["stroke"],'stroke-width':f'{s["stroke_width"]:.4f}','stroke-linecap':s.get("linecap","butt"),'stroke-linejoin':s.get("linejoin","miter")})
            return '<polyline '+self._svg_attr_string(attrs)+'/>'
        if typ=="quadratic":
            p0,q,p1=s["p0"],s["q"],s["p1"]
            attrs=dict(extra_attrs)
            attrs.update({'d':f'M {p0[0]:.4f} {p0[1]:.4f} Q {q[0]:.4f} {q[1]:.4f} {p1[0]:.4f} {p1[1]:.4f}','fill':'none','stroke':s["stroke"],'stroke-width':f'{s["stroke_width"]:.4f}','stroke-linecap':'round'})
            return '<path '+self._svg_attr_string(attrs)+'/>'
        raise ValueError(typ)

    def render_batch(self,count,out_dir:Path,max_sample_restarts=1,skip_deadlocks=False,max_logical_samples=None,
                     collection_plan_attempts=128,calibration_rounds=96):
        """Render exactly the requested logical seeds; never acceptance-skip to another seed.

        ``max_sample_restarts``, ``skip_deadlocks`` and ``max_logical_samples`` are retained only
        as call-site compatibility parameters while downstream tools migrate.  They no longer
        select alternate logical samples or enlarge whole-sample retry budgets.  A construction
        invariant failure propagates for that exact requested seed and is a renderer bug.
        """
        out_dir.mkdir(parents=True,exist_ok=True)
        reports=[]
        for logical_index in range(count):
            placed,report=self.generate_sample(logical_index,max_sample_restarts=1,
                                               collection_plan_attempts=collection_plan_attempts,
                                               calibration_rounds=calibration_rounds)
            svg=self.svg_for(placed,report); out_index=len(reports)
            path=out_dir/f"pcb_v48_{out_index:02d}_seed_{report['seed']}.svg"; path.write_text(svg)
            (out_dir/f"pcb_v48_{out_index:02d}_report.json").write_text(json.dumps(report,indent=2))
            reports.append(report)
        return reports,[]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--aspect-ratio',default='1:1',help='output shape as W:H; no pixel dimensions')
    ap.add_argument('--scale',type=float,default=1.0,help='design zoom; lower values expose more logical PCB territory')
    ap.add_argument('--main-chip-density-multiplier',type=float,default=1.0,metavar='0.2..2.0')
    ap.add_argument('--main-run-length-multiplier',type=float,default=1.0,metavar='0.2..3.0')
    ap.add_argument('--local-density',type=float,default=DEFAULT_LOCAL_DENSITY,metavar='0..1')
    ap.add_argument('--component-density',type=float,default=DEFAULT_COMPONENT_DENSITY,metavar='0..1')
    ap.add_argument('--seed',type=lambda x:int(x,0),default=None); ap.add_argument('--count',type=int,default=1)
    ap.add_argument('--out-dir',type=Path,default=Path('v48_output'))
    ap.add_argument('--collection-plan-attempts',type=int,default=128)
    ap.add_argument('--calibration-rounds',type=int,default=96)
    ap.add_argument('--pathway-debug-stage',choices=('corridors',),default=None)
    args=ap.parse_args()
    r=V48Renderer(args.aspect_ratio,args.scale,args.seed,
                  main_chip_density_multiplier=args.main_chip_density_multiplier,
                  main_run_length_multiplier=args.main_run_length_multiplier,
                  local_density=args.local_density,
                  component_density=args.component_density)
    r.pathway_debug_stage=args.pathway_debug_stage
    reports,skipped=r.render_batch(args.count,args.out_dir,
                                   collection_plan_attempts=args.collection_plan_attempts,calibration_rounds=args.calibration_rounds)
    print(json.dumps(dict(base_seed=r.seed,reports=reports,skipped_logical_indices=skipped),indent=2))

if __name__=='__main__': main()
