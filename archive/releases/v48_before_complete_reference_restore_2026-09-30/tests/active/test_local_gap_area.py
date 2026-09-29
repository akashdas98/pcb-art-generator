"""The LOCAL area ledger must count only gaps shared by distinct traces."""

import random
import unittest

import numpy as np

from local_gap_area import LocalGapAreaField


def sparse(points):
    result = {}
    for x, y in points:
        cell = x // 4, y // 4
        result[cell] = result.get(cell, 0) | 1 << ((y % 4) * 4 + x % 4)
    return result


def points(mask):
    return {(cx * 4 + b % 4, cy * 4 + b // 4)
            for (cx, cy), bits in mask.items()
            for b in range(16) if bits & (1 << b)}


def reference(traces, allowed, field):
    """Small dense, padded Boolean reference independent of support counters."""
    height = field.height + 2 * field.pad_y
    width = field.width + 2 * field.pad_x

    def dilate(image):
        result = np.zeros_like(image)
        for dx, dy in field.stencil:
            x0, x1 = max(0, -dx), min(width, width - dx)
            y0, y1 = max(0, -dy), min(height, height - dy)
            result[y0 + dy:y1 + dy, x0 + dx:x1 + dx] |= image[y0:y1, x0:x1]
        return result

    arrays = []
    for trace in traces:
        image = np.zeros((height, width), dtype=bool)
        for x, y in points(trace):
            image[y + field.pad_y, x + field.pad_x] = True
        arrays.append(image)
    base = np.logical_or.reduce(arrays) if arrays else np.zeros((height, width), bool)
    dilated = dilate(base)
    closed = np.ones_like(base)
    for dx, dy in field.stencil:
        x0, x1 = max(0, -dx), min(width, width - dx)
        y0, y1 = max(0, -dy), min(height, height - dy)
        shifted = np.zeros_like(base)
        shifted[y0:y1, x0:x1] = dilated[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
        closed &= shifted
    support = np.zeros_like(base, dtype=np.int32)
    for trace in arrays:
        support += dilate(trace)
    output = base | (closed & (support >= 2))
    return {(x, y) for x, y in points(allowed)
            if output[y + field.pad_y, x + field.pad_x]}


class LocalGapAreaTests(unittest.TestCase):
    def make_field(self, traces, *, allowed=None, radius=2.1, cw=4, ch=4):
        base = sparse(set().union(*(points(t) for t in traces)))
        return LocalGapAreaField(4, 4, cw, ch, 4, source_mask=base,
                                 allowed_mask=allowed, trace_masks=traces,
                                 radius=radius)

    def test_local_gap_two_parallel_traces_gain_and_retire_together(self):
        upper = sparse((x, 5) for x in range(2, 14))
        lower = sparse((x, 8) for x in range(2, 14))
        field = self.make_field([upper, lower])
        base = points(upper) | points(lower)
        extra = points(field.output_mask()) - base
        self.assertTrue(extra)
        self.assertTrue(all(5 < y < 8 for _, y in extra))
        self.assertEqual(points(field.output_mask()),
                         reference([upper, lower], sparse((x, y) for y in range(16)
                                                         for x in range(16)), field))
        before = field.output_mask()
        token = field.change(source_removed_mask=lower,
                             support_removed=(field.expand_mask(lower),))
        self.assertEqual(field.output_mask(), before)
        self.assertTrue(extra & points(token.output_removed))
        field.commit(token)
        self.assertEqual(points(field.output_mask()), points(upper))
        self.assertEqual(field.output_count, len(points(upper)))

    def test_local_gap_isolated_bend_and_distant_lines_have_no_gap_credit(self):
        bend = sparse([(x, 3) for x in range(2, 11)] +
                      [(10, y) for y in range(3, 11)])
        self.assertEqual(points(self.make_field([bend]).output_mask()), points(bend))
        distant = sparse((x, 15) for x in range(2, 14))
        field = self.make_field([bend, distant])
        self.assertEqual(points(field.output_mask()), points(bend) | points(distant))

    def test_local_gap_canonical_clip_and_physical_scale_invariance(self):
        traces = [sparse((x, y) for x in range(2, 14)) for y in (5, 8)]
        allowed = sparse((x, y) for y in range(16) for x in range(16)
                         if x < 9 and y < 8)
        original = self.make_field(traces, allowed=allowed)
        scaled = self.make_field(traces, allowed=allowed, cw=8, ch=8, radius=4.2)
        self.assertEqual(original.stencil, scaled.stencil)
        self.assertEqual(original.output_mask(), scaled.output_mask())
        self.assertEqual(points(original.output_mask()),
                         reference(traces, allowed, original))
        self.assertTrue(points(original.output_mask()) <= points(allowed))
        self.assertTrue(points(original.output_mask()) -
                        set().union(*(points(t) for t in traces)))

    def test_local_gap_overlap_support_preview_and_stale_token(self):
        trace = sparse((x, 6) for x in range(4, 12))
        field = self.make_field([trace, trace])
        first = field.change(support_removed=(field.expand_mask(trace),))
        self.assertEqual(first.output_added, {})
        self.assertEqual(first.output_removed, {})
        self.assertEqual(points(field.output_mask()), points(trace))
        field.commit(first)
        second = field.change(source_removed_mask=trace,
                              support_removed=(field.expand_mask(trace),))
        self.assertEqual(points(field.output_mask()), points(trace))
        field.commit(second)
        self.assertEqual(field.output_mask(), {})
        with self.assertRaises(ValueError):
            field.commit(first)
        with self.assertRaises(ValueError):
            field.change(source_removed_mask=trace)

    def test_local_gap_sparse_incremental_matches_dense_boolean_reference(self):
        rng = random.Random(58371)
        allowed = sparse((x, y) for y in range(16) for x in range(16)
                         if rng.random() > 0.15)
        traces = [sparse({(rng.randrange(16), rng.randrange(16))
                          for _ in range(7)}) for _ in range(5)]
        field = self.make_field(traces, allowed=allowed)
        for _ in range(15):
            self.assertEqual(points(field.output_mask()), reference(traces, allowed, field))
            old = points(field.output_mask())
            if traces and rng.random() < 0.6:
                trace = traces.pop(rng.randrange(len(traces)))
                remaining = set().union(*(points(t) for t in traces))
                lost_base = sparse(points(trace) - remaining)
                token = field.change(source_removed_mask=lost_base,
                                     support_removed=(field.expand_mask(trace),))
            else:
                trace = sparse({(rng.randrange(16), rng.randrange(16))
                                for _ in range(7)})
                existing = set().union(*(points(t) for t in traces))
                token = field.change(source_added_mask=sparse(points(trace) - existing),
                                     support_added=(field.expand_mask(trace),))
                traces.append(trace)
            expected = reference(traces, allowed, field)
            self.assertEqual((old | points(token.output_added)) -
                             points(token.output_removed), expected)
            self.assertEqual(points(field.output_mask()), old)
            field.commit(token)
            self.assertEqual(field.output_count, len(expected))


if __name__ == '__main__':
    unittest.main()
