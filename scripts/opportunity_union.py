#!/usr/bin/env python3
"""M ∪ S opportunity union for A-Momentum shadow discovery.

M (shirt-expression) and S (sticker-native) are independent discovery radars.
Exact normalized core equality may dedupe them into one opportunity. Neither
radar is a confirmation gate for the other.
"""
import argparse, hashlib, json, re, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import wave_coupler as wc

ENGINE_VERSION="0.2.0"
S_FORMAT_TOKENS={"sticker","stickers"}

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def norm_tokens(text):
    s=str(text or "").casefold().replace("'","")
    return re.findall(r"[a-z0-9]+",s)

def s_core_key(text):
    toks=[t for t in norm_tokens(text) if t not in S_FORMAT_TOKENS]
    return " ".join(toks) if toks else " ".join(norm_tokens(text))

def group_s(rows):
    groups={}; order=[]
    for row in rows:
        core=s_core_key(row.get("related_query"))
        if not core: continue
        if core not in groups:
            groups[core]={
              "opportunity_core":core,
              "query_variants":[],
              "seed_evidence":[],
              "any_breakout":False
            }; order.append(core)
        g=groups[core]
        q=row.get("related_query")
        if q and q not in g["query_variants"]:
            g["query_variants"].append(q)
        ev={
          "source_seed":row.get("source_seed"),
          "rank":row.get("rank"),
          "related_query":q,
          "rising_value":row.get("rising_value"),
          "is_breakout":row.get("is_breakout",False)
        }
        g["seed_evidence"].append(ev)
        g["any_breakout"]=g["any_breakout"] or bool(ev["is_breakout"])
    return [groups[k] for k in order]

def oid(core):
    return "o-"+hashlib.sha256(str(core).encode("utf-8")).hexdigest()[:16]

def raw_context(core,raw_waves):
    exact=[]; partial=[]
    for rw in raw_waves:
        rel=wc.match_relation(rw.get("raw_trend_title"),core)
        item={"wave_id":rw.get("wave_id"),"raw_trend_title":rw.get("raw_trend_title")}
        if rel=="EXACT": exact.append(item)
        elif rel=="PARTIAL_PHRASE_OVERLAP": partial.append(item)
    if exact: state="EXACT_COUPLED_CONTEXT"
    elif partial: state="PARTIAL_OVERLAP_CONTEXT"
    else: state="NO_RAW_CONTEXT"
    return state,exact,partial

def build(dual,sticker):
    raw=dual.get("raw_wave_capture",{}).get("candidates",[])
    m_items=dual.get("opportunity_intake",[])
    s_groups=group_s(sticker.get("merch_waves",[]))
    by_core={}

    for m in m_items:
        core=m.get("merch_core")
        if not core: continue
        by_core[core]={
          "opportunity_id":oid(core),
          "opportunity_core":core,
          "merch_core":core,
          "source_lanes":["M"],
          "m_evidence":{
            "query_variants":m.get("query_variants",[]),
            "seed_evidence":m.get("seed_evidence",[]),
            "any_breakout":m.get("any_breakout",False)
          },
          "s_evidence":None
        }

    for s in s_groups:
        core=s["opportunity_core"]
        if core in by_core:
            by_core[core]["source_lanes"].append("S")
            by_core[core]["s_evidence"]=s
        else:
            by_core[core]={
              "opportunity_id":oid(core),
              "opportunity_core":core,
              "merch_core":core,
              "source_lanes":["S"],
              "m_evidence":None,
              "s_evidence":s
            }

    intake=[]
    for core in sorted(by_core):
        x=by_core[core]
        lanes=x["source_lanes"]
        if lanes==["M"]: lane="M_ONLY"
        elif lanes==["S"]: lane="S_ONLY"
        else: lane="M_S_MULTI_RADAR"
        state,exact,partial=raw_context(core,raw)
        x.update({
          "source_lane":lane,
          "intake_state":"DISCOVERY_INTAKE_READY_UNSCREENED",
          "requires_cross_radar_confirmation":False,
          "r_context_role":"OPTIONAL_ENRICHMENT_NOT_ADMISSION_GATE",
          "r_context_state":state,
          "r_exact_matches":exact,
          "r_partial_matches":partial,
          "fixed_wait_before_discovery_hours":0,
          "temporal_observation_mode":"PARALLEL_NON_BLOCKING",
          "structural_triage_required":True,
          "mechanism_decomposition_automatic":False,
          "commercial_eligibility_decision":None,
          "production_eligible":False
        })
        intake.append(x)

    m_count=sum(1 for x in intake if x["source_lane"]=="M_ONLY")
    s_count=sum(1 for x in intake if x["source_lane"]=="S_ONLY")
    both=sum(1 for x in intake if x["source_lane"]=="M_S_MULTI_RADAR")

    out=dict(dual)
    out["schema"]="A_MOMENTUM_MULTI_RADAR_SHADOW"
    out["schema_version"]="1.0"
    out["engine_version"]=ENGINE_VERSION
    out["sticker_proxy_capture"]=sticker
    out["sticker_observation_count"]=len(sticker.get("merch_waves",[]))
    out["unique_sticker_core_count"]=len(s_groups)
    out["sticker_grouping_policy"]="NORMALIZED_QUERY_WITH_STICKER_FORMAT_TOKENS_REMOVED_PRESERVE_SEED_EVIDENCE"
    out["opportunity_union_policy"]="EXACT_NORMALIZED_CORE_DEDUPE_M_OR_S_NO_INTERSECTION_GATE"
    out["opportunity_intake"]=intake
    out["opportunity_intake_count"]=len(intake)
    out["opportunity_union_summary"]={
      "M_ONLY":m_count,
      "S_ONLY":s_count,
      "M_S_MULTI_RADAR":both,
      "TOTAL_UNIQUE":len(intake)
    }
    out["discovery_model"]={
      "independent_opportunity_lanes":["MERCH_PROXY_WAVE","STICKER_NATIVE_WAVE"],
      "opportunity_union":"M_OR_S",
      "cross_radar_confirmation_required":False,
      "raw_wave_role":"PARALLEL_ATTENTION_CONTEXT",
      "coupling_role":"OPTIONAL_EVIDENCE_ENRICHMENT_NOT_ADMISSION_GATE",
      "temporal_observation_mode":"PARALLEL_NON_BLOCKING"
    }
    out["commercial_bridge_active"]=False
    out["sticker_radar_is_m_confirmation"]=False
    return out

