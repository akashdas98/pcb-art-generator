"""Optional multi-seed stress probes.

This suite is intentionally outside the release gate because it samples additional logical
boards. It uses the same one-attempt + skip policy as production; it never resurrects the old
64-restart-per-logical-sample behavior.
"""
from pathlib import Path
import sys, tempfile, unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pcb_v40_renderer import V40Renderer

class GeometryStressTests(unittest.TestCase):
    def test_three_additional_boards_preserve_hard_geometry(self):
        for seed in (2026080602,2026080603,2026080604):
            r=V40Renderer(1000,1000,seed=seed)
            with tempfile.TemporaryDirectory() as td:
                reports,_skipped=r.render_batch(1,Path(td),max_sample_restarts=1,max_logical_samples=8)
            rep=reports[0]
            for key in ('pathway_static_intersection_count','pathway_unmarked_overlap_count',
                        'pathway_collapsed_overlap_count','pathway_unmarked_stroke_overlap_count',
                        'pathway_compensating_zigzag_count','pathway_tiny_termination_trace_count',
                        'pathway_midline_connection_count','pathway_multiply_connected_trace_count',
                        'pathway_termination_marker_overlap_count','pathway_duplicate_trace_cleanup_count',
                        'pathway_intersection_trace_cleanup_count','pathway_non_octilinear_segment_count',
                        'pathway_illegal_turn_count','pathway_illegal_connection_junction_turn_count'):
                self.assertEqual(rep.get(key,0),0,(seed,key,rep.get(key)))

if __name__=='__main__': unittest.main(verbosity=2)
