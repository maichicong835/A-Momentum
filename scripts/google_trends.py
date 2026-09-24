#!/usr/bin/env python3
"""Public Google Trends native-history sensor. No credential is used."""
import argparse, json, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
ENGINE_VERSION="0.2.0"

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def load_if_exists(path):
    p=Path(path) if path else None
    return load(p) if p and p.exists() else None
def parse_iso(s): return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(timezone.utc)
def iso_utc(ts):
    if getattr(ts,"tzinfo",None) is None: ts=ts.tz_localize("UTC")
    else: ts=ts.tz_convert("UTC")
    return ts.isoformat()

def completed_24h_blocks(rows,max_blocks=7):
    if not rows: return []
    rows=sorted(rows,key=lambda x:x[0]); tail=[rows[-1]]
    for cur in reversed(rows[:-1]):
        delta=tail[0][0]-cur[0]
        if timedelta(minutes=50) <= delta <= timedelta(minutes=70): tail.insert(0,cur)
        else: break
    nblocks=min(max_blocks,len(tail)//24)
    if nblocks<3: return []
    tail=tail[-nblocks*24:]; out=[]
    for i in range(nblocks):
        block=tail[i*24:(i+1)*24]; vals=[float(v) for _,v in block]
        out.append({"t":block[-1][0].isoformat(),"value":round(sum(vals)/24.0,6),
                    "window_start":block[0][0].isoformat(),"window_end":block[-1][0].isoformat(),"sample_count":24})
    return out

def latest_success_by_entity(observations):
    latest={}
    for o in observations:
        key=o.get("entity_key"); observed=o.get("observed_at")
        if not key or not observed: continue
        if key not in latest or parse_iso(observed)>parse_iso(latest[key]["observed_at"]):
            latest[key]=o
    return latest

def merge_last_good(history_observations,current_observations):
    latest=latest_success_by_entity(history_observations)
    for key,o in latest_success_by_entity(current_observations).items():
        if key not in latest or parse_iso(o["observed_at"])>=parse_iso(latest[key]["observed_at"]):
            latest[key]=o
    return [latest[k] for k in sorted(latest)]

def self_test():
    base=datetime(2026,1,1,tzinfo=timezone.utc)
    rows=[(base+timedelta(hours=i),float(i%17)) for i in range(72)]
    b=completed_24h_blocks(rows); assert len(b)==3 and all(x["sample_count"]==24 for x in b)
    assert completed_24h_blocks(rows[:20]+rows[21:])==[]
    old={"entity_key":"x","observed_at":"2026-01-01T00:00:00+00:00"}
    new={"entity_key":"x","observed_at":"2026-01-02T00:00:00+00:00"}
    assert merge_last_good([old],[])[0]["observed_at"]==old["observed_at"]
    assert merge_last_good([old],[new])[0]["observed_at"]==new["observed_at"]
    print("AMOMENTUM_GOOGLE_24H_AGGREGATION_SELF_TEST_PASS")
    print("AMOMENTUM_OBSERVATION_CONTINUITY_SELF_TEST_PASS")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--due-plan"); ap.add_argument("--out"); ap.add_argument("--status-out")
    ap.add_argument("--previous"); ap.add_argument("--continuity-seed")
    ap.add_argument("--timeframe",default="now 7-d"); ap.add_argument("--geo",default="US")
    ap.add_argument("--max-queries",type=int,default=15); ap.add_argument("--sleep-seconds",type=float,default=1.0)
    ap.add_argument("--self-test",action="store_true"); a=ap.parse_args()
    if a.self_test: self_test(); return
    if not a.due_plan or not a.out or not a.status_out: raise SystemExit("--due-plan --out --status-out required")
    plan=load(a.due_plan); selected=plan.get("due",[])[:max(0,a.max_queries)]
    history=[]
    for path in [a.continuity_seed,a.previous]:
        s=load_if_exists(path)
        if s: history.extend(s.get("observations",[]))
    history_latest=latest_success_by_entity(history)
    observations=[]; gaps=[]; attempts=[]
    try:
        from pytrends.request import TrendReq
    except Exception as e:
        gaps.append({"scope":"COLLECTOR_IMPORT","state":"SENSOR_GAP_PROVIDER_RUNTIME","error_class":type(e).__name__}); selected=[]
    for idx,item in enumerate(selected,1):
        queries=item.get("query_family") or []; query=str(queries[0]).strip() if queries else ""
        attempted_at=plan.get("as_of")
        if not query:
            gaps.append({"watch_id":item.get("watch_id"),"mechanism_key":item.get("mechanism_key"),"surface":"GOOGLE_TRENDS",
                         "state":"SENSOR_GAP_NO_QUERY_FAMILY","error_class":"NO_QUERY_FAMILY"})
            attempts.append({"watch_id":item.get("watch_id"),"entity_key":item.get("mechanism_key"),
                             "attempted_at":attempted_at,"result":"SENSOR_GAP","error_class":"NO_QUERY_FAMILY"})
            continue
        success=False; last_error=None; successful_observation=None
        for attempt in range(2):
            try:
                py=TrendReq(hl="en-US",tz=0,timeout=(10,25),retries=0,backoff_factor=0)
                py.build_payload([query],cat=0,timeframe=a.timeframe,geo=a.geo,gprop="")
                df=py.interest_over_time()
                if df is None or df.empty or query not in df.columns: raise RuntimeError("EMPTY_NATIVE_SERIES")
                if "isPartial" in df.columns: df=df[df["isPartial"]==False]
                rows=[(parse_iso(iso_utc(t)),float(v)) for t,v in df[query].items()]
                blocks=completed_24h_blocks(rows,max_blocks=7)
                if len(blocks)<3: raise RuntimeError("COMPLETED_24H_BLOCKS_LT_3")
                token=blocks[0]["window_start"]+"__"+blocks[-1]["window_end"]
                successful_observation={
                  "observation_id":f"google-trends-24h-{item['watch_id']}-{idx:02d}",
                  "observed_at":blocks[-1]["t"],"entity_type":"MECHANISM","entity_key":item["mechanism_key"],
                  "surface":"GOOGLE_TRENDS","proxy":f"INTEREST_24H_MEAN_NATIVE_WINDOW::{token}",
                  "points":[{"t":x["t"],"value":x["value"]} for x in blocks],
                  "native_series":True,"supporting_only":False,
                  "provenance":{"source_ref":"GOOGLE_TRENDS_NATIVE_HISTORY_PUBLIC_RUNTIME","machine_observed":True,
                                "note":f"geo={a.geo}; timeframe={a.timeframe}; completed non-overlapping 24h means; query={query}"}}
                observations.append(successful_observation)
                attempts.append({"watch_id":item.get("watch_id"),"entity_key":item.get("mechanism_key"),
                                 "attempted_at":attempted_at,"result":"SUCCESS",
                                 "observed_at":successful_observation["observed_at"]})
                success=True; break
            except Exception as e:
                last_error=type(e).__name__
                if attempt==0: time.sleep(max(a.sleep_seconds,0.2))
        if not success:
            gaps.append({"watch_id":item.get("watch_id"),"mechanism_key":item.get("mechanism_key"),"surface":"GOOGLE_TRENDS",
                         "state":"SENSOR_GAP_PROVIDER_OR_SHAPE_FAILURE_NOT_ZERO_DEMAND","error_class":last_error})
            attempts.append({"watch_id":item.get("watch_id"),"entity_key":item.get("mechanism_key"),
                             "attempted_at":attempted_at,"result":"SENSOR_GAP","error_class":last_error})
        time.sleep(max(a.sleep_seconds,0.0))
    merged=merge_last_good(history,observations)
    current_success_keys={o["entity_key"] for o in observations}
    gap_keys={g.get("mechanism_key") for g in gaps if g.get("mechanism_key")}
    not_due=plan.get("not_due",[])
    out={"schema":"A_MOMENTUM_OBSERVATION_SET","engine_version":ENGINE_VERSION,"as_of":plan.get("as_of"),
         "source":"GOOGLE_TRENDS_NATIVE_HISTORY_PUBLIC_RUNTIME_24H_MEAN",
         "observations":merged,"current_attempts":attempts,
         "not_due":[{"watch_id":x.get("watch_id"),"entity_key":x.get("mechanism_key"),
                     "last_observed_at":x.get("last_observed_at")} for x in not_due],
         "sensor_gaps":gaps,
         "continuity":{
           "policy":"LAST_GOOD_PER_MECHANISM_WITH_ATTEMPT_TRUTH",
           "history_success_count_before":len(history_latest),
           "current_success_count":len(observations),
           "current_gap_count":len(gaps),
           "preserved_not_due_count":sum(1 for x in not_due if x.get("mechanism_key") in history_latest and x.get("mechanism_key") not in current_success_keys),
           "preserved_gap_count":sum(1 for k in gap_keys if k in history_latest and k not in current_success_keys),
           "merged_last_good_count":len(merged),
           "sensor_gap_advances_freshness":False,
           "not_due_advances_freshness":False
         }}
    status={"schema":"A_MOMENTUM_SENSOR_STATUS","surface":"GOOGLE_TRENDS","engine_version":ENGINE_VERSION,
            "as_of":plan.get("as_of"),"due_count":len(selected),"success_count":len(observations),"gap_count":len(gaps),
            "aggregation":"NON_OVERLAPPING_COMPLETED_24H_MEAN","minimum_blocks":3,
            "provider_failure_is_zero_demand":False,"credentials_used":False,
            "result":"PASS_WITH_DATA" if observations else "SENSOR_GAP_FALLBACK_REQUIRED"}
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    Path(a.status_out).write_text(json.dumps(status,indent=2)+"\n",encoding="utf-8")
    print("AMOMENTUM_GOOGLE_TRENDS_SUCCESS_COUNT",len(observations))
    print("AMOMENTUM_GOOGLE_TRENDS_GAP_COUNT",len(gaps))
    print("AMOMENTUM_GOOGLE_TRENDS_MERGED_LAST_GOOD_COUNT",len(merged))
    print("AMOMENTUM_GOOGLE_TRENDS_RESULT",status["result"])
if __name__=="__main__": main()
