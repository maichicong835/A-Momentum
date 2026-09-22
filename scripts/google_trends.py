#!/usr/bin/env python3
"""Public Google Trends native-history sensor. No credential is used."""
import argparse, json, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
ENGINE_VERSION="0.2.0"
def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
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
def self_test():
    base=datetime(2026,1,1,tzinfo=timezone.utc)
    rows=[(base+timedelta(hours=i),float(i%17)) for i in range(72)]
    b=completed_24h_blocks(rows); assert len(b)==3 and all(x["sample_count"]==24 for x in b)
    assert completed_24h_blocks(rows[:20]+rows[21:])==[]
    print("AMOMENTUM_GOOGLE_24H_AGGREGATION_SELF_TEST_PASS")
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--due-plan"); ap.add_argument("--out"); ap.add_argument("--status-out")
    ap.add_argument("--timeframe",default="now 7-d"); ap.add_argument("--geo",default="US")
    ap.add_argument("--max-queries",type=int,default=15); ap.add_argument("--sleep-seconds",type=float,default=1.0)
    ap.add_argument("--self-test",action="store_true"); a=ap.parse_args()
    if a.self_test: self_test(); return
    if not a.due_plan or not a.out or not a.status_out: raise SystemExit("--due-plan --out --status-out required")
    plan=load(a.due_plan); selected=plan.get("due",[])[:max(0,a.max_queries)]
    observations=[]; gaps=[]
    try: from pytrends.request import TrendReq
    except Exception as e:
        gaps.append({"scope":"COLLECTOR_IMPORT","state":"SENSOR_GAP_PROVIDER_RUNTIME","error_class":type(e).__name__}); selected=[]
    for idx,item in enumerate(selected,1):
        queries=item.get("query_family") or []; query=str(queries[0]).strip() if queries else ""
        if not query:
            gaps.append({"watch_id":item.get("watch_id"),"state":"SENSOR_GAP_NO_QUERY_FAMILY"}); continue
        success=False; last_error=None
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
                observations.append({
                  "observation_id":f"google-trends-24h-{item['watch_id']}-{idx:02d}",
                  "observed_at":blocks[-1]["t"],"entity_type":"MECHANISM","entity_key":item["mechanism_key"],
                  "surface":"GOOGLE_TRENDS","proxy":f"INTEREST_24H_MEAN_NATIVE_WINDOW::{token}",
                  "points":[{"t":x["t"],"value":x["value"]} for x in blocks],
                  "native_series":True,"supporting_only":False,
                  "provenance":{"source_ref":"GOOGLE_TRENDS_NATIVE_HISTORY_PUBLIC_RUNTIME","machine_observed":True,
                                "note":f"geo={a.geo}; timeframe={a.timeframe}; completed non-overlapping 24h means; query={query}"}})
                success=True; break
            except Exception as e:
                last_error=type(e).__name__
                if attempt==0: time.sleep(max(a.sleep_seconds,0.2))
        if not success:
            gaps.append({"watch_id":item.get("watch_id"),"mechanism_key":item.get("mechanism_key"),"surface":"GOOGLE_TRENDS",
                         "state":"SENSOR_GAP_PROVIDER_OR_SHAPE_FAILURE_NOT_ZERO_DEMAND","error_class":last_error})
        time.sleep(max(a.sleep_seconds,0.0))
    out={"schema":"A_MOMENTUM_OBSERVATION_SET","engine_version":ENGINE_VERSION,"as_of":plan.get("as_of"),
         "source":"GOOGLE_TRENDS_NATIVE_HISTORY_PUBLIC_RUNTIME_24H_MEAN","observations":observations,"sensor_gaps":gaps}
    status={"schema":"A_MOMENTUM_SENSOR_STATUS","surface":"GOOGLE_TRENDS","engine_version":ENGINE_VERSION,
            "as_of":plan.get("as_of"),"due_count":len(selected),"success_count":len(observations),"gap_count":len(gaps),
            "aggregation":"NON_OVERLAPPING_COMPLETED_24H_MEAN","minimum_blocks":3,
            "provider_failure_is_zero_demand":False,"credentials_used":False,
            "result":"PASS_WITH_DATA" if observations else "SENSOR_GAP_FALLBACK_REQUIRED"}
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    Path(a.status_out).write_text(json.dumps(status,indent=2)+"\n",encoding="utf-8")
    print("AMOMENTUM_GOOGLE_TRENDS_SUCCESS_COUNT",len(observations))
    print("AMOMENTUM_GOOGLE_TRENDS_GAP_COUNT",len(gaps)); print("AMOMENTUM_GOOGLE_TRENDS_RESULT",status["result"])
if __name__=="__main__": main()
