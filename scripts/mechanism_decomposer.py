#!/usr/bin/env python3
"""Conservative Mechanism Decomposition Shadow for A-Momentum.

This layer turns only explicitly review-allowed evidence into coarse mechanism
hypotheses. It does not generate product copy, preserve source wording as a
reusable creative, clear IP/trademark/property risk, validate commercial demand,
materialize bridge/anchor queries, or mutate production state.
"""
import argparse
import hashlib
import json
from pathlib import Path

ENGINE_VERSION="0.2.0"

STRUCTURAL_MAP={
    "PHRASE_EXPRESSION":{
        "mechanism_family":"RELATIONAL_OR_IDENTITY_PHRASE_EXPRESSION",
        "expression_mode":"WORDING_LED",
        "social_function":"SOCIAL_POSITIONING_OR_RELATIONAL_HUMOR",
        "transferable_unit":"PHRASE_STRUCTURE_AND_SOCIAL_JOB_ONLY",
        "source_reuse_policy":"EVIDENCE_ONLY_DO_NOT_REUSE_SOURCE_WORDING"
    },
    "CAUSE_AWARENESS_EXPRESSION":{
        "mechanism_family":"CAUSE_AFFILIATION_AND_AWARENESS_SIGNALING",
        "expression_mode":"WORDING_OR_SYMBOL_HYBRID",
        "social_function":"CAUSE_AFFILIATION_OR_SUPPORT_SIGNALING",
        "transferable_unit":"AFFILIATION_SIGNALING_MECHANISM_ONLY",
        "source_reuse_policy":"EVIDENCE_ONLY_NO_SOURCE_WORDING_OR_SYMBOL_REUSE_WITHOUT_DOWNSTREAM_REVIEW"
    }
}

SEMANTIC_MAP={
    "CULTURAL_SYMBOL_OR_OBJECT":{
        "mechanism_family":"CULTURAL_SYMBOL_DISPLAY",
        "expression_mode":"VISUAL_LED_OR_HYBRID",
        "social_function":"CULTURAL_AFFILIATION_OR_RECOGNITION",
        "transferable_unit":"SYMBOLIC_OBJECT_ROLE_ONLY",
        "source_reuse_policy":"EVIDENCE_ONLY_DO_NOT_REUSE_SOURCE_ICONOGRAPHY"
    },
    "GENERIC_CONCEPT_OR_THEME":{
        "mechanism_family":"THEME_IDENTITY_EXPRESSION",
        "expression_mode":"HYBRID_UNSPECIFIED",
        "social_function":"IDENTITY_OR_THEME_AFFILIATION",
        "transferable_unit":"THEME_AS_IDENTITY_MARKER_ONLY",
        "source_reuse_policy":"EVIDENCE_ONLY_DO_NOT_REUSE_SOURCE_EXPRESSION"
    }
}

def hypothesis_id(opportunity_id,family):
    raw=f"{opportunity_id}|{family}".encode("utf-8")
    return "mh-"+hashlib.sha256(raw).hexdigest()[:16]

def index_by(rows,key="opportunity_id"):
    return {x.get(key):x for x in rows or [] if x.get(key)}

def collect_review_allowed(doc):
    intake=index_by(doc.get("opportunity_intake",[]))
    triage=index_by(doc.get("structural_triage_decisions",[]))
    semantic=index_by(doc.get("semantic_resolution_decisions",[]))
    eligible=[]
    for oid,item in intake.items():
        t=triage.get(oid,{})
        s=semantic.get(oid,{})
        if t.get("mechanism_decomposition_allowed") is True:
            eligible.append({
                "opportunity_id":oid,
                "merch_core":item.get("merch_core"),
                "basis_layer":"STRUCTURAL_TRIAGE",
                "basis_type":t.get("structural_type"),
                "basis_confidence":t.get("confidence"),
                "basis_reason_codes":t.get("reason_codes",[])
            })
        elif s.get("mechanism_review_allowed") is True:
            eligible.append({
                "opportunity_id":oid,
                "merch_core":item.get("merch_core"),
                "basis_layer":"SEMANTIC_RESOLUTION",
                "basis_type":s.get("semantic_class"),
                "basis_confidence":s.get("confidence"),
                "basis_reason_codes":s.get("reason_codes",[]),
                "semantic_provenance":s.get("provenance")
            })
    return eligible

