#!/usr/bin/env python3
import argparse, glob, json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ENGINE_VERSION="0.1.3"
STRONG_COMMERCE={"AMAZON","ETSY"}

def dt(s):
    return datetime.fromisoformat(s.replace("Z","+00:00"))

def elapsed_hours(a,b):
    return max((dt(b)-dt(a)).total_seconds()/3600.0,1e-9)

def interval_velocity(p0,p1):
    v0=float(p0["value"]); v1=float(p1["value"]); h=elapsed_hours(p0["t"],p1["t"])
    return (v1-v0)/h, None if v0==0 else ((v1-v0)/abs(v0))/h

def analyze_series(points):
    pts=sorted(points,key=lambda x:dt(x["t"]))
    out={"timepoints":len(pts),"velocity":None,"normalized_velocity":None,"acceleration":None,"series_state":"MOMENTUM_UNPROVEN"}
    if len(pts)<2:
        return out
    values=[float(p["value"]) for p in pts]
    # A zero-only normalized trend series means the provider has insufficient
    # measurable interest for this proxy. It is not evidence of decline.
    if all(abs(v)<1e-12 for v in values):
        return out
    v,n=interval_velocity(pts[-2],pts[-1]); out["velocity"]=v; out["normalized_velocity"]=n
    if len(pts)==2:
        if v>0:
            out["series_state"]="POSITIVE_VELOCITY"
        elif v<0:
            out["series_state"]="DECELERATING"
        else:
            out["series_state"]="STABLE" if values[-1]>0 else "MOMENTUM_UNPROVEN"
        return out
    _,n0=interval_velocity(pts[-3],pts[-2]); v1,n1=interval_velocity(pts[-2],pts[-1])
    if n0 is not None and n1 is not None:
        out["acceleration"]=n1-n0
        if v1>0 and out["acceleration"]>0:
            out["series_state"]="POSITIVE_ACCELERATION"
        elif v1>0:
            out["series_state"]="POSITIVE_VELOCITY"
        elif v1<0:
            out["series_state"]="DECELERATING"
        else:
            out["series_state"]="STABLE" if values[-1]>0 else "MOMENTUM_UNPROVEN"
    else:
        if v1>0:
            out["series_state"]="POSITIVE_VELOCITY"
        elif v1<0:
            out["series_state"]="DECELERATING"
        else:
            out["series_state"]="STABLE" if values[-1]>0 else "MOMENTUM_UNPROVEN"
    return out

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def validate_observation(o):
    for k in ["observation_id","observed_at","entity_type","entity_key","surface","proxy","points","provenance"]:
        if k not in o: raise ValueError(f"observation missing {k}")
    if not o["points"]: raise ValueError("empty points")
    if not o["provenance"].get("machine_observed",False): raise ValueError("machine_observed must be true")
    for p in o["points"]: dt(p["t"]); float(p["value"])

def load_sets(base_path, observation_glob):
    sets=[load(base_path)]
    for p in sorted(glob.glob(observation_glob)):
        sets.append(load(p))
    return sets

def merge_points(observations):
    groups=defaultdict(dict)
    metadata={}
    breakout=defaultdict(list)
    candidate_keys=defaultdict(set)
    for o in observations:
        validate_observation(o)
        k=(o["entity_type"],o["entity_key"],o["surface"],o["proxy"])
        metadata[k]={"entity_type":o["entity_type"],"entity_key":o["entity_key"],"surface":o["surface"],"proxy":o["proxy"]}
        if o.get("candidate_key"): candidate_keys[o["entity_key"]].add(o["candidate_key"])
        if o.get("breakout_proxy"): breakout[o["entity_key"]].append(o["breakout_proxy"])
        for p in o["points"]:
            t=p["t"]; value=float(p["value"])
            if t in groups[k] and groups[k][t] != value:
                raise ValueError(f"same-proxy timestamp discordance {k} {t}: {groups[k][t]} != {value}")
            groups[k][t]=value
    series=[]
    for k,by_t in groups.items():
        pts=[{"t":t,"value":v} for t,v in by_t.items()]
        a=analyze_series(pts)
        series.append({**metadata[k],**a,"points":sorted(pts,key=lambda x:dt(x["t"]))})
    return series,breakout,candidate_keys

def aggregate_entities(series,breakout,candidate_keys):
    by_entity=defaultdict(list)
    for s in series: by_entity[s["entity_key"]].append(s)
    result=[]
    for entity_key,ss in sorted(by_entity.items()):
        accel=[s for s in ss if s["series_state"]=="POSITIVE_ACCELERATION"]
        pos=[s for s in ss if s["series_state"] in {"POSITIVE_ACCELERATION","POSITIVE_VELOCITY"}]
        stable=[s for s in ss if s["series_state"]=="STABLE"]
        decel=[s for s in ss if s["series_state"]=="DECELERATING"]
        accel_surfaces={s["surface"] for s in accel}
        strong_accel=any(s["surface"] in STRONG_COMMERCE for s in accel)
        breakout_high=any(
            b.get("cohort_percentile",0)>=90 and b.get("object_age_hours",10**9)<=72 and b.get("independent_proliferation_count",0)>=2
            for b in breakout.get(entity_key,[])
        )
        if strong_accel or len(accel_surfaces)>=2:
            state="ACCELERATING_CONFIRMED"
        elif pos:
            state="VELOCITY_POSITIVE_ACCELERATION_UNPROVEN"
        elif stable and not decel:
            state="MATURE_STABLE_DEMAND"
        elif breakout_high:
            state="BREAKOUT_PROXY_HIGH"
        elif decel:
            state="DECELERATING"
        else:
            state="MOMENTUM_UNPROVEN"
        result.append({
            "entity_key":entity_key,
            "candidate_keys":sorted(candidate_keys.get(entity_key,set())),
            "state":state,
            "series":ss,
            "independent_accelerating_surfaces":sorted(accel_surfaces),
            "strong_commerce_acceleration":strong_accel,
            "breakout_proxy_high":breakout_high
        })
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--observations",default="examples/demo-observations.json")
    ap.add_argument("--observations-glob",default="examples/observations/*.json")
    ap.add_argument("--pool",default="examples/demo-quality-pool.json")
    ap.add_argument("--out",default="-")
    a=ap.parse_args()
    sets=load_sets(a.observations,a.observations_glob)
    observations=[o for s in sets for o in s.get("observations",[])]
    pool=load(a.pool)
    if pool.get("count")!=len(pool.get("entries",[])): raise SystemExit("pool count mismatch")
    if pool.get("count",0)<pool.get("minimum_pool_target",14): raise SystemExit("commercial fallback pool below minimum target")
    series,breakout,candidate_keys=merge_points(observations)
    entities=aggregate_entities(series,breakout,candidate_keys)
    latest=max((p["t"] for s in series for p in s["points"]),default=sets[0]["as_of"])
    receipt={
      "schema":"A_MOMENTUM_RECEIPT",
      "engine_version":ENGINE_VERSION,
      "as_of":latest,
      "observation_set_count":len(sets),
      "observation_count":len(observations),
      "entities":entities,
      "fallback_pool_status":{"count":pool["count"],"minimum_pool_target":pool["minimum_pool_target"],"status":"PASS"},
      "result":"PASS_BENCHMARK"
    }
    payload=json.dumps(receipt,indent=2,sort_keys=True)+"\n"
    if a.out=="-": print(payload,end="")
    else:
        Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(payload,encoding="utf-8")
if __name__=="__main__": main()
