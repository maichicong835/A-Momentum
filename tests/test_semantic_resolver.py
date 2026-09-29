#!/usr/bin/env python3
import importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("semantic_resolver",ROOT/"scripts"/"semantic_resolver.py")
s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)

class SemanticResolver(unittest.TestCase):
    def fake(self,rows):
        return lambda params: {"search":rows}

    def test_exact_person_is_metadata_resolved_but_not_mechanism_allowed(self):
        r=s.resolve_one("dolly parton",self.fake([{
            "id":"Q1","label":"Dolly Parton","description":"American singer and actress",
            "match":{"type":"label","text":"Dolly Parton"},"concepturi":"https://www.wikidata.org/entity/Q1"
        }]))
        self.assertEqual(r["resolution_state"],"RESOLVED_EXACT_METADATA")
        self.assertEqual(r["semantic_class"],"NAMED_PERSON_ENTITY")
        self.assertFalse(r["mechanism_review_allowed"])
        self.assertEqual(r["provenance"]["qid"],"Q1")

    def test_exact_alias_and_cultural_object_can_enter_review_not_auto_decomposition(self):
        r=s.resolve_one("foam finger",self.fake([{
            "id":"Q2","label":"Foam finger","description":"sports paraphernalia item used by fans",
            "match":{"type":"alias","text":"foam finger"}
        }]))
        self.assertEqual(r["semantic_class"],"CULTURAL_SYMBOL_OR_OBJECT")
        self.assertTrue(r["mechanism_review_allowed"])

    def test_multiple_exact_matches_remain_ambiguous(self):
        rows=[
          {"id":"Q1","label":"Underdog","description":"concept in competition","match":{"type":"label","text":"Underdog"}},
          {"id":"Q2","label":"Underdog","description":"animated television series","match":{"type":"label","text":"Underdog"}}
        ]
        r=s.resolve_one("underdog",self.fake(rows))
        self.assertEqual(r["resolution_state"],"AMBIGUOUS_EXACT_METADATA_MATCH")
        self.assertIsNone(r["semantic_class"])

    def test_no_exact_match_remains_hold(self):
        r=s.resolve_one("sophie cunningham indiana fever",self.fake([{
            "id":"Q9","label":"Sophie Cunningham","description":"American basketball player","match":{"type":"label","text":"Sophie Cunningham"}
        }]))
        self.assertEqual(r["resolution_state"],"NO_EXACT_METADATA_MATCH")

    def test_layer_has_no_market_ip_commercial_or_production_authority(self):
        doc={"structural_triage_decisions":[
          {"opportunity_id":"a","merch_core":"dolly parton","disposition":"HOLD_SEMANTIC_REVIEW"}
        ]}
        out=s.apply(doc,self.fake([{
          "id":"Q1","label":"Dolly Parton","description":"American singer and actress",
          "match":{"type":"label","text":"Dolly Parton"}
        }]),0)
        self.assertTrue(s.validate(out))
        d=out["semantic_resolution_decisions"][0]
        self.assertFalse(d["market_signal_authority"])
        self.assertFalse(d["commercial_eligibility_authority"])
        self.assertFalse(d["ip_safety_authority"])
        self.assertFalse(d["mechanism_decomposition_automatic"])
        self.assertFalse(d["production_eligible"])

if __name__=="__main__":
    unittest.main()
