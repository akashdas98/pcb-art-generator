import json, sys, time, traceback
from pathlib import Path
from pcb_v48_renderer import (
    V48Renderer, SplitMix64, chip_seed, retry_seed, placement_seed
)

def replay(sample_seed_value:int, aspect_ratio:str, scale:float, out_path:Path):
    start=time.perf_counter()
    meta={"sample_seed":int(sample_seed_value),"aspect_ratio":aspect_ratio,"scale":float(scale)}
    try:
        r=V48Renderer(aspect_ratio, scale, 0)
        cur_seed=int(sample_seed_value)
        srng=SplitMix64(cur_seed)
        nc=r.chip_count(srng); N=r.collection_count(srng)
        assigns,quotas=r.assign_collection_families(srng,N)
        if assigns is None:
            raise RuntimeError("collection family construction unexpectedly returned no assignment")
        chips=[]; chip_sigs=set()
        for j in range(nc):
            base=chip_seed(cur_seed,j); found=None
            for rr in range(128):
                try:
                    g=r.generate_chip(retry_seed(base,rr) if rr else base,j)
                except RuntimeError:
                    continue
                sig=r._chip_geometry_fingerprint(g)
                if sig not in chip_sigs:
                    found=g; chip_sigs.add(sig); break
            if found is None:
                for salt in range(256):
                    g=r._construct_chip_fallback(retry_seed(base,0x50000+salt),j)
                    sig=r._chip_geometry_fingerprint(g)
                    if sig not in chip_sigs:
                        found=g; chip_sigs.add(sig); break
            if found is None:
                raise RuntimeError("chip uniqueness construction exhausted for requested seed")
            chips.append(found)
        chip_rng=SplitMix64(placement_seed(cur_seed))
        placed_chips=r.place_objects(chips,[],[],chip_rng)
        if placed_chips is None:
            placed_chips=r._deterministic_place_main_chip_population(chips)
        if placed_chips is None:
            raise RuntimeError("main-chip population cannot fit the valid canvas under hard clearances")
        groups,stats=r.generate_main_pathways(cur_seed,placed_chips)
        meta.update({
            "status":"PASS","elapsed_s":time.perf_counter()-start,
            "chip_count":len(placed_chips),
            "launch_trace_count":stats.get("pathway_launch_trace_count"),
            "visible_launch_trace_count":stats.get("pathway_visible_launch_trace_count"),
            "unresolved":stats.get("pathway_main_active_unmaterialized_launch_trace_count",0),
            "stalled_sides":stats.get("pathway_main_stalled_side_count",0),
            "short_terminations":stats.get("pathway_main_short_termination_trace_count",0),
            "unaccounted":stats.get("pathway_main_unaccounted_launch_trace_count",0),
            "underfloor_fragment_rejects":stats.get("pathway_underfloor_fragment_reject_count",0),
            "young_branch_survival_transactions":stats.get("pathway_young_branch_survival_transaction_count",0),
        })
    except BaseException as e:
        meta.update({"status":"FAIL","elapsed_s":time.perf_counter()-start,"exception":repr(e),"traceback":traceback.format_exc()})
    out_path.write_text(json.dumps(meta,indent=2))
    print(json.dumps(meta),flush=True)
    return 0 if meta["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(replay(int(sys.argv[1]),sys.argv[2],float(sys.argv[3]),Path(sys.argv[4])))
