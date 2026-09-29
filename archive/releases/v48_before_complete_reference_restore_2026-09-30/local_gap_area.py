"""Incremental binary closing on the canonical 4x4 residual-area grid.

The caller supplies *source* masks for individual LOCAL families.  Source
support counts make overlapping families safe to retire independently.  A
preview does not mutate the field; its token can be committed once, provided
the field has not changed in the meantime.  Only source-transition stencil
neighbors are visited by an update.  ``output_mask`` deliberately performs a
full scan and should be used only at a phase boundary.
"""

from dataclasses import dataclass
import math
from numbers import Integral

import numpy as np


Mask = dict[tuple[int, int], int]


@dataclass(frozen=True)
class GapChange:
    """A pending field update and its allowed-domain output difference."""

    output_added: Mask
    output_removed: Mask
    output_count_delta: int
    _owner: object
    _version: int
    _base_deltas: tuple[np.ndarray, np.ndarray]
    _dilation_deltas: tuple[np.ndarray, np.ndarray]
    _erosion_deltas: tuple[np.ndarray, np.ndarray]
    _support_deltas: tuple[np.ndarray, np.ndarray]


class LocalGapAreaField:
    """Count LOCAL source and nearby-line gaps by physical binary closing.

    ``nx, ny`` are coarse cell dimensions and ``cw, ch`` their physical sizes.
    ``module`` is the physical routing module.  Closing uses a symmetric
    elliptical fine-grid stencil whose centers are at most ``radius`` apart
    (half a module by default).  ``trace_masks`` contains each visible trace
    as a separate source mask.  Its dilated footprint contributes at most one
    vote per trace to distinct-trace support.  Output includes base pixels and
    closed gaps supported by at least two traces.  ``allowed_mask`` clips
    *reported* output, not the morphological
    computation; sources may be outside it when a physical gap crosses its
    edge.  All masks use ``(coarse_x, coarse_y): sixteen_bit_mask``.
    """

    def __init__(self, nx: int, ny: int, cw: float, ch: float,
                 module: float, source_mask: Mask | None = None,
                 allowed_mask: Mask | None = None,
                 trace_masks=None, radius: float | None = None):
        if nx <= 0 or ny <= 0 or cw <= 0 or ch <= 0 or module <= 0:
            raise ValueError("grid dimensions, cell sizes and module must be positive")
        if radius is not None and radius <= 0:
            raise ValueError("radius must be positive")
        self.nx = nx
        self.ny = ny
        self.width = nx * 4
        self.height = ny * 4
        self.radius = module / 2.0 if radius is None else radius
        sx, sy = cw / 4.0, ch / 4.0
        rx = math.floor(self.radius / sx + 1e-12)
        ry = math.floor(self.radius / sy + 1e-12)
        self.stencil = tuple(
            (dx, dy)
            for dy in range(-ry, ry + 1)
            for dx in range(-rx, rx + 1)
            if (dx * sx) ** 2 + (dy * sy) ** 2 <= self.radius ** 2 + 1e-12
        )
        # Two stencil radii leave all values needed to erode the original
        # domain inside the padded array, even for edge-touching sources.
        self.pad_x = 2 * rx + 1
        self.pad_y = 2 * ry + 1
        self.padded_width = self.width + 2 * self.pad_x
        self.padded_height = self.height + 2 * self.pad_y
        self._stencil_offsets = np.asarray(
            [dy * self.padded_width + dx for dx, dy in self.stencil],
            dtype=np.int64)
        shape = (self.padded_height, self.padded_width)
        self.base_support = np.zeros(shape, dtype=np.int32)
        self.dilation_support = np.zeros(shape, dtype=np.int32)
        self.erosion_support = np.zeros(shape, dtype=np.int32)
        self.trace_support = np.zeros(shape, dtype=np.int32)
        self.allowed = np.ones((self.height, self.width), dtype=bool)
        if allowed_mask is not None:
            self.allowed.fill(False)
            for x, y in self._pixels(allowed_mask):
                self.allowed[y, x] = True
        for x, y in self._pixels(source_mask or {}):
            self.base_support[self.pad_y + y, self.pad_x + x] += 1
        self._sum_shifted(self.base_support > 0, self.dilation_support)
        self._sum_shifted(self.dilation_support > 0, self.erosion_support)
        for trace in trace_masks or ():
            for x, y in self._pixels(self.expand_mask(trace)):
                self.trace_support[self.pad_y + y, self.pad_x + x] += 1
        self.output_count = int(np.count_nonzero(self._domain_output()))
        self._version = 0

    def _pixels(self, mask):
        if not hasattr(mask, "items"):
            for x, y in mask:
                if not (isinstance(x, Integral) and isinstance(y, Integral) and
                        0 <= x < self.width and 0 <= y < self.height):
                    raise ValueError(f"source pixel outside grid: {(x, y)}")
                yield int(x), int(y)
            return
        for (cx, cy), bits in mask.items():
            if not (0 <= cx < self.nx and 0 <= cy < self.ny):
                raise ValueError(f"source cell outside grid: {(cx, cy)}")
            if not isinstance(bits, Integral) or bits < 0 or bits > 0xffff:
                raise ValueError("source mask bits must be a 16-bit integer")
            bits = int(bits)
            while bits:
                bit = bits & -bits
                k = bit.bit_length() - 1
                yield cx * 4 + k % 4, cy * 4 + k // 4
                bits -= bit

    def _sum_shifted(self, source: np.ndarray, destination: np.ndarray):
        h, w = source.shape
        for dx, dy in self.stencil:
            x0, x1 = max(0, -dx), min(w, w - dx)
            y0, y1 = max(0, -dy), min(h, h - dy)
            destination[y0 + dy:y1 + dy, x0 + dx:x1 + dx] += source[y0:y1, x0:x1]

    def _domain_output(self):
        ys = slice(self.pad_y, self.pad_y + self.height)
        xs = slice(self.pad_x, self.pad_x + self.width)
        return ((self.base_support[ys, xs] > 0) |
                ((self.erosion_support[ys, xs] == len(self.stencil)) &
                 (self.trace_support[ys, xs] >= 2))) & self.allowed

    def expand_mask(self, mask: Mask) -> Mask:
        """Dilate one trace into a sparse, once-per-pixel support footprint."""
        pixels = set()
        for x, y in self._pixels(mask):
            for dx, dy in self.stencil:
                xx, yy = x + dx, y + dy
                if 0 <= xx < self.width and 0 <= yy < self.height:
                    pixels.add((xx, yy))
        result: Mask = {}
        for x, y in sorted(pixels):
            cell = (x // 4, y // 4)
            result[cell] = result.get(cell, 0) | 1 << ((y % 4) * 4 + x % 4)
        return result

    def output_mask(self) -> Mask:
        """Materialize the current allowed output (linear board scan)."""
        result: Mask = {}
        ys, xs = np.nonzero(self._domain_output())
        for y, x in zip(ys.tolist(), xs.tolist()):
            cell = (x // 4, y // 4)
            result[cell] = result.get(cell, 0) | 1 << ((y % 4) * 4 + x % 4)
        return result

    @staticmethod
    def _packed(deltas: dict[int, int]):
        if not deltas:
            return np.empty(0, np.int64), np.empty(0, np.int32)
        keys = sorted(deltas)
        return np.asarray(keys, np.int64), np.asarray([deltas[k] for k in keys], np.int32)

    def _stencil_deltas(self, centers: np.ndarray, signs: np.ndarray):
        """Accumulate one local dilation/erosion frontier without a board scan."""
        if not len(centers):
            return self._packed({})
        neighbors = (centers[:, None] + self._stencil_offsets).ravel()
        low = int(neighbors.min())
        span = int(neighbors.max()) - low + 1
        # For a compact transaction, local bincount is linear and avoids a
        # sort.  The cap prevents a few scattered pixels from allocating or
        # scanning a nearly whole-board temporary.
        local_span = span <= min(len(neighbors) * 2,
                                 self.base_support.size // 4)
        if local_span:
            if np.all(signs == signs[0]):
                counts = np.bincount(neighbors - low, minlength=span)
                indices = np.flatnonzero(counts) + low
                deltas = counts[indices - low].astype(np.int32) * signs[0]
            else:
                weights = np.repeat(signs, len(self.stencil))
                counts = np.bincount(neighbors - low, weights=weights,
                                     minlength=span).astype(np.int32)
                indices = np.flatnonzero(counts) + low
                deltas = counts[indices - low]
        elif np.all(signs == signs[0]):
            indices, counts = np.unique(neighbors, return_counts=True)
            deltas = counts.astype(np.int32) * signs[0]
        else:
            indices, inverse = np.unique(neighbors, return_inverse=True)
            weights = np.repeat(signs, len(self.stencil))
            deltas = np.bincount(inverse, weights=weights,
                                 minlength=len(indices)).astype(np.int32)
            keep = deltas != 0
            indices, deltas = indices[keep], deltas[keep]
        return indices, deltas

    @staticmethod
    def _on_candidates(candidates: np.ndarray, packed):
        values = np.zeros(len(candidates), np.int32)
        indices, deltas = packed
        if len(indices):
            values[np.searchsorted(candidates, indices)] = deltas
        return values

    def change(self, source_added_mask: Mask | None = None,
               source_removed_mask: Mask | None = None,
               *, support_added=(), support_removed=(),
               commit: bool = False) -> GapChange:
        """Preview source-family additions/removals, optionally applying them.

        An addition increments per-pixel support even when that pixel is
        already occupied.  A removal decrements it and must not underflow.
        Equal addition/removal of the same pixel cancels in this transaction.
        """
        w = self.padded_width
        base = self.base_support.ravel()
        dilation = self.dilation_support.ravel()
        erosion = self.erosion_support.ravel()
        base_delta: dict[int, int] = {}
        for sign, mask in ((1, source_added_mask), (-1, source_removed_mask)):
            for x, y in self._pixels(mask or {}):
                i = (self.pad_y + y) * w + self.pad_x + x
                base_delta[i] = base_delta.get(i, 0) + sign
        base_delta = {i: d for i, d in base_delta.items() if d}
        support_delta: dict[int, int] = {}
        for sign, masks in ((1, support_added), (-1, support_removed)):
            for mask in masks:
                for x, y in self._pixels(mask):
                    i = (self.pad_y + y) * w + self.pad_x + x
                    support_delta[i] = support_delta.get(i, 0) + sign
        support_delta = {i: d for i, d in support_delta.items() if d}
        trace_support = self.trace_support.ravel()
        base_packed = self._packed(base_delta)
        support_packed = self._packed(support_delta)
        bi, bd = base_packed
        si, sd = support_packed
        if np.any(base[bi] + bd < 0):
            raise ValueError("source removal exceeds source support")
        if np.any(trace_support[si] + sd < 0):
            raise ValueError("trace support removal exceeds support count")
        base_toggles = ((base[bi] + bd > 0).astype(np.int32) -
                        (base[bi] > 0).astype(np.int32))
        keep = base_toggles != 0
        dilation_packed = self._stencil_deltas(bi[keep], base_toggles[keep])
        di, dd = dilation_packed
        after_dilation = dilation[di] + dd
        if np.any(after_dilation < 0):
            raise AssertionError("dilation support underflow")
        dilation_toggles = ((after_dilation > 0).astype(np.int32) -
                            (dilation[di] > 0).astype(np.int32))
        keep = dilation_toggles != 0
        erosion_packed = self._stencil_deltas(di[keep], dilation_toggles[keep])
        ei, ed = erosion_packed
        added: Mask = {}
        removed: Mask = {}
        limit = len(self.stencil)
        candidates = np.unique(np.concatenate((bi, si, ei)))
        if len(candidates):
            bd_all = self._on_candidates(candidates, base_packed)
            sd_all = self._on_candidates(candidates, support_packed)
            ed_all = self._on_candidates(candidates, erosion_packed)
            after = erosion[candidates] + ed_all
            if np.any((after < 0) | (after > limit)):
                raise AssertionError("erosion support outside stencil range")
            y, x = np.divmod(candidates, w)
            x -= self.pad_x
            y -= self.pad_y
            inside = ((x >= 0) & (x < self.width) &
                      (y >= 0) & (y < self.height))
            valid = np.flatnonzero(inside)
            valid = valid[self.allowed[y[valid], x[valid]]]
            was = ((base[candidates] > 0) |
                   ((erosion[candidates] == limit) &
                    (trace_support[candidates] >= 2)))
            now = ((base[candidates] + bd_all > 0) |
                   ((after == limit) &
                    (trace_support[candidates] + sd_all >= 2)))
            changed = valid[was[valid] != now[valid]]
            for k in changed.tolist():
                xx, yy = int(x[k]), int(y[k])
                cell = (xx // 4, yy // 4)
                target = added if now[k] else removed
                target[cell] = target.get(cell, 0) | 1 << ((yy % 4) * 4 + xx % 4)
        token = GapChange(added, removed,
                          sum(m.bit_count() for m in added.values())
                          - sum(m.bit_count() for m in removed.values()),
                          self, self._version,
                          base_packed, dilation_packed,
                          erosion_packed, support_packed)
        if commit:
            self.commit(token)
        return token

    def preview_removal(self, source_removed_mask) -> GapChange:
        """Preview removal from a sparse mask or fine-grid ``(x, y)`` pixels."""
        return self.change(source_removed_mask=source_removed_mask)

    def commit(self, token: GapChange) -> None:
        if token._owner is not self or token._version != self._version:
            raise ValueError("change token belongs to a different field state")
        for field, packed in ((self.base_support, token._base_deltas),
                              (self.dilation_support, token._dilation_deltas),
                              (self.erosion_support, token._erosion_deltas),
                              (self.trace_support, token._support_deltas)):
            indices, deltas = packed
            field.ravel()[indices] += deltas
        self.output_count += token.output_count_delta
        self._version += 1
