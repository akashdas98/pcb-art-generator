import json,sys,time,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[6]))
from pcb_v48_renderer import V48Renderer
out=Path(sys.argv[1]); rl=float(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
t=time.perf_counter()
try:
    r=V48Renderer('1:1',.35,20260827184756,main_chip_density_multiplier=.25,main_run_length_multiplier=rl)
    placed,report=r.generate_sample(0)
    dt=time.perf_counter()-t
    (out/'report.json').write_text(json.dumps(report,indent=2,sort_keys=True))
    (out/'result.svg').write_text(r.svg_for(placed,report))
    (out/'wall_seconds.txt').write_text(f'{dt:.9f}\n')
    (out/'rc.txt').write_text('0\n')
except BaseException:
    (out/'exception.txt').write_text(traceback.format_exc())
    (out/'rc.txt').write_text('1\n')
