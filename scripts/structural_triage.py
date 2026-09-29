#!/usr/bin/env python3
"""Conservative Structural Triage for M-primary A-Momentum shadow intake.

This is intentionally NOT semantic entity resolution, IP clearance, commercial
eligibility, mechanism generation, or production selection. It only recognizes
a few high-confidence query structures and defaults ambiguity to HOLD.
"""
import argparse
import json
import re
from pathlib import Path

ENGINE_VERSION="0.2.0"

PRODUCT_PHRASES={
    "long sleeve",
}
PRODUCT_TOKENS={
    "flannel","toddler","boys","boy","girls","girl","women","womens","woman",
    "mens","men","man","kids","kid","youth","baby","blanket"
}
AWARENESS_TOKENS={"awareness"}
LOCAL_PHRASES={"near me"}

def norm(text):
    s=str(text or "").casefold().replace("'","")
    return " ".join(re.findall(r"[a-z0-9]+",s))

def tokens(text):
    return norm(text).split()

def phrase_expression_signal(core):
    t=tokens(core)
    if not t:
        return False
    if t[0] in {"i","im","we","my","our","you","your"}:
        return True
    # Require a pronoun-like subject before relational wording; do not classify
    # arbitrary uses of "with" as slogans.
    return ("with" in t and any(x in t for x in {"i","im","we","my","our","you","your"}))

def awareness_expression_signal(core):
    return any(t in AWARENESS_TOKENS for t in tokens(core))

def local_purchase_signal(core):
    n=norm(core)
    return any(p in n for p in LOCAL_PHRASES)

def product_configuration_signal(core):
    n=norm(core)
    t=set(tokens(core))
    if any(p in n for p in PRODUCT_PHRASES):
        return True
    return bool(t & PRODUCT_TOKENS)

def triage_one(item):
    core=item.get("merch_core","")
    evidence=[]
    if local_purchase_signal(core):
        disposition="HOLD_LOCAL_PURCHASE_INTENT"
        structural_type="LOCAL_PURCHASE_OR_NAVIGATION"
        evidence.append("LOCAL_INTENT_NEAR_ME")
        allowed=False
        confidence="HIGH"
    elif product_configuration_signal(core):
        disposition="HOLD_PRODUCT_CONFIGURATION"
        structural_type="APPAREL_OR_PRODUCT_CONFIGURATION_DEMAND"
        evidence.append("PRODUCT_FORM_OR_DEMOGRAPHIC_TERMS")
        allowed=False
        confidence="HIGH"
    elif awareness_expression_signal(core):
        disposition="PASS_EXPRESSION_STRUCTURE"
        structural_type="CAUSE_AWARENESS_EXPRESSION"
        evidence.append("AWARENESS_EXPRESSION_TOKEN")
        allowed=True
        confidence="HIGH"
    elif phrase_expression_signal(core):
        disposition="PASS_EXPRESSION_STRUCTURE"
        structural_type="PHRASE_EXPRESSION"
        evidence.append("PRONOUN_LED_EXPRESSION_STRUCTURE")
        allowed=True
        confidence="HIGH"
    else:
        disposition="HOLD_SEMANTIC_REVIEW"
        structural_type="UNRESOLVED_THEME_OBJECT_ENTITY_OR_PROPERTY"
        evidence.append("QUERY_STRUCTURE_INSUFFICIENT_FOR_SAFE_SEMANTIC_CLASSIFICATION")
        allowed=False
        confidence="UNRESOLVED"
    return {
        "triage_id":item.get("opportunity_id"),
        "opportunity_id":item.get("opportunity_id"),
        "merch_core":core,
        "disposition":disposition,
        "structural_type":structural_type,
        "confidence":confidence,
        "reason_codes":evidence,
        "mechanism_decomposition_allowed":allowed,
        "mechanism_decomposition_automatic":False,
        "semantic_entity_resolution_performed":False,
        "named_entity_or_property_clearance_performed":False,
        "commercial_eligibility_decision":None,
        "ip_safety_decision":None,
        "production_eligible":False
    }

