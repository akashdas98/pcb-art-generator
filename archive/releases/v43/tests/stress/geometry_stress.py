"""Optional multi-seed stress probes.

This suite is intentionally outside the release gate because it samples additional logical
boards. It uses the same one-attempt + skip policy as production; it never resurrects the old
64-restart-per-logical-sample behavior.
"""
from pathlib import Path
import sys, tempfile, unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from pcb_v43_renderer import V43Renderer, SplitMix64, sample_seed, chip_seed, placement_seed, retry_seed

class GeometryStressTests(unittest.TestCase):

    def _main_only_report(self,width,height,seed):
        r=V43Renderer(width,height,seed=seed)
        sseed=sample_seed(r.seed,0); srng=SplitMix64(sseed)
        nc=r.chip_count(srng); N=r.collection_count(srng)
        assigns,quotas=r.assign_collection_families(srng,N)
        self.assertIsNotNone(assigns)
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
            self.assertIsNotNone(found)
            chips.append(found)
        placed=r.place_objects(chips,[],[],SplitMix64(placement_seed(sseed)))
        self.assertIsNotNone(placed)
        _groups,rep=r.generate_main_pathways(sseed,placed)
        return rep

    def test_tall_canvas_main_network_preserves_exact_octilinearity(self):
        for height in (6248,8046):
            rep=self._main_only_report(1200,height,1)
            self.assertEqual(rep.get('pathway_non_octilinear_segment_count'),0,(height,rep))
            self.assertEqual(rep.get('pathway_illegal_turn_count'),0,(height,rep))
            self.assertEqual(rep.get('pathway_illegal_connection_junction_turn_count'),0,(height,rep))

    def test_three_additional_boards_preserve_hard_geometry(self):
        for seed in (2026080602,2026080603,2026080604):
            r=V43Renderer(1000,1000,seed=seed)
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
