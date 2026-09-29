#!/usr/bin/env python3
import importlib.util, pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("wave_coupler",ROOT/"scripts"/"wave_coupler.py")
w=importlib.util.module_from_spec(spec); spec.loader.exec_module(w)

class Coupler(unittest.TestCase):
    def test_conservative_matching(self):
        self.assertTrue(w.conservative_match("Alpha Wave","alpha wave shirt"))
        self.assertTrue(w.conservative_match("Delta","delta shirts"))
        self.assertFalse(w.conservative_match("Delta","delta airlines shirt sale"))
        self.assertEqual(w.match_relation("Dolly Parton estate planning","dolly parton"),"PARTIAL_PHRASE_OVERLAP")
    def test_cross_seed_merch_variants_group_without_losing_evidence(self):
        rows=[
            {"source_seed":"shirt","rank":1,"related_query":"im with stupid shirt","rising_value":6000,"is_breakout":False},
            {"source_seed":"t shirt","rank":2,"related_query":"i'm with stupid t shirt","rising_value":1200,"is_breakout":False}
        ]
        groups=w.group_merch_waves(rows)
        self.assertEqual(len(groups),1)
        self.assertEqual(groups[0]["merch_core"],"im with stupid")
        self.assertEqual(len(groups[0]["seed_evidence"]),2)

    def test_partial_entity_overlap_is_unresolved_not_coupled(self):
        raw={"candidates":[{"wave_id":"r1","raw_trend_title":"Dolly Parton estate planning"}]}
        merch={"provider_status":"PASS_WITH_DATA","merch_waves":[
            {"source_seed":"shirt","rank":1,"related_query":"Dolly Parton shirt","rising_value":80,"is_breakout":False}
        ]}
        out=w.build(raw,merch)
        self.assertEqual(out["coupling_summary"]["COUPLED_WAVE"],0)
        self.assertEqual(out["coupling_summary"]["UNRESOLVED"],1)
        c=out["couplings"][0]
        self.assertEqual(c["unresolved_reason"],"PARTIAL_PHRASE_OR_ENTITY_OVERLAP_NOT_PHENOMENON_PROOF")
        self.assertEqual(len(c["merch_overlap_candidates"]),1)

    def test_states_and_boundaries(self):
        raw={"candidates":[{"wave_id":"r1","raw_trend_title":"Alpha Wave"},{"wave_id":"r2","raw_trend_title":"Beta Event"}]}
        merch={"provider_status":"PASS_WITH_DATA","merch_waves":[
            {"source_seed":"shirt","rank":1,"related_query":"Alpha Wave shirt","rising_value":"Breakout","is_breakout":True},
            {"source_seed":"shirts","rank":2,"related_query":"Crochet gifts shirts","rising_value":200,"is_breakout":False},
            {"source_seed":"t shirt","rank":3,"related_query":"crochet gifts t shirt","rising_value":100,"is_breakout":False}
        ]}
        out=w.build(raw,merch)
        self.assertTrue(w.validate_output(out))
        self.assertEqual(out["coupling_summary"]["COUPLED_WAVE"],1)
        self.assertEqual(out["coupling_summary"]["RAW_ONLY_WAVE"],1)
        self.assertEqual(out["coupling_summary"]["MERCH_NATIVE_WAVE"],1)
        self.assertEqual(out["merch_observation_count"],3)
        self.assertEqual(out["unique_merch_core_count"],2)
        self.assertFalse(out["commercial_eligibility_automatic"])
        self.assertTrue(all(x["bridge_queries"]==[] and x["anchor_query"] is None for x in out["couplings"]))
if __name__=="__main__": unittest.main()
