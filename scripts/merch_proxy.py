#!/usr/bin/env python3
"""Shadow-only Google Trends merch-proxy collector.

Transport policy: build one batched Google Trends payload for the fixed merch
seed family, then fetch each Related Queries widget independently. This reduces
request bursts, preserves partial success, and opens a circuit on HTTP 429
instead of retry-storming the same egress. Provider failure is never interpreted
as zero demand or as no rising queries.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ENGINE_VERSION="0.2.0"
DEFAULT_SEEDS=["shirt","shirts","t shirt"]
TRANSPORT_STRATEGY="BATCH_PAYLOAD_SHARED_COOKIE_PER_WIDGET_PARTIAL_PRESERVATION"

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def normalize_seeds(raw):
    out=[]
    for x in raw:
        q=" ".join(str(x).split()).strip()
        if q and q not in out:
            out.append(q)
    return out

def normalize_value(value):
    if isinstance(value,(int,float)):
        return {"raw":value,"numeric":float(value),"breakout":False}
    s=str(value).strip()
    if s.casefold()=="breakout":
        return {"raw":"Breakout","numeric":None,"breakout":True}
    try:
        return {"raw":s,"numeric":float(s),"breakout":False}
    except Exception:
        return {"raw":s,"numeric":None,"breakout":False}

def _row(seed,rank,query,value):
    return {
        "merch_wave_id":f"{seed.casefold().replace(' ','-')}-{rank:02d}",
        "source_seed":seed,
        "rank":rank,
        "related_query":query,
        "rising_value":value["raw"],
        "rising_value_numeric":value["numeric"],
        "is_breakout":value["breakout"],
        "role":"MERCH_PROXY_RISING_QUERY"
    }

def rows_from_frame(seed,frame,limit=25):
    if frame is None or getattr(frame,"empty",True):
        return []
    rows=[]
    for idx,(_,r) in enumerate(frame.head(max(1,int(limit))).iterrows(),1):
        query=" ".join(str(r.get("query","")).split()).strip()
        if query:
            rows.append(_row(seed,idx,query,normalize_value(r.get("value"))))
    return rows

def rows_from_response(seed,payload,limit=25):
    ranked=((payload or {}).get("default") or {}).get("rankedList") or []
    rising=ranked[1].get("rankedKeyword") or [] if len(ranked)>=2 else []
    rows=[]
    for idx,item in enumerate(rising[:max(1,int(limit))],1):
        query=" ".join(str(item.get("query","")).split()).strip()
        if query:
            rows.append(_row(seed,idx,query,normalize_value(item.get("value"))))
    return rows

def widget_seed(widget):
    try:
        return widget["request"]["restriction"]["complexKeywordsRestriction"]["keyword"][0]["value"]
    except Exception:
        return None

def is_rate_limit_error(exc):
    if type(exc).__name__=="TooManyRequestsError":
        return True
    response=getattr(exc,"response",None)
    if getattr(response,"status_code",None)==429:
        return True
    return "429" in str(exc)

def classify_transport_health(provider_status,waves,transport):
    if provider_status=="PASS_WITH_DATA" and waves:
        return "RECOVERED_WITH_DATA"
    if provider_status=="PARTIAL_WITH_DATA" and waves:
        return "PARTIAL_WITH_DATA"
    if transport.get("rate_limit_event_count",0)>0 or transport.get("rate_limit_circuit_open") is True:
        return "THROTTLED"
    if provider_status=="PASS_NO_RISING_DATA":
        return "PASS_NO_RISING_DATA"
    if provider_status=="PARTIAL_NO_RISING_DATA":
        return "PARTIAL_NO_RISING_DATA"
    return "OTHER_SENSOR_GAP"

def make_output(seeds,geo,timeframe,seed_results,waves,gaps,transport):
    success_seed_count=sum(1 for x in seed_results if x.get("result")=="SUCCESS")
    if success_seed_count==0:
        provider_status="SENSOR_GAP"
    elif gaps:
        provider_status="PARTIAL_WITH_DATA" if waves else "PARTIAL_NO_RISING_DATA"
    else:
        provider_status="PASS_WITH_DATA" if waves else "PASS_NO_RISING_DATA"
    transport_health_state=classify_transport_health(provider_status,waves,transport)
    downstream_ready=transport_health_state in {"RECOVERED_WITH_DATA","PARTIAL_WITH_DATA"}
    return {
        "schema":"A_MOMENTUM_MERCH_PROXY_SHADOW",
        "schema_version":"1.1",
        "engine_version":ENGINE_VERSION,
        "mode":"SHADOW_ONLY_NO_PRODUCTION_AUTHORITY",
        "captured_at":now_iso(),
        "geo":geo,
        "timeframe":timeframe,
        "seeds":seeds,
        "seed_results":seed_results,
        "merch_waves":waves,
        "merch_wave_count":len(waves),
        "sensor_gaps":gaps,
        "provider_status":provider_status,
        "transport_health_state":transport_health_state,
        "usable_merch_evidence":bool(waves),
        "bridge_experiment_input_ready":downstream_ready,
        "bridge_experiment_input_readiness_role":"TRANSPORT_AND_EVIDENCE_AVAILABILITY_ONLY_NOT_COMMERCIAL_ELIGIBILITY",
        "credentials_used":False,
        "provider_failure_is_zero_demand":False,
        "provider_gap_is_no_rising_queries":False,
        "cross_seed_score_comparison_forbidden":True,
        "partial_success_preserved":True,
        "transport":transport,
        "rising_value_semantics":"PROVIDER_REPORTED_WITHIN_SEED_ONLY_NOT_CROSS_REQUEST_MAGNITUDE"
    }

def collect_once(seeds,timeframe="now 7-d",geo="US",limit=25,build_retries=2,
                 between_seed_seconds=6.0,rate_limit_cooldown_seconds=30.0,
                 client_factory=None,sleep_fn=time.sleep):
    seeds=normalize_seeds(seeds)
    seed_results=[]; waves=[]; gaps=[]
    transport={
        "strategy":TRANSPORT_STRATEGY,
        "batched_seed_payload":True,
        "shared_client_context":True,
        "per_widget_partial_preservation":True,
        "immediate_seed_retry_on_429":False,
        "rate_limit_circuit_breaker":True,
        "batch_build_attempt_count":0,
        "related_query_attempt_count":0,
        "rate_limit_event_count":0,
        "rate_limit_circuit_open":False,
        "between_seed_seconds":float(between_seed_seconds),
        "rate_limit_cooldown_seconds":float(rate_limit_cooldown_seconds),
        "logical_request_plan":"ONE_BATCH_TOKEN_REQUEST_PLUS_UP_TO_ONE_RELATED_QUERY_REQUEST_PER_SEED",
        "unofficial_transport":True
    }
    if client_factory is None:
        try:
            from pytrends.request import TrendReq
            client_factory=lambda: TrendReq(hl="en-US",tz=0,timeout=(10,25),retries=0,backoff_factor=0)
        except Exception as e:
            gaps=[{"scope":"COLLECTOR_IMPORT","result":"SENSOR_GAP","error_class":type(e).__name__}]
            return make_output(seeds,geo,timeframe,seed_results,waves,gaps,transport)

    client=None; build_error=None
    for attempt in range(max(1,int(build_retries))):
        transport["batch_build_attempt_count"]+=1
        try:
            client=client_factory()
            client.build_payload(seeds,cat=0,timeframe=timeframe,geo=geo,gprop="")
            build_error=None
            break
        except Exception as e:
            client=None
            build_error=e
            if is_rate_limit_error(e):
                transport["rate_limit_event_count"]+=1
            if attempt+1<max(1,int(build_retries)):
                sleep_fn(max(float(rate_limit_cooldown_seconds),0.0))
    if client is None:
        error_class=type(build_error).__name__ if build_error else "UNKNOWN_BATCH_BUILD_ERROR"
        state="RATE_LIMITED_BATCH_BUILD" if build_error and is_rate_limit_error(build_error) else "BATCH_BUILD_SENSOR_GAP"
        if state=="RATE_LIMITED_BATCH_BUILD":
            transport["rate_limit_circuit_open"]=True
        for seed in seeds:
            gap={"seed":seed,"result":"SENSOR_GAP","gap_state":state,"error_class":error_class,"attempted_related_query":False}
            gaps.append(gap); seed_results.append(dict(gap))
        return make_output(seeds,geo,timeframe,seed_results,waves,gaps,transport)

    widgets={}
    for widget in getattr(client,"related_queries_widget_list",[]) or []:
        seed=widget_seed(widget)
        if seed and seed not in widgets:
            widgets[seed]=widget

    circuit_open=False
    for idx,seed in enumerate(seeds):
        if circuit_open:
            gap={"seed":seed,"result":"SENSOR_GAP","gap_state":"RATE_LIMIT_CIRCUIT_OPEN","error_class":"TooManyRequestsError","attempted_related_query":False}
            gaps.append(gap); seed_results.append(dict(gap))
            continue
        widget=widgets.get(seed)
        if not widget:
            gap={"seed":seed,"result":"SENSOR_GAP","gap_state":"MISSING_RELATED_QUERY_WIDGET","error_class":"MissingWidget","attempted_related_query":False}
            gaps.append(gap); seed_results.append(dict(gap))
            continue
        payload={"req":json.dumps(widget["request"]),"token":widget["token"],"tz":client.tz}
        transport["related_query_attempt_count"]+=1
        try:
            response=client._get_data(
                url=client.RELATED_QUERIES_URL,
                method=client.GET_METHOD,
                trim_chars=5,
                params=payload
            )
            seed_rows=rows_from_response(seed,response,limit)
            waves.extend(seed_rows)
            seed_results.append({"seed":seed,"result":"SUCCESS","rising_count":len(seed_rows),"attempted_related_query":True})
        except Exception as e:
            if is_rate_limit_error(e):
                transport["rate_limit_event_count"]+=1
                transport["rate_limit_circuit_open"]=True
                circuit_open=True
                gap={"seed":seed,"result":"SENSOR_GAP","gap_state":"RATE_LIMITED_RELATED_QUERY","error_class":type(e).__name__,"attempted_related_query":True}
            else:
                gap={"seed":seed,"result":"SENSOR_GAP","gap_state":"RELATED_QUERY_SENSOR_GAP","error_class":type(e).__name__,"attempted_related_query":True}
            gaps.append(gap); seed_results.append(dict(gap))
        if idx+1<len(seeds) and not circuit_open:
            sleep_fn(max(float(between_seed_seconds),0.0))
    return make_output(seeds,geo,timeframe,seed_results,waves,gaps,transport)

def validate_output(out):
    assert out["schema"]=="A_MOMENTUM_MERCH_PROXY_SHADOW"
    assert out["mode"]=="SHADOW_ONLY_NO_PRODUCTION_AUTHORITY"
    assert out["credentials_used"] is False
    assert out["provider_failure_is_zero_demand"] is False
    assert out["provider_gap_is_no_rising_queries"] is False
    assert out["cross_seed_score_comparison_forbidden"] is True
    assert out["partial_success_preserved"] is True
    assert out["merch_wave_count"]==len(out["merch_waves"])
    assert out["provider_status"] in {"PASS_WITH_DATA","PASS_NO_RISING_DATA","PARTIAL_WITH_DATA","PARTIAL_NO_RISING_DATA","SENSOR_GAP"}
    assert out["transport_health_state"] in {"RECOVERED_WITH_DATA","PARTIAL_WITH_DATA","THROTTLED","PASS_NO_RISING_DATA","PARTIAL_NO_RISING_DATA","OTHER_SENSOR_GAP"}
    assert out["usable_merch_evidence"] is (out["merch_wave_count"]>0)
    assert out["bridge_experiment_input_ready"] is (out["transport_health_state"] in {"RECOVERED_WITH_DATA","PARTIAL_WITH_DATA"})
    assert out["bridge_experiment_input_readiness_role"]=="TRANSPORT_AND_EVIDENCE_AVAILABILITY_ONLY_NOT_COMMERCIAL_ELIGIBILITY"
    t=out["transport"]
    assert t["strategy"]==TRANSPORT_STRATEGY
    assert t["batched_seed_payload"] is True
    assert t["shared_client_context"] is True
    assert t["per_widget_partial_preservation"] is True
    assert t["immediate_seed_retry_on_429"] is False
    assert t["rate_limit_circuit_breaker"] is True
    for row in out["merch_waves"]:
        assert row["role"]=="MERCH_PROXY_RISING_QUERY"
        assert row["source_seed"] in out["seeds"]
        assert row["rank"]>=1
    return True

def self_test():
    class FakeClient:
        RELATED_QUERIES_URL="RELATED"; GET_METHOD="get"; tz=0
        def __init__(self,rate_limit_seed=None):
            self.rate_limit_seed=rate_limit_seed; self.related_queries_widget_list=[]; self.build_calls=0
        def build_payload(self,seeds,cat,timeframe,geo,gprop):
            self.build_calls+=1
            self.related_queries_widget_list=[
                {"request":{"restriction":{"complexKeywordsRestriction":{"keyword":[{"value":s}]}}},"token":"t-"+s}
                for s in seeds
            ]
        def _get_data(self,url,method,trim_chars,params):
            seed=json.loads(params["req"])["restriction"]["complexKeywordsRestriction"]["keyword"][0]["value"]
            if seed==self.rate_limit_seed:
                class TooManyRequestsError(Exception): pass
                raise TooManyRequestsError("429")
            return {"default":{"rankedList":[{"rankedKeyword":[]},{"rankedKeyword":[{"query":seed+" alpha","value":"Breakout"}]}]}}
    c=FakeClient()
    out=collect_once(["shirt","shirts","t shirt"],client_factory=lambda:c,build_retries=1,between_seed_seconds=0,rate_limit_cooldown_seconds=0,sleep_fn=lambda _:None)
    assert validate_output(out) and c.build_calls==1
    assert out["transport_health_state"]=="RECOVERED_WITH_DATA"
    assert out["bridge_experiment_input_ready"] is True
    c2=FakeClient("shirts")
    out2=collect_once(["shirt","shirts","t shirt"],client_factory=lambda:c2,build_retries=1,between_seed_seconds=0,rate_limit_cooldown_seconds=0,sleep_fn=lambda _:None)
    assert out2["provider_status"]=="PARTIAL_WITH_DATA"
    assert out2["transport_health_state"]=="PARTIAL_WITH_DATA"
    assert out2["bridge_experiment_input_ready"] is True
    assert out2["transport"]["related_query_attempt_count"]==2
    assert out2["seed_results"][2]["gap_state"]=="RATE_LIMIT_CIRCUIT_OPEN"
    print("A_MOMENTUM_MERCH_PROXY_SELF_TEST_PASS",out["merch_wave_count"],out2["provider_status"])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seeds",default="shirt|shirts|t shirt")
    ap.add_argument("--timeframe",default="now 7-d")
    ap.add_argument("--geo",default="US")
    ap.add_argument("--limit",type=int,default=25)
    ap.add_argument("--build-retries",type=int,default=2)
    ap.add_argument("--between-seed-seconds",type=float,default=6.0)
    ap.add_argument("--rate-limit-cooldown-seconds",type=float,default=30.0)
    ap.add_argument("--out")
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        self_test(); return
    if not a.out:
        raise SystemExit("--out required")
    out=collect_once(a.seeds.split("|"),a.timeframe,a.geo,a.limit,a.build_retries,a.between_seed_seconds,a.rate_limit_cooldown_seconds)
    validate_output(out)
    Path(a.out).write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("A_MOMENTUM_MERCH_PROXY_STATUS",out["provider_status"])
    print("A_MOMENTUM_MERCH_PROXY_WAVE_COUNT",out["merch_wave_count"])
    print("A_MOMENTUM_MERCH_PROXY_GAP_COUNT",len(out["sensor_gaps"]))
    print("A_MOMENTUM_MERCH_PROXY_TRANSPORT",json.dumps(out["transport"],sort_keys=True))

if __name__=="__main__":
    main()
