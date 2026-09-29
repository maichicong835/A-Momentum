#!/usr/bin/env python3
"""Conservative dual-wave coupler for A-Momentum shadow evidence."""
import argparse
import json
import re
from pathlib import Path

ENGINE_VERSION="0.2.0"
MERCH_TOKENS={"shirt","shirts","tshirt","tshirts","tee","tees","graphic","t"}

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def norm_tokens(text):
    s=str(text or "").casefold().replace("'","")
    return re.findall(r"[a-z0-9]+",s)

def core_merch_tokens(text):
    return [t for t in norm_tokens(text) if t not in MERCH_TOKENS]

def merch_core_key(text):
    core=core_merch_tokens(text)
    return " ".join(core) if core else " ".join(norm_tokens(text))

def group_merch_waves(rows):
    groups={}
    order=[]
    for row in rows:
        key=merch_core_key(row.get("related_query"))
        if not key:
            continue
        if key not in groups:
            groups[key]={
                "merch_core":key,
                "query_variants":[],
                "seed_evidence":[],
                "any_breakout":False
            }
            order.append(key)
        g=groups[key]
        q=row.get("related_query")
        if q and q not in g["query_variants"]:
            g["query_variants"].append(q)
        evidence={
            "source_seed":row.get("source_seed"),
            "rank":row.get("rank"),
            "related_query":q,
            "rising_value":row.get("rising_value"),
            "is_breakout":row.get("is_breakout",False)
        }
        g["seed_evidence"].append(evidence)
        g["any_breakout"]=g["any_breakout"] or bool(evidence["is_breakout"])
    return [groups[k] for k in order]

def match_relation(raw_title,merch_query_or_core):
    r=norm_tokens(raw_title)
    m=norm_tokens(merch_core_key(merch_query_or_core))
    if not r or not m:
        return "NONE"
    if r==m:
        return "EXACT"
    if len(r)>=2 and len(m)>=2:
        rs=" ".join(r); ms=" ".join(m)
        if rs in ms or ms in rs:
            return "PARTIAL_PHRASE_OVERLAP"
    return "NONE"

def conservative_match(raw_title,merch_query_or_core):
    return match_relation(raw_title,merch_query_or_core)=="EXACT"

def build(raw,merch):
    raw_waves=raw.get("candidates",[])
    merch_observations=merch.get("merch_waves",[])
    merch_groups=group_merch_waves(merch_observations)
    provider_status=merch.get("provider_status","SENSOR_GAP")
    used=set(); couplings=[]
    for rw in raw_waves:
        matches=[]; overlaps=[]; overlap_indexes=[]
        for i,group in enumerate(merch_groups):
            relation=match_relation(rw.get("raw_trend_title"),group.get("merch_core"))
            if relation=="EXACT":
                used.add(i)
                matches.append(group)
            elif relation=="PARTIAL_PHRASE_OVERLAP":
                overlaps.append(group)
                overlap_indexes.append(i)
        unresolved_reason=None
        if matches:
            state="COUPLED_WAVE"
        elif provider_status=="SENSOR_GAP":
            state="UNRESOLVED"
            unresolved_reason="MERCH_PROXY_SENSOR_GAP"
        elif overlaps:
            state="UNRESOLVED"
            unresolved_reason="PARTIAL_PHRASE_OR_ENTITY_OVERLAP_NOT_PHENOMENON_PROOF"
            used.update(overlap_indexes)
        else:
            state="RAW_ONLY_WAVE"
        couplings.append({
            "wave_id":rw.get("wave_id"),
            "raw_trend_title":rw.get("raw_trend_title"),
            "coupling_state":state,
            "match_policy":"EXACT_NORMALIZED_CORE_ONLY_PARTIAL_OVERLAP_IS_UNRESOLVED",
            "merch_matches":matches,
            "merch_overlap_candidates":overlaps,
            "unresolved_reason":unresolved_reason,
            "commercial_eligibility_decision":None,
            "mechanism_key":None,
            "bridge_queries":[],
            "anchor_query":None,
            "production_eligible":False
        })
    for i,group in enumerate(merch_groups):
        if i in used:
            continue
        couplings.append({
            "wave_id":None,
            "raw_trend_title":None,
            "coupling_state":"MERCH_NATIVE_WAVE",
            "match_policy":"UNMATCHED_UNIQUE_MERCH_CORE",
            "merch_matches":[group],
            "merch_overlap_candidates":[],
            "unresolved_reason":None,
            "commercial_eligibility_decision":None,
            "mechanism_key":None,
            "bridge_queries":[],
            "anchor_query":None,
            "production_eligible":False
        })
    summary={k:sum(1 for x in couplings if x["coupling_state"]==k) for k in ["COUPLED_WAVE","MERCH_NATIVE_WAVE","RAW_ONLY_WAVE","UNRESOLVED"]}
    return {
        "schema":"A_MOMENTUM_DUAL_WAVE_SHADOW",
        "schema_version":"1.2",
        "engine_version":ENGINE_VERSION,
        "mode":"SHADOW_ONLY_NO_PRODUCTION_AUTHORITY",
        "raw_wave_capture":raw,
        "merch_proxy_capture":merch,
        "merch_observation_count":len(merch_observations),
        "unique_merch_core_count":len(merch_groups),
        "merch_grouping_policy":"NORMALIZED_QUERY_WITH_MERCH_FORMAT_TOKENS_REMOVED_PRESERVE_SEED_EVIDENCE",
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
    assert out["unique_merch_core_count"]<=out["merch_observation_count"]
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
        {"source_seed":"shirts","rank":2,"related_query":"Crochet gifts shirts","rising_value":300,"is_breakout":False},
        {"source_seed":"t shirt","rank":3,"related_query":"crochet gifts t shirt","rising_value":120,"is_breakout":False}
    ]}
    groups=group_merch_waves(merch["merch_waves"])
    assert len(groups)==2
    assert len([g for g in groups if g["merch_core"]=="crochet gifts"][0]["seed_evidence"])==2
    out=build(raw,merch); validate_output(out)
    assert out["coupling_summary"]["COUPLED_WAVE"]==1
    assert out["coupling_summary"]["RAW_ONLY_WAVE"]==1
    assert out["coupling_summary"]["MERCH_NATIVE_WAVE"]==1
    assert out["merch_observation_count"]==3 and out["unique_merch_core_count"]==2
    gap=build(raw,{"provider_status":"SENSOR_GAP","merch_waves":[]})
    assert gap["coupling_summary"]["UNRESOLVED"]==2
    assert conservative_match("Delta","delta")
    assert not conservative_match("Delta","delta airlines")
    assert match_relation("Dolly Parton estate planning","dolly parton")=="PARTIAL_PHRASE_OVERLAP"
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
    print("A_MOMENTUM_DUAL_WAVE_MERCH_COUNTS",out["merch_observation_count"],out["unique_merch_core_count"])
    print("A_MOMENTUM_DUAL_WAVE_COUPLER_PASS",json.dumps(out["coupling_summary"],sort_keys=True))

if __name__=="__main__":
    main()
