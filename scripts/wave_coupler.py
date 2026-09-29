#!/usr/bin/env python3
"""Conservative dual-wave coupler for A-Momentum shadow evidence."""
import argparse
import json
import re
from pathlib import Path

ENGINE_VERSION="0.2.0"
MERCH_TOKENS={"shirt","shirts","tshirt","tshirts","tee","tees","graphic"}

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def norm_tokens(text):
    return re.findall(r"[a-z0-9]+",str(text or "").casefold())

def core_merch_tokens(text):
    toks=norm_tokens(text)
    return [t for t in toks if t not in MERCH_TOKENS and t!="t"]

def conservative_match(raw_title,merch_query):
    r=norm_tokens(raw_title)
    m=core_merch_tokens(merch_query)
    if not r or not m:
        return False
    if r==m:
        return True
    # Multi-token containment only. Single-token raw waves require exact equality.
    if len(r)>=2 and len(m)>=2:
        rs=" ".join(r); ms=" ".join(m)
        return rs in ms or ms in rs
    return False

def build(raw,merch):
    raw_waves=raw.get("candidates",[])
    merch_waves=merch.get("merch_waves",[])
    provider_status=merch.get("provider_status","SENSOR_GAP")
    used=set(); couplings=[]
    for rw in raw_waves:
        matches=[]
        for i,mw in enumerate(merch_waves):
            if conservative_match(rw.get("raw_trend_title"),mw.get("related_query")):
                used.add(i)
                matches.append({
                    "source_seed":mw.get("source_seed"),
                    "rank":mw.get("rank"),
                    "related_query":mw.get("related_query"),
                    "rising_value":mw.get("rising_value"),
                    "is_breakout":mw.get("is_breakout",False)
                })
        if matches:
            state="COUPLED_WAVE"
        elif provider_status=="SENSOR_GAP":
            state="UNRESOLVED"
        else:
            state="RAW_ONLY_WAVE"
        couplings.append({
            "wave_id":rw.get("wave_id"),
            "raw_trend_title":rw.get("raw_trend_title"),
            "coupling_state":state,
            "match_policy":"CONSERVATIVE_NORMALIZED_PHRASE_MATCH",
            "merch_matches":matches,
            "commercial_eligibility_decision":None,
            "mechanism_key":None,
            "bridge_queries":[],
            "anchor_query":None,
            "production_eligible":False
        })
    for i,mw in enumerate(merch_waves):
        if i in used:
            continue
        couplings.append({
            "wave_id":None,
            "raw_trend_title":None,
            "coupling_state":"MERCH_NATIVE_WAVE",
            "match_policy":"UNMATCHED_MERCH_RISING_QUERY",
            "merch_matches":[{
                "source_seed":mw.get("source_seed"),
                "rank":mw.get("rank"),
                "related_query":mw.get("related_query"),
                "rising_value":mw.get("rising_value"),
                "is_breakout":mw.get("is_breakout",False)
            }],
            "commercial_eligibility_decision":None,
            "mechanism_key":None,
            "bridge_queries":[],
            "anchor_query":None,
            "production_eligible":False
        })
    summary={k:sum(1 for x in couplings if x["coupling_state"]==k) for k in ["COUPLED_WAVE","MERCH_NATIVE_WAVE","RAW_ONLY_WAVE","UNRESOLVED"]}
    return {
        "schema":"A_MOMENTUM_DUAL_WAVE_SHADOW",
        "schema_version":"1.0",
        "engine_version":ENGINE_VERSION,
        "mode":"SHADOW_ONLY_NO_PRODUCTION_AUTHORITY",
        "raw_wave_capture":raw,
        "merch_proxy_capture":merch,
        "couplings":couplings,
        "coupling_summary":summary,
        "coupling_authority":"EVIDENCE_CLASSIFICATION_ONLY_NOT_COMMERCIAL_ELIGIBILITY",
        "magnitude_comparison_across_independent_trends_requests_forbidden":True,
        "commercial_eligibility_automatic":False,
        "mechanism_decomposition_automatic":False,
        "bridge_query_materialization_automatic":False,
        "anchor_assignment_automatic":False,
        "runtime_latest_mutation":False,
        "production_watchlist_mutation":False,
        "credentials_used":False
    }

def validate_output(out):
    assert out["schema"]=="A_MOMENTUM_DUAL_WAVE_SHADOW"
    assert out["mode"]=="SHADOW_ONLY_NO_PRODUCTION_AUTHORITY"
    assert out["credentials_used"] is False
    assert out["runtime_latest_mutation"] is False
    assert out["production_watchlist_mutation"] is False
    assert out["magnitude_comparison_across_independent_trends_requests_forbidden"] is True
    assert out["commercial_eligibility_automatic"] is False
    assert out["mechanism_decomposition_automatic"] is False
    assert out["bridge_query_materialization_automatic"] is False
    assert out["anchor_assignment_automatic"] is False
    valid={"COUPLED_WAVE","MERCH_NATIVE_WAVE","RAW_ONLY_WAVE","UNRESOLVED"}
    assert all(x["coupling_state"] in valid for x in out["couplings"])
    assert all(x["bridge_queries"]==[] and x["anchor_query"] is None and x["mechanism_key"] is None for x in out["couplings"])
    return True

def self_test():
    raw={"candidates":[
        {"wave_id":"r1","raw_trend_title":"Alpha Wave"},
        {"wave_id":"r2","raw_trend_title":"Delta"}
    ]}
    merch={"provider_status":"PASS_WITH_DATA","merch_waves":[
        {"source_seed":"shirt","rank":1,"related_query":"Alpha Wave shirt","rising_value":"Breakout","is_breakout":True},
        {"source_seed":"shirts","rank":2,"related_query":"Crochet gifts shirts","rising_value":300,"is_breakout":False}
    ]}
    out=build(raw,merch); validate_output(out)
    assert out["coupling_summary"]["COUPLED_WAVE"]==1
    assert out["coupling_summary"]["RAW_ONLY_WAVE"]==1
    assert out["coupling_summary"]["MERCH_NATIVE_WAVE"]==1
    gap=build(raw,{"provider_status":"SENSOR_GAP","merch_waves":[]})
    assert gap["coupling_summary"]["UNRESOLVED"]==2
    assert conservative_match("Delta","Delta shirt")
    assert not conservative_match("Delta","Delta Airlines shirt sale")
    print("A_MOMENTUM_DUAL_WAVE_COUPLER_SELF_TEST_PASS")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",required=True)
    ap.add_argument("--merch",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        self_test(); return
    out=build(load(a.raw),load(a.merch))
    validate_output(out)
    Path(a.out).write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("A_MOMENTUM_DUAL_WAVE_COUPLER_PASS",json.dumps(out["coupling_summary"],sort_keys=True))

if __name__=="__main__":
    main()
