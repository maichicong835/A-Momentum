#!/usr/bin/env python3
import argparse, json, math
from datetime import datetime
from pathlib import Path

ENGINE_VERSION = "0.1.0"

def dt(s):
    return datetime.fromisoformat(s.replace("Z","+00:00"))

def hours(a,b):
    return max((dt(b)-dt(a)).total_seconds()/3600.0, 1e-9)

def interval_velocity(p0,p1):
    v0=float(p0["value"]); v1=float(p1["value"])
    h=hours(p0["t"],p1["t"])
    absolute=(v1-v0)/h
    normalized=None if v0==0 else ((v1-v0)/abs(v0))/h
    return absolute, normalized

def analyze_points(points):
    pts=sorted(points,key=lambda x:dt(x["t"]))
    out={"timepoints":len(pts),"velocity":None,"normalized_velocity":None,"acceleration":None,"state":"MOMENTUM_UNPROVEN"}
    if len(pts)<2:
        return out
    a,n=interval_velocity(pts[-2],pts[-1])
    out["velocity"]=a; out["normalized_velocity"]=n
    if len(pts)==2:
        out["state"]="VELOCITY_POSITIVE_ACCELERATION_UNPROVEN" if a>0 else ("DECELERATING" if a<0 else "MATURE_STABLE_DEMAND")
        return out
    a0,n0=interval_velocity(pts[-3],pts[-2])
    a1,n1=interval_velocity(pts[-2],pts[-1])
    if n0 is not None and n1 is not None:
        out["acceleration"]=n1-n0
        if a1>0 and out["acceleration"]>0:
            out["state"]="ACCELERATING_CANDIDATE"
        elif abs(a1)<1e-12:
            out["state"]="MATURE_STABLE_DEMAND"
        else:
            out["state"]="DECELERATING"
    else:
        out["state"]="VELOCITY_POSITIVE_ACCELERATION_UNPROVEN" if a1>0 else "DECELERATING"
    return out

def load_json(path):
    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)

def validate_observation(o):
    required=["observation_id","observed_at","entity_type","entity_key","surface","proxy","points","provenance"]
    missing=[k for k in required if k not in o]
    if missing: raise ValueError(f"observation missing {missing}")
    if not o["points"]: raise ValueError("observation points empty")
    if not o["provenance"].get("machine_observed",False):
        raise ValueError("machine_observed must be true for benchmark authority")
    for p in o["points"]:
        dt(p["t"]); float(p["value"])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--observations",default="data/bootstrap-observations.json")
    ap.add_argument("--pool",default="data/commercial-quality-pool.json")
    ap.add_argument("--out",default="-")
    args=ap.parse_args()

    obsset=load_json(args.observations)
    pool=load_json(args.pool)
    observations=obsset.get("observations",[])
    if pool.get("count") != len(pool.get("entries",[])):
        raise SystemExit("pool count mismatch")
    if pool.get("count",0) < pool.get("minimum_pool_target",14):
        raise SystemExit("commercial fallback pool below minimum target")

    entities=[]
    for o in observations:
        validate_observation(o)
        a=analyze_points(o["points"])
        if a["timepoints"]<3 and a["state"]=="ACCELERATING_CANDIDATE":
            raise SystemExit("invalid acceleration claim")
        entities.append({
            "observation_id":o["observation_id"],
            "candidate_key":o.get("candidate_key"),
            "entity_type":o["entity_type"],
            "entity_key":o["entity_key"],
            "surface":o["surface"],
            "proxy":o["proxy"],
            "state":a["state"],
            "timepoints":a["timepoints"],
            "velocity":a["velocity"],
            "normalized_velocity":a["normalized_velocity"],
            "acceleration":a["acceleration"],
            "source_ref":o["provenance"]["source_ref"]
        })

    receipt={
        "schema":"A_MOMENTUM_RECEIPT",
        "engine_version":ENGINE_VERSION,
        "as_of":obsset["as_of"],
        "entities":entities,
        "fallback_pool_status":{
            "count":pool["count"],
            "minimum_pool_target":pool["minimum_pool_target"],
            "status":"PASS" if pool["count"]>=pool["minimum_pool_target"] else "FAIL"
        },
        "result":"PASS_BOOTSTRAP_BENCHMARK"
    }
    payload=json.dumps(receipt,indent=2,sort_keys=True)+"\n"
    if args.out=="-":
        print(payload,end="")
    else:
        Path(args.out).parent.mkdir(parents=True,exist_ok=True)
        Path(args.out).write_text(payload,encoding="utf-8")

if __name__=="__main__":
    main()
