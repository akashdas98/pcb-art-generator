#!/usr/bin/env python3
"""Cheap deterministic V48 performance/behavior harness.

Runs only Phase A (main-chip creation/placement) + Phase B (main routing/preflight),
so optimization candidates can be screened without paying for residual components/local-gap fill.
Can load any renderer source path, making differential comparisons against a known-good oracle cheap.
"""
from __future__ import annotations
import argparse, importlib.util, importlib.machinery, inspect, json, math, os, resource, sys, time, hashlib
from pathlib import Path

WORK_KEYS = (
    'pathway_lookahead_evaluation_count','pathway_gesture_clear_check_count',
    'pathway_holistic_connection_pair_count','pathway_holistic_front_round_count','pathway_decision_round_count',
    'pathway_local_space_capacity_evaluation_count','pathway_reroute_scheduled_count',
    'pathway_reroute_exhausted_count','pathway_traceback_count','pathway_traceback_segment_count',
    'pathway_recovery_fragment_count','pathway_reroute_short_rebase_count',
    'pathway_persistence_shared_tick_count','pathway_persistence_shared_rebuild_count',
    'pathway_incremental_rollback_batch_count','pathway_incremental_rollback_segment_remove_count',
)
HARD_KEYS = (
    'pathway_launch_trace_count','pathway_visible_launch_trace_count',
    'pathway_main_unaccounted_launch_trace_count','pathway_main_short_termination_trace_count',
    'pathway_main_stalled_side_count','pathway_non_octilinear_segment_count','pathway_illegal_turn_count',
    'pathway_unmarked_clearance_violation_count','pathway_unmarked_overlap_count',
    'pathway_static_intersection_count','pathway_intersection_trace_cleanup_count',
)
QUALITY_KEYS = (
    'pathway_mean_segments_per_trace','pathway_mean_geometric_length','pathway_mean_turns_per_trace',
    'pathway_connection_count','pathway_cross_chip_connection_count','pathway_cross_chip_connected_trace_count','pathway_post_main_terminal_connection_count','pathway_escape_trace_count',
    'pathway_termination_trace_count','pathway_bundled_forced_termination_trace_count',
)

def load_module(path: Path):
    tag='v48bench_'+hashlib.sha1(str(path.resolve()).encode()).hexdigest()[:12]
    loader=importlib.machinery.SourceFileLoader(tag,str(path))
    spec=importlib.util.spec_from_loader(tag,loader)
    if spec is None or spec.loader is None: raise RuntimeError(f'cannot load {path}')
    mod=importlib.util.module_from_spec(spec); sys.modules[tag]=mod; spec.loader.exec_module(mod)
    return mod

def build_chips(mod, r, cur_seed):
    srng=mod.SplitMix64(cur_seed)
    nc=r.chip_count(srng)
    # Consume the same collection-count/family-assignment RNG work as generate_sample before chips.
    N=r.collection_count(srng)
    assigns,quotas=r.assign_collection_families(srng,N)
    if assigns is None: raise RuntimeError('collection family assignment failed in deterministic setup')
    chips=[]; sigs=set()
    for j in range(nc):
        base=mod.chip_seed(cur_seed,j); found=None
        for rr in range(128):
            try: g=r.generate_chip(mod.retry_seed(base,rr) if rr else base,j)
            except RuntimeError: continue
            sig=(g.structural.get('orientation'),g.structural.get('aspect_bin'),g.structural.get('motifs'),
                 g.structural.get('inner_border_count'),g.structural.get('exterior_side_set_configuration'))
            if sig not in sigs: found=g; sigs.add(sig); break
        if found is None: raise RuntimeError(f'chip generation failed at {j}')
        chips.append(found)
    placed=r.place_objects(chips,[],[],mod.SplitMix64(mod.placement_seed(cur_seed)))
    if placed is None: raise RuntimeError('chip placement failed')
    return placed, nc

