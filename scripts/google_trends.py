#!/usr/bin/env python3
"""Public Google Trends native-history sensor. No credential is used."""
import argparse, json, re, time
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
def _key(text,upper=False):
    parts=re.findall(r"[a-z0-9]+",str(text or "").casefold()); out="_".join(parts) or "empty"
    return out.upper() if upper else out
def stable_query_proxy_id(query,geo="US",timeframe="now 7-d"): return f"GT_{_key(geo,True)}_WEB_{_key(timeframe,True)}::{_key(query)}"
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
        out.append({"t":block[-1][0].isoformat(),"value":round(sum(vals)/24.0,6),"window_start":block[0][0].isoformat(),"window_end":block[-1][0].isoformat(),"sample_count":24})
    return out
def latest_success_by_entity(observations):
    latest={}
    for o in observations:
        key=o.get("entity_key"); observed=o.get("observed_at")
        if key and observed and (key not in latest or parse_iso(observed)>parse_iso(latest[key]["observed_at"])): latest[key]=o
    return latest
def merge_last_good(history_observations,current_observations):
    latest=latest_success_by_entity(history_observations)
    for key,o in latest_success_by_entity(current_observations).items():
        if key not in latest or parse_iso(o["observed_at"])>=parse_iso(latest[key]["observed_at"]): latest[key]=o
    return [latest[k] for k in sorted(latest)]
def query_candidates(item,max_variants=3):
    out=[]
    for raw in item.get("query_family") or []:
        q=str(raw).strip()
        if q and q not in out: out.append(q)
        if len(out)>=max(1,int(max_variants)): break
    return out
def query_specs(item,max_variants=3,geo="US",timeframe="now 7-d"):
    queries=query_candidates(item,max_variants)
    if not queries: return []
    mi=item.get("measurement_identity") or {}; anchor=mi.get("anchor_query"); anchor_pid=mi.get("anchor_proxy_id")
    if not anchor or anchor!=queries[0]: raise ValueError("ANCHOR_QUERY_MUST_EQUAL_FIRST_QUERY")
    if anchor_pid!=stable_query_proxy_id(anchor,geo,timeframe): raise ValueError("ANCHOR_PROXY_ID_MISMATCH")
    return [{"query":q,"query_ordinal":i,"measurement_basis":"PRIMARY_ANCHOR" if i==1 else "FALLBACK_PROXY",
             "query_proxy_id":anchor_pid if i==1 else stable_query_proxy_id(q,geo,timeframe),
             "anchor_query":anchor,"anchor_proxy_id":anchor_pid} for i,q in enumerate(queries,1)]
def retry_backoff_seconds(attempt_index,base_seconds): return max(float(base_seconds),0.2)*(2**max(0,int(attempt_index)))
def safe_exception_diagnostic(error,stage):
    """Expose only a bounded stage/code; never serialize raw provider error text."""
    owned_shape_errors={
        ("VALIDATE_NATIVE_SERIES","EMPTY_NATIVE_SERIES"):"EMPTY_NATIVE_SERIES",
        ("VALIDATE_COMPLETED_BLOCKS","COMPLETED_24H_BLOCKS_LT_3"):"COMPLETED_24H_BLOCKS_LT_3",
    }
    code=owned_shape_errors.get((stage,str(error))) if type(error) is RuntimeError else None
    return {"error_stage":stage,"error_code":code or "UNCLASSIFIED_PROVIDER_OR_LIBRARY_EXCEPTION"}
