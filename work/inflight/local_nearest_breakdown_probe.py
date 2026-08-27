#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.machinery, importlib.util, json, sys, time
from pathlib import Path

def load(path: Path):
    tag='localnearest_'+hashlib.sha1(str(path.resolve()).encode()).hexdigest()[:12]
    loader=importlib.machinery.SourceFileLoader(tag,str(path)); spec=importlib.util.spec_from_loader(tag,loader)
    m=importlib.util.module_from_spec(spec); sys.modules[tag]=m; spec.loader.exec_module(m); return m

def run(source,aspect,scale,seed):
    m=load(source); R=m.V48Renderer; P=m.BundleGesturePlanner
    real_tree=m.STRtree; active={'v':False}; records=[]; seq={'n':0}
    class TimedTree:
        def __init__(self, geoms, *a, **kw):
            self._active=active['v']; self._n=len(geoms); self._slot=None
            c=time.process_time(); self._tree=real_tree(geoms,*a,**kw); dt=time.process_time()-c
            if self._active:
                # In the historical launch block construction is static then path, once each.
                self._slot='static' if (seq['n']%2)==0 else 'path'; seq['n']+=1
                records.append({'op':'build','slot':self._slot,'n':self._n,'cpu_s':dt})
        def query_nearest(self,*a,**kw):
            c=time.process_time(); out=self._tree.query_nearest(*a,**kw); dt=time.process_time()-c
            if self._active: records.append({'op':'query_nearest','slot':self._slot,'n':self._n,'cpu_s':dt})
            return out
        def __getattr__(self,name): return getattr(self._tree,name)
    m.STRtree=TimedTree
    orig=P._launch_local_gap_fronts
    def launch(self,*a,**kw):
        active['v']=True
        try:return orig(self,*a,**kw)
        finally:active['v']=False
    P._launch_local_gap_fronts=launch
    r=R(aspect_ratio=aspect,scale=scale,seed=seed)
    c=time.process_time(); _placed,report=r.generate_sample(0,max_sample_restarts=1,collection_plan_attempts=256,calibration_rounds=256); total=time.process_time()-c
    agg={}
    for rec in records:
        k=rec['slot']+'_'+rec['op']; d=agg.setdefault(k,{'calls':0,'cpu_s':0.0,'geom_total':0}); d['calls']+=1; d['cpu_s']+=rec['cpu_s']; d['geom_total']+=rec['n']
    return {'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'aspect':aspect,'scale':scale,'seed':seed,'total_cpu_s':total,'nearest':agg,'records':records,
            'local':{k:v for k,v in report.items() if k in ('pathway_local_gap_visible_trace_count','pathway_local_gap_trace_count','pathway_local_gap_spawn_attempt_count','pathway_local_gap_region_count')}}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,default=Path('pcb_v48_renderer.py')); ap.add_argument('--aspect',required=True); ap.add_argument('--scale',type=float,default=.75); ap.add_argument('--seed',type=int,default=0); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args()
    row=run(a.source,a.aspect,a.scale,a.seed); a.out.write_text(json.dumps(row,indent=2,sort_keys=True)+'\n'); print(json.dumps(row,sort_keys=True))
if __name__=='__main__':main()