def validate(out):
    assert out["schema"]=="A_MOMENTUM_MULTI_RADAR_SHADOW"
    assert out["opportunity_union_policy"]=="EXACT_NORMALIZED_CORE_DEDUPE_M_OR_S_NO_INTERSECTION_GATE"
    assert out["discovery_model"]["opportunity_union"]=="M_OR_S"
    assert out["discovery_model"]["cross_radar_confirmation_required"] is False
    assert out["commercial_bridge_active"] is False
    assert out["sticker_radar_is_m_confirmation"] is False
    assert out["opportunity_intake_count"]==out["opportunity_union_summary"]["TOTAL_UNIQUE"]==len(out["opportunity_intake"])
    assert out["opportunity_union_summary"]["M_ONLY"]+out["opportunity_union_summary"]["S_ONLY"]+out["opportunity_union_summary"]["M_S_MULTI_RADAR"]==len(out["opportunity_intake"])
    assert all(x["source_lane"] in {"M_ONLY","S_ONLY","M_S_MULTI_RADAR"} for x in out["opportunity_intake"])
    assert all(x["requires_cross_radar_confirmation"] is False for x in out["opportunity_intake"])
    assert all(x["structural_triage_required"] is True for x in out["opportunity_intake"])
    assert all(x["production_eligible"] is False for x in out["opportunity_intake"])
    return True

def self_test():
    dual={
      "schema":"A_MOMENTUM_DUAL_WAVE_SHADOW",
      "mode":"SHADOW_ONLY_NO_PRODUCTION_AUTHORITY",
      "raw_wave_capture":{"candidates":[]},
      "opportunity_intake":[
        {"merch_core":"shared","query_variants":["shared shirt"],"seed_evidence":[{"source_seed":"shirt"}],"any_breakout":False},
        {"merch_core":"m only","query_variants":["m only shirt"],"seed_evidence":[{"source_seed":"shirt"}],"any_breakout":False}
      ],
      "couplings":[],
      "credentials_used":False,
      "runtime_latest_mutation":False,
      "production_watchlist_mutation":False
    }
    sticker={"merch_waves":[
      {"source_seed":"sticker","rank":1,"related_query":"shared sticker","rising_value":100,"is_breakout":False},
      {"source_seed":"stickers","rank":2,"related_query":"s only stickers","rising_value":200,"is_breakout":False}
    ]}
    out=build(dual,sticker); assert validate(out)
    assert out["opportunity_union_summary"]=={"M_ONLY":1,"S_ONLY":1,"M_S_MULTI_RADAR":1,"TOTAL_UNIQUE":3}
    by={x["opportunity_core"]:x for x in out["opportunity_intake"]}
    assert by["shared"]["source_lanes"]==["M","S"]
    assert by["s only"]["source_lane"]=="S_ONLY"
    print("A_MOMENTUM_OPPORTUNITY_UNION_SELF_TEST_PASS",out["opportunity_union_summary"])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dual",required=True)
    ap.add_argument("--sticker",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        self_test(); return
    out=build(load(a.dual),load(a.sticker))
    validate(out)
    Path(a.out).write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("A_MOMENTUM_OPPORTUNITY_UNION_PASS",json.dumps(out["opportunity_union_summary"],sort_keys=True))

if __name__=="__main__":
    main()