def decompose_one(candidate):
    basis=candidate.get("basis_layer")
    btype=candidate.get("basis_type")
    mapping=(STRUCTURAL_MAP if basis=="STRUCTURAL_TRIAGE" else SEMANTIC_MAP).get(btype)
    if not mapping:
        return {
            "opportunity_id":candidate.get("opportunity_id"),
            "source_merch_core":candidate.get("merch_core"),
            "decomposition_state":"HOLD_UNSUPPORTED_REVIEW_TYPE",
            "basis_layer":basis,
            "basis_type":btype,
            "mechanism_hypothesis":None,
            "reason_codes":["REVIEW_ALLOWED_INPUT_TYPE_NOT_IN_CONSERVATIVE_DECOMPOSITION_ALLOWLIST"],
            "production_eligible":False
        }
    family=mapping["mechanism_family"]
    return {
        "opportunity_id":candidate.get("opportunity_id"),
        "source_merch_core":candidate.get("merch_core"),
        "decomposition_state":"SHADOW_MECHANISM_HYPOTHESIS",
        "basis_layer":basis,
        "basis_type":btype,
        "basis_confidence":candidate.get("basis_confidence"),
        "basis_reason_codes":candidate.get("basis_reason_codes",[]),
        "semantic_provenance":candidate.get("semantic_provenance"),
        "mechanism_hypothesis":{
            "mechanism_candidate_id":hypothesis_id(candidate.get("opportunity_id"),family),
            "mechanism_family":family,
            "expression_mode":mapping["expression_mode"],
            "social_function":mapping["social_function"],
            "transferable_unit":mapping["transferable_unit"],
            "source_reuse_policy":mapping["source_reuse_policy"],
            "abstraction_level":"MECHANISM_FAMILY_ONLY_NOT_PRODUCT_CREATIVE",
            "source_specific_wording_or_iconography_reuse_allowed":False,
            "source_topic_is_market_evidence_not_generated_copy":True
        },
        "commercial_eligibility_decision":None,
        "ip_safety_decision":None,
        "trademark_clearance_performed":False,
        "copyright_or_property_clearance_performed":False,
        "idea_generation_performed":False,
        "bridge_query_materialized":False,
        "anchor_query_assigned":False,
        "watchlist_promotion_allowed":False,
        "daily7_selection_authority":False,
        "production_eligible":False
    }

def apply(doc):
    eligible=collect_review_allowed(doc)
    decisions=[decompose_one(x) for x in eligible]
    hypotheses=[x for x in decisions if x.get("decomposition_state")=="SHADOW_MECHANISM_HYPOTHESIS"]
    holds=[x for x in decisions if x.get("decomposition_state")!="SHADOW_MECHANISM_HYPOTHESIS"]
    family_summary={}
    for x in hypotheses:
        fam=x["mechanism_hypothesis"]["mechanism_family"]
        family_summary[fam]=family_summary.get(fam,0)+1
    doc["mechanism_decomposition"]={
        "schema":"A_MOMENTUM_MECHANISM_DECOMPOSITION_SHADOW",
        "schema_version":"1.0",
        "engine_version":ENGINE_VERSION,
        "authority":"SHADOW_ABSTRACTION_ONLY",
        "execution_mode":"AUTOMATIC_SHADOW_TRANSFORM_ON_EXPLICIT_REVIEW_ALLOWED_INPUTS",
        "review_allowed_input_count":len(eligible),
        "decision_count":len(decisions),
        "hypothesis_count":len(hypotheses),
        "unsupported_hold_count":len(holds),
        "family_summary":family_summary,
        "source_wording_or_iconography_reuse_forbidden":True,
        "commercial_eligibility_authority":False,
        "ip_safety_authority":False,
        "mechanism_production_authority":False,
        "idea_generation_authority":False,
        "bridge_query_authority":False,
        "anchor_assignment_authority":False,
        "watchlist_promotion_authority":False,
        "daily7_selection_authority":False
    }
    doc["mechanism_decomposition_decisions"]=decisions
    return doc

