#!/usr/bin/env python3
import argparse, glob, json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
ENGINE_VERSION="0.2.0"; STRONG_COMMERCE={"AMAZON","ETSY"}; MEASUREMENT_TRUTH_STATES={"PRIMARY_ANCHOR","FALLBACK_PROXY","ANCHOR_GAP"}
def dt(s): return datetime.fromisoformat(s.replace("Z","+00:00"))
def elapsed_hours(a,b): return max((dt(b)-dt(a)).total_seconds()/3600.0,1e-9)
def interval_velocity(p0,p1):
    v0=float(p0["value"]); v1=float(p1["value"]); h=elapsed_hours(p0["t"],p1["t"]); return (v1-v0)/h, None if v0==0 else ((v1-v0)/abs(v0))/h
def analyze_series(points):
    pts=sorted(points,key=lambda x:dt(x["t"])); out={"timepoints":len(pts),"velocity":None,"normalized_velocity":None,"acceleration":None,"series_state":"MOMENTUM_UNPROVEN"}
    if len(pts)<2: return out
    values=[float(p["value"]) for p in pts]
    if all(abs(v)<1e-12 for v in values): return out
    v,n=interval_velocity(pts[-2],pts[-1]); out["velocity"]=v; out["normalized_velocity"]=n
    if len(pts)==2:
        out["series_state"]="POSITIVE_VELOCITY" if v>0 else "DECELERATING" if v<0 else "STABLE" if values[-1]>0 else "MOMENTUM_UNPROVEN"; return out
    _,n0=interval_velocity(pts[-3],pts[-2]); v1,n1=interval_velocity(pts[-2],pts[-1])
    if n0 is not None and n1 is not None:
        out["acceleration"]=n1-n0
        out["series_state"]="POSITIVE_ACCELERATION" if v1>0 and out["acceleration"]>0 else "POSITIVE_VELOCITY" if v1>0 else "DECELERATING" if v1<0 else "STABLE" if values[-1]>0 else "MOMENTUM_UNPROVEN"
    else: out["series_state"]="POSITIVE_VELOCITY" if v1>0 else "DECELERATING" if v1<0 else "STABLE" if values[-1]>0 else "MOMENTUM_UNPROVEN"
    return out
def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def validate_observation(o):
    for k in ["observation_id","observed_at","entity_type","entity_key","surface","proxy","points","provenance"]:
        if k not in o: raise ValueError(f"observation missing {k}")
    if not o["points"] or not o["provenance"].get("machine_observed",False): raise ValueError("invalid observation")
    for p in o["points"]: dt(p["t"]); float(p["value"])
def load_sets(base_path, observation_glob):
    sets=[load(base_path)]
    for p in sorted(glob.glob(observation_glob)): sets.append(load(p))
    return sets
def merge_points(observations):
    groups=defaultdict(dict); metadata={}; breakout=defaultdict(list); candidate_keys=defaultdict(set)
    for o in observations:
        validate_observation(o); k=(o["entity_type"],o["entity_key"],o["surface"],o["proxy"])
        metadata[k]={"entity_type":o["entity_type"],"entity_key":o["entity_key"],"surface":o["surface"],"proxy":o["proxy"]}
        if o.get("measurement_identity"): metadata[k]["measurement_identity"]=o["measurement_identity"]
        if o.get("candidate_key"): candidate_keys[o["entity_key"]].add(o["candidate_key"])
        if o.get("breakout_proxy"): breakout[o["entity_key"]].append(o["breakout_proxy"])
        for p in o["points"]:
            t=p["t"]; value=float(p["value"])
            if t in groups[k] and groups[k][t]!=value: raise ValueError(f"same-proxy timestamp discordance {k} {t}")
            groups[k][t]=value
    series=[]
    for k,by_t in groups.items():
        pts=[{"t":t,"value":v} for t,v in by_t.items()]; series.append({**metadata[k],**analyze_series(pts),"points":sorted(pts,key=lambda x:dt(x["t"]))})
    return series,breakout,candidate_keys