def apply(doc):
    intake=doc.get("opportunity_intake",[])
    decisions=[triage_one(x) for x in intake]
    summary={}
    for d in decisions:
        summary[d["disposition"]]=summary.get(d["disposition"],0)+1
    doc["structural_triage"]={
        "schema":"A_MOMENTUM_STRUCTURAL_TRIAGE_SHADOW",
        "schema_version":"1.0",
        "engine_version":ENGINE_VERSION,
        "authority":"SHADOW_STRUCTURE_ONLY",
        "policy":"HIGH_CONFIDENCE_STRUCTURE_ONLY_DEFAULT_AMBIGUITY_TO_HOLD",
        "decision_count":len(decisions),
        "summary":summary,
        "semantic_entity_resolution_performed":False,
        "named_entity_or_property_clearance_performed":False,
        "commercial_eligibility_authority":False,
        "ip_safety_authority":False,
        "mechanism_generation_authority":False
    }
    doc["structural_triage_decisions"]=decisions
    return doc

def validate(doc):
    intake=doc.get("opportunity_intake",[])
    triage=doc["structural_triage"]
    decisions=doc["structural_triage_decisions"]
    assert triage["authority"]=="SHADOW_STRUCTURE_ONLY"
    assert triage["decision_count"]==len(decisions)==len(intake)
    assert triage["semantic_entity_resolution_performed"] is False
    assert triage["commercial_eligibility_authority"] is False
    assert triage["ip_safety_authority"] is False
    assert triage["mechanism_generation_authority"] is False
    valid={
        "PASS_EXPRESSION_STRUCTURE",
        "HOLD_PRODUCT_CONFIGURATION",
        "HOLD_LOCAL_PURCHASE_INTENT",
        "HOLD_SEMANTIC_REVIEW"
    }
    assert all(x["disposition"] in valid for x in decisions)
    assert all(x["mechanism_decomposition_automatic"] is False for x in decisions)
    assert all(x["semantic_entity_resolution_performed"] is False for x in decisions)
    assert all(x["named_entity_or_property_clearance_performed"] is False for x in decisions)
    assert all(x["commercial_eligibility_decision"] is None for x in decisions)
    assert all(x["ip_safety_decision"] is None for x in decisions)
    assert all(x["production_eligible"] is False for x in decisions)
    ids={x.get("opportunity_id") for x in intake}
    assert {x.get("opportunity_id") for x in decisions}==ids
    return True

def self_test():
    cases=[
        ("im with stupid","PASS_EXPRESSION_STRUCTURE","PHRASE_EXPRESSION",True),
        ("breast cancer awareness","PASS_EXPRESSION_STRUCTURE","CAUSE_AWARENESS_EXPRESSION",True),
        ("toddler long sleeve","HOLD_PRODUCT_CONFIGURATION","APPAREL_OR_PRODUCT_CONFIGURATION_DEMAND",False),
        ("dolly parton near me","HOLD_LOCAL_PURCHASE_INTENT","LOCAL_PURCHASE_OR_NAVIGATION",False),
        ("dolly parton","HOLD_SEMANTIC_REVIEW","UNRESOLVED_THEME_OBJECT_ENTITY_OR_PROPERTY",False),
        ("foam finger","HOLD_SEMANTIC_REVIEW","UNRESOLVED_THEME_OBJECT_ENTITY_OR_PROPERTY",False),
    ]
    intake=[]
    for i,(core,disp,stype,allowed) in enumerate(cases):
        x={"opportunity_id":f"m-{i}","merch_core":core}
        d=triage_one(x)
        assert d["disposition"]==disp
        assert d["structural_type"]==stype
        assert d["mechanism_decomposition_allowed"] is allowed
        intake.append(x)
    doc=apply({"opportunity_intake":intake})
    assert validate(doc)
    print("A_MOMENTUM_STRUCTURAL_TRIAGE_SELF_TEST_PASS",len(cases),doc["structural_triage"]["summary"])

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
    print("A_MOMENTUM_STRUCTURAL_TRIAGE_PASS",json.dumps(doc["structural_triage"]["summary"],sort_keys=True))

if __name__=="__main__":
    main()
