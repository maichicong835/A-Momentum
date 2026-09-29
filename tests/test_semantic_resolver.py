#!/usr/bin/env python3
import importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("semantic_resolver",ROOT/"scripts"/"semantic_resolver.py")
s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)

class SemanticResolver(unittest.TestCase):
    def api(self,search_rows,entities=None):
        entities=entities or {}
        def fake(params):
            if params["action"]=="wbsearchentities":
                return {"search":search_rows}
            return {"entities":entities}
        return fake

    def test_unique_primary_label_can_canonicalize_multiple_exact_matches(self):
        rows=[
          {"id":"Q1","label":"Dolly Parton","description":"American singer, songwriter and actress","match":{"type":"label","text":"Dolly Parton"}},
          {"id":"Q2","label":"Other work","description":"song","match":{"type":"alias","text":"Dolly Parton"}}
        ]
        fake=self.api(rows)
        r=s.resolve_one("dolly parton",fake,fake)
        self.assertEqual(r["semantic_class"],"NAMED_PERSON_ENTITY")
        self.assertEqual(r["provenance"]["canonicalization_basis"],"UNIQUE_PRIMARY_LABEL_AMONG_EXACT_MATCHES")
        self.assertFalse(r["mechanism_review_allowed"])
        self.assertTrue(s.contains_term("American singer, songwriter and actress","singer"))
        self.assertFalse(s.contains_term("American singer, songwriter and actress","song"))

    def test_unique_enwiki_sitelink_can_canonicalize_alias_collision(self):
        rows=[
          {"id":"Q1","label":"The Creation of Adam","description":"fresco painting","match":{"type":"alias","text":"Creation of Adam"}},
          {"id":"Q2","label":"Copy of Creation of Adam","description":"artwork","match":{"type":"alias","text":"Creation of Adam"}}
        ]
        entities={
          "Q1":{"labels":{"en":{"value":"The Creation of Adam"}},"descriptions":{"en":{"value":"fresco painting by Michelangelo"}},"sitelinks":{"enwiki":{"title":"The Creation of Adam"}}},
          "Q2":{"labels":{"en":{"value":"Copy of Creation of Adam"}},"descriptions":{"en":{"value":"artwork"}},"sitelinks":{}}
        }
        fake=self.api(rows,entities)
        r=s.resolve_one("creation of adam",fake,fake)
        self.assertEqual(r["semantic_class"],"CREATIVE_PROPERTY_OR_WORK")
        self.assertEqual(r["provenance"]["canonicalization_basis"],"UNIQUE_ENWIKI_SITELINK_AMONG_EXACT_MATCHES")

    def test_multiple_canonical_exact_matches_remain_ambiguous(self):
        rows=[
          {"id":"Q1","label":"Underdog","description":"concept in competition","match":{"type":"label","text":"Underdog"}},
          {"id":"Q2","label":"Underdog","description":"animated television series","match":{"type":"label","text":"Underdog"}}
        ]
        entities={
          "Q1":{"labels":{"en":{"value":"Underdog"}},"descriptions":{"en":{"value":"concept in competition"}},"sitelinks":{"enwiki":{"title":"Underdog"}}},
          "Q2":{"labels":{"en":{"value":"Underdog"}},"descriptions":{"en":{"value":"animated television series"}},"sitelinks":{"enwiki":{"title":"Underdog (TV series)"}}}
        }
        fake=self.api(rows,entities)
        r=s.resolve_one("underdog",fake,fake)
        self.assertEqual(r["resolution_state"],"AMBIGUOUS_EXACT_METADATA_MATCH")
        self.assertIsNone(r["semantic_class"])

    def test_no_exact_match_remains_hold(self):
        fake=self.api([{"id":"Q9","label":"Sophie Cunningham","description":"American basketball player","match":{"type":"label","text":"Sophie Cunningham"}}])
        r=s.resolve_one("sophie cunningham indiana fever",fake,fake)
        self.assertEqual(r["resolution_state"],"NO_EXACT_METADATA_MATCH")

    def test_cultural_object_can_enter_review_not_auto_decomposition(self):
        rows=[{"id":"Q2","label":"Foam finger","description":"sports paraphernalia item used by fans","match":{"type":"label","text":"foam finger"}}]
        fake=self.api(rows)
        r=s.resolve_one("foam finger",fake,fake)
        self.assertEqual(r["semantic_class"],"CULTURAL_SYMBOL_OR_OBJECT")
        self.assertTrue(r["mechanism_review_allowed"])

    def test_layer_has_no_market_ip_commercial_or_production_authority(self):
        rows=[{"id":"Q1","label":"Dolly Parton","description":"American singer and actress","match":{"type":"label","text":"Dolly Parton"}}]
        fake=self.api(rows)
        doc={"structural_triage_decisions":[
          {"opportunity_id":"a","merch_core":"dolly parton","disposition":"HOLD_SEMANTIC_REVIEW"}
        ]}
        out=s.apply(doc,fake,fake,0)
        self.assertTrue(s.validate(out))
        d=out["semantic_resolution_decisions"][0]
        self.assertFalse(d["market_signal_authority"])
        self.assertFalse(d["commercial_eligibility_authority"])
        self.assertFalse(d["ip_safety_authority"])
        self.assertFalse(d["mechanism_decomposition_automatic"])
        self.assertFalse(d["production_eligible"])

if __name__=="__main__":
    unittest.main()
