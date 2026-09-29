import sys,json,time,hashlib,importlib.machinery,importlib.util
from pathlib import Path

def load(path):
    tag='resperf_'+hashlib.sha1((str(path)+str(time.time_ns())).encode()).hexdigest()[:10]
    loader=importlib.machinery.SourceFileLoader(tag,str(path)); spec=importlib.util.spec_from_loader(tag,loader)
    m=importlib.util.module_from_spec(spec); sys.modules[tag]=m; spec.loader.exec_module(m); return m
src=Path(sys.argv[1]); scale=float(sys.argv[2]); seed=int(sys.argv[3]); out=Path(sys.argv[4])
m=load(src); r=m.V48Renderer(aspect_ratio='1:1',scale=scale,seed=seed)
times={}
for name in ('_place_component_population_on_frozen_routes','generate_local_gap_pathways'):
    old=getattr(r,name)
    def wrap(*a,__old=old,__name=name,**kw):
        c=time.process_time(); w=time.perf_counter()
        try:return __old(*a,**kw)
        finally: times[__name]={'cpu_s':time.process_time()-c,'wall_s':time.perf_counter()-w}
    setattr(r,name,wrap)
c=time.process_time(); w=time.perf_counter(); placed,rep=r.generate_sample(0); total={'cpu_s':time.process_time()-c,'wall_s':time.perf_counter()-w}
keep={k:v for k,v in rep.items() if k.startswith('pathway_local_gap_') or k.startswith('component_residual_') or k.startswith('component_gap_scheduler_')}
keep.update({k:rep.get(k) for k in ('chip_count','collection_count','pathway_gesture_clear_check_count','pathway_lookahead_evaluation_count')})
data={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'scale':scale,'seed':seed,'times':times,'total':total,'report':keep}
out.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n'); print(json.dumps({'src':data['sha256'][:8],'scale':scale,'seed':seed,'total_cpu':total['cpu_s'],'comp_cpu':times.get('_place_component_population_on_frozen_routes',{}).get('cpu_s'),'local_cpu':times.get('generate_local_gap_pathways',{}).get('cpu_s'),'local_sources':rep.get('pathway_local_gap_source_count'),'local_target_evals':rep.get('pathway_local_gap_target_cell_evaluation_count'),'local_spawn_attempts':rep.get('pathway_local_gap_spawn_attempt_count'),'local_clusters':rep.get('pathway_local_gap_fill_cluster_count')}))
