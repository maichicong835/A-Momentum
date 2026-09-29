#!/usr/bin/env python3
"""Shadow-only Google Trends merch-proxy collector.

Purpose: observe Rising related queries around a tiny fixed merch seed family
without granting any production, commercial-eligibility, anchor, or watchlist
authority. Provider failure is explicit and never interpreted as zero demand.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ENGINE_VERSION="0.2.0"
DEFAULT_SEEDS=["shirt","shirts","t shirt"]

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

def rows_from_frame(seed,frame,limit=25):
    if frame is None or getattr(frame,"empty",True):
        return []
    rows=[]
    for idx,(_,r) in enumerate(frame.head(max(1,int(limit))).iterrows(),1):
        query=" ".join(str(r.get("query","")).split()).strip()
        if not query:
            continue
        value=normalize_value(r.get("value"))
        rows.append({
            "merch_wave_id":f"{seed.casefold().replace(' ','-')}-{idx:02d}",
            "source_seed":seed,
            "rank":idx,
            "related_query":query,
            "rising_value":value["raw"],
            "rising_value_numeric":value["numeric"],
            "is_breakout":value["breakout"],
            "role":"MERCH_PROXY_RISING_QUERY"
        })
    return rows

def collect(seeds,timeframe="now 7-d",geo="US",limit=25,retries=2,sleep_seconds=2.0,client_factory=None):
    seeds=normalize_seeds(seeds)
    results=[]; gaps=[]; success_seed_count=0
    if client_factory is None:
        try:
            from pytrends.request import TrendReq
            client_factory=lambda: TrendReq(hl="en-US",tz=0,timeout=(10,25),retries=0,backoff_factor=0)
        except Exception as e:
            return {
                "schema":"A_MOMENTUM_MERCH_PROXY_SHADOW",
                "schema_version":"1.0",
                "engine_version":ENGINE_VERSION,
                "mode":"SHADOW_ONLY_NO_PRODUCTION_AUTHORITY",
                "captured_at":now_iso(),
                "geo":geo,
                "timeframe":timeframe,
                "seeds":seeds,
                "seed_results":[],
                "merch_waves":[],
                "sensor_gaps":[{"scope":"COLLECTOR_IMPORT","error_class":type(e).__name__}],
                "provider_status":"SENSOR_GAP",
                "credentials_used":False,
                "provider_failure_is_zero_demand":False,
                "cross_seed_score_comparison_forbidden":True
            }
    for seed in seeds:
        last_error=None; seed_rows=None
        for attempt in range(max(1,int(retries))):
            try:
                py=client_factory()
                py.build_payload([seed],cat=0,timeframe=timeframe,geo=geo,gprop="")
                related=py.related_queries() or {}
                rising=(related.get(seed) or {}).get("rising")
                seed_rows=rows_from_frame(seed,rising,limit)
                success_seed_count+=1
                results.append({"seed":seed,"result":"SUCCESS","rising_count":len(seed_rows)})
                break
            except Exception as e:
                last_error=type(e).__name__
                if attempt+1<max(1,int(retries)):
                    time.sleep(max(float(sleep_seconds),0.2)*(2**attempt))
        if seed_rows is None:
            gaps.append({"seed":seed,"result":"SENSOR_GAP","error_class":last_error})
            results.append({"seed":seed,"result":"SENSOR_GAP","rising_count":0,"error_class":last_error})
        else:
            # Keep every seed result separate; never compare normalized magnitude across seed pulls.
            pass
        if seed_rows:
            for row in seed_rows:
                row["captured_at"]=now_iso()
            gaps_for_seed=False
        time.sleep(max(float(sleep_seconds),0.0))
    waves=[]
    # Re-run only over successful seed records is intentionally avoided; rows are captured in-place below.
    # Build from local successful pulls retained by a second deterministic pass via result cache.
    # The cache lives only in this function and carries no provider state.
    # To keep implementation compact, store rows through an attached private field before finalizing.
    return _collect_with_rows(seeds,timeframe,geo,limit,retries,sleep_seconds,client_factory)

def _collect_with_rows(seeds,timeframe,geo,limit,retries,sleep_seconds,client_factory):
    seed_results=[]; waves=[]; gaps=[]; success_seed_count=0
    for seed in seeds:
        last_error=None; seed_rows=None
        for attempt in range(max(1,int(retries))):
            try:
                py=client_factory()
                py.build_payload([seed],cat=0,timeframe=timeframe,geo=geo,gprop="")
                related=py.related_queries() or {}
                rising=(related.get(seed) or {}).get("rising")
                seed_rows=rows_from_frame(seed,rising,limit)
                success_seed_count+=1
                seed_results.append({"seed":seed,"result":"SUCCESS","rising_count":len(seed_rows)})
                waves.extend(seed_rows)
                break
            except Exception as e:
                last_error=type(e).__name__
                if attempt+1<max(1,int(retries)):
                    time.sleep(max(float(sleep_seconds),0.2)*(2**attempt))
        if seed_rows is None:
            gaps.append({"seed":seed,"result":"SENSOR_GAP","error_class":last_error})
            seed_results.append({"seed":seed,"result":"SENSOR_GAP","rising_count":0,"error_class":last_error})
        time.sleep(max(float(sleep_seconds),0.0))
    if success_seed_count==0:
        provider_status="SENSOR_GAP"
    elif gaps:
        provider_status="PARTIAL_WITH_DATA" if waves else "PARTIAL_NO_RISING_DATA"
    else:
        provider_status="PASS_WITH_DATA" if waves else "PASS_NO_RISING_DATA"
    return {
        "schema":"A_MOMENTUM_MERCH_PROXY_SHADOW",
        "schema_version":"1.0",
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
        "credentials_used":False,
        "provider_failure_is_zero_demand":False,
        "cross_seed_score_comparison_forbidden":True,
        "rising_value_semantics":"PROVIDER_REPORTED_WITHIN_SEED_ONLY_NOT_CROSS_REQUEST_MAGNITUDE"
    }

def collect_once(seeds,timeframe="now 7-d",geo="US",limit=25,retries=2,sleep_seconds=2.0,client_factory=None):
    seeds=normalize_seeds(seeds)
    if client_factory is None:
        try:
            from pytrends.request import TrendReq
            client_factory=lambda: TrendReq(hl="en-US",tz=0,timeout=(10,25),retries=0,backoff_factor=0)
        except Exception as e:
            return {
                "schema":"A_MOMENTUM_MERCH_PROXY_SHADOW","schema_version":"1.0","engine_version":ENGINE_VERSION,
                "mode":"SHADOW_ONLY_NO_PRODUCTION_AUTHORITY","captured_at":now_iso(),"geo":geo,"timeframe":timeframe,
                "seeds":seeds,"seed_results":[],"merch_waves":[],"merch_wave_count":0,
                "sensor_gaps":[{"scope":"COLLECTOR_IMPORT","error_class":type(e).__name__}],
                "provider_status":"SENSOR_GAP","credentials_used":False,
                "provider_failure_is_zero_demand":False,"cross_seed_score_comparison_forbidden":True,
                "rising_value_semantics":"PROVIDER_REPORTED_WITHIN_SEED_ONLY_NOT_CROSS_REQUEST_MAGNITUDE"
            }
    return _collect_with_rows(seeds,timeframe,geo,limit,retries,sleep_seconds,client_factory)

def validate_output(out):
    assert out["schema"]=="A_MOMENTUM_MERCH_PROXY_SHADOW"
    assert out["mode"]=="SHADOW_ONLY_NO_PRODUCTION_AUTHORITY"
    assert out["credentials_used"] is False
    assert out["provider_failure_is_zero_demand"] is False
    assert out["cross_seed_score_comparison_forbidden"] is True
    assert out["merch_wave_count"]==len(out["merch_waves"])
    assert out["provider_status"] in {"PASS_WITH_DATA","PASS_NO_RISING_DATA","PARTIAL_WITH_DATA","PARTIAL_NO_RISING_DATA","SENSOR_GAP"}
    for row in out["merch_waves"]:
        assert row["role"]=="MERCH_PROXY_RISING_QUERY"
        assert row["source_seed"] in out["seeds"]
        assert row["rank"]>=1
    return True

def self_test():
    class FakeFrame:
        empty=False
        def head(self,n): return self
        def iterrows(self):
            return iter([(0,{"query":"Alpha Wave shirt","value":"Breakout"}),(1,{"query":"Beta tee","value":250})])
    rows=rows_from_frame("shirt",FakeFrame(),25)
    assert rows[0]["is_breakout"] is True and rows[0]["rising_value_numeric"] is None
    assert rows[1]["rising_value_numeric"]==250.0
    out={"schema":"A_MOMENTUM_MERCH_PROXY_SHADOW","schema_version":"1.0","engine_version":ENGINE_VERSION,
         "mode":"SHADOW_ONLY_NO_PRODUCTION_AUTHORITY","captured_at":"TEST","geo":"US","timeframe":"now 7-d",
         "seeds":["shirt"],"seed_results":[{"seed":"shirt","result":"SUCCESS","rising_count":2}],
         "merch_waves":rows,"merch_wave_count":2,"sensor_gaps":[],"provider_status":"PASS_WITH_DATA",
         "credentials_used":False,"provider_failure_is_zero_demand":False,"cross_seed_score_comparison_forbidden":True,
         "rising_value_semantics":"PROVIDER_REPORTED_WITHIN_SEED_ONLY_NOT_CROSS_REQUEST_MAGNITUDE"}
    assert validate_output(out)
    print("A_MOMENTUM_MERCH_PROXY_SELF_TEST_PASS",len(rows))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seeds",default="shirt|shirts|t shirt")
    ap.add_argument("--timeframe",default="now 7-d")
    ap.add_argument("--geo",default="US")
    ap.add_argument("--limit",type=int,default=25)
    ap.add_argument("--retries",type=int,default=2)
    ap.add_argument("--sleep-seconds",type=float,default=2.0)
    ap.add_argument("--out")
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        self_test(); return
    if not a.out:
        raise SystemExit("--out required")
    out=collect_once(a.seeds.split("|"),a.timeframe,a.geo,a.limit,a.retries,a.sleep_seconds)
    validate_output(out)
    Path(a.out).write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("A_MOMENTUM_MERCH_PROXY_STATUS",out["provider_status"])
    print("A_MOMENTUM_MERCH_PROXY_WAVE_COUNT",out["merch_wave_count"])
    print("A_MOMENTUM_MERCH_PROXY_GAP_COUNT",len(out["sensor_gaps"]))

if __name__=="__main__":
    main()