def validate(doc):
    meta=doc["mechanism_decomposition"]
    ds=doc["mechanism_decomposition_decisions"]
    eligible=collect_review_allowed(doc)
    assert meta["authority"]=="SHADOW_ABSTRACTION_ONLY"
    assert meta["execution_mode"]=="AUTOMATIC_SHADOW_TRANSFORM_ON_EXPLICIT_REVIEW_ALLOWED_INPUTS"
    assert meta["review_allowed_input_count"]==len(eligible)==len(ds)==meta["decision_count"]
    assert meta["source_wording_or_iconography_reuse_forbidden"] is True
    assert meta["commercial_eligibility_authority"] is False
    assert meta["ip_safety_authority"] is False
    assert meta["mechanism_production_authority"] is False
    assert meta["idea_generation_authority"] is False
    assert meta["bridge_query_authority"] is False
    assert meta["anchor_assignment_authority"] is False
    assert meta["watchlist_promotion_authority"] is False
    assert meta["daily7_selection_authority"] is False
    eligible_ids={x["opportunity_id"] for x in eligible}
    assert {x["opportunity_id"] for x in ds}==eligible_ids
    for d in ds:
        assert d["production_eligible"] is False
        if d["decomposition_state"]=="SHADOW_MECHANISM_HYPOTHESIS":
            h=d["mechanism_hypothesis"]
            assert h["source_specific_wording_or_iconography_reuse_allowed"] is False
            assert h["abstraction_level"]=="MECHANISM_FAMILY_ONLY_NOT_PRODUCT_CREATIVE"
            assert d["commercial_eligibility_decision"] is None
            assert d["ip_safety_decision"] is None
            assert d["trademark_clearance_performed"] is False
            assert d["copyright_or_property_clearance_performed"] is False
            assert d["idea_generation_performed"] is False
            assert d["bridge_query_materialized"] is False
            assert d["anchor_query_assigned"] is False
            assert d["watchlist_promotion_allowed"] is False
            assert d["daily7_selection_authority"] is False
    return True

def self_test():
    doc={
      "opportunity_intake":[
        {"opportunity_id":"p","merch_core":"im with stupid"},
        {"opportunity_id":"a","merch_core":"breast cancer awareness"},
        {"opportunity_id":"c","merch_core":"foam finger"},
        {"opportunity_id":"x","merch_core":"dolly parton"}
      ],
      "structural_triage_decisions":[
        {"opportunity_id":"p","structural_type":"PHRASE_EXPRESSION","confidence":"HIGH","reason_codes":["PRONOUN_LED_EXPRESSION_STRUCTURE"],"mechanism_decomposition_allowed":True},
        {"opportunity_id":"a","structural_type":"CAUSE_AWARENESS_EXPRESSION","confidence":"HIGH","reason_codes":["AWARENESS_EXPRESSION_TOKEN"],"mechanism_decomposition_allowed":True},
        {"opportunity_id":"c","structural_type":"UNRESOLVED_THEME_OBJECT_ENTITY_OR_PROPERTY","mechanism_decomposition_allowed":False},
        {"opportunity_id":"x","structural_type":"UNRESOLVED_THEME_OBJECT_ENTITY_OR_PROPERTY","mechanism_decomposition_allowed":False}
      ],
      "semantic_resolution_decisions":[
        {"opportunity_id":"c","semantic_class":"CULTURAL_SYMBOL_OR_OBJECT","confidence":"HIGH","reason_codes":["DESCRIPTION_CULTURAL_OBJECT_SIGNAL"],"mechanism_review_allowed":True,"provenance":{"qid":"Q1"}},
        {"opportunity_id":"x","semantic_class":"NAMED_PERSON_ENTITY","confidence":"HIGH","reason_codes":["DESCRIPTION_PERSON_ROLE_SIGNAL"],"mechanism_review_allowed":False,"provenance":{"qid":"Q2"}}
      ]
    }
    out=apply(doc); assert validate(out)
    assert out["mechanism_decomposition"]["review_allowed_input_count"]==3
    assert out["mechanism_decomposition"]["hypothesis_count"]==3
    by={x["opportunity_id"]:x for x in out["mechanism_decomposition_decisions"]}
    assert by["p"]["mechanism_hypothesis"]["mechanism_family"]=="RELATIONAL_OR_IDENTITY_PHRASE_EXPRESSION"
    assert by["a"]["mechanism_hypothesis"]["mechanism_family"]=="CAUSE_AFFILIATION_AND_AWARENESS_SIGNALING"
    assert by["c"]["mechanism_hypothesis"]["mechanism_family"]=="CULTURAL_SYMBOL_DISPLAY"
    assert "x" not in by
    assert all(x["production_eligible"] is False for x in by.values())
    print("A_MOMENTUM_MECHANISM_DECOMPOSITION_SELF_TEST_PASS",out["mechanism_decomposition"]["family_summary"])

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
    print("A_MOMENTUM_MECHANISM_DECOMPOSITION_PASS",json.dumps(doc["mechanism_decomposition"]["family_summary"],sort_keys=True))

if __name__=="__main__":
    main()
