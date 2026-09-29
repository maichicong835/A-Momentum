#!/usr/bin/env python3
import importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("structural_triage",ROOT/"scripts"/"structural_triage.py")
s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)

class StructuralTriage(unittest.TestCase):
    def test_high_confidence_expression_pass(self):
        a=s.triage_one({"opportunity_id":"a","merch_core":"im with stupid"})
        b=s.triage_one({"opportunity_id":"b","merch_core":"breast cancer awareness"})
        self.assertEqual(a["structural_type"],"PHRASE_EXPRESSION")
        self.assertEqual(b["structural_type"],"CAUSE_AWARENESS_EXPRESSION")
        self.assertTrue(a["mechanism_decomposition_allowed"])
        self.assertTrue(b["mechanism_decomposition_allowed"])

    def test_product_and_local_intent_hold(self):
        a=s.triage_one({"opportunity_id":"a","merch_core":"toddler long sleeve"})
        b=s.triage_one({"opportunity_id":"b","merch_core":"dolly parton near me"})
        self.assertEqual(a["disposition"],"HOLD_PRODUCT_CONFIGURATION")
        self.assertEqual(b["disposition"],"HOLD_LOCAL_PURCHASE_INTENT")
        self.assertFalse(a["mechanism_decomposition_allowed"])
        self.assertFalse(b["mechanism_decomposition_allowed"])

    def test_ambiguous_theme_or_entity_never_gets_fake_semantic_label(self):
        for core in ["dolly parton","foam finger","creation of adam","underdog"]:
            d=s.triage_one({"opportunity_id":core,"merch_core":core})
            self.assertEqual(d["disposition"],"HOLD_SEMANTIC_REVIEW")
            self.assertEqual(d["structural_type"],"UNRESOLVED_THEME_OBJECT_ENTITY_OR_PROPERTY")
            self.assertFalse(d["semantic_entity_resolution_performed"])
            self.assertFalse(d["named_entity_or_property_clearance_performed"])

    def test_one_decision_per_intake_and_no_authority_escalation(self):
        doc={"opportunity_intake":[
            {"opportunity_id":"a","merch_core":"im with stupid"},
            {"opportunity_id":"b","merch_core":"flannel"},
            {"opportunity_id":"c","merch_core":"foam finger"}
        ]}
        out=s.apply(doc)
        self.assertTrue(s.validate(out))
        self.assertEqual(out["structural_triage"]["decision_count"],3)
        self.assertFalse(out["structural_triage"]["commercial_eligibility_authority"])
        self.assertFalse(out["structural_triage"]["ip_safety_authority"])
        self.assertTrue(all(x["production_eligible"] is False for x in out["structural_triage_decisions"]))

if __name__=="__main__":
    unittest.main()