def aggregate_entities(series,breakout,candidate_keys):
    by_entity=defaultdict(list)
    for s in series: by_entity[s["entity_key"]].append(s)
    result=[]
    for entity_key,ss in sorted(by_entity.items()):
        accel=[s for s in ss if s["series_state"]=="POSITIVE_ACCELERATION"]; pos=[s for s in ss if s["series_state"] in {"POSITIVE_ACCELERATION","POSITIVE_VELOCITY"}]
        stable=[s for s in ss if s["series_state"]=="STABLE"]; decel=[s for s in ss if s["series_state"]=="DECELERATING"]; accel_surfaces={s["surface"] for s in accel}
        strong_accel=any(s["surface"] in STRONG_COMMERCE for s in accel); breakout_high=any(b.get("cohort_percentile",0)>=90 and b.get("object_age_hours",10**9)<=72 and b.get("independent_proliferation_count",0)>=2 for b in breakout.get(entity_key,[]))
        state="ACCELERATING_CONFIRMED" if strong_accel or len(accel_surfaces)>=2 else "VELOCITY_POSITIVE_ACCELERATION_UNPROVEN" if pos else "MATURE_STABLE_DEMAND" if stable and not decel else "BREAKOUT_PROXY_HIGH" if breakout_high else "DECELERATING" if decel else "MOMENTUM_UNPROVEN"
        result.append({"entity_key":entity_key,"candidate_keys":sorted(candidate_keys.get(entity_key,set())),"state":state,"series":ss,"independent_accelerating_surfaces":sorted(accel_surfaces),"strong_commerce_acceleration":strong_accel,"breakout_proxy_high":breakout_high})
    return result
def latest_google_successes(sets):
    latest={}
    for s in sets:
        for o in s.get("observations",[]):
            if o.get("surface")!="GOOGLE_TRENDS": continue
            key=o.get("entity_key"); observed=o.get("observed_at")
            if key and observed and (key not in latest or dt(observed)>dt(latest[key]["observed_at"])): latest[key]=o
    return latest
def current_cycle_states(sets):
    candidates=[s for s in sets if "current_attempts" in s or "not_due" in s]
    if not candidates: return {}
    current=max(candidates,key=lambda s:dt(s.get("as_of","1970-01-01T00:00:00+00:00"))); out={}
    for a in current.get("current_attempts",[]):
        key=a.get("entity_key")
        if key: out[key]={"latest_attempt_at":a.get("attempted_at"),"latest_attempt_state":a.get("result"),"latest_attempt_error_class":a.get("error_class"),"measurement_basis":a.get("measurement_basis"),"anchor_query":a.get("anchor_query"),"anchor_proxy_id":a.get("anchor_proxy_id"),"query_proxy_id":a.get("query_proxy_id")}
    for n in current.get("not_due",[]):
        key=n.get("entity_key"); mi=n.get("measurement_identity") or {}
        if key and key not in out: out[key]={"latest_attempt_at":None,"latest_attempt_state":"NOT_DUE","latest_attempt_error_class":None,"measurement_basis":None,"anchor_query":mi.get("anchor_query"),"anchor_proxy_id":mi.get("anchor_proxy_id"),"query_proxy_id":None}
    return out
def measurement_contract(watchlist):
    if not watchlist: return {},[]
    by_entity={}; anchors=defaultdict(list); proxy_to_query={}
    for w in watchlist.get("entries",[]):
        qf=w.get("query_family") or []; mi=w.get("measurement_identity") or {}
        if not qf or mi.get("anchor_query")!=qf[0] or not mi.get("anchor_proxy_id"): raise ValueError(f"invalid measurement identity for {w.get('watch_id')}")
        pid=mi["anchor_proxy_id"]; aq=mi["anchor_query"]
        if pid in proxy_to_query and proxy_to_query[pid]!=aq: raise ValueError(f"anchor proxy collision {pid}")
        proxy_to_query[pid]=aq; by_entity[w["mechanism_key"]]={"anchor_query":aq,"anchor_proxy_id":pid}; anchors[pid].append(w["mechanism_key"])
    shared=[{"anchor_proxy_id":pid,"anchor_query":proxy_to_query[pid],"mechanism_keys":sorted(keys)} for pid,keys in sorted(anchors.items()) if len(keys)>1]
    return by_entity,shared
