import json, time, traceback
from pathlib import Path
from pcb_v48_renderer import V48Renderer, sample_seed
base_seed=8528317405406420078
out=Path('work/inflight/evidence/20260827_exact_seed_replay')
meta={'base_seed':base_seed,'aspect_ratio':'1:6','scale':0.35,'logical_index':0,
      'expected_sample_seed':9409060408987575905}
start=time.perf_counter()
try:
    r=V48Renderer('1:6',0.35,base_seed)
    actual=sample_seed(r.seed,0)
    meta['actual_sample_seed']=actual
    assert actual==meta['expected_sample_seed'], (actual,meta['expected_sample_seed'])
    placed,report=r.generate_sample(0)
    meta['elapsed_seconds']=time.perf_counter()-start
    meta['status']='PASS'
    meta['report_seed']=report.get('seed')
    (out/'exact_report.json').write_text(json.dumps(report,indent=2))
    (out/f'exact_seed_{actual}.svg').write_text(r.svg_for(placed,report))
except BaseException as e:
    meta['elapsed_seconds']=time.perf_counter()-start
    meta['status']='FAIL'
    meta['exception']=repr(e)
    meta['traceback']=traceback.format_exc()
    (out/'exact_failure.txt').write_text(meta['traceback'])
    raise
finally:
    (out/'run_metadata.json').write_text(json.dumps(meta,indent=2))
    print(json.dumps(meta,indent=2), flush=True)
