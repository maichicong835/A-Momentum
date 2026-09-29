#!/usr/bin/env python3
"""Provenance-first semantic resolution for A-Momentum shadow discovery.

Only HOLD_SEMANTIC_REVIEW items are queried. Wikidata is metadata-only and
never a market signal, IP/trademark authority, commercial gate, or mechanism
generator. Exact label/alias matches may be classified; ambiguity remains HOLD.
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ENGINE_VERSION="0.2.0"
ENDPOINT="https://www.wikidata.org/w/api.php"

CREATIVE_TERMS=(
    "television series","tv series","film","movie","video game","painting",
    "fresco","song","album","novel","book","fictional character","franchise",
    "television program","work of art","artwork","play","musical"
)
PERSON_TERMS=(
    "singer","actor","actress","politician","basketball player","football player",
    "baseball player","tennis player","athlete","fashion designer","designer",
    "musician","writer","author","entrepreneur","businessman","businesswoman",
    "coach","journalist","comedian","rapper"
)
ORG_TERMS=("company","brand","organization","corporation","fashion label","sports team","basketball team","football team")
EVENT_TERMS=("event","hurricane","tropical cyclone","tournament","championship","election","incident","disaster")
CULTURAL_TERMS=("personification","symbol","sports paraphernalia","novelty item","practical joke","prop")
PRODUCT_TERMS=("device","beverage","drink","headgear","garment","clothing","toy")
CONCEPT_TERMS=("concept","term","phenomenon","stereotype","social role","condition")

def norm(text):
    s=str(text or "").casefold().replace("'","")
    return " ".join(re.findall(r"[a-z0-9]+",s))

def api_get(params,timeout=15,retries=2,sleep_seconds=0.4):
    q=urllib.parse.urlencode(params)
    url=ENDPOINT+"?"+q
    last=None
    for attempt in range(max(1,int(retries))):
        try:
            req=urllib.request.Request(url,headers={
                "User-Agent":"A-Momentum-Semantic-Shadow/0.2.0 (metadata-only)",
                "Accept":"application/json"
            })
            with urllib.request.urlopen(req,timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last=e
            if attempt+1<max(1,int(retries)):
                time.sleep(max(float(sleep_seconds),0.1)*(2**attempt))
    raise last

def exact_candidates(query,search_results):
    nq=norm(query)
    out=[]
    for r in search_results or []:
        label=norm(r.get("label"))
        match=norm((r.get("match") or {}).get("text"))
        if nq and (label==nq or match==nq):
            out.append(r)
    # dedupe qid while preserving order
    seen=set(); uniq=[]
    for r in out:
        qid=r.get("id")
        if qid and qid not in seen:
            seen.add(qid); uniq.append(r)
    return uniq

def contains_term(desc,term):
    d=" "+norm(desc)+" "
    t=" "+norm(term)+" "
    return t in d

def contains_any(desc,terms):
    return any(contains_term(desc,x) for x in terms)

def classify_exact(result):
    desc=norm(result.get("description"))
    # Search result type is metadata evidence only. Match whole normalized
    # tokens/phrases so "song" never matches "songwriter", etc.
    if contains_any(desc,CREATIVE_TERMS):
        return "CREATIVE_PROPERTY_OR_WORK",False,"DESCRIPTION_CREATIVE_WORK_SIGNAL"
    if contains_any(desc,PERSON_TERMS):
        return "NAMED_PERSON_ENTITY",False,"DESCRIPTION_PERSON_ROLE_SIGNAL"
    if contains_any(desc,ORG_TERMS):
        return "ORGANIZATION_OR_BRAND_ENTITY",False,"DESCRIPTION_ORGANIZATION_SIGNAL"
    if contains_any(desc,EVENT_TERMS):
        return "EVENT_OR_INCIDENT",False,"DESCRIPTION_EVENT_SIGNAL"
    if contains_any(desc,CULTURAL_TERMS):
        return "CULTURAL_SYMBOL_OR_OBJECT",True,"DESCRIPTION_CULTURAL_OBJECT_SIGNAL"
    if contains_any(desc,PRODUCT_TERMS):
        return "PRODUCT_OR_PHYSICAL_OBJECT",False,"DESCRIPTION_PRODUCT_OBJECT_SIGNAL"
    if contains_any(desc,CONCEPT_TERMS):
        return "GENERIC_CONCEPT_OR_THEME",True,"DESCRIPTION_CONCEPT_SIGNAL"
    return "EXACT_ENTITY_UNRESOLVED",False,"EXACT_ENTITY_DESCRIPTION_NOT_IN_HIGH_CONFIDENCE_TYPE_SET"

def resolve_one(core,search_fn=api_get):
    params={
        "action":"wbsearchentities","search":core,"language":"en","uselang":"en",
        "format":"json","limit":5,"type":"item","origin":"*"
    }
    try:
        data=search_fn(params)
    except Exception as e:
        return {
            "resolution_state":"SEMANTIC_PROVIDER_GAP","semantic_class":None,
            "confidence":"UNRESOLVED","mechanism_review_allowed":False,
            "reason_codes":["WIKIDATA_PROVIDER_GAP",type(e).__name__],
            "provenance":{"provider":"WIKIDATA","endpoint_action":"wbsearchentities","query":core}
        }
    results=data.get("search",[])
    exact=exact_candidates(core,results)
    if len(exact)==0:
        return {
            "resolution_state":"NO_EXACT_METADATA_MATCH","semantic_class":None,
            "confidence":"UNRESOLVED","mechanism_review_allowed":False,
            "reason_codes":["NO_EXACT_LABEL_OR_ALIAS_MATCH"],
            "provenance":{"provider":"WIKIDATA","endpoint_action":"wbsearchentities","query":core,"result_count":len(results)}
        }
    if len(exact)>1:
        return {
            "resolution_state":"AMBIGUOUS_EXACT_METADATA_MATCH","semantic_class":None,
            "confidence":"UNRESOLVED","mechanism_review_allowed":False,
            "reason_codes":["MULTIPLE_EXACT_LABEL_OR_ALIAS_MATCHES"],
            "provenance":{"provider":"WIKIDATA","endpoint_action":"wbsearchentities","query":core,
                          "exact_qids":[x.get("id") for x in exact]}
        }
    r=exact[0]
    semantic_class,allowed,reason=classify_exact(r)
    qid=r.get("id")
    return {
        "resolution_state":"RESOLVED_EXACT_METADATA",
        "semantic_class":semantic_class,
        "confidence":"HIGH" if semantic_class!="EXACT_ENTITY_UNRESOLVED" else "UNRESOLVED",
        "mechanism_review_allowed":allowed,
        "reason_codes":[reason],
        "provenance":{
            "provider":"WIKIDATA","endpoint_action":"wbsearchentities","query":core,
            "qid":qid,"label":r.get("label"),"description":r.get("description"),
            "match_type":(r.get("match") or {}).get("type"),
            "match_text":(r.get("match") or {}).get("text"),
            "concept_url":r.get("concepturi") or (f"https://www.wikidata.org/wiki/{qid}" if qid else None)
        }
    }

def apply(doc,search_fn=api_get,sleep_seconds=0.15):
    targets=[x for x in doc.get("structural_triage_decisions",[]) if x.get("disposition")=="HOLD_SEMANTIC_REVIEW"]
    decisions=[]
    for t in targets:
        r=resolve_one(t.get("merch_core",""),search_fn)
        r.update({
            "semantic_resolution_id":t.get("opportunity_id"),
            "opportunity_id":t.get("opportunity_id"),
            "merch_core":t.get("merch_core"),
            "market_signal_authority":False,
            "commercial_eligibility_authority":False,
            "ip_safety_authority":False,
            "mechanism_decomposition_automatic":False,
            "production_eligible":False
        })
        decisions.append(r)
        if search_fn is api_get:
            time.sleep(max(float(sleep_seconds),0.0))
    summary={}
    for d in decisions:
        key=d["semantic_class"] or d["resolution_state"]
        summary[key]=summary.get(key,0)+1
    gaps=sum(1 for d in decisions if d["resolution_state"]=="SEMANTIC_PROVIDER_GAP")
    if not decisions:
        status="PASS_NO_TARGETS"
    elif gaps==len(decisions):
        status="SENSOR_GAP"
    elif gaps:
        status="PARTIAL_WITH_GAPS"
    else:
        status="PASS_WITH_DATA"
    doc["semantic_resolution"]={
        "schema":"A_MOMENTUM_SEMANTIC_RESOLUTION_SHADOW",
        "schema_version":"1.0",
        "engine_version":ENGINE_VERSION,
        "authority":"EXACT_METADATA_RESOLUTION_ONLY",
        "provider":"WIKIDATA",
        "provider_role":"METADATA_ONLY_NOT_MARKET_SIGNAL",
        "provider_status":status,
        "target_count":len(targets),
        "decision_count":len(decisions),
        "summary":summary,
        "exact_match_required":True,
        "ambiguous_or_missing_exact_match_remains_hold":True,
        "market_signal_authority":False,
        "commercial_eligibility_authority":False,
        "ip_safety_authority":False,
        "mechanism_generation_authority":False
    }
    doc["semantic_resolution_decisions"]=decisions
    return doc

def validate(doc):
    meta=doc["semantic_resolution"]; ds=doc["semantic_resolution_decisions"]
    assert meta["authority"]=="EXACT_METADATA_RESOLUTION_ONLY"
    assert meta["provider_role"]=="METADATA_ONLY_NOT_MARKET_SIGNAL"
    assert meta["decision_count"]==len(ds)==meta["target_count"]
    assert meta["exact_match_required"] is True
    assert meta["ambiguous_or_missing_exact_match_remains_hold"] is True
    assert meta["market_signal_authority"] is False
    assert meta["commercial_eligibility_authority"] is False
    assert meta["ip_safety_authority"] is False
    assert meta["mechanism_generation_authority"] is False
    valid_states={"RESOLVED_EXACT_METADATA","NO_EXACT_METADATA_MATCH","AMBIGUOUS_EXACT_METADATA_MATCH","SEMANTIC_PROVIDER_GAP"}
    assert all(x["resolution_state"] in valid_states for x in ds)
    assert all(x["market_signal_authority"] is False for x in ds)
    assert all(x["commercial_eligibility_authority"] is False for x in ds)
    assert all(x["ip_safety_authority"] is False for x in ds)
    assert all(x["mechanism_decomposition_automatic"] is False for x in ds)
    assert all(x["production_eligible"] is False for x in ds)
    return True

def self_test():
    fixtures={
      "dolly parton":{"search":[{"id":"Q123","label":"Dolly Parton","description":"American singer, songwriter and actress","match":{"type":"label","text":"Dolly Parton"},"concepturi":"https://www.wikidata.org/entity/Q123"}]},
      "creation of adam":{"search":[{"id":"Q456","label":"The Creation of Adam","description":"fresco painting by Michelangelo","match":{"type":"alias","text":"Creation of Adam"},"concepturi":"https://www.wikidata.org/entity/Q456"}]},
      "foam finger":{"search":[{"id":"Q789","label":"Foam finger","description":"sports paraphernalia item used by fans","match":{"type":"label","text":"Foam finger"},"concepturi":"https://www.wikidata.org/entity/Q789"}]},
      "underdog":{"search":[
        {"id":"Q1","label":"Underdog","description":"concept in competition","match":{"type":"label","text":"Underdog"}},
        {"id":"Q2","label":"Underdog","description":"animated television series","match":{"type":"label","text":"Underdog"}}
      ]},
      "thicker kicker":{"search":[]}
    }
    def fake(params):
        return fixtures[params["search"]]
    a=resolve_one("dolly parton",fake); assert a["semantic_class"]=="NAMED_PERSON_ENTITY" and not a["mechanism_review_allowed"]
    b=resolve_one("creation of adam",fake); assert b["semantic_class"]=="CREATIVE_PROPERTY_OR_WORK"
    c=resolve_one("foam finger",fake); assert c["semantic_class"]=="CULTURAL_SYMBOL_OR_OBJECT" and c["mechanism_review_allowed"]
    d=resolve_one("underdog",fake); assert d["resolution_state"]=="AMBIGUOUS_EXACT_METADATA_MATCH"
    e=resolve_one("thicker kicker",fake); assert e["resolution_state"]=="NO_EXACT_METADATA_MATCH"
    doc={"structural_triage_decisions":[
      {"opportunity_id":"a","merch_core":"dolly parton","disposition":"HOLD_SEMANTIC_REVIEW"},
      {"opportunity_id":"b","merch_core":"foam finger","disposition":"HOLD_SEMANTIC_REVIEW"}
    ]}
    out=apply(doc,fake,0); assert validate(out)
    print("A_MOMENTUM_SEMANTIC_RESOLUTION_SELF_TEST_PASS",out["semantic_resolution"]["summary"])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input")
    ap.add_argument("--out")
    ap.add_argument("--self-test",action="store_true")
    a=ap.parse_args()
    if a.self_test:
        self_test(); return
    if not a.input or not a.out:
        raise SystemExit("--input and --out required")
    doc=json.loads(Path(a.input).read_text(encoding="utf-8"))
    doc=apply(doc)
    validate(doc)
    Path(a.out).write_text(json.dumps(doc,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("A_MOMENTUM_SEMANTIC_RESOLUTION_PASS",doc["semantic_resolution"]["provider_status"],json.dumps(doc["semantic_resolution"]["summary"],sort_keys=True))

if __name__=="__main__":
    main()
