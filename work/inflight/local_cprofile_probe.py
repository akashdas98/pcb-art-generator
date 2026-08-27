#!/usr/bin/env python3
from __future__ import annotations
import argparse,cProfile,pstats,io,hashlib,importlib.machinery,importlib.util,json,sys,time
from pathlib import Path

def load(path):
 t='lcprof_'+hashlib.sha1(str(path.resolve()).encode()).hexdigest()[:12]; ld=importlib.machinery.SourceFileLoader(t,str(path)); sp=importlib.util.spec_from_loader(t,ld); m=importlib.util.module_from_spec(sp); sys.modules[t]=m; sp.loader.exec_module(m); return m

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--aspect',required=True); ap.add_argument('--scale',type=float,default=.75); ap.add_argument('--seed',type=int,default=0); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args(); m=load(Path('pcb_v48_renderer.py'))
 orig=m.V48Renderer.generate_local_gap_pathways; holder={}
 def wrap(self,*args,**kw):
  pr=cProfile.Profile(); c=time.process_time(); pr.enable()
  try:return orig(self,*args,**kw)
  finally:
   pr.disable(); holder['cpu_s']=time.process_time()-c
   s=io.StringIO(); pstats.Stats(pr,stream=s).sort_stats('cumtime').print_stats(80); holder['profile']=s.getvalue()
 m.V48Renderer.generate_local_gap_pathways=wrap
 r=m.V48Renderer(aspect_ratio=a.aspect,scale=a.scale,seed=a.seed); _,rep=r.generate_sample(0,max_sample_restarts=1,collection_plan_attempts=256,calibration_rounds=256)
 a.out.write_text(json.dumps({'aspect':a.aspect,'cpu_s':holder['cpu_s'],'profile':holder['profile'],'local_trace_count':rep.get('pathway_local_gap_trace_count'),'visible':rep.get('pathway_local_gap_visible_trace_count'),'regions':rep.get('pathway_local_gap_region_count')},indent=2)+'\n')
 print(holder['profile'])
if __name__=='__main__':main()
