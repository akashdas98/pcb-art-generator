import json,sys,time,hashlib
from pathlib import Path
from pcb_v48_renderer import V48Renderer
mult=float(sys.argv[1]); seed=int(sys.argv[2]); out=Path(sys.argv[3]); out.mkdir(parents=True,exist_ok=True)
t0=time.perf_counter()
r=V48Renderer(aspect_ratio=(1,1),scale=.35,seed=seed,main_chip_density_multiplier=.25,main_run_length_multiplier=mult)
placed,rep=r.generate_sample(0)
elapsed=time.perf_counter()-t0
rep=dict(rep); rep['qualification_elapsed_seconds']=elapsed; rep['base_seed']=seed; rep['requested_run_length_multiplier']=mult
svg=r.svg_for(placed,rep)
(out/'result.svg').write_text(svg)
(out/'report.json').write_text(json.dumps(rep,indent=2,sort_keys=True))
print(json.dumps({'mult':mult,'seed':rep.get('seed'),'elapsed':elapsed,'chip_count':rep.get('main_chip_count'),
'cross':rep.get('pathway_cross_chip_connection_count'),'local_clusters':rep.get('pathway_local_gap_fill_cluster_count'),
'local_cluster_max':rep.get('pathway_local_gap_fill_cluster_realized_max'),'component_cluster_max':rep.get('component_residual_fill_cluster_realized_max'),
'stalled':rep.get('pathway_main_stalled_side_count'),'short':rep.get('pathway_main_short_termination_trace_count'),
'unaccounted':rep.get('pathway_main_unaccounted_launch_trace_count')}))