def run_one(source: Path, aspect: str, scale: float, seed: int,
            main_chip_density_multiplier: float=1.0, main_run_length_multiplier: float=1.0):
    mod=load_module(source)
    Renderer=getattr(mod,'V48Renderer',None) or getattr(mod,'V46Renderer',None) or getattr(mod,'V45Renderer',None)
    if Renderer is None: raise RuntimeError(f'no supported renderer class in {source}')
    params=inspect.signature(Renderer).parameters
    kwargs=dict(aspect_ratio=aspect, scale=scale, seed=seed)
    if 'main_chip_density_multiplier' in params:
        kwargs['main_chip_density_multiplier']=main_chip_density_multiplier
    if 'main_run_length_multiplier' in params:
        kwargs['main_run_length_multiplier']=main_run_length_multiplier
    r=Renderer(**kwargs)
    logical_seed=mod.sample_seed(r.seed,0)
    t0=time.perf_counter(); c0=time.process_time()
    placed,nc=build_chips(mod,r,logical_seed)
    chip_wall=time.perf_counter()-t0
    route0=time.perf_counter(); cpu0=time.process_time()
    status='PASS'; error=None; stats={}
    groups=[]
    try:
        groups,stats=r.generate_main_pathways(logical_seed, placed)
    except Exception as e:
        status='FAIL'; error=f'{type(e).__name__}: {e}'
    route_wall=time.perf_counter()-route0; route_cpu=time.process_time()-cpu0
    total_wall=time.perf_counter()-t0; total_cpu=time.process_time()-c0
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    out={
        'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'aspect_ratio':aspect,'scale':scale,'seed':seed,'logical_seed':logical_seed,
        'main_chip_density_multiplier':(getattr(r,'main_chip_density_multiplier',None)),
        'main_run_length_multiplier':(getattr(r,'main_run_length_multiplier',None)),
        'status':status,'error':error,'chip_count':nc,'chip_wall_s':chip_wall,
        'main_wall_s':route_wall,'main_cpu_s':route_cpu,'total_wall_s':total_wall,'total_cpu_s':total_cpu,
        'max_rss_kib':rss,
        'output_geometry_sha256':(hashlib.sha256(json.dumps(
            [[p.svg for p in g.primitives] for g in groups],sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if groups else None),
        'effective_area_multiplier':(float(aspect.split(':')[0])/float(aspect.split(':')[1]) if float(aspect.split(':')[0])>=float(aspect.split(':')[1]) else float(aspect.split(':')[1])/float(aspect.split(':')[0]))/(scale*scale),
    }
    if stats:
        for k in WORK_KEYS+HARD_KEYS+QUALITY_KEYS: out[k]=stats.get(k,0)
        for k in ('pathway_gesture_clear_opportunity_count','pathway_gesture_legality_cache_hit_count',
                  'pathway_gesture_legality_cache_miss_count','pathway_path_collision_cache_hit_count',
                  'pathway_path_collision_cache_miss_count','pathway_reroute_unique_exhausted_front_count',
                  'pathway_reroute_repeat_exhausted_attempt_count','pathway_reroute_repeat_same_front_state_count',
                  'pathway_reroute_repeat_changed_front_state_count','pathway_reroute_repeat_same_local_state_count',
                  'pathway_reroute_repeat_changed_local_state_count','pathway_static_query_cache_hit_count',
                  'pathway_static_query_cache_miss_count'):
            out[k]=stats.get(k,0)
        out['pathway_profile']=stats.get('pathway_profile')
        for k,v in stats.items():
            if k.startswith('pathway_locality_'):
                out[k]=v
        seg=max(1,stats.get('pathway_trace_count',stats.get('pathway_visible_launch_trace_count',1))*max(stats.get('pathway_mean_segments_per_trace',0),1e-9))
        out['gesture_checks_per_final_segment']=stats.get('pathway_gesture_clear_check_count',0)/seg
        out['lookaheads_per_final_segment']=stats.get('pathway_lookahead_evaluation_count',0)/seg
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('sources',nargs='+',type=Path)
    ap.add_argument('--aspect-ratio',default='1:1')
    ap.add_argument('--scale',type=float,default=1.0)
    ap.add_argument('--seed',type=int,default=20260816)
    ap.add_argument('--main-chip-density-multiplier',type=float,default=1.0)
    ap.add_argument('--main-run-length-multiplier',type=float,default=1.0)
    ap.add_argument('--out',type=Path)
    args=ap.parse_args()
    rows=[]
    for src in args.sources:
        row=run_one(src,args.aspect_ratio,args.scale,args.seed,
                    main_chip_density_multiplier=args.main_chip_density_multiplier,
                    main_run_length_multiplier=args.main_run_length_multiplier); rows.append(row)
        print(json.dumps(row,sort_keys=True),flush=True)
    payload={'runs':rows}
    if len(rows)==2:
        a,b=rows
        delta={}
        for k in ('main_wall_s','main_cpu_s','max_rss_kib')+WORK_KEYS+QUALITY_KEYS:
            av=a.get(k); bv=b.get(k)
            if isinstance(av,(int,float)) and isinstance(bv,(int,float)):
                delta[k]={'a':av,'b':bv,'delta':bv-av,'ratio':(bv/av if av else None)}
        payload['delta_a_to_b']=delta
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')

if __name__=='__main__': main()