def observation_signal_basis(obs,contract):
    if not obs: return None
    mi=obs.get("measurement_identity") or {}; basis=mi.get("signal_basis")
    if basis in {"PRIMARY_ANCHOR","FALLBACK_PROXY"}: return basis
    if contract and obs.get("proxy")==contract.get("anchor_proxy_id"): return "PRIMARY_ANCHOR"
    ordinal=(obs.get("provenance") or {}).get("query_ordinal")
    return "PRIMARY_ANCHOR" if ordinal==1 else "FALLBACK_PROXY" if isinstance(ordinal,int) and ordinal>1 else None
def attach_temporal_freshness(entities,sets,generated_at,fresh_hours,watchlist=None):
    last_success=latest_google_successes(sets); cycle=current_cycle_states(sets); contracts,shared_groups=measurement_contract(watchlist); shared_by=defaultdict(list)
    for g in shared_groups:
        for key in g["mechanism_keys"]: shared_by[key]=[x for x in g["mechanism_keys"] if x!=key]
    fresh=stale=unobserved=0; latest_time=None
    for entity in entities:
        key=entity["entity_key"]; obs=last_success.get(key); cur=cycle.get(key,{}); observed_at=obs.get("observed_at") if obs else None; age=None
        if observed_at:
            age=max(0.0,(dt(generated_at)-dt(observed_at)).total_seconds()/3600.0); latest_time=observed_at if latest_time is None or dt(observed_at)>dt(latest_time) else latest_time
            freshness="FRESH_WITHIN_THRESHOLD" if age<=fresh_hours else "STALE_OVER_THRESHOLD"; fresh+=1 if age<=fresh_hours else 0; stale+=1 if age>fresh_hours else 0
        else: freshness="UNOBSERVED"; unobserved+=1
        entity.update({"last_successful_observed_at":observed_at,"temporal_evidence_age_hours_at_generation":age,"temporal_evidence_freshness_at_generation":freshness,
          "latest_attempt_at":cur.get("latest_attempt_at"),"latest_attempt_state":cur.get("latest_attempt_state","NO_CURRENT_CYCLE_RECORD"),"latest_attempt_error_class":cur.get("latest_attempt_error_class"),"signal_state_is_last_known_not_freshness_claim":True})
        contract=contracts.get(key)
        if contract:
            signal_basis=observation_signal_basis(obs,contract); attempt_state=cur.get("latest_attempt_state")
            truth=cur.get("measurement_basis") if attempt_state=="SUCCESS" and cur.get("measurement_basis") in {"PRIMARY_ANCHOR","FALLBACK_PROXY"} else "ANCHOR_GAP" if attempt_state=="SENSOR_GAP" else signal_basis if signal_basis in {"PRIMARY_ANCHOR","FALLBACK_PROXY"} else "ANCHOR_GAP"
            entity["measurement_truth_state"]=truth; entity["measurement_identity"]={"anchor_query":contract["anchor_query"],"anchor_proxy_id":contract["anchor_proxy_id"],
              "signal_query_proxy_id":cur.get("query_proxy_id") or ((obs.get("measurement_identity") or {}).get("query_proxy_id") if obs else None),
              "shared_anchor_with":shared_by.get(key,[]),"anchor_evidence_independent":len(shared_by.get(key,[]))==0,"fallback_success_redefines_anchor_identity":False}
    states=[v.get("latest_attempt_state","NO_CURRENT_CYCLE_RECORD") for v in cycle.values()]; total=len(entities)
    return {"freshness_basis":"LAST_SUCCESSFUL_OBSERVED_AT_NOT_RECEIPT_GENERATED_AT","freshness_threshold_hours":fresh_hours,"latest_successful_observed_at":latest_time,"entity_count":total,
      "fresh_entity_count":fresh,"stale_entity_count":stale,"unobserved_entity_count":unobserved,"fresh_entity_ratio":0.0 if total==0 else round(fresh/total,6),
      "current_cycle_success_count":sum(1 for s in states if s=="SUCCESS"),"current_cycle_gap_count":sum(1 for s in states if s=="SENSOR_GAP"),"current_cycle_not_due_count":sum(1 for s in states if s=="NOT_DUE"),
      "sensor_gap_advances_freshness":False,"not_due_advances_freshness":False}
