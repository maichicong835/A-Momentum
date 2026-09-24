#!/usr/bin/env python3
import argparse, glob, json
from datetime import datetime, timezone
from pathlib import Path
ENGINE_VERSION="0.2.0"

def parse_dt(s): return datetime.fromisoformat(s.replace("Z","+00:00"))
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--watchlist",required=True); ap.add_argument("--bootstrap",required=True)
    ap.add_argument("--continuity-seed")
    ap.add_argument("--observations-glob",default="runtime/latest/google-trends-observations.json")
    ap.add_argument("--now"); ap.add_argument("--out",required=True); a=ap.parse_args()
    now=parse_dt(a.now) if a.now else datetime.now(timezone.utc)
    wset=load(a.watchlist); sets=[load(a.bootstrap)]
    if a.continuity_seed and Path(a.continuity_seed).exists(): sets.append(load(a.continuity_seed))
    for p in sorted(glob.glob(a.observations_glob)): sets.append(load(p))
    latest={}
    for s in sets:
        for o in s.get("observations",[]):
            key=o.get("entity_key")
            for point in o.get("points",[]):
                t=parse_dt(point["t"])
                if key and (key not in latest or t>latest[key]): latest[key]=t
    due=[]; not_due=[]
    for w in wset.get("entries",[]):
        key=w["mechanism_key"]; cadence=float(w["cadence_hours"]); last=latest.get(key)
        elapsed=None if last is None else (now-last).total_seconds()/3600.0
        rec={"watch_id":w["watch_id"],"mechanism_key":key,"cadence_class":w["cadence_class"],
             "cadence_hours":cadence,"last_observed_at":None if last is None else last.isoformat(),
             "elapsed_hours":elapsed,"query_family":w["query_family"],"preferred_surfaces":w["preferred_surfaces"]}
        (due if last is None or elapsed>=cadence else not_due).append(rec)
    out={"schema":"A_MOMENTUM_DUE_PLAN","engine_version":ENGINE_VERSION,"as_of":now.isoformat(),
         "watch_count":len(wset.get("entries",[])),"due_count":len(due),"not_due_count":len(not_due),
         "due":due,"not_due":not_due,"continuity_seed_used":bool(a.continuity_seed and Path(a.continuity_seed).exists()),
         "log_policy":"PUBLIC_RUNTIME_NO_CREDENTIAL_VALUES"}
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print("A_MOMENTUM_DUE_COUNT",len(due)); print("A_MOMENTUM_NOT_DUE_COUNT",len(not_due))
if __name__=="__main__": main()
