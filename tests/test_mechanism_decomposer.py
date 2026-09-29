#!/usr/bin/env python3
import importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("mechanism_decomposer",ROOT/"scripts"/"mechanism_decomposer.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class MechanismDecomposer(unittest.TestCase):
    def base_doc(self):
        return {
          "opportunity_intake":[
            {"opportunity_id":"p","merch_core":"im with stupid"},
            {"opportunity_id":"a","merch_core":"breast cancer awareness"},
            {"opportunity_id":"c","merch_core":"foam finger"},
            {"opportunity_id":"x","merch_core":"dolly parton"}
          ],
          "structural_triage_decisions":[
            {"opportunity_id":"p","structural_type":"PHRASE_EXPRESSION","confidence":"HIGH","reason_codes":[],"mechanism_decomposition_allowed":True},
            {"opportunity_id":"a","structural_type":"CAUSE_AWARENESS_EXPRESSION","confidence":"HIGH","reason_codes":[],"mechanism_decomposition_allowed":True},
            {"opportunity_id":"c","structural_type":"UNRESOLVED_THEME_OBJECT_ENTITY_OR_PROPERTY","mechanism_decomposition_allowed":False},
            {"opportunity_id":"x","structural_type":"UNRESOLVED_THEME_OBJECT_ENTITY_OR_PROPERTY","mechanism_decomposition_allowed":False}
          ],
          "semantic_resolution_decisions":[
            {"opportunity_id":"c","semantic_class":"CULTURAL_SYMBOL_OR_OBJECT","confidence":"HIGH","reason_codes":[],"mechanism_review_allowed":True,"provenance":{"qid":"Q1"}},
            {"opportunity_id":"x","semantic_class":"NAMED_PERSON_ENTITY","confidence":"HIGH","reason_codes":[],"mechanism_review_allowed":False,"provenance":{"qid":"Q2"}}
          ]
        }

    def test_only_explicit_review_allowed_inputs_enter_decomposition(self):
        out=m.apply(self.base_doc())
        self.assertTrue(m.validate(out))
        ids={x["opportunity_id"] for x in out["mechanism_decomposition_decisions"]}
        self.assertEqual(ids,{"p","a","c"})
        self.assertNotIn("x",ids)

    def test_phrase_is_abstracted_not_reused_as_product_copy(self):
        out=m.apply(self.base_doc())
        d={x["opportunity_id"]:x for x in out["mechanism_decomposition_decisions"]}["p"]
        h=d["mechanism_hypothesis"]
        self.assertEqual(h["mechanism_family"],"RELATIONAL_OR_IDENTITY_PHRASE_EXPRESSION")
        self.assertFalse(h["source_specific_wording_or_iconography_reuse_allowed"])
        self.assertEqual(h["abstraction_level"],"MECHANISM_FAMILY_ONLY_NOT_PRODUCT_CREATIVE")
        self.assertFalse(d["idea_generation_performed"])

    def test_cause_and_cultural_object_map_to_distinct_families(self):
        out=m.apply(self.base_doc())
        by={x["opportunity_id"]:x for x in out["mechanism_decomposition_decisions"]}
        self.assertEqual(by["a"]["mechanism_hypothesis"]["mechanism_family"],"CAUSE_AFFILIATION_AND_AWARENESS_SIGNALING")
        self.assertEqual(by["c"]["mechanism_hypothesis"]["mechanism_family"],"CULTURAL_SYMBOL_DISPLAY")

    def test_no_authority_escalation(self):
        out=m.apply(self.base_doc())
        meta=out["mechanism_decomposition"]
        self.assertFalse(meta["commercial_eligibility_authority"])
        self.assertFalse(meta["ip_safety_authority"])
        self.assertFalse(meta["mechanism_production_authority"])
        self.assertFalse(meta["idea_generation_authority"])
        self.assertFalse(meta["bridge_query_authority"])
        self.assertFalse(meta["anchor_assignment_authority"])
        self.assertFalse(meta["watchlist_promotion_authority"])
        self.assertFalse(meta["daily7_selection_authority"])
        self.assertTrue(all(x["production_eligible"] is False for x in out["mechanism_decomposition_decisions"]))

if __name__=="__main__":
    unittest.main()
