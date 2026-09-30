#!/usr/bin/env python3
"""Independent sticker-native S-wave radar built on the hardened pytrends transport."""
import argparse, json
from pathlib import Path
import merch_proxy as base

ENGINE_VERSION="0.2.0"
DEFAULT_SEEDS=["sticker","stickers","vinyl sticker"]

def collect(seeds,timeframe="now 7-d",geo="US",limit=25,build_retries=2,
            between_seed_seconds=6.0,rate_limit_cooldown_seconds=30.0,
            client_factory=None,sleep_fn=base.time.sleep):
    out=base.collect_once(
        seeds,timeframe,geo,limit,build_retries,
        between_seed_seconds,rate_limit_cooldown_seconds,
        client_factory,sleep_fn
    )
    base.validate_output(out)
    out["schema"]="A_MOMENTUM_STICKER_PROXY_SHADOW"
    out["schema_version"]="1.0"
    out["radar"]="S_STICKER_NATIVE"
    out["radar_role"]="INDEPENDENT_STICKER_NATIVE_DISCOVERY_NOT_M_CONFIRMATION"
    out["source_family"]="GOOGLE_TRENDS_RELATED_QUERIES_RISING"
    out["commercial_eligibility_authority"]=False
    out["m_confirmation_authority"]=False
    out["production_eligible"]=False
    for row in out.get("merch_waves",[]):
        row["role"]="STICKER_NATIVE_RISING_QUERY"
    return out

def validate(out):
    assert out["schema"]=="A_MOMENTUM_STICKER_PROXY_SHADOW"
    assert out["radar"]=="S_STICKER_NATIVE"
    assert out["radar_role"]=="INDEPENDENT_STICKER_NATIVE_DISCOVERY_NOT_M_CONFIRMATION"
    assert out["commercial_eligibility_authority"] is False
    assert out["m_confirmation_authority"] is False
    assert out["production_eligible"] is False
    assert out["credentials_used"] is False
    assert out["provider_failure_is_zero_demand"] is False
    assert out["provider_gap_is_no_rising_queries"] is False
    assert all(x["role"]=="STICKER_NATIVE_RISING_QUERY" for x in out["merch_waves"])
    return True

def self_test():
    class FakeClient:
        RELATED_QUERIES_URL="RELATED"; GET_METHOD="get"; tz=0
        def __init__(self):
            self.related_queries_widget_list=[]
        def build_payload(self,seeds,cat,timeframe,geo,gprop):
            self.related_queries_widget_list=[
              {"request":{"restriction":{"complexKeywordsRestriction":{"keyword":[{"value":s}]}}},"token":"t-"+s}
              for s in seeds
            ]
        def _get_data(self,url,method,trim_chars,params):
            req=json.loads(params["req"])
            seed=req["restriction"]["complexKeywordsRestriction"]["keyword"][0]["value"]
            return {"default":{"rankedList":[{"rankedKeyword":[]},{"rankedKeyword":[{"query":seed+" alpha","value":500}]}]}}
    out=collect(DEFAULT_SEEDS,client_factory=FakeClient,build_retries=1,between_seed_seconds=0,rate_limit_cooldown_seconds=0,sleep_fn=lambda _:None)
    assert validate(out)
    assert out["merch_wave_count"]==3
    print("A_MOMENTUM_STICKER_PROXY_SELF_TEST_PASS",out["merch_wave_count"])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seeds",default="sticker|stickers|vinyl sticker")
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
    out=collect(a.seeds.split("|"),a.timeframe,a.geo,a.limit,a.build_retries,a.between_seed_seconds,a.rate_limit_cooldown_seconds)
    validate(out)
    Path(a.out).write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("A_MOMENTUM_STICKER_PROXY_STATUS",out["provider_status"])
    print("A_MOMENTUM_STICKER_PROXY_WAVE_COUNT",out["merch_wave_count"])
    print("A_MOMENTUM_STICKER_PROXY_TRANSPORT",json.dumps(out["transport"],sort_keys=True))

if __name__=="__main__":
    main()