def build_measurement_identity_summary(entities,watchlist):
    contracts,shared_anchor_groups=measurement_contract(watchlist); measured=[e for e in entities if e.get("entity_key") in contracts]; counts={s:0 for s in MEASUREMENT_TRUTH_STATES}; proxy_groups=defaultdict(list)
    for e in measured:
        state=e.get("measurement_truth_state","ANCHOR_GAP"); state=state if state in counts else "ANCHOR_GAP"; counts[state]+=1
        pid=(e.get("measurement_identity") or {}).get("signal_query_proxy_id")
        if pid and state in {"PRIMARY_ANCHOR","FALLBACK_PROXY"}: proxy_groups[pid].append(e["entity_key"])
    shared_signal=[{"query_proxy_id":pid,"mechanism_keys":sorted(keys)} for pid,keys in sorted(proxy_groups.items()) if len(keys)>1]
    return {"state":"M1_MEASUREMENT_IDENTITY_ACTIVE","entity_count":len(measured),"primary_anchor_count":counts["PRIMARY_ANCHOR"],"fallback_proxy_count":counts["FALLBACK_PROXY"],"anchor_gap_count":counts["ANCHOR_GAP"],
      "shared_anchor_group_count":len(shared_anchor_groups),"shared_anchor_groups":shared_anchor_groups,"shared_signal_proxy_groups":shared_signal,"shared_proxy_evidence_is_independent":False,"fallback_proxy_redefines_anchor_identity":False}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--observations",default="examples/demo-observations.json"); ap.add_argument("--observations-glob",default="examples/observations/*.json")
    ap.add_argument("--pool",default="examples/demo-quality-pool.json"); ap.add_argument("--watchlist"); ap.add_argument("--out",default="-"); ap.add_argument("--engine-commit-sha",default="UNBOUND")
    ap.add_argument("--generated-at"); ap.add_argument("--evidence-fresh-hours",type=float,default=8.0); a=ap.parse_args()
    sets=load_sets(a.observations,a.observations_glob); observations=[o for s in sets for o in s.get("observations",[])]; pool=load(a.pool); watchlist=load(a.watchlist) if a.watchlist else None
    if pool.get("count")!=len(pool.get("entries",[])): raise SystemExit("pool count mismatch")
    if pool.get("count",0)<pool.get("minimum_pool_target",14): raise SystemExit("commercial fallback pool below minimum target")
    series,breakout,candidate_keys=merge_points(observations); entities=aggregate_entities(series,breakout,candidate_keys); generated_at=a.generated_at or datetime.now(timezone.utc).isoformat()
    temporal_summary=attach_temporal_freshness(entities,sets,generated_at,a.evidence_fresh_hours,watchlist); latest=max((p["t"] for s in series for p in s["points"]),default=sets[0]["as_of"])
    receipt={"schema":"A_MOMENTUM_RECEIPT","engine_version":ENGINE_VERSION,"engine_commit_sha":a.engine_commit_sha,"generated_at":generated_at,"as_of":latest,"observation_set_count":len(sets),
      "observation_count":len(observations),"temporal_evidence_summary":temporal_summary,"entities":entities,"fallback_pool_status":{"count":pool["count"],"minimum_pool_target":pool["minimum_pool_target"],"status":"PASS"},"result":"PASS_BENCHMARK"}
    if watchlist: receipt["measurement_identity_summary"]=build_measurement_identity_summary(entities,watchlist)
    payload=json.dumps(receipt,indent=2,sort_keys=True)+"\n"
    if a.out=="-": print(payload,end="")
    else: Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(payload,encoding="utf-8")
if __name__=="__main__": main()