def self_test():
    base=datetime(2026,1,1,tzinfo=timezone.utc); rows=[(base+timedelta(hours=i),float(i%17)) for i in range(72)]
    b=completed_24h_blocks(rows); assert len(b)==3 and all(x["sample_count"]==24 for x in b); assert completed_24h_blocks(rows[:20]+rows[21:])==[]
    old={"entity_key":"x","observed_at":"2026-01-01T00:00:00+00:00"}; new={"entity_key":"x","observed_at":"2026-01-02T00:00:00+00:00"}
    assert merge_last_good([old],[])[0]["observed_at"]==old["observed_at"]; assert merge_last_good([old],[new])[0]["observed_at"]==new["observed_at"]
    assert query_candidates({"query_family":["a","a"," b ","c"]},3)==["a","b","c"]
    pid=stable_query_proxy_id("accountant sticker"); item={"query_family":["accountant sticker","spreadsheet sticker"],"measurement_identity":{"anchor_query":"accountant sticker","anchor_proxy_id":pid}}
    specs=query_specs(item,3); assert specs[0]["measurement_basis"]=="PRIMARY_ANCHOR" and specs[0]["query_proxy_id"]==pid
    assert specs[1]["measurement_basis"]=="FALLBACK_PROXY" and specs[1]["query_proxy_id"]!=pid
    assert retry_backoff_seconds(0,3)==3 and retry_backoff_seconds(2,3)==12
    print("AMOMENTUM_GOOGLE_24H_AGGREGATION_SELF_TEST_PASS"); print("AMOMENTUM_OBSERVATION_CONTINUITY_SELF_TEST_PASS")
    print("AMOMENTUM_QUERY_FALLBACK_SELF_TEST_PASS"); print("AMOMENTUM_MEASUREMENT_IDENTITY_SELF_TEST_PASS")
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--due-plan"); ap.add_argument("--out"); ap.add_argument("--status-out")
    ap.add_argument("--previous"); ap.add_argument("--continuity-seed"); ap.add_argument("--timeframe",default="now 7-d"); ap.add_argument("--geo",default="US")
    ap.add_argument("--max-queries",type=int,default=15); ap.add_argument("--max-query-variants",type=int,default=3); ap.add_argument("--retries-per-query",type=int,default=2)
    ap.add_argument("--sleep-seconds",type=float,default=3.0); ap.add_argument("--self-test",action="store_true"); a=ap.parse_args()
    if a.self_test: self_test(); return
    if not a.due_plan or not a.out or not a.status_out: raise SystemExit("--due-plan --out --status-out required")
    plan=load(a.due_plan); selected=plan.get("due",[])[:max(0,a.max_queries)]; history=[]
    for path in [a.continuity_seed,a.previous]:
        s=load_if_exists(path)
        if s: history.extend(s.get("observations",[]))
    history_latest=latest_success_by_entity(history); observations=[]; gaps=[]; attempts=[]; provider_attempt_count=0; fallback_success_count=0
    try: from pytrends.request import TrendReq
    except Exception as e:
        gaps.append({"scope":"COLLECTOR_IMPORT","state":"SENSOR_GAP_PROVIDER_RUNTIME","error_class":type(e).__name__}); selected=[]
    for idx,item in enumerate(selected,1):
        try: specs=query_specs(item,a.max_query_variants,a.geo,a.timeframe); identity_error=None
        except Exception as e: specs=[]; identity_error=type(e).__name__
        attempted_at=plan.get("as_of")
        if not specs:
            err=identity_error or "NO_QUERY_FAMILY"; gaps.append({"watch_id":item.get("watch_id"),"mechanism_key":item.get("mechanism_key"),"surface":"GOOGLE_TRENDS","state":"SENSOR_GAP_NO_QUERY_FAMILY_OR_IDENTITY","error_class":err})
            attempts.append({"watch_id":item.get("watch_id"),"entity_key":item.get("mechanism_key"),"attempted_at":attempted_at,"result":"SENSOR_GAP","error_class":err,"measurement_basis":"ANCHOR_GAP","queries_attempted":[]}); continue
        success=False; last_error=None; last_diagnostic=None; entity_attempt_log=[]
        for spec in specs:
            query=spec["query"]; q_index=spec["query_ordinal"]
            for attempt in range(max(1,a.retries_per_query)):
                provider_attempt_count+=1
                stage="INITIALIZE_CLIENT"
                try:
                    py=TrendReq(hl="en-US",tz=0,timeout=(10,25),retries=0,backoff_factor=0)
                    stage="BUILD_QUERY_PAYLOAD"
                    py.build_payload([query],cat=0,timeframe=a.timeframe,geo=a.geo,gprop="")
                    stage="FETCH_NATIVE_SERIES"
                    df=py.interest_over_time()
                    stage="VALIDATE_NATIVE_SERIES"
                    if df is None or df.empty or query not in df.columns: raise RuntimeError("EMPTY_NATIVE_SERIES")
                    if "isPartial" in df.columns: df=df[df["isPartial"]==False]
                    rows=[(parse_iso(iso_utc(t)),float(v)) for t,v in df[query].items()]
                    stage="VALIDATE_COMPLETED_BLOCKS"
                    blocks=completed_24h_blocks(rows,max_blocks=7)
                    if len(blocks)<3: raise RuntimeError("COMPLETED_24H_BLOCKS_LT_3")
                    o={"observation_id":f"google-trends-24h-{item['watch_id']}-{idx:02d}","observed_at":blocks[-1]["t"],"entity_type":"MECHANISM","entity_key":item["mechanism_key"],
                       "surface":"GOOGLE_TRENDS","proxy":spec["query_proxy_id"],"points":[{"t":x["t"],"value":x["value"]} for x in blocks],"native_series":True,"supporting_only":False,
                       "measurement_identity":{"anchor_query":spec["anchor_query"],"anchor_proxy_id":spec["anchor_proxy_id"],"query_used":query,"query_proxy_id":spec["query_proxy_id"],
                         "signal_basis":spec["measurement_basis"],"native_window":{"window_start":blocks[0]["window_start"],"window_end":blocks[-1]["window_end"]}},
                       "provenance":{"source_ref":"GOOGLE_TRENDS_NATIVE_HISTORY_PUBLIC_RUNTIME","machine_observed":True,"note":f"geo={a.geo}; timeframe={a.timeframe}; completed non-overlapping 24h means; query={query}",
                         "query_used":query,"query_ordinal":q_index,"measurement_basis":spec["measurement_basis"]}}
                    observations.append(o); entity_attempt_log.append({"query":query,"query_ordinal":q_index,"attempt":attempt+1,"result":"SUCCESS"})
                    attempts.append({"watch_id":item.get("watch_id"),"entity_key":item.get("mechanism_key"),"attempted_at":attempted_at,"result":"SUCCESS","observed_at":o["observed_at"],
                      "query_used":query,"query_ordinal":q_index,"measurement_basis":spec["measurement_basis"],"anchor_query":spec["anchor_query"],"anchor_proxy_id":spec["anchor_proxy_id"],
                      "query_proxy_id":spec["query_proxy_id"],"provider_attempts":len(entity_attempt_log)})
                    if q_index>1: fallback_success_count+=1
                    success=True; break
                except Exception as e:
                    last_error=type(e).__name__; last_diagnostic=safe_exception_diagnostic(e,stage)
                    entity_attempt_log.append({"query":query,"query_ordinal":q_index,"attempt":attempt+1,"result":"SENSOR_GAP","error_class":last_error,**last_diagnostic})
                    if attempt+1<max(1,a.retries_per_query): time.sleep(retry_backoff_seconds(attempt,a.sleep_seconds))
            if success: break
            if q_index<len(specs): time.sleep(max(a.sleep_seconds,0.2))
        if not success:
            gaps.append({"watch_id":item.get("watch_id"),"mechanism_key":item.get("mechanism_key"),"surface":"GOOGLE_TRENDS","state":"SENSOR_GAP_PROVIDER_OR_SHAPE_FAILURE_NOT_ZERO_DEMAND",
              "error_class":last_error,**(last_diagnostic or {}),"attempt_diagnostics":[{"query_ordinal":x["query_ordinal"],"attempt":x["attempt"],"error_class":x["error_class"],"error_stage":x["error_stage"],"error_code":x["error_code"]} for x in entity_attempt_log if x["result"]=="SENSOR_GAP"],"measurement_basis":"ANCHOR_GAP","anchor_query":specs[0]["anchor_query"],"anchor_proxy_id":specs[0]["anchor_proxy_id"],
              "queries_attempted":[x["query"] for x in specs],"provider_attempts":len(entity_attempt_log)})
            attempts.append({"watch_id":item.get("watch_id"),"entity_key":item.get("mechanism_key"),"attempted_at":attempted_at,"result":"SENSOR_GAP","error_class":last_error,**(last_diagnostic or {}),
              "measurement_basis":"ANCHOR_GAP","anchor_query":specs[0]["anchor_query"],"anchor_proxy_id":specs[0]["anchor_proxy_id"],"queries_attempted":[x["query"] for x in specs],
              "provider_attempts":len(entity_attempt_log)})
        time.sleep(max(a.sleep_seconds,0.0))
    merged=merge_last_good(history,observations); current_success_keys={o["entity_key"] for o in observations}; gap_keys={g.get("mechanism_key") for g in gaps if g.get("mechanism_key")}; not_due=plan.get("not_due",[])
    out={"schema":"A_MOMENTUM_OBSERVATION_SET","engine_version":ENGINE_VERSION,"as_of":plan.get("as_of"),"source":"GOOGLE_TRENDS_NATIVE_HISTORY_PUBLIC_RUNTIME_24H_MEAN","observations":merged,
      "current_attempts":attempts,"not_due":[{"watch_id":x.get("watch_id"),"entity_key":x.get("mechanism_key"),"last_observed_at":x.get("last_observed_at"),"measurement_identity":x.get("measurement_identity")} for x in not_due],
      "sensor_gaps":gaps,"continuity":{"policy":"LAST_GOOD_PER_MECHANISM_WITH_ATTEMPT_TRUTH","history_success_count_before":len(history_latest),"current_success_count":len(observations),
      "current_gap_count":len(gaps),"provider_attempt_count":provider_attempt_count,"query_fallback_success_count":fallback_success_count,
      "preserved_not_due_count":sum(1 for x in not_due if x.get("mechanism_key") in history_latest and x.get("mechanism_key") not in current_success_keys),
      "preserved_gap_count":sum(1 for k in gap_keys if k in history_latest and k not in current_success_keys),"merged_last_good_count":len(merged),
      "sensor_gap_advances_freshness":False,"not_due_advances_freshness":False,"fallback_success_redefines_anchor_identity":False}}
    success_basis=[x.get("measurement_basis") for x in attempts if x.get("result")=="SUCCESS"]; rate_limit_gap_count=sum(1 for g in gaps if g.get("error_class")=="TooManyRequestsError")
    status={"schema":"A_MOMENTUM_SENSOR_STATUS","surface":"GOOGLE_TRENDS","engine_version":ENGINE_VERSION,"as_of":plan.get("as_of"),"due_count":len(selected),"success_count":len(observations),
      "gap_count":len(gaps),"provider_attempt_count":provider_attempt_count,"query_fallback_success_count":fallback_success_count,
      "primary_anchor_success_count":sum(1 for s in success_basis if s=="PRIMARY_ANCHOR"),"fallback_proxy_success_count":sum(1 for s in success_basis if s=="FALLBACK_PROXY"),
      "anchor_gap_count":sum(1 for x in attempts if x.get("measurement_basis")=="ANCHOR_GAP"),"rate_limit_gap_count":rate_limit_gap_count,
      "query_variant_policy":"TRY_DISTINCT_QUERY_FAMILY_VARIANTS_BEFORE_ENTITY_GAP","measurement_identity_policy":"PRIMARY_ANCHOR_THEN_DISTINCT_FALLBACK_PROXY",
      "aggregation":"NON_OVERLAPPING_COMPLETED_24H_MEAN","minimum_blocks":3,"provider_failure_is_zero_demand":False,"credentials_used":False,
      "result":"PASS_WITH_DATA" if observations else "SENSOR_GAP_FALLBACK_REQUIRED"}
    Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8"); Path(a.status_out).write_text(json.dumps(status,indent=2)+"\n",encoding="utf-8")
    print("AMOMENTUM_GOOGLE_TRENDS_SUCCESS_COUNT",len(observations)); print("AMOMENTUM_GOOGLE_TRENDS_GAP_COUNT",len(gaps)); print("AMOMENTUM_GOOGLE_TRENDS_PROVIDER_ATTEMPT_COUNT",provider_attempt_count)
    print("AMOMENTUM_GOOGLE_TRENDS_QUERY_FALLBACK_SUCCESS_COUNT",fallback_success_count); print("AMOMENTUM_GOOGLE_TRENDS_MERGED_LAST_GOOD_COUNT",len(merged)); print("AMOMENTUM_GOOGLE_TRENDS_RESULT",status["result"])
if __name__=="__main__": main()
