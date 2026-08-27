#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.machinery, importlib.util, json, sys, time
from pathlib import Path

def load(path: Path):
    tag='localaspect_'+hashlib.sha1(str(path.resolve()).encode()).hexdigest()[:12]
    loader=importlib.machinery.SourceFileLoader(tag,str(path)); spec=importlib.util.spec_from_loader(tag,loader)
    m=importlib.util.module_from_spec(spec); sys.modules[tag]=m; spec.loader.exec_module(m); return m

def run(source,aspect,scale,seed):
    m=load(source); R=m.V48Renderer; P=m.BundleGesturePlanner
    active={'local':False}; times={}
    orig_gen=R.generate_local_gap_pathways
    def gen(self,*a,**kw):
        active['local']=True
        try:return orig_gen(self,*a,**kw)
        finally:active['local']=False
    R.generate_local_gap_pathways=gen
    names=['_launch_local_gap_fronts','_run_local_gap_fast_rounds','_local_gap_target','_gesture_clear',
           '_local_gap_direct_mopup','_local_gap_fragment_mopup','_local_gap_deterministic_debt_completion',
           '_local_gap_service_fraction','_local_gap_covered_cells']
    for name in names:
        orig=getattr(P,name)
        def make(fn,nm):
            def w(self,*a,**kw):
                if not active['local']: return fn(self,*a,**kw)
                c=time.process_time()
                try:return fn(self,*a,**kw)
                finally:
                    d=times.setdefault(nm,{'cpu_s':0.0,'calls':0}); d['cpu_s']+=time.process_time()-c; d['calls']+=1
            return w
        setattr(P,name,make(orig,name))
    r=R(aspect_ratio=aspect,scale=scale,seed=seed)
    c=time.process_time(); placed,report=r.generate_sample(0,max_sample_restarts=1,collection_plan_attempts=256,calibration_rounds=256); total=time.process_time()-c
    local={k:v for k,v in report.items() if k.startswith('pathway_local_gap_')}
    return {'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'aspect':aspect,'scale':scale,'seed':seed,'total_cpu_s':total,'timings':times,'local_stats':local,
            'whole':{k:report.get(k) for k in ['pathway_gesture_clear_check_count','pathway_lookahead_evaluation_count','pathway_launch_trace_count','component_residual_gap_total_component_count']}}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,default=Path('pcb_v48_renderer.py')); ap.add_argument('--aspect',required=True); ap.add_argument('--scale',type=float,default=.75); ap.add_argument('--seed',type=int,default=0); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args()
    row=run(a.source,a.aspect,a.scale,a.seed); a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(row,indent=2,sort_keys=True)+'\n'); print(json.dumps(row,sort_keys=True))
if __name__=='__main__':main()
