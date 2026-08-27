#!/usr/bin/env python3
"""Time V48 production phases without changing generation semantics.

This harness loads an arbitrary renderer source, wraps selected instance methods with wall/CPU
accumulators, executes one ordinary ``generate_sample`` call, and hashes the complete primitive
SVG payload.  It is intended for proxy scaling work; candidates still need the normal release
suite and production gates.
"""
from __future__ import annotations
import argparse, hashlib, importlib.machinery, importlib.util, json, resource, sys, time
from pathlib import Path

def load_module(path: Path):
    tag='v48phase_'+hashlib.sha1(str(path.resolve()).encode()).hexdigest()[:12]
    loader=importlib.machinery.SourceFileLoader(tag,str(path)); spec=importlib.util.spec_from_loader(tag,loader)
    if spec is None or spec.loader is None: raise RuntimeError(f'cannot load {path}')
    mod=importlib.util.module_from_spec(spec); sys.modules[tag]=mod; spec.loader.exec_module(mod); return mod

def run_one(source: Path, aspect: str, scale: float, seed: int, sample_index: int):
    mod=load_module(source); Renderer=getattr(mod,'V48Renderer')
    r=Renderer(aspect_ratio=aspect,scale=scale,seed=seed)
    phases={}
    groups={
        'main_routing':['generate_main_pathways'],
        'component_prepare':['_prepare_component_population_once'],
        'component_place':['_place_component_population_on_frozen_routes'],
        'local_gap_routing':['generate_local_gap_pathways'],
        'final_clearance_audits':['_unauthorized_component_pathway_overlap_count','_local_component_clearance_violation_count','_main_local_pathway_clearance_violation_count'],
        'final_validation':['validate_sample','build_report'],
    }
    for phase,names in groups.items():
        for name in names:
            original=getattr(r,name)
            def make_wrapper(fn,phase_name):
                def wrapped(*args,**kwargs):
                    w0=time.perf_counter(); c0=time.process_time()
                    try: return fn(*args,**kwargs)
                    finally:
                        rec=phases.setdefault(phase_name,{'wall_s':0.0,'cpu_s':0.0,'calls':0})
                        rec['wall_s']+=time.perf_counter()-w0; rec['cpu_s']+=time.process_time()-c0; rec['calls']+=1
                return wrapped
            setattr(r,name,make_wrapper(original,phase))
    w0=time.perf_counter(); c0=time.process_time()
    placed,report=r.generate_sample(sample_index,max_sample_restarts=1,collection_plan_attempts=256,calibration_rounds=256)
    total_wall=time.perf_counter()-w0; total_cpu=time.process_time()-c0
    geom_hash=hashlib.sha256(json.dumps([[p.svg for p in g.primitives] for g in placed],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    accounted=sum(x['wall_s'] for x in phases.values())
    return {
        'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'aspect_ratio':aspect,'scale':scale,'seed':seed,'sample_index':sample_index,'status':'PASS',
        'total_wall_s':total_wall,'total_cpu_s':total_cpu,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'output_geometry_sha256':geom_hash,'phase_times':phases,'unattributed_wall_s':max(0.0,total_wall-accounted),
        'report':{k:report.get(k) for k in (
            'chip_count','collection_count','pathway_launch_trace_count','pathway_visible_launch_trace_count',
            'pathway_main_short_termination_trace_count','pathway_main_stalled_side_count',
            'pathway_local_gap_fill_actual','pathway_local_gap_source_count','pathway_local_gap_trace_count',
            'component_residual_gap_fill_actual','component_residual_gap_total_component_count',
            'pathway_gesture_clear_check_count','pathway_lookahead_evaluation_count')}
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('sources',nargs='+',type=Path)
    ap.add_argument('--aspect-ratio',default='1:1'); ap.add_argument('--scale',type=float,default=1.0)
    ap.add_argument('--seed',type=int,default=20260816); ap.add_argument('--sample-index',type=int,default=0); ap.add_argument('--out',type=Path)
    a=ap.parse_args(); rows=[]
    for source in a.sources:
        row=run_one(source,a.aspect_ratio,a.scale,a.seed,a.sample_index); rows.append(row); print(json.dumps(row,sort_keys=True),flush=True)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps({'runs':rows},indent=2,sort_keys=True)+'\n')
if __name__=='__main__': main()
