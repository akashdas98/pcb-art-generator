import json, math, time, traceback
from pathlib import Path
from pcb_v48_renderer import V48Renderer, SplitMix64, chip_seed, retry_seed, placement_seed, BundleGesturePlanner
seed=3524258640260304746
out=Path('work/inflight/evidence/20260827_persistence_totality_birth_fix/exact_seed_replays/run5_front527_diagnostic.json')
r=V48Renderer('1:6',0.35,0)
srng=SplitMix64(seed); nc=r.chip_count(srng); N=r.collection_count(srng); assigns,quotas=r.assign_collection_families(srng,N)
chips=[]; sigs=set()
for j in range(nc):
    base=chip_seed(seed,j); found=None
    for rr in range(128):
        try: g=r.generate_chip(retry_seed(base,rr) if rr else base,j)
        except RuntimeError: continue
        sig=r._chip_geometry_fingerprint(g)
        if sig not in sigs: found=g; sigs.add(sig); break
    if found is None:
        for salt in range(256):
            g=r._construct_chip_fallback(retry_seed(base,0x50000+salt),j); sig=r._chip_geometry_fingerprint(g)
            if sig not in sigs: found=g; sigs.add(sig); break
    if found is None: raise RuntimeError('chip placement prep failed')
    chips.append(found)
placed=r.place_objects(chips,[],[],SplitMix64(placement_seed(seed))) or r._deterministic_place_main_chip_population(chips)
planner=BundleGesturePlanner(r,seed,placed,enable_failure_certificates=True)
start=time.perf_counter(); result={"sample_seed":seed,"aspect_ratio":"1:6","scale":0.35}
try:
    planner.run_main_only(); result['status']='UNEXPECTED_PASS'
except BaseException as e:
    result['status']='FAIL_CAPTURED'; result['exception']=repr(e); result['elapsed_s']=time.perf_counter()-start
    def lens(f):
        paths=planner._materialized_paths(f)
        return {str(tid):sum(math.hypot(b[0]-a[0],b[1]-a[1]) for a,b in zip(paths.get(tid,()),paths.get(tid,())[1:]))/planner.module for tid in f.get('ids',())}
    def brief(f):
        if not f: return None
        d={k:f.get(k) for k in ('id','parent','branch_parent','chip','side','side_index','depth','status','lifecycle','gestures','local_gestures','travel','branch_stage','branch_turn','fan_pending','fan_group','fragment_group','recovery_fragment_child','fragment_pending','failures','reroute_attempts','reroute_mode_rounds','quality_repair_reason','recovery_floor_segments','connection_lock','forced_straight_modules','forced_turn_modules','branch_retry_after_gesture','launch_fan_short_rebase','rescue_branch_short_rebase')}
        d['ids']=list(f.get('ids',())); d['path_len']=len(f.get('path',())); d['route_history_len']=len(f.get('route_history',())); d['lane_lengths_modules']=lens(f)
        d['route_history_tail']=[{k:s.get(k) for k in ('dir','travel','gestures','local_gestures','branch_stage','branch_turn','normal_len_count')} for s in f.get('route_history',())[-8:]]
        return d
    unresolved=[f for f in planner.fronts.values() if f.get('status')=='active' and planner._main_persistence_reasons(f)]
    result['unresolved']=[brief(f) | {'reasons':planner._main_persistence_reasons(f)} for f in unresolved]
    f=planner.fronts.get(527)
    result['front527']=brief(f)
    chain=[]; cur=f; seen=set()
    while cur and cur.get('id') not in seen:
        seen.add(cur['id']); chain.append(brief(cur)); cur=planner.fronts.get(cur.get('parent'))
    result['parent_chain']=chain
    if f:
        result['same_parent']=[brief(x) for x in planner.fronts.values() if x.get('parent')==f.get('parent')]
        result['stats']={k:v for k,v in planner.stats.items() if any(s in k for s in ('branch','traceback','reroute','fragment','persistence','survival','transaction')) and isinstance(v,(int,float,str,bool))}
    result['traceback']=traceback.format_exc()
out.write_text(json.dumps(result,indent=2))
print(json.dumps({k:result[k] for k in result if k not in ('traceback','unresolved','parent_chain','same_parent','stats','front527')},indent=2),flush=True)
raise SystemExit(0)
